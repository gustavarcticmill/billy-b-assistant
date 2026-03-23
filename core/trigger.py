"""Session trigger abstraction for multi-source session lifecycle.

Provides trigger_session_start(source) and trigger_session_stop(source) as the
single entry point for starting/stopping conversation sessions from any trigger
source: hardware button, wake word detection, or UI test.
"""

import asyncio
import contextlib
import threading
import time
from concurrent.futures import CancelledError

from . import audio, config
from .logger import logger
from .movements import move_head
from .session_manager import BillySession


# Session state (moved from button.py)
is_active = False
session_thread = None
interrupt_event = threading.Event()
session_instance: BillySession | None = None
_session_start_lock = threading.Lock()

# D-04: Global debounce -- single timer, any source resets it
_last_trigger_time: float = 0.0
_DEBOUNCE_SECONDS: float = 0.5

# D-05: ALSA mic handoff delay (configurable within 50-100ms range)
_MIC_HANDOFF_DELAY: float = 0.075  # 75ms default


def _force_release_session_start_lock(reason: str):
    """Best-effort lock release to recover from stuck session threads."""
    if _session_start_lock.locked():
        try:
            _session_start_lock.release()
            logger.warning(f"Force-released session start lock ({reason})", "Broom")
        except RuntimeError:
            # Lock may have been released concurrently.
            pass


def trigger_session_start(source: str) -> None:
    """Start a conversation session from any trigger source.

    Args:
        source: Trigger source identifier -- "hardware", "wake_word", or "ui_test".
    """
    global is_active, session_thread, interrupt_event, session_instance
    global _last_trigger_time

    # D-04: Global debounce -- any source resets the timer
    now = time.time()
    if now - _last_trigger_time < _DEBOUNCE_SECONDS:
        return
    _last_trigger_time = now

    # D-03/WAKE-07: Hardware source requires physical button to be pressed
    if source == "hardware":
        from . import button as _btn

        if not _btn.button.is_pressed:
            return

    # If session is already active, stop it instead
    if is_active:
        trigger_session_stop(source)
        return

    # Use lock to prevent concurrent session starts
    if not _session_start_lock.acquire(blocking=False):
        # Recovery path: if no active session is running, try to clear a stale
        # lock/thread.
        if not is_active:
            logger.warning(
                "Session start lock busy while inactive; attempting recovery",
                "Fire",
            )
            if session_thread and session_thread.is_alive():
                interrupt_event.set()
                audio.stop_playback()
                if session_instance and session_instance.loop:
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            session_instance.stop_session(),
                            session_instance.loop,
                        )
                        with contextlib.suppress(Exception):
                            future.result(timeout=1.5)
                    except Exception as e:
                        logger.warning(
                            f"Stale-session stop during recovery failed: {e}",
                            "Warning",
                        )
                session_thread.join(timeout=1.0)
            if session_thread and session_thread.is_alive():
                logger.warning(
                    "Session thread still alive during recovery; forcing stale cleanup",
                    "Warning",
                )
            # Always attempt to recover lock here; stale thread may linger but
            # should not block new triggers indefinitely.
            session_instance = None
            session_thread = None
            _force_release_session_start_lock("inactive stale lock recovery")
            if _session_start_lock.acquire(blocking=False):
                logger.info("Recovered stale session lock; continuing start", "Check")
            else:
                logger.warning(
                    "Could not recover session lock yet, try again",
                    "Warning",
                )
                return
        else:
            logger.warning(
                "Session start already in progress, ignoring trigger",
                "Warning",
            )
            return

    try:
        # D-05/WAKE-04: Notify hotword controller before session mic opens
        from .hotword import controller as _hw

        _hw.notify_session_state(True)
        time.sleep(_MIC_HANDOFF_DELAY)

        # Ensure previous session thread is fully finished before starting new
        if session_thread and session_thread.is_alive():
            logger.warning("Previous session thread still running, waiting...", "Wait")
            session_thread.join(timeout=2.0)
            if session_thread.is_alive():
                logger.warning(
                    "Previous session thread did not finish, attempting forced stop",
                    "Warning",
                )
                if session_instance and session_instance.loop:
                    with contextlib.suppress(Exception):
                        future = asyncio.run_coroutine_threadsafe(
                            session_instance.request_stop(),
                            session_instance.loop,
                        )
                        future.result(timeout=1.0)
                    with contextlib.suppress(Exception):
                        future = asyncio.run_coroutine_threadsafe(
                            session_instance._close_ws(timeout=0.5),
                            session_instance.loop,
                        )
                        future.result(timeout=2.0)
                session_thread.join(timeout=1.5)
                if session_thread.is_alive():
                    if not is_active:
                        logger.warning(
                            "Detaching stale inactive session thread and continuing",
                            "Broom",
                        )
                        session_thread = None
                        session_instance = None
                    else:
                        logger.error(
                            "Previous session thread did not finish,"
                            " aborting new session",
                            "Error",
                        )
                        _session_start_lock.release()
                        return

        audio.ensure_playback_worker_started(config.CHUNK_MS)
        # Clear the playback done event so session waits for wake-up sound
        audio.playback_done_event.clear()
        # WAKE-06: Play wake-up sound for all trigger sources
        threading.Thread(target=audio.play_random_wake_up_clip, daemon=True).start()
        is_active = True
        interrupt_event = threading.Event()  # Fresh event for each session
        logger.info(f"Session triggered by {source}. Listening...", "Mic")

        def run_session():
            global session_instance, is_active
            try:
                session_instance = BillySession(interrupt_event=interrupt_event)
                session_instance.last_activity[0] = time.time()
                asyncio.run(session_instance.start())
            except Exception as e:
                logger.error(f"Session error: {e}")
            finally:
                move_head("off")
                is_active = False
                session_instance = None  # Clear reference

                # D-06/WAKE-09: Resume wake word listening immediately
                # Controller's 2.0s cooldown prevents self-trigger
                _hw.notify_session_state(False)

                # D-07: Verify wake word stream recovers
                if config.WAKE_WORD_ENABLED:
                    time.sleep(0.1)  # Brief settle time
                    _status = _hw.get_status()
                    if not _status.get("running") and _status.get("enabled"):
                        logger.warning(
                            "Wake word stream did not reopen after session;"
                            " retrying...",
                            "Warning",
                        )
                        time.sleep(0.5)
                        _hw.notify_session_state(False)  # Retry
                        time.sleep(0.1)
                        _status = _hw.get_status()
                        if not _status.get("running") and _status.get("enabled"):
                            logger.error(
                                "Wake word stream failed to reopen after"
                                " retry. Wake word disabled until restart.",
                                "Error",
                            )

                logger.info("Waiting for trigger...", "Clock")
                # Release lock when session finishes
                with contextlib.suppress(Exception):
                    _session_start_lock.release()

        session_thread = threading.Thread(target=run_session, daemon=True)
        session_thread.start()
        # Lock will be released by the session thread when it finishes
    except Exception as e:
        # If anything goes wrong, release the lock
        logger.error(f"Error starting session: {e}")
        with contextlib.suppress(Exception):
            _session_start_lock.release()


def trigger_session_stop(source: str) -> None:
    """Stop an active conversation session from any trigger source.

    Args:
        source: Trigger source identifier -- "hardware", "wake_word", or "ui_test".
    """
    global is_active, session_thread, session_instance

    logger.info(f"Stop triggered by {source} during active session.", "Stop")

    # Try to hand turn back to user if assistant is speaking
    if (
        session_instance
        and session_instance.loop
        and session_instance.is_assistant_turn()
    ):
        try:
            logger.info("Assistant is speaking. Handing turn back to user...", "Mic")
            future = asyncio.run_coroutine_threadsafe(
                session_instance.interrupt_to_user_turn(),
                session_instance.loop,
            )
            future.result(timeout=3.0)
            logger.success("Turn handed back to user (mic open).")
            return
        except Exception as e:
            logger.warning(f"Turn handoff failed, stopping session instead: {e}")

    interrupt_event.set()
    audio.stop_playback()

    if session_instance:
        try:
            logger.info("Stopping active session...", "Stop")
            with contextlib.suppress(CancelledError):
                future = asyncio.run_coroutine_threadsafe(
                    session_instance.stop_session(), session_instance.loop
                )
                # Add timeout to prevent hanging
                try:
                    future.result(timeout=5.0)
                    logger.success("Session stopped.")
                except TimeoutError:
                    logger.warning("Session stop timeout, forcing cleanup")
                    with contextlib.suppress(Exception):
                        force_stop_future = asyncio.run_coroutine_threadsafe(
                            session_instance.request_stop(),
                            session_instance.loop,
                        )
                        force_stop_future.result(timeout=1.0)
                    with contextlib.suppress(Exception):
                        force_close_future = asyncio.run_coroutine_threadsafe(
                            session_instance._close_ws(timeout=0.5),
                            session_instance.loop,
                        )
                        force_close_future.result(timeout=2.0)
        except Exception as e:
            logger.warning(f"Error stopping session ({type(e)}): {e}")
        finally:
            # Always ensure cleanup
            session_instance = None
            # Wait for session thread to finish to ensure mic is fully closed
            if session_thread and session_thread.is_alive():
                logger.info("Waiting for session thread to finish...", "Wait")
                session_thread.join(timeout=2.0)
                if session_thread.is_alive():
                    logger.warning("Session thread did not finish in time", "Warning")
                    _force_release_session_start_lock("session thread timeout")
    is_active = False

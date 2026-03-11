"""Microphone management wrapper for Billy session."""

import asyncio
import time

import numpy as np

from .. import audio
from ..config import DEBUG_MODE, SILENCE_THRESHOLD, TEXT_ONLY_MODE
from ..logger import logger
from ..mic import MicManager


class MicManagerWrapper:
    """Manages microphone lifecycle and audio input."""

    def __init__(self, session):
        self.session = session
        self.mic = MicManager()
        self.mic_running = False
        self.mic_timeout_task = None
        self.last_rms = 0.0
        self._mic_guard_until = 0.0
        self._mic_data_started = False
        self._logged_waiting_for_wakeup = False

    def start(self, *, retry=True):
        """Try to open the mic with optional retry on failure."""
        if self.mic_running or not self.session.session_active.is_set():
            return

        try:
            if self.mic is None:
                self.mic = MicManager()

            self.mic.start(self.callback)
            self.mic_running = True
            self._mic_guard_until = time.time() + 0.35
            if DEBUG_MODE:
                logger.info("Mic started", "🎤")
            if not self.mic_timeout_task or self.mic_timeout_task.done():
                self.mic_timeout_task = asyncio.create_task(self.timeout_checker())
            self.session._set_listening_state()

        except Exception as e:
            self.mic_running = False
            logger.error(f"Mic start failed: {e}")
            if retry and self.session.session_active.is_set():
                asyncio.create_task(self._retry_loop())

    def stop(self):
        """Stop the microphone."""
        if self.mic_running:
            try:
                self.mic.stop()
                time.sleep(0.1)
            except Exception as e:
                logger.warning(f"Error stopping mic: {e}")
            self.mic_running = False

    async def start_after_playback(self, delay: float = 0.6, retries: int = 3) -> bool:
        """Open mic after playback with retry logic."""
        for attempt in range(1, retries + 1):
            try:
                if attempt > 1:
                    wait_time = delay * (attempt - 1) + 0.5
                    logger.info(
                        f"Waiting {wait_time:.1f}s before mic retry {attempt}...", "⏳"
                    )
                    await asyncio.sleep(wait_time)

                if self.mic_running:
                    self.mic.stop()
                    self.mic_running = False
                    await asyncio.sleep(0.2)

                if not self.mic_running:
                    self.mic.start(self.callback)
                    self.mic_running = True
                    self._mic_guard_until = time.time() + 0.35
                    if not self.mic_timeout_task or self.mic_timeout_task.done():
                        self.mic_timeout_task = asyncio.create_task(
                            self.timeout_checker()
                        )
                    self.session._set_listening_state()
                print(f"🎙️ Mic opened (attempt {attempt}).")
                return True
            except Exception as e:
                logger.warning(f"Mic open failed (attempt {attempt}/{retries}): {e}")
                if "Device unavailable" in str(e) and attempt < retries:
                    await self._reset_audio_system()

        logger.error("Mic failed to open after retries.")
        return False

    def callback(self, indata, *_):
        """Handle incoming audio data from microphone."""
        if not self.session.session_active.is_set():
            return

        if not self.session.state.allow_mic_input:
            return

        # Don't send audio while Billy is speaking (prevents echo)
        if self.session.state.assistant_speaking:
            return

        # Don't send audio while response is active (prevents echo from buffered audio)
        if self.session.state.response_active:
            return

        if not TEXT_ONLY_MODE and not audio.playback_done_event.is_set():
            if not self._logged_waiting_for_wakeup:
                logger.info("🔇 Mic waiting for wake-up sound to finish...", "⏳")
                self._logged_waiting_for_wakeup = True
            return

        if not self._mic_data_started and not TEXT_ONLY_MODE:
            logger.info("Mic data now being sent (wake-up sound finished)", "🎤")
            self._mic_data_started = True

        samples = indata[:, 0]
        rms = np.sqrt(np.mean(np.square(samples.astype(np.float32))))
        self.last_rms = rms

        if DEBUG_MODE:
            print(f"\r🎙️ Mic Volume: {rms:.1f}", end="", flush=True)

        if time.time() < self._mic_guard_until:
            return

        if rms > SILENCE_THRESHOLD:
            self.session.state.update_activity()
            self.session.state.increment_loud_mic_chunks()

        self.session.state.increment_mic_chunks()
        audio.send_mic_audio(self.session.ws, samples, self.session.loop)

    async def timeout_checker(self):
        """Monitor mic activity and timeout if idle too long."""
        from ..config import MIC_TIMEOUT_SECONDS
        from ..movements import move_tail_async

        logger.info("Mic timeout checker active", "🛡️")
        last_tail_move = 0

        while self.session.session_active.is_set():
            if not self.mic_running:
                await asyncio.sleep(0.2)
                continue

            # Don't timeout while assistant is actively processing/responding.
            if self.session.state.response_active:
                await asyncio.sleep(0.2)
                continue

            now = time.time()
            idle_seconds = now - max(
                self.session.last_activity[0], audio.last_played_time
            )
            timeout_offset = 2

            if idle_seconds - timeout_offset > 0.5:
                elapsed = idle_seconds - timeout_offset
                progress = min(elapsed / MIC_TIMEOUT_SECONDS, 1.0)
                bar_len = 20
                filled = int(bar_len * progress)
                bar = "█" * filled + "-" * (bar_len - filled)
                print(
                    f"\r👂 {MIC_TIMEOUT_SECONDS}s timeout: [{bar}] {elapsed:.1f}s "
                    f"| Mic Volume:: {self.last_rms:.4f} / Threshold: {SILENCE_THRESHOLD:.4f}",
                    end="",
                    flush=True,
                )

                if now - last_tail_move > 1.0:
                    move_tail_async(duration=0.2)
                    last_tail_move = now

                if elapsed > MIC_TIMEOUT_SECONDS:
                    logger.info(
                        f"No mic activity for {MIC_TIMEOUT_SECONDS}s. Ending input...",
                        "⏱️",
                    )
                    await self.session.stop_session()
                    break

            await asyncio.sleep(0.5)

    async def _retry_loop(self):
        """Retry opening mic once with backoff."""
        if DEBUG_MODE:
            logger.verbose("Mic retry loop started", "🔁")

        if not self.session.session_active.is_set():
            return

        await asyncio.sleep(0.5)

        try:
            self.mic = MicManager()
        except Exception as e:
            logger.warning(f"MicManager recreate failed: {e}")

        try:
            self.mic.start(self.callback)
            self.mic_running = True
            self._mic_guard_until = time.time() + 0.35
            logger.info("Mic started after retry", "✅")
            if not self.mic_timeout_task or self.mic_timeout_task.done():
                self.mic_timeout_task = asyncio.create_task(self.timeout_checker())
            self.session._set_listening_state()
        except Exception as e:
            self.mic_running = False
            logger.warning(f"Mic retry failed: {e}")
            logger.info("Assuming no follow-up needed, ending session.", "🛑")
            await self.session.stop_session()

    async def _reset_audio_system(self):
        """Reset audio system for device unavailable errors."""
        logger.info("Attempting audio system reset...", "🔄")
        try:
            import subprocess

            import sounddevice as sd

            sd._terminate()
            await asyncio.sleep(0.5)
            sd._initialize()

            subprocess.run(
                ["sudo", "alsactl", "restore"], capture_output=True, timeout=5
            )
            subprocess.run(
                ["sudo", "fuser", "-k", "/dev/snd/*"], capture_output=True, timeout=3
            )

            await asyncio.sleep(2.0)
            logger.info("Audio system reset completed", "✅")
        except Exception as e:
            logger.warning(f"Audio reset failed: {e}")

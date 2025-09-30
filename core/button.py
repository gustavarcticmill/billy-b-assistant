import asyncio
import contextlib
import threading
import time
from concurrent.futures import CancelledError

from gpiozero import Button

from . import audio, config
from .hotword import controller as wake_word_controller
from .movements import move_head
from .session import BillySession


SOURCE_LABELS = {
    "hardware": "hardware button",
    "wake_word": "wake word",
    "ui-test": "UI test",
}

TRIGGER_DEBOUNCE_SECONDS = 0.5


# Button and session globals
is_active = False
active_source: str | None = None
session_thread: threading.Thread | None = None
interrupt_event = threading.Event()
session_instance: BillySession | None = None
last_trigger_times: dict[str, float] = {}
state_lock = threading.RLock()

# Setup hardware button
button = Button(config.BUTTON_PIN, pull_up=True)


def is_billy_speaking():
    """Return True if Billy is playing audio (wake-up or response)."""
    if not audio.playback_done_event.is_set():
        return True
    return bool(not audio.playback_queue.empty())


def _source_label(source: str | None) -> str:
    if source is None:
        return "unknown"
    return SOURCE_LABELS.get(source, source)


def trigger_session_start(source: str) -> bool:
    global is_active, active_source, interrupt_event, session_thread

    now = time.time()
    label = _source_label(source)

    with state_lock:
        last_time = last_trigger_times.get(source, 0.0)
        if now - last_time < TRIGGER_DEBOUNCE_SECONDS:
            return False

        if is_active:
            owner = _source_label(active_source)
            if source != active_source:
                print(f"⏳ Ignoring {label} trigger; session owned by {owner}.")
            last_trigger_times[source] = now
            return False

        last_trigger_times[source] = now
        is_active = True
        active_source = source
        interrupt_event = threading.Event()

    wake_word_controller.notify_session_state(True)
    audio.ensure_playback_worker_started(config.CHUNK_MS)
    threading.Thread(target=audio.play_random_wake_up_clip, daemon=True).start()
    print(f"🎤 Session triggered by {label}. Listening...")

    def run_session():
        global session_instance, is_active, active_source, session_thread
        try:
            move_head("on")
            session_instance = BillySession(interrupt_event=interrupt_event)
            session_instance.last_activity[0] = time.time()
            asyncio.run(session_instance.start())
        finally:
            move_head("off")
            session_instance = None
            with state_lock:
                is_active = False
                active_source = None
                session_thread = None
            wake_word_controller.notify_session_state(False)
            print("🕐 Waiting for trigger...")

    runner = threading.Thread(target=run_session, daemon=True)
    with state_lock:
        session_thread = runner
    runner.start()
    return True


def trigger_session_stop(source: str, *, reason: str | None = None, force: bool = False) -> bool:
    global session_instance

    now = time.time()
    label = _source_label(source)

    with state_lock:
        if not is_active:
            return False
        current_owner = active_source
        last_trigger_times[source] = now

    if current_owner and source != current_owner and not force:
        print(
            f"ℹ️ {label} requested stop but session owned by {_source_label(current_owner)}. Continuing with stop."
        )

    print(f"🔁 Stop requested by {label}{f' ({reason})' if reason else ''}.")
    interrupt_event.set()
    audio.stop_playback()

    instance = session_instance
    if instance:
        try:
            print("🛑 Stopping active session...")
            with contextlib.suppress(CancelledError):
                future = asyncio.run_coroutine_threadsafe(
                    instance.stop_session(), instance.loop
                )
                future.result()
            print("✅ Session stopped.")
        except Exception as err:  # noqa: BLE001
            print(f"⚠️ Error stopping session ({type(err)}): {err}")
    return True


def on_button():
    if not button.is_pressed:
        return

    if is_active:
        print("🔁 Button pressed during active session.")
        trigger_session_stop("hardware")
        return

    if not trigger_session_start("hardware"):
        print("⚠️ Button trigger ignored due to debounce or active session.")


def start_loop():
    audio.detect_devices(debug=config.DEBUG_MODE)
    button.when_pressed = on_button
    wake_word_controller.set_parameters(
        enabled=config.WAKE_WORD_ENABLED,
        sensitivity=config.WAKE_WORD_SENSITIVITY,
        threshold=config.WAKE_WORD_THRESHOLD,
        endpoint=config.WAKE_WORD_ENDPOINT,
        porcupine_access_key=config.WAKE_WORD_PORCUPINE_ACCESS_KEY,
    )

    if config.WAKE_WORD_ENABLED:
        wake_word_controller.set_detection_callback(_handle_wake_word_trigger)
        wake_word_controller.enable()
        wake_word_controller.start()
        print("🟢 Wake word listener active.")
    else:
        wake_word_controller.set_detection_callback(None)
        wake_word_controller.disable()
        wake_word_controller.stop()
        print("⚪️ Wake word listener disabled.")

    print("🎦 Ready. Press button or say the wake word to start a voice session. Press Ctrl+C to quit.")
    print("🕐 Waiting for trigger...")
    while True:
        time.sleep(0.1)


def _handle_wake_word_trigger(payload: dict | None) -> None:
    payload = payload or {}
    label = payload.get("label")
    score = payload.get("score")
    level = payload.get("level")

    if label and score is not None:
        print(f"👂 Wake word '{label}' detected (score={score:.2f}).")
    elif level is not None:
        print(f"👂 Wake word detected (level={level:.0f}).")
    else:
        print("👂 Wake word detected.")

    if not trigger_session_start("wake_word"):
        print("ℹ️ Wake word trigger ignored; session already active or debounced.")

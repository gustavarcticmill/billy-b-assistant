import time

from . import audio, config, trigger
from .logger import logger
from .movements import move_head, move_tail


try:
    from gpiozero import Button
    from gpiozero.mixins import HoldThread

    gpiozero_available = True
except ImportError:
    gpiozero_available = False

if config.MOCKFISH or not gpiozero_available:
    # Mock button in mockfish mode or if gpiozero not available
    class MockButton:
        def __init__(self, pin, pull_up=True):
            self.pin = pin
            self.when_pressed = None
            self.is_pressed = False
            if config.MOCKFISH:
                logger.info(f"Mockfish: Button on pin {pin} mocked", "Fish")
            elif not gpiozero_available:
                logger.info(
                    f"gpiozero not available: Button on pin {pin} mocked", "Fish"
                )
                # Start thread to listen for Enter key using pynput
                import threading

                threading.Thread(target=self._listen, daemon=True).start()

        def _listen(self):
            # Use fallback input() method for mock button
            self._fallback_listen()

        def _fallback_listen(self):
            import sys

            if not sys.stdin.isatty():
                logger.warning(
                    "stdin is not a tty, mock button input not available", "Warning"
                )
                return
            while True:
                try:
                    user_input = input("Press Enter to simulate button press: ")
                    if user_input == "" and self.when_pressed:
                        self.when_pressed()
                except (EOFError, KeyboardInterrupt):
                    break

        def close(self):
            pass

    Button = MockButton

# Setup hardware button
button = Button(config.BUTTON_PIN, pull_up=True)


def _ensure_button_hold_thread():
    """Work around rare gpiozero race where _hold_thread becomes None."""
    if config.MOCKFISH or not gpiozero_available:
        return
    try:
        hold_thread = getattr(button, "_hold_thread", None)
        if hold_thread is None:
            button._hold_thread = HoldThread(button)
            logger.warning("Repaired gpiozero button hold thread", "Wrench")
    except Exception as e:
        logger.warning(f"Failed to repair button hold thread: {e}", "Warning")


def is_billy_speaking():
    """Return True if Billy is playing audio (wake-up or response)."""
    if not audio.playback_done_event.is_set():
        return True
    return bool(not audio.playback_queue.empty())


def on_button():
    """Handle physical button press by delegating to trigger module."""
    trigger.trigger_session_start("hardware")


def start_loop():
    audio.detect_devices(debug=config.DEBUG_MODE)
    _ensure_button_hold_thread()

    # D-02/WAKE-05: Initialize wake word detection
    if config.WAKE_WORD_ENABLED:
        from .hotword import controller as wake_word_controller

        def _on_wake_word_detected(payload: dict) -> None:
            """Callback invoked by hotword controller on wake word detection."""
            logger.info(f"Wake word detected: {payload}", "Speech")
            trigger.trigger_session_start("wake_word")

        wake_word_controller.set_detection_callback(_on_wake_word_detected)
        wake_word_controller.start()
        logger.info("Wake word detection enabled and started", "Ear")
    else:
        logger.info("Wake word detection disabled (WAKE_WORD_ENABLED=false)", "Info")

    if config.FLAP_ON_BOOT:
        logger.info("Starting Billy startup animation", "Theater")
        move_head("on")
        time.sleep(0.5)
        move_tail(0.3)
        move_tail(0.3)
        move_head("off")
        time.sleep(0.5)
        move_tail(0.3)
        move_tail(0.3)
        logger.info("Billy startup animation complete", "Check")

    button.when_pressed = on_button
    logger.info(
        "Ready. Press button to start a voice session. Press Ctrl+C to quit.", "Movie"
    )
    logger.info("Waiting for button press...", "Clock")
    if config.MOCKFISH:
        logger.info("Mockfish mode: use Enter to simulate button press", "Fish")
        try:
            while True:
                input("Press Enter to simulate button press: ")
                button.is_pressed = True
                on_button()
        except KeyboardInterrupt:
            pass
    else:
        while True:
            _ensure_button_hold_thread()
            time.sleep(0.1)

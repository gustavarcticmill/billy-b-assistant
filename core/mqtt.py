import asyncio
import json
import os
import subprocess
import threading
import time

import paho.mqtt.client as mqtt

from .config import CHUNK_MS, MQTT_HOST, MQTT_PASSWORD, MQTT_PORT, MQTT_USERNAME
from .logger import logger
from .movements import stop_all_motors


mqtt_client: mqtt.Client | None = None
mqtt_connected = False


def mqtt_available():
    return all([MQTT_HOST, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD])


def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        logger.success("MQTT connected successfully!", "🔌")
        mqtt_send_discovery()
        client.subscribe("billy/command")
        client.subscribe("billy/say")  # single endpoint
        client.subscribe("billy/song")
        client.subscribe("billy/wakeup/play")
    else:
        logger.warning(f"MQTT connection failed with code {rc}")


def start_mqtt():
    global mqtt_client
    if not mqtt_available():
        logger.warning("MQTT not configured, skipping.")
        return

    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    def connect_with_retry():
        while True:
            try:
                mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
                mqtt_client.loop_start()
                mqtt_publish("billy/state", "idle", retain=True)
                return
            except Exception as e:
                logger.error(f"MQTT connection error: {e}")
                time.sleep(5)

    threading.Thread(target=connect_with_retry, daemon=True).start()


def stop_mqtt():
    global mqtt_client
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        logger.info("MQTT disconnected.", "🔌")


def mqtt_publish(topic, payload, retain=True, retry=True):
    global mqtt_client, mqtt_connected

    if mqtt_available():
        if not mqtt_client or not mqtt_connected:
            if retry:
                logger.info("MQTT not connected. Trying to reconnect...", "🔁")
                try:
                    mqtt_client.reconnect()
                    mqtt_connected = True
                except Exception as e:
                    logger.error(f"MQTT reconnect failed: {e}")
                    return
            else:
                logger.warning(
                    f"MQTT not connected. Skipping publish {topic}={payload}"
                )
                return

        try:
            mqtt_client.publish(topic, payload, retain=retain)
            logger.verbose(f"MQTT publish: {topic} = {payload} (retain={retain})", "📡")
        except Exception as e:
            logger.error(f"MQTT publish failed: {e}")


def mqtt_send_discovery():
    """Send MQTT discovery messages for Home Assistant."""
    if not mqtt_client:
        return

    device = {
        "identifiers": ["billy_bass"],
        "name": "Big Mouth Billy Bass",
        "model": "Billy Bassistant",
        "manufacturer": "ThingsFromThom",
    }

    # Sensor for Billy's state
    payload_sensor = {
        "name": "Billy State",
        "unique_id": "billy_state",
        "state_topic": "billy/state",
        "icon": "mdi:fish",
        "device": device,
    }
    mqtt_client.publish(
        "homeassistant/sensor/billy/state/config",
        json.dumps(payload_sensor),
        retain=True,
    )

    # Button to send shutdown command
    payload_button = {
        "name": "Billy Shutdown",
        "unique_id": "billy_shutdown",
        "command_topic": "billy/command",
        "payload_press": "shutdown",
        "device": device,
    }
    mqtt_client.publish(
        "homeassistant/button/billy/shutdown/config",
        json.dumps(payload_button),
        retain=True,
    )

    # Button to restart Billy service
    payload_button_restart = {
        "name": "Billy Restart",
        "unique_id": "billy_restart",
        "command_topic": "billy/command",
        "payload_press": "restart-billy",
        "device": device,
    }
    mqtt_client.publish(
        "homeassistant/button/billy/restart/config",
        json.dumps(payload_button_restart),
        retain=True,
    )

    # Button to reboot the system
    payload_button_reboot = {
        "name": "Billy Reboot",
        "unique_id": "billy_reboot",
        "command_topic": "billy/command",
        "payload_press": "reboot",
        "device": device,
    }
    mqtt_client.publish(
        "homeassistant/button/billy/reboot/config",
        json.dumps(payload_button_reboot),
        retain=True,
    )

    # Button to toggle listening
    payload_button_listen = {
        "name": "Billy Listen",
        "unique_id": "billy_listen",
        "command_topic": "billy/command",
        "payload_press": "listen",
        "device": device,
    }
    mqtt_client.publish(
        "homeassistant/button/billy/listen/config",
        json.dumps(payload_button_listen),
        retain=True,
    )

    # Single text entity
    payload_text_input = {
        "name": "Billy Say",
        "unique_id": "billy_say",
        "command_topic": "billy/say",
        "mode": "text",
        "max": 255,
        "device": device,
    }
    mqtt_client.publish(
        "homeassistant/text/billy/say/config",
        json.dumps(payload_text_input),
        retain=True,
    )

    # Single text entity for playing songs
    payload_song_input = {
        "name": "Billy Song",
        "unique_id": "billy_song",
        "command_topic": "billy/song",
        "mode": "text",
        "max": 255,
        "device": device,
    }
    mqtt_client.publish(
        "homeassistant/text/billy/song/config",
        json.dumps(payload_song_input),
        retain=True,
    )


# ----- Helpers ----------------------------------------------------------

FORCE_OFF_TAGS = ("[[nochat]]", "[[announce-only]]", "[[one-shot]]", "[[no-follow-up]]")
FORCE_ON_TAGS = ("[[chat]]", "[[follow-up]]")


def _parse_say_payload(raw: str):
    """
    Accept raw text or JSON: {"text":"...", "interactive": true/false}
    Plus inline flags inside text:
      [[nochat]] / [[announce-only]] / [[one-shot]] / [[no-follow-up]] -> interactive=False
      [[chat]] / [[follow-up]] -> interactive=True
    Returns (clean_text, interactive: None|True|False)
    """
    s = raw.strip()
    interactive = None
    text = s

    # JSON override (still single endpoint; optional for power-users)
    try:
        data = json.loads(s)
        if isinstance(data, dict):
            text = str(data.get("text", "")).strip()
            if "interactive" in data:
                interactive = bool(data["interactive"])
    except json.JSONDecodeError:
        pass

    low = text.lower()

    # Inline flags take precedence over JSON 'interactive'
    for tag in FORCE_OFF_TAGS:
        if tag in low:
            interactive = False
            text = re_sub_ignorecase(text, tag, "")

    for tag in FORCE_ON_TAGS:
        if tag in low:
            interactive = True
            text = re_sub_ignorecase(text, tag, "")

    return text.strip(), interactive


def _parse_song_payload(raw: str) -> str:
    """Accept raw text or JSON: {"song":"..."}; returns song name or empty string."""
    s = raw.strip()
    song = s
    try:
        data = json.loads(s)
        if isinstance(data, dict):
            song = str(data.get("song", "")).strip()
    except json.JSONDecodeError:
        pass
    return song.strip()


def re_sub_ignorecase(s: str, find: str, repl: str) -> str:
    import re

    return re.sub(re.escape(find), repl, s, flags=re.IGNORECASE)


def _run_async(coro):
    def _runner():
        asyncio.run(coro)

    threading.Thread(target=_runner, daemon=True).start()


# Helper functions for toggle listening -- delegate to trigger module
def mqtt_toggle_listening():
    from . import trigger

    if trigger.is_active:
        mqtt_stop_listening()
    else:
        mqtt_start_listening()


def mqtt_start_listening():
    """Start a listening session via MQTT command, delegating to trigger module."""
    from . import trigger

    trigger.trigger_session_start("mqtt")


def mqtt_stop_listening():
    """Stop an active listening session via MQTT command, delegating to trigger module."""
    from . import trigger

    if not trigger.is_active:
        return

    trigger.trigger_session_stop("mqtt")


# -----------------------------------------------------------------------


def on_message(client, userdata, msg):
    logger.verbose(f"MQTT message received: {msg.topic} = {msg.payload.decode()}", "📩")
    if msg.topic == "billy/command":
        command = msg.payload.decode().strip().lower()
        if command == "shutdown":
            logger.warning(
                "Shutdown command received over MQTT. Shutting down...", "🛑"
            )
            try:
                stop_all_motors()
            except Exception as e:
                logger.warning(f"Error stopping motors: {e}")
            stop_mqtt()
            subprocess.Popen(["sudo", "shutdown", "now"])

        elif command == "restart-billy":
            logger.warning(
                "Restart Billy command received over MQTT. Restarting service...", "🔁"
            )
            try:
                stop_all_motors()
            except Exception as e:
                logger.warning(f"Error stopping motors: {e}")
            subprocess.Popen(["sudo", "systemctl", "restart", "billy.service"])
        elif command == "reboot":
            logger.warning(
                "Reboot command received over MQTT. Rebooting system...", "🔁"
            )
            try:
                stop_all_motors()
            except Exception as e:
                logger.warning(f"Error stopping motors: {e}")
            stop_mqtt()
            subprocess.Popen(["sudo", "shutdown", "-r", "now"])
        elif command == "listen":
            logger.warning(
                "Listen command received over MQTT. Starting or stopping listening...",
                "🔁",
            )
            try:
                mqtt_toggle_listening()
            except Exception as e:
                logger.warning(f"Error starting/stopping listening: {e}")
        return

    if msg.topic == "billy/say":
        print(f"📩 Received SAY command: {msg.payload.decode()}")

        import asyncio
        import threading

        # 🔁 Lazy import here to avoid circular import with session.py
        from .say import say

        try:
            text = msg.payload.decode().strip()
            if text:

                def run_say():
                    asyncio.run(say(text=text))  # interactive=None -> AUTO follow-up

                threading.Thread(target=run_say, daemon=True).start()
            else:
                print("⚠️ SAY command received, but text was empty")
        except Exception as e:
            logger.error(f"Failed to run say(): {e}")
        return

    if msg.topic == "billy/song":
        print(f"📩 Received SONG command: {msg.payload.decode()}")
        try:
            from .audio import play_song

            song_name = _parse_song_payload(msg.payload.decode())
            if song_name:
                _run_async(play_song(song_name))
            else:
                print("⚠️ SONG command received, but song name was empty")
        except Exception as e:
            logger.error(f"Failed to run play_song(): {e}")
        return

    if msg.topic == "billy/wakeup/play":
        try:
            payload = json.loads(msg.payload.decode() or "{}")
            index = int(payload.get("index", 0))
            persona_name = str(payload.get("persona", "")).strip() or None

            if index < 1 or index > 99:
                logger.warning(
                    f"Invalid wakeup preview index received over MQTT: {index}", "⚠️"
                )
                return

            if not persona_name:
                from .persona_manager import persona_manager

                persona_name = persona_manager.current_persona

            project_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..")
            )
            sound_path = None
            if persona_name and persona_name != "default":
                persona_sound_path = os.path.join(
                    project_root, "personas", persona_name, "wakeup", f"{index}.wav"
                )
                if os.path.exists(persona_sound_path):
                    sound_path = persona_sound_path
            elif persona_name == "default":
                sound_path = os.path.join(
                    project_root, "sounds", "wake-up", "custom", f"{index}.wav"
                )

            if not sound_path:
                sound_path = os.path.join(
                    project_root, "sounds", "wake-up", "custom", f"{index}.wav"
                )

            if not os.path.exists(sound_path):
                logger.warning(
                    f"Wakeup preview clip not found: persona={persona_name} index={index}",
                    "⚠️",
                )
                return

            from .audio import enqueue_wav_to_playback, ensure_playback_worker_started

            ensure_playback_worker_started(CHUNK_MS)
            enqueue_wav_to_playback(sound_path)
            logger.info(
                f"Queued wakeup preview via MQTT: persona={persona_name} index={index}",
                "🔊",
            )
        except Exception as e:
            logger.error(f"Failed to process MQTT wakeup preview: {e}")

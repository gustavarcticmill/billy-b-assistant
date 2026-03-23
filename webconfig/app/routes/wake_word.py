"""Wake word detection web routes.

Exposes the WakeWordController's functionality (status, events, runtime config,
test triggers, and calibration) to the web dashboard.
"""

import dataclasses
import time

import numpy as np
import sounddevice as sd
from flask import Blueprint, jsonify, request


bp = Blueprint("wake_word", __name__)


@bp.route("/wake-word/status")
def status():
    """Return current wake word controller status."""
    try:
        from core.hotword import controller

        return jsonify(controller.get_status())
    except Exception as e:
        return jsonify({
            "enabled": False,
            "running": False,
            "error": str(e),
            "mode": "unavailable",
        })


@bp.route("/wake-word/events")
def events():
    """Drain up to 50 pending events from the controller queue."""
    try:
        import queue as queue_module

        from core.hotword import controller

        eq = controller.get_event_queue()
        drained = []
        for _ in range(50):
            try:
                event = eq.get_nowait()
                drained.append(dataclasses.asdict(event))
            except queue_module.Empty:
                break
        return jsonify({"events": drained, "count": len(drained)})
    except Exception as e:
        return jsonify({"events": [], "count": 0, "error": str(e)})


@bp.route("/wake-word/runtime-config", methods=["POST"])
def runtime_config():
    """Update controller parameters at runtime."""
    data = request.get_json() or {}
    try:
        from core.hotword import controller

        params = {}
        if "enabled" in data:
            params["enabled"] = str(data["enabled"]).lower() in (
                "true",
                "1",
                "yes",
            )
        if "sensitivity" in data:
            params["sensitivity"] = float(data["sensitivity"])
        if "threshold" in data:
            params["threshold"] = float(data["threshold"])
        if "endpoint" in data:
            params["endpoint"] = str(data["endpoint"])
        if "porcupine_access_key" in data:
            params["porcupine_access_key"] = str(
                data["porcupine_access_key"]
            )
        controller.set_parameters(**params)
        return jsonify({"status": "ok", "applied": list(params.keys())})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/wake-word/test", methods=["POST"])
def test():
    """Simulate or stop a session trigger for testing."""
    data = request.get_json() or {}
    action = data.get("action", "simulate")
    try:
        from core.trigger import trigger_session_start, trigger_session_stop

        if action == "simulate":
            trigger_session_start("ui_test")
            return jsonify({"status": "ok", "action": "simulate"})
        elif action == "stop":
            trigger_session_stop("ui_test")
            return jsonify({"status": "ok", "action": "stop"})
        else:
            return jsonify({"error": f"Unknown action: {action}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/wake-word/calibrate", methods=["POST"])
def calibrate():
    """Record ambient or phrase audio and return RMS metrics."""
    data = request.get_json() or {}
    mode = data.get("mode", "ambient")
    duration = 3  # seconds -- sufficient for RMS baseline

    try:
        from core.hotword import controller

        # Pause wake word listener to free the mic
        controller.notify_session_state(True)
        try:
            rms_values = []

            def _cal_callback(indata, frames, time_info, status):
                rms = float(np.sqrt(np.mean(np.square(indata))))
                rms_values.append(rms)

            with sd.InputStream(callback=_cal_callback):
                time.sleep(duration)

            if not rms_values:
                return jsonify({"error": "No audio data captured"}), 500

            rms_mean = float(np.mean(rms_values))
            rms_peak = float(np.max(rms_values))
            # For ambient mode: suggest threshold 50% above peak noise
            suggested_threshold = (
                round(rms_peak * 1.5) if mode == "ambient" else None
            )

            result = {
                "mode": mode,
                "rms_mean": round(rms_mean, 1),
                "rms_peak": round(rms_peak, 1),
                "duration_seconds": duration,
                "sample_count": len(rms_values),
            }
            if suggested_threshold is not None:
                result["suggested_threshold"] = suggested_threshold

            return jsonify(result)
        finally:
            # Always resume wake word listener
            controller.notify_session_state(False)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/wake-word/calibrate/apply", methods=["POST"])
def calibrate_apply():
    """Persist calibration values to .env and update runtime controller."""
    data = request.get_json() or {}
    try:
        from core.hotword import controller
        from dotenv import set_key

        from .system import ENV_PATH

        applied = {}
        if "threshold" in data:
            val = str(data["threshold"])
            set_key(
                ENV_PATH,
                "WAKE_WORD_THRESHOLD",
                val,
                quote_mode="never",
            )
            applied["threshold"] = val
        if "sensitivity" in data:
            val = str(data["sensitivity"])
            set_key(
                ENV_PATH,
                "WAKE_WORD_SENSITIVITY",
                val,
                quote_mode="never",
            )
            applied["sensitivity"] = val

        # Also update runtime controller
        params = {}
        if "threshold" in data:
            params["threshold"] = float(data["threshold"])
        if "sensitivity" in data:
            params["sensitivity"] = float(data["sensitivity"])
        if params:
            controller.set_parameters(**params)

        return jsonify({"status": "ok", "applied": applied})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

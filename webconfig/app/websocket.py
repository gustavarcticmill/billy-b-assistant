import json
import subprocess
import time

from flask import Blueprint
from flask_sock import Sock


bp = Blueprint("websocket", __name__)
sock = Sock()


def get_service_status():
    """Get full billy.service status with persona/personality data."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "billy.service"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        status = result.stdout.strip()

        # Get persona and personality data
        try:
            from core.persona_manager import persona_manager
            from core.personality import PERSONALITY

            return {
                "status": status,
                "current_persona": persona_manager.current_persona,
                "current_personality": PERSONALITY.to_dict()
                if hasattr(PERSONALITY, 'to_dict')
                else None,
            }
        except Exception:
            return {"status": status}
    except Exception:
        return {"status": "unknown"}


def get_logs(lines=50):
    """Get recent logs from billy.service."""
    try:
        result = subprocess.run(
            ["journalctl", "-u", "billy.service", "-n", str(lines), "--no-pager"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.stdout
    except Exception:
        return ""


@sock.route("/ws")
def websocket_handler(ws):
    """WebSocket endpoint for real-time updates."""
    last_status = None
    last_logs = None

    while True:
        try:
            # Check for status changes
            status = get_service_status()
            if status != last_status:
                ws.send(json.dumps({"type": "status", "data": status}))
                last_status = status

            # Check for new logs
            logs = get_logs(50)
            if logs != last_logs:
                ws.send(json.dumps({"type": "logs", "data": logs}))
                last_logs = logs

            # Sleep to avoid excessive polling
            time.sleep(1)

        except Exception:
            break

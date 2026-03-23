import os
import shutil
import subprocess

# Import logger
import sys
import threading
import time
import uuid
from pathlib import Path

from dotenv import find_dotenv, set_key
from flask import Blueprint, jsonify, render_template, request
from packaging.version import parse as parse_version

from core.news_manager import load_news_sources, save_news_sources

from ..core_imports import core_config, voice_provider_registry
from ..state import (
    PROJECT_ROOT,
    RELEASE_NOTE,
    get_current_version,
    load_versions,
    save_versions,
)


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from core.logger import logger


bp = Blueprint("system", __name__)

# Find .env file in project root (not webconfig directory)
ENV_PATH = find_dotenv(usecwd=True)
if not ENV_PATH or not os.path.exists(ENV_PATH):
    # Fallback: look for .env in project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ENV_PATH = os.path.join(project_root, ".env")
CONFIG_KEYS = [
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "BILLY_MODEL",
    "BILLY_PINS",
    "MIC_TIMEOUT_SECONDS",
    "SILENCE_THRESHOLD",
    "MQTT_HOST",
    "MQTT_PORT",
    "MQTT_USERNAME",
    "MQTT_PASSWORD",
    "HA_HOST",
    "HA_TOKEN",
    "HA_LANG",
    "MIC_PREFERENCE",
    "SPEAKER_PREFERENCE",
    "FLASK_PORT",
    "RUN_MODE",
    "SHOW_SUPPORT",
    "TURN_EAGERNESS",
    "FORCE_PASS_CHANGE",
    "MOUTH_ARTICULATION",
    "LOG_LEVEL",
    "DEFAULT_USER",
    "CURRENT_USER",
    "SHOW_RC_VERSIONS",
    "FLAP_ON_BOOT",
    "NEWS_REQUEST_TIMEOUT_SECONDS",
    "WAKE_WORD_ENABLED",
    "WAKE_WORD_SENSITIVITY",
    "WAKE_WORD_THRESHOLD",
    "WAKE_WORD_ENDPOINT",
    "WAKE_WORD_PORCUPINE_ACCESS_KEY",
]


def _normalize_source_payload(data: dict) -> dict:
    name = str(data.get("name") or "").strip()
    url = str(data.get("url") or "").strip()
    topics_raw = data.get("topics", [])

    if not name:
        raise ValueError("Source name is required")
    if not url:
        raise ValueError("Source URL is required")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("Source URL must start with http:// or https://")
    return {
        "name": name,
        "url": url,
        "topics": _normalize_topics(topics_raw),
    }


def _normalize_topics(raw_topics) -> list[str]:
    if isinstance(raw_topics, str):
        source = [part.strip().lower() for part in raw_topics.split(",")]
    elif isinstance(raw_topics, list):
        source = [str(part).strip().lower() for part in raw_topics]
    else:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for topic in source:
        if not topic or topic in seen:
            continue
        seen.add(topic)
        normalized.append(topic)
    return normalized


def _remove_path(path: Path, removed: list[str]) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    removed.append(str(path))


def _remove_env_and_versions() -> dict:
    removed: dict[str, bool] = {"env": False, "versions": False}
    errors: list[str] = []

    env_path = Path(ENV_PATH)
    example_path = Path(PROJECT_ROOT) / ".env.example"
    if env_path.exists():
        try:
            env_path.unlink()
        except Exception as exc:
            errors.append(f"Failed to delete .env: {exc}")
    try:
        if example_path.exists():
            shutil.copy(example_path, env_path)
        else:
            env_path.touch()
        removed["env"] = True
    except Exception as exc:
        errors.append(f"Failed to reset .env: {exc}")

    versions_path = Path(PROJECT_ROOT) / "versions.ini"
    if versions_path.exists():
        try:
            versions_path.unlink()
            removed["versions"] = True
        except Exception as exc:
            errors.append(f"Failed to delete versions.ini: {exc}")

    return {"removed": removed, "errors": errors}


def _remove_custom_profiles() -> dict:
    removed: list[str] = []
    errors: list[str] = []

    profiles_dir = Path(PROJECT_ROOT) / "profiles"
    if profiles_dir.exists():
        for profile_file in profiles_dir.glob("*.ini"):
            if (
                profile_file.name.lower() == "guest.ini"
                or profile_file.stem.lower() == "guest"
            ):
                continue
            try:
                _remove_path(profile_file, removed)
            except Exception as exc:
                errors.append(f"Failed to delete profile {profile_file}: {exc}")

    return {"removed": removed, "errors": errors}


def _remove_custom_personas() -> dict:
    removed: list[str] = []
    errors: list[str] = []

    default_persona = Path(PROJECT_ROOT) / "persona.ini"
    personas_dir = Path(PROJECT_ROOT) / "personas"
    if personas_dir.exists():
        for persona_file in personas_dir.glob("*.ini"):
            if persona_file.stem.lower() == "default":
                continue
            try:
                _remove_path(persona_file, removed)
            except Exception as exc:
                errors.append(f"Failed to delete persona file {persona_file}: {exc}")
        for persona_dir in personas_dir.iterdir():
            if not persona_dir.is_dir():
                continue
            if persona_dir.name.lower() == "default":
                continue
            try:
                _remove_path(persona_dir, removed)
            except Exception as exc:
                errors.append(f"Failed to delete persona folder {persona_dir}: {exc}")

    # Always keep the default persona.ini in the project root
    if default_persona.exists():
        pass

    return {"removed": removed, "errors": errors}


def _clear_service_logs() -> dict:
    errors: list[str] = []
    units = ["billy.service", "billy-webconfig.service"]
    for unit in units:
        for args in (
            ["sudo", "journalctl", "-u", unit, "--rotate"],
            ["sudo", "journalctl", "-u", unit, "--vacuum-time=1s"],
        ):
            try:
                result = subprocess.run(
                    args, check=False, capture_output=True, text=True
                )
                if result.returncode != 0:
                    stderr = result.stderr.strip() or result.stdout.strip()
                    errors.append(f"{unit}: {' '.join(args[1:])} failed: {stderr}")
            except FileNotFoundError:
                errors.append("journalctl not available")
                break
            except Exception as exc:
                errors.append(f"{unit}: {' '.join(args[1:])} failed: {exc}")

    # Clear CLI history for the user running this service.
    try:
        import pwd

        current_user = pwd.getpwuid(os.getuid())
        current_home = Path(current_user.pw_dir)
        for history_file in (
            current_home / ".bash_history",
            current_home / ".zsh_history",
        ):
            if history_file.exists():
                history_file.write_text("")
    except Exception as exc:
        errors.append(f"Failed to clear CLI history: {exc}")
    return {"errors": errors}


def _remove_active_wifi_connections() -> dict:
    removed: list[str] = []
    errors: list[str] = []
    try:
        logger.info(
            "[factory_reset] Checking active NetworkManager connections...", "📡"
        )
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            errors.append(f"nmcli list failed: {stderr}")
            logger.warning(f"[factory_reset] nmcli list failed: {stderr}")
            return {"removed": removed, "errors": errors}
        logger.info(f"[factory_reset] nmcli active output: {result.stdout.strip()}")
        for line in result.stdout.splitlines():
            parts = line.split(":")
            if len(parts) < 2:
                continue
            name, conn_type = parts[0], parts[1]
            if conn_type not in {"wifi", "802-11-wireless"} or not name:
                continue
            logger.info(f"[factory_reset] Deleting Wi-Fi connection: {name}")
            delete_result = subprocess.run(
                ["sudo", "nmcli", "connection", "delete", name],
                check=False,
                capture_output=True,
                text=True,
            )
            if delete_result.returncode != 0:
                stderr = delete_result.stderr.strip() or delete_result.stdout.strip()
                errors.append(f"Failed to delete Wi-Fi '{name}': {stderr}")
                logger.warning(
                    f"[factory_reset] Failed to delete Wi-Fi '{name}': {stderr}"
                )
                continue
            removed.append(name)
            logger.info(f"[factory_reset] Deleted Wi-Fi connection: {name}")
    except FileNotFoundError:
        errors.append("nmcli not available")
        logger.warning("[factory_reset] nmcli not available")
    except Exception as exc:
        errors.append(f"Wi-Fi removal failed: {exc}")
        logger.warning(f"[factory_reset] Wi-Fi removal failed: {exc}")
    return {"removed": removed, "errors": errors}


def _reset_git_worktree() -> dict:
    errors: list[str] = []
    details: dict[str, str] = {}
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            errors.append(f"git rev-parse failed: {stderr}")
            return {"errors": errors, "details": details}
        head = result.stdout.strip()
        details["head"] = head

        reset_result = subprocess.run(
            ["git", "reset", "--hard", head],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if reset_result.returncode != 0:
            stderr = reset_result.stderr.strip() or reset_result.stdout.strip()
            errors.append(f"git reset --hard failed: {stderr}")
    except FileNotFoundError:
        errors.append("git not available")
    except Exception as exc:
        errors.append(f"git reset failed: {exc}")

    return {"errors": errors, "details": details}


def delayed_restart():
    time.sleep(1.5)
    subprocess.run(["sudo", "systemctl", "restart", "billy-webconfig.service"])
    subprocess.run(["sudo", "systemctl", "restart", "billy.service"])


@bp.route("/")
def index():
    return render_template(
        "index.html",
        config={k: str(getattr(core_config, k, "")) for k in CONFIG_KEYS}
        | {
            "VOICE_OPTIONS": [
                "alloy",
                "ash",
                "ballad",
                "coral",
                "echo",
                "sage",
                "shimmer",
                "verse",
                "marin",
                "cedar",
            ],
        },
    )


@bp.route("/version")
def version_info():
    versions = load_versions()
    # Always check the current checked-out version from git
    current = get_current_version()
    latest = versions["version"].get("latest", "unknown")

    logger.verbose(
        f"[version_info] Detected current version: {current}, stored: {versions['version'].get('current', 'unknown')}, latest: {latest}"
    )

    # Update the stored current version if it's different
    stored_current = versions["version"].get("current", "unknown")
    if current != stored_current:
        logger.info(
            f"[version_info] Updating stored version from {stored_current} to {current}"
        )
        save_versions(current, latest)

    try:
        update_available = (
            current != "unknown"
            and latest != "unknown"
            and parse_version(latest.lstrip("v")) > parse_version(current.lstrip("v"))
        )
    except Exception as e:
        logger.warning(f"[version_info] Error checking update availability: {e}")
        update_available = False

    response = {
        "current": current,
        "latest": latest,
        "update_available": update_available,
    }
    logger.verbose(f"[version_info] Returning: {response}")
    return jsonify(response)


@bp.route("/update", methods=["POST"])
def perform_update():
    versions = load_versions()
    current = versions["version"].get("current", "unknown")
    latest = versions["version"].get("latest", "unknown")
    if current == latest or latest == "unknown":
        return jsonify({"status": "up-to-date", "version": current})
    try:
        subprocess.check_output(["git", "remote", "-v"], cwd=PROJECT_ROOT, text=True)
        subprocess.check_call(["git", "fetch", "--tags"], cwd=PROJECT_ROOT)
        subprocess.check_call(
            ["git", "checkout", "--force", f"tags/{latest}"], cwd=PROJECT_ROOT
        )
        venv_pip = os.path.join(PROJECT_ROOT, "venv", "bin", "pip")
        output = subprocess.check_output(
            [venv_pip, "install", "--upgrade", "-r", "requirements.txt"],
            cwd=PROJECT_ROOT,
            stderr=subprocess.STDOUT,
            text=True,
        )
        logger.info(f"📦 Pip install output:\n{output}")
        # Refresh current version from git after checkout to ensure accuracy
        actual_current = get_current_version()
        save_versions(actual_current, latest)
        threading.Thread(
            target=lambda: (
                time.sleep(2),
                subprocess.run([
                    "sudo",
                    "systemctl",
                    "restart",
                    "billy-webconfig.service",
                ]),
            )
        ).start()
        threading.Thread(
            target=lambda: (
                time.sleep(2),
                subprocess.run(["sudo", "systemctl", "restart", "billy.service"]),
            )
        ).start()
        return jsonify({"status": "updated", "version": latest})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@bp.route("/update-simulate", methods=["POST"])
def simulate_update():
    """Run update workflow against currently checked-out revision."""
    try:
        versions = load_versions()
        latest = versions["version"].get("latest", "unknown")

        # Keep current code version: reinstall deps for current checkout and restart services.
        current_ref = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
        ).strip()
        subprocess.check_call(
            ["git", "checkout", "--force", current_ref], cwd=PROJECT_ROOT
        )

        venv_pip = os.path.join(PROJECT_ROOT, "venv", "bin", "pip")
        output = subprocess.check_output(
            [venv_pip, "install", "--upgrade", "-r", "requirements.txt"],
            cwd=PROJECT_ROOT,
            stderr=subprocess.STDOUT,
            text=True,
        )
        logger.info(f"📦 Simulated update pip output:\n{output}")

        actual_current = get_current_version()
        save_versions(actual_current, latest)

        threading.Thread(
            target=lambda: (
                time.sleep(2),
                subprocess.run([
                    "sudo",
                    "systemctl",
                    "restart",
                    "billy-webconfig.service",
                ]),
            )
        ).start()
        threading.Thread(
            target=lambda: (
                time.sleep(2),
                subprocess.run(["sudo", "systemctl", "restart", "billy.service"]),
            )
        ).start()

        return jsonify({
            "status": "restarting",
            "message": "Simulated update complete. Restarting services...",
            "version": actual_current,
        })
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "error": str(e)}), 500
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@bp.route("/release-note")
def release_note():
    return jsonify(RELEASE_NOTE)


@bp.route("/save", methods=["POST"])
def save():
    data = request.json
    old_port = os.getenv("FLASK_PORT", "80")
    changed_port = False
    for key, value in data.items():
        if key in CONFIG_KEYS:
            set_key(ENV_PATH, key, value, quote_mode='never')
            if key == "FLASK_PORT" and str(value) != str(old_port):
                changed_port = True
    response = {"status": "ok"}
    if changed_port:
        response["port_changed"] = True
        threading.Thread(target=delayed_restart).start()
    return jsonify(response)


@bp.route("/config")
def get_config():
    # Reload .env file and core config to get latest values
    from dotenv import load_dotenv

    load_dotenv(ENV_PATH, override=True)

    # Reload core config module to pick up new .env values
    import importlib
    import sys

    if 'core.config' in sys.modules:
        importlib.reload(sys.modules['core.config'])

    # Re-import core_config to get fresh values
    from ..core_imports import core_config

    # Get basic configuration
    config_data = {k: str(getattr(core_config, k, "")) for k in CONFIG_KEYS}

    # Add voice options from the current provider
    try:
        current_provider = voice_provider_registry.get_provider()
        voices = current_provider.get_supported_voices()
    except Exception as e:
        logger.warning(f"[config] No realtime provider available: {e}")
        voices = []
    config_data["VOICE_OPTIONS"] = voices

    # Add user profile information
    try:
        from core.config import DEFAULT_USER
        from core.profile_manager import user_manager

        # Get current user from .env file (already reloaded above)
        current_user_name = (
            os.getenv("CURRENT_USER", "").strip().strip("'\"").lower()
        )  # Remove quotes, whitespace, and normalize to lowercase
        current_user = None

        # Update config_data with fresh CURRENT_USER value
        config_data["CURRENT_USER"] = current_user_name

        # If we have a current user in .env, try to load it
        if current_user_name and current_user_name.lower() != "guest":
            try:
                current_user = user_manager.identify_user(current_user_name, "high")
            except Exception as e:
                print(f"Failed to load current user {current_user_name}: {e}")

        # Only fall back to DEFAULT_USER if CURRENT_USER is completely empty (not set)
        # If CURRENT_USER is explicitly set to "guest", respect that choice
        if (
            not current_user
            and not current_user_name
            and DEFAULT_USER
            and DEFAULT_USER.lower() != "guest"
        ):
            try:
                current_user = user_manager.identify_user(DEFAULT_USER, "high")
                # Only update CURRENT_USER in .env if it was completely empty
                config_data["CURRENT_USER"] = DEFAULT_USER
            except Exception as e:
                print(f"Failed to load default user {DEFAULT_USER}: {e}")

        # Add user profile data
        if current_user:
            config_data["CURRENT_USER"] = {
                "name": current_user.name,
                "data": current_user.data,
                "memories": current_user.get_memories(10),
                "context": current_user.get_context_string(),
            }
        else:
            # If no user is loaded, preserve the CURRENT_USER value from .env
            # This could be "guest" or a user name that couldn't be loaded
            config_data["CURRENT_USER"] = (
                current_user_name if current_user_name else None
            )

        # Add available profiles with full data including preferred personas
        try:
            from core.profile_manager import UserProfile

            available_profiles = []
            for user_name in user_manager.list_all_users():
                try:
                    profile = UserProfile(user_name)
                    available_profiles.append({
                        "name": profile.name,
                        "data": profile.data,
                    })
                except Exception as e:
                    print(f"Failed to load profile {user_name}: {e}")
                    # Add basic info even if full profile can't be loaded
                    available_profiles.append({
                        "name": user_name,
                        "data": {"USER_INFO": {"preferred_persona": "default"}},
                    })
            config_data["AVAILABLE_PROFILES"] = available_profiles
        except Exception as e:
            print(f"Failed to load profile data: {e}")
            config_data["AVAILABLE_PROFILES"] = []

        # Add available personas and current persona
        try:
            from core.persona_manager import persona_manager

            config_data["AVAILABLE_PERSONAS"] = persona_manager.get_available_personas()
            config_data["CURRENT_PERSONA"] = persona_manager.current_persona
        except Exception as e:
            print(f"Failed to load personas: {e}")
            config_data["AVAILABLE_PERSONAS"] = []
            config_data["CURRENT_PERSONA"] = "default"

    except Exception as e:
        print(f"Failed to load user profile data: {e}")
        config_data["CURRENT_USER"] = None
        config_data["AVAILABLE_PROFILES"] = []
        config_data["AVAILABLE_PERSONAS"] = []

    return jsonify(config_data)


@bp.route("/profiles/current-user", methods=["PATCH"])
def update_current_user_profile():
    """Update the current user's profile settings."""
    try:
        from core.persona_manager import persona_manager
        from core.profile_manager import user_manager

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        current_user = user_manager.get_current_user()
        if not current_user:
            return jsonify({"error": "No current user"}), 400

        # Handle persona switching
        if data.get("action") == "switch_persona":
            new_persona = data.get("preferred_persona")
            if new_persona:
                # Update user's preferred persona
                current_user.data['USER_INFO']['preferred_persona'] = new_persona
                current_user._save_profile()

                # Switch persona manager to new persona
                persona_manager.switch_persona(new_persona)

                return jsonify({
                    "success": True,
                    "message": f"Switched to {new_persona} persona",
                })

        return jsonify({"error": "Invalid action"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/config/refresh", methods=["POST"])
def refresh_config():
    """Refresh core configuration modules to pick up new settings."""
    try:
        # Reload .env file first
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH, override=True)

        # Import and reload core modules that might have cached configuration
        import importlib
        import sys

        # Reload core modules that contain configuration
        modules_to_reload = [
            'core.config',
            'core.personality',
            'core.wakeup',
            'core.say',
            'core.audio',
        ]

        for module_name in modules_to_reload:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])

        # Also reload the core_imports to get fresh references
        if 'app.core_imports' in sys.modules:
            importlib.reload(sys.modules['app.core_imports'])

        return jsonify({"status": "ok", "message": "Configuration refreshed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/config/auto-refresh", methods=["POST"])
def auto_refresh_config():
    """Automatically refresh configuration when .env changes are detected."""
    try:
        # Reload .env file
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH, override=True)

        # Reload core config module
        import importlib
        import sys

        if 'core.config' in sys.modules:
            importlib.reload(sys.modules['core.config'])

        # Get updated configuration
        from ..core_imports import core_config

        # Return updated config data
        config_data = {k: str(getattr(core_config, k, "")) for k in CONFIG_KEYS}

        # Add user profile information
        try:
            from core.config import DEFAULT_USER
            from core.profile_manager import user_manager

            # Get current user from .env file (fresh read)
            current_user_name = os.getenv("CURRENT_USER", "").strip().strip("'\"")
            current_user = None

            # Update config_data with fresh CURRENT_USER value
            config_data["CURRENT_USER"] = current_user_name

            # If we have a current user in .env, try to load it
            if current_user_name and current_user_name.lower() != "guest":
                try:
                    current_user = user_manager.identify_user(current_user_name, "high")
                except Exception as e:
                    print(f"Failed to load current user {current_user_name}: {e}")

            # Only fall back to DEFAULT_USER if CURRENT_USER is completely empty
            if (
                not current_user
                and not current_user_name
                and DEFAULT_USER
                and DEFAULT_USER.lower() != "guest"
            ):
                try:
                    current_user = user_manager.identify_user(DEFAULT_USER, "high")
                    config_data["CURRENT_USER"] = DEFAULT_USER
                except Exception as e:
                    print(f"Failed to load default user {DEFAULT_USER}: {e}")

            # Add user profile data
            if current_user:
                config_data["CURRENT_USER"] = {
                    "name": current_user.name,
                    "data": current_user.data,
                    "memories": current_user.get_memories(10),
                    "context": current_user.get_context_string(),
                }
            else:
                config_data["CURRENT_USER"] = (
                    current_user_name if current_user_name else None
                )

            # Add available profiles with full data including preferred personas
            try:
                from core.profile_manager import UserProfile

                available_profiles = []
                for user_name in user_manager.list_all_users():
                    try:
                        profile = UserProfile(user_name)
                        available_profiles.append({
                            "name": profile.name,
                            "data": profile.data,
                        })
                    except Exception as e:
                        print(f"Failed to load profile {user_name}: {e}")
                        # Add basic info even if full profile can't be loaded
                        available_profiles.append({
                            "name": user_name,
                            "data": {"USER_INFO": {"preferred_persona": "default"}},
                        })
                config_data["AVAILABLE_PROFILES"] = available_profiles
            except Exception as e:
                print(f"Failed to load profile data: {e}")
                config_data["AVAILABLE_PROFILES"] = []

            # Add available personas
            try:
                from core.persona_manager import persona_manager

                config_data["AVAILABLE_PERSONAS"] = (
                    persona_manager.get_available_personas()
                )
            except Exception as e:
                print(f"Failed to load personas: {e}")
                config_data["AVAILABLE_PERSONAS"] = []

        except Exception as e:
            print(f"Failed to load user profile data: {e}")
            config_data["CURRENT_USER"] = None
            config_data["AVAILABLE_PROFILES"] = []
            config_data["AVAILABLE_PERSONAS"] = []

        return jsonify({
            "status": "ok",
            "message": "Configuration auto-refreshed",
            "config": config_data,
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@bp.route("/news/sources", methods=["GET"])
def get_news_sources():
    try:
        return jsonify({"sources": load_news_sources()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/news/sources", methods=["POST"])
def add_news_source():
    data = request.get_json(silent=True) or {}
    try:
        normalized = _normalize_source_payload(data)
        sources = load_news_sources()
        normalized["id"] = str(data.get("id") or f"src-{uuid.uuid4().hex[:10]}")
        if any(source.get("id") == normalized["id"] for source in sources):
            return jsonify({"error": "Source id already exists"}), 409
        sources.append(normalized)
        saved = save_news_sources(sources)
        return jsonify({"status": "ok", "sources": saved})
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/news/sources/<source_id>", methods=["PATCH"])
def update_news_source(source_id: str):
    data = request.get_json(silent=True) or {}
    try:
        sources = load_news_sources()
        source = next((src for src in sources if src.get("id") == source_id), None)
        if not source:
            return jsonify({"error": "Source not found"}), 404

        merged = dict(source)
        merged.update({
            "name": data.get("name", source.get("name")),
            "url": data.get("url", source.get("url")),
            "topics": data.get("topics", source.get("topics", [])),
        })
        normalized = _normalize_source_payload(merged)
        normalized["id"] = source_id

        updated_sources = [
            normalized if src.get("id") == source_id else src for src in sources
        ]
        saved = save_news_sources(updated_sources)
        return jsonify({"status": "ok", "sources": saved})
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/news/sources/<source_id>", methods=["DELETE"])
def delete_news_source(source_id: str):
    try:
        sources = load_news_sources()
        filtered = [source for source in sources if source.get("id") != source_id]
        if len(filtered) == len(sources):
            return jsonify({"error": "Source not found"}), 404
        saved = save_news_sources(filtered)
        return jsonify({"status": "ok", "sources": saved})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/get-env')
def get_env():
    try:
        with open('.env') as f:
            return f.read(), 200
    except Exception as e:
        return str(e), 500


@bp.route('/save-env', methods=['POST'])
def save_env():
    content = request.json.get('content', '')
    try:
        with open('.env', 'w') as f:
            f.write(content)
        return jsonify({"status": "ok", "message": ".env saved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/factory-reset", methods=["POST"])
def factory_reset():
    data = request.get_json(silent=True) or {}
    if not data.get("confirm"):
        return jsonify({"status": "error", "error": "Confirmation required"}), 400
    options = data.get("options") or {}
    env_enabled = options.get("env", True)
    profiles_enabled = options.get("profiles", True)
    personas_enabled = options.get("personas", True)
    logs_enabled = options.get("logs", True)
    wifi_enabled = options.get("wifi", True)
    git_enabled = options.get("git", True)
    reboot_enabled = options.get("reboot", True)

    env_results = (
        _remove_env_and_versions() if env_enabled else {"removed": {}, "errors": []}
    )
    profile_results = (
        _remove_custom_profiles() if profiles_enabled else {"removed": [], "errors": []}
    )
    persona_results = (
        _remove_custom_personas() if personas_enabled else {"removed": [], "errors": []}
    )
    log_results = _clear_service_logs() if logs_enabled else {"errors": []}
    git_results = (
        _reset_git_worktree() if git_enabled else {"errors": [], "details": {}}
    )
    wifi_results = (
        _remove_active_wifi_connections()
        if wifi_enabled
        else {"removed": [], "errors": []}
    )

    errors = (
        env_results.get("errors", [])
        + profile_results.get("errors", [])
        + persona_results.get("errors", [])
        + log_results.get("errors", [])
        + wifi_results.get("errors", [])
        + git_results.get("errors", [])
    )

    response = {
        "status": "ok" if not errors else "partial",
        "removed": {
            "env": env_results.get("removed", {}).get("env", False),
            "versions": env_results.get("removed", {}).get("versions", False),
            "profiles": profile_results.get("removed", []),
            "personas": persona_results.get("removed", []),
        },
        "logs_cleared": logs_enabled and not log_results.get("errors"),
        "wifi_removed": wifi_results.get("removed", []),
        "git_reset": git_enabled and not git_results.get("errors"),
        "git_details": git_results.get("details", {}),
        "requested": {
            "env": env_enabled,
            "profiles": profiles_enabled,
            "personas": personas_enabled,
            "logs": logs_enabled,
            "wifi": wifi_enabled,
            "git": git_enabled,
            "reboot": reboot_enabled,
        },
        "errors": errors,
    }
    logger.info(f"[factory_reset] Completed with status: {response['status']}")
    if reboot_enabled and response["status"] == "ok":
        try:
            threading.Thread(
                target=lambda: (
                    time.sleep(2),
                    subprocess.Popen(["sudo", "reboot"]),
                )
            ).start()
            response["rebooting"] = True
        except Exception as exc:
            response["rebooting"] = False
            response["errors"].append(f"Failed to reboot: {exc}")
    else:
        response["rebooting"] = False
        response["restarting_services"] = response["status"] == "ok"
    return jsonify(response)


@bp.route("/hostname", methods=["GET", "POST"])
def hostname():
    if request.method == "GET":
        return jsonify({"hostname": os.uname().nodename})
    if request.method == "POST":
        data = request.get_json()
        new_hostname = data.get("hostname", "").strip()
        if not new_hostname:
            return jsonify({"error": "Invalid hostname"}), 400
        try:
            subprocess.check_call(["sudo", "hostnamectl", "set-hostname", new_hostname])
            subprocess.run(["sudo", "systemctl", "restart", "avahi-daemon"])
            return jsonify({"status": "ok", "hostname": new_hostname})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Unsupported method"}), 405

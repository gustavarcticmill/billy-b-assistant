import os
import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, TYPE_CHECKING

import numpy as np
import sounddevice as sd
from scipy.signal import resample

from . import config

if TYPE_CHECKING:  # pragma: no cover - only for static analysis
    from . import audio as audio_module

try:  # Optional dependency, loaded when engine=openwakeword.
    from openwakeword.model import Model as OpenWakeWordModel

    _OWW_AVAILABLE = True
except Exception:  # noqa: BLE001 - handled gracefully in controller.
    OpenWakeWordModel = Any  # type: ignore[assignment]
    _OWW_AVAILABLE = False


WakeWordCallback = Callable[[dict], None]


@dataclass
class WakeWordEvent:
    timestamp: float
    kind: str
    level: float | None = None
    threshold: float | None = None
    message: str | None = None
    payload: dict | None = None


class WakeWordController:
    """Lightweight wake-word detector with amplitude-based fallback logic."""

    cooldown_seconds = 2.0

    def __init__(self, on_detect: WakeWordCallback | None = None):
        self._on_detect: WakeWordCallback | None = on_detect
        self.enabled = config.WAKE_WORD_ENABLED
        self.engine = config.WAKE_WORD_ENGINE
        self.sensitivity = self._clamp_sensitivity(config.WAKE_WORD_SENSITIVITY)
        self.threshold = max(config.WAKE_WORD_THRESHOLD, 0.0)
        self.endpoint = config.WAKE_WORD_ENDPOINT

        self._stream: sd.InputStream | None = None
        self._running = False
        self._lock = threading.RLock()
        self._session_active = False
        self._last_detection = 0.0
        self._trigger_streak = 0
        self._last_meter_emit = 0.0
        self._last_error: str | None = None
        self._event_queue: "queue.Queue[WakeWordEvent]" = queue.Queue(maxsize=256)
        self._input_samplerate = None
        self._detector_mode = "rms"
        self._oww_model: OpenWakeWordModel | None = None
        self._oww_required_rate = 16000
        self._oww_last_scores: dict[str, float] | None = None
        self._hardware_enabled = True

    def set_detection_callback(self, callback: WakeWordCallback | None) -> None:
        with self._lock:
            self._on_detect = callback

    def enable(self) -> None:
        with self._lock:
            self.enabled = True
            self._sync_stream_state()

    def disable(self) -> None:
        with self._lock:
            self.enabled = False
            self._sync_stream_state()

    def start(self) -> None:
        with self._lock:
            self._sync_stream_state()

    def stop(self) -> None:
        with self._lock:
            self._close_stream()

    def notify_session_state(self, active: bool) -> None:
        with self._lock:
            self._session_active = active
            self._sync_stream_state()

    def set_parameters(
        self,
        *,
        enabled: Optional[bool] = None,
        engine: Optional[str] = None,
        sensitivity: Optional[float] = None,
        threshold: Optional[float] = None,
        endpoint: Optional[str] = None,
    ) -> None:
        with self._lock:
            if enabled is not None:
                self.enabled = bool(enabled)
            restart_required = False

            if engine is not None and engine != self.engine:
                self.engine = engine
                restart_required = True
            if sensitivity is not None:
                self.sensitivity = self._clamp_sensitivity(float(sensitivity))
            if threshold is not None:
                self.threshold = max(float(threshold), 0.0)
            if endpoint is not None and endpoint != self.endpoint:
                self.endpoint = endpoint
                restart_required = True

            if restart_required and self._running:
                self._close_stream()
            self._sync_stream_state()

    def get_status(self) -> dict:
        with self._lock:
            return {
                "enabled": self.enabled,
                "running": self._running,
                "engine": self.engine,
                "sensitivity": self.sensitivity,
                "threshold": self.threshold,
                "endpoint": self.endpoint,
                "session_active": self._session_active,
                "last_error": self._last_error,
                "events_pending": self._event_queue.qsize(),
                "detector_mode": self._detector_mode,
                "oww_available": _OWW_AVAILABLE,
                "hardware_enabled": self._hardware_enabled,
            }

    def get_event_queue(self) -> "queue.Queue[WakeWordEvent]":
        return self._event_queue

    # === Internal helpers ===

    @staticmethod
    def _clamp_sensitivity(value: float) -> float:
        return min(max(value, 0.0), 1.0)

    def _sync_stream_state(self) -> None:
        should_run = self.enabled and self._hardware_enabled and not self._session_active
        if should_run and not self._running:
            self._open_stream()
        elif not should_run and self._running:
            self._close_stream()

    def _open_stream(self) -> None:
        try:
            audio_mod = self._get_audio_module()
            if audio_mod.MIC_DEVICE_INDEX is None:
                audio_mod.detect_devices(debug=config.DEBUG_MODE)

            channels = max(1, audio_mod.MIC_CHANNELS or 1)
            samplerate = audio_mod.MIC_RATE or 16000
            blocksize = audio_mod.CHUNK_SIZE or int(samplerate * config.CHUNK_MS / 1000)

            self._prepare_engine()

            self._stream = sd.InputStream(
                samplerate=samplerate,
                device=audio_mod.MIC_DEVICE_INDEX,
                channels=channels,
                dtype="int16",
                blocksize=blocksize,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._running = True
            self._input_samplerate = samplerate
            self._publish_event(
                "status",
                message="listener_started",
                payload={"samplerate": samplerate, "mode": self._detector_mode},
            )
        except Exception as exc:  # noqa: BLE001 we want to log and keep running
            self._last_error = str(exc)
            self.enabled = False
            self._running = False
            self._stream = None
            self._publish_event("error", message=str(exc))
            print(f"⚠️ Wake word listener failed to start: {exc}")

    def _close_stream(self) -> None:
        if self._stream is None:
            self._running = False
            return

        try:
            self._stream.stop()
            self._stream.close()
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ Wake word listener failed to close: {exc}")
        finally:
            self._stream = None
            self._running = False
            self._publish_event("status", message="listener_stopped")
            self._input_samplerate = None

    def _prepare_engine(self) -> None:
        self._oww_model = None
        self._detector_mode = "rms"
        self._oww_last_scores = None

        if self.engine.lower() != "openwakeword":
            return

        if not _OWW_AVAILABLE:
            raise RuntimeError(
                "openwakeword engine requested but the openwakeword package is not installed"
            )

        model_path = (self.endpoint or "").strip()
        if not model_path:
            raise RuntimeError(
                "WAKE_WORD_ENDPOINT must point to an OpenWakeWord model file when engine=openwakeword"
            )
        if not os.path.exists(model_path):
            raise RuntimeError(f"Wake-word model not found: {model_path}")

        self._ensure_oww_resources()

        kwargs = {}
        lower_path = model_path.lower()
        if lower_path.endswith(".onnx"):
            kwargs["inference_framework"] = "onnx"
        elif lower_path.endswith(".tflite"):
            kwargs["inference_framework"] = "tflite"

        try:
            self._oww_model = OpenWakeWordModel(wakeword_models=[model_path], **kwargs)
        except Exception as exc:  # noqa: BLE001 - surface error to caller
            raise RuntimeError(f"Failed to load OpenWakeWord model: {exc}") from exc

        # Discover sample rate if exposed, otherwise default to 16 kHz.
        if hasattr(self._oww_model, "sample_rate"):
            self._oww_required_rate = int(getattr(self._oww_model, "sample_rate"))
        else:
            self._oww_required_rate = 16000

        self._detector_mode = "openwakeword"
        self._publish_event(
            "status",
            message="openwakeword_model_loaded",
            payload={"model": model_path, "sample_rate": self._oww_required_rate},
        )

    def _frames_required(self) -> int:
        # Higher sensitivity means fewer consecutive frames required.
        return max(1, int(round(3 - self.sensitivity * 2)))

    def _audio_callback(self, indata, frames, time_info, status):  # noqa: ANN001
        if status:
            self._publish_event("stream_warning", message=str(status))

        if not self._running:
            return

        data = np.array(indata, dtype=np.float32)
        if data.ndim > 1:
            data = data.mean(axis=1)

        rms = float(np.sqrt(np.mean(np.square(data))))
        now = time.time()

        if np.isnan(rms) or np.isinf(rms):
            return

        if now - self._last_meter_emit > 0.25:
            if config.DEBUG_MODE:
                print(f"[wake-word] RMS={rms:.0f} threshold={self.threshold:.0f}")
            self._publish_event("meter", level=rms, threshold=self.threshold)
            self._last_meter_emit = now

        if self._detector_mode == "openwakeword" and self._oww_model is not None:
            self._process_openwakeword(now, data)
            return

        if rms >= self.threshold:
            self._trigger_streak += 1
        else:
            self._trigger_streak = 0

        if self._trigger_streak < self._frames_required():
            return

        if (now - self._last_detection) < self.cooldown_seconds:
            return

        self._trigger_streak = 0
        self._last_detection = now

        payload = {
            "engine": self.engine,
            "mode": self._detector_mode,
            "level": rms,
            "threshold": self.threshold,
        }
        self._publish_event(
            "detected",
            level=rms,
            threshold=self.threshold,
            payload=payload,
        )

        self._dispatch_detection(payload)

    def _process_openwakeword(self, timestamp: float, data: np.ndarray) -> None:
        if self._oww_model is None or self._input_samplerate is None:
            return

        chunk = data / 32768.0  # normalise to [-1, 1]

        if self._input_samplerate != self._oww_required_rate:
            target_len = int(len(chunk) * self._oww_required_rate / self._input_samplerate)
            if target_len <= 0:
                return
            chunk = resample(chunk, target_len)

        try:
            scores = self._oww_model.predict(chunk)
        except Exception as exc:  # noqa: BLE001
            self._publish_event("error", message=f"OpenWakeWord inference failed: {exc}")
            self._last_error = str(exc)
            return

        self._oww_last_scores = scores or {}

        if self._oww_last_scores:
            best_label, best_score = max(
                self._oww_last_scores.items(), key=lambda item: item[1]
            )
        else:
            best_label, best_score = None, 0.0

        if config.DEBUG_MODE:
            print(
                f"[wake-word] best_label={best_label} score={best_score:.3f} "
                f"sensitivity={self.sensitivity:.2f}"
            )

        self._publish_event(
            "scores",
            payload={
                "scores": self._oww_last_scores,
                "best_label": best_label,
                "best_score": best_score,
            },
        )

        if best_score < self.sensitivity:
            return

        if (timestamp - self._last_detection) < self.cooldown_seconds:
            return

        self._last_detection = timestamp
        payload = {
            "engine": self.engine,
            "mode": self._detector_mode,
            "label": best_label,
            "score": float(best_score),
            "scores": self._oww_last_scores,
        }
        self._publish_event("detected", payload=payload)
        self._dispatch_detection(payload)

    def _publish_event(
        self,
        kind: str,
        *,
        level: float | None = None,
        threshold: float | None = None,
        message: str | None = None,
        payload: dict | None = None,
    ) -> None:
        event = WakeWordEvent(
            timestamp=time.time(),
            kind=kind,
            level=level,
            threshold=threshold,
            message=message,
            payload=payload,
        )
        try:
            self._event_queue.put_nowait(event)
        except queue.Full:
            try:
                _ = self._event_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._event_queue.put_nowait(event)
            except queue.Full:
                # If it still fails, drop the event silently.
                pass

    def _dispatch_detection(self, payload: dict) -> None:
        callback = self._on_detect
        if callback is None:
            return

        threading.Thread(
            target=self._invoke_callback,
            args=(callback, payload),
            daemon=True,
        ).start()

    @staticmethod
    def _invoke_callback(callback: WakeWordCallback, payload: dict) -> None:
        try:
            callback(payload)
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ Wake word callback failed: {exc}")

    _audio_module = None

    @classmethod
    def _get_audio_module(cls):
        if cls._audio_module is None:
            from . import audio as audio_module

            cls._audio_module = audio_module
        return cls._audio_module

    def set_hardware_enabled(self, enabled: bool) -> None:
        with self._lock:
            enabled_flag = bool(enabled)
            if enabled_flag == self._hardware_enabled:
                return
            self._hardware_enabled = enabled_flag
            if not enabled_flag and self._running:
                self._close_stream()
            self._publish_event(
                "status",
                message="hardware_enabled" if enabled_flag else "hardware_disabled",
                payload={"hardware_enabled": enabled_flag},
            )

    @staticmethod
    def _ensure_oww_resources() -> None:
        from importlib import resources

        try:
            files = resources.files("openwakeword.resources.models")
            if not list(files.iterdir()):  # pylint: disable=unsupported-binary-operation
                raise FileNotFoundError
        except (FileNotFoundError, ModuleNotFoundError):
            try:
                from openwakeword.utils import download_models

                download_models()
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    "OpenWakeWord support files are missing. Download them once or set WAKE_WORD_ENDPOINT to a valid model."
                ) from exc


controller = WakeWordController()

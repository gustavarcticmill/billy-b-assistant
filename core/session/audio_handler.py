"""Audio handling for Billy session."""

import asyncio
import base64
import time
from typing import Any

from .. import audio
from ..config import CHUNK_MS, TEXT_ONLY_MODE
from ..logger import logger


class AudioHandler:
    """Handles audio input/output for the session."""

    def __init__(self, session):
        self.session = session
        self.audio_buffer = bytearray()

    def clear_buffer(self):
        """Clear the audio buffer."""
        self.audio_buffer.clear()

    def on_audio_delta(self, data: dict[str, Any]):
        """Handle incoming audio delta from assistant."""
        if TEXT_ONLY_MODE:
            return

        self.session.state.assistant_speaking = True
        self.session.state._turn_had_speech = True

        audio_b64 = data.get("audio") or data.get("delta")
        if not audio_b64:
            return

        # First audio frame of this turn: force mic gating until playback is done.
        if not self.audio_buffer and audio.playback_done_event.is_set():
            audio.playback_done_event.clear()

        audio_chunk = base64.b64decode(audio_b64)
        self.audio_buffer.extend(audio_chunk)
        self.session.last_activity[0] = time.time()
        audio.playback_queue.put(audio_chunk)

        if self.session.interrupt_event.is_set():
            logger.warning(
                "Assistant turn interrupted. Stopping response playback.", "⛔"
            )
            while not audio.playback_queue.empty():
                try:
                    audio.playback_queue.get_nowait()
                    audio.playback_queue.task_done()
                except Exception:
                    break
            self.session.session_active.clear()
            self.session.interrupt_event.clear()

    async def wait_for_playback_complete(self):
        """Wait for audio playback to complete."""
        if not TEXT_ONLY_MODE:
            await asyncio.to_thread(audio.playback_queue.join)
            await asyncio.sleep(0.3)

    def save_response_audio(self):
        """Save the response audio buffer to disk."""
        if len(self.audio_buffer) > 0:
            logger.verbose(
                f"Saving audio buffer ({len(self.audio_buffer)} bytes)", "💾"
            )
            audio.rotate_and_save_response_audio(self.audio_buffer)
        else:
            logger.warning("Audio buffer was empty, skipping save.")

    def signal_playback_done(self):
        """Signal that playback is complete."""
        audio.playback_done_event.set()

    @staticmethod
    def ensure_playback_worker():
        """Ensure the playback worker is started."""
        if not TEXT_ONLY_MODE:
            audio.ensure_playback_worker_started(CHUNK_MS)

    @staticmethod
    def stop_playback():
        """Stop audio playback immediately."""
        audio.stop_playback()

    @staticmethod
    async def enqueue_wav(path: str):
        """Enqueue a WAV file for playback."""
        await asyncio.to_thread(audio.enqueue_wav_to_playback, path)

    @staticmethod
    async def wait_for_playback_queue():
        """Wait for the playback queue to empty."""
        await asyncio.to_thread(audio.playback_queue.join)

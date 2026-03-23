import asyncio
import contextlib
import json
import socket
import time
from typing import Any

import websockets.exceptions

from . import audio
from .config import (
    DEBUG_MODE,
    DEBUG_MODE_INCLUDE_DELTA,
    FOLLOW_UP_RETRY_LIMIT,
    MIC_TIMEOUT_SECONDS,
    REALTIME_AI_PROVIDER,
    RUN_MODE,
    SERVER_VAD_PARAMS,
    SILENCE_THRESHOLD,
    TEXT_ONLY_MODE,
    TURN_EAGERNESS,
    is_conversation_state_enabled,
)
from .logger import logger
from .movements import stop_all_motors
from .persona_manager import persona_manager
from .profile_manager import user_manager
from .realtime_ai_provider import voice_provider_registry


def get_instructions_with_user_context():
    """Generate instructions with current user context and persona if available."""
    import os

    from dotenv import load_dotenv

    from .config import ENV_PATH
    from .session import InstructionContext, instruction_builder

    load_dotenv(ENV_PATH, override=True)
    current_user_env = os.getenv("CURRENT_USER", "").strip().strip("'\"")
    current_user = user_manager.get_current_user()

    if current_user_env and current_user_env.lower() == "guest":
        mode = "guest"
    elif current_user:
        mode = "user"
    else:
        mode = "guest"

    context = InstructionContext(
        mode=mode,
        persona_name=persona_manager.current_persona,
        user_profile=current_user,
    )

    return instruction_builder.build(context)


def get_tools_for_current_mode():
    """Get tools list based on current mode (guest vs user mode)."""
    import os

    from dotenv import load_dotenv

    from .config import ENV_PATH
    from .session import tool_manager

    load_dotenv(ENV_PATH, override=True)
    current_user_env = os.getenv("CURRENT_USER", "").strip().strip("'\"")

    logger.info(
        f"🔧 get_tools_for_current_mode: CURRENT_USER='{current_user_env}'", "🔧"
    )

    if current_user_env and current_user_env.lower() == "guest":
        mode = "guest"
    else:
        mode = "user"

    tools = tool_manager.get_tools(mode)

    # Add provider-specific tools
    provider_tools = voice_provider_registry.get_provider().get_provider_tools()
    tools.extend(provider_tools)

    return tools


class BillySession:
    def __init__(
        self,
        interrupt_event=None,
        *,
        conversation_provider=None,
        kickoff_text: str | None = None,
        kickoff_kind: str = "literal",
        kickoff_to_interactive: bool = False,
        autofollowup: str = "auto",
    ):
        self.realtime_ai_provider = (
            conversation_provider
            or voice_provider_registry.get_provider(REALTIME_AI_PROVIDER)
        )
        self.ws = None
        self.ws_lock: asyncio.Lock = asyncio.Lock()
        self.loop = None
        self.last_activity = [time.time()]
        self.session_active = asyncio.Event()
        self.interrupt_event = interrupt_event or asyncio.Event()

        # Track session initialization
        self.session_initialized = False
        self.run_mode = RUN_MODE
        self._stopping = False
        self._interaction_count_recorded = False

        # Kickoff (MQTT say)
        self.kickoff_text = (kickoff_text or "").strip() or None
        self.kickoff_kind = kickoff_kind
        self.kickoff_to_interactive = kickoff_to_interactive
        self.kickoff_first_turn_done = False

        # Follow-up
        self.autofollowup = autofollowup

        # Tool args buffer (for streamed args)
        self._tool_args_buffer: dict[str, str] = {}

        self._logged_user_transcript_item_ids: set[str] = set()

        # Initialize handlers
        from .session import (
            AudioHandler,
            ErrorHandler,
            FunctionHandler,
            MicManagerWrapper,
            PersonaHandler,
            SessionState,
            UserHandler,
        )

        self.function_handler = FunctionHandler(self)
        self.audio_handler = AudioHandler(self)
        self.state = SessionState(self)
        self.user_handler = UserHandler(self)
        self.persona_handler = PersonaHandler(self)
        self.mic_manager = MicManagerWrapper(self)
        self.error_handler = ErrorHandler(self)

    def is_assistant_turn(self) -> bool:
        return self.state.is_assistant_turn()

    def is_user_turn(self) -> bool:
        return self.state.is_user_turn()

    def _set_listening_state(self):
        self.state.set_listening_state()

    def _set_speaking_state(self):
        self.state.set_speaking_state()

    def _set_idle_state(self):
        self.state.set_idle_state()

    # ---- Websocket helpers ---------------------------------------------
    async def _ws_send_json(self, payload: dict[str, Any]):
        """Send a JSON payload over the session websocket with locking.

        This method is a small convenience to avoid repeating the lock and
        json.dumps boilerplate across the codebase.
        """
        lock_acquired = False
        try:
            await asyncio.wait_for(self.ws_lock.acquire(), timeout=2.0)
            lock_acquired = True
            if self.ws is not None:
                await self.realtime_ai_provider.send_message(self.ws, payload)
        except asyncio.TimeoutError:
            logger.warning(
                "Timed out acquiring ws_lock for send; dropping payload", "⚠️"
            )
        finally:
            if lock_acquired:
                self.ws_lock.release()

    async def _close_ws(self, timeout: float = 1.0):
        lock_acquired = False
        ws_to_close = None
        try:
            await asyncio.wait_for(self.ws_lock.acquire(), timeout=2.0)
            lock_acquired = True
            ws_to_close = self.ws
            if not ws_to_close:
                return
        except asyncio.TimeoutError:
            # Lock contention during shutdown should not wedge session teardown.
            ws_to_close = self.ws
            logger.warning(
                "Timed out acquiring ws_lock during close; forcing websocket close without lock",
                "⚠️",
            )

        if not ws_to_close:
            return

        try:
            await asyncio.wait_for(ws_to_close.close(), timeout=max(0.5, timeout))
        except asyncio.TimeoutError:
            # Close timeout is common during teardown races; detach quietly.
            logger.info("Websocket close timed out during shutdown; continuing.", "⏱️")
        except websockets.exceptions.ConnectionClosed:
            # Already closed by remote/local side.
            pass
        except Exception as e:
            logger.warning(f"Error closing websocket ({type(e).__name__}): {e!r}", "⚠️")
        finally:
            if self.ws is ws_to_close:
                self.ws = None
            if lock_acquired:
                self.ws_lock.release()

    # ---- Message type constants ----------------------------------------
    AUDIO_OUT_TYPES = {
        "response.output_audio",
        "response.output_audio.delta",
    }
    TRANSCRIPT_DELTA_TYPES = {
        "response.output_audio_transcript.delta",
        "response.audio_transcript.delta",
        "response.text.delta",
    }
    TRANSCRIPT_DONE_TYPES = {
        "response.output_audio_transcript.done",
        "response.audio_transcript.done",
        "response.text.done",
    }
    USER_TRANSCRIPT_TYPES = {
        "conversation.item.input_audio_transcription.completed",
    }

    # ---- Private handlers -----------------------------------------------
    def _on_response_created(self):
        self.state.on_response_created()
        # Clear any buffered audio on OpenAI's side to prevent echo
        asyncio.create_task(self._clear_input_audio_buffer())

    async def _clear_input_audio_buffer(self):
        """Clear OpenAI's input audio buffer to prevent echo."""
        try:
            await self._ws_send_json({"type": "input_audio_buffer.clear"})
            if DEBUG_MODE:
                logger.verbose("Cleared input audio buffer to prevent echo", "🧹")
        except Exception as e:
            logger.warning(f"Failed to clear audio buffer: {e}")

    def _on_input_speech_started(self):
        self.state.on_input_speech_started()

    def _on_conversation_item_done(self, data: dict[str, Any]):
        self.state.on_conversation_item_done(data)
        self._log_user_transcript_from_item(data)

    def _log_user_transcript_from_item(self, data: dict[str, Any]):
        """Log finalized user transcript when present in conversation.item.done."""
        item = data.get("item") or {}
        if item.get("role") != "user":
            return

        item_id = item.get("id")
        content = item.get("content") or []
        transcript_parts: list[str] = []
        for part in content:
            transcript = (part.get("transcript") or "").strip()
            if transcript:
                transcript_parts.append(transcript)

        transcript = " ".join(transcript_parts).strip()
        if not transcript:
            return
        if item_id and item_id in self._logged_user_transcript_item_ids:
            return

        logger.info(f"User said: {transcript!r}", "🗣️")
        if item_id:
            self._logged_user_transcript_item_ids.add(item_id)

    def _on_user_transcript_done(self, data: dict[str, Any]):
        """Handle direct user transcription completion events."""
        transcript = (data.get("transcript") or "").strip()
        item_id = data.get("item_id")
        if transcript:
            # Meaningful user reply received: clear follow-up retry counter.
            self.state.mark_user_turn_meaningful()
            if not item_id or item_id not in self._logged_user_transcript_item_ids:
                logger.info(f"User said: {transcript!r}", "🗣️")
            if item_id:
                self._logged_user_transcript_item_ids.add(item_id)
            return

        if DEBUG_MODE:
            logger.verbose(
                f"User transcription completed but empty (item_id={item_id!r})",
                "ℹ️",
            )

    def _on_transcript_done(self, data: dict[str, Any]):
        self.state.on_transcript_done(data)

    def _on_audio_out(self, data: dict[str, Any]):
        self.audio_handler.on_audio_delta(data)

    def _on_transcript_delta(self, t: str, data: dict[str, Any]):
        delta = data.get("delta", "")
        self.state.on_transcript_delta(t, delta)

    def _on_tool_args_delta(self, data: dict[str, Any]):
        name = data.get("name")
        if name:
            self._tool_args_buffer.setdefault(name, "")
            self._tool_args_buffer[name] += data.get("arguments", "")

    async def _on_tool_args_done(self, data: dict[str, Any]):
        name = data.get("name")
        raw_args = data.get("arguments")
        call_id = data.get("call_id")
        if not raw_args and name:
            raw_args = self._tool_args_buffer.pop(name, "{}")

        # Delegate to function handler
        await self.function_handler.handle(name, raw_args, call_id)

    async def _on_response_done(self, data: dict[str, Any]):
        if self.state._skip_post_response_once:
            response = data.get("response") or {}
            status_details = response.get("status_details") or {}
            cancelled_by_client = (
                status_details.get("type") == "cancelled"
                and status_details.get("reason") == "client_cancelled"
            )
            output_items = response.get("output") or []
            has_meaningful_output = bool(
                self.state._turn_had_speech
                or self.state._saw_follow_up_call
                or any(
                    (item.get("type") == "message" and (item.get("content") or []))
                    or item.get("type") == "function_call"
                    for item in output_items
                )
            )

            # Manual turn-handoff interrupts intentionally cancel the current response.
            # Even if partial transcript/audio exists, post-response follow-up logic
            # should be skipped because the mic was already reopened explicitly.
            if cancelled_by_client:
                self.state._skip_post_response_once = False
                self.state.allow_mic_input = True
                self.state.assistant_speaking = False
                self.last_activity[0] = time.time()
                logger.info(
                    "Skipping post-response handling for client-cancelled interrupt; mic handoff already active.",
                    "🔇",
                )
                return

            # We only skip post-response handling when the cancelled turn truly produced
            # no assistant output. If output exists, process it normally to avoid getting
            # stuck in a half-open "listening/retry" state.
            if not has_meaningful_output:
                self.state._skip_post_response_once = False
                self.state.allow_mic_input = True
                self.state.assistant_speaking = False
                self.last_activity[0] = time.time()
                logger.info(
                    "Skipping post-response handling for cancelled short/noise turn; staying in listening mode.",
                    "🔇",
                )
                return

            logger.info(
                "Skip flag was set, but assistant output was present; continuing normal post-response handling.",
                "🔄",
            )
            self.state._skip_post_response_once = False

        response = data.get("response") or {}
        status_details = response.get("status_details") or {}
        error = status_details.get("error")
        if error:
            error_type = (error.get("type") or error.get("code") or "error").lower()
            error_message = error.get("message", "Unknown error")
            logger.error(f"OpenAI API Error [{error_type}]: {error_message}")
            mapped_code = "noapikey" if "invalid_api_key" in error_type else "error"
            await self.error_handler.play_error_sound(mapped_code, error_message)
            return
        logger.success("Assistant response complete.", "✿")

        if not TEXT_ONLY_MODE:
            await self.audio_handler.wait_for_playback_complete()
            self.audio_handler.save_response_audio()
            self.audio_handler.clear_buffer()
            self.audio_handler.signal_playback_done()
            self.last_activity[0] = time.time()

        # Only mark assistant turn complete after local playback has finished.
        self.state.on_response_done()

        # Check if conversation_state was called - if not, log warning
        # (heuristic will be used in _post_response_handling)
        if (
            is_conversation_state_enabled()
            and not self.state._saw_follow_up_call
            and self.state._turn_had_speech
        ):
            logger.warning(
                "⚠️ conversation_state was NOT called by the model - using heuristic fallback"
            )
            if DEBUG_MODE:
                heuristic_result = self.state.wants_follow_up_heuristic()
                logger.verbose(
                    f"Using heuristic fallback: follow_up_expected={heuristic_result}",
                    "🔍",
                )

        # Kickoff follow-up switch
        if self.kickoff_text and not self.kickoff_first_turn_done:
            if self.state._turn_had_speech:
                self.kickoff_first_turn_done = True
                if self.kickoff_to_interactive:
                    print("🔁 Kickoff complete — switching to interactive mode.")
                    self.mic_manager.start()
                elif self.autofollowup == "auto":
                    asked_question = self.state.wants_follow_up_heuristic()
                    wants_follow_up = self.state.follow_up_expected or asked_question
                    if wants_follow_up:
                        print("🔁 Auto follow-up detected — opening mic.")
                        opened = await self.mic_manager.start_after_playback()
                        if not opened:
                            logger.error(
                                "Failed to reopen mic for kickoff follow-up. Ending session.",
                                "❌",
                            )
                            await self.stop_session()
                            return
                        self.last_activity[0] = time.time()
                    else:
                        print(
                            "🔁 Kickoff complete — no follow-up needed. Closing session."
                        )
                        await self.stop_session()
                        return
            else:
                if DEBUG_MODE:
                    logger.info(
                        "Kickoff turn ended with no speech (tool-only). Waiting for next turn.",
                        "ℹ️",
                    )

        if self.run_mode == "dory":
            logger.info("Dory mode active. Ending session after single response.", "🎣")
            await self.stop_session()
            return

        # Post-response handling: decide whether to reopen mic or end session
        await self._post_response_handling()

    async def _post_response_handling(self):
        """Handle post-response logic: reopen mic or end session."""
        last_user_turn_meaningful = self.state._last_user_turn_meaningful
        if self.state.full_response_text.strip():
            print(
                f"📝 Transcript completed: \"{self.state.full_response_text.strip()}\""
            )
        logger.verbose(f"Full response: {self.state.full_response_text.strip()}", "🧠")

        # If a new response was triggered (greeting, HA command, etc), skip post-response handling
        if self.state._triggered_new_response:
            logger.info("New response triggered, skipping post-response handling", "🔄")
            return

        if not self.session_active.is_set():
            print()  # Add newline to end the mic volume display line
            logger.info(
                "Session inactive after timeout or interruption. Not restarting.", "🚪"
            )
            self._set_idle_state()
            stop_all_motors()
            await self._close_ws()
            return

        # If the model produced no spoken output this turn (tool-only/empty turn),
        # keep listening and avoid follow-up heuristics/retry accounting.
        if not self.state._turn_had_speech:
            logger.info(
                "No assistant speech this turn; staying in listening mode.",
                "🔇",
            )
            self.state._saw_follow_up_call = False
            self.state.full_response_text = ""
            self.state._last_user_turn_meaningful = False
            self.last_activity[0] = time.time()
            opened = await self.mic_manager.start_after_playback()
            if not opened:
                logger.error(
                    "Failed to reopen mic after tool-only turn. Ending session.",
                    "❌",
                )
                self._set_idle_state()
                stop_all_motors()
                await self._close_ws()
            return

        # Determine if follow-up is expected
        asked_question = self.state.wants_follow_up_heuristic()

        # Always log follow-up decision for debugging
        logger.info(
            f"Follow-up decision | mode={self.autofollowup}"
            f" | tool_expects={self.state.follow_up_expected}"
            f" | qmark={asked_question}"
            f" | had_speech={self.state._turn_had_speech}"
            f" | saw_follow_up_call={self.state._saw_follow_up_call}",
            "🧪",
        )

        if self.autofollowup == "always":
            wants_follow_up = True
        elif self.autofollowup == "never":
            wants_follow_up = False
        else:
            # If conversation_state was called, trust it
            # Otherwise fall back to heuristic (question mark detection)
            if self.state._saw_follow_up_call:
                if last_user_turn_meaningful:
                    wants_follow_up = self.state.follow_up_expected
                else:
                    if (
                        self.state.follow_up_expected
                        and self.state.follow_up_retry_count < FOLLOW_UP_RETRY_LIMIT
                    ):
                        wants_follow_up = True
                        logger.info(
                            "conversation_state requested follow-up on low-confidence user turn; allowing one grace retry.",
                            "🔁",
                        )
                    else:
                        wants_follow_up = False
                    if self.state.follow_up_expected and not wants_follow_up:
                        logger.info(
                            "Ignoring conversation_state follow-up on empty/noisy user turn.",
                            "🔇",
                        )
            else:
                wants_follow_up = asked_question

        if is_conversation_state_enabled() and not self.state._saw_follow_up_call:
            logger.warning(
                "conversation_state not called this turn; using heuristic instead."
            )

        if wants_follow_up:
            # Retry budget is only for no-content/silence turns.
            if not last_user_turn_meaningful:
                if self.state.follow_up_retry_count >= FOLLOW_UP_RETRY_LIMIT:
                    logger.info(
                        f"Follow-up retry limit reached ({FOLLOW_UP_RETRY_LIMIT}). Ending session.",
                        "🛑",
                    )
                    self.state._saw_follow_up_call = False
                    self.state.follow_up_retry_count = 0
                    self.state._last_user_turn_meaningful = False
                    self._set_idle_state()
                    stop_all_motors()
                    await self._close_ws()
                    return

                self.state.increment_follow_up_retry()
                logger.info(
                    f"Follow-up expected after empty/noisy turn. Keeping session open "
                    f"(retry {self.state.follow_up_retry_count}/{FOLLOW_UP_RETRY_LIMIT}).",
                    "🔁",
                )
            else:
                self.state.follow_up_retry_count = 0
                logger.info(
                    "Follow-up expected after meaningful user input. Keeping session open.",
                    "🔁",
                )
            # Reset the flag after using it
            self.state._saw_follow_up_call = False
            self.state._last_user_turn_meaningful = False
            opened = await self.mic_manager.start_after_playback()
            if not opened:
                logger.error(
                    "Failed to reopen mic for follow-up window. Ending session.",
                    "❌",
                )
                self.state.follow_up_retry_count = 0
                self._set_idle_state()
                stop_all_motors()
                await self._close_ws()
                return
            self.state.full_response_text = ""
            self.last_activity[0] = time.time()
            return

        logger.info("No follow-up. Ending session.", "🛑")
        # Reset the flag after using it
        self.state._saw_follow_up_call = False
        self.state.follow_up_retry_count = 0
        self.state._last_user_turn_meaningful = False
        self._set_idle_state()
        stop_all_motors()
        await self._close_ws()

    # ---- Mic helpers -------------------------------------------------
    async def start(self):
        self.loop = asyncio.get_running_loop()
        logger.info("Session starting...", "⏱️")

        await self.persona_handler.reload_persona_from_profile()

        vad_params = SERVER_VAD_PARAMS[TURN_EAGERNESS]
        logger.info(f"🔧 VAD Parameters (eagerness={TURN_EAGERNESS}): {vad_params}")
        logger.info(
            f"🔧 Audio Config: SILENCE_THRESHOLD={SILENCE_THRESHOLD}, MIC_TIMEOUT_SECONDS={MIC_TIMEOUT_SECONDS}"
        )

        # Reset state
        self.audio_handler.clear_buffer()
        self.state.reset_for_new_session()
        self._logged_user_transcript_item_ids.clear()
        self.last_activity[0] = time.time()
        self.session_active.set()
        self._stopping = False
        self._interaction_count_recorded = False
        self._local_vad_active = False
        self._local_vad_hold_until = 0.0

        logger.info(
            f"🔧 Mic state check: allow_mic_input={self.state.allow_mic_input}, "
            f"session_active={self.session_active.is_set()}, "
            f"playback_done_event={'SET' if audio.playback_done_event.is_set() else 'CLEAR (waiting for wake-up)'}, "
            f"TEXT_ONLY_MODE={TEXT_ONLY_MODE}",
            "🔧",
        )

        async with self.ws_lock:
            if self.ws is None:
                try:
                    persona_voice = persona_manager.get_current_persona_voice()
                    logger.info(
                        f"Using persona '{persona_manager.current_persona}' voice '{persona_voice}' for session startup",
                        "🎭",
                    )
                    self.ws = await self.realtime_ai_provider.connect(
                        instructions=get_instructions_with_user_context(),
                        tools=get_tools_for_current_mode(),
                        server_vad_params=SERVER_VAD_PARAMS[TURN_EAGERNESS],
                        interrupt_response=False,
                        text_only_mode=TEXT_ONLY_MODE,
                        voice=persona_voice,
                    )

                    # Kickoff message (from MQTT say)
                    if self.kickoff_text:
                        if self.kickoff_kind == "prompt":
                            kickoff_payload = self.kickoff_text
                        elif self.kickoff_kind == "literal":
                            follow_up_clause = (
                                "After you finish speaking, call `conversation_state` once. "
                                "If the line is not a question and needs no reply, set expects_follow_up=false."
                                if is_conversation_state_enabled()
                                else "After you finish speaking, end naturally. Do not include internal tool-call text."
                            )
                            kickoff_payload = (
                                "Say the user's message **verbatim**, word for word, with no additions or reinterpretation.\n"
                                "Maintain personality, but do NOT rephrase or expand.\n\n"
                                f"Repeat this literal message sent via MQTT: {self.kickoff_text}"
                                "\n\n"
                                f"{follow_up_clause}"
                            )
                        else:
                            kickoff_payload = self.kickoff_text

                        await self.realtime_ai_provider.send_message(
                            self.ws,
                            {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [
                                        {"type": "input_text", "text": kickoff_payload}
                                    ],
                                },
                            },
                        )
                        await self.realtime_ai_provider.send_message(
                            self.ws, {"type": "response.create"}
                        )

                except websockets.exceptions.ConnectionClosedError as e:
                    reason = getattr(e, "reason", str(e))
                    if "invalid_api_key" in reason:
                        await self.error_handler.play_error_sound("noapikey", reason)
                    else:
                        await self.error_handler.play_error_sound("error", reason)
                    return

                except socket.gaierror:
                    await self.error_handler.play_error_sound(
                        "nowifi", "Network unreachable or DNS failed"
                    )
                    return

                except Exception as e:
                    await self.error_handler.play_error_sound("error", str(e))
                    return

        if not TEXT_ONLY_MODE:
            self.audio_handler.ensure_playback_worker()

        await self.run_stream()

    async def run_stream(self):
        if not TEXT_ONLY_MODE and not audio.playback_done_event.is_set():
            await asyncio.to_thread(audio.playback_done_event.wait)

        logger.info(
            "Mic stream active. Say something..."
            if not self.kickoff_text
            else "Announcing kickoff...",
            "🎙️" if not self.kickoff_text else "📣",
        )
        if self.kickoff_text:
            self._set_speaking_state()

        try:
            asyncio.create_task(self.user_handler.auto_identify_default_user())

            # Start mic immediately for normal interactive sessions.
            # Keep the session.updated fallback below in case startup races.
            if not self.kickoff_text:
                self.mic_manager.start()

            assert self.ws is not None
            async for message in self.ws:
                if not self.session_active.is_set():
                    print("🚪 Session marked as inactive, stopping stream loop.")
                    print()  # Add newline to end the mic volume display line
                    break
                data = json.loads(message)
                if DEBUG_MODE and (
                    DEBUG_MODE_INCLUDE_DELTA
                    or not (data.get("type") or "").endswith("delta")
                ):
                    logger.verbose(f"Raw message: {data}", "🔁")

                if data.get("type") in ("session.updated", "session_updated"):
                    self.session_initialized = True
                    # Fallback: start mic if it wasn't already started.
                    if not self.kickoff_text and not self.mic_manager.mic_running:
                        logger.info(
                            "🎵 Session initialized with VAD settings, starting mic",
                            "✅",
                        )
                        self.mic_manager.start()

                await self.handle_message(data)

        except Exception as e:
            logger.error(f"Error opening mic input: {e}")
            self.session_active.clear()

        finally:
            try:
                self.mic_manager.stop()
                logger.info("Mic stream closed.", "🎙️")
            except Exception as e:
                logger.warning(f"Error while stopping mic: {e}")

    async def handle_message(self, data):
        t = data.get("type") or ""

        if t == "response.created":
            if self.state.should_ignore_short_response():
                self.state._skip_post_response_once = True
                with contextlib.suppress(Exception):
                    await self._ws_send_json({"type": "response.cancel"})
                self.state.allow_mic_input = True
                self.state.assistant_speaking = False
                self.last_activity[0] = time.time()
                logger.info(
                    "Cancelled response triggered by short audio turn; staying in listening mode.",
                    "🔇",
                )
                return
            self._on_response_created()
            return
        if t == "input_audio_buffer.speech_started":
            self._on_input_speech_started()
            return
        if t == "input_audio_buffer.speech_stopped":
            return
        if t in self.TRANSCRIPT_DONE_TYPES:
            self._on_transcript_done(data)
            return
        if t in self.AUDIO_OUT_TYPES:
            self._on_audio_out(data)
            return
        if t == "input_audio_buffer.committed":
            self.state.on_audio_committed(self.state._pending_input_audio_chunks)
            return
        if t == "conversation.item.done":
            self._on_conversation_item_done(data)
            return
        if t in self.USER_TRANSCRIPT_TYPES:
            self._on_user_transcript_done(data)
            return
        if t in self.TRANSCRIPT_DELTA_TYPES and "delta" in data:
            self._on_transcript_delta(t, data)
            return
        if t == "response.function_call_arguments.delta":
            self._on_tool_args_delta(data)
            return
        if t == "response.function_call_arguments.done":
            await self._on_tool_args_done(data)
            return
        if t == "response.done":
            await self._on_response_done(data)
            return
        if t == "error":
            error: dict[str, Any] = data.get("error") or {}
            code = error.get("code", "error").lower()
            message = error.get("message", "Unknown error")
            if code == "response_cancel_not_active":
                logger.verbose(
                    "Ignoring non-fatal cancel race: no active response to cancel.",
                    "ℹ️",
                )
                return
            if code == "conversation_already_has_active_response":
                logger.verbose(
                    "Ignoring non-fatal race: response already in progress.",
                    "ℹ️",
                )
                return
            mapped_code = "noapikey" if "invalid_api_key" in code else "error"
            logger.error(f"API Error ({mapped_code}): {message}")
            await self.error_handler.play_error_sound(mapped_code, message)
            return
        # else: ignore unrecognized messages silently

    async def stop_session(self):
        if self._stopping:
            return
        self._stopping = True
        logger.info("Stopping session...", "🛑")

        # Increment interaction count for current user at end of session
        if not self._interaction_count_recorded:
            user_manager.increment_current_user_interaction_count()
            self._interaction_count_recorded = True

        self.session_active.clear()
        self.mic_manager.stop()
        await self._close_ws()

        # Give the message loop a moment to exit
        await asyncio.sleep(0.1)

    async def request_stop(self):
        logger.info("Stop requested via external signal.", "🛑")
        self.session_active.clear()

    async def interrupt_to_user_turn(self):
        """Interrupt the assistant response and hand control back to the user mic."""
        if not self.session_active.is_set():
            return

        logger.info("Interrupting assistant turn and reopening mic...", "🛑")
        self.interrupt_event.clear()
        audio.stop_playback()

        if self.state.response_active:
            # Ignore the trailing response.done from this cancelled assistant turn.
            self.state._skip_post_response_once = True
            with contextlib.suppress(Exception):
                await self._ws_send_json({"type": "response.cancel"})

        # Force user-turn gating open even if provider state is racing.
        self.state.response_active = False
        self.state.allow_mic_input = True
        self.state.assistant_speaking = False
        self.state._saw_follow_up_call = False
        self.last_activity[0] = time.time()
        opened = await self.mic_manager.start_after_playback(delay=0.2, retries=2)
        if not opened:
            logger.warning(
                "Mic reopen failed after startup race fallback; session may need restart.",
                "⚠️",
            )

from __future__ import annotations

import logging
import os
import re
from typing import Any

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentServer, AgentSession, TurnHandlingOptions, inference
from livekit.plugins import deepgram

from hr_voice_agent.access import Actor, Role
from hr_voice_agent.action_store import ActionStore
from hr_voice_agent.config import AgentConfig
from hr_voice_agent.fixtures import FixtureRepository
from hr_voice_agent.hrms_backend import HRMSBackend, HRMSBackendConfig
from hr_voice_agent.voice_agent import create_voice_agent


load_dotenv(".env.local")
load_dotenv("agent/.env.local")

config = AgentConfig.from_environment(os.environ)
# HRMS Core uses port 8081. LiveKit's production worker health server also
# defaults to 8081, so give the voice worker its own port to avoid a silent
# startup failure that leaves LiveKit with no available agent.
try:
    worker_port = int(os.environ.get("VOICE_WORKER_PORT", "8091"))
except ValueError:
    worker_port = 8091
server = AgentServer(port=worker_port)
logger = logging.getLogger("hr_voice_agent")


def build_turn_handling(
    direct_deepgram: bool = False, stt_provider: str = ""
) -> TurnHandlingOptions:
    if direct_deepgram or stt_provider in {"sarvam", "auto"}:
        # Provider STT emits final/end-of-speech events, so let it commit turns.
        # Running a second hosted turn detector can flush or interrupt the same
        # utterance prematurely. This also keeps the fallback inference path
        # on the same explicit STT turn policy as the direct providers.
        return TurnHandlingOptions(
            turn_detection="stt",
            endpointing={"min_delay": 0.5, "max_delay": 2.5},
            interruption={
                "enabled": True,
                "mode": "vad",
                "min_duration": 0.5,
                "min_words": 1,
                "resume_false_interruption": True,
                "false_interruption_timeout": 2.0,
            },
        )
    return TurnHandlingOptions(
        turn_detection=inference.TurnDetector(),
        endpointing={"min_delay": 0.8, "max_delay": 3.0},
        interruption={
            "enabled": True,
            "mode": "adaptive",
            "min_duration": 0.8,
            "min_words": 2,
            "resume_false_interruption": True,
            "false_interruption_timeout": 2.0,
        },
    )


def build_tts(config: AgentConfig):
    provider = config.tts_provider
    if provider == "sarvam":
        from livekit.plugins import sarvam

        class LanguageAwareSarvamTTS(sarvam.TTS):
            def synthesize(self, text: str, **kwargs):
                language = "kn-IN" if re.search(r"[\u0C80-\u0CFF]", text) else "en-IN"
                self.update_options(target_language_code=language)
                return super().synthesize(text, **kwargs)

        return LanguageAwareSarvamTTS(
            model=config.sarvam_tts_model,
            speaker=config.sarvam_tts_speaker,
            target_language_code="en-IN",
        )
    if provider == "google":
        # Import lazily so deployments that keep the default LiveKit/Deepgram
        # setup do not need Google credentials or the optional plugin installed.
        from livekit.plugins import google

        return google.TTS(
            language=config.google_tts_language,
            voice_name=config.google_tts_voice,
        )
    if provider not in {"auto", "deepgram", "inference", "sarvam"}:
        raise ValueError(f"Unsupported VOICE_TTS_PROVIDER: {provider}")
    if provider == "deepgram" or (provider == "auto" and config.direct_deepgram):
        if not config.deepgram_api_key:
            raise RuntimeError("Deepgram TTS requires DEEPGRAM_API_KEY.")
        return deepgram.TTS(
            model=config.deepgram_tts_model,
            api_key=config.deepgram_api_key,
        )
    return config.tts


def actor_from_participant(participant: Any) -> Actor:
    role_value = participant.attributes.get("hrms.role")
    user_id = participant.attributes.get("hrms.user_id")
    if user_id != participant.identity or role_value not in {"employee", "hr_admin"}:
        raise RuntimeError("Trusted HRMS participant attributes are missing or invalid.")
    return Actor(
        user_id=user_id,
        role=Role(role_value),
        tenant_id=participant.attributes.get("hrms.tenant_id", ""),
        display_name=participant.attributes.get("hrms.name", ""),
        session_cookie=participant.attributes.get("hrms.session_cookie", ""),
    )


@server.rtc_session(agent_name=config.agent_name)
async def hr_assistant(ctx: agents.JobContext) -> None:
    participant = await ctx.wait_for_participant()
    actor = actor_from_participant(participant)
    fixtures = FixtureRepository()
    backend = HRMSBackend(HRMSBackendConfig.from_environment())
    voice_agent = create_voice_agent(actor, fixtures, ActionStore(), backend=backend)

    if config.stt_provider == "sarvam":
        from livekit.plugins import sarvam

        stt = sarvam.STTRealtime(
            language="auto",
            mode=config.sarvam_stt_mode,
            stream_type="balanced",
        )
        logger.info("Using Sarvam adaptive STT (language=auto, mode=%s)", config.sarvam_stt_mode)
    elif config.direct_deepgram:
        stt = deepgram.STT(
            model=config.deepgram_stt_model,
            language=config.deepgram_stt_language,
            api_key=config.deepgram_api_key,
            interim_results=True,
            punctuate=True,
            smart_format=True,
            filler_words=True,
            endpointing_ms=300,
        )
        logger.info(
            "Using direct Deepgram STT (stt=%s, language=%s)",
            config.deepgram_stt_model,
            config.deepgram_stt_language,
        )
    else:
        stt = config.stt
        logger.warning(
            "DEEPGRAM_API_KEY is not configured; using LiveKit inference STT (stt=%s)",
            config.stt,
        )
    tts = build_tts(config)
    logger.info(
        "Using TTS provider=%s language=%s voice=%s",
        config.tts_provider,
        config.google_tts_language,
        config.google_tts_voice,
    )

    session = AgentSession(
        stt=stt,
        llm=config.llm,
        tts=tts,
        turn_handling=build_turn_handling(
            config.direct_deepgram, config.stt_provider
        ),
    )
    recovery_spoken = False

    @session.on("error")
    def on_pipeline_error(event: object) -> None:
        nonlocal recovery_spoken
        error = getattr(event, "error", None)
        source_name = type(getattr(event, "source", None)).__name__.casefold()
        logger.warning("Voice pipeline provider error (%s)", source_name or "unknown")
        if recovery_spoken or getattr(error, "recoverable", False) or "tts" in source_name:
            return
        recovery_spoken = True
        session.say(
            "I'm having trouble with the voice service right now. Please try again in a moment."
        )

    await session.start(room=ctx.room, agent=voice_agent)
    person = actor.display_name or (
        fixtures.employee(actor.user_id)["preferred_name"]
        if not actor.session_cookie
        else "there"
    )
    role_help = (
        "leave, payslips, tasks, and HR information"
        if actor.role is Role.EMPLOYEE
        else "the employee directory, pending leave requests, and HR operations"
    )
    await session.generate_reply(
        instructions=(
            f"Greet {person} by name. Say you can help with {role_help}, then ask "
            "what they need. Keep it to two short sentences."
        )
    )


if __name__ == "__main__":
    agents.cli.run_app(server)

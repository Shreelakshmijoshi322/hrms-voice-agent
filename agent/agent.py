from __future__ import annotations

import os
import logging

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentServer, AgentSession, TurnHandlingOptions, inference

from hr_voice_agent.config import AgentConfig
from hr_voice_agent.voice_agent import HRMSVoiceAgent


load_dotenv(".env.local")
load_dotenv("agent/.env.local")

config = AgentConfig.from_environment(os.environ)
server = AgentServer()
logger = logging.getLogger("hr_voice_agent")


@server.rtc_session(agent_name=config.agent_name)
async def hr_assistant(ctx: agents.JobContext) -> None:
    session = AgentSession(
        stt=config.stt,
        llm=config.llm,
        tts=config.tts,
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
        ),
    )
    recovery_spoken = False

    @session.on("error")
    def on_pipeline_error(event: object) -> None:
        nonlocal recovery_spoken
        error = getattr(event, "error", None)
        source_name = type(getattr(event, "source", None)).__name__.casefold()
        logger.warning("Voice pipeline provider error (%s)", source_name or "unknown")
        if (
            recovery_spoken
            or getattr(error, "recoverable", False)
            or "tts" in source_name
        ):
            return
        recovery_spoken = True
        session.say(
            "I'm having trouble with the voice service right now. Please try again in a moment."
        )

    await session.start(room=ctx.room, agent=HRMSVoiceAgent())
    await session.generate_reply(
        instructions=(
            "Greet Maya by name. Say you can help with leave, payslips, and HR "
            "policies, then ask what she needs. Keep it to two short sentences."
        )
    )


if __name__ == "__main__":
    agents.cli.run_app(server)

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentServer, AgentSession, TurnHandlingOptions, inference

from hr_voice_agent.access import Actor, Role
from hr_voice_agent.action_store import ActionStore
from hr_voice_agent.config import AgentConfig
from hr_voice_agent.fixtures import FixtureRepository
from hr_voice_agent.voice_agent import create_voice_agent


load_dotenv(".env.local")
load_dotenv("agent/.env.local")

config = AgentConfig.from_environment(os.environ)
server = AgentServer()
logger = logging.getLogger("hr_voice_agent")


def build_turn_handling() -> TurnHandlingOptions:
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


def actor_from_participant(participant: Any) -> Actor:
    role_value = participant.attributes.get("hrms.role")
    user_id = participant.attributes.get("hrms.user_id")
    if user_id != participant.identity or role_value not in {"employee", "hr_admin"}:
        raise RuntimeError("Trusted HRMS participant attributes are missing or invalid.")
    return Actor(user_id=user_id, role=Role(role_value))


@server.rtc_session(agent_name=config.agent_name)
async def hr_assistant(ctx: agents.JobContext) -> None:
    participant = await ctx.wait_for_participant()
    actor = actor_from_participant(participant)
    fixtures = FixtureRepository()
    voice_agent = create_voice_agent(actor, fixtures, ActionStore())
    session = AgentSession(
        stt=config.stt,
        llm=config.llm,
        tts=config.tts,
        turn_handling=build_turn_handling(),
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
    person = fixtures.employee(actor.user_id)["preferred_name"]
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

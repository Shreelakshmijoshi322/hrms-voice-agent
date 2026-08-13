from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class AgentConfig:
    stt: str
    llm: str
    tts: str
    agent_name: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> "AgentConfig":
        return cls(
            stt=environment.get("VOICE_STT_MODEL", "deepgram/nova-3:en"),
            llm=environment.get("VOICE_LLM_MODEL", "google/gemma-4-31b-it"),
            tts=environment.get("VOICE_TTS_MODEL", "inworld/inworld-tts-2:Ashley"),
            agent_name=environment.get("VOICE_AGENT_NAME", "hr-assistant"),
        )

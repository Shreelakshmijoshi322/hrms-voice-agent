from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class AgentConfig:
    stt: str
    llm: str
    tts: str
    agent_name: str
    deepgram_api_key: str
    direct_deepgram: bool
    deepgram_stt_model: str
    deepgram_stt_language: str
    deepgram_tts_model: str
    tts_provider: str
    google_tts_language: str
    google_tts_voice: str
    stt_provider: str
    sarvam_stt_mode: str
    sarvam_tts_model: str
    sarvam_tts_speaker: str

    @staticmethod
    def _as_bool(value: str | None, default: bool = False) -> bool:
        if value is None:
            return default
        return value.strip().casefold() not in {"0", "false", "no", "off"}

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> "AgentConfig":
        deepgram_api_key = environment.get("DEEPGRAM_API_KEY", "").strip()
        # Direct Deepgram is opt-in by an explicit key. This lets the worker
        # continue serving while a key is being provisioned, then switch over
        # automatically on its next restart.
        direct_deepgram = bool(deepgram_api_key) and cls._as_bool(
            environment.get("VOICE_DIRECT_DEEPGRAM"),
            default=True,
        )
        return cls(
            stt=environment.get("VOICE_STT_MODEL", "deepgram/nova-3:multi"),
            llm=environment.get("VOICE_LLM_MODEL", "google/gemma-4-31b-it"),
            tts=environment.get("VOICE_TTS_MODEL", "inworld/inworld-tts-2:Ashley"),
            agent_name=environment.get("VOICE_AGENT_NAME", "hr-assistant"),
            deepgram_api_key=deepgram_api_key,
            direct_deepgram=direct_deepgram,
            deepgram_stt_model=environment.get("DEEPGRAM_STT_MODEL", "nova-3"),
            deepgram_stt_language=environment.get("DEEPGRAM_STT_LANGUAGE", "multi"),
            deepgram_tts_model=environment.get(
                "DEEPGRAM_TTS_MODEL", "aura-2-andromeda-en"
            ),
            tts_provider=environment.get("VOICE_TTS_PROVIDER", "auto").strip().casefold(),
            google_tts_language=environment.get("GOOGLE_TTS_LANGUAGE", "kn-IN"),
            google_tts_voice=environment.get(
                "GOOGLE_TTS_VOICE", "kn-IN-Standard-A"
            ),
            stt_provider=environment.get("VOICE_STT_PROVIDER", "auto").strip().casefold(),
            sarvam_stt_mode=environment.get("SARVAM_STT_MODE", "codemix"),
            sarvam_tts_model=environment.get("SARVAM_TTS_MODEL", "bulbul:v3"),
            sarvam_tts_speaker=environment.get("SARVAM_TTS_SPEAKER", "shubh"),
        )

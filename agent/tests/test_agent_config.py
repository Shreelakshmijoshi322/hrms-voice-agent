import unittest

from hr_voice_agent.config import AgentConfig


class AgentConfigTests(unittest.TestCase):
    def test_uses_livekit_inference_defaults(self) -> None:
        config = AgentConfig.from_environment({})

        self.assertEqual(config.stt, "deepgram/nova-3:multi")
        self.assertEqual(config.llm, "google/gemma-4-31b-it")
        self.assertEqual(config.tts, "inworld/inworld-tts-2:Ashley")
        self.assertEqual(config.agent_name, "hr-assistant")
        self.assertEqual(config.tts_provider, "auto")
        self.assertEqual(config.google_tts_language, "kn-IN")
        self.assertEqual(config.google_tts_voice, "kn-IN-Standard-A")
        self.assertEqual(config.stt_provider, "auto")
        self.assertEqual(config.sarvam_stt_mode, "codemix")

    def test_accepts_model_overrides_without_domain_changes(self) -> None:
        config = AgentConfig.from_environment(
            {
                "VOICE_STT_MODEL": "deepgram/nova-3:multi",
                "VOICE_LLM_MODEL": "openai/gpt-5-mini",
                "VOICE_TTS_MODEL": "cartesia/sonic-3:voice-id",
                "VOICE_TTS_PROVIDER": "google",
                "GOOGLE_TTS_LANGUAGE": "kn-IN",
                "GOOGLE_TTS_VOICE": "kn-IN-Chirp3-HD-Aoede",
                "VOICE_STT_PROVIDER": "sarvam",
                "SARVAM_STT_MODE": "codemix",
            }
        )

        self.assertEqual(config.stt, "deepgram/nova-3:multi")
        self.assertEqual(config.llm, "openai/gpt-5-mini")
        self.assertEqual(config.tts, "cartesia/sonic-3:voice-id")
        self.assertEqual(config.tts_provider, "google")
        self.assertEqual(config.google_tts_language, "kn-IN")
        self.assertEqual(config.google_tts_voice, "kn-IN-Chirp3-HD-Aoede")
        self.assertEqual(config.stt_provider, "sarvam")
        self.assertEqual(config.sarvam_stt_mode, "codemix")


if __name__ == "__main__":
    unittest.main()

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

from hr_voice_agent.access import Role


def load_entrypoint():
    path = Path(__file__).parents[1] / "agent.py"
    spec = importlib.util.spec_from_file_location("hr_agent_entrypoint", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class AgentEntrypointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entrypoint = load_entrypoint()

    def test_turn_handling_waits_for_complete_phrases_and_filters_backchannels(self):
        options = self.entrypoint.build_turn_handling()

        self.assertEqual(options["endpointing"], {"min_delay": 0.8, "max_delay": 3.0})
        self.assertEqual(options["interruption"]["mode"], "adaptive")
        self.assertEqual(options["interruption"]["min_duration"], 0.8)
        self.assertEqual(options["interruption"]["min_words"], 2)
        self.assertTrue(options["interruption"]["resume_false_interruption"])
        self.assertEqual(options["interruption"]["false_interruption_timeout"], 2.0)

    def test_actor_comes_only_from_matching_trusted_participant_attributes(self):
        participant = SimpleNamespace(
            identity="EMP-1042",
            attributes={"hrms.user_id": "EMP-1042", "hrms.role": "employee"},
        )

        actor = self.entrypoint.actor_from_participant(participant)

        self.assertEqual(actor.user_id, "EMP-1042")
        self.assertIs(actor.role, Role.EMPLOYEE)

        participant.attributes["hrms.user_id"] = "HR-2001"
        with self.assertRaisesRegex(RuntimeError, "missing or invalid"):
            self.entrypoint.actor_from_participant(participant)


if __name__ == "__main__":
    unittest.main()

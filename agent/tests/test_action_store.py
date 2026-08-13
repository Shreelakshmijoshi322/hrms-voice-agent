import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hr_voice_agent.action_store import (
    ActionAuthorizationError,
    ActionStateError,
    ActionStore,
)


class ActionStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "demo.sqlite"
        self.now = datetime(2026, 8, 13, tzinfo=timezone.utc)
        self.store = ActionStore(self.path, now=lambda: self.now)

    def test_leave_request_is_visible_to_another_store_instance(self):
        created = self.store.create_leave_request(
            "EMP-1042", "2026-08-14", "2026-08-20", "vacation", 7
        )

        second = ActionStore(self.path)

        self.assertEqual(
            second.list_leave_requests(status="pending_hr")[0].id,
            created.id,
        )

    def test_confirmation_is_actor_scoped_single_use_and_writes_profile(self):
        pending = self.store.prepare_action(
            actor_id="EMP-1042",
            action_type="profile_update",
            payload={"field": "preferred_name", "value": "Maya Joshi"},
            prompt="Confirm name update?",
        )
        with self.assertRaises(ActionAuthorizationError):
            self.store.confirm_action(pending.id, actor_id="HR-2001")

        self.store.execute_action(pending.id, actor_id="EMP-1042")

        self.assertEqual(
            self.store.get_profile_overrides("EMP-1042")["preferred_name"],
            "Maya Joshi",
        )
        with self.assertRaises(ActionStateError):
            self.store.execute_action(pending.id, actor_id="EMP-1042")

    def test_expired_confirmation_cannot_execute(self):
        pending = self.store.prepare_action(
            actor_id="EMP-1042",
            action_type="profile_update",
            payload={"field": "phone", "value": "+91 90000 09999"},
            prompt="Confirm phone update?",
        )
        expired_store = ActionStore(
            self.path,
            now=lambda: self.now + timedelta(minutes=6),
        )

        with self.assertRaisesRegex(ActionStateError, "expired"):
            expired_store.execute_action(pending.id, actor_id="EMP-1042")


if __name__ == "__main__":
    unittest.main()

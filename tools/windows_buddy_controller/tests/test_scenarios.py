import unittest

from windows_buddy_controller.scenarios import ScenarioController


class ScenarioTests(unittest.TestCase):
    def test_manual_approval_and_clear_prompt(self):
        controller = ScenarioController()
        controller.set_approval("req_1", "Bash", "git push")
        heartbeat = controller.heartbeat()
        self.assertEqual(heartbeat["waiting"], 1)
        self.assertEqual(heartbeat["prompt"]["id"], "req_1")

        controller.clear_prompt()
        heartbeat = controller.heartbeat()
        self.assertEqual(heartbeat["waiting"], 0)
        self.assertNotIn("prompt", heartbeat)

    def test_card_can_allow_manual_approval_and_trigger_completion(self):
        controller = ScenarioController()
        controller.set_approval("req_1", "Bash", "git push")

        self.assertFalse(controller.resolve_approval("wrong", "once"))
        self.assertTrue(controller.resolve_approval("req_1", "once"))
        heartbeat = controller.heartbeat()
        self.assertEqual(heartbeat["waiting"], 0)
        self.assertEqual(heartbeat["running"], 0)
        self.assertEqual(heartbeat["message"], "审批已允许 · Codex 任务已完成")
        self.assertEqual(heartbeat["tokens"], 50000)

    def test_card_can_deny_manual_approval(self):
        controller = ScenarioController()
        controller.set_approval("req_1", "Bash", "git push")

        self.assertTrue(controller.resolve_approval("req_1", "deny"))
        heartbeat = controller.heartbeat()
        self.assertEqual(heartbeat["waiting"], 0)
        self.assertEqual(heartbeat["message"], "审批已拒绝")

    def test_fresh_manual_approval_ids_are_unique_and_bounded(self):
        controller = ScenarioController()
        first = controller.set_fresh_approval("Bash", "git status")
        second = controller.set_fresh_approval("Bash", "git status")

        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("manual_"))
        self.assertLess(len(first.encode("utf-8")), 64)
        self.assertEqual(controller.heartbeat()["prompt"]["id"], second)

    def test_auto_cycle_has_expected_sequence(self):
        controller = ScenarioController()
        names = [controller.advance_auto().name for _ in range(5)]
        self.assertEqual(names, ["空闲", "工作中", "待确认", "已完成", "休眠"])
        self.assertEqual(controller.heartbeat()["total"], 0)

    def test_codex_completion_uses_message_and_triggers_celebration_score(self):
        controller = ScenarioController()
        controller.set_completed("测试全部通过")
        heartbeat = controller.heartbeat()
        self.assertEqual(heartbeat["message"], "测试全部通过")
        self.assertEqual(heartbeat["tokens"], 50000)


if __name__ == "__main__":
    unittest.main()

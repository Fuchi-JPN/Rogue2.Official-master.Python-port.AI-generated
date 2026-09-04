"""Actuator変換・禁止キー検証の単体テスト（設計書 §4）"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai.schemas import AIAction
from ai import actuator


class TestActuator(unittest.TestCase):
    def test_move(self):
        self.assertEqual(actuator.action_to_keys(AIAction(type="move", direction="l")), ["l"])

    def test_run(self):
        # 高速移動は大文字キー（typed actionのみ許可）
        self.assertEqual(actuator.action_to_keys(AIAction(type="run", direction="l")), ["L"])
        self.assertEqual(actuator.action_to_keys(AIAction(type="move", raw_keys="L")), [])

    def test_fight_keys(self):
        # fightは'f'+方向（方向入力待ちへの対応）
        self.assertEqual(actuator.action_to_keys(AIAction(type="fight", direction="h")), ["f", "h"])

    def test_item_action(self):
        self.assertEqual(actuator.action_to_keys(AIAction(type="quaff", item_slot="b")), ["q", "b"])

    def test_noop(self):
        self.assertEqual(actuator.action_to_keys(AIAction(type="noop")), [])

    def test_forbidden_raw(self):
        # Q/S/F/大文字移動/X（強制終了専用）は拒否
        for raw in ("Q", "S", "F", "H", "!", "o", "a", "X"):
            self.assertEqual(actuator.action_to_keys(AIAction(type="move", raw_keys=raw)), [],
                             msg=raw)

    def test_invalid_direction(self):
        self.assertEqual(actuator.action_to_keys(AIAction(type="move", direction="x")), [])

    def test_unknown_type(self):
        self.assertEqual(actuator.action_to_keys(AIAction(type="dance")), [])


if __name__ == "__main__":
    unittest.main()

"""Observer・ドライバ・リプレイの単体テスト（設計書 §3 §9）"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import const
import entities
import dungeon as dungeon_mod
import level_generator as level_gen
import utils
from ai import observer
from ai.schemas import AIOptions
from ai.session_log import load_replay_keys
from ai import input_hook


class TestObserver(unittest.TestCase):
    def _level(self):
        utils.set_random_seed(1)
        dung = dungeon_mod.DungeonLevel(level=1)
        level_gen.LevelGenerator(dung).make_level()
        return dung

    def test_build_observation(self):
        dung = self._level()
        p = entities.Player()
        p.row, p.col = 10, 10
        p.hp_current = 12
        p.hp_max = 12
        obs = observer.build_observation(p, dung, turn=3)
        self.assertEqual(obs.turn, 3)
        self.assertEqual(obs.player_pos, (10, 10))
        self.assertTrue(len(obs.local_view) > 0)
        self.assertIsNotNone(obs.status)

    def test_stairs_found(self):
        dung = self._level()
        p = entities.Player()
        p.row, p.col = 10, 10
        obs = observer.build_observation(p, dung)
        # 生成レベルには階段タイルが存在するはず（%探索）
        found = any(dung.get_tile(r, c) & const.STAIRS
                    for r in range(const.MIN_ROW, const.ROGUE_LINES - 1)
                    for c in range(const.ROGUE_COLUMNS))
        if found:
            self.assertIsNotNone(obs.stairs_pos)

    def test_input_hook_queue(self):
        input_hook.clear()
        input_hook.push_keys("qb")
        self.assertEqual(input_hook.pop_key(), "q")
        self.assertEqual(input_hook.hook_getchar_str(), "b")
        self.assertIsNone(input_hook.pop_key())
        input_hook.clear()


class TestDriver(unittest.TestCase):
    def test_intervention_keys(self):
        from ai.driver import AIDriver, ForceQuit
        game = type("G", (), {"display": None, "message": None})()
        d = AIDriver(game, AIOptions(enabled=True, log_file=""))
        # Qはパススルー
        self.assertEqual(d._handle_human("Q"), "Q")
        # Xは強制終了（手動モード中も有効）
        with self.assertRaises(ForceQuit):
            d._handle_human("X")
        # spaceで停止（新規ドライバで）
        d2 = AIDriver(game, AIOptions(enabled=True, log_file=""))
        self.assertIsNone(d2._handle_human(" "))
        self.assertTrue(d2.paused)
        # sで単歩
        self.assertIsNone(d2._handle_human("s"))
        self.assertTrue(d2.step_once)
        # mで手動
        d2.paused = False
        self.assertIsNone(d2._handle_human("m"))
        self.assertTrue(d2.manual)
        # 手動中は素通し
        self.assertEqual(d2._handle_human("h"), "h")
        # qで終了
        d2.manual = False
        self.assertIsNone(d2._handle_human("q"))
        self.assertFalse(d2.active)

    def test_force_quit_flag(self):
        from ai import input_hook
        input_hook.clear()
        self.assertFalse(input_hook.consume_force_quit())
        input_hook.request_force_quit()
        self.assertTrue(input_hook.consume_force_quit())
        self.assertFalse(input_hook.consume_force_quit())

    def test_replay_loading(self):
        import json
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            f.write(json.dumps({"keys": ["h", "j"]}) + "\n")
            f.write(json.dumps({"keys": "l"}) + "\n")
            path = f.name
        try:
            self.assertEqual(load_replay_keys(path), ["h", "j", "l"])
        finally:
            os.unlink(path)

    def test_headless_smoke(self):
        from ai.driver import run_headless_smoke
        res = run_headless_smoke(seed=1, turns=60, log_file="")
        self.assertGreaterEqual(res["turns"], 1)
        self.assertIn("hp", res)

    def test_followup_queue_first(self):
        # 追加入力待ちの後続キーは新規判断より優先される
        from ai.driver import AIDriver
        from ai.schemas import AIOptions
        from ai import input_hook
        game = type("G", (), {"display": None, "message": None})()
        d = AIDriver(game, AIOptions(enabled=True, log_file="", trace_file="",
                                     provider="scripted"))
        d.start()
        try:
            input_hook.push_keys("h")
            got = d.next_key(lambda: None)
            self.assertEqual(got, "h")
        finally:
            d.stop()

    def test_auto_ack_flag(self):
        from ai.driver import AIDriver
        from ai.schemas import AIOptions
        from ai import input_hook
        game = type("G", (), {"display": None, "message": None})()
        d = AIDriver(game, AIOptions(enabled=True, log_file="", trace_file="",
                                     provider="scripted"))
        d.start()
        try:
            self.assertTrue(input_hook.auto_ack_enabled())
        finally:
            d.stop()
        self.assertFalse(input_hook.auto_ack_enabled())

    def test_wait_for_ack_auto(self):
        # 全自動中は確認待ちがgetchを呼ばずに抜ける
        from ai import input_hook
        from display import Message
        input_hook.set_auto_ack(True)
        try:
            class FakeDisplay:
                def getch(self):
                    raise AssertionError("must not block")
            m = Message(FakeDisplay())
            m._wait_for_ack()
        finally:
            input_hook.set_auto_ack(False)

    def test_guard_illegal_move(self):
        import const as _const
        from ai.driver import AIDriver
        from ai.schemas import AIOptions, AIAction, AIObservation
        game = type("G", (), {"display": None, "message": None})()
        d = AIDriver(game, AIOptions(enabled=True, log_file="", trace_file=""))
        obs = AIObservation()
        obs.player_pos = (10, 10)
        cache = {}
        for r in range(_const.MIN_ROW, _const.ROGUE_LINES - 1):
            for c in range(_const.ROGUE_COLUMNS):
                cache[(r, c)] = _const.VERTWALL
        cache[(10, 9)] = _const.FLOOR  # hのみ開通
        obs._tile_cache = cache
        wall = AIAction(type="move", direction="l")
        fixed = d._guard_illegal_move(obs, wall)
        self.assertIsNotNone(fixed)
        self.assertNotEqual(fixed[0].direction, "l")
        ok = AIAction(type="move", direction="h")
        self.assertIsNone(d._guard_illegal_move(obs, ok))

    def test_trace_write(self):
        import json
        import tempfile
        from ai.driver import AIDriver
        from ai.schemas import AIOptions, AIObservation
        game = type("G", (), {"display": None, "message": None})()
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
            path = f.name
        try:
            d = AIDriver(game, AIOptions(enabled=True, log_file="", trace_file=path,
                                           provider="scripted"))
            d.start()
            obs = AIObservation()
            obs.player_pos = (10, 10)
            d._write_trace(obs, 5)
            d.stop()
            lines = open(path, encoding="utf-8").read().strip().split("\n")
            rec = json.loads(lines[0])
            self.assertIn("turn", rec)
        finally:
            os.unlink(path)


class TestTicker(unittest.TestCase):
    def test_frame_scrolls(self):
        from ai import monitor
        f0 = monitor.ticker_frame("abcdefghij", 4, 0)
        f1 = monitor.ticker_frame("abcdefghij", 4, 1)
        self.assertEqual(f0, "abcd")
        self.assertNotEqual(f0, f1)
        self.assertEqual(monitor.ticker_frame("", 4, 9), "")

    def test_width_aware(self):
        from ai import monitor
        self.assertEqual(monitor.disp_width("あいう"), 6)
        self.assertEqual(monitor.disp_width("ab"), 2)
        # 全角混じりで79桁に収まること（折り返し防止）
        s = monitor.format_overlay("llm", "m", 16, 120, "ＨＰ満タン、敵なし、階段へ移動", 12, 12, 2, 0)
        self.assertLessEqual(monitor.disp_width(s), 79)

    def test_no_extra_row(self):
        from ai import monitor
        game = type("G", (), {"display": None, "stdscr": None})()
        self.assertIsNone(monitor.ticker_row(game))


if __name__ == "__main__":
    unittest.main()

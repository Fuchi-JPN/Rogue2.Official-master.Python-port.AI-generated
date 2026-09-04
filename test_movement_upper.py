"""高速移動（大文字キー）本体対応の回帰テスト。

C版準拠：小文字=1歩、大文字=ぶつかるまで連続移動。
is_directionが大文字を弾くと「そのコマンドは不明です」になる。
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import const
import entities
import dungeon as dungeon_mod
import level_generator as level_gen
import utils
from actions import Movement


class TestRunCommand(unittest.TestCase):
    def test_is_direction_both_cases(self):
        m = Movement(entities.Player(), dungeon_mod.DungeonLevel(level=1), None, None, None)
        for ch in "hjklbyun":
            self.assertTrue(m.is_direction(ch), ch)
            self.assertTrue(m.is_direction(ch.upper()), ch.upper())

    def test_uppercase_run_terminates(self):
        utils.set_random_seed(1)
        dung = dungeon_mod.DungeonLevel(level=1)
        level_gen.LevelGenerator(dung).make_level()
        p = entities.Player()
        p.row, p.col = 10, 10
        p.hp_current = 12
        p.hp_max = 12
        start = (p.row, p.col)
        m = Movement(p, dung, None, None, None)
        m.multiple_move_rogue("L")  # ハングせず復帰すること
        self.assertNotEqual((p.row, p.col), start)

    def test_gr_row_col_terminates(self):
        # NO_ROOM(-1)ビット検査の混入による無限ループの再発防止
        import const as _const
        from combat import MonsterAI
        utils.set_random_seed(1)
        dung = dungeon_mod.DungeonLevel(level=1)
        level_gen.LevelGenerator(dung).make_level()
        p = entities.Player()
        p.row, p.col = 10, 10
        mai = MonsterAI(p, dung)
        row, col = mai._gr_row_col(_const.FLOOR | _const.TUNNEL | _const.STAIRS | _const.OBJECT)
        self.assertTrue(dung.dungeon[row][col] & (_const.FLOOR | _const.TUNNEL | _const.STAIRS | _const.OBJECT))
        mai.put_mons()  # ハングせず復帰すること
        self.assertGreater(len(dung.monsters), 0)


if __name__ == "__main__":
    unittest.main()

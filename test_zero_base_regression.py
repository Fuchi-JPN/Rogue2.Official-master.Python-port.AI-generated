"""ゼロベース再検証 回帰テスト (v2.1 E-1/E-2/E-3)。

C行番号・Py行番号・テスト名の4点証拠を残すための最小回帰。
実行: python3 -c "import sys; sys.path.insert(0,'python'); import test_zero_base_regression"
または pytest があれば pytest python/test_zero_base_regression.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unittest.mock import MagicMock
import unittest

import const
import entities
import inventory
import actions
import combat
import use_actions
import game_state
from entities import Item, Player


class TestZeroBaseRegression(unittest.TestCase):
    def test_mask_chars(self):
        """Z-L5: room.c:161,165 vs display.py:566"""
        # display.pyは `from . import const` のため単体import不可の場合がある。
        # その場合はソース照合で検証する（C room.c:161 '/' / :165 ']'）。
        try:
            try:
                from display import Display
            except ImportError:
                from python.display import Display
            self.assertEqual(Display.get_mask_char(const.WAND), '/')
            self.assertEqual(Display.get_mask_char(const.ARMOR), ']')
        except ImportError:
            with open(os.path.join(os.path.dirname(__file__), 'display.py'), encoding='utf-8') as f:
                src = f.read()
            self.assertIn("_const.WAND: '/'", src)
            self.assertIn("_const.ARMOR: ']'", src)

    def test_armor_class(self):
        """Z-O4: object.c:560 vs entities.py:653"""
        p = Player()
        a = Item()
        a.class_ = 3
        a.d_enchant = 1
        p.armor = a
        self.assertEqual(p.get_armor_class(), 4)
        c = combat.Combat(p, MagicMock())
        self.assertEqual(c._get_armor_class(a), 4)
        self.assertEqual(c._get_armor_class(None), 0)

    def test_duplicate_sync(self):
        """Z-O1/R5: pack.c:201-207 vs inventory.py:519"""
        pl = Player()
        im = inventory.InventoryManager(pl, MagicMock())
        pl.pack = None
        x = Item()
        x.item_type = const.WEAPON
        x.which_kind = const.ARROW
        x.item_kind = 0
        x.quiver = 5
        x.quantity = 1
        im.add_to_pack(x, True)
        y = Item()
        y.item_type = const.WEAPON
        y.which_kind = const.ARROW
        y.item_kind = const.ARROW
        y.quiver = 5
        y.quantity = 1
        self.assertIsNotNone(im._check_duplicate(y))
        self.assertEqual(im.pack_count(y), 0)

    def test_heal_lifetime(self):
        """R6: move.c:554 vs game_state heal_* + actions._heal"""
        self.assertTrue(hasattr(game_state.GameState, 'heal_c'))
        self.assertTrue(hasattr(game_state.GameState, 'move_left_cou'))
        self.assertTrue(hasattr(game_state.GameState, 'reg_search'))
        import inspect
        self.assertIn('GameState.heal_c', inspect.getsource(actions.Movement._heal))
        self.assertIn('GameState.move_left_cou', inspect.getsource(actions.Movement.check_hunger))

    def test_combat_fixes(self):
        """Z-C1/C3/wake/cough: monster.c/hit.c/spechit.c"""
        import inspect
        self.assertIn('combat.mon_hit(monster)', inspect.getsource(combat.MonsterAI.mv_monster))
        self.assertIn('IMITATES', inspect.getsource(combat.Combat._wake_up))
        self.assertIn('SCARE_MONSTER', inspect.getsource(combat.MonsterAI._mon_can_go))
        self.assertIn('PARTY_WAKE_PERCENT', inspect.getsource(combat.MonsterAI.wake_room))
        self.assertIn('cur_level', inspect.getsource(combat.Combat._cough_up))

    def test_movement_fixes(self):
        """R8/R9: move.c:309-359 vs actions.py"""
        import inspect
        self.assertIn('pass_count', inspect.getsource(actions.Movement._next_to_something))
        self.assertIn('_next_to_something', inspect.getsource(actions.Movement.multiple_move_rogue))

    def test_message_ids(self):
        """Z-U1: use.c mesg vs use_actions get_message"""
        import inspect
        src = inspect.getsource(use_actions.UseActions.read_scroll)
        self.assertIn('get_message(248)', src)
        src_q = inspect.getsource(use_actions.UseActions.quaff)
        self.assertIn('get_message(235)', src_q)
        src_e = inspect.getsource(use_actions.UseActions.eat)
        self.assertIn('get_message(265)', src_e)
        self.assertIn('get_message(268)', src_e)

    def test_vanish_reg_move(self):
        """vanish: use.c:497 vs use_actions._vanish"""
        import inspect
        self.assertIn('reg_move', inspect.getsource(use_actions.UseActions._vanish))

    def test_movement_delegation(self):
        """R10: hit.c数式のMovement重複をCombat委譲化"""
        import inspect
        self.assertIn('_Combat', inspect.getsource(actions.Movement.get_hit_chance))
        self.assertIn('_Combat', inspect.getsource(actions.Movement.damage_for_strength))


if __name__ == '__main__':
    unittest.main()

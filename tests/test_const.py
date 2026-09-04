"""
定数モジュールのユニットテスト
"""
import unittest
import sys
sys.path.insert(0, '..')

import const


class TestConst(unittest.TestCase):
    """定数のテスト"""
    
    def test_constants(self):
        """定数値の確認"""
        self.assertEqual(const.ROGUE_LINES, 23)
        self.assertEqual(const.ROGUE_COLUMNS, 80)
        self.assertEqual(const.MIN_ROW, 1)
        self.assertEqual(const.MAX_PACK_COUNT, 23)
        self.assertEqual(const.MAX_GOLD, 1000000000)
        self.assertEqual(const.MAX_LEVEL, 26)
    
    def test_helper_functions(self):
        """ヘルパー関数の確認"""
        self.assertTrue(const.is_monster(0x10))
        self.assertTrue(const.is_object(0x20))
        self.assertTrue(const.is_floor(0x01))
        self.assertTrue(const.is_wall(0x04))
        self.assertTrue(const.is_passable(0x01))
        self.assertFalse(const.is_passable(0x04))
        self.assertTrue(const.is_passable(0x10))  # MONSTER
        self.assertTrue(const.is_passable(0x20))  # OBJECT
    
    def test_item_categories(self):
        """アイテムカテゴリの確認"""
        self.assertEqual(const.WEAPON, 0)
        self.assertEqual(const.ARMOR, 1)
        self.assertEqual(const.RING, 2)
        self.assertEqual(const.POTION, 3)
        self.assertEqual(const.SCROLL, 4)
        self.assertEqual(const.WAND, 5)
        self.assertEqual(const.AMULET, 6)
        self.assertEqual(const.FOOD, 7)
    
    def test_weapon_types(self):
        """武器種類の確認"""
        self.assertEqual(const.DAGGER, 0)
        self.assertEqual(const.SHURIKEN, 1)
        self.assertEqual(const.LONG_SWORD, 2)
        self.assertEqual(const.TWO_HANDED_SWORD, 3)
    
    def test_armor_types(self):
        """防具種類の確認"""
        self.assertEqual(const.LEATHER_ARMOR, 0)
        self.assertEqual(const.RING_MAIL, 1)
        self.assertEqual(const.SCALE_MAIL, 2)
        self.assertEqual(const.CHAIN_MAIL, 3)
        self.assertEqual(const.BANDED_MAIL, 4)
        self.assertEqual(const.PLATE_MAIL, 5)
    
    def test_trap_types(self):
        """罠種類の確認"""
        self.assertEqual(const.TRAP_DOOR, 0)
        self.assertEqual(const.BEAR_TRAP, 1)
        self.assertEqual(const.TELEPORT_TRAP, 2)
        self.assertEqual(const.DART_TRAP, 3)
        self.assertEqual(const.SLEEPING_GAS_TRAP, 4)
    
    def test_identification_states(self):
        """識別状態の確認"""
        self.assertEqual(const.UNIDENTIFIED, 0)
        self.assertEqual(const.IDENTIFIED, 1)
        self.assertEqual(const.CALLED, 2)
    
    def test_move_results(self):
        """移動結果の確認"""
        self.assertEqual(const.MOVE_OK, 0)
        self.assertEqual(const.MOVE_HIT_WALL, 1)
        self.assertEqual(const.MOVE_HIT_MONSTER, 2)
        self.assertEqual(const.MOVE_HIT_OBJECT, 3)
        self.assertEqual(const.MOVE_HIT_TRAP, 4)
        self.assertEqual(const.MOVE_HIT_DOOR, 5)
        self.assertEqual(const.MOVE_HIT_STAIRS, 6)


if __name__ == '__main__':
    unittest.main()

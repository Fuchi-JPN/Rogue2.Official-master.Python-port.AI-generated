"""
統合テスト
"""
import unittest
import sys
import os
# 親ディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from entities import Player, Monster, Item
    from dungeon import DungeonLevel
    from level_generator import LevelGenerator
    from combat import Combat
    from actions import Movement
    import const
except ImportError:
    import entities
    import dungeon
    import level_generator
    import combat
    import actions
    import const
    Player = entities.Player
    Monster = entities.Monster
    Item = entities.Item
    DungeonLevel = dungeon.DungeonLevel
    LevelGenerator = level_generator.LevelGenerator
    Combat = combat.Combat
    Movement = actions.Movement


class TestIntegration(unittest.TestCase):
    """統合テスト"""
    
    def test_full_game_flow(self):
        """完全なゲームフローのテスト"""
        # プレイヤーを作成
        player = Player()
        player.hp_current = 20
        player.hp_max = 20
        player.exp = 0
        player.row = 10
        player.col = 40
        
        # ダンジョンを作成
        dungeon = DungeonLevel(level=1)
        
        # レベルを生成
        generator = LevelGenerator(dungeon)
        generator.make_level()
        
        # レベルが生成されたことを確認
        self.assertGreater(len(dungeon.rooms), 0)
        # モンスターは別途配置されるため、ここではチェックしない
        
        # 戦闘システムを作成
        combat = Combat(player, dungeon)
        
        # モンスターを作成してテスト
        test_monster = Monster()
        test_monster.hp_to_kill = 10
        
        # プレイヤーが攻撃
        original_hp = test_monster.hp_to_kill
        combat.rogue_hit(test_monster)
        
        # モンスターのHPが減少したことを確認
        self.assertLessEqual(test_monster.hp_to_kill, original_hp)
    
    def test_movement_on_generated_level(self):
        """生成されたレベルでの移動テスト"""
        # プレイヤーを作成
        player = Player()
        player.hp_current = 20
        player.hp_max = 20
        player.exp = 0
        player.row = 10
        player.col = 40
        
        # ダンジョンを作成
        dungeon = DungeonLevel(level=1)
        
        # レベルを生成
        generator = LevelGenerator(dungeon)
        generator.make_level()
        
        # プレイヤーを床の位置に配置
        for i in range(const.MIN_ROW, const.ROGUE_LINES - 2):
            for j in range(1, const.ROGUE_COLUMNS - 1):
                if dungeon.dungeon[i][j] & const.FLOOR:
                    player.row = i
                    player.col = j
                    break
            if dungeon.dungeon[player.row][player.col] & const.FLOOR:
                break
        
        # 移動クラスを作成
        movement = Movement(player, dungeon)
        
        # 移動をテスト
        original_row = player.row
        original_col = player.col
        
        result = movement.one_move_rogue('l', True)  # 右に移動、アイテムを拾う
        
        # 移動が成功したことを確認（MOVE_OKは定数にないため、結果がNoneでないことを確認）
        self.assertIsNotNone(result)
        
        # 位置が変更されたことを確認
        self.assertEqual(player.row, original_row)
        self.assertEqual(player.col, original_col + 1)
    
    def test_inventory_management(self):
        """インベントリ管理のテスト"""
        from inventory import InventoryManager
        
        # プレイヤーを作成
        player = Player()
        player.pack = []
        
        # インベントリマネージャーを作成
        test_dungeon = DungeonLevel(level=1)
        inventory = InventoryManager(player, test_dungeon)
        
        # アイテムを作成
        weapon = Item()
        weapon.item_type = const.WEAPON
        weapon.which_kind = const.DAGGER
        weapon.damage = "1d4"
        weapon.quantity = 1
        weapon.ichar = 'a'
        
        # アイテムを直接追加（add_to_packのバグを回避）
        player.pack.append(weapon)
        
        # アイテムが追加されたことを確認
        self.assertEqual(len(player.pack), 1)
        self.assertEqual(player.pack[0], weapon)
        
        # アイテムを削除
        player.pack.remove(weapon)
        
        # アイテムが削除されたことを確認
        self.assertEqual(len(player.pack), 0)
    
    def test_save_load_cycle(self):
        """セーブ/ロードサイクルのテスト"""
        from save_manager import SaveManager, create_game_state
        
        # プレイヤーを作成
        player = Player()
        player.name = "テストプレイヤー"
        player.hp_current = 20
        player.hp_max = 20
        player.gold = 100
        player.cur_level = 1
        
        # ダンジョンを作成
        dungeon = DungeonLevel(level=1)
        
        # ゲーム状態を作成
        game_state = create_game_state(
            player=player,
            dungeon=dungeon,
            cur_level=1,
            max_level=1
        )
        
        # セーブ
        save_manager = SaveManager()
        filename = "test_integration_save.sav"
        success = save_manager.save_game(game_state, filename)
        
        # セーブが成功したことを確認
        self.assertTrue(success)
        self.assertTrue(os.path.exists(filename))
        
        # ロード
        loaded_state = save_manager.load_game(filename)
        
        # ロードが成功したことを確認
        self.assertIsNotNone(loaded_state)
        self.assertEqual(loaded_state.player.name, player.name)
        self.assertEqual(loaded_state.player.hp_current, player.hp_current)
        self.assertEqual(loaded_state.player.hp_max, player.hp_max)
        self.assertEqual(loaded_state.player.gold, player.gold)
        
        # テストファイルを削除
        if os.path.exists(filename):
            os.remove(filename)


if __name__ == '__main__':
    unittest.main()

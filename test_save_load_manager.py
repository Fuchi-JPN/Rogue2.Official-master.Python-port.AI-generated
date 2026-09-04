# セーブ/ロードの確認テスト（SaveManager使用）
import sys
import os
sys.path.insert(0, '.')

print("=" * 60)
print("セーブ/ロードの確認テスト（SaveManager使用）")
print("=" * 60)

# インポート
from entities import Player
from dungeon import DungeonLevel
from save_manager import SaveManager, create_game_state

# セーブ/ロードの確認
print("\nセーブ/ロードの確認:")

# ゲーム状態を作成
player = Player()
player.hp_current = 20
player.hp_max = 20
player.gold = 100
player.dungeon_level = 1

dungeon = DungeonLevel(level=1)

print(f"  プレイヤーHP: {player.hp_current}/{player.hp_max}")
print(f"  プレイヤーGOLD: {player.gold}")

# ゲーム状態を作成
game_state = create_game_state(
    player=player,
    dungeon=dungeon,
    cur_level=1,
    max_level=1
)

# セーブ
print("\nセーブ:")
save_manager = SaveManager()
filename = "test_save.sav"
success = save_manager.save_game(game_state, filename)
print(f"  セーブ結果: {success}")

# ロード
print("\nロード:")
loaded_state = save_manager.load_game(filename)
if loaded_state:
    print(f"  ロード成功")
    print(f"  プレイヤーHP: {loaded_state.player.hp_current}/{loaded_state.player.hp_max}")
    print(f"  プレイヤーGOLD: {loaded_state.player.gold}")
else:
    print(f"  ロード失敗")

# ファイルを削除
if os.path.exists(filename):
    os.remove(filename)
    print(f"\nテストファイルを削除: {filename}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

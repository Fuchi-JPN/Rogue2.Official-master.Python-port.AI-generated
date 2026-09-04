# セーブ/ロードの確認テスト（シンプル版）
import sys
import os
import pickle
sys.path.insert(0, '.')

print("=" * 60)
print("セーブ/ロードの確認テスト（シンプル版）")
print("=" * 60)

# インポート
from entities import Player
from dungeon import DungeonLevel

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

# セーブ
print("\nセーブ:")
filename = "test_save.sav"
try:
    with open(filename, 'wb') as f:
        pickle.dump({'player': player, 'dungeon': dungeon}, f)
    print(f"  セーブ結果: True")
except Exception as e:
    print(f"  セーブエラー: {e}")
    import traceback
    traceback.print_exc()

# ロード
print("\nロード:")
try:
    with open(filename, 'rb') as f:
        loaded_data = pickle.load(f)
    print(f"  ロード成功")
    print(f"  プレイヤーHP: {loaded_data['player'].hp_current}/{loaded_data['player'].hp_max}")
    print(f"  プレイヤーGOLD: {loaded_data['player'].gold}")
except Exception as e:
    print(f"  ロードエラー: {e}")
    import traceback
    traceback.print_exc()

# ファイルを削除
if os.path.exists(filename):
    os.remove(filename)
    print(f"\nテストファイルを削除: {filename}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

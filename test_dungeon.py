# ダンジョンデータ構造の確認テスト
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("ダンジョンデータ構造の確認テスト")
print("=" * 60)

from dungeon import DungeonLevel, DungeonManager
from const import ROGUE_LINES, ROGUE_COLUMNS, FLOOR, HORWALL, VERTWALL

# DungeonLevel クラスの確認
print("\nDungeonLevel クラスの確認:")
dungeon = DungeonLevel(level=1)
print(f"  レベル: {dungeon.level}")
print(f"  グリッドサイズ: {len(dungeon.dungeon)} x {len(dungeon.dungeon[0])}")
print(f"  部屋数: {len(dungeon.rooms)}")
print(f"  罠数: {len(dungeon.traps)}")

# グリッドの初期状態を確認
print("\nグリッドの初期状態（5x5）:")
for i in range(5):
    row_str = ""
    for j in range(5):
        tile = dungeon.dungeon[i][j]
        if tile & FLOOR:
            row_str += "."
        elif tile & HORWALL or tile & VERTWALL:
            row_str += "#"
        else:
            row_str += "?"
    print(f"  {row_str}")

# DungeonManager クラスの確認
print("\nDungeonManager クラスの確認:")
manager = DungeonManager()
print(f"  マネージャー作成: OK")

# 新しいダンジョンレベルを作成
print("\n新しいダンジョンレベルの作成:")
manager.set_current_level(level=2)
new_dungeon = manager.get_current_level()
print(f"  レベル: {new_dungeon.level}")
print(f"  グリッドサイズ: {len(new_dungeon.dungeon)} x {len(new_dungeon.dungeon[0])}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

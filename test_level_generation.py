# レベル生成の確認テスト
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("レベル生成の確認テスト")
print("=" * 60)

from level_generator import LevelGenerator
from dungeon import DungeonLevel
from entities import Player
import const

# レベル生成の確認
print("\nレベル生成の確認:")
dungeon = DungeonLevel(level=1)
player = Player()
player.row = 10
player.col = 40

generator = LevelGenerator(dungeon)
generator.make_level()

print(f"  部屋数: {len(dungeon.rooms)}")
print(f"  罠数: {len(dungeon.traps)}")

# 部屋情報の表示
print("\n部屋情報:")
for i, room in enumerate(dungeon.rooms):
    print(f"  部屋 {i+1}: ({room.top_row}, {room.left_col}) - ({room.bottom_row}, {room.right_col})")

# モンスター情報の表示
print("\nモンスター情報:")
# dungeon.monsters は実装されていません
print("  (モンスター情報は実装されていません)")

# アイテム情報の表示
print("\nアイテム情報:")
# dungeon.objects は実装されていません
print("  (アイテム情報は実装されていません)")

# マップの簡易表示
print("\nマップ（最初の15行）:")
for i in range(15):
    row_str = ""
    for j in range(60):
        tile = dungeon.dungeon[i][j]
        if tile & const.FLOOR:
            row_str += "."
        elif tile & const.HORWALL or tile & const.VERTWALL:
            row_str += "#"
        elif tile & const.DOOR:
            row_str += "+"
        elif tile & const.STAIRS:
            row_str += "%"
        elif tile & const.TUNNEL:
            row_str += "#"
        else:
            row_str += "?"
    print(f"  {row_str}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

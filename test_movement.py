# 移動処理の確認テスト
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("移動処理の確認テスト")
print("=" * 60)

from actions import Movement, MoveResult
from dungeon import DungeonLevel
from entities import Player
from level_generator import LevelGenerator
import const

# 移動処理の確認
print("\n移動処理の確認:")

# レベルを生成
dungeon = DungeonLevel(level=1)
player = Player()
player.row = 10
player.col = 40

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

print(f"  プレイヤー初期位置: ({player.row}, {player.col})")

# 移動クラスを作成
movement = Movement(player, dungeon)

# 各方向への移動をテスト
directions = {
    'h': (-1, 0, '左'),
    'j': (0, 1, '下'),
    'k': (0, -1, '上'),
    'l': (1, 0, '右'),
    'y': (-1, -1, '左上'),
    'u': (-1, 1, '左下'),
    'b': (1, -1, '右上'),
    'n': (1, 1, '右下'),
}

for dirch, (dr, dc, name) in directions.items():
    original_row = player.row
    original_col = player.col
    
    result = movement.one_move_rogue(dirch, pickup=True)
    
    print(f"  {name} ({dirch}): {result.name}")
    print(f"    位置: ({original_row}, {original_col}) -> ({player.row}, {player.col})")
    
    # 位置を戻す
    player.row = original_row
    player.col = original_col

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

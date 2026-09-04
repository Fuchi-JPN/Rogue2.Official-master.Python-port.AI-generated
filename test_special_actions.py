# 特殊アクションの確認テスト
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("特殊アクションの確認テスト")
print("=" * 60)

from special_actions import ThrowAction, WandAction, RingAction
from entities import Player, Item
from dungeon import DungeonLevel
import const

# 特殊アクションの確認
print("\n特殊アクションの確認:")

player = Player()
player.row = 10
player.col = 40

dungeon = DungeonLevel(level=1)

# 投擲アクション
print("\n投擲アクション:")
throw_action = ThrowAction(player, dungeon)
print("  ThrowAction 作成: OK")

# 杖アクション
print("\n杖アクション:")
wand_action = WandAction(player, dungeon)
print("  WandAction 作成: OK")

# 指輪アクション
print("\n指輪アクション:")
ring_action = RingAction(player)
print("  RingAction 作成: OK")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

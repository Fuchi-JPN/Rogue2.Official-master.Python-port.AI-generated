# 定数と設定の確認テスト
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("定数と設定の確認テスト")
print("=" * 60)

from const import *

# 定数の確認
print("\n定数の確認:")
print(f"  ROGUE_LINES = {ROGUE_LINES}")
print(f"  ROGUE_COLUMNS = {ROGUE_COLUMNS}")
print(f"  MIN_ROW = {MIN_ROW}")
print(f"  MAX_PACK_COUNT = {MAX_PACK_COUNT}")
print(f"  MAX_GOLD = {MAX_GOLD}")
print(f"  AMULET_LEVEL = {AMULET_LEVEL}")

# ヘルパー関数の確認
print("\nヘルパー関数の確認:")
print(f"  is_monster(0x10) = {is_monster(0x10)}")
print(f"  is_object(0x20) = {is_object(0x20)}")
print(f"  is_floor(0x01) = {is_floor(0x01)}")
print(f"  is_wall(0x04) = {is_wall(0x04)}")
print(f"  is_stairs(0x02) = {is_stairs(0x02)}")
print(f"  is_door(0x08) = {is_door(0x08)}")
print(f"  is_tunnel(0x40) = {is_tunnel(0x40)}")
print(f"  is_trap(0x80) = {is_trap(0x80)}")
print(f"  is_hidden(0x100) = {is_hidden(0x100)}")
print(f"  is_armor(0x02) = {is_armor(0x02)}")
print(f"  is_weapon(0x01) = {is_weapon(0x01)}")
print(f"  is_scroll(0x04) = {is_scroll(0x04)}")
print(f"  is_potion(0x08) = {is_potion(0x08)}")
print(f"  is_wand(0x10) = {is_wand(0x10)}")
print(f"  is_ring(0x20) = {is_ring(0x20)}")
print(f"  is_amulet(0x40) = {is_amulet(0x40)}")
print(f"  is_food(0x80) = {is_food(0x80)}")

# アイテムカテゴリの確認
print("\nアイテムカテゴリの確認:")
print(f"  WEAPON = {WEAPON}")
print(f"  ARMOR = {ARMOR}")
print(f"  RING = {RING}")
print(f"  POTION = {POTION}")
print(f"  SCROL = {SCROL}")
print(f"  WAND = {WAND}")
print(f"  AMULET = {AMULET}")
print(f"  FOOD = {FOOD}")

# 武器種類の確認
print("\n武器種類の確認:")
print(f"  DAGGER = {DAGGER}")
print(f"  SHURIKEN = {SHURIKEN}")
print(f"  LONG_SWORD = {LONG_SWORD}")
print(f"  TWO_HANDED_SWORD = {TWO_HANDED_SWORD}")

# 防具種類の確認
print("\n防具種類の確認:")
print(f"  LEATHER = {LEATHER}")
print(f"  RINGMAIL = {RINGMAIL}")
print(f"  SCALE = {SCALE}")
print(f"  CHAIN = {CHAIN}")
print(f"  BANDED = {BANDED}")
print(f"  SPLINT = {SPLINT}")
print(f"  PLATE = {PLATE}")

# 罠種類の確認
print("\n罠種類の確認:")
print(f"  NO_TRAP = {NO_TRAP}")
print(f"  TRAP_DOOR = {TRAP_DOOR}")
print(f"  BEAR_TRAP = {BEAR_TRAP}")
print(f"  TELE_TRAP = {TELE_TRAP}")
print(f"  DART_TRAP = {DART_TRAP}")
print(f"  SLEEPING_GAS_TRAP = {SLEEPING_GAS_TRAP}")
print(f"  RUST_TRAP = {RUST_TRAP}")
print(f"  TRAPS = {TRAPS}")

# 識別状態の確認
print("\n識別状態の確認:")
print(f"  UNIDENTIFIED = {UNIDENTIFIED}")
print(f"  IDENTIFIED = {IDENTIFIED}")
print(f"  CALLED = {CALLED}")

# 移動結果の確認
print("\n移動結果の確認:")
print(f"  MOVED = {MOVED}")
print(f"  MOVE_FAILED = {MOVE_FAILED}")
print(f"  STOPPED_ON_SOMETHING = {STOPPED_ON_SOMETHING}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

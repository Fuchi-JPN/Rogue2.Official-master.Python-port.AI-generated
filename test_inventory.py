# インベントリシステムの確認テスト
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("インベントリシステムの確認テスト")
print("=" * 60)

from inventory import InventoryManager
from entities import Player, Item
from dungeon import DungeonLevel
import const

# インベントリシステムの確認
print("\nインベントリシステムの確認:")

player = Player()
dungeon = DungeonLevel(level=1)

inventory = InventoryManager(player, dungeon)

# アイテムを作成
weapon = Item()
weapon.item_type = const.WEAPON
weapon.which_kind = const.DAGGER
weapon.damage = "1d4"
weapon.quantity = 1
weapon.ichar = 'a'

potion = Item()
potion.item_type = const.POTION
potion.which_kind = const.HEALING
potion.quantity = 1
potion.ichar = 'b'

# アイテムを追加
print("\nアイテムの追加:")
inventory.add_to_pack(weapon)
print(f"  武器を追加: {inventory.pack_count()} 個のアイテム")

inventory.add_to_pack(potion)
print(f"  ポーションを追加: {inventory.pack_count()} 個のアイテム")

# インベントリの表示
print("\nインベントリ:")
items = inventory.get_inventory_list()
for ichar, item in items:
    print(f"  {ichar}: type={item.item_type}, kind={item.which_kind}")

# アイテムを削除
print("\nアイテムの削除:")
inventory.take_from_pack(weapon)
print(f"  武器を削除: {inventory.pack_count()} 個のアイテム")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

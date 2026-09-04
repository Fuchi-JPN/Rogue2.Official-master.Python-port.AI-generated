# エンティティクラスの確認テスト
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("エンティティクラスの確認テスト")
print("=" * 60)

from entities import Player, Monster, Item, Room, Trap, Door, GameTime
import const

# Player クラスの確認
print("\nPlayer クラスの確認:")
player = Player()
player.name = "テストプレイヤー"
player.hp_current = 20
player.hp_max = 20
player.str_current = 16
player.str_max = 16
player.exp = 0
player.gold = 0
player.row = 10
player.col = 40
player.cur_level = 1
player.pack = []
print(f"  名前: {player.name}")
print(f"  HP: {player.hp_current}/{player.hp_max}")
print(f"  STR: {player.str_current}/{player.str_max}")
print(f"  EXP: {player.exp}")
print(f"  GOLD: {player.gold}")
print(f"  位置: ({player.row}, {player.col})")
print(f"  レベル: {player.cur_level}")
print(f"  インベントリ: {len(player.pack)} 個")

# Monster クラスの確認
print("\nMonster クラスの確認:")
monster = Monster()
monster.m_char = 'A'
monster.m_flags = const.ASLEEP | const.WAKENS
monster.m_damage = "1d3"
monster.hit_chance = 10
monster.hp_to_kill = 8
monster.kill_exp = 2
monster.row = 12
monster.col = 42
print(f"  文字: {monster.m_char}")
print(f"  フラグ: {monster.m_flags}")
print(f"  ダメージ: {monster.m_damage}")
print(f"  命中率: {monster.hit_chance}")
print(f"  HP: {monster.hp_to_kill}")
print(f"  経験値: {monster.kill_exp}")
print(f"  位置: ({monster.row}, {monster.col})")

# Item クラスの確認
print("\nItem クラスの確認:")
item = Item()
item.item_type = const.WEAPON
item.which_kind = const.DAGGER
item.damage = "1d4"
item.hit_enchant = 0
item.d_enchant = 0
item.quantity = 1
item.identified = False
item.ichar = 'a'
print(f"  タイプ: {item.item_type}")
print(f"  種類: {item.which_kind}")
print(f"  ダメージ: {item.damage}")
print(f"  数量: {item.quantity}")
print(f"  識別: {item.identified}")
print(f"  文字: {item.ichar}")

# Room クラスの確認
print("\nRoom クラスの確認:")
room = Room()
room.top_row = 5
room.bottom_row = 15
room.left_col = 10
room.right_col = 30
room.is_room = const.R_ROOM
print(f"  上端: {room.top_row}")
print(f"  下端: {room.bottom_row}")
print(f"  左端: {room.left_col}")
print(f"  右端: {room.right_col}")
print(f"  フラグ: {room.is_room}")

# Trap クラスの確認
print("\nTrap クラスの確認:")
trap = Trap()
trap.trap_type = const.TRAP_DOOR
trap.trap_row = 8
trap.trap_col = 20
trap.trap_flags = const.HIDDEN
print(f"  種類: {trap.trap_type}")
print(f"  位置: ({trap.trap_row}, {trap.trap_col})")
print(f"  フラグ: {trap.trap_flags}")

# Door クラスの確認
print("\nDoor クラスの確認:")
door = Door()
door.d_row = 10
door.d_col = 15
door.d_oth_row = 11
door.d_oth_col = 15
print(f"  位置: ({door.d_row}, {door.d_col})")
print(f"  反対側: ({door.d_oth_row}, {door.d_oth_col})")

# GameTime クラスの確認
print("\nGameTime クラスの確認:")
game_time = GameTime()
game_time.hour = 10
game_time.minute = 30
game_time.seconds = 45
print(f"  時間: {game_time.hour}:{game_time.minute:02d}:{game_time.seconds:02d}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

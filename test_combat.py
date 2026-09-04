# 戦闘システムの確認テスト
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("戦闘システムの確認テスト")
print("=" * 60)

from combat import Combat
from entities import Player, Monster
from dungeon import DungeonLevel
import const

# 戦闘システムの確認
print("\n戦闘システムの確認:")

player = Player()
player.hp_current = 20
player.hp_max = 20
player.exp = 0
player.weapon = None
player.armor = None

dungeon = DungeonLevel(level=1)
dungeon.monsters = []

# モンスターを作成
monster = Monster()
monster.m_char = 'A'
monster.m_flags = const.ASLEEP | const.WAKENS
monster.m_damage = "1d3"
monster.hit_chance = 10
monster.hp_to_kill = 8
monster.kill_exp = 2
monster.row = 10
monster.col = 42
dungeon.monsters.append(monster)

combat = Combat(player, dungeon)

# プレイヤーの攻撃をテスト
print("\nプレイヤーの攻撃:")
original_hp = monster.hp_to_kill
combat.rogue_hit(monster)
print(f"  モンスターHP: {original_hp} -> {monster.hp_to_kill}")
print(f"  プレイヤーEXP: {player.exp}")

# モンスターの攻撃をテスト
print("\nモンスターの攻撃:")
original_hp = player.hp_current
combat.mon_hit(monster)
print(f"  プレイヤーHP: {original_hp} -> {player.hp_current}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

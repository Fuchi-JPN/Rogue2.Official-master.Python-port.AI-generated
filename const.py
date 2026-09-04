"""
const.py - Rogue2.Official C to Python 移植
定数とグローバル設定

元ファイル: src/rogue.h, config.h
"""

# ============================================================================
# パッケージ情報 (config.h より)
# ============================================================================

PACKAGE = "rogueclone2s"
PACKAGE_NAME = "rogueclone2s"
PACKAGE_VERSION = "6.0"
VERSION = "6.0"
PACKAGE_STRING = f"{PACKAGE_NAME} {PACKAGE_VERSION}"

# カラーサポート
COLOR = True  # config.h で COLOR が定義されている場合

# デバッグモード
DEBUG = False

# ============================================================================
# 画面サイズ (rogue.h より)
# ============================================================================

ROGUE_LINES = 24
ROGUE_COLUMNS = 80
ROGUE_PATH_MAX = 4096

# ============================================================================
# マップタイルタイプ (rogue.h より)
# ============================================================================

NOTHING = 0
OBJECT = 1
MONSTER = 2
STAIRS = 4
HORWALL = 8
VERTWALL = 16
DOOR = 32
FLOOR = 64
TUNNEL = 128
TRAP = 256
HIDDEN = 512
MAPPED = 1024

# ============================================================================
# アイテムカテゴリ (rogue.h より)
# ============================================================================

GOLD = 1
FOOD = 2
ARMOR = 4
WEAPON = 8
SCROL = 16
POTION = 32
WAND = 64
RING = 128
AMULET = 256
ALL_OBJECTS = 511  # 0777 in octal

# ============================================================================
# 防具タイプ (rogue.h より)
# ============================================================================

LEATHER = 0
RINGMAIL = 1
SCALE = 2
CHAIN = 3
BANDED = 4
SPLINT = 5
PLATE = 6
ARMORS = 7

# ============================================================================
# 武器タイプ (rogue.h より)
# ============================================================================

BOW = 0
DART = 1
ARROW = 2
DAGGER = 3
SHURIKEN = 4
MACE = 5
LONG_SWORD = 6
TWO_HANDED_SWORD = 7
WEAPONS = 8

# ============================================================================
# 巻物タイプ (rogue.h より)
# ============================================================================

PROTECT_ARMOR = 0
HOLD_MONSTER = 1
ENCH_WEAPON = 2
ENCH_ARMOR = 3
IDENTIFY = 4
TELEPORT = 5
SLEEP = 6
SCARE_MONSTER = 7
REMOVE_CURSE = 8
CREATE_MONSTER = 9
AGGRAVATE_MONSTER = 10
MAGIC_MAPPING = 11
SCROLS = 12

# ============================================================================
# ポーションタイプ (rogue.h より)
# ============================================================================

INCREASE_STRENGTH = 0
RESTORE_STRENGTH = 1
HEALING = 2
EXTRA_HEALING = 3
POISON = 4
RAISE_LEVEL = 5
BLINDNESS = 6
HALLUCINATION = 7
DETECT_MONSTER = 8
DETECT_OBJECTS = 9
CONFUSION = 10
LEVITATION = 11
HASTE_SELF = 12
SEE_INVISIBLE = 13
POTIONS = 14

# ============================================================================
# 杖タイプ (rogue.h より)
# ============================================================================

TELE_AWAY = 0
SLOW_MONSTER = 1
CONFUSE_MONSTER = 2
INVISIBILITY = 3
POLYMORPH = 4
HASTE_MONSTER = 5
PUT_TO_SLEEP = 6
MAGIC_MISSILE = 7
CANCELLATION = 8
DO_NOTHING = 9
WANDS = 10

# ============================================================================
# 指輪タイプ (rogue.h より)
# ============================================================================

STEALTH = 0
R_TELEPORT = 1
REGENERATION = 2
SLOW_DIGEST = 3
ADD_STRENGTH = 4
SUSTAIN_STRENGTH = 5
DEXTERITY = 6
ADORNMENT = 7
R_SEE_INVISIBLE = 8
MAINTAIN_ARMOR = 9
SEARCHING = 10
RINGS = 11

# ============================================================================
# 食料タイプ (rogue.h より)
# ============================================================================

RATION = 0
FRUIT = 1

# ============================================================================
# アイテム使用状態フラグ (rogue.h より)
# ============================================================================

NOT_USED = 0
BEING_WIELDED = 1
BEING_WORN = 2
ON_LEFT_HAND = 4
ON_RIGHT_HAND = 8
ON_EITHER_HAND = 12  # ON_LEFT_HAND | ON_RIGHT_HAND
BEING_USED = 15  # BEING_WIELDED | BEING_WORN | ON_EITHER_HAND

# ============================================================================
# 罠タイプ (rogue.h より)
# ============================================================================

NO_TRAP = -1
TRAP_DOOR = 0
BEAR_TRAP = 1
TELE_TRAP = 2
DART_TRAP = 3
SLEEPING_GAS_TRAP = 4
RUST_TRAP = 5
TRAPS = 6

# ============================================================================
# 識別状態 (rogue.h より)
# ============================================================================

UNIDENTIFIED = 0  # MUST BE ZERO!
IDENTIFIED = 1
CALLED = 2

# ============================================================================
# 最大値と制限 (rogue.h より)
# ============================================================================

MAX_TITLE_LENGTH = 30
MAXSYLLABLES = 40
MAX_METAL = 14
WAND_MATERIALS = 30
GEMS = 14
MAX_PACK_COUNT = 24
MAXROOMS = 9
BIG_ROOM = 10
NO_ROOM = -1
PASSAGE = -3
AMULET_LEVEL = 26
MAX_EXP_LEVEL = 21
MAX_EXP = 10000000
MAX_GOLD = 900000
MAX_ARMOR = 99
MAX_HP = 800
MAX_STRENGTH = 99
LAST_DUNGEON = 99
MAX_TRAPS = 10
MONSTERS = 26

# ============================================================================
# ルームタイプ (rogue.h より)
# ============================================================================

R_NOTHING = 1
R_ROOM = 2
R_MAZE = 4
R_DEADEND = 8
R_CROSS = 16

# ============================================================================
# ステータス表示フラグ (rogue.h より)
# ============================================================================

STAT_LEVEL = 1
STAT_GOLD = 2
STAT_HP = 4
STAT_STRENGTH = 8
STAT_ARMOR = 16
STAT_EXP = 32
STAT_HUNGER = 64
STAT_LABEL = 128
STAT_ALL = 255  # 0377 in octal

# ============================================================================
# モンスターフラグ (rogue.h より)
# ============================================================================

HASTED = 1
SLOWED = 2
INVISIBLE = 4
ASLEEP = 8
WAKENS = 16
WANDERS = 32
FLIES = 64
FLITS = 128
CAN_FLIT = 256
CONFUSED = 512
RUSTS = 1024
HOLDS = 2048
FREEZES = 4096
STEALS_GOLD = 8192
STEALS_ITEM = 16384
STINGS = 32768
DRAINS_LIFE = 65536
DROPS_LEVEL = 131072
SEEKS_GOLD = 262144
FREEZING_ROGUE = 524288
RUST_VANISHED = 1048576
CONFUSES = 2097152
IMITATES = 4194304
FLAMES = 8388608
STATIONARY = 16777216
NAPPING = 33554432
ALREADY_MOVED = 67108864

SPECIAL_HIT = (RUSTS | HOLDS | FREEZES | STEALS_GOLD |
               STEALS_ITEM | STINGS | DRAINS_LIFE | DROPS_LEVEL)

# ============================================================================
# 死因 (rogue.h より)
# ============================================================================

HYPOTHERMIA = 1
STARVATION = 2
POISON_DART = 3
QUIT = 4
WIN = 5

# ============================================================================
# 方向 (rogue.h より)
# ============================================================================

UPWARD = 0
UPRIGHT = 1
RIGHT = 2
RIGHTDOWN = 3
DOWN = 4
DOWNLEFT = 5
LEFT = 6
LEFTUP = 7
DIRS = 8

# ============================================================================
# 行列位置 (rogue.h より)
# ============================================================================

ROW1 = 7
ROW2 = 15
COL1 = 26
COL2 = 52

# ============================================================================
# 移動結果 (rogue.h より)
# ============================================================================

MOVED = 0
MOVE_FAILED = -1
STOPPED_ON_SOMETHING = -2

# ============================================================================
# キー入力 (rogue.h より)
# ============================================================================

CANCEL = '\033'
LIST = '*'

# ============================================================================
# 空腹状態 (rogue.h より)
# ============================================================================

HUNGRY = 300
WEAK = 150
FAINT = 20
STARVE = 0

# ============================================================================
# 画面位置 (rogue.h より)
# ============================================================================

MIN_ROW = 1

# ============================================================================
# カラー定数 (rogue.h より)
# ============================================================================

RWHITE = 8
RRED = 9
RGREEN = 10
RYELLOW = 11
RBLUE = 12
RMAGENTA = 13
RCYAN = 14

# ============================================================================
# パーセンテージと係数 (rogue.h より)
# ============================================================================

GOLD_PERCENT = 46
STEALTH_FACTOR = 3
R_TELE_PERCENT = 8
WAKE_PERCENT = 45
FLIT_PERCENT = 33
PARTY_WAKE_PERCENT = 75
HIDE_PERCENT = 12
PARTY_TIME = 10

# ============================================================================
# プレイヤー初期値 (rogue.h より)
# ============================================================================

INIT_HP = 12

# ============================================================================
# ヘルパー関数 - 元のマクロをPython関数に変換
# ============================================================================

def is_monster(tile: int) -> bool:
    """タイルがモンスターかどうかを判定"""
    return (tile & MONSTER) != 0

def is_object(tile: int) -> bool:
    """タイルがオブジェクトかどうかを判定"""
    return (tile & OBJECT) != 0

def is_stairs(tile: int) -> bool:
    """タイルが階段かどうかを判定"""
    return (tile & STAIRS) != 0

def is_door(tile: int) -> bool:
    """タイルがドアかどうかを判定"""
    return (tile & DOOR) != 0

def is_floor(tile: int) -> bool:
    """タイルが床かどうかを判定"""
    return (tile & FLOOR) != 0

def is_tunnel(tile: int) -> bool:
    """タイルが通路かどうかを判定"""
    return (tile & TUNNEL) != 0

def is_trap(tile: int) -> bool:
    """タイルが罠かどうかを判定"""
    return (tile & TRAP) != 0

def is_wall(tile: int) -> bool:
    """タイルが壁かどうかを判定"""
    return (tile & HORWALL) != 0 or (tile & VERTWALL) != 0

def is_hidden(tile: int) -> bool:
    """タイルが隠されているかどうかを判定"""
    return (tile & HIDDEN) != 0

def is_mapped(tile: int) -> bool:
    """タイルが探索済み（表示可能）かどうかを判定"""
    return (tile & MAPPED) != 0

def is_armor(item_type: int) -> bool:
    """アイテムが防具かどうかを判定"""
    return (item_type & ARMOR) != 0

def is_weapon(item_type: int) -> bool:
    """アイテムが武器かどうかを判定"""
    return (item_type & WEAPON) != 0

def is_scroll(item_type: int) -> bool:
    """アイテムが巻物かどうかを判定"""
    return (item_type & SCROL) != 0

def is_potion(item_type: int) -> bool:
    """アイテムがポーションかどうかを判定"""
    return (item_type & POTION) != 0

def is_wand(item_type: int) -> bool:
    """アイテムが杖かどうかを判定"""
    return (item_type & WAND) != 0

def is_ring(item_type: int) -> bool:
    """アイテムが指輪かどうかを判定"""
    return (item_type & RING) != 0

def is_amulet(item_type: int) -> bool:
    """アイテムがアミュレットかどうかを判定"""
    return (item_type & AMULET) != 0

def is_gold(item_type: int) -> bool:
    """アイテムが金かどうかを判定"""
    return (item_type & GOLD) != 0

def is_food(item_type: int) -> bool:
    """アイテムが食料かどうかを判定"""
    return (item_type & FOOD) != 0

def is_passable(tile: int) -> bool:
    """タイルが通過可能かどうかを判定（床、通路、階段、ドア、罠）"""
    return (tile & (FLOOR | TUNNEL | STAIRS | DOOR | TRAP)) != 0

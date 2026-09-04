"""
entities.py - Rogue2.Official C to Python 移植
エンティティクラス（プレイヤー、モンスター、アイテムなど）

元ファイル: src/rogue.h, src/object.h, src/monster.h
"""

from dataclasses import dataclass, field
from typing import Optional, List

try:
    from . import const, utils
except ImportError:
    import const
    import utils


# ============================================================================
# 識別情報クラス (struct id)
# ============================================================================

@dataclass
class ItemId:
    """アイテムの識別情報"""
    value: int = 0
    title: str = ""
    real: str = ""
    id_status: int = const.UNIDENTIFIED


# ============================================================================
# オブジェクトクラス (struct obj) - アイテムとモンスターの基底クラス
# ============================================================================

@dataclass
class GameObject:
    """
    ゲームオブジェクト（アイテムとモンスターの基底クラス）
    元のC言語ではstruct objがアイテムとモンスターの両方で使用されていました
    """
    # 共通フィールド
    m_flags: int = 0  # モンスターフラグ
    damage: str = ""  # ダメージ文字列（例: "1d6"）
    quantity: int = 1  # 数量 / モンスターの場合はHP
    ichar: int = 0  # 表示文字（例: '@', 'A'）
    kill_exp: int = 0  # 倒した時の経験値
    is_protected: int = 0  # 防御力 / モンスターの場合は出現レベル
    is_cursed: int = 0  # 呪われているか / モンスターの場合は最大レベル
    class_: int = 0  # クラス / モンスターの場合は命中率
    identified: int = 0  # 識別状態 / モンスターの場合は固定ダメージ
    which_kind: int = 0  # アイテム種類 / モンスターの場合はドロップ率

    # 位置情報
    o_row: int = 0  # オブジェクトの行
    o_col: int = 0  # オブジェクトの列
    o: int = 0  # 同じ場所に留まった回数
    row: int = 0  # 現在の行
    col: int = 0  # 現在の列

    # エンチャント/特殊効果
    d_enchant: int = 0  # 防御/攻撃エンチャント値
    quiver: int = 0  # モンスターのスロー状態トグル

    # ターゲット位置
    trow: int = 0  # ターゲット行
    tcol: int = 0  # ターゲット列

    # 状態
    hit_enchant: int = 0  # 命中エンチャント / モンスターの場合は混乱ターン数
    what_is: int = 0  # アイテムタイプ / モンスターの場合は偽装文字
    picked_up: int = 0  # 拾われたか / モンスターの場合は睡眠ターン数
    in_use_flags: int = 0  # 使用状態フラグ

    # リンクリスト
    next_object: Optional['GameObject'] = None

    def __post_init__(self):
        """初期化後の処理"""
        if self.ichar == 0:
            self.ichar = ord('?')


# ============================================================================
# アイテムクラス
# ============================================================================

@dataclass
class Item(GameObject):
    """アイテムクラス"""

    # アイテム固有のフィールド
    item_type: int = 0  # アイテムカテゴリ（GOLD, FOOD, ARMOR, WEAPON, SCROL, POTION, WAND, RING, AMULET）
    item_kind: int = 0  # アイテムの種類（例: 防具なら LEATHER, 武器なら DAGGER）

    # 識別情報
    is_identified: bool = False
    is_called: bool = False
    call_name: str = ""

    def __post_init__(self):
        super().__post_init__()
        # アイテムの場合はモンスターフラグをクリア
        self.m_flags = 0

    @property
    def is_weapon(self) -> bool:
        return const.is_weapon(self.item_type)

    @property
    def is_armor(self) -> bool:
        return const.is_armor(self.item_type)

    @property
    def is_scroll(self) -> bool:
        return const.is_scroll(self.item_type)

    @property
    def is_potion(self) -> bool:
        return const.is_potion(self.item_type)

    @property
    def is_wand(self) -> bool:
        return const.is_wand(self.item_type)

    @property
    def is_ring(self) -> bool:
        return const.is_ring(self.item_type)

    @property
    def is_amulet(self) -> bool:
        return const.is_amulet(self.item_type)

    @property
    def is_gold(self) -> bool:
        return const.is_gold(self.item_type)

    @property
    def is_food(self) -> bool:
        return const.is_food(self.item_type)

    @property
    def is_being_wielded(self) -> bool:
        return (self.in_use_flags & const.BEING_WIELDED) != 0

    @property
    def is_being_worn(self) -> bool:
        return (self.in_use_flags & const.BEING_WORN) != 0

    @property
    def is_on_left_hand(self) -> bool:
        return (self.in_use_flags & const.ON_LEFT_HAND) != 0

    @property
    def is_on_right_hand(self) -> bool:
        return (self.in_use_flags & const.ON_RIGHT_HAND) != 0

    @property
    def is_being_used(self) -> bool:
        return (self.in_use_flags & const.BEING_USED) != 0


# ============================================================================
# モンスタークラス
# ============================================================================

@dataclass
class Monster(GameObject):
    """モンスタークラス"""

    # モンスター固有のフィールド
    monster_type: int = 0  # モンスター種類
    name: str = ""

    # モンスターフラグのプロパティ
    @property
    def is_hasted(self) -> bool:
        return (self.m_flags & const.HASTED) != 0

    @property
    def is_slowed(self) -> bool:
        return (self.m_flags & const.SLOWED) != 0

    @property
    def is_invisible(self) -> bool:
        return (self.m_flags & const.INVISIBLE) != 0

    @property
    def is_asleep(self) -> bool:
        return (self.m_flags & const.ASLEEP) != 0

    @property
    def is_waking(self) -> bool:
        return (self.m_flags & const.WAKENS) != 0

    @property
    def is_wandering(self) -> bool:
        return (self.m_flags & const.WANDERS) != 0

    @property
    def is_flying(self) -> bool:
        return (self.m_flags & const.FLIES) != 0

    @property
    def is_flitting(self) -> bool:
        return (self.m_flags & const.FLITS) != 0

    @property
    def can_flit(self) -> bool:
        return (self.m_flags & const.CAN_FLIT) != 0

    @property
    def is_confused(self) -> bool:
        return (self.m_flags & const.CONFUSED) != 0

    @property
    def is_rusting(self) -> bool:
        return (self.m_flags & const.RUSTS) != 0

    @property
    def is_holding(self) -> bool:
        return (self.m_flags & const.HOLDS) != 0

    @property
    def is_freezing(self) -> bool:
        return (self.m_flags & const.FREEZES) != 0

    @property
    def is_stealing_gold(self) -> bool:
        return (self.m_flags & const.STEALS_GOLD) != 0

    @property
    def is_stealing_item(self) -> bool:
        return (self.m_flags & const.STEALS_ITEM) != 0

    @property
    def is_stinging(self) -> bool:
        return (self.m_flags & const.STINGS) != 0

    @property
    def is_draining_life(self) -> bool:
        return (self.m_flags & const.DRAINS_LIFE) != 0

    @property
    def is_dropping_level(self) -> bool:
        return (self.m_flags & const.DROPS_LEVEL) != 0

    @property
    def is_seeking_gold(self) -> bool:
        return (self.m_flags & const.SEEKS_GOLD) != 0

    @property
    def is_freezing_rogue(self) -> bool:
        return (self.m_flags & const.FREEZING_ROGUE) != 0

    @property
    def is_rust_vanished(self) -> bool:
        return (self.m_flags & const.RUST_VANISHED) != 0

    @property
    def is_confusing(self) -> bool:
        return (self.m_flags & const.CONFUSES) != 0

    @property
    def is_imitating(self) -> bool:
        return (self.m_flags & const.IMITATES) != 0

    @property
    def is_flaming(self) -> bool:
        return (self.m_flags & const.FLAMES) != 0

    @property
    def is_stationary(self) -> bool:
        return (self.m_flags & const.STATIONARY) != 0

    @property
    def is_napping(self) -> bool:
        return (self.m_flags & const.NAPPING) != 0

    @property
    def has_already_moved(self) -> bool:
        return (self.m_flags & const.ALREADY_MOVED) != 0

    @property
    def has_special_hit(self) -> bool:
        return (self.m_flags & const.SPECIAL_HIT) != 0

    # モンスターの表示文字（m_char プロパティ）
    @property
    def m_char(self) -> str:
        """モンスターの表示文字を文字列で取得"""
        return chr(self.ichar) if 0 <= self.ichar <= 0x10FFFF else '?'

    @m_char.setter
    def m_char(self, value: str) -> None:
        """モンスターの表示文字を設定（文字列または整数）"""
        if isinstance(value, str) and len(value) > 0:
            self.ichar = ord(value[0])
        elif isinstance(value, int):
            self.ichar = value
        else:
            self.ichar = ord('?')

    # モンスターのHP
    @property
    def hp(self) -> int:
        return self.quantity

    @hp.setter
    def hp(self, value: int):
        self.quantity = value

    # モンスターの出現レベル
    @property
    def level_min(self) -> int:
        return self.is_protected

    # モンスターの最大レベル
    @property
    def level_max(self) -> int:
        return self.is_cursed

    # モンスターの命中率
    @property
    def hit_chance(self) -> int:
        return self.class_

    @hit_chance.setter
    def hit_chance(self, value: int):
        self.class_ = value

    # モンスターのドロップ率
    @property
    def drop_percent(self) -> int:
        return self.which_kind

    @drop_percent.setter
    def drop_percent(self, value: int):
        self.which_kind = value

    # モンスターの偽装文字
    @property
    def disguise(self) -> int:
        return self.what_is

    @disguise.setter
    def disguise(self, value: int):
        self.what_is = value

    # モンスターの次のモンスター（リンクリスト）
    @property
    def next_monster(self) -> Optional['Monster']:
        return self.next_object

    @next_monster.setter
    def next_monster(self, value: Optional['Monster']):
        self.next_object = value

    # C版 #define エイリアス (rogue.h lines 185-198)
    # hp_to_kill = quantity (C: #define hp_to_kill quantity)
    @property
    def hp_to_kill(self) -> int:
        return self.quantity

    @hp_to_kill.setter
    def hp_to_kill(self, value: int):
        self.quantity = value

    # first_level = is_protected (C: #define first_level is_protected)
    @property
    def first_level(self) -> int:
        return self.is_protected

    @first_level.setter
    def first_level(self, value: int):
        self.is_protected = value

    # last_level = is_cursed (C: #define last_level is_cursed)
    @property
    def last_level(self) -> int:
        return self.is_cursed

    @last_level.setter
    def last_level(self, value: int):
        self.is_cursed = value

    # m_damage = damage (C: #define m_damage damage)
    @property
    def m_damage(self) -> str:
        return self.damage

    @m_damage.setter
    def m_damage(self, value: str):
        self.damage = value

    # stationary_damage = identified (C: #define stationary_damage identified)
    @property
    def stationary_damage(self) -> int:
        return self.identified

    @stationary_damage.setter
    def stationary_damage(self, value) -> None:
        if isinstance(value, int):
            self.identified = value
        else:
            try:
                self.identified = int(value)
            except (ValueError, TypeError):
                self.identified = 0

    # trail_char = d_enchant
    @property
    def trail_char(self) -> str:
        return chr(self.d_enchant) if 0 < self.d_enchant <= 0x10FFFF else (str(self.d_enchant) if self.d_enchant else '.')

    @trail_char.setter
    def trail_char(self, value) -> None:
        if isinstance(value, str) and len(value) > 0:
            self.d_enchant = ord(value[0])
        elif isinstance(value, int):
            self.d_enchant = value
        else:
            self.d_enchant = ord('.')

    # slowed_toggle = quiver
    @property
    def slowed_toggle(self) -> int:
        return self.quiver

    @slowed_toggle.setter
    def slowed_toggle(self, value: int) -> None:
        self.quiver = value

    # moves_confused = hit_enchant
    @property
    def moves_confused(self) -> int:
        return self.hit_enchant

    @moves_confused.setter
    def moves_confused(self, value: int) -> None:
        self.hit_enchant = value

    # nap_length = picked_up
    @property
    def nap_length(self) -> int:
        return self.picked_up

    @nap_length.setter
    def nap_length(self, value: int) -> None:
        self.picked_up = value


# モンスターデータ表 (monster.c より)
MON_TAB = [
    # flags, damage, hp, char, exp, first_level, last_level, hit_chance, drop_percent
    {"flags": (const.ASLEEP | const.WAKENS | const.WANDERS | const.RUSTS), "damage": "0d0", "hp": 25, "ichar": 'A', "exp": 20, "first": 9, "last": 18, "hit": 100, "drop": 0},
    {"flags": (const.ASLEEP | const.WANDERS | const.FLITS), "damage": "1d3", "hp": 10, "ichar": 'B', "exp": 2, "first": 1, "last": 8, "hit": 60, "drop": 0},
    {"flags": (const.ASLEEP | const.WANDERS), "damage": "3d3/2d5", "hp": 32, "ichar": 'C', "exp": 15, "first": 7, "last": 16, "hit": 85, "drop": 10},
    {"flags": (const.ASLEEP | const.WAKENS | const.FLAMES), "damage": "4d6/4d9", "hp": 145, "ichar": 'D', "exp": 5000, "first": 21, "last": 126, "hit": 100, "drop": 90},
    {"flags": (const.ASLEEP | const.WAKENS), "damage": "1d3", "hp": 11, "ichar": 'E', "exp": 2, "first": 1, "last": 7, "hit": 65, "drop": 0},
    {"flags": (const.HOLDS | const.STATIONARY), "damage": "5d5", "hp": 73, "ichar": 'F', "exp": 91, "first": 12, "last": 126, "hit": 80, "drop": 0},
    {"flags": (const.ASLEEP | const.WAKENS | const.WANDERS | const.FLIES), "damage": "5d5/5d5", "hp": 115, "ichar": 'G', "exp": 2000, "first": 20, "last": 126, "hit": 85, "drop": 10},
    {"flags": (const.ASLEEP | const.WAKENS | const.WANDERS), "damage": "1d3/1d2", "hp": 15, "ichar": 'H', "exp": 3, "first": 1, "last": 10, "hit": 67, "drop": 0},
    {"flags": (const.ASLEEP | const.FREEZES), "damage": "0d0", "hp": 15, "ichar": 'I', "exp": 5, "first": 2, "last": 11, "hit": 68, "drop": 0},
    {"flags": (const.ASLEEP | const.WANDERS), "damage": "3d10/4d5", "hp": 132, "ichar": 'J', "exp": 3000, "first": 21, "last": 126, "hit": 100, "drop": 0},
    {"flags": (const.ASLEEP | const.WAKENS | const.WANDERS | const.FLIES), "damage": "1d4", "hp": 10, "ichar": 'K', "exp": 2, "first": 1, "last": 6, "hit": 60, "drop": 0},
    {"flags": (const.ASLEEP | const.STEALS_GOLD), "damage": "0d0", "hp": 25, "ichar": 'L', "exp": 21, "first": 6, "last": 16, "hit": 75, "drop": 0},
    {"flags": (const.ASLEEP | const.WAKENS | const.WANDERS | const.CONFUSES), "damage": "4d4/3d7", "hp": 97, "ichar": 'M', "exp": 250, "first": 18, "last": 126, "hit": 85, "drop": 25},
    {"flags": (const.ASLEEP | const.STEALS_ITEM), "damage": "0d0", "hp": 25, "ichar": 'N', "exp": 39, "first": 10, "last": 19, "hit": 75, "drop": 100},
    {"flags": (const.ASLEEP | const.WANDERS | const.WAKENS | const.SEEKS_GOLD), "damage": "1d6", "hp": 25, "ichar": 'O', "exp": 5, "first": 4, "last": 13, "hit": 70, "drop": 10},
    {"flags": (const.ASLEEP | const.INVISIBLE | const.WANDERS | const.FLITS), "damage": "5d4", "hp": 76, "ichar": 'P', "exp": 120, "first": 15, "last": 24, "hit": 80, "drop": 50},
    {"flags": (const.ASLEEP | const.WAKENS | const.WANDERS), "damage": "3d5", "hp": 30, "ichar": 'Q', "exp": 20, "first": 8, "last": 17, "hit": 78, "drop": 20},
    {"flags": (const.ASLEEP | const.WAKENS | const.WANDERS | const.STINGS), "damage": "2d5", "hp": 19, "ichar": 'R', "exp": 10, "first": 3, "last": 12, "hit": 70, "drop": 0},
    {"flags": (const.ASLEEP | const.WAKENS | const.WANDERS), "damage": "1d3", "hp": 8, "ichar": 'S', "exp": 2, "first": 1, "last": 9, "hit": 50, "drop": 0},
    {"flags": (const.ASLEEP | const.WAKENS | const.WANDERS), "damage": "4d6/1d4", "hp": 75, "ichar": 'T', "exp": 125, "first": 13, "last": 22, "hit": 75, "drop": 33},
    {"flags": (const.ASLEEP | const.WAKENS | const.WANDERS), "damage": "4d10", "hp": 90, "ichar": 'U', "exp": 200, "first": 17, "last": 26, "hit": 85, "drop": 33},
    {"flags": (const.ASLEEP | const.WAKENS | const.WANDERS | const.DRAINS_LIFE), "damage": "1d14/1d4", "hp": 55, "ichar": 'V', "exp": 350, "first": 19, "last": 126, "hit": 85, "drop": 18},
    {"flags": (const.ASLEEP | const.WANDERS | const.DROPS_LEVEL), "damage": "2d8", "hp": 45, "ichar": 'W', "exp": 55, "first": 14, "last": 23, "hit": 75, "drop": 0},
    {"flags": (const.ASLEEP | const.IMITATES), "damage": "4d6", "hp": 42, "ichar": 'X', "exp": 110, "first": 16, "last": 25, "hit": 75, "drop": 0},
    {"flags": (const.ASLEEP | const.WANDERS), "damage": "3d6", "hp": 35, "ichar": 'Y', "exp": 50, "first": 11, "last": 20, "hit": 80, "drop": 20},
    {"flags": (const.ASLEEP | const.WAKENS | const.WANDERS), "damage": "1d7", "hp": 21, "ichar": 'Z', "exp": 8, "first": 5, "last": 14, "hit": 69, "drop": 0}
]

# モンスター名 (src/mesg より)
M_NAMES = [
    "水ごけの怪物", "大こうもり", "ケンタウロス", "ドラゴン", "大うずら", "はえとりぐさ",
    "翼ライオン", "小鬼", "氷の怪物", "巨大トカゲ",
    "大はやぶさ", "金持ち妖精", "メデューサ", "ニンフ", "欲ばり鬼", "幽霊",
    "大つのじか", "がらがらへび", "へび", "巨人", "一角獣",
    "バンパイア", "死霊", "物まねの怪物", "雪男", "ゾンビ"
]

def create_monster(mn: int) -> Monster:
    """指定したインデックスのモンスターを作成"""
    data = MON_TAB[mn]
    m = Monster()
    m.m_flags = data["flags"]
    m.damage = data["damage"]
    m.quantity = data["hp"]  # quantityをHPとして使用
    m.hp = data["hp"]
    m.ichar = ord(data["ichar"])
    m.kill_exp = data["exp"]
    m.is_protected = data["first"] # 出現レベル
    m.is_cursed = data["last"] # 最大レベル
    m.class_ = data["hit"] # 命中率
    m.which_kind = data["drop"] # ドロップ率
    m.name = M_NAMES[mn]  # 名前をセット
    return m


# ============================================================================
# プレイヤークラス (struct fight)
# ============================================================================

@dataclass
class Player:
    """プレイヤークラス（元のC言語ではstruct fighter）"""

    # 装備
    armor: Optional[Item] = None
    weapon: Optional[Item] = None
    left_ring: Optional[Item] = None
    right_ring: Optional[Item] = None

    # ステータス
    hp_current: int = const.INIT_HP
    hp_max: int = const.INIT_HP
    str_current: int = 16
    str_max: int = 16

    # インベントリ（packはアイテムのリンクリスト）
    pack: Optional[Item] = None

    # 所持金と経験値
    gold: int = 0
    exp: int = 1
    exp_points: int = 0

    # 位置
    row: int = 0
    col: int = 0

    # 表示文字
    fchar: int = ord('@')

    # 残り移動回数（空腹度、C版 rogue.h: 1250）
    # moves_left <= HUNGRY (300): 空腹状態
    # moves_left <= WEAK (150): 弱り状態
    # moves_left <= FAINT (20): 気絶状態
    # moves_left <= STARVE (0): 餓死
    moves_left: int = 1250

    # レベル
    dungeon_level: int = 1

    # 注意: 状態フラグ（blind, confused, halluc等）はC言語版と同様にグローバル変数で管理
    # 詳細は use_actions.py を参照

    def next_avail_ichar(self) -> str:
        """利用可能なインベントリ文字（a-z）を取得"""
        ichars = [False] * 26
        curr = self.pack
        while curr:
            if 'a' <= chr(curr.ichar) <= 'z':
                ichars[curr.ichar - ord('a')] = True
            curr = curr.next_object
        
        for i in range(26):
            if not ichars[i]:
                return chr(ord('a') + i)
        return '?'

    @property
    def is_hungry(self) -> bool:
        """空腹状態かどうか（C言語版: moves_left <= HUNGRY）"""
        return self.moves_left <= const.HUNGRY

    @property
    def is_weak(self) -> bool:
        """弱り状態かどうか（C言語版: moves_left <= WEAK）"""
        return self.moves_left <= const.WEAK

    @property
    def is_fainting(self) -> bool:
        """気絶状態かどうか（C言語版: moves_left <= FAINT）"""
        return self.moves_left <= const.FAINT

    @property
    def is_starving(self) -> bool:
        """餓死状態かどうか（C言語版: moves_left <= STARVE）"""
        return self.moves_left <= const.STARVE

    @property
    def is_dead(self) -> bool:
        return self.hp_current <= 0

    # レベルアップに必要な経験値テーブル (C版 level.c: level_points[])
    LEVEL_POINTS = [
        10, 20, 40, 80, 160, 320, 640, 1300, 2600, 5200,
        10000, 20000, 40000, 80000, 160000, 320000, 1000000, 3333333,
        6666666, const.MAX_EXP, 99900000
    ]

    def add_exp(self, amount: int, promotion: bool = True) -> List[int]:
        """経験値を追加 (C版 level.c: add_exp)

        経験値ポイントを加算し、レベルアップ判定を行う。
        promotion=True の場合、レベルアップ時にHPが増加する。
        レベルアップした新しいレベル番号のリストを返す。
        """
        try:
            from .game_state import GameState
        except ImportError:
            from game_state import GameState

        self.exp_points += amount

        new_levels = []
        old_exp = self.exp

        if self.exp > 0 and self.exp <= len(Player.LEVEL_POINTS):
            if self.exp_points >= Player.LEVEL_POINTS[self.exp - 1]:
                new_exp = self.get_exp_level(self.exp_points)
                if self.exp_points > const.MAX_EXP:
                    self.exp_points = const.MAX_EXP + 1
                for i in range(old_exp + 1, new_exp + 1):
                    new_levels.append(i)
                    if promotion:
                        hp = 10 if GameState.wizard else utils.get_rand(3, 10)
                        self.hp_current += hp
                        self.hp_max += hp
                    self.exp = i

        return new_levels

    @staticmethod
    def get_exp_level(exp_points: int) -> int:
        """経験値ポイントからレベルを計算 (C版 level.c: get_exp_level)"""
        for i in range(len(Player.LEVEL_POINTS) - 1):
            if Player.LEVEL_POINTS[i] > exp_points:
                return i + 1
        return len(Player.LEVEL_POINTS)

    def heal(self, amount: int) -> None:
        """HPを回復"""
        self.hp_current = min(self.hp_max + amount, const.MAX_HP)

    def damage(self, amount: int) -> None:
        """ダメージを受ける"""
        self.hp_current -= amount
        if self.hp_current < 0:
            self.hp_current = 0

    def get_armor_class(self) -> int:
        """防具クラスを取得 (C版 object.c: get_armor_class)"""
        # C: return(obj ? obj->class + obj->d_enchant : 0);
        if self.armor is None:
            return 0
        return self.armor.class_ + self.armor.d_enchant


# ============================================================================
# ドアクラス (struct dr)
# ============================================================================

@dataclass
class Door:
    """ドアクラス"""
    oth_room: int = const.NO_ROOM  # 向かいの部屋
    oth_row: int = 0  # 向かいの部屋の行
    oth_col: int = 0  # 向かいの部屋の列
    door_row: int = 0  # ドアの行
    door_col: int = 0  # ドアの列


# ============================================================================
# ルームクラス (struct rm)
# ============================================================================

@dataclass
class Room:
    """ルームクラス"""
    bottom_row: int = 0
    right_col: int = 0
    left_col: int = 0
    top_row: int = 0
    # doors[0]: 上方向, doors[1]: 右方向, doors[2]: 下方向, doors[3]: 左方向
    doors: List[Door] = field(default_factory=lambda: [Door() for _ in range(4)])
    is_room: int = const.R_NOTHING

    @property
    def width(self) -> int:
        return self.right_col - self.left_col + 1

    @property
    def height(self) -> int:
        return self.bottom_row - self.top_row + 1

    @property
    def center_row(self) -> int:
        return (self.top_row + self.bottom_row) // 2

    @property
    def center_col(self) -> int:
        return (self.left_col + self.right_col) // 2

    def contains(self, row: int, col: int) -> bool:
        """指定した座標がルーム内にあるか"""
        return (self.top_row <= row <= self.bottom_row and
                self.left_col <= col <= self.right_col)


# ============================================================================
# 罠クラス (struct tr)
# ============================================================================

@dataclass
class Trap:
    """罠クラス"""
    trap_type: int = const.NO_TRAP
    trap_row: int = 0
    trap_col: int = 0

    @property
    def is_trap_door(self) -> bool:
        return self.trap_type == const.TRAP_DOOR

    @property
    def is_bear_trap(self) -> bool:
        return self.trap_type == const.BEAR_TRAP

    @property
    def is_tele_trap(self) -> bool:
        return self.trap_type == const.TELE_TRAP

    @property
    def is_dart_trap(self) -> bool:
        return self.trap_type == const.DART_TRAP

    @property
    def is_sleeping_gas_trap(self) -> bool:
        return self.trap_type == const.SLEEPING_GAS_TRAP

    @property
    def is_rust_trap(self) -> bool:
        return self.trap_type == const.RUST_TRAP


# ============================================================================
# 時間クラス (struct rogue_time)
# ============================================================================

@dataclass
class GameTime:
    """ゲーム時間クラス"""
    year: int = 1987
    month: int = 1
    day: int = 1
    hour: int = 0
    minute: int = 0
    second: int = 0

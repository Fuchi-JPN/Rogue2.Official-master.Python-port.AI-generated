"""
dungeon.py - Rogue2.Official C to Python 移植
ダンジョンレベルとマップデータ構造

元ファイル: src/level.h, src/room.h, src/rogue.h
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

try:
    from . import const
    from .entities import Room, Door, Trap, Monster, Item
except ImportError:
    import const
    import entities
    Room = entities.Room
    Door = entities.Door
    Trap = entities.Trap
    Monster = entities.Monster
    Item = entities.Item


# ============================================================================
# ダンジョンレベルクラス
# ============================================================================

@dataclass
class DungeonLevel:
    """
    ダンジョンレベルクラス
    2次元配列（リストのリスト）でグリッド（壁、床、通路）を表現
    """
    # レベル番号
    level: int = 1

    # ダンジョンマップ（2次元配列）
    # dungeon[row][col] でアクセス
    dungeon: List[List[int]] = field(default_factory=lambda: [
        [const.NOTHING for _ in range(const.ROGUE_COLUMNS)]
        for _ in range(const.ROGUE_LINES)
    ])

    # 説明文字配列（表示用）
    descs: List[List[str]] = field(default_factory=lambda: [
        [' ' for _ in range(const.ROGUE_COLUMNS)]
        for _ in range(const.ROGUE_LINES)
    ])

    # 部屋リスト
    rooms: List[Room] = field(default_factory=list)

    # 罠リスト
    traps: List[Trap] = field(default_factory=list)

    # モンスターリスト（C言語版のlevel_monsters.next_monster連結リストに相当）
    monsters: List[Monster] = field(default_factory=list)

    # レベル上のオブジェクト（アイテム）
    level_objects: Optional[Item] = None
    level_monsters: Optional[Monster] = None

    # 階段の位置
    stairs_row: int = 0
    stairs_col: int = 0

    # アミュレットの位置（最下層のみ）
    amulet_row: int = 0
    amulet_col: int = 0
    has_amulet: bool = False

    # ゴールドの総量
    total_gold: int = 0

    def __post_init__(self):
        """初期化後の処理"""
        # 部屋リストを初期化
        if not self.rooms:
            self.rooms = [Room() for _ in range(const.MAXROOMS)]

    def is_valid_position(self, row: int, col: int) -> bool:
        """座標が有効かどうかを判定"""
        return (0 <= row < const.ROGUE_LINES and
                0 <= col < const.ROGUE_COLUMNS)

    def get_tile(self, row: int, col: int) -> int:
        """指定した座標のタイルタイプを取得"""
        if not self.is_valid_position(row, col):
            return const.HORWALL
        return self.dungeon[row][col]

    def set_tile(self, row: int, col: int, tile_type: int) -> None:
        """指定した座標のタイルタイプを設定"""
        if self.is_valid_position(row, col):
            self.dungeon[row][col] = tile_type

    def get_desc(self, row: int, col: int) -> str:
        """指定した座標の説明文字を取得"""
        if not self.is_valid_position(row, col):
            return ' '
        return self.descs[row][col]

    def set_desc(self, row: int, col: int, desc: str) -> None:
        """指定した座標の説明文字を設定"""
        if self.is_valid_position(row, col):
            self.descs[row][col] = desc

    def is_floor(self, row: int, col: int) -> bool:
        """床かどうかを判定"""
        tile = self.get_tile(row, col)
        return const.is_floor(tile) or const.is_door(tile) or const.is_stairs(tile)

    def is_wall(self, row: int, col: int) -> bool:
        """壁かどうかを判定"""
        tile = self.get_tile(row, col)
        return const.is_wall(tile)

    def is_door(self, row: int, col: int) -> bool:
        """ドアかどうかを判定"""
        tile = self.get_tile(row, col)
        return const.is_door(tile)

    def is_tunnel(self, row: int, col: int) -> bool:
        """通路かどうかを判定"""
        tile = self.get_tile(row, col)
        return const.is_tunnel(tile)

    def is_trap(self, row: int, col: int) -> bool:
        """罠があるかどうかを判定"""
        tile = self.get_tile(row, col)
        return const.is_trap(tile)

    def is_stairs(self, row: int, col: int) -> bool:
        """階段かどうかを判定"""
        tile = self.get_tile(row, col)
        return const.is_stairs(tile)

    def get_room_number(self, row: int, col: int) -> int:
        """座標が含まれる部屋番号を取得"""
        for i, room in enumerate(self.rooms):
            if room.contains(row, col):
                return i
        return const.NO_ROOM

    def get_room(self, room_number: int) -> Optional[Room]:
        """部屋番号から部屋を取得"""
        if 0 <= room_number < len(self.rooms):
            return self.rooms[room_number]
        return None

    def add_room(self, room: Room) -> None:
        """部屋を追加"""
        if len(self.rooms) < const.MAXROOMS:
            self.rooms.append(room)

    def add_trap(self, trap: Trap) -> None:
        """罠を追加"""
        if len(self.traps) < const.MAX_TRAPS:
            self.traps.append(trap)

    def get_trap_at(self, row: int, col: int) -> Optional[Trap]:
        """指定した座標の罠を取得"""
        for trap in self.traps:
            if trap.trap_row == row and trap.trap_col == col:
                return trap
        return None

    def clear(self) -> None:
        """レベルをクリア"""
        # マップを空で埋める
        for row in range(const.ROGUE_LINES):
            for col in range(const.ROGUE_COLUMNS):
                self.dungeon[row][col] = const.NOTHING
                self.descs[row][col] = ' '

        # 部屋をリセット
        self.rooms = [Room() for _ in range(const.MAXROOMS)]

        # 罠をクリア
        self.traps = []

        # オブジェクトとモンスターをクリア
        self.level_objects = None
        self.level_monsters = None
        self.monsters = []

        # 階段とアミュレットをリセット
        self.stairs_row = 0
        self.stairs_col = 0
        self.amulet_row = 0
        self.amulet_col = 0
        self.has_amulet = False

        # ゴールドをリセット
        self.total_gold = 0


# ============================================================================
# ダンジョンマネージャークラス
# ============================================================================

@dataclass
class DungeonManager:
    """ダンジョンマネージャークラス"""

    # 現在のレベル
    current_level: int = 1

    # 各レベルのダンジョン（必要に応じてキャッシュ）
    levels: dict[int, DungeonLevel] = field(default_factory=dict)

    # 現在のダンジョンレベル
    current_dungeon: Optional[DungeonLevel] = None

    def __post_init__(self):
        """初期化後の処理"""
        if self.current_dungeon is None:
            self.current_dungeon = DungeonLevel(level=self.current_level)

    def get_current_level(self) -> DungeonLevel:
        """現在のレベルを取得"""
        if self.current_dungeon is None:
            self.current_dungeon = DungeonLevel(level=self.current_level)
        return self.current_dungeon

    def set_current_level(self, level: int) -> None:
        """現在のレベルを設定"""
        self.current_level = level
        if level in self.levels:
            self.current_dungeon = self.levels[level]
        else:
            self.current_dungeon = DungeonLevel(level=level)
            self.levels[level] = self.current_dungeon

    def save_level(self, level: int, dungeon: DungeonLevel) -> None:
        """レベルを保存"""
        self.levels[level] = dungeon

    def load_level(self, level: int) -> Optional[DungeonLevel]:
        """レベルをロード"""
        return self.levels.get(level)

    def clear_all_levels(self) -> None:
        """すべてのレベルをクリア"""
        self.levels.clear()
        self.current_level = 1
        self.current_dungeon = DungeonLevel(level=1)

    def is_amulet_level(self) -> bool:
        """アミュレットがあるレベルかどうかを判定"""
        return self.current_level >= const.AMULET_LEVEL


# ============================================================================
# ユーティリティ関数
# ============================================================================

def get_direction_offset(direction: int) -> Tuple[int, int]:
    """
    方向から座標オフセットを取得
    direction: 0=UP, 1=UPRIGHT, 2=RIGHT, 3=RIGHTDOWN,
              4=DOWN, 5=DOWNLEFT, 6=LEFT, 7=LEFTUP
    """
    offsets = [
        (-1, 0),   # UPWARD
        (-1, 1),   # UPRIGHT
        (0, 1),    # RIGHT
        (1, 1),    # RIGHTDOWN
        (1, 0),    # DOWN
        (1, -1),   # DOWNLEFT
        (0, -1),   # LEFT
        (-1, -1),  # LEFTUP
    ]
    if 0 <= direction < len(offsets):
        return offsets[direction]
    return (0, 0)


def get_room_number(dungeon: DungeonLevel, row: int, col: int) -> int:
    """
    座標が含まれる部屋番号を取得（スタンドアロン関数）
    
    C言語版との互換性のために用意された関数。
    DungeonLevel.get_room_number()メソッドと同等の機能を提供する。
    """
    return dungeon.get_room_number(row, col)


def get_opposite_direction(direction: int) -> int:
    """反対方向を取得"""
    return (direction + 4) % 8


def is_adjacent(row1: int, col1: int, row2: int, col2: int) -> bool:
    """2つの座標が隣接しているかどうかを判定"""
    return abs(row1 - row2) <= 1 and abs(col1 - col2) <= 1


def distance(row1: int, col1: int, row2: int, col2: int) -> int:
    """2つの座標間のマンハッタン距離を計算"""
    return abs(row1 - row2) + abs(col1 - col2)


def euclidean_distance(row1: int, col1: int, row2: int, col2: int) -> float:
    """2つの座標間のユークリッド距離を計算"""
    return ((row1 - row2) ** 2 + (col1 - col2) ** 2) ** 0.5


def clamp(value: int, min_value: int, max_value: int) -> int:
    """値を範囲内にクランプ"""
    return max(min_value, min(value, max_value))


def clamp_row(row: int) -> int:
    """行を有効範囲内にクランプ"""
    return clamp(row, 0, const.ROGUE_LINES - 1)


def clamp_col(col: int) -> int:
    """列を有効範囲内にクランプ"""
    return clamp(col, 0, const.ROGUE_COLUMNS - 1)


def is_in_bounds(row: int, col: int) -> bool:
    """座標がマップ境界内にあるかどうかを判定"""
    return 0 <= row < const.ROGUE_LINES and 0 <= col < const.ROGUE_COLUMNS


def is_in_dungeon(row: int, col: int) -> bool:
    """座標がダンジョン内（壁以外）にあるかどうかを判定"""
    return is_in_bounds(row, col) and row >= const.MIN_ROW

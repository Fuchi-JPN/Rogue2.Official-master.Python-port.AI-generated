"""
level_generator.py - Rogue2.Official C to Python 移植
レベル生成ロジック

元ファイル: src/level.c, src/room.c
"""

import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

try:
    from . import const
    from . import dungeon
    from . import entities
    from . import utils
except ImportError:
    import const
    import dungeon
    import entities
    import utils


# ============================================================================
# 経験値レベルテーブル
# ============================================================================

LEVEL_POINTS = [
    10, 20, 40, 80, 160, 320, 640, 1300, 2600, 5200,
    10000, 20000, 40000, 80000, 160000, 320000, 1000000,
    3333333, 6666666, const.MAX_EXP, 99900000
]

# ランダム部屋順序
RANDOM_ROOMS = [3, 7, 5, 2, 0, 6, 1, 4, 8]


# ============================================================================
# LevelGeneratorクラス - レベル生成
# ============================================================================

class LevelGenerator:
    """レベル生成クラス"""

    def __init__(self, dungeon_level: dungeon.DungeonLevel, cur_level: Optional[int] = None):
        """初期化"""
        self.dungeon_level = dungeon_level
        self.cur_level = cur_level if cur_level is not None else dungeon_level.level
        self.max_level = self.cur_level
        self.cur_room = const.NO_ROOM
        self.party_room = const.NO_ROOM
        self.r_de = const.NO_ROOM  # C言語版の静的変数 r_de に相当
        self.party_counter = 0
        self.rooms_visited: List[bool] = [False] * const.MAXROOMS

    def make_level(self) -> None:
        """レベルを生成"""
        # レベルをインクリメント
        if self.cur_level < const.LAST_DUNGEON:
            self.cur_level += 1
            self.dungeon_level.level = self.cur_level

        if self.cur_level > self.max_level:
            self.max_level = self.cur_level

        # 必須部屋を決定
        must_exist1 = utils.get_rand(0, 2)
        vertical = utils.coin_toss()
        if vertical:
            must_exist3 = (must_exist2 := must_exist1 + 3) + 3
        else:
            must_exist3 = (must_exist2 := (must_exist1 * 3) + 1) + 1

        # ビッグルームを生成するか判定
        big_room = (self.cur_level == self.party_counter) and utils.rand_percent(1)

        if big_room:
            self._make_room(const.BIG_ROOM, 0, 0, 0)
        else:
            for i in range(const.MAXROOMS):
                self._make_room(i, must_exist1, must_exist2, must_exist3)

        if not big_room:
            # 迷宮を追加
            self._add_mazes()

            # 部屋順序をシャッフル
            self._mix_random_rooms()

            # 部屋を接続
            for j in range(const.MAXROOMS):
                i = RANDOM_ROOMS[j]

                if i < (const.MAXROOMS - 1):
                    self._connect_rooms(i, i + 1)
                if i < (const.MAXROOMS - 3):
                    self._connect_rooms(i, i + 3)
                if i < (const.MAXROOMS - 2):
                    if (self.dungeon_level.rooms[i + 1].is_room & const.R_NOTHING) and \
                       (i + 1 != 4 or vertical):
                        if self._connect_rooms(i, i + 2):
                            self.dungeon_level.rooms[i + 1].is_room = const.R_CROSS
                if i < (const.MAXROOMS - 6):
                    if (self.dungeon_level.rooms[i + 3].is_room & const.R_NOTHING) and \
                       (i + 3 != 4 or not vertical):
                        if self._connect_rooms(i, i + 6):
                            self.dungeon_level.rooms[i + 3].is_room = const.R_CROSS

                if self._is_all_connected():
                    break

            # レベルを埋める
            self._fill_out_level()

        # アミュレットを配置
        if not self.dungeon_level.has_amulet and self.cur_level >= const.AMULET_LEVEL:
            self._put_amulet()

    def _make_room(self, rn: int, r1: int, r2: int, r3: int) -> None:
        """部屋を作成"""
        left_col, right_col, top_row, bottom_row = 0, 0, 0, 0
        width, height = 0, 0
        row_offset, col_offset = 0, 0

        if rn == const.BIG_ROOM:
            top_row = utils.get_rand(const.MIN_ROW, const.MIN_ROW + 5)
            bottom_row = utils.get_rand(const.ROGUE_LINES - 7, const.ROGUE_LINES - 2)
            left_col = utils.get_rand(0, 10)
            right_col = utils.get_rand(const.ROGUE_COLUMNS - 11, const.ROGUE_COLUMNS - 2)
            rn = 0
        else:
            # 列セクターを決定
            if rn % 3 == 0:
                left_col = 0
                right_col = const.COL1 - 1
            elif rn % 3 == 1:
                left_col = const.COL1 + 1
                right_col = const.COL2 - 1
            else:
                left_col = const.COL2 + 1
                right_col = const.ROGUE_COLUMNS - 2

            # 行セクターを決定
            if rn // 3 == 0:
                top_row = const.MIN_ROW
                bottom_row = const.ROW1 - 1
            elif rn // 3 == 1:
                top_row = const.ROW1 + 1
                bottom_row = const.ROW2 - 1
            else:
                top_row = const.ROW2 + 1
                bottom_row = const.ROGUE_LINES - 2

            height = utils.get_rand(4, (bottom_row - top_row + 1))
            width = utils.get_rand(7, (right_col - left_col - 2))

            row_offset = utils.get_rand(0, ((bottom_row - top_row) - height + 1))
            col_offset = utils.get_rand(0, ((right_col - left_col) - width + 1))

            top_row += row_offset
            bottom_row = top_row + height - 1
            left_col += col_offset
            right_col = left_col + width - 1

            # 必須部屋でない場合は確率でスキップ
            if (rn != r1) and (rn != r2) and (rn != r3) and utils.rand_percent(40):
                self.dungeon_level.rooms[rn].top_row = top_row
                self.dungeon_level.rooms[rn].bottom_row = bottom_row
                self.dungeon_level.rooms[rn].left_col = left_col
                self.dungeon_level.rooms[rn].right_col = right_col
                return

        # 部屋を描画
        self.dungeon_level.rooms[rn].is_room = const.R_ROOM

        for i in range(top_row, bottom_row + 1):
            for j in range(left_col, right_col + 1):
                if i == top_row or i == bottom_row:
                    ch = const.HORWALL
                elif j == left_col or j == right_col:
                    ch = const.VERTWALL
                else:
                    ch = const.FLOOR
                self.dungeon_level.set_tile(i, j, ch)

        self.dungeon_level.rooms[rn].top_row = top_row
        self.dungeon_level.rooms[rn].bottom_row = bottom_row
        self.dungeon_level.rooms[rn].left_col = left_col
        self.dungeon_level.rooms[rn].right_col = right_col

    def _connect_rooms(self, room1: int, room2: int) -> bool:
        """部屋を通路で接続"""
        logger.debug(f"Attempting to connect room {room1} and {room2}")
        row1, col1, row2, col2 = 0, 0, 0, 0
        dir, rev = 0, 0

        valid_rooms = const.R_ROOM | const.R_MAZE | const.R_DEADEND | const.R_CROSS
        if not (self.dungeon_level.rooms[room1].is_room & valid_rooms):
            logger.debug(f"Room {room1} is not a valid room/maze (type: {self.dungeon_level.rooms[room1].is_room})")
            return False
        if not (self.dungeon_level.rooms[room2].is_room & valid_rooms):
            logger.debug(f"Room {room2} is not a valid room/maze (type: {self.dungeon_level.rooms[room2].is_room})")
            return False

        if self._same_row(room1, room2):
            if self.dungeon_level.rooms[room1].left_col > self.dungeon_level.rooms[room2].right_col:
                dir = const.LEFT
                rev = const.RIGHT
            else:
                dir = const.RIGHT
                rev = const.LEFT
        elif self._same_col(room1, room2):
            if self.dungeon_level.rooms[room1].top_row > self.dungeon_level.rooms[room2].bottom_row:
                dir = const.UPWARD
                rev = const.DOWN
            else:
                dir = const.DOWN
                rev = const.UPWARD
        else:
            return False

        r1, c1 = self._put_door(room1, dir)
        r2, c2 = self._put_door(room2, rev)

        # 座標を更新
        row1, col1 = r1, c1
        row2, col2 = r2, c2

        # 通路を描画
        self._draw_simple_passage(row1, col1, row2, col2, dir)
        # 確率で迷路風に追加
        while utils.rand_percent(4):
            self._draw_simple_passage(row1, col1, row2, col2, dir)

        # ドア情報を設定
        dp = self.dungeon_level.rooms[room1].doors[dir // 2]
        dp.oth_room = room2
        dp.oth_row = row2
        dp.oth_col = col2

        dp = self.dungeon_level.rooms[room2].doors[((dir + 4) % const.DIRS) // 2]
        dp.oth_room = room1
        dp.oth_row = row1
        dp.oth_col = col1

        return True

    def _put_door(self, room_num: int, direction: int) -> Tuple[int, int]:
        """ドアを配置"""
        room = self.dungeon_level.rooms[room_num]
        wall_width = 0 if (room.is_room & const.R_MAZE) else 1

        if direction == const.UPWARD or direction == const.DOWN:
            row = room.top_row if direction == const.UPWARD else room.bottom_row
            # 最大100回試行して有効な位置を見つける
            for _ in range(100):
                col = utils.get_rand(room.left_col + wall_width, room.right_col - wall_width)
                tile = self.dungeon_level.get_tile(row, col)
                if tile & (const.HORWALL | const.TUNNEL):
                    break
            else:
                # 有効な位置が見つからない場合は中央を使用
                col = (room.left_col + room.right_col) // 2
        else:  # LEFT or RIGHT
            col = room.left_col if direction == const.LEFT else room.right_col
            # 最大100回試行して有効な位置を見つける
            for _ in range(100):
                row = utils.get_rand(room.top_row + wall_width, room.bottom_row - wall_width)
                tile = self.dungeon_level.get_tile(row, col)
                if tile & (const.VERTWALL | const.TUNNEL):
                    break
            else:
                # 有効な位置が見つからない場合は中央を使用
                row = (room.top_row + room.bottom_row) // 2

        if room.is_room & const.R_ROOM:
            self.dungeon_level.set_tile(row, col, const.DOOR)

        if self.cur_level > 2 and utils.rand_percent(const.HIDE_PERCENT):
            tile = self.dungeon_level.get_tile(row, col)
            self.dungeon_level.set_tile(row, col, tile | const.HIDDEN)

        room.doors[direction // 2].door_row = row
        room.doors[direction // 2].door_col = col

        return row, col

    def _draw_simple_passage(self, row1: int, col1: int, row2: int, col2: int, direction: int) -> None:
        """単純な通路を描画"""
        logger.debug(f"Drawing passage: From({row1}, {col1}) To({row2}, {col2}) Dir:{direction}")
        if direction == const.LEFT or direction == const.RIGHT:
            # 水平方向の接続
            if col1 > col2:
                row1, row2 = row2, row1
                col1, col2 = col2, col1
            
            # 中間点を決定
            middle_col = utils.get_rand(col1 + 1, col2 - 1)
            
            # 隣接している場合の調整
            if middle_col > col2 - 1: middle_col = col2 - 1
            if middle_col < col1 + 1: middle_col = col1 + 1
            if col2 - col1 <= 1: middle_col = col1 # 隣接時は始点か終点を使用
            
            logger.debug(f"Horizontal passage middle_col: {middle_col}")

            # セグメント1: 水平 (col1 -> middle)
            for i in range(col1 + 1, middle_col + 1):
                logger.debug(f"Setting TUNNEL at ({row1}, {i})")
                self.dungeon_level.set_tile(row1, i, const.TUNNEL)
                
            # セグメント2: 垂直 (row1 -> row2 at middle)
            start_r, end_r = min(row1, row2), max(row1, row2)
            for i in range(start_r, end_r + 1):
                if i == row1 and i == row2: continue # 両端が同じ行なら何もしない（ありえないが）
                logger.debug(f"Setting TUNNEL at ({i}, {middle_col})")
                self.dungeon_level.set_tile(i, middle_col, const.TUNNEL)

            # セグメント3: 水平 (middle -> col2)
            for i in range(middle_col, col2):
                if i == col1: continue # 始点は上書きしない
                logger.debug(f"Setting TUNNEL at ({row2}, {i})")
                self.dungeon_level.set_tile(row2, i, const.TUNNEL)

        else:  # UPWARD or DOWN
            # 垂直方向の接続
            if row1 > row2:
                row1, row2 = row2, row1
                col1, col2 = col2, col1
            
            # 中間点を決定
            middle_row = utils.get_rand(row1 + 1, row2 - 1)
            
            # 隣接している場合の調整
            if middle_row > row2 - 1: middle_row = row2 - 1
            if middle_row < row1 + 1: middle_row = row1 + 1
            if row2 - row1 <= 1: middle_row = row1 # 隣接時は始点を使用（row1）
            
            logger.debug(f"Vertical passage middle_row: {middle_row}")

            # セグメント1: 垂直 (row1 -> middle)
            # row1はDoorなので +1 から開始。middle_row まで（inclusive）
            for i in range(row1 + 1, middle_row + 1):
                logger.debug(f"Setting TUNNEL at ({i}, {col1})")
                self.dungeon_level.set_tile(i, col1, const.TUNNEL)
            
            # セグメント2: 水平 (col1 -> col2 at middle)
            start_c, end_c = min(col1, col2), max(col1, col2)
            for i in range(start_c, end_c + 1):
                # 中間列全体をTunnelにする（角を含む）
                logger.debug(f"Setting TUNNEL at ({middle_row}, {i})")
                self.dungeon_level.set_tile(middle_row, i, const.TUNNEL)

            # セグメント3: 垂直 (middle -> row2)
            # middle_row から row2 - 1 まで
            for i in range(middle_row, row2):
                if i == middle_row and col1 != col2: 
                    # コーナー（middle_row, col2）は既に塗られている可能性があるが、念のため
                    # ただし start_c..end_c ループで塗られている
                    pass
                logger.debug(f"Setting TUNNEL at ({i}, {col2})")
                self.dungeon_level.set_tile(i, col2, const.TUNNEL)

        if utils.rand_percent(const.HIDE_PERCENT):
            self._hide_boxed_passage(row1, col1, row2, col2, 1)

    def _same_row(self, room1: int, room2: int) -> bool:
        """同じ行か判定"""
        return (room1 // 3) == (room2 // 3)

    def _same_col(self, room1: int, room2: int) -> bool:
        """同じ列か判定"""
        return (room1 % 3) == (room2 % 3)

    def _add_mazes(self) -> None:
        """迷宮を追加"""
        if self.cur_level <= 1:
            return

        start = utils.get_rand(0, const.MAXROOMS - 1)
        maze_percent = (self.cur_level * 5) // 4

        if self.cur_level > 15:
            maze_percent += self.cur_level

        for i in range(const.MAXROOMS):
            j = (start + i) % const.MAXROOMS
            if self.dungeon_level.rooms[j].is_room & const.R_NOTHING:
                if utils.rand_percent(maze_percent):
                    self.dungeon_level.rooms[j].is_room = const.R_MAZE
                    self._make_maze(
                        utils.get_rand(self.dungeon_level.rooms[j].top_row + 1,
                                     self.dungeon_level.rooms[j].bottom_row - 1),
                        utils.get_rand(self.dungeon_level.rooms[j].left_col + 1,
                                     self.dungeon_level.rooms[j].right_col - 1),
                        self.dungeon_level.rooms[j].top_row,
                        self.dungeon_level.rooms[j].bottom_row,
                        self.dungeon_level.rooms[j].left_col,
                        self.dungeon_level.rooms[j].right_col
                    )
                    self._hide_boxed_passage(
                        self.dungeon_level.rooms[j].top_row,
                        self.dungeon_level.rooms[j].left_col,
                        self.dungeon_level.rooms[j].bottom_row,
                        self.dungeon_level.rooms[j].right_col,
                        utils.get_rand(0, 2)
                    )

    def _make_maze(self, r: int, c: int, tr: int, br: int, lc: int, rc: int) -> None:
        """迷宮を作成"""
        dirs = [const.UPWARD, const.DOWN, const.LEFT, const.RIGHT]

        self.dungeon_level.set_tile(r, c, const.TUNNEL)

        if utils.rand_percent(33):
            # 方向をシャッフル
            for _ in range(10):
                t1 = utils.get_rand(0, 3)
                t2 = utils.get_rand(0, 3)
                dirs[t1], dirs[t2] = dirs[t2], dirs[t1]

        for direction in dirs:
            if direction == const.UPWARD:
                if ((r - 1) >= tr and
                    self.dungeon_level.get_tile(r - 1, c) != const.TUNNEL and
                    self.dungeon_level.get_tile(r - 1, c - 1) != const.TUNNEL and
                    self.dungeon_level.get_tile(r - 1, c + 1) != const.TUNNEL and
                    self.dungeon_level.get_tile(r - 2, c) != const.TUNNEL):
                    self._make_maze(r - 1, c, tr, br, lc, rc)
            elif direction == const.DOWN:
                if ((r + 1) <= br and
                    self.dungeon_level.get_tile(r + 1, c) != const.TUNNEL and
                    self.dungeon_level.get_tile(r + 1, c - 1) != const.TUNNEL and
                    self.dungeon_level.get_tile(r + 1, c + 1) != const.TUNNEL and
                    self.dungeon_level.get_tile(r + 2, c) != const.TUNNEL):
                    self._make_maze(r + 1, c, tr, br, lc, rc)
            elif direction == const.LEFT:
                if ((c - 1) >= lc and
                    self.dungeon_level.get_tile(r, c - 1) != const.TUNNEL and
                    self.dungeon_level.get_tile(r - 1, c - 1) != const.TUNNEL and
                    self.dungeon_level.get_tile(r + 1, c - 1) != const.TUNNEL and
                    self.dungeon_level.get_tile(r, c - 2) != const.TUNNEL):
                    self._make_maze(r, c - 1, tr, br, lc, rc)
            elif direction == const.RIGHT:
                if ((c + 1) <= rc and
                    self.dungeon_level.get_tile(r, c + 1) != const.TUNNEL and
                    self.dungeon_level.get_tile(r - 1, c + 1) != const.TUNNEL and
                    self.dungeon_level.get_tile(r + 1, c + 1) != const.TUNNEL and
                    self.dungeon_level.get_tile(r, c + 2) != const.TUNNEL):
                    self._make_maze(r, c + 1, tr, br, lc, rc)

    def _hide_boxed_passage(self, row1: int, col1: int, row2: int, col2: int, n: int) -> None:
        """通路を隠す"""
        if self.cur_level <= 2:
            return

        if row1 > row2:
            row1, row2 = row2, row1
        if col1 > col2:
            col1, col2 = col2, col1

        h = row2 - row1
        w = col2 - col1

        if w >= 5 or h >= 5:
            row_cut = 1 if h >= 2 else 0
            col_cut = 1 if w >= 2 else 0

            for _ in range(n):
                for _ in range(10):
                    row = utils.get_rand(row1 + row_cut, row2 - row_cut)
                    col = utils.get_rand(col1 + col_cut, col2 - col_cut)
                    if self.dungeon_level.get_tile(row, col) == const.TUNNEL:
                        tile = self.dungeon_level.get_tile(row, col)
                        self.dungeon_level.set_tile(row, col, tile | const.HIDDEN)
                        break

    def _fill_out_level(self) -> None:
        """レベルを埋める"""
        self._mix_random_rooms()

        # C言語版: r_de = NO_ROOM;
        self.r_de = const.NO_ROOM

        for i in range(const.MAXROOMS):
            rn = RANDOM_ROOMS[i]
            if (self.dungeon_level.rooms[rn].is_room & const.R_NOTHING) or \
               ((self.dungeon_level.rooms[rn].is_room & const.R_CROSS) and utils.coin_toss()):
                self._fill_it(rn, True)

        # C言語版: if (r_de != NO_ROOM) { fill_it(r_de, 0); }
        if self.r_de != const.NO_ROOM:
            self._fill_it(self.r_de, False)

    def _fill_it(self, rn: int, do_rec_de: bool) -> None:
        """部屋を埋める"""
        offsets = [-1, 1, 3, -3]

        # オフセットをシャッフル
        for _ in range(10):
            srow = utils.get_rand(0, 3)
            scol = utils.get_rand(0, 3)
            t = offsets[srow]
            offsets[srow] = offsets[scol]
            offsets[scol] = t

        did_this = False
        rooms_found = 0

        for i in range(4):
            target_room = rn + offsets[i]

            if ((target_room < 0) or (target_room >= const.MAXROOMS)) or \
               (not (self._same_row(rn, target_room) or self._same_col(rn, target_room))) or \
               (not (self.dungeon_level.rooms[target_room].is_room & (const.R_ROOM | const.R_MAZE))):
                continue

            if self._same_row(rn, target_room):
                tunnel_dir = const.RIGHT if self.dungeon_level.rooms[rn].left_col < \
                    self.dungeon_level.rooms[target_room].left_col else const.LEFT
            else:
                tunnel_dir = const.DOWN if self.dungeon_level.rooms[rn].top_row < \
                    self.dungeon_level.rooms[target_room].top_row else const.UPWARD

            door_dir = (tunnel_dir + 4) % const.DIRS

            if self.dungeon_level.rooms[target_room].doors[door_dir // 2].oth_room != const.NO_ROOM:
                continue

            found, mr, mc = self._mask_room(rn, const.TUNNEL)
            if (not do_rec_de) or did_this or (not found):
                srow = (self.dungeon_level.rooms[rn].top_row + self.dungeon_level.rooms[rn].bottom_row) // 2
                scol = (self.dungeon_level.rooms[rn].left_col + self.dungeon_level.rooms[rn].right_col) // 2
            else:
                srow = mr
                scol = mc

            dr, dc = self._put_door(target_room, door_dir)
            rooms_found += 1
            self._draw_simple_passage(srow, scol, dr, dc, tunnel_dir)
            self.dungeon_level.rooms[rn].is_room = const.R_DEADEND
            self.dungeon_level.set_tile(srow, scol, const.TUNNEL)

            if i < 3 and not did_this:
                did_this = True
                if utils.coin_toss():
                    continue

            if rooms_found < 2 and do_rec_de:
                self._recursive_deadend(rn, offsets, srow, scol)
            break

    def _recursive_deadend(self, rn: int, offsets: List[int], srow: int, scol: int) -> None:
        """再帰的にデッドエンドを埋める"""
        self.dungeon_level.rooms[rn].is_room = const.R_DEADEND
        self.dungeon_level.set_tile(srow, scol, const.TUNNEL)

        for i in range(4):
            de = rn + offsets[i]
            if ((de < 0) or (de >= const.MAXROOMS)) or \
               (not (self._same_row(rn, de) or self._same_col(rn, de))):
                continue

            if not (self.dungeon_level.rooms[de].is_room & const.R_NOTHING):
                continue

            drow = (self.dungeon_level.rooms[de].top_row + self.dungeon_level.rooms[de].bottom_row) // 2
            dcol = (self.dungeon_level.rooms[de].left_col + self.dungeon_level.rooms[de].right_col) // 2

            if self._same_row(rn, de):
                tunnel_dir = const.RIGHT if self.dungeon_level.rooms[rn].left_col < \
                    self.dungeon_level.rooms[de].left_col else const.LEFT
            else:
                tunnel_dir = const.DOWN if self.dungeon_level.rooms[rn].top_row < \
                    self.dungeon_level.rooms[de].top_row else const.UPWARD

            self._draw_simple_passage(srow, scol, drow, dcol, tunnel_dir)
            # C言語版: r_de = de; (party_room ではない)
            self.r_de = de
            self._recursive_deadend(de, offsets, drow, dcol)

    def _mask_room(self, rn: int, mask: int) -> Tuple[bool, int, int]:
        """部屋内の指定マスクを持つタイルを検索 (C版 level.c: mask_room)"""
        room = self.dungeon_level.rooms[rn]
        for i in range(room.top_row, room.bottom_row + 1):
            for j in range(room.left_col, room.right_col + 1):
                if self.dungeon_level.get_tile(i, j) & mask:
                    return True, i, j
        return False, 0, 0

    def _is_all_connected(self) -> bool:
        """すべての部屋が接続されているか判定"""
        starting_room = 0

        for i in range(const.MAXROOMS):
            self.rooms_visited[i] = False
            if self.dungeon_level.rooms[i].is_room & (const.R_ROOM | const.R_MAZE):
                starting_room = i

        self._visit_rooms(starting_room)

        for i in range(const.MAXROOMS):
            if (self.dungeon_level.rooms[i].is_room & (const.R_ROOM | const.R_MAZE)) and \
               (not self.rooms_visited[i]):
                return False

        return True

    def _visit_rooms(self, rn: int) -> None:
        """部屋を訪問（再帰）"""
        self.rooms_visited[rn] = True

        for i in range(4):
            oth_rn = self.dungeon_level.rooms[rn].doors[i].oth_room
            if oth_rn >= 0 and not self.rooms_visited[oth_rn]:
                self._visit_rooms(oth_rn)

    def _mix_random_rooms(self) -> None:
        """ランダム部屋順序をシャッフル"""
        for i in range(const.MAXROOMS):
            j = utils.get_rand(i, const.MAXROOMS - 1)
            RANDOM_ROOMS[i], RANDOM_ROOMS[j] = RANDOM_ROOMS[j], RANDOM_ROOMS[i]

    def _put_amulet(self) -> None:
        """アミュレットを配置 (C版 level.c: put_amulet相当)"""
        for _ in range(50):
            rn = utils.get_rand(0, const.MAXROOMS - 1)
            try:
                room = self.dungeon_level.get_room(rn)
            except Exception:
                continue
            if not (room.is_room & const.R_ROOM):
                continue
            row = utils.get_rand(room.top_row + 1, room.bottom_row - 1)
            col = utils.get_rand(room.left_col + 1, room.right_col - 1)
            if self.dungeon_level.get_tile(row, col) == const.FLOOR:
                amulet = entities.Item()
                amulet.item_type = const.AMULET
                amulet.ichar = ord(',')
                amulet.row, amulet.col = row, col
                amulet.next_object = self.dungeon_level.level_objects
                self.dungeon_level.level_objects = amulet
                self.dungeon_level.set_tile(row, col, const.FLOOR | const.OBJECT)
                break
        self.dungeon_level.has_amulet = True

    def put_player(self, avoid_room: int) -> Tuple[int, int]:
        """プレイヤーを配置"""
        rn = avoid_room
        misses = 0

        for misses in range(2):
            if rn == avoid_room:
                row, col = self._gr_row_col(const.FLOOR | const.TUNNEL | const.OBJECT | const.STAIRS)
                rn = self.dungeon_level.get_room_number(row, col)

        return row, col

    def _gr_row_col(self, mask: int) -> Tuple[int, int]:
        """ランダムな座標を取得"""
        while True:
            r = utils.get_rand(const.MIN_ROW, const.ROGUE_LINES - 2)
            c = utils.get_rand(0, const.ROGUE_COLUMNS - 1)
            rn = self.dungeon_level.get_room_number(r, c)

            if rn == const.NO_ROOM:
                continue
            if not (self.dungeon_level.get_tile(r, c) & mask):
                continue
            if self.dungeon_level.get_tile(r, c) & (~mask):
                continue
            if not (self.dungeon_level.rooms[rn].is_room & (const.R_ROOM | const.R_MAZE)):
                continue

            return r, c

    @staticmethod
    def get_mask_char(item_type: int) -> str:
        """アイテム種別文字 (C版 room.c: get_mask_char相当)"""
        mapping = {
            const.SCROL: '?', const.POTION: '!', const.GOLD: '*',
            const.FOOD: ':', const.WAND: '/', const.ARMOR: ']',
            const.WEAPON: ')', const.RING: '=', const.AMULET: ',',
        }
        return mapping.get(item_type, '~')

    def get_dungeon_char(self, row: int, col: int) -> str:
        """ダンジョンの文字を取得 (C版 room.c: get_dungeon_char相当)"""
        mask = self.dungeon_level.get_tile(row, col)

        if mask & const.MONSTER:
            # 連結リストから実文字を取得（C版 gmc_row_col相当）
            cur = getattr(self.dungeon_level, 'level_monsters', None)
            while cur is not None:
                if cur.row == row and cur.col == col:
                    ich = getattr(cur, 'ichar', 0)
                    if isinstance(ich, int) and 65 <= ich <= 90:
                        return chr(ich)
                    if isinstance(ich, str) and len(ich) == 1:
                        return ich
                    break
                cur = getattr(cur, 'next_object', None)
            return 'M'
        if mask & const.OBJECT:
            # 種別文字を取得（C版 get_mask_char相当）
            cur = getattr(self.dungeon_level, 'level_objects', None)
            while cur is not None:
                if cur.row == row and cur.col == col:
                    return self.get_mask_char(cur.item_type)
                cur = getattr(cur, 'next_object', None)
            return '*'
        if mask & (const.TUNNEL | const.STAIRS | const.HORWALL | const.VERTWALL | const.FLOOR | const.DOOR):
            if (mask & (const.TUNNEL | const.STAIRS)) and not (mask & const.HIDDEN):
                return '%' if (mask & const.STAIRS) else '#'
            if mask & const.HORWALL:
                return '-'
            if mask & const.VERTWALL:
                return '|'
            if mask & const.FLOOR:
                if mask & const.TRAP:
                    if not (self.dungeon_level.get_tile(row, col) & const.HIDDEN):
                        return '^'
                return '.'
        if mask & const.DOOR:
            if mask & const.HIDDEN:
                if (col > 0 and self.dungeon_level.get_tile(row, col - 1) & const.HORWALL) or \
                   (col < const.ROGUE_COLUMNS - 1 and self.dungeon_level.get_tile(row, col + 1) & const.HORWALL):
                    return '-'
                else:
                    return '|'
            else:
                return '+'

        return ' '

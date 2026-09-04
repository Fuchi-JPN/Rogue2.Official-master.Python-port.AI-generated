"""
display.py - Rogue2.Official C to Python 移植
画面描画システム

元ファイル: src/display.c, src/message.c
"""

from typing import Optional, Dict, List


import logging
logger = logging.getLogger(__name__)

try:
    from . import const
    from . import config
    from . import entities
    from . import dungeon
    from . import special_actions
    from .game_state import GameState
    from .ai.input_hook import hook_getch_int as _ai_hook_getch_int
    from .ai.input_hook import request_force_quit as _ai_request_force_quit
    from .ai.input_hook import auto_ack_enabled as _ai_auto_ack_enabled
except ImportError:
    import const
    import config
    import entities
    import dungeon
    import special_actions
    from game_state import GameState
    try:
        from ai.input_hook import hook_getch_int as _ai_hook_getch_int
        from ai.input_hook import request_force_quit as _ai_request_force_quit
        from ai.input_hook import auto_ack_enabled as _ai_auto_ack_enabled
    except ImportError:
        _ai_hook_getch_int = None
        _ai_request_force_quit = None
        _ai_auto_ack_enabled = None


# ============================================================================
# カラー定数
# ============================================================================

WHITE = 1
RED = 2
GREEN = 3
YELLOW = 4
BLUE = 5
MAGENTA = 6
CYAN = 7
WHITE_REVERSE = 8
RED_REVERSE = 9
GREEN_REVERSE = 10
YELLOW_REVERSE = 11
BLUE_REVERSE = 12
MAGENTA_REVERSE = 13
CYAN_REVERSE = 14


# ============================================================================
# Displayクラス - 画面描画システム
# ============================================================================

class Display:
    """画面描画システムクラス"""

    def __init__(self, stdscr):
        """初期化"""
        self.stdscr = stdscr
        self.curses = config.get_curses_module()

        # カラー設定
        self.use_color = config.COLOR
        self.color_str = "cbmyg"  # デフォルトのカラーマップ
        self.ch_attr: Dict[int, int] = {}

        # 初期化
        self._init_color_attr()

    def _init_color_attr(self) -> None:
        """カラー属性配列を初期化"""
        if self.use_color and self.curses.has_colors():
            try:
                self._init_color_pairs()
                self._create_color_map()
                return
            except Exception:
                pass
        # カラーなし
        self.use_color = False
        for k in range(128):
            self.ch_attr[k] = 0

    def _init_color_pairs(self) -> None:
        """カラーペアを初期化"""
        # 背景色の定義
        if hasattr(self.curses, 'assume_default_colors'):
            self.curses.assume_default_colors(
                self.curses.COLOR_WHITE,
                self.curses.COLOR_BLACK
            )

        # 表示色の定義
        self.curses.init_pair(WHITE, self.curses.COLOR_WHITE, self.curses.COLOR_BLACK)
        self.curses.init_pair(RED, self.curses.COLOR_RED, self.curses.COLOR_BLACK)
        self.curses.init_pair(GREEN, self.curses.COLOR_GREEN, self.curses.COLOR_BLACK)
        self.curses.init_pair(YELLOW, self.curses.COLOR_YELLOW, self.curses.COLOR_BLACK)
        self.curses.init_pair(BLUE, self.curses.COLOR_BLUE, self.curses.COLOR_BLACK)
        self.curses.init_pair(MAGENTA, self.curses.COLOR_MAGENTA, self.curses.COLOR_BLACK)
        self.curses.init_pair(CYAN, self.curses.COLOR_CYAN, self.curses.COLOR_BLACK)
        self.curses.init_pair(WHITE_REVERSE, self.curses.COLOR_BLACK, self.curses.COLOR_WHITE)
        self.curses.init_pair(RED_REVERSE, self.curses.COLOR_BLACK, self.curses.COLOR_RED)
        self.curses.init_pair(GREEN_REVERSE, self.curses.COLOR_BLACK, self.curses.COLOR_GREEN)
        self.curses.init_pair(YELLOW_REVERSE, self.curses.COLOR_BLACK, self.curses.COLOR_YELLOW)
        self.curses.init_pair(BLUE_REVERSE, self.curses.COLOR_BLACK, self.curses.COLOR_BLUE)
        self.curses.init_pair(MAGENTA_REVERSE, self.curses.COLOR_BLACK, self.curses.COLOR_MAGENTA)
        self.curses.init_pair(CYAN_REVERSE, self.curses.COLOR_BLACK, self.curses.COLOR_CYAN)

    def _create_color_map(self) -> None:
        """カラーマップを作成"""
        color_type = "wrgybmcWRGYBMC"
        colormap_list = [0] * 5

        # 表示設定解析
        for i in range(min(5, len(self.color_str))):
            j = self._r_index(color_type, self.color_str[i], False)
            if j >= 0:
                colormap_list[i] = self._get_color_pair(color_type[j])

        # 文字のカラーマップの作成
        for ch in "-|#+":
            self._get_colorpair_number(ord(ch), colormap_list[0])
        self._get_colorpair_number(ord('.'), colormap_list[1])
        for ch in range(ord('A'), ord('Z') + 1):
            self._get_colorpair_number(ch, colormap_list[2])
        for ch in "%!?/=)]^*:,":
            self._get_colorpair_number(ord(ch), colormap_list[3])
        self._get_colorpair_number(ord('@'), colormap_list[4])

    def _r_index(self, s: str, ch: str, last: bool) -> int:
        """文字列から文字のインデックスを取得"""
        if last:
            for i in range(len(s) - 1, -1, -1):
                if s[i] == ch:
                    return i
        else:
            for i, c in enumerate(s):
                if c == ch:
                    return i
        return -1

    def _get_color_pair(self, ch: str) -> int:
        """文字からカラーペア番号を取得"""
        color_map = {
            'w': WHITE, 'r': RED, 'g': GREEN, 'y': YELLOW, 'b': BLUE,
            'm': MAGENTA, 'c': CYAN,
            'W': WHITE_REVERSE, 'R': RED_REVERSE, 'G': GREEN_REVERSE,
            'Y': YELLOW_REVERSE, 'B': BLUE_REVERSE, 'M': MAGENTA_REVERSE,
            'C': CYAN_REVERSE
        }
        return color_map.get(ch, 0)

    def _get_colorpair_number(self, ch: int, num: int) -> None:
        """文字のカラーペア番号を設定"""
        self.ch_attr[ch] = num

    def _put_colorpair_number(self, ch: int) -> int:
        """文字のカラーペア番号を取得"""
        return self.ch_attr.get(ch, 0)

    def _set_color(self, ch: int) -> None:
        """文字に応じてカラーを設定"""
        if self.use_color:
            color_pair = self._put_colorpair_number(ch)
            self.stdscr.attrset(self.curses.color_pair(color_pair))

    def refresh(self) -> int:
        """refreshのラッパー"""
        result = self.stdscr.refresh()
        if not hasattr(self, '_refresh_log_count'):
            self._refresh_log_count = 0
        if self._refresh_log_count < 2:
            logger.debug(f"refresh() called -> {result}")
            self._refresh_log_count += 1
        return result

    def addch(self, ch: int) -> int:
        """addchのラッパー"""
        self._set_color(ch)
        return self.stdscr.addstr(chr(ch)) if hasattr(self.stdscr, 'addstr') else self.stdscr.addch(ch)

    def mvaddch(self, y: int, x: int, ch: int) -> int:
        """mvaddchのラッパー"""
        self._set_color(ch)
        try:
            result = self.stdscr.addstr(y, x, chr(ch))
            if not hasattr(self, '_mvaddch_log_count'):
                self._mvaddch_log_count = 0
            if self._mvaddch_log_count < 3:
                logger.debug(f"mvaddch: ({y},{x}) ch={ch}('{chr(ch)}') via addstr -> {result}")
                self._mvaddch_log_count += 1
            return result
        except Exception as e:
            logger.debug(f"mvaddch: addstr failed at ({y},{x}): {e}, falling back to addch")
            return self.stdscr.addch(y, x, ch)

    def addstr(self, s: str) -> int:
        """addstrのラッパー"""
        if self.use_color:
            self.stdscr.attrset(self.curses.color_pair(0))
        return self.stdscr.addstr(s)

    def mvaddstr(self, y: int, x: int, s: str) -> int:
        """mvaddstrのラッパー"""
        if self.use_color:
            try:
                attr = self.stdscr.inch(y, x) & self.curses.A_ATTRIBUTES
                if attr & self.curses.A_REVERSE:
                    self.stdscr.attrset(self.curses.color_pair(CYAN))
                    self.stdscr.attron(self.curses.A_REVERSE)
                else:
                    self.stdscr.attrset(self.curses.color_pair(0))
            except Exception:
                self.stdscr.attrset(self.curses.color_pair(0))
        return self.stdscr.addstr(y, x, s)

    def move(self, y: int, x: int) -> int:
        """moveのラッパー"""
        return self.stdscr.move(y, x)

    def mvinch(self, y: int, x: int) -> int:
        """mvinchのラッパー"""
        ch = self.stdscr.inch(y, x)
        if self.use_color:
            return ch & self.curses.A_CHARTEXT
        return ch

    def clrtoeol(self) -> int:
        """clrtoeolのラッパー"""
        return self.stdscr.clrtoeol()

    def clear(self) -> int:
        """clearのラッパー"""
        return self.stdscr.clear()

    def getch(self) -> int:
        """getchのラッパー（AI自動プレイ時はキューを優先）"""
        if _ai_hook_getch_int is not None:
            hooked = _ai_hook_getch_int()
            if hooked is not None:
                return hooked
        return self.stdscr.getch()

    def dump_screen(self):
        """画面全文（24x80）のダンプ。AI観測用。失敗時はNone"""
        try:
            lines = []
            for y in range(const.ROGUE_LINES):
                try:
                    raw = self.stdscr.instr(y, 0, const.ROGUE_COLUMNS)
                    lines.append(raw.decode("utf-8", "ignore").rstrip())
                except Exception:
                    lines.append("")
            return lines
        except Exception:
            return None

    # ==========================================================================
    # マップ描画
    # ==========================================================================

    def draw_map(self, dungeon: dungeon.DungeonLevel, player: entities.Player) -> None:
        """マップを描画（1行目から22行目まで）"""
        drawn_count = 0
        player_room = dungeon.get_room_number(player.row, player.col) if hasattr(dungeon, 'get_room_number') else const.NO_ROOM
        logger.debug(f"draw_map: player=({player.row},{player.col}), player_room={player_room}, DEBUG={const.DEBUG}")

        for row in range(const.MIN_ROW, const.ROGUE_LINES - 1):
            for col in range(const.ROGUE_COLUMNS):
                tile = dungeon.get_tile(row, col)
                tile_room = dungeon.get_room_number(row, col) if hasattr(dungeon, 'get_room_number') else const.NO_ROOM
                if (tile & const.MAPPED) or const.DEBUG or (tile_room == player_room and tile_room != const.NO_ROOM):
                    self._draw_tile(dungeon, row, col, tile)
                    drawn_count += 1
                else:
                    self.mvaddch(row, col, ord(' '))

        logger.debug(f"draw_map: drew {drawn_count} tiles")
        # プレイヤーを描画
        self.mvaddch(player.row, player.col, player.fchar)

    def _draw_tile(self, dungeon_level, row: int, col: int, tile: int) -> None:
        """タイルを描画（C言語版 room.c: get_dungeon_char の分岐順に準拠）"""
        ch = ' '
        # C版の優先順: TUNNEL/STAIRS(&&!HIDDEN) → HORWALL → VERTWALL
        # → FLOOR(TRAP&&!HIDDEN→^) → DOOR。単独TRAPは' '。
        if (tile & (const.TUNNEL | const.STAIRS)) and not (tile & const.HIDDEN):
            ch = '%' if (tile & const.STAIRS) else '#'
        elif tile & const.HORWALL:
            ch = '-'
        elif tile & const.VERTWALL:
            ch = '|'
        elif tile & const.FLOOR:
            if (tile & const.TRAP) and not (tile & const.HIDDEN):
                ch = '^'
            else:
                ch = '.'
        elif tile & const.DOOR:
            # 隠されたドアは壁として表示（C言語版と同じ）
            if tile & const.HIDDEN:
                # 周囲の壁に合わせて表示（dungeon_levelを使用）
                if ((col > 0 and dungeon_level.get_tile(row, col - 1) & const.HORWALL) or
                    (col < const.ROGUE_COLUMNS - 1 and dungeon_level.get_tile(row, col + 1) & const.HORWALL)):
                    ch = '-'
                else:
                    ch = '|'
            else:
                ch = '+'

        self.mvaddch(row, col, ord(ch))

    def draw_entities(self, dungeon: dungeon.DungeonLevel, player: entities.Player, cur_room: int = const.NO_ROOM, blind: bool = False) -> None:
        """エンティティを描画"""
        if blind:
            logger.debug("draw_entities: blind, only drawing player")
            self.mvaddch(player.row, player.col, player.fchar)
            return

        halluc = GameState.halluc > 0 if hasattr(GameState, 'halluc') else False
        logger.debug(f"draw_entities: cur_room={cur_room}, blind={blind}, halluc={halluc}")

        # アイテムを描画（C版の優先順 MONSTER→OBJECTに合わせ怪より先）
        obj_count = 0
        obj = dungeon.level_objects
        while obj:
            if self.rogue_can_see(dungeon, player, cur_room, obj.row, obj.col, blind):
                self.mvaddch(obj.row, obj.col, obj.ichar)
                obj_count += 1
            obj = obj.next_object

        logger.debug(f"draw_entities: drew {obj_count} objects")
        # モンスターを描画
        mon_count = 0
        monster = dungeon.level_monsters
        while monster:
            if self.rogue_can_see(dungeon, player, cur_room, monster.row, monster.col, blind):
                mon_count += 1
                # C版 gmc(): detect_monster/see_invisible → INVISIBLE可視, IMITATES→disguise, それ以外→m_char
                if (not (GameState.detect_monster or GameState.see_invisible or GameState.r_see_invisible) and
                        monster.m_flags & const.INVISIBLE):
                    ch = monster.trail_char
                elif monster.m_flags & const.IMITATES:
                    ch = monster.disguise
                else:
                    ch = monster.ichar
                self.mvaddch(monster.row, monster.col, ch)
            monster = monster.next_object
        logger.debug(f"draw_entities: drew {mon_count} monsters")
        # プレイヤーを描画
        self.mvaddch(player.row, player.col, player.fchar)

    def rogue_can_see(self, dungeon: dungeon.DungeonLevel, player: entities.Player, cur_room: int, row: int, col: int, blind: bool = False) -> bool:
        """プレイヤーがその座標を見ることができるか (C版 monster.c: rogue_can_see)
        
        C版: return (!blind && (((get_room_number(row, col) == cur_room) &&
                !(rooms[cur_room].is_room & R_MAZE)) || rogue_is_around(row, col)));
        """
        if blind:
            return False

        # 1. プレイヤーの隣接 8 マス (rogue_is_around 相当)
        rdif = row - player.row
        cdif = col - player.col
        if -1 <= rdif <= 1 and -1 <= cdif <= 1:
            return True
            
        # 2. 同じ部屋にいる (迷路不可)
        rn = dungeon.get_room_number(row, col)
        if rn != const.NO_ROOM and rn == cur_room:
            room = dungeon.get_room(rn)
            if room and not (room.is_room & const.R_MAZE):
                return True
                
        return False

    # ==========================================================================
    # ユーティリティ
    # ==========================================================================

    # ==========================================================================
    # モンスター経路設定 (C版 room.c: dr_course, get_oth_room)
    # ==========================================================================

    def dr_course(self, monster, entering: bool, row: int, col: int, dungeon_level) -> None:
        """モンスターの移動経路を設定 (C版 room.c: dr_course)"""
        try:
            import utils as _utils
        except ImportError:
            from . import utils as _utils

        monster.row = row
        monster.col = col

        # C版: mon_sees(monster, rogue.row, rogue.col)
        if self._mon_sees(monster, self.player_row, self.player_col, dungeon_level):
            monster.trow = const.NO_ROOM
            return

        rn = dungeon_level.get_room_number(row, col)

        if entering:
            self._dr_course_entering(monster, rn, dungeon_level, _utils)
        else:
            self._dr_course_exiting(monster, rn, row, col, dungeon_level)

    def _mon_sees(self, monster, row: int, col: int, dungeon_level) -> bool:
        """モンスターがターゲットを見ているか (C版 monster.c: mon_sees)"""
        rn = dungeon_level.get_room_number(row, col)
        mn = dungeon_level.get_room_number(monster.row, monster.col)

        if (rn != const.NO_ROOM and
                rn == mn and
                not (dungeon_level.rooms[rn].is_room & const.R_MAZE)):
            return True

        rdif = row - monster.row
        cdif = col - monster.col
        return -1 <= rdif <= 1 and -1 <= cdif <= 1

    def _dr_course_entering(self, monster, rn, dungeon_level, _utils) -> None:
        """部屋に入る場合の経路設定"""
        r = _utils.get_rand(0, const.MAXROOMS - 1)
        for i in range(const.MAXROOMS):
            rr = (r + i) % const.MAXROOMS
            if not (dungeon_level.rooms[rr].is_room & (const.R_ROOM | const.R_MAZE)):
                continue
            if rr == rn:
                continue
            for k in range(4):
                if dungeon_level.rooms[rr].doors[k].oth_room == rn:
                    monster.trow = dungeon_level.rooms[rr].doors[k].oth_row
                    monster.tcol = dungeon_level.rooms[rr].doors[k].oth_col
                    if monster.trow == monster.row and monster.tcol == monster.col:
                        continue
                    return

        # 袋小路へのドア
        for i in range(dungeon_level.rooms[rn].top_row, dungeon_level.rooms[rn].bottom_row + 1):
            for j in range(dungeon_level.rooms[rn].left_col, dungeon_level.rooms[rn].right_col + 1):
                if (i != monster.row and j != monster.col and
                        dungeon_level.get_tile(i, j) & const.DOOR):
                    monster.trow = i
                    monster.tcol = j
                    return

        # 元の部屋へ
        for i in range(const.MAXROOMS):
            for j in range(4):
                if dungeon_level.rooms[i].doors[j].oth_room == rn:
                    for k in range(4):
                        if dungeon_level.rooms[rn].doors[k].oth_room == i:
                            monster.trow = dungeon_level.rooms[rn].doors[k].oth_row
                            monster.tcol = dungeon_level.rooms[rn].doors[k].oth_col
                            return
        monster.trow = -1

    def _dr_course_exiting(self, monster, rn, row, col, dungeon_level) -> None:
        """部屋を出る場合の経路設定"""
        d = -1
        room = dungeon_level.rooms[rn]
        if row == room.top_row:
            d = const.UPWARD // 2
        elif row == room.bottom_row:
            d = const.DOWN // 2
        elif col == room.left_col:
            d = const.LEFT // 2
        elif col == room.right_col:
            d = const.RIGHT // 2

        if d != -1 and room.doors[d].oth_room >= 0:
            monster.trow = room.doors[d].oth_row
            monster.tcol = room.doors[d].oth_col
        else:
            monster.trow = const.NO_ROOM

    def sound_bell(self) -> None:
        """ベルを鳴らす"""
        self.curses.beep()

    def save_screen(self, filename: str = "rogue.screen") -> None:
        """画面をファイルに保存 (C版 message.c: save_screen相当)"""
        try:
            with open(filename, 'w', encoding='utf-8') as fp:
                for i in range(const.ROGUE_LINES):
                    # 右端の空白を刈って書き出す（C版の逆走トリムと等価）
                    row = ''.join(chr(self.mvinch(i, j)) for j in range(const.ROGUE_COLUMNS))
                    fp.write(row.rstrip() + '\n')
        except Exception:
            self.sound_bell()


    def _object_at_monsters(self, level, row: int, col: int):
        """指定位置のモンスターを取得"""
        if not level:
            return None
        obj = level.level_monsters
        while obj:
            if obj.row == row and obj.col == col:
                return obj
            obj = obj.next_monster
        return None

    def get_dungeon_char(self, dungeon_level, row: int, col: int) -> str:
        """指定した座標のダンジョン文字を取得 (C版 room.c: get_dungeon_char)"""
        try:
            tile = dungeon_level.get_tile(row, col)

            # MONSTER: モンスター表示文字を返す
            if tile & const.MONSTER:
                return self._gmc_row_col(dungeon_level, row, col)

            # OBJECT: アイテム表示文字を返す
            if tile & const.OBJECT:
                obj = self._object_at_objects(dungeon_level, row, col)
                if obj:
                    return Display.get_mask_char(obj.item_type)
                return '~'

            if tile & (const.TUNNEL | const.STAIRS | const.HORWALL | const.VERTWALL | const.FLOOR | const.DOOR):
                if (tile & (const.TUNNEL | const.STAIRS)) and not (tile & const.HIDDEN):
                    return '%' if (tile & const.STAIRS) else '#'
                if tile & const.HORWALL:
                    return '-'
                if tile & const.VERTWALL:
                    return '|'
                if tile & const.FLOOR:
                    if tile & const.TRAP:
                        if not (tile & const.HIDDEN):
                            return '^'
                    return '.'
                if tile & const.DOOR:
                    if tile & const.HIDDEN:
                        if ((col > 0 and dungeon_level.get_tile(row, col - 1) & const.HORWALL) or
                            (col < const.ROGUE_COLUMNS - 1 and dungeon_level.get_tile(row, col + 1) & const.HORWALL)):
                            return '-'
                        return '|'
                    return '+'
            return ' '
        except:
            return ' '

    def _gmc_row_col(self, dungeon_level, row: int, col: int) -> str:
        """モンスターの表示文字を取得 (C版 monster.c: gmc_row_col / gmc)"""
        monster = self._object_at_monsters(dungeon_level, row, col)
        if monster:
            # C版 gmc順: 不可視/blind → trail、IMITATES → disguise、else m_char
            if ((not (GameState.detect_monster or GameState.see_invisible or
                      getattr(GameState, 'r_see_invisible', 0)) and
                    (monster.m_flags & const.INVISIBLE)) or GameState.blind):
                return monster.trail_char
            if monster.m_flags & const.IMITATES:
                return chr(monster.disguise) if hasattr(monster, 'disguise') else 'M'
            return chr(monster.ichar) if monster.ichar else 'M'
        return '&'

    def _object_at_objects(self, level, row: int, col: int):
        """指定位置のアイテムを取得"""
        if not level:
            return None
        obj = level.level_objects
        while obj:
            if obj.row == row and obj.col == col:
                return obj
            obj = obj.next_object
        return None

    @staticmethod
    def get_mask_char(mask: int) -> str:
        """アイテムタイプに対応する表示文字を取得 (C版 room.c: get_mask_char)"""
        from . import const as _const
        mapping = {
            _const.SCROL: '?', _const.POTION: '!', _const.GOLD: '*',
            _const.FOOD: ':', _const.WAND: '/', _const.ARMOR: ']',
            _const.WEAPON: ')', _const.RING: '=', _const.AMULET: ',',
        }
        return mapping.get(mask, '~')

    def light_up_room(self, dungeon_level, player, room_number: int) -> None:
        """部屋を照らす (C版 room.c: light_up_room)"""
        logger.debug(f"light_up_room: room={room_number}, blind={GameState.blind}")
        if not GameState.blind:
            room = dungeon_level.rooms[room_number]
            tile_count = 0
            for i in range(room.top_row, room.bottom_row + 1):
                for j in range(room.left_col, room.right_col + 1):
                    tile = dungeon_level.get_tile(i, j)
                    # MONSTERフラグがある場合: 一時的に除去して床文字をtrail_charに設定
                    if tile & const.MONSTER:
                        monster = self._object_at_monsters(dungeon_level, i, j)
                        if monster and hasattr(monster, 'trail_char'):
                            dungeon_level.dungeon[i][j] &= ~const.MONSTER
                            trail_ch = self.get_dungeon_char(dungeon_level, i, j)
                            dungeon_level.dungeon[i][j] |= const.MONSTER
                            if isinstance(trail_ch, str) and len(trail_ch) == 1:
                                monster.trail_char = trail_ch
                    # 探索済みにセット
                    dungeon_level.dungeon[i][j] |= const.MAPPED
                    ch = self.get_dungeon_char(dungeon_level, i, j)
                    self.mvaddch(i, j, ord(ch))
                    tile_count += 1

            logger.debug(f"light_up_room: drew {tile_count} tiles, drawing player at ({player.row},{player.col})")
            self.mvaddch(player.row, player.col, player.fchar)
        else:
            logger.debug("light_up_room: blind, skipping")

    def light_passage(self, dungeon_level, player, row: int, col: int) -> None:
        """通路を照らす (C版 room.c: light_passage)"""
        if GameState.blind:
            return

        # C版: i_end = (row < ROGUE_LINES-2) ? 1 : 0
        i_end = 1 if row < (const.ROGUE_LINES - 2) else 0
        j_end = 1 if col < (const.ROGUE_COLUMNS - 1) else 0

        # C版: for (i = (row > MIN_ROW) ? -1 : 0; i <= i_end; i++)
        i_start = -1 if row > const.MIN_ROW else 0
        j_start = -1 if col > 0 else 0

        for i in range(i_start, i_end + 1):
            for j in range(j_start, j_end + 1):
                nr, nc = row + i, col + j
                if not dungeon_level.is_valid_position(nr, nc):
                    continue

                # C版: if (can_move(row, col, row+i, col+j))
                if self._can_move_light(dungeon_level, row, col, nr, nc):
                    # 探索済みにセット
                    dungeon_level.dungeon[nr][nc] |= const.MAPPED
                    ch = self.get_dungeon_char(dungeon_level, nr, nc)
                    self.mvaddch(nr, nc, ord(ch))

    @staticmethod
    def _can_move_light(dungeon_level, r1: int, c1: int, r2: int, c2: int) -> bool:
        """点灯用の移動可否 (C版 move.c: can_move相当)"""
        try:
            t2 = dungeon_level.get_tile(r2, c2)
        except Exception:
            return False
        # is_passable相当（範囲内前提。HIDDENは罠のみ可）
        if t2 & const.HIDDEN:
            if not (t2 & const.TRAP):
                return False
        elif not (t2 & (const.FLOOR | const.TUNNEL | const.DOOR | const.STAIRS | const.TRAP)):
            return False
        if r1 != r2 and c1 != c2:
            try:
                t1 = dungeon_level.get_tile(r1, c1)
                if (t1 & const.DOOR) or (t2 & const.DOOR):
                    return False
                if not dungeon_level.get_tile(r1, c2) or not dungeon_level.get_tile(r2, c1):
                    return False
            except Exception:
                return False
        return True

    def darken_room(self, dungeon_level, room_number: int, blind: bool) -> None:
        """部屋を暗くする (C版 room.c: darken_room)"""
        room = dungeon_level.get_room(room_number)
        if not room:
            return

        for row in range(room.top_row + 1, room.bottom_row):
            for col in range(room.left_col + 1, room.right_col):
                tile = dungeon_level.get_tile(row, col)

                if blind:
                    # 盲目時は全てスペース
                    self.mvaddch(row, col, ord(' '))
                else:
                    # OBJECT/STAIRS は消さない
                    if not (tile & (const.OBJECT | const.STAIRS)):
                        # detect_monster かつ MONSTER フラグあり → 消さない
                        if not (GameState.detect_monster and (tile & const.MONSTER)):
                            # IMITATES モンスターチェック（簡易: 画面に文字が残っていれば消す）
                            monster = self._object_at_monsters(dungeon_level, row, col)
                            is_imitating = monster and (monster.m_flags & const.IMITATES)
                            if not is_imitating:
                                self.mvaddch(row, col, ord(' '))
                            # 発見済み罠は '^' で再表示
                            if (tile & const.TRAP) and not (tile & const.HIDDEN):
                                self.mvaddch(row, col, ord('^'))
        self.refresh()

    def inventory(self, pack: Optional[entities.Item], mask: int, stats=None, player: Optional[entities.Player] = None) -> None:
        """インベントリを表示（C言語版 invent.c: inventory に対応）
        
        注意: Python版では player.pack が直接最初のアイテムを指す（ダミーヘッドではない）
        C言語版では rogue.pack はダミーヘッドで、rogue.pack.next_object からアイテムが始まる
        """
        if not pack:
            # メッセージを表示したいが、Messageオブジェクトが必要
            return

        # アイテムリストを作成
        # Python版: pack 自体が最初のアイテムを指す（C版の pack.next_object に相当）
        items = []
        curr = pack
        while curr:
            if curr.item_type & mask:
                desc = self.get_item_desc(curr)
                # C版: Protected(obj) ? '}' : ')'
                prot_char = '}' if (curr.item_type & const.ARMOR) and getattr(curr, 'is_protected', False) else ')'
                items.append(f" {chr(curr.ichar)}{prot_char} {desc}")
            curr = curr.next_object
            
        if not items:
            return

        # 「スペースを押してください」メッセージ
        msg = "  ＝スペースを押してください＝"
        items.append(msg)
        
        # インベントリ表示の開始列を計算（画面右側）
        # C版: col = ROGUE_COLUMNS - (maxlen + 2);
        max_len = max(self._utf8strlen(s) for s in items)
        col = const.ROGUE_COLUMNS - (max_len + 2)
        
        # C言語版と同じく、表示前に元の画面内容を保存
        # C版: for (row = 0; row < i; row++) { if (row > 0) { for (j = col; j < ROGUE_COLUMNS; j++) { descs[row - 1][j - col] = mvinch_rogue(row, j); } } }
        saved_chars = []
        for row in range(len(items)):
            if row > 0:
                line_chars = []
                for j in range(col, const.ROGUE_COLUMNS):
                    ch = self.mvinch(row, j)
                    line_chars.append(chr(ch))
                saved_chars.append(''.join(line_chars))
            else:
                saved_chars.append('')
        
        # 画面右側にオーバーレイ表示（0行目から）
        for row, item in enumerate(items):
            if row >= const.ROGUE_LINES - 1:
                break
            self.mvaddstr(row, col, item)
            self.clrtoeol()
        
        self.refresh()
        
        # キー入力を待つ（スペースまたはEnter）
        while True:
            ch = self.stdscr.getch()
            if ch == ord(' ') or ch == ord('\n') or ch == ord('\r') or ch == 27:
                break
        
        # C言語版と同じく、保存しておいた元の画面内容を復元
        # C版: move(0, 0); clrtoeol(); for (j = 1; j < i; j++) { mvaddstr_rogue(j, col, descs[j - 1]); }
        self.move(0, 0)
        self.clrtoeol()
        
        for j in range(1, len(saved_chars)):
            if j < const.ROGUE_LINES - 1:
                self.mvaddstr(j, col, saved_chars[j])
                self.clrtoeol()
        
        # C版: move(ROGUE_LINES - 1, 0); clrtoeol(); print_stats(STAT_ALL);
        self.move(const.ROGUE_LINES - 1, 0)
        self.clrtoeol()
        
        # ステータスを再描画
        if stats and player:
            stats.print_stats(player, const.STAT_ALL)
        
        self.refresh()
    
    def _utf8strlen(self, s: str) -> int:
        """UTF-8文字列の表示幅を計算（日本語は2文字幅と仮定）"""
        width = 0
        for ch in s:
            if ord(ch) > 127:
                width += 2  # 日本語などは2文字幅
            else:
                width += 1
        return width

    def get_item_desc(self, item: entities.Item) -> str:
        """アイテムの説明文を取得 (C版 invent.c: get_desc相当の condensed 版)"""
        try:
            import inventory as _inv
        except ImportError:
            try:
                from . import inventory as _inv
            except ImportError:
                _inv = None

        def _id_name(table, kind, fallback: str) -> str:
            try:
                if table is not None and 0 <= kind < len(table):
                    e = table[kind]
                    st = getattr(e, 'id_status', const.UNIDENTIFIED)
                    if st == const.IDENTIFIED and getattr(e, 'real', ''):
                        return e.real
                    if st == const.CALLED and getattr(e, 'title', ''):
                        return "「%s」と呼ばれているもの" % e.title
                    if getattr(e, 'title', ''):
                        return e.title
            except Exception:
                pass
            return fallback

        armor_names = ["布の服", "レザージャケット", "リングメイル", "スケイルメイル", "チェインメイル", "スプレンティッドメイル", "プレートメイル"]
        weapon_names = ["メイス", "長剣", "ショートボウ", "矢", "ダガー", "シュリケン", "ロングボウ", "十字架"]

        qty = "" if item.quantity <= 1 else "%d個の" % item.quantity
        suffix = ""
        try:
            if item.is_being_used:
                suffix = "(装備中)"
        except Exception:
            pass

        if item.item_type == const.GOLD:
            return "%d ゴールド" % item.quantity

        if item.item_type == const.FOOD:
            base = "食料" if item.which_kind == const.RATION else "果物"
            return "%s%s%s" % (qty, base, suffix)

        if item.item_type == const.ARMOR:
            name = armor_names[item.which_kind] if 0 <= item.which_kind < len(armor_names) else "未知の鎧"
            ench = ""
            if getattr(item, 'identified', 0) and item.d_enchant:
                ench = " [%+d]" % item.d_enchant
            return "%s%s%s%s" % (qty, name, ench, suffix)

        if item.item_type == const.WEAPON:
            name = weapon_names[item.which_kind] if 0 <= item.which_kind < len(weapon_names) else "未知の武器"
            ench = ""
            if getattr(item, 'identified', 0) and (item.hit_enchant or item.d_enchant):
                ench = " [%+d,%+d]" % (item.hit_enchant, item.d_enchant)
            return "%s%s%s%s" % (qty, name, ench, suffix)

        if item.item_type == const.SCROL:
            table = getattr(_inv, 'id_scrolls', None)
            return "%s巻物「%s」%s" % (qty, _id_name(table, item.which_kind, "何か"), suffix)
        if item.item_type == const.POTION:
            table = getattr(_inv, 'id_potions', None)
            colors = getattr(_inv, 'po_color', None)
            base = _id_name(table, item.which_kind, "")
            if not base and colors and 0 <= item.which_kind < len(colors):
                base = "%s色" % colors[item.which_kind]
            return "%s%sの薬%s" % (qty, base or "何か", suffix)
        if item.item_type == const.WAND:
            table = getattr(_inv, 'id_wands', None)
            base = _id_name(table, item.which_kind, "何かの杖")
            charges = " [%d回]" % item.class_ if item.class_ > 0 else ""
            return "%s%s%s%s" % (qty, base, charges, suffix)
        if item.item_type == const.RING:
            table = getattr(_inv, 'id_rings', None)
            return "%s%sの指輪%s" % (qty, _id_name(table, item.which_kind, "何か"), suffix)
        if item.item_type == const.AMULET:
            return "イェンダーのアミュレット"

        return "未知のアイテム"


# ============================================================================
# Messageクラス - メッセージシステム
# ============================================================================

class Message:
    """メッセージシステムクラス"""

    def __init__(self, display: Display):
        """初期化"""
        self.display = display
        self.msg_line: str = ""
        self.msg_col: int = 0
        self.msg_cleared: bool = True
        self.hunger_str: str = ""

    def message(self, msg: str, intrpt: bool = False) -> None:
        """メッセージを表示（C言語版 message.c: message に対応）"""
        # C版 message.c:40-46前置：割込指定時は割込順序を進める
        if intrpt:
            try:
                GameState.interrupted = True
            except Exception:
                pass
        if not self.msg_cleared:
            # 前のメッセージが残っている場合は --more-- を表示
            self.display.mvaddstr(const.MIN_ROW - 1, self.msg_col, " ［続く］")
            self.display.clrtoeol()
            self.display.refresh()
            self._wait_for_ack()
            # メッセージ行をクリア (C版 check_message相当)
            self._check_message()

        # 新しいメッセージを表示
        self.msg_line = msg
        self.display.move(const.MIN_ROW - 1, 0)
        self.display.clrtoeol()  # 先に行をクリア
        self.display.mvaddstr(const.MIN_ROW - 1, 0, msg)
        self.display.addch(ord(' '))  # C言語版ではメッセージの後にスペースを追加
        self.display.refresh()
        self.msg_cleared = False
        # 日本語文字数を考慮した長さ計算（簡易版）
        self.msg_col = self.display._utf8strlen(msg)
        
    def remessage(self) -> None:
        """最後のメッセージを再表示"""
        if self.msg_line:
            self.message(self.msg_line, False)

    def _check_message(self) -> None:
        """メッセージをクリア"""
        if self.msg_cleared:
            return
        self.display.move(const.MIN_ROW - 1, 0)
        self.display.clrtoeol()
        self.display.refresh()
        self.msg_cleared = True

    def _wait_for_ack(self) -> None:
        """確認を待つ（C版 message.c: wait_for_ack）"""
        # 全自動運転中は人間待ちしない。後続入力は消費せず残す
        if _ai_auto_ack_enabled is not None and _ai_auto_ack_enabled():
            return
        while True:
            ch = self.display.getch()
            if ch == ord(' ') or ch == ord('\n') or ch == ord('\r') or ch == 27:
                break
            if ch == ord('X'):
                # AI自動プレイ中の強制終了要求として記録し、待ちを解く。
                # 実際の終了はGame._get_input/AIDriverがForceQuitで行う
                if _ai_request_force_quit is not None:
                    _ai_request_force_quit()
                break

    def clear(self) -> None:
        """メッセージをクリア"""
        self._check_message()

    def set_hunger(self, hunger_str: str) -> None:
        """空腹状態を設定"""
        self.hunger_str = hunger_str


# ============================================================================
# Statsクラス - ステータス表示
# ============================================================================

class Stats:
    """ステータス表示クラス"""

    def __init__(self, display: Display, message: Message):
        """初期化"""
        self.display = display
        self.message = message

    def print_stats(self, player: entities.Player, stat_mask: int) -> None:
        """ステータスを表示"""
        row = const.ROGUE_LINES - 1
        label = (stat_mask & const.STAT_LABEL) != 0

        # レベル
        if stat_mask & const.STAT_LEVEL:
            if label:
                self.display.mvaddstr(row, 0, "Level:")
            buf = str(player.dungeon_level)
            self.display.mvaddstr(row, 7, buf)
            self._pad(buf, 2)

        # 金塊
        if stat_mask & const.STAT_GOLD:
            if label:
                if player.gold > const.MAX_GOLD:
                    player.gold = const.MAX_GOLD
                self.display.mvaddstr(row, 10, "Gold:")
            buf = str(player.gold)
            self.display.mvaddstr(row, 16, buf)
            self._pad(buf, 6)

        # HP
        if stat_mask & const.STAT_HP:
            if label:
                self.display.mvaddstr(row, 23, "HP:")
            # C版: label外で無条件に丸める
            if player.hp_max > const.MAX_HP:
                player.hp_current -= (player.hp_max - const.MAX_HP)
                player.hp_max = const.MAX_HP
            buf = f"{player.hp_current}({player.hp_max})"
            self.display.mvaddstr(row, 27, buf)
            self._pad(buf, 8)

        # 強さ
        if stat_mask & const.STAT_STRENGTH:
            if label:
                self.display.mvaddstr(row, 36, "Str:")
            # C版: label外で無条件に丸める
            if player.str_max > const.MAX_STRENGTH:
                player.str_current -= (player.str_max - const.MAX_STRENGTH)
                player.str_max = const.MAX_STRENGTH
            # C版: rogue.str_current + add_strength
            str_display = player.str_current + special_actions.add_strength
            buf = f"{str_display}({player.str_max})"
            self.display.mvaddstr(row, 41, buf)
            self._pad(buf, 6)

        # 防御
        if stat_mask & const.STAT_ARMOR:
            if label:
                self.display.mvaddstr(row, 48, "Arm:")
            # C版: label外で無条件に丸める
            if player.armor and player.armor.d_enchant > const.MAX_ARMOR:
                player.armor.d_enchant = const.MAX_ARMOR
            buf = str(player.get_armor_class())
            self.display.mvaddstr(row, 53, buf)
            self._pad(buf, 2)

        # 経験値
        if stat_mask & const.STAT_EXP:
            if label:
                self.display.mvaddstr(row, 56, "Exp:")
            buf = f"{player.exp}/{player.exp_points}"
            self.display.mvaddstr(row, 61, buf)
            self._pad(buf, 11)

        # 空腹状態 (C版: 無条件描画＋行末消去)
        if stat_mask & const.STAT_HUNGER:
            if self.message.hunger_str:
                self.display.mvaddstr(row, 73, self.message.hunger_str)
            else:
                self.display.mvaddstr(row, 73, " " * 7)
            try:
                self.display.clrtoeol()
            except Exception:
                pass

        self.display.refresh()

    def _pad(self, s: str, n: int) -> None:
        """文字列をパディング"""
        for i in range(len(s), n):
            self.display.addch(ord(' '))

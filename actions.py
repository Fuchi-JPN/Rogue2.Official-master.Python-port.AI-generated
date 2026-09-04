"""
actions.py - 移動処理とアクション
src/move.c, src/trap.c から移植

移動、衝突判定、罠の処理などを実装します。
"""

from typing import Optional, Tuple
from enum import IntEnum
import logging

try:
    from . import const, utils
    from .entities import Player, Monster, Item, Trap
    from .dungeon import DungeonLevel, get_direction_offset
    from .text_resources import get_message
    from .game_state import GameState
    from .combat import Combat, MonsterAI
except ImportError:
    import const, utils
    import entities
    import dungeon
    from text_resources import get_message
    from game_state import GameState
    from combat import Combat, MonsterAI
    Player = entities.Player
    Monster = entities.Monster
    Item = entities.Item
    Trap = entities.Trap
    DungeonLevel = dungeon.DungeonLevel
    get_direction_offset = dungeon.get_direction_offset

logger = logging.getLogger(__name__)


# 移動結果
class MoveResult(IntEnum):
    """移動結果"""
    MOVE_FAILED = 0
    MOVED = 1
    STOPPED_ON_SOMETHING = 2


# グローバル変数は GameState に集約
_GS = GameState

def __getattr__(name):
    _proxy = {
        'm_moves': 'm_moves', 'jump': 'jump', 'bent_passage': 'bent_passage',
        'pass_go': 'pass_go', 'bear_trap': 'bear_trap', 'trap_door': 'trap_door',
    }
    if name in _proxy:
        return getattr(_GS, _proxy[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __setattr__(name, value):
    _proxy = {
        'm_moves': 'm_moves', 'jump': 'jump', 'bent_passage': 'bent_passage',
        'pass_go': 'pass_go', 'bear_trap': 'bear_trap', 'trap_door': 'trap_door',
    }
    if name in _proxy:
        setattr(_GS, _proxy[name], value)
    else:
        globals()[name] = value

# 罠のメッセージ（簡易版、後でメッセージファイルから読み込むようにする）
TRAP_MESSAGES = {
    const.TRAP_DOOR: ("落とし穴", "床が突然崩れ落ちた！"),
    const.BEAR_TRAP: ("熊の罠", "熊の罠にかかった！"),
    const.TELE_TRAP: ("テレポートの罠", "突然、場所が変わった！"),
    const.DART_TRAP: ("毒矢の罠", "毒矢が飛んできた！"),
    const.SLEEPING_GAS_TRAP: ("眠りガスの罠", "眠りガスが噴き出した！"),
    const.RUST_TRAP: ("錆の罠", "突然、錆が吹き出した！"),
}


class Movement:
    """移動処理クラス"""

    @property
    def halluc(self): return GameState.halluc
    @halluc.setter
    def halluc(self, v): GameState.halluc = v

    @property
    def blind(self): return GameState.blind
    @blind.setter
    def blind(self, v): GameState.blind = v

    @property
    def confused(self): return GameState.confused
    @confused.setter
    def confused(self, v): GameState.confused = v

    @property
    def levitate(self): return GameState.levitate
    @levitate.setter
    def levitate(self, v): GameState.levitate = v

    @property
    def haste_self(self): return GameState.haste_self
    @haste_self.setter
    def haste_self(self, v): GameState.haste_self = v

    @property
    def auto_search(self): return GameState.auto_search
    @auto_search.setter
    def auto_search(self, v): GameState.auto_search = v

    @property
    def stealthy(self): return GameState.stealthy
    @stealthy.setter
    def stealthy(self, v): GameState.stealthy = v

    @property
    def being_held(self): return GameState.being_held
    @being_held.setter
    def being_held(self, v): GameState.being_held = v

    @property
    def r_teleport(self): return GameState.r_teleport
    @r_teleport.setter
    def r_teleport(self, v): GameState.r_teleport = v

    @property
    def e_rings(self): return GameState.e_rings
    @e_rings.setter
    def e_rings(self, v): GameState.e_rings = v

    @property
    def regeneration(self): return GameState.regeneration
    @regeneration.setter
    def regeneration(self, v): GameState.regeneration = v

    @property
    def ring_exp(self): return GameState.ring_exp
    @ring_exp.setter
    def ring_exp(self, v): GameState.ring_exp = v

    @property
    def sustain_strength(self): return GameState.sustain_strength
    @sustain_strength.setter
    def sustain_strength(self, v): GameState.sustain_strength = v

    @property
    def cur_level(self): return GameState.cur_level
    @cur_level.setter
    def cur_level(self, v): GameState.cur_level = v

    @property
    def max_level(self): return GameState.max_level
    @max_level.setter
    def max_level(self, v): GameState.max_level = v

    @property
    def party_room(self): return GameState.party_room
    @party_room.setter
    def party_room(self, v): GameState.party_room = v

    @property
    def interrupted(self): return GameState.interrupted
    @interrupted.setter
    def interrupted(self, v): GameState.interrupted = v

    def __init__(self, player: Player, dungeon: DungeonLevel, display=None, message=None, game=None):
        self.player = player
        self.dungeon = dungeon
        self.display = display
        self.msg = message
        self.game = game
        GameState.cur_room = self._get_room_number(player.row, player.col)
        GameState.cur_room = GameState.cur_room
        # _heal関数の静的変数（C言語版から移植）
        self._heal_exp = -1
        self._heal_n = 0
        self._heal_c = 0
        self._heal_alt = False
        # _check_hunger関数の静的変数（C言語版から移植）
        self._move_left_cou = 0
        # _search関数の静的変数（C言語版から移植）
        self._reg_search = False

    def one_move_rogue(self, dirch: str, pickup: bool) -> MoveResult:
        """1回の移動処理"""

        # C言語版では、プレイヤーが移動を開始するとメッセージをクリアする
        if self.msg:
            self.msg.clear()

        r = self.player.row
        c = self.player.col
        GameState.bent_passage = False

        if self.confused:
            dirch = self._gr_dir()

        r, c = self._get_dir_rc(dirch, r, c, 1)
        row, col = r, c

        # 詳細なデバッグログ
        current_tile = self.dungeon.dungeon[self.player.row][self.player.col]
        target_tile = self.dungeon.dungeon[row][col]
        logger.debug(f"=" * 60)
        logger.debug(f"[one_move_rogue] dirch='{dirch}', pickup={pickup}")
        logger.debug(f"  Current: ({self.player.row}, {self.player.col}), tile={current_tile}")
        logger.debug(f"  Target:  ({row}, {col}), tile={target_tile}")
        logger.debug(f"  Target tile breakdown: TUNNEL={bool(target_tile & const.TUNNEL)}, FLOOR={bool(target_tile & const.FLOOR)}, DOOR={bool(target_tile & const.DOOR)}, HIDDEN={bool(target_tile & const.HIDDEN)}")

        if not self._can_move(self.player.row, self.player.col, row, col):
            logger.debug(f"[one_move_rogue] MOVE FAILED by _can_move")
            if (GameState.cur_room == const.PASSAGE and not self.blind and not self.confused
                    and dirch not in "yubn"):
                GameState.bent_passage = True
            return MoveResult.MOVE_FAILED

        if self.being_held or GameState.bear_trap:
            if not (self.dungeon.dungeon[row][col] & const.MONSTER):
                if self.being_held:
                    if self.msg:
                        self.msg.message(get_message(67), 1)  # "怪物につかまえられて、逃げられない。"
                else:
                    if self.msg:
                        self.msg.message(get_message(68), 0)  # "熊のわなが、なかなかはずれない。"
                    self.reg_move()
                return MoveResult.MOVE_FAILED

        if self.r_teleport:
            if utils.rand_percent(const.R_TELE_PERCENT):
                self._tele()
                return MoveResult.STOPPED_ON_SOMETHING

        if self.dungeon.dungeon[row][col] & const.MONSTER:
            monster = self._monster_at(row, col)
            if monster:
                self.rogue_hit(monster)
                self.reg_move()
                return MoveResult.MOVE_FAILED
            else:
                # モンスターが存在しない場合はフラグをクリア（ゴーストフラグ修正）
                # C言語版ではモンスター死亡時にフラグをクリアするが、
                # 何らかの理由でフラグが残っている場合の安全策
                self.dungeon.dungeon[row][col] &= ~const.MONSTER
                logger.info(f"Cleared stale MONSTER flag at ({row}, {col})")

        # 移動前の座標を保存
        old_row, old_col = self.player.row, self.player.col
        
        # プレイヤーの位置を更新 (描画関数のために先に更新)
        self.player.row = row
        self.player.col = col

        # ドアと通路の処理
        if self.dungeon.dungeon[row][col] & const.DOOR:
            if GameState.cur_room == const.PASSAGE:
                GameState.cur_room = self._get_room_number(row, col)
                if self.display:
                    self.display.light_up_room(self.dungeon, self.player, GameState.cur_room)
                self.wake_room(GameState.cur_room, True, row, col)
            else:
                if self.display:
                    self.display.light_passage(self.dungeon, self.player, row, col)
        elif (self.dungeon.dungeon[old_row][old_col] & const.DOOR) and (self.dungeon.dungeon[row][col] & const.TUNNEL):
            if self.display:
                self.dungeon.dungeon[row][col] |= const.MAPPED
                self.display.light_passage(self.dungeon, self.player, row, col)
            self.wake_room(GameState.cur_room, False, old_row, old_col)
            if self.display:
                self.display.darken_room(self.dungeon, GameState.cur_room, self.blind > 0)
            GameState.cur_room = const.PASSAGE
        elif self.dungeon.dungeon[row][col] & const.TUNNEL:
            if self.display:
                # 足元のMAPPEDフラグを立てる
                self.dungeon.dungeon[row][col] |= const.MAPPED
                self.display.light_passage(self.dungeon, self.player, row, col)
            pass
            
        # 画面更新（移動元を消去し、移動先を描画）
        if self.display:
            # 移動元を消去（元の地形を描画）
            # light_up_room等が呼ばれた場合でも、ここで消去しても問題ない（はず）
            # ただしlight_up_roomが呼ばれた場合、既に全体が再描画されている
            # 効率化のためにはフラグ管理が必要だが、一旦単純に上書きする
            
            # 移動元
            if not (self.dungeon.dungeon[row][col] & const.DOOR and GameState.cur_room != const.PASSAGE): 
                 # 部屋に入った場合(light_up_room)以外は消去必要？
                 # いや、light_up_roomは部屋全体を描く。移動元が通路なら消去必要。
                 # 移動元が部屋なら、light_up_roomには含まれない（別の部屋/通路）
                 # 安全のため常に消去
                 pass

            ch = self.display.get_dungeon_char(self.dungeon, old_row, old_col)
            self.display.mvaddch(old_row, old_col, ord(ch))
            
            # 移動先
            # light_passageは#を描くので、その後に@を描く必要あり
            # light_up_roomは@を描くが、ここで上書きしても問題ない
            self.display.mvaddch(row, col, self.player.fchar)

        # アイテムの処理
        if self.dungeon.dungeon[row][col] & const.OBJECT:
            if self.levitate:
                if pickup:
                    return MoveResult.STOPPED_ON_SOMETHING
                # C版: levitate時はアイテムを説明だけして拾わない
                obj = self._object_at(row, col)
                if obj and self.msg:
                    desc = self._get_obj_desc(obj)
                    self.msg.message(desc, 0)
                self.reg_move()
                return MoveResult.MOVED

            obj = self._object_at(row, col)
            if obj:
                if pickup:
                    self.pick_up(row, col)
                self.reg_move()
                return MoveResult.STOPPED_ON_SOMETHING

        # 罠、階段、ドアの処理
        if self.dungeon.dungeon[row][col] & (const.DOOR | const.STAIRS | const.TRAP):
            if (not self.levitate) and (self.dungeon.dungeon[row][col] & const.TRAP):
                self._trap_player(row, col)
            if (self.dungeon.dungeon[row][col] & const.STAIRS) and self.msg:
                self.msg.message("下り階段がある")
            self.reg_move()
            return MoveResult.STOPPED_ON_SOMETHING

        if self.reg_move():
            return MoveResult.STOPPED_ON_SOMETHING

        return MoveResult.STOPPED_ON_SOMETHING if self.confused else MoveResult.MOVED

    def multiple_move_rogue(self, dirch: str):
        """連続移動（C版 move.c: multiple_move_rogue）"""
        # viキーバインド（Ctrl+hjkl 等）
        # C: do { ... } while (!next_to_something(row, col));
        if dirch in "\010\012\013\014\031\025\016\002":
            dirch = chr(ord(dirch) + 96)
            while True:
                row = self.player.row
                col = self.player.col
                m = self.one_move_rogue(dirch, True)
                if m == MoveResult.STOPPED_ON_SOMETHING or self.interrupted:
                    break
                if m != MoveResult.MOVE_FAILED:
                    # C版: 成功時は next_to_something で継続判定
                    if self._next_to_something(row, col):
                        break
                    continue
                # pass_goリトライロジック（C版 209-239行目）
                if not GameState.pass_go or not GameState.bent_passage:
                    break
                # 4方向（hjkl）をチェックして代替経路を探す
                n = 0
                ch = dirch
                directions = "hjkl"
                for i, d in enumerate(directions):
                    r, c = self.player.row, self.player.col
                    r, c = self._get_dir_rc(d, r, c, 1)
                    # 反対方向（dir[3-i]）を除外
                    if self.is_passable(r, c) and dirch != directions[3 - i]:
                        n += 1
                        ch = d
                # 通過可能な方向が1つだけなら、その方向に変更してリトライ
                if n == 1:
                    dirch = ch
                    continue
                break
        # 大文字キーバインド（HJKL 等）
        elif dirch in "HJKLBYUN":
            dirch = chr(ord(dirch) + 32)
            while True:
                row = self.player.row
                col = self.player.col
                m = self.one_move_rogue(dirch, True)
                if self.interrupted:
                    break
                if m == MoveResult.MOVED:
                    if self._next_to_something(row, col):
                        break
                    continue
                if m != MoveResult.MOVE_FAILED:
                    break
                # pass_goリトライロジック
                if not GameState.pass_go or not GameState.bent_passage:
                    break
                n = 0
                ch = dirch
                directions = "hjkl"
                for i, d in enumerate(directions):
                    r, c = self.player.row, self.player.col
                    r, c = self._get_dir_rc(d, r, c, 1)
                    if self.is_passable(r, c) and dirch != directions[3 - i]:
                        n += 1
                        ch = d
                if n == 1:
                    dirch = ch
                    continue
                break

    def is_passable(self, row: int, col: int) -> bool:
        """通過可能か判定"""
        import sys
        if (row < const.MIN_ROW or row > (const.ROGUE_LINES - 2)
                or col < 0 or col > (const.ROGUE_COLUMNS - 1)):
            logger.debug(f"[is_passable] OUT_OF_BOUNDS: ({row}, {col})")
            return False
        tile = self.dungeon.dungeon[row][col]
        if tile & const.HIDDEN:
            result = bool(tile & const.TRAP)
            logger.debug(f"[is_passable] HIDDEN tile at ({row}, {col}): tile={tile}, is_trap={result}")
            return result
        result = bool(tile & (const.FLOOR | const.TUNNEL | const.DOOR | const.STAIRS | const.TRAP))
        logger.debug(f"[is_passable] ({row}, {col}): tile={tile}, TUNNEL={bool(tile & const.TUNNEL)}, FLOOR={bool(tile & const.FLOOR)}, DOOR={bool(tile & const.DOOR)}, result={result}")
        return result

    def _next_to_something(self, drow: int, dcol: int) -> bool:
        """何かに隣接しているか (C版 move.c: next_to_something)"""
        if self.confused:
            return True
        if self.blind:
            return False

        i_end = 1 if self.player.row < (const.ROGUE_LINES - 2) else 0
        j_end = 1 if self.player.col < (const.ROGUE_COLUMNS - 1) else 0

        pass_count = 0
        for i in range((-1 if self.player.row > const.MIN_ROW else 0), i_end + 1):
            for j in range((-1 if self.player.col > 0 else 0), j_end + 1):
                if (i == 0 and j == 0) or (self.player.row + i == drow and self.player.col + j == dcol):
                    continue
                row = self.player.row + i
                col = self.player.col + j
                s = self.dungeon.dungeon[row][col]
                if s & const.HIDDEN:
                    continue
                if s & (const.MONSTER | const.OBJECT | const.STAIRS):
                    # C版: 旧-新が直線上で折れた場合は素通り (continue)
                    if ((row == drow or col == dcol) and
                            not (row == self.player.row or col == self.player.col)):
                        continue
                    return True
                if s & const.TRAP:
                    # HIDDENは上部で除外済み。直交継続条件は上記と同様
                    if ((row == drow or col == dcol) and
                            not (row == self.player.row or col == self.player.col)):
                        continue
                    return True
                if ((i - j == 1) or (i - j == -1)) and (s & const.TUNNEL):
                    # C版: 斜めTUNNELは2個で停止
                    pass_count += 1
                    if pass_count > 1:
                        return True
                if (s & const.DOOR) and ((i == 0) or (j == 0)):
                    return True
        return False

    def _can_move(self, row1: int, col1: int, row2: int, col2: int) -> bool:
        """移動可能か判定"""
        logger.debug(f"[_can_move] Checking move from ({row1}, {col1}) to ({row2}, {col2})")
        
        # is_passableチェック
        passable = self.is_passable(row2, col2)
        if not passable:
            logger.debug(f"[_can_move] BLOCKED: is_passable({row2}, {col2}) = False")
            return False
        
        # 斜め移動のチェック
        if (row1 != row2) and (col1 != col2):
            tile1 = self.dungeon.dungeon[row1][col1]
            tile2 = self.dungeon.dungeon[row2][col2]
            tile_corner1 = self.dungeon.dungeon[row1][col2]
            tile_corner2 = self.dungeon.dungeon[row2][col1]
            
            logger.debug(f"[_can_move] Diagonal move check:")
            logger.debug(f"  tile1({row1},{col1})={tile1}, is_DOOR={bool(tile1 & const.DOOR)}")
            logger.debug(f"  tile2({row2},{col2})={tile2}, is_DOOR={bool(tile2 & const.DOOR)}")
            logger.debug(f"  corner1({row1},{col2})={tile_corner1}, is_NOTHING={tile_corner1 == 0}")
            logger.debug(f"  corner2({row2},{col1})={tile_corner2}, is_NOTHING={tile_corner2 == 0}")
            
            if (tile1 & const.DOOR
                    or tile2 & const.DOOR
                    or not tile_corner1
                    or not tile_corner2):
                logger.debug(f"[_can_move] BLOCKED: Diagonal move blocked by door or empty corner")
                return False
        
        logger.debug(f"[_can_move] OK: Move allowed")
        return True

    def is_direction(self, c: str) -> bool:
        """方向キーか判定（C版準拠：小文字＝1歩、大文字＝連続移動）"""
        return c in "hjklbyunHJKLBYUN"

    def check_hunger(self, messages_only: bool) -> bool:
        """空腹チェック"""
        fainted = False

        if self.player.moves_left == const.HUNGRY:
            if self.msg:
                self.msg.message(get_message(72), 0)  # "空腹になってきた。"
        if self.player.moves_left == const.WEAK:
            if self.msg:
                self.msg.message(get_message(74), 1)  # "空腹のせいで力がなくなってきた。"
        if self.player.moves_left <= const.FAINT:
            if self.player.moves_left == const.FAINT:
                if self.msg:
                    self.msg.message(get_message(76), 1)  # "空腹で、もう死にそうだ。"
            n = utils.get_rand(0, const.FAINT - self.player.moves_left)
            if n > 0:
                fainted = True
                if utils.rand_percent(40):
                    self.player.moves_left += 1
                if self.msg:
                    self.msg.message(get_message(77), 1)  # "空腹で、目がくらくらする。"
                for _ in range(n):
                    if utils.coin_toss():
                        self.mv_mons()
                if self.msg:
                    self.msg.message(get_message(66), 1)  # "ようやく体が自由になった。"

        if messages_only:
            return fainted

        if self.player.moves_left <= const.STARVE:
            if self.game:
                self.game.killed_by(None, const.STARVATION)
            return fainted

        if self.msg:
            if self.player.moves_left <= const.FAINT:
                self.msg.set_hunger(get_message(75))  # "瀕死"
            elif self.player.moves_left <= const.WEAK:
                self.msg.set_hunger(get_message(73))  # "飢餓"
            elif self.player.moves_left <= const.HUNGRY:
                self.msg.set_hunger(get_message(71))  # "空腹"
            else:
                self.msg.set_hunger("")

        # 食べ物の指輪による影響 (C版 move.c:444-470。move_left_couはGameState集約)
        match self.e_rings:
            case -1:
                self.player.moves_left -= GameState.move_left_cou
            case 0:
                self.player.moves_left -= 1
            case 1:
                self.player.moves_left -= 1
                self.check_hunger(True)
                self.player.moves_left -= GameState.move_left_cou
            case 2:
                self.player.moves_left -= 1
                self.check_hunger(True)
                self.player.moves_left -= 1

        GameState.move_left_cou ^= 1
        return fainted

    def reg_move(self) -> bool:
        """移動後の処理 (C版 move.c: reg_move)"""

        # C版: if ((rogue.moves_left <= HUNGRY) || (cur_level >= max_level))
        if (self.player.moves_left <= const.HUNGRY) or (self.cur_level >= self.max_level):
            fainted = self.check_hunger(False)
        else:
            fainted = False

        # C版: mv_mons();
        self.mv_mons()

        # C版: if (++m_moves >= 120) { m_moves = 0; wanderer(); }
        GameState.m_moves += 1
        if GameState.m_moves >= 120:
            GameState.m_moves = 0
            self._wanderer()

        # C版: if (halluc) { if (!(--halluc)) { unhallucinate(); } else { hallucinate(); } }
        if self.halluc:
            self.halluc -= 1
            if not self.halluc:
                self._unhallucinate()
            else:
                self._hallucinate()

        # C版: if (blind) { if (!(--blind)) { unblind(); } }
        if self.blind:
            self.blind -= 1
            if not self.blind:
                self._unblind()

        # C版: if (confused) { if (!(--confused)) { unconfuse(); } }
        if self.confused:
            self.confused -= 1
            if not self.confused:
                self._unconfuse()

        # C版: if (bear_trap) { bear_trap--; }
        if GameState.bear_trap:
            GameState.bear_trap -= 1

        # C版: if (levitate) { if (!(--levitate)) { message(mesg[78], 1); if (dungeon[rogue.row][rogue.col] & TRAP) { trap_player(rogue.row, rogue.col); } } }
        if self.levitate:
            self.levitate -= 1
            if not self.levitate:
                if self.msg:
                    self.msg.message(get_message(78), 1)  # "ようやく地面に足がついた。"
                if self.dungeon.dungeon[self.player.row][self.player.col] & const.TRAP:
                    self._trap_player(self.player.row, self.player.col)

        # C版: if (haste_self) { if (!(--haste_self)) { message(mesg[79], 0); } }
        if self.haste_self:
            self.haste_self -= 1
            if not self.haste_self:
                if self.msg:
                    self.msg.message(get_message(79), 0)  # "素早くなる薬の効き目がなくなった。"

        # C版: heal();
        self._heal()

        # C版: if (auto_search > 0) { search(auto_search, auto_search); }
        if self.auto_search > 0:
            self._search(self.auto_search, True)

        return fainted

    def rest(self, count: int):
        """休憩"""
        self.interrupted = False
        for i in range(count):
            if self.interrupted:
                break
            self.reg_move()

    def _gr_dir(self) -> str:
        """ランダム方向"""
        return "jklhyubn"[utils.get_rand(1, 8) - 1]

    def _heal(self):
        """回復（C版 move.c: heal。static変数はGameStateに集約）"""
        na = [0, 20, 18, 17, 14, 13, 10, 9, 8, 7, 4, 3]

        if self.player.hp_current == self.player.hp_max:
            GameState.heal_c = 0
            return

        if self.player.exp != GameState.heal_exp:
            GameState.heal_exp = self.player.exp
            if GameState.heal_exp < 1 or GameState.heal_exp > 11:
                GameState.heal_n = 2
            else:
                GameState.heal_n = na[GameState.heal_exp]

        if GameState.heal_c + 1 >= GameState.heal_n:
            GameState.heal_c = 0
            self.player.hp_current += 1
            GameState.heal_alt = not GameState.heal_alt
            if GameState.heal_alt:
                self.player.hp_current += 1
            self.player.hp_current += self.regeneration
            if self.player.hp_current > self.player.hp_max:
                self.player.hp_current = self.player.hp_max
            # C版: print_stats(STAT_HP);
            if self.game:
                self.game._print_stats(const.STAT_HP)
        else:
            GameState.heal_c += 1

    def _get_dir_rc(self, dirch: str, row: int, col: int, add: int) -> Tuple[int, int]:
        """方向から座標変化を取得"""
        # 文字列から方向への変換
        # C言語版 src/hit.c get_dir_rc と一致させる
        dir_map = {
            'h': const.LEFT,       # 左
            'j': const.DOWN,       # 下
            'k': const.UPWARD,     # 上
            'l': const.RIGHT,      # 右
            'y': const.LEFTUP,     # 左上 (row--, col--)
            'u': const.UPRIGHT,    # 右上 (row--, col++) ← 修正: DOWNLEFTからUPRIGHTに変更
            'b': const.DOWNLEFT,   # 左下 (row++, col--) ← 修正: UPRIGHTからDOWNLEFTに変更
            'n': const.RIGHTDOWN,  # 右下 (row++, col++)
        }
        direction = dir_map.get(dirch, const.RIGHT)
        dr, dc = get_direction_offset(direction)
        return row + dr * add, col + dc * add

    def _get_room_number(self, row: int, col: int) -> int:
        """部屋番号を取得"""
        for i, room in enumerate(self.dungeon.rooms):
            if (room.top_row <= row <= room.bottom_row
                    and room.left_col <= col <= room.right_col):
                return i
        return const.NO_ROOM

    def _object_at(self, row: int, col: int) -> Optional[Item]:
        """指定位置のアイテムを取得"""
        obj = self.dungeon.level_objects
        while obj:
            if obj.row == row and obj.col == col:
                return obj
            obj = obj.next_object
        return None

    def _get_obj_desc(self, obj: Item) -> str:
        """アイテムの簡易説明 (C版 move.c MOVE_ON分岐)"""
        type_names = {
            const.FOOD: "食料", const.WEAPON: "武器", const.ARMOR: "防具",
            const.POTION: "ポーション", const.SCROL: "巻物",
            const.WAND: "杖", const.RING: "指輪", const.AMULET: "アミュレット",
        }
        return type_names.get(obj.item_type, "何か")

    def _trap_player(self, row: int, col: int):
        """プレイヤーが罠にかかる"""

        t = self._trap_at(row, col)
        if t == const.NO_TRAP:
            return

        self.dungeon.dungeon[row][col] &= ~const.HIDDEN

        if utils.rand_percent(self.player.exp + self.ring_exp):
            if self.msg:
                self.msg.message(get_message(228), 1)  # "危うく、わなにはまるところだった。"
            return

        match t:
            case const.TRAP_DOOR:
                GameState.trap_door = True
                GameState.new_level_message = get_message(217)  # "急に床がくずれ、足元から落ちてしまった！"
            case const.BEAR_TRAP:
                if self.msg:
                    self.msg.message(get_message(219), 1)  # "熊のわなにつかまった！"
                GameState.bear_trap = utils.get_rand(4, 7)
            case const.TELE_TRAP:
                if self.display:
                    self.display.mvaddch(self.player.row, self.player.col, ord('^'))
                self._tele()
            case const.DART_TRAP:
                if self.msg:
                    self.msg.message(get_message(223), 1)  # "小さな投げ矢が飛んできて、肩にささった！"
                damage = utils.roll_damage("1d6")
                self.player.hp_current -= damage
                if self.player.hp_current <= 0:
                    self.player.hp_current = 0
                if (not self.sustain_strength and utils.rand_percent(40)
                        and self.player.str_current >= 3):
                    self.player.str_current -= 1
                if self.game:
                    self.game._print_stats(const.STAT_HP | const.STAT_STRENGTH)
                if self.player.hp_current <= 0:
                    if self.game:
                        self.game.killed_by(None, const.POISON_DART)
            case const.SLEEPING_GAS_TRAP:
                if self.msg:
                    self.msg.message(get_message(225), 1)  # "不思議なもやにつつまれ、眠り込んでしまった！"
                self._take_a_nap()
            case const.RUST_TRAP:
                if self.msg:
                    self.msg.message(get_message(227), 1)  # "頭の上から大量の水が降ってきた！"
                self._rust(None)

    def _trap_at(self, row: int, col: int) -> int:
        """指定位置の罠の種類を取得"""
        for trap in self.dungeon.traps:
            if trap.trap_row == row and trap.trap_col == col:
                return trap.trap_type
        return const.NO_TRAP

    def pick_up(self, row: int, col: int) -> None:
        """アイテムを拾う（C言語版 pack.c: pick_up に対応）"""
        obj = self._object_at(row, col)
        if not obj:
            return

        # 怖がらせの巻物の特殊処理（C版 pack.c:86-96）
        if (obj.item_type == const.SCROL and obj.which_kind == const.SCARE_MONSTER
                and obj.picked_up):
            if self.msg:
                self.msg.message(get_message(86), 0)  # "モンスター除けの巻物は、床で役に立たなくなった。"
            self.dungeon.dungeon[row][col] &= ~const.OBJECT
            self._remove_object_from_level(obj)
            # C版: id_scrolls[SCARE_MONSTER].id_status = IDENTIFIED
            try:
                from . import inventory as inv_module
            except ImportError:
                import inventory as inv_module
            if inv_module.id_scrolls[const.SCARE_MONSTER].id_status == const.UNIDENTIFIED:
                inv_module.id_scrolls[const.SCARE_MONSTER].id_status = const.IDENTIFIED
            return

        # 金の処理（C版 pack.c:97-102, kick_into_pack:581-583）
        if obj.item_type == const.GOLD:
            self.player.gold += obj.quantity
            self.dungeon.dungeon[row][col] &= ~const.OBJECT
            self._remove_object_from_level(obj)
            if self.game:
                self.game._print_stats(const.STAT_GOLD)
            # C版 kick_into_pack: 金の場合はget_descしてmessageを表示
            if self.msg and self.display:
                desc = self.display.get_item_desc(obj)
                self.msg.message(desc, 0)
            return

        # インベントリがいっぱいかチェック（C版 pack.c:104-107）
        if self._pack_count(obj) >= const.MAX_PACK_COUNT:
            if self.msg:
                self.msg.message(get_message(87), 1)  # "荷物がいっぱいで、これ以上持てない。"
            return

        # ダンジョンのリストから削除
        self.dungeon.dungeon[row][col] &= ~const.OBJECT
        self._remove_object_from_level(obj)

        # 重複チェックと追加（C版 pack.c:109-111）
        obj = self._add_to_pack(obj, True)
        obj.picked_up = 1

        if self.msg:
            desc = self.display.get_item_desc(obj) if self.display else "アイテム"
            self.msg.message(f"{desc} を拾った ({chr(obj.ichar)})")

    def _remove_object_from_level(self, obj: Item) -> None:
        """レベルオブジェクトリストから削除（C版 pack.c: take_from_pack）"""
        prev = None
        curr = self.dungeon.level_objects
        while curr:
            if curr == obj:
                if prev:
                    prev.next_object = curr.next_object
                else:
                    self.dungeon.level_objects = curr.next_object
                return
            prev = curr
            curr = curr.next_object

    def _pack_count(self, new_obj: Optional[Item] = None) -> int:
        """インベントリ内のアイテム数をカウント（C版 pack.c: pack_count）"""
        count = 0
        obj = self.player.pack

        while obj:
            if obj.item_type != const.WEAPON:
                count += obj.quantity
            elif not new_obj:
                count += 1
            elif (new_obj.item_type != const.WEAPON or
                  (obj.which_kind not in (const.ARROW, const.DAGGER, const.DART, const.SHURIKEN)) or
                  (new_obj.which_kind != obj.which_kind) or
                  (obj.quiver != new_obj.quiver)):
                count += 1
            obj = obj.next_object

        return count

    def _check_duplicate(self, obj: Item) -> Optional[Item]:
        """重複アイテムをチェック（C版 pack.c: check_duplicate）"""
        # 武器、食料、巻物、ポーションのみ
        if not (obj.item_type & (const.WEAPON | const.FOOD | const.SCROL | const.POTION)):
            return None

        # 果物は重複しない
        if obj.item_type == const.FOOD and obj.which_kind == const.FRUIT:
            return None

        curr = self.player.pack
        while curr:
            if (curr.item_type == obj.item_type and
                    curr.which_kind == obj.which_kind):
                # 武器の場合は矢、短剣、ダーツ、手裏剣のみ重複（C版のquiverチェック含む）
                if (obj.item_type != const.WEAPON or
                    ((obj.which_kind in (const.ARROW, const.DAGGER, const.DART, const.SHURIKEN)) and
                     (obj.quiver == curr.quiver))):
                    return curr
            curr = curr.next_object

        return None

    def _add_to_pack(self, obj: Item, condense: bool) -> Item:
        """アイテムをインベントリに追加（C版 pack.c: add_to_pack）"""
        if condense:
            op = self._check_duplicate(obj)
            if op:
                # 重複アイテムは数量を追加
                op.quantity += obj.quantity
                return op
            else:
                # 新しい文字を割り当て
                obj.ichar = ord(self.player.next_avail_ichar())

        # ソート順に挿入（C版の非ORIGINALロジック）
        if self.player.pack is None:
            self.player.pack = obj
            obj.next_object = None
        else:
            prev = None
            curr = self.player.pack
            while curr and curr.next_object:
                if curr.next_object.item_type > obj.item_type:
                    break
                prev = curr
                curr = curr.next_object

            if prev is None:
                # 先頭に挿入
                if self.player.pack.item_type > obj.item_type:
                    obj.next_object = self.player.pack
                    self.player.pack = obj
                else:
                    obj.next_object = self.player.pack.next_object
                    self.player.pack.next_object = obj
            else:
                obj.next_object = curr.next_object
                curr.next_object = obj

        return obj

    def rogue_hit(self, monster: Monster, force_hit: bool = False) -> None:
        """プレイヤーがモンスターを攻撃 — Combat に委譲"""
        combat = Combat(self.player, self.dungeon)
        combat.display = self.display
        combat.msg = self.msg
        combat.game = self.game
        combat.rogue_hit(monster, force_hit)

    def mon_hit(self, monster: Monster) -> None:
        """モンスターがプレイヤーを攻撃 — Combat に委譲"""
        combat = Combat(self.player, self.dungeon)
        combat.display = self.display
        combat.msg = self.msg
        combat.game = self.game
        combat.mon_hit(monster)

    def get_hit_chance(self, weapon: Optional[Item]) -> int:
        """プレイヤーの命中率を取得 (C版 hit.c: get_hit_chance。Combatに委譲)"""
        from .combat import Combat as _Combat
        c = _Combat(self.player, self.dungeon)
        return c._get_hit_chance(weapon)

    def to_hit(self, weapon: Optional[Item]) -> int:
        """武器の命中ボーナスを取得 (C版 hit.c: to_hit。Combatに委譲)"""
        from .combat import Combat as _Combat
        c = _Combat(self.player, self.dungeon)
        return c._to_hit(weapon)

    def get_weapon_damage(self, weapon: Optional[Item]) -> int:
        """プレイヤーの武器ダメージを取得 (C版 hit.c: get_weapon_damage。Combatに委譲)"""
        from .combat import Combat as _Combat
        c = _Combat(self.player, self.dungeon)
        return c._get_weapon_damage(weapon)

    def get_w_damage(self, weapon: Optional[Item]) -> int:
        """武器自体のダメージロール (C版 hit.c: get_w_damage。Combatに委譲)"""
        from .combat import Combat as _Combat
        c = _Combat(self.player, self.dungeon)
        return c._get_w_damage(weapon)

    def damage_for_strength(self) -> int:
        """力によるダメージボーナス (C版 hit.c: damage_for_strength。Combatに委譲)"""
        from .combat import Combat as _Combat
        c = _Combat(self.player, self.dungeon)
        return c._damage_for_strength()

    def _kill_monster(self, monster: Monster) -> None:
        """モンスターを死亡させる"""
        row, col = monster.row, monster.col
        
        # level_monsters 連結リストから削除
        prev = None
        curr = self.dungeon.level_monsters
        while curr:
            if curr == monster:
                if prev:
                    prev.next_object = curr.next_object
                else:
                    self.dungeon.level_monsters = curr.next_object
                break
            prev = curr
            curr = curr.next_object

        # monsters[] Pythonリストからも削除
        if monster in self.dungeon.monsters:
            self.dungeon.monsters.remove(monster)
            
        # タイルからフラグ削除
        self.dungeon.dungeon[row][col] &= ~const.MONSTER
        logger.info(f"Monster killed at ({row}, {col})")
        
        # モンスターがいた位置を再描画（C言語版と同じ）
        if self.display:
            ch = self.display.get_dungeon_char(self.dungeon, row, col)
            self.display.mvaddch(row, col, ord(ch))
            self.display.refresh()

    def _monster_at(self, row: int, col: int) -> Optional[Monster]:
        """指定位置のモンスターを取得"""
        monster = self.dungeon.level_monsters
        while monster:
            if monster.row == row and monster.col == col:
                return monster
            monster = monster.next_object
        return None

    def mv_mons(self) -> None:
        """モンスターの移動 — MonsterAI に委譲"""
        ai = MonsterAI(self.player, self.dungeon)
        ai.display = self.display
        ai.msg = self.msg
        ai.game = self.game
        ai.mv_mons()

    def rogue_can_see(self, row: int, col: int) -> bool:
        """プレイヤーがその座標を見ることができるか (C版 monster.c: rogue_can_see)"""
        if self.blind:
            return False

        if self.rogue_is_around(row, col):
            return True

        rn = self.dungeon.get_room_number(row, col)
        if rn != const.NO_ROOM and rn == GameState.cur_room:
            room = self.dungeon.get_room(rn)
            if room and not (room.is_room & const.R_MAZE):
                return True

        return False

    def rogue_is_around(self, row: int, col: int) -> bool:
        """プレイヤーの周囲 8 マスにいるか"""
        rdif = row - self.player.row
        cdif = col - self.player.col
        return -1 <= rdif <= 1 and -1 <= cdif <= 1

    def wake_room(self, rn: int, entering: bool, row: int, col: int) -> None:
        """部屋のモンスターを目覚めさせる (C版 monster.c: wake_room相当)"""
        # C: party_roomならPARTY_WAKE_PERCENT、stealthyで除算、enteringでtrow設定
        wake_percent = const.PARTY_WAKE_PERCENT if rn == GameState.party_room else const.WAKE_PERCENT
        if self.stealthy > 0:
            wake_percent //= (const.STEALTH_FACTOR + self.stealthy)
        monster = self.dungeon.level_monsters
        while monster:
            in_room = (rn == self.dungeon.get_room_number(monster.row, monster.col))
            if in_room:
                if entering:
                    monster.trow = const.NO_ROOM
                else:
                    monster.trow = row
                    monster.tcol = col
            if (monster.m_flags & const.WAKENS) and in_room:
                if utils.rand_percent(wake_percent):
                    if not (monster.m_flags & const.NAPPING):
                        monster.m_flags &= ~(const.ASLEEP | const.IMITATES | const.WAKENS)
            monster = monster.next_object

    def search(self, n: int, is_auto: bool):
        """探索（パブリックメソッド）"""
        self._search(n, is_auto)
    
    def _search(self, n: int, is_auto: bool):
        """探索（内部実装）"""
        found = 0
        shown = 0
        # C言語版: static boolean reg_search; （静的変数）

        # 隠されたものをカウント
        for i in range(-1, 2):
            for j in range(-1, 2):
                row = self.player.row + i
                col = self.player.col + j
                if (row < const.MIN_ROW or row >= (const.ROGUE_LINES - 1)
                        or col < 0 or col >= const.ROGUE_COLUMNS):
                    continue
                if self.dungeon.dungeon[row][col] & const.HIDDEN:
                    found += 1

        # 探索実行
        for s in range(n):
            for i in range(-1, 2):
                for j in range(-1, 2):
                    row = self.player.row + i
                    col = self.player.col + j
                    if (row < const.MIN_ROW or row >= (const.ROGUE_LINES - 1)
                            or col < 0 or col >= const.ROGUE_COLUMNS):
                        continue
                    if self.dungeon.dungeon[row][col] & const.HIDDEN:
                        if utils.rand_percent(17 + self.player.exp + self.ring_exp):
                            self.dungeon.dungeon[row][col] &= ~const.HIDDEN
                            if (not self.blind and (row != self.player.row or col != self.player.col)):
                                # 発見した隠し扉/罠を表示
                                if self.display:
                                    ch = self.display.get_dungeon_char(self.dungeon, row, col)
                                    self.display.mvaddch(row, col, ord(ch))
                            shown += 1
                            if self.dungeon.dungeon[row][col] & const.TRAP:
                                t = self._trap_at(row, col)
                                if self.msg and t != const.NO_TRAP:
                                    trap_name = TRAP_MESSAGES.get(t, ("罠", "罠だ！"))[0]
                                    self.msg.message(f"{trap_name}を発見した！")
                    if (shown == found and found > 0) or self.interrupted:
                        return
            if not is_auto:
                # C版 trap.c: search static reg_search (GameState集約)
                GameState.reg_search = not GameState.reg_search
                if GameState.reg_search:
                    self.reg_move()

    def _unhallucinate(self) -> None:
        """幻覚解除 (C版 use.c: unhallucinate)"""
        self.halluc = 0
        if self.display:
            self._relight()
        if self.msg:
            self.msg.message("頭がすっきりした", 1)

    def _unblind(self) -> None:
        """盲目解除 (C版 use.c: unblind)"""
        self.blind = 0
        if self.msg:
            self.msg.message("目が見えるようになった", 1)
        if self.display:
            self._relight()
        if self.halluc:
            self._hallucinate()

    def _unconfuse(self) -> None:
        """混乱解除 (C版 use.c: unconfuse)"""
        self.confused = 0
        if self.msg:
            if self.halluc:
                self.msg.message("頭がクラクラした...", 1)
            else:
                self.msg.message("頭がすっきりした", 1)

    def _hallucinate(self) -> None:
        """幻覚効果 (C版 use.c: hallucinate)"""
        if self.blind:
            return
        if not self.display:
            return
        # 画面上のオブジェクトとモンスターの表示をランダムに変更
        obj = self.dungeon.level_objects
        while obj:
            ch = self.display.mvinch(obj.row, obj.col)
            if ((ch < 'A') or (ch > 'Z')) and ((obj.row != self.player.row) or (obj.col != self.player.col)):
                if (ch != ' ') and (ch != '.') and (ch != '#') and (ch != '+'):
                    self.display.mvaddch(obj.row, obj.col, ord(self._gr_obj_char()))
            obj = obj.next_object

        monster = self.dungeon.level_monsters
        while monster:
            ch = self.display.mvinch(monster.row, monster.col)
            if (ch >= 'A') and (ch <= 'Z'):
                self.display.mvaddch(monster.row, monster.col, utils.get_rand(ord('A'), ord('Z')))
            monster = monster.next_object

    def _gr_obj_char(self) -> str:
        """ランダムなオブジェクト文字を生成"""
        chars = "?!/=)]:,*"
        return chars[utils.get_rand(0, len(chars) - 1)]

    def _relight(self) -> None:
        """再点灯 (C版 use.c: relight)"""
        if not self.display:
            return
        if GameState.cur_room == const.PASSAGE:
            self.display.light_passage(self.dungeon, self.player, self.player.row, self.player.col)
        else:
            self.display.light_up_room(self.dungeon, self.player, GameState.cur_room)
        self.display.mvaddch(self.player.row, self.player.col, self.player.fchar)

    def _wanderer(self) -> None:
        """放浪モンスターを生成 (C版 monster.c: wanderer)"""
        # combat.pyのMonsterAI.wanderer()を使用
        try:
            from .combat import MonsterAI
        except ImportError:
            from combat import MonsterAI
        
        ai = MonsterAI(self.player, self.dungeon)
        ai.display = self.display
        ai.msg = self.msg
        ai.game = self.game
        ai.cur_level = self.cur_level
        ai.cur_room = GameState.cur_room
        ai.blind = self.blind
        ai.halluc = self.halluc
        ai.haste_self = self.haste_self
        ai.wanderer()

    def _tele(self) -> None:
        """テレポート (C版 use.c: tele)
        
        C言語版のロジック:
        1. 現在位置を消去（地形を描画）
        2. 現在の部屋を暗くする
        3. put_player()で新しい位置に配置
        4. being_held, bear_trapをクリア
        """
        
        # C版: mvaddch_rogue(rogue.row, rogue.col, get_dungeon_char(rogue.row, rogue.col));
        if self.display:
            ch = self.display.get_dungeon_char(self.dungeon, self.player.row, self.player.col)
            self.display.mvaddch(self.player.row, self.player.col, ord(ch))
        
        # C版: if (cur_room >= 0) { darken_room(cur_room); }
        if GameState.cur_room >= 0 and self.display:
            self.display.darken_room(self.dungeon, GameState.cur_room, self.blind > 0)
        
        # C版: put_player(get_room_number(rogue.row, rogue.col));
        # put_player()の実装: gr_row_col()でランダムな位置を取得
        nr = self._get_room_number(self.player.row, self.player.col)
        rn = nr
        
        # C版: for (misses = 0; ((misses < 2) && (rn == nr)); misses++)
        for misses in range(2):
            if rn != nr:
                break
            # gr_row_col()相当: FLOOR | TUNNEL | OBJECT | STAIRSを持つランダムな位置を取得
            row, col = self._gr_row_col_for_tele()
            rn = self._get_room_number(row, col)
        
        # 新しい位置に移動
        self.player.row = row
        self.player.col = col
        
        # C版: if (dungeon[rogue.row][rogue.col] & TUNNEL)
        if self.dungeon.dungeon[row][col] & const.TUNNEL:
            GameState.cur_room = const.PASSAGE
        else:
            GameState.cur_room = rn
        
        # C版: if (cur_room != PASSAGE) { light_up_room(cur_room); } else { light_passage(); }
        if GameState.cur_room != const.PASSAGE:
            if self.display:
                self.display.light_up_room(self.dungeon, self.player, GameState.cur_room)
        else:
            if self.display:
                self.display.light_passage(self.dungeon, self.player, row, col)
        
        # C版: wake_room(get_room_number(rogue.row, rogue.col), 1, rogue.row, rogue.col);
        self.wake_room(self._get_room_number(row, col), True, row, col)
        
        # C版: mvaddch_rogue(rogue.row, rogue.col, rogue.fchar);
        if self.display:
            self.display.mvaddch(row, col, self.player.fchar)
        
        # C版: being_held = 0; bear_trap = 0;
        GameState.being_held = False
        GameState.bear_trap = 0
    
    def _gr_row_col_for_tele(self) -> Tuple[int, int]:
        """テレポート用のランダム位置取得 (C版 level.c: gr_row_col相当)"""
        for _ in range(1000):  # 無限ループ防止
            row = utils.get_rand(const.MIN_ROW, const.ROGUE_LINES - 2)
            col = utils.get_rand(0, const.ROGUE_COLUMNS - 1)
            tile = self.dungeon.dungeon[row][col]
            # C版: (FLOOR | TUNNEL | OBJECT | STAIRS)
            if tile & (const.FLOOR | const.TUNNEL | const.OBJECT | const.STAIRS):
                return row, col
        # フォールバック
        return const.MIN_ROW + 1, 1

    def _take_a_nap(self) -> None:
        """居眠り (C版 use.c: take_a_nap)"""
        i = utils.get_rand(2, 5)
        for _ in range(i):
            self.mv_mons()
        if self.msg:
            self.msg.message(get_message(66), 0)  # "ようやく体が自由になった。"

    def _rust(self, monster) -> None:
        """錆効果 (C版 spechit.c: rust)
        
        C言語版のロジック:
        1. 防具がない、AC<=1、または革鎧なら何もしない
        2. 防具が保護されている場合: mesg[201]を表示してRUST_VANISHEDフラグを立てる
        3. そうでない場合: d_enchantを減らしてmesg[202]を表示
        """
        armor = self.player.armor
        if not armor:
            return
        
        # C版: get_armor_class(rogue.armor) <= 1
        ac = self.player.get_armor_class()
        if ac <= 1:
            return
        
        # C版: rogue.armor->which_kind == LEATHER
        if armor.which_kind == const.LEATHER:
            return
        
        # C版: if ((rogue.armor->is_protected) || maintain_armor)
        maintain_armor = GameState.maintain_armor
        
        if armor.is_protected or maintain_armor:
            # 保護されている場合
            if monster and not (monster.m_flags & const.RUST_VANISHED):
                if self.msg:
                    self.msg.message(get_message(201), 0)  # "水ごけの湿り気はすぐに消え去った。"
                monster.m_flags |= const.RUST_VANISHED
        else:
            # 保護されていない場合: 錆びる
            armor.d_enchant -= 1
            if self.msg:
                self.msg.message(get_message(202), 0)  # "よろいはさびてしまった！"
            if self.game:
                self.game._print_stats(const.STAT_ARMOR)


class TrapManager:
    """罠管理クラス"""

    @staticmethod
    def add_traps(dungeon: DungeonLevel, cur_level: int, party_room: int = const.NO_ROOM):
        """罠を追加"""
        # レベルに応じた罠の数を決定
        if cur_level <= 2:
            n = 0
        elif cur_level <= 7:
            n = utils.get_rand(0, 2)
        elif cur_level <= 11:
            n = utils.get_rand(1, 2)
        elif cur_level <= 16:
            n = utils.get_rand(2, 3)
        elif cur_level <= 21:
            n = utils.get_rand(2, 4)
        elif cur_level <= (const.AMULET_LEVEL + 2):
            n = utils.get_rand(3, 5)
        else:
            n = utils.get_rand(5, const.MAX_TRAPS)

        for i in range(n):
            trap_type = utils.get_rand(0, const.TRAPS - 1)

            if i == 0 and party_room != const.NO_ROOM:
                # パーティ部屋に罠を配置
                tries = 0
                room = dungeon.rooms[party_room]
                while tries < 15:
                    row = utils.get_rand(room.top_row + 1, room.bottom_row - 1)
                    col = utils.get_rand(room.left_col + 1, room.right_col - 1)
                    tries += 1
                    if not ((dungeon.dungeon[row][col] & (
                            const.OBJECT | const.STAIRS | const.TRAP | const.TUNNEL))
                            or (dungeon.dungeon[row][col] == const.NOTHING)):
                        break
                if tries >= 15:
                    row, col = TrapManager._gr_row_col(dungeon, const.FLOOR | const.MONSTER)
            else:
                row, col = TrapManager._gr_row_col(dungeon, const.FLOOR | const.MONSTER)

            trap = Trap(trap_type=trap_type, trap_row=row, trap_col=col)
            dungeon.traps.append(trap)
            dungeon.dungeon[row][col] |= const.TRAP | const.HIDDEN

    @staticmethod
    def _gr_row_col(dungeon: DungeonLevel, mask: int) -> Tuple[int, int]:
        """指定されたマスクを持つランダムな座標を取得"""
        while True:
            row = utils.get_rand(const.MIN_ROW, const.ROGUE_LINES - 2)
            col = utils.get_rand(0, const.ROGUE_COLUMNS - 1)
            if dungeon.dungeon[row][col] & mask:
                return row, col

    @staticmethod
    def show_traps(dungeon: DungeonLevel, display=None):
        """罠を表示（デバッグ用）"""
        for i in range(const.ROGUE_LINES):
            for j in range(const.ROGUE_COLUMNS):
                if dungeon.dungeon[i][j] & const.TRAP:
                    if display:
                        display.mvaddch(i, j, ord('^'))

"""
use_actions.py - アイテムの使用
src/use.c から移植

ポーションを飲む、巻物を読む、食料を食べる処理を実装します。
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from . import inventory
    from .entities import Player, Item, Monster
    from .dungeon import DungeonLevel

try:
    from . import const, utils
    from .entities import Player, Item, Monster
    from .dungeon import DungeonLevel
    from . import inventory
    from .text_resources import get_message
    from .game_state import GameState
except ImportError:
    import const, utils
    import entities
    import inventory
    import dungeon
    from text_resources import get_message
    from game_state import GameState
    Player = entities.Player
    Item = entities.Item
    Monster = entities.Monster
    DungeonLevel = dungeon.DungeonLevel


# グローバル状態変数は GameState に集約
# モジュールレベルの global 宣言によるアクセスを GameState に委譲
_GS = GameState
_halluc = 0
_blind = 0
_confused = 0
_levitate = 0
_haste_self = 0
_see_invisible = False
_extra_hp = 0
_detect_monster = False
_being_held = False
_bear_trap = 0
_sustain_strength = False

def __getattr__(name):
    _proxy = {
        'halluc': 'halluc', 'blind': 'blind', 'confused': 'confused',
        'levitate': 'levitate', 'haste_self': 'haste_self',
        'see_invisible': 'see_invisible', 'extra_hp': 'extra_hp',
        'detect_monster': 'detect_monster', 'being_held': 'being_held',
        'bear_trap': 'bear_trap', 'sustain_strength': 'sustain_strength',
        'fruit': 'fruit',
    }
    if name in _proxy:
        return getattr(_GS, _proxy[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __setattr__(name, value):
    _proxy = {
        'halluc': 'halluc', 'blind': 'blind', 'confused': 'confused',
        'levitate': 'levitate', 'haste_self': 'haste_self',
        'see_invisible': 'see_invisible', 'extra_hp': 'extra_hp',
        'detect_monster': 'detect_monster', 'being_held': 'being_held',
        'bear_trap': 'bear_trap', 'sustain_strength': 'sustain_strength',
        'fruit': 'fruit',
    }
    if name in _proxy:
        setattr(_GS, _proxy[name], value)
    else:
        globals()[name] = value

class UseActions:
    """アイテム使用アクションクラス"""

    def __init__(self, player: Player, dungeon: DungeonLevel, inv_manager: inventory.InventoryManager, display=None, message=None, game=None):
        self.player = player
        self.dungeon = dungeon
        self.inv_manager = inv_manager
        self.display = display
        self.message = message
        self.game = game
        self.cur_room = const.NO_ROOM

    def quaff(self, obj=None) -> bool:
        if obj is None:
            ch = self.inv_manager._pack_letter("どれを飲みますか？", const.POTION)
            if ch == const.CANCEL:
                return False
            obj = self.inv_manager._get_letter_object(ch)
            if obj is None:
                return False

        if obj.item_type != const.POTION:
            # message("それはポーションではない", 0)
            return False

        # C版では obj->which_kind を使用
        kind = obj.which_kind if hasattr(obj, 'which_kind') else (obj.item_kind if hasattr(obj, 'item_kind') else 0)
        
        match kind:
            case const.INCREASE_STRENGTH:
                if self.message:
                    self.message.message(get_message(234), 0)  # "何だか、力がわいてくるぞ！"
                self.player.str_current += 1
                if self.player.str_current > self.player.str_max:
                    self.player.str_max = self.player.str_current
            case const.RESTORE_STRENGTH:
                self.player.str_current = self.player.str_max
                if self.message:
                    self.message.message(get_message(235), 0)  # C版 use.c:81 mesg[235]
            case const.HEALING:
                if self.message:
                    self.message.message(get_message(236), 0)  # "気分がよくなった！"
                self._potion_heal(False)
            case const.EXTRA_HEALING:
                if self.message:
                    self.message.message(get_message(237), 0)  # "とても気分がよくなった！"
                self._potion_heal(True)
            case const.POISON:
                if not GameState.sustain_strength:
                    self.player.str_current -= utils.get_rand(1, 3)
                    if self.player.str_current < 1:
                        self.player.str_current = 1
                if self.message:
                    self.message.message(get_message(238), 0)  # "この水薬は毒だった！"
                if GameState.halluc:
                    self._unhallucinate()
            case const.RAISE_LEVEL:
                # C版: rogue.exp_points = level_points[rogue.exp - 1]; add_exp(1, 1);
                if self.player.exp > 0 and self.player.exp <= len(Player.LEVEL_POINTS):
                    self.player.exp_points = Player.LEVEL_POINTS[self.player.exp - 1]
                self._add_exp(1, True)
            case const.BLINDNESS:
                self._go_blind()
            case const.HALLUCINATION:
                if self.message:
                    self.message.message(get_message(239), 0)  # "ふにゃ？ 何もかもが虹色にみえるなあ？"
                GameState.halluc += utils.get_rand(500, 800)
            case const.DETECT_MONSTER:
                self._show_monsters()
                # モンスターがいなければ「奇妙な感じがした」
            case const.DETECT_OBJECTS:
                if self.dungeon.level_objects:
                    if not GameState.blind:
                        self._show_objects()
                else:
                    if self.message:
                        self.message.message(get_message(230), 0)  # "不思議な気分におそわれたが、すぐに消えていった。"
            case const.CONFUSION:
                if self.message:
                    if GameState.halluc:
                        self.message.message(get_message(240), 0)  # "何だか酔っぱらいみたいな気分だ！"
                    else:
                        self.message.message(get_message(241), 0)  # "あれ？ ここはどこ？ 私はだれ？"
                self._confuse()
            case const.LEVITATION:
                if self.message:
                    self.message.message(get_message(242), 0)  # "体が宙に浮いてしまった！"
                GameState.levitate += utils.get_rand(15, 30)
                GameState.being_held = False
                GameState.bear_trap = 0
            case const.HASTE_SELF:
                if self.message:
                    self.message.message(get_message(243), 0)  # "体が素早く動くようになった！"
                GameState.haste_self += utils.get_rand(11, 21)
                if not (GameState.haste_self % 2):
                    GameState.haste_self += 1
            case const.SEE_INVISIBLE:
                if self.message:
                    self.message.message(get_message(244) % GameState.fruit, 0)  # "う〜む、%sジュースのような味がする。"
                if GameState.blind:
                    self._unblind()
                GameState.see_invisible = True
                self._relight()

        # ステータス更新
        if getattr(self, 'game', None):
            self.game._print_stats(const.STAT_STRENGTH | const.STAT_HP)
        
        # ポーションを識別済みにする
        # C版ORIGINALモード: プレイヤーが名前を付けていない(CALLEDでない)場合のみ識別
        if kind < len(inventory.id_potions):
            inventory.id_potions[kind].id_status = const.IDENTIFIED
        self._vanish(obj, True)
        return True

    def read_scroll(self, obj=None) -> bool:
        if obj is None:
            ch = self.inv_manager._pack_letter("どれを読みますか？", const.SCROL)
            if ch == const.CANCEL:
                return False
            obj = self.inv_manager._get_letter_object(ch)
            if obj is None:
                return False

        if obj.item_type != const.SCROL:
            # message("それは巻物ではない", 0)
            return False

        # C版では obj->which_kind を使用
        kind = obj.which_kind if hasattr(obj, 'which_kind') else (obj.item_kind if hasattr(obj, 'item_kind') else 0)

        match kind:
            case const.SCARE_MONSTER:
                if self.message:
                    self.message.message(get_message(248), 0)  # C版 use.c:309 mesg[248
            case const.HOLD_MONSTER:
                self._hold_monster()
            case const.ENCH_WEAPON:
                if self.player.weapon:
                    if self.player.weapon.item_type == const.WEAPON:
                        if self.message:
                            color = get_message(275)  # "青い"
                            self.message.message(get_message(249) % (self.player.weapon, color), 0)  # "手に持った%sが、ほんの少し%s輝きに包まれた。"
                        if utils.coin_toss():
                            self.player.weapon.hit_enchant += 1
                        else:
                            self.player.weapon.d_enchant += 1
                    self.player.weapon.is_cursed = False
                else:
                    if self.message:
                        self.message.message(get_message(250), 0)  # "何だか、手がむずむずする。"
            case const.ENCH_ARMOR:
                if self.player.armor:
                    if self.message:
                        color = get_message(275)  # "青い"
                        self.message.message(get_message(251) % color, 0)  # "着ているよろいが、ほんの少し%s輝きに包まれた。"
                    self.player.armor.d_enchant += 1
                    self.player.armor.is_cursed = False
                else:
                    if self.message:
                        self.message.message(get_message(252), 0)  # "何だか、体がむずむずする。"
            case const.IDENTIFY:
                if self.message:
                    self.message.message(get_message(253), 0)  # "これは持ちものを調べる巻き物だった。"
                obj.identified = const.IDENTIFIED
                if kind < len(inventory.id_scrolls):
                    inventory.id_scrolls[kind].id_status = const.IDENTIFIED
                self._idntfy()
            case const.TELEPORT:
                self._tele()
            case const.SLEEP:
                if self.message:
                    self.message.message(get_message(254), 0)  # "知らないうちに眠り込んでしまった。"
                self._take_a_nap()
            case const.PROTECT_ARMOR:
                if self.player.armor:
                    if self.message:
                        self.message.message(get_message(255), 0)  # "着ているよろいは、輝く金色の光に守られた。"
                    self.player.armor.is_protected = True
                    self.player.armor.is_cursed = False
                else:
                    if self.message:
                        self.message.message(get_message(256), 0)  # "何だか、顔がむずむずする。"
            case const.REMOVE_CURSE:
                if self.message:
                    # C版 use.c:365 message(!halluc?mesg[257]:mesg[258])
                    msg = get_message(257) if not GameState.halluc else get_message(258)
                    self.message.message(msg, 0)
                self._uncurse_all()
            case const.CREATE_MONSTER:
                self._create_monster()
            case const.AGGRAVATE_MONSTER:
                self._aggravate()
            case const.MAGIC_MAPPING:
                if self.message:
                    self.message.message(get_message(259), 0)  # "おや、この巻き物には地図が書いてある！"
                self._draw_magic_map()

        # 巻物を識別済みにする
        # C版ORIGINALモード: プレイヤーが名前を付けていない(CALLEDでない)場合のみ識別
        if kind < len(inventory.id_scrolls):
            inventory.id_scrolls[kind].id_status = const.IDENTIFIED
        # C版: vanish(obj, (obj->which_kind != SLEEP), &rogue.pack)
        self._vanish(obj, kind != const.SLEEP)
        return True

    def eat(self, obj=None) -> bool:
        if obj is None:
            ch = self.inv_manager._pack_letter("何を食べますか？", const.FOOD)
            if ch == const.CANCEL:
                return False
            obj = self.inv_manager._get_letter_object(ch)
            if obj is None:
                return False

        if obj.item_type != const.FOOD:
            # message("それは食料ではない", 0)
            return False

        # C版では obj->which_kind を使用
        kind = obj.which_kind if hasattr(obj, 'which_kind') else (obj.item_kind if hasattr(obj, 'item_kind') else 0)

        moves = 0
        # C版: if ((obj->which_kind == FRUIT) || rand_percent(60))
        if kind == const.FRUIT or utils.rand_percent(60):
            moves = utils.get_rand(900, 1100)
            if kind == const.RATION:
                # C版 use.c:614-616 RATION当り mesg[265]
                if utils.get_rand(1, 10) == 1:
                    if self.message:
                        self.message.message(get_message(265), 0)
                else:
                    if self.message:
                        self.message.message(get_message(266), 0)  # "ああ、おいしかった。"
            else:
                if self.message:
                    self.message.message(get_message(267) % GameState.fruit, 0)  # "おや、なんて甘い%sだ。"
        else:
            moves = utils.get_rand(700, 900)
            if self.message:
                # C版 use.c:625-626 外れ mesg[268] + add_exp(2,1)
                self.message.message(get_message(268), 0)
            # C版: add_exp(2, 1);
            self._add_exp(2, True)

        # C版: rogue.moves_left /= 3; rogue.moves_left += moves;
        self.player.moves_left //= 3
        self.player.moves_left += moves
        # hunger_str[0] = 0;
        if getattr(self, 'game', None):
            self.game._print_stats(const.STAT_HUNGER)
        
        self._vanish(obj, True)
        return True

    def _vanish(self, obj: Item, rm: bool) -> None:
        """アイテムを消費する (C版 use.c: vanish)"""
        if obj.quantity > 1:
            obj.quantity -= 1
        else:
            if obj.in_use_flags & const.BEING_WIELDED:
                self.inv_manager.unwield(obj)
            elif obj.in_use_flags & const.BEING_WORN:
                self.inv_manager.unwear(obj)
            elif obj.in_use_flags & const.ON_EITHER_HAND:
                self.inv_manager.un_put_on(obj)
            self.inv_manager.take_from_pack(obj)
        if rm:
            # C版: if (rm) reg_move();
            if getattr(self, 'game', None) is not None and hasattr(self.game, '_movement'):
                try:
                    self.game._movement.reg_move()
                except Exception:
                    pass

    def _potion_heal(self, extra: bool) -> None:
        """ポーションの回復効果 (C版 use.c: potion_heal)"""
        
        # C版: rogue.hp_current += rogue.exp;
        self.player.hp_current += self.player.exp

        # C版: ratio = rogue.hp_current * 100L / rogue.hp_max;
        ratio = self.player.hp_current * 100 // self.player.hp_max

        if ratio >= 100:
            self.player.hp_max += (2 if extra else 1)
            GameState.extra_hp += (2 if extra else 1)
            self.player.hp_current = self.player.hp_max
        elif ratio >= 90:
            self.player.hp_max += (1 if extra else 0)
            GameState.extra_hp += (1 if extra else 0)
            self.player.hp_current = self.player.hp_max
        else:
            if ratio < 33:
                ratio = 33
            if extra:
                ratio += ratio
            add = ratio * (self.player.hp_max - self.player.hp_current) // 100
            self.player.hp_current += add
            if self.player.hp_current > self.player.hp_max:
                self.player.hp_current = self.player.hp_max

        if GameState.blind:
            self._unblind()
        if GameState.confused and extra:
            self._unconfuse()
        elif GameState.confused:
            GameState.confused = (GameState.confused // 2) + 1
        if GameState.halluc and extra:
            self._unhallucinate()
        elif GameState.halluc:
            GameState.halluc = (GameState.halluc // 2) + 1

    def _add_exp(self, e: int, promotion: bool) -> None:
        """経験値を追加する (C版 level.c: add_exp)"""
        new_levels = self.player.add_exp(e, promotion)
        for lv in new_levels:
            if self.message:
                self.message.message(get_message(53) % lv, 0)

    def _idntfy(self) -> bool:
        """アイテムを識別する (C版 use.c: idntfy)"""
        ch = self.inv_manager._pack_letter("何を識別しますか？", const.ALL_OBJECTS)
        if ch == const.CANCEL:
            return False

        obj = self.inv_manager._get_letter_object(ch)
        if obj is None:
            # message("そのようなアイテムはない", 0)
            return False

        obj.identified = const.IDENTIFIED
        if obj.item_type & (const.SCROL | const.POTION | const.WEAPON | const.ARMOR | const.WAND | const.RING):
            id_table = self.inv_manager._get_id_table(obj)
            kind = obj.which_kind if hasattr(obj, 'which_kind') else 0
            if id_table and kind < len(id_table):
                id_table[kind].id_status = const.IDENTIFIED

        # desc = self.inv_manager.get_desc(obj, True)
        # message(desc, 0)
        return True

    def _hold_monster(self) -> None:
        """モンスターを拘束する (C版 use.c: hold_monster)"""
        mcount = 0

        for i in range(-2, 3):
            for j in range(-2, 3):
                row = self.player.row + i
                col = self.player.col + j
                if (row < const.MIN_ROW or row > (const.ROGUE_LINES - 2)
                        or col < 0 or col > (const.ROGUE_COLUMNS - 1)):
                    continue
                # dungeon.dungeon を使用
                if hasattr(self.dungeon, 'dungeon'):
                    dungeon_grid = self.dungeon.dungeon
                else:
                    dungeon_grid = self.dungeon.dungeon
                if dungeon_grid[row][col] & const.MONSTER:
                    monster = self._monster_at(row, col)
                    if monster:
                        monster.m_flags |= const.ASLEEP
                        monster.m_flags &= ~const.WAKENS
                        mcount += 1

        if mcount == 0:
            if self.message:
                # C版 use.c:661 mesg[269]
                self.message.message(get_message(269), 0)
        elif mcount == 1:
            if self.message:
                self.message.message(get_message(270), 0)  # "怪物は動けなくなった！"
        else:
            if self.message:
                self.message.message(get_message(271), 0)  # "怪物どもは動けなくなった！"

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
            ch = self._get_dungeon_char(self.player.row, self.player.col)
            self.display.mvaddch(self.player.row, self.player.col, ord(ch))
        
        # C版: if (cur_room >= 0) { darken_room(cur_room); }
        if self.cur_room >= 0 and self.display:
            self.display.darken_room(self.dungeon, self.cur_room, self.blind > 0)
        
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
        if hasattr(self.dungeon, 'dungeon'):
            tile = self.dungeon.dungeon[row][col]
        else:
            tile = self.dungeon.dungeon[row][col]
            
        if tile & const.TUNNEL:
            self.cur_room = const.PASSAGE
        else:
            self.cur_room = rn
        
        # C版: if (cur_room != PASSAGE) { light_up_room(cur_room); } else { light_passage(); }
        if self.cur_room != const.PASSAGE:
            self._light_up_room(self.cur_room)
        else:
            self._light_passage(row, col)
        
        # C版: wake_room(get_room_number(rogue.row, rogue.col), 1, rogue.row, rogue.col);
        from actions import Movement
        movement = Movement(self.player, self.dungeon)
        movement.wake_room(self._get_room_number(row, col), True, row, col)
        
        # C版: mvaddch_rogue(rogue.row, rogue.col, rogue.fchar);
        if self.display:
            self.display.mvaddch(row, col, self.player.fchar)
        
        # C版: being_held = 0; bear_trap = 0;
        GameState.being_held = False
        GameState.bear_trap = 0
    
    def _gr_row_col_for_tele(self):
        """テレポート用のランダム位置取得 (C版 level.c: gr_row_col相当)"""
        for _ in range(1000):  # 無限ループ防止
            row = utils.get_rand(const.MIN_ROW, const.ROGUE_LINES - 2)
            col = utils.get_rand(0, const.ROGUE_COLUMNS - 1)
            if hasattr(self.dungeon, 'dungeon'):
                tile = self.dungeon.dungeon[row][col]
            else:
                tile = self.dungeon.dungeon[row][col]
            # C版: (FLOOR | TUNNEL | OBJECT | STAIRS)
            if tile & (const.FLOOR | const.TUNNEL | const.OBJECT | const.STAIRS):
                return row, col
        # フォールバック
        return const.MIN_ROW + 1, 1
    
    def _get_room_number(self, row: int, col: int) -> int:
        """部屋番号を取得"""
        rooms = self.dungeon.rooms if hasattr(self.dungeon, 'rooms') else []
        for i, room in enumerate(rooms):
            if (room.top_row <= row <= room.bottom_row
                    and room.left_col <= col <= room.right_col):
                return i
        return const.NO_ROOM

    def _hallucinate(self) -> None:
        """幻覚効果 (C版 use.c: hallucinate)"""
        if GameState.blind:
            return
        # 画面上のモンスターとアイテムの表示を変更
        # C版では level_objects と level_monsters を走査して文字を変更
        if self.display:
            # オブジェクトの幻覚表示
            obj = self.dungeon.level_objects if hasattr(self.dungeon, 'level_objects') else None
            while obj:
                ch = self.display.mvinch(obj.row, obj.col)
                if ((ch < 'A') or (ch > 'Z')) and ((obj.row != self.player.row) or (obj.col != self.player.col)):
                    if (ch != ' ') and (ch != '.') and (ch != '#') and (ch != '+'):
                        self.display.mvaddch(obj.row, obj.col, self._gr_obj_char())
                obj = obj.next_object

            # モンスターの幻覚表示
            for monster in (self.dungeon.monsters if hasattr(self.dungeon, 'monsters') else []):
                ch = self.display.mvinch(monster.row, monster.col)
                if (ch >= 'A') and (ch <= 'Z'):
                    self.display.mvaddch(monster.row, monster.col, chr(utils.get_rand(ord('A'), ord('Z'))))

    def _gr_obj_char(self) -> str:
        """ランダムなオブジェクト文字を生成"""
        chars = "?!/=)]:,*"
        return chars[utils.get_rand(0, len(chars) - 1)]

    def _unhallucinate(self) -> None:
        """幻覚解除 (C版 use.c: unhallucinate)"""
        GameState.halluc = 0
        self._relight()
        if self.message:
            # C版 use.c:720 mesg[272]
            self.message.message(get_message(272), 1)

    def _unblind(self) -> None:
        """盲目解除 (C版 use.c: unblind)"""
        GameState.blind = 0
        if self.message:
            self.message.message(get_message(273), 1)  # "暗闇のとばりが上がってゆく。"
        self._relight()
        if GameState.halluc:
            self._hallucinate()
        if GameState.detect_monster:
            self._show_monsters()

    def _relight(self) -> None:
        """再点灯 (C版 use.c: relight)"""
        # C版: if (cur_room == PASSAGE) light_passage(rogue.row, rogue.col); else light_up_room(cur_room);
        if self.cur_room == const.PASSAGE:
            self._light_passage(self.player.row, self.player.col)
        else:
            self._light_up_room(self.cur_room)
        # C版: mvaddch_rogue(rogue.row, rogue.col, rogue.fchar);
        if self.display:
            self.display.mvaddch(self.player.row, self.player.col, self.player.fchar)

    def _light_up_room(self, rn: int) -> None:
        """部屋を照らす (C版 room.c: light_up_room)"""
        if GameState.blind:
            return
        if rn < 0 or rn >= len(self.dungeon.rooms):
            return
        room = self.dungeon.rooms[rn]
        if self.display:
            for i in range(room.top_row, room.bottom_row + 1):
                for j in range(room.left_col, room.right_col + 1):
                    ch = self._get_dungeon_char(i, j)
                    self.display.mvaddch(i, j, ch)
            self.display.mvaddch(self.player.row, self.player.col, self.player.fchar)

    def _light_passage(self, row: int, col: int) -> None:
        """通路を照らす (C版 room.c: light_passage)"""
        if GameState.blind:
            return
        if self.display:
            i_end = 1 if row < (const.ROGUE_LINES - 2) else 0
            j_end = 1 if col < (const.ROGUE_COLUMNS - 1) else 0
            i_start = -1 if row > const.MIN_ROW else 0
            j_start = -1 if col > 0 else 0
            for i in range(i_start, i_end + 1):
                for j in range(j_start, j_end + 1):
                    if self._can_move(row, col, row + i, col + j):
                        ch = self._get_dungeon_char(row + i, col + j)
                        self.display.mvaddch(row + i, col + j, ch)

    def _can_move(self, row1: int, col1: int, row2: int, col2: int) -> bool:
        """移動可能かどうかを判定"""
        # 簡易実装：範囲内ならTrue
        if row2 < const.MIN_ROW or row2 >= const.ROGUE_LINES:
            return False
        if col2 < 0 or col2 >= const.ROGUE_COLUMNS:
            return False
        return True

    def _get_dungeon_char(self, row: int, col: int) -> str:
        """ダンジョン文字を取得 (C版 room.c: get_dungeon_char)"""
        if hasattr(self.dungeon, 'dungeon'):
            mask = self.dungeon.dungeon[row][col]
        else:
            mask = self.dungeon.dungeon[row][col]

        if mask & const.MONSTER:
            return self._gmc_row_col(row, col)
        if mask & const.OBJECT:
            return '!'  # 簡易実装
        if mask & const.STAIRS:
            return '%'
        if mask & const.TUNNEL:
            return '#'
        if mask & const.HORWALL:
            return '-'
        if mask & const.VERTWALL:
            return '|'
        if mask & const.FLOOR:
            if mask & const.TRAP and not (mask & const.HIDDEN):
                return '^'
            return '.'
        if mask & const.DOOR:
            if mask & const.HIDDEN:
                return '+'  # 簡易実装
            return '+'
        return ' '

    def _gmc_row_col(self, row: int, col: int) -> str:
        """モンスター文字を取得"""
        monster = self._monster_at(row, col)
        if monster:
            return monster.m_char if hasattr(monster, 'm_char') else 'M'
        return 'M'

    def _take_a_nap(self) -> None:
        """居眠り (C版 use.c: take_a_nap)
        
        C言語版のロジック:
        1. 2〜5回のループ
        2. sleep(1)で1秒待機
        3. mv_mons()でモンスターを移動
        4. 最後に"ようやく体が自由になった。"メッセージ
        """
        import time
        
        i = utils.get_rand(2, 5)
        # C版: sleep(1);
        time.sleep(1)
        
        # C版: while (i--) { mv_mons(); }
        try:
            from .combat import MonsterAI
        except ImportError:
            from combat import MonsterAI
        
        ai = MonsterAI(self.player, self.dungeon)
        ai.display = getattr(self, 'display', None)
        ai.msg = getattr(self, 'msg', None)
        ai.game = getattr(self, 'game', None)
        for _ in range(i):
            ai.mv_mons()
        
        # C版: sleep(1);
        time.sleep(1)
        
        # C版: message(you_can_move_again, 0);
        if self.message:
            self.message.message(get_message(66), 0)  # "ようやく体が自由になった。"

    def _go_blind(self) -> None:
        """盲目になる (C版 use.c: go_blind)"""
        if not GameState.blind:
            if self.message:
                self.message.message(get_message(274), 0)  # "深い暗闇のとばりがあたりをおおってゆく。"
        GameState.blind += utils.get_rand(500, 800)

        # C版: detect_monster の場合はモンスターを非表示
        if GameState.detect_monster:
            for monster in (self.dungeon.monsters if hasattr(self.dungeon, 'monsters') else []):
                if self.display:
                    trail = monster.trail_char if hasattr(monster, 'trail_char') else ' '
                    self.display.mvaddch(monster.row, monster.col, trail)

    def _confuse(self) -> None:
        """混乱 (C版 use.c: confuse)"""
        GameState.confused += utils.get_rand(12, 22)

    def _unconfuse(self) -> None:
        """混乱解除 (C版 use.c: unconfuse)"""
        GameState.confused = 0
        if self.message:
            self.message.message(get_message(277), 1)  # "ようやく、頭がはっきりしてきた。"

    def _uncurse_all(self) -> None:
        """全ての呪いを解除する (C版 use.c: uncurse_all)"""
        obj = self.player.pack
        while obj:
            obj.is_cursed = False
            obj = obj.next_object

    def _monster_at(self, row: int, col: int):
        """指定位置のモンスターを取得"""
        monsters = self.dungeon.monsters if hasattr(self.dungeon, 'monsters') else []
        for monster in monsters:
            if monster.row == row and monster.col == col:
                return monster
        return None

    def _show_monsters(self) -> None:
        """モンスターを表示する (C版 use.c: show_monsters)"""
        GameState.detect_monster = True
        monsters = self.dungeon.monsters if hasattr(self.dungeon, 'monsters') else []
        if monsters:
            for monster in monsters:
                if self.display:
                    self.display.mvaddch(monster.row, monster.col, monster.m_char if hasattr(monster, 'm_char') else 'M')
            if self.display:
                self.display.refresh()
        # else:
        #     message("奇妙な感じがした", 0)

    def _show_objects(self) -> None:
        """オブジェクトを表示する (C版 use.c: show_objects)"""
        obj = self.dungeon.level_objects if hasattr(self.dungeon, 'level_objects') else None
        if obj:
            while obj:
                if self.display:
                    ch = self._get_mask_char(obj.item_type)
                    self.display.mvaddch(obj.row, obj.col, ch)
                obj = obj.next_object
            if self.display:
                self.display.refresh()

    def _get_mask_char(self, mask: int) -> str:
        """マスクから文字を取得 (C版 room.c: get_mask_char)"""
        match mask:
            case const.SCROL:
                return '?'
            case const.POTION:
                return '!'
            case const.GOLD:
                return '*'
            case const.FOOD:
                return ':'
            case const.WAND:
                return '/'
            case const.ARMOR:
                return ']'
            case const.WEAPON:
                return ')'
            case const.RING:
                return '='
            case const.AMULET:
                return ','
            case _:
                return '~'

    def _create_monster(self) -> None:
        """モンスターを生成する (C版 use.c: create_monster)"""
        try:
            from .combat import MonsterAI
        except ImportError:
            from combat import MonsterAI
        
        ai = MonsterAI(self.player, self.dungeon)
        ai.display = getattr(self, 'display', None)
        ai.msg = getattr(self, 'msg', None)
        ai.game = getattr(self, 'game', None)
        ai.cur_level = getattr(self, 'cur_level', 1)
        ai.create_monster()

    def _aggravate(self) -> None:
        """モンスターを怒らせる (C版 use.c: aggravate)"""
        if self.message:
            self.message.message(get_message(65), 0)  # "どこからか、かん高いうなり声が聞こえてくる。"
        
        try:
            from .combat import MonsterAI
        except ImportError:
            from combat import MonsterAI
        
        ai = MonsterAI(self.player, self.dungeon)
        ai.display = getattr(self, 'display', None)
        ai.msg = getattr(self, 'msg', None)
        ai.game = getattr(self, 'game', None)
        ai.aggravate()

    def _draw_magic_map(self) -> None:
        """魔法の地図を描画 (C版 room.c: draw_magic_map)"""
        if not self.display:
            return
        mask = const.HORWALL | const.VERTWALL | const.DOOR | const.TUNNEL | const.TRAP | const.STAIRS | const.MONSTER
        for i in range(const.ROGUE_LINES):
            for j in range(const.ROGUE_COLUMNS):
                if hasattr(self.dungeon, 'dungeon'):
                    s = self.dungeon.dungeon[i][j]
                else:
                    s = self.dungeon.dungeon[i][j]
                if s & mask:
                    ch = self.display.mvinch(i, j)
                    if (ch == ' ') or ((ch >= 'A') and (ch <= 'Z')) or (s & (const.TRAP | const.HIDDEN)):
                        # HIDDEN を解除
                        if hasattr(self.dungeon, 'dungeon'):
                            self.dungeon.dungeon[i][j] &= ~const.HIDDEN
                        else:
                            self.dungeon.dungeon[i][j] &= ~const.HIDDEN
                        if s & const.HORWALL:
                            new_ch = '-'
                        elif s & const.VERTWALL:
                            new_ch = '|'
                        elif s & const.DOOR:
                            new_ch = '+'
                        elif s & const.TRAP:
                            new_ch = '^'
                        elif s & const.STAIRS:
                            new_ch = '%'
                        elif s & const.TUNNEL:
                            new_ch = '#'
                        else:
                            continue
                        if not (s & const.MONSTER) or (ch == ' '):
                            self.display.addch(new_ch)

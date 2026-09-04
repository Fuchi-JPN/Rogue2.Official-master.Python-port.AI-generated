"""
special_actions.py - 特殊アクション
src/throw.c, src/zap.c, src/ring.c から移植

投擲、杖の効果、指輪の装備によるステータス変化を実装します。
"""

from typing import Optional, Tuple

try:
    from . import const, utils
    from .entities import Player, Monster, Item
    from .dungeon import DungeonLevel
    from .game_state import GameState
    from .ai.input_hook import hook_getch_int as _ai_hook_getch_int
except ImportError:
    import const, utils
    import entities
    import dungeon
    Player = entities.Player
    Monster = entities.Monster
    Item = entities.Item
    DungeonLevel = dungeon.DungeonLevel
    from game_state import GameState
    try:
        from ai.input_hook import hook_getch_int as _ai_hook_getch_int
    except ImportError:
        _ai_hook_getch_int = None


def _ai_aware_getch():
    """AIキーキューを優先するcurses.getch（自動プレイ時の後続入力用）"""
    if _ai_hook_getch_int is not None:
        hooked = _ai_hook_getch_int()
        if hooked is not None:
            return hooked
    import curses
    return curses.getch()


# グローバル変数は GameState に集約
_GS = GameState

def __getattr__(name):
    _proxy = {
        'wizard': 'wizard', 'stealthy': 'stealthy', 'r_rings': 'r_rings',
        'e_rings': 'e_rings', 'add_strength': 'add_strength',
        'regeneration': 'regeneration', 'ring_exp': 'ring_exp',
        'r_teleport': 'r_teleport', 'r_see_invisible': 'r_see_invisible',
        'sustain_strength': 'sustain_strength', 'maintain_armor': 'maintain_armor',
        'auto_search': 'auto_search', 'being_held': 'being_held',
    }
    if name in _proxy:
        return getattr(_GS, _proxy[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __setattr__(name, value):
    _proxy = {
        'wizard': 'wizard', 'stealthy': 'stealthy', 'r_rings': 'r_rings',
        'e_rings': 'e_rings', 'add_strength': 'add_strength',
        'regeneration': 'regeneration', 'ring_exp': 'ring_exp',
        'r_teleport': 'r_teleport', 'r_see_invisible': 'r_see_invisible',
        'sustain_strength': 'sustain_strength', 'maintain_armor': 'maintain_armor',
        'auto_search': 'auto_search', 'being_held': 'being_held',
    }
    if name in _proxy:
        setattr(_GS, _proxy[name], value)
    else:
        globals()[name] = value


class ThrowAction:
    """投擲アクションクラス (C版 throw.c から移植)"""

    def __init__(self, player: Player, dungeon: DungeonLevel, display=None, message=None):
        self.player = player
        self.dungeon = dungeon
        self.display = display
        self.message = message
        # rand_around用の静的変数
        self._rand_row = 0
        self._rand_col = 0
        self._rand_pos = [8, 7, 1, 3, 4, 5, 2, 6, 0]  # C版の初期値

    def throw(self, dirch: int, weapon: Item) -> bool:
        """
        アイテムを投げる (C版 throw.c: throw)
        
        Args:
            dirch: 方向 (0-7)
            weapon: 投げる武器
        
        Returns:
            成功したかどうか
        """
        if weapon is None:
            return False

        # 呪われた装備品は投げられない
        if (weapon.in_use_flags & const.BEING_USED) and weapon.is_cursed:
            if self.message:
                self.message.message("呪われていて投げられない！")
            return False

        row = self.player.row
        col = self.player.col

        # 装備中の武器を外す (C版: lines 64-72)
        if (weapon.in_use_flags & const.BEING_WIELDED) and (weapon.quantity <= 1):
            self._unwield(weapon)
        elif weapon.in_use_flags & const.BEING_WORN:
            # mv_aquatars() は未実装
            self._unwear(weapon)
        elif weapon.in_use_flags & const.ON_EITHER_HAND:
            self._un_put_on(weapon)

        # 投擲経路を取得し、モンスターに当たったかチェック
        row, col, monster = self._get_thrown_at_monster(weapon, dirch, row, col)

        # プレイヤー位置を再描画 (C版: lines 74-75)
        if self.display:
            self.display.mvaddch(self.player.row, self.player.col, self.player.fchar)
            self.display.refresh()

        # 着地点を描画 (C版: lines 77-79)
        if self._rogue_can_see(row, col) and ((row != self.player.row) or (col != self.player.col)):
            if self.display:
                dch = self._get_dungeon_char(row, col)
                self.display.mvaddch(row, col, dch)

        # モンスターに当たった場合 (C版: lines 80-89)
        if monster:
            self._wake_up(monster)
            self._check_gold_seeker(monster)

            if not self._throw_at_monster(monster, weapon):
                self._flop_weapon(weapon, row, col)
        else:
            self._flop_weapon(weapon, row, col)

        # アイテムを消費 (C版: line 90)
        self._vanish(weapon, True)
        return True

    def _throw_at_monster(self, monster: Monster, weapon: Item) -> bool:
        """モンスターに投げる"""
        hit_chance = self._get_hit_chance(weapon)
        damage = self._get_weapon_damage(weapon)

        # 矢と弓のボーナス
        if (weapon.which_kind == const.ARROW and
            self.player.weapon and self.player.weapon.which_kind == const.BOW):
            damage += self._get_weapon_damage(self.player.weapon)
            damage = (damage * 2) // 3
            hit_chance += hit_chance // 3
        elif (weapon.in_use_flags & const.BEING_WIELDED and
              weapon.which_kind in (const.DAGGER, const.SHURIKEN, const.DART)):
            damage = (damage * 3) // 2
            hit_chance += hit_chance // 3

        if not utils.rand_percent(hit_chance):
            return False

        # 杖の効果
        if weapon.item_type == const.WAND and utils.rand_percent(75):
            self._zap_monster(monster, weapon.which_kind)
        elif weapon.item_type == const.POTION:
            self._potion_monster(monster, weapon.which_kind)
        else:
            self._mon_damage(monster, damage)

        return True

    def _get_thrown_at_monster(self, obj: Item, dirch: int, row: int, col: int) -> Tuple[int, int, Optional[Monster]]:
        """
        投げた先のモンスターを取得 (C版 throw.c: get_thrown_at_monster)
        
        Args:
            obj: 投げるオブジェクト
            dirch: 方向 (0-7)
            row: 開始行
            col: 開始列
        
        Returns:
            (最終行, 最終列, モンスターまたはNone)
        """
        orow = row
        ocol = col

        ch = self._get_mask_char(obj.item_type)

        for i in range(24):
            # 方向に従って座標を更新 (C版: line 147)
            row, col = self._get_dir_rc(dirch, row, col, False)
            
            # 範囲チェック
            if row < const.MIN_ROW or row >= const.ROGUE_LINES - 1:
                return orow, ocol, None
            if col < 0 or col >= const.ROGUE_COLUMNS:
                return orow, ocol, None

            tile = self.dungeon.get_tile(row, col)

            # 壁または何もない場所なら停止 (C版: lines 148-154)
            if (tile == const.NOTHING or
                ((tile & (const.HORWALL | const.VERTWALL | const.HIDDEN)) and
                 not (tile & const.TRAP))):
                return orow, ocol, None

            # 飛翔経路を表示 (C版: lines 155-163)
            if (i != 0) and self._rogue_can_see(orow, ocol):
                if self.display:
                    dch = self._get_dungeon_char(orow, ocol)
                    self.display.mvaddch(orow, ocol, dch)

            if self._rogue_can_see(row, col):
                if not (tile & const.MONSTER):
                    if self.display:
                        self.display.mvaddch(row, col, ch)
                if self.display:
                    self.display.refresh()

            orow = row
            ocol = col

            # モンスターがいる場合 (C版: lines 166-170)
            if tile & const.MONSTER:
                if not self._imitating(row, col):
                    monster = self._monster_at(row, col)
                    if monster:
                        return row, col, monster

            # 通路では加速 (C版: lines 171-173)
            if tile & const.TUNNEL:
                i += 2

        return row, col, None

    def _flop_weapon(self, weapon: Item, row: int, col: int) -> None:
        """
        武器を落とす (C版 throw.c: flop_weapon)
        
        投げた武器が床に落ちる処理。周囲9マスから適切な位置を探す。
        """
        i = 0
        found = False

        # 適切な着地点を探す (C版: lines 188-197)
        while (i < 9 and
               self.dungeon.get_tile(row, col) & ~(const.FLOOR | const.TUNNEL | const.DOOR | const.MONSTER)):
            row, col = self._rand_around(i, row, col)
            i += 1

            if (row > (const.ROGUE_LINES - 2) or row < const.MIN_ROW or
                col > (const.ROGUE_COLUMNS - 1) or col < 0 or
                not self.dungeon.get_tile(row, col) or
                self.dungeon.get_tile(row, col) & ~(const.FLOOR | const.TUNNEL | const.DOOR | const.MONSTER)):
                continue

            found = True
            break

        if found or (i == 0):
            # 新しい武器オブジェクトを作成 (C版: lines 200-205)
            new_weapon = Item()
            # 属性をコピー
            for attr in ['item_type', 'which_kind', 'damage', 'hit_enchant', 'd_enchant',
                         'is_protected', 'is_cursed', 'identified', 'quantity']:
                if hasattr(weapon, attr):
                    setattr(new_weapon, attr, getattr(weapon, attr))
            new_weapon.in_use_flags = const.NOT_USED
            new_weapon.quantity = 1
            new_weapon.ichar = ord('L')
            new_weapon.row = row
            new_weapon.col = col
            
            # フロアに配置 (C版: line 205)
            self._place_at(new_weapon, row, col)
            
            # 表示更新 (C版: lines 206-223)
            if self._rogue_can_see(row, col) and ((row != self.player.row) or (col != self.player.col)):
                tile = self.dungeon.get_tile(row, col)
                mon = tile & const.MONSTER
                
                if mon:
                    # モンスターがいる位置なら trail_char を設定
                    monster = self._monster_at(row, col)
                    if monster:
                        monster.trail_char = self._get_dungeon_char(row, col)
                
                # 表示
                if self.display:
                    dch = self._get_dungeon_char(row, col)
                    self.display.mvaddch(row, col, dch)
        else:
            # どこにも置けない場合 (C版 throw.c:224-232 mesg[215] "%sは地面に落ちると、どこかに消えてしまった。")
            if self.message:
                try:
                    from .text_resources import get_message as _gm
                    _name = getattr(weapon, 'damage', '') or '武器'
                    # get_desc相当がなければ武器種別名で代替
                    self.message.message(_gm(215) % _name if '%s' in _gm(215) else _gm(215))
                except Exception:
                    self.message.message("武器は消えた！")

    def _rand_around(self, i: int, row: int, col: int) -> Tuple[int, int]:
        """
        周囲のランダムな位置を取得 (C版 throw.c: rand_around)
        
        C版のアルゴリズムを忠実に再現:
        - i=0 の時に初期化とシャッフルを行う
        - pos配列を使ってランダムな順序で周囲9マスを返す
        """
        # C版の静的配列 (lines 242-243)
        # ra[] = { 1, 1, -1, -1, 0, 1, 0, -1, 0 }
        # ca[] = { 1, -1, 1, -1, 1, 0, 0, 0, -1 }
        ra = [1, 1, -1, -1, 0, 1, 0, -1, 0]
        ca = [1, -1, 1, -1, 1, 0, 0, 0, -1]

        if i == 0:
            # 初期化 (C版: lines 245-259)
            self._rand_row = row
            self._rand_col = col

            # ランダムにシャッフル
            o = utils.get_rand(1, 8)
            for _ in range(5):
                x = utils.get_rand(0, 8) % 9
                y = (x + o) % 9
                self._rand_pos[x], self._rand_pos[y] = self._rand_pos[y], self._rand_pos[x]

        # 位置を取得 (C版: lines 261-263)
        j = self._rand_pos[i] % 9
        return self._rand_row + ra[j], self._rand_col + ca[j]

    def _potion_monster(self, monster: Monster, kind: int) -> None:
        """
        ポーションをモンスターに投げる (C版 throw.c: potion_monster)
        
        ポーションの種類に応じてモンスターに効果を与える。
        """
        # 最大HPを取得 (C版: line 272)
        maxhp = entities.MON_TAB[ord(monster.m_char) - ord('A')]["hp_to_kill"] if hasattr(monster, 'm_char') else monster.hp_to_kill

        if kind in (const.RESTORE_STRENGTH, const.LEVITATION, const.HALLUCINATION,
                    const.DETECT_MONSTER, const.DETECT_OBJECTS, const.SEE_INVISIBLE):
            # 効果なし (C版: lines 275-281)
            pass
        elif kind == const.EXTRA_HEALING:
            # 大回復 (C版: lines 282-284)
            monster.hp_to_kill += (maxhp - monster.hp_to_kill) * 2 // 3
        elif kind in (const.INCREASE_STRENGTH, const.HEALING, const.RAISE_LEVEL):
            # 小回復 (C版: lines 285-289)
            monster.hp_to_kill += (maxhp - monster.hp_to_kill) // 5
        elif kind == const.POISON:
            # 毒ダメージ (C版: lines 290-292)
            self._mon_damage(monster, (monster.hp_to_kill // 4) + 1)
        elif kind == const.BLINDNESS:
            # 盲目＝睡眠 (C版: lines 293-295)
            monster.m_flags |= (const.ASLEEP | const.WAKENS)
        elif kind == const.CONFUSION:
            # 混乱 (C版: lines 296-299)
            monster.m_flags |= const.CONFUSED
            monster.moves_confused += utils.get_rand(12, 22)
        elif kind == const.HASTE_SELF:
            # 加速 (C版: lines 300-305)
            if monster.m_flags & const.SLOWED:
                monster.m_flags &= ~const.SLOWED
            else:
                monster.m_flags |= const.HASTED

    def _get_hit_chance(self, weapon: Item) -> int:
        """命中確率を計算"""
        if weapon is None:
            return 40
        return 40 + 3 * (self._get_number(weapon.damage) + weapon.hit_enchant)

    def _get_weapon_damage(self, weapon: Item) -> int:
        """武器ダメージを計算"""
        if weapon is None:
            return 0
        return self._get_damage(weapon.damage)

    def _get_damage(self, ds: str) -> int:
        """ダメージ文字列からダメージを計算"""
        total = 0
        i = 0

        while i < len(ds):
            n = self._get_number(ds[i:])
            while i < len(ds) and ds[i] != 'd':
                i += 1
            if i >= len(ds):
                break
            i += 1

            d = self._get_number(ds[i:])
            while i < len(ds) and ds[i] != '/':
                i += 1

            for _ in range(n):
                total += utils.get_rand(1, d)

            if i < len(ds) and ds[i] == '/':
                i += 1

        return total

    def _get_number(self, s: str) -> int:
        """文字列から数値を取得"""
        total = 0
        for ch in s:
            if '0' <= ch <= '9':
                total = total * 10 + (ord(ch) - ord('0'))
            else:
                break
        return total

    def _mon_damage(self, monster: Monster, damage: int) -> int:
        """モンスターにダメージを与える"""
        monster.hp_to_kill -= damage
        if monster.hp_to_kill <= 0:
            if monster in self.dungeon.monsters:
                self.dungeon.monsters.remove(monster)
            return 0
        return 1

    def _get_direction(self) -> str:
        """方向を取得"""
        if self.message:
            self.message.message("どちらに？")
        try:
            ch = _ai_aware_getch()
            dir_map = {
                ord('h'): const.LEFT, ord('j'): const.DOWN,
                ord('k'): const.UP, ord('l'): const.RIGHT,
                ord('y'): const.LEFTUP, ord('u'): const.UPRIGHT,
                ord('b'): const.DOWNLEFT, ord('n'): const.RIGHTDOWN,
            }
            return dir_map.get(ch, const.CANCEL)
        except Exception:
            return const.CANCEL

    def _pack_letter(self, prompt: str, category: int) -> str:
        """インベントリから選択 (C版 pack.c: pack_letter)"""
        obj = self.player.pack
        has_match = False
        while obj:
            if obj.item_type & category:
                has_match = True
                break
            obj = obj.next_object

        if not has_match:
            return const.CANCEL

        if self.display and self.message:
            self.display.inventory(self.player.pack, category, None, self.player)
            self.message.message(prompt)
            while True:
                try:
                    ch = _ai_aware_getch()
                except Exception:
                    break
                if ch == 27:
                    return const.CANCEL
                if ch == ord('*'):
                    # LIST: 再表示して再入力 (C版 pack_letter相当)
                    self.display.inventory(self.player.pack, category, None, self.player)
                    self.message.message(prompt)
                    continue
                return chr(ch)

        obj = self.player.pack
        while obj:
            if obj.item_type & category:
                return chr(obj.ichar) if obj.ichar else const.CANCEL
            obj = obj.next_object

        return const.CANCEL

    def _get_letter_object(self, ch: str) -> Optional[Item]:
        """文字からアイテムを取得"""
        obj = self.player.pack
        while obj:
            if chr(obj.ichar) == ch:
                return obj
            obj = obj.next_object
        return None

    def _unwield(self, weapon: Item) -> None:
        """武器を外す"""
        weapon.in_use_flags &= ~const.BEING_WIELDED
        self.player.weapon = None

    def _unwear(self, armor: Item) -> None:
        """防具を外す"""
        armor.in_use_flags &= ~const.BEING_WORN
        self.player.armor = None

    def _un_put_on(self, ring: Item) -> None:
        """指輪を外す"""
        if ring.in_use_flags & const.ON_LEFT_HAND:
            ring.in_use_flags &= ~const.ON_LEFT_HAND
            self.player.left_ring = None
        elif ring.in_use_flags & const.ON_RIGHT_HAND:
            ring.in_use_flags &= ~const.ON_RIGHT_HAND
            self.player.right_ring = None

    def _vanish(self, item: Item, rm: bool) -> None:
        """
        アイテムを消滅させる (C版 use.c: vanish)
        
        Args:
            item: 消滅させるアイテム
            rm: reg_move() を呼ぶかどうか（現在は未実装）
        """
        if item.quantity > 1:
            item.quantity -= 1
        else:
            # 装備フラグをクリア
            if item.in_use_flags & const.BEING_WIELDED:
                self._unwield(item)
            elif item.in_use_flags & const.BEING_WORN:
                self._unwear(item)
            elif item.in_use_flags & const.ON_EITHER_HAND:
                self._un_put_on(item)
            
            # インベントリから削除
            self._remove_from_pack(item)
        
        if rm:
            # reg_move() はここで呼ぶべきだが、現在は未実装
            pass

    def _remove_from_pack(self, item: Item) -> None:
        """インベントリからアイテムを削除"""
        pack = self.player.pack
        if pack is None:
            return
        
        if pack == item:
            self.player.pack = item.next_object
        else:
            curr = pack
            while curr and curr.next_object != item:
                curr = curr.next_object
            if curr:
                curr.next_object = item.next_object

    def _place_at(self, item: Item, row: int, col: int) -> None:
        """アイテムを配置 (C版 object.c: place_at)"""
        item.row = row
        item.col = col
        item.next_object = self.dungeon.level_objects
        self.dungeon.level_objects = item
        self.dungeon.set_tile(row, col, self.dungeon.get_tile(row, col) | const.OBJECT)

    def _imitating(self, row: int, col: int) -> bool:
        """
        イミテーターかチェック (C版 monster.c: imitating)
        
        モンスターが偽装しているかどうかを判定。
        """
        monster = self._monster_at(row, col)
        if monster and (monster.m_flags & const.IMITATES):
            return True
        return False

    def _monster_at(self, row: int, col: int) -> Optional[Monster]:
        """指定位置のモンスターを取得 (C版 monster.c: object_at)"""
        monster = self.dungeon.level_monsters
        while monster:
            if monster.row == row and monster.col == col:
                return monster
            monster = monster.next_object
        return None

    def _rogue_can_see(self, row: int, col: int) -> bool:
        """プレイヤーが指定位置を見えるか (C版 monster.c: rogue_can_see)"""
        if GameState.blind:
            return False
        rdif = row - self.player.row
        cdif = col - self.player.col
        if -1 <= rdif <= 1 and -1 <= cdif <= 1:
            return True
        rn = self.dungeon.get_room_number(row, col)
        if rn != const.NO_ROOM and rn == GameState.cur_room:
            rooms = self.dungeon.rooms
            if rn < len(rooms) and not (rooms[rn].is_room & const.R_MAZE):
                return True
        return False

    def _get_dungeon_char(self, row: int, col: int) -> str:
        """指定位置のダンジョン文字を取得 (C版 display.c: get_dungeon_char)"""
        tile = self.dungeon.get_tile(row, col)
        
        if tile & const.MONSTER:
            monster = self._monster_at(row, col)
            if monster:
                return monster.m_char if hasattr(monster, 'm_char') else 'M'
        if tile & const.OBJECT:
            obj = self._object_at(row, col)
            if obj:
                return chr(obj.ichar) if obj.ichar else '*'
        if tile & const.STAIRS:
            return '%'
        if tile & const.TRAP:
            return '^'
        if tile & const.DOOR:
            return '+'
        if tile & const.FLOOR:
            return '.'
        if tile & const.TUNNEL:
            return '#'
        if tile & const.HORWALL:
            return '-'
        if tile & const.VERTWALL:
            return '|'
        return ' '

    def _object_at(self, row: int, col: int) -> Optional[Item]:
        """指定位置のオブジェクトを取得"""
        obj = self.dungeon.level_objects
        while obj:
            if obj.row == row and obj.col == col:
                return obj
            obj = obj.next_object
        return None

    def _wake_up(self, monster: Monster) -> None:
        """モンスターを起こす (C版 monster.c: wake_up)"""
        monster.m_flags &= ~(const.ASLEEP | const.IMITATES | const.WAKENS)

    def _check_gold_seeker(self, monster: Monster) -> None:
        """ゴールド探索者をチェック (C版 spechit.c: check_gold_seeker)"""
        # C: monster->m_flags &= ~SEEKS_GOLD;
        monster.m_flags &= ~const.SEEKS_GOLD

    def _get_mask_char(self, item_type: int) -> str:
        """アイテムタイプから文字を取得 (C版 room.c: get_mask_char)"""
        if item_type == const.WEAPON:
            return ')'
        elif item_type == const.ARMOR:
            return ']'  # C版 room.c:165 ARMOR->']'
        elif item_type == const.RING:
            return '='
        elif item_type == const.POTION:
            return '!'
        elif item_type == const.SCROL:
            return '?'
        elif item_type == const.WAND:
            return '/'  # C版 room.c:161 WAND->'/'
        elif item_type == const.AMULET:
            return '"'
        elif item_type == const.FOOD:
            return ':'
        return '*'

    def _get_dir_rc(self, dirch: str, row: int, col: int, allow_off_screen: bool) -> Tuple[int, int]:
        """方向から座標変化を取得"""
        try:
            from .dungeon import get_direction_offset
        except ImportError:
            from dungeon import get_direction_offset
        dr, dc = get_direction_offset(dirch)
        return row + dr, col + dc

    def _zap_monster(self, monster: Monster, kind: int) -> None:
        """モンスターに杖の効果を与える (C版 zap.c:188-261)"""
        if kind == const.SLOW_MONSTER:
            if monster.m_flags & const.HASTED:
                monster.m_flags &= ~const.HASTED
            else:
                monster.slowed_toggle = 0
                monster.m_flags |= const.SLOWED
        elif kind == const.HASTE_MONSTER:
            if monster.m_flags & const.SLOWED:
                monster.m_flags &= ~const.SLOWED
            else:
                monster.m_flags |= const.HASTED
        elif kind == const.TELE_AWAY:
            self._tele_away(monster)
        elif kind == const.CONFUSE_MONSTER:
            monster.m_flags |= const.CONFUSED
            monster.moves_confused += utils.get_rand(12, 22)
        elif kind == const.INVISIBILITY:
            monster.m_flags |= const.INVISIBLE
        elif kind == const.POLYMORPH:
            # モンスターを変身 (C版 zap.c:224-238)
            if monster.m_flags & const.HOLDS:
                GameState.being_held = False
            # 現在の状態を保存
            nm = monster.next_monster
            tc = monster.trail_char
            row = monster.row
            col = monster.col
            # 新しいモンスターを生成
            self._gr_monster(monster, utils.get_rand(0, const.MONSTERS - 1))
            # 状態を復元
            monster.row = row
            monster.col = col
            monster.next_monster = nm
            monster.trail_char = tc
            # イミテーターでない場合は起こす
            if not (monster.m_flags & const.IMITATES):
                self._wake_up(monster)
        elif kind == const.PUT_TO_SLEEP:
            monster.m_flags |= (const.ASLEEP | const.NAPPING)
            monster.nap_length = utils.get_rand(3, 6)
        elif kind == const.MAGIC_MISSILE:
            # 魔法の矢 - プレイヤーの攻撃として扱う (C版 zap.c:243-245)
            self._rogue_hit(monster, True)
        elif kind == const.CANCELLATION:
            if monster.m_flags & const.HOLDS:
                GameState.being_held = False
            if monster.m_flags & const.STEALS_ITEM:
                monster.drop_percent = 0
            monster.m_flags &= ~(const.FLIES | const.FLITS | const.SPECIAL_HIT |
                                 const.INVISIBLE | const.FLAMES | const.IMITATES |
                                 const.CONFUSES | const.SEEKS_GOLD | const.HOLDS)
        elif kind == const.DO_NOTHING:
            if self.message:
                self.message.message("何も起きなかった。", 0)

    def _gr_monster(self, monster: Monster, mn: int) -> None:
        """
        モンスターを生成/変身させる (C版 monster.c: gr_monster)
        
        Args:
            monster: モンスターオブジェクト
            mn: モンスター番号 (0-25)
        """
        try:
            from .entities import MON_TAB
        except ImportError:
            from entities import MON_TAB
        
        # モンスターテーブルからコピー
        mon_data = MON_TAB[mn]
        monster.m_flags = mon_data["m_flags"]
        monster.damage = mon_data["damage"]
        monster.hp_to_kill = mon_data["hp_to_kill"]
        monster.m_char = mon_data["m_char"]
        monster.kill_exp = mon_data["kill_exp"]
        monster.first_level = mon_data["first_level"]
        monster.last_level = mon_data["last_level"]
        monster.hit_chance = mon_data["m_hit_chance"]
        monster.drop_percent = mon_data["drop_percent"]
        
        # イミテーターの場合は偽装文字を設定
        if monster.m_flags & const.IMITATES:
            monster.disguise = self._gr_obj_char()
        
        # アミュレットレベルより深い階層では加速
        cur_level = GameState.cur_level
        
        if cur_level > (const.AMULET_LEVEL + 2):
            monster.m_flags |= const.HASTED
        
        monster.trow = const.NO_ROOM

    def _gr_obj_char(self) -> str:
        """ランダムなオブジェクト文字を生成 (C版 monster.c: gr_obj_char)"""
        rs = "%!?]=/):*"
        return rs[utils.get_rand(0, 8)]

    def _rogue_hit(self, monster: Monster, must_hit: bool) -> None:
        """
        プレイヤーがモンスターを攻撃する (C版 hit.c: rogue_hit)
        魔法の矢などの特殊攻撃用に簡略化
        """
        try:
            from .combat import Combat
        except ImportError:
            from combat import Combat
        
        # Combat クラスを使用して攻撃
        combat = Combat(self.player, self.dungeon)
        combat.rogue_hit(monster, must_hit)

    def _tele_away(self, monster: Monster) -> None:
        """モンスターをテレポートさせる (C版 zap.c: tele_away)"""
        try:
            from .combat import being_held
        except ImportError:
            from combat import being_held

        if monster.m_flags & const.HOLDS:
            GameState.being_held = False

        # 現在位置のモンスター表示を消す
        if self.display:
            self.display.mvaddch(monster.row, monster.col, monster.trail_char)
        
        self.dungeon.set_tile(monster.row, monster.col,
                              self.dungeon.get_tile(monster.row, monster.col) & ~const.MONSTER)

        # ランダムな位置へ移動
        row, col = self._gr_row_col(const.FLOOR | const.TUNNEL | const.STAIRS | const.OBJECT)
        if row >= 0 and col >= 0:
            monster.row = row
            monster.col = col
            self.dungeon.set_tile(row, col,
                                  self.dungeon.get_tile(row, col) | const.MONSTER)
            monster.trail_char = self._get_dungeon_char(row, col)
            
            # 表示更新
            if self._rogue_can_see(row, col):
                if self.display:
                    self.display.mvaddch(row, col, monster.m_char)

    def _gr_row_col(self, mask: int) -> Tuple[int, int]:
        """ランダムな位置を取得 (C版 move.c: gr_row_col)"""
        for _ in range(100):
            row = utils.get_rand(const.MIN_ROW, const.ROGUE_LINES - 2)
            col = utils.get_rand(0, const.ROGUE_COLUMNS - 1)
            tile = self.dungeon.get_tile(row, col)
            if tile & mask:
                return row, col
        return -1, -1


class WandAction:
    """杖アクションクラス"""

    def __init__(self, player: Player, dungeon: DungeonLevel, display=None, message=None):
        self.player = player
        self.dungeon = dungeon
        self.display = display
        self.message = message

    def zapp(self, dir_const=None, wand=None) -> None:
        """杖を振る"""
        if dir_const is None or wand is None:
            dirch = self._get_direction()
            if dirch == const.CANCEL:
                return
            wch = self._pack_letter("どの杖を振りますか？", const.WAND)
            if wch == const.CANCEL:
                return
            wand = self._get_letter_object(wch)
            if wand is None or wand.item_type != const.WAND:
                return
        else:
            dirch = dir_const

        if wand.class_ <= 0:
            return

        wand.class_ -= 1
        row = self.player.row
        col = self.player.col

        if wand.which_kind == const.MAGIC_MISSILE:
            monster = self._get_missiled_monster(dirch, row, col)
        else:
            monster = self._get_zapped_monster(dirch, row, col)

        if monster:
            self._wake_up(monster)
            self._zap_monster(monster, wand.which_kind)

    def _get_zapped_monster(self, dirch: str, row: int, col: int) -> Optional[Monster]:
        """杖の効果を受けるモンスターを取得"""
        while True:
            orow = row
            ocol = col
            row, col = self._get_dir_rc(dirch, row, col, False)

            if ((row == orow and col == ocol) or
                (self.dungeon.dungeon[row][col] & (const.HORWALL | const.VERTWALL)) or
                self.dungeon.dungeon[row][col] == const.NOTHING):
                return None

            if self.dungeon.dungeon[row][col] & const.MONSTER:
                if not self._imitating(row, col):
                    return self._monster_at(row, col)

    def _get_missiled_monster(self, dirch: str, row: int, col: int) -> Optional[Monster]:
        """魔法の矢のターゲットを取得"""
        orow = row
        ocol = col
        first = True

        while True:
            row, col = self._get_dir_rc(dirch, row, col, False)

            if ((row == orow and col == ocol) or
                (self.dungeon.dungeon[row][col] & (const.HORWALL | const.VERTWALL)) or
                self.dungeon.dungeon[row][col] == const.NOTHING):
                return None

            if self.dungeon.dungeon[row][col] & const.MONSTER:
                if not self._imitating(row, col):
                    return self._monster_at(row, col)

            first = False
            orow = row
            ocol = col

    def _zap_monster(self, monster: Monster, kind: int) -> None:
        """モンスターに杖の効果を与える (C版 zap.c:188-261)"""
        if kind == const.SLOW_MONSTER:
            if monster.m_flags & const.HASTED:
                monster.m_flags &= ~const.HASTED
            else:
                monster.slowed_toggle = 0
                monster.m_flags |= const.SLOWED
        elif kind == const.HASTE_MONSTER:
            if monster.m_flags & const.SLOWED:
                monster.m_flags &= ~const.SLOWED
            else:
                monster.m_flags |= const.HASTED
        elif kind == const.TELE_AWAY:
            self._tele_away(monster)
        elif kind == const.CONFUSE_MONSTER:
            monster.m_flags |= const.CONFUSED
            monster.moves_confused += utils.get_rand(12, 22)
        elif kind == const.INVISIBILITY:
            monster.m_flags |= const.INVISIBLE
        elif kind == const.POLYMORPH:
            # モンスターを変身 (C版 zap.c:224-238)
            if monster.m_flags & const.HOLDS:
                GameState.being_held = False
            # 現在の状態を保存
            nm = monster.next_monster
            tc = monster.trail_char
            row = monster.row
            col = monster.col
            # 新しいモンスターを生成
            self._gr_monster(monster, utils.get_rand(0, const.MONSTERS - 1))
            # 状態を復元
            monster.row = row
            monster.col = col
            monster.next_monster = nm
            monster.trail_char = tc
            # イミテーターでない場合は起こす
            if not (monster.m_flags & const.IMITATES):
                self._wake_up(monster)
        elif kind == const.PUT_TO_SLEEP:
            monster.m_flags |= (const.ASLEEP | const.NAPPING)
            monster.nap_length = utils.get_rand(3, 6)
        elif kind == const.MAGIC_MISSILE:
            # 魔法の矢 - プレイヤーの攻撃として扱う (C版 zap.c:243-245)
            self._rogue_hit(monster, True)
        elif kind == const.CANCELLATION:
            if monster.m_flags & const.HOLDS:
                GameState.being_held = False
            if monster.m_flags & const.STEALS_ITEM:
                monster.drop_percent = 0
            monster.m_flags &= ~(const.FLIES | const.FLITS | const.SPECIAL_HIT |
                                 const.INVISIBLE | const.FLAMES | const.IMITATES |
                                 const.CONFUSES | const.SEEKS_GOLD | const.HOLDS)
        elif kind == const.DO_NOTHING:
            pass  # 何もしない

    def _gr_monster(self, monster: Monster, mn: int) -> None:
        """モンスターを生成/変身させる (C版 monster.c: gr_monster)"""
        try:
            from .entities import MON_TAB
        except ImportError:
            from entities import MON_TAB
        
        mon_data = MON_TAB[mn]
        monster.m_flags = mon_data["m_flags"]
        monster.damage = mon_data["damage"]
        monster.hp_to_kill = mon_data["hp_to_kill"]
        monster.m_char = mon_data["m_char"]
        monster.kill_exp = mon_data["kill_exp"]
        monster.first_level = mon_data["first_level"]
        monster.last_level = mon_data["last_level"]
        monster.hit_chance = mon_data["m_hit_chance"]
        monster.drop_percent = mon_data["drop_percent"]
        
        if monster.m_flags & const.IMITATES:
            monster.disguise = self._gr_obj_char()
        
        cur_level = GameState.cur_level
        
        if cur_level > (const.AMULET_LEVEL + 2):
            monster.m_flags |= const.HASTED
        
        monster.trow = const.NO_ROOM

    def _gr_obj_char(self) -> str:
        """ランダムなオブジェクト文字を生成"""
        rs = "%!?]=/):*"
        return rs[utils.get_rand(0, 8)]

    def _rogue_hit(self, monster: Monster, must_hit: bool) -> None:
        """プレイヤーがモンスターを攻撃する"""
        try:
            from .combat import Combat
        except ImportError:
            from combat import Combat
        
        combat = Combat(self.player, self.dungeon)
        combat.rogue_hit(monster, must_hit)

    def _tele_away(self, monster: Monster) -> None:
        """モンスターをテレポートさせる"""

        if monster.m_flags & const.HOLDS:
            GameState.being_held = False

        self.dungeon.dungeon[monster.row][monster.col] &= ~const.MONSTER

        for _ in range(100):
            row = utils.get_rand(const.MIN_ROW, const.ROGUE_LINES - 2)
            col = utils.get_rand(0, const.ROGUE_COLUMNS - 1)
            if self.dungeon.dungeon[row][col] & (const.FLOOR | const.TUNNEL | const.STAIRS):
                monster.row = row
                monster.col = col
                self.dungeon.dungeon[row][col] |= const.MONSTER
                break

    def _wake_up(self, monster: Monster) -> None:
        """モンスターを起こす"""
        monster.m_flags &= ~(const.ASLEEP | const.IMITATES | const.WAKENS)

    def _get_direction(self) -> str:
        """方向を取得"""
        if self.message:
            self.message.message("どちらに？")
        try:
            ch = _ai_aware_getch()
            dir_map = {
                ord('h'): const.LEFT, ord('j'): const.DOWN,
                ord('k'): const.UP, ord('l'): const.RIGHT,
                ord('y'): const.LEFTUP, ord('u'): const.UPRIGHT,
                ord('b'): const.DOWNLEFT, ord('n'): const.RIGHTDOWN,
            }
            return dir_map.get(ch, const.CANCEL)
        except Exception:
            return const.CANCEL

    def _pack_letter(self, prompt: str, category: int) -> str:
        """インベントリから選択 (C版 pack.c: pack_letter)"""
        obj = self.player.pack
        has_match = False
        while obj:
            if obj.item_type & category:
                has_match = True
                break
            obj = obj.next_object

        if not has_match:
            return const.CANCEL

        if self.display and self.message:
            self.display.inventory(self.player.pack, category, None, self.player)
            self.message.message(prompt)
            while True:
                try:
                    ch = _ai_aware_getch()
                except Exception:
                    break
                if ch == 27:
                    return const.CANCEL
                if ch == ord('*'):
                    # LIST: 再表示して再入力 (C版 pack_letter相当)
                    self.display.inventory(self.player.pack, category, None, self.player)
                    self.message.message(prompt)
                    continue
                return chr(ch)

        obj = self.player.pack
        while obj:
            if obj.item_type & category:
                return chr(obj.ichar) if obj.ichar else const.CANCEL
            obj = obj.next_object

        return const.CANCEL

    def _get_letter_object(self, ch: str) -> Optional[Item]:
        """文字からアイテムを取得"""
        obj = self.player.pack
        while obj:
            if chr(obj.ichar) == ch:
                return obj
            obj = obj.next_object
        return None

    def _get_dir_rc(self, dirch: str, row: int, col: int, allow_off_screen: bool) -> Tuple[int, int]:
        """方向から座標変化を取得"""
        try:
            from .dungeon import get_direction_offset
        except ImportError:
            from dungeon import get_direction_offset
        dr, dc = get_direction_offset(dirch)
        return row + dr, col + dc

    def _imitating(self, row: int, col: int) -> bool:
        """イミテーターかチェック (C版 monster.c: imitating)"""
        monster = self._monster_at(row, col)
        if monster and (monster.m_flags & const.IMITATES):
            return True
        return False

    def _monster_at(self, row: int, col: int) -> Optional[Monster]:
        """指定位置のモンスターを取得"""
        for monster in self.dungeon.monsters:
            if monster.row == row and monster.col == col:
                return monster
        return None


class RingAction:
    """指輪アクションクラス"""

    def __init__(self, player: Player):
        self.player = player

    def put_on_ring(self) -> None:
        """指輪を装備する"""

        if GameState.r_rings >= 2:
            return

        ch = self._pack_letter("どの指輪を装備しますか？", const.RING)
        if ch == const.CANCEL:
            return

        ring = self._get_letter_object(ch)
        if ring is None or ring.item_type != const.RING:
            return

        if ring.in_use_flags & (const.ON_LEFT_HAND | const.ON_RIGHT_HAND):
            return

        if GameState.r_rings == 1:
            on_left = self.player.left_ring is None
        else:
            on_left = self._select_hand()

        if on_left is None:
            return

        if (on_left and self.player.left_ring) or (not on_left and self.player.right_ring):
            return

        self._do_put_on(ring, on_left)
        self._ring_stats()

    def remove_ring(self) -> None:
        """指輪を外す"""

        if GameState.r_rings == 0:
            return

        # 左右の選択
        if self.player.left_ring and not self.player.right_ring:
            on_left = True
        elif not self.player.left_ring and self.player.right_ring:
            on_left = False
        else:
            on_left = self._select_hand()

        if on_left is None:
            return

        if on_left and self.player.left_ring:
            ring = self.player.left_ring
        elif not on_left and self.player.right_ring:
            ring = self.player.right_ring
        else:
            return

        if ring.is_cursed:
            return

        self._un_put_on(ring)
        self._ring_stats()

    def _do_put_on(self, ring: Item, on_left: bool) -> None:
        """指輪を装備する"""
        if on_left:
            ring.in_use_flags |= const.ON_LEFT_HAND
            self.player.left_ring = ring
        else:
            ring.in_use_flags |= const.ON_RIGHT_HAND
            self.player.right_ring = ring

    def _un_put_on(self, ring: Item) -> None:
        """指輪を外す"""
        if ring.in_use_flags & const.ON_LEFT_HAND:
            ring.in_use_flags &= ~const.ON_LEFT_HAND
            self.player.left_ring = None
        elif ring.in_use_flags & const.ON_RIGHT_HAND:
            ring.in_use_flags &= ~const.ON_RIGHT_HAND
            self.player.right_ring = None

    def _ring_stats(self) -> None:
        """指輪のステータスを更新"""

        GameState.stealthy = 0
        GameState.r_rings = 0
        GameState.e_rings = 0
        GameState.r_teleport = False
        GameState.sustain_strength = False
        GameState.add_strength = 0
        GameState.regeneration = 0
        GameState.ring_exp = 0
        GameState.r_see_invisible = False
        GameState.maintain_armor = False
        GameState.auto_search = 0

        for ring in [self.player.left_ring, self.player.right_ring]:
            if ring is None:
                continue

            GameState.r_rings += 1
            GameState.e_rings += 1

            if ring.which_kind == const.STEALTH:
                GameState.stealthy += 1
            elif ring.which_kind == const.R_TELEPORT:
                GameState.r_teleport = True
            elif ring.which_kind == const.REGENERATION:
                GameState.regeneration += 1
            elif ring.which_kind == const.SLOW_DIGEST:
                GameState.e_rings -= 2
            elif ring.which_kind == const.ADD_STRENGTH:
                GameState.add_strength += ring.class_
            elif ring.which_kind == const.SUSTAIN_STRENGTH:
                GameState.sustain_strength = True
            elif ring.which_kind == const.DEXTERITY:
                GameState.ring_exp += ring.class_
            elif ring.which_kind == const.R_SEE_INVISIBLE:
                GameState.r_see_invisible = True
            elif ring.which_kind == const.MAINTAIN_ARMOR:
                GameState.maintain_armor = True
            elif ring.which_kind == const.SEARCHING:
                GameState.auto_search += 2

    def _select_hand(self) -> Optional[bool]:
        """左右の手を選択"""
        # 簡易版 - 常に左
        return True

    def _pack_letter(self, prompt: str, category: int) -> str:
        """インベントリから選択 (C版 pack.c: pack_letter)"""
        obj = self.player.pack
        has_match = False
        while obj:
            if obj.item_type & category:
                has_match = True
                break
            obj = obj.next_object

        if not has_match:
            return const.CANCEL

        obj = self.player.pack
        while obj:
            if obj.item_type & category:
                return chr(obj.ichar) if obj.ichar else const.CANCEL
            obj = obj.next_object

        return const.CANCEL

    def _get_letter_object(self, ch: str) -> Optional[Item]:
        """文字からアイテムを取得"""
        obj = self.player.pack
        while obj:
            if chr(obj.ichar) == ch:
                return obj
            obj = obj.next_object
        return None

    def inv_rings(self) -> None:
        """装備中の指輪を表示"""
        if self.player.left_ring:
            pass  # 表示
        if self.player.right_ring:
            pass  # 表示


def gr_ring(ring: Item, assign_wk: bool) -> None:
    """指輪を生成"""
    ring.item_type = const.RING

    if assign_wk:
        ring.which_kind = utils.get_rand(0, const.RINGS - 1)

    ring.class_ = 0

    if ring.which_kind == const.R_TELEPORT:
        ring.is_cursed = True
    elif ring.which_kind in (const.ADD_STRENGTH, const.DEXTERITY):
        ring.class_ = utils.get_rand(0, 4) - 2
        while ring.class_ == 0:
            ring.class_ = utils.get_rand(0, 4) - 2
        ring.is_cursed = ring.class_ < 0
    elif ring.which_kind == const.ADORNMENT:
        ring.is_cursed = utils.coin_toss()

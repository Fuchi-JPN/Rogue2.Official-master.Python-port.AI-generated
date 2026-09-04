"""
combat.py - 戦闘システムとモンスターAI
src/hit.c, src/monster.c から移植

攻撃判定、ダメージ計算、経験値取得、モンスターAIを実装します。
"""

from typing import Optional, Tuple, List

try:
    from . import const, utils
    from .entities import Player, Monster, Item
    from .dungeon import DungeonLevel, get_direction_offset, get_room_number
    from .game_state import GameState
    
except ImportError:
    import const, utils
    import entities
    import dungeon
    Player = entities.Player
    Monster = entities.Monster
    Item = entities.Item
    DungeonLevel = dungeon.DungeonLevel
    get_direction_offset = dungeon.get_direction_offset
    get_room_number = dungeon.get_room_number
    from game_state import GameState
    from text_resources import get_message


# グローバル変数は GameState に集約
_GS = GameState

def __getattr__(name):
    _proxy = {
        'fight_monster': 'fight_monster', 'hit_message': 'hit_message',
        'wizard': 'wizard', 'ring_exp': 'ring_exp', 'r_rings': 'r_rings',
        'add_strength': 'add_strength', 'interrupted': 'interrupted',
        'being_held': 'being_held', 'mon_disappeared': 'mon_disappeared',
    }
    if name in _proxy:
        return getattr(_GS, _proxy[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __setattr__(name, value):
    _proxy = {
        'fight_monster': 'fight_monster', 'hit_message': 'hit_message',
        'wizard': 'wizard', 'ring_exp': 'ring_exp', 'r_rings': 'r_rings',
        'add_strength': 'add_strength', 'interrupted': 'interrupted',
        'being_held': 'being_held', 'mon_disappeared': 'mon_disappeared',
    }
    if name in _proxy:
        setattr(_GS, _proxy[name], value)
    else:
        globals()[name] = value

# モンスターテーブルとモンスター名は entities.py からインポート
try:
    from .entities import MON_TAB, M_NAMES
except ImportError:
    from entities import MON_TAB, M_NAMES


class Combat:
    """戦闘システムクラス"""

    def __init__(self, player: Player, dungeon: DungeonLevel):
        self.player = player
        self.dungeon = dungeon
        self.nick_name = "プレイヤー"
        self.cur_level = 1

    def mon_hit(self, monster: Monster, other: Optional[str] = None, flame: bool = False) -> None:
        """モンスターがプレイヤーを攻撃"""

        if GameState.fight_monster and monster != GameState.fight_monster:
            GameState.fight_monster = None

        monster.trow = const.NO_ROOM

        # 命中率を計算
        if self.cur_level >= (const.AMULET_LEVEL * 2):
            hit_chance = 100
        else:
            hit_chance = monster.hit_chance
            hit_chance -= ((2 * self.player.exp) + (2 * GameState.ring_exp)) - GameState.r_rings

        if GameState.wizard:
            hit_chance //= 2

        if not GameState.fight_monster:
            GameState.interrupted = True

        mn = self._mon_name(monster)

        if other:
            hit_chance -= (self.player.exp + GameState.ring_exp) - GameState.r_rings

        if not utils.rand_percent(hit_chance):
            if not GameState.fight_monster:
                # message=f"{other if other else mn}を避けた", 1)
                pass
            return

        if not GameState.fight_monster:
            # message=f"{other if other else mn}に攻撃された！", 1)
            pass

        # ダメージを計算
        if not (monster.m_flags & const.STATIONARY):
            damage = utils.roll_damage(monster.m_damage)
            if other and flame:
                damage -= self._get_armor_class(self.player.armor)
                if damage < 0:
                    damage = 1

            if self.cur_level >= (const.AMULET_LEVEL * 2):
                minus = (const.AMULET_LEVEL * 2) - self.cur_level
            else:
                minus = self._get_armor_class(self.player.armor) * 3
                minus = minus * damage // 100
            damage -= minus
        else:
            damage = monster.stationary_damage
            monster.stationary_damage += 1

        if GameState.wizard:
            damage //= 3

        if damage > 0:
            self._rogue_damage(damage, monster)

        # 特殊攻撃
        if monster.m_flags & const.SPECIAL_HIT:
            self._special_hit(monster)

    def rogue_hit(self, monster: Optional[Monster], force_hit: bool = False) -> None:
        """プレイヤーがモンスターを攻撃"""

        if monster is None:
            return

        if self._check_imitator(monster):
            return

        hit_chance = 100 if force_hit else self._get_hit_chance(self.player.weapon)

        if GameState.wizard:
            hit_chance *= 2

        if not utils.rand_percent(hit_chance):
            if not GameState.fight_monster:
                if getattr(self, 'msg', None):
                    self.msg.message("攻撃は外れた。", 0)
            self._check_gold_seeker(monster)
            self._wake_up(monster)
            return

        damage = self._get_weapon_damage(self.player.weapon)

        if GameState.wizard:
            damage *= 3

        if self._mon_damage(monster, damage):
            if not GameState.fight_monster:
                mn = self._mon_name(monster)
                if getattr(self, 'msg', None):
                    self.msg.message(f"{mn}にダメージを与えた。", 0)

        self._check_gold_seeker(monster)
        self._wake_up(monster)

    def _rogue_damage(self, d: int, monster: Optional[Monster]) -> None:
        """プレイヤーがダメージを受ける (C版 hit.c: rogue_damage)"""
        # C: if (d >= hp) { hp = 0; print; killed_by(monster, 0); } hp -= d; print;
        if d >= self.player.hp_current:
            self.player.hp_current = 0
            if getattr(self, 'game', None):
                self.game._print_stats(const.STAT_HP)
                self.game.killed_by(monster, 0)
                return
            # game未結線時もHP負値化で死亡を明示 (Cはhp-=dで負値)
            self.player.hp_current -= d
            return

        self.player.hp_current -= d
        if getattr(self, 'game', None):
            self.game._print_stats(const.STAT_HP)

    def _get_damage(self, ds: str, r: bool) -> int:
        """ダメージ文字列からダメージを計算"""
        i = 0
        total = 0

        while i < len(ds):
            n = self._get_number(ds[i:])
            while i < len(ds) and ds[i] != 'd':
                i += 1
            if i >= len(ds):
                break
            i += 1  # 'd'をスキップ

            d = self._get_number(ds[i:])
            while i < len(ds) and ds[i] != '/':
                i += 1

            for _ in range(n):
                if r:
                    total += utils.get_rand(1, d)
                else:
                    total += d

            if i < len(ds) and ds[i] == '/':
                i += 1

        return total

    def _get_w_damage(self, obj: Optional[Item]) -> int:
        """武器のダメージを計算"""
        if obj is None or obj.item_type != const.WEAPON:
            return -1

        to_hit = self._get_number(obj.damage) + obj.hit_enchant
        i = 0
        while i < len(obj.damage) and obj.damage[i] != 'd':
            i += 1
        if i >= len(obj.damage):
            return -1
        i += 1  # 'd'をスキップ

        damage = self._get_number(obj.damage[i:]) + obj.d_enchant

        new_damage = f"{to_hit}d{damage}"
        return self._get_damage(new_damage, True)

    def _get_number(self, s: str) -> int:
        """文字列から数値を取得"""
        total = 0
        for ch in s:
            if '0' <= ch <= '9':
                total = total * 10 + (ord(ch) - ord('0'))
            else:
                break
        return total

    def _to_hit(self, obj: Optional[Item]) -> int:
        """命中値を計算"""
        if obj is None:
            return 1
        return self._get_number(obj.damage) + obj.hit_enchant

    def _damage_for_strength(self) -> int:
        """筋力によるダメージボーナスを計算"""
        strength = self.player.str_current + GameState.add_strength
        if strength <= 6:
            return strength - 5

        sa = [14, 17, 18, 20, 21, 30, 9999]
        ra = [1, 3, 4, 5, 6, 7, 8]

        for i in range(len(sa)):
            if strength <= sa[i]:
                return ra[i]

        return 8

    def _mon_damage(self, monster: Monster, damage: int) -> int:
        """モンスターにダメージを与える"""

        row = monster.row
        col = monster.col

        monster.hp_to_kill -= damage

        if monster.hp_to_kill <= 0:
            self.dungeon.dungeon[row][col] &= ~const.MONSTER

            # モンスターの位置を地形文字に戻す (C版: mvaddch_rogue + get_dungeon_char)
            if getattr(self, 'display', None):
                ch = self.display.get_dungeon_char(self.dungeon, row, col)
                self.display.mvaddch(row, col, ord(ch) if isinstance(ch, str) else ch)

            GameState.fight_monster = None
            self._cough_up(monster)

            mn = self._mon_name(monster)
            if getattr(self, 'msg', None):
                self.msg.message(f"{mn}を倒した！", 1)

            # 経験値を追加 (C版: add_exp(monster->kill_exp, 1))
            new_levels = self.player.add_exp(monster.kill_exp, promotion=True)
            for lv in new_levels:
                if getattr(self, 'msg', None):
                    
                    self.msg.message(get_message(53) % lv, 0)

            # モンスターを削除（両方のリストから削除）
            if monster in self.dungeon.monsters:
                self.dungeon.monsters.remove(monster)
            
            # level_monsters連結リストからも削除（ゴーストフラグ問題の修正）
            self._remove_from_level_monsters(monster)

            if monster.m_flags & const.HOLDS:
                GameState.being_held = False

            return 0

        return 1

    def fight(self, to_the_death: bool = False) -> None:
        """戦闘 (C版 hit.c: fight)

        C版では one_move_rogue(ch, 0) をループ内で呼び reg_move 等の
        副作用を含む。Python版では rogue_hit + mon_hit + reg_move で再現。
        """

        ch = self._get_direction()
        if ch == const.CANCEL:
            return

        row, col = self.player.row, self.player.col
        # 文字→方向定数に変換 (C版 get_directionは定数を返す)
        char_to_dir = {'h': const.LEFT, 'j': const.DOWN, 'k': const.UPWARD,
                       'l': const.RIGHT, 'y': const.LEFTUP, 'u': const.UPRIGHT,
                       'b': const.DOWNLEFT, 'n': const.RIGHTDOWN}
        dirch = char_to_dir.get(ch, ch)
        row, col = self._get_dir_rc(dirch, row, col, False)

        monster = self._monster_at(row, col)
        if monster is None:
            return

        GameState.fight_monster = monster

        if not (monster.m_flags & const.STATIONARY):
            possible_damage = (self._get_damage(monster.m_damage, False) * 2) // 3
        else:
            possible_damage = monster.stationary_damage - 1

        while GameState.fight_monster:
            if not to_the_death and self.player.hp_current <= possible_damage:
                GameState.fight_monster = None
                break
            if GameState.interrupted or not (self.dungeon.dungeon[row][col] & const.MONSTER):
                GameState.fight_monster = None
                break

            m = self._monster_at(row, col)
            if m != GameState.fight_monster:
                GameState.fight_monster = None
                break

            self.rogue_hit(GameState.fight_monster, False)
            if GameState.fight_monster:
                self.mon_hit(GameState.fight_monster)
                # C版 one_move_rogue 経由で reg_move が呼ばれるのを再現
                from actions import Movement
                movement = Movement(self.player, self.dungeon)
                movement.reg_move()

    def _get_dir_rc(self, dirch: int, row: int, col: int, allow_off_screen: bool) -> Tuple[int, int]:
        """方向から座標変化を取得
        
        Args:
            dirch: 方向定数（const.UPWARD, const.DOWN など）
            row: 現在の行
            col: 現在の列
            allow_off_screen: 画面外への移動を許可するか
        """
        dr, dc = get_direction_offset(dirch)

        if not allow_off_screen:
            if dr < 0 and row <= const.MIN_ROW:
                return row, col
            if dr > 0 and row >= (const.ROGUE_LINES - 2):
                return row, col
            if dc < 0 and col <= 0:
                return row, col
            if dc > 0 and col >= (const.ROGUE_COLUMNS - 1):
                return row, col

        return row + dr, col + dc

    def _get_hit_chance(self, weapon: Optional[Item]) -> int:
        """命中確率を計算"""
        hit_chance = 40 + 3 * self._to_hit(weapon)
        hit_chance += ((2 * self.player.exp) + (2 * GameState.ring_exp)) - GameState.r_rings
        return hit_chance

    def _get_weapon_damage(self, weapon: Optional[Item]) -> int:
        """武器ダメージを計算"""
        damage = self._get_w_damage(weapon) + self._damage_for_strength()
        damage += ((self.player.exp + GameState.ring_exp) - GameState.r_rings + 1) // 2
        return damage

    def _get_armor_class(self, armor: Optional[Item]) -> int:
        """防具クラスを計算 (C版 object.c: get_armor_class)"""
        # C: return(obj ? obj->class + obj->d_enchant : 0);
        if armor is None:
            return 0
        return armor.class_ + armor.d_enchant

    def _mon_name(self, monster: Monster) -> str:
        """モンスター名を取得 (C版 monster.c: mon_name)"""
        if GameState.blind or ((monster.m_flags & const.INVISIBLE) and
                               not (GameState.detect_monster or GameState.see_invisible or GameState.r_see_invisible)):
            return "何者か"

        if GameState.halluc:
            ch = utils.get_rand(ord('A'), ord('Z')) - ord('A')
            return M_NAMES[ch]

        ch = monster.ichar - ord('A')
        if 0 <= ch < len(M_NAMES):
            return M_NAMES[ch]
        return f"モンスター({monster.monster_type})"

    def _check_imitator(self, monster: Monster) -> bool:
        """イミテーターかチェック (C版 spechit.c:355-371)"""
        if monster.m_flags & const.IMITATES:
            self._wake_up(monster)
            if not GameState.blind:
                if getattr(self, 'display', None):
                    ch = self.display.get_dungeon_char(self.dungeon, monster.row, monster.col)
                    self.display.mvaddch(monster.row, monster.col, ord(ch) if isinstance(ch, str) else ch)
                    self.display.refresh()
                mn = self._mon_name(monster)
                if getattr(self, 'msg', None):
                    self.msg.message(f"{mn}の正体があらわれた！", 1)
            return True
        return False

    def _special_hit(self, monster: Monster) -> None:
        """
        特殊攻撃 (C版 spechit.c:45-73)
        
        モンスターの特殊攻撃フラグに応じた効果を発動する。
        """
        # 混乱中は66%の確率で特殊攻撃を失敗
        if (monster.m_flags & const.CONFUSED) and utils.rand_percent(66):
            return
        
        # 錆攻撃
        if monster.m_flags & const.RUSTS:
            self._rust(monster)
        
        # 拘束攻撃（浮遊中は無効）
        if (monster.m_flags & const.HOLDS) and not GameState.levitate:
            GameState.being_held = True
        
        # 凍結攻撃
        if monster.m_flags & const.FREEZES:
            self._freeze(monster)
        
        # 刺攻撃
        if monster.m_flags & const.STINGS:
            self._sting(monster)
        
        # 生命力吸収
        if monster.m_flags & const.DRAINS_LIFE:
            self._drain_life()
        
        # レベル低下
        if monster.m_flags & const.DROPS_LEVEL:
            self._drop_level()
        
        # 金貨盗難
        if monster.m_flags & const.STEALS_GOLD:
            self._steal_gold(monster)
        elif monster.m_flags & const.STEALS_ITEM:
            self._steal_item(monster)

    def _rust(self, monster: Monster) -> None:
        """
        錆攻撃 (C版 spechit.c:76-92)
        
        プレイヤーの防具を錆びさせる。
        """
        # 防具がない、ACが1以下、または革防具の場合は効果なし
        if (self.player.armor is None or
            self._get_armor_class(self.player.armor) <= 1 or
            self.player.armor.which_kind == const.LEATHER):
            return
        
        # 保護されている場合
        if self.player.armor.is_protected or GameState.maintain_armor:
            if monster and not (monster.m_flags & const.RUST_VANISHED):
                if getattr(self, 'msg', None):
                    
                    self.msg.message(get_message(201), 0)  # "防具は錆びなかった。"
                monster.m_flags |= const.RUST_VANISHED
        else:
            self.player.armor.d_enchant -= 1
            if getattr(self, 'msg', None):
                
                self.msg.message(get_message(202), 0)  # "防具が錆びた！"
            if getattr(self, 'game', None):
                self.game._print_stats(const.STAT_ARMOR)

    def _freeze(self, monster: Monster) -> None:
        """
        凍結攻撃 (C版 spechit.c:94-124)
        
        プレイヤーを凍結させ、体温を下げる。
        """
        # 12%の確率で回避
        if utils.rand_percent(12):
            return
        
        # 凍結確率を計算
        freeze_percent = 99
        freeze_percent -= (self.player.str_current + (self.player.str_current // 2))
        freeze_percent -= ((self.player.exp + GameState.ring_exp) * 4)
        freeze_percent -= (self._get_armor_class(self.player.armor) * 5)
        freeze_percent -= (self.player.hp_max // 3)
        
        if freeze_percent > 10:
            monster.m_flags |= const.FREEZING_ROGUE
            # message(mesg[203], 1)  # "体が凍りついた！"
            # C版はmv_mons()（MonsterAI側）。Combat自体にmv_monsはないため委譲
            _mai = MonsterAI(self.player, self.dungeon)
            for attr in ("display", "msg", "game"):
                if hasattr(self, attr):
                    try:
                        setattr(_mai, attr, getattr(self, attr))
                    except Exception:
                        pass
            n = utils.get_rand(4, 8)
            for _ in range(n):
                _mai.mv_mons()

            if utils.rand_percent(freeze_percent):
                for _ in range(50):
                    _mai.mv_mons()
                self._rogue_damage(self.player.hp_current, None)
                return
            
            # message(you_can_move_again, 1)
            monster.m_flags &= ~const.FREEZING_ROGUE

    def _steal_gold(self, monster: Monster) -> None:
        """
        金貨盗難 (C版 spechit.c:126-144)
        
        プレイヤーから金貨を盗む。
        """
        # 金貨がない、または10%の確率で回避
        if self.player.gold <= 0 or utils.rand_percent(10):
            return
        
        # 盗む金額を計算
        amount = utils.get_rand(self.cur_level * 10, self.cur_level * 30)
        if amount > self.player.gold:
            amount = self.player.gold
        
        self.player.gold -= amount
        if getattr(self, 'msg', None):
            
            self.msg.message(get_message(204), 0)  # "金貨を盗まれた！"
        if getattr(self, 'game', None):
            self.game._print_stats(const.STAT_GOLD)
        
        # モンスターを消失させる
        self._disappear(monster)

    def _steal_item(self, monster: Monster) -> None:
        """アイテム盗難 (C版 spechit.c:146-220)"""
        if utils.rand_percent(15):
            return

        obj = self.player.pack
        if obj is None:
            self._disappear(monster)
            return

        # 非ORIGINAL: 装備中の呪いなし飾り指輪を優先盗難
        curr = obj
        while curr:
            if (curr.what_is == const.RING and
                    curr.which_kind == const.ADORNMENT and
                    curr.in_use_flags & const.ON_EITHER_HAND and
                    not curr.is_cursed):
                if getattr(self, 'inv_manager', None):
                    self.inv_manager.un_put_on(curr)
                # adornment ラベルへ飛ぶ
                self._steal_item_vanish(curr)
                self._disappear(monster)
                return
            curr = curr.next_object

        # 装備していないアイテムがあるかチェック
        has_something = False
        curr = self.player.pack
        while curr:
            if not (curr.in_use_flags & const.BEING_USED):
                has_something = True
                break
            curr = curr.next_object

        if not has_something:
            self._disappear(monster)
            return

        # ランダムにアイテムを選択
        n = utils.get_rand(0, const.MAX_PACK_COUNT)
        curr = self.player.pack

        for i in range(n + 1):
            curr = curr.next_object
            while curr is None or (curr.in_use_flags & const.BEING_USED):
                if curr is None:
                    curr = self.player.pack
                else:
                    curr = curr.next_object

        self._steal_item_vanish(curr)
        self._disappear(monster)

    def _steal_item_vanish(self, obj: Item) -> None:
        """盗まれたアイテムを消去 (C版 spechit.c + use.c: vanish)"""
        

        # 武器以外はquantityを一時的に1にして描述
        if obj.what_is != const.WEAPON:
            t = obj.quantity
            obj.quantity = 1

        # アイテム名+盗難メッセージ (C版: get_desc + mesg[205])
        if getattr(self, 'msg', None):
            desc = self._get_obj_desc(obj)
            self.msg.message(desc + get_message(205), 0)

        # quantityを復元
        if obj.what_is != const.WEAPON:
            obj.quantity = t

        # vanish(obj, 0, &rogue.pack)
        self._vanish_item(obj, False)

    def _vanish_item(self, obj: Item, rm: bool) -> None:
        """アイテムを消失させる (C版 use.c: vanish)"""
        if obj.quantity > 1:
            obj.quantity -= 1
        else:
            inv = getattr(self, 'inv_manager', None)
            if obj.in_use_flags & const.BEING_WIELDED:
                if inv:
                    inv.unwield(obj)
            elif obj.in_use_flags & const.BEING_WORN:
                if inv:
                    inv.unwear(obj)
            elif obj.in_use_flags & const.ON_EITHER_HAND:
                if inv:
                    inv.un_put_on(obj)
            if inv:
                inv.take_from_pack(obj)
        if rm:
            if getattr(self, 'game', None):
                self.game.reg_move()

    def _get_obj_desc(self, obj: Item) -> str:
        """アイテムの簡易説明"""
        type_names = {
            const.FOOD: "食料", const.WEAPON: "武器", const.ARMOR: "防具",
            const.POTION: "ポーション", const.SCROL: "巻物",
            const.WAND: "杖", const.RING: "指輪", const.AMULET: "アミュレット",
        }
        return type_names.get(obj.what_is, "何か")

    def _disappear(self, monster: Monster) -> None:
        """モンスターが消える (C版 spechit.c: disappear)"""

        row = monster.row
        col = monster.col
        
        self.dungeon.dungeon[row][col] &= ~const.MONSTER
        # if rogue_can_see(row, col):
        #     mvaddch_rogue(row, col, get_dungeon_char(row, col))
        
        # モンスターをリストから削除（両方のリストから削除）
        if monster in self.dungeon.monsters:
            self.dungeon.monsters.remove(monster)
        
        # level_monsters連結リストからも削除（ゴーストフラグ問題の修正）
        self._remove_from_level_monsters(monster)
        
        GameState.mon_disappeared = True

    def _remove_from_level_monsters(self, monster: Monster) -> None:
        """
        level_monsters連結リストからモンスターを削除
        
        C言語版では単一の連結リストで管理されているが、
        Python版では2つのリスト（monstersリストとlevel_monsters連結リスト）が
        存在するため、両方から削除する必要がある。
        """
        if self.dungeon.level_monsters is None:
            return
        
        # 先頭要素の場合
        if self.dungeon.level_monsters == monster:
            self.dungeon.level_monsters = monster.next_object
            return
        
        # 連結リストを走査して削除
        prev = self.dungeon.level_monsters
        curr = prev.next_object
        while curr:
            if curr == monster:
                prev.next_object = curr.next_object
                return
            prev = curr
            curr = curr.next_object

    def _sting(self, monster: Monster) -> None:
        """
        刺攻撃 (C版 spechit.c:388-408)
        
        プレイヤーの筋力を低下させる。
        """
        sting_chance = 35
        
        # 筋力が3以下、または維持の指輪がある場合は無効
        if self.player.str_current <= 3 or GameState.sustain_strength:
            return
        
        # 確率を計算
        sting_chance += (6 * (6 - self._get_armor_class(self.player.armor)))
        
        if (self.player.exp + GameState.ring_exp) > 8:
            sting_chance -= (6 * ((self.player.exp + GameState.ring_exp) - 8))
        
        if utils.rand_percent(sting_chance):
            # message(f"{mon_name(monster)}に刺された！", 0)
            self.player.str_current -= 1
            if getattr(self, 'game', None):
                self.game._print_stats(const.STAT_STRENGTH)

    def _drain_life(self) -> None:
        """
        生命力吸収 (C版 spechit.c:430-457)
        
        プレイヤーのHPまたは筋力を低下させる。
        """
        # 60%の確率で回避、または条件を満たさない
        if utils.rand_percent(60) or self.player.hp_max <= 30 or self.player.hp_current < 10:
            return
        
        # 1: HP低下、2: 筋力低下、3: 両方
        n = utils.get_rand(1, 3)
        
        # if n != 2 or not sustain_strength:
        #     message(mesg[208], 0)  # "生命力を吸い取られた！"
        
        if n != 2:
            self.player.hp_max -= 1
            self.player.hp_current -= 1
            # less_hp += 1
        
        if n != 1:
            if self.player.str_current > 3 and not GameState.sustain_strength:
                self.player.str_current -= 1
                if utils.coin_toss():
                    self.player.str_max -= 1
        
        # print_stats(STAT_STRENGTH | STAT_HP)
        if getattr(self, 'game', None):
            self.game._print_stats(const.STAT_STRENGTH | const.STAT_HP)

    def _drop_level(self) -> None:
        """レベル低下 (C版 spechit.c:410-428)"""
        if utils.rand_percent(80) or self.player.exp <= 5:
            return
        
        # C版: exp_points = level_points[exp-2] - get_rand(9, 29)
        if self.player.exp >= 2:
            self.player.exp_points = Player.LEVEL_POINTS[self.player.exp - 2] - utils.get_rand(9, 29)
        else:
            self.player.exp_points = 0
        
        self.player.exp -= 2
        
        # HP減少 (C版: hp_raise()の値を減算)
        hp = 10 if GameState.wizard else utils.get_rand(3, 10)
        
        self.player.hp_current -= hp
        if self.player.hp_current <= 0:
            self.player.hp_current = 1
        
        self.player.hp_max -= hp
        if self.player.hp_max <= 0:
            self.player.hp_max = 1
        
        # C版: add_exp(1, 0) — レベル再計算 promotionなし
        new_levels = self.player.add_exp(1, False)
        for lv in new_levels:
            if getattr(self, 'msg', None):
                
                self.msg.message(get_message(53) % lv, 0)

    def _check_gold_seeker(self, monster: Monster) -> None:
        """金を探すモンスターかチェック"""
        monster.m_flags &= ~const.SEEKS_GOLD

    def _wake_up(self, monster: Monster) -> None:
        """モンスターを起こす (C版 monster.c: wake_up)"""
        # C: if (!(monster->m_flags & NAPPING)) monster->m_flags &= ~(ASLEEP|IMITATES|WAKENS);
        if not (monster.m_flags & const.NAPPING):
            monster.m_flags &= ~(const.ASLEEP | const.IMITATES | const.WAKENS)

    def _cough_up(self, monster: Monster) -> None:
        """モンスターがアイテムを吐き出す (C版 spechit.c: cough_up)"""
        # C: if (cur_level < max_level) return;
        if GameState.cur_level < GameState.max_level:
            return
        obj = Item()
        if monster.m_flags & const.STEALS_GOLD:
            # C: GOLD qty = cur_level*15-30
            obj.item_type = const.GOLD
            obj.which_kind = 0
            obj.quantity = max(1, GameState.cur_level * 15 - 30)
        else:
            if not (monster.drop_percent > 0 and utils.rand_percent(monster.drop_percent)):
                return
            # C: obj = gr_object() 相当の簡易生成（種別ランダム）
            obj.item_type = utils.get_rand(const.GOLD, const.RING)
            obj.which_kind = 0
            obj.quantity = 1
        # C: try_to_cough 螺旋配置 (n=0..5)。占有・階段・罠を避け TUNNEL/FLOOR/DOOR要求
        for n in range(6):
            for dr in range(-n, n + 1):
                for dc in range(-n, n + 1):
                    if max(abs(dr), abs(dc)) != n:
                        continue
                    r, c = monster.row + dr, monster.col + dc
                    if not (0 <= r < const.ROGUE_LINES and 0 <= c < const.ROGUE_COLUMNS):
                        continue
                    tile = self.dungeon.dungeon[r][c]
                    if tile & (const.OBJECT | const.STAIRS | const.TRAP):
                        continue
                    if not (tile & (const.TUNNEL | const.FLOOR | const.DOOR)):
                        continue
                    obj.row, obj.col = r, c
                    obj.next_object = self.dungeon.level_objects
                    self.dungeon.level_objects = obj
                    self.dungeon.dungeon[r][c] |= const.OBJECT
                    return
        # 全失敗は破棄 (C: free_object)

    def _get_direction(self) -> str:
        """方向を取得 (C版 message.c: get_direction相当)"""
        game = getattr(self, 'game', None)
        if game is not None and hasattr(game, '_get_direction_input'):
            try:
                dirch = game._get_direction_input("どちらに？")
                if dirch:
                    return dirch
            except Exception:
                pass
        return const.CANCEL

    def _monster_at(self, row: int, col: int) -> Optional[Monster]:
        """指定位置のモンスターを取得"""
        for monster in self.dungeon.monsters:
            if monster.row == row and monster.col == col:
                return monster
        return None


class MonsterAI:
    """モンスターAIクラス"""

    @property
    def cur_level(self): return GameState.cur_level
    @cur_level.setter
    def cur_level(self, v): GameState.cur_level = v

    @property
    def cur_room(self): return GameState.cur_room
    @cur_room.setter
    def cur_room(self, v): GameState.cur_room = v

    @property
    def blind(self): return GameState.blind
    @blind.setter
    def blind(self, v): GameState.blind = v

    @property
    def halluc(self): return GameState.halluc
    @halluc.setter
    def halluc(self, v): GameState.halluc = v

    @property
    def haste_self(self): return GameState.haste_self
    @haste_self.setter
    def haste_self(self, v): GameState.haste_self = v

    @property
    def detect_monster(self): return GameState.detect_monster
    @detect_monster.setter
    def detect_monster(self, v): GameState.detect_monster = v

    @property
    def see_invisible(self): return GameState.see_invisible
    @see_invisible.setter
    def see_invisible(self, v): GameState.see_invisible = v

    @property
    def r_see_invisible(self): return GameState.r_see_invisible
    @r_see_invisible.setter
    def r_see_invisible(self, v): GameState.r_see_invisible = v

    @property
    def stealthy(self): return GameState.stealthy
    @stealthy.setter
    def stealthy(self, v): GameState.stealthy = v

    def __init__(self, player: Player, dungeon: DungeonLevel):
        self.player = player
        self.dungeon = dungeon

    def put_mons(self) -> None:
        """モンスターを配置"""
        n = utils.get_rand(4, 6)

        for _ in range(n):
            monster = self.gr_monster(None, 0)
            if (monster.m_flags & const.WANDERS) and utils.coin_toss():
                self._wake_up(monster)
            row, col = self._gr_row_col(const.FLOOR | const.TUNNEL | const.STAIRS | const.OBJECT)
            self.put_m_at(row, col, monster)

    def gr_monster(self, monster: Optional[Monster], mn: int) -> Monster:
        """モンスターを生成"""
        if monster is None:
            monster = Monster()

            while True:
                mn = utils.get_rand(0, len(MON_TAB) - 1)
                # MON_TABは辞書形式: {"flags", "damage", "hp", "ichar", "exp", "first", "last", "hit", "drop"}
                if (self.cur_level >= MON_TAB[mn]["first"]) and (self.cur_level <= MON_TAB[mn]["last"]):
                    break

        # モンスターテーブルからコピー（辞書形式）
        data = MON_TAB[mn]
        monster.m_flags = data["flags"]
        monster.m_damage = data["damage"]
        monster.hp_to_kill = data["hp"]
        monster.ichar = ord(data["ichar"])  # C言語版と同様にord()で整数に変換
        monster.kill_exp = data["exp"]
        monster.hit_chance = data["hit"]
        monster.first_level = data["first"]
        monster.last_level = data["last"]
        monster.drop_percent = data["drop"]
        monster.name = M_NAMES[mn]  # モンスター名を設定

        if monster.m_flags & const.IMITATES:
            monster.disguise = ord(self._gr_obj_char())  # C言語版と同様にord()で整数に変換

        if self.cur_level > (const.AMULET_LEVEL + 2):
            monster.m_flags |= const.HASTED

        monster.trow = const.NO_ROOM
        return monster

    def mv_mons(self) -> None:
        """全モンスターを移動"""

        if self.haste_self % 2:
            return

        for monster in self.dungeon.monsters[:]:
            GameState.mon_disappeared = False

            if monster.m_flags & const.HASTED:
                self.mv_monster(monster, self.player.row, self.player.col)
                if GameState.mon_disappeared:
                    continue
            elif monster.m_flags & const.SLOWED:
                monster.slowed_toggle = not monster.slowed_toggle
                if monster.slowed_toggle:
                    continue

            if (monster.m_flags & const.CONFUSED) and self.move_confused(monster):
                continue

            flew = False
            if (monster.m_flags & const.FLIES) and not (monster.m_flags & const.NAPPING):
                if not self._mon_can_go(monster, self.player.row, self.player.col):
                    flew = True
                    self.mv_monster(monster, self.player.row, self.player.col)

            if not (flew and self._mon_can_go(monster, self.player.row, self.player.col)):
                self.mv_monster(monster, self.player.row, self.player.col)

    def party_monsters(self, rn: int, n: int) -> None:
        """パーティーモンスターを配置
        
        C言語版ではmon_tab[i].first_levelを一時的に変更しているが、
        Python版ではMON_TABを変更せず、生成時のレベル判定を調整する
        """
        rooms = self.dungeon.rooms

        n += n

        # 一時的にcur_levelを調整（MON_TABを変更しない）
        original_cur_level = self.cur_level
        self.cur_level = max(1, self.cur_level - (self.cur_level % 3))

        for _ in range(n):
            if self._no_room_for_monster(rn):
                break

            found = False
            for _ in range(250):
                row = utils.get_rand(rooms[rn].top_row + 1, rooms[rn].bottom_row - 1)
                col = utils.get_rand(rooms[rn].left_col + 1, rooms[rn].right_col - 1)
                if not (self.dungeon.dungeon[row][col] & const.MONSTER):
                    if self.dungeon.dungeon[row][col] & (const.FLOOR | const.TUNNEL):
                        found = True
                        break

            if found:
                monster = self.gr_monster(None, 0)
                if not (monster.m_flags & const.IMITATES):
                    monster.m_flags |= const.WAKENS
                self.put_m_at(row, col, monster)

        # cur_levelを元に戻す
        self.cur_level = original_cur_level

    def gmc_row_col(self, row: int, col: int) -> str:
        """指定位置のモンスター文字を取得"""
        monster = self._monster_at(row, col)
        if monster:
            return self.gmc(monster)
        return '&'

    def gmc(self, monster: Monster) -> str:
        """モンスターの表示文字を取得"""
        if (not (self.detect_monster or self.see_invisible or self.r_see_invisible) and
                (monster.m_flags & const.INVISIBLE)) or self.blind:
            return monster.trail_char
        if monster.m_flags & const.IMITATES:
            return chr(monster.disguise)  # 整数を文字に変換
        return chr(monster.ichar)  # 整数を文字に変換

    def mv_monster(self, monster: Monster, row: int, col: int) -> None:
        """モンスターを移動"""
        if monster.m_flags & const.ASLEEP:
            if monster.m_flags & const.NAPPING:
                monster.nap_length -= 1
                if monster.nap_length <= 0:
                    monster.m_flags &= ~(const.NAPPING | const.ASLEEP)
                return

            if (monster.m_flags & const.WAKENS) and self._rogue_is_around(monster.row, monster.col):
                wake_percent = const.WAKE_PERCENT
                if self.stealthy > 0:
                    wake_percent //= (const.STEALTH_FACTOR + self.stealthy)
                if utils.rand_percent(wake_percent):
                    self._wake_up(monster)
            return

        elif monster.m_flags & const.ALREADY_MOVED:
            monster.m_flags &= ~const.ALREADY_MOVED
            return

        if (monster.m_flags & const.FLITS) and self._flit(monster):
            return

        if (monster.m_flags & const.STATIONARY) and not self._mon_can_go(monster, self.player.row, self.player.col):
            return

        if monster.m_flags & const.FREEZING_ROGUE:
            return

        if (monster.m_flags & const.CONFUSES) and self._m_confuse(monster):
            return

        if self._mon_can_go(monster, self.player.row, self.player.col):
            # C版 monster.c:262-264 隣接可なら攻撃してreturn
            # （Combat経由。MonsterAI自体にmon_hitはない）
            combat = Combat(self.player, self.dungeon)
            for attr in ("display", "msg", "game"):
                if hasattr(self, attr):
                    try:
                        setattr(combat, attr, getattr(self, attr))
                    except Exception:
                        pass
            combat.mon_hit(monster)
            return

        if (monster.m_flags & const.FLAMES) and self._flame_broil(monster):
            return

        if (monster.m_flags & const.SEEKS_GOLD) and self._seek_gold(monster):
            return

        if (monster.trow == monster.row) and (monster.tcol == monster.col):
            monster.trow = const.NO_ROOM
        elif monster.trow != const.NO_ROOM:
            row = monster.trow
            col = monster.tcol

        if monster.row > row:
            row = monster.row - 1
        elif monster.row < row:
            row = monster.row + 1

        if (self.dungeon.dungeon[row][monster.col] & const.DOOR) and self._mtry(monster, row, monster.col):
            return

        if monster.col > col:
            col = monster.col - 1
        elif monster.col < col:
            col = monster.col + 1

        if (self.dungeon.dungeon[monster.row][col] & const.DOOR) and self._mtry(monster, monster.row, col):
            return

        if self._mtry(monster, row, col):
            return

        # ランダムな方向を試す
        tried = [False] * 6
        for _ in range(6):
            while True:
                n = utils.get_rand(0, 5)
                if not tried[n]:
                    break

            if n == 0 and self._mtry(monster, row, monster.col - 1):
                break
            elif n == 1 and self._mtry(monster, row, monster.col):
                break
            elif n == 2 and self._mtry(monster, row, monster.col + 1):
                break
            elif n == 3 and self._mtry(monster, monster.row - 1, col):
                break
            elif n == 4 and self._mtry(monster, monster.row, col):
                break
            elif n == 5 and self._mtry(monster, monster.row + 1, col):
                break

            tried[n] = True

        # 停滞チェック
        if (monster.row == monster.o_row) and (monster.col == monster.o_col):
            monster.o += 1
            if monster.o > 4:
                if (monster.trow == const.NO_ROOM) and not self._mon_sees(monster, self.player.row, self.player.col):
                    monster.trow = utils.get_rand(1, const.ROGUE_LINES - 2)
                    monster.tcol = utils.get_rand(0, const.ROGUE_COLUMNS - 1)
                else:
                    monster.trow = const.NO_ROOM
                    monster.o = 0
        else:
            monster.o_row = monster.row
            monster.o_col = monster.col
            monster.o = 0

    def _mtry(self, monster: Monster, row: int, col: int) -> bool:
        """モンスターの移動を試みる"""
        if self._mon_can_go(monster, row, col):
            self._move_mon_to(monster, row, col)
            return True
        return False

    def _get_dungeon_char(self, row: int, col: int, ignore_monster: bool = False) -> str:
        """指定位置のダンジョン文字を取得 (C版 mvinch_rogue相当)"""
        tile = self.dungeon.get_tile(row, col)

        # trail_char取得時はMONSTERビットを無視する（素の地形文字。
        # さもないと怪物文字が残像として残る）
        if tile & const.MONSTER and not ignore_monster:
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

    def _move_mon_to(self, monster: Monster, row: int, col: int) -> None:
        """モンスターを指定位置に移動 (C版 monster.c: move_mon_to)"""
        # C版 monster.c:411-416 ドアマスへの移動はdr_course経由（trow/tcol管理）
        if self.dungeon.dungeon[row][col] & const.DOOR:
            if getattr(self, 'display', None):
                try:
                    rn = self.dungeon.get_room_number(row, col)
                    entering = (rn == GameState.cur_room)
                    self.display.dr_course(monster, entering, row, col, self.dungeon)
                except Exception:
                    pass
        mrow = monster.row
        mcol = monster.col

        self.dungeon.dungeon[mrow][mcol] &= ~const.MONSTER
        self.dungeon.dungeon[row][col] |= const.MONSTER

        # C版: c = mvinch_rogue(mrow, mcol); if ((c >= 'A') && (c <= 'Z'))
        # 画面上の古い位置の文字がモンスター文字(A-Z)の場合のみ消去処理を行う
        # 見えない位置のモンスターは画面に描かれていないので消去不要
        if getattr(self, 'display', None):
            c = self.display.mvinch(mrow, mcol)
            if c >= ord('A') and c <= ord('Z'):
                if not self.detect_monster:
                    tc = monster.trail_char
                    self.display.mvaddch(mrow, mcol, ord(tc) if isinstance(tc, str) else tc)
                else:
                    if self._rogue_can_see(mrow, mcol):
                        tc = monster.trail_char
                        self.display.mvaddch(mrow, mcol, ord(tc) if isinstance(tc, str) else tc)
                    else:
                        if monster.trail_char == '.':
                            monster.trail_char = ' '
                        tc = monster.trail_char
                        self.display.mvaddch(mrow, mcol, ord(tc) if isinstance(tc, str) else tc)

        # C版: monster->trail_char = mvinch_rogue(row, col);
        # mvinchは配置前の画面を読むためMONSTERビットを無視する
        monster.trail_char = self._get_dungeon_char(row, col, ignore_monster=True)

        # C版: if (!blind && (detect_monster || rogue_can_see(row, col)))
        if not GameState.blind and (self.detect_monster or self._rogue_can_see(row, col)):
            if not (monster.m_flags & const.INVISIBLE) or self.detect_monster or GameState.see_invisible or GameState.r_see_invisible:
                if getattr(self, 'display', None):
                    mc = self.gmc(monster)
                    self.display.mvaddch(row, col, ord(mc) if isinstance(mc, str) else mc)

        # C版 monster.c:406-410 ドア条件の追加消去 (==FLOOR厳密一致)
        if (self.dungeon.dungeon[row][col] & const.DOOR and
                self.dungeon.get_room_number(row, col) != GameState.cur_room and
                self.dungeon.dungeon[mrow][mcol] == const.FLOOR and
                not GameState.blind):
            if getattr(self, 'display', None):
                self.display.mvaddch(mrow, mcol, ord(' '))

        monster.row = row
        monster.col = col

    def _mon_can_go(self, monster: Monster, row: int, col: int) -> bool:
        """モンスターが移動できるかチェック"""
        dr = monster.row - row
        dc = monster.col - col

        if dr >= 2 or dr <= -2 or dc >= 2 or dc <= -2:
            return False

        if not self.dungeon.dungeon[monster.row][col] or not self.dungeon.dungeon[row][monster.col]:
            return False

        if not const.is_passable(self.dungeon.dungeon[row][col]) or (self.dungeon.dungeon[row][col] & const.MONSTER):
            return False

        if (monster.row != row) and (monster.col != col):
            if (self.dungeon.dungeon[row][col] & const.DOOR) or (self.dungeon.dungeon[monster.row][monster.col] & const.DOOR):
                return False

        if not (monster.m_flags & (const.FLITS | const.CONFUSED | const.CAN_FLIT)) and monster.trow == const.NO_ROOM:
            if ((monster.row < self.player.row and row < monster.row) or
                (monster.row > self.player.row and row > monster.row) or
                (monster.col < self.player.col and col < monster.col) or
                (monster.col > self.player.col and col > monster.col)):
                return False

        if self.dungeon.dungeon[row][col] & const.OBJECT:
            # C版 monster.c:447-452 SCARE_MONSTER巻物上へは侵入不可
            obj = self._object_at(row, col)
            if obj is not None and obj.item_type == const.SCROL and obj.which_kind == const.SCARE_MONSTER:
                return False

        return True

    def _wake_up(self, monster: Monster) -> None:
        """モンスターを起こす"""
        if not (monster.m_flags & const.NAPPING):
            monster.m_flags &= ~(const.ASLEEP | const.IMITATES | const.WAKENS)

    def wake_room(self, rn: int, entering: bool, row: int, col: int) -> None:
        """部屋のモンスターを起こす (C版 monster.c: wake_room)"""
        # C: wake_percent = (rn == party_room) ? PARTY_WAKE_PERCENT(75) : WAKE_PERCENT(45)
        wake_percent = const.PARTY_WAKE_PERCENT if rn == GameState.party_room else const.WAKE_PERCENT
        if self.stealthy > 0:
            wake_percent //= (const.STEALTH_FACTOR + self.stealthy)

        for monster in self.dungeon.monsters:
            in_room = (rn == get_room_number(self.dungeon, monster.row, monster.col))

            if in_room:
                if entering:
                    monster.trow = const.NO_ROOM
                else:
                    monster.trow = row
                    monster.tcol = col

            if (monster.m_flags & const.WAKENS) and in_room:
                if utils.rand_percent(wake_percent):
                    self._wake_up(monster)

    def mon_name(self, monster: Monster) -> str:
        """モンスター名を取得"""
        if self.blind or ((monster.m_flags & const.INVISIBLE) and
                          not (self.detect_monster or self.see_invisible or self.r_see_invisible)):
            return "何か"

        if self.halluc:
            ch = utils.get_rand(ord('A'), ord('Z')) - ord('A')
            return M_NAMES[ch]

        ch = monster.ichar - ord('A')  # icharは既に整数
        return M_NAMES[ch]

    def _mon_name(self, monster: Monster) -> str:
        """モンスター名を取得（Combat._mon_nameとの互換エイリアス）"""
        return self.mon_name(monster)

    def _rogue_is_around(self, row: int, col: int) -> bool:
        """プレイヤーが近くにいるかチェック"""
        rdif = row - self.player.row
        cdif = col - self.player.col
        return (rdif >= -1) and (rdif <= 1) and (cdif >= -1) and (cdif <= 1)

    def wanderer(self) -> None:
        """放浪モンスターを生成"""
        monster = None
        found = False

        for _ in range(15):
            monster = self.gr_monster(None, 0)
            if not (monster.m_flags & (const.WAKENS | const.WANDERS)):
                continue
            found = True
            break

        if found:
            self._wake_up(monster)
            found = False

            for _ in range(25):
                row, col = self._gr_row_col(const.FLOOR | const.TUNNEL | const.STAIRS | const.OBJECT)
                if not self._rogue_can_see(row, col):
                    self.put_m_at(row, col, monster)
                    found = True
                    break

    def show_monsters(self) -> None:
        """モンスターを表示"""
        self.detect_monster = True

        if self.blind:
            return

        for monster in self.dungeon.monsters:
            if monster.m_flags & const.IMITATES:
                monster.m_flags &= ~const.IMITATES
                monster.m_flags |= const.WAKENS

    def create_monster(self) -> None:
        """モンスターを作成"""
        r = self.player.row
        c = self.player.col

        for i in range(9):
            r, c = self._rand_around(i, r, c)
            row, col = r, c

            if ((row == self.player.row and col == self.player.col) or
                row < const.MIN_ROW or row > (const.ROGUE_LINES - 2) or
                col < 0 or col > (const.ROGUE_COLUMNS - 1)):
                continue

            if (not (self.dungeon.dungeon[row][col] & const.MONSTER) and
                (self.dungeon.dungeon[row][col] & (const.FLOOR | const.TUNNEL | const.STAIRS | const.DOOR))):
                monster = self.gr_monster(None, 0)
                self.put_m_at(row, col, monster)

                if monster.m_flags & (const.WANDERS | const.WAKENS):
                    self._wake_up(monster)
                return

    def put_m_at(self, row: int, col: int, monster: Monster) -> None:
        """モンスターを配置"""
        monster.row = row
        monster.col = col
        self.dungeon.dungeon[row][col] |= const.MONSTER
        # C版: monster->trail_char = mvinch_rogue(row, col);
        # 配置後のためMONSTERビットを無視して素の地形文字を取る
        monster.trail_char = self._get_dungeon_char(row, col, ignore_monster=True)
        # 両方のリストに追加（C言語版互換）
        self.dungeon.monsters.append(monster)
        # level_monsters連結リストの先頭に追加
        monster.next_object = self.dungeon.level_monsters
        self.dungeon.level_monsters = monster
        self._aim_monster(monster)

    def _aim_monster(self, monster: Monster) -> None:
        """モンスターのターゲットを設定"""
        rn = get_room_number(self.dungeon, monster.row, monster.col)

        if rn < 0 or rn >= len(self.dungeon.rooms):
            return

        r = utils.get_rand(0, 12)

        for i in range(4):
            d = (r + i) % 4
            if self.dungeon.rooms[rn].doors[d].oth_room != const.NO_ROOM:
                monster.trow = self.dungeon.rooms[rn].doors[d].door_row
                monster.tcol = self.dungeon.rooms[rn].doors[d].door_col
                break

    def _rogue_can_see(self, row: int, col: int) -> bool:
        """プレイヤーが見えるかチェック"""
        return (not self.blind and
                ((get_room_number(self.dungeon, row, col) == self.cur_room and
                  not (self.dungeon.rooms[self.cur_room].is_room & const.R_MAZE)) or
                 self._rogue_is_around(row, col)))

    def move_confused(self, monster: Monster) -> bool:
        """混乱状態で移動"""
        if not (monster.m_flags & const.ASLEEP):
            monster.moves_confused -= 1
            if monster.moves_confused <= 0:
                monster.m_flags &= ~const.CONFUSED

            if monster.m_flags & const.STATIONARY:
                return utils.coin_toss()
            elif utils.rand_percent(15):
                return True

            row = monster.row
            col = monster.col

            for i in range(9):
                row, col = self._rand_around(i, row, col)
                if row == self.player.row and col == self.player.col:
                    return False
                if self._mtry(monster, row, col):
                    return True

        return False

    def _flit(self, monster: Monster) -> bool:
        """フリット移動"""
        if not utils.rand_percent(const.FLIT_PERCENT):
            return False

        if utils.rand_percent(10):
            return True

        row = monster.row
        col = monster.col

        for i in range(9):
            row, col = self._rand_around(i, row, col)
            if row == self.player.row and col == self.player.col:
                continue
            if self._mtry(monster, row, col):
                return True

        return True

    def _gr_obj_char(self) -> str:
        """オブジェクト文字を生成"""
        chars = "%!?]=/):*"
        r = utils.get_rand(0, 8)
        return chars[r]

    def _no_room_for_monster(self, rn: int) -> bool:
        """部屋にモンスターを配置できるかチェック"""
        room = self.dungeon.rooms[rn]
        for i in range(room.top_row + 1, room.bottom_row):
            for j in range(room.left_col + 1, room.right_col):
                if not (self.dungeon.dungeon[i][j] & const.MONSTER):
                    return False
        return True

    def aggravate(self) -> None:
        """全モンスターを起こす"""
        for monster in self.dungeon.monsters:
            self._wake_up(monster)
            monster.m_flags &= ~const.IMITATES

    def _mon_sees(self, monster: Monster, row: int, col: int) -> bool:
        """モンスターが位置を見えるかチェック"""
        rn = get_room_number(self.dungeon, row, col)

        if (rn != const.NO_ROOM and
            rn == get_room_number(self.dungeon, monster.row, monster.col) and
            not (self.dungeon.rooms[rn].is_room & const.R_MAZE)):
            return True

        rdif = row - monster.row
        cdif = col - monster.col
        return (rdif >= -1) and (rdif <= 1) and (cdif >= -1) and (cdif <= 1)

    def mv_aquatars(self) -> None:
        """アクアターを移動"""
        for monster in self.dungeon.monsters:
            if chr(monster.ichar) == 'A' and self._mon_can_go(monster, self.player.row, self.player.col):
                self.mv_monster(monster, self.player.row, self.player.col)
                monster.m_flags |= const.ALREADY_MOVED

    def _gr_row_col(self, tile_types: int) -> Tuple[int, int]:
        """ランダムな行と列を取得 (C版 room.c: gr_row_col相当)"""
        while True:
            row = utils.get_rand(const.MIN_ROW, const.ROGUE_LINES - 2)
            col = utils.get_rand(0, const.ROGUE_COLUMNS - 1)
            tile = self.dungeon.dungeon[row][col]
            if not (tile & tile_types):
                continue
            # 自位置除外 (C版 room.c:191)
            if row == self.player.row and col == self.player.col:
                continue
            # 部屋・迷路マスのみ (C版 R_ROOM|R_MAZE相当の厳密化。
            # NO_ROOMは部屋番号であってタイルビットではない点に注意)
            try:
                rn = self.dungeon.get_room_number(row, col)
                if rn >= 0:
                    room = self.dungeon.rooms[rn]
                    if not (room.is_room & (const.R_ROOM | const.R_MAZE)):
                        continue
            except Exception:
                pass
            return row, col

    def _rand_around(self, i: int, row: int, col: int) -> Tuple[int, int]:
        """周囲のランダムな位置を取得"""
        offsets = [
            (0, 0), (-1, -1), (-1, 0), (-1, 1),
            (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)
        ]
        dr, dc = offsets[i]
        return row + dr, col + dc

    def _object_at(self, row: int, col: int) -> Optional[Item]:
        """指定位置のオブジェクトを取得"""
        obj = self.dungeon.level_objects
        while obj:
            if obj.row == row and obj.col == col:
                return obj
            obj = obj.next_object
        return None

    def _monster_at(self, row: int, col: int) -> Optional[Monster]:
        """指定位置のモンスターを取得"""
        for monster in self.dungeon.monsters:
            if monster.row == row and monster.col == col:
                return monster
        return None

    def _flame_broil(self, monster: Monster) -> bool:
        """
        炎攻撃 (C版 spechit.c:481-522)
        
        モンスターがプレイヤーに炎を吐く。
        """
        # プレイヤーが見えない、または50%の確率で回避
        if not self._mon_sees(monster, self.player.row, self.player.col) or utils.coin_toss():
            return False
        
        # 距離チェック
        row = self.player.row - monster.row
        col = self.player.col - monster.col
        
        if row < 0:
            row = -row
        if col < 0:
            col = -col
        
        # 斜め方向は距離が等しい場合のみ、最大7マス
        if ((row != 0) and (col != 0) and (row != col)) or ((row > 7) or (col > 7)):
            return False
        
        # 炎のアニメーション（簡易版では省略）
        # if not self.blind and not self._rogue_is_around(monster.row, monster.col):
        #     # 炎の表示
        #     pass
        
        # 攻撃を実行
        # mon_hit(monster, flame_name, 1)
        # Combatインスタンスを作成して攻撃
        combat = Combat(self.player, self.dungeon)
        combat.mon_hit(monster, "炎", flame=True)
        return True

    def _seek_gold(self, monster: Monster) -> bool:
        """
        金貨探索 (C版 spechit.c:302-332)
        
        モンスターが部屋内の金貨を探して移動する。
        """
        # モンスターがいる部屋を取得
        rn = get_room_number(self.dungeon, monster.row, monster.col)
        if rn < 0:
            return False
        
        room = self.dungeon.rooms[rn]
        
        # 部屋内の金貨を探す
        for i in range(room.top_row + 1, room.bottom_row):
            for j in range(room.left_col + 1, room.right_col):
                # 金貨があるかチェック
                if self._gold_at(i, j) and not (self.dungeon.dungeon[i][j] & const.MONSTER):
                    # CAN_FLITフラグを一時的に設定
                    monster.m_flags |= const.CAN_FLIT
                    can_go = self._mon_can_go(monster, i, j)
                    monster.m_flags &= ~const.CAN_FLIT
                    
                    if can_go:
                        self._move_mon_to(monster, i, j)
                        monster.m_flags |= const.ASLEEP
                        monster.m_flags &= ~(const.WAKENS | const.SEEKS_GOLD)
                        return True
                    
                    # 直接移動できない場合は近づく
                    monster.m_flags &= ~const.SEEKS_GOLD
                    monster.m_flags |= const.CAN_FLIT
                    self.mv_monster(monster, i, j)
                    monster.m_flags &= ~const.CAN_FLIT
                    monster.m_flags |= const.SEEKS_GOLD
                    return True
        
        return False

    def _gold_at(self, row: int, col: int) -> bool:
        """
        指定位置に金貨があるかチェック (C版 spechit.c:334-346)
        """
        if self.dungeon.dungeon[row][col] & const.OBJECT:
            # level_objectsから金貨を探す
            obj = getattr(self.dungeon, 'level_objects', None)
            while obj:
                if obj.row == row and obj.col == col and obj.item_type == const.GOLD:
                    return True
                obj = getattr(obj, 'next_object', None)
        return False

    def _m_confuse(self, monster: Monster) -> bool:
        """
        混乱攻撃 (C版 spechit.c:459-479)
        
        モンスターがプレイヤーを混乱させる。
        """
        # プレイヤーが見えない場合は無効
        if not self._rogue_can_see(monster.row, monster.col):
            return False
        
        # 45%の確率で攻撃をキャンセル
        if utils.rand_percent(45):
            monster.m_flags &= ~const.CONFUSES
            return False
        
        # 55%の確率で混乱
        if utils.rand_percent(55):
            monster.m_flags &= ~const.CONFUSES
            GameState.confused += utils.get_rand(12, 22)
            if self.msg:
                mn = self._mon_name(monster)
                self.msg.message(f"{mn}の視線が合った！", 1)
            return True
        
        return False

"""
inventory.py - インベントリシステム
src/pack.c, src/invent.c から移植

アイテムを拾う、捨てる、インベントリ内での文字割り当て（'a', 'b'など）を管理します。
"""

from typing import Optional, List, Tuple, Dict

try:
    from . import const, utils
    from .entities import Player, Item, ItemId
    from .dungeon import DungeonLevel
    from .ai.input_hook import hook_getchar_str as _ai_hook_getchar_str
except ImportError:
    import const, utils
    import entities
    import dungeon
    Player = entities.Player
    Item = entities.Item
    ItemId = entities.ItemId
    DungeonLevel = dungeon.DungeonLevel
    try:
        from ai.input_hook import hook_getchar_str as _ai_hook_getchar_str
    except ImportError:
        _ai_hook_getchar_str = None


# アイテム識別テーブル
# C版 object.c の初期値 (value, real) を設定
id_scrolls: List[ItemId] = [
    ItemId(value=505, real="よろいを守る"),       # PROTECT_ARMOR  mesg[362]
    ItemId(value=200, real="怪物を封じこめる"),   # HOLD_MONSTER   mesg[363]
    ItemId(value=235, real="武器に魔法をかける"),  # ENCH_WEAPON    mesg[364]
    ItemId(value=235, real="よろいに魔法をかける"), # ENCH_ARMOR     mesg[365]
    ItemId(value=175, real="持ちものの種類がわかる"), # IDENTIFY    mesg[366]
    ItemId(value=190, real="テレポートする"),      # TELEPORT       mesg[367]
    ItemId(value=25, real="眠りにおちる"),         # SLEEP          mesg[368]
    ItemId(value=610, real="怪物を近寄せない"),    # SCARE_MONSTER  mesg[369]
    ItemId(value=210, real="のろいを解く"),        # REMOVE_CURSE   mesg[370]
    ItemId(value=100, real="怪物を作りだす"),      # CREATE_MONSTER mesg[371]
    ItemId(value=25, real="怪物を怒らせる"),       # AGGRAVATE_MONSTER mesg[372]
    ItemId(value=180, real="魔法の地図の"),        # MAGIC_MAPPING  mesg[373]
]
id_potions: List[ItemId] = [
    ItemId(value=100, real="強さが増す"),          # INCREASE_STRENGTH  mesg[348]
    ItemId(value=250, real="強さが元にもどる"),    # RESTORE_STRENGTH   mesg[349]
    ItemId(value=100, real="体力が回復する"),      # HEALING            mesg[350]
    ItemId(value=200, real="体力がとても回復する"), # EXTRA_HEALING     mesg[351]
    ItemId(value=10, real="毒の"),                 # POISON             mesg[352]
    ItemId(value=300, real="経験が増す"),          # RAISE_LEVEL        mesg[353]
    ItemId(value=10, real="目が見えなくなる"),     # BLINDNESS          mesg[354]
    ItemId(value=25, real="幻覚をおこす"),         # HALLUCINATION      mesg[355]
    ItemId(value=100, real="遠くの怪物がわかる"),   # DETECT_MONSTER    mesg[356]
    ItemId(value=100, real="遠くのものがわかる"),   # DETECT_OBJECTS    mesg[357]
    ItemId(value=10, real="頭が混乱する"),         # CONFUSION          mesg[358]
    ItemId(value=80, real="空中に浮きあがる"),     # LEVITATION         mesg[359]
    ItemId(value=150, real="素早くなる"),          # HASTE_SELF         mesg[360]
    ItemId(value=145, real="見えないものが見える"), # SEE_INVISIBLE     mesg[361]
]
id_wands: List[ItemId] = [
    ItemId(value=25, real="怪物を遠くに飛ばす"),   # TELE_AWAY      mesg[389]
    ItemId(value=50, real="怪物を遅くする"),       # SLOW_MONSTER   mesg[390]
    ItemId(value=45, real="怪物を混乱させる"),     # CONFUSE_MONSTER mesg[391]
    ItemId(value=8, real="怪物を見えなくする"),    # INVISIBILITY   mesg[392]
    ItemId(value=55, real="ほかの怪物にする"),     # POLYMORPH      mesg[393]
    ItemId(value=2, real="怪物を素早くする"),      # HASTE_MONSTER  mesg[394]
    ItemId(value=25, real="眠らせる"),             # PUT_TO_SLEEP   mesg[395]
    ItemId(value=20, real="魔法のミサイルの"),     # MAGIC_MISSILE  mesg[396]
    ItemId(value=20, real="魔力を封じる"),         # CANCELLATION   mesg[397]
    ItemId(value=0, real="役に立たない"),          # DO_NOTHING     mesg[398]
]
id_rings: List[ItemId] = [
    ItemId(value=250, real="身を隠す"),            # STEALTH            mesg[399]
    ItemId(value=100, real="テレポートする"),      # R_TELEPORT         mesg[400]
    ItemId(value=255, real="体力が復活する"),      # REGENERATION       mesg[401]
    ItemId(value=295, real="食べものが長持ちする"), # SLOW_DIGEST       mesg[402]
    ItemId(value=200, real="強さが増す"),          # ADD_STRENGTH       mesg[403]
    ItemId(value=250, real="強さが減らない"),      # SUSTAIN_STRENGTH   mesg[404]
    ItemId(value=250, real="機敏になる"),          # DEXTERITY          mesg[405]
    ItemId(value=25, real="飾りものの"),           # ADORNMENT          mesg[406]
    ItemId(value=300, real="見えないものが見える"), # R_SEE_INVISIBLE   mesg[407]
    ItemId(value=290, real="よろいが丈夫になる"),   # MAINTAIN_ARMOR    mesg[408]
    ItemId(value=270, real="隠れたものを見つける"), # SEARCHING         mesg[409]
]
id_weapons: List[ItemId] = [
    ItemId(value=150, real="弓"),        # BOW              mesg[374]
    ItemId(value=8, real="投げ矢"),      # DART             mesg[375]
    ItemId(value=15, real="矢"),         # ARROW            mesg[376]
    ItemId(value=27, real="短剣"),       # DAGGER           mesg[377]
    ItemId(value=35, real="手裏剣"),     # SHURIKEN         mesg[378]
    ItemId(value=360, real="ほこ"),      # MACE             mesg[379]
    ItemId(value=470, real="長い剣"),    # LONG_SWORD       mesg[380]
    ItemId(value=580, real="大きな剣"),  # TWO_HANDED_SWORD mesg[381]
]
id_armors: List[ItemId] = [
    ItemId(value=300, real="", id_status=const.UNIDENTIFIED),  # LEATHER
    ItemId(value=300, real="", id_status=const.UNIDENTIFIED),  # RINGMAIL
    ItemId(value=400, real="", id_status=const.UNIDENTIFIED),  # SCALE
    ItemId(value=500, real="", id_status=const.UNIDENTIFIED),  # CHAIN
    ItemId(value=600, real="", id_status=const.UNIDENTIFIED),  # BANDED
    ItemId(value=600, real="", id_status=const.UNIDENTIFIED),  # SPLINT
    ItemId(value=700, real="", id_status=const.UNIDENTIFIED),  # PLATE
]

# ポーションの色 (C版 mesg[334]-mesg[347], 14色)
po_color = [
    "青い", "赤い", "緑の", "灰色の", "茶色の",
    "透明な", "ピンクの", "白い", "紫の", "黒い",
    "黄色い", "水色の", "ぶどう色の", "オレンジ色の"
]

# 杖の素材 (C版 mesg[410]-mesg[439], WAND_MATERIALS=30)
wand_materials = [
    "鋼鉄", "青銅", "金", "銀", "銅",
    "ニッケル", "コバルト", "すず", "鉄", "マグネシウム",
    "クロム", "石炭", "プラチナ", "シリコン", "チタン",
    "チーク", "樫", "桜", "白樺", "松",
    "杉", "アメリカ杉", "バルサ", "象牙やし", "胡桃",
    "楓", "マホガニー", "楡", "やし", "柿"
]

# 木製素材の閾値（C言語版: MAX_METAL = 14）
# インデックス > MAX_METAL の素材が木製
MAX_METAL = 14

# 宝石の種類 (C版 mesg[440]-mesg[453], GEMS=14)
gems = [
    "ダイヤ", "アクアマリン", "るり", "ルビー", "エメラルド",
    "サファイア", "紫水晶", "水晶", "虎目石", "オパール",
    "めのう", "トルコ石", "真珠", "ざくろ石"
]

# 音節 (C版 mesg[454]-mesg[493], MAXSYLLABLES=40)
syllables = [
    "ぶん ", "に ", "とす ", "ら ", "ぽみ ",
    "ぷ ", "どん ", "せろ ", "い ", "か ",
    "そろ ", "む ", "ろお ", "わ ", "おふ ",
    "ろん ", "わっと ", "ぴお ", "ぽんぽ ", "どどら ",
    "ひゅ ", "よふ ", "ぽた ", "るん ", "ばび ",
    "ろろり ", "ずず ", "ぐり ", "こも ", "きき ",
    "およ ", "いむ ", "にゃあ ", "うー ", "ぐふる ",
    "こぴ ", "すーる ", "ぽろん ", "みーる ", "ぽきし "
]

# 杖が木製かどうか
is_wood = [False] * const.WANDS


def get_wand_and_ring_materials():
    """
    杖と指輪の素材を初期化
    
    C言語版の get_wand_and_ring_materials() から移植
    - 各杖タイプにランダムに素材を割り当て
    - is_wood[i] = (素材インデックス > MAX_METAL) で木製かどうかを設定
    - 各指輪タイプにランダムに宝石を割り当て
    """
    # 杖の素材を割り当て
    used_materials = [False] * len(wand_materials)
    for i in range(const.WANDS):
        while True:
            j = utils.get_rand(0, len(wand_materials) - 1)
            if not used_materials[j]:
                break
        used_materials[j] = True
        
        id_wands[i].title = wand_materials[j]
        is_wood[i] = (j > MAX_METAL)
    
    # 指輪の宝石を割り当て
    used_gems = [False] * len(gems)
    for i in range(const.RINGS):
        while True:
            j = utils.get_rand(0, len(gems) - 1)
            if not used_gems[j]:
                break
        used_gems[j] = True
        
        id_rings[i].title = gems[j]


def mix_colors():
    """
    ポーションの色をシャッフル
    
    C言語版の mix_colors() から移植
    """
    for i in range(const.POTIONS):
        id_potions[i].title = po_color[i]
    
    for i in range(const.POTIONS):
        j = utils.get_rand(i, const.POTIONS - 1)
        id_potions[i].title, id_potions[j].title = id_potions[j].title, id_potions[i].title


def make_scroll_titles():
    """
    巻物のタイトルを生成
    
    C言語版の make_scroll_titles() から移植
    """
    for i in range(const.SCROLS):
        num_sylls = utils.get_rand(2, 5)
        title = "「"
        for _ in range(num_sylls):
            s = utils.get_rand(1, len(syllables) - 1)
            title += syllables[s]
        title += "」"
        id_scrolls[i].title = title


class InventoryManager:
    """インベントリ管理クラス"""

    def __init__(self, player: Player, dungeon: DungeonLevel):
        self.player = player
        self.dungeon = dungeon

    def add_to_pack(self, obj: Item, condense: bool = True) -> Optional[Item]:
        """アイテムをインベントリに追加"""
        if condense:
            op = self._check_duplicate(obj)
            if op:
                # 重複アイテムは数量を追加
                op.quantity += obj.quantity
                return op
            else:
                # 新しい文字を割り当て
                obj.ichar = self._next_avail_ichar()

        # ソート順に挿入
        if self.player.pack is None:
            self.player.pack = obj
            obj.next_object = None
        else:
            # タイプ順にソート
            prev = None
            current = self.player.pack
            while current and current.next_object:
                if current.next_object.item_type > obj.item_type:
                    break
                prev = current
                current = current.next_object

            if prev is None:
                # 先頭に挿入
                if self.player.pack.item_type > obj.item_type:
                    obj.next_object = self.player.pack
                    self.player.pack = obj
                else:
                    obj.next_object = self.player.pack.next_object
                    self.player.pack.next_object = obj
            else:
                obj.next_object = current.next_object
                current.next_object = obj

        return obj

    def take_from_pack(self, obj: Item) -> None:
        """インベントリからアイテムを削除"""
        if self.player.pack is None:
            return

        if self.player.pack == obj:
            self.player.pack = obj.next_object
        else:
            current = self.player.pack
            while current and current.next_object != obj:
                current = current.next_object
            if current:
                current.next_object = obj.next_object

    def pick_up(self, row: int, col: int) -> Tuple[Optional[Item], int]:
        """アイテムを拾う"""
        obj = self._object_at(row, col)
        if obj is None:
            return None, 0

        status = 1

        # 怖がらせの巻物の特殊処理 (C版 pack.c:86-96)
        # which_kind/item_kind二重化対応で両方参照
        _sk = obj.which_kind if getattr(obj, 'which_kind', 0) else getattr(obj, 'item_kind', 0)
        if (obj.item_type == const.SCROL and _sk == const.SCARE_MONSTER
                and obj.picked_up):
            # message(mesg[86])相当、地上から消去
            self.dungeon.dungeon[row][col] &= ~const.OBJECT
            self._remove_object(obj)
            status = 0
            # C版 pack.c:92-94 初回拾得で自動識別
            try:
                if id_scrolls[const.SCARE_MONSTER].id_status == const.UNIDENTIFIED:
                    id_scrolls[const.SCARE_MONSTER].id_status = const.IDENTIFIED
            except Exception:
                pass
            return None, status

        # 金の処理
        if obj.item_type == const.GOLD:
            self.player.gold += obj.quantity
            self.dungeon.dungeon[row][col] &= ~const.OBJECT
            self._remove_object(obj)
            return obj, status

        # インベントリがいっぱいかチェック
        if self.pack_count(obj) >= const.MAX_PACK_COUNT:
            # message("荷物がいっぱいだ", 1)
            return None, status

        self.dungeon.dungeon[row][col] &= ~const.OBJECT
        self._remove_object(obj)
        obj = self.add_to_pack(obj, True)
        obj.picked_up = True
        return obj, status

    def drop(self) -> bool:
        """アイテムを捨てる"""
        # 現在位置にアイテムがあるかチェック
        if self.dungeon.dungeon[self.player.row][self.player.col] & (const.OBJECT | const.STAIRS | const.TRAP):
            # message("ここには何も置けない", 0)
            return False

        # インベントリが空かチェック
        if self.player.pack is None:
            # message("何も持っていない", 0)
            return False

        # 捨てるアイテムを選択
        ch = self._pack_letter("どれを捨てますか？", const.ALL_OBJECTS)
        if ch == const.CANCEL:
            return False

        obj = self._get_letter_object(ch)
        if obj is None:
            # message("そのようなアイテムはない", 0)
            return False

        # 装備中のアイテムは呪われていないかチェック
        if obj.in_use_flags & const.BEING_WIELDED:
            if obj.is_cursed:
                # message("それは呪われている！", 0)
                return False
            self.unwield(obj)
        elif obj.in_use_flags & const.BEING_WORN:
            if obj.is_cursed:
                # message("それは呪われている！", 0)
                return False
            self.unwear(obj)
        elif obj.in_use_flags & const.ON_EITHER_HAND:
            if obj.is_cursed:
                # message("それは呪われている！", 0)
                return False
            self.un_put_on(obj)

        obj.row = self.player.row
        obj.col = self.player.col

        # 複数アイテムの場合
        if obj.quantity > 1 and obj.item_type != const.WEAPON:
            obj.quantity -= 1
            new_item = Item()
            new_item.__dict__.update(obj.__dict__)
            new_item.quantity = 1
            new_item.next_object = None
            obj = new_item
        else:
            obj.ichar = 'L'
            self.take_from_pack(obj)

        self._place_at(obj, self.player.row, self.player.col)
        # message(f"{obj.name}を置いた", 0)
        return True

    def take_off(self) -> bool:
        """防具を外す"""
        if self.player.armor:
            if self.player.armor.is_cursed:
                # message("それは呪われている！", 0)
                return False
            obj = self.player.armor
            self.unwear(obj)
            # message(f"{obj.name}を脱いだ", 0)
            return True
        else:
            # message("防具を着ていない", 0)
            return False

    def wear(self, obj=None) -> bool:
        if self.player.armor:
            return False

        if obj is None:
            ch = self._pack_letter("どれを着ますか？", const.ARMOR)
            if ch == const.CANCEL:
                return False
            obj = self._get_letter_object(ch)
            if obj is None:
                return False

        if obj.item_type != const.ARMOR:
            return False

        obj.identified = const.IDENTIFIED
        self.do_wear(obj)
        return True

    def unwear(self, obj: Item) -> None:
        """防具を外す"""
        if obj:
            obj.in_use_flags &= ~const.BEING_WORN
        self.player.armor = None

    def do_wear(self, obj: Item) -> None:
        """防具を装備"""
        self.player.armor = obj
        obj.in_use_flags |= const.BEING_WORN
        obj.identified = const.IDENTIFIED

    def wield(self, obj=None) -> bool:
        if self.player.weapon and self.player.weapon.is_cursed:
            return False

        if obj is None:
            ch = self._pack_letter("どれを装備しますか？", const.WEAPON)
            if ch == const.CANCEL:
                return False
            obj = self._get_letter_object(ch)
            if obj is None:
                return False

        if obj.item_type & (const.ARMOR | const.RING):
            return False

        if obj.in_use_flags & const.BEING_WIELDED:
            return False

        self.unwield(self.player.weapon)
        self.do_wield(obj)
        return True

    def do_wield(self, obj: Item) -> None:
        """武器を装備"""
        self.player.weapon = obj
        obj.in_use_flags |= const.BEING_WIELDED

    def unwield(self, obj: Item) -> None:
        """武器を外す"""
        if obj:
            obj.in_use_flags &= ~const.BEING_WIELDED
        self.player.weapon = None

    def put_on(self) -> bool:
        """指輪を装備"""
        ch = self._pack_letter("どれをはめますか？", const.RING)
        if ch == const.CANCEL:
            return False

        obj = self._get_letter_object(ch)
        if obj is None:
            # message("そのようなアイテムはない", 0)
            return False

        if obj.item_type != const.RING:
            # message("それは指輪ではない", 0)
            return False

        # どちらの手に装備するか
        if self.player.left_ring and self.player.right_ring:
            # message("両手に指輪をはめている", 0)
            return False
        elif self.player.left_ring:
            self.player.right_ring = obj
            obj.in_use_flags |= const.ON_RIGHT_HAND
        else:
            self.player.left_ring = obj
            obj.in_use_flags |= const.ON_LEFT_HAND

        obj.identified = const.IDENTIFIED
        # message(f"{obj.name}をはめた", 0)
        return True

    def un_put_on(self, obj: Item) -> None:
        """指輪を外す"""
        if obj:
            obj.in_use_flags &= ~const.ON_EITHER_HAND
        if self.player.left_ring == obj:
            self.player.left_ring = None
        if self.player.right_ring == obj:
            self.player.right_ring = None

    def pack_count(self, new_obj: Optional[Item] = None) -> int:
        """インベントリ内のアイテム数をカウント (C版 pack.c: pack_count)"""
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

    def has_amulet(self) -> bool:
        """アミュレットを持っているか"""
        obj = self.player.pack
        while obj:
            if obj.item_type == const.AMULET:
                return True
            obj = obj.next_object
        return False

    def get_inventory_list(self, mask: int = const.ALL_OBJECTS) -> List[Tuple[str, Item]]:
        """インベントリリストを取得"""
        items = []
        obj = self.player.pack

        while obj:
            if obj.item_type & mask:
                items.append((obj.ichar, obj))
            obj = obj.next_object

        return items

    def _check_duplicate(self, obj: Item) -> Optional[Item]:
        """重複アイテムをチェック (C版 pack.c: check_duplicate)"""
        # 武器、食料、巻物、ポーションのみ
        if not (obj.item_type & (const.WEAPON | const.FOOD | const.SCROL | const.POTION)):
            return None

        # C版 pack.c:184-215 FRUIT除外。which_kind/item_kind二重化対応で両方参照
        obj_kind = obj.which_kind if getattr(obj, 'which_kind', 0) else getattr(obj, 'item_kind', 0)
        if obj.item_type == const.FOOD and obj_kind == const.FRUIT:
            return None

        current = self.player.pack
        while current:
            cur_kind = current.which_kind if getattr(current, 'which_kind', 0) else getattr(current, 'item_kind', 0)
            if (current.item_type == obj.item_type and cur_kind == obj_kind):
                # 武器の場合は矢、短剣、ダーツ、手裏剣のみ重複
                # かつquiver（矢筒の数）が同じ場合のみ重複扱い (C版 pack.c:201-207)
                if (obj.item_type != const.WEAPON or
                        (obj_kind in (const.ARROW, const.DAGGER, const.DART, const.SHURIKEN) and
                         obj.quiver == current.quiver)):
                    return current
            current = current.next_object

        return None

    def _next_avail_ichar(self) -> str:
        """次に使用可能な文字を取得"""
        ichars = [False] * 26

        obj = self.player.pack
        while obj:
            if 'a' <= obj.ichar <= 'z':
                ichars[ord(obj.ichar) - ord('a')] = True
            obj = obj.next_object

        for i in range(26):
            if not ichars[i]:
                return chr(ord('a') + i)

        return '?'

    def _pack_letter(self, prompt: str, mask: int) -> str:
        """インベントリから文字を選択 (C版 pack.c: pack_letter)"""
        if not self._mask_pack(mask):
            # message("該当するアイテムがない", 0)
            return const.CANCEL

        if getattr(self, 'display', None) and getattr(self, 'message', None):
            self.display.inventory(self.player.pack, mask, None, self.player)
            self.message.message(prompt)
            ch = self._getchar()
            if ch == '\x1b' or ch is None:
                return const.CANCEL
            return ch

        obj = self.player.pack
        while obj:
            if obj.item_type & mask:
                ch = obj.ichar
                if isinstance(ch, int):
                    ch = chr(ch)
                return ch if ch else const.CANCEL
            obj = obj.next_object

        return const.CANCEL

    def _getchar(self) -> Optional[str]:
        """cursesから1文字入力を取得（AI自動プレイ時はキューを優先）"""
        if _ai_hook_getchar_str is not None:
            hooked = _ai_hook_getchar_str()
            if hooked is not None:
                return hooked
        try:
            import curses
            return chr(curses.getch())
        except Exception:
            return None

    def _mask_pack(self, mask: int) -> bool:
        """マスクに一致するアイテムがあるか"""
        obj = self.player.pack
        while obj:
            if obj.item_type & mask:
                return True
            obj = obj.next_object
        return False

    def _get_id_table(self, obj: Item):
        """アイテム種別の識別テーブルを返す (C版 invent.c: get_id_table)"""
        t = getattr(obj, "item_type", 0)
        if t & const.SCROL:
            return id_scrolls
        if t & const.POTION:
            return id_potions
        if t & const.WAND:
            return id_wands
        if t & const.RING:
            return id_rings
        if t & const.WEAPON:
            return id_weapons
        if t & const.ARMOR:
            return id_armors
        return None

    def _get_letter_object(self, ch: str) -> Optional[Item]:
        """文字からアイテムを取得"""
        obj = self.player.pack
        while obj:
            if obj.ichar == ch:
                return obj
            obj = obj.next_object
        return None

    def _object_at(self, row: int, col: int) -> Optional[Item]:
        """指定位置のアイテムを取得"""
        obj = self.dungeon.level_objects
        while obj:
            if obj.row == row and obj.col == col:
                return obj
            obj = obj.next_object
        return None

    def _remove_object(self, obj: Item) -> None:
        """オブジェクトリストから削除"""
        if self.dungeon.level_objects == obj:
            self.dungeon.level_objects = obj.next_object
        else:
            current = self.dungeon.level_objects
            while current and current.next_object != obj:
                current = current.next_object
            if current:
                current.next_object = obj.next_object

    def _place_at(self, obj: Item, row: int, col: int) -> None:
        """指定位置にアイテムを配置"""
        obj.row = row
        obj.col = col
        obj.next_object = self.dungeon.level_objects
        self.dungeon.level_objects = obj
        self.dungeon.dungeon[row][col] |= const.OBJECT

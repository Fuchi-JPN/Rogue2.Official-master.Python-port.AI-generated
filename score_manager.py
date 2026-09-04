"""
score_manager.py - スコアリング
src/score.c から移植

スコア記録、ハイスコア管理、アイテム売却を実装します。
"""

import os
from typing import Optional, List
from dataclasses import dataclass, field

try:
    from . import const
    from .entities import Player, Item
except ImportError:
    import const
    import entities
    Player = entities.Player
    Item = entities.Item


@dataclass
class ScoreEntry:
    """スコアエントリ"""
    rank: int
    score: int
    name: str
    level: int
    cause: str  # 死因または勝利


class ScoreManager:
    """スコア管理クラス"""

    def __init__(self):
        self.score_file = ".rogue.scores"
        self.score_only = False
        self.show_skull = True

    def killed_by(self, monster_name: Optional[str] = None, other: int = 0, player: Optional[Player] = None) -> None:
        """死亡時の処理"""
        if player is None:
            return

        # 退出以外はスコアを減らす
        if other != const.QUIT:
            player.gold = (player.gold * 9) // 10

        # 死因を決定
        if other:
            cause = self._get_death_cause(other)
        else:
            cause = f"{monster_name}に殺された"

        # スコアを記録
        self._put_scores(player, monster_name, other, cause)

    def win(self, player: Player, display=None) -> None:
        """勝利時の処理 (C版 score.c: win)"""
        # 装備を解除 (C版: unwield, unwear, un_put_on)
        if player.weapon:
            player.weapon.in_use_flags &= ~const.BEING_WIELDED
            player.weapon = None
        if player.armor:
            player.armor.in_use_flags &= ~const.BEING_WORN
            player.armor = None
        if player.left_ring:
            player.left_ring.in_use_flags &= ~const.ON_LEFT_HAND
            player.left_ring = None
        if player.right_ring:
            player.right_ring.in_use_flags &= ~const.ON_RIGHT_HAND
            player.right_ring = None

        # アイテムを識別
        self._id_all()

        # アイテムを売却
        gold_earned = self._sell_pack(player, display)
        player.gold += gold_earned

        if player.gold > const.MAX_GOLD:
            player.gold = const.MAX_GOLD

        # スコアを記録
        self._put_scores(player, None, const.WIN, "勝利！")

    def _put_scores(self, player: Player, monster_name: Optional[str], other: int, cause: str) -> None:
        """スコアを記録して表示"""
        # 既存のスコアを読み込む
        scores = self._load_scores()

        # 新しいスコアエントリを作成
        new_entry = ScoreEntry(
            rank=0,
            score=player.gold,
            name=player.name if player.name else "プレイヤー",
            level=player.dungeon_level,
            cause=cause
        )

        # ランクを決定
        rank = self._get_rank(scores, new_entry)

        if rank < 10:
            # スコアを挿入
            scores.insert(rank, new_entry)
            if len(scores) > 10:
                scores = scores[:10]

            # スコアを保存
            self._save_scores(scores)

        # スコアを表示
        self._display_scores(scores, rank)

    def _load_scores(self) -> List[ScoreEntry]:
        """スコアファイルから読み込む"""
        scores = []

        try:
            if os.path.exists(self.score_file):
                with open(self.score_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            parts = line.strip().split(',')
                            if len(parts) >= 5:
                                scores.append(ScoreEntry(
                                    rank=int(parts[0]),
                                    score=int(parts[1]),
                                    name=parts[2],
                                    level=int(parts[3]),
                                    cause=','.join(parts[4:])
                                ))
        except Exception as e:
            print(f"スコア読み込みエラー: {e}")

        return scores

    def _save_scores(self, scores: List[ScoreEntry]) -> None:
        """スコアファイルに保存"""
        try:
            with open(self.score_file, 'w', encoding='utf-8') as f:
                for entry in scores:
                    f.write(f"{entry.rank},{entry.score},{entry.name},{entry.level},{entry.cause}\n")
        except Exception as e:
            print(f"スコア保存エラー: {e}")

    def _get_rank(self, scores: List[ScoreEntry], new_entry: ScoreEntry) -> int:
        """新しいスコアのランクを取得"""
        for i, entry in enumerate(scores):
            if new_entry.score > entry.score:
                return i
        return len(scores)

    def _display_scores(self, scores: List[ScoreEntry], current_rank: int) -> None:
        """スコアを表示"""
        print("\n" + "=" * 60)
        print("トップ10 ローグライクプレイヤー")
        print("=" * 60)
        print(f"{'順位':<6}{'スコア':<12}{'名前':<16}{'レベル':<8}{'死因/結果'}")
        print("-" * 60)

        for i, entry in enumerate(scores):
            marker = ">>>" if i == current_rank else "   "
            print(f"{marker}{i+1:<3} {entry.score:<12} {entry.name:<16} {entry.level:<8} {entry.cause}")

        print("=" * 60)

    def _get_death_cause(self, other: int) -> str:
        """死因を取得"""
        causes = {
            const.HYPOTHERMIA: "低体温症で死亡",
            const.STARVATION: "餓死",
            const.POISON_DART: "毒矢で死亡",
            const.QUIT: "退出",
            const.WIN: "勝利"
        }
        return causes.get(other, "死亡")

    def _sell_pack(self, player: Player, display=None) -> int:
        """インベントリのアイテムを売却 (C版 score.c: sell_pack)"""
        total_gold = 0
        row = 2

        if display:
            # curses表示
            display.clear()
            display.mvaddstr(1, 0, "アイテム売却:")

        items = []
        curr = player.pack
        while curr:
            if curr.item_type != const.FOOD:
                curr.identified = True
                value = self._get_value(curr)
                total_gold += value
                items.append((value, curr))
            curr = curr.next_object

        for value, item in items:
            item_name = self._get_item_desc(item, display)
            if display:
                if row < const.ROGUE_LINES:
                    buf = f"{value:5d}      {item_name}"
                    display.mvaddstr(row, 0, buf)
                    row += 1
            else:
                print(f"{value:6}g    {item_name}")

        if display:
            display.refresh()
            # メッセージ待ち
            display.mvaddstr(const.ROGUE_LINES - 1, 0, "--スペースキーで続行--")
            display.refresh()
            while True:
                ch = display.getch()
                if ch in (ord(' '), ord('\n'), ord('\r'), 27):
                    break
        else:
            print("-" * 60)
            print(f"合計: {total_gold}g")

        return total_gold

    def _get_item_desc(self, item: Item, display=None) -> str:
        """アイテムの説明を取得 (C版 invent.c: get_desc 同等)"""
        try:
            from . import inventory as inv
        except ImportError:
            import inventory as inv

        if item.item_type == const.GOLD:
            return f"{item.quantity} ゴールド"
        if item.item_type == const.FOOD:
            kind = item.which_kind
            if kind == const.RATION:
                return "食料"
            return "果物"  # fruit
        if item.item_type == const.SCROL:
            if item.identified:
                return f"巻物「{inv.id_scrolls[item.which_kind].real}」"
            return inv.make_scroll_titles(item.which_kind) if hasattr(inv, 'make_scroll_titles') else "巻物"
        if item.item_type == const.POTION:
            if item.identified:
                return f"{inv.po_color[item.which_kind]}ポーション"
            return f"{inv.po_color[item.which_kind]}ポーション"
        if item.item_type == const.WAND:
            wc = item.which_kind
            material = inv.wand_materials[wc % len(inv.wand_materials)] if inv.wand_materials else "不明"
            if item.identified:
                return f"{material}の杖「{inv.id_wands[wc].real}」"
            return f"{material}の杖"
        if item.item_type == const.RING:
            if item.identified:
                return f"指輪「{inv.id_rings[item.which_kind].real}」"
            return "指輪"
        if item.item_type == const.ARMOR:
            name = inv.id_armors[item.which_kind].real if inv.id_armors[item.which_kind].real else "よろい"
            if item.is_protected:
                name = "防錆の" + name
            return name
        if item.item_type == const.WEAPON:
            return inv.id_weapons[item.which_kind].real if inv.id_weapons[item.which_kind].real else "武器"
        if item.item_type == const.AMULET:
            return "イェンダーのアミュレット"
        return "アイテム"

    def _get_value(self, item: Item) -> int:
        """アイテムの価値を計算 (C版 score.c: get_value)"""
        try:
            from . import inventory
        except ImportError:
            import inventory

        wc = item.which_kind

        if item.item_type == const.WEAPON:
            val = inventory.id_weapons[wc].value if wc < len(inventory.id_weapons) else 10
            if wc in (const.ARROW, const.DAGGER, const.SHURIKEN, const.DART):
                val *= item.quantity
            val += (item.d_enchant * 85) + (item.hit_enchant * 85)
        elif item.item_type == const.ARMOR:
            val = (inventory.id_armors[wc].value if wc < len(inventory.id_armors) else 10) + (item.d_enchant * 75)
            if item.is_protected:
                val += 200
        elif item.item_type == const.WAND:
            val = (inventory.id_wands[wc].value if wc < len(inventory.id_wands) else 10) * (item.class_ + 1)
        elif item.item_type == const.SCROL:
            val = (inventory.id_scrolls[wc].value if wc < len(inventory.id_scrolls) else 10) * item.quantity
        elif item.item_type == const.POTION:
            val = (inventory.id_potions[wc].value if wc < len(inventory.id_potions) else 10) * item.quantity
        elif item.item_type == const.AMULET:
            val = 5000
        elif item.item_type == const.RING:
            val = (inventory.id_rings[wc].value if wc < len(inventory.id_rings) else 10) * (item.class_ + 1)
        else:
            val = 10

        if val <= 0:
            val = 10

        return val

    def _get_item_name(self, item: Item) -> str:
        """アイテム名を取得"""
        # 簡易版 - アイテムタイプのみ返す
        types = {
            const.WEAPON: "武器",
            const.ARMOR: "防具",
            const.WAND: "杖",
            const.SCROL: "巻物",
            const.POTION: "ポーション",
            const.RING: "指輪",
            const.AMULET: "アミュレット",
            const.FOOD: "食料"
        }
        return types.get(item.item_type, "アイテム")

    def _id_all(self) -> None:
        """全アイテムを識別（勝利時）"""
        # C言語版のid_all()に基づく実装
        # 注意: C言語版ではid_ringsは処理しない
        try:
            from . import inventory
        except ImportError:
            import inventory

        for i in range(const.SCROLS):
            inventory.id_scrolls[i].id_status = const.IDENTIFIED
        for i in range(const.WEAPONS):
            inventory.id_weapons[i].id_status = const.IDENTIFIED
        for i in range(const.ARMORS):
            inventory.id_armors[i].id_status = const.IDENTIFIED
        for i in range(const.WANDS):
            inventory.id_wands[i].id_status = const.IDENTIFIED
        for i in range(const.POTIONS):
            inventory.id_potions[i].id_status = const.IDENTIFIED

    def quit(self, player: Player) -> None:
        """退出時の処理"""
        # 確認
        response = input("本当に終了しますか？ (y/n): ")
        if response.lower() != 'y':
            return

        self.killed_by(None, const.QUIT, player)

    def get_high_scores(self) -> List[ScoreEntry]:
        """ハイスコア一覧を取得"""
        return self._load_scores()

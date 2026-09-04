"""
game_state.py - ゲーム状態の一元管理

C言語版のグローバル変数を一元管理するモジュール。
src/use.c, src/move.c, src/ring.c などで定義されている
グローバル変数をこのモジュールで管理します。

使用方法:
    from game_state import GameState
    
    # 状態変数へのアクセス
    GameState.halluc = 100
    if GameState.blind:
        ...
"""

from dataclasses import dataclass, field
from typing import Optional, List

try:
    from . import const
except ImportError:
    import const


@dataclass
class GameStateClass:
    """ゲーム状態を一元管理するクラス
    
    C言語版のグローバル変数に対応:
    - halluc (use.c): 幻覚状態の残りターン数
    - blind (use.c): 盲目状態の残りターン数
    - confused (use.c): 混乱状態の残りターン数
    - levitate (use.c): 浮遊状態の残りターン数
    - haste_self (use.c): 加速状態の残りターン数
    - see_invisible (use.c): 不可視看见フラグ
    - extra_hp (use.c): ポーションによる追加HP
    - detect_monster (use.c): モンスター検出フラグ
    - bear_trap (move.c): 熊の罠の残りターン数
    - being_held (move.c): 捕まえられているフラグ
    - sustain_strength (ring.c): 筋力維持フラグ
    - m_moves (move.c): 移動カウンター（wanderer用）
    - interrupted (move.c): 割り込みフラグ
    - r_teleport (ring.c): ランダムテレポート指輪フラグ
    - auto_search (ring.c): 自動探索回数
    - regeneration (ring.c): HP再生回数
    - e_rings (ring.c): 満腹度への指輪効果
    - add_strength (ring.c): 筋力ボーナス
    - stealthy (ring.c): 忍び足フラグ
    - maintain_armor (ring.c): 防具維持フラグ
    - r_see_invisible (ring.c): 指輪による不可視看见
    - confused_player (combat.c): プレイヤー混乱フラグ
    - aggravate_monster (use.c): モンスター怒りフラグ
    - wizard (debug): デバッグモードフラグ
    - ring_exp (ring.c): 指輪による経験値ボーナス
    - r_rings (ring.c): 右手の指輪
    - l_rings (ring.c): 左手の指輪
    - cur_room (level.c): 現在の部屋番号
    - cur_level (level.c): 現在のダンジョンレベル
    - max_level (level.c): 到達した最大ダンジョンレベル
    - party_room (level.c): パーティールーム番号
    - party_counter (level.c): パーティーカウンター
    - foods (level.c): 食料カウンター
    - hunger_str (move.c): 空腹文字列
    - jump (move.c): ジャンプモード
    - bent_passage (move.c): 曲がり角フラグ
    """
    
    # 状態変数 (use.c)
    halluc: int = 0
    blind: int = 0
    confused: int = 0
    levitate: int = 0
    haste_self: int = 0
    see_invisible: bool = False
    extra_hp: int = 0
    detect_monster: bool = False
    
    # 状態変数 (move.c)
    bear_trap: int = 0
    being_held: bool = False
    m_moves: int = 0
    interrupted: bool = False
    hunger_str: str = ""
    jump: bool = False
    bent_passage: bool = False
    pass_go: bool = True
    trap_door: bool = False
    new_level_message: str = ""
    
    # 状態変数 (ring.c)
    sustain_strength: bool = False
    auto_search: int = 0
    regeneration: int = 0
    e_rings: int = 0
    add_strength: int = 0
    stealthy: int = 0
    maintain_armor: bool = False
    r_see_invisible: bool = False
    r_teleport: bool = False
    ring_exp: int = 0
    r_rings: int = 0
    
    # 状態変数 (combat.c)
    confused_player: bool = False
    aggravate_monster: bool = False
    fight_monster: object = None
    hit_message: str = ""
    mon_disappeared: bool = False
    # 指輪左右・スコア分離 (save.c 33項目対応、動的付与の固定化)
    l_rings: int = 0
    score_only: bool = False
    login_name: str = ""
    
    # 状態変数 (level.c)
    cur_room: int = const.NO_ROOM
    cur_level: int = 1
    max_level: int = 1
    party_room: int = const.NO_ROOM
    party_counter: int = 0
    foods: int = 0
    
    # デバッグモード
    wizard: bool = False

    # C static変数の単一集約 (move.c: heal/check_hunger/search寿命対策)
    # Movement都度生成でもリセットされないようGameStateに保持する
    heal_exp: int = -1
    heal_n: int = 0
    heal_c: int = 0
    heal_alt: bool = False
    move_left_cou: int = 0
    reg_search: bool = False
    
    # フルーツ名
    fruit: str = "こけもも"
    
    # メッセージ
    you_can_move_again: str = "ようやく体が自由になった。"
    
    def reset(self) -> None:
        """ゲーム状態をリセット"""
        self.halluc = 0
        self.blind = 0
        self.confused = 0
        self.levitate = 0
        self.haste_self = 0
        self.see_invisible = False
        self.extra_hp = 0
        self.detect_monster = False
        self.bear_trap = 0
        self.being_held = False
        self.m_moves = 0
        self.interrupted = False
        self.hunger_str = ""
        self.jump = False
        self.bent_passage = False
        self.pass_go = True
        self.trap_door = False
        self.new_level_message = ""
        self.sustain_strength = False
        self.auto_search = 0
        self.regeneration = 0
        self.e_rings = 0
        self.add_strength = 0
        self.stealthy = 0
        self.maintain_armor = False
        self.r_see_invisible = False
        self.r_teleport = False
        self.ring_exp = 0
        self.r_rings = 0
        self.confused_player = False
        self.aggravate_monster = False
        self.fight_monster = None
        self.hit_message = ""
        self.mon_disappeared = False
        self.cur_room = const.NO_ROOM
        self.cur_level = 1
        self.max_level = 1
        self.party_room = const.NO_ROOM
        self.party_counter = 0
        self.foods = 0
        self.wizard = False
        self.heal_exp = -1
        self.heal_n = 0
        self.heal_c = 0
        self.heal_alt = False
        self.move_left_cou = 0
        self.reg_search = False
    
    def reg_move_state(self) -> None:
        """移動毎の状態更新 (C版 move.c: reg_move の状態処理部分)"""
        # halluc処理
        if self.halluc:
            self.halluc -= 1
            if not self.halluc:
                self._unhallucinate()
        
        # blind処理
        if self.blind:
            self.blind -= 1
            if not self.blind:
                self._unblind()
        
        # confused処理
        if self.confused:
            self.confused -= 1
            if not self.confused:
                self._unconfuse()
        
        # bear_trap処理
        if self.bear_trap:
            self.bear_trap -= 1
        
        # levitate処理
        if self.levitate:
            self.levitate -= 1
            if not self.levitate:
                # mesg[78]: "ふっと、地面に足がついた。"
                pass
        
        # haste_self処理
        if self.haste_self:
            self.haste_self -= 1
            if not self.haste_self:
                # mesg[79]: "素早くなる薬の効き目がなくなった。"
                pass
        
        # m_moves更新 (wanderer用)
        self.m_moves += 1
        if self.m_moves >= 120:
            self.m_moves = 0
    
    def _unhallucinate(self) -> None:
        """幻覚解除"""
        pass  # 呼び出し元で処理
    
    def _unblind(self) -> None:
        """盲目解除"""
        pass  # 呼び出し元で処理
    
    def _unconfuse(self) -> None:
        """混乱解除"""
        pass  # 呼び出し元で処理


# シングルトンインスタンス
GameState = GameStateClass()


# モジュールレベルのアクセス関数 (C言語版との互換性用)
def get_halluc() -> int:
    return GameState.halluc

def set_halluc(value: int) -> None:
    GameState.halluc = value

def get_blind() -> int:
    return GameState.blind

def set_blind(value: int) -> None:
    GameState.blind = value

def get_confused() -> int:
    return GameState.confused

def set_confused(value: int) -> None:
    GameState.confused = value

def get_levitate() -> int:
    return GameState.levitate

def set_levitate(value: int) -> None:
    GameState.levitate = value

def get_haste_self() -> int:
    return GameState.haste_self

def set_haste_self(value: int) -> None:
    GameState.haste_self = value

def get_bear_trap() -> int:
    return GameState.bear_trap

def set_bear_trap(value: int) -> None:
    GameState.bear_trap = value

def get_being_held() -> bool:
    return GameState.being_held

def set_being_held(value: bool) -> None:
    GameState.being_held = value

def get_detect_monster() -> bool:
    return GameState.detect_monster

def set_detect_monster(value: bool) -> None:
    GameState.detect_monster = value

def get_see_invisible() -> bool:
    return GameState.see_invisible

def set_see_invisible(value: bool) -> None:
    GameState.see_invisible = value

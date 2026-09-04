"""
schemas.py - AI自律プレイ機能のデータスキーマ

設計書 §3.2 / §4.1 / §5.3 / §5.4.3
"""
from dataclasses import dataclass, field
from typing import Optional


# ============================================================================
# 観測
# ============================================================================

@dataclass
class AIStatus:
    level: int = 1
    gold: int = 0
    hp_cur: int = 0
    hp_max: int = 0
    str_cur: int = 0
    str_max: int = 0
    armor_class: int = 0
    exp_level: int = 1
    exp_points: int = 0
    moves_left: int = 0
    hunger: str = ""


@dataclass
class AIObservation:
    turn: int = 0
    player_pos: tuple = (0, 0)
    status: AIStatus = field(default_factory=AIStatus)
    local_view: list = field(default_factory=list)
    room_id: int = -3  # PASSAGE相当の既定値
    visible_monsters: list = field(default_factory=list)
    visible_items: list = field(default_factory=list)
    visible_doors: list = field(default_factory=list)
    all_doors: list = field(default_factory=list)
    unopened_doors: list = field(default_factory=list)
    search_count: int = 0  # 当手位置での隠し扉探索手数
    stairs_pos: Optional[tuple] = None
    message: Optional[str] = None
    mode: str = "normal"
    flags: dict = field(default_factory=dict)
    inventory_summary: list = field(default_factory=list)
    raw_screen: Optional[list] = None


# ============================================================================
# 行動
# ============================================================================

@dataclass
class AIAction:
    type: str = "noop"
    direction: Optional[str] = None
    item_slot: Optional[str] = None
    raw_keys: Optional[str] = None


# ============================================================================
# 識別メモ・リスク評価
# ============================================================================

@dataclass
class IdentifyMemo:
    potion: dict = field(default_factory=dict)
    scroll: dict = field(default_factory=dict)


@dataclass
class RiskAssessment:
    hp_ratio: float = 1.0
    hunger_level: str = "ok"
    adjacent_enemies: int = 0
    escape_routes: int = 0
    can_rest_safely: bool = True
    should_descend: bool = False


# ============================================================================
# 起動オプション
# ============================================================================

@dataclass
class AIOptions:
    enabled: bool = False
    provider: str = "openrouter"  # openrouter | openai_compat | scripted
    model: str = "inception/mercury-2.5-preview"
    endpoint: str = "https://openrouter.ai/api/v1/chat/completions"
    api_key: str = ""
    max_turns: int = 500
    delay_ms: int = 120
    timeout: float = 20.0
    max_tokens: int = 4096  # 推論系モデルはreasoningで消費するため余裕を持たせる
    log_file: str = "ai_session.jsonl"
    trace_file: str = "ai_trace.jsonl"  # 全文記録（prompt全文+生応答）。空で無効
    show_screen: bool = True  # 画面ダンプ全文をLLMへ添付する
    headless: bool = False
    replay_file: str = ""
    llm_fallback: bool = False  # True時のみLLM失敗でscripted継続（既定は即終了）

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "AIOptions":
        if not d:
            return cls()
        kw = {}
        for f in ("enabled", "provider", "model", "endpoint", "api_key",
                  "max_turns", "delay_ms", "timeout", "log_file",
                  "trace_file", "show_screen", "headless", "replay_file",
                  "llm_fallback", "max_tokens"):
            if f in d and d[f] is not None:
                kw[f] = d[f]
        return cls(**kw)

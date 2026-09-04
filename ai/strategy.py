"""
strategy.py - 攻略ロジックの正本（設計書 §5.4）

ScriptedPolicyは本モジュールのdecide()を直接実行し、
LLMAgentPolicyは本モジュールの定数・優先度表から生成した
プロンプト文面（llm.build_strategy_section）を注入する。
閾値の二重実装を防ぐため、本ファイルの定数が唯一の正本。
"""
from collections import deque
from typing import Optional

try:
    from .. import const
except ImportError:
    import const

try:
    from .schemas import AIAction, AIObservation, RiskAssessment
except ImportError:
    from schemas import AIAction, AIObservation, RiskAssessment


# ============================================================================
# 閾値（正本）
# ============================================================================

HP_REST_THRESHOLD = 1.0    # これ未満なら安全時にrest（＝満タン以外は回復待ち）
HP_FIGHT_MIN = 0.3         # これ未満では戦わない
HP_CRITICAL = 0.15         # 瀕死：退避・非常手段のみ

HUNGER_OK = 300            # const.HUNGRY：これ以下で食料探索へ
HUNGER_URGENT = 150        # const.WEAK：これ以下で食料最優先
HUNGER_FAINT = 20          # const.FAINT

STUCK_WINDOW = 8           # 直近N手の位置履歴で振動検知
STUCK_DISTINCT = 2         # 異なる座標がこの数以下なら停滞

# 8方向（設計書 §4.2。v2.1でu/b修正済み）
DIR_DELTA = {
    'h': (0, -1), 'j': (1, 0), 'k': (-1, 0), 'l': (0, 1),
    'y': (-1, -1), 'u': (-1, 1), 'b': (1, -1), 'n': (1, 1),
}

_PASSABLE_BITS = const.FLOOR | const.TUNNEL | const.DOOR | const.STAIRS


def tile_passable(tile: int) -> bool:
    """BFS・退路計算用の通過可否（MONSTER占有は不可）"""
    if tile & const.MONSTER:
        return False
    return bool(tile & _PASSABLE_BITS)


def legal_moves(obs: AIObservation) -> list:
    """現在位置から移動可能な方向文字の列（壁への空振り防止用）。

    本体 _can_move の斜め規則（ドア角・空虚角の禁止）まで再現する。
    """
    cache = getattr(obs, "_tile_cache", {}) or {}
    rmax, cmax = getattr(obs, "_grid_size", (const.ROGUE_LINES, const.ROGUE_COLUMNS))
    pr, pc = obs.player_pos

    def tile_fn(r, c):
        if not (const.MIN_ROW <= r < rmax and 0 <= c < cmax):
            return None
        return cache.get((r, c))

    out = []
    for d, (dr, dc) in DIR_DELTA.items():
        t = tile_fn(pr + dr, pc + dc)
        if t is None or not tile_passable(t):
            continue
        if dr != 0 and dc != 0 and _diag_blocked(tile_fn, pr, pc, pr + dr, pc + dc):
            continue
        out.append(d)
    return out


def hunger_level(moves_left: int) -> str:
    if moves_left <= HUNGER_FAINT:
        return "faint"
    if moves_left <= HUNGER_URGENT:
        return "weak"
    if moves_left <= HUNGER_OK:
        return "hungry"
    return "ok"


# 進行方向の記憶用：8方向の羅針盤名と左右関係
COMPASS = {
    'h': 'west', 'j': 'south', 'k': 'north', 'l': 'east',
    'y': 'northwest', 'u': 'northeast', 'b': 'southwest', 'n': 'southeast',
}
# 直進方向に対する左手・右手（直交4方向のみ。斜めは直進のみ）
LEFT_OF = {'h': 'j', 'j': 'l', 'l': 'k', 'k': 'h'}
RIGHT_OF = {'h': 'k', 'k': 'l', 'l': 'j', 'j': 'h'}


class ExplorationMemory:
    """踏破記憶：未開の扉（未通過の+）を覚える。

    ドアを「開ける」＝そのタイルを踏むこと。階層変化でリセットする。
    """

    SEARCH_BUDGET = 10  # 行き止まりでの隠し扉探索の上限手数

    def __init__(self):
        self.level = None
        self.visited: set = set()
        self.opened: set = set()
        self.search_counts: dict = {}  # pos -> 探索手数
        self.deadends: set = set()  # 探索打ち切り済みの行き止まり

    def update(self, obs: AIObservation):
        lv = obs.status.level
        if lv != self.level:
            self.level = lv
            self.visited = set()
            self.opened = set()
            self.search_counts = {}
            self.deadends = set()
        pos = tuple(obs.player_pos)
        self.visited.add(pos)
        for d in getattr(obs, "all_doors", None) or []:
            if tuple(d) == pos:
                self.opened.add(tuple(d))

    def unopened(self, obs: AIObservation) -> list:
        return [tuple(d) for d in (getattr(obs, "all_doors", None) or [])
                if tuple(d) not in self.opened]

    def unopened_visible(self, obs: AIObservation) -> list:
        """表示中の未開扉のみ。降下判断はこの一覧で行う"""
        return [tuple(d) for d in (getattr(obs, "visible_doors", None) or [])
                if tuple(d) not in self.opened]

    def search_count_at(self, pos) -> int:
        return self.search_counts.get(tuple(pos), 0)

    def deadend_pending(self, obs: AIObservation, heading) -> bool:
        """行き止まり探索の条件判定（副作用なし）"""
        pos = tuple(obs.player_pos)
        if pos in self.deadends:
            return False
        cache = getattr(obs, "_tile_cache", {}) or {}
        cur = cache.get(pos)
        if cur is None or not (cur & (const.TUNNEL | const.DOOR)):
            return False
        if corridor_step(obs, heading) is not None:
            self.search_counts.pop(pos, None)
            return False
        # 引き返し以外の選択肢があれば行き止まりではない（向き直しで解決）
        back = REVERSE_OF.get(heading)
        fresh = [d for d in legal_moves(obs) if d != back]
        if fresh:
            self.search_counts.pop(pos, None)
            return False
        for m in obs.visible_monsters:
            if max(abs(m["pos"][0] - pos[0]), abs(m["pos"][1] - pos[1])) <= 1:
                return False
        if obs.status.moves_left <= HUNGER_URGENT:
            return False
        return True

    def deadend_action(self, obs: AIObservation, heading):
        """行き止まりならsearch行動、予算超過で打ち切り。不要ならNone"""
        if not self.deadend_pending(obs, heading):
            return None
        pos = tuple(obs.player_pos)
        n = self.search_counts.get(pos, 0)
        if n >= self.SEARCH_BUDGET:
            self.deadends.add(pos)
            return None
        self.search_counts[pos] = n + 1
        return AIAction(type="search")


REVERSE_OF = {'h': 'l', 'l': 'h', 'j': 'k', 'k': 'j',
              'y': 'n', 'n': 'y', 'u': 'b', 'b': 'u'}


def corridor_step(obs: AIObservation, heading):
    """通路追従の次の一手。条件外・判断不能時はNone。

    通路（#）・扉（+）上で前進方向が既知の場合：直進、なければ
    左右のいずれか一方が開通していればそちらへ。来た方向への
    Uターン（部屋への逆戻り）は選ばない。分岐・袋小路はNone
    （通常判断に委ねる）。
    """
    if not heading or heading not in DIR_DELTA:
        return None
    cache = getattr(obs, "_tile_cache", {}) or {}
    pr, pc = obs.player_pos
    cur = cache.get((pr, pc))
    if cur is None or not (cur & (const.TUNNEL | const.DOOR)):
        return None
    legal = set(legal_moves(obs))
    back = REVERSE_OF.get(heading)
    if heading in legal:
        return heading
    if heading in LEFT_OF:
        left = LEFT_OF[heading]
        right = RIGHT_OF[heading]
        l_ok = left in legal and left != back
        r_ok = right in legal and right != back
        if l_ok and not r_ok:
            return left
        if r_ok and not l_ok:
            return right
    return None


def assess(obs: AIObservation) -> RiskAssessment:
    """観測からリスク評価を算出する"""
    st = obs.status
    hp_ratio = (st.hp_cur / st.hp_max) if st.hp_max > 0 else 1.0
    adj = 0
    escapes = 0
    pr, pc = obs.player_pos
    for m in obs.visible_monsters:
        mr, mc = m["pos"]
        if max(abs(mr - pr), abs(mc - pc)) <= 1:
            adj += 1
    for (dr, dc) in DIR_DELTA.values():
        t = obs._tile_cache.get((pr + dr, pc + dc)) if hasattr(obs, "_tile_cache") else None
        if t is not None and tile_passable(t):
            escapes += 1
    flags = obs.flags
    bad_state = bool(flags.get("confused") or flags.get("blind") or
                     flags.get("halluc") or flags.get("being_held") or
                     flags.get("bear_trap"))
    can_rest = (adj == 0 and not bad_state)
    should_descend = (obs.stairs_pos is not None and
                      (hp_ratio >= 1.0 or hunger_level(st.moves_left) == "ok") and
                      adj == 0)
    return RiskAssessment(
        hp_ratio=hp_ratio,
        hunger_level=hunger_level(st.moves_left),
        adjacent_enemies=adj,
        escape_routes=escapes,
        can_rest_safely=can_rest,
        should_descend=should_descend,
    )


def detect_stuck(pos_history: list) -> bool:
    """同一少数マスの往復（振動）を検知する"""
    if len(pos_history) < STUCK_WINDOW:
        return False
    return len(set(pos_history[-STUCK_WINDOW:])) <= STUCK_DISTINCT


def _diag_blocked(tile_fn, r1, c1, r2, c2) -> bool:
    """斜め移動の可否（本体 actions._can_move と同規則）。

    起点・終点いずれかがドア、または角マスが空虚なら不可。
    """
    t1 = tile_fn(r1, c1)
    t2 = tile_fn(r2, c2)
    if t1 is None or t2 is None:
        return True
    if (t1 & const.DOOR) or (t2 & const.DOOR):
        return True
    if not tile_fn(r1, c2) or not tile_fn(r2, c1):
        return True
    return False


def bfs_next_step(tile_fn, start: tuple, goals: set, blocked_extra=frozenset()):
    """BFSで goals のいずれかへの次の一手（方向文字）を返す。到達不能はNone。

    tile_fn(row, col) -> tile int または None（範囲外）
    """
    if start in goals:
        return None
    prev = {start: None}
    prev_dir = {}
    q = deque([start])
    found = None
    while q:
        cur = q.popleft()
        if cur in goals:
            found = cur
            break
        for d, (dr, dc) in DIR_DELTA.items():
            nxt = (cur[0] + dr, cur[1] + dc)
            if nxt in prev or nxt in blocked_extra:
                continue
            t = tile_fn(*nxt)
            if t is None or not tile_passable(t):
                continue
            if dr != 0 and dc != 0 and _diag_blocked(tile_fn, cur[0], cur[1], nxt[0], nxt[1]):
                continue
            prev[nxt] = cur
            prev_dir[nxt] = d
            q.append(nxt)
    if found is None:
        return None
    # startの次の一手を復元
    cur = found
    while prev[cur] != start:
        cur = prev[cur]
    return prev_dir[cur]


def _first_step_toward(obs: AIObservation, target: tuple):
    """targetへのBFS次の一手を obs のタイルキャッシュで求める"""
    cache = getattr(obs, "_tile_cache", {}) or {}
    rmax, cmax = getattr(obs, "_grid_size", (const.ROGUE_LINES, const.ROGUE_COLUMNS))

    def tile_fn(r, c):
        if not (const.MIN_ROW <= r < rmax and 0 <= c < cmax):
            return None
        return cache.get((r, c))

    return bfs_next_step(tile_fn, obs.player_pos, {target})


def _obs_tile_fn(obs: AIObservation):
    """観測のタイル関数（BFS・直線路共用）"""
    cache = getattr(obs, "_tile_cache", {}) or {}
    rmax, cmax = getattr(obs, "_grid_size", (const.ROGUE_LINES, const.ROGUE_COLUMNS))

    def tile_fn(r, c):
        if not (const.MIN_ROW <= r < rmax and 0 <= c < cmax):
            return None
        return cache.get((r, c))

    return tile_fn


def bfs_distance(obs: AIObservation, target: tuple):
    """BFS最短距離。到達不能はNone"""
    tile_fn = _obs_tile_fn(obs)
    start = tuple(obs.player_pos)
    goal = tuple(target)
    if start == goal:
        return 0
    prev = {start}
    q = deque([(start, 0)])
    while q:
        cur, dist = q.popleft()
        for d, (dr, dc) in DIR_DELTA.items():
            nxt = (cur[0] + dr, cur[1] + dc)
            if nxt in prev:
                continue
            t = tile_fn(*nxt)
            if t is None or not tile_passable(t):
                continue
            if dr != 0 and dc != 0 and _diag_blocked(tile_fn, cur[0], cur[1], nxt[0], nxt[1]):
                continue
            if nxt == goal:
                return dist + 1
            prev.add(nxt)
            q.append((nxt, dist + 1))
    return None


RUN_MIN_DIST = 3  # この距離以上かつ直線路なら高速移動（run）を使う


def straight_runway(obs: AIObservation, d: str, min_len: int = 3) -> bool:
    """方向dへmin_lenマス以上の直線路があるか"""
    if d not in DIR_DELTA:
        return False
    tile_fn = _obs_tile_fn(obs)
    pr, pc = tuple(obs.player_pos)
    dr, dc = DIR_DELTA[d]
    r, c = pr, pc
    for _ in range(min_len):
        nr, nc = r + dr, c + dc
        t = tile_fn(nr, nc)
        if t is None or not tile_passable(t):
            return False
        if dr != 0 and dc != 0 and _diag_blocked(tile_fn, r, c, nr, nc):
            return False
        r, c = nr, nc
    return True


def travel_action(obs: AIObservation, d: str, target=None):
    """移動行動の作成。長距離直線路は高速移動（run＝大文字キー）にする。

    runは「何かにぶつかるまで連続移動」し、LLM問い合わせ回数を減らす。
    """
    if target is not None:
        dist = bfs_distance(obs, tuple(target))
        if dist is not None and dist >= RUN_MIN_DIST and straight_runway(obs, d, 3):
            return AIAction(type="run", direction=d)
    elif straight_runway(obs, d, 2):
        return AIAction(type="run", direction=d)
    return AIAction(type="move", direction=d)


def route_hint(obs: AIObservation):
    """LLM用の経路ヒント (方向, 目的) を返す。なければ (None, None)。

    未開の扉が残っていれば最寄りを優先（餓死寸前を除く）。
    なければ階段到達可→階段、不可→到達可能な最寄り扉、の順。
    """
    unopened = getattr(obs, "unopened_doors", None) or []
    if unopened and obs.status.moves_left > HUNGER_URGENT:
        tgt = min(unopened, key=lambda p: _dist(obs.player_pos, tuple(p)))
        d = _first_step_toward(obs, tuple(tgt))
        if d:
            return d, "unopened door"
    if obs.stairs_pos:
        d = _first_step_toward(obs, obs.stairs_pos)
        if d:
            return d, "stairs"
    doors = sorted(getattr(obs, "visible_doors", []) or [],
                   key=lambda p: _dist(obs.player_pos, p))
    for door in doors[:6]:
        d = _first_step_toward(obs, door)
        if d:
            return d, "door"
    return None, None


def decide(obs: AIObservation, risk: RiskAssessment, memo, pos_history: list,
           heading=None, memory=None):
    """優先度表S0〜S8に従い (AIAction, reason) を返す。

    memo: IdentifyMemo（将来の装備・識別判断用。現行は参照のみ）
    pos_history: [(row, col), ...]（S8振動検知用）
    heading: 前手の移動方向（通路追従用。h/j/k/l/y/u/b/n）
    memory: ExplorationMemory（行き止まり探索用。None可）
    """
    st = obs.status
    flags = obs.flags

    # S1: 拘束・罠
    if flags.get("being_held") or flags.get("bear_trap"):
        d = _retreat_direction(obs)
        if d:
            return AIAction(type="move", direction=d), "捕縛状態から脱出"
        return AIAction(type="rest"), "捕縛中で待機"

    # S2: 隣接モンスター
    if risk.adjacent_enemies > 0:
        if (risk.hp_ratio >= HP_FIGHT_MIN and risk.adjacent_enemies == 1
                and not (flags.get("confused") or flags.get("blind") or flags.get("halluc"))):
            m = _adjacent_monster_dir(obs)
            return AIAction(type="fight", direction=m), "有利な1対1で攻撃"
        d = _retreat_direction(obs)
        if d:
            return AIAction(type="move", direction=d), "不利な戦闘から退避"
        return AIAction(type="rest"), "退路なし・回復に賭ける"

    # S8: 振動検知（戦闘より先に抜ける。無限往復の打ち切り）
    if detect_stuck(pos_history):
        d = _random_free_direction(obs, avoid=set(pos_history[-STUCK_WINDOW:]))
        if d:
            return AIAction(type="move", direction=d), "振動検知・ランダム脱出"

    # S4: 空腹（餓死回避のみ最優先。回復・ stair より上）
    if risk.hunger_level in ("weak", "faint"):
        act = _seek_food(obs)
        if act:
            return act
        # 食料が見えなければ降下を急ぐ
        if obs.stairs_pos:
            d = _first_step_toward(obs, obs.stairs_pos)
            if d:
                return travel_action(obs, d, obs.stairs_pos), "食料なし・降下を急ぐ"

    # S5: 拾得（敵隣接なし限り最優先。回復・降下より上）
    if _item_at_feet(obs):
        return AIAction(type="pickup"), "足元のアイテム拾得"

    # S5b: 通路追従（進行方向を記憶し、直進・左右で扉を探す）
    d = corridor_step(obs, heading)
    if d:
        return travel_action(obs, d), "通路を直進"

    # S5c: 行き止まりの隠し扉探索（最大10手。なければ打ち切り）
    if memory is not None:
        act = memory.deadend_action(obs, heading)
        if act is not None:
            n = memory.search_count_at(obs.player_pos)
            return act, "隠し扉を探索（%d/%d）" % (n, memory.SEARCH_BUDGET)

    if obs.visible_items:
        tgt = min(obs.visible_items, key=lambda it: _dist(obs.player_pos, it["pos"]))["pos"]
        d = _first_step_toward(obs, tgt)
        if d:
            return travel_action(obs, d, tgt), "アイテムへ移動"

    # S3: 回復待ち
    if st.hp_cur < st.hp_max and risk.can_rest_safely:
        return AIAction(type="rest"), "安全に回復待ち"

    # S4続き：hungry段階の食料探索
    if risk.hunger_level == "hungry":
        act = _seek_food(obs)
        if act:
            return act

    # S6: 階段へ（未開の扉が残っていれば扉優先。餓死寸除く）
    unopened = getattr(obs, "unopened_doors", None) or []
    if unopened and risk.hunger_level not in ("weak", "faint"):
        tgt = min(unopened, key=lambda p: _dist(obs.player_pos, tuple(p)))
        d = _first_step_toward(obs, tuple(tgt))
        if d:
            return travel_action(obs, d, tgt), "未開の扉へ"
    if risk.should_descend and obs.stairs_pos:
        d = _first_step_toward(obs, obs.stairs_pos)
        if d:
            return travel_action(obs, d, obs.stairs_pos), "階段へ移動"
        if obs.player_pos == obs.stairs_pos:
            return AIAction(type="descend"), "階段を降りる"

    # S7: 探索歩行（階段・未踏破へ）
    d = _explore_step(obs, pos_history)
    if d:
        return AIAction(type="move", direction=d), "未踏破方向へ探索"

    # S6最終：階段が見えていれば接近（HP満タンでなくても居座り回避）
    if obs.stairs_pos:
        d = _first_step_toward(obs, obs.stairs_pos)
        if d:
            return travel_action(obs, d, obs.stairs_pos), "階段へ接近"
        if obs.player_pos == obs.stairs_pos:
            return AIAction(type="descend"), "階段を降りる"

    return AIAction(type="rest"), "安全策で待機"


# ============================================================================
# 内部ヘルパー
# ============================================================================

def _dist(a: tuple, b: tuple) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _adjacent_monster_dir(obs: AIObservation):
    pr, pc = obs.player_pos
    for m in obs.visible_monsters:
        mr, mc = m["pos"]
        dr, dc = mr - pr, mc - pc
        if max(abs(dr), abs(dc)) == 1:
            for d, (ddr, ddc) in DIR_DELTA.items():
                if (ddr, ddc) == (dr, dc):
                    return d
    return "h"


def _retreat_direction(obs: AIObservation):
    """モンスターから遠ざかる移動可能方向（なければNone）"""
    pr, pc = obs.player_pos
    mons = [m["pos"] for m in obs.visible_monsters]
    cache = getattr(obs, "_tile_cache", {}) or {}
    best = None
    best_score = -1
    for d, (dr, dc) in DIR_DELTA.items():
        t = cache.get((pr + dr, pc + dc))
        if t is None or not tile_passable(t):
            continue
        score = min([_dist((pr + dr, pc + dc), m) for m in mons] or [99])
        if score > best_score:
            best_score = score
            best = d
    return best


def _random_free_direction(obs: AIObservation, avoid: set):
    import random
    pr, pc = obs.player_pos
    cache = getattr(obs, "_tile_cache", {}) or {}
    cands = []
    for d, (dr, dc) in DIR_DELTA.items():
        if (pr + dr, pc + dc) in avoid:
            continue
        t = cache.get((pr + dr, pc + dc))
        if t is not None and tile_passable(t):
            cands.append(d)
    if not cands:
        for d, (dr, dc) in DIR_DELTA.items():
            t = cache.get((pr + dr, pc + dc))
            if t is not None and tile_passable(t):
                cands.append(d)
    return random.choice(cands) if cands else None


def _item_at_feet(obs: AIObservation) -> bool:
    return any(it["pos"] == obs.player_pos for it in obs.visible_items)


def _seek_food(obs: AIObservation):
    """食料（':'）への移動。なければNone"""
    foods = [it for it in obs.visible_items if it.get("glyph") == ":"]
    if not foods:
        return None
    tgt = min(foods, key=lambda it: _dist(obs.player_pos, it["pos"]))["pos"]
    if tgt == obs.player_pos:
        return AIAction(type="pickup"), "食料を拾得"
    d = _first_step_toward(obs, tgt)
    if d:
        return travel_action(obs, d, tgt), "食料へ移動"
    return None


def _explore_step(obs: AIObservation, pos_history: list):
    """未訪問寄りの移動可能方向。履歴の逆方向を避ける"""
    pr, pc = obs.player_pos
    cache = getattr(obs, "_tile_cache", {}) or {}
    recent = set(pos_history[-4:]) if pos_history else set()
    cands = []
    for d, (dr, dc) in DIR_DELTA.items():
        nxt = (pr + dr, pc + dc)
        t = cache.get(nxt)
        if t is None or not tile_passable(t):
            continue
        penalty = 1 if nxt in recent else 0
        cands.append((penalty, d))
    if not cands:
        return None
    cands.sort()
    return cands[0][1]

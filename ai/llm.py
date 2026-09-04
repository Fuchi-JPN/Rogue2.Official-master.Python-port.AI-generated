"""
llm.py - OpenAI互換ChatClient＋LLMAgentPolicy（設計書 §6）

依存は標準urllibのみ。プロバイダー・モデル・endpointは設定で切替。
既定は OpenRouter + inception/mercury-2.5-preview。
攻略文面は strategy.py の定数から機械生成する（§6.5）。
"""
import json
import logging
import socket
import time
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

try:
    from . import strategy
    from . import actuator
    from .policies import ScriptedPolicy
    from .schemas import AIAction, AIObservation, IdentifyMemo
except ImportError:
    import strategy
    import actuator
    from policies import ScriptedPolicy
    from schemas import AIAction, AIObservation, IdentifyMemo


DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "inception/mercury-2.5-preview"


class LLMConnectionError(Exception):
    """LLM接続失敗（フォールバックせず終了するための専用例外）。

    Game.run() の except Exception で捕捉され、端末復帰後に
    エラーメッセージが表示される。str()は原因＋対処ヒントを含む。
    """


def _join_blocks(value) -> str:
    """ブロック配列・文字列を結合する"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for b in value:
            if isinstance(b, str):
                parts.append(b)
            elif isinstance(b, dict) and isinstance(b.get("text"), str):
                parts.append(b["text"])
        return "".join(parts)
    return ""


def extract_message_content(msg: dict):
    """message dictから本文を取り出す。文字列・ブロック配列・reasoning系に対応"""
    content = msg.get("content")
    if content is None:
        # 推論系モデルは本文をreasoning系フィールドに返すことがある
        content = msg.get("reasoning_content") or msg.get("reasoning") or msg.get("text")
    if isinstance(content, list):
        # ブロック配列形式（[{"type":"text","text":"..."}]等）の結合
        parts = []
        for b in content:
            if isinstance(b, str):
                parts.append(b)
            elif isinstance(b, dict) and isinstance(b.get("text"), str):
                parts.append(b["text"])
        content = "".join(parts)
    return content


def parse_llm_response(payload: dict):
    """応答payload→(content, reasoning, finish_reason)。HTTP済み・形状検証付き"""
    try:
        choice = payload["choices"][0]
        msg = choice["message"]
        content = extract_message_content(msg)
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("unexpected response shape: %s" % str(payload)[:300])
    reasoning = _join_blocks(msg.get("reasoning") or msg.get("reasoning_content"))
    return content, reasoning, choice.get("finish_reason")


def build_strategy_section() -> str:
    """§5.4正本から攻略文面を機械生成する（手書き重複コピーの禁止）"""
    return (
        "RULES OF SURVIVAL (follow strictly, in order):\n"
        "1. If a monster is adjacent: fight ONLY if HP >= %d%% of max and only one enemy.\n"
        "   If HP < %d%%, confused/blind/hallucinating/held/trapped, or 2+ enemies adjacent: RETREAT, do not fight.\n"
        "2. Rest is a LAST resort (healing happens over time while you move, and standing still wastes food). "
        "Even below half HP, keep exploring if no monster is visible. "
        "Rest only when hurt AND (enemies are visible OR there is nothing else to do).\n"
        "   Exception: if food counter moves_left <= %d, prioritize finding food over resting.\n"
        "   Exception 2: if items are visible and no enemy is adjacent, pick them up FIRST (move to them, pickup at feet) before resting or descending.\n"
        "3. Starvation kills: moves_left<=%d hungry (find food soon), <=%d weak (food first, ignore everything else),\n"
        "   <=%d faint, <=0 death. Eat RATION first, save FRUIT. Never linger when weak.\n"
        "4. Descend the stairs when HP is full (or food is comfortable) and no enemy guards the stairs.\n"
        "   Do not over-explore: staying too long starves you.\n"
        "5. Identify safely: equip/try ONE unknown item at a time, only at full HP in safety.\n"
        "   Cursed gear cannot be removed. Keep one emergency teleport/healing scroll or potion in reserve.\n"
    "6. Search for hidden traps/doors before stepping into unknown tiles.\n"
    "7. Move ONLY in the directions listed as Legal moves. Moving into a wall wastes the turn.\n"
    "8. Follow the Shortest-path hint for movement: it is the computed shortest route (stairs when reachable, otherwise the nearest door). "
    "If the room has no items and no enemies, head to the visible door (+) into the next room instead of wandering.\n"
    "9. Corridors: once on a passage (#), keep your Previous-move heading (same direction); "
    "at junctions take the left open branch (left-hand rule), never go back the way you came. "
    "While committed to a passage, ignore items/doors/stairs BEHIND you; only forward goals count. "
    "Make for the next + door. Do not reverse without reason (fighting/fleeing/adjacent pickup only).\n"
    "   After passing through a door (+), NEVER turn back into the room you came from: "
    "keep going through the passage until the next door, unless fighting, fleeing, or picking an adjacent item.\n"
    "10. Clear the visible area first: while visible Unopened doors remain, NEVER head for the stairs "
    "unless you are dying (HP below 15%% of max, or food counter weak/faint). "
    "When items are nearby (within 5), take them before doors. "
    "Open every door you can see, enter each room, then take the stairs.\n"
    "11. Dead ends: if you are on a passage/door with nowhere to go, use search (up to 10 times) "
    "to reveal hidden doors. The prompt shows Dead-end searches so far.\n"
    "12. Prefer run over move for travel of 3+ tiles in a straight clear line "
    "(passages, toward stairs/doors/items): run moves until something interesting and saves queries. "
    "Use move for 1-2 tiles, combat-adjacent steps, and precise positioning.\n"
    % (int(strategy.HP_FIGHT_MIN * 100), int(strategy.HP_FIGHT_MIN * 100),
           strategy.HUNGER_OK,
           strategy.HUNGER_OK, strategy.HUNGER_URGENT, strategy.HUNGER_FAINT)
    )


SYSTEM_PROMPT = (
    "You are an autonomous player of a classic roguelike (Rogue clone, Japanese UTF-8 version).\n"
    "Goal: survive as long as possible and descend to deeper floors. Dying ends the run.\n\n"
    + build_strategy_section() +
    "\nSYMBOL LEGEND (screen and lists use exactly these):\n"
    "Terrain: -=horizontal wall, |=vertical wall, .=room floor, #=passage, +=door, %=stairs, ^=trap.\n"
    "Items: *=gold, :=food, !=potion, ?=scroll, /=wand, )=weapon, ]=armor, ==ring, ,=amulet.\n"
    "Units: @=you, A-Z=monster (letter identifies the species).\n"
    "PASSABLE (you may step onto): . # + % and all item glyphs (* : ! ? / ) ] = ,).\n"
    "  Stairs % also need the descend action after stepping on. A-Z is NOT walkable: attack with fight.\n"
    "BLOCKED (never choose a move into these): - | space/void/unknown.\n"
    "^ (trap) is walkable but avoid it unless the hint tells you to.\n"
    "\nOUTPUT: exactly one JSON object, no other text:\n"
    '{"type":"move|run|rest|search|pickup|descend|ascend|quaff|read|eat|wield|wear|takeoff|puton|remove|drop|throw|zap|fight|inventory|help|noop",\n'
    ' "direction":"h|j|k|l|y|u|b|n (required for move/run/fight/throw/zap)",\n'
    ' "item_slot":"a-z (required for item actions)",\n'
    ' "reason":"short reason in Japanese, max 40 chars"}\n'
    "Directions: h=left j=down k=up l=right y=upper-left u=upper-right b=lower-left n=lower-right.\n"
    "FORBIDDEN: uppercase moves, Ctrl keys, Q (quit), S (save), o, !, a, F (fight-to-death). Never output them.\n"
    "One turn = one action. When in doubt, choose the safer action (rest/retreat/noop)."
)


def format_observation(obs: AIObservation, risk, memo: IdentifyMemo, history_summary: str,
                       heading=None) -> str:
    st = obs.status
    hp_pct = int(100 * risk.hp_ratio)
    mons = ", ".join("%s@%s" % (m["glyph"], m["pos"]) for m in obs.visible_monsters[:8]) or "none"
    items = ", ".join("%s@%s" % (it["glyph"], it["pos"]) for it in obs.visible_items[:8]) or "none"
    inv = ", ".join("%s:%s(x%s)%s" % (
        s["slot"], s["type"], s["qty"],
        "[" + ",".join(s["equip"]) + "]" if s["equip"] else "") for s in obs.inventory_summary) or "empty"
    legal = "".join(strategy.legal_moves(obs)) or "none (rest/search only)"
    adj = strategy.adjacent_enemy_dirs(obs)
    adj_txt = ", ".join("%s=%s" % (d, g) for d, g in sorted(adj.items())) or "none"
    unopened = getattr(obs, "unopened_doors", None) or []
    unopened_txt = ", ".join(str(tuple(p)) for p in unopened[:12]) or "none (visible area cleared)"
    heading_txt = ("none (no previous move)"
                   if not heading else
                   "%s (you are heading %s)" % (heading, strategy.COMPASS.get(heading, "?")))
    hint_dir, hint_target = strategy.route_hint(obs, heading)
    if hint_dir and hint_target == "stairs":
        hint = "move %s toward the stairs (shortest path)" % hint_dir
    elif hint_dir and hint_target == "nearby item":
        hint = "move %s toward the nearby item first (items beat doors)" % hint_dir
    elif hint_dir:
        hint = "move %s toward the nearest passage/door ahead (shortest path, keep forward)" % hint_dir
    else:
        hint = "none"
    return (
        "Turn %d, Dungeon level %d. Survival risk: HP %d/%d (%d%%), "
        "food counter %d (%s), adjacent enemies %d, escape routes %d, safe-to-rest=%s.\n"
        "Position %s, room %s. Stairs: %s. Doors: %s.\n"
        "Unopened doors (visible, rooms not yet entered; clear them before descending): %s.\n"
        "Dead-end searches so far at your tile (search up to 10 if stuck): %d.\n"
        "Previous move (your heading): %s.\n"
        "Legal moves (passable tiles only, never bump walls): %s.\n"
        "Shortest-path hint (follow it for movement unless fighting/fleeing): %s.\n"
        "Visible monsters: %s. Visible items: %s.\n"
        "Adjacent enemies by fight direction (use exactly this): %s.\n"
        "Status effects: %s. Message: \"%s\".\n"
        "Inventory: %s. Identified: potions %s, scrolls %s.\n"
        "Recent history: %s.\n"
        "%s"
        "Decide the next single action as JSON."
        % (obs.turn, st.level, st.hp_cur, st.hp_max, hp_pct,
           st.moves_left, risk.hunger_level, risk.adjacent_enemies,
           risk.escape_routes, risk.can_rest_safely,
           obs.player_pos, obs.room_id, obs.stairs_pos,
           getattr(obs, "visible_doors", None) or "unseen",
           unopened_txt,
           getattr(obs, "search_count", 0),
           heading_txt,
           legal, hint,
           mons, items, adj_txt, obs.flags or "none", obs.message or "",
           inv, memo.potion or "{}", memo.scroll or "{}",
           history_summary or "none", _screen_block(obs))
    )


def _screen_block(obs: AIObservation) -> str:
    """画面ダンプ全文の添付部。なしの場合は空文字"""
    raw = getattr(obs, "raw_screen", None)
    if not raw:
        return ""
    lines = [ln if len(ln) <= 80 else ln[:80] for ln in raw[:24]]
    return (
        "Full screen dump (80x24, row0=message, last row=status, "
        "@=you, +=door, %=stairs, A-Z=monsters, see legend in rules):\n"
        "```\n" + "\n".join(lines) + "\n```\n"
        "The structured fields above are authoritative; use the dump for spatial relations.\n"
    )


def classify_error(e: Exception) -> str:
    """接続失敗の原因を人間可読の短文に分類する（表示・ログ用）"""
    msg = str(e)
    # タイムアウト（urllibはTimeoutError/socket.timeout、または文言で検出）
    if isinstance(e, (TimeoutError, socket.timeout)) or "timed out" in msg:
        return "タイムアウト（サーバ無応答・回線遅延）"
    code = getattr(e, "code", None)
    if isinstance(code, int):
        if code == 401:
            return "401認証失敗（APIキー無効・期限切れ・provider不一致）"
        if code == 402:
            return "402残高不足・支払い要確認"
        if code == 404:
            return "404（endpoint・モデル名の綴りを確認）"
        if code == 429:
            return "429レート制限（時間をおいて再試行）"
        if 500 <= code <= 599:
            return "サーバエラーHTTP%d（一時的障害の可能性）" % code
        return "HTTP%dエラー" % code
    low = msg.lower()
    if "name or service not known" in low or "nodename nor servname" in low or "name resolution" in low:
        return "DNS解決失敗（endpointのホスト名・回線を確認）"
    if "connection refused" in low:
        return "接続拒否（endpointの向き先・プロキシを確認）"
    if "ssl" in low or "certificate" in low:
        return "SSL/証明書エラー（時刻ずれ・プロキシ干渉の可能性）"
    if "request failed" in low or "urlopen" in low:
        return "接続失敗（回線・プロキシ・endpointを確認）"
    if "unexpected response shape" in low:
        return "応答形式異常（providerの応答仕様を確認）"
    if "not an action object" in low or "failed validation" in low:
        return "行動形式不正（モデル応答がJSON行動になっていない）"
    if "expecting value" in low or "json" in low or "delimiter" in low:
        return "応答がJSONでない（モデル応答の乱れ）"
    if "invalid control character" in low or "unterminated string" in low:
        return "応答JSONに制御文字混入（モデル応答の乱れ。自動補正して継続）"
    if "finish_reason=length" in low:
        return "出力がmax_tokensで打切り（--ai-max-tokensを増やす）"
    if "empty content" in low or "has no attribute 'strip'" in low:
        return "応答本文が空（モデルが空応答・reasoningのみ返却。モデル名・可用性を確認）"
    return "接続失敗（%s）" % (msg[:80] or type(e).__name__)


class ChatClient:
    """OpenAI互換Chat Completionsクライアント（urllibのみ）"""

    def __init__(self, endpoint=DEFAULT_ENDPOINT, api_key="",
                 referer="https://localhost/rogue2", title="rogue2-ai-agent",
                 timeout=20.0, model=DEFAULT_MODEL, max_tokens=4096):
        self.endpoint = endpoint
        self.api_key = api_key or ""
        self.referer = referer
        self.title = title
        self.timeout = timeout
        self.model = model
        self.max_tokens = max_tokens

    def complete(self, system: str, user: str, temperature=0.2,
                 max_tokens=None) -> str:
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint, data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer %s" % self.api_key,
                "HTTP-Referer": self.referer,
                "X-Title": self.title,
            },
            method="POST",
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                payload = json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # classify_errorが原因判別できるようHTTPコードを保持する
            err = RuntimeError("HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]))
            err.code = e.code
            raise err
        except Exception as e:
            raise RuntimeError("request failed: %s" % e)
        latency_ms = int((time.time() - t0) * 1000)
        content, reasoning, finish = parse_llm_response(payload)
        if content is None or (isinstance(content, str) and not content.strip()):
            # 原因究明用に原文の形状をログへ（curl再現時の突合材料）
            try:
                logger.debug("empty LLM response: choice=%s", json.dumps(payload["choices"][0])[:2000])
            except Exception:
                pass
            raise RuntimeError(
                "empty content (finish_reason=%s, msg_keys=%s): モデルが空応答を返した。 "
                "--ai-modelの綴り・モデル可用性を確認"
                % (finish, sorted(payload["choices"][0]["message"].keys())
                   if isinstance(payload["choices"][0].get("message"), dict) else "?"))
        return content, latency_ms, reasoning


def _loads_action_json(t: str):
    """行動JSONの寛容な解釈。順に試す。

    1. 厳密JSON、2. 制御文字許容（strict=False）、
    3. 先頭余文つきの場合に最初の {...} を切り出して再試行。
    """
    try:
        return json.loads(t)
    except ValueError:
        pass
    try:
        return json.loads(t, strict=False)
    except ValueError:
        pass
    s, e = t.find("{"), t.rfind("}")
    if 0 <= s < e:
        return json.loads(t[s:e + 1], strict=False)
    raise ValueError("action JSON parse failed: %s" % t[:200])


def parse_action(text: str):
    """LLM応答→AIAction。フェンス除去→JSON→検証。不正は例外"""
    if not isinstance(text, str):
        raise ValueError("empty content: 応答本文が文字列でない（None等）")
    t = text.strip()
    if t.startswith("```"):
        # ```json ... ``` を剥がす
        lines = t.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        t = "\n".join(lines).strip()
    obj = _loads_action_json(t)
    if not isinstance(obj, dict) or "type" not in obj:
        raise ValueError("not an action object")
    act = AIAction(
        type=str(obj.get("type", "noop")),
        direction=obj.get("direction"),
        item_slot=obj.get("item_slot"),
        raw_keys=obj.get("raw_keys"),
    )
    if not actuator.validate(act):
        raise ValueError("action failed validation: %s" % t[:200])
    reason = str(obj.get("reason", ""))[:40]
    return act, reason


class LLMAgentPolicy:
    """LLM Policy。既定は失敗時フォールバックせず終了する。

    fallback_enabled=True（--ai-llm-fallback）の場合のみ従来の
    Scriptedフォールバックを行う。
    """
    name = "llm"

    def __init__(self, client: ChatClient, memo=None, fallback=None,
                 max_consecutive_failures: int = 5,
                 fallback_enabled: bool = False,
                 max_parse_retries: int = 2,
                 max_request_retries: int = 3,
                 retry_backoff: float = 2.0):
        self.client = client
        self.memo = memo if memo is not None else IdentifyMemo()
        self.fallback = fallback
        self.failures = 0
        self.max_consecutive_failures = max_consecutive_failures
        self.fallback_enabled = fallback_enabled
        self.max_parse_retries = max_parse_retries
        self.max_request_retries = max_request_retries
        self.retry_backoff = retry_backoff
        self.pinned_scripted = False
        self.pos_history: list = []
        self.last_latency_ms = 0
        self.last_fallback = False
        self.last_error = ""  # 直近の接続失敗原因（classify_errorの結果）
        self.last_reasoning = ""  # 直近の推論文（ティッカー表示用）
        self.last_system = ""  # 直近のsystem prompt（全文記録用）
        self.last_user = ""  # 直近のuser prompt（全文記録用）
        self.last_raw = ""  # 直近の生応答（全文記録用）
        self.heading = None  # 前手の移動方向（driverが更新）
        self.memory = strategy.ExplorationMemory()

    def _complete_with_retry(self, user: str):
        """complete＋parse retry。通信失敗・parse失敗とも再試行する。

        一過性の回線断・サーバ側リセット・JSON崩れは再試行で回復する
        ことが多い。通信は指数バックオフ付き。使い果たしたら最後の
        例外を送出する。
        """
        last_exc = None
        attempts = 1 + max(max(0, self.max_request_retries),
                           max(0, self.max_parse_retries))
        for i in range(attempts):
            try:
                text, latency, reasoning = self.client.complete(SYSTEM_PROMPT, user)
            except Exception as e:
                last_exc = e
                self.last_raw = ""
                if i < attempts - 1:
                    time.sleep(self.retry_backoff * (2 ** i))
                continue
            try:
                parse_action(text)
            except Exception as e:
                # parse失敗は即座に新しい応答を取り直す（sleepなし）
                last_exc = e
                self.last_raw = text
                continue
            return text, latency, reasoning
        raise last_exc

    def _scripted(self, obs, history):
        pol = self.fallback
        if pol is None:
            pol = ScriptedPolicy(memo=self.memo)
            pol.pos_history = self.pos_history
            self.fallback = pol
        act, reason = pol.decide(obs, history)
        self.pos_history = pol.pos_history
        return act, reason

    def decide(self, obs: AIObservation, history: list):
        if self.pinned_scripted:
            act, reason = self._scripted(obs, history)
            self.last_fallback = True
            return act, reason + "（scripted固定）"
        self.memory.update(obs)
        obs.unopened_doors = self.memory.unopened_visible(obs)
        obs.search_count = self.memory.search_count_at(obs.player_pos)
        risk = strategy.assess(obs)
        hist = "; ".join(str(h) for h in history[-5:])
        user = format_observation(obs, risk, self.memo, hist, heading=self.heading)
        self.last_system = SYSTEM_PROMPT
        self.last_user = user
        self.last_raw = ""
        try:
            text, latency, reasoning = self._complete_with_retry(user)
            self.last_raw = text
            self.last_latency_ms = latency
            self.last_reasoning = reasoning or ""
            act, reason = parse_action(text)
            self.failures = 0
            self.last_fallback = False
            self.last_error = ""
        except Exception as e:
            self.failures += 1
            cause = classify_error(e)
            self.last_error = cause
            if not self.fallback_enabled:
                raise LLMConnectionError(
                    "LLM接続失敗[%s] model=%s endpoint=%s → "
                    "APIキー（OPENROUTER_API_KEY等）・--ai-model・--ai-endpointを確認してください"
                    % (cause, self.client.model, self.client.endpoint))
            if self.failures >= self.max_consecutive_failures:
                self.pinned_scripted = True
            act, reason = self._scripted(obs, history)
            self.last_fallback = True
            reason = "LLM接続失敗[%s]→scripted継続" % cause
            return act, reason
        self.pos_history.append(tuple(obs.player_pos))
        if len(self.pos_history) > 64:
            self.pos_history = self.pos_history[-64:]
        return act, reason

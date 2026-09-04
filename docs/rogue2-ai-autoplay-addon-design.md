# Rogue2 Python移植版 AI自律プレイ機能 — 追加機能設計書

| 項目 | 内容 |
|---|---|
| バージョン | v1.1（初版＋攻略ロジック追加） |
| 作成日 | 2026-09-04 |
| 親仕様 | `python/docs/rougeclone2-ai-agent-spec.md` v0.1（外部PTYハーネス案） |
| 位置付け | 本体（`python/`）にAI自律プレイ機能を **内蔵アドオン** として付加するための設計書。本書を実装の単一真実源とする |
| 基本方針 | 操作は全自動。プレイ過程は人間が実画面（curses画面）上で観察できる。プロバイダー・モデルは任意設定可、デフォルトは OpenRouter `inception/mercury-2.5-preview` |

---

## 1. 目的・スコープ

### 1.1 目的

1. **自動プレイ機能の付加**：人間がキーを押さなくてもAIが `Game._play_level` のメインループを駆動し、移動→拾得→戦闘→階段降下の基本ループを自律的に回せるようにする。
2. **人間による実画面モニター**：curses画面は従来通り描画し続け、人間はその画面を見てAIの挙動・不具合を観察できる。一時停止・ステップ実行・速度変更・介入を可能にする。
3. **本体デバッグへの還流**：AIの操作ログ・状態遷移・判断根拠・クラッシュ情報を `rogue_debug.log`／専用AIログに残し、v2.1デバッグ計画の一次資料にする。

### 1.2 親仕様との関係（重要）

親仕様は **本体無改変・外部プロセス（PTY/tmux）＋画面パース** を前提とする（L0〜L6構成、11章GameStateは画面由来）。

本追加機能は方針を変え、**本体と同一プロセス内のアドオン** とする。理由：

| 観点 | 親仕様（外部ハーネス） | 本設計（内蔵アドオン） |
|---|---|---|
| 観測 | 80×24画面テキストをパースしてGameState復元。全角幅・More待ち文字列等の壊れやすさあり（7章リスク表） | 内部オブジェクト（`Player`／`DungeonLevel`／`GameState`／`Message`）から直接スナップショット取得。パース不要で精度100%。画面パーサー層（L2/L3）は不要 |
| 操作 | PTYへキーストローク送信 | `Game._get_input()` の入力源を差し替え（後述）。キー対応表は親仕様付録Aを流用 |
| 監視 | tmux attachで観察 | curses実画面をそのまま描画＋AI状態オーバーレイ。人間は同じ端末で観察 |
| 改変量 | ゼロ（別リポジトリ級） | 最小（入力源の戦略化＋CLI追加＋新規 `ai_` モジュール群）。ゲームロジック・描画ロジックは触らない |
| 両立性 | 将来の外部fuzzと併用可 | 本アドオンのログ形式を親仕様14章（ダンプ・差分・リプレイ）と互換にし、外部ハーネス導入時も流用可能にする |

親仕様の以下は本設計でもそのまま採用する：Policy抽象（10.5）、リフレックス概念（10.4）、GameState/Actionスキーマ思想（11章）、ロギング・リプレイ・差分チェック思想（10.6/14章）、フェーズ分割思想（15章）。

### 1.3 非スコープ

- ゲームバランス調整・難易度変更・新アイテム等のゲーム内容の変更。
- 勝率最大化のための高度な攻略AI（当面は「最後まで壊さず回る」ことを優先）。
- 外部PTY/tmuxハーネスの実装（将来の任意タスクとして残す）。
- 複数セッション並列実行（単一セッションの安定を先に確保）。

---

## 2. 全体アーキテクチャ

```
┌──────────────────────────────────────────────────────────┐
│ 人間の目（実画面モニター）                                  │
│  curses 80x24: マップ＋メッセージ＋ステータス（従来通り）    │
│  ＋ AIオーバーレイ行（policy/thought/turn/speed/paused）    │
└──────────────────────────▲───────────────────────────────┘
                           │ 描画（既存 Display/Message/Stats）
┌──────────────────────────┴───────────────────────────────┐
│ Game（既存、最小改変）                                     │
│  _play_level ループ → _get_input() → 分岐処理（既存）       │
│       ▲                                                    │
│       │ 入力源の差し替え（InputProvider戦略）                │
│ ┌─────┴──────────────────────────────────────────────┐    │
│ │ AIドライバ（新規 ai/ パッケージ）                     │    │
│ │  Observer → Policy → Actuator → Monitor/Logger      │    │
│ └────────────────────────────────────────────────────┘    │
│  人間介入キー（pause/step/speed/quit）は _get_input 内で横取り │
└──────────────────────────────────────────────────────────┘
```

### 2.1 設計原則

1. **ゲームロジック無改変**：`one_move_rogue`／戦闘／生成／描画には手を入れない。変えるのは入力の出所と起動時配線のみ。
2. **観測は内部状態から**：画面OCRをしない。`player`／`dungeon`／`GameState`／`Message`から観測を組み立てる。
3. **人間が主導権を奪える**：いつでも一時停止・1手進行・速度変更・AI解除（手動復帰）・安全終了ができる。
4. **LLMなしでも回る**：APIキーなし・オフラインではルールベースPolicyで動作する。LLMは差し替え可能なPolicyの一種。
5. **すべて記録する**：ターン毎の観測・思考・行動・結果・例外をJSONLに残し、リプレイ可能にする。

---

## 3. 観測（Observer）— 画面パース不要の内部スナップショット

### 3.1 観測源（既存資産の流用）

| 観測項目 | 取得源（現行コード） | 備考 |
|---|---|---|
| 自機位置・HP・空腹・装備・所持金・経験 | `Game.player`（`entities.Player`） | 直接参照。コピーしてスナップショット化 |
| 床・壁・ドア・通路・罠・階段タイル | `DungeonManager.get_current_level().dungeon`（2次元int配列）＋`const.*`ビット | `FLOOR/TUNNEL/DOOR/STAIRS/TRAP/HIDDEN/MONSTER/OBJECT` で解釈 |
| 部屋・ドア・罠リスト | `DungeonLevel.rooms/doors/traps` | `cur_room` は `GameState.cur_room` |
| モンスター・アイテム位置 | `DungeonLevel.monsters/level_monsters/level_objects` | `trail_char` 等も含め取得可 |
| メッセージ・空腹文字 | `display.Message.msg_line`、`GameState.hunger_str` | More待ち等の特殊状態は後述 |
| 階数・最大到達階 | `DungeonManager.current_level`、`GameState.max_level` | 内部値なのでパース誤りなし |
| グローバル状態 | `game_state.GameState`（halluc/blind/confused/levitate/haste_self/being_held/bear_trap等） | v2.1で集約済みの単一真実源 |

### 3.2 AI観測スキーマ

親仕様11章を内蔵版に焼き直す。`raw_screen` はモニター・デバッグ用に残すが、意思決定の主入力は構造化フィールドとする。

```python
@dataclass
class AIStatus:
    level: int; gold: int
    hp_cur: int; hp_max: int
    str_cur: int; str_max: int
    armor_class: int
    exp_level: int; exp_points: int
    moves_left: int               # 空腹カウンタ
    hunger: str                   # GameState.hunger_str（"" / 空腹 / 飢餓 / 瀕死）

@dataclass
class AIObservation:
    turn: int
    player_pos: tuple[int, int]
    status: AIStatus
    # 視界：自機中心の切り出し（デフォルト半径10）＋全マップ要約
    local_view: list[str]         # 可視範囲の文字切り出し（@ . # + - | % ^ *等）
    room_id: int                  # GameState.cur_room（PASSAGE含む）
    visible_monsters: list[dict]  # [{pos, char, hp_known, flags}]
    visible_items: list[dict]     # [{pos, glyph, kind_hint}]
    stairs_pos: tuple[int,int] | None
    message: str | None           # 最新メッセージ行
    mode: str                     # normal | level_transition | dead | victory | need_confirm
    flags: dict                   # {blind, halluc, confused, levitate, being_held, bear_trap, ...}
    inventory_summary: list[dict] # [{slot, type, kind, qty, equip}]
    raw_screen: list[str] | None  # 80x24（ログ・LLM任意添付用、通常は省略可）
```

- `local_view` の文字化は `Display.get_dungeon_char`／`get_mask_char` と同一規則を使い、人間の見た目とAIの見た目を一致させる。
- `mode=need_confirm` は「AIだけでは決めない方がよい確認」（例：Q終了確認・セーブ確認）に使う。デフォルトは確認を出さない安全側行動を選ぶ。

### 3.3 リフレックス相当の扱い（内蔵版の簡略化）

親仕様10.4のリフレックス層は、外部ハーネスでは「More待ち自動送り」が必須だった。内蔵版では：

- `Message.message(..., intrpt)` の継続待ちは内部API経由のため、AIは待ち状態を直接検知できる。自動送りは行わず、観測の `message` としてPolicyに渡す。
- y/n確認・方向選択・持ち物選択は `Game._play_level` の各分岐（`_quaff/_read_scroll/_throw/_zapp` 等の対話）が担う。AI Actuatorは **確認を発生させない行動を優先** し、確認が発生した場合は中断して次ターンに回す（無限待ち防止）。

---

## 4. 行動（Actuator）— 意味行動→キーの一対一変換

### 4.1 行動スキーマ

```python
@dataclass
class AIAction:
    type: str
    # "move" | "rest" | "search" | "pickup" | "descend" | "ascend"
    # | "quaff" | "read" | "eat" | "wield" | "wear" | "takeoff"
    # | "puton" | "remove" | "drop" | "throw" | "zap" | "fight"
    # | "help" | "inventory" | "wait_confirm" | "noop"
    direction: str | None = None   # 8方向（h j k l y u b n）
    item_slot: str | None = None   # インベントリ文字（a-z）
    raw_keys: str | None = None    # エスケープハッチ（上記で表せない場合のみ）
```

### 4.2 キー対応表（現行 `Game._play_level`／`_get_input` 実装準拠）

| AIAction | 送出キー | 本体側分岐 |
|---|---|---|
| move(hjkl八方向) | `hjklbyun` の1文字 | `movement.is_direction`→`one_move_rogue` |
| 連続移動が必要な場合 | 使わない（1手ずつ送る。安全のため大文字・Ctrl系は送出禁止） | — |
| rest/search/pickup | `.`／`s`／`,` | `movement.rest/search/pick_up` |
| descend/ascend | `>`／`<` | 階段分岐 |
| quaff/read/eat | `q`／`r`／`e`（対話が発生したら中断） | `_quaff/_read_scroll/_eat` |
| wield/wear/takeoff/puton/remove/drop/throw/zap | `w/W/T/P/R/d/t/z`（対話発生時は中断） | 各 `_wield` 等 |
| fight | `f`（`F`は送出禁止：無限ループ化防止） | `_fight(False)` |
| inventory/help | `i`／`?`（画面復帰を確認して閉じる） | inventory分岐 |
| noop | 何も送らない（1ターン空転） | — |

禁止キー：`Q`（終了）・`S`（セーブ）・`o`（未実装）・`!`（シェル）・大文字移動・Ctrl系・`a`（リプレイ）。AIは送出してはならない（Actuatorでバリデーションし、違反はnoop化＋ログ）。

方向文字は `h=左 j=下 k=上 l=右 y=左上 u=右上 b=左下 n=右下`（v2.1で `u/b` 修正済みを確認済み）。

---

## 5. Policy（意思決定）— 差し替え可能な2種＋1抽象

```python
class Policy:
    name: str
    def decide(self, obs: AIObservation, history: list[dict]) -> tuple[AIAction, str]:
        """(行動, 思考メモ) を返す。思考メモはログ・モニター表示用"""
        ...
```

### 5.1 ScriptedPolicy（デフォルト・オフライン可）

LLMなしで回るルールベース。優先度順：

1. 隣接モンスターがいる → `fight`（HPが最大の3割未満なら `rest` で回復を優先）。
2. 足元にアイテム／金塊がある → `pickup`。
3. HPが減っていて敵が隣接していない → `rest`（v2.1のheal寿命修正を前提に回復待ち）。
4. 階段が見えている → 階段へ最短歩行（BFS、壁・罠回避は `is_passable` 準拠）。
5. 未踏破方向へ探索歩行（`search` を挟みつつ壁沿い移動）。
6. 詰み・振動検知（同一4マス往復） → ランダム方向へ脱出。
7. 食料が尽きかけ（`moves_left` 僅少）→ 食料探索を優先（なければ降下を急ぐ）。

ScriptedPolicyは **ハーネス自体のスモークテスト**（親仕様Phase 4相当）も兼ねる。

### 5.2 LLMAgentPolicy（本命）

- 観測をコンパクトなテキストプロンプトに整形し、OpenAI互換Chat Completions APIに投げ、JSONで行動を受け取る。
- プロンプトは「状態→選択肢→制約（禁止キー・1手のみ・JSONのみ）」の固定枠＋直近N手の要約＋識別メモ（薬・巻物の効果対応表）。
- 応答不正・タイムアウト・通信失敗時はScriptedPolicyにフォールバック（1手分）。連続失敗が閾値超えで自動的にScriptedに固定＋警告表示。
- 長期記憶は持ち越さない（1セッション内のみ）。肥大化防止のため履歴は直近20手＋要約200字以内。

### 5.3 識別メモ（両Policy共通）

```python
@dataclass
class IdentifyMemo:
    potion: dict[str, str]   # slot -> 効果（使用後に記録）
    scroll: dict[str, str]
```

巻物・薬は1度使えば判明する仕様のため、単純なslot→効果マップで足りる（親仕様13章）。

### 5.4 攻略ロジック — 死なずに奥の階層まで進める確率を高める戦略

本機能はテストプレイ用途だが、操作のランダム打ちでは深層到達も異常検出もできない。そこで両Policy共通の **攻略ロジック（生存戦略）** を `strategy.py` に単一実装し、ScriptedPolicyは直接実行、LLMAgentPolicyはプロンプトとして注入する（§6.5）。方針は「稼ぐより死なない」。数値の根拠は現行実装：空腹 `HUNGRY=300/WEAK=150/FAINT=20/STARVE=0`（`const.py`）、初期 `moves_left=1250`（`entities.py`）、自然回復はターン経過で徐々に進行（`actions.Movement._heal`、v2.1で寿命修正済み）。

#### 5.4.1 五本柱

1. **HP管理（回復待ちの徹底）**：敵が隣接していない安全時は、HPが最大でなければ `rest` で回復を待つ（自然回復は無敵の無料回復）。HPが最大の3割未満では戦闘・探索を停止し回復専念。瀕死（1〜2撃で即死し得る水準）では回復薬（判明済みHEALING/EXTRA_HEALING）の使用を検討し、なければ階段へ退避。
2. **空腹管理（餓死は最大の死因）**：`moves_left` が `HUNGRY(300)` を切ったら食料探索を最優先に格上げし、`WEAK(150)` を切ったら降下より食料確保を優先する。`eat` はRATION優先・FRUIT温存（FRUITは60%側の安定栄養）。腐食・栄養の取り違えに注意（v2.1で文言ID修正済み）。
3. **戦闘選択（勝てる相手とだけ戦う）**：隣接1体かつHP余裕ありのときのみ `fight`。複数隣接・HP3割未満・状態異常中（confused/blind/halluc/held/bear_trap）は戦わず退避。通路・ドアの隘路で1対1に持ち込む。`F`（死ぬまで戦う）は送出禁止。
4. **降下判断（欲張らない）**：現在階の未踏破が残っていても、(a) HPが減っている、(b) 食料が心許ない、`WEAK` 接近時、(c) 識別が進んでいない消耗状態では深追いせず階段降下を優先する。逆にHP満タン・食料余裕あり・階段周辺に敵影なしのときは降下する（居座りは空腹死を招く）。
5. **装備・識別・非常手段の温存**：拾得品は即 `wear/wield/puton` せず、安全時に1つずつ装備して呪い・効果を確認する（呪い装備は外せない）。未識別の薬・巻物はHP満タン・安全時に1つずつ試す（識別メモに記録）。テレポート・睡眠・回復系の巻物／薬は非常用に1つ残す。罠（`^`、通常隠蔽）は `search` で事前発見し、踏んだら慌てず状況確認。

#### 5.4.2 意思決定の優先度表（毎手、上から評価）

| 優先度 | 条件 | 行動 |
|---|---|---|
| S0 | 死亡・勝利・階層遷移中 | noop（運転・記録のみ） |
| S1 | 罠拘束・掴み状態（being_held/bear_trap） | 脱出不能なら待機・回復、可能なら脱出方向へ移動 |
| S2 | 隣接モンスターあり | HP余裕あり→`fight`／HP3割未満→退避移動／複数隣接→退避移動 |
| S8 | 振動・停滞検知 | ランダム脱出（履歴の逆方向を避ける） |
| S4 | `moves_left <= 150`（weak以下） | 食料探索（`:`・未探索部屋へ）。見えなければ降下を急ぐ |
| S5 | 可視アイテムあり（敵隣接なし限り） | 足元→`pickup`、離席→最短接近。回復・降下より優先 |
| S3 | HPが最大でなく安全（隣接敵なし） | `rest`（回復待ち。空腹S4と競合時は空腹優先） |
| S4 | `moves_left <= 300`（空腹接近） | 食料探索。`<=150` は上記S4に含まれる |
| S6 | 階段可視＋（HP満タンまたは食料余裕） | 階段へBFS移動→`descend` |
| S7 | 未踏破・未探索 | `search` を挟みつつ壁沿い・BFS探索 |

S3とS4の競合（回復したいが腹が減る）は空腹優先とする。回復待ちの1手と空腹の1手はどちらも命に直結するため、残量が少ない方を優先する。

#### 5.4.3 リスク評価フィールド（Observerが算出、両Policyが利用）

```python
@dataclass
class RiskAssessment:
    hp_ratio: float          # hp_cur / hp_max
    hunger_level: str        # ok(>300) / hungry(<=300) / weak(<=150) / faint(<=20)
    adjacent_enemies: int    # 隣接8マスのモンスター数
    escape_routes: int       # 移動可能な隣接マス数（is_passable準拠）
    can_rest_safely: bool    # 隣接敵なし and 状態異常なし
    should_descend: bool     # S6条件の事前計算
```

`RiskAssessment` は `strategy.py::assess(obs)` で算出し、ScriptedPolicyは分岐に直接使用、LLMには観測テキストの一部として渡す（§6.5）。判定ロジックの二重実装を防ぐため、閾値（3割・300/150等）は `strategy.py` の定数に集約する。

---

## 6. LLMプロバイダー抽象 — 任意設定可、既定はOpenRouter mercury

### 6.1 要件

- プロバイダー・モデル・endpoint・APIキーをすべて設定可能にする。コード改変なしに切替できる。
- 既定は OpenRouter の OpenAI互換endpoint `https://openrouter.ai/api/v1/chat/completions`、モデル `inception/mercury-2.5-preview`。
- 依存追加なし（標準 `urllib` のみ）。`requests`/`openai` パッケージは要求しない。
- OpenRouter必須ヘッダ（`HTTP-Referer`、`X-Title`）を送出できる。

### 6.2 設定項目（CLI＞環境変数＞既定値の優先順）

| 設定 | CLI | 環境変数 | 既定値 |
|---|---|---|---|
| プロバイダー種別 | `--ai-provider` | `ROGUE_AI_PROVIDER` | `openrouter`（`openai_compat`／`scripted` も可） |
| モデル | `--ai-model` | `ROGUE_AI_MODEL` | `inception/mercury-2.5-preview` |
| endpoint | `--ai-endpoint` | `ROGUE_AI_ENDPOINT`（または `OPENAI_BASE_URL`） | `https://openrouter.ai/api/v1/chat/completions` |
| APIキー | —（セキュリティのためCLI不可） | `OPENROUTER_API_KEY`（または `OPENAI_API_KEY`） | なし（未設定時はScriptedに自動フォールバック） |
| 最大ターン | `--ai-max-turns` | `ROGUE_AI_MAX_TURNS` | `500` |
| 1手の待ちms | `--ai-delay-ms` | `ROGUE_AI_DELAY_MS` | `120`（人間が目で追える速さ） |
| LLMタイムアウト秒 | `--ai-timeout` | `ROGUE_AI_TIMEOUT` | `20` |
| LLM max_tokens | `--ai-max-tokens` | `ROGUE_AI_MAX_TOKENS` | `4096`（推論系はreasoningで消費するため多め。`length`打切り時は増加） |
| ログ dc | `--ai-log` | `ROGUE_AI_LOG` | `ai_session.jsonl` |
| ヘッドレス | `--ai-headless` | `ROGUE_AI_HEADLESS` | off（既定は実画面あり） |

### 6.3 クライアント仕様

```python
@dataclass
class ChatRequest:
    model: str
    messages: list[dict]   # [{role, content}]
    temperature: float = 0.2
    max_tokens: int = 512
    response_format: dict | None = None  # {"type": "json_object"}（相手が対応時のみ）

class ChatClient:
    def __init__(self, endpoint, api_key, referer, title, timeout): ...
    def complete(self, req: ChatRequest) -> str: ...  # 応答本文（choices[0].message.content）
```

- リクエストは `POST {endpoint}`、ヘッダ `Authorization: Bearer KEY`＋`Content-Type: application/json`＋（OpenRouter時）`HTTP-Referer`／`X-Title`。
- 応答は `choices[0].message.content` を取り、```json フェンス除去→`json.loads`→`AIAction` 検証の順で解釈する。
- HTTPエラー・JSON破損・スキーマ違反はすべてフォールバック契機とし、内容をログに残す。

### 6.4 プロンプト枠（固定部）

- system：ゲームルール要約＋禁止キー＋「1手だけ・JSONのみ」制約＋方向定義。
- user：観測テキスト（状態・視界・所持・メッセージ・識別メモ・直近履歴要約）＋「次の一手をJSONで」。
- assistant応答例：`{"type":"move","direction":"l","reason":"階段へ接近"}`。`reason` はモニター表示・ログ用。

### 6.5 攻略プロンプト実装 — §5.4をLLMに注入する

§5.4の攻略ロジックは `strategy.py` のコードが正本だが、LLMには同じ内容をプロンプトとして渡す。二重管理の齟齬を防ぐため、プロンプト文面は `llm.py::build_strategy_section()` が `strategy.py` の定数・優先度表から機械生成する（手書きの重複コピーを残さない）。

#### SYSTEMプロンプト（固定部）

```
You are an autonomous player of a classic roguelike (Rogue clone, Japanese UTF-8 version).
Goal: survive as long as possible and descend to deeper floors. Dying ends the run.

RULES OF SURVIVAL (follow strictly, in order):
1. If a monster is adjacent: fight ONLY if HP >= 30% of max and only one enemy.
   If HP < 30%, confused/blind/hallucinating/held/trapped, or 2+ enemies adjacent: RETREAT, do not fight.
2. If HP is not full and no enemy is adjacent: rest to regenerate (healing over time is free).
   Exception: if food counter moves_left <= 300, prioritize finding food over resting.
3. Starvation kills: moves_left<=300 hungry (find food soon), <=150 weak (food first, ignore everything else),
   <=20 faint, <=0 death. Eat RATION first, save FRUIT. Never linger when weak.
4. Descend the stairs when HP is full (or food is comfortable) and no enemy guards the stairs.
   Do not over-explore: staying too long starves you.
5. Identify safely: equip/try ONE unknown item at a time, only at full HP in safety.
   Cursed gear cannot be removed. Keep one emergency teleport/healing scroll or potion in reserve.
6. Search for hidden traps/doors before stepping into unknown tiles.

OUTPUT: exactly one JSON object, no other text:
{"type":"move|rest|search|pickup|descend|ascend|quaff|read|eat|wield|wear|takeoff|puton|remove|drop|throw|zap|fight|inventory|help|noop",
 "direction":"h|j|k|l|y|u|b|n (required for move/fight/throw/zap)",
 "item_slot":"a-z (required for item actions)",
 "reason":"short reason in Japanese, max 40 chars"}
Directions: h=left j=down k=up l=right y=upper-left u=upper-right b=lower-left n=lower-right.
FORBIDDEN: uppercase moves, Ctrl keys, Q (quit), S (save), o, !, a, F (fight-to-death). Never output them.
One turn = one action. When in doubt, choose the safer action (rest/retreat/noop).
```

#### USERプロンプト（毎手生成部）

```
Turn {turn}, Dungeon level {level}. Survival risk: HP {hp_cur}/{hp_max} ({hp_ratio}%),
food counter {moves_left} ({hunger_level}), adjacent enemies {adjacent_enemies},
escape routes {escape_routes}, safe-to-rest={can_rest_safely}.
Position ({row},{col}), room {room_id}. Stairs: {stairs_pos or "unseen"}.
Visible monsters: {list or "none"}. Visible items: {list or "none"}.
Status effects: {flags or "none"}. Message: "{message}".
Inventory: {slots or "empty"}. Identified: potions {…}, scrolls {…}.
Recent history: {last up to 5 turns: action -> result}.
Decide the next single action as JSON.
```

- `{hunger_level}` 等は `strategy.assess()` の算出値をそのまま埋め込む（LLMに再計算させない）。
- `temperature=0.2`、`max_tokens=512`。応答は§6.3の手順で解釈し、スキーマ違反・禁止キーはnoop化＋Scriptedフォールバック。
- プロンプト全文は `ai_trace.jsonl` に任意記録し、チューニング（閾値・文言のA/B比較）の材料にする。

---

## 7. 人間モニター設計 — 実画面で観察できること

### 7.1 基本方針

- curses画面構成（メッセージ行／マップ／ステータス行）は変えない。人間が普段プレイする画面と同じものを見る。
- AI状態は **メッセージ行を潰さない場所**（例：ステータス行の末尾または一時的な最終行上書き→即時復帰）に1行オーバーレイ表示する。ゲーム表示の永続破壊はしない。
- 操作は全自動だが、人間はいつでも割って入れる。

### 7.2 オーバーレイ表示内容

```
[AI:llm/mercury-2.5 T123 spd120ms] 階段へ接近 (move:l) | HP12/12 L1 G0 | [space]pause [s]step [+-]speed [m]manual [q]quit [X]kill
```

- policy名・モデル短名・ターン数・速度・直近思考（先頭40字）・HP等の要点・操作ヒント。

### 7.3 人間介入キー（AI運転中の予約キー）

| キー | 動作 |
|---|---|
| `space` | 一時停止／再開トグル |
| `s`（停止中） | 1手だけ進める（ステップ） |
| `+`／`-` | 速度変更（delay ms増減） |
| `m` | 手動モードへ切替（以降は人間のキー入力。`m` 再押下でAI復帰） |
| `q` | AI運転を安全終了（ゲーム自体は継続。確認なし） |
| `X` | **強制終了**（即時プロセス終了。セーブ・スコア記録なし。確認待ち等のブロッキング待機中も有効） |
| `Q` | 従来通りゲーム終了（AI運転中はAIが送出しない。人間のみ） |

- 介入キーは `Game._get_input` 内でAI入力より優先して横取りする。AIの行動候補と競合させない。
- 一時停止中はゲーム時間を進めない（入力を消費しない待機ループ）。
- `X` は `AIDriver.force_quit()`→`ForceQuit`送出→`run()`の例外捕捉＋`finally`の`_clean_up`で端末復帰後に終了する。確認待ち（`Message._wait_for_ack`）のブロッキング中も、`X`で待ちを解いてフラグを立て、次の`_get_input`で終了する。`X`は未使用キーであり、AIの送出はActuatorが禁止する。

### 7.4 ヘッドレスモード（任意）

- `--ai-headless` 指定時はcurses初期化をスキップし、描画なしで高速に回す。長時間fuzz・回帰用。
- ヘッドレス時はオーバーレイなし。進捗はstdoutの1行ログ＋JSONLに記録する。

---

## 8. 本体への改変点（最小差分リスト）

| # | 箇所 | 改変内容 | 備考 |
|---|---|---|---|
| M1 | `main.py` | `--ai`／`--ai-provider`／`--ai-model`／`--ai-endpoint`／`--ai-max-turns`／`--ai-delay-ms`／`--ai-timeout`／`--ai-log`／`--ai-headless` 引数追加。`Game(..., ai_options)` へ受け渡し | 既存引数の互換維持 |
| M2 | `game.py Game.__init__` | `ai_options` 引数追加・保持。`self.ai_driver` 初期値None | 既存呼び出しは `ai_options=None` で従来通り |
| M3 | `game.py Game.run/_init` | AI指定時のみ `AIDriver` を生成・開始。ヘッドレス時はcurses初期化分岐 | 通常起動の挙動不変 |
| M4 | `game.py Game._get_input` | 先頭に介入キー横取り→AI運転中は `ai_driver.next_key()` を返す分岐を追加。通常時は既存処理へフォールスルー | **唯一のホットパス改変**。AIなしでは1分岐増のみ |
| M5 | `game.py Game._play_level` | ターン境界で `ai_driver.on_turn(obs)` 通知（ログ・終了判定用）。ループ本体は不変 | 通知失敗は無視（ゲーム継続優先） |
| M6 | 新規 `python/ai/` パッケージ | `observer.py`／`strategy.py`（攻略ロジック正本・§5.4）／`policies.py`／`llm.py`（§6.5プロンプト生成）／`actuator.py`／`driver.py`／`monitor.py`／`session_log.py` | 本体ロジックに混ぜない |
| M7 | 新規テスト | `test_ai_*.py`（変換表・禁止キー・フォールバック・リプレイ） | 既存テストに影響させない |

禁止事項：`actions.py`／`combat.py`／`display.py` のゲームルール・描画規則の変更、`const.py` の値変更。

---

## 9. ロギング・リプレイ・異常検知（デバッグ還流）

### 9.1 記録形式（JSONL、1行1ターン）

```json
{"turn":123,"obs":{...},"thought":"階段へ接近","action":{"type":"move","direction":"l"},"keys":"l","result":{"pos":[10,31],"hp":[12,12],"message":"..."},"policy":"llm","model":"inception/mercury-2.5-preview","latency_ms":812,"fallback":false}
```

- 既存 `rogue_debug.log` とは別ファイル（`ai_session.jsonl`）に記録し、`debug.py` のキーログとも突合可能にする。
- LLMプロンプト全文・応答全文は `ai_trace.jsonl`（任意・容量大）に分離し、既定では要約のみ残す。

### 9.2 状態差分チェッカー

- 送信行動と次ターン観測を突き合わせ、想定外（移動を送ったのに座標不変で障害物なし等）を `anomaly` として記録する（親仕様14章）。
- anomalyはゲームを止めない。v2.1追補の未解決項目と突合できるよう、タイル・部屋・モンスターIDを添える。

### 9.3 クラッシュ・ハング対応

- 例外時はトレース＋直前N手の観測を保存し、セッションを安全終了する（自動再起動はしない。人間が画面を見ている前提のため）。
- ハング検知：同一観測のまま規定手数（既定50手）進んだら「停滞」と判定し、Scripted脱出→それでも解消しなければ停止＋報告。
- ターン上限（既定500手）到達で正常終了扱いとする。

### 9.4 リプレイ

- `ai_session.jsonl` の `keys` 列を順に再生する `--ai-replay FILE` モードを用意する。本体再実行での事後解析用（親仕様14章の決定的リプレイ相当）。

---

## 10. CLI・起動例

```bash
# ルールベースで実画面モニター付き自動プレイ（APIキー不要）
python -m python.main --ai --ai-provider scripted

# 既定LLM（OpenRouter mercury）で自動プレイ
export OPENROUTER_API_KEY="sk-or-..."
python -m python.main --ai

# モデル・速度・上限を指定
python -m python.main --ai --ai-model "inception/mercury-2.5-preview" \
  --ai-delay-ms 200 --ai-max-turns 1000 --ai-log ai_run1.jsonl

# 別プロバイダー（OpenAI互換なら任意可）
export OPENAI_API_KEY="sk-..."
python -m python.main --ai --ai-provider openai_compat \
  --ai-endpoint "https://api.openai.com/v1/chat/completions" --ai-model "gpt-4o-mini"

# ヘッドレス高速回帰（画面なし）
python -m python.main --ai --ai-headless --ai-max-turns 2000

# リプレイ
python -m python.main --ai-replay ai_run1.jsonl
```

後方互換：引数なしの起動は従来通りの手動プレイ。

---

## 11. 実装フェーズ（親仕様15章の内蔵版焼き直し）

| Phase | 内容 | 完了条件 |
|---|---|---|
| A0 | 観測・行動スキーマ＋キー対応表の固定。本書§3§4の凍結 | レビュー承認 |
| A1 | 入力差し替え（M1〜M4）＋ScriptedPolicy＋モニター表示＋一時停止/速度/手動切替 | 人間が画面を見ながら「移動→拾得→降下」のループを確認 |
| A1b | 攻略ロジック `strategy.py`（§5.4）＋RiskAssessment＋ScriptedPolicyへの組込 | 単体テストでS0〜S8の分岐（空腹/瀕死/複数隣接/振動）が期待通り発火する |
| A2 | Observer完全化（視界・識別メモ・差分検知）＋JSONLログ＋リプレイ | ログから1手の因果を追跡可能 |
| A3 | ChatClient＋LLMAgentPolicy＋フォールバック＋ヘッドレス | APIキーなしでもScriptedで完走、キーありでLLM完走 |
| A4 | 長時間スモーク（500〜2000手）＋異常カタログ化＋v2.1追補への還流 | 人手では気づきにくい不具合を1件以上特定（親仕様6章の成功基準） |

---

## 12. 受け入れ基準・リスク

### 受け入れ基準

1. `--ai --ai-provider scripted` で300手以上、AI起因の例外・ハングなく完走できる。
2. 実画面の描画・操作感が手動時と変わらず、人間がオーバーレイと介入キーで状況を把握できる。
3. LLM設定（既定OpenRouter mercury）で100手以上完走、または失敗時はScriptedフォールバックで継続できる。
4. ログから任意ターンの観測・思考・行動・結果を再現でき、異常候補を1件以上報告できる。
5. 既存テスト（`test_zero_base_regression` 等）がすべて通過し、手動起動の挙動が変わらない。
6. 攻略指標：ScriptedPolicyで複数回（例：10走）の平均到達階層・平均生存ターンが、ランダム行動ベースラインを有意に上回る。LLM PolicyはScriptedと同等以上を目指す（勝率最大化は非目的のため、厳密な有意差検定までは要求しない）。

### リスクと対策

| リスク | 対策 |
|---|---|
| LLM応答遅延で画面が固まって見える | delayとは別にタイムアウト＋フォールバック。待機中はオーバーレイに思考中表示 |
| APIキー漏洩 | CLI引数でキーを受け取らない。envのみ。ログにキーを残さない |
| AIが禁止キー（Q/S/!）を送る | Actuatorでバリデーションしnoop化＋警告ログ |
| 無限ループ・振動 | 停滞検知→脱出→停止の三段構え |
| コスト増大 | 既定は低トークン・短履歴。ヘッドレス大量回転はScriptedのみで行う |
| 本体未完成ゆえの頻繁な異常 | 異常で止めず記録＋継続を既定にし、v2.1追補へ還流する |

---

## 13. ファイル構成案（新規のみ）

```
python/ai/
  __init__.py
  schemas.py      # AIObservation / AIAction / IdentifyMemo / RiskAssessment
  observer.py     # 内部状態→観測の組み立て（画面パースなし）
  strategy.py     # 攻略ロジック正本（優先度表S0-S8・閾値・assess()・§6.5文面生成）
  policies.py     # Policy抽象＋ScriptedPolicy（strategy.py駆動のBFS移動・回復・脱出）
  llm.py          # ChatClient（urllib）＋LLMAgentPolicy（プロンプト・JSON解釈・フォールバック）
  actuator.py     # 行動→キー変換＋禁止キー検証
  driver.py       # ターン駆動・終了判定・停滞検知（Gameとの接点）
  monitor.py      # オーバーレイ表示・介入キー定義
  session_log.py  # JSONL記録・リプレイ読込・差分検知
python/test_ai_*.py  # 変換表・禁止キー・フォールバック・リプレイ・攻略分岐の単体テスト
```

---

## 付録： 親仕様からの流用表

- コマンド体系・シンボル体系：親仕様付録A/Bをそのまま採用（ただし `u/b` はv2.1修正後の定義に従う）。
- スライディングウィンドウ・識別メモ・More待ち注意・全角幅注意：親仕様7/10.5/13章の指摘を本設計§5§7に反映済み。
- ログ・リプレイ・差分・スモークの思想：親仕様10.6/14章を§9に内蔵版として具体化。

以上

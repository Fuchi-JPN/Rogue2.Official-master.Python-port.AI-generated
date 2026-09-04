# Rogue2.Official Python移植版 仕様書

## 1. 概要

### 1.1 プロジェクト情報
- **プロジェクト名**: Rogue2.Official Python移植版
- **元プロジェクト**: Rogue2.Official (C言語版ローグライクゲーム)
- **ターゲット環境**: Linux / macOS / Windows (Python 3.8+)
- **UIライブラリ**: Python標準ライブラリ `curses`

### 1.2 移植方針

#### 1.2.1 アーキテクチャ
Model-View-Controller (MVC) パターンを採用：

| レイヤー | 担当モジュール | 責務 |
|---------|--------------|------|
| **Model** | `entities.py`, `dungeon.py`, `const.py` | ゲーム状態、データ構造、定数 |
| **View** | `display.py`, `text_resources.py` | 画面描画、メッセージ表示 |
| **Controller** | `game.py`, `actions.py`, `combat.py`, `inventory.py`, `use_actions.py`, `special_actions.py` | 入力処理、ゲームロジック |

#### 1.2.2 データ構造変換ルール

| C言語 | Python | 例 |
|-------|--------|-----|
| `struct` | `dataclass` または `class` | `struct object` → `class Item` |
| `static` 変数（関数内） | クラス変数またはモジュール変数 | `static short move_left_cou` → `Movement.move_left_cou` |
| `static` 変数（ファイル内） | モジュールレベル変数 | `static boolean wizard` → `wizard = False` |
| `extern` 変数 | モジュール間インポート | `extern struct rogue` → `from entities import Player` |
| ビットフィールド | 整数定数とビット演算 | `unsigned short is_food: 1` → `is_food()` ヘルパー関数 |
| 配列 | リストまたは辞書 | `char names[26][30]` → `M_NAMES: List[str]` |
| ポインター | オブジェクト参照 | `struct object *next_object` → `next_object: Optional[Item]` |

#### 1.2.3 命名規則

| C言語 | Python | 例 |
|-------|--------|-----|
| `snake_case` 変数 | `snake_case` 変数 | `cur_level` → `cur_level` |
| `UPPER_CASE` 定数 | `UPPER_CASE` 定数 | `MAXROOMS` → `MAXROOMS` |
| `CamelCase` 関数 | `snake_case` メソッド | `oneMoveRogue()` → `one_move_rogue()` |
| 構造体名 | PascalCase クラス | `struct object` → `class Item` |

---

## 2. 画面表示システム

### 2.1 画面構成

```
+--------------------------------------------------------------------------------+
|                                                                                |
|  ダンジョンマップ (24行 x 80桁)                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
|                                                                                |
+--------------------------------------------------------------------------------+
|Level: 1  Gold: 0    Hp: 12(12)  Str: 16(16)  Arm: 4  Exp: 1/0                  |
+--------------------------------------------------------------------------------+
```

### 2.2 画面サイズ定数

```python
ROGUE_LINES = 24      # 画面行数
ROGUE_COLUMNS = 80    # 画面桁数
```

### 2.3 マップタイル表示文字

| タイル種別 | 文字 | 定数 |
|-----------|------|------|
| 床 | `.` | `FLOOR` |
| 通路 | `#` | `TUNNEL` |
| 水平壁 | `-` | `HORWALL` |
| 垂直壁 | `|` | `VERTWALL` |
| ドア | `+` | `DOOR` |
| 階段 | `%` | `STAIRS` |
| トラップ | `^` | `TRAP` |
| プレイヤー | `@` | - |
| モンスター | 種別依存 | - |
| アイテム | 種別依存 | - |

### 2.4 ステータスバー表示

最下行に以下の情報を表示：
- **Level**: 現在のダンジョンレベル
- **Gold**: 所持金
- **Hp**: 現在HP/最大HP
- **Str**: 現在筋力/最大筋力
- **Arm**: 防具クラス
- **Exp**: レベル/経験値

### 2.5 カラー対応

```python
# カラー定数
RWHITE = 0
RRED = 1
RGREEN = 2
RYELLOW = 3
RBLUE = 4
RMAGENTA = 5
RCYAN = 6

# カラー有効フラグ
COLOR = False  # config.py
```

---

## 3. キー入力システム

### 3.1 移動キー

#### 3.1.1 矢印キー / hjkl
| キー | 方向 | 定数 |
|------|------|------|
| `h` / `←` | 左 | `LEFT` |
| `j` / `↓` | 下 | `DOWN` |
| `k` / `↑` | 上 | `UP` |
| `l` / `→` | 右 | `RIGHT` |
| `y` | 左上 | `UPLEFT` |
| `u` | 右上 | `UPRIGHT` |
| `b` | 左下 | `DOWNLEFT` |
| `n` | 右下 | `DOWNRIGHT` |

#### 3.1.2 方向定数と座標オフセット

```python
# 方向インデックス
UPWARD = 0
UPRIGHT = 1
RIGHT = 2
DOWNRIGHT = 3
DOWN = 4
DOWNLEFT = 5
LEFT = 6
UPLEFT = 7

# 座標オフセット (行, 列)
DIR_OFFSETS = [
    (-1, 0),   # UPWARD
    (-1, 1),   # UPRIGHT
    (0, 1),    # RIGHT
    (1, 1),    # DOWNRIGHT
    (1, 0),    # DOWN
    (1, -1),   # DOWNLEFT
    (0, -1),   # LEFT
    (-1, -1),  # UPLEFT
]
```

### 3.2 アクションキー

| キー | アクション | メソッド |
|------|-----------|----------|
| `.` | 待機 | `rest()` |
| `,` | アイテム拾う | `pick_up()` |
| `d` | アイテム落とす | `drop()` |
| `e` | 食べる | `eat()` |
| `i` | インベントリ表示 | `inventory()` |
| `q` | 飲む | `quaff()` |
| `r` | 巻物読む | `read_scroll()` |
| `s` | 探索 | `search()` |
| `t` | 投げる | `throw()` |
| `w` | 武器装備 | `wield()` |
| `W` | 防具装備 | `wear()` |
| `T` | 防具外す | `take_off()` |
| `P` | 指輪装備 | `put_on_ring()` |
| `R` | 指輪外す | `remove_ring()` |
| `z` | 杖を使う | `zapp()` |
| `>` | 階段降りる | `descend_stairs()` |
| `<` | 階段昇る | `ascend_stairs()` |
| `S` | セーブ | `save_game()` |
| `Q` | 終了 | `quit()` |

### 3.3 移動結果定数

```python
MOVED = 0             # 移動成功
MOVE_FAILED = -1      # 移動失敗（壁など）
STOPPED_ON_SOMETHING = -2  # 何かにぶつかった
```

---

## 4. ファイル構成

### 4.1 モジュール一覧

| ファイル | 責務 | 主要クラス/関数 |
|---------|------|----------------|
| `main.py` | エントリーポイント | `main()`, `parse_args()` |
| `game.py` | ゲーム全体管理 | `Game` |
| `const.py` | ゲーム定数 | タイル、アイテム、モンスター定数 |
| `config.py` | 設定管理 | 環境設定 |
| `entities.py` | エンティティ定義 | `Player`, `Monster`, `Item`, `Room`, `Door`, `Trap` |
| `dungeon.py` | ダンジョン管理 | `DungeonLevel`, `DungeonManager` |
| `level_generator.py` | レベル生成 | `LevelGenerator` |
| `actions.py` | 移動・アクション | `Movement`, `TrapManager` |
| `inventory.py` | インベントリ管理 | `InventoryManager` |
| `combat.py` | 戦闘システム | `Combat`, `MonsterAI` |
| `use_actions.py` | アイテム使用 | `UseActions` |
| `special_actions.py` | 特殊アクション | `ThrowAction`, `WandAction`, `RingAction` |
| `save_manager.py` | セーブ/ロード | `GameState`, `SaveManager` |
| `score_manager.py` | スコア管理 | `ScoreEntry`, `ScoreManager` |
| `display.py` | 画面描画 | `Display`, `Message`, `Stats` |
| `text_resources.py` | テキストリソース | `TextResources` |
| `utils.py` | ユーティリティ | `get_rand()`, `roll_dice()` |

### 4.2 依存関係

```
main.py
  └── game.py
        ├── display.py (View)
        ├── dungeon.py (Model)
        │     └── entities.py
        ├── level_generator.py
        ├── actions.py
        │     └── entities.py
        ├── inventory.py
        ├── combat.py
        │     └── entities.py
        ├── use_actions.py
        ├── special_actions.py
        ├── save_manager.py
        └── score_manager.py
```

---

## 5. 主要クラス

### 5.1 Game クラス (`game.py`)

ゲーム全体のライフサイクルを管理。

#### 属性
```python
class Game:
    player: Player           # プレイヤー
    dungeon: DungeonManager  # ダンジョン管理
    display: Display         # 画面描画
    message: Message         # メッセージ管理
    stats: Stats             # ステータス表示
    running: bool            # ゲーム実行フラグ
    cur_level: int           # 現在レベル
    max_level: int           # 到達最深レベル
```

#### 主要メソッド
```python
def run(self) -> None:
    """ゲーム開始（メインループ）"""

def _init(self) -> None:
    """初期化処理"""

def _init_curses(self) -> None:
    """curses初期化"""

def _init_game_data(self) -> None:
    """ゲームデータ初期化"""

def _make_level(self) -> None:
    """レベル生成"""

def _play_level(self) -> None:
    """レベルプレイ（入力処理ループ）"""

def _get_input(self) -> int:
    """キー入力取得"""

def _clean_up(self) -> None:
    """終了処理"""
```

### 5.2 Player クラス (`entities.py`)

プレイヤーキャラクター。

#### 属性
```python
@dataclass
class Player:
    hp_current: int = 12          # 現在HP
    hp_max: int = 12              # 最大HP
    str_current: int = 16         # 現在筋力
    str_max: int = 16             # 最大筋力
    exp: int = 1                  # レベル
    exp_points: int = 0           # 経験値
    gold: int = 0                 # 所持金
    row: int = 0                  # 現在行
    col: int = 0                  # 現在列
    fchar: str = '@'              # 表示文字
    moves_left: int = 0           # 残り移動回数
    armor: Optional[Item] = None  # 装備中防具
    weapon: Optional[Item] = None # 装備中武器
    left_ring: Optional[Item] = None   # 左手指輪
    right_ring: Optional[Item] = None  # 右手指輪
    pack: List[Item] = field(default_factory=list)  # インベントリ
    name: str = ""                # プレイヤー名
    dungeon_level: int = 1        # ダンジョンレベル
```

### 5.3 Monster クラス (`entities.py`)

モンスター。

#### 属性
```python
@dataclass
class Monster:
    m_flags: int = 0              # モスターフラグ（ビットマスク）
    damage: str = ""              # ダメージダイス（例: "1d6"）
    hp_to_kill: int = 0           # 倒すのに必要なHP
    m_char: str = ''              # 表示文字
    kill_exp: int = 0             # 倒した時の経験値
    first_level: int = 0          # 出現開始レベル
    last_level: int = 0           # 出現終了レベル
    m_hit_chance: int = 0         # 命中率
    stationary_damage: str = ""   # 停止型のダメージ
    drop_percent: int = 0         # アイテムドロップ率
    trail_char: str = ''          # 移動前の地形文字
    slowed_toggle: bool = False   # 減速トグル
    moves_confused: int = 0       # 混乱移動残り
    nap_length: int = 0           # 睡眠時間
    disguise: str = ''            # 変装文字
    next_monster: Optional[Monster] = None  # 次のモンスター（連結リスト）
    row: int = 0                  # 現在行
    col: int = 0                  # 現在列
    monster_type: int = 0         # モンスター種別
```

### 5.4 Item クラス (`entities.py`)

アイテム。

#### 属性
```python
@dataclass
class Item:
    item_type: int = 0            # アイテム種別（GOLD/FOOD/ARMOR等）
    which_kind: int = 0           # サブタイプ
    damage: str = ""              # ダメージダイス
    quantity: int = 1             # 数量
    ichar: str = ''               # インベントリ文字
    hit_enchant: int = 0          # 命中エンチャント
    d_enchant: int = 0            # ダメージエンチャント
    is_protected: bool = False    # 保護状態
    is_cursed: bool = False       # 呪い状態
    identified: int = 0           # 識別状態
    in_use_flags: int = 0         # 使用中フラグ
    row: int = 0                  # 配置行
    col: int = 0                  # 配置列
    next_object: Optional[Item] = None  # 次のアイテム（連結リスト）
```

### 5.5 DungeonLevel クラス (`dungeon.py`)

単一ダンジョンレベル。

#### 属性
```python
class DungeonLevel:
    level: int                    # レベル番号
    dungeon: List[List[int]]      # 2次元グリッド（タイルフラグ）
    rooms: List[Room]             # 部屋リスト
    traps: List[Trap]             # 罠リスト
    stairs_row: int               # 階段行
    stairs_col: int               # 階段列
```

#### 主要メソッド
```python
def clear(self) -> None:
    """グリッドをクリア"""

def get_tile(self, row: int, col: int) -> int:
    """指定座標のタイルを取得"""

def set_tile(self, row: int, col: int, value: int) -> None:
    """指定座標にタイルを設定"""
```

### 5.6 DungeonManager クラス (`dungeon.py`)

複数レベルのダンジョン管理。

#### 属性
```python
class DungeonManager:
    levels: Dict[int, DungeonLevel]  # レベル番号 → DungeonLevel
    current_level: int               # 現在のレベル番号
```

#### 主要メソッド
```python
def create_level(self, level: int) -> DungeonLevel:
    """新しいレベルを作成"""

def get_current_level(self) -> DungeonLevel:
    """現在のレベルを取得"""

def set_current_level(self, level: int) -> None:
    """現在のレベルを設定"""
```

### 5.7 LevelGenerator クラス (`level_generator.py`)

ダンジョンレベル生成。

#### 主要メソッド
```python
def make_level(self, dungeon: DungeonLevel, level: int) -> None:
    """レベル生成メイン処理"""

def create_room(self, dungeon: DungeonLevel, room: Room) -> None:
    """部屋を作成"""

def connect_rooms(self, dungeon: DungeonLevel, room1: Room, room2: Room) -> None:
    """部屋を通路で接続"""

def put_player(self, dungeon: DungeonLevel, player: Player) -> None:
    """プレイヤーを配置"""

def put_stairs(self, dungeon: DungeonLevel) -> None:
    """階段を配置"""
```

### 5.8 Movement クラス (`actions.py`)

移動処理。

#### 属性
```python
class Movement:
    player: Player
    dungeon: DungeonLevel
    
    # クラス変数（C言語のstatic変数に相当）
    move_left_cou: int = 0  # 消化遅延指輪の移動カウンター
    reg_search: bool = False  # 探索トグル
```

#### 主要メソッド
```python
def one_move_rogue(self, dir: int, pickup: bool) -> int:
    """1回の移動処理"""

def multiple_move_rogue(self, dir: int) -> None:
    """連続移動"""

def is_passable(self, row: int, col: int) -> bool:
    """通行可能判定"""

def check_hunger(self) -> None:
    """空腹状態チェック"""

def get_dir_rc(self, dir: int, row: int, col: int) -> Tuple[int, int]:
    """方向から座標を計算"""
```

### 5.9 Combat クラス (`combat.py`)

戦闘システム。

#### 主要メソッド
```python
def mon_hit(self, monster: Monster) -> None:
    """モンスターの攻撃"""

def rogue_hit(self, monster: Monster) -> None:
    """プレイヤーの攻撃"""

def fight(self, dir: int, to_death: bool) -> int:
    """戦闘開始"""

def _get_damage(self, damage_str: str) -> int:
    """ダイス文字列からダメージ計算"""
```

### 5.10 MonsterAI クラス (`combat.py`)

モンスターAI。

#### 主要メソッド
```python
def put_mons(self, dungeon: DungeonLevel, level: int) -> None:
    """モンスターを配置"""

def mv_mons(self) -> None:
    """全モンスターの移動"""

def mv_monster(self, monster: Monster) -> None:
    """単一モンスターの移動"""
```

### 5.11 InventoryManager クラス (`inventory.py`)

インベントリ管理。

#### 主要メソッド
```python
def add_to_pack(self, item: Item, force: bool) -> bool:
    """アイテムを追加"""

def pick_up(self) -> None:
    """足元のアイテムを拾う"""

def drop(self) -> None:
    """アイテムを落とす"""

def wear(self) -> None:
    """防具を装備"""

def wield(self) -> None:
    """武器を装備"""

def put_on(self) -> None:
    """指輪を装備"""

def inventory(self) -> None:
    """インベントリ表示"""
```

### 5.12 UseActions クラス (`use_actions.py`)

アイテム使用。

#### 主要メソッド
```python
def quaff(self) -> None:
    """ポーションを飲む"""

def read_scroll(self) -> None:
    """巻物を読む"""

def eat(self) -> None:
    """食料を食べる"""
```

### 5.13 Display クラス (`display.py`)

画面描画。

#### 属性
```python
class Display:
    stdscr: Any       # curses標準画面
    use_color: bool   # カラー使用フラグ
    color_str: List[str]  # カラー文字列
```

#### 主要メソッド
```python
def draw_map(self, dungeon: DungeonLevel) -> None:
    """マップを描画"""

def refresh(self) -> None:
    """画面更新"""

def clear(self) -> None:
    """画面クリア"""

def mvaddch(self, row: int, col: int, char: str) -> None:
    """指定位置に文字を描画"""

def mvaddstr(self, row: int, col: int, string: str) -> None:
    """指定位置に文字列を描画"""
```

### 5.14 SaveManager クラス (`save_manager.py`)

セーブ/ロード管理。

#### 主要メソッド
```python
def save_game(self, state: GameState) -> bool:
    """ゲームをセーブ"""

def load_game(self) -> Optional[GameState]:
    """ゲームをロード"""

def get_save_files(self) -> List[str]:
    """セーブファイル一覧を取得"""

def delete_save_file(self) -> bool:
    """セーブファイルを削除"""
```

---

## 6. 主要定数

### 6.1 タイルタイプ (`const.py`)

```python
# マップタイルフラグ（ビットマスク）
NOTHING = 0
MONSTER = 0x01
OBJECT = 0x02
STAIRS = 0x04
TRAP = 0x08
DOOR = 0x10
FLOOR = 0x20
TUNNEL = 0x40
HORWALL = 0x80
VERTWALL = 0x100
HIDDEN = 0x200
```

### 6.2 アイテム種別

```python
GOLD = 0
FOOD = 1
ARMOR = 2
WEAPON = 3
SCROL = 4
POTION = 5
WAND = 6
RING = 7
AMULET = 8
```

### 6.3 防具タイプ

```python
LEATHER = 0
RINGMAIL = 1
SCALE = 2
CHAIN = 3
BANDED = 4
SPLINT = 5
PLATE = 6
```

### 6.4 武器タイプ

```python
BOW = 0
DART = 1
ARROW = 2
DAGGER = 3
SHURIKEN = 4
MACE = 5
LONG_SWORD = 6
TWO_HANDED_SWORD = 7
```

### 6.5 罠タイプ

```python
NO_TRAP = 0
TRAP_DOOR = 1
BEAR_TRAP = 2
TELE_TRAP = 3
DART_TRAP = 4
SLEEPING_GAS_TRAP = 5
RUST_TRAP = 6
```

### 6.6 モンスターフラグ

```python
HASTED = 0x0001
SLOWED = 0x0002
INVISIBLE = 0x0004
ASLEEP = 0x0008
WAKENS = 0x0010
WANDERS = 0x0020
FLIES = 0x0040
FLITS = 0x0080
CAN_FLIT = 0x0100
CONFUSED = 0x0200
RUSTS = 0x0400
HOLDS = 0x0800
FREEZES = 0x1000
STEALS_GOLD = 0x2000
STEALS_ITEM = 0x4000
STINGS = 0x8000
DRAINS_LIFE = 0x10000
DROPS_LEVEL = 0x20000
SEEKS_GOLD = 0x40000
FREEZING_ROGUE = 0x80000
RUST_VANISHED = 0x100000
CONFUSES = 0x200000
IMITATES = 0x400000
FLAMES = 0x800000
STATIONARY = 0x1000000
NAPPING = 0x2000000
ALREADY_MOVED = 0x4000000
```

### 6.7 空腹状態

```python
HUNGRY = 300   # 空腹
WEAK = 150     # 虚弱
FAINT = 20     # 失神
STARVE = 0     # 餓死
```

### 6.8 ゲーム制限値

```python
MAX_PACK_COUNT = 24    # インベントリ最大数
MAXROOMS = 9          # 最大部屋数
AMULET_LEVEL = 26     # アミュレット出現階
MAX_EXP_LEVEL = 21    # 最大経験レベル
MAX_HP = 800          # 最大HP
MAX_STRENGTH = 99     # 最大筋力
```

---

## 7. グローバル状態変数

### 7.1 プレイヤー状態フラグ

以下の変数はモジュールレベルで管理（C言語のstatic/extern変数に相当）：

```python
# use_actions.py, combat.py, special_actions.py 等
halluc = False           # 幻覚状態
blind = False            # 盲目状態
confused = False         # 混乱状態
levitate = False         # 浮遊状態
haste_self = False       # 加速状態
see_invisible = False    # 不可視視認
detect_monster = False   # モンスター検出
wizard = False           # ウィザードモード
ring_exp = 0             # 指輪経験値ボーナス
r_rings = 0              # 装備中の指輪数
e_rings = 0              # 有効な指輪数
add_strength = 0         # 筋力ボーナス
aggravate_monster = False  # モンスター怒り状態
stealthy = False         # 忍び足
confused_player = False  # プレイヤー混乱
bear_trap = 0            # 熊罠カウンター
being_held = False       # 保持されている状態
```

---

## 8. データ構造詳細

### 8.1 ダンジョングリッド

2次元リストで表現。各セルはタイルフラグのビット和。

```python
# 例: 床にモンスターがいる
dungeon[row][col] = FLOOR | MONSTER  # 0x21

# 例: 隠しドア
dungeon[row][col] = DOOR | HIDDEN    # 0x210
```

### 8.2 アイテム連結リスト

同一座標に複数アイテムが存在する場合、連結リストで管理。

```python
# 座標(row, col)のアイテムを取得
def get_item_at(dungeon: DungeonLevel, row: int, col: int) -> Optional[Item]:
    # 連結リストを走査
    item = items_head
    while item:
        if item.row == row and item.col == col:
            return item
        item = item.next_object
    return None
```

### 8.3 モンスター連結リスト

アクティブなモンスターを連結リストで管理。

```python
# モンスターリストの先頭
monsters_head: Optional[Monster] = None

# 全モンスターを走査
def for_each_monster(callback):
    monster = monsters_head
    while monster:
        callback(monster)
        monster = monster.next_monster
```

---

## 9. 主要アルゴリズム

### 9.1 レベル生成

```
1. 3x3グリッドに最大9部屋を配置
2. 各部屋をランダムに生成（サイズ、位置）
3. 隣接する部屋を通路で接続
4. 階段を配置
5. 罠を配置
6. モンスターを配置
7. アイテムを配置
8. プレイヤーを配置
```

### 9.2 モンスター移動

```
1. 睡眠状態チェック → 継続または起床
2. 特殊能力チェック（移動、攻撃）
3. プレイヤーへの経路探索
4. 移動実行
5. trail_char更新
```

### 9.3 戦闘処理

```
1. 命中判定（命中率ダイス）
2. 命中時 → ダメージ計算
3. HP更新
4. 死亡判定
5. 特殊効果適用（錆、毒、レベルドレイン等）
```

---

## 10. セーブデータ構造

### 10.1 GameState クラス

```python
class GameState:
    # プレイヤー情報
    player: Player
    
    # ダンジョン情報
    dungeon: DungeonLevel
    
    # ゲーム状態
    cur_level: int
    max_level: int
    foods: int
    party_room: int
    party_counter: int
    cur_room: int
    
    # 状態フラグ
    being_held: bool
    bear_trap: int
    halluc: bool
    blind: bool
    confused: bool
    levitate: bool
    haste_self: bool
    see_invisible: bool
    detect_monster: bool
    wizard: bool
    score_only: bool
    m_moves: int
    
    # アイテム識別情報
    id_potions: List[int]
    id_scrolls: List[int]
    id_wands: List[int]
    id_rings: List[int]
    is_wood: List[bool]
    
    # その他
    hunger_str: str
    login_name: str
```

---

## 11. C言語版との主な相違点

### 11.1 静的変数の扱い

| C言語 | Python | 対応 |
|-------|--------|------|
| 関数内static変数 | クラス変数に変換 | `Movement.move_left_cou` |
| ファイル内static変数 | モジュール変数 | `halluc`, `blind` 等 |

### 11.2 属性名変更

| C言語 | Python | 理由 |
|-------|--------|------|
| `dungeon.grid` | `dungeon.dungeon` | Pythonの命名規則 |
| `monster.monster_kind` | `monster.monster_type` | 型との混同回避 |

### 11.3 方向定数の修正

| 元 | 修正後 | 理由 |
|----|--------|------|
| `LEFTDOWN` | `DOWNLEFT` | 一貫性 |
| `RIGHTUP` | `UPRIGHT` | 一貫性 |

---

## 12. テスト一覧

| テストファイル | 対象 |
|---------------|------|
| `test_imports.py` | モジュールインポート |
| `test_const.py` | 定数定義 |
| `test_entities.py` | エンティティクラス |
| `test_dungeon.py` | ダンジョンデータ構造 |
| `test_main.py` | メインエントリーポイント |
| `test_utils.py` | ユーティリティ関数 |
| `test_level_generation.py` | レベル生成 |
| `test_movement.py` | 移動処理 |
| `test_inventory.py` | インベントリシステム |
| `test_combat.py` | 戦闘システム |
| `test_special_actions.py` | 特殊アクション |
| `test_save_load.py` | セーブ/ロード |
| `test_score.py` | スコア管理 |
| `test_text_resources.py` | テキストリソース |
| `tests/test_integration.py` | 統合テスト |

---

## 13. 実行方法

### 13.1 起動

```bash
cd python
python main.py
```

### 13.2 コマンドラインオプション

```bash
python main.py --help
python main.py --save-file game.sav
python main.py --wizard  # ウィザードモード
```

### 13.3 テスト実行

```bash
cd python
python -m pytest
```

---

## 14. 改訂履歴

| 版 | 日付 | 内容 |
|----|------|------|
| 1.0 | 2026-03-05 | 初版作成 |

---

**以上**

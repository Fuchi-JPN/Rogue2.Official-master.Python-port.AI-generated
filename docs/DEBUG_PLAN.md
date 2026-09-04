# Rogue2.Official Python 移植 - 動作確認とデバッグ手順書

## 目次

1. [環境構築](#環境構築)
2. [段階的な動作確認計画](#段階的な動作確認計画)
3. [デバッグ手順](#デバッグ手順)
4. [トラブルシューティング](#トラブルシューティング)

---

## 環境構築

### 1. 仮想環境の作成 (venv)

Python 3.8以降が必要です。

#### Windows (cmd.exe)
```cmd
cd m:\src\Rogue2.Official-master
python -m venv venv
venv\Scripts\activate
```

#### Windows (PowerShell)
```powershell
cd m:\src\Rogue2.Official-master
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### Linux/Mac
```bash
cd /path/to/Rogue2.Official-master
python3 -m venv venv
source venv/bin/activate
```

### 2. 必要なライブラリのインストール

#### Windowsの場合
```bash
pip install windows-curses
```

#### Linux/Macの場合
```bash
# ncursesは通常システムにインストールされています
# Ubuntu/Debianの場合:
sudo apt-get install python3-dev libncurses5-dev

# macOSの場合:
brew install ncurses
```

### 3. 依存関係ファイルの作成

`python/requirements.txt`を作成:

```txt
# Windows用
windows-curses>=2.0.1
```

または、Linux/Mac用:

```txt
# Linux/Mac用（ncursesはシステムにインストール済みと仮定）
```

インストール:
```bash
pip install -r python/requirements.txt
```

---

## 段階的な動作確認計画

### フェーズ 0: 基礎動作確認

#### テスト 0.1: モジュールインポート確認
```python
# python/test_imports.py
import sys
sys.path.insert(0, '.')

try:
    import const
    print("✓ const モジュール: OK")
except Exception as e:
    print(f"✗ const モジュール: {e}")

try:
    import entities
    print("✓ entities モジュール: OK")
except Exception as e:
    print(f"✗ entities モジュール: {e}")

try:
    import dungeon
    print("✓ dungeon モジュール: OK")
except Exception as e:
    print(f"✗ dungeon モジュール: {e}")

try:
    import game
    print("✓ game モジュール: OK")
except Exception as e:
    print(f"✗ game モジュール: {e}")

try:
    import display
    print("✓ display モジュール: OK")
except Exception as e:
    print(f"✗ display モジュール: {e}")

try:
    import utils
    print("✓ utils モジュール: OK")
except Exception as e:
    print(f"✗ utils モジュール: {e}")

try:
    import level_generator
    print("✓ level_generator モジュール: OK")
except Exception as e:
    print(f"✗ level_generator モジュール: {e}")

try:
    import actions
    print("✓ actions モジュール: OK")
except Exception as e:
    print(f"✗ actions モジュール: {e}")

try:
    import inventory
    print("✓ inventory モジュール: OK")
except Exception as e:
    print(f"✗ inventory モジュール: {e}")

try:
    import use_actions
    print("✓ use_actions モジュール: OK")
except Exception as e:
    print(f"✗ use_actions モジュール: {e}")

try:
    import combat
    print("✓ combat モジュール: OK")
except Exception as e:
    print(f"✗ combat モジュール: {e}")

try:
    import special_actions
    print("✓ special_actions モジュール: OK")
except Exception as e:
    print(f"✗ special_actions モジュール: {e}")

try:
    import save_manager
    print("✓ save_manager モジュール: OK")
except Exception as e:
    print(f"✗ save_manager モジュール: {e}")

try:
    import score_manager
    print("✓ score_manager モジュール: OK")
except Exception as e:
    print(f"✗ score_manager モジュール: {e}")

try:
    import text_resources
    print("✓ text_resources モジュール: OK")
except Exception as e:
    print(f"✗ text_resources モジュール: {e}")

print("\nすべてのモジュールのインポートが完了しました！")
```

実行:
```bash
cd python
python test_imports.py
```

---

### フェーズ 1: 基盤構築とデータ構造

#### テスト 1.1: 定数と設定の確認
```python
# python/test_const.py
import sys
sys.path.insert(0, '.')

from const import *

# 定数の確認
print("定数の確認:")
print(f"  ROGUE_LINES = {ROGUE_LINES}")
print(f"  ROGUE_COLUMNS = {ROGUE_COLUMNS}")
print(f"  MIN_ROW = {MIN_ROW}")
print(f"  MAX_PACK_COUNT = {MAX_PACK_COUNT}")
print(f"  MAX_GOLD = {MAX_GOLD}")

# ヘルパー関数の確認
print("\nヘルパー関数の確認:")
print(f"  is_monster(0x10) = {is_monster(0x10)}")
print(f"  is_object(0x20) = {is_object(0x20)}")
print(f"  is_floor(0x01) = {is_floor(0x01)}")
print(f"  is_wall(0x04) = {is_wall(0x04)}")
print(f"  is_passable(0x01) = {is_passable(0x01)}")
print(f"  is_passable(0x04) = {is_passable(0x04)}")
```

#### テスト 1.2: エンティティクラスの確認
```python
# python/test_entities.py
import sys
sys.path.insert(0, '.')

from entities import Player, Monster, Item, Room, Trap

# Player クラスの確認
print("Player クラスの確認:")
player = Player()
player.name = "テストプレイヤー"
player.hp_current = 20
player.hp_max = 20
player.str_current = 16
player.str_max = 16
player.exp = 0
player.gold = 0
player.row = 10
player.col = 40
print(f"  名前: {player.name}")
print(f"  HP: {player.hp_current}/{player.hp_max}")
print(f"  STR: {player.str_current}/{player.str_max}")
print(f"  EXP: {player.exp}")
print(f"  GOLD: {player.gold}")
print(f"  位置: ({player.row}, {player.col})")

# Monster クラスの確認
print("\nMonster クラスの確認:")
monster = Monster()
monster.m_char = 'A'
monster.m_flags = ASLEEP | WAKENS
monster.m_damage = "1d3"
monster.m_hit_chance = 10
monster.hp_to_kill = 8
monster.kill_exp = 2
monster.row = 12
monster.col = 42
print(f"  文字: {monster.m_char}")
print(f"  フラグ: {monster.m_flags}")
print(f"  ダメージ: {monster.m_damage}")
print(f"  命中率: {monster.m_hit_chance}")
print(f"  HP: {monster.hp_to_kill}")
print(f"  経験値: {monster.kill_exp}")
print(f"  位置: ({monster.row}, {monster.col})")

# Item クラスの確認
print("\nItem クラスの確認:")
item = Item()
item.item_type = WEAPON
item.which_kind = DAGGER
item.damage = "1d4"
item.hit_enchant = 0
item.d_enchant = 0
item.quantity = 1
item.identified = False
print(f"  タイプ: {item.item_type}")
print(f"  種類: {item.which_kind}")
print(f"  ダメージ: {item.damage}")
print(f"  数量: {item.quantity}")
print(f"  識別: {item.identified}")

# Room クラスの確認
print("\nRoom クラスの確認:")
room = Room()
room.top_row = 5
room.bottom_row = 15
room.left_col = 10
room.right_col = 30
room.is_room = R_ROOM
print(f"  上端: {room.top_row}")
print(f"  下端: {room.bottom_row}")
print(f"  左端: {room.left_col}")
print(f"  右端: {room.right_col}")
print(f"  フラグ: {room.is_room}")
```

#### テスト 1.3: ダンジョンデータ構造の確認
```python
# python/test_dungeon.py
import sys
sys.path.insert(0, '.')

from dungeon import DungeonLevel, DungeonManager
from const import ROGUE_LINES, ROGUE_COLUMNS, FLOOR, WALL

# DungeonLevel クラスの確認
print("DungeonLevel クラスの確認:")
dungeon = DungeonLevel(level=1)
print(f"  レベル: {dungeon.level}")
print(f"  グリッドサイズ: {len(dungeon.grid)} x {len(dungeon.grid[0])}")
print(f"  部屋数: {len(dungeon.rooms)}")
print(f"  モンスター数: {len(dungeon.monsters)}")
print(f"  アイテム数: {len(dungeon.objects)}")

# グリッドの初期状態を確認
print("\nグリッドの初期状態（5x5）:")
for i in range(5):
    row_str = ""
    for j in range(5):
        tile = dungeon.grid[i][j]
        if tile & FLOOR:
            row_str += "."
        elif tile & WALL:
            row_str += "#"
        else:
            row_str += "?"
    print(f"  {row_str}")

# DungeonManager クラスの確認
print("\nDungeonManager クラスの確認:")
manager = DungeonManager()
print(f"  マネージャー作成: OK")
```

---

### フェーズ 2: ゲームループと表示系

#### テスト 2.1: メインエントリーポイントの確認
```python
# python/test_main.py
import sys
sys.path.insert(0, '.')

from main import parse_args

# コマンドライン引数解析の確認
print("コマンドライン引数解析の確認:")
args = parse_args([])
print(f"  デフォルト引数: {args}")

args = parse_args(['--score'])
print(f"  --score 引数: {args}")

args = parse_args(['--restore', 'test.sav'])
print(f"  --restore 引数: {args}")
```

#### テスト 2.2: ユーティリティ関数の確認
```python
# python/test_utils.py
import sys
sys.path.insert(0, '.')

from utils import get_rand, rand_percent, coin_toss, roll_damage

# 乱数関数の確認
print("乱数関数の確認:")
print(f"  get_rand(1, 10) = {get_rand(1, 10)}")
print(f"  rand_percent(50) = {rand_percent(50)}")
print(f"  coin_toss() = {coin_toss()}")

# ダメージロールの確認
print("\nダメージロールの確認:")
print(f"  roll_damage('1d6', 1) = {roll_damage('1d6', 1)}")
print(f"  roll_damage('2d4', 1) = {roll_damage('2d4', 1)}")
print(f"  roll_damage('1d6/2d4', 1) = {roll_damage('1d6/2d4', 1)}")
```

#### テスト 2.3: curses表示の確認（簡易版）
```python
# python/test_display_simple.py
import sys
sys.path.insert(0, '.')

try:
    import curses

    def test_curses(stdscr):
        stdscr.clear()
        stdscr.addstr(0, 0, "Curses テスト")
        stdscr.addstr(2, 0, "Enterキーで終了...")
        stdscr.refresh()
        stdscr.getch()

    print("curses モジュール: OK")
    print("テストを実行するには以下のコマンドを実行してください:")
    print("  python -c \"import curses; curses.wrapper(lambda s: s.addstr(0,0,'OK'); s.refresh(); s.getch())\"")
except ImportError as e:
    print(f"curses モジュール: {e}")
    print("Windowsの場合: pip install windows-curses")
```

---

### フェーズ 3: ワールド生成と移動

#### テスト 3.1: レベル生成の確認
```python
# python/test_level_generation.py
import sys
sys.path.insert(0, '.')

from level_generator import LevelGenerator
from dungeon import DungeonLevel
from entities import Player

# レベル生成の確認
print("レベル生成の確認:")
dungeon = DungeonLevel(level=1)
player = Player()
player.row = 10
player.col = 40

generator = LevelGenerator(dungeon, player)
generator.make_level()

print(f"  部屋数: {len(dungeon.rooms)}")
print(f"  モンスター数: {len(dungeon.monsters)}")
print(f"  アイテム数: {len(dungeon.objects)}")

# 部屋情報の表示
print("\n部屋情報:")
for i, room in enumerate(dungeon.rooms):
    print(f"  部屋 {i+1}: ({room.top_row}, {room.left_col}) - ({room.bottom_row}, {room.right_col})")

# モンスター情報の表示
print("\nモンスター情報:")
for i, monster in enumerate(dungeon.monsters):
    print(f"  モンスター {i+1}: {monster.m_char} at ({monster.row}, {monster.col})")

# アイテム情報の表示
print("\nアイテム情報:")
for i, item in enumerate(dungeon.objects):
    print(f"  アイテム {i+1}: type={item.item_type} at ({item.row}, {item.col})")

# マップの簡易表示
print("\nマップ（最初の15行）:")
for i in range(15):
    row_str = ""
    for j in range(60):
        tile = dungeon.grid[i][j]
        if dungeon.grid[i][j] & const.MONSTER:
            # モンスターがいる
            for monster in dungeon.monsters:
                if monster.row == i and monster.col == j:
                    row_str += monster.m_char
                    break
        elif dungeon.grid[i][j] & const.OBJECT:
            # アイテムがある
            row_str += "*"
        elif dungeon.grid[i][j] & const.FLOOR:
            row_str += "."
        elif dungeon.grid[i][j] & const.WALL:
            row_str += "#"
        elif dungeon.grid[i][j] & const.DOOR:
            row_str += "+"
        elif dungeon.grid[i][j] & const.STAIRS:
            row_str += "%"
        elif dungeon.grid[i][j] & const.TUNNEL:
            row_str += "#"
        else:
            row_str += "?"
    print(f"  {row_str}")
```

#### テスト 3.2: 移動処理の確認
```python
# python/test_movement.py
import sys
sys.path.insert(0, '.')

from actions import Movement, MoveResult
from dungeon import DungeonLevel
from entities import Player
from level_generator import LevelGenerator
import const

# 移動処理の確認
print("移動処理の確認:")

# レベルを生成
dungeon = DungeonLevel(level=1)
player = Player()
player.row = 10
player.col = 40

generator = LevelGenerator(dungeon, player)
generator.make_level()

# プレイヤーを床の位置に配置
for i in range(const.MIN_ROW, const.ROGUE_LINES - 2):
    for j in range(1, const.ROGUE_COLUMNS - 1):
        if dungeon.grid[i][j] & const.FLOOR:
            player.row = i
            player.col = j
            break
    if dungeon.grid[player.row][player.col] & const.FLOOR:
        break

print(f"  プレイヤー初期位置: ({player.row}, {player.col})")

# 移動クラスを作成
movement = Movement(player, dungeon)

# 各方向への移動をテスト
directions = {
    'h': (-1, 0, '左'),
    'j': (0, 1, '下'),
    'k': (0, -1, '上'),
    'l': (1, 0, '右'),
    'y': (-1, -1, '左上'),
    'u': (-1, 1, '左下'),
    'b': (1, -1, '右上'),
    'n': (1, 1, '右下'),
}

for dirch, (dr, dc, name) in directions.items():
    original_row = player.row
    original_col = player.col
    
    result = movement.one_move_rogue(dirch)
    
    print(f"  {name} ({dirch}): {result.name}")
    print(f"    位置: ({original_row}, {original_col}) -> ({player.row}, {player.col})")
    
    # 位置を戻す
    player.row = original_row
    player.col = original_col
```

---

### フェーズ 4: アクションとインタラクション

#### テスト 4.1: インベントリシステムの確認
```python
# python/test_inventory.py
import sys
sys.path.insert(0, '.')

from inventory import InventoryManager
from entities import Player, Item
import const

# インベントリシステムの確認
print("インベントリシステムの確認:")

player = Player()
player.pack = []

inventory = InventoryManager(player)

# アイテムを作成
weapon = Item()
weapon.item_type = const.WEAPON
weapon.which_kind = const.DAGGER
weapon.damage = "1d4"
weapon.quantity = 1
weapon.ichar = 'a'

potion = Item()
potion.item_type = const.POTION
potion.which_kind = const.HEALING
potion.quantity = 1
potion.ichar = 'b'

# アイテムを追加
print("\nアイテムの追加:")
inventory.add_to_pack(weapon)
print(f"  武器を追加: {len(player.pack)} 個のアイテム")

inventory.add_to_pack(potion)
print(f"  ポーションを追加: {len(player.pack)} 個のアイテム")

# インベントリの表示
print("\nインベントリ:")
for i, item in enumerate(player.pack):
    print(f"  {item.ichar}: type={item.item_type}, kind={item.which_kind}")

# アイテムを削除
print("\nアイテムの削除:")
inventory.drop(weapon)
print(f"  武器を削除: {len(player.pack)} 個のアイテム")
```

#### テスト 4.2: 戦闘システムの確認
```python
# python/test_combat.py
import sys
sys.path.insert(0, '.')

from combat import Combat
from entities import Player, Monster
from dungeon import DungeonLevel
import const

# 戦闘システムの確認
print("戦闘システムの確認:")

player = Player()
player.hp_current = 20
player.hp_max = 20
player.exp = 0
player.weapon = None
player.armor = None

dungeon = DungeonLevel(level=1)
dungeon.monsters = []

# モンスターを作成
monster = Monster()
monster.m_char = 'A'
monster.m_flags = const.ASLEEP | const.WAKENS
monster.m_damage = "1d3"
monster.m_hit_chance = 10
monster.hp_to_kill = 8
monster.kill_exp = 2
monster.row = 10
monster.col = 42
dungeon.monsters.append(monster)

combat = Combat(player, dungeon)

# プレイヤーの攻撃をテスト
print("\nプレイヤーの攻撃:")
original_hp = monster.hp_to_kill
combat.rogue_hit(monster)
print(f"  モンスターHP: {original_hp} -> {monster.hp_to_kill}")
print(f"  プレイヤーEXP: {player.exp}")

# モンスターの攻撃をテスト
print("\nモンスターの攻撃:")
original_hp = player.hp_current
combat.mon_hit(monster)
print(f"  プレイヤーHP: {original_hp} -> {player.hp_current}")
```

#### テスト 4.3: 特殊アクションの確認
```python
# python/test_special_actions.py
import sys
sys.path.insert(0, '.')

from special_actions import ThrowAction, WandAction, RingAction
from entities import Player, Item
from dungeon import DungeonLevel
import const

# 特殊アクションの確認
print("特殊アクションの確認:")

player = Player()
player.row = 10
player.col = 40

dungeon = DungeonLevel(level=1)

# 投擲アクション
print("\n投擲アクション:")
throw_action = ThrowAction(player, dungeon)
print("  ThrowAction 作成: OK")

# 杖アクション
print("\n杖アクション:")
wand_action = WandAction(player, dungeon)
print("  WandAction 作成: OK")

# 指輪アクション
print("\n指輪アクション:")
ring_action = RingAction(player)
print("  RingAction 作成: OK")
```

---

### フェーズ 5: 仕上げと外部ファイル

#### テスト 5.1: セーブ/ロードの確認
```python
# python/test_save_load.py
import sys
import os
sys.path.insert(0, '.')

from save_manager import SaveManager, GameState, create_game_state, restore_game_state
from entities import Player
from dungeon import DungeonLevel

# セーブ/ロードの確認
print("セーブ/ロードの確認:")

# ゲーム状態を作成
player = Player()
player.name = "テストプレイヤー"
player.hp_current = 20
player.hp_max = 20
player.gold = 100
player.cur_level = 1

dungeon = DungeonLevel(level=1)

game_state = create_game_state(
    player=player,
    dungeon=dungeon,
    cur_level=1,
    max_level=1,
    gold=100
)

print(f"  プレイヤー: {player.name}")
print(f"  HP: {player.hp_current}/{player.hp_max}")
print(f"  GOLD: {player.gold}")

# セーブ
print("\nセーブ:")
save_manager = SaveManager()
filename = "test_save.sav"
success = save_manager.save_game(game_state, filename)
print(f"  セーブ結果: {success}")

# ロード
print("\nロード:")
loaded_state = save_manager.load_game(filename)
if loaded_state:
    print(f"  ロード成功")
    print(f"  プレイヤー: {loaded_state.player.name}")
    print(f"  HP: {loaded_state.player.hp_current}/{loaded_state.player.hp_max}")
    print(f"  GOLD: {loaded_state.player.gold}")
else:
    print(f"  ロード失敗")

# ファイルを削除
if os.path.exists(filename):
    os.remove(filename)
    print(f"\nテストファイルを削除: {filename}")
```

#### テスト 5.2: スコアリングの確認
```python
# python/test_score.py
import sys
import os
sys.path.insert(0, '.')

from score_manager import ScoreManager
from entities import Player

# スコアリングの確認
print("スコアリングの確認:")

player = Player()
player.name = "テストプレイヤー"
player.hp_current = 20
player.hp_max = 20
player.gold = 1000
player.cur_level = 5

score_manager = ScoreManager()

# スコア記録
print("\nスコア記録:")
score_manager.killed_by("ドラゴン", 0, player)

# ハイスコア表示
print("\nハイスコア:")
scores = score_manager.get_high_scores()
for i, entry in enumerate(scores):
    print(f"  {i+1}. {entry.name}: {entry.score}g - {entry.cause}")

# テストファイルを削除
if os.path.exists(score_manager.score_file):
    os.remove(score_manager.score_file)
    print(f"\nテストファイルを削除: {score_manager.score_file}")
```

#### テスト 5.3: テキストリソースの確認
```python
# python/test_text_resources.py
import sys
sys.path.insert(0, '.')

from text_resources import TextResources, get_message, set_language

# テキストリソースの確認
print("テキストリソースの確認:")

# 日本語メッセージ
print("\n日本語メッセージ:")
tr = TextResources("ja")
print(f"  ようこそ: {tr.get(0)}")
print(f"  終了します: {tr.get(1)}")
print(f"  ゲームオーバー: {tr.get(52)}")
print(f"  勝利: {tr.get(53)}")

# 英語メッセージ
print("\n英語メッセージ:")
tr_en = TextResources("en")
print(f"  Welcome: {tr_en.get(0)}")
print(f"  Goodbye: {tr_en.get(1)}")
print(f"  Game Over: {tr_en.get(52)}")
print(f"  Victory: {tr_en.get(53)}")

# グローバル関数の確認
print("\nグローバル関数:")
print(f"  get_message(0) (ja): {get_message(0)}")
set_language("en")
print(f"  get_message(0) (en): {get_message(0)}")
set_language("ja")
print(f"  get_message(0) (ja): {get_message(0)}")
```

---

## デバッグ手順

### 1. ログ出力の追加

`python/debug.py`を作成:

```python
import logging
import sys
from datetime import datetime

def setup_logging(level=logging.DEBUG):
    """ログ出力を設定"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # ファイルハンドラ
    file_handler = logging.FileHandler('debug.log', encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # コンソールハンドラ
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # ルートロガーに追加
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return logging.getLogger(__name__)

def log_function_call(func):
    """関数呼び出しをログに記録するデコレータ"""
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"呼び出し: {func.__name__}({args}, {kwargs})")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"戻り値: {result}")
            return result
        except Exception as e:
            logger.error(f"エラー: {e}")
            raise
    return wrapper
```

### 2. ユニットテストの作成

`python/tests/`ディレクトリを作成し、以下のテストファイルを作成:

```python
# python/tests/test_const.py
import unittest
import sys
sys.path.insert(0, '..')

import const

class TestConst(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(const.ROGUE_LINES, 23)
        self.assertEqual(const.ROGUE_COLUMNS, 80)
        self.assertEqual(const.MIN_ROW, 1)
        self.assertEqual(const.MAX_PACK_COUNT, 23)
    
    def test_helper_functions(self):
        self.assertTrue(const.is_monster(0x10))
        self.assertTrue(const.is_object(0x20))
        self.assertTrue(const.is_floor(0x01))
        self.assertTrue(const.is_wall(0x04))
        self.assertTrue(const.is_passable(0x01))
        self.assertFalse(const.is_passable(0x04))

if __name__ == '__main__':
    unittest.main()
```

テストの実行:
```bash
cd python/tests
python -m unittest test_const.py
```

### 3. 統合テストの作成

`python/tests/test_integration.py`を作成:

```python
import unittest
import sys
sys.path.insert(0, '..')

from entities import Player, Monster, Item
from dungeon import DungeonLevel
from level_generator import LevelGenerator
from combat import Combat
import const

class TestIntegration(unittest.TestCase):
    def test_full_game_flow(self):
        """完全なゲームフローのテスト"""
        # プレイヤーを作成
        player = Player()
        player.hp_current = 20
        player.hp_max = 20
        player.exp = 0
        player.row = 10
        player.col = 40
        
        # ダンジョンを作成
        dungeon = DungeonLevel(level=1)
        
        # レベルを生成
        generator = LevelGenerator(dungeon, player)
        generator.make_level()
        
        # レベルが生成されたことを確認
        self.assertGreater(len(dungeon.rooms), 0)
        self.assertGreater(len(dungeon.monsters), 0)
        
        # モンスターが配置されていることを確認
        monster = dungeon.monsters[0]
        self.assertIsNotNone(monster)
        
        # 戦闘システムを作成
        combat = Combat(player, dungeon)
        
        # プレイヤーが攻撃
        original_hp = monster.hp_to_kill
        combat.rogue_hit(monster)
        
        # モンスターのHPが減少したことを確認
        self.assertLessEqual(monster.hp_to_kill, original_hp)

if __name__ == '__main__':
    unittest.main()
```

---

## トラブルシューティング

### 1. モジュールインポートエラー

#### 問題: `ModuleNotFoundError: No module named 'xxx'`

**解決策:**
1. `sys.path` を確認
2. `__init__.py` が存在するか確認
3. モジュール名が正しいか確認

```python
import sys
print("Python path:")
for p in sys.path:
    print(f"  {p}")
```

### 2. cursesエラー

#### 問題: `ModuleNotFoundError: No module named '_curses'` (Windows)

**解決策:**
```bash
pip install windows-curses
```

#### 問題: `curses.error: setupterm: could not find terminal`

**解決策:**
- Windows Terminal または適切なターミナルエミュレータを使用
- 環境変数 `TERM` を設定: `set TERM=xterm-256color`

### 3. 定数の未定義エラー

#### 問題: `NameError: name 'XXX' is not defined`

**解決策:**
1. `const.py` に定数が定義されているか確認
2. モジュールが正しくインポートされているか確認
3. 循環インポートがないか確認

### 4. 属性エラー

#### 問題: `AttributeError: 'XXX' object has no attribute 'YYY'`

**解決策:**
1. クラス定義を確認
2. 属性が初期化されているか確認
3. クラスの継承関係を確認

### 5. 型エラー

#### 問題: `TypeError: unsupported operand type(s)`

**解決策:**
1. 型変換を追加
2. 型ヒントを確認
3. 演算子のオーバーロードを確認

---

## 実行手順のまとめ

### 1. 環境構築

#### Windows (cmd.exe)
```cmd
cd m:\src\Rogue2.Official-master
python -m venv venv
venv\Scripts\activate
pip install windows-curses
```

#### Windows (PowerShell)
```powershell
cd m:\src\Rogue2.Official-master
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install windows-curses
```

#### Ubuntu Linux
```bash
# プロジェクトディレクトリに移動
cd /path/to/Rogue2.Official-master

# Python 3と開発ツールのインストール（必要な場合）
sudo apt-get update
sudo apt-get install python3 python3-venv python3-dev libncurses5-dev

# 仮想環境の作成
python3 -m venv venv

# 仮想環境の有効化
source venv/bin/activate

# 依存関係のインストール（cursesはシステムにインストール済み）
pip install -r python/requirements.txt
```

#### macOS
```bash
# プロジェクトディレクトリに移動
cd /path/to/Rogue2.Official-master

# Homebrewでncursesをインストール（必要な場合）
brew install ncurses

# 仮想環境の作成
python3 -m venv venv

# 仮想環境の有効化
source venv/bin/activate

# 依存関係のインストール
pip install -r python/requirements.txt
```

### 2. テストの実行

#### Windows
```cmd
cd python
python test_imports.py
python test_const.py
python test_entities.py
python test_dungeon.py
python test_main.py
python test_utils.py
python test_level_generation.py
python test_movement.py
python test_inventory.py
python test_combat.py
python test_special_actions.py
python test_save_load.py
python test_score.py
python test_text_resources.py

cd tests
python -m unittest discover
```

#### Ubuntu Linux / macOS
```bash
# モジュールインポート確認
cd python
python3 test_imports.py

# 各モジュールのテスト
python3 test_const.py
python3 test_entities.py
python3 test_dungeon.py
python3 test_main.py
python3 test_utils.py
python3 test_level_generation.py
python3 test_movement.py
python3 test_inventory.py
python3 test_combat.py
python3 test_special_actions.py
python3 test_save_load.py
python3 test_score.py
python3 test_text_resources.py

# ユニットテスト
cd tests
python3 -m unittest discover
```

### 3. ゲームの実行

#### Windows
```cmd
cd python
python main.py

# スコアのみ表示
python main.py --score

# セーブファイルから復元
python main.py --restore save.sav
```

#### Ubuntu Linux / macOS
```bash
# ゲームの実行
cd python
python3 main.py

# スコアのみ表示
python3 main.py --score

# セーブファイルから復元
python3 main.py --restore save.sav
```

### 4. Ubuntu Linux用の詳細な実行手順

```bash
# ============================================
# Ubuntu Linuxでの完全な実行手順
# ============================================

# 1. システムの更新と必要なパッケージのインストール
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-dev libncurses5-dev git

# 2. プロジェクトディレクトリに移動
cd /path/to/Rogue2.Official-master

# 3. 仮想環境の作成
python3 -m venv venv

# 4. 仮想環境の有効化
source venv/bin/activate

# 5. 依存関係のインストール
pip install -r python/requirements.txt

# 6. モジュールインポート確認
cd python
python3 test_imports.py

# 7. 各モジュールのテスト（個別実行）
python3 test_const.py
python3 test_entities.py
python3 test_dungeon.py
python3 test_main.py
python3 test_utils.py
python3 test_level_generation.py
python3 test_movement.py
python3 test_inventory.py
python3 test_combat.py
python3 test_special_actions.py
python3 test_save_load.py
python3 test_score.py
python3 test_text_resources.py

# 8. ユニットテストの実行
cd tests
python3 -m unittest discover

# 9. ゲームの実行
cd ..
python3 main.py

# 10. 仮想環境の終了
deactivate
```

---

## 次のステップ

この手順書に従って、段階的に動作確認を行い、問題があればデバッグ手順に従って修正してください。すべてのテストが通過したら、実際のゲームプレイを開始できます。

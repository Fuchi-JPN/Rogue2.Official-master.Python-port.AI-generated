# Python版とC言語版の初期値比較レポート

## 概要
このドキュメントは、Rogue2.OfficialのPython移植版における全ての変数の初期値をC言語版と比較した結果をまとめたものです。

---

## 1. Player クラス (struct fighter) の初期値比較

### 1.1 一致している初期値

| フィールド | C言語版 | Python版 | 状態 |
|-----------|---------|----------|------|
| armor | 0 (NULL) | None | ✅ |
| weapon | 0 (NULL) | None | ✅ |
| left_ring | 0 (NULL) | None | ✅ |
| right_ring | 0 (NULL) | None | ✅ |
| hp_current | INIT_HP (12) | const.INIT_HP (12) | ✅ |
| hp_max | INIT_HP (12) | const.INIT_HP (12) | ✅ |
| str_current | 16 | 16 | ✅ |
| str_max | 16 | 16 | ✅ |
| pack | {0} (空) | None | ✅ |
| gold | 0 | 0 | ✅ |
| exp | 1 | 1 | ✅ |
| exp_points | 0 | 0 | ✅ |
| row | 0 | 0 | ✅ |
| col | 0 | 0 | ✅ |
| fchar | '@' | ord('@') | ✅ |
| moves_left | 1250 | 1250 | ✅ (修正済み) |

### 1.2 Python版に存在しないC言語版のフィールド

なし（全てのC言語版フィールドがPython版に存在）

### 1.3 C言語版に存在しないPython版のフィールド

| フィールド | Python初期値 | 問題点 |
|-----------|-------------|--------|
| hunger | const.HUNGRY (300) | ❌ C言語版には存在しない。空腹状態はmoves_leftで管理 |
| dungeon_level | 1 | ❌ C言語版のstruct fighterには存在しない（cur_levelはグローバル変数） |
| is_blind | False | ❌ C言語版ではグローバル変数 `blind` |
| is_confused | False | ❌ C言語版ではグローバル変数 `confused` |
| is_hallucinating | False | ❌ C言語版ではグローバル変数 `halluc` |
| is_levitating | False | ❌ C言語版ではグローバル変数 `levitate` |
| is_hasted | False | ❌ C言語版ではグローバル変数 `haste_self` |
| is_seeing_invisible | False | ❌ C言語版ではグローバル変数 `see_invisible` |
| stealth_bonus | 0 | ❌ C言語版のstruct fighterには存在しない |
| regeneration_bonus | 0 | ❌ C言語版のstruct fighterには存在しない |
| slow_digest | False | ❌ C言語版のstruct fighterには存在しない |
| searching_bonus | 0 | ❌ C言語版のstruct fighterには存在しない |
| sustain_strength | False | ❌ C言語版のstruct fighterには存在しない |
| maintain_armor | False | ❌ C言語版のstruct fighterには存在しない |
| trap_damage | 0 | ❌ C言語版のstruct fighterには存在しない |

---

## 2. グローバル変数の初期値比較

### 2.1 use.c / use_actions.py

| 変数名 | C言語版 | Python版 | 状態 |
|--------|---------|----------|------|
| halluc | 0 | 0 | ✅ |
| blind | 0 | 0 | ✅ |
| confused | 0 | 0 | ✅ |
| levitate | 0 | 0 | ✅ |
| haste_self | 0 | 0 | ✅ |
| see_invisible | 0 (False) | False | ✅ |
| extra_hp | 0 | 0 | ✅ |
| detect_monster | 0 (False) | False | ✅ |
| being_held | 0 (False) | False | ✅ |
| bear_trap | 0 | 0 | ✅ |
| sustain_strength | ❌ 存在しない | False | ❌ Python版にのみ存在 |

### 2.2 move.c / actions.py

| 変数名 | C言語版 | Python版 | 状態 |
|--------|---------|----------|------|
| m_moves | 0 | 0 | ✅ |
| jump | 1 (ORIGINAL) / 0 (非ORIGINAL) | False | ⚠️ デフォルト値が異なる |
| bent_passage | 未初期化 | False | ⚠️ C言語版は未初期化 |
| bear_trap | 0 (trap.c) | 0 | ✅ |
| trap_door | 0 (trap.c) | False | ✅ |

### 2.3 level.c / グローバル

| 変数名 | C言語版 | Python版 | 状態 |
|--------|---------|----------|------|
| cur_level | 0 | - | ⚠️ Python版ではMovementインスタンス変数 |
| max_level | 1 | - | ⚠️ Python版ではMovementインスタンス変数 |
| party_room | NO_ROOM | - | ⚠️ Python版ではMovementインスタンス変数 |
| party_counter | 未初期化 (init.c で設定) | - | ⚠️ Python版では別の場所 |

### 2.4 init.c / グローバル

| 変数名 | C言語版 | Python版 | 状態 |
|--------|---------|----------|------|
| login_name | 未初期化 | - | - |
| nick_name | "" | - | - |
| rest_file | 0 | - | - |
| cant_int | 0 | - | - |
| did_int | 0 | - | - |
| score_only | 0 | - | - |
| init_curses | 0 | - | - |
| save_is_interactive | 1 | - | - |
| show_skull | 1 | - | - |
| ask_quit | 1 | - | - |
| pass_go | 1 | - | - |
| do_restore | 0 | - | - |
| use_color | 1 | - | - |

---

## 3. 重要な相違点と修正が必要な項目

### 3.1 高優先度（ゲーム動作に影響）

#### ❌ Player.hunger フィールド
- **問題**: C言語版には存在しないフィールドが追加されている
- **C言語版の動作**: 空腹状態は `moves_left` で管理
  - `moves_left <= HUNGRY (300)`: 空腹
  - `moves_left <= WEAK (150)`: 弱り
  - `moves_left <= FAINT (20)`: 気絶
  - `moves_left <= STARVE (0)`: 餓死
- **推奨修正**: `hunger` フィールドを削除し、`moves_left` で管理

#### ⚠️ jump 変数のデフォルト値
- **C言語版**: `#if defined(ORIGINAL)` で 1、それ以外は 0
- **Python版**: `False` (0)
- **影響**: 移動中の表示動作が変わる可能性
- **推奨**: 互換性のため `True` に設定

### 3.2 中優先度（アーキテクチャの違い）

#### ⚠️ プレイヤー状態の管理方法
- **C言語版**: グローバル変数で管理 (`blind`, `confused`, `halluc` 等)
- **Python版**: Playerクラスのインスタンス変数 (`is_blind`, `is_confused` 等)
- **影響**: 状態の参照・更新方法が異なる
- **推奨**: どちらの方法でも動作するが、グローバル変数を使用する方がC言語版に近い

#### ⚠️ レベル関連変数
- **C言語版**: グローバル変数 `cur_level`, `max_level`, `party_room`
- **Python版**: Movementクラスのインスタンス変数
- **影響**: 複数のクラス間での共有が困難になる可能性
- **推奨**: グローバル変数またはGameクラスで管理

### 3.3 低優先度（動作に影響しない）

#### Python版にのみ存在するフィールド
以下のフィールドはC言語版のstruct fighterには存在しないが、ゲーム動作には直接影響しない：
- `stealth_bonus`, `regeneration_bonus`, `slow_digest`, `searching_bonus`
- `sustain_strength`, `maintain_armor`, `trap_damage`

これらは指輪の効果等を管理するために追加されたと思われるが、C言語版では別の方法で実装されている。

---

## 4. 修正推奨事項

### 4.1 即時修正が必要

1. **Player.hunger フィールドの削除**
   - `moves_left` で空腹状態を管理するように変更
   - `hunger` プロパティを削除し、`moves_left` ベースの判定に変更

### 4.2 検討が必要

1. **jump 変数**
   - デフォルト値を `True` に変更するか、設定で切り替え可能にする

2. **グローバル変数の統一**
   - `cur_level`, `max_level` 等をグローバル変数またはGameクラスで一元管理

3. **状態変数の管理方法**
   - Playerクラスのインスタンス変数とグローバル変数の二重管理を避ける

---

## 5. 検証方法

### 5.1 テストケース

```python
def test_player_initial_values():
    """Player初期値がC言語版と一致することを確認"""
    player = Player()
    
    # 装備
    assert player.armor is None
    assert player.weapon is None
    assert player.left_ring is None
    assert player.right_ring is None
    
    # ステータス
    assert player.hp_current == 12  # INIT_HP
    assert player.hp_max == 12
    assert player.str_current == 16
    assert player.str_max == 16
    
    # 所持金・経験値
    assert player.gold == 0
    assert player.exp == 1
    assert player.exp_points == 0
    
    # 位置
    assert player.row == 0
    assert player.col == 0
    
    # 表示文字
    assert player.fchar == ord('@')
    
    # 空腹度（重要！）
    assert player.moves_left == 1250  # C言語版と同じ
```

---

## 6. 結論

Python移植版の初期値は概ねC言語版と一致していますが、以下の重要な相違点があります：

1. **Player.hunger フィールド**: C言語版には存在せず、`moves_left` で管理すべき
2. **jump 変数**: デフォルト値が異なる
3. **状態変数の管理**: グローバル変数 vs インスタンス変数の違い

これらの相違点を修正することで、C言語版と同じ動作を再現できます。

---

作成日: 2026-02-15

# Rogue2.Official C言語版とPython移植版の相違点リスト_v1.0

## 🔴 重要度: 致命的バグ（ゲーム進行に影響）

### 1. 方向キーマッピングの誤り ([`python/actions.py:451-460`](python/actions.py:451))
**C言語版** ([`src/hit.c:340-388`](src/hit.c:340) `get_dir_rc`):
```c
case 'u':  // row--, col++ = UPRIGHT
case 'b':  // row++, col-- = DOWNLEFT
```
**Python版** (誤り):
```python
'u': const.DOWNLEFT,   # ← 誤り! UPRIGHTであるべき
'b': const.UPRIGHT,    # ← 誤り! DOWNLEFTであるべき
```
**修正方法**: 'u'と'b'のマッピングを入れ替える

---

### 2. モンスターテーブルの重複定義とデータ不一致

**問題**: 2つのファイルに異なるモンスターテーブルが定義されている

| ファイル | MON_TAB構造 | M_NAMES |
|---------|------------|---------|
| [`python/entities.py:280-317`](python/entities.py:280) | dict形式、26体 | 26種類（日本語名） |
| [`python/combat.py:36-75`](python/combat.py:36) | tuple形式、26体 | 25種類（日本語名、内容が異なる） |

**C言語版** ([`src/monster.c:40-67`](src/monster.c:40)): 単一の`mon_tab[MONSTERS]`配列

**修正方法**: `combat.py`のMON_TABとM_NAMESを削除し、`entities.py`の定義を使用

---

### 3. モンスターデータ構造のフィールド不一致

**C言語版** ([`src/rogue.h:200-222`](src/rogue.h:200) `struct obj`):
```c
m_flags, damage, quantity(hp_to_kill), ichar, kill_exp, 
is_protected(first_level), is_cursed(last_level), class(m_hit_chance), 
identified(stationary_damage), which_kind(drop_percent), ...
```

**Python版** ([`python/combat.py:47-75`](python/combat.py:47)):
```python
# tuple形式: (flags, damage, first_level, m_char, kill_exp, 
#            m_hit_chance, hp_to_kill, last_level, steal_gold, ...)
```
**問題**: フィールド順序がC言語版と一致していない

---

## 🟠 重要度: 高（機能不全）

### 4. `dungeon.monsters`属性の不存在

**Python版** ([`python/combat.py:300-301`](python/combat.py:300)):
```python
if monster in self.dungeon.monsters:  # ← AttributeError!
    self.dungeon.monsters.remove(monster)
```
**C言語版**: `level_monsters`連結リストを使用

**修正方法**: `DungeonLevel`クラスに`monsters`リストを追加、または`level_monsters`を使用

---

### 5. `roll_damage`関数のシグネチャ不一致

**Python版** ([`python/combat.py:126`](python/combat.py:126)):
```python
damage = utils.roll_damage(monster.m_damage, 1)
```
**utils.pyの定義**:
```python
def roll_damage(damage_str: str) -> int:  # 第2引数なし
```
**修正方法**: `roll_damage`の第2引数を削除するか、関数定義に引数を追加

---

### 6. `get_direction_offset`への引数型エラー

**Python版** ([`python/combat.py:347`](python/combat.py:347)):
```python
dr, dc = get_direction_offset(dirch)  # dirchは文字
```
**dungeon.pyの定義**:
```python
def get_direction_offset(direction: int) -> Tuple[int, int]:  # intを期待
```
**修正方法**: 文字から方向定数への変換を追加

---

## 🟡 重要度: 中（動作不一致）

### 7. `is_passable`関数の呼び出し方法

**C言語版** ([`src/move.c:296-306`](src/move.c:296)):
```c
int is_passable(int row, int col) {
    return (int)(dungeon[row][col] & (FLOOR | TUNNEL | DOOR | STAIRS | TRAP));
}
```
**Python版** ([`python/combat.py:703`](python/combat.py:703)):
```python
if not const.is_passable(self.dungeon.dungeon[row][col]):  # タイル値を渡す
```
**修正方法**: `const.is_passable(tile_value)`または`self.is_passable(row, col)`に統一

---

### 8. `mon_damage`関数の戻り値の意味逆転

**C言語版** ([`src/hit.c:263-294`](src/hit.c:263)):
```c
// 戻り値: 0 = 死亡, 1 = 生存
if (monster->hp_to_kill <= 0) {
    return 0;  // 死亡
}
return 1;  // 生存
```
**Python版** ([`python/actions.py:603-614`](python/actions.py:603)):
```python
def mon_damage(self, monster: Monster, damage: int) -> bool:
    monster.hp -= damage
    if monster.hp <= 0:
        return True  # 死亡
    return False  # 生存
```
**影響**: `rogue_hit`での判定ロジックが逆になる可能性

---

### 9. `heal`関数の静的変数の扱い

**C言語版** ([`src/move.c:552-577`](src/move.c:552)):
```c
static short heal_exp = -1, n, c = 0;
static boolean alt;
```
**Python版** ([`python/actions.py:418-446`](python/actions.py:418)):
```python
def _heal(self):
    heal_exp = -1  # ローカル変数（毎回リセット）
    n = 0
    c = 0
    alt = False
```
**修正方法**: インスタンス変数またはクラス変数として保持

---

### 10. `party_monsters`でのタプル変更エラー

**Python版** ([`python/combat.py:523-550`](python/combat.py:523)):
```python
MON_TAB[i] = (MON_TAB[i][0] & ~const.ASLEEP, ...)  # TypeError!
```
**問題**: タプルは不変（immutable）のため変更できない

**修正方法**: リストに変換するか、新しいタプルを作成してリスト全体を更新

---

## 🟢 重要度: 低（コード品質・互換性）

### 11. 属性名の不一致

| C言語版 | Python版 | 状態 |
|---------|----------|------|
| `dungeon[row][col]` | `dungeon.dungeon[row][col]` | 要確認 |
| `rogue.pack` | `player.pack` | ✅ 正常な改名 |
| `obj.what_is` | `item.item_type` | ✅ 正常な改名 |
| `monster.m_char` | `monster.m_char` | ✅ 一致 |
| `monster.quantity` (hp) | `monster.hp` / `monster.quantity` | 要統一 |

---

### 12. 未実装・スタブ関数

以下の関数が`const.CANCEL`を返すか、空実装:

- [`python/inventory.py:420-428`](python/inventory.py:420) `_pack_letter()`
- [`python/combat.py:408-411`](python/combat.py:408) `_get_direction()`
- [`python/combat.py:388-391`](python/combat.py:388) `_special_hit()`
- [`python/combat.py:403-406`](python/combat.py:403) `_cough_up()`
- [`python/combat.py:970-983`](python/combat.py:970) `_flame_broil()`, `_seek_gold()`, `_m_confuse()`

---

### 13. グローバル変数のスコープ問題

**C言語版**: ファイルスコープのextern変数
```c
extern short cur_level, max_level, cur_room;
extern boolean being_held, detect_monster;
```
**Python版**: クラスインスタンス変数またはモジュール変数として分散
- `actions.py`: `m_moves`, `bear_trap`, `bent_passage`
- `combat.py`: `fight_monster`, `hit_message`, `wizard`
- `use_actions.py`: `halluc`, `blind`, `confused`, etc.

**修正方法**: グローバル状態を`GameState`クラス等に集約

---

### 14. `mask_room`関数の未実装

**C言語版** ([`src/level.c:543-558`](src/level.c:543)): `mask_room()`関数が存在
**Python版**: `level_generator.py`に未実装

---

### 15. `fill_it`関数での`mask_room`呼び出し

**C言語版** ([`src/level.c:486-490`](src/level.c:486)):
```c
if ((!do_rec_de) || did_this || (!mask_room(rn, &srow, &scol, TUNNEL))) {
    srow = (rooms[rn].top_row + rooms[rn].bottom_row) / 2;
    scol = (rooms[rn].left_col + rooms[rn].right_col) / 2;
}
```
**Python版** ([`python/level_generator.py:486-494`](python/level_generator.py:486)): `mask_room`呼び出しなし

---

## 📋 推奨修正優先順位

1. **最優先**: 方向キーマッピング修正（バグ#1）
2. **高**: モンスターテーブル統合（バグ#2, #3）
3. **高**: `dungeon.monsters`属性追加（バグ#4）
4. **中**: 関数シグネチャ統一（バグ#5, #6, #7）
5. **中**: 戻り値・静的変数修正（バグ#8, #9）
6. **低**: 未実装関数の完全実装
7. **低**: グローバル状態管理の整理

---

以上の相違点リストに基づき、Python移植版の修正とデバッグを行ってください。
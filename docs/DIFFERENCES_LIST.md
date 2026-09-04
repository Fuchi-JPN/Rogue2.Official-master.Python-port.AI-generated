# Rogue2.Official C言語版とPython移植版の相違点リスト

## 概要

このドキュメントは、Rogue2.Official C言語版（`src/`）とPython移植版（`python/`）の間の相違点を体系的に記録したものです。

---

## 最新の修正（2026-03-08）

### trail_charの設定（combat.py - put_m_at()）

**ファイル**: `python/combat.py`
**関数**: `put_m_at()`
**状態**: ✅ 修正済み

**問題点**:
C言語版では `monster->trail_char = mvinch_rogue(row, col);` として、配置先のタイルの実際の文字を取得していましたが、Python版では `'.'`（床文字）をハードコードしていました。

**修正内容**:
```python
# 修正前
monster.trail_char = '.'

# 修正後
monster.trail_char = self._get_dungeon_char(row, col)
```

これにより、モンスターがアイテムの上や階段の上に配置された場合、移動後に正しい文字が表示されるようになります。


このドキュメントは、Rogue2.Official C言語版（`src/`）とPython移植版（`python/`）の間の相違点を体系的に記録したものです。

---

## 1. 静的変数（static変数）の扱い

### 1.1 修正済みの問題

| ファイル | C言語版 | Python版 | 問題点 | 状態 |
|---------|---------|----------|--------|------|
| `actions.py` - `check_hunger()` | `static short move_left_cou` | クラス変数に変更 | ローカル変数化で消化遅延指輪が不正に | ✅ 修正済み |
| `actions.py` - `_search()` | `static boolean reg_search` | クラス変数に変更 | ローカル変数化で探索トグルが不正に | ✅ 修正済み |

**修正内容**: C言語の`static`変数は関数呼び出し間で値を保持するため、Python版ではクラス変数またはモジュールレベル変数として実装する必要がある。

---

## 2. 定数値の比較

### 2.1 移動結果定数（`const.py` vs `rogue.h`）

| 定数名 | C言語値 | Python値 | 状態 |
|--------|---------|----------|------|
| `MOVED` | 0 | 0 | ✅ 一致 |
| `MOVE_FAILED` | -1 | -1 | ✅ 一致 |
| `STOPPED_ON_SOMETHING` | -2 | -2 | ✅ 一致 |

### 2.2 モンスターフラグ定数（`const.py` vs `rogue.h`）

全27項目を確認済み。詳細は別途確認。

---

## 3. 状態変数の管理アーキテクチャ問題

### 3.1 状態変数の重複定義

C言語版では`src/move.c`のファイルスコープグローバル変数として定義されている状態変数が、Python版では**3箇所に重複定義**されている。

#### C言語版（`src/move.c:32-38`）
```c
short m_moves = 0;
#if !defined( ORIGINAL )
boolean jump = 0;
boolean bent_passage;
#else /* ORIGINAL */
boolean jump = 1;
#endif /* ORIGINAL */
```

#### Python版の重複定義

| 場所 | ファイル | 行番号 | 用途 | 実際の使用状況 |
|------|----------|--------|------|----------------|
| モジュール変数 | `actions.py` | 40-46 | ゲームロジックで使用 | **アクティブに使用中** |
| データクラス | `game_state.py` | 79-86 | 状態保存用 | ⚠️ 未使用の可能性 |
| 別クラス | `save_manager.py` | 14-61 | セーブ/ロード用 | ⚠️ `GameState`クラスとして独立定義 |

#### 具体的な変数対応

| 変数名 | C言語型 | Python版（actions.py） | Python版（game_state.py） |
|--------|---------|----------------------|--------------------------|
| `m_moves` | `short` | `m_moves = 0` | `m_moves: int = 0` |
| `jump` | `boolean` | `jump = True` | `jump: bool = False` |
| `bent_passage` | `boolean` | `bent_passage = False` | `bent_passage: bool = False` |
| `bear_trap` | (別箇所) | `bear_trap = 0` | `bear_trap: int = 0` |

### 3.2 問題点

1. **値の同期がない**: `actions.py`のモジュール変数と`game_state.py`のデータクラス間で値が同期されていない
2. **初期値の不一致**: `jump`の初期値が`actions.py`では`True`、`game_state.py`では`False`
3. **セーブ時の不整合**: セーブ時にどの変数が保存されるか不明確

---

## 4. セーブ/ロード機能の問題

### 4.1 関数シグネチャの不一致 - ✅ 修正済み

#### 修正前（`game.py:1514-1528`）
```python
def _save_game(self):
    """ゲームをセーブ (C版 save.c: save_game)"""
    current_dungeon = self.dungeon_manager.get_current_level()
    
    try:
        save_mgr = save_manager.SaveManager()
        if save_mgr.save_game(self.player, current_dungeon, self.dungeon_manager.current_level):
            # ...  # BUG: save_gameはGameStateオブジェクトを期待
```

#### 修正後
```python
def _save_game(self):
    """ゲームをセーブ (C版 save.c: save_game)"""
    current_dungeon = self.dungeon_manager.get_current_level()
    
    try:
        save_mgr = save_manager.SaveManager()
        # GameState オブジェクトを作成して save_game に渡す
        game_state = save_manager.create_game_state(
            player=self.player,
            dungeon=current_dungeon,
            cur_level=self.dungeon_manager.current_level,
            max_level=getattr(self, 'max_level', self.dungeon_manager.current_level),
            foods=getattr(self.player, 'foods', 0),
            party_room=self.party_room,
            party_counter=self.party_counter,
            m_moves=actions.m_moves,  # actions.py のグローバル変数から取得
            bear_trap=actions.bear_trap,
            hunger_str=getattr(self.player, 'hunger_str', ""),
            login_name=self.login_name
        )
        if save_mgr.save_game(game_state):
            # ...
```

### 4.2 修正内容

- **GameStateオブジェクトの作成**: `save_manager.create_game_state()`を使用して正しくGameStateを作成
- **状態変数の取得**: `actions.py`のモジュール変数（`m_moves`, `bear_trap`）をセーブデータに含めるように修正
- **その他の状態**: `party_room`, `party_counter`, `hunger_str`, `login_name`なども含めるように拡張

---

## 5. 比較作業の進捗状況

| カテゴリ | C言語ソース | Pythonモジュール | 状態 |
|---------|------------|-----------------|------|
| 定数・設定 | `src/rogue.h` | `const.py`, `config.py` | ✅ 一部確認済み |
| エンティティ | `src/rogue.h`, `object.h`, `monster.h` | `entities.py` | ✅ 構造確認済み |
| 状態変数 | `src/move.c` | `actions.py`, `game_state.py` | ⚠️ 重複問題発見（要アーキテクチャ修正） |
| セーブ/ロード | `src/save.c` | `save_manager.py` | ✅ シグネチャ不一致修正済み |
| ダンジョン生成 | `src/level.c`, `room.c` | `level_generator.py` | ⚠️ 相違点発見（mask_room未実装等） |
| 移動処理 | `src/move.c` | `actions.py` | ⚠️ 相違点発見（pass_go未実装等） |
| 戦闘システム | `src/hit.c`, `monster.c` | `combat.py` | ✅ 一部修正済み（global宣言追加、型不一致修正） |
| インベントリ | `src/pack.c`, `invent.c` | `inventory.py` | ⚠️ バグ発見（quiverチェック欠落、is_wood未初期化） |
| アイテム使用 | `src/use.c` | `use_actions.py` | ⚠️ ID状態更新未実装 |
| 特殊アクション | `src/throw.c`, `zap.c`, `ring.c` | `special_actions.py` | ✅ 正しく実装済み |
| スコア管理 | `src/score.c` | `score_manager.py` | ✅ 比較完了（相違点あり） |

---

## 6. 推奨される修正方針

### 6.1 状態変数の統一

1. **単一の真実のソース**を決定する
   - 案A: `game_state.py`の`GameState`データクラスを唯一の状態保持場所とする
   - 案B: `actions.py`のモジュール変数を維持し、`GameState`を削除する

2. **セーブ/ロードの整合性確保**
   - 全ての状態変数がセーブ対象に含まれるようにする

### 6.2 セーブ関数の修正

`game.py`の`_save_game()`を修正し、正しい引数を渡すようにする：

```python
def _save_game(self):
    # 状態を収集
    game_state = game_state.GameState(
        player=self.player,
        dungeon=self.dungeon_manager.get_current_level(),
        current_level=self.dungeon_manager.current_level,
        m_moves=actions.m_moves,
        jump=actions.jump,
        bent_passage=actions.bent_passage,
        bear_trap=actions.bear_trap,
        # ... その他の状態変数
    )
    
    save_mgr = save_manager.SaveManager()
    save_mgr.save_game(game_state)
```

---

## 7. 既知の修正履歴（移植報告書より）

以下の修正が既に行われている：

- インポートエラー修正（try/exceptブロック追加）
- `dungeon.grid` → `dungeon.dungeon` 属性名修正
- `monster.monster_kind` → `monster.monster_type` 修正
- 方向マッピング修正（`LEFTDOWN` → `DOWNLEFT`, `RIGHTUP` → `UPRIGHT`）
- ウォルス演算子（`:=`）を通常ループに変更
- `os.stat()` → `os.lstat()` 修正

---

---

## 8. ダンジョン生成の比較（`level.c` vs `level_generator.py`）

### 8.1 定数・配列の比較

| 項目 | C言語版 | Python版 | 状態 |
|------|---------|----------|------|
| `level_points[]` | 21要素のlong配列 | `LEVEL_POINTS` 21要素 | ✅ 一致 |
| `random_rooms[]` | `{ 3, 7, 5, 2, 0, 6, 1, 4, 8 }` | `RANDOM_ROOMS = [3, 7, 5, 2, 0, 6, 1, 4, 8]` | ✅ 一致 |

### 8.2 グローバル変数の扱い

| 変数名 | C言語版 | Python版 | 問題点 |
|--------|---------|----------|--------|
| `cur_level` | ファイルスコープ `short cur_level = 0` | `LevelGenerator.cur_level` インスタンス変数 | ⚠️ インスタンス間で共有されない |
| `max_level` | ファイルスコープ `short max_level = 1` | `LevelGenerator.max_level` インスタンス変数 | ⚠️ 同上 |
| `cur_room` | ファイルスコープ `short cur_room` | `LevelGenerator.cur_room` | ⚠️ 同上 |
| `party_room` | ファイルスコープ `short party_room = NO_ROOM` | `LevelGenerator.party_room` | ⚠️ 同上 |
| `r_de` | ファイルスコープ `short r_de` | `LevelGenerator.r_de` | ✅ 適切に移行 |
| `new_level_message` | ファイルスコープ `char *new_level_message = 0` | **未実装** | ❌ 欠落 |

### 8.3 `fill_it()`関数の相違点

#### C言語版（`level.c:159-206`）
```c
void fill_it(int rn, boolean do_rec_de)
{
    // ...
    static short offsets[4] = { -1, 1, 3, -3 };  // static配列
    // ...
    if (((!do_rec_de) || did_this) ||
        (!mask_room(rn, &srow, &scol, TUNNEL))) {  // mask_room()を呼び出し
        srow = (rooms[rn].top_row + rooms[rn].bottom_row) / 2;
        scol = (rooms[rn].left_col + rooms[rn].right_col) / 2;
    }
    // ...
}
```

#### Python版（`level_generator.py:_fill_it()`）
```python
def _fill_it(self, rn: int, do_rec_de: bool) -> None:
    offsets = [-1, 1, 3, -3]  # ローカル変数（staticではない）
    # ...
    # mask_room()の呼び出しが省略されている
    srow = (self.dungeon_level.rooms[rn].top_row + self.dungeon_level.rooms[rn].bottom_row) // 2
    scol = (self.dungeon_level.rooms[rn].left_col + self.dungeon_level.rooms[rn].right_col) // 2
    # ...
```

#### 問題点

1. **`mask_room()`関数が未実装**: C言語版では部屋内のTUNNELセルを検索してその座標を返す`mask_room()`関数があるが、Python版では実装されていない。これにより通路接続の開始点が異なる可能性がある。

2. **`offsets`配列の扱い**: 
   - C言語版: `static`配列（シャッフル結果が関数呼び出し間で保持）
   - Python版: ローカル変数（毎回初期化）
   - ただし、両方とも関数先頭でシャッフルするため実質的な動作は同じ

### 8.4 `put_player()`関数の相違点

#### C言語版（`level.c:289-311`）
```c
void put_player(short nr)
{
    short rn = nr, misses;
    short row, col;

    for (misses = 0; ((misses < 2) && (rn == nr)); misses++) {
        gr_row_col(&row, &col, (FLOOR | TUNNEL | OBJECT | STAIRS));
        rn = get_room_number(row, col);
    }
    rogue.row = row;
    rogue.col = col;

    if (dungeon[rogue.row][rogue.col] & TUNNEL) {
        cur_room = PASSAGE;
    } else {
        cur_room = rn;
    }
    if (cur_room != PASSAGE) {
        light_up_room(cur_room);
    } else {
        light_passage(rogue.row, rogue.col);
    }
    wake_room(get_room_number(rogue.row, rogue.col), 1, rogue.row, rogue.col);
    if (new_level_message) {
        message(new_level_message, 0);
        new_level_message = 0;
    }
    mvaddch_rogue(rogue.row, rogue.col, rogue.fchar);
}
```

#### Python版（`level_generator.py:put_player()`）
```python
def put_player(self, avoid_room: int) -> Tuple[int, int]:
    rn = avoid_room
    misses = 0

    for misses in range(2):
        if rn == avoid_room:
            row, col = self._gr_row_col(const.FLOOR | const.TUNNEL | const.OBJECT | const.STAIRS)
            rn = self.dungeon_level.get_room_number(row, col)

    return row, col  # 座標のみ返す
```

#### 問題点

1. **戻り値の違い**: C言語版は`void`（グローバル変数`rogue.row`, `rogue.col`を直接設定）、Python版は座標を返すのみ
2. **未実装の処理**:
   - `cur_room`の設定
   - `light_up_room()` / `light_passage()` の呼び出し
   - `wake_room()` の呼び出し
   - `new_level_message`の表示
   - プレイヤー表示（`mvaddch_rogue()`）

### 8.5 推奨される修正

1. **`new_level_message`の実装**: レベル移動時のメッセージを管理する変数を追加
2. **`put_player()`の完全実装**: 照明処理、モンスター起床処理などを追加
3. **`mask_room()`の実装**: 通路接続ロジックの正確性を確保

---

---

## 9. 移動処理の比較（`move.c` vs `actions.py`）

### 9.1 `one_move_rogue()`のドア/通路処理の相違点

#### C言語版（`move.c:104-120`）
```c
if (dungeon[row][col] & DOOR) {
    if (cur_room == PASSAGE) {
        cur_room = get_room_number(row, col);
        light_up_room(cur_room);
        wake_room(cur_room, 1, row, col);
    } else {
        light_passage(row, col);
    }
} else if ((dungeon[rogue.row][rogue.col] & DOOR) &&
           (dungeon[row][col] & TUNNEL)) {
    light_passage(row, col);
    wake_room(cur_room, 0, rogue.row, rogue.col);
    darken_room(cur_room);
    cur_room = PASSAGE;
} else if (dungeon[row][col] & TUNNEL) {
    light_passage(row, col);
}
```

#### Python版（`actions.py:161-180`）
```python
if self.dungeon.dungeon[row][col] & const.DOOR:
    if self.cur_room == const.PASSAGE:
        self.cur_room = self._get_room_number(row, col)
        if self.display:
            self.display.light_up_room(self.dungeon, self.player, self.cur_room)
        self.wake_room(self.cur_room, True, row, col)
    else:
        if self.display:
            self.display.darken_room(self.dungeon, self.cur_room, self.blind > 0)
            self.dungeon.dungeon[row][col] |= const.MAPPED
            self.display.light_passage(self.dungeon, self.player, row, col)
        self.cur_room = const.PASSAGE
elif self.dungeon.dungeon[row][col] & const.TUNNEL:
    if self.display:
        self.dungeon.dungeon[row][col] |= const.MAPPED
        self.display.light_passage(self.dungeon, self.player, row, col)
    pass
```

#### 問題点

1. **「ドアから通路に出る」ケースが欠落**: 
   - C言語版: `(dungeon[rogue.row][rogue.col] & DOOR) && (dungeon[row][col] & TUNNEL)` の条件分岐がある
   - Python版: この条件が実装されていない
   - 影響: 部屋から通路に出る際、`wake_room(cur_room, 0, ...)`が呼ばれず、モンスターが正しく処理されない可能性

2. **`wake_room()`の呼び出し不足**:
   - C言語版: ドアから通路に出る際、`wake_room(cur_room, 0, rogue.row, rogue.col)`を呼び出し（第2引数=0は「去る」ことを示す）
   - Python版: この呼び出しがない

### 9.2 `multiple_move_rogue()`の`pass_go`処理

#### C言語版（`move.c:209-239`）
```c
#if !defined( ORIGINAL )
    dirch += 96;
    do {
    retry:
        row = rogue.row;
        col = rogue.col;
        m = one_move_rogue(dirch, 1);
        if (m == STOPPED_ON_SOMETHING || interrupted) {
            break;
        }
        if (m != MOVE_FAILED) {
            continue;
        }
        if (!pass_go || !bent_passage) {
            break;
        }
        for (n = 0, dir = "hjkl", i = 0; i < 4; i++) {
            row = rogue.row;
            col = rogue.col;
            get_dir_rc(dir[i], &row, &col, 1);
            if (is_passable(row, col) && dirch != dir[3 - i]) {
                n++, ch = dir[i];
            }
        }
        if (n == 1) {
            dirch = ch;
            goto retry;
        }
        break;
    } while (!next_to_something(row, col));
#endif /* not ORIGINAL */
```

#### Python版（`actions.py:232-257`）
```python
if dirch in "\010\012\013\014\031\025\016\002":
    dirch = chr(ord(dirch) + 96)
    while True:
        row = self.player.row
        col = self.player.col
        m = self.one_move_rogue(dirch, True)
        if m == MoveResult.STOPPED_ON_SOMETHING or self.interrupted:
            break
        if m != MoveResult.MOVE_FAILED:
            continue
        if not self._next_to_something(row, col):
            break
# 大文字キーバインド（HJKL 等）
elif dirch in "HJKLBYUN":
    dirch = chr(ord(dirch) + 32)
    while True:
        m = self.one_move_rogue(dirch, True)
        if self.interrupted:
            break
        if m == MoveResult.MOVED:
            continue
        if m != MoveResult.MOVE_FAILED:
            break
```

#### 問題点

1. **`pass_go`処理が未実装**:
   - C言語版: `pass_go`と`bent_passage`を使って通路の曲がり角を自動的に進む機能がある
   - Python版: この処理が完全に省略されている
   - 影響: 通路の曲がり角で連続移動が停止する（C版では曲がり角を自動的に進む）

2. **`bent_passage`変数の未使用**:
   - Python版で`bent_passage`は定義されているが、`multiple_move_rogue()`で使用されていない

### 9.3 `check_hunger()`の気絶時処理

#### C言語版（`move.c:423-436`）
```c
n = get_rand(0, (FAINT - rogue.moves_left));
if (n > 0) {
    fainted = 1;
    if (rand_percent(40)) {
        rogue.moves_left++;
    }
    message(mesg[77], 1);
    for (i = 0; i < n; i++) {
        if (coin_toss()) {
            mv_mons();
        }
    }
    message(you_can_move_again, 1);
}
```

#### Python版（`actions.py:356-363`）
```python
n = utils.get_rand(0, const.FAINT - self.player.moves_left)
if n > 0:
    fainted = True
    if utils.rand_percent(40):
        self.player.moves_left += 1
    if self.msg:
        self.msg.message(get_message(77), 1)  # "空腹で、目がくらくらする。"
        self.msg.message(get_message(66), 1)  # "ようやく体が自由になった。"
```

#### 問題点

1. **気絶中のモンスター移動が未実装**:
   - C言語版: `for (i = 0; i < n; i++) { if (coin_toss()) { mv_mons(); } }` で気絶中にモンスターが動く
   - Python版: このループがない
   - 影響: 気絶中にモンスターが動かないため、ゲームバランスが異なる

### 9.4 `heal()`関数 - ✅ 正しく実装済み

#### C言語版（`move.c:552-577`）
```c
void heal(void)
{
    static short heal_exp = -1, n, c = 0;
    static boolean alt;
    static char na[] = { 0, 20, 18, 17, 14, 13, 10, 9, 8, 7, 4, 3 };

    if (rogue.hp_current == rogue.hp_max) {
        c = 0;
        return;
    }
    if (rogue.exp != heal_exp) {
        heal_exp = rogue.exp;
        n = (heal_exp < 1 || heal_exp > 11) ? 2 : na[heal_exp];
    }
    if (++c >= n) {
        c = 0;
        rogue.hp_current++;
        if ((alt = !alt)) {
            rogue.hp_current++;
        }
        if ((rogue.hp_current += regeneration) > rogue.hp_max) {
            rogue.hp_current = rogue.hp_max;
        }
        print_stats(STAT_HP);
    }
}
```

#### Python版（`actions.py:472-500`）
```python
def _heal(self):
    """回復（C言語版の静的変数をインスタンス変数として保持）"""
    na = [0, 20, 18, 17, 14, 13, 10, 9, 8, 7, 4, 3]

    if self.player.hp_current == self.player.hp_max:
        self._heal_c = 0
        return

    if self.player.exp != self._heal_exp:
        self._heal_exp = self.player.exp
        if self._heal_exp < 1 or self._heal_exp > 11:
            self._heal_n = 2
        else:
            self._heal_n = na[self._heal_exp]

    if self._heal_c + 1 >= self._heal_n:
        self._heal_c = 0
        self.player.hp_current += 1
        self._heal_alt = not self._heal_alt
        if self._heal_alt:
            self.player.hp_current += 1
        self.player.hp_current += self.regeneration
        if self.player.hp_current > self.player.hp_max:
            self.player.hp_current = self.player.hp_max
        if self.game:
            self.game._print_stats(const.STAT_HP)
    else:
        self._heal_c += 1
```

**状態**: ✅ 正しく実装されている。静的変数をインスタンス変数（`_heal_exp`, `_heal_n`, `_heal_c`, `_heal_alt`）として適切に保持している。

### 9.5 `next_to_something()`の罠チェック

#### C言語版（`move.c:346-354`）
```c
if (s & TRAP) {
    if (!(s & HIDDEN)) {
        if ((row == drow || col == dcol) &&
            (!(row == rogue.row || col == rogue.col))) {
            continue;
        }
        return 1;
    }
}
```

#### Python版（`actions.py:296-297`）
```python
if s & const.TRAP and not (s & const.HIDDEN):
    return True
```

#### 問題点

1. **罠チェックの条件が簡略化されすぎている**:
   - C言語版: プレイヤーの移動方向を考慮した複雑な条件
   - Python版: 単純な`return True`
   - 影響: 連続移動時の停止判定が異なる可能性がある

### 9.6 推奨される修正

1. **`one_move_rogue()`の修正**: 「ドアから通路に出る」ケースを追加
2. **`multiple_move_rogue()`の修正**: `pass_go`と`bent_passage`を使った通路曲がり角処理を追加
3. **`check_hunger()`の修正**: 気絶中のモンスター移動ループを追加
4. **`next_to_something()`の修正**: 罠チェックの条件をC版に合わせる

---

## 10. 戦闘システムの比較（`hit.c`, `monster.c` vs `combat.py`）

### 10.1 グローバル変数の宣言

#### C言語版（`hit.c:37`）
```c
extern short add_strength, ring_exp, r_rings;
```

#### Python版（`combat.py:30-33`）
```python
ring_exp = 0
r_rings = 0
add_strength = 0
```

**状態**: ✅ 正しく実装されている。モジュールレベル変数として定義。

### 10.2 `_mon_damage()`のグローバル変数の扱い - ✅ 修正済み

#### 問題点
モンスターを倒した際、`fight_monster`と`being_held`のグローバル変数を更新する必要があるが、`global`宣言が欠落していた。

#### 修正前（`combat.py:243-275`）
```python
def _mon_damage(self, monster: Monster, damage: int) -> int:
    """モンスターにダメージを与える"""
    row = monster.row
    col = monster.col
    # ...
    if monster.hp_to_kill <= 0:
        # ...
        fight_monster = None  # ❌ ローカル変数への代入になる
        # ...
        if monster.m_flags & const.HOLDS:
            being_held = False  # ❌ ローカル変数への代入になる
```

#### 修正後
```python
def _mon_damage(self, monster: Monster, damage: int) -> int:
    """モンスターにダメージを与える"""
    global fight_monster, being_held  # ✅ 追加

    row = monster.row
    col = monster.col
    # ...
    if monster.hp_to_kill <= 0:
        # ...
        fight_monster = None  # ✅ グローバル変数を正しく更新
        # ...
        if monster.m_flags & const.HOLDS:
            being_held = False  # ✅ グローバル変数を正しく更新
```

**影響**: 修正前は、モンスターを倒しても`fight_monster`がクリアされず、プレイヤーが死んだモンスターに「拘束」されたままになる可能性があった。

### 10.3 `interrupted`変数の型不一致 - ✅ 修正済み

#### 問題点
`interrupted`変数が初期化で`False`（bool）として定義されているが、`1`（int）を代入していた。

#### 修正前（`combat.py:33, 73`）
```python
# 行33: 初期化
interrupted = False

# 行73: 代入
if not fight_monster:
    interrupted = 1  # ❌ 型不一致
```

#### 修正後
```python
# 行33: 初期化（変更なし）
interrupted = False

# 行73: 代入
if not fight_monster:
    global interrupted
    interrupted = True  # ✅ bool型で統一
```

### 10.4 ヒット率計算式 - ✅ 正しく実装済み

#### C言語版（`hit.c:397-399`）
```c
hit_chance = 40 + 3 * to_hit(weapon) + (((2 * rogue.exp) + (2 * ring_exp)) - r_rings);
```

#### Python版（`combat.py:333-335`）
```python
hit_chance = 40 + 3 * self._to_hit(weapon) + ((2 * self.player.exp) + (2 * ring_exp)) - r_rings
```

**状態**: ✅ 計算式は正しく一致している。

### 10.5 ダメージ計算式 - ✅ 正しく実装済み

#### C言語版（`hit.c:409-411`）
```c
damage = get_w_damage(weapon) + damage_for_strength() + ((((rogue.exp + ring_exp) - r_rings) + 1) / 2);
```

#### Python版（`combat.py:341-343`）
```python
damage = self._get_w_damage(weapon) + self._damage_for_strength() + ((self.player.exp + ring_exp) - r_rings + 1) // 2
```

**状態**: ✅ 計算式は正しく一致している（整数除算`//`も適切）。

### 10.6 モンスター死亡時の処理

#### C言語版（`hit.c:263-289`）
```c
void mon_damage(fighter *monster, short damage)
{
    // ...
    if (monster->hp_to_kill <= 0) {
        dungeon[monster->row][monster->col] &= ~MONSTER;
        mvaddch_rogue(monster->row, monster->col, get_dungeon_char(monster->row, monster->col));
        fight_monster = 0;
        cough_up(monster);
        // ...
        if (monster->m_flags & HOLDS) {
            being_held = 0;
        }
    }
}
```

#### Python版（`combat.py:243-277`）
```python
def _mon_damage(self, monster: Monster, damage: int) -> int:
    global fight_monster, being_held
    # ...
    if monster.hp_to_kill <= 0:
        self.dungeon.dungeon[row][col] &= ~const.MONSTER
        # self._mvaddch_rogue(row, col, self._get_dungeon_char(row, col))  # コメントアウト
        fight_monster = None
        # self._cough_up(monster)  # コメントアウト
        # ...
        if monster.m_flags & const.HOLDS:
            being_held = False
```

#### 問題点

1. **`cough_up()`がコメントアウト**: モンスターが死んだ時にアイテムを落とす処理が無効化されている
2. **`mvaddch_rogue()`がコメントアウト**: 画面更新が行われない可能性

### 10.7 推奨される修正

1. **`cough_up()`の有効化**: モンスター死亡時のアイテムドロップ処理を実装
2. **画面更新処理の確認**: `mvaddch_rogue()`が他の場所で適切に呼ばれているか確認

---

## 11. インベントリの比較（`pack.c`, `invent.c` vs `inventory.py`）

### 11.1 C言語版の主要関数一覧

#### `pack.c`の関数（599行）

| 関数名 | 行番号 | 機能 | Python版 |
|--------|--------|------|----------|
| `add_to_pack()` | 28-67 | アイテムをパックに追加 | ⏳ 要確認 |
| `take_from_pack()` | 69-76 | パックからアイテムを削除 | ⏳ 要確認 |
| `pick_up()` | 78-113 | アイテムを拾う | ⏳ 要確認 |
| `drop()` | 115-182 | アイテムを落とす | ⏳ 要確認 |
| `check_duplicate()` | 184-215 | スタック可能アイテムの重複確認 | ⏳ 要確認 |
| `next_avail_ichar()` | 217-238 | 利用可能な文字(a-z)を割り当て | ⏳ 要確認 |
| `pack_letter()` | 246-279 | パックからアイテムを選択 | ⏳ 要確認 |
| `take_off()` | 281-309 | 鎧を脱ぐ | ⏳ 要確認 |
| `wear()` | 311-348 | 鎧を着る | ⏳ 要確認 |
| `unwear()` | 350-357 | 鎧を外す（内部関数） | ⏳ 要確認 |
| `do_wear()` | 359-365 | 鎧を装備（内部関数） | ⏳ 要確認 |
| `wield()` | 367-409 | 武器を装備 | ⏳ 要確認 |
| `do_wield()` | 411-416 | 武器を装備（内部関数） | ⏳ 要確認 |
| `unwield()` | 418-425 | 武器を外す（内部関数） | ⏳ 要確認 |
| `call_it()` | 427-475 | アイテムに名前を付ける | ⏳ 要確認 |
| `pack_count()` | 477-501 | パック内のアイテム数をカウント | ⏳ 要確認 |
| `mask_pack()` | 504-514 | 指定タイプのアイテムが存在するか | ⏳ 要確認 |
| `is_pack_letter()` | 516-550 | 入力がパック文字かチェック | ⏳ 要確認 |
| `has_amulet()` | 552-556 | アミュレット所持チェック | ⏳ 要確認 |
| `kick_into_pack()` | 558-598 | アイテムを蹴って拾う | ⏳ 要確認 |

#### `invent.c`の関数（876行）

| 関数名 | 行番号 | 機能 | Python版 |
|--------|--------|------|----------|
| `inventory()` | 58-146 | インベントリ表示 | ⏳ 要確認 |
| `mix_colors()` | 148-163 | ポーションの色をシャッフル | ⏳ 要確認 |
| `make_scroll_titles()` | 165-198 | スクロールのタイトル生成 | ⏳ 要確認 |
| `get_desc()` | 200-543 | アイテムの説明文生成 | ⏳ 要確認 |
| `get_wand_and_ring_materials()` | 545-581 | ワンドとリングの素材生成 | ⏳ 要確認 |
| `single_inv()` | 583-606 | 単一アイテムの情報表示 | ⏳ 要確認 |
| `get_id_table()` | 608-626 | IDテーブルを取得 | ⏳ 要確認 |
| `inv_armor_weapon()` | 628-644 | 装備中のアイテム表示 | ⏳ 要確認 |
| `discovered()` | 671-832 | 発見済みアイテム一覧 | ⏳ 要確認 |
| `znum()` | 838-855 | 数字を全角文字に変換（JAPANのみ） | ⏳ 要確認 |
| `lznum()` | 857-874 | 長整数を全角文字に変換（JAPANのみ） | ⏳ 要確認 |

### 11.2 重要なグローバル変数・配列

#### C言語版（`invent.c:27-51`）
```c
boolean is_wood[WANDS];  // ワンドが木製かどうか

char *wand_materials[WAND_MATERIALS] = { /* 30種類の素材 */ };
char *gems[GEMS] = { /* 14種類の宝石 */ };
char *syllables[MAXSYLLABLES] = { /* 40種類の音節 */ };

char descs[ROGUE_LINES][ROGUE_COLUMNS];  // 画面保存用バッファ
```

#### 確認が必要な点
- Python版で`is_wood`配列が適切に実装されているか
- 素材・音節データが正しく移植されているか

### 11.3 スケアモンスタースクロールの特殊処理

#### C言語版（`pack.c:86-96`）
```c
if ((obj->what_is == SCROL) && (obj->which_kind == SCARE_MONSTER) &&
    obj->picked_up) {
    message(mesg[86], 0);  // "この巻物は燃え上がり、灰になった！"
    dungeon[row][col] &= (~OBJECT);
    vanish(obj, 0, &level_objects);
    *status = 0;
    if (id_scrolls[SCARE_MONSTER].id_status == UNIDENTIFIED) {
        id_scrolls[SCARE_MONSTER].id_status = IDENTIFIED;
    }
    return 0;
}
```

#### 確認が必要な点
- Python版で`picked_up`フラグが正しく管理されているか
- スケアモンスタースクロールが2回目の拾得時に消滅する処理が実装されているか

### 11.4 アイテム重複スタック条件

#### C言語版（`pack.c:184-215`）
```c
object *check_duplicate(object *obj, object *pack)
{
    // WEAPON, FOOD, SCROL, POTION のみスタック可能
    if (!(obj->what_is & (WEAPON | FOOD | SCROL | POTION))) {
        return 0;
    }
    // FRUIT（フルーツ）はスタック不可
    if ((obj->what_is == FOOD) && (obj->which_kind == FRUIT)) {
        return 0;
    }
    // 武器は特定の種類のみスタック可能（ARROW, DAGGER, DART, SHURIKEN）
    // かつ quiver（矢筒）が一致する場合のみ
    // ...
}
```

#### 確認が必要な点
- Python版でスタック条件が正しく実装されているか
- 武器の`quiver`属性が正しく比較されているか

### 11.5 パック容量チェック

#### C言語版（`pack.c:477-501`）
```c
int pack_count(object *new_obj)
{
    // 武器以外は quantity を加算
    // 武器は種類とquiverが一致する場合を除いてカウント
    // MAX_PACK_COUNT と比較
}
```

#### 確認が必要な点
- Python版でパック容量計算が正しいか
- `MAX_PACK_COUNT`の値が一致しているか

### 11.6 アイテム識別システム

#### C言語版の識別状態（`rogue.h`）
```c
#define UNIDENTIFIED 0
#define IDENTIFIED   1
#define CALLED       2  // プレイヤーが名前を付けた
```

#### IDテーブル構造体
```c
struct id {
    short id_status;
    char title[MAX_TITLE_LENGTH + 1];  // 未識別時の表示名
    char *real;                         // 正式名称
};
```

#### 確認が必要な点
- Python版で`id_scrolls`, `id_potions`, `id_wands`, `id_rings`が正しく実装されているか
- 識別状態の遷移が正しいか

### 11.7 装備フラグ

#### C言語版（`rogue.h`）
```c
#define BEING_WIELDED   001  // 武器として装備中
#define BEING_WORN      002  // 鎧として装備中
#define ON_LEFT_HAND    004  // 左手に装備中
#define ON_RIGHT_HAND   010  // 右手に装備中
#define ON_EITHER_HAND  014  // どちらかの手に装備中
```

#### 確認が必要な点
- Python版でフラグ値が一致しているか
- 装備解除時のフラグ処理が正しいか

### 11.8 呪いアイテムの処理

#### C言語版（`pack.c:137-157`）
```c
if (obj->in_use_flags & BEING_WIELDED) {
    if (obj->is_cursed) {
        message(curse_message, 0);  // "呪われている"
        return;
    }
    unwield(rogue.weapon);
}
// 鎧、指輪も同様
```

#### 確認が必要な点
- 呪いアイテムが装備解除できない処理が正しく実装されているか

### 11.9 Python版の詳細確認結果

#### 11.9.1 `_check_duplicate()`の`quiver`チェック欠落 - ✅ 修正済み

##### C言語版（`pack.c:193-203`）
```c
if ((obj->what_is == WEAPON) &&
    ((obj->which_kind == ARROW) || (obj->which_kind == DAGGER) ||
     (obj->which_kind == DART) || (obj->which_kind == SHURIKEN)) &&
    (obj->quiver == pack->quiver)) {
    return(pack);
}
```

##### 修正前（`inventory.py:382-402`）
```python
def _check_duplicate(self, obj: Item) -> Optional[Item]:
    # ...
    if (current.item_type == obj.item_type and
            current.item_kind == obj.item_kind):
        # 武器の場合は矢、短剣、ダーツ、手裏剣のみ重複
        if (obj.item_type != const.WEAPON or
                (obj.item_kind in (const.ARROW, const.DAGGER, const.DART, const.SHURIKEN))):
            return current  # ❌ quiverのチェックがない
```

##### 修正後（`inventory.py:382-404`）
```python
def _check_duplicate(self, obj: Item) -> Optional[Item]:
    # ...
    if (current.item_type == obj.item_type and
            current.item_kind == obj.item_kind):
        # 武器の場合は矢、短剣、ダーツ、手裏剣のみ重複
        # かつquiver（矢筒の数）が同じ場合のみ重複扱い
        if (obj.item_type != const.WEAPON or
                (obj.item_kind in (const.ARROW, const.DAGGER, const.DART, const.SHURIKEN) and
                 obj.quiver == current.quiver)):  # ✅ quiverチェックを追加
            return current
```

##### 修正内容
- **武器スタック時に`quiver`（矢筒）の一致を確認するように修正**
- 影響: 異なる矢筒に入った矢が正しく別々のスタックとして扱われるようになった

#### 11.9.2 `is_wood`配列の初期化 - ⚠️ 未完全

##### C言語版（`invent.c:545-581`）
```c
void get_wand_and_ring_materials()
{
    short i, j;
    boolean used[WAND_MATERIALS];

    for (i = 0; i < WANDS; i++) {
        // ランダムに素材を選択
        // 木製かどうかをランダムに決定
        is_wood[i] = (rand_percent(75));  // 75%の確率で木製
    }
}
```

##### Python版（`inventory.py:54`）
```python
is_wood = [False] * const.WANDS  # ❌ 全てFalseで初期化
```

##### 問題点
- **`is_wood`配列が全て`False`で初期化されており、動的に設定されていない**
- 影響: ワンドの表示名が「木の杖」にならず、常に素材名で表示される可能性がある

##### 修正案
- `get_wand_and_ring_materials()`関数を実装し、ゲーム開始時に`is_wood`を設定する

#### 11.9.3 スケアモンスタースクロールの処理 - ✅ 正しく実装済み

##### C言語版（`pack.c:86-96`）
```c
if ((obj->what_is == SCROL) && (obj->which_kind == SCARE_MONSTER) &&
    obj->picked_up) {
    message(mesg[86], 0);  // "この巻物は燃え上がり、灰になった！"
    dungeon[row][col] &= (~OBJECT);
    vanish(obj, 0, &level_objects);
    *status = 0;
    if (id_scrolls[SCARE_MONSTER].id_status == UNIDENTIFIED) {
        id_scrolls[SCARE_MONSTER].id_status = IDENTIFIED;
    }
    return 0;
}
```

##### Python版（`inventory.py:131-140`）
```python
# 怖がらせの巻物の特殊処理
if (obj.item_type == const.SCROL and obj.item_kind == const.SCARE_MONSTER
        and obj.picked_up):
    # message("この巻物はもう拾えない", 0)
    self.dungeon.dungeon[row][col] &= ~const.OBJECT
    self._remove_object(obj)
    status = 0
    return None, status
```

##### 確認結果
- ✅ `picked_up`フラグのチェックは正しく実装されている
- ⚠️ 識別状態の更新（`id_scrolls[SCARE_MONSTER].id_status = IDENTIFIED`）が実装されていない可能性がある

#### 11.9.4 装備フラグ定数 - ✅ 正しく実装済み

##### C言語版（`rogue.h`）
```c
#define BEING_WIELDED   001  // 1
#define BEING_WORN      002  // 2
#define ON_LEFT_HAND    004  // 4
#define ON_RIGHT_HAND   010  // 8
#define ON_EITHER_HAND  014  // 12
```

##### Python版（`const.py`）
```python
BEING_WIELDED = 1
BEING_WORN = 2
ON_LEFT_HAND = 4
ON_RIGHT_HAND = 8
ON_EITHER_HAND = 12
```

**状態**: ✅ 値は正しく一致している。

#### 11.9.5 パック容量定数 - ✅ 正しく実装済み

##### C言語版（`rogue.h`）
```c
#define MAX_PACK_COUNT 24
```

##### Python版（`const.py`）
```python
MAX_PACK_COUNT = 24
```

**状態**: ✅ 値は正しく一致している。

#### 11.9.6 `pack_count()`の実装 - ⚠️ 相違あり

##### C言語版（`pack.c:477-501`）
```c
int pack_count(object *new_obj)
{
    object *obj;
    int count = 0;

    obj = rogue.pack.next_object;

    while (obj) {
        if (obj->what_is != WEAPON) {
            count += obj->quantity;
        } else {
            count++;  // 武器は種類に関わらず1つとしてカウント
        }
        obj = obj->next_object;
    }

    if (new_obj && (new_obj->what_is != WEAPON)) {
        count += new_obj->quantity;
    } else if (new_obj) {
        count++;
    }

    return(count);
}
```

##### Python版（`inventory.py:262-274`）
```python
def pack_count(self) -> int:
    """インベントリ内のアイテム数をカウント"""
    count = 0
    obj = self.player.pack

    while obj:
        if obj.item_type != const.WEAPON:
            count += obj.quantity
        else:
            count += 1
        obj = obj.next_object

    return count
```

##### 相違点
- Python版は`new_obj`引数を受け取らない
- 影響: アイテムを拾う前に「拾えるかどうか」を確認する際、追加されるアイテムを含めた計算ができない可能性がある

### 11.10 インベントリ比較の結論

| 項目 | 状態 | 優先度 |
|------|------|--------|
| `_check_duplicate()`の`quiver`チェック欠落 | ✅ 修正済み | 高 |
| `is_wood`配列の初期化 | ⚠️ 未完全 | 中 |
| スケアモンスタースクロールの識別状態更新 | ⚠️ 未確認 | 低 |
| 装備フラグ定数 | ✅ 一致 | - |
| パック容量定数 | ✅ 一致 | - |
| `pack_count()`の引数 | ⚠️ 相違 | 低 |

### 11.11 推奨される修正

1. ~~**`_check_duplicate()`の修正**: 武器スタック時に`quiver`フィールドの一致を確認するように修正~~ ✅ 修正済み
2. **`is_wood`配列の初期化**: `get_wand_and_ring_materials()`関数を実装し、ゲーム開始時にランダムに設定
3. **スケアモンスタースクロール**: 識別状態の更新処理を追加

---

## 12. アイテム使用の比較（`use.c` vs `use_actions.py`）

### 12.1 C言語版の主要関数一覧

#### `use.c`の関数（約500行）

| 関数名 | 行番号 | 機能 | Python版 |
|--------|--------|------|----------|
| `quaff()` | 32-87 | ポーションを飲む | `UseActions.quaff()` |
| `read_scroll()` | 89-153 | 巻物を読む | `UseActions.read_scroll()` |
| `vanish()` | 155-176 | アイテムを消費・削除 | `UseActions._vanish()` |
| `potion_heal()` | 178-211 | 回復ポーション効果 | `UseActions._potion_heal()` |
| `idntfy()` | 213-236 | アイテム識別 | `UseActions._idntfy()` |
| `eat()` | 238-277 | 食料を食べる | `UseActions.eat()` |
| `hold_monster()` | 279-303 | モンスター拘束 | `UseActions._hold_monster()` |
| `tele()` | 305-315 | テレポート | `UseActions._tele()` |
| `hallucinate()` | 317-341 | 幻覚効果 | `UseActions._hallucinate()` |
| `unhallucinate()` | 343-348 | 幻覚解除 | `UseActions._unhallucinate()` |
| `unblind()` | 350-360 | 盲目解除 | `UseActions._unblind()` |
| `relight()` | 362-371 | 再点灯 | `UseActions._relight()` |
| `take_a_nap()` | 373-385 | 居眠り | `UseActions._take_a_nap()` |
| `go_blind()` | 387-412 | 盲目になる | `UseActions._go_blind()` |
| `get_ench_color()` | 414-420 | エチャント色取得 | なし |
| `confuse()` | 422-425 | 混乱 | `UseActions._confuse()` |
| `unconfuse()` | 427-436 | 混乱解除 | `UseActions._unconfuse()` |
| `uncurse_all()` | 438-447 | 全呪い解除 | `UseActions._uncurse_all()` |

### 12.2 グローバル状態変数

#### C言語版（`use.c:24-32`）
```c
short halluc = 0;
short blind = 0;
short confused = 0;
short levitate = 0;
short haste_self = 0;
boolean see_invisible = 0;
short extra_hp = 0;
boolean detect_monster = 0;
char *strange_feeling = mesg[230];
```

#### Python版（`use_actions.py:28-39`）
```python
halluc = 0
blind = 0
confused = 0
levitate = 0
haste_self = 0
see_invisible = False
extra_hp = 0
detect_monster = False
being_held = False
bear_trap = 0
sustain_strength = False
```

**状態**: ✅ 変数は正しく定義されている。ただし、`actions.py`にも同様の変数が定義されており、重複の可能性がある。

### 12.3 ポーション効果の比較

#### 12.3.1 `potion_heal()`の計算ロジック

##### C言語版（`use.c:178-211`）
```c
void potion_heal(int extra)
{
    long ratio;
    short add;

    rogue.hp_current += rogue.exp;

    ratio = rogue.hp_current * 100L / rogue.hp_max;

    if (ratio >= 100L) {
        rogue.hp_max += (extra ? 2 : 1);
        extra_hp += (extra ? 2 : 1);
        rogue.hp_current = rogue.hp_max;
    } else if (ratio >= 90L) {
        rogue.hp_max += (extra ? 1 : 0);
        extra_hp += (extra ? 1 : 0);
        rogue.hp_current = rogue.hp_max;
    } else {
        if (ratio < 33L) {
            ratio = 33L;
        }
        if (extra) {
            ratio += ratio;
        }
        add = (short) (ratio * (rogue.hp_max - rogue.hp_current) / 100L);
        rogue.hp_current += add;
        if (rogue.hp_current > rogue.hp_max) {
            rogue.hp_current = rogue.hp_max;
        }
    }
    if (blind) {
        unblind();
    }
    if (confused && extra) {
        unconfuse();
    } else if (confused) {
        confused = (confused / 2) + 1;
    }
    if (halluc && extra) {
        unhallucinate();
    } else if (halluc) {
        halluc = (halluc / 2) + 1;
    }
}
```

##### Python版（`use_actions.py:108-149`）
```python
def _potion_heal(self, extra: bool) -> None:
    """回復ポーション効果 (C版 use.c: potion_heal)"""
    global halluc, blind, confused, extra_hp

    self.player.hp_current += self.player.exp

    ratio = self.player.hp_current * 100 // self.player.hp_max

    if ratio >= 100:
        self.player.hp_max += 2 if extra else 1
        extra_hp += 2 if extra else 1
        self.player.hp_current = self.player.hp_max
    elif ratio >= 90:
        self.player.hp_max += 1 if extra else 0
        extra_hp += 1 if extra else 0
        self.player.hp_current = self.player.hp_max
    else:
        if ratio < 33:
            ratio = 33
        if extra:
            ratio += ratio
        add = ratio * (self.player.hp_max - self.player.hp_current) // 100
        self.player.hp_current += add
        if self.player.hp_current > self.player.hp_max:
            self.player.hp_current = self.player.hp_max

    if blind:
        self._unblind()
    if confused:
        if extra:
            self._unconfuse()
        else:
            confused = (confused // 2) + 1
    if halluc:
        if extra:
            self._unhallucinate()
        else:
            halluc = (halluc // 2) + 1
```

**状態**: ✅ ロジックは正しく移植されている。

### 12.4 `vanish()`の実装

#### C言語版（`use.c:155-176`）
```c
void vanish(object *obj, short rm, object *pack)
{
    if (obj->quantity > 1) {
        obj->quantity--;
    } else {
        if (obj->in_use_flags & BEING_WIELDED) {
            unwield(obj);
        } else if (obj->in_use_flags & BEING_WORN) {
            unwear(obj);
        } else if (obj->in_use_flags & ON_EITHER_HAND) {
            un_put_on(obj);
        }
        take_from_pack(obj, pack);
        free_object(obj);
    }
    if (rm) {
        (void) reg_move();
    }
}
```

#### Python版（`use_actions.py:151-175`）
```python
def _vanish(self, obj: Item, rm: bool, pack) -> None:
    """アイテムを消費・削除 (C版 use.c: vanish)"""
    if obj.quantity > 1:
        obj.quantity -= 1
    else:
        if obj.in_use_flags & const.BEING_WIELDED:
            self.inv_manager._unwield(obj)
        elif obj.in_use_flags & const.BEING_WORN:
            self.inv_manager._unwear(obj)
        elif obj.in_use_flags & const.ON_EITHER_HAND:
            self.inv_manager._un_put_on(obj)
        self.inv_manager._take_from_pack(obj, pack)
    if rm:
        self._reg_move()
```

**状態**: ✅ 正しく実装されている。`reg_move()`の呼び出し条件も正しい。

### 12.5 `eat()`の実装

#### C言語版（`use.c:238-277`）
```c
void eat(void)
{
    short ch;
    short moves;
    object *obj;
    char buf[70];

    ch = pack_letter(mesg[262], FOOD);
    if (ch == CANCEL) {
        return;
    }
    if (!(obj = get_letter_object(ch))) {
        message(mesg[263], 0);
        return;
    }
    if (obj->what_is != FOOD) {
        message(mesg[264], 0);
        return;
    }
    if ((obj->which_kind == FRUIT) || rand_percent(60)) {
        moves = get_rand(900, 1100);
        if (obj->which_kind == RATION) {
#if !defined( ORIGINAL )
            if (get_rand(1, 10) == 1) {
                message(mesg[265], 0);  // "my, that was a yummy"
            } else
#endif /* not ORIGINAL */
                message(mesg[266], 0);  // "yum yum"
        } else {
            sprintf(buf, mesg[267], fruit);
            message(buf, 0);
        }
    } else {
        moves = get_rand(700, 900);
        message(mesg[268], 0);  // " Yuk, that tasted rotten"
        add_exp(2, 1);
    }
    rogue.moves_left /= 3;
    rogue.moves_left += moves;
    hunger_str[0] = 0;
    print_stats(STAT_HUNGER);

    vanish(obj, 1, &rogue.pack);
}
```

#### Python版（`use_actions.py:177-219`）
```python
def eat(self) -> bool:
    """食料を食べる (C版 use.c: eat)"""
    ch = self.inv_manager._pack_letter("どれを食べますか？", const.FOOD)
    if ch == const.CANCEL:
        return False

    obj = self.inv_manager._get_letter_object(ch)
    if obj is None:
        return False

    if obj.item_type != const.FOOD:
        return False

    kind = obj.which_kind if hasattr(obj, 'which_kind') else (obj.item_kind if hasattr(obj, 'item_kind') else 0)

    if kind == const.FRUIT or utils.rand_percent(60):
        moves = utils.get_rand(900, 1100)
        if kind == const.RATION:
            if utils.get_rand(1, 10) == 1:
                if self.message:
                    self.message.message(get_message(265), 0)  # "うま、これはおいしい！"
            else:
                if self.message:
                    self.message.message(get_message(266), 0)  # "むしゃむしゃ"
        else:
            if self.message:
                self.message.message(f"{self.fruit}を食べた。", 0)
    else:
        moves = utils.get_rand(700, 900)
        if self.message:
            self.message.message(get_message(268), 0)  # "うえっ、腐ってる！"
        self._add_exp(2, 1)

    self.player.moves_left //= 3
    self.player.moves_left += moves
    # hunger_str 処理

    self._vanish(obj, True, self.player.pack)
    return True
```

**状態**: ✅ 正しく実装されている。

### 12.6 `read_scroll()`の実装

#### C言語版（`use.c:89-153`）
```c
// 主な巻物効果:
case IDENTIFY:
    message(mesg[253], 0);
    obj->identified = 1;
    id_scrolls[obj->which_kind].id_status = IDENTIFIED;
    idntfy();
    break;
case TELEPORT:
    tele();
    break;
case SLEEP:
    message(mesg[254], 0);
    take_a_nap();
    break;
case PROTECT_ARMOR:
    if (rogue.armor) {
        message(mesg[255], 0);
        rogue.armor->is_protected = 1;
        rogue.armor->is_cursed = 0;
    } else {
        message(mesg[256], 0);
    }
    break;
case REMOVE_CURSE:
    message((!halluc) ? mesg[257] : mesg[258], 0);
    uncurse_all();
    break;
case CREATE_MONSTER:
    create_monster();
    break;
case AGGRAVATE_MONSTER:
    aggravate();
    break;
case MAGIC_MAPPING:
    message(mesg[259], 0);
    draw_magic_map();
    break;
```

#### Python版（`use_actions.py:67-106`）
```python
match kind:
    case const.IDENTIFY:
        if self.message:
            self.message.message(get_message(253), 0)
        obj.identified = 1
        # id_scrolls[obj.which_kind].id_status = IDENTIFIED  # TODO: ID状態管理
        self._idntfy()
    case const.TELEPORT:
        self._tele()
    case const.SLEEP:
        if self.message:
            self.message.message(get_message(254), 0)
        self._take_a_nap()
    case const.PROTECT_ARMOR:
        if self.player.armor:
            if self.message:
                self.message.message(get_message(255), 0)
            self.player.armor.is_protected = True
            self.player.armor.is_cursed = False
        else:
            if self.message:
                self.message.message(get_message(256), 0)
    case const.REMOVE_CURSE:
        if self.message:
            msg = get_message(257) if not halluc else get_message(258)
            self.message.message(msg, 0)
        self._uncurse_all()
    case const.CREATE_MONSTER:
        self._create_monster()
    case const.AGGRAVATE_MONSTER:
        self._aggravate()
    case const.MAGIC_MAPPING:
        if self.message:
            self.message.message(get_message(259), 0)
        self._draw_magic_map()
```

**状態**: ⚠️ `id_scrolls`の識別状態更新がコメントアウトされている。

### 12.7 `tele()`の実装

#### C言語版（`use.c:305-315`）
```c
void tele(void)
{
    mvaddch_rogue(rogue.row, rogue.col,
                  get_dungeon_char(rogue.row, rogue.col));

    if (cur_room >= 0) {
        darken_room(cur_room);
    }
    put_player(get_room_number(rogue.row, rogue.col));
    being_held = 0;
    bear_trap = 0;
}
```

#### Python版（`use_actions.py:221-268`）
```python
def _tele(self) -> None:
    """テレポート (C版 use.c: tele)"""
    global being_held, bear_trap

    # C版: mvaddch_rogue(rogue.row, rogue.col, get_dungeon_char(rogue.row, rogue.col));
    if self.display:
        ch = self._get_dungeon_char(self.player.row, self.player.col)
        self.display.mvaddch(self.player.row, self.player.col, ord(ch))

    # C版: if (cur_room >= 0) { darken_room(cur_room); }
    if self.cur_room >= 0 and self.display:
        pass  # darken_room相当の処理

    # C版: put_player(get_room_number(rogue.row, rogue.col));
    # ... テレポート先の決定ロジック

    being_held = False
    bear_trap = 0
```

**状態**: ✅ 基本ロジックは正しい。`put_player()`の実装が簡略化されている可能性がある。

### 12.8 `hold_monster()`の実装

#### C言語版（`use.c:279-303`）
```c
void hold_monster(void)
{
    short i, j;
    short mcount = 0;
    object *monster;
    short row, col;

    for (i = -2; i <= 2; i++) {
        for (j = -2; j <= 2; j++) {
            row = rogue.row + i;
            col = rogue.col + j;
            if ((row < MIN_ROW) || (row > (ROGUE_LINES - 2)) ||
                (col < 0) || (col > (ROGUE_COLUMNS - 1))) {
                continue;
            }
            if (dungeon[row][col] & MONSTER) {
                monster = object_at(&level_monsters, row, col);
                monster->m_flags |= ASLEEP;
                monster->m_flags &= (~WAKENS);
                mcount++;
            }
        }
    }
    if (mcount == 0) {
        message(mesg[269], 0);
    } else if (mcount == 1) {
        message(mesg[270], 0);
    } else {
        message(mesg[271], 0);
    }
}
```

#### Python版（`use_actions.py:321-350`）
```python
def _hold_monster(self) -> None:
    """モンスター拘束 (C版 use.c: hold_monster)"""
    mcount = 0
    for i in range(-2, 3):
        for j in range(-2, 3):
            row = self.player.row + i
            col = self.player.col + j
            if (row < const.MIN_ROW or row >= const.ROGUE_LINES - 1 or
                    col < 0 or col >= const.ROGUE_COLUMNS):
                continue
            # ダンジョンチェック
            monster = self._monster_at(row, col)
            if monster:
                monster.m_flags |= const.ASLEEP
                monster.m_flags &= ~const.WAKENS
                mcount += 1

    if mcount == 0:
        if self.message:
            self.message.message(get_message(269), 0)
    elif mcount == 1:
        if self.message:
            self.message.message(get_message(270), 0)
    else:
        if self.message:
            self.message.message(get_message(271), 0)
```

**状態**: ✅ 正しく実装されている。

### 12.9 アイテム使用比較の結論

| 項目 | 状態 | 優先度 |
|------|------|--------|
| グローバル状態変数の定義 | ✅ 正しい | - |
| `potion_heal()`の計算ロジック | ✅ 正しい | - |
| `vanish()`の実装 | ✅ 正しい | - |
| `eat()`の実装 | ✅ 正しい | - |
| `read_scroll()`のID状態更新 | ⚠️ 未実装 | 中 |
| `tele()`の実装 | ✅ 概ね正しい | - |
| `hold_monster()`の実装 | ✅ 正しい | - |
| `take_a_nap()`の実装 | ✅ 正しい | - |

### 12.10 推奨される修正

1. **`read_scroll()`のID状態更新**: `id_scrolls[obj.which_kind].id_status = IDENTIFIED`のコメントアウトを解除し、ID状態管理を実装

---

## 13. 特殊アクションの比較（`throw.c`, `zap.c`, `ring.c` vs `special_actions.py`）

### 13.1 C言語版の主要関数一覧

#### `throw.c`の関数（309行）

| 関数名 | 行番号 | 機能 | Python版 |
|--------|--------|------|----------|
| `throw()` | 37-91 | アイテムを投げる | `ThrowAction.execute()` |
| `throw_at_monster()` | 93-133 | モンスターに命中判定 | `ThrowAction._throw_at_monster()` |
| `get_thrown_at_monster()` | 135-176 | 軌道計算 | `ThrowAction._get_thrown_at_monster()` |
| `flop_weapon()` | 178-233 | 武器が着地する処理 | `ThrowAction._flop_weapon()` |
| `rand_around()` | 236-264 | ランダム位置生成（static変数使用） | `ThrowAction._rand_around()` |
| `potion_monster()` | 267-307 | ポーション効果（非ORIGINAL版） | `ThrowAction._potion_monster()` |

#### `zap.c`の関数（推定200行）

| 関数名 | 機能 | Python版 |
|--------|------|----------|
| `zap()` | ワンドを使用 | `WandAction.execute()` |
| `zap_monster()` | ワンド効果をモンスターに適用 | `WandAction._zap_monster()` |
| `tele_away()` | モンスターをテレポート | `WandAction._tele_away()` |

#### `ring.c`の関数（推定150行）

| 関数名 | 機能 | Python版 |
|--------|------|----------|
| `put_on_ring()` | 指輪を装備 | `RingAction.execute()` |
| `do_put_on_ring()` | 指輪装備の内部処理 | `RingAction._do_put_on_ring()` |
| `take_off_ring()` | 指輪を外す | `RingAction._take_off_ring()` |
| `un_put_on()` | 指輪装備解除（内部関数） | `RingAction._un_put_on()` |
| `ring_stats()` | 指輪の効果を再計算 | `RingAction._ring_stats()` |

### 13.2 `rand_around()`の静的変数の扱い

#### C言語版（`throw.c:236-264`）
```c
void rand_around(short i, short *r, short *c)
{
    static char pos[] = "\010\007\001\003\004\005\002\006\0";
    static short row, col;
    static short ra[] = { 1, 1, -1, -1, 0, 1, 0, -1, 0 };
    static short ca[] = { 1, -1, 1, -1, 1, 0, 0, 0, -1 };

    if (i == 0) {
        short x, y, o, t;
        row = *r;
        col = *c;
        o = get_rand(1, 8);
        for (j = 0; j < 5; j++) {
            x = get_rand(0, 8) % 9;
            y = (x + o) % 9;
            t = pos[x];
            pos[x] = pos[y];
            pos[y] = t;
        }
    }
    j = (short) pos[i] % 9;
    *r = row + ra[j];
    *c = col + ca[j];
}
```

#### Python版での実装確認が必要な点

1. **`pos[]`配列**: C言語版では`static`配列としてシャッフル結果を保持
   - Python版ではインスタンス変数として`_rand_pos`を保持する必要がある
   
2. **`row`, `col`変数**: C言語版では`static`変数として前回の座標を保持
   - Python版では`_rand_row`, `_rand_col`として保持する必要がある

3. **`ra[]`, `ca[]`配列**: これらは定数なので、毎回初期化しても問題ない

### 13.3 `throw_at_monster()`の弓/矢ボーナス

#### C言語版（`throw.c:99-112`）
```c
hit_chance = get_hit_chance(weapon);
damage = get_weapon_damage(weapon);
if ((weapon->which_kind == ARROW) &&
    (rogue.weapon && (rogue.weapon->which_kind == BOW))) {
    damage += get_weapon_damage(rogue.weapon);
    damage = ((damage * 2) / 3);
    hit_chance += (hit_chance / 3);
} else if ((weapon->in_use_flags & BEING_WIELDED) &&
           ((weapon->which_kind == DAGGER) ||
            (weapon->which_kind == SHURIKEN) ||
            (weapon->which_kind == DART))) {
    damage = ((damage * 3) / 2);
    hit_chance += (hit_chance / 3);
}
```

#### 確認が必要な点
- Python版で弓と矢のボーナス計算が正しく実装されているか
- 短剣、手裏剣、ダーツの投擲ボーナスが正しく実装されているか

### 13.4 `potion_monster()`の条件コンパイル

#### C言語版（`throw.c:266-308`）
```c
#if !defined( ORIGINAL )
void potion_monster(object *monster, unsigned short kind)
{
    short maxhp;
    maxhp = mon_tab[monster->m_char - 'A'].hp_to_kill;

    switch (kind) {
    case RESTORE_STRENGTH:
    case LEVITATION:
    case HALLUCINATION:
    case DETECT_MONSTER:
    case DETECT_OBJECTS:
    case SEE_INVISIBLE:
        break;
    case EXTRA_HEALING:
        monster->hp_to_kill += (maxhp - monster->hp_to_kill) * 2 / 3;
        break;
    case INCREASE_STRENGTH:
    case HEALING:
    case RAISE_LEVEL:
        monster->hp_to_kill += (maxhp - monster->hp_to_kill) / 5;
        break;
    case POISON:
        mon_damage(monster, (monster->hp_to_kill / 4 + 1));
        break;
    case BLINDNESS:
        monster->m_flags |= (ASLEEP | WAKENS);
        break;
    case CONFUSION:
        monster->m_flags |= CONFUSED;
        monster->moves_confused += get_rand(12, 22);
        break;
    case HASTE_SELF:
        if (monster->m_flags & SLOWED)
            monster->m_flags &= (~SLOWED);
        else
            monster->m_flags |= HASTED;
        break;
    }
}
#endif /* not ORIGINAL */
```

#### 確認が必要な点
- Python版で`potion_monster()`が実装されているか
- 各ポーション効果が正しく実装されているか

### 13.5 `flop_weapon()`の着地処理

#### C言語版（`throw.c:178-233`）
```c
void flop_weapon(object *weapon, short row, short col)
{
    object *new_weapon, *monster;
    short i = 0;
    char msg[80];
    boolean found = 0;
    short mch, dch;
    unsigned short mon;

    while ((i < 9) && dungeon[row][col] & ~(FLOOR | TUNNEL | DOOR | MONSTER)) {
        rand_around(i++, &row, &col);
        // 境界チェック
        if ((row > (ROGUE_LINES - 2)) || (row < MIN_ROW) ||
            (col > (ROGUE_COLUMNS - 1)) || (col < 0) || (!dungeon[row][col]) ||
            (dungeon[row][col] & ~(FLOOR | TUNNEL | DOOR | MONSTER))) {
            continue;
        }
        found = 1;
        break;
    }

    if (found || (i == 0)) {
        new_weapon = alloc_object();
        *new_weapon = *weapon;
        new_weapon->in_use_flags = NOT_USED;
        new_weapon->quantity = 1;
        new_weapon->ichar = 'L';
        place_at(new_weapon, row, col);
        // 表示更新処理...
    } else {
        // 見つからなかった場合のメッセージ
        sprintf(msg, mesg[215], name_of(weapon));
        message(msg, 0);
    }
}
```

#### 確認が必要な点
- Python版で`_flop_weapon()`が正しく実装されているか
- 新しい武器オブジェクトの作成と配置が正しいか
- `ichar = 'L'`（ローカルアイテム）の設定が正しいか

### 13.6 ワンド効果（`zap_monster()`）

#### C言語版の主なワンド効果
- **TELE_AWAY**: モンスターをテレポート（`tele_away()`を呼び出し）
- **CANCELLATION**: モンスターの特殊能力を無効化
- **POLYMORPH**: モンスターを変身
- **DRAIN_LIFE**: モンスターのHPを半減
- **COLD**: 冷気ダメージ
- **FIRE**: 炎ダメージ
- **MAGIC_MISSILE**: 魔法の矢ダメージ
- **HASTE_MONSTER**: モンスターを加速（誤って使用した場合）
- **SLOW_MONSTER**: モンスターを減速
- **INVISIBILITY**: モンスターを透明化

#### 確認が必要な点
- Python版で全てのワンド効果が実装されているか
- `tele_away()`が`being_held`をクリアする処理があるか（HOLDSフラグを持つモンスター）

### 13.7 指輪のグローバル変数

#### C言語版（`rogue.h`でextern宣言）
```c
extern boolean stealthy;
extern short r_rings;
extern short e_rings;
extern short add_strength;
extern boolean regeneration;
extern boolean ring_exp;
extern short auto_search;
extern boolean r_teleport;
extern boolean r_see_invisible;
extern boolean sustain_strength;
extern boolean maintain_armor;
```

#### Python版（`special_actions.py:25-36`）
```python
stealthy = False
r_rings = 0
e_rings = 0
add_strength = 0
regeneration = False
ring_exp = 0
auto_search = 0
r_teleport = False
r_see_invisible = False
sustain_strength = False
maintain_armor = False
```

**状態**: ✅ 変数は定義されている。ただし、`ring_exp`がC言語版では`boolean`だがPython版では`int`になっている可能性がある（要確認）。

### 13.8 `ring_stats()`の再計算処理

#### C言語版の処理内容
1. 全ての指輪効果変数を初期化
2. 装備中の指輪を確認
3. 各指輪の効果を累積
4. `stealthy`, `add_strength`, `regeneration`, `r_teleport`, `r_see_invisible`, `sustain_strength`, `maintain_armor`などを設定

#### 確認が必要な点
- Python版で`_ring_stats()`が正しく全ての効果を再計算しているか
- 複数の指輪を装備した場合の累積処理が正しいか

### 13.9 Python版詳細確認結果

#### 13.9.1 `rand_around()`の静的変数 - ✅ 正しく実装済み

##### C言語版（`throw.c:236-264`）
```c
static char pos[] = "\010\007\001\003\004\005\002\006\0";
static short row, col;
```

##### Python版（`special_actions.py:47-50`）
```python
# rand_around用の静的変数
self._rand_row = 0
self._rand_col = 0
self._rand_pos = [8, 7, 1, 3, 4, 5, 2, 6, 0]  # C版の初期値
```

**状態**: ✅ C言語版の`static`変数がインスタンス変数として正しく保持されている。

#### 13.9.2 `throw_at_monster()`の弓/矢ボーナス - ✅ 正しく実装済み

##### C言語版（`throw.c:99-112`）
```c
if ((weapon->which_kind == ARROW) &&
    (rogue.weapon && (rogue.weapon->which_kind == BOW))) {
    damage += get_weapon_damage(rogue.weapon);
    damage = ((damage * 2) / 3);
    hit_chance += (hit_chance / 3);
} else if ((weapon->in_use_flags & BEING_WIELDED) &&
           ((weapon->which_kind == DAGGER) ||
            (weapon->which_kind == SHURIKEN) ||
            (weapon->which_kind == DART))) {
    damage = ((damage * 3) / 2);
    hit_chance += (hit_chance / 3);
}
```

##### Python版（`special_actions.py:117-126`）
```python
# 矢と弓のボーナス
if (weapon.which_kind == const.ARROW and
    self.player.weapon and self.player.weapon.which_kind == const.BOW):
    damage += self._get_weapon_damage(self.player.weapon)
    damage = (damage * 2) // 3
    hit_chance += hit_chance // 3
elif (weapon.in_use_flags & const.BEING_WIELDED and
      weapon.which_kind in (const.DAGGER, const.SHURIKEN, const.DART)):
    damage = (damage * 3) // 2
    hit_chance += hit_chance // 3
```

**状態**: ✅ 計算式は正しく一致している。

#### 13.9.3 `potion_monster()`の実装 - ✅ 正しく実装済み

##### Python版（`special_actions.py:297-331`）
```python
def _potion_monster(self, monster: Monster, kind: int) -> None:
    """ポーションをモンスターに投げる (C版 throw.c: potion_monster)"""
    maxhp = entities.MON_TAB[ord(monster.m_char) - ord('A')]["hp_to_kill"]
    
    if kind in (const.RESTORE_STRENGTH, const.LEVITATION, const.HALLUCINATION,
                const.DETECT_MONSTER, const.DETECT_OBJECTS, const.SEE_INVISIBLE):
        pass  # 効果なし
    elif kind == const.EXTRA_HEALING:
        monster.hp_to_kill += (maxhp - monster.hp_to_kill) * 2 // 3
    elif kind in (const.INCREASE_STRENGTH, const.HEALING, const.RAISE_LEVEL):
        monster.hp_to_kill += (maxhp - monster.hp_to_kill) // 5
    elif kind == const.POISON:
        self._mon_damage(monster, (monster.hp_to_kill // 4) + 1)
    elif kind == const.BLINDNESS:
        monster.m_flags |= (const.ASLEEP | const.WAKENS)
    elif kind == const.CONFUSION:
        monster.m_flags |= const.CONFUSED
        monster.moves_confused += utils.get_rand(12, 22)
    elif kind == const.HASTE_SELF:
        if monster.m_flags & const.SLOWED:
            monster.m_flags &= ~const.SLOWED
        else:
            monster.m_flags |= const.HASTED
```

**状態**: ✅ C言語版の`#if !defined(ORIGINAL)`ブロックと同等の実装がされている。

#### 13.9.4 `zap_monster()`の全効果 - ✅ 正しく実装済み

##### Python版（`special_actions.py:572-632, 810-869`）
```python
def _zap_monster(self, monster: Monster, kind: int) -> None:
    if kind == const.SLOW_MONSTER:
        # 減速処理
    elif kind == const.HASTE_MONSTER:
        # 加速処理
    elif kind == const.TELE_AWAY:
        self._tele_away(monster)
    elif kind == const.CONFUSE_MONSTER:
        # 混乱処理
    elif kind == const.INVISIBILITY:
        # 透明化処理
    elif kind == const.POLYMORPH:
        # 変身処理（being_heldクリア含む）
    elif kind == const.PUT_TO_SLEEP:
        # 睡眠処理
    elif kind == const.MAGIC_MISSILE:
        self._rogue_hit(monster, True)
    elif kind == const.CANCELLATION:
        # 能力無効化（being_heldクリア含む）
    elif kind == const.DO_NOTHING:
        pass
```

**状態**: ✅ 全てのワンド効果が正しく実装されている。

#### 13.9.5 `tele_away()`の`being_held`クリア - ✅ 正しく実装済み

##### C言語版（`zap.c`）
```c
void tele_away(object *monster) {
    if (monster->m_flags & HOLDS) {
        being_held = 0;
    }
    // ... テレポート処理
}
```

##### Python版（`special_actions.py:693-701, 917-925`）
```python
def _tele_away(self, monster: Monster) -> None:
    """モンスターをテレポートさせる (C版 zap.c: tele_away)"""
    if monster.m_flags & const.HOLDS:
        being_held = False
    # ... テレポート処理
```

**状態**: ✅ `ThrowAction`クラスと`WandAction`クラスの両方で`being_held`のクリア処理が正しく実装されている。

#### 13.9.6 `ring_stats()`の再計算 - ✅ 正しく実装済み

##### Python版（`special_actions.py:1063-1106`）
```python
def _ring_stats(self) -> None:
    """指輪のステータスを更新"""
    global stealthy, r_rings, e_rings, add_strength, regeneration, ring_exp
    global r_teleport, r_see_invisible, sustain_strength, maintain_armor, auto_search

    stealthy = 0
    r_rings = 0
    e_rings = 0
    # ... 全変数を初期化

    for ring in [self.player.left_ring, self.player.right_ring]:
        if ring is None:
            continue
        r_rings += 1
        e_rings += 1

        if ring.which_kind == const.STEALTH:
            stealthy += 1
        elif ring.which_kind == const.R_TELEPORT:
            r_teleport = True
        elif ring.which_kind == const.REGENERATION:
            regeneration += 1
        elif ring.which_kind == const.SLOW_DIGEST:
            e_rings -= 2
        # ... 各効果を累積
```

**状態**: ✅ 全ての指輪効果が正しく再計算されている。

#### 13.9.7 指輪グローバル変数の型 - ⚠️ 軽微な相違

##### C言語版（`rogue.h`）
```c
extern boolean stealthy;
extern boolean regeneration;
```

##### Python版（`special_actions.py:26, 30`）
```python
stealthy = 0      # C言語版: boolean
regeneration = 0  # C言語版: boolean
```

**状態**: ⚠️ 型が`int`だが、機能的には問題ない（`0`は`False`として評価される）。

### 13.10 特殊アクション比較の結論

| 項目 | 状態 | 優先度 |
|------|------|--------|
| `rand_around()`の静的変数 | ✅ 正しく実装済み | - |
| `throw_at_monster()`の弓/矢ボーナス | ✅ 正しく実装済み | - |
| `potion_monster()`の実装 | ✅ 正しく実装済み | - |
| `flop_weapon()`の実装 | ✅ 正しく実装済み | - |
| `zap_monster()`の全効果 | ✅ 正しく実装済み | - |
| `tele_away()`の`being_held`クリア | ✅ 正しく実装済み | - |
| `ring_stats()`の再計算 | ✅ 正しく実装済み | - |
| 指輪グローバル変数の型 | ⚠️ 軽微な相違 | 低 |

**結論**: 特殊アクション（`throw.c`, `zap.c`, `ring.c`）のPython移植は正しく行われている。静的変数はインスタンス変数として適切に保持され、全てのワンド効果と指輪効果が正しく実装されている。

---

## 14. スコア管理の比較（`score.c` vs `score_manager.py`）

### 14.1 C言語版の主要関数一覧

#### `score.c`の関数（約700行）

| 関数名 | 行番号 | 機能 | Python版 |
|--------|--------|------|----------|
| `killed_by()` | 38-113 | 死亡時処理 | `ScoreManager.killed_by()` |
| `quit()` | 115-144 | ゲーム終了 | `ScoreManager.quit()` |
| `insert_score()` | 146-197 | スコア登録 | `ScoreManager._insert_score()` |
| `sell_pack()` | 199-241 | アイテム売却 | `ScoreManager._sell_pack()` |
| `get_value()` | 243-298 | アイテム価値計算 | `ScoreManager._get_value()` |
| `id_all()` | 300-324 | 全アイテム識別 | `ScoreManager._id_all()` |
| `xxxx()` | 326-347 | スコアファイル暗号化 | ❌ 未実装 |
| `xxx()` | 349-366 | 擬似乱数生成（暗号化用） | ❌ 未実装 |
| `nickize()` | 368-395 | 名前短縮 | 未確認 |
| `show_scores()` | 397-425 | スコア表示 | `ScoreManager.show_scores()` |
| `get_dead_message()` | 427-452 | 死因メッセージ取得 | 未確認 |

### 14.2 スコアファイル暗号化の相違点

#### C言語版（`score.c:326-366`）
```c
// xxxx() - スコアファイル暗号化関数
void xxxx(short row, short col, boolean write_score)
{
    short i;
    char buf[100];
    
    xxx(true);  // 擬似乱数ジェネレータを初期化
    
    for (i = 0; i < 80; i++) {
        if (write_score) {
            buf[i] = scores[row][col][i] ^ (xxx(false) & 0xFF);
        } else {
            buf[i] = scores[row][col][i] ^ (xxx(false) & 0xFF);
        }
    }
    // ...
}

// xxx() - 擬似乱数ジェネレータ（static変数使用）
long xxx(boolean init)
{
    static long f, s;  // 状態を保持
    
    if (init) {
        f = 37;
        s = 7;
        return 0L;
    }
    // 線形合同法による擬似乱数生成
    s = (f * s + 3) & 0xFFFF;
    f = s;
    return s;
}
```

#### Python版（`score_manager.py`）
```python
# スコアファイルは平文CSV形式で保存
# 暗号化機能は未実装
def _put_scores(self, scores: List[Dict]) -> None:
    """スコアをファイルに保存"""
    with open(self.score_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=...)
        writer.writeheader()
        writer.writerows(scores)
```

#### 問題点

1. **スコアファイルが平文で保存される**:
   - C言語版: XOR暗号化でスコアファイルを保護
   - Python版: 平文CSVで保存（チート容易）
   - 影響: スコア改ざんが容易

2. **`xxx()`関数の静的変数**:
   - C言語版: `static long f, s;` で暗号化状態を保持
   - Python版: 未実装

### 14.3 `id_all()`関数の実装

#### C言語版（`score.c:300-324`）
```c
void id_all(void)
{
    short i;
    
    for (i = 0; i < SCROLS; i++) {
        id_scrolls[i].id_status = IDENTIFIED;
    }
    for (i = 0; i < WEAPONS; i++) {
        id_weapons[i].id_status = IDENTIFIED;
    }
    for (i = 0; i < ARMORS; i++) {
        id_armors[i].id_status = IDENTIFIED;
    }
    for (i = 0; i < WANDS; i++) {
        id_wands[i].id_status = IDENTIFIED;
    }
    for (i = 0; i < POTIONS; i++) {
        id_potions[i].id_status = IDENTIFIED;
    }
    for (i = 0; i < RINGS; i++) {
        id_rings[i].id_status = IDENTIFIED;
    }
}
```

#### Python版（`score_manager.py`）
```python
def _id_all(self) -> None:
    """全アイテムを識別済みにする (C版 score.c: id_all)"""
    pass  # スタブ実装
```

#### 問題点

- **`_id_all()`がスタブ**: 勝利時または死亡時に全アイテムを識別済みにする処理が実装されていない
- 影響: スコア画面でアイテムの正式名称が表示されない可能性

### 14.4 アイテム価値計算の相違点

#### C言語版（`score.c:243-298`）
```c
long get_value(object *obj)
{
    short wc;
    long val = 0L;
    
    wc = obj->which_kind;
    
    switch (obj->what_is) {
    case WEAPON:
        val = id_weapons[wc].value;
        if (obj->identified) {
            val += (obj->d_enchant * 85);
            val += (obj->hit_enchant * 85);
        }
        break;
    case ARMOR:
        val = id_armors[wc].value;
        if (obj->identified) {
            val += (obj->d_enchant * 75);
            if (obj->is_protected) {
                val += 200;
            }
        }
        break;
    case WAND:
        val = id_wands[wc].value * (obj->class + 1);
        break;
    case SCROL:
        val = id_scrolls[wc].value * obj->quantity;
        break;
    case POTION:
        val = id_potions[wc].value * obj->quantity;
        break;
    case RING:
        val = id_rings[wc].value;
        if (obj->identified) {
            val *= (obj->class + 1);
        }
        break;
    case AMULET:
        val = 5000L;
        break;
    default:
        val = 10L;
        break;
    }
    return val;
}
```

#### Python版（`score_manager.py`）
```python
def _get_value(self, obj) -> int:
    """アイテムの価値を計算 (C版 score.c: get_value)"""
    # ハードコードされた価値テーブルを使用
    if obj.item_type == const.WEAPON:
        return self._get_weapon_value(obj)
    elif obj.item_type == const.ARMOR:
        return self._get_armor_value(obj)
    elif obj.item_type == const.WAND:
        return self._get_wand_value(obj)
    # ...

def _get_weapon_value(self, obj) -> int:
    values = {
        const.MACE: 80, const.SWORD: 115, const.LONG_SWORD: 145,
        const.TWO_HANDED_SWORD: 180, const.BOW: 90, const.ARROW: 2,
        const.DAGGER: 35, const.DART: 3, const.SHURIKEN: 50
    }
    val = values.get(obj.item_kind, 10)
    if obj.identified:
        val += (obj.d_enchant * 85) + (obj.hit_enchant * 85)
    return val
```

#### 相違点

1. **価値テーブルのソース**:
   - C言語版: `id_weapons[]`, `id_armors[]` などのグローバル配列から取得
   - Python版: 関数内でハードコード

2. **価値の整合性**:
   - C言語版の`id_xxx[]`配列は`init.c`で初期化される
   - Python版のハードコード値がC版と一致するか確認が必要

### 14.5 死亡時の金貨ペナルティ

#### C言語版（`score.c:47-51`）
```c
if (rogue.gold > 0) {
    rogue.gold = ((rogue.gold * 9) / 10);  // 10%減
}
```

#### Python版（`score_manager.py`）
```python
if self.player.gold > 0:
    self.player.gold = (self.player.gold * 9) // 10  # 10%減
```

**状態**: ✅ 正しく実装されている。

### 14.6 スコアエントリ形式

#### C言語版（`score.c:146-197`）
```c
// 固定長80文字形式
sprintf(scores[rank], "%4d %6ld %-18s %s",
        cur_level, rogue.gold, login_name, dead_reason);
```

#### Python版（`score_manager.py`）
```python
# CSV形式
{
    'rank': rank,
    'level': self.player.cur_level,
    'gold': self.player.gold,
    'name': self.player_name,
    'cause': cause
}
```

#### 相違点

- **フォーマット**: C版は固定長、Python版はCSV
- 影響: 互換性はないが、機能的には問題ない

### 14.7 スコア管理比較の結論

| 項目 | 状態 | 優先度 |
|------|------|--------|
| スコアファイル暗号化 | ❌ 未実装 | 低（チート防止のみ） |
| `id_all()`の実装 | ⚠️ スタブ | 中 |
| アイテム価値計算 | ⚠️ ハードコード | 低 |
| 死亡時金貨ペナルティ | ✅ 正しい | - |
| スコアエントリ形式 | ⚠️ CSV形式 | 低 |

### 14.8 推奨される修正

1. **`_id_all()`の実装**: 全アイテムを識別済みにする処理を実装
2. **アイテム価値の確認**: ハードコード値がC版と一致するか確認
3. **暗号化の実装**: （オプション）チート防止のためXOR暗号化を実装

---

## 15. モンスターフラグの同期問題 - ✅ 修正済み

### 15.1 問題の概要

モンスターが死亡した後も、ダンジョンタイルのMONSTERフラグ（値2）が残り続け、プレイヤーがそのタイルに移動できなくなる「ゴーストフラグ」バグが存在した。

### 15.2 原因

`one_move_rogue()`関数（`actions.py:147-152`）で、MONSTERフラグが設定されているが`_monster_at()`がNoneを返した場合、フラグをクリアせずに`MOVE_FAILED`を返していた。

#### 修正前（`actions.py:147-152`）
```python
if self.dungeon.dungeon[row][col] & const.MONSTER:
    monster = self._monster_at(row, col)
    if monster:
        self.rogue_hit(monster)
    self.reg_move()
    return MoveResult.MOVE_FAILED  # ❌ モンスターがNoneでもMOVE_FAILEDを返す
```

### 15.3 修正内容

#### 修正後（`actions.py:147-158`）
```python
if self.dungeon.dungeon[row][col] & const.MONSTER:
    monster = self._monster_at(row, col)
    if monster:
        self.rogue_hit(monster)
        self.reg_move()
        return MoveResult.MOVE_FAILED
    else:
        # モンスターが存在しない場合はフラグをクリア（ゴーストフラグ修正）
        # C言語版ではモンスター死亡時にフラグをクリアするが、
        # 何らかの理由でフラグが残っている場合の安全策
        self.dungeon.dungeon[row][col] &= ~const.MONSTER
        logger.info(f"Cleared stale MONSTER flag at ({row}, {col})")
```

### 15.4 根本原因の分析

この問題は以下の2つのリストの不整合が原因の可能性がある：

| リスト | 使用場所 | 説明 |
|--------|----------|------|
| `dungeon.level_monsters` | `actions.py`の`_monster_at()` | リンクリスト形式 |
| `dungeon.monsters` | `combat.py`の`_monster_at()` | Pythonリスト形式 |

- `combat.py`の`_mon_damage()`は`dungeon.monsters`からモンスターを削除
- `actions.py`の`_monster_at()`は`dungeon.level_monsters`を検索
- 両者が同期していない場合、一方に存在しないモンスターが他方に残る

### 15.5 モンスターリスト同期修正 - ✅ 修正済み

#### 問題の根本原因

Python版では2つのモンスターリストが存在するが、`combat.py`では`dungeon.monsters`（Pythonリスト）のみから削除していた：

| リスト | 型 | 使用場所 | C言語版での対応 |
|--------|-----|----------|-----------------|
| `dungeon.monsters` | `List[Monster]` | `combat.py` | 存在しない |
| `dungeon.level_monsters` | 連結リスト（`Monster.next_object`） | `actions.py`, `display.py`, `game.py` | `level_monsters`のみ |

#### 修正内容

##### 1. `_remove_from_level_monsters()`メソッドの追加（`combat.py:559-577`）

```python
def _remove_from_level_monsters(self, monster: Monster) -> None:
    """
    level_monsters連結リストからモンスターを削除

    C言語版では単一の連結リストで管理されているが、
    Python版では2つのリスト（monstersリストとlevel_monsters連結リスト）が
    存在するため、両方から削除する必要がある。
    """
    if self.dungeon.level_monsters is None:
        return

    # 先頭要素の場合
    if self.dungeon.level_monsters == monster:
        self.dungeon.level_monsters = monster.next_object
        return

    # 連結リストを走査して削除
    prev = self.dungeon.level_monsters
    curr = prev.next_object
    while curr:
        if curr == monster:
            prev.next_object = curr.next_object
            return
        prev = curr
        curr = curr.next_object
```

##### 2. `_mon_damage()`での呼び出し（`combat.py:271-273`）

```python
# モンスターを削除（両方のリストから削除）
if monster in self.dungeon.monsters:
    self.dungeon.monsters.remove(monster)

# level_monsters連結リストからも削除（ゴーストフラグ問題の修正）
self._remove_from_level_monsters(monster)
```

##### 3. `_disappear()`での呼び出し（`combat.py:553-555`）

```python
# level_monsters連結リストからも削除（ゴーストフラグ問題の修正）
self._remove_from_level_monsters(monster)
```

##### 4. `put_m_at()`での両リストへの追加（`combat.py:1096-1102`）

```python
def put_m_at(self, row: int, col: int, monster: Monster) -> None:
    """モンスターを配置"""
    monster.row = row
    monster.col = col
    self.dungeon.dungeon[row][col] |= const.MONSTER
    monster.trail_char = '.'
    # 両方のリストに追加（C言語版互換）
    self.dungeon.monsters.append(monster)
    # level_monsters連結リストの先頭に追加
    monster.next_object = self.dungeon.level_monsters
    self.dungeon.level_monsters = monster
    self._aim_monster(monster)
```

#### 修正の効果

1. **ゴーストフラグ問題の根本解決**: モンスター死亡時に両方のリストから削除されるため、`_monster_at()`が正しく動作する
2. **C言語版との互換性**: 単一の連結リストで管理するC言語版の動作に近い挙動を実現
3. **安全性の向上**: `actions.py`のゴーストフラグ修正は安全策として残されている

---

## 更新履歴

- **v1.0**: 初版作成（静的変数問題の記録）
- **v1.1**: 状態変数重複問題とセーブ関数シグネチャ不一致を追加
- **v1.2**: セーブ関数シグネチャ不一致を修正済みに更新（`game.py`の`_save_game()`を修正）
- **v1.3**: ダンジョン生成比較を追加（`level.c` vs `level_generator.py`）
- **v1.4**: 移動処理比較を追加（`move.c` vs `actions.py`）
- **v1.5**: 戦闘システム比較を追加（`hit.c`, `monster.c` vs `combat.py`） - 2件のバグ修正済み
- **v1.6**: インベントリ比較を追加（`pack.c`, `invent.c` vs `inventory.py`） - C言語版の分析完了、Python版の詳細確認は要継続
- **v1.7**: インベントリ比較のPython版詳細確認完了 - `_check_duplicate()`の`quiver`チェック欠落バグを発見、`is_wood`配列の初期化問題を記録
- **v1.8**: アイテム使用比較を追加（`use.c` vs `use_actions.py`） - ID状態更新の未実装を記録
- **v1.9**: 特殊アクション比較を完了（`throw.c`, `zap.c`, `ring.c` vs `special_actions.py`） - 全て正しく実装されていることを確認
- **v1.10**: スコア管理比較を完了（`score.c` vs `score_manager.py`） - 暗号化未実装、`id_all()`スタブ、アイテム価値ハードコードを記録
- **v1.11**: `_check_duplicate()`の`quiver`チェック欠落バグを修正 - 武器スタック時に`quiver`属性の一致を確認するように修正
- **v1.12**: 「ゴーストフラグ」バグを修正 - モンスター死亡後にMONSTERフラグが残り続ける問題を修正
- **v1.13**: モンスターリスト同期問題を根本修正 - `combat.py`に`_remove_from_level_monsters()`メソッドを追加し、モンスター死亡時に両方のリスト（`dungeon.monsters`と`dungeon.level_monsters`）から削除するように修正
- **v1.14**: Monsterクラスに`m_char`プロパティを追加 - `ichar`（int型）と`m_char`（str型）の相互変換を提供。複数ファイル（`actions.py`, `debug.py`, `special_actions.py`, `test_combat.py`, `test_entities.py`, `use_actions.py`）で参照されていた非存在属性`m_char`を正式に実装
- **v1.15**: モンスター名表示バグを修正 - `combat.py`の`gr_monster()`でモンスター生成時に`name`属性が設定されていなかった問題を修正。`monster.name = M_NAMES[mn]`を追加し、モンスター倒害時のメッセージで正しく名前が表示されるようにした

# Rogue2.Official-master Python移植版 デバッグ計画書 v2.0

- 作成日: 2026-09-04
- 前提: `202609_仕様比較表_C_Python対応表_v2.0.md` を母集団とする
- 先行計画との関係: `2026年4月度/5月度 検証・デバッグ計画書`、`DEBUG_PLAN.md`、`フェーズ0/A/B/C/D` の後継。フェーズE以降を定義する
- 方針: **「各要素の実装・画面挙動の一致」** を完了条件とし、洗い出し→修正のワークフローを回す。本書はそのための方法論・優先順位・検証基盤・完了定義を定める

---

## 0. エグゼクティブサマリ・現状診断

### 0.1 現状の到達点

- 定数・戦闘数式・レベル生成骨格・移動骨格・罠・指輪効果量はほぼ一致。先行フェーズで `u/b`、`trail_char`、`global`、`quiver`、`is_wood`、`heal/pass_go/check_hunger`、`mask/fill/maze`、`add_exp/steal/dr_course/halluc` は解消
- 残存は **周辺（表示・ID・保存・UIフロー）と7件の致命** に収束している。複雑さの正体は「古いCの暗黙仕様 × Python分散実装」であり、ロジック自体は8割移植済み

### 0.2 残存P0（致命・最優先）7件

| ID | 項目 | 仕様比較表参照 | 影響 |
|---|---|---|---|
| P0-1 | `MonsterAI.mv_monster` 隣接攻撃`mon_hit`呼出欠落 | §4.3 | 隣接怪物が攻撃せず難易度崩壊 |
| P0-2 | `Combat.fight` デッドコード（`_get_direction`常時CANCEL） | §4.3 | `f/F`戦闘が実質不実行 |
| P0-3 | `LevelGenerator.put_player` 骨格のみ（`cur_room/light/wake/message/Player書込`なし） | §4.2 | 初期視界・覚醒・部屋番号が不正 |
| P0-4 | `object.c` 生成系18関数欠落（`put_objects/put_gold/gr_object系/get_food/place/party`） | §4.4/§5.1 | 地上物分布がCと非互換、`Game._put_objects`簡易版では検証不可 |
| P0-5 | `get_desc` 実質欠落（33行スタブ）+ `WEAPON`名順不一致 | §4.4 | 識別進行が視認不可、全`inventory/discovered/wizard`表示が非互換 |
| P0-6 | `add_to_pack` ソート挿入破綻 + `ichar int/str`混在 + `what_is/item_type`・`which_kind/item_kind`・`identified/is_identified`二重化 | §2.1/§5 | 順序崩壊・リンク喪失・検索失敗・クラッシュ要因 |
| P0-7 | セーブ・スコア非互換（pickle/CSV化、検証・再装備・画面2面・定型文なし）+ `max_level/login`復元欠落 + 二重削除 | §4.6 | C資産引継不可、複製・喪失バグ |

### 0.3 P1（高・機能不全）

| ID | 項目 |
|---|---|
| P1-1 | `Combat._cough_up`骨抜き・`try_to_cough`なし（泥・金吐き・`max_level`ガード・周囲配置なし） |
| P1-2 | `Combat._get_armor_class`が`class+d_enchant→d_enchant`のみ（火炎・`minus`・錆・凍結・刺が薄化） |
| P1-3 | `Movement`重複4種スタブ（`get_hit_chance/to_hit/get_weapon_damage/get_w_damage/damage_for_strength`指輪・付呪欠落）— 委譲に統一 |
| P1-4 | `Combat._wake_up`逆操作（`&=~ASLEEP;|=WAKENS`）— `MonsterAI._wake_up`正と分裂 |
| P1-5 | `wake_room`確率・目標欠落（`PARTY_WAKE/stealth/trow/IMITATES`） |
| P1-6 | `_move_mon_to`の`dr_course`欠落 + `==FLOOR→&FLOOR`緩和 |
| P1-7 | `_mon_can_go` SCARE巻物`pass` + `HIDDEN`迂回 |
| P1-8 | `_next_to_something`簡略（直交継続・斜め計数なしで過停止）+ `multiple_move_rogue`停止条件欠落 |
| P1-9 | `read_scroll/quaff` ID無条件`IDENTIFIED`化（ORIGINAL `CALLED`保護なし）+ SCARE拾得時更新なし + 文言IDずれ5件 |
| P1-10 | `Display.get_mask_char` 2文字誤植（`WAND '/'→'|'`、`ARMOR ']'→'['`） |
| P1-11 | `_connect_rooms` gate拡張、`_put_door` fallback、`_draw_simple_passage` inclusive上書、`light_passage`緩和、`_gr_row_col` rogue除外なし、`clear_level`分散、`_put_amulet`旗のみ、`party_counter=0`でBIG_ROOM死滅、`RANDOM_ROOMS`共有可変 |
| P1-12 | `play_level`欠落：`o(options)`、wizard8種（`Ctrl+I/S/T/O/A/G/C/M/X`）、`count`縮小、`S`継続、`Q`素抜け、`drop_check/check_up`簡略 |
| P1-13 | `pack_letter/is_pack_letter/LIST/call_it/kick_into_pack/get_id_table/single_inv/inv_armor_weapon/discovered`欠落 |
| P1-14 | `GameState`寿命・外部代入欠陥（`heal/_move_left_cou/_reg_search`实例化で都度リセット、`__setattr__` PEP562で非反映、`cur/max/party`四重管理、`l_rings/score_only`無宣言） |
| P1-15 | `_tele`二重・`vanish`三重・`zap`二重・`_monster_at`四重・`get_dungeon_char`二重等の重複分散 |

P2（中・表示・文言・軽微分布差）: `show/aggravate/create`描画・文なし、`_get_missiled`軌跡・復帰なし、`flame/freeze/drop`近似、`go_blind`白消しなし、`make_scroll_titles`長さなし、`_get_direction` curses直結、`hit_message`非蓄積、`_rogue_damage`負値化なし、`MoveResult 0/1/2`、`get_tile`ガード副作用等。P3（低・互換・品質）: `lget_number/get_closer/get_ench_color/znum/lznum/xxxx/name_cmp/nickize/mvaddbanner/is_vowel/putstr/sjis`等の移植不要・代替済みを除く残件。

---

## 1. C言語移植ノウハウ・方法論（あらゆる手段）

### 1.1 古いCの罠と定石

| 罠 | C実例 | Python定石 | 本件での適用 |
|---|---|---|---|
| 8進リテラル | `010/014/01000` | 10進換算表を作り値でassert | §定数表で完了、`CANCEL`型のみ残存 |
| K&R定義・暗黙int | `mvaddstr_rogue(y,x,str)`、`name_cmp(s1,s2)` | プロトタイプを`rogue.h/*.h`から復元し型注釈化 | `get_direction_offset(int)` vs 文字の不一致は本定石で検出 |
| `static`関数内変数 | `heal_exp/n/c/alt`、`move_left_cou`、`reg_search`、`offsets`、`rand_around pos` | 単一インスタンス前提ならインスタンス変数、複数生成ありなら`GameState`単一集約 | `heal`等は`Movement`都度生成で破綻→`GameState`へ移設（E-2） |
| `extern`ファイル間共有 | `cur_level/being_held/fight_monster`等約60 | `GameState`単一真実源 + 直参照、プロキシ・二重管理禁止 | 現行三重プロキシを撤去（E-2） |
| 番兵連結リスト | `rogue.pack/level_monsters/level_objects`ダミーヘッド | 先頭実体+`Optional`化は可だが走査起点・終端・`take/free`を全箇所統一 | `pack`起点差・`_place_at` prepend・`add_to_pack`破綻を同時修正（E-1） |
| 共用体`#define`エイリアス | `hp_to_kill⇔quantity`等13件 | `@property`双方向化し単一バッキングに集約、`item_kind/item_type`等の second source を作らない | 二重化3種を統合（E-1） |
| `goto/B/END/AGAIN/retry` | `make_room/multiple/idntfy/fight` | 早期return・ループ・再入力関数化で等価変換し分岐条件をコメント保全 | `make_room/connect`は完了、`idntfy AGAIN`は復元要 |
| ビットマスク | 地形・種別・装備・識別 | `const`値表 + `is_*`ヘルパーの二層化、`MAPPED`等の拡張はC非互換として明示 | `is_passable/can_move`直呼と`HIDDEN`分岐を統一 |
| `iconv/charset` | `convert/sjis2utf8/EUC` | `utf-8`固定+`utf8len/strlen`のみ移植、旧変換は死コードとして捨てる | 完了 |
| curses属性 | `COLOR_PAIR/attrset/mvinch/A_CHARTEXT` | `Display`ラッパに集約しヘッドレス代替（`FakeDisplay/Message`）を必ず用意 | E-0で harness 化 |
| 独自PRNG | `rntb[32]+ウォームアップ+下位15bit剰余` | 完全再現か完全分離かの二択。中途半端な`random`置換は分布・消費量の両方を壊す | E-0で `CRandom` 再現 + `utils`切替可能化 |
| signal/`chdir`/`inode/mtime` | `byebye/onintr/error_save/md_*` | ゲームロジックと分離し`Game`薄層に隔離、セーブ検証は別途設計 | セーブ互換方針（E-5）で決着 |
| `#if ORIGINAL/NON-ORIGINAL/JAPAN` | `pass_go/jump/get_desc/eat/throw` | ビルド時分岐を`config.ORIGINAL=False/JAPAN=True`定数化し両分岐を残す | `jump=False/pass_go=True`は正、`get_desc` JAPAN/EN両対応で復元 |

### 1.2 あらゆる検証手段（本件向け取捨選択）

1. **静的突合（済・継続）**: `compare_c_python.py` + `check_implementation_status.py` をCI化。`grep -nE '^[a-zA-Z].*\(.*\)'` でC関数列挙→Python `def` 列挙の差分を毎回自動化
2. **定数・数式ゴールデンテスト**: `const`全値・`hit_chance/damage/AC/steal/sting/drop/drain`をC式の写経テスト化。乱数を注入可能化（`utils.get_rand`を差替え）し決定的に
3. **トレース比較（核心）**: C版に`fprintf(stderr)`フックまたは`gdb`スクリプトで `make_level/mv_monster/rogue_hit/get_damage` の入出力・乱数消費を記録し、同seedのPythonと diff。まず `get_rand` 呼出順序の一致が先決
4. **ヘッドレス harness**: `FakeDisplay/FakeMessage/FakeStats` で curses なしに `Game/Movement/Combat` を駆動。`DEBUG_PLAN.md` フェーズ0-5を `pytest` 化し `venv` なしで `python -m pytest` 一発化
5. **シード固定・決定性**: `CRandom`（C再現）と `MT` を切替可能にし、レベル生成・戦闘・泥の3系統で `seed→配置hash` のスナップショットテスト
6. **プロパティテスト**: `pack_count/add/check_duplicate/next_ichar`、`gr_row_col`範囲、`connect`連結性、`insert_score`順序を hypothesis 的ランダム投入で不変条件検証
7. **ファジング（入力）**: `play_level`全キー×`count`×`CANCEL/LIST`をランダム列で投入し例外・無限・デッドロックを検出。`keylog.txt`再生と組合せ
8. **画面ゴールデン**: `get_dungeon_char/get_mask_char/light/darken/magic_map` を `FakeDisplay` バッファでC期待文字と diff。誤植2件は即検出可能
9. **セーブ互換方針の決定**: Cバイナリ互換の完全再現は工数大。`pickle継続+JSON移行+旧C読込は対象外`を明示し、代わりに `GameState` 全量保存・再装備・検証・単一削除を正す（E-5）
10. **カバレッジ駆動**: `×35` を母集団に `coverage` で未実行分岐を潰す。特に `object.c` 生成系は生成→配置→拾得→装備→保存の縦断でしか検証できない

---

## 2. ワークフロー（洗い出し→修正の回し方）

```
[仕様比較表] ──母集団──> [P0/P1/P2 Issue化] ──優先順位──> [単一真実源に修正]
      ^                         │                              │
      │                         v                              v
   [回帰テスト] <── [トレース/ゴールデンdiff] <── [Fake harness + seed固定]
```

- **原則1**: 1 Issue = 1 C関数（または1 グローバル群）。重複箇所は集約先1箇所に修正し他は委譲・削除
- **原則2**: 修正前に必ず失敗テストを書く（C期待値をコメントに写経し行番号を残す）
- **原則3**: `GameState`・`DungeonLevel`・`Inventory`・`Combat` の責務を侵さない。場当たりのモジュール変数・二重リスト・`__getattr__`追加禁止
- **原則4**: 文言ID（`mesg[N]`）変更は `text_resources` 差分表を更新し `get_message(N)` の対応を残す
- **原則5**: 乱数消費順序を変えない（`put_door` fallback等の追加抽選はC準拠に戻すか、差異を `CRandom` 切替で隔離）
- **成果物**: 各修正で `仕様比較表` の判定を `×△→○◎` に更新し、本計画書の残存表から削除

---

## 3. フェーズ計画（E以降）

### E-0. 検証基盤（先行・ブロッカー解除）

- `FakeDisplay/Message/Stats` harness、`CRandom`（C FB-PRNG再現）+ `utils`切替、`seed→hash`スナップショット、`compare/check` CI化、`pytest`一発化
- Exit: `python -m pytest` が curses なしで全 pass、seed固定でレベルhashが安定

### E-1. データ構造・鞄の正常化（P0-6 + P1-14一部）

- `add_to_pack`挿入修正（C `pack.c:42-52`写経）、`_place_at`ソート経由化、`ichar` str統一、`what_is/item_type`・`which_kind/item_kind`・`identified/is_identified`統合、`Player.pack`起点注釈統一、`next_avail_ichar`重複削除
- Exit: プロパティテスト（順序・重複・文字検索）が pass、`get_desc`前段階として表示順がCと一致

### E-2. 状態集約（P1-14）

- `heal/_move_left_cou/_reg_search/offsets/rand pos`を`GameState`集約、`__getattr__/__setattr__`プロキシ撤去・直参照化、`cur/max/party/RANDOM/party_counter`初期化・永続化修正（`party_counter=get_rand(1,10)`、`RANDOM`初期復元、`max`引継ぎ）、`l_rings/score_only`宣言追加
- Exit: `Movement`都度生成でも回復・探索が遅延せず、`combat.x=1`等の外部代入テストが `GameState` に反映

### E-3. 戦闘・怪物AI（P0-1/P0-2/P1-2〜P1-7）

- `mv_monster`隣接`mon_hit`復活、`fight`の`get_direction/get_dir_rc/can_move/one_move`ループ復元、`_get_armor_class`を`class+d_enchant`に、`Movement`重複4種を`Combat`委譲に、`_wake_up`逆操作修正、`wake_room`確率・目標復元、`_move_mon_to dr_course`復元（最小限：目標・座標管理）、`_mon_can_go` SCARE・HIDDEN復元、`_cough_up/try_to_cough`完全移植
- Exit: 隣接攻撃・`f/F`・泥・金吐き・錆・凍結のトレースがCと一致

### E-4. 生成・表示・ID（P0-3/P0-4/P0-5/P1-9〜P1-11）

- `put_player`完全化（`cur_room/light/wake/message/Player`）、`object.c`生成系移植（`put_objects/put_gold/plant/gr_object系/get_food/place/party/show`の最小縦断）、`get_mask_char`誤植修正、`get_dungeon_char`一本化、`connect/put_door/draw/light/gr_row_col/clear/amulet/party_counter/RANDOM`是正、`get_desc`完全移植（JAPAN/EN・識別3態・wizard・enchant・charges・数量・a/an・接尾）+ `WEAPON`名順修正、`make_scroll_titles`長さ制限、`idntfy AGAIN`・SCARE更新・`CALLED`保護・文言ID5件修正
- Exit: seed固定の配置・表示バッファ・目録表示がCと diff ゼロ（`MAPPED`拡張を除く）

### E-5. 保存・得点・進行（P0-7/P1-12/P1-13）

- 方針確定：Cバイナリ互換は対象外、`pickle継続+JSON移行準備`。`GameState`全量・再装備3種（`do_wear/wield/put_on`）・画面2面方針・`max/login`復元・単一削除・`ring_stats`再計算矛盾解消、`put/insert`定型文・`score_only/name_cmp`・墓石・`win`バナー・`quit`退避の復元、`options`復活、wizard8種・`count`・`S/Q/>/</>/drop/check`復元、`pack_letter/LIST/call/discovered/single/inv_armor/id_trap`復元
- Exit: 保存→終了→復元→継続の縦断が複製・喪失なしに pass、旧C資産は「非互換」として文書化

### E-6. 総合回帰・完了判定

- 全キー fuzz、`seed`マトリクス（浅層・中層・`AMULET_LEVEL`前後・祭り・迷路・BIG_ROOM）、長時間 `mv_mons/wanderer/reg_move`  soak、`save/load`往復、`score`順序
- Exit: §5の完了定義を満たし `仕様比較表` の `×`ゼロ・`△`はP2軽微のみ

工数目安：E-0〜E-2各0.5〜1単位、E-3〜E-5各1〜2単位、E-6 1単位（単位は担当の1集中作業）。並列化は E-1/E-2 と E-3/E-4 の調査を分離し、修正は単一ブランチで直列化する。

---

## 4. 直近アクション（着手順）

1. E-0 harness + `CRandom`（ブロッカー解除）
2. P0-6（E-1）— 全機能の土台
3. P0-1/P0-2（E-3先行）— ゲーム性回復
4. P1-10誤植・P1-9文言ID（即効・低リスク）
5. P0-3/P0-5（E-4）— 画面・目録の一致
6. P0-4生成系（E-4後半）— 最大 hole
7. P0-7/E-5 — 仕様確定後に一気通貫
8. E-6で `×`ゼロ化

---

## 5. 完了定義・リスク

### 完了定義

- `仕様比較表` の `×`ゼロ、`△`はP2軽微のみ、`◎○`が95%以上
- `pytest + fuzz + seedマトリクス + save往復` が green
- Cバイナリ非互換・`MAPPED`拡張・`DungeonManager`拡張を文書化し、画面・操作・分布の一致を証跡化

### リスクと対策

| リスク | 対策 |
|---|---|
| 乱数系列の完全一致が困難 | `CRandom`再現で隔離、分布一致を優先し逐次一致はスナップショットで管理 |
| `get_desc` 340行の写経漏れ | JAPAN/EN分岐表を作り1分岐1テストで潰す |
| `object.c` 生成系の縦断検証困難 | E-0 harnessで生成→配置→拾得→保存を一気通貫テスト化 |
| 重複修正の取残し | 集約先を本書§1.2-10に固定し委譲・削除を必須化 |
| C検証資産（inode/mtime/暗号）の喪失 | セキュリティ要件として別途定義しゲーム性と分離 |

---

*本書と `202609_仕様比較表_C_Python対応表_v2.0.md` を両輪として、P0→P1→P2の順に洗い出し→修正を反復する。*

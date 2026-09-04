# Rogue2.Official C言語版 ↔ Python移植版 仕様比較表 v2.0

- 作成日: 2026-09-04
- 対象C: `src/*.c + *.h`（24モジュール, 約13,048行）
- 対象Python: `python/*.py`（実装約11,000行 + テスト約5,000行）
- 先行資料統合: `DIFFERENCES_LIST.md` / `相違点リスト_v1.0.md` / `SPECIFICATION.md` / `DEBUG_PLAN.md` / `202604_フェーズ0/1/補遺/最終` / `202605_フェーズA/B/C/D` / `移植作業報告書(Chutes GLM版)` / `移植手順書.md` / `INITIAL_VALUES_COMPARISON.md`
- 調査方法: 6系統並列精査（表示・初期化 / レベル・部屋 / 戦闘・移動・怪物 / 物・鞄・目録 / 使用・投擲・杖・指輪・特殊・罠 / 保存・得点・進行）+ `grep/wc`実測 + 定数値突合
- 判定凡例:
  - `◎ 対応` = ロジック等価（軽微な型・命名差のみ）
  - `○ 略対応` = 概ね移植だがメッセージ・描画・待機等の周辺欠落あり
  - `△ 部分的` = 存在するが分岐・条件・引数・副作用の欠落あり（要修正）
  - `× 未実装/スタブ` = 指定範囲に対応なし、常時CANCEL/空実装/`pass`、または範囲外にもなし
  - `→移設` = 指定Pythonファイル内にはないが他Pythonファイルに存在

---

## 0. 全体規模・ファイル対応表

### 0.1 行数実測

| Cファイル | 行数 | Python対応先 | 行数 | 備考 |
|---|---|---|---|---|
| `rogue.h` | 450 | `const.py(462)` + `entities.py(760)` | 1222 | 定数+構造体を2分割 |
| `display.c` | 328 | `display.py(941)` | 941 | cursesラッパ+照明+目録表示を集約し肥大 |
| `hit.c` | 410 | `combat.py(1583) Combat部` | — | `spechit`一部も`Combat`に混入 |
| `init.c` | 601 | `game.py:_init/_player_init(171-352)` + `config.py(152)` + `main.py(88)` | — | `do_args/do_opts/player_init/signal`が分散 |
| `invent.c` | 876 | `inventory.py(636) + display.py:655-780` | — | `get_desc`は33行スタブ化で大幅縮小 |
| `level.c` | 825 | `level_generator.py(692)` | 692 | `drop_check/check_up/add_exp`は移設 |
| `machdep.c` | 324 | `config.py + game.py:_clean_up/_signal_handler` | — | `md_*`はos/signal直書きに置換 |
| `main.c` | 123 | `main.py(88)` | 88 | `read_mesg/usage`は`text_resources/config`に分散 |
| `message.c` | 501 | `display.py:Message/Stats(787-941)` | — | `input_line/do_input_line`は未移植 |
| `monster.c` | 790 | `combat.py:MonsterAI部` | — | 26関数ほぼ網羅 |
| `move.c` | 578 | `actions.py:Movement(77-1280)` | — | `actions.py`全体で約1340行 |
| `object.c` | 905 | `game.py:_put_objects/_put_stairs(381-483)` + `inventory.py:_place_at` | — | `gr_object系8関数`は欠落 |
| `pack.c` | 599 | `inventory.py(636)` + `actions.py:744-891`重複 | — | 二重実装あり |
| `play.c` | 590 | `game.py:_play_level(540-796)` | 257 | キー分岐は表で詳述 |
| `random.c` | 92 | `utils.py(253)` | 253 | MT化で系列非互換 |
| `ring.c` | 316 | `special_actions.py:RingAction(1080-1268)` | 188 | `message/reg_move`欠落で縮小 |
| `room.c` | 432 | `level_generator.py一部 + display.py:571-653` | — | `party_objects/gr_room`欠落 |
| `save.c` | 489 | `save_manager.py(214)` | 214 | pickle化で大幅縮小（粒度喪失） |
| `score.c` | 1069 | `score_manager.py(350)` | 350 | バイナリ→CSVで縮小（互換喪失） |
| `spechit.c` | 538 | `combat.py:423-802 + 1472-1570` | — | `cough_up/try_to_cough`のみスタブ |
| `throw.c` | 309 | `special_actions.py:ThrowAction(57-798)` | — | 概ね移植 |
| `trap.c` | 247 | `actions.py:TrapManager(1281-1360) + Movement._trap_*` | — | `id_trap/search`は分離・欠落 |
| `use.c` | 836 | `use_actions.py(852)` | 852 | 行数は酷似、ID更新・文言IDに差 |
| `zap.c` | 336 | `special_actions.py:WandAction(799-1079)` | 280 | 軌跡描画欠落 |
| 合計 | **13,048** | Python実装計 | **約11,200** (`game.py`1866含む) | 見かけは近いが欠落分は`game.py`肥大で相殺 |

### 0.2 モジュール対応総括

| Cモジュール | Python主対応 | 状態 | 一言 |
|---|---|---|---|
| `rogue.h` 定数 | `const.py` | ◎ | 8進→10進換算一致、`MAPPED=1024`のみ拡張 |
| `rogue.h struct obj/fighter/rm/dr/tr/id` | `entities.py + dungeon.py` | △ | `what_is/item_type`, `which_kind/item_kind`, `identified/is_identified`二重化、`ichar int/str`混在 |
| `display` | `display.py:Display` | ○ | 色・`mvinch`・照明は対応、`convert/iconv`は簡略 |
| `init` | `game.py:_init/_player_init + config/main` | △ | `do_opts/set_opts/env_get_value/utf8len`系・signal3種の完全性に欠落 |
| `message` | `display.py:Message/Stats` | △ | `message/remessage/check/print_stats`は対応、`input_line/do_input_line/rgetchar`編集本体なし |
| `machdep` | `config.py/game.py` | ○ | 機能は置換、セーブ検証（inode/mtime）なし |
| `random` | `utils.py` | △ | APIは対応、系列（FB-PRNG vs MT）非互換 |
| `main` | `main.py` | ○ | `-s/-r`は対応、`read_mesg`は`text_resources.load_from_file`に置換 |
| `level` | `level_generator.py` | ○ | `mask/fill/maze/hide`は実装済（旧報告の「未実装」は解消）、`put_player`は骨格のみ |
| `room` | `display.py + level_generator/dungeon` | △ | `get_dungeon_char/get_mask_char`に誤植2件、`party_objects/gr_room`なし |
| `monster` | `combat.py:MonsterAI` | ○ | `mv_monster`隣接攻撃呼出欠落のみ致命、他は○ |
| `hit` | `combat.py:Combat` | ○ | 数式一致、`fight`のみデッドコード化 |
| `move` | `actions.py:Movement` | ○ | `pass_go/bent_passage/check_hunger/heal`は実装済、`next_to_something`簡略+`multiple`停止条件欠落 |
| `object` | `game.py + inventory.py` | × | `put_objects/put_gold/gr_object系8種/make_party/show_objects/wizard`が欠落の最大 hole |
| `pack` | `inventory.py` | ○ | `quiver/new_obj`は修正済、`pack_letter/is_pack_letter/LIST/call_it/kick`が欠落 |
| `invent` | `inventory.py + display.py` | △ | `mix/is_wood`は対応、`get_desc/discovered/single/inv_armor`は欠落・スタブ |
| `use` | `use_actions.py` | ○ | ロジック対応、ID無条件化・文言IDずれ5件 |
| `throw` | `special_actions.py:ThrowAction` | ○ | `_check_gold_seeker=pass`のみ要修正 |
| `zap` | `special_actions.py:WandAction` | ○ | 軌跡・復帰・`DO_NOTHING`文欠落 |
| `ring` | `special_actions.py:RingAction` | △ | `_select_hand常左/inv_rings空/messageなし`で半スタブ |
| `spechit` | `combat.py` | ○ | `_cough_up`骨抜きのみ残存 |
| `trap` | `actions.py` | ○ | `id_trap`スタブのみ |
| `save` | `save_manager.py + game.py:_save/_restore` | △ | pickle化で非互換・検証なし・再装備なし |
| `score` | `score_manager.py + game.py:killed_by/_win` | △ | CSV化で非互換・墓石/定型文なし |
| `play` | `game.py:_play_level` | △ | `o`+wizard8種+count縮小が欠落（キー表参照） |

---

## 1. 定数対応表（`src/rogue.h` ↔ `python/const.py`）

実測で値一致を確認。8進表記は10進換算で比較。

### 1.1 地形・アイテム種別（完全一致）

| 定数 | C (`rogue.h`) | Python (`const.py`) | 判定 |
|---|---|---|---|
| `NOTHING/OBJECT/MONSTER/STAIRS` | `0/01/02/04` → 0/1/2/4 | 同値 | ◎ |
| `HORWALL/VERTWALL/DOOR/FLOOR/TUNNEL/TRAP/HIDDEN` | `010/020/040/0100/0200/0400/01000` → 8/16/32/64/128/256/512 | 同値 | ◎ |
| `MAPPED` | なし（Python拡張） | `1024` | ○拡張（Cにない表示用） |
| `GOLD/FOOD/ARMOR/WEAPON/SCROL/POTION/WAND/RING/AMULET/ALL_OBJECTS` | `01/02/04/010/020/040/0100/0200/0400/0777` → 1/2/4/8/16/32/64/128/256/511 | 同値 | ◎ |
| `LEATHER〜PLATE/ARMORS` | `0〜6/7` | 同値 | ◎ |
| `BOW〜TWO_HANDED_SWORD/WEAPONS` | `0〜7/8` | 同値 | ◎ |
| `PROTECT_ARMOR〜MAGIC_MAPPING/SCROLS` | `0〜11/12` | 同値 | ◎ |
| `INCREASE_STRENGTH〜SEE_INVISIBLE/POTIONS` | `0〜13/14` | 同値 | ◎ |
| `TELE_AWAY〜DO_NOTHING/WANDS` | `0〜9/10` | 同値 | ◎ |
| `STEALTH〜SEARCHING/RINGS` | `0〜10/11` | 同値 | ◎ |
| `RATION/FRUIT` | `0/1` | 同値 | ◎ |
| `NOT_USED/BEING_WIELDED/BEING_WORN/ON_LEFT/ON_RIGHT/ON_EITHER/BEING_USED` | `0/01/02/04/010/014/017` → 0/1/2/4/8/12/15 | 同値 | ◎ |
| `NO_TRAP/TRAP_DOOR/BEAR_TRAP/TELE_TRAP/DART_TRAP/SLEEPING_GAS/RUST_TRAP/TRAPS` | `-1/0/1/2/3/4/5/6` | 同値 | ◎ |
| `UNIDENTIFIED/IDENTIFIED/CALLED` | `00/01/02` → 0/1/2 | 同値 | ◎ |
| `MAX_PACK_COUNT/MAX_TITLE/MAXSYLLABLES/MAX_METAL/WAND_MATERIALS/GEMS/GOLD_PERCENT/PARTY_TIME` | `24/30/40/14/30/14/46/10` | 同値 | ◎ |
| `STAT_LEVEL/GOLD/HP/STR/ARMOR/EXP/HUNGER/LABEL/ALL` | `01/02/04/010/020/040/0100/0200/0377` → 1/2/4/8/16/32/64/128/255 | 同値 | ◎ |
| `PASSAGE/NO_ROOM/BIG_ROOM/MAXROOMS` | `-3/-1/10/9` | 同値 | ◎ |
| `R_NOTHING/R_ROOM/R_MAZE/R_DEADEND/R_CROSS` | `01/02/04/010/020` → 1/2/4/8/16 | 同値 | ◎ |
| `AMULET_LEVEL/MAX_EXP_LEVEL/MAX_EXP/MAX_GOLD/MAX_HP/ROGUE_LINES/COLUMNS/MIN_ROW` | `26/21/10000000/900000/800/24/80/1` | 同値 | ◎ |
| `STEALTH_FACTOR/R_TELE_PERCENT/HIDE_PERCENT/WAKE_PERCENT/FLIT_PERCENT/PARTY_WAKE_PERCENT` | `3/8/12/45/33/75` | 同値（`PARTY_WAKE→PARTY_WAKE_PERCENT`改名のみ） | ◎ |
| `CANCEL/LIST` | `'\033'(27)/'*'` (short/int) | `'\033'/'*'` (str) | △型相違（比較はstr前提で動作するがCは数値） |
| 確率表 `id_weapons/id_armors/id_scrolls/id_potions/id_wands/id_rings` value列 | `object.c:60-137` | `inventory.py:26-99` | ◎一致 |
| 素材表 `po_color/wand_materials/gems/syllables` 14/30/14/40件 | `object.c:52-56 + invent.c:29-51` | `inventory.py:102-139` | ◎件数・順序一致 |
| `fruit=mesg[333]` | `こけもも` | `text_resources.py:386` | ◎ |

### 1.2 要注意定数

- `PARTY_WAKE` → `PARTY_WAKE_PERCENT` 改名のみ、値75一致。`MonsterAI.wake_room`は常時`WAKE_PERCENT`で分岐欠落（§4）。
- `CANCEL` 型差は `inventory.py:318,343,382,413` の `ch==CANCEL` がstr比較になるため、Cの `short c` との直接移植ではないが動作上は無害。`game.py:_get_count` の `ESC→0` はC `CANCEL` と別扱いで要統一。

---

## 2. データ構造対応表

### 2.1 `struct obj`（`rogue.h:200-222`）→ `GameObject/Item/Monster`

Cの共用体エイリアス（`#define m_damage damage`等13件）をPythonは`@property`で再現。

| Cフィールド | 型/初期値 | Python | 判定 |
|---|---|---|---|
| `m_flags` | ulong 0 | `GameObject.m_flags=0` | ◎ |
| `damage` / `m_damage` | char* `"1d1"` | `GameObject.damage=""` + `Monster.m_damage↔damage` | △初期値 `""` vs `"1d1"` |
| `quantity` / `hp_to_kill` | short 1 | `GameObject.quantity=1` + `Monster.hp/hp_to_kill↔quantity` | ◎兼用再現 |
| `ichar` / `m_char` | short `'L'(76)` | `GameObject.ichar=0→ord('?')` + `Monster.m_char str↔int`、Itemはstr/int混在 | △型破綻（`chr(curr.ichar)`がstr時例外、`==ch`がint/str不一致で失敗し得る） |
| `kill_exp` | short | `GameObject.kill_exp=0` | ◎ |
| `is_protected` / `first_level` | short | `GameObject.is_protected=0` + `Monster.first_level/level_min↔is_protected` | ◎ |
| `is_cursed` / `last_level` | short 0 | `GameObject.is_cursed=0` + `Monster.last_level/level_max↔is_cursed` | ◎ |
| `class` / `m_hit_chance` | short | `GameObject.class_=0`（予約語回避）+ `Monster.hit_chance↔class_` | ◎ |
| `identified` / `stationary_damage` | short UNIDENTIFIED | `GameObject.identified=0` + `Monster.stationary_damage↔identified` + `Item.is_identified/is_called/call_name`併存 | △二重管理で未連動 |
| `which_kind` / `drop_percent` | ushort | `GameObject.which_kind=0` + `Monster.drop_percent↔which_kind` + `Item.item_kind=0`併存 | ×分裂（`_check_duplicate`は`item_kind`、`pack_count`は`which_kind`で判定不一致） |
| `o_row/o_col/o/row/col` | short | `GameObject.o_row/o_col/o/row/col=0` | ◎ |
| `d_enchant` / `trail_char` | short | `GameObject.d_enchant=0` + `Monster.trail_char str↔int` | ◎ |
| `quiver` / `slowed_toggle` | short（矢は0-126） | `GameObject.quiver=0` + `Monster.slowed_toggle↔quiver` | ◎ |
| `trow/tcol` | short | `GameObject.trow/tcol=0` | ◎ |
| `hit_enchant` / `moves_confused` | short | `GameObject.hit_enchant=0` + `Monster.moves_confused↔hit_enchant` | ◎ |
| `what_is` / `disguise` | ushort | `GameObject.what_is=0` + `Monster.disguise↔what_is` + `Item.item_type=0`併存 | ×分裂（所持系は`item_type`、一部は混用） |
| `picked_up` / `nap_length` | short 0 | `GameObject.picked_up=0` + `Monster.nap_length↔picked_up` | ○（`True/1`混用のみ） |
| `in_use_flags` | ushort NOT_USED | `GameObject.in_use_flags=0` + `is_being_wielded/worn/left/right/used` prop | ◎ |
| `next_object` / `next_monster` | struct obj* | `GameObject.next_object=None` + `Monster.next_monster↔next_object` | ◎ |
| `struct fight` | `pack:object`ダミーヘッド | `Player.pack:Optional[Item]=None`実体起点 | △意図的変更だが全走査起点が`pack` vs `pack.next_object`に相違 |
| `struct id` | value/title/real/id_status | `ItemId: value/title/real/id_status=UNIDENTIFIED` | ◎ |
| `struct rm/dr/tr` | rooms/doors/traps固定配列 | `Room/Door/Trap` dataclass + `DungeonLevel.rooms:List[Room]`等 | ◎（`doors[0]=上,1=右,2=下,3=左`は`dir//2`と一致） |

### 2.2 主要クラス対応

| C概念 | Pythonクラス | 判定 |
|---|---|---|
| `fighter rogue` | `entities.Player`（hp/str/exp/gold/row/col/fchar/moves_left=1250/armor/weapon/left_ring/right_ring/pack） | ○（pack番兵廃止、gold/exp int化のみ） |
| `object level_monsters/level_objects` 番兵連結 | `DungeonLevel.monsters:List + level_monsters:Optional`二重、`level_objects:Optional`連結 | △二重管理で同期漏れ・走査対象不統一（`Combat._monster_at`は`monsters`、`Movement._monster_at`は`level_monsters`） |
| `dungeon[24][80] ushort` | `DungeonLevel.dungeon:List[List[int]]` + `get_tile/set_tile` | ○（`set_tile`はORでなく上書、`get_tile`範囲外→`HORWALL`はCにないガード） |
| `rooms[9]/rooms_visited[9]/traps[10]/descs[24][80]` | `DungeonLevel.rooms/traos/descs` + `LevelGenerator.rooms_visited` | ○（固定→可変list、`clear`は再生成） |
| `DungeonManager` | 新設（Cにない複数階保持） | ○拡張 |

---

## 3. グローバル変数対応表（C extern/static → Python `GameState`集約）

Pythonは `game_state.py:GameStateClass` シングルトンに集約し、`actions/combat/use_actions/special_actions` から `@property` / `__getattr__` プロキシで参照。方針自体は正しいが外部代入・寿命に欠陥あり（§7）。

| Cグローバル | C定義 | Python保持先 | 判定 |
|---|---|---|---|
| `fight_monster` | `hit.c:33 object*=0` | `GameState.fight_monster=None` | ○（外部`combat.fight_monster=x`はPEP562で非反映） |
| `hit_message[80]` | `hit.c:34 ""` | `GameState.hit_message=""` | △蓄積・表示せず`pass/msg`化 |
| `m_moves/jump/bent_passage/pass_go` | `move.c:32-38/init.c:42` | `GameState.m_moves/jump/bent_passage/pass_go` | ◎（`jump=False`は非ORIGINAL準拠） |
| `being_held/interrupted/mon_disappeared` | `spechit.c:36/rogue.h/monster.c:30` | `GameState.being_held/interrupted/mon_disappeared` | ◎ |
| `halluc/blind/confused/levitate/haste_self/see_invisible/extra_hp/detect_monster` | `use.c:33-40` | `GameState.*` | ◎ |
| `stealthy/r_rings/add_strength/e_rings/regeneration/ring_exp/auto_search/r_teleport/r_see_invisible/sustain/maintain_armor` | `ring.c:27-29` | `GameState.*` | ◎ |
| `cur_level/max_level/cur_room/party_room/party_counter/foods/r_de/new_level_message/random_rooms/level_points` | `level.c:30-59` | `GameState.* + LevelGenerator.* + DungeonLevel/DungeonManager` 四重管理 | △分散（`LevelGenerator`は`__init__`で`max`を`cur`に初期化し永続maxにならず、`put_player`の`cur_room`は死蔵、`party_counter`は常時0でBIG_ROOM死滅、`RANDOM_ROOMS`は共有可変で初期順序に戻らず） |
| `dungeon/rooms/level_monsters/level_objects/traps/descs` | `rogue.h:314-328/object.c` | `DungeonLevel.*` | ○ |
| `login_name/nick_name/rest_file/cant_int/did_int/score_only/init_curses/save_is_interactive/show_skull/ask_quit/org_dir/game_dir/use_color/error_file` | `init.c:34-46` | `config.py/Game/score_manager`に分散 | △（`score_only/login_name`は`GameState`無宣言で動的付与） |
| `msg_line/msg_col/msg_cleared/hunger_str` | `message.c:28-31` | `display.py:Message/msg_line/msg_col + GameState.hunger_str` | ○ |
| `is_wood/wand_materials/gems/syllables/po_title/sc_title/wa_title/ri_title` | `invent.c/object.c` | `inventory.py:is_wood/materials + text_resources` | ◎（`is_wood=(j>MAX_METAL)`再現済） |
| `cur_level/party_room/new_level/interrupted/ring_exp/sustain/blind`（trap extern） | `trap.c:39-44` | `GameState.*` | ◎ |
| `less_hp/flame_name/strange_feeling/left_or_right/no_ring/curse_message/unknown_command/you_can_move_again/fruit` | 各`.c` | `GameState.you_can_move_again/fruit`のみ、`less_hp/strange/left_or_right/no_ring`は欠落・直書き | △ |
| `trap_strings[12]` | `trap.c:34` | `actions.py:TRAP_MESSAGES`辞書 | ○（文言変更のみ） |
| `wizard/wiz_passwd` | `zap.c:33-35` | `GameState.wizard`（passwdなし） | △ |

---

## 4. 関数対応表

### 4.1 表示・初期化・メッセージ・機種依存・乱数・主処理

| C関数 | Python対応 | 判定 | 備考 |
|---|---|---|---|
| `display.c:init_color_attr/put_colorpair_number/get_colorpair_number/addch/mvaddch/addstr/mvaddstr/mvinch/convert` | `display.py:Display._init_color_attr/_get_color_pair/_put_colorpair_number/_get_colorpair_number/addch/mvaddch/addstr/mvaddstr/mvinch` | ○ | `convert/iconv`簡略、`sjis2utf8`死コードは移植不要、`ch_attr[256]`再現 |
| `init.c:utf8len/u8mb/utf8strlen` | `display.py:_utf8strlen + game.py` | ○ | `>127→2幅`近似 |
| `init.c:init/player_init/clean_up/start_window/stop_window/byebye/onintr/error_save` | `game.py:_init/_player_init/_clean_up/_init_curses/_signal_handler*` | △ | 食料+RINGMAIL+MACE/BOW+矢25-35は再現、`do_args(-s/-r)/do_opts/set_opts/env_get_value`のROGUEOPT/ROGUES連結・`chdir(game_dir)`・signal3種完全性に欠落 |
| `message.c:message/remessage/check_message/get_direction/input_line/do_input_line/rgetchar/print_stats/pad/save_screen/sound_bell/is_digit/r_index` | `display.py:Message.message/remessage/_check_message + Stats.print_stats/_pad/save_screen/sound_bell` | △ | `get_direction/input_line`編集本体（EUC/SJIS2バイト・MAX_TITLE・CANCEL・空白刈り）なし、`wait_for_ack`はinline化 |
| `machdep.c:md_heed/ignore/get_file_id/link_count/gct/gfmt/df/gln/ghome/malloc/gseed/exit/getlogin` | `config.py:get_game_dir/org_dir/save_path + game.py:_get_login_name/_get_random_seed/_clean_up` | ○ | inode/mtime検証なし、`putstr`宣言のみは移植不要 |
| `random.c:srrandom/rrandom/get_rand/rand_percent/coin_toss` | `utils.py:set_random_seed/get_rand/rand_percent/coin_toss/rnd/shuffle/roll_dice/parse_damage/roll_damage` | △ | API対応だがFB-PRNG(31要素+ウォームアップ310回+下位15bit剰余) vs MTで系列非互換、小区間バイアスも相違 |
| `main.c:main/read_mesg/usage` | `main.py:main/parse_args + text_resources.load_from_file` | ○ | `message_file/save_file`対応 |

### 4.2 レベル・部屋（`level.c/room.c` → `level_generator.py/dungeon.py/display.py`）

旧報告の「`mask_room`未実装」は解消済。現行は `◎` が大半。

| C関数 | Python対応 | 判定 |
|---|---|---|
| `make_level/make_room/same_row/same_col/add_mazes/fill_out_level/fill_it/recursive_deadend/mask_room/make_maze/hide_boxed_passage/mix_random_rooms` | `LevelGenerator.make_level/_make_room/_same_row/_same_col/_add_mazes/_fill_out_level/_fill_it/_recursive_deadend/_mask_room/_make_maze/_hide_boxed_passage/_mix_random_rooms` | ◎（`_mask_room`のみTuple化、`_mix`は共有可変） |
| `connect_rooms` | `LevelGenerator._connect_rooms` | △ gateが`R_ROOM\|R_MAZE`→`+R_DEADEND\|R_CROSS`に拡張され連結判定と矛盾 |
| `clear_level` | `DungeonLevel.clear + Game._clear_level` | △ `detect/see/held/bear/party/rogue/clear`の原子性なし、`traps [10]→[]` |
| `put_door` | `LevelGenerator._put_door` | △ 100回打切り+中央fallbackで地形破壊・乱数消費変動 |
| `draw_simple_passage` | `LevelGenerator._draw_simple_passage` | △ inclusive再描画でドア上書・clamp分岐で分布差 |
| `put_player` | `LevelGenerator.put_player` | △ 座標抽選のみ、`cur_room/light/wake/message/mvaddch/Player書込`欠落、`rogue同位除外`なし |
| `drop_check` | なし | × |
| `check_up` | →`Game._check_up` | △ `wizard`素通しなし |
| `add_exp/get_exp_level/hp_raise` | →`Player.add_exp/get_exp_level`内inline | ○（フェーズDで境界・MAX_EXP・wizard10を修正済） |
| `show_average_hp` | なし | ×（`Ctrl+A`と共に欠落） |
| `light_up_room/light_passage/darken_room` | →`Display.light_up_room/light_passage/darken_room` | ○（`MAPPED`拡張、`light_passage`は`can_move→is_passable`緩和で角越し点灯） |
| `get_dungeon_char` | `LevelGenerator.get_dungeon_char` + →`Display.get_dungeon_char` | △ 前者は`M/*`スタブで二重化、後者が忠実 |
| `get_mask_char` | →`Display.get_mask_char` | △ `WAND '/'→'|'`、`ARMOR ']'→'['` 誤植2件 |
| `gr_row_col` | `LevelGenerator._gr_row_col` | △ `rogue同位除外`なし |
| `gr_room` | なし | × |
| `party_objects` | なし（`Game._put_objects`は金35%+品25%簡易） | × `N/n/250試行/gr_object`なし |
| `get_room_number/is_all_connected/visit_rooms` | `DungeonLevel.get_room_number + LevelGenerator._is_all_connected/_visit_rooms` | ◎ |
| `draw_magic_map` | →`UseActions._draw_magic_map` | △ `trail_char`更新なし |
| `dr_course/get_oth_room` | →`Display.dr_course/_dr_course_entering/exiting` | ○（独立`get_oth_room`はinline化） |

### 4.3 怪物・命中・移動（`monster.c/hit.c/move.c` → `combat.py/actions.py`）

| C関数 | Python対応 | 判定 |
|---|---|---|
| `put_mons/gr_monster/mv_mons/gmc_row_col/gmc/aim_monster/rogue_can_see/move_confused/flit/gr_obj_char/no_room_for_monster/aggravate/mon_sees/mv_aquatars/mon_name/rogue_is_around/wanderer/show_monsters/create_monster/put_m_at` | `MonsterAI.put_mons/gr_monster/mv_mons/gmc_row_col/gmc/_aim_monster/_rogue_can_see/move_confused/_flit/_gr_obj_char/_no_room_for_monster/aggravate/_mon_sees/mv_aquatars/mon_name/_rogue_is_around/wanderer/show_monsters/create_monster/put_m_at` | ◎○（`gr_monster`は13列中8列複写で残留継承、`show/aggravate/create`は描画・文なし、`wanderer`は`free`なしで無害） |
| `party_monsters` | `MonsterAI.party_monsters` | △ `mon_tab`緩和→`cur_level`仮減算で弱体寄り |
| `mv_monster` | `MonsterAI.mv_monster` | × **隣接攻撃`mon_hit`呼出欠落（`return`のみ）— 致命** |
| `mtry/move_mon_to` | `MonsterAI._mtry/_move_mon_to` | ○△（`dr_course`欠落、`==FLOOR→&FLOOR`緩和、`mvinch→_get_dungeon_char`推定） |
| `mon_can_go` | `MonsterAI._mon_can_go` | △ SCARE巻物`pass`、`HIDDEN`迂回 |
| `wake_up/wake_room` | `MonsterAI._wake_up/wake_room + Movement.wake_room + Combat._wake_up` | △ 3分裂、`Combat`版は`&=~ASLEEP;|=WAKENS`逆操作、`PARTY_WAKE/stealth/trow/IMITATES`のいずれか欠落 |
| `mon_hit/rogue_hit/get_damage/get_w_damage/get_number/to_hit/damage_for_strength/mon_damage/get_hit_chance/get_weapon_damage` | `Combat.mon_hit/rogue_hit/_get_damage/_get_w_damage/_get_number/_to_hit/_damage_for_strength/_mon_damage/_get_hit_chance/_get_weapon_damage` | ◎○（数式一致、`_rogue_damage`は`killed_by`・負値化なし、`_mon_damage`は`cough_up`簡易化のみ、`_get_armor_class`は`class+d_enchant→d_enchant`欠落） |
| `lget_number` | なし | ×軽微 |
| `fight/get_dir_rc` | `Combat.fight/_get_dir_rc + Movement._get_dir_rc` | ×△（`fight`は`_get_direction`常時CANCELでデッドコード、`get_dir_rc`自体は`u/b`修正済で正） |
| `one_move_rogue/multiple_move_rogue/is_passable/can_move/is_direction/check_hunger/reg_move/rest/gr_dir/heal` | `Movement.one_move_rogue/multiple_move_rogue/is_passable/_can_move/is_direction/check_hunger/reg_move/rest/_gr_dir/_heal` | ○△（`pass_go/bent_passage/check_hunger気絶ループ/heal式`は実装済、`next_to_something`簡略+`multiple`停止条件欠落、`heal/_move_left_cou/_reg_search`は实例寿命で破綻、`MoveResult 0/1/2≠0/-1/-2`は内部のみで無害） |
| `next_to_something` | `Movement._next_to_something` | △ `MONSTER\|OBJECT\|STAIRS`直交継続・斜めTUNNEL計数欠落で過停止 |
| `move_onto` | `game.py`入力層に分散 | △ |
| `dr_course/cough_up/try_to_cough`（`move_mon_to/mon_damage`内） | なし / `Combat._cough_up`スタブ | ×（`try_to_cough`なし、`_cough_up`は5行簡易） |

戦闘数式は `Combat` 側で一致（`Movement` 側の重複4種 `get_hit_chance/to_hit/get_weapon_damage/get_w_damage/damage_for_strength` は指輪・付呪欠落のスタブで要削除・委譲）。

### 4.4 物・鞄・目録（`object.c/pack.c/invent.c` → `inventory.py/display.py/entities.py`）

最大の hole は `object.c` 生成系。

| C関数 | Python対応 | 判定 |
|---|---|---|
| `put_objects/put_gold/plant_gold/rand_place/put_amulet/put_stairs/make_party/next_party/show_objects/new_object_for_wizard/list_object/gr_object/gr_what_is/gr_scroll/gr_potion/gr_weapon/gr_armor/gr_wand/get_food/name_of/alloc/free/free_stuff` | なし（`Game._put_objects/_put_stairs`簡易のみ、`special_actions.gr_ring`のみ存在） | ×欠落（`alloc`初期値`ichar='L'/damage="1d1"`、`gr_*`確率表、`show_objects`透視もなし） |
| `place_at/object_at/get_letter_object` | `inventory.py:_place_at/_object_at/_get_letter_object` | ○（`_place_at`はprependでソート迂回） |
| `get_armor_class` | `entities.Player.get_armor_class` | △ `class+d_enchant/0` vs `10/10-d_enchant` |
| `add_to_pack/take_from_pack` | `inventory.py:add_to_pack/take_from_pack(+_remove_object)` | △ ソート挿入破綻（3件目以降崩壊・リンク喪失可能性）+地上/所持分離 |
| `pick_up` | `inventory.py:pick_up + actions.py:pick_up`重複 | △ SCARE時`id_scrolls[SCARE]=IDENTIFIED`更新欠落、`pack_count(obj)`自体は有 |
| `drop` | `inventory.py:drop` | ○（呪い3種検査一致、欠落は`message/mv_aquatars/print/reg_move/mesg[88-92]`） |
| `check_duplicate` | `inventory.py:_check_duplicate` | ○（`quiver`修正済、残差は`item_kind/which_kind`不整合と加算位置） |
| `next_avail_ichar/mask_pack/has_amulet` | `inventory.py:_next_avail_ichar/_mask_pack/has_amulet(+Player.next_avail_ichar重複)` | ◎○ |
| `pack_count` | `inventory.py:pack_count(new_obj=None)` | ◎（`new_obj`対応済） |
| `wait_for_ack/pack_letter` | `display.py inline + inventory.py:_pack_letter`スタブ | △ `is_pack_letter`記号→mask・`LIST→inventory`ループなし |
| `take_off/wear/unwear/do_wear/wield/do_wield/unwield` | `inventory.py:take_off/wear/unwear/do_wear/wield/do_wield/unwield` | ○（フラグ・`identified=1`一致、欠落は`message/mv_aquatars/print/reg_move`） |
| `is_pack_letter/call_it` | なし | ×（`CALLED`遷移手段なし） |
| `kick_into_pack` | なし | ×（`levitate`検査・`(ichar)`付加・`reg_move`なし） |
| `inventory` | `display.py:inventory + inventory.py:get_inventory_list` | △ 頁分割なし、`Protected`判定誤り（`getattr(curr,'is_protected')`） |
| `mix_colors/get_wand_and_ring_materials` | `inventory.py:mix_colors/get_wand_and_ring_materials` | ◎ |
| `make_scroll_titles` | `inventory.py:make_scroll_titles` | △ JAPANのみ、長さ制限・ENなしで幅超過可 |
| `get_desc` | `display.py:get_item_desc` 33行スタブ | ×実質欠落（識別3態・wizard・enchant・charges・数量・a/an・装備接尾なし、`WEAPON`名順もC `mesg[374-381]`と不一致） |
| `get_id_table/single_inv/inv_armor_weapon/discovered/znum/lznum` | なし | × |

### 4.5 使用・投擲・杖・指輪・特殊・罠

| C関数 | Python対応 | 判定 |
|---|---|---|
| `quaff/read_scroll/vanish/potion_heal/idntfy/eat/hold_monster/tele` | `use_actions.py:quaff/read_scroll/_vanish/_potion_heal/_idntfy/eat/_hold_monster/_tele` | ○（`_idntfy`は`AGAIN goto`・desc表示欠落、`_vanish`は`free/reg_move`欠落、`_potion_heal`は完全） |
| `hallucinate/unhallucinate/unblind/relight/take_a_nap/go_blind/confuse/unconfuse/uncurse_all/get_ench_color` | `use_actions.py + actions.py`二重 | △ `go_blind`部屋白消しなし、`_unconfuse/_unhallucinate`文言ID誤り、`get_ench_color`欠落（`mesg[275]`直埋め） |
| `throw/throw_at_monster/get_thrown_at_monster/flop_weapon/rand_around/potion_monster` | `special_actions.py:ThrowAction.throw/_throw_at_monster/_get_thrown_at_monster/_flop_weapon/_rand_around/_potion_monster` | ○（`_check_gold_seeker=pass`、`hit_message/curse/mv_aquatars/消失mesg[215]`なし） |
| `zapp/get_zapped/get_missiled/zap_monster/tele_away/wizardize` | `special_actions.py:WandAction.zapp/_get_zapped/_get_missiled/_zap_monster/_tele_away + Game._wizardize`スタブ | ○△（`_get_missiled`軌跡・復帰なし、`DO_NOTHING`無言、`_wizardize`はpasswdなし即時反転） |
| `put_on/do_put_on/remove/un_put_on/gr_ring/inv_rings/ring_stats` | `special_actions.py:RingAction.put_on_ring/_do_put_on/remove_ring/_un_put_on/gr_ring/inv_rings/_ring_stats` | △ `_select_hand`常左、`inv_rings`空、`message/reg_move/print/relight`なし |
| `special_hit/rust/freeze/steal_gold/steal_item/disappear/sting/drop_level/drain_life/m_confuse/flame_broil/seek_gold/gold_at/check_gold_seeker/check_imitator/imitating/get_closer` | `combat.py:Combat/MonsterAI`に移設 | ○（`cough_up/try_to_cough`のみ×、`get_closer`はinline化、`_wake_up`逆操作、`_check_gold_seeker`は`ThrowAction`側`pass`） |
| `trap_at/trap_player/add_traps/id_trap/show_traps/search` | `actions.py:_trap_at/_trap_player/TrapManager.add_traps/show_traps + Movement.search/_search + Game._id_trap`スタブ | ○△（`id_trap`未実装固定文のみ） |

### 4.6 保存・得点・進行（`save.c/score.c/play.c` → `save_manager.py/score_manager.py/game.py`）

| C関数 | Python対応 | 判定 |
|---|---|---|
| `save_game/save_into_file/restore/write_pack/read_pack/rw_dungeon/rw_id/write_string/read_string/rw_rooms/r_read/r_write/has_been_touched` | `save_manager.py:save_game/load_game + game.py:_save_game/_restore/_restore_ring_stats` | △ pickle一括で粒度・暗号・検証・再装備・画面2面なし |
| `killed_by/win/mvaddbanner/quit/put_scores/insert_score/is_vowel/sell_pack/get_value/id_all/name_cmp/xxxx/xxx/nickize/center/sf_error` | `score_manager.py:killed_by/win/_put_scores/_get_rank/_display_scores/_sell_pack/_get_value/_id_all/quit + game.py:killed_by/_win/center内関数` | △○（`sell/get_value/id_all`は○、`put/insert`はCSV・定型文なし、`killed_by/win/quit`は記録/描画に分裂し`put_scores`未連動・`show_skull/QUIT`分岐欠落、`mvaddbanner/xxxx/name_cmp/nickize`なし） |
| `play_level` 全キー | `game.py:_play_level` | △（キー表参照：`o`+wizard8種なし、`count`縮小、`S`継続、`Q`素抜け、`v/?/@`簡易） |
| `help/identify/options/doshell` | `game.py:_help/_identify_char/_doshell`（`options`なし） | △○△× |

#### `play_level` 全キー対応（`play.c:51-310` vs `game.py:540-796`）

| Cキー | C動作 | Python | 判定 |
|---|---|---|---|
| `. s i f F hjklbyun HJKLBYUN+Ctrl系 e q r m d P R Ctrl+P Ctrl+W ) ] = T W w c z t @ D / ! a Space default` | 規定通り | 対応（`^→_id_trap`のみスタブ、`c→_call_it`スタブ、`D→_discovered`スタブ、`v→_show_version`1行簡易、`?→_help`17行簡易、`/→_identify_char`辞書簡易） | ○△ |
| `> <` | `drop_check/check_up→return` | STAIRS直検・`_check_up` | △ 罠・持物・wizard素通しなし |
| `Q S ,` | `byebye→killed_by(QUIT)/save_game/kick_into_pack` | `return1/_save_game(継続)/pick_up` | △ 終了・削除・levitate検査なし |
| `0-9` | 100未満蓄積→`goto CH`任意反復 | `s/./hjklbyun`のみ | △ 反復対象縮小 |
| `Ctrl+I/S/T/O/A/G/C/M/X` wizard8種+一括 | 地図・罠・物・怪・平均HP・生成 | なし（`1,3,7,9,13,15,19,20,24`未処理、`Ctrl+C`は終了に転用し衝突） | × |
| `o` | `options()` | なし→不明扱い | × |
| loop頭 `hit_message/trap_door/interrupted` | 処理 | `trap_door`のみ | △ |

---

## 5. 未実装・スタブ一覧（要修正の母集団）

### 5.1 完全欠落（CにありPython全域になし）

- `object.c`: `put_objects/put_gold/plant_gold/gr_object/gr_what_is/gr_scroll/gr_potion/gr_weapon/gr_armor/gr_wand/get_food/name_of/alloc_object/free_object/free_stuff/make_party/next_party/show_objects/new_object_for_wizard/list_object/put_amulet配置部/rand_place`
- `level/room`: `drop_check/show_average_hp/gr_room/party_objects`
- `pack/invent`: `is_pack_letter/call_it/kick_into_pack/get_id_table/single_inv/inv_armor_weapon/discovered/znum/lznum` + `get_desc`実体
- `use`: `get_ench_color`
- `spechit`: `try_to_cough/get_closer`
- `hit`: `lget_number`
- `save`: `write_pack/read_pack/rw_dungeon/rw_id/write_string/read_string/rw_rooms/r_read/r_write/has_been_touched/xxxx/xxx`
- `score`: `mvaddbanner/is_vowel/name_cmp/nickize`
- `play`: `options` + wizard8種（`Ctrl+I/S/T/O/A/G/C/M/X`）+ `show_average_hp`

### 5.2 スタブ（存在するが空・固定文・常時CANCEL）

- `Combat._get_direction:804` 常時CANCEL → `fight`デッドコード化
- `Combat._cough_up:793` 5行簡易
- `ThrowAction._check_gold_seeker:610` `pass`
- `RingAction._select_hand:1208` 常左、`inv_rings:1243` 空
- `Game._id_trap:1690/_call_it:1651/_discovered:1600` 固定文
- `Game._wizardize:1795` passwdなし反転
- `Movement`側重複4種（`get_hit_chance/to_hit/get_weapon_damage/get_w_damage/damage_for_strength:908-944`）は指輪・付呪欠落スタブ
- `LevelGenerator._put_amulet:625` 旗のみ、`get_dungeon_char:660` `M/*`スタブ
- `Display.get_mask_char:561` 2文字誤植、`inventory.py:_pack_letter:559` 単発版

### 5.3 重複実装（修正は全箇所要・委譲に統一すべき）

| 機能 | 箇所 | 推奨集約先 |
|---|---|---|
| `hallucinate/unhallucinate/unblind/unconfuse/relight/tele/take_a_nap/rust` | `use_actions.py` vs `actions.py` | `UseActions`に集約し`Movement`は委譲 |
| `vanish` | `use_actions._vanish` vs `ThrowAction._vanish` vs `Combat._vanish_item` | `InventoryManager`または`UseActions`に一本化 |
| `zap_monster/gr_monster/tele_away/rogue_hit` | `ThrowAction:644-788` vs `WandAction:877-993` | 共通`Combat`に委譲 |
| `search/reg_search` + `TrapManager(add/showのみ)` | `Movement` vs `TrapManager` | `TrapManager`に集約または明確分担 |
| `pick_up/pack_count/check_duplicate/add_to_pack/mon_hit/rogue_hit/wake_room/gr_obj_char` | `actions.py` vs `inventory/combat` | `Inventory/Combat/MonsterAI`に委譲 |
| `_monster_at`走査対象 | `Combat(monsters)` vs `Movement(level_monsters)` vs `ThrowAction(level_monsters)` vs `WandAction(monsters)` | `DungeonLevel`単一APIに統一 |
| `get_dungeon_char/get_mask_char/_tele/_gr_row_col` | `level_generator/display/use/special/combat`に分散 | `display`+`dungeon`に集約 |
| `LEVEL_POINTS/RANDOM_ROOMS` | `level_generator` vs `entities.Player` | `const`または`entities`に一本化 |
| `GameState`プロキシ | `actions/combat/use/special`の`@property/__getattr__`三重 | `GameState`直参照+外部代入禁止に統一（§7） |

---

## 6. 既知修正済み vs 残存（先行報告との突合）

| 先行指摘 | 現状 |
|---|---|
| 方向`u/b`逆転（v1.0 #1） | 解消済（`dungeon.get_direction_offset/actions._get_dir_rc/game/special`とも正） |
| `trail_char='.'`硬直（DIFF §最新） | 解消済（`_get_dungeon_char`使用） |
| `_mon_damage global`欠落（DIFF §10.2） | 解消済（`global fight_monster,being_held`追加、ただしPEP562外部代入欠陥は残存） |
| `interrupted int/bool`（DIFF §10.3） | 解消済（`True`統一） |
| `quiver`欠落（DIFF §11.9.1） | 解消済（ただし`item_kind/which_kind`不整合は残存） |
| `heal/check_hunger/pass_go/bent_passage`（v1.0 #9/DIFF §9） | 実装済（残差は寿命・停止条件のみ） |
| `mask_room/fill_it`未実装（v1.0 #14/15） | 実装済（`_mask_room/_fill_it/_recursive_deadend/_make_maze/_hide_boxed`あり） |
| `put_player`完全性（DIFF §8.4） | 未解消（骨格のみ） |
| `is_wood`（DIFF §11.9.2） | 解消済（`(j>MAX_METAL)`再現） |
| SCARE識別更新（DIFF §11.9.3） | 未解消 |
| `pack_count(new_obj)`（DIFF §11.9.6） | 解消済 |
| `read_scroll` ID更新（DIFF §12） | 未解消（無条件IDENTIFIED化） |
| `cough_up/mvaddch`コメアウト（DIFF §10.6） | 半解消（呼出は有効、中身がスタブ） |
| `add_exp/drop_level/steal_item/dr_course/halluc文字`（フェーズD） | 解消済 |
| 本表の残存P0/P1 | §7のデバッグ計画書へ引継 |

---

## 7. 統計サマリ

- C関数総数: 約205（`save/score`重複定義含むと約215）
- Python対応: `◎約70 / ○約80 / △約45 / ×約35`（重複・移設含む延べ数）
- 完全欠落の塊: `object.c`生成系（約18関数）が最大、`options/wizard`系、`get_desc/discovered`系が次点
- 致命（ゲーム進行停止・クラッシュ・無限・データ喪失に直結）は `mv_monster攻撃欠落/fightデッドコード/put_player骨格/object生成欠落/get_desc欠落/add_to_pack破綻/ichar・kind二重化/save互換喪失` の7件に収束
- 定数・数式（命中・ damage・AC除く・罠・指輪効果量）はほぼ一致し、残存は周辺（表示・ID・保存・UIフロー）に集中

---

*以上を母集団として、修正ワークフロー・優先順位・検証法は `202609_Rogue2_Python移植版デバッグ計画書_v2.0.md` に定義する。*

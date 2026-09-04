# 仕様比較表 v2.1 — ゼロベース再検証追補（v2.0 修正版）

- 作成日: 2026-09-04（v2.1）
- 親文書: `202609_仕様比較表_C_Python対応表_v2.0.md`（母集団・全関数表は継承。本追補が矛盾する場合は本追補を優先）
- 検証方針: **旧世代LLMの既存レポート（DIFFERENCES_LIST / 相違点v1.0 / SPEC / フェーズ0/A/B/C/D / 移植報告書）の「修正済み」「一致」記述を一切信用せず、CとPython現物のみで再判定**。6系統並列監査 + 作成者による現物grep裏付け済み
- 信頼度ラベル:
  - `V-OK` = 現物対照で修正・一致を確認（証拠行番号あり）
  - `V-NG` = 現物対照で未修正・不一致を確認（旧報告は誤り）
  - `V-REG` = 修正により改悪・退行（旧報告の処方が誤り）
  - `V-MIS` = 旧報告の判定自体が誤判定（見落とし・誇張・対象違い）
  - `V-PART` = 部分的に真（形状は正しいがデータ・副作用・寿命・分岐のいずれかが欠落）
  - `DYN` = 静的確定不可、動的検証要（最小手順付き）

---

## 1. 旧報告「修正済み」12項目の再検証結果（現物証拠付き）

| # | 旧主張 | 再判定 | C証拠 | Python証拠 | 補足 |
|---|---|---|---|---|---|
| R1 | 方向u/b修正済み | `V-OK` | `hit.c:370-386` u=row--col++ / b=row++col-- | `actions.py:653-654` u:UPRIGHT / b:DOWNLEFT、`dungeon.py:266,270` | y/n/h/j/k/l含め一致 |
| R2 | trail_char修正済み | `V-NG`（部分的） | `monster.c:399` mvinch取得、`406-410` `==FLOOR`厳密+blind条件 | `combat.py:1164,1174-1177` `_get_dungeon_char`推定 + `&FLOOR`緩和 | 画面取得→合成推定に劣化、ドア消去条件緩和。`V-PART` |
| R3 | fight_monster/being_held global修正済み | `V-OK`（条件付き） | `hit.c:33,47-48,287-289` / `spechit.c:36` | `game_state.py:81,107` + `combat.py:75-76,278,299-300` | 単一集約は正。外部`combat.x=`代入はPEP562で非反映の残存欠陥あり |
| R4 | interrupted型修正済み | `V-OK` | `rogue.h:27` char、`play.c:43`、`hit.c:61` | `game_state.py:83` bool、`combat.py:91` True | `True==1`で同値 |
| R5 | quiverチェック修正済み | `V-MIS`（誤判定・死文） | `pack.c:201-207,490-496` 比較 + `object.c:470` `quiver=get_rand(0,126)`付与 | `inventory.py:535-537` 比較文あり、ただしリポジトリ全体で`quiver=get_rand` 0件、`entities.py:62` 初期0のみ。作成者grepで裏付け | 比較文だけ移植し識別子付与なし。全武器quiver=0で常時合致 |
| R6 | heal静的変数修正済み | `V-REG`（改悪） | `move.c:554,566-571` static永続 | `actions.py:169-172,628-641` インスタンス変数 + `combat.py:349` fight毎`Movement(...)`新規 | 式は等価だが寿命劣化。fightループ内毎回リセットで回復停止 |
| R7 | check_hunger気絶ループ修正済み | `V-OK` | `move.c:423-434` | `actions.py:485-496,498-499` | `_move_left_cou`寿命は別件として分離 |
| R8 | pass_go/bent_passage修正済み | `V-NG` | `move.c:35,64,76-78,211-238` `do{}while(!next_to)`+retry | `game_state.py:86-87`、`actions.py:187,206-208` 設定のみ、`333-360` に`_next_to`呼出なし・row/col死変数 | フラグ設定は正、停止条件欠落で直進無限 |
| R9 | next_to罠条件（簡略指摘） | `V-NG`（未修正のまま） | `move.c:339-359` 継続条件+pass_count>1 | `actions.py:424-429` 即True×3、HIDDEN再確認は死条件 | 過停止 |
| R10 | hit_chance/damage数式一致 | `V-PART` | `hit.c:54-56,396-408` + `object.c:560` `class+d_enchant` | `combat.py:84-85,377-384` 本体一致、ただし`actions.py:908-925` 指輪欠落・`to_hit None→0`（Cは1）、`_get_armor 387-391` d_enchantのみ、`entities.py:653` `10-d_enchant` | Combat本体は概ね正、Movement重複4種+防具2種が不一致。負数`//`床除算1ずれ残存 |
| R11 | cough_up有効化済み | `V-NG` | `spechit.c:245-279` cur<maxガード+GOLD量+gr_object+螺旋try_to_cough | `combat.py:793-802` 同一マス直置きのみ | 呼出有効化のみ、中身スタブ |
| R12 | is_wood初期化済み | `V-PART` | `invent.c:27,555-565` + `object.c:280-281,721` 消費 | `inventory.py:142,156-164` 生成一致 + `game.py:291-292` 呼出一致、ただし`display.py:747-780` 消費なし・`is_wood`参照0件 | 生成は`V-OK`、消費（staff分岐・discovered）は未移植 |

追加再検証（旧報告の周辺主張）:

| 旧主張 | 再判定 | 証拠 |
|---|---|---|
| pack_count(new_obj)対応済み | `V-PART`（分裂） | `actions.py:811-828` 真、`inventory.py:479-496` は`which_kind` vs `_check_duplicate:532` `item_kind`分裂で矛盾（`_check True`かつ`pack_count 1`）。作成者レビューで確定 |
| 呪い検査対応 | `V-PART`（分岐のみ） | `inventory.py:327-341,362-371,407-409` 分岐一致、`message/reg_move/mv_aquatars`なし |
| mask/fill/maze/hide実装済み | `V-OK`（大半） | `mask:583-590` Tuple化のみ等価、`fill:496-552` static寿命のみ差、`recursive:554-581` ◎、`maze:410-451` OOBガードのみ差、`hide:453-477` ◎、`mix:619-623` ◎。旧報告の「RANDOM共有可変=バグ」は`V-MIS`（C同型永続で等価、隔離はテスト時のみ要） |
| draw_simple inclusive上書 | `V-MIS`（誇張） | 非隣接時3セグメント和集合は等価。真の差は隣接時clamp+`<=1`固定化（`level_generator.py:302-304,336-338` vs `level.c:351,366`）のみ |
| potion_heal/eat完全 | `V-NG` | 式は一致だが文言IDずれ（RESTORE 236/235、eat 265↔268 swap）で完全ではない。現物対照で確定 |
| vanish完全 | `V-NG` | `use_actions.py:341-343` `if rm: pass`、`special_actions.py:485-509` 同様。`reg_move`欠落を現物確認 |
| 無条件IDENTIFIED=バグ | `V-MIS`（半真） | C非ORIGINALは無条件（`use.c:158,277,380,484`）でPy無条件は合致。真の問題はORIGINALガード欠落+CALLED到達不能+pick_up二重化（`actions:751-764` 有 vs `inventory:277-284` 無） |
| 定数完全一致 | `V-PART` | 値一致は真。ただし`CANCEL/LIST` int→str型差、`MAPPED=1024`拡張（`grep MAPPED src/` 0件）、`PARTY_WAKE改名`主張は偽（両方75で改名なし、真の欠陥は用法分岐欠落） |

---

## 2. 新規発掘バグ（ゼロベース・旧報告見落とし分、32件要約）

### 2.1 戦闘・怪物（8件、監査N1-N8）

- `Z-C1 [致命]` mv_monster隣接攻撃欠落（`monster.c:262-264` vs `combat.py:1028-1030` コメントのみ）
- `Z-C2 [致命]` rogue_damage死亡鎖切断（`hit.c:152-161` killed_by+二重減算 vs `combat.py:172-183` returnのみ。`_killed_by`コメアウトと連動）
- `Z-C3 [高]` SCARE素通り（`monster.c:447-452` vs `combat.py:1209-1211` pass）
- `Z-C4 [高]` show_monsters非描画（`monster.c:569-570` vs `combat.py:1282-1293`）
- `Z-C5 [高]` rand_around累積+固定順（`throw.c:236-264` origin+swap vs `combat.py:1447-1454` 固定offsets+呼出側累積）
- `Z-C6 [高]` wake_room party75/45+stealth+trow欠落 + actions版簡略（`monster.c:471-493` vs `combat.py:1222-1224` + `actions.py:1016-1025`）
- `Z-C7 [中]` WAND `/`→`|`・擬態集合不一致（`room.c:162-164` vs `display.py:566`、`monster.c:715` vs `actions.py:1129`）
- `Z-C8 [中]` gr_row_col厳密性欠落（`room.c:187-191` 5条件 vs `combat.py:1439-1445` 1条件）

### 2.2 レベル・部屋（10件、B1-B10）

- `Z-L1` connect gate拡張（`level.c:234-235` vs `level_generator.py:198-199`）
- `Z-L2` put_door fallback地形破壊（無限 vs 100回+中央）
- `Z-L3` draw隣接分布差（C 2択 vs Py固定。非隣接は等価で旧報告誇張を訂正）
- `Z-L4` MAPPED+~mask受理縮小+自位置除外なし（`room.c:187-191` vs `level_generator.py:651-653` + `display:590,623`）
- `Z-L5` get_mask_char 2誤植（現物確認済み）
- `Z-L6` BIG_ROOM到達不能+party/max寿命+_put_amulet旗のみ二重配置
- `Z-L7` clear_level原子性喪失3件（traps 10維持→[]、rooms座標残存→ゼロ化、detect/see/held/bear/party/rogue残留）
- `Z-L8` draw_magic_map型クラッシュ+trail未更新（`mvinch int` vs `str`比較、`addch str` vs `chr(int)`要求）
- `Z-L9` fill offsets static永続 vs 毎回初期化
- `Z-L10` light_passage can_move→is_passable緩和（角越し・隠し誤点灯）

### 2.3 物・鞄・目録（8件、N1-N8）

- `Z-O1 [致命]` 三重二重化（what_is/item_type・which_kind/item_kind・identified/is_identified）。`game.py:302-344`放置0でmerge失敗を現物確認
- `Z-O2 [致命]` ichar int/str混在で両ヘルパー互いにTypeError（`entities:45,79-80,563-564` vs `inventory:225,355,549,555` vs `display:674`）。`chr(str)`実測
- `Z-O3 [高]` get_desc 340行→33行スタブ。ARMOR/WEAPON名順不一致、識別3態・enchant・charges・数量・a/an・接尾全欠落
- `Z-O4 [高]` get_armor_class逆符号+定数混入（C `class+d_enchant/0` vs `entities:653-658` `10/10-d_enchant`）
- `Z-O5 [高]` pack_letter/LIST対話欠落・先頭自動返却（`pack.c:246-279,517-550` vs `inventory:559-582`）
- `Z-O6 [中]` SCARE識別二重分裂（`actions:751-764` 有 vs `inventory:277-284` 無）
- `Z-O7 [中]` _place_at prepend vs ソートappend（`object.c:218-225` vs `inventory:630-636`）
- `Z-O8 [中高]` 生成確率表・初期値群未移植（gr_what_is/scroll/potion/weapon/armor/wand/food全表、alloc既定、`put_objects/gold/plant/stairs/rand/amulet/next_party/free/name/list/wizard/show/make_party`、scroll title長さ、single/id_table/inv_armor/discovered/call/mask/znum）

### 2.4 使用・投擲・杖・指輪・罠（8件抜粋、全量は監査報告参照）

- `Z-U1` 文言IDずれ8件確定：RESTORE 235→236使い回し（`use.c:80` vs `use_actions:115,118`）、SCARE 248→369（`use.c:309` vs `:211`）、hold0匹 269→230（`use.c:661` vs `:437`）、unhallucinate 272→277（`use.c:720` vs `:567`+`actions:1084`直書き）、eat 265↔268 swap（`use.c:614-626` vs `:305,315`）、REMOVE_CURSE halluc分岐消失（`use.c:365` vs `:262`）、flop 215消失（`throw.c:229` vs `special:283`直書き）、imitator/m_confuse/steal直書き化。作成者grepで裏付け
- `Z-U2` vanish reg_move欠落3箇所（現物`pass`確認）
- `Z-U3` _cough_up骨抜き・try_to_coughなし（前出R11）
- `Z-U4` Throw _check_gold_seeker pass（`throw.c:82` vs `special:610-613`）
- `Z-U5` _get_missiled軌跡・復帰なし（`zap.c:152-185` vs `special:855-875`）
- `Z-U6` Ring _select_hand常左・inv_rings空・message/reg_moveなし（`ring.c:35-250` vs `special:1086-1268`）
- `Z-U7` go_blind白消しなし（`use.c:764-793` vs `use_actions:700-712`）
- `Z-U8` get_ench_color欠落・halluc/tele/nap/rust/vanish/search重複分散（責務表はv2.0 §5.3継承）

### 2.5 保存・得点・進行（16件、N-SV/SC/PL）

- `Z-S1 [致命]` pickle RCE（`save_manager:159-160` vs C fread+xxxx）
- `Z-S2 [高]` login/file_id/mtime/余剰検証全欠落 + login復元なし（`save.c:199-265` vs `_restore:868-956`）
- `Z-S3 [高]` l_rings←r_ringsコピペ + login/max復元欠落（`game.py:1585-1586,1549`現物）
- `Z-S4 [中]` 破損時新規すり替え（`save_manager:148-175` None→`game.py:207-214`素通り vs C即終了）
- `Z-S5 [中]` 二重削除+失敗黙殺（`save_manager:162-167`→`game.py:945-947` vs `save.c:267-273`）
- `Z-SC1 [高]` score_only追放なし+CSV改竄自由（`score.c:489-508` vs `score_manager:87-146`）
- `Z-SC2 [中]` QUIT墓石+固定座標はみ出し（`score.c:96` vs `game.py:1067,1072`）
- `Z-SC3 [高]` 死因`other==HUNGRY(300)`到達不能（`game.py:1105` vs `actions:503,727`+`const:338`）
- `Z-SC4 [致命]` 実プレイ死亡スコアなし+怪物致死不死（`game.py:1058-1125` putなし + `combat:178`コメアウト+`172-179` return）
- `Z-SC5 [中]` winバナー固定+stdout混入
- `Z-P1 [高]` o完全欠落+wizard8種全欠落（`play.c:221-268,299` vs `_play_level:540-797`）
- `Z-P2 [中]` hit_message/interrupted初期化なし（`play.c:58-66` vs `game:556-558`）
- `Z-P3 [高]` count嚥下捨て（`_get_count:1834-1850` + `760-764`二重読み vs `play.c:209-218` goto CH）
- `Z-P4 [高]` S継続複製（`save.c:150-152`終了 vs `_save_game:1538-1598`継続）
- `Z-P5 [高]` Q即return（`game:577-579` vs `play:195-196→byebye→quit→killed_by→put_scores`）
- `Z-P6 [中]` >/</,条件縮小（levitate/wizard/OBJECT/reg_move。`level.c:692-706,709-729` + `pack.c:559-598` vs `game:582-586,1717-1744,639-640`）

### 2.6 表示・初期化（11件、B0-B10要約）

- `Z-D0` MAPPED幽霊ビット（`const:47`、src 0件。`display:254,590,623` + `RUSTS=1024`同値紛らわしさ）
- `Z-D1` message割込意味欠落（`message.c:40-66` vs `display:798-820`。mesg[11]直書き二重管理）
- `Z-D2` mvaddstr 187/188色欠落（`display.c:277-280` vs `display:203-215`）
- `Z-D3` print_stats JAPAN列→英語列固定+hunger clrtoeol欠落（`message.c:321-418` vs `display:872-934`）
- `Z-D4` pad len化+save_screen二重反転破損（`message.c:433,449-456` vs `display:940,473-485`）
- `Z-D5` get_direction連携欠落（`message.c:90-100` vs `game:1138-1150`）
- `Z-D6` rgetchar濾過+input_line本体欠落（`message.c:102-297` vs 対応なし。save_screen呼出者0）
- `Z-D7` signal三点欠落+PRNG非互換（`machdep:58-65` vs `game:102-109`、`random:21-91` FB vs `utils:16-44` MT）
- `Z-D8` do_args/do_opts未移植+save_file消失+read_mesg非互換（`init:327-600` vs `main:22-48`+`config:54-79`、`main:65-69`、`text:836-852` vs `main.c:90-112`）
- `Z-D9` player_init食料identified差（C UNIDENTIFIED既定 vs `game:300-306` =1。数量1はalloc既定依存で等価証明不能）
- `Z-D10` 初期化順序入替+ring_stats(0)欠落（`init:195-204` vs `game:282-293,958-1005`。RNG消費ずれ）

---

## 3. v2.0判定の訂正表（本追補による上書き）

| v2.0記述 | 訂正後 |
|---|---|
| quiver修正済み（§4.4/§6） | 死文に訂正。比較文のみで付与なし。E-1にquiver付与を復活 |
| heal正しく実装（§DIFF継承） | 改悪に訂正。GameState集約へ |
| pass_go/bent実装済み（残差は停止のみ） | フラグのみ正、停止条件欠落はP0級に格上げ |
| RANDOM共有可変=バグ | 誤判定に訂正。C同型で等価。テスト隔離のみ |
| draw inclusive上書でドア破壊 | 誇張に訂正。非隣接等価、隣接分布差のみ |
| 無条件IDENTIFIED=バグ | 半真に訂正。非ORIGINAL合致、ORIGINALガード+CALLED到達不能+二重化が真の問題 |
| 定数完全一致 | 条件付きに訂正（CANCEL型・MAPPED・PARTY改名主張の3点留保） |
| P0 7件 | P0 12件に拡大（Z-C1/Z-C2/Z-O1/Z-O2/Z-S1/Z-SC4を格上げ、Z-P3/Z-P4をP0に準ずる扱い） |
| 旧報告修正済みは信頼可 | 全て`V-*`再判定必須に変更。以降の修正は証拠行番号なしに「完了」と書かない |

---

## 4. 要動的検証リスト（静的確定を避けた18件）

 combat D1-D6（乱数分布・trail可視・heal実害・fight到達・interrupt・cough占有）、level 1-8（非隣接等価・隣接ハング・OOB・MAPPED影響・magic例外・dr_course例外・BIG到達・エンジン分離）、object D1-D7（pack順・分页・is_wood永続・分布・対話・透視・幅負）、use/save/score/play/display D群（§2各監査のDYN項目継承）。各最小手順は各監査報告の「要動的検証」章を正とする。

---

*本追補をもってv2.0の「修正済み」前提は廃棄し、v2.1デバッグ計画書の母集団とする。*

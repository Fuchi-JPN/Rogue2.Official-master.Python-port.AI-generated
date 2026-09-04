# Rogue2.Official-master Python移植版 デバッグ計画書 v2.1（ゼロベース改訂版）

- 作成日: 2026-09-04（v2.1）
- 親文書: `202609_Rogue2_Python移植版デバッグ計画書_v2.0.md` + `202609_仕様比較表_C_Python対応表_v2.0.md` + `202609_仕様比較表_C_Python対応表_v2.1_ゼロベース再検証追補.md`（本書と矛盾する場合は本書+v2.1追補を優先）
- 改訂理由: **既存検証レポートは旧世代LLM作成で「解消」記述が信用できない**。現物対照で誤判定・改悪・見落としを確認したため、ゼロベースで母集団・優先度・検証法を再定義する
- 本書の使い方: P0→P1→P2のIssue駆動で洗い出し→修正を回す。以降「完了」と書くには証拠行番号+C抜粋+回帰テストを必須とする

---

## 0. ゼロベース再検証の結論（v2.0からの変更点）

### 0.1 信頼崩壊の実例（現物裏付け済み）

- `quiver修正済み`→死文（付与`object.c:470`未移植、作成者grepで`quiver=get_rand` 0件確認）
- `heal正しく実装`→改悪（`combat.py:349` fight毎`Movement()`新規でカウンタ停止）
- `cough_up有効化`→呼出のみ、中身5行スタブ（`spechit.c:245-279` vs `combat.py:793-802`）
- `無条件IDENTIFIED=バグ`→半真（C非ORIGINALは無条件で合致。真の問題はORIGINALガード+CALLED到達不能+二重化）
- `RANDOM共有=バグ`→誤判定（C同型永続で等価）
- `draw inclusive破壊`→誇張（非隣接等価、隣接分布差のみ）
- 文言ID 8件ずれ（RESTORE/eat swap/SCARE/hold/unhallucinate/REMOVE_CURSE/flop等）を新規確定（`use_actions:115,211,305,315,437,567`現物）
- `vanish reg_move` 3箇所`pass`を現物確認（`use_actions:341-343`）
- `fight`常時CANCEL（`combat:804-807`）、`WAND/ARMOR`誤植（`display:566`）、pickle RCE（`save_manager:159-160`）、死因到達不能（`game:1105` vs `actions:503,727`）等、旧報告にない32+16+11件を新規発掘

### 0.2 P0の拡大（7件→12件）

| ID | 項目 | 根拠 |
|---|---|---|
| P0-1 | mv_monster隣接攻撃欠落 | Z-C1 |
| P0-2 | fightデッドコード | R10 + Z-C系 |
| P0-3 | put_player骨格 | Z-L系 |
| P0-4 | object生成18関数欠落 | Z-O8 |
| P0-5 | get_desc欠落 | Z-O3 |
| P0-6 | add_to_pack破綻+三重二重化+ichar混在 | Z-O1/Z-O2 |
| P0-7 | save/score非互換+復元欠落 | Z-S系 |
| P0-8（格上げ） | rogue_damage死亡鎖切断+不死 | Z-C2 + Z-SC4 |
| P0-9（格上げ） | quiver死文（分布・容量の前提崩壊） | R5 |
| P0-10（格上げ） | heal寿命改悪（回復停止） | R6 |
| P0-11（準P0） | count嚥下・S複製（経済・操作破壊） | Z-P3/Z-P4 |
| P0-12（準P0） | pickle RCE（配布・共有で危険） | Z-S1 |

P1は文言ID8件・cough/armor/wake/move/tele/mask/connect/door/clear/amulet/pack_letter/ring/GameState重複等約25件、P2は表示・色・幅・signal・do_opts等の約20件に拡大。詳細はv2.1追補§2を母集団とする。

---

## 1. 移植ノウハウ・方法論（拡充版）

### 1.1 二度と騙されないための原則（ゼロベース運用）

1. **文書は証拠にならない**: 「修正済み」はC行番号+Py行番号+両抜粋+テスト名の4点なしには受理しない。v2.1追補の`V-*`ラベルを全Issueに付与する
2. **形状とデータと寿命を分離**: 比較文があっても付与（quiver）・消費（is_wood）・寿命（heal/static）・呼出（fight/CANCEL）のいずれかが欠ければ未修正
3. **二重実装は分裂する**: pick_up（SCARE識別）、_tele、vanish、zap、_monster_at、get_dungeon_char、LEVEL_POINTS等は集約先を1つに固定し他は委譲・削除。両方直す運用は破綻する
4. **型は値と同じ**: CANCEL int→str、ichar int/str、MAPPED幽霊ビット、`//`床除算の負数1ずれ、`len` vs `utf8len` vs 幅2推定の3分裂は表示・分岐を壊す
5. **乱数は回数と値を分離**: FB-PRNG vs MTは値一致不可。回数等価（呼出順序）と分布等価（統計検定）を混同しない。`CRandom`再現で隔離する
6. **メッセージIDは転記ミスの温床**: mesg[N]→get_message(N)は全件機械突合し、直書きプロンプト・ハードコード文言を一掃する。今回8件確定済み
7. **セーブは互換・検証・原子性**: 形式・検証（login/file_id/mtime/余剰）・再装備・画面2面・単一削除・終了の6軸で設計する。pickle継続ならRCE対策（署名・JSON移行・読込制限）を必須とする

### 1.2 古いCの罠と定石（v2.0継承+追加）

v2.0 §1.1に加え、今回確定した追加定石：

| 罠 | 追加定石 |
|---|---|
| `alloc`既定値依存（quantity/ichar/identified/damage） | 既定値を`GameObject`に写経し`rand_place/drop`等の番兵`'L'`を再現する |
| 確率表の分散（gr_what_is/scroll/potion/weapon/armor/wand/food） | 表を`const`に集約しχ²検定で分布検証する。`game.py`簡易表は削除する |
| `try_to_cough`螺旋・`rand_around` swap・`offsets` static | 探索順をC通り（swap回数・初期順・累積有無）に再現しseed hashで検証する |
| `dr_course/get_oth_room`経路記憶 | ドア通過目標（trow）を捨てず`GameState`に保持する |
| `input_line/do_input_line`編集本体 | `call_it`/名前/果物のために最小再実装（MAX_TITLE・CANCEL・空白刈り）する |
| `do_opts/ROGUEOPT` | 環境差異として別途仕様化し、ゲーム性と分離する |
| `show_average_hp/Ctrl+A` | 非wizardでも有効なためwizard括りから外して復活させる |
| `MAPPED`等の独自拡張 | Cビットと衝突しないか（RUSTS=1024同値紛らわしさ）・保存互換・受理集合（~mask）への影響を必ず評価する |

### 1.3 検証手段の拡充（あらゆる手段の具体化）

1. **機械差分CI**: C関数grep→Py def grepの未対応リストを毎回生成。`quiver=get_rand` 0件のようなデータ側欠落も`grep 割当`で検出する
2. **ID機械突合**: `src/mesg` N→`get_message(N)`呼出の全件表を生成し、直書き・重複・欠番を検出する
3. **型混在検出**: `ichar`、`CANCEL/LIST`、`mvinch/addch` int/strの到達可能性を動的ダンプ+静的grepで洗う
4. **寿命検出**: `Movement()`生成箇所grep + `__init__`カウンタで`heal/move_left/reg_search`の進行率を測定する
5. **二重実装検出**: 同名`_tele/_vanish/_monster_at/get_dungeon_char`等の定義箇所列挙をCI化し、集約漏れを警告する
6. **トレース比較**: `get_rand`呼出順序の記録再生でレベル・戦闘・泥の分岐点を特定する（値一致は求めない）
7. **画面ゴールデン**: `FakeDisplay`バッファで`get_dungeon/mask/light/darken/magic`をC期待文字とdiffする（誤植2件は即検出）
8. **分布検定**: 生成表・泥・命中を統計検定する（ prohibition: 目視・少数試行での「一致」主張禁止）
9. **fuzz**: 全キー×count×CANCEL/LIST×wizardのランダム列で例外・無限・デッドを検出する（`keylog.txt`再生併用）
10. **save往復・改竄試験**: 正常往復・切断・複製・他人複写・16進改竄・二重削除・権限不足の7試験を必須化する
11. **セキュリティ試験**: pickle RCEのPoC確認→署名・JSON・許可型制限のいずれかで閉じる

---

## 2. ワークフロー（改訂）

```
[v2.1追補 母集団] → [Issue化（V-*+証拠4点）] → [失敗テスト先行] → [単一集約先に修正]
      ^                    │                                    │
      │                    v                                    v
 [v2.1追補更新] ← [回帰（機械差分+ID突合+型寿命+画面+分布+fuzz+save7試験）]
```

- 1 Issue = 1 C関数または1グローバル群または1文言ID。重複は集約先1箇所のみ修正
- 修正PRに `C行 / Py行 / 抜粋 / テスト名` を必須記載。旧報告引用のみは却下
- `DYN`は動的手順の実行結果なしに閉じない
- v2.1追補の判定を`V-NG→V-OK`に更新し、本書残存表から削除する

---

## 3. フェーズ計画（改訂E-0〜E-7）

### E-0. 基盤・機械化（ブロッカー解除）

Fake harness、CRandom切替、seed hash、機械差分CI、ID突合CI、二重・型・寿命検出、`pytest`一発化。Exit: cursesなしgreen + seed安定 + 未対応リスト自動生成

### E-1. 構造・寿命の正常化（P0-6/P0-9/P0-10 + GameState）

`add_to_pack`写経、`_place_at`経由化、ichar str統一、三重二重化統合（what_is/item_type等）、`quiver=get_rand(0,126)`+数量3-15復活、`heal/move_left/reg_search/offsets`のGameState集約、プロキシ撤去、cur/max/party/RANDOM/party_counter永続化、l_rings/score_only宣言。Exit: N1/N2再現スクリプトが正値（merge矛盾解消・TypeError解消）+ 10手進行率がCと一致

### E-2. 戦闘・AIの回復（P0-1/P0-2/P0-8 + P1戦闘群）

mv_monster攻撃復活、fightループ復元、rogue_damage鎖復元（killed_by+put_scores連動）、_get_armor修復、Movement重複4種委譲、_wake逆操作修正、wake確率目標復元、move_mon_to dr_course最小復元、mon_can_go SCARE/HIDDEN復元、cough/try_to_cough完全移植、rand_around swap復元、gr_row_col厳密化、show描画復元。Exit: 隣接攻撃・f/F・死亡・泥のトレース一致

### E-3. 生成・表示・IDの一致（P0-3/P0-5 + P1生成表示群 + 文言8件）

put_player完全化、object生成系縦断移植、get_mask誤植修正、get_dungeon一本化、connect/door/draw/light/gr/clear/amulet/party/RANDOM是正、MAPPED影響評価（除去フィルタ or 仕様化）、get_desc完全移植+WEAPON順修正+scroll長さ制限、idntfy AGAIN・SCARE・CALLED・ORIGINALガード・文言ID8件修正、vanish reg_move復活、magic/dr_course型修復。Exit: seed配置・表示バッファ・目録のdiffゼロ（拡張除く）+ 文言ID突合ゼロ

### E-4. 使用・投擲・杖・指輪・罠の完全化

eat/throw/zap/ring/spechit/trapの残存（missiled復帰・flop文言・gold_seeker・select右手・inv_rings・go_blind白消し・ench_color・search/id_trap・pack_letter/LIST・call/discovered/single/inv_armor・get_id_table・znum）。重複集約（tele/vanish/zap/search/pick_up等）を完了させる。Exit: 全分岐のID・文言・tick消費がCと一致

### E-5. 保存・得点・進行の再設計（P0-7/P0-11/P0-12 + P1進行群）

方針確定（C互換対象外を明言、pickle継続ならRCE対策必須）。全量保存・再装備3種・画面2面方針・max/login復元・単一削除・ring再計算矛盾解消、put/insert定型文・score_only・墓石・win・quit鎖復元、options復活、wizard8種・count・S/Q/>/</,復元、o復活。Exit: save7試験 + 死亡記録鎖 + fuzz green。旧C資産は非互換として文書化

### E-6. 表示・初期化の残存（P2群）

message割込・mvaddstr色・print列・pad幅・save_screen・get_direction・rgetchar・input_line・signal・seed・do_args/opts・player_init identified・順序・ring初回。Exit: JAPAN実画面の桁・色・入力・起動が一致

### E-7. 総合回帰・完了判定

seedマトリクス（浅/中/AMULET前後/祭/迷路/BIG）、soak（mv_mons/wanderer/reg_move長時間）、save往復・改竄、score順序、全キーfuzz。Exit: §4完了定義を満たし`×`ゼロ・`△`はP2軽微のみ

順序推奨: E-0 → E-1 → E-2先行（P0-1/2/8） → 文言即効 → E-3 → E-4 → E-5 → E-6 → E-7。E-1/E-2調査は並列可、修正は直列化。

---

## 4. 完了定義・リスク（改訂）

### 完了定義

- v2.1追補の`×`ゼロ、`△`はP2軽微のみ、`◎○`95%以上。各`V-NG/V-REG/V-MIS`が`V-OK`に更新され証拠4点付き
- `pytest + 機械差分 + ID突合 + 型寿命 + 画面 + 分布 + fuzz + save7試験 + セキュリティ試験` green
- C非互換（バイナリ・MAPPED・DungeonManager・MT既定）を文書化し、画面・操作・分布の一致を証跡化

### リスク

| リスク | 対策 |
|---|---|
| 再度の「直感修正」による改悪 | 証拠4点なし受理禁止、寿命・データ・呼出の3軸レビューを必須化 |
| 二重実装の取残し | 集約先固定表（v2.0 §5.3継承）+ CI検出で委譲・削除を強制 |
| 乱数完全一致への固執 | 回数・分布に分離し値一致は求めない。CRandomで隔離 |
| get_desc/object生成の工数膨張 | 1分岐1テストで分割しE-3を縦断（生成→配置→拾得→表示→保存）で検証 |
| pickle RCEの先送り | E-5のExit条件にし、暫定でも読込制限・署名・JSONのいずれかを先行適用 |
| 文言IDの再発 | ID突合CIで直書き・重複を検出し、新規文言はmesg番号必須化 |

---

*本書+v2.1追補をもってv2.0の前提は廃棄し、P0-12→P1→P2の順に洗い出し→修正を反復する。*

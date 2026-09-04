"""
driver.py - AI運転の統括（設計書 §7・§9・§10）

Game._get_input() から毎ターン呼ばれる。観測→決定→キー化→
後続キー投入→ログ→オーバーレイ→介入処理を一手分だけ行う。
ゲームロジックには一切触れない。
"""
import time

try:
    from .. import const
except ImportError:
    import const

try:
    from . import input_hook
    from . import actuator
    from . import monitor
    from . import observer
    from . import strategy
    from .policies import ScriptedPolicy
    from .schemas import AIOptions, IdentifyMemo, AIAction
    from .session_log import SessionLog, check_anomaly, load_replay_keys
except ImportError:
    import ai.input_hook as input_hook
    import ai.actuator as actuator
    import ai.monitor as monitor
    import ai.observer as observer
    import ai.strategy as strategy
    from ai.policies import ScriptedPolicy
    from ai.schemas import AIOptions, IdentifyMemo, AIAction
    from ai.session_log import SessionLog, check_anomaly, load_replay_keys


def _short_model(model: str) -> str:
    return model.split("/")[-1][:14]


class ForceQuit(Exception):
    """AI自動プレイ中の強制終了要求（キーX）。

    Game._get_input / AIDriver.next_key から送出される。
    run() の except Exception で捕捉され、finally の _clean_up で
    端末復帰後に終了する。途中の bare except に飲まれないよう、
    送出箇所（dispatcher・介入処理）は try の外に置くこと。
    """


class AIDriver:
    def __init__(self, game, options: AIOptions):
        self.game = game
        self.options = options
        self.active = True
        self.paused = False
        self.manual = False
        self.step_once = False
        self.turn = 0
        self.delay_ms = options.delay_ms
        self.memo = IdentifyMemo()
        self.history: list = []
        self.policy = None
        self.policy_name = "scripted"
        self.model_short = ""
        self.log = SessionLog(options.log_file)
        self._prev = None  # 直前ターンの記録（result確定用）
        self._replay_keys: list = []
        self._replay_idx = 0
        self._stuck_count = 0
        self._sig_window: list = []
        self._notice = ""  # オーバーレイに常時出す通知（LLM接続失敗等）
        self._llm_error_logged = ""
        self._ticker_text = ""  # 推論文ティッカー原文
        self._ticker_t0 = 0.0
        self._ticker_interval = 0.12  # 秒/文字
        self.trace = SessionLog(options.trace_file) if options.trace_file else None
        self.corrections = 0  # 不合理手の補正回数

    # -- 起動 ----------------------------------------------------------

    def start(self):
        self.log.open()
        if self.trace is not None:
            self.trace.open()
        input_hook.clear()
        input_hook.set_auto_ack(True)
        if self.options.replay_file:
            try:
                self._replay_keys = load_replay_keys(self.options.replay_file)
            except Exception as e:
                self._log_event("replay load failed: %s" % e)
                self._replay_keys = []
            self.policy_name = "replay"
            return
        if self.options.provider == "scripted" or not self.options.api_key:
            if self.options.provider != "scripted" and not self.options.api_key:
                # LLM指定なのにキーなし＝接続不能。フォールバックせず終了する
                try:
                    from .llm import LLMConnectionError
                except ImportError:
                    from llm import LLMConnectionError
                raise LLMConnectionError(
                    "LLM接続失敗[APIキー未設定] provider=%s model=%s → "
                    "OPENROUTER_API_KEY（またはOPENAI_API_KEY）を設定してください"
                    % (self.options.provider, self.options.model))
            self.policy = ScriptedPolicy(memo=self.memo)
            self.policy_name = "scripted"
            return
        # LLM
        try:
            from .llm import ChatClient, LLMAgentPolicy
        except ImportError:
            from ai.llm import ChatClient, LLMAgentPolicy
        client = ChatClient(
            endpoint=self.options.endpoint,
            api_key=self.options.api_key,
            timeout=self.options.timeout,
            model=self.options.model,
            max_tokens=self.options.max_tokens,
        )
        self.policy = LLMAgentPolicy(client, memo=self.memo,
                                     fallback=ScriptedPolicy(memo=self.memo),
                                     fallback_enabled=self.options.llm_fallback)
        self.policy_name = "llm"
        self.model_short = _short_model(self.options.model)

    def stop(self, reason: str = ""):
        if reason:
            self._log_event("stop: %s" % reason)
        self.active = False
        try:
            input_hook.set_auto_ack(False)
        except Exception:
            pass
        try:
            self.log.close()
        except Exception:
            pass
        try:
            if self.trace is not None:
                self.trace.close()
        except Exception:
            pass
        input_hook.clear()
        try:
            monitor.clear_ticker(self.game)
        except Exception:
            pass

    def force_quit(self):
        """強制終了：ログ確定→端末復帰→ForceQuit送出（即時終了）"""
        try:
            self._log_event("force quit by human (X)")
        except Exception:
            pass
        self.active = False
        try:
            self.log.close()
        except Exception:
            pass
        input_hook.clear()
        try:
            monitor.clear_ticker(self.game)
        except Exception:
            pass
        try:
            self.game._clean_up("")
        except Exception:
            pass
        raise ForceQuit("X")

    # -- Game._get_input からの呼び出し --------------------------------

    def next_key(self, manual_reader):
        """一手分のキーを返す。Noneは空転（入力なし扱い）"""
        if not self.active:
            return None
        if input_hook.consume_force_quit():
            self.force_quit()
        self._render_ticker()
        try:
            human = manual_reader()
        except ForceQuit:
            raise
        except Exception:
            human = None
        if human is not None:
            r = self._handle_human(human)
            if r is not None:
                return r  # 'Q'パススルー等
            if self.paused and not self.step_once:
                return None
            if self.manual:
                try:
                    return manual_reader()
                except Exception:
                    return None
        else:
            if self.paused and not self.step_once:
                return None
            if self.manual:
                return None

        # 追加入力待ち（fight方向・スロット選択等）への後続キーを優先する。
        # 新規判断より先に渡さないと、次手のキーがプロンプトに横取りされる
        queued = input_hook.pop_key()
        if queued is not None:
            return queued

        if self.turn >= self.options.max_turns:
            self._overlay("turn limit reached")
            self.stop("max turns %d" % self.options.max_turns)
            return None

        # リプレイモード
        if self._replay_keys:
            if self._replay_idx >= len(self._replay_keys):
                self.stop("replay exhausted")
                return None
            k = self._replay_keys[self._replay_idx]
            self._replay_idx += 1
            self.turn += 1
            self._overlay("replay %d/%d" % (self._replay_idx, len(self._replay_keys)))
            return k

        return self._ai_turn()

    # -- AI一手 ---------------------------------------------------------

    def _ai_turn(self):
        try:
            obs = observer.build_from_game(
                self.game, turn=self.turn,
                with_screen=bool(self.options.show_screen))
        except Exception as e:
            self._log_event("observation failed: %s" % e)
            return None

        # 直前ターンのresult確定
        if self._prev is not None:
            prev = self._prev
            prev["result"] = {
                "pos": list(obs.player_pos),
                "hp": [obs.status.hp_cur, obs.status.hp_max],
                "message": obs.message,
            }
            try:
                risk0 = strategy.assess(obs)
                anomaly = check_anomaly(
                    {"type": prev["action"].get("type")},
                    prev["prev_pos"], obs.player_pos,
                    target_passable=True)
                # 厳密な可否はBFS由来の weakest 判定に留める
                if anomaly and risk0.adjacent_enemies == 0:
                    prev["anomaly"] = anomaly
            except Exception:
                pass
            self.log.write(prev)
            self._prev = None

        # 停滞検知（位置・HP・所持・階層・敵影・品数の複合。空腹・文言は毎手
        # 変わるため除外。3マス以内の往復振動も検知する）
        sig = (tuple(obs.player_pos), obs.status.hp_cur,
               obs.status.gold, obs.status.level,
               len(obs.visible_monsters), len(obs.visible_items))
        self._sig_window.append(sig)
        if len(self._sig_window) > 12:
            self._sig_window = self._sig_window[-12:]
        if len(self._sig_window) >= 12 and len(set(self._sig_window)) <= 3:
            self._stuck_count += 1
        else:
            self._stuck_count = 0
        if self._stuck_count >= 8:
            st = obs.status
            self._overlay("stuck (no progress)", hp=(st.hp_cur, st.hp_max),
                          level=st.level, gold=st.gold)
            self.stop("stuck")
            return None

        t0 = time.time()
        try:
            action, thought = self.policy.decide(obs, self.history)
        except Exception as e:
            # LLM接続失敗・強制終了は飲み込まず上位へ（表示して終了するため）
            if e.__class__.__name__ in ("LLMConnectionError", "ForceQuit"):
                self._write_trace_error(obs, e)
                raise
            self._log_event("policy failed: %s" % e)
            return None
        latency_ms = int((time.time() - t0) * 1000)
        # 全文記録（prompt全文＋生応答。ai_trace.jsonl）
        self._write_trace(obs, latency_ms)
        # 不合理手の補正：壁方向へのmoveはscriptedで差し替え
        corrected = self._guard_illegal_move(obs, action)
        if corrected is not None:
            action, thought = corrected
            thought = thought + "（壁手補正）"
            self.corrections += 1
        # 通路追従の補正：純粋な通路状況でLLMが逸脱したら直進に戻す
        corr2 = self._guard_corridor(obs, action)
        if corr2 is not None:
            action, thought = corr2
            thought = thought + "（通路追従）"
            self.corrections += 1
        # 行き止まり探索の補正：予算内はsearchに統一する
        corr3 = self._guard_deadend(obs, action)
        if corr3 is not None:
            action, thought = corr3
            thought = thought + "（隠し扉探索）"
            self.corrections += 1
        # 高速移動への格上げ：最短路ヒント通りのmoveはrunにする
        if action.type == "move" and action.direction:
            hint_dir, _ = strategy.route_hint(obs)
            if hint_dir == action.direction and strategy.straight_runway(obs, action.direction, 3):
                action = AIAction(type="run", direction=action.direction)
                thought = thought + "（高速移動）"
        fallback = bool(getattr(self.policy, "last_fallback", False))
        if hasattr(self.policy, "last_latency_ms") and getattr(self.policy, "last_latency_ms", 0):
            latency_ms = self.policy.last_latency_ms
        # LLM接続失敗は原因を特定して表示・記録してからフォールバックする
        last_err = getattr(self.policy, "last_error", "") or ""
        if fallback and last_err:
            self._notice = "LLM×:%s" % last_err
            if last_err != self._llm_error_logged:
                self._llm_error_logged = last_err
                self._log_event("LLM connection failed [%s]; fallback to scripted" % last_err)
                if getattr(self.policy, "pinned_scripted", False):
                    self._log_event("LLM pinned to scripted after repeated failures")
        elif not fallback and self._notice.startswith("LLM×"):
            self._notice = ""  # 回復したら通知を消す

        keys = actuator.action_to_keys(action)
        if not keys:
            # noop：空転（ゲーム時間を進めない）
            self._set_ticker(getattr(self.policy, "last_reasoning", "") or thought)
            self._finish_turn(obs, action, thought, [], latency_ms, fallback)
            return None

        first, rest = keys[0], keys[1:]
        if rest:
            input_hook.push_keys("".join(rest))
        self._set_ticker(getattr(self.policy, "last_reasoning", "") or thought)
        self._finish_turn(obs, action, thought, keys, latency_ms, fallback)
        # 進行方向の記憶（次手の通路追従・heading表示用）
        try:
            if action.type == "move" and action.direction:
                if hasattr(self.policy, "heading"):
                    self.policy.heading = action.direction
        except Exception:
            pass

        if self.step_once:
            self.step_once = False
            self.paused = True
        if self.delay_ms > 0:
            time.sleep(self.delay_ms / 1000.0)
        return first

    def _write_trace(self, obs, latency_ms):
        """全文記録。失敗は無視"""
        if self.trace is None:
            return
        try:
            pol = self.policy
            self.trace.write({
                "turn": self.turn + 1,
                "model": self.options.model if self.policy_name == "llm" else "",
                "system": getattr(pol, "last_system", ""),
                "user": getattr(pol, "last_user", ""),
                "raw": getattr(pol, "last_raw", ""),
                "reasoning": getattr(pol, "last_reasoning", ""),
                "latency_ms": latency_ms,
                "pos": list(obs.player_pos),
            })
        except Exception:
            pass

    def _write_trace_error(self, obs, exc):
        """失敗時の原文記録（原因究明用）。失敗は無視"""
        if self.trace is None:
            return
        try:
            pol = self.policy
            self.trace.write({
                "turn": self.turn + 1,
                "model": self.options.model if self.policy_name == "llm" else "",
                "error": str(exc)[:300],
                "raw": getattr(pol, "last_raw", ""),
                "pos": list(obs.player_pos),
            })
        except Exception:
            pass

    def _guard_illegal_move(self, obs, action):
        """壁方向moveの差し替え。補正不要ならNone"""
        try:
            if action.type != "move" or not action.direction:
                return None
            if action.direction in strategy.legal_moves(obs):
                return None
            fb = getattr(self.policy, "fallback", None)
            if fb is None:
                try:
                    fb = ScriptedPolicy(memo=self.memo)
                except Exception:
                    return None
            return fb.decide(obs, self.history)
        except Exception:
            return None

    def _guard_corridor(self, obs, action):
        """純粋な通路状況での逸脱を直進に戻す。不要ならNone"""
        try:
            if self.policy_name != "llm":
                return None
            if getattr(self.policy, "last_fallback", False):
                return None
            if action.type != "move":
                return None
            heading = getattr(self.policy, "heading", None)
            if not heading:
                return None
            cache = getattr(obs, "_tile_cache", {}) or {}
            pr, pc = obs.player_pos
            cur = cache.get((pr, pc))
            if cur is None or not (cur & (const.TUNNEL | const.DOOR)):
                return None
            # 近接敵・至近品・足元階段があれば通常判断を尊重
            for m in obs.visible_monsters:
                if max(abs(m["pos"][0] - pr), abs(m["pos"][1] - pc)) <= 1:
                    return None
            for it in obs.visible_items:
                if max(abs(it["pos"][0] - pr), abs(it["pos"][1] - pc)) <= 2:
                    return None
            if obs.stairs_pos == (pr, pc):
                return None
            d = strategy.corridor_step(obs, heading)
            if d and d != action.direction:
                return AIAction(type="move", direction=d), "通路を直進"
            return None
        except Exception:
            return None

    def _guard_deadend(self, obs, action):
        """行き止まり予算内のsearch統一。不要ならNone"""
        try:
            if self.policy_name != "llm":
                return None
            if getattr(self.policy, "last_fallback", False):
                return None
            mem = getattr(self.policy, "memory", None)
            if mem is None:
                return None
            heading = getattr(self.policy, "heading", None)
            if action.type == "search":
                # 自発searchも予算計数する（打ち切り判定のため）
                if mem.deadend_pending(obs, heading):
                    mem.deadend_action(obs, heading)
                return None
            if not mem.deadend_pending(obs, heading):
                return None
            act = mem.deadend_action(obs, heading)
            if act is not None:
                return act, "隠し扉を探索"
            return None
        except Exception:
            return None

    def _finish_turn(self, obs, action, thought, keys, latency_ms, fallback):
        self.turn += 1
        act_dict = {"type": action.type, "direction": action.direction,
                    "item_slot": action.item_slot}
        self.history.append("%s->%s" % (act_dict, thought))
        if len(self.history) > 20:
            self.history = self.history[-20:]
        self._prev = {
            "turn": self.turn,
            "obs": _obs_summary(obs),
            "thought": thought,
            "action": act_dict,
            "keys": keys,
            "policy": self.policy_name,
            "model": self.options.model if self.policy_name == "llm" else "",
            "latency_ms": latency_ms,
            "fallback": fallback,
        }
        st = obs.status
        base_state = "PAUSED" if self.paused else ("MANUAL" if self.manual else "")
        state = " ".join(x for x in (self._notice, base_state) if x)
        self._overlay(thought, hp=(st.hp_cur, st.hp_max),
                      level=st.level, gold=st.gold, state=state)

    # -- 介入・表示・記録 --------------------------------------------------

    def _handle_human(self, key):
        """人間キーの横取り。キー返却が必要な場合のみ文字を返す"""
        if key == monitor.KEY_FORCE_QUIT:
            self.force_quit()
        if self.manual:
            if key == monitor.KEY_MANUAL:
                self.manual = False
                self._overlay("AI resumed")
                return None
            return key  # 手動中はすべて通す
        if key in monitor.KEY_PASSTHROUGH:
            return key
        if key == monitor.KEY_MANUAL:
            self.manual = True
            input_hook.clear()  # 残留する後続入力を破棄
            self._overlay("manual mode")
            return None
        if key == monitor.KEY_AI_QUIT:
            self._overlay("AI off")
            self.stop("human quit AI driving")
            return None
        if key == monitor.KEY_PAUSE:
            self.paused = not self.paused
            self._overlay("paused" if self.paused else "resumed")
            return None
        if key == monitor.KEY_STEP and self.paused:
            self.step_once = True
            return None
        if key == monitor.KEY_FASTER:
            self.delay_ms = max(0, self.delay_ms - 50)
            return None
        if key == monitor.KEY_SLOWER:
            self.delay_ms = self.delay_ms + 50
            return None
        # AI運転中の通常キーは無視（設計書 §7.3）
        return None

    def _overlay(self, thought, hp=(0, 0), level=0, gold=0, state=None):
        if state is None:
            base = "PAUSED" if self.paused else ("MANUAL" if self.manual else "")
            state = " ".join(x for x in (self._notice, base) if x)
        text = monitor.format_overlay(
            self.policy_name, self.model_short or "-", self.turn,
            self.delay_ms, thought, hp[0], hp[1], level, gold,
            state=state)
        # 端末に余白行がなければティッカーをオーバーレイ内に埋め込む
        if self._ticker_text and monitor.ticker_row(self.game) is None:
            frame = monitor.ticker_frame(self._ticker_text, 28, self.turn)
            text = monitor.truncate_width(text, 50) + " ~" + frame
            text = monitor.truncate_width(text, 79)
        monitor.render_overlay(self.game, text)

    def _set_ticker(self, text: str):
        """ティッカー原文の更新（変化時のみ時刻リセット）"""
        if text != self._ticker_text:
            self._ticker_text = text or ""
            self._ticker_t0 = time.time()

    def _render_ticker(self):
        """専用行へのティッカーフレーム描画（毎入力ポーリング）"""
        if not self._ticker_text:
            return
        if monitor.ticker_row(self.game) is None:
            return
        try:
            width = const.ROGUE_COLUMNS - 1
            offset = int((time.time() - self._ticker_t0) / self._ticker_interval)
            monitor.render_ticker(
                self.game, monitor.ticker_frame(self._ticker_text, width, offset))
        except Exception:
            pass

    def _log_event(self, msg: str):
        try:
            self.log.write({"event": msg, "turn": self.turn})
        except Exception:
            pass


def _obs_summary(obs) -> dict:
    st = obs.status
    return {
        "pos": list(obs.player_pos),
        "hp": [st.hp_cur, st.hp_max],
        "moves_left": st.moves_left,
        "level": st.level,
        "monsters": len(obs.visible_monsters),
        "items": len(obs.visible_items),
        "stairs": list(obs.stairs_pos) if obs.stairs_pos else None,
        "message": obs.message,
        "flags": obs.flags,
    }


def run_headless_smoke(seed=1, turns: int = 300, log_file: str = "") -> dict:
    """cursesなし高速スモーク（設計書 §7.4）。

    Game.run()を使わず Player/DungeonLevel/LevelGenerator/Movementを
    直接駆動する。移動・探索・戦闘（移動経由）のみ対象。
    """
    try:
        from .. import entities, dungeon as dungeon_mod
        from .. import level_generator as level_gen
        from .. import actions as actions_mod
        from .. import utils as utils_mod
    except ImportError:
        import entities
        import dungeon as dungeon_mod
        import level_generator as level_gen
        import actions as actions_mod
        import utils as utils_mod

    utils_mod.set_random_seed(seed)
    player = entities.Player()
    dung = dungeon_mod.DungeonLevel(level=1)
    level_gen.LevelGenerator(dung).make_level()
    # プレイヤー配置：最初のFLOORタイル
    placed = False
    for r in range(const.MIN_ROW, const.ROGUE_LINES - 1):
        for c in range(const.ROGUE_COLUMNS):
            try:
                t = dung.get_tile(r, c)
            except Exception:
                continue
            if t & (const.FLOOR | const.TUNNEL):
                player.row, player.col = r, c
                placed = True
                break
        if placed:
            break

    pol = ScriptedPolicy(memo=IdentifyMemo())
    move = actions_mod.Movement(player, dung, None, None, None)
    log = SessionLog(log_file) if log_file else None
    if log:
        log.open()
    history = []
    max_level_reached = 1
    try:
        for t in range(turns):
            obs = observer.build_observation(player, dung, turn=t)
            action, thought = pol.decide(obs, history)
            history.append("%s" % action.type)
            if len(history) > 20:
                history = history[-20:]
            if action.type == "move" and action.direction:
                try:
                    move.one_move_rogue(action.direction, True)
                except Exception as e:
                    if log:
                        log.write({"turn": t, "error": str(e)[:200]})
                    break
            elif action.type == "rest":
                try:
                    move.rest(1)
                except Exception:
                    pass
            elif action.type == "search":
                try:
                    move.search(1, False)
                except Exception:
                    pass
            elif action.type == "pickup":
                try:
                    move.pick_up(player.row, player.col)
                except Exception:
                    pass
            elif action.type == "fight" and action.direction:
                try:
                    move.one_move_rogue(action.direction, True)
                except Exception:
                    pass
            # descendはheadless対象外（階層遷移はGame.runの責務）
            if player.hp_current <= 0:
                break
            if log and t % 10 == 0:
                log.write({"turn": t, "obs": _obs_summary(obs),
                           "thought": thought,
                           "action": {"type": action.type,
                                      "direction": action.direction}})
    finally:
        if log:
            log.close()
    return {"turns": t + 1, "hp": [player.hp_current, player.hp_max],
            "pos": [player.row, player.col],
            "moves_left": player.moves_left,
            "max_level": max_level_reached}

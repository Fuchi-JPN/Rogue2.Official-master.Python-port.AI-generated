"""LLMクライアント・プロンプト・フォールバックの単体テスト（設計書 §6）"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai import llm
from ai.schemas import AIObservation, AIStatus, IdentifyMemo
from ai import strategy


class _FailClient(llm.ChatClient):
    def complete(self, system, user, temperature=0.2, max_tokens=512):
        raise RuntimeError("offline")


class _ScriptedClient(llm.ChatClient):
    def complete(self, system, user, temperature=0.2, max_tokens=512):
        return '{"type":"rest","reason":"休む"}', 5, "thinking about resting"


class TestLLM(unittest.TestCase):
    def test_strategy_section_from_constants(self):
        # 文面がstrategy正本から生成されていること（§6.5）
        s = llm.build_strategy_section()
        self.assertIn(str(int(strategy.HP_FIGHT_MIN * 100)), s)
        self.assertIn(str(strategy.HUNGER_OK), s)
        self.assertIn(str(strategy.HUNGER_URGENT), s)

    def test_parse_action(self):
        act, reason = llm.parse_action('```json\n{"type":"move","direction":"l","reason":" test "}\n```')
        self.assertEqual(act.type, "move")
        self.assertEqual(act.direction, "l")

    def test_parse_rejects_forbidden(self):
        with self.assertRaises(ValueError):
            llm.parse_action('{"type":"move","raw_keys":"Q"}')

    def test_parse_rejects_none(self):
        # content:null応答（'NoneType' has no attribute 'strip'の再発防止）
        with self.assertRaises(ValueError):
            llm.parse_action(None)

    def test_parse_control_chars(self):
        # 文字列内の生制御文字（Invalid control character対策）
        act, _ = llm.parse_action('{"type":"rest","reason":"a\x01b"}')
        self.assertEqual(act.type, "rest")
        # 前置余文つき
        act, _ = llm.parse_action('考えた結果\n{"type":"move","direction":"h"}')
        self.assertEqual(act.direction, "h")

    def test_max_tokens_default(self):
        # 推論系モデルのlength打切り対策で既定4096
        from ai.schemas import AIOptions
        self.assertEqual(AIOptions().max_tokens, 4096)
        self.assertEqual(llm.ChatClient().max_tokens, 4096)

    def test_classify_length_truncation(self):
        self.assertIn("--ai-max-tokens",
                      llm.classify_error(ValueError("empty content (finish_reason=length)")))

    def test_classify_empty_content(self):
        self.assertIn("応答本文が空",
                      llm.classify_error(ValueError("empty content (finish_reason=stop)")))
        self.assertIn("応答本文が空",
                      llm.classify_error(AttributeError("'NoneType' object has no attribute 'strip'")))

    def test_extract_message_content(self):
        self.assertEqual(llm.extract_message_content({"content": "hi"}), "hi")
        self.assertIsNone(llm.extract_message_content({}))
        self.assertEqual(
            llm.extract_message_content({"content": [{"type": "text", "text": "a"},
                                                     {"type": "text", "text": "b"}]}),
            "ab")
        self.assertEqual(llm.extract_message_content({"content": None, "reasoning": "r"}), "r")

    def test_fallback_on_failure(self):
        # 既定はフォールバックせず終了（原因付き）
        pol = llm.LLMAgentPolicy(_FailClient(), max_consecutive_failures=2,
                                 max_request_retries=0, max_parse_retries=0)
        obs = AIObservation()
        obs.status.hp_cur = 12
        obs.status.hp_max = 12
        obs.status.moves_left = 1000
        obs.player_pos = (10, 10)
        obs._tile_cache = {}
        with self.assertRaises(llm.LLMConnectionError) as cm:
            pol.decide(obs, [])
        self.assertTrue(pol.last_error)
        self.assertIn("LLM接続失敗", str(cm.exception))

    def test_opt_in_fallback(self):
        # --ai-llm-fallback時のみscripted継続
        pol = llm.LLMAgentPolicy(_FailClient(), max_consecutive_failures=2,
                                 fallback_enabled=True,
                                 max_request_retries=0, max_parse_retries=0)
        obs = AIObservation()
        obs.status.hp_cur = 12
        obs.status.hp_max = 12
        obs.status.moves_left = 1000
        obs.player_pos = (10, 10)
        obs._tile_cache = {}
        act, reason = pol.decide(obs, [])
        self.assertTrue(pol.last_fallback)
        self.assertIn("LLM接続失敗", reason)
        # 2回連続失敗で固定化
        pol.decide(obs, [])
        self.assertTrue(pol.pinned_scripted)

    def test_parse_retry_recovers(self):
        # 1回崩れ→2回目正常で回復する
        class Flaky(llm.ChatClient):
            def __init__(self):
                self.n = 0
            def complete(self, system, user, temperature=0.2, max_tokens=512):
                self.n += 1
                if self.n == 1:
                    return '{"type": "move"\n"direction": "h"}', 1, ""
                return '{"type":"move","direction":"h","reason":"ok"}', 2, ""
        pol = llm.LLMAgentPolicy(Flaky(), max_parse_retries=2)
        obs = AIObservation()
        obs.status.hp_cur = 12
        obs.status.hp_max = 12
        obs.status.moves_left = 1000
        obs.player_pos = (10, 10)
        obs._tile_cache = {}
        act, _ = pol.decide(obs, [])
        self.assertEqual(act.direction, "h")
        self.assertFalse(pol.last_fallback)

    def test_parse_retry_exhausted(self):
        # 常に崩れ→原因付きで終了
        class Bad(llm.ChatClient):
            def complete(self, system, user, temperature=0.2, max_tokens=512):
                return '{"type": "move"\n"direction": "h"}', 1, ""
        pol = llm.LLMAgentPolicy(Bad(), max_parse_retries=1, max_request_retries=0)
        obs = AIObservation()
        obs.status.hp_cur = 12
        obs.status.hp_max = 12
        obs.status.moves_left = 1000
        obs.player_pos = (10, 10)
        obs._tile_cache = {}
        with self.assertRaises(llm.LLMConnectionError):
            pol.decide(obs, [])

    def test_request_retry_recovers(self):
        # 2回回線失敗→3回目成功で継続する
        import urllib.error

        class FlakyNet(llm.ChatClient):
            def __init__(self):
                self.n = 0

            def complete(self, system, user, temperature=0.2, max_tokens=512):
                self.n += 1
                if self.n <= 2:
                    raise urllib.error.URLError("Connection reset by peer")
                return '{"type":"rest","reason":"ok"}', 1, ""

        pol = llm.LLMAgentPolicy(FlakyNet(), max_request_retries=3,
                                 max_parse_retries=0, retry_backoff=0)
        obs = AIObservation()
        obs.status.hp_cur = 12
        obs.status.hp_max = 12
        obs.status.moves_left = 1000
        obs.player_pos = (10, 10)
        obs._tile_cache = {}
        act, _ = pol.decide(obs, [])
        self.assertEqual(act.type, "rest")
        self.assertEqual(pol.client.n, 3)

    def test_request_retry_exhausted(self):
        import urllib.error

        class DeadNet(llm.ChatClient):
            def complete(self, system, user, temperature=0.2, max_tokens=512):
                raise urllib.error.URLError("Connection reset by peer")

        pol = llm.LLMAgentPolicy(DeadNet(), max_request_retries=1,
                                 max_parse_retries=0, retry_backoff=0)
        obs = AIObservation()
        obs.status.hp_cur = 12
        obs.status.hp_max = 12
        obs.status.moves_left = 1000
        obs.player_pos = (10, 10)
        obs._tile_cache = {}
        with self.assertRaises(llm.LLMConnectionError):
            pol.decide(obs, [])

    def test_classify_error(self):
        import socket
        import urllib.error
        # タイムアウト
        self.assertIn("タイムアウト", llm.classify_error(TimeoutError("timed out")))
        self.assertIn("タイムアウト", llm.classify_error(socket.timeout("timed out")))
        # HTTP系（code保持のRuntimeError）
        for code, expect in ((401, "401"), (404, "404"), (429, "429"), (500, "サーバエラー")):
            e = RuntimeError("HTTP %d: x" % code)
            e.code = code
            self.assertIn(expect, llm.classify_error(e))
        # DNS・接続拒否
        self.assertIn("DNS", llm.classify_error(OSError("Name or service not known")))
        self.assertIn("接続拒否", llm.classify_error(OSError("Connection refused")))
        # JSON・形式異常
        self.assertIn("JSON", llm.classify_error(ValueError("Expecting value: line 1")))
        self.assertIn("行動形式不正", llm.classify_error(ValueError("action failed validation: x")))

    def test_llm_success_path(self):
        pol = llm.LLMAgentPolicy(_ScriptedClient())
        obs = AIObservation()
        obs.status.hp_cur = 12
        obs.status.hp_max = 12
        obs.status.moves_left = 1000
        obs.player_pos = (10, 10)
        obs._tile_cache = {}
        act, _ = pol.decide(obs, [])
        self.assertEqual(act.type, "rest")
        self.assertFalse(pol.last_fallback)
        self.assertEqual(pol.last_reasoning, "thinking about resting")

    def test_parse_llm_response(self):
        payload = {"choices": [{"message": {"role": "assistant",
                                            "content": [{"type": "text", "text": "x"}],
                                            "reasoning": "why"},
                                "finish_reason": "stop"}]}
        content, reasoning, finish = llm.parse_llm_response(payload)
        self.assertEqual(content, "x")
        self.assertEqual(reasoning, "why")
        self.assertEqual(finish, "stop")

    def test_prompt_has_hint_and_doors(self):
        import const as _const
        from ai.schemas import AIObservation
        from ai import strategy as _st
        obs = AIObservation()
        obs.status.hp_cur = 12
        obs.status.hp_max = 12
        obs.status.moves_left = 1000
        obs.player_pos = (10, 10)
        cache = {}
        for r in range(_const.MIN_ROW, _const.ROGUE_LINES - 1):
            for c in range(_const.ROGUE_COLUMNS):
                cache[(r, c)] = _const.FLOOR
        obs._tile_cache = cache
        obs.stairs_pos = (10, 13)
        obs.visible_doors = [(12, 10)]
        risk = _st.assess(obs)
        from ai.schemas import IdentifyMemo
        text = llm.format_observation(obs, risk, IdentifyMemo(), "")
        self.assertIn("Legal moves", text)
        self.assertIn("Shortest-path hint", text)
        self.assertIn("Doors", text)
        self.assertNotIn("Full screen dump", text)

    def test_prompt_screen_block(self):
        import const as _const
        from ai.schemas import AIObservation, IdentifyMemo
        from ai import strategy as _st
        obs = AIObservation()
        obs.status.hp_cur = 12
        obs.status.hp_max = 12
        obs.status.moves_left = 1000
        obs.player_pos = (10, 10)
        obs._tile_cache = {}
        obs.raw_screen = ["@....", "-----"]
        risk = _st.assess(obs)
        text = llm.format_observation(obs, risk, IdentifyMemo(), "")
        self.assertIn("Full screen dump", text)
        self.assertIn("@....", text)

    def test_prompt_heading(self):
        import const as _const
        from ai.schemas import AIObservation, IdentifyMemo
        from ai import strategy as _st
        obs = AIObservation()
        obs.status.hp_cur = 12
        obs.status.hp_max = 12
        obs.status.moves_left = 1000
        obs.player_pos = (10, 10)
        obs._tile_cache = {}
        risk = _st.assess(obs)
        text = llm.format_observation(obs, risk, IdentifyMemo(), "", heading="l")
        self.assertIn("Previous move", text)
        self.assertIn("east", text)

    def test_legend_passable_blocked(self):
        self.assertIn("PASSABLE", llm.SYSTEM_PROMPT)
        self.assertIn("BLOCKED", llm.SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()

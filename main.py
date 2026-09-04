"""
main.py - Rogue2.Official C to Python 移植
メインエントリーポイント

元ファイル: src/main.c, src/init.c
"""

import sys
import argparse
from typing import Optional

try:
    from . import config
    from .game import Game
    from . import debug
except ImportError:
    import config
    from game import Game
    import debug


def parse_args(argv=None) -> argparse.Namespace:
    """コマンドライン引数を解析（argv指定時はその引数を解析）"""
    parser = argparse.ArgumentParser(
        prog="rogue",
        description="Rogue2.Official - ローグライクゲーム"
    )
    parser.add_argument(
        "-s", "--score",
        action="store_true",
        help="スコアのみ表示"
    )
    parser.add_argument(
        "-r", "--restore",
        metavar="SAVE_FILE",
        help="セーブファイルからゲームを再開"
    )
    parser.add_argument(
        "message_file",
        nargs="?",
        help="メッセージファイルのパス"
    )
    parser.add_argument(
        "save_file",
        nargs="?",
        help="セーブファイルのパス"
    )
    # --- AI自律プレイ機能（設計書 §10） ---
    parser.add_argument(
        "--ai",
        action="store_true",
        help="AI自律プレイを有効化（実画面モニター付き）"
    )
    parser.add_argument(
        "--ai-provider",
        default=None,
        help="AIプロバイダー: openrouter | openai_compat | scripted"
    )
    parser.add_argument(
        "--ai-model",
        default=None,
        help="モデル名（既定: inception/mercury-2.5-preview）"
    )
    parser.add_argument(
        "--ai-endpoint",
        default=None,
        help="Chat Completions endpoint URL"
    )
    parser.add_argument(
        "--ai-max-turns",
        type=int,
        default=None,
        help="AI運転の最大ターン数"
    )
    parser.add_argument(
        "--ai-delay-ms",
        type=int,
        default=None,
        help="1手の表示待ちミリ秒（人間が目で追える速さ）"
    )
    parser.add_argument(
        "--ai-timeout",
        type=float,
        default=None,
        help="LLM呼び出しタイムアウト秒"
    )
    parser.add_argument(
        "--ai-log",
        default=None,
        help="AIセッションログ(JSONL)のパス"
    )
    parser.add_argument(
        "--ai-headless",
        action="store_true",
        help="cursesなし高速スモーク（移動・探索のみ）"
    )
    parser.add_argument(
        "--ai-replay",
        metavar="AI_LOG",
        default=None,
        help="記録済みAIログのキーを再生しながら実画面で観察"
    )
    parser.add_argument(
        "--ai-llm-fallback",
        action="store_true",
        help="LLM接続失敗時にscriptedで継続（既定は原因表示して終了）"
    )
    parser.add_argument(
        "--ai-max-tokens",
        type=int,
        default=None,
        help="LLM応答のmax_tokens（推論系は多めに。既定4096）"
    )
    parser.add_argument(
        "--ai-trace",
        default=None,
        help="LLM全文記録(JSONL)のパス（既定ai_trace.jsonl）"
    )
    parser.add_argument(
        "--ai-no-trace",
        action="store_true",
        help="LLM全文記録を無効化"
    )
    parser.add_argument(
        "--ai-no-screen",
        action="store_true",
        help="画面ダンプ全文のLLM添付を無効化（トークン節約）"
    )
    return parser.parse_args(argv)


def _build_ai_options(args: argparse.Namespace) -> Optional[dict]:
    """CLI引数・環境変数からAI設定を組み立てる（CLI＞環境変数＞既定値）"""
    import os
    if not args.ai and not args.ai_headless and not args.ai_replay:
        return None
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        try:
            from .ai.schemas import AIOptions
        except ImportError:
            from ai.schemas import AIOptions
        defaults = AIOptions()
    except Exception:
        defaults = None
    env = os.getenv
    if args.ai_replay:
        return {
            "enabled": True, "provider": "scripted",
            "model": defaults.model if defaults else "",
            "endpoint": defaults.endpoint if defaults else "",
            "api_key": "",
            "max_turns": args.ai_max_turns or 100000,
            "delay_ms": args.ai_delay_ms if args.ai_delay_ms is not None else (defaults.delay_ms if defaults else 120),
            "timeout": args.ai_timeout or (defaults.timeout if defaults else 20.0),
            "log_file": args.ai_log or "",
            "headless": False,
            "replay_file": args.ai_replay,
        }
    return {
        "enabled": True,
        "provider": args.ai_provider or env("ROGUE_AI_PROVIDER") or (defaults.provider if defaults else "openrouter"),
        "model": args.ai_model or env("ROGUE_AI_MODEL") or (defaults.model if defaults else "inception/mercury-2.5-preview"),
        "endpoint": args.ai_endpoint or env("ROGUE_AI_ENDPOINT") or env("OPENAI_BASE_URL") or (defaults.endpoint if defaults else "https://openrouter.ai/api/v1/chat/completions"),
        "api_key": env("OPENROUTER_API_KEY") or env("OPENAI_API_KEY") or "",
        "max_turns": args.ai_max_turns or int(env("ROGUE_AI_MAX_TURNS") or (defaults.max_turns if defaults else 500)),
        "delay_ms": args.ai_delay_ms if args.ai_delay_ms is not None else int(env("ROGUE_AI_DELAY_MS") or (defaults.delay_ms if defaults else 120)),
        "timeout": args.ai_timeout or float(env("ROGUE_AI_TIMEOUT") or (defaults.timeout if defaults else 20.0)),
        "log_file": args.ai_log or env("ROGUE_AI_LOG") or (defaults.log_file if defaults else "ai_session.jsonl"),
        "trace_file": "" if args.ai_no_trace else (
            args.ai_trace or env("ROGUE_AI_TRACE") or (defaults.trace_file if defaults else "ai_trace.jsonl")),
        "show_screen": not args.ai_no_screen and env("ROGUE_AI_SCREEN") != "0",
        "headless": False,
        "replay_file": "",
        "llm_fallback": args.ai_llm_fallback or env("ROGUE_AI_LLM_FALLBACK") == "1",
        "max_tokens": args.ai_max_tokens or int(env("ROGUE_AI_MAX_TOKENS") or (defaults.max_tokens if defaults else 4096)),
    }


def main() -> int:
    """メイン関数"""
    # 最初にログを設定
    debug.setup_logging(log_file='rogue_debug.log')
    
    try:
        args = parse_args()
        debug.get_logger().debug("main: args parsed, loading config")

        # 設定をロード
        config.load_config()
        debug.get_logger().debug("main: config loaded, creating game")

        # ヘッドレスAIスモーク（cursesなし。設計書 §7.4）
        if args.ai_headless:
            import os as _os
            _os.environ.setdefault("ROGUE_AI_MAX_TURNS", str(args.ai_max_turns or 300))
            try:
                from .ai.driver import run_headless_smoke
            except ImportError:
                from ai.driver import run_headless_smoke
            result = run_headless_smoke(
                turns=args.ai_max_turns or int(_os.getenv("ROGUE_AI_MAX_TURNS", "300")),
                log_file=args.ai_log or _os.getenv("ROGUE_AI_LOG", ""),
            )
            print("headless smoke: %s" % (result,))
            return 0

        # ゲームインスタンスを作成
        game = Game(
            score_only=args.score,
            restore_file=args.restore,
            message_file=args.message_file,
            ai_options=_build_ai_options(args),
        )
        debug.get_logger().debug("main: game created, starting run")

        # ゲームを開始
        return game.run()

    except KeyboardInterrupt:
        # Ctrl+C で終了
        print("\nゲームを中断しました。")
        return 0
    except Exception as e:
        print(f"エラーが発生しました: {e}", file=sys.stderr)
        if config.DEBUG:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

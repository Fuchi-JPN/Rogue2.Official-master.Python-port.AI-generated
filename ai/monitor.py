"""
monitor.py - 人間モニター用オーバーレイ・介入キー定義（設計書 §7）

curses画面構成は変えない。最終行（ステータス行）への一時的な
1行上書きに留め、ゲーム表示の永続破壊はしない。
"""
try:
    from .. import const
except ImportError:
    import const

import unicodedata


def disp_width(s: str) -> int:
    """端末上の表示幅（全角2・半角1）。折り返し防止用"""
    w = 0
    for ch in s:
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def truncate_width(s: str, maxw: int) -> str:
    """表示幅で切り詰める。1行に収めて折り返しを防ぐ"""
    w = 0
    out = []
    for ch in s:
        cw = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if w + cw > maxw:
            break
        out.append(ch)
        w += cw
    return "".join(out)


# 介入キー（設計書 §7.3）。AI運転中に人間が押すキー
KEY_PAUSE = " "
KEY_STEP = "s"
KEY_FASTER = "+"
KEY_SLOWER = "-"
KEY_MANUAL = "m"
KEY_AI_QUIT = "q"
KEY_FORCE_QUIT = "X"  # 強制終了（即時プロセス終了。AIは送出禁止）
KEY_PASSTHROUGH = {"Q"}  # ゲーム終了等、人間のみ・そのまま通す


def format_overlay(policy_name: str, model_short: str, turn: int,
                   delay_ms: int, thought: str, hp_cur, hp_max,
                   level, gold, state: str = "") -> str:
    thought = truncate_width(thought or "", 40)
    base = ("[AI:%s/%s T%d spd%dms] %s | HP%s/%s L%s G%s%s | "
            "[space]pause [s]step [+-]speed [m]manual [q]quit [X]kill"
            % (policy_name, model_short, turn, delay_ms, thought,
               hp_cur, hp_max, level, gold,
               (" " + state) if state else ""))
    return truncate_width(base, const.ROGUE_COLUMNS - 1)


def render_overlay(game, text: str) -> None:
    """最終行にオーバーレイ表示する。失敗は無視（ゲーム継続優先）"""
    try:
        display = getattr(game, "display", None)
        if display is None:
            return
        display.mvaddstr(const.ROGUE_LINES - 1, 0, text)
        try:
            display.clrtoeol()
        except Exception:
            pass
        display.refresh()
    except Exception:
        pass


# -- 推論文ティッカー ------------------------------------------------------
# ステータス行の下（25行目以降）に端末余白があれば専用行を使い、
# なければオーバーレイ行内に埋め込む。

TICKER_ROW = const.ROGUE_LINES  # 0-indexedで25行目


def ticker_row(game):
    """専用行が使えれば行番号、なければNone"""
    try:
        stdscr = getattr(getattr(game, "display", None), "stdscr", None)
        if stdscr is None:
            stdscr = getattr(game, "stdscr", None)
        if stdscr is None:
            return None
        maxy, _ = stdscr.getmaxyx()
        return TICKER_ROW if maxy > TICKER_ROW else None
    except Exception:
        return None


def ticker_frame(text: str, width: int, offset: int) -> str:
    """ティッカーの1フレーム分を切り出す（純粋関数・表示幅基準）"""
    flat = " ".join((text or "").split())
    if not flat:
        return ""
    pad = " " * width
    loop = flat + pad
    n = len(loop)
    off = offset % n
    frame = (loop + loop)[off:off + width + 8]
    return truncate_width(frame, width)


def render_ticker(game, segment: str) -> None:
    """専用行にティッカー断片を描く。失敗は無視"""
    try:
        display = getattr(game, "display", None)
        if display is None:
            return
        display.mvaddstr(TICKER_ROW, 0,
                         truncate_width(segment, const.ROGUE_COLUMNS - 1))
        try:
            display.clrtoeol()
        except Exception:
            pass
        display.refresh()
    except Exception:
        pass


def clear_ticker(game) -> None:
    """専用行を消去する"""
    try:
        render_ticker(game, "")
    except Exception:
        pass

"""
input_hook.py - AIキーキューの一元管理

本体側の全raw入力点（Game._get_input / Display.getch /
InventoryManager._getchar / special_actions内のcurses.getch）が、
cursesを読む前にこのキューを参照する。ゲームロジックへの変更は含まない。

 NOTE: 本モジュールは本体・AIのいずれからもimportされるため、
       他のaiモジュール・本体モジュールへの依存を持たせないこと。
"""
from collections import deque

_queue: deque = deque()


def push_keys(s) -> None:
    """AIの後続キーをキューに積む（例: 'q'に対するスロット文字）"""
    if not s:
        return
    for ch in s:
        _queue.append(ch)


def pop_key():
    """キューの先頭1文字を取り出す。空ならNone"""
    if _queue:
        return _queue.popleft()
    return None


def peek_key():
    """キューの先頭を消費せずに覗く。空ならNone"""
    if _queue:
        return _queue[0]
    return None


def has_keys() -> bool:
    return bool(_queue)


def clear() -> None:
    _queue.clear()


def hook_getch_int():
    """Display.getch / curses.getch系用のフック。int(ord)またはNone"""
    k = pop_key()
    if k is None:
        return None
    return ord(k) if isinstance(k, str) else k


def hook_getchar_str():
    """InventoryManager._getchar系用のフック。strまたはNone"""
    k = pop_key()
    if k is None:
        return None
    return k if isinstance(k, str) else chr(k)


# -- 強制終了フラグ ------------------------------------------------------
# ブロッキング待ち（Display._wait_for_ack等）からでも要求できるよう、
# キューとは別のプロセス内フラグで伝達する。消費はGame._get_input
# またはAIDriver.next_keyが行い、ForceQuitとして上位へ伝播させる。

_force_quit = False


def request_force_quit() -> None:
    global _force_quit
    _force_quit = True


def consume_force_quit() -> bool:
    """要求があれば取り除いてTrue。なければFalse"""
    global _force_quit
    if _force_quit:
        _force_quit = False
        return True
    return False


# -- 全自動モード ----------------------------------------------------------
# AI運転中は確認待ち（_wait_for_ack）を人間なしで自動承認する。
_auto_ack = False


def set_auto_ack(on: bool) -> None:
    global _auto_ack
    _auto_ack = bool(on)


def auto_ack_enabled() -> bool:
    return _auto_ack

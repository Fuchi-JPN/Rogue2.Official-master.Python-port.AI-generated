"""
config.py - Rogue2.Official C to Python 移植
ゲーム設定と環境設定

元ファイル: src/rogue.h, config.h, src/init.c
"""

import os
import sys
from typing import Optional

# ============================================================================
# パッケージ情報
# ============================================================================

PACKAGE_NAME = "rogueclone2s"
PACKAGE_VERSION = "6.0"
PACKAGE_STRING = f"{PACKAGE_NAME} {PACKAGE_VERSION}"

# ============================================================================
# ゲーム設定
# ============================================================================

# 画面サイズ
SCREEN_LINES = 24
SCREEN_COLUMNS = 80

# ゲームディレクトリ設定
GAME_DIR: Optional[str] = None
ORG_DIR: Optional[str] = None

# セーブファイル名
SAVE_FILE = "rogue.save"
SCORE_FILE = "rogue.scores"

# メッセージファイル
MESG_FILE = "mesg"
MESG_J_FILE = "mesg_J"
MESG_E_FILE = "mesg_E"

# 言語設定
LANGUAGE = "ja"  # "ja" or "en"

# デバッグモード
DEBUG = False

# カラー設定
COLOR = True  # カラー表示を使用するかどうか

# ============================================================================
# 環境変数から設定をロード
# ============================================================================

def load_config() -> None:
    """環境変数から設定をロード"""
    global GAME_DIR, ORG_DIR, LANGUAGE, DEBUG

    # ゲームディレクトリ
    GAME_DIR = os.getenv("ROGUE_DIR")
    if not GAME_DIR:
        # デフォルトのゲームディレクトリ
        GAME_DIR = os.path.join(os.path.dirname(__file__), "..")

    # オリジナルディレクトリ
    ORG_DIR = os.getenv("ROGUE_ORG_DIR")
    if not ORG_DIR:
        ORG_DIR = os.path.join(GAME_DIR, "src")

    # 言語設定
    lang = os.getenv("ROGUE_LANG")
    if lang:
        LANGUAGE = lang.lower()
        if LANGUAGE not in ("ja", "en"):
            LANGUAGE = "ja"

    # デバッグモード
    debug = os.getenv("ROGUE_DEBUG")
    if debug:
        DEBUG = debug.lower() in ("1", "true", "yes", "on")

# ============================================================================
# パス取得ヘルパー関数
# ============================================================================

def get_game_dir() -> str:
    """ゲームディレクトリのパスを取得"""
    if GAME_DIR is None:
        load_config()
    return GAME_DIR or ""

def get_org_dir() -> str:
    """オリジナルソースディレクトリのパスを取得"""
    if ORG_DIR is None:
        load_config()
    return ORG_DIR or ""

def get_save_file_path() -> str:
    """セーブファイルのパスを取得"""
    home_dir = os.path.expanduser("~")
    return os.path.join(home_dir, SAVE_FILE)

def get_score_file_path() -> str:
    """スコアファイルのパスを取得"""
    home_dir = os.path.expanduser("~")
    return os.path.join(home_dir, SCORE_FILE)

def get_mesg_file_path() -> str:
    """メッセージファイルのパスを取得"""
    if LANGUAGE == "ja":
        filename = MESG_J_FILE
    else:
        filename = MESG_E_FILE
    return os.path.join(get_org_dir(), filename)

# ============================================================================
# プラットフォーム判定
# ============================================================================

def is_windows() -> bool:
    """Windowsプラットフォームかどうかを判定"""
    return sys.platform == "win32"

def is_unix() -> bool:
    """Unix系プラットフォームかどうかを判定"""
    return sys.platform in ("linux", "darwin", "freebsd", "openbsd")

# ============================================================================
# ncurses/curses ライブラリ設定
# ============================================================================

def get_curses_module():
    """適切なcursesモジュールを取得"""
    try:
        if is_windows():
            import windows_curses as curses
        else:
            import curses
        return curses
    except ImportError:
        if is_windows():
            raise ImportError(
                "windows-curses がインストールされていません。"
                "pip install windows-curses を実行してください。"
            )
        else:
            raise ImportError(
                "curses モジュールが見つかりません。"
                "Unix/Linux/macOS の場合はシステムにcursesライブラリをインストールしてください。"
            )

# 設定をロード
load_config()

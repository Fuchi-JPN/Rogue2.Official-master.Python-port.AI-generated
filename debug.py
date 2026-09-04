"""
デバッグユーティリティモジュール

ログ出力やデバッグ用の関数を提供します。
キー操作ログは keylog.txt に分離して出力します。
"""

import logging
import sys
import os
from datetime import datetime
from functools import wraps
from typing import Callable, Any, Optional

# ロガーの設定
_logger = None
_keylog_file = None
_keylog_enabled = True
_keylog_max_size = 1024 * 1024  # 1MB

def setup_logging(level=logging.DEBUG, log_file='debug.log'):
    """ログ出力を設定 (curses画面を壊さないようファイル出力のみ)"""
    global _logger
    
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # ファイルハンドラ
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # ルートロガーに追加（コンソール出力なし）
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    
    _logger = logging.getLogger(__name__)
    return _logger

def get_logger():
    """ロガーを取得"""
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger

def log_function_call(func: Callable) -> Callable:
    """関数呼び出しをログに記録するデコレータ"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger()
        logger.debug(f"呼び出し: {func.__name__}({args}, {kwargs})")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"戻り値: {result}")
            return result
        except Exception as e:
            logger.error(f"エラー: {e}")
            raise
    return wrapper

def log_variable(name: str, value: Any):
    """変数の値をログに記録"""
    logger = get_logger()
    logger.debug(f"変数 {name} = {value}")

def log_grid(dungeon, max_rows=5, max_cols=10):
    """ダンジョングリッドをログに記録"""
    logger = get_logger()
    logger.debug("ダンジョングリッド:")
    for i in range(min(max_rows, len(dungeon.dungeon))):
        row_str = ""
        for j in range(min(max_cols, len(dungeon.dungeon[0]))):
            tile = dungeon.dungeon[i][j]
            if tile & 0x01:  # FLOOR
                row_str += "."
            elif tile & 0x04:  # WALL
                row_str += "#"
            else:
                row_str += "?"
        logger.debug(f"  {row_str}")

def log_monsters(dungeon):
    """モンスター情報をログに記録"""
    logger = get_logger()
    logger.debug(f"モンスター数: {len(dungeon.monsters)}")
    for i, monster in enumerate(dungeon.monsters):
        logger.debug(f"  モンスター {i+1}: {monster.m_char} at ({monster.row}, {monster.col}), HP={monster.hp_to_kill}")

def log_inventory(player):
    """インベントリ情報をログに記録"""
    logger = get_logger()
    logger.debug(f"インベントリ: {len(player.pack)} 個のアイテム")
    for i, item in enumerate(player.pack):
        logger.debug(f"  {item.ichar}: type={item.item_type}, kind={item.which_kind}")

def log_player_state(player):
    """プレイヤーの状態をログに記録"""
    logger = get_logger()
    logger.debug(f"プレイヤー状態:")
    logger.debug(f"  名前: {player.name}")
    logger.debug(f"  HP: {player.hp_current}/{player.hp_max}")
    logger.debug(f"  STR: {player.str_current}/{player.str_max}")
    logger.debug(f"  EXP: {player.exp}")
    logger.debug(f"  GOLD: {player.gold}")
    logger.debug(f"  位置: ({player.row}, {player.col})")
    logger.debug(f"  レベル: {player.dungeon_level}")

def log_rooms(dungeon):
    """部屋情報をログに記録"""
    logger = get_logger()
    logger.debug(f"部屋数: {len(dungeon.rooms)}")
    for i, room in enumerate(dungeon.rooms):
        logger.debug(f"  部屋 {i+1}: ({room.top_row}, {room.left_col}) - ({room.bottom_row}, {room.right_col})")


# ============================================================================
# キー操作ログ機能
# ============================================================================

def setup_keylog(log_file: str = 'keylog.txt', enabled: bool = True, max_size: int = 1024 * 1024):
    """
    キー操作ログを設定
    
    Args:
        log_file: ログファイル名
        enabled: ログ有効/無効
        max_size: 最大ファイルサイズ（バイト）。超過時はローテーション
    """
    global _keylog_file, _keylog_enabled, _keylog_max_size
    
    _keylog_enabled = enabled
    _keylog_max_size = max_size
    
    if enabled:
        try:
            # ファイルサイズチェック
            if os.path.exists(log_file):
                size = os.path.getsize(log_file)
                if size > max_size:
                    # ローテーション: 古いファイルをバックアップ
                    backup = log_file + '.old'
                    if os.path.exists(backup):
                        os.remove(backup)
                    os.rename(log_file, backup)
            
            _keylog_file = open(log_file, 'a', encoding='utf-8')
            _keylog_file.write(f"\n{'='*60}\n")
            _keylog_file.write(f"新規セッション: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            _keylog_file.write(f"{'='*60}\n")
            _keylog_file.flush()
        except Exception as e:
            print(f"キーログファイルを開けませんでした: {e}")
            _keylog_enabled = False


def log_key(key: str, context: Optional[str] = None, result: Optional[str] = None):
    """
    キー操作をログに記録
    
    Args:
        key: 押されたキー
        context: コンテキスト（例: "移動", "インベントリ", "戦闘"）
        result: 操作の結果（例: "移動成功", "アイテム取得"）
    
    ログ形式:
        [時刻] キー コンテキスト: 結果
        例: [12:34:56] j 移動: (5,3)->(6,3)
    """
    global _keylog_file, _keylog_enabled
    
    if not _keylog_enabled or _keylog_file is None:
        return
    
    try:
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # キーの表現を整形
        key_repr = _format_key(key)
        
        # ログ行を構築
        log_line = f"[{timestamp}] {key_repr}"
        if context:
            log_line += f" {context}"
        if result:
            log_line += f": {result}"
        
        _keylog_file.write(log_line + "\n")
        _keylog_file.flush()
        
    except Exception:
        pass  # ログ出力エラーは無視


def _format_key(key: str) -> str:
    """キーを読みやすい形式に変換"""
    special_keys = {
        '\n': 'Enter',
        '\r': 'Enter',
        '\t': 'Tab',
        '\x1b': 'Esc',
        ' ': 'Space',
        '\x7f': 'Backspace',
        '\x08': 'Backspace',
    }
    
    if key in special_keys:
        return f"[{special_keys[key]}]"
    
    # 矢印キーなどのエスケープシーケンス
    if key.startswith('\x1b['):
        seq_map = {
            '\x1b[A': '[Up]',
            '\x1b[B': '[Down]',
            '\x1b[C': '[Right]',
            '\x1b[D': '[Left]',
            '\x1b[H': '[Home]',
            '\x1b[F': '[End]',
        }
        return seq_map.get(key, f"[Seq:{repr(key)}]")
    
    # 表示可能文字
    if 32 <= ord(key) <= 126:
        return key
    
    # 制御文字
    if ord(key) < 32:
        return f"[Ctrl+{chr(ord(key) + 64)}]"
    
    return f"[0x{ord(key):02x}]"


def log_key_sequence(keys: list, description: str = ""):
    """
    キーシーケンスをログに記録
    
    Args:
        keys: キーのリスト
        description: シーケンスの説明
    
    例:
        log_key_sequence(['j', 'j', 'l', 'k'], "移動シーケンス")
    """
    global _keylog_file, _keylog_enabled
    
    if not _keylog_enabled or _keylog_file is None:
        return
    
    try:
        timestamp = datetime.now().strftime('%H:%M:%S')
        key_str = ''.join(_format_key(k) for k in keys)
        log_line = f"[{timestamp}] SEQUENCE: {key_str}"
        if description:
            log_line += f" ({description})"
        _keylog_file.write(log_line + "\n")
        _keylog_file.flush()
    except Exception:
        pass


def log_game_state(player=None, dungeon=None, turn: int = 0):
    """
    ゲーム状態をキーログに記録（デバッグ用）
    
    Args:
        player: プレイヤーオブジェクト
        dungeon: ダンジョンオブジェクト
        turn: ターン数
    """
    global _keylog_file, _keylog_enabled
    
    if not _keylog_enabled or _keylog_file is None:
        return
    
    try:
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_line = f"[{timestamp}] STATE: turn={turn}"
        
        if player:
            log_line += f" HP={player.hp_current}/{player.hp_max}"
            log_line += f" pos=({player.row},{player.col})"
        
        if dungeon:
            mon_count = len(dungeon.monsters) if hasattr(dungeon, 'monsters') else 0
            log_line += f" monsters={mon_count}"
        
        _keylog_file.write(log_line + "\n")
        _keylog_file.flush()
    except Exception:
        pass


def close_keylog():
    """キーログファイルを閉じる"""
    global _keylog_file
    
    if _keylog_file is not None:
        try:
            _keylog_file.write(f"セッション終了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            _keylog_file.close()
        except Exception:
            pass
        _keylog_file = None


def is_keylog_enabled() -> bool:
    """キーログが有効かどうか"""
    return _keylog_enabled

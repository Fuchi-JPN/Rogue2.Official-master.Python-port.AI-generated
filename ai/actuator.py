"""
actuator.py - AIAction → キーストローク変換＋検証（設計書 §4）

現行 Game._play_level / _get_input 実装準拠。
禁止キーは検証で弾き、noop相当（[]）に変換する。
"""
try:
    from .schemas import AIAction
except ImportError:
    from schemas import AIAction


# 方向が必要な行動
_NEED_DIR = {"move", "run", "fight", "throw", "zap"}
# スロットが必要な行動
_NEED_SLOT = {"quaff", "read", "eat", "wield", "wear", "takeoff",
              "puton", "remove", "drop", "throw", "zap"}

# 送出禁止キー（設計書 §4.2）。Xは人間の強制終了専用のためAIは送出禁止
FORBIDDEN_KEYS = set("QSo!aFHJKLBYUNX\x08\x0a\x0b\x0c\x19\x15\x0e\x02")

# 行動→基本キー
_BASE_KEY = {
    "move": None,  # directionそのもの
    "run": None,  # directionの大文字（何かにぶつかるまで連続移動）
    "rest": ".",
    "search": "s",
    "pickup": ",",
    "descend": ">",
    "ascend": "<",
    "quaff": "q",
    "read": "r",
    "eat": "e",
    "wield": "w",
    "wear": "W",
    "takeoff": "T",
    "puton": "P",
    "remove": "R",
    "drop": "d",
    "throw": "t",
    "zap": "z",
    "fight": "f",
    "inventory": "i",
    "help": "?",
    "noop": None,
    "wait_confirm": None,
}

_VALID_DIRS = set("hjklbyun")


def validate(action: AIAction) -> bool:
    """行動の妥当性を検証する。不正ならFalse"""
    if action.type not in _BASE_KEY:
        return False
    if action.type in ("noop", "wait_confirm"):
        return True
    if action.raw_keys:
        # エスケープハッチ：禁止キーを含むものは拒否
        if any(k in FORBIDDEN_KEYS or k == "F" for k in action.raw_keys):
            return False
        return True
    if action.type in _NEED_DIR:
        if action.direction not in _VALID_DIRS:
            return False
    if action.type in _NEED_SLOT:
        if not action.item_slot or len(action.item_slot) != 1:
            return False
        if not ("a" <= action.item_slot <= "z"):
            return False
    return True


def action_to_keys(action: AIAction) -> list:
    """AIAction → キー列（先頭が主キー、残りは後続プロンプト用）。

    不正な行動は []（noop相当）を返す。
    """
    if not validate(action):
        return []
    if action.type in ("noop", "wait_confirm"):
        return []
    if action.raw_keys:
        return list(action.raw_keys)
    if action.type == "move":
        return [action.direction]
    if action.type == "run":
        # 高速移動（連続移動キー）。raw_keys経由の大文字は禁止のまま
        return [action.direction.upper()]
    if action.type == "fight":
        return ["f", action.direction]
    if action.type in ("throw", "zap"):
        keys = [_BASE_KEY[action.type]]
        if action.item_slot:
            keys.append(action.item_slot)
        if action.direction:
            keys.append(action.direction)
        return keys
    key = _BASE_KEY[action.type]
    if action.type in _NEED_SLOT:
        return [key, action.item_slot]
    return [key]

"""
utils.py - Rogue2.Official C to Python 移植
ユーティリティ関数 - ランダム生成

元ファイル: src/random.c
"""

import random
from typing import Tuple


# ============================================================================
# ランダム生成ユーティリティ
# ============================================================================

def set_random_seed(seed: int) -> None:
    """乱数シードを設定"""
    random.seed(seed)


def get_rand(x: int, y: int) -> int:
    """
    xからyまでの乱数を取得（両端を含む）
    元のC言語のget_rand関数と同じ動作
    """
    if x > y:
        x, y = y, x
    return random.randint(x, y)


def rand_percent(percentage: int) -> bool:
    """
    指定したパーセンテージでTrueを返す
    元のC言語のrand_percent関数と同じ動作
    """
    return get_rand(1, 100) <= percentage


def coin_toss() -> bool:
    """
    コイントス（50%の確率でTrue）
    元のC言語のcoin_toss関数と同じ動作
    """
    return random.choice([True, False])


def rnd(n: int) -> int:
    """
    0からn-1までの乱数を取得
    元のC言語のrnd関数と同じ動作
    """
    if n <= 0:
        return 0
    return random.randint(0, n - 1)


def rand_bool() -> bool:
    """ランダムなブール値を取得"""
    return random.choice([True, False])


def rand_choice(choices: list):
    """リストからランダムに1つを選択"""
    return random.choice(choices)


def rand_choices(choices: list, k: int) -> list:
    """リストから重複なしでk個をランダムに選択"""
    return random.sample(choices, k)


def rand_float(min_val: float = 0.0, max_val: float = 1.0) -> float:
    """min_valからmax_valまでのランダムな浮動小数点数を取得"""
    return random.uniform(min_val, max_val)


def rand_gauss(mu: float = 0.0, sigma: float = 1.0) -> float:
    """ガウス分布に従う乱数を取得"""
    return random.gauss(mu, sigma)


def shuffle_list(lst: list) -> None:
    """リストをシャッフル（インプレース）"""
    random.shuffle(lst)


def shuffled_list(lst: list) -> list:
    """シャッフルされた新しいリストを返す"""
    return random.sample(lst, len(lst))


# ============================================================================
# ダイスロールユーティリティ
# ============================================================================

def roll_dice(num: int, sides: int) -> int:
    """
    ダイスを振る
    num: ダイスの数
    sides: ダイスの面数
    戻り値: 合計値
    """
    total = 0
    for _ in range(num):
        total += get_rand(1, sides)
    return total


def roll_dice_str(dice_str: str) -> int:
    """
    ダイス文字列を解析してダイスを振る
    dice_str: "2d6" や "1d6/2d4" のような形式
    戻り値: 合計値
    """
    try:
        return roll_damage(dice_str, randomize=True)
    except (ValueError, IndexError):
        return 0


def _get_number(s: str, pos: int) -> Tuple[int, int]:
    """
    文字列のpos位置から数値を読み取る (C版 hit.c: get_number)
    戻り値: (読み取った数値, 次の読み取り位置)
    """
    total = 0
    while pos < len(s) and '0' <= s[pos] <= '9':
        total = (10 * total) + (ord(s[pos]) - ord('0'))
        pos += 1
    return total, pos


def parse_damage(damage_str: str) -> Tuple[int, int]:
    """
    ダメージ文字列を解析して（ダイス数、面数）を返す
    damage_str: "2d6" や "1d6/2d4" のような形式（"/"区切りの先頭のみ）
    戻り値: (ダイス数, 面数)
    """
    try:
        num, i = _get_number(damage_str, 0)
        if i >= len(damage_str) or damage_str[i] != 'd':
            return (1, 1)
        sides, _ = _get_number(damage_str, i + 1)
        if num == 0 or sides == 0:
            return (1, 1)
        return (num, sides)
    except (ValueError, IndexError):
        return (1, 1)


def roll_damage(damage_str: str, randomize: bool = True) -> int:
    """
    ダメージ文字列を解析してダメージを計算 (C版 hit.c: get_damage)
    damage_str: "2d6" や "1d6/2d4" のような形式
    randomize: True=ランダムロール、False=最大値
    戻り値: ダメージ値
    """
    total = 0
    i = 0
    while i < len(damage_str):
        n, i = _get_number(damage_str, i)
        while i < len(damage_str) and damage_str[i] != 'd':
            i += 1
        if i < len(damage_str):
            i += 1
        d, i = _get_number(damage_str, i)
        while i < len(damage_str) and damage_str[i] != '/':
            i += 1

        for _ in range(n):
            if randomize:
                total += get_rand(1, d)
            else:
                total += d

        if i < len(damage_str) and damage_str[i] == '/':
            i += 1

    return total


# ============================================================================
# 重み付きランダム選択
# ============================================================================

def weighted_choice(choices: list, weights: list):
    """
    重み付きでランダムに選択
    choices: 選択肢のリスト
    weights: 重みのリスト
    戻り値: 選ばれた要素
    """
    return random.choices(choices, weights=weights, k=1)[0]


def weighted_choice_dict(weighted_dict: dict):
    """
    重み付き辞書からランダムに選択
    weighted_dict: {要素: 重み} の辞書
    戻り値: 選ばれた要素
    """
    choices = list(weighted_dict.keys())
    weights = list(weighted_dict.values())
    return weighted_choice(choices, weights)


# ============================================================================
# 範囲ユーティリティ
# ============================================================================

def clamp(value: int, min_val: int, max_val: int) -> int:
    """値を範囲内にクランプ"""
    return max(min_val, min(value, max_val))


def lerp(a: float, b: float, t: float) -> float:
    """線形補間"""
    return a + (b - a) * t


def lerp_int(a: int, b: int, t: float) -> int:
    """線形補間（整数）"""
    return int(lerp(a, b, t))


# ============================================================================
# その他のユーティリティ
# ============================================================================

def sign(value: int) -> int:
    """符号を取得"""
    if value > 0:
        return 1
    elif value < 0:
        return -1
    return 0


def abs_clamp(value: int, max_abs: int) -> int:
    """絶対値をmax_abs以下にクランプ"""
    return clamp(value, -max_abs, max_abs)


def min_max(values: list) -> Tuple[int, int]:
    """リストの最小値と最大値を取得"""
    return (min(values), max(values))


def safe_div(a: int, b: int, default: int = 0) -> int:
    """安全な除算（ゼロ除算対策）"""
    if b == 0:
        return default
    return a // b

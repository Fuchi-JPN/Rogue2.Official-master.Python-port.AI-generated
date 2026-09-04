# ユーティリティ関数の確認テスト
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("ユーティリティ関数の確認テスト")
print("=" * 60)

from utils import get_rand, rand_percent, coin_toss, roll_damage

# 乱数関数の確認
print("\n乱数関数の確認:")
print(f"  get_rand(1, 10) = {get_rand(1, 10)}")
print(f"  get_rand(1, 10) = {get_rand(1, 10)}")
print(f"  get_rand(1, 10) = {get_rand(1, 10)}")
print(f"  rand_percent(50) = {rand_percent(50)}")
print(f"  rand_percent(50) = {rand_percent(50)}")
print(f"  rand_percent(50) = {rand_percent(50)}")
print(f"  coin_toss() = {coin_toss()}")
print(f"  coin_toss() = {coin_toss()}")
print(f"  coin_toss() = {coin_toss()}")

# ダメージロールの確認
print("\nダメージロールの確認:")
print(f"  roll_damage('1d6') = {roll_damage('1d6')}")
print(f"  roll_damage('1d6') = {roll_damage('1d6')}")
print(f"  roll_damage('1d6') = {roll_damage('1d6')}")
print(f"  roll_damage('2d4') = {roll_damage('2d4')}")
print(f"  roll_damage('2d4') = {roll_damage('2d4')}")
print(f"  roll_damage('2d4') = {roll_damage('2d4')}")
print(f"  roll_damage('1d6/2d4') = {roll_damage('1d6/2d4')}")
print(f"  roll_damage('1d6/2d4') = {roll_damage('1d6/2d4')}")
print(f"  roll_damage('1d6/2d4') = {roll_damage('1d6/2d4')}")

# 範囲ユーティリティの確認
print("\n範囲ユーティリティの確認:")
# get_rand_range, get_rand_range_int は実装されていません
print("  (範囲ユーティリティは実装されていません)")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

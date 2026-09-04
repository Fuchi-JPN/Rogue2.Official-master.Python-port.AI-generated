# スコアリングの確認テスト
import sys
import os
sys.path.insert(0, '.')

print("=" * 60)
print("スコアリングの確認テスト")
print("=" * 60)

from score_manager import ScoreManager
from entities import Player

# スコアリングの確認
print("\nスコアリングの確認:")

player = Player()
player.name = "テストプレイヤー"
player.hp_current = 20
player.hp_max = 20
player.gold = 1000
player.cur_level = 5

score_manager = ScoreManager()

# スコア記録
print("\nスコア記録:")
score_manager.killed_by("ドラゴン", 0, player)

# ハイスコア表示
print("\nハイスコア:")
scores = score_manager.get_high_scores()
for i, entry in enumerate(scores):
    print(f"  {i+1}. {entry.name}: {entry.score}g - {entry.cause}")

# テストファイルを削除
if os.path.exists(score_manager.score_file):
    os.remove(score_manager.score_file)
    print(f"\nテストファイルを削除: {score_manager.score_file}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

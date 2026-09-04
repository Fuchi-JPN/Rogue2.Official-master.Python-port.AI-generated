# メインエントリーポイントの確認テスト
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("メインエントリーポイントの確認テスト")
print("=" * 60)

from main import parse_args

# コマンドライン引数解析の確認
print("\nコマンドライン引数解析の確認:")

args = parse_args([])
print(f"  デフォルト引数:")
print(f"    score: {args.score}")
print(f"    restore: {args.restore}")

args = parse_args(['--score'])
print(f"\n  --score 引数:")
print(f"    score: {args.score}")
print(f"    restore: {args.restore}")

args = parse_args(['--restore', 'test.sav'])
print(f"\n  --restore 引数:")
print(f"    score: {args.score}")
print(f"    restore: {args.restore}")

args = parse_args(['--score', '--restore', 'test.sav'])
print(f"\n  --score --restore 引数:")
print(f"    score: {args.score}")
print(f"    restore: {args.restore}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

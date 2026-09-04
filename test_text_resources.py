# テキストリソースの確認テスト
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("テキストリソースの確認テスト")
print("=" * 60)

from text_resources import TextResources, get_message, set_language

# 日本語メッセージ
print("\n日本語メッセージ:")
try:
    tr = TextResources("ja")
    print(f"  ようこそ: {tr.get(0)}")
    print(f"  終了します: {tr.get(1)}")
    print(f"  ゲームオーバー: {tr.get(52)}")
    print(f"  勝利: {tr.get(53)}")
except Exception as e:
    print(f"  エラー: {e}")

# 英語メッセージ
print("\n英語メッセージ:")
try:
    tr_en = TextResources("en")
    print(f"  Welcome: {tr_en.get(0)}")
    print(f"  Goodbye: {tr_en.get(1)}")
    print(f"  Game Over: {tr_en.get(52)}")
    print(f"  Victory: {tr_en.get(53)}")
except Exception as e:
    print(f"  エラー: {e}")

# グローバル関数の確認
print("\nグローバル関数:")
try:
    print(f"  get_message(0) (ja): {get_message(0)}")
    set_language("en")
    print(f"  get_message(0) (en): {get_message(0)}")
    set_language("ja")
    print(f"  get_message(0) (ja): {get_message(0)}")
except Exception as e:
    print(f"  エラー: {e}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)

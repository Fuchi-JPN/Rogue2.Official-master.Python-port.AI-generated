# モジュールインポート確認テスト
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("モジュールインポート確認テスト")
print("=" * 60)

modules = [
    ('const', '定数定義'),
    ('config', '設定管理'),
    ('entities', 'エンティティクラス'),
    ('dungeon', 'ダンジョンデータ構造'),
    ('game', 'ゲームクラス'),
    ('display', '画面描画'),
    ('utils', 'ユーティリティ関数'),
    ('level_generator', 'レベル生成'),
    ('actions', '移動処理'),
    ('inventory', 'インベントリ管理'),
    ('use_actions', 'アイテム使用'),
    ('combat', '戦闘システムとモンスターAI'),
    ('special_actions', '特殊アクション'),
    ('save_manager', 'セーブ/ロード管理'),
    ('score_manager', 'スコアリング'),
    ('text_resources', 'テキストリソース管理'),
]

failed = []
for module_name, description in modules:
    try:
        __import__(module_name)
        print(f"✓ {module_name:20s} ({description})")
    except Exception as e:
        print(f"✗ {module_name:20s} ({description})")
        print(f"  エラー: {e}")
        failed.append((module_name, e))

print("=" * 60)
if failed:
    print(f"失敗: {len(failed)} 個のモジュール")
    for module_name, e in failed:
        print(f"  - {module_name}: {e}")
    sys.exit(1)
else:
    print("すべてのモジュールのインポートが成功しました！")
    sys.exit(0)

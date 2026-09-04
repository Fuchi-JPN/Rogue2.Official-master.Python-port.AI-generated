#!/usr/bin/env python3
"""
check_unused_classes.py - Python版Rogue2.Officialの未使用クラスを検出するスクリプト

このスクリプトは以下のことを行います:
1. pythonサブディレクトリ直下の*.pyファイルから全てのクラス定義を抽出
2. 各クラスが他のファイルからインポート/使用されているかを確認
3. C言語版の構造体が実際に使用されているかを確認
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Python版のクラス定義（抽出対象）
PYTHON_CLASSES = [
    # entities.py
    "ItemId", "GameObject", "Item", "Monster", "Player", "Door", "Room", "Trap", "GameTime",
    # dungeon.py
    "DungeonLevel", "DungeonManager",
    # actions.py
    "MoveResult", "Movement", "TrapManager",
    # combat.py
    "Combat", "MonsterAI",
    # display.py
    "Display", "Message", "Stats",
    # game.py
    "Game",
    # inventory.py
    "InventoryManager",
    # level_generator.py
    "LevelGenerator",
    # save_manager.py
    "GameState", "SaveManager",
    # score_manager.py
    "ScoreEntry", "ScoreManager",
    # special_actions.py
    "ThrowAction", "WandAction", "RingAction",
    # text_resources.py
    "TextResources",
    # use_actions.py
    "UseActions",
]

# C言語版の構造体（比較用）
C_STRUCTS = [
    # rogue.h
    "fighter", "object", "monster", "room", "door", "trap", "rogue_time",
    # その他
    "id", "obj", "rm", "dr", "tr",
]

def find_python_classes(python_dir: str) -> Dict[str, List[Tuple[str, int]]]:
    """
    Pythonファイルからクラス定義を抽出
    
    Returns:
        Dict[class_name, List[(file_name, line_number)]]
    """
    classes = {}
    
    for py_file in Path(python_dir).glob("*.py"):
        if py_file.name.startswith("test_") or py_file.name == "check_unused_classes.py":
            continue
            
        with open(py_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                match = re.match(r"^class\s+(\w+)", line)
                if match:
                    class_name = match.group(1)
                    if class_name not in classes:
                        classes[class_name] = []
                    classes[class_name].append((py_file.name, i))
    
    return classes

def find_class_usage(python_dir: str, class_name: str, definition_file: str) -> List[Tuple[str, int]]:
    """
    指定したクラスが他のファイルで使用されているかを確認
    
    Returns:
        List[(file_name, line_number)] - 使用されている場所のリスト
    """
    usages = []
    
    for py_file in Path(python_dir).glob("*.py"):
        if py_file.name == definition_file or py_file.name == "check_unused_classes.py":
            continue
            
        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()
            
            # インポート文での使用を確認
            import_patterns = [
                rf"from\s+[\w.]+\s+import\s+.*\b{class_name}\b",
                rf"import\s+.*\b{class_name}\b",
            ]
            
            for pattern in import_patterns:
                if re.search(pattern, content):
                    usages.append((py_file.name, 0))  # 0 = インポート文
                    break
            
            # クラス名の使用を確認（インスタンス化、型ヒントなど）
            usage_patterns = [
                rf"\b{class_name}\s*\(",  # インスタンス化
                rf":\s*{class_name}\b",   # 型ヒント
                rf"->\s*{class_name}\b",  # 戻り値の型ヒント
                rf"\[\s*{class_name}\b",  # ジェネリクス
                rf"\b{class_name}\s*\.",  # クラスメソッド/変数アクセス
            ]
            
            for i, line in enumerate(content.split("\n"), 1):
                for pattern in usage_patterns:
                    if re.search(pattern, line):
                        usages.append((py_file.name, i))
                        break
    
    return usages

def find_c_struct_usage(src_dir: str, struct_name: str) -> List[Tuple[str, int]]:
    """
    C言語版の構造体が使用されているかを確認
    
    Returns:
        List[(file_name, line_number)]
    """
    usages = []
    
    for c_file in Path(src_dir).glob("*.c"):
        with open(c_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
            # struct名の使用を確認
            patterns = [
                rf"struct\s+{struct_name}\b",
                rf"\b{struct_name}\s*\*",
                rf"\b{struct_name}\s+\w+",
            ]
            
            for i, line in enumerate(content.split("\n"), 1):
                for pattern in patterns:
                    if re.search(pattern, line):
                        usages.append((c_file.name, i))
                        break
    
    # ヘッダファイルも確認
    for h_file in Path(src_dir).glob("*.h"):
        with open(h_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
            for i, line in enumerate(content.split("\n"), 1):
                for pattern in patterns:
                    if re.search(pattern, line):
                        usages.append((h_file.name, i))
                        break
    
    return usages

def main():
    # パスの設定
    script_dir = Path(__file__).parent
    python_dir = script_dir  # pythonサブディレクトリ
    src_dir = script_dir.parent / "src"  # C言語版のソースディレクトリ
    
    print("=" * 70)
    print("Python版 Rogue2.Official 未使用クラス検出スクリプト")
    print("=" * 70)
    print()
    
    # Pythonクラスの抽出
    print("1. Pythonクラス定義の抽出")
    print("-" * 70)
    python_classes = find_python_classes(python_dir)
    
    for class_name in sorted(python_classes.keys()):
        locations = python_classes[class_name]
        for file_name, line_num in locations:
            print(f"  {class_name}: {file_name}:{line_num}")
    print()
    
    # 各クラスの使用状況確認
    print("2. クラス使用状況の確認")
    print("-" * 70)
    
    unused_classes = []
    test_only_classes = []
    used_classes = []
    
    for class_name in sorted(python_classes.keys()):
        locations = python_classes[class_name]
        definition_file = locations[0][0]
        
        usages = find_class_usage(python_dir, class_name, definition_file)
        
        # テストファイルでのみ使用されているかを確認
        non_test_usages = [u for u in usages if not u[0].startswith("test_")]
        test_usages = [u for u in usages if u[0].startswith("test_")]
        
        if not usages:
            unused_classes.append((class_name, definition_file))
            print(f"  [未使用] {class_name} ({definition_file})")
        elif not non_test_usages and test_usages:
            test_only_classes.append((class_name, definition_file, test_usages))
            print(f"  [テストのみ] {class_name} ({definition_file})")
        else:
            used_classes.append((class_name, definition_file, non_test_usages))
            print(f"  [使用済] {class_name} ({definition_file}) - {len(non_test_usages)}箇所")
    
    print()
    
    # サマリー
    print("=" * 70)
    print("3. サマリー")
    print("=" * 70)
    print(f"  総クラス数: {len(python_classes)}")
    print(f"  使用済み: {len(used_classes)}")
    print(f"  テストのみ: {len(test_only_classes)}")
    print(f"  未使用: {len(unused_classes)}")
    print()
    
    if unused_classes:
        print("  [削除候補] 未使用クラス:")
        for class_name, file_name in unused_classes:
            print(f"    - {class_name} ({file_name})")
    
    if test_only_classes:
        print("  [確認推奨] テストのみで使用されるクラス:")
        for class_name, file_name, usages in test_only_classes:
            print(f"    - {class_name} ({file_name})")
            for usage_file, usage_line in usages[:3]:
                print(f"        使用: {usage_file}:{usage_line}")
    
    print()
    
    # C言語版との比較
    print("=" * 70)
    print("4. C言語版との比較")
    print("=" * 70)
    
    # C言語版の構造体使用状況
    if src_dir.exists():
        print("  C言語版の構造体使用状況:")
        for struct_name in C_STRUCTS:
            usages = find_c_struct_usage(src_dir, struct_name)
            if usages:
                print(f"    {struct_name}: {len(usages)}箇所で使用")
            else:
                print(f"    {struct_name}: 未使用の可能性")
    else:
        print("  C言語版ソースディレクトリが見つかりません")
    
    print()
    print("完了")

if __name__ == "__main__":
    main()

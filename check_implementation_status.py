#!/usr/bin/env python3
"""
check_implementation_status.py - DIFFERENCES_LIST.mdの「次のステップ」の実装状況を確認するスクリプト

このスクリプトは以下のことを行います:
1. pythonサブディレクトリ直下の*.pyファイルのみを対象
2. 各機能の実装状況を確認
3. C言語版との比較を行う
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

# pythonサブディレクトリ直下の*.pyファイルのみを対象
PYTHON_DIR = Path(__file__).parent
SRC_DIR = PYTHON_DIR.parent / "src"

def find_in_python_files(pattern: str) -> List[Tuple[str, int]]:
    """pythonサブディレクトリ直下の*.pyファイルのみでパターンを検索"""
    results = []
    for py_file in PYTHON_DIR.glob("*.py"):
        if py_file.name.startswith("test_") or py_file.name.startswith("check_"):
            continue
        with open(py_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if re.search(pattern, line):
                    results.append((py_file.name, i))
    return results

def find_in_c_files(pattern: str) -> List[Tuple[str, int]]:
    """C言語版の*.c, *.hファイルでパターンを検索"""
    results = []
    for c_file in SRC_DIR.glob("*.c"):
        with open(c_file, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if re.search(pattern, line):
                    results.append((c_file.name, i))
    for h_file in SRC_DIR.glob("*.h"):
        with open(h_file, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if re.search(pattern, line):
                    results.append((h_file.name, i))
    return results

def check_function_implementation(func_name: str, py_file: str) -> Dict:
    """関数の実装状況を確認"""
    result = {
        "function": func_name,
        "python_file": py_file,
        "python_defined": False,
        "python_called": False,
        "c_defined": False,
        "c_called": False,
    }
    
    # Pythonでの定義確認
    py_def_pattern = rf"def\s+{func_name}\s*\("
    py_defs = find_in_python_files(py_def_pattern)
    if py_defs:
        result["python_defined"] = True
        result["python_def_location"] = py_defs[0]
    
    # Pythonでの呼び出し確認
    py_call_pattern = rf"\b{func_name}\s*\("
    py_calls = find_in_python_files(py_call_pattern)
    # 定義箇所以外の呼び出し
    if py_defs:
        py_calls_filtered = [c for c in py_calls if c != py_defs[0]]
    else:
        py_calls_filtered = py_calls
    if py_calls_filtered:
        result["python_called"] = True
        result["python_call_locations"] = py_calls_filtered[:3]  # 最初の3箇所
    
    # C言語版での定義確認
    c_def_pattern = rf"(void|int|char|struct)\s+{func_name}\s*\("
    c_defs = find_in_c_files(c_def_pattern)
    if c_defs:
        result["c_defined"] = True
        result["c_def_location"] = c_defs[0]
    
    # C言語版での呼び出し確認
    c_call_pattern = rf"\b{func_name}\s*\("
    c_calls = find_in_c_files(c_call_pattern)
    if c_defs:
        c_calls_filtered = [c for c in c_calls if c != c_defs[0]]
    else:
        c_calls_filtered = c_calls
    if c_calls_filtered:
        result["c_called"] = True
        result["c_call_locations"] = c_calls_filtered[:3]
    
    return result

def main():
    print("=" * 70)
    print("DIFFERENCES_LIST.md「次のステップ」の実装状況確認")
    print("=" * 70)
    print()
    
    # 確認する関数リスト
    functions_to_check = [
        # 1. text_resources.py の拡充
        ("get_message", "text_resources.py"),
        ("load_japanese_messages", "text_resources.py"),
        
        # 4. wanderer() の実装
        ("wanderer", "actions.py"),
        
        # 5. create_monster() の実装
        ("create_monster", "use_actions.py"),
        
        # 6. aggravate() の実装
        ("aggravate", "use_actions.py"),
        
        # 7. 罠効果の完全実装
        ("tele", "actions.py"),
        ("take_a_nap", "actions.py"),
        ("rust", "actions.py"),
        
        # 8. 空腹システムの完全実装
        ("check_hunger", "actions.py"),
        ("fainting", "actions.py"),
        ("starve", "actions.py"),
    ]
    
    print("1. 関数の実装状況")
    print("-" * 70)
    
    for func_name, py_file in functions_to_check:
        result = check_function_implementation(func_name, py_file)
        
        status = "[OK]" if result["python_defined"] else "[NG]"
        c_status = "[OK]" if result["c_defined"] else "[NG]"
        
        print(f"\n  {func_name}:")
        print(f"    Python defined: {status} {result.get('python_def_location', 'none')}")
        print(f"    C defined: {c_status} {result.get('c_def_location', 'none')}")
        
        if result["python_called"]:
            print(f"    Python called: [OK] {result.get('python_call_locations', [])}")
        else:
            print(f"    Python called: [NG] not called")
        
        if result.get("c_called"):
            print(f"    C called: [OK] {result.get('c_call_locations', [])}")
    
    print()
    print("=" * 70)
    print("2. サマリー")
    print("=" * 70)
    
    implemented = 0
    not_implemented = 0
    
    for func_name, py_file in functions_to_check:
        result = check_function_implementation(func_name, py_file)
        if result["python_defined"]:
            implemented += 1
        else:
            not_implemented += 1
    
    print(f"  実装済み: {implemented}")
    print(f"  未実装: {not_implemented}")
    
    print()
    print("完了")

if __name__ == "__main__":
    main()

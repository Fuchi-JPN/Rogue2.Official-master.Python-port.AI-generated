#!/usr/bin/env python3
"""
compare_c_python.py - C言語版とPython版の相違点を洗い出すスクリプト

このスクリプトは以下の比較を行います：
1. 関数定義の比較（C言語版の関数がPython版に存在するか）
2. 定数の比較
3. 構造体とクラスの比較
4. グローバル変数の比較

使用方法:
    python compare_c_python.py
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


# C言語版のファイルとPython版の対応表
FILE_MAPPING = {
    'src/main.c': 'python/main.py',
    'src/init.c': 'python/game.py',
    'src/level.c': 'python/level_generator.py',
    'src/room.c': 'python/level_generator.py',
    'src/display.c': 'python/display.py',
    'src/move.c': 'python/actions.py',
    'src/monster.c': 'python/combat.py',
    'src/object.c': 'python/inventory.py',
    'src/pack.c': 'python/inventory.py',
    'src/hit.c': 'python/combat.py',
    'src/use.c': 'python/use_actions.py',
    'src/zap.c': 'python/special_actions.py',
    'src/throw.c': 'python/special_actions.py',
    'src/ring.c': 'python/special_actions.py',
    'src/save.c': 'python/save_manager.py',
    'src/score.c': 'python/score_manager.py',
    'src/trap.c': 'python/actions.py',
    'src/random.c': 'python/utils.py',
    'src/message.c': 'python/display.py',
    'src/invent.c': 'python/inventory.py',
    'src/spechit.c': 'python/combat.py',
}


def extract_c_functions(c_file: Path) -> Dict[str, List[str]]:
    """C言語ファイルから関数定義を抽出"""
    functions = {}
    
    if not c_file.exists():
        return functions
    
    content = c_file.read_text(encoding='utf-8', errors='ignore')
    
    # C言語の関数定義パターン
    # 戻り値の型 関数名(引数) { または 戻り値の型 関数名(引数) 改行 {
    pattern = r'(?:^|\n)\s*(?:(?:static|extern)\s+)?(\w+(?:\s*\*)?)\s+(\w+)\s*\([^)]*\)\s*(?:\{|$)'
    
    matches = re.findall(pattern, content, re.MULTILINE)
    
    for return_type, func_name in matches:
        # 除外する関数名（C言語の標準関数など）
        if func_name in ('main', 'printf', 'sprintf', 'malloc', 'free', 'exit'):
            continue
        functions[func_name] = {
            'return_type': return_type.strip(),
            'file': str(c_file)
        }
    
    return functions


def extract_python_functions(py_file: Path) -> Dict[str, dict]:
    """Pythonファイルから関数定義を抽出"""
    functions = {}
    
    if not py_file.exists():
        return functions
    
    content = py_file.read_text(encoding='utf-8', errors='ignore')
    
    # Pythonの関数定義パターン
    # def 関数名(引数):
    pattern = r'def\s+(\w+)\s*\([^)]*\)\s*(?:->\s*[^:]+)?:'
    
    matches = re.findall(pattern, content)
    
    for func_name in matches:
        # プライベートメソッドは先頭に_を付けて保存
        functions[func_name] = {
            'file': str(py_file)
        }
    
    return functions


def extract_c_globals(c_file: Path) -> Dict[str, str]:
    """C言語ファイルからグローバル変数を抽出"""
    globals_dict = {}
    
    if not c_file.exists():
        return globals_dict
    
    content = c_file.read_text(encoding='utf-8', errors='ignore')
    
    # グローバル変数のパターン
    # (static|extern)? 型 変数名 = 値; または 型 変数名;
    pattern = r'(?:^|\n)\s*(?:static|extern)?\s*(\w+(?:\s*\*)?)\s+(\w+)\s*(?:=|;)'
    
    matches = re.findall(pattern, content, re.MULTILINE)
    
    for var_type, var_name in matches:
        # 除外する変数名
        if var_name in ('main', 'NULL', 'TRUE', 'FALSE'):
            continue
        globals_dict[var_name] = var_type.strip()
    
    return globals_dict


def extract_python_globals(py_file: Path) -> Set[str]:
    """Pythonファイルからグローバル変数を抽出"""
    globals_set = set()
    
    if not py_file.exists():
        return globals_set
    
    content = py_file.read_text(encoding='utf-8', errors='ignore')
    
    # モジュールレベルの変数のパターン
    # 変数名 = 値 (関数定義の外)
    lines = content.split('\n')
    in_function = False
    
    for line in lines:
        # 関数定義の開始/終了を検出
        if line.strip().startswith('def '):
            in_function = True
        elif in_function and line and not line[0].isspace() and not line.strip().startswith('#'):
            in_function = False
        
        if not in_function:
            match = re.match(r'^(\w+)\s*=', line)
            if match:
                var_name = match.group(1)
                # 除外する変数名
                if not var_name.startswith('_') and var_name not in ('True', 'False', 'None'):
                    globals_set.add(var_name)
    
    return globals_set


def extract_c_defines(c_file: Path) -> Dict[str, str]:
    """C言語ファイルから#define定数を抽出"""
    defines = {}
    
    if not c_file.exists():
        return defines
    
    content = c_file.read_text(encoding='utf-8', errors='ignore')
    
    # #define 定数名 値
    pattern = r'#define\s+(\w+)\s+(.+)'
    
    matches = re.findall(pattern, content)
    
    for name, value in matches:
        # 関数マクロは除外
        if '(' not in name:
            defines[name] = value.strip()
    
    return defines


def compare_functions():
    """関数の比較を行う"""
    print("=" * 80)
    print("関数の比較")
    print("=" * 80)
    
    all_c_functions = {}
    all_py_functions = {}
    
    # C言語版の関数を抽出
    for c_file in Path('src').glob('*.c'):
        funcs = extract_c_functions(c_file)
        all_c_functions.update(funcs)
    
    # Python版の関数を抽出
    for py_file in Path('python').glob('*.py'):
        funcs = extract_python_functions(py_file)
        all_py_functions.update(funcs)
    
    # C言語版にあってPython版にない関数
    missing_in_python = set(all_c_functions.keys()) - set(all_py_functions.keys())
    
    print(f"\nC言語版の関数数: {len(all_c_functions)}")
    print(f"Python版の関数数: {len(all_py_functions)}")
    print(f"\nPython版に存在しないC言語版の関数 ({len(missing_in_python)}個):")
    
    # ファイル別に分類
    by_file = {}
    for func_name in sorted(missing_in_python):
        c_file = all_c_functions[func_name]['file']
        if c_file not in by_file:
            by_file[c_file] = []
        by_file[c_file].append(func_name)
    
    for c_file, funcs in sorted(by_file.items()):
        print(f"\n  {c_file}:")
        for func in funcs:
            print(f"    - {func}")


def compare_globals():
    """グローバル変数の比較を行う"""
    print("\n" + "=" * 80)
    print("グローバル変数の比較")
    print("=" * 80)
    
    all_c_globals = {}
    all_py_globals = set()
    
    # C言語版のグローバル変数を抽出
    for c_file in Path('src').glob('*.c'):
        globals_dict = extract_c_globals(c_file)
        all_c_globals.update(globals_dict)
    
    # Python版のグローバル変数を抽出
    for py_file in Path('python').glob('*.py'):
        globals_set = extract_python_globals(py_file)
        all_py_globals.update(globals_set)
    
    # C言語版にあってPython版にない変数
    missing_in_python = set(all_c_globals.keys()) - all_py_globals
    
    print(f"\nC言語版のグローバル変数数: {len(all_c_globals)}")
    print(f"Python版のグローバル変数数: {len(all_py_globals)}")
    print(f"\nPython版に存在しないC言語版のグローバル変数 ({len(missing_in_python)}個):")
    
    for var_name in sorted(missing_in_python):
        print(f"  - {var_name} ({all_c_globals[var_name]})")


def compare_defines():
    """定数の比較を行う"""
    print("\n" + "=" * 80)
    print("定数の比較 (#define)")
    print("=" * 80)
    
    all_c_defines = {}
    
    # C言語版の定数を抽出
    for c_file in list(Path('src').glob('*.h')) + list(Path('src').glob('*.c')):
        defines = extract_c_defines(c_file)
        all_c_defines.update(defines)
    
    # Python版の定数を読み込み
    py_constants = set()
    const_file = Path('python/const.py')
    if const_file.exists():
        content = const_file.read_text(encoding='utf-8', errors='ignore')
        matches = re.findall(r'^(\w+)\s*=', content, re.MULTILINE)
        py_constants.update(matches)
    
    print(f"\nC言語版の定数数: {len(all_c_defines)}")
    print(f"Python版の定数数: {len(py_constants)}")
    
    # C言語版にあってPython版にない定数
    missing_in_python = set(all_c_defines.keys()) - py_constants
    
    print(f"\nPython版に存在しないC言語版の定数 ({len(missing_in_python)}個):")
    
    for name in sorted(missing_in_python):
        if not name.startswith('_'):  # 内部定数は除外
            print(f"  - {name} = {all_c_defines[name]}")


def check_function_implementation():
    """関数の実装状況を詳細にチェック"""
    print("\n" + "=" * 80)
    print("重要関数の実装状況チェック")
    print("=" * 80)
    
    # 重要な関数リスト（C言語版の主要な関数）
    important_functions = {
        'src/main.c': ['main'],
        'src/init.c': ['init', 'env_get', 'getpwuid'],
        'src/level.c': ['make_level', 'clear_level', 'visit_rooms', 'make_maze', 'hide_box', 'put_player'],
        'src/room.c': ['create_room', 'connect_rooms', 'draw_simple_passage', 'rooms_counter'],
        'src/display.c': ['draw_map', 'mvaddch_rogue', 'get_dungeon_char', 'get_terrain_char'],
        'src/move.c': ['one_move_rogue', 'multiple_move_rogue', 'can_move', 'is_passable', 'next_to_something', 'check_hunger', 'reg_move', 'heal'],
        'src/monster.c': ['put_mons', 'gr_monster', 'mv_mons', 'mv_monster', 'party_monsters', 'gmc_row_col', 'gmc', 'wake_up', 'wake_room', 'mon_name', 'rogue_is_around', 'wanderer', 'show_monsters', 'create_monster', 'put_m_at', 'aim_monster', 'rogue_can_see', 'move_confused', 'flit', 'gr_obj_char', 'no_room_for_monster', 'aggravate', 'mon_sees', 'mv_aquatars'],
        'src/object.c': ['put_objects', 'get_terrain_char', 'gr_object', 'get_letter_object', 'check_duplicate', 'put_stairs', 'add_traps', 'put_trap', 'object_at', 'get_mask_char', 'place_at', 'remove_from', 'is_object', 'get_w_damage', 'alloc_object', 'free_object', 'get_damage', 'get_number', 'get_desc'],
        'src/pack.c': ['add_to_pack', 'take_from_pack', 'pick_up', 'drop', 'pack_letter', 'get_letter_object', 'pack_count', 'has_amulet', 'kick_into_pack'],
        'src/hit.c': ['mon_hit', 'rogue_hit', 'rogue_damage', 'get_damage', 'get_w_damage', 'get_number', 'to_hit', 'damage_for_strength', 'mon_damage', 'fight', 'get_dir_rc', 'get_hit_chance', 'get_weapon_damage', 'get_armor_class', 'mon_name', 'check_imitator', 'special_hit', 'check_gold_seeker', 'wake_up', 'cough_up', 'get_direction', 'monster_at'],
        'src/use.c': ['quaff', 'read_scroll', 'eat', 'vanish', 'potion_heal', 'idntfy', 'hold_monster', 'tele', 'hallucinate', 'unhallucinate', 'unblind', 'relight', 'take_a_nap', 'go_blind', 'get_ench_color', 'confuse', 'unconfuse', 'uncurse_all'],
        'src/zap.c': ['zapp', 'get_zapped_monster', 'get_missiled_monster', 'zap_monster', 'tele_away', 'slow_monster', 'confuse_monster', 'invisibility', 'polymorph', 'haste_monster', 'put_to_sleep', 'magic_missile', 'cancellation', 'do_nothing'],
        'src/throw.c': ['throw', 'throw_at_monster', 'get_thrown_at_monster', 'flop_weapon', 'rand_around', 'potion_monster'],
        'src/ring.c': ['put_on_ring', 'remove_ring', 'do_put_on', 'un_put_on', 'ring_stats', 'gr_ring', 'inv_rings'],
        'src/save.c': ['save_game', 'restore', 'write_pack', 'read_pack', 'write_level', 'read_level', 'rw_level', 'rw_dungeon', 'rw_id', 'rw_objects', 'get_save_file'],
        'src/score.c': ['killed_by', 'win', 'quit', 'put_scores', 'get_value', 'is_saved', 'delete_saved'],
        'src/trap.c': ['trap_player', 'trap_at', 'add_traps', 'show_traps', 'id_trap', 'rust', 'tele', 'take_a_nap', 'wanderer'],
        'src/spechit.c': ['special_hit', 'rust', 'hold', 'freeze', 'steal_gold', 'steal_item', 'sting', 'drain_life', 'drop_level', 'confuse', 'imitate', 'flame', 'stationary', 'nap'],
    }
    
    # Python版の関数を抽出
    all_py_functions = {}
    for py_file in Path('python').glob('*.py'):
        funcs = extract_python_functions(py_file)
        all_py_functions.update(funcs)
    
    # 各C言語ファイルの関数をチェック
    for c_file, functions in important_functions.items():
        print(f"\n{c_file}:")
        
        for func_name in functions:
            # Python版で同等の関数を探す
            # C言語版の関数名をPython版の命名規則に変換
            py_func_names = [
                func_name,  # そのまま
                f"_{func_name}",  # プライベートメソッド
                func_name.lower(),  # 小文字
                f"_{func_name.lower()}",  # 小文字プライベート
            ]
            
            found = False
            for py_name in py_func_names:
                if py_name in all_py_functions:
                    found = True
                    break
            
            if found:
                print(f"  [OK] {func_name}")
            else:
                print(f"  [MISSING] {func_name}")


def main():
    """メイン関数"""
    print("C言語版とPython版の相違点分析")
    print("=" * 80)
    
    # 作業ディレクトリを確認
    if not Path('src').exists():
        print("エラー: src ディレクトリが見つかりません")
        print("このスクリプトはプロジェクトのルートディレクトリで実行してください")
        return
    
    if not Path('python').exists():
        print("エラー: python ディレクトリが見つかりません")
        print("このスクリプトはプロジェクトのルートディレクトリで実行してください")
        return
    
    # 各種比較を実行
    compare_functions()
    compare_globals()
    compare_defines()
    check_function_implementation()
    
    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)


if __name__ == '__main__':
    main()

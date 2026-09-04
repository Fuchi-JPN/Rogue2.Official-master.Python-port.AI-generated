"""
save_manager.py - セーブ/ロード管理
src/save.c から移植

Pythonのpickleモジュールを使用してセーブ/ロードを実装します。
"""

import pickle
import os
from typing import Optional


# ゲーム状態を保存するクラス（モジュールレベルで定義）
class GameState:
    """ゲーム状態を保存するクラス"""
    
    def __init__(self, player, dungeon, cur_level=1, max_level=1, foods=0,
                 party_room=0, party_counter=0, cur_room=0, being_held=False,
                 bear_trap=0, halluc=0, blind=0, confused=0, levitate=0,
                 haste_self=0, see_invisible=False, detect_monster=False,
                 wizard=False, score_only=False, m_moves=0, id_potions=None,
                 id_scrolls=None, id_wands=None, id_rings=None, is_wood=None,
                 hunger_str="", login_name="",
                 # 追加: C版 save.c で保存されるフィールド
                 sustain_strength=False, add_strength=0, ring_exp=0,
                 stealthy=0, r_teleport=False, auto_search=0,
                 regeneration=0, e_rings=0, r_see_invisible=False,
                 maintain_armor=False, confused_player=False,
                 aggravate_monster=False, interrupted=False, extra_hp=0,
                 trap_door=False, new_level_message="",
                 l_rings=0, r_rings=0, traps=None):
        # プレイヤー情報
        self.player = player

        # ダンジョン情報
        self.dungeon = dungeon

        # ゲーム状態
        self.cur_level = cur_level
        self.max_level = max_level
        self.foods = foods
        self.party_room = party_room
        self.party_counter = party_counter
        self.cur_room = cur_room

        # 状態フラグ
        self.being_held = being_held
        self.bear_trap = bear_trap
        self.halluc = halluc
        self.blind = blind
        self.confused = confused
        self.levitate = levitate
        self.haste_self = haste_self
        self.see_invisible = see_invisible
        self.detect_monster = detect_monster
        self.wizard = wizard
        self.score_only = score_only
        self.m_moves = m_moves

        # アイテム識別情報
        self.id_potions = id_potions if id_potions is not None else []
        self.id_scrolls = id_scrolls if id_scrolls is not None else []
        self.id_wands = id_wands if id_wands is not None else []
        self.id_rings = id_rings if id_rings is not None else []
        self.is_wood = is_wood if is_wood is not None else []

        # 指輪効果関連 (ring.c)
        self.sustain_strength = sustain_strength
        self.add_strength = add_strength
        self.ring_exp = ring_exp
        self.stealthy = stealthy
        self.r_teleport = r_teleport
        self.auto_search = auto_search
        self.regeneration = regeneration
        self.e_rings = e_rings
        self.r_see_invisible = r_see_invisible
        self.maintain_armor = maintain_armor
        self.l_rings = l_rings
        self.r_rings = r_rings

        # 戦闘・移動関連
        self.confused_player = confused_player
        self.aggravate_monster = aggravate_monster
        self.interrupted = interrupted
        self.extra_hp = extra_hp
        self.trap_door = trap_door
        self.new_level_message = new_level_message

        # 罠配列
        self.traps = traps if traps is not None else []

        # その他
        self.hunger_str = hunger_str
        self.login_name = login_name


class SaveManager:
    """セーブ/ロード管理クラス"""

    def __init__(self):
        self.save_file = ""
        self.write_failed = False

    def save_game(self, game_state: GameState, filename: Optional[str] = None) -> bool:
        """ゲームをセーブする"""
        if filename is None:
            filename = self.save_file

        if not filename:
            return False

        try:
            # チルダ展開
            if filename.startswith('~'):
                filename = os.path.expanduser(filename)

            # ディレクトリが存在しない場合は作成
            dirname = os.path.dirname(filename)
            if dirname and not os.path.exists(dirname):
                os.makedirs(dirname)

            # セーブ
            with open(filename, 'wb') as f:
                pickle.dump(game_state, f)

            self.write_failed = False
            return True

        except Exception as e:
            print(f"セーブエラー: {e}")
            self.write_failed = True
            return False

    def load_game(self, filename: Optional[str] = None) -> Optional[GameState]:
        """ゲームをロードする"""
        if filename is None:
            filename = self.save_file

        if not filename:
            return None

        try:
            # チルダ展開
            if filename.startswith('~'):
                filename = os.path.expanduser(filename)

            # ファイルの存在チェック
            if not os.path.exists(filename):
                print(f"ファイルが存在しません: {filename}")
                return None

            # リンクチェック
            import stat
            if stat.S_ISLNK(os.lstat(filename).st_mode):
                print("ファイルはリンクされています")
                return None

            # ロード
            with open(filename, 'rb') as f:
                game_state = pickle.load(f)

            # ウィザードモードでない場合はファイルを削除
            if not game_state.wizard:
                try:
                    os.remove(filename)
                except:
                    pass

            return game_state

        except Exception as e:
            import traceback
            print(f"ロードエラー: {e}")
            traceback.print_exc()
            return None

    def get_save_files(self, save_dir: str = ".") -> list:
        """セーブファイルの一覧を取得"""
        save_files = []

        try:
            for filename in os.listdir(save_dir):
                if filename.endswith('.sav'):
                    filepath = os.path.join(save_dir, filename)
                    save_files.append(filepath)
        except Exception as e:
            print(f"セーブファイル一覧の取得エラー: {e}")

        return save_files

    def delete_save_file(self, filename: str) -> bool:
        """セーブファイルを削除"""
        try:
            if os.path.exists(filename):
                os.remove(filename)
                return True
            return False
        except Exception as e:
            print(f"削除エラー: {e}")
            return False


def create_game_state(player, dungeon, **kwargs) -> GameState:
    """ゲーム状態を作成する"""
    return GameState(
        player=player,
        dungeon=dungeon,
        **kwargs
    )


def restore_game_state(game_state: GameState) -> tuple:
    """ゲーム状態からプレイヤーとダンジョンを復元する"""
    return game_state.player, game_state.dungeon

"""
game.py - Rogue2.Official C to Python 移植
ゲームクラス - メインループと初期化

元ファイル: src/init.c, src/main.c
"""

import os
import sys
import signal
import logging
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(filename='rogue_debug.log', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from . import const
    from . import config
    from . import entities
    from . import dungeon
    from . import display
    from . import utils
    from . import level_generator
    from . import actions
    from . import inventory
    from . import use_actions
    from . import special_actions
    from . import combat
    from . import save_manager
    from . import debug as debug_module
    from .game_state import GameState
    from .ai.input_hook import consume_force_quit as _ai_consume_force_quit
    from .ai.driver import ForceQuit as _AIForceQuit
except ImportError:
    import const
    import config
    import entities
    import dungeon
    import display
    import utils
    import level_generator
    import actions
    import inventory
    import use_actions
    import special_actions
    import combat
    import save_manager
    import debug as debug_module
    from game_state import GameState
    try:
        from ai.input_hook import consume_force_quit as _ai_consume_force_quit
        from ai.driver import ForceQuit as _AIForceQuit
    except ImportError:
        _ai_consume_force_quit = None
        _AIForceQuit = None


class Game:
    """ゲームクラス - ゲーム全体を管理"""

    def __init__(
        self,
        score_only: bool = False,
        restore_file: Optional[str] = None,
        message_file: Optional[str] = None,
        ai_options: Optional[dict] = None,
    ):
        """初期化"""
        self.score_only = score_only
        self.restore_file = restore_file
        self.message_file = message_file
        # AI自律プレイ設定（設計書 §8 M2。Noneまたは{'enabled': False}で従来通り）
        self.ai_options = ai_options
        self.ai_driver = None
        # 現在階層のMovement（消費時のreg_move連動用。C版 vanish相当）
        self._movement = None
        # _get_inputの1文字プッシュバック（count終端子の再dispatch用。C版 goto CH相当）
        self._pushback = None

        # プレイヤー
        self.player: entities.Player = entities.Player()

        # ダンジョンマネージャー
        self.dungeon_manager: dungeon.DungeonManager = dungeon.DungeonManager()

        # ゲーム設定
        self.ask_quit = True
        self.jump = False
        self.pass_go = True
        self.show_skull = True
        self.use_color = config.COLOR

        # ログイン名とニックネーム
        self.login_name: str = ""
        self.nick_name: str = ""

        # パーティ設定
        self.party_room: int = 0
        self.party_counter: int = 0

        # cursesウィンドウ
        self.stdscr = None

        # 表示システム
        self.display: Optional[display.Display] = None
        self.message: Optional[display.Message] = None
        self.stats: Optional[display.Stats] = None

        # 初期化済みフラグ
        self.is_initialized = False
        
        # 前回コマンド保存 (C版 play.c: oldcmd)
        self.last_command: Optional[str] = None
        
        # シグナルハンドラを設定（Ctrl+Zのみ、Ctrl+Cはcurses内部処理に任せる）
        signal.signal(signal.SIGINT, signal.default_int_handler)
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, signal.default_int_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._signal_handler)
        if hasattr(signal, 'SIGTSTP'):
            signal.signal(signal.SIGTSTP, self._signal_handler_tstp)
        # C版 machdep.c: md_heed_signals相当の追加
        if hasattr(signal, 'SIGQUIT'):
            signal.signal(signal.SIGQUIT, self._signal_handler)
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, self._signal_handler)

    def run(self) -> int:
        """ゲームを実行"""
        try:
            # ロケール設定
            import locale
            locale.setlocale(locale.LC_ALL, "")

            # 初期化
            if self._init():
                # セーブファイルからの復帰
                return self._play_level()

            # メインループ（C言語版と同じ）
            while True:
                logger.debug("=== MAIN LOOP: level start ===")
                self._clear_level()
                logger.debug("MAIN: after _clear_level")
                self._make_level()
                logger.debug("MAIN: after _make_level")
                self._put_objects()
                logger.debug("MAIN: after _put_objects")
                self._put_stairs()
                logger.debug("MAIN: after _put_stairs")
                self._add_traps()
                logger.debug("MAIN: after _add_traps")
                self._put_mons()
                logger.debug("MAIN: after _put_mons")
                self._put_player(self.party_room)
                logger.debug(f"MAIN: after _put_player, player at ({self.player.row},{self.player.col}), display={self.display is not None}")
            
                # 初期描画
                if self.display:
                    logger.debug("MAIN: calling draw_map")
                    self.display.draw_map(self.dungeon_manager.get_current_level(), self.player)
                    logger.debug("MAIN: after draw_map, calling draw_entities")
                    self.display.draw_entities(self.dungeon_manager.get_current_level(), self.player, 
                                               self._get_room_number(self.dungeon_manager.get_current_level(), self.player.row, self.player.col))
                    logger.debug("MAIN: after draw_entities")
                else:
                    logger.error("MAIN: self.display is None!")
                self._print_stats(const.STAT_ALL)
                logger.debug("MAIN: after print_stats, entering _play_level")

                result = self._play_level()
                if result != 0:
                    return result

        except Exception as e:
            logger.error(f"Critical game error: {e}", exc_info=True)
            self._clean_up("") # Restore terminal before printing error
            print(f"\nゲームエラー: {e}", file=sys.stderr)
            if const.DEBUG:
                import traceback
                traceback.print_exc()
            else:
                print("詳細は rogue_debug.log を確認してください。")
            return 1
        finally:
            self._clean_up("")

    def _init(self) -> bool:
        """初期化処理"""
        logger.debug("_init: started")
        # キーログを初期化
        debug_module.setup_keylog('keylog.txt', enabled=True)

        # メッセージファイルの読込 (C版 main.c: read_mesg相当)
        if self.message_file:
            try:
                import text_resources as _tr
                _tr.get_text_resources().load_from_file(self.message_file)
            except Exception as e:
                logger.warning(f"message file load failed: {e}")

        # ログイン名を取得
        self.login_name = self._get_login_name()
        if not self.login_name or len(self.login_name) >= 30:
            self._clean_up("ログイン名が無効です")

        if not self.nick_name:
            self.nick_name = self.login_name

        # cursesを初期化
        self.stdscr = self._init_curses()
        logger.debug(f"_init: after _init_curses, stdscr={self.stdscr is not None}, display={self.display is not None}")
        if self.stdscr is None:
            logger.error("_init: stdscr is None, returning True")
            return True

        # 画面サイズチェック
        if (self.stdscr.getmaxyx()[0] < const.ROGUE_LINES or
                self.stdscr.getmaxyx()[1] < const.ROGUE_COLUMNS):
            self._clean_up("画面サイズが小さすぎます")

        # スコアのみ表示モード
        if self.score_only:
            self._put_scores()
            return True

        # 乱数シードを設定
        seed = self._get_random_seed()
        utils.set_random_seed(seed)

        # セーブファイルからの復帰
        if self.restore_file:
            if self._restore(self.restore_file):
                return True

        # ゲーム初期化
        self._init_game_data()
        logger.debug("_init: returning False (normal path)")
        return False

    def _init_curses(self):
        """cursesを初期化"""
        logger.debug("_init_curses: starting")
        curses = None
        stdscr = None
        try:
            curses_module = config.get_curses_module()
            stdscr = curses_module.initscr()
            logger.debug(f"_init_curses: initscr OK, screen size={stdscr.getmaxyx()}")

            try:
                curses_module.raw()
                logger.debug("_init_curses: raw() OK")
            except Exception as e:
                logger.debug(f"_init_curses: raw() failed: {e}")
                try:
                    curses_module.cbreak()
                    logger.debug("_init_curses: cbreak() OK")
                except Exception as e2:
                    logger.debug(f"_init_curses: cbreak() failed: {e2}")
            curses_module.noecho()
            try:
                curses_module.nonl()
            except Exception:
                pass

            stdscr.keypad(True)
            stdscr.timeout(100)
            logger.debug("_init_curses: keypad+timeout set")

            if curses_module.has_colors() and self.use_color:
                try:
                    curses_module.start_color()
                    try:
                        curses_module.use_default_colors()
                    except Exception:
                        pass
                except Exception as e_color:
                    logger.debug(f"_init_curses: color init failed: {e_color}")
                    self.use_color = False

            self.display = display.Display(stdscr)
            # Display初期化後にuse_colorを同期
            self.display.use_color = self.use_color
            self.message = display.Message(self.display)
            self.stats = display.Stats(self.display, self.message)
            logger.debug(f"_init_curses: display/message/stats initialized, use_color={self.use_color}")

            self.is_initialized = True
            logger.debug("_init_curses: returning stdscr (SUCCESS)")
            return stdscr

        except Exception as e:
            if stdscr:
                try:
                    stdscr.keypad(False)
                    curses_module.echo()
                    curses_module.nocbreak()
                    curses_module.endwin()
                except Exception:
                    pass
            import traceback
            traceback.print_exc()
            print(f"\ncurses初期化エラー: {e}\n", file=sys.stderr)
            return None

    def _init_game_data(self) -> None:
        """ゲームデータを初期化"""
        # プレイヤーを初期化
        self._player_init()

        # パーティカウンターを設定
        self.party_counter = utils.get_rand(1, const.PARTY_TIME)

        # C版 invent.c: アイテム素材・色・タイトルの初期化
        inventory.get_wand_and_ring_materials()
        inventory.mix_colors()
        inventory.make_scroll_titles()

    def _player_init(self) -> None:
        """プレイヤーを初期化"""
        # インベントリをクリア
        self.player.pack = None

        # 初期食料
        food = entities.Item()
        food.item_type = const.FOOD
        food.which_kind = const.RATION  # C版: which_kindを使用
        food.quantity = 1
        food.identified = 1
        self._add_to_pack(food)

        # 初期防具（リングメイル）
        armor = entities.Item()
        armor.item_type = const.ARMOR
        armor.which_kind = const.RINGMAIL  # C版: which_kindを使用
        armor.class_ = const.RINGMAIL + 2
        armor.is_protected = 0
        armor.d_enchant = 1
        self._add_to_pack(armor)
        self._do_wear(armor)
        self.player.armor = armor

        # 初期武器（メイス）
        mace = entities.Item()
        mace.item_type = const.WEAPON
        mace.which_kind = const.MACE  # C版: which_kindを使用
        mace.damage = "2d3"
        mace.hit_enchant = 1
        mace.d_enchant = 1
        mace.identified = 1
        self._add_to_pack(mace)
        self._do_wield(mace)
        self.player.weapon = mace

        # 弓
        bow = entities.Item()
        bow.item_type = const.WEAPON
        bow.which_kind = const.BOW  # C版: which_kindを使用
        bow.damage = "1d2"
        bow.hit_enchant = 1
        bow.d_enchant = 0
        bow.identified = 1
        self._add_to_pack(bow)

        # 矢 (C版 init.c:248 quantity 25-35、object.c:470 quiver識別子付与)
        arrow = entities.Item()
        arrow.item_type = const.WEAPON
        arrow.which_kind = const.ARROW  # C版: which_kindを使用
        arrow.item_kind = const.ARROW  # 二重化同期 (inventory._check_duplicateはitem_kind参照)
        arrow.quantity = utils.get_rand(25, 35)
        arrow.quiver = utils.get_rand(0, 126)  # C版 object.c:470 矢束識別子
        arrow.damage = "1d2"
        arrow.hit_enchant = 0
        arrow.d_enchant = 0
        arrow.identified = 1
        self._add_to_pack(arrow)

    def _add_to_pack(self, item: entities.Item) -> None:
        """アイテムをインベントリに追加"""
        item.ichar = ord(self.player.next_avail_ichar())
        item.next_object = self.player.pack
        self.player.pack = item

    def _do_wear(self, item: entities.Item) -> None:
        """防具を装備"""
        item.in_use_flags |= const.BEING_WORN

    def _do_wield(self, item: entities.Item) -> None:
        """武器を装備"""
        item.in_use_flags |= const.BEING_WIELDED

    def _clear_level(self) -> None:
        """レベルをクリア"""
        current_dungeon = self.dungeon_manager.get_current_level()
        current_dungeon.clear()

    def _make_level(self) -> None:
        """レベルを生成"""
        # レベル移動メッセージの表示 (C版 level.c: make_level)
        if GameState.new_level_message:
            if self.message:
                self.message.message(GameState.new_level_message, 0)
            GameState.new_level_message = ""
        self.generator = level_generator.LevelGenerator(self.dungeon_manager.get_current_level(), self.dungeon_manager.current_level)
        self.generator.make_level()

    def _make_random_item(self) -> entities.Item:
        """ランダムアイテムを1個生成 (C版 gr_object系の簡易版)"""
        item = entities.Item()
        r = utils.get_rand(0, 100)
        if r < 20:
            item.item_type = const.FOOD
            item.ichar = ord(':')
            item.which_kind = const.RATION if utils.rand_percent(80) else const.FRUIT
        elif r < 40:
            item.item_type = const.POTION
            item.ichar = ord('!')
            item.which_kind = utils.get_rand(0, const.POTIONS - 1)
        elif r < 60:
            item.item_type = const.SCROL
            item.ichar = ord('?')
            item.which_kind = utils.get_rand(0, const.SCROLS - 1)
        elif r < 75:
            item.item_type = const.WAND
            item.ichar = ord('/')
            item.which_kind = utils.get_rand(0, const.WANDS - 1)
        elif r < 85:
            item.item_type = const.WEAPON
            item.ichar = ord(')')
            wkind = utils.get_rand(0, const.WEAPONS - 1)
            item.which_kind = wkind
            if wkind in (const.ARROW, const.DAGGER, const.DART, const.SHURIKEN):
                item.quantity = utils.get_rand(3, 15)
                item.quiver = utils.get_rand(0, 126)
        elif r < 95:
            item.item_type = const.ARMOR
            item.ichar = ord(']')
            item.which_kind = utils.get_rand(0, const.ARMORS - 1)
        else:
            item.item_type = const.RING
            item.ichar = ord('=')
            item.which_kind = utils.get_rand(0, const.RINGS - 1)
        item.item_kind = item.which_kind
        return item

    def _put_party_objects(self, rn: int) -> None:
        """祭り部屋の品配置 (C版 room.c: party_objects相当)"""
        current_dungeon = self.dungeon_manager.get_current_level()
        try:
            room = current_dungeon.get_room(rn)
        except Exception:
            return
        n = utils.get_rand(5, 10)
        for _ in range(n):
            for _ in range(250):
                row = utils.get_rand(room.top_row + 1, room.bottom_row - 1)
                col = utils.get_rand(room.left_col + 1, room.right_col - 1)
                if current_dungeon.get_tile(row, col) == const.FLOOR:
                    item = self._make_random_item()
                    item.row, item.col = row, col
                    item.next_object = current_dungeon.level_objects
                    current_dungeon.level_objects = item
                    current_dungeon.set_tile(row, col, const.FLOOR | const.OBJECT)
                    break

    def _put_objects(self) -> None:
        """オブジェクトを配置"""
        current_dungeon = self.dungeon_manager.get_current_level()

        # 祭り部屋の品配置
        if getattr(self, 'party_room', const.NO_ROOM) not in (const.NO_ROOM, None):
            try:
                if self.party_room >= 0:
                    self._put_party_objects(self.party_room)
            except Exception:
                pass
        
        # 各部屋に確率でアイテムを配置
        for i in range(const.MAXROOMS):
            room = current_dungeon.get_room(i)
            if not (room.is_room & (const.R_ROOM | const.R_MAZE)):
                continue
            
            # ゴールド
            if utils.rand_percent(35):
                for _ in range(10):
                    row = utils.get_rand(room.top_row + 1, room.bottom_row - 1)
                    col = utils.get_rand(room.left_col + 1, room.right_col - 1)
                    if current_dungeon.get_tile(row, col) == const.FLOOR:
                        gold = entities.Item()
                        gold.item_type = const.GOLD
                        gold.ichar = ord('*')
                        gold.quantity = utils.get_rand(2, 50 + 10 * self.dungeon_manager.current_level)
                        gold.row, gold.col = row, col
                        gold.next_object = current_dungeon.level_objects
                        current_dungeon.level_objects = gold
                        current_dungeon.set_tile(row, col, const.FLOOR | const.OBJECT)
                        break

            # 一般アイテム (食料, 武器, 防具, 杖, 巻物, ポーション, 指輪)
            if utils.rand_percent(25):
                for _ in range(10):
                    row = utils.get_rand(room.top_row + 1, room.bottom_row - 1)
                    col = utils.get_rand(room.left_col + 1, room.right_col - 1)
                    if current_dungeon.get_tile(row, col) == const.FLOOR:
                        item = self._make_random_item()

                        item.row, item.col = row, col
                        item.next_object = current_dungeon.level_objects
                        current_dungeon.level_objects = item
                        current_dungeon.set_tile(row, col, const.FLOOR | const.OBJECT)
                        break

        # アミュレット (特定のレベルで配置)
        if self.dungeon_manager.current_level >= const.AMULET_LEVEL:
            # まだ配置されていなければ
            has_amulet = False
            curr = current_dungeon.level_objects
            while curr:
                if curr.item_type == const.AMULET:
                    has_amulet = True
                    break
                curr = curr.next_object
            
            if not has_amulet:
                # ランダムな部屋に配置
                for _ in range(50):
                    rn = utils.get_rand(0, const.MAXROOMS - 1)
                    room = current_dungeon.get_room(rn)
                    if not (room.is_room & const.R_ROOM): continue
                    
                    row = utils.get_rand(room.top_row + 1, room.bottom_row - 1)
                    col = utils.get_rand(room.left_col + 1, room.right_col - 1)
                    if current_dungeon.get_tile(row, col) == const.FLOOR:
                        amulet = entities.Item()
                        amulet.item_type = const.AMULET
                        amulet.ichar = ord(',')
                        amulet.row, amulet.col = row, col
                        amulet.next_object = current_dungeon.level_objects
                        current_dungeon.level_objects = amulet
                        current_dungeon.set_tile(row, col, const.FLOOR | const.OBJECT)
                        break

    def _put_stairs(self) -> None:
        """階段を配置"""
        row, col = self.generator._gr_row_col(const.FLOOR)
        self.dungeon_manager.get_current_level().set_tile(row, col, const.STAIRS)

    def _add_traps(self) -> None:
        """罠を追加"""
        current_dungeon = self.dungeon_manager.get_current_level()
        actions.TrapManager.add_traps(current_dungeon, self.dungeon_manager.current_level, self.party_room)

    def _put_mons(self) -> None:
        """モンスターを配置"""
        logger.debug("_put_mons: start")
        current_dungeon = self.dungeon_manager.get_current_level()
        level = self.dungeon_manager.current_level
        logger.debug(f"_put_mons: level={level}, dungeon_rooms={len(current_dungeon.rooms)}")
        ai = combat.MonsterAI(self.player, current_dungeon)
        ai.display = self.display
        ai.msg = self.message
        ai.game = self
        ai.cur_level = level
        logger.debug(f"_put_mons: MonsterAI created, party_room={self.party_room}, NO_ROOM={const.NO_ROOM}")
        if self.party_room != const.NO_ROOM:
            logger.debug(f"_put_mons: calling party_monsters({self.party_room}, {level})")
            ai.party_monsters(self.party_room, level)
            logger.debug("_put_mons: party_monsters done")
        logger.debug("_put_mons: calling put_mons()")
        ai.put_mons()
        logger.debug("_put_mons: done")

    def _put_player(self, room_number: int) -> None:
        """プレイヤーを配置 (C版 level.c: put_player相当)"""
        logger.debug(f"put_player: room_number={room_number}")
        current_dungeon = self.dungeon_manager.get_current_level()
        generator = level_generator.LevelGenerator(current_dungeon)
        row, col = generator.put_player(room_number)
        self.player.row = row
        self.player.col = col
        logger.debug(f"put_player: placed at {row},{col}, display={self.display is not None}")

        # 現在部屋を設定 (C版 cur_room)
        try:
            GameState.cur_room = self._get_room_number(
                current_dungeon, self.player.row, self.player.col)
        except Exception:
            pass

        # 初期位置を照らす
        if self.display:
            tile = current_dungeon.get_tile(self.player.row, self.player.col)
            logger.debug(f"Initial tile type: {tile}")
            if tile & const.TUNNEL:
                # 通路にいる場合
                logger.debug("Lighting passage")
                self.display.light_passage(current_dungeon, self.player,
                                          self.player.row, self.player.col)
            else:
                # 部屋にいる場合
                room_num = self._get_room_number(current_dungeon,
                                                self.player.row, self.player.col)
                logger.debug(f"Lighting room {room_num}")
                if room_num >= 0:
                    self.display.light_up_room(current_dungeon, self.player, room_num)

        # 部屋の怪物を起こす (C版 wake_room)
        try:
            movement = actions.Movement(self.player, current_dungeon,
                                        self.display, self.message, self)
            movement.wake_room(GameState.cur_room, True,
                               self.player.row, self.player.col)
        except Exception:
            pass

        # 新階層メッセージ (C版 new_level_message)
        try:
            if GameState.new_level_message and self.message:
                self.message.message(GameState.new_level_message, False)
                GameState.new_level_message = ""
        except Exception:
            pass

    def _print_stats(self, stats_mask: int) -> None:
        """ステータスを表示"""
        if self.stats:
            logger.debug(f"_print_stats: mask={stats_mask}, player hp={self.player.hp_current}")
            self.stats.print_stats(self.player, stats_mask)
            logger.debug("_print_stats: done")
        else:
            logger.error("_print_stats: self.stats is None!")

    def _play_level(self) -> int:
        """レベルをプレイ"""
        self._maybe_start_ai()
        current_dungeon = self.dungeon_manager.get_current_level()
        movement = actions.Movement(self.player, current_dungeon, self.display, self.message, self)
        self._movement = movement

        # メインループ（C版のplay_level()と同じ）
        logger.debug("_play_level: starting game loop")
        refresh_logged = False
        while True:
            if self.display:
                self.display.refresh()
                if not refresh_logged:
                    logger.debug("_play_level: first refresh called")
                    refresh_logged = True
            
            # 罠の落とし穴チェック (C版 play.c: trap_door)
            if GameState.trap_door:
                GameState.trap_door = False
                return 0
            
            # キー入力待ち
            ch = self._get_input()
            if ch:
                logger.debug(f"Input received: {ch} (ord={ord(ch) if len(ch)==1 else 'N/A'})")
            
            if ch is None:
                continue
            
            # 前回コマンド繰り返し (C版 play.c: case 'a')
            if ch == 'a':
                if self.last_command:
                    ch = self.last_command
                else:
                    if self.message:
                        self.message.message("前回のコマンドがない")
                    continue
            
            if ch == 'Q':
                # 終了確認 (C版 score.c: quit相当。'y'以外は復帰)
                if self.message:
                    self.message.message("本当に終了しますか？ (y/n)", False)
                confirm = self._get_input()
                if confirm == 'y':
                    self.killed_by(None, const.QUIT)
                    return 1
                continue
            
            # 階段を降りる
            if ch == '>':
                if current_dungeon.get_tile(self.player.row, self.player.col) & const.STAIRS:
                    self.dungeon_manager.current_level += 1
                    self.player.dungeon_level = self.dungeon_manager.current_level
                    return 0

            # 移動処理
            if movement.is_direction(ch):
                if ch in "hjklbyun":
                    # 単一移動
                    movement.one_move_rogue(ch, True)
                elif ch in "HJKLBYUN":
                    # 連続移動（大文字）
                    movement.multiple_move_rogue(ch)
            
            # Ctrl+キーによる連続移動 (C版の CTRL('H') 等に相当)
            elif ch in '\x08\x0a\x0b\x0c\x19\x15\x0e\x02':  # Ctrl+H/J/K/L/Y/U/N/B
                # 制御文字を小文字に変換 (C版: dirch += 96)
                ctrl_to_dir = {
                    '\x08': 'h',  # Ctrl+H -> h
                    '\x0a': 'j',  # Ctrl+J -> j
                    '\x0b': 'k',  # Ctrl+K -> k
                    '\x0c': 'l',  # Ctrl+L -> l
                    '\x19': 'y',  # Ctrl+Y -> y
                    '\x15': 'u',  # Ctrl+U -> u
                    '\x0e': 'n',  # Ctrl+N -> n
                    '\x02': 'b',  # Ctrl+B -> b
                }
                dirch = ctrl_to_dir.get(ch)
                if dirch:
                    movement.multiple_move_rogue(dirch)
            
            # Ctrl+P: 過去メッセージ表示
            elif ch == '\x10':  # Ctrl+P
                self._remessage()

            # Ctrl+W: ウィザードモード
            elif ch == '\x17':  # Ctrl+W
                self._wizardize()

            # ---- wizard系・情報系 (C版 play.c: CTRL(*)相当) ----
            elif ch == '\x09':  # Ctrl+I: 地上品透視
                if GameState.wizard:
                    if self.display:
                        self.display.inventory(current_dungeon.level_objects,
                                               const.ALL_OBJECTS, self.stats, self.player)
                        self.display.draw_map(current_dungeon, self.player)
                elif self.message:
                    self.message.message("そのコマンドは不明です")
            elif ch == '\x13':  # Ctrl+S: 魔法地図
                if GameState.wizard:
                    inv = inventory.InventoryManager(self.player, current_dungeon)
                    use_actions.UseActions(self.player, current_dungeon, inv,
                                           self.display, self.message, self)._draw_magic_map()
                elif self.message:
                    self.message.message("そのコマンドは不明です")
            elif ch == '\x14':  # Ctrl+T: 罠表示
                if GameState.wizard:
                    actions.TrapManager.show_traps(current_dungeon, self.display)
                elif self.message:
                    self.message.message("そのコマンドは不明です")
            elif ch == '\x0f':  # Ctrl+O: 物表示
                if GameState.wizard:
                    inv = inventory.InventoryManager(self.player, current_dungeon)
                    use_actions.UseActions(self.player, current_dungeon, inv,
                                           self.display, self.message, self)._show_objects()
                elif self.message:
                    self.message.message("そのコマンドは不明です")
            elif ch == '\x01':  # Ctrl+A: 平均HP（wizard不要。C版準拠）
                if self.message:
                    self.message.message("HP %d/%d (Lv%d)" % (
                        self.player.hp_current, self.player.hp_max, self.player.exp))
            elif ch == '\x07':  # Ctrl+G: wizard品生成
                if GameState.wizard:
                    if self.message:
                        self.message.message("wizard品生成（未実装）")
                elif self.message:
                    self.message.message("そのコマンドは不明です")
            elif ch == '\r':  # Ctrl+M: 怪物表示
                if GameState.wizard:
                    try:
                        mai = combat.MonsterAI(self.player, current_dungeon)
                        mai.show_monsters()
                    except Exception:
                        pass
                elif self.message:
                    self.message.message("そのコマンドは不明です")
            elif ch == '\x18':  # Ctrl+X: 一括表示
                if GameState.wizard:
                    actions.TrapManager.show_traps(current_dungeon, self.display)
                    inv = inventory.InventoryManager(self.player, current_dungeon)
                    use_actions.UseActions(self.player, current_dungeon, inv,
                                           self.display, self.message, self)._draw_magic_map()
                elif self.message:
                    self.message.message("そのコマンドは不明です")
            
            # インベントリ表示
            elif ch == 'i':
                if self.display:
                    self.display.inventory(self.player.pack, const.ALL_OBJECTS, self.stats, self.player)
                    # インベントリ表示後は再描画が必要
                    self.display.draw_map(current_dungeon, self.player)
                    self.display.draw_entities(current_dungeon, self.player, GameState.cur_room)
            
            # 探索コマンド
            elif ch == 's':
                movement.search(1, False)
            
            # 休憩コマンド
            elif ch == '.':
                movement.rest(1)
            
            # アイテムを拾う
            elif ch == ',':
                movement.pick_up(self.player.row, self.player.col)
            
            # 投げる
            elif ch == 't':
                self._throw()
            
            # 戦闘
            elif ch == 'f':
                self._fight(False)
            
            # 死ぬまで戦う
            elif ch == 'F':
                self._fight(True)
            
            # 飲む（ポーション）
            elif ch == 'q':
                self._quaff()
            
            # 読む（巻物）
            elif ch == 'r':
                self._read_scroll()
            
            # 移動（アイテムを拾わない）
            elif ch == 'm':
                self._move_onto()
            
            # 食べる
            elif ch == 'e':
                self._eat()
            
            # 武器装備
            elif ch == 'w':
                self._wield()
            
            # 鎧装備
            elif ch == 'W':
                self._wear()
            
            # 鎧脱ぐ
            elif ch == 'T':
                self._take_off()
            
            # 指輪装備
            elif ch == 'P':
                self._put_on_ring()
            
            # 指輪外す
            elif ch == 'R':
                self._remove_ring()
            
            # 落とす
            elif ch == 'd':
                self._drop()
            
            # 杖を振る
            elif ch == 'z':
                self._zapp()
            
            # 階段を上る
            elif ch == '<':
                if self._check_up():
                    return 0  # レベルを再生成
            
            # ヘルプ
            elif ch == '?':
                self._help()
            
            # バージョン表示
            elif ch == 'v':
                self._show_version()
            
            # セーブ
            elif ch == 'S':
                self._save_game()
            
            # ステータス表示
            elif ch == '@':
                self._print_stats(const.STAT_ALL)
            
            # 発見済みアイテム一覧
            elif ch == 'D':
                self._discovered()
            
            # 文字の識別
            elif ch == '/':
                self._identify_char()
            
            # 名前をつける
            elif ch == 'c':
                self._call_it()
            
            # 武器情報
            elif ch == ')':
                self._inv_weapon()
            
            # 防具情報
            elif ch == ']':
                self._inv_armor()
            
            # 指輪情報
            elif ch == '=':
                self._inv_rings()
            
            # 罠識別
            elif ch == '^':
                self._id_trap()
            
            # 単一アイテム表示
            elif ch == 'I':
                self._single_inv()
            
            # スペース（何もしない）
            elif ch == ' ':
                pass
            
            # シェル実行
            elif ch == '!':
                self._doshell()

            # オプション (C版 play.c: options相当の最小実装)
            elif ch == 'o':
                self._options()
            
            # カウント入力（0-9。C版 play.c: count処理＋goto CH）
            elif ch in '0123456789':
                count, term = self._get_count(ch)
                if term is None:
                    continue  # ESCキャンセル（C版 break相当）
                if term == 's':
                    movement.search(count, False)
                elif term == '.':
                    movement.rest(count)
                elif term in 'hjklbyun':
                    for _ in range(count):
                        result = movement.one_move_rogue(term, True)
                        if result != const.MOVED:
                            break
                else:
                    # count対象外はcountを無視して通常dispatch（pushback）
                    self._pushback = term
                    if term != 'a':
                        self.last_command = term
                    continue
                # last_command には count なしのコマンドを保存
                if term != 'a':
                    self.last_command = term
                continue
            
            # 不明なコマンド
            else:
                if self.message:
                    self.message.message("そのコマンドは不明です")
            
            # 前回コマンドを保存 (C版 play.c: oldcmd = cmd)
            # ただし、'a' コマンド自体は保存しない
            if ch != 'a':
                self.last_command = ch
            
            # 再描画が必要な場合（本来はイベント駆動が望ましいが、一旦毎ターン呼ぶ）
            if self.display:
                 self.display.draw_entities(current_dungeon, self.player, GameState.cur_room)

        return 0

    def _maybe_start_ai(self) -> None:
        """AIドライバの遅延起動（設計書 §8 M3。初回_play_level時に1度だけ）"""
        if self.ai_driver is not None:
            return
        opts = getattr(self, "ai_options", None)
        if not opts or not opts.get("enabled"):
            return
        try:
            from .ai.schemas import AIOptions
            from .ai.driver import AIDriver
        except ImportError:
            from ai.schemas import AIOptions
            from ai.driver import AIDriver
        self.ai_driver = AIDriver(self, AIOptions.from_dict(opts))
        self.ai_driver.start()

    def _get_input(self) -> Optional[str]:
        """キー入力を取得（AI運転中はドライバに委譲。設計書 §8 M4）"""
        # 強制終了要求（キーX。確認待ち等のブロッキング待機から設定される）
        if _ai_consume_force_quit is not None and _ai_consume_force_quit():
            driver = getattr(self, "ai_driver", None)
            if driver is not None:
                driver.force_quit()
            try:
                self._clean_up("")
            except Exception:
                pass
            if _AIForceQuit is not None:
                raise _AIForceQuit("X")
            raise KeyboardInterrupt
        # プッシュバック（count終端子の再利用。C版 goto CH相当）
        if self._pushback is not None:
            ch, self._pushback = self._pushback, None
            return ch
        driver = getattr(self, "ai_driver", None)
        if driver is not None and getattr(driver, "active", False):
            return driver.next_key(self._get_input_manual)
        return self._get_input_manual()

    def _get_input_manual(self) -> Optional[str]:
        """キー入力を取得（従来のcurses直読み。AIなし時の経路）"""
        if not self.stdscr:
            return None

        curses = config.get_curses_module()
        try:
            ch = self.stdscr.getch()
            
            if ch == -1:
                return None
            
            # 特殊キーの処理
            if ch == curses.KEY_UP:
                result = 'k'
            elif ch == curses.KEY_DOWN:
                result = 'j'
            elif ch == curses.KEY_LEFT:
                result = 'h'
            elif ch == curses.KEY_RIGHT:
                result = 'l'
            elif ch == curses.KEY_RESIZE:
                return None
            elif ch == 3:  # Ctrl+C
                logger.debug("Ctrl+C detected (chr 3)")
                debug_module.log_key('[Ctrl+C]', context="システム", result="終了")
                self._clean_up("")
                return None
            # Ctrl+キーの処理 (C版の CTRL(c) マクロ相当)
            # CTRL(c) = (c) & 037 で制御文字に変換
            # 逆に、制御文字 + 96 で小文字に戻す
            elif ch == 8:    # Ctrl+H (BS) -> 連続左移動
                result = '\x08'  # 制御文字として返す
            elif ch == 10:   # Ctrl+J (LF) -> 連続下移動
                result = '\x0a'
            elif ch == 11:   # Ctrl+K -> 連続上移動
                result = '\x0b'
            elif ch == 12:   # Ctrl+L -> 連続右移動
                result = '\x0c'
            elif ch == 25:   # Ctrl+Y -> 連続左上移動
                result = '\x19'
            elif ch == 21:   # Ctrl+U -> 連続右上移動
                result = '\x15'
            elif ch == 14:   # Ctrl+N -> 連続右下移動
                result = '\x0e'
            elif ch == 2:    # Ctrl+B -> 連続左下移動
                result = '\x02'
            elif ch == 16:   # Ctrl+P -> 過去メッセージ表示
                result = '\x10'
            elif ch == 23:   # Ctrl+W -> ウィザードモード
                result = '\x17'
            elif 0 <= ch <= 255:
                result = chr(ch)
            else:
                return None
            
            # キー操作をログに記録
            if result:
                debug_module.log_key(result, context="入力")
            
            return result
        except KeyboardInterrupt:
            logger.debug("KeyboardInterrupt detected")
            debug_module.log_key('[Ctrl+C]', context="システム", result="終了")
            self._clean_up("")
            return None
        except:
            return None

    def _restore(self, save_file: str) -> bool:
        """セーブファイルから復帰 (C版 save.c: restore)"""
        try:
            save_mgr = save_manager.SaveManager()
            loaded = save_mgr.load_game(save_file)
            if loaded is None:
                logger.warning("Failed to load save file")
                return False

            # プレイヤー・ダンジョンの復元
            self.player = loaded.player
            current_dungeon = loaded.dungeon
            if hasattr(loaded, 'traps') and loaded.traps:
                current_dungeon.traps = loaded.traps
            self.dungeon_manager.save_level(loaded.cur_level, current_dungeon)
            self.dungeon_manager.set_current_level(loaded.cur_level)
            self.dungeon_manager.current_level = loaded.cur_level
            self.player.dungeon_level = loaded.cur_level

            # ゲーム状態変数の復元 (game_state.py GameStateClass)
            GameState.cur_level = loaded.cur_level
            GameState.max_level = getattr(loaded, 'max_level', loaded.cur_level)
            GameState.foods = getattr(loaded, 'foods', 0)
            GameState.party_room = getattr(loaded, 'party_room', const.NO_ROOM)
            GameState.party_counter = getattr(loaded, 'party_counter', 0)
            GameState.cur_room = getattr(loaded, 'cur_room', const.NO_ROOM)
            GameState.being_held = getattr(loaded, 'being_held', False)
            GameState.bear_trap = getattr(loaded, 'bear_trap', 0)
            GameState.halluc = getattr(loaded, 'halluc', 0)
            GameState.blind = getattr(loaded, 'blind', 0)
            GameState.confused = getattr(loaded, 'confused', 0)
            GameState.levitate = getattr(loaded, 'levitate', 0)
            GameState.haste_self = getattr(loaded, 'haste_self', 0)
            GameState.see_invisible = getattr(loaded, 'see_invisible', False)
            GameState.detect_monster = getattr(loaded, 'detect_monster', False)
            GameState.wizard = getattr(loaded, 'wizard', False)
            GameState.score_only = getattr(loaded, 'score_only', False)
            GameState.m_moves = getattr(loaded, 'm_moves', 0)
            GameState.hunger_str = getattr(loaded, 'hunger_str', "")
            GameState.sustain_strength = getattr(loaded, 'sustain_strength', False)
            GameState.add_strength = getattr(loaded, 'add_strength', 0)
            GameState.ring_exp = getattr(loaded, 'ring_exp', 0)
            GameState.stealthy = getattr(loaded, 'stealthy', 0)
            GameState.r_teleport = getattr(loaded, 'r_teleport', False)
            GameState.auto_search = getattr(loaded, 'auto_search', 0)
            GameState.regeneration = getattr(loaded, 'regeneration', 0)
            GameState.e_rings = getattr(loaded, 'e_rings', 0)
            GameState.r_see_invisible = getattr(loaded, 'r_see_invisible', False)
            GameState.maintain_armor = getattr(loaded, 'maintain_armor', False)
            GameState.confused_player = getattr(loaded, 'confused_player', False)
            GameState.aggravate_monster = getattr(loaded, 'aggravate_monster', False)
            GameState.interrupted = getattr(loaded, 'interrupted', False)
            GameState.extra_hp = getattr(loaded, 'extra_hp', 0)
            GameState.trap_door = getattr(loaded, 'trap_door', False)
            GameState.new_level_message = getattr(loaded, 'new_level_message', "")
            if hasattr(loaded, 'r_rings'):
                GameState.r_rings = loaded.r_rings

            # IDテーブルの復元
            if loaded.id_potions:
                inventory.id_potions = loaded.id_potions
            if loaded.id_scrolls:
                inventory.id_scrolls = loaded.id_scrolls
            if loaded.id_wands:
                inventory.id_wands = loaded.id_wands
            if loaded.id_rings:
                inventory.id_rings = loaded.id_rings
            if loaded.is_wood:
                inventory.is_wood = loaded.is_wood

            # パーティルーム・カウンター
            self.party_room = GameState.party_room
            self.party_counter = GameState.party_counter

            # ロード後に指輪効果を再計算 (C版 save.c: restore → ring_stats(0))
            self._restore_ring_stats()

            # ウィザードモードでなければセーブファイルを削除
            if not GameState.wizard:
                save_mgr.delete_save_file(save_file)

            logger.info("Game restored successfully")
            return True

        except Exception as e:
            logger.error(f"Restore error: {e}", exc_info=True)
            if self.message:
                self.message.message(f"復元エラー: {e}")
            return False

    def _restore_ring_stats(self):
        """ロード後に指輪効果を再計算 (C版 ring.c: ring_stats(0))"""
        try:
            from . import special_actions as sa
        except ImportError:
            import special_actions as sa

        # 指輪効果変数をリセット
        GameState.stealthy = 0
        GameState.r_rings = 0
        GameState.e_rings = 0
        GameState.r_teleport = False
        GameState.sustain_strength = False
        GameState.add_strength = 0
        GameState.regeneration = 0
        GameState.ring_exp = 0
        GameState.r_see_invisible = False
        GameState.maintain_armor = False
        GameState.auto_search = 0

        # 装備中の指輪に基づいて再計算
        for ring in [self.player.left_ring, self.player.right_ring]:
            if ring is None:
                continue
            ring_kind = ring.which_kind
            ring_class = getattr(ring, 'class_', 0)

            GameState.r_rings += 1
            GameState.e_rings += 1

            if ring_kind == const.STEALTH:
                GameState.stealthy += 1
            elif ring_kind == const.R_TELEPORT:
                GameState.r_teleport = True
            elif ring_kind == const.REGENERATION:
                GameState.regeneration += 1
            elif ring_kind == const.SLOW_DIGEST:
                GameState.e_rings -= 2
            elif ring_kind == const.ADD_STRENGTH:
                GameState.add_strength += ring_class
            elif ring_kind == const.SUSTAIN_STRENGTH:
                GameState.sustain_strength = True
            elif ring_kind == const.DEXTERITY:
                GameState.ring_exp += ring_class
            elif ring_kind == const.R_SEE_INVISIBLE:
                GameState.r_see_invisible = True
            elif ring_kind == const.MAINTAIN_ARMOR:
                GameState.maintain_armor = True
            elif ring_kind == const.SEARCHING:
                GameState.auto_search += 2

    def _put_scores(self) -> None:
        """スコアを表示 (C版 score.c: put_scores相当の最小実装)"""
        try:
            mgr = score_manager.ScoreManager()
            scores = mgr.get_high_scores()
        except Exception:
            scores = []
        if self.display:
            try:
                self.display.clear()
                self.display.mvaddstr(2, 30, "Top 10 Rogue Scores")
                for i, e in enumerate(scores[:10]):
                    line = "%2d. %dG %s" % (i + 1, getattr(e, 'gold', 0), getattr(e, 'name', ''))
                    self.display.mvaddstr(4 + i, 20, line[:40])
                self.display.mvaddstr(const.ROGUE_LINES - 1, 0, "--スペースキーで終了--")
                self.display.refresh()
                while True:
                    ch = self.display.getch()
                    if ch in (ord(' '), 27, ord('\n'), ord('\r')):
                        break
            except Exception:
                pass
        else:
            for i, e in enumerate(scores[:10]):
                print("%2d. %dG %s" % (i + 1, getattr(e, 'gold', 0), getattr(e, 'name', '')))

    def _get_login_name(self) -> str:
        """ログイン名を取得"""
        try:
            import getpass
            return getpass.getuser()
        except:
            return "player"

    def _get_random_seed(self) -> int:
        """乱数シードを取得"""
        import time
        return int(time.time())

    def _clean_up(self, error_msg: str) -> None:
        """クリーンアップして終了"""
        # キーログを閉じる
        debug_module.close_keylog()
        
        if self.stdscr:
            try:
                self.stdscr.move(const.ROGUE_LINES - 1, 0)
                self.stdscr.clrtoeol()
                self.stdscr.refresh()
            except:
                pass
            self._end_curses()

        if error_msg:
            print(f"\n{error_msg}\n")

    def _signal_handler(self, signum, frame):
        """シグナルハンドラ（Ctrl+C対応）"""
        self._clean_up("")
        sys.exit(0)

    def _signal_handler_tstp(self, signum, frame):
        """シグナルハンドラ（Ctrl+Z対応、Unixのみ）"""
        if self.stdscr:
            self._end_curses()
            os.kill(os.getpid(), signal.SIGSTOP)
            # 再開時
            self.stdscr = self._init_curses()
            self.stdscr.refresh()

    def killed_by(self, monster, other):
        """死亡処理（C版 score.c: killed_by。表示+ScoreManager記録）"""
        import time
        # entitiesはファイル先頭でインポート済み

        # スコア記録 (C版 killed_by末尾 put_scores相当。二重減額を避けotherのみ渡す)
        try:
            from .score_manager import ScoreManager as _SM
            _sm = _SM()
            _name = getattr(monster, 'name', None) or getattr(monster, 'm_char', None)
            if isinstance(_name, int):
                try:
                    _name = chr(_name)
                except Exception:
                    _name = str(_name)
            # QUITは金減額なし・墓石なしがC仕様。記録自体は行う
            # 注意: _sm.killed_by内で金9/10減額済みのためここでは減額しない (C score.c:82-84相当)
            _sm.killed_by(_name, other, self.player)
        except Exception:
            pass
        
        # 金額ペナルティはScoreManager側で実施済みのためここでは行わない

        if self.display:
            # 画面クリア
            self.stdscr.clear()
            
            # 墓石の描画 (src/score.c より)
            xpos = [35, 34, 33, 32, 31, 30, 30, 30, 30, 30, 30, 30, 29, 21]
            grave = [
                "----------",
                "/          \\",
                "/            \\",
                "/              \\",
                "/                \\",
                "/                  \\",
                "|                  |",
                "|                  |",
                "|                  |",
                "|                  |",
                "|                  |",
                "|                  |",
                "*|     *  *  *      | *",
                "________)/\\\\_//(\\/(/\\)/\\//\\/|_)_______"
            ]
            
            for i, line in enumerate(grave):
                self.display.mvaddstr(i + 3, xpos[i], line)
            
            # テキストを中央寄せ
            def center(y, text):
                x = (const.ROGUE_COLUMNS - len(text)) // 2
                self.display.mvaddstr(y, x, text)
            
            center(6, "Ｒ．Ｉ．Ｐ．")
            center(9, self.nick_name)
            
            if other == 0 and monster:
                # モンスターに殺された
                center(12, monster.name)
                center(13, "に殺されました")
            elif other == const.STARVATION:
                center(12, "飢え")
                center(13, "で死にました")
            elif other == const.POISON_DART:
                center(12, "毒矢")
                center(13, "で死にました")
            elif other == const.HYPOTHERMIA:
                center(12, "低体温")
                center(13, "で死にました")
            elif other == const.QUIT:
                center(12, "引退しました")
                
            center(10, f"{self.player.gold} ゴールド")
            
            lt = time.localtime()
            center(14, f"{lt.tm_year}年")
            
            self.display.refresh()
            # メッセージ待機
            self.display.mvaddstr(const.ROGUE_LINES - 1, 0, "--スペースキーで終了--")
            self.display.refresh()
            while True:
                ch = self.display.getch()
                if ch == ord(' '): break
        
        self._clean_up("")
        sys.exit(0)
    
    def _get_room_number(self, dungeon_level, row: int, col: int) -> int:
        """指定位置の部屋番号を取得"""
        for i in range(const.MAXROOMS):
            room = dungeon_level.rooms[i]
            if (row >= room.top_row and row <= room.bottom_row and
                col >= room.left_col and col <= room.right_col):
                return i
        return const.NO_ROOM
    
    # ===== ヘルパーメソッド =====
    
    def _get_direction_input(self, prompt: str = "方向? ") -> Optional[str]:
        """方向キー入力を取得して方向文字を返す"""
        if self.message:
            self.message.message(prompt)
        
        while True:
            ch = self._get_input()
            if ch is None:
                return None
            if ch in 'hjklbyunHJKLBYUN':
                return ch.lower()
            if ch == '\x1b' or ch == 'q':  # ESC or q to cancel
                return None
    
    def _select_from_pack(self, prompt: str, mask: int) -> Optional[entities.Item]:
        """インベントリからアイテムを選択 (C版 pack.c: pack_letter相当)"""
        if self.display:
            # インベントリを表示
            self.display.inventory(self.player.pack, mask, self.stats, self.player)

            # 文字入力待ち（LIST '*' で再表示ループ。C版 pack_letter相当）
            if self.message:
                self.message.message(prompt)

            while True:
                ch = self._get_input()
                if ch is None or ch == '\x1b':
                    current_dungeon = self.dungeon_manager.get_current_level()
                    self.display.draw_map(current_dungeon, self.player)
                    return None
                if ch == '*':
                    # LIST: 一覧を再表示して再入力
                    self.display.inventory(self.player.pack, mask, self.stats, self.player)
                    if self.message:
                        self.message.message(prompt)
                    continue

                # 選択されたアイテムを検索
                obj = self._get_letter_object(ch)
                if obj is not None and (obj.item_type & mask):
                    return obj
                # 種別キー（is_pack_letter相当: ? ! : ) ] / = ,）→該当先頭品
                mapped = self._pack_letter_mask(ch)
                if mapped:
                    obj = self.player.pack
                    while obj:
                        if obj.item_type & mapped:
                            return obj
                        obj = obj.next_object
                if self.message:
                    self.message.message("そのようなアイテムはない")

            # 再描画
            current_dungeon = self.dungeon_manager.get_current_level()
            self.display.draw_map(current_dungeon, self.player)

        # 非display経路（AI/ヘッドレス用）：先頭一致品を返す
        obj = self.player.pack
        while obj:
            if obj.item_type & mask:
                return obj
            obj = obj.next_object
        return None

    @staticmethod
    def _pack_letter_mask(ch: str) -> int:
        """種別キー→マスク (C版 pack.c: is_pack_letter相当)"""
        return {
            '?': const.SCROL, '!': const.POTION, ':': const.FOOD,
            ')': const.WEAPON, ']': const.ARMOR, '/': const.WAND,
            '=': const.RING, ',': const.AMULET,
        }.get(ch, 0)
    
    def _get_letter_object(self, ch: str) -> Optional[entities.Item]:
        """文字からアイテムを取得"""
        obj = self.player.pack
        while obj:
            if chr(obj.ichar) == ch:
                return obj
            obj = obj.next_object
        return None
    
    # ===== コマンド実装 =====
    
    def _throw(self):
        """
        投げるコマンド (C版 throw.c: throw)
        
        方向と武器を選択して投擲する。
        """
        current_dungeon = self.dungeon_manager.get_current_level()
        
        # 方向を取得
        dirch = self._get_direction_input("どちらに投げますか？")
        if dirch is None:
            if self.message:
                self.message.message("キャンセル")
            return
        
        # 方向文字を方向定数に変換
        dir_map = {
            'h': const.LEFT, 'j': const.DOWN, 'k': const.UP, 'l': const.RIGHT,
            'y': const.LEFTUP, 'u': const.UPRIGHT, 'b': const.DOWNLEFT, 'n': const.RIGHTDOWN
        }
        dir_const = dir_map.get(dirch)
        if dir_const is None:
            return
        
        # 投げるアイテムを選択
        obj = self._select_from_pack("何を投げますか？", const.WEAPON)
        if obj is None:
            return
        
        # 投擲アクションを実行 (C版 throw.c 準拠)
        throw_action = special_actions.ThrowAction(
            self.player, current_dungeon, self.display, self.message
        )
        throw_action.throw(dir_const, obj)
        
        # 画面を再描画
        if self.display:
            self.display.draw_map(current_dungeon, self.player)
            self.display.draw_entities(current_dungeon, self.player,
                                        self._get_room_number(current_dungeon, self.player.row, self.player.col))
    
    def _monster_at(self, row: int, col: int, current_dungeon) -> Optional[entities.Monster]:
        """指定位置のモンスターを取得"""
        monster = current_dungeon.level_monsters
        while monster:
            if monster.row == row and monster.col == col:
                return monster
            monster = monster.next_object
        return None
    
    def _remove_monster(self, monster: entities.Monster, current_dungeon):
        """モンスターをリストから削除"""
        if current_dungeon.level_monsters == monster:
            current_dungeon.level_monsters = monster.next_object
        else:
            curr = current_dungeon.level_monsters
            while curr and curr.next_object != monster:
                curr = curr.next_object
            if curr:
                curr.next_object = monster.next_object
    
    def _remove_from_pack(self, item: entities.Item):
        """アイテムをインベントリから削除"""
        if self.player.pack == item:
            self.player.pack = item.next_object
        else:
            curr = self.player.pack
            while curr and curr.next_object != item:
                curr = curr.next_object
            if curr:
                curr.next_object = item.next_object
    
    def _fight(self, force: bool):
        """戦闘コマンド"""
        current_dungeon = self.dungeon_manager.get_current_level()
        
        dirch = self._get_direction_input("どちらと戦いますか？")
        if dirch is None:
            return
        
        dir_map = {
            'h': (0, -1), 'j': (1, 0), 'k': (-1, 0), 'l': (0, 1),
            'y': (-1, -1), 'u': (-1, 1), 'b': (1, -1), 'n': (1, 1)
        }
        dr, dc = dir_map.get(dirch, (0, 0))
        target_row = self.player.row + dr
        target_col = self.player.col + dc
        
        monster = self._monster_at(target_row, target_col, current_dungeon)
        if monster:
            combat_instance = combat.Combat(self.player, current_dungeon)
            combat_instance.display = self.display
            combat_instance.msg = self.message
            combat_instance.game = self
            combat_instance.rogue_hit(monster, force)
            if monster.hp_to_kill > 0:
                combat_instance.mon_hit(monster)
        else:
            if self.message:
                self.message.message("そこには何もいない")
    
    def _quaff(self):
        """ポーションを飲む"""
        current_dungeon = self.dungeon_manager.get_current_level()
        
        obj = self._select_from_pack("何を飲みますか？", const.POTION)
        if obj is None:
            return
        
        if obj.item_type != const.POTION:
            if self.message:
                self.message.message("それはポーションではない")
            return
        
        inv_manager = inventory.InventoryManager(self.player, current_dungeon)
        use_action = use_actions.UseActions(self.player, current_dungeon, inv_manager, self.display, self.message, self)
        use_action.quaff(obj)
    
    def _read_scroll(self):
        """巻物を読む"""
        current_dungeon = self.dungeon_manager.get_current_level()
        
        obj = self._select_from_pack("何を読みますか？", const.SCROL)
        if obj is None:
            return
        
        if obj.item_type != const.SCROL:
            if self.message:
                self.message.message("それは巻物ではない")
            return
        
        inv_manager = inventory.InventoryManager(self.player, current_dungeon)
        use_action = use_actions.UseActions(self.player, current_dungeon, inv_manager, self.display, self.message, self)
        use_action.read_scroll(obj)
    
    def _eat(self):
        """食べる"""
        current_dungeon = self.dungeon_manager.get_current_level()
        
        obj = self._select_from_pack("何を食べますか？", const.FOOD)
        if obj is None:
            return
        
        if obj.item_type != const.FOOD:
            if self.message:
                self.message.message("それは食料ではない")
            return
        
        inv_manager = inventory.InventoryManager(self.player, current_dungeon)
        use_action = use_actions.UseActions(self.player, current_dungeon, inv_manager, self.display, self.message, self)
        use_action.eat(obj)
    
    def _wield(self):
        """武器を装備"""
        current_dungeon = self.dungeon_manager.get_current_level()
        
        obj = self._select_from_pack("何を装備しますか？", const.WEAPON)
        if obj is None:
            return
        
        if obj.item_type != const.WEAPON:
            if self.message:
                self.message.message("それは武器ではない")
            return
        
        inv_manager = inventory.InventoryManager(self.player, current_dungeon)
        inv_manager.wield(obj)
    
    def _wear(self):
        """鎧を装備"""
        current_dungeon = self.dungeon_manager.get_current_level()
        
        obj = self._select_from_pack("何を着ますか？", const.ARMOR)
        if obj is None:
            return
        
        if obj.item_type != const.ARMOR:
            if self.message:
                self.message.message("それは鎧ではない")
            return
        
        inv_manager = inventory.InventoryManager(self.player, current_dungeon)
        inv_manager.wear(obj)
    
    def _take_off(self):
        """鎧を脱ぐ"""
        current_dungeon = self.dungeon_manager.get_current_level()
        inv_manager = inventory.InventoryManager(self.player, current_dungeon)
        inv_manager.take_off()
    
    def _put_on_ring(self):
        """指輪を装備"""
        ring_action = special_actions.RingAction(self.player)
        ring_action.put_on_ring()
    
    def _remove_ring(self):
        """指輪を外す"""
        ring_action = special_actions.RingAction(self.player)
        ring_action.remove_ring()
    
    def _drop(self):
        """アイテムを落とす (C版 pack.c: drop相当)"""
        current_dungeon = self.dungeon_manager.get_current_level()

        # 落とすアイテムを選択
        obj = self._select_from_pack("何を落としますか？", const.ALL_OBJECTS)
        if obj is None:
            return

        # 階段・罠上には落とせない (C版 pack.c:122)
        tile = current_dungeon.get_tile(self.player.row, self.player.col)
        if tile & (const.STAIRS | const.TRAP):
            if self.message:
                self.message.message("ここには落とせない")
            return

        # 装備中なら外す（指輪の呪い検査含む）
        if obj.in_use_flags & const.BEING_WIELDED:
            if obj.is_cursed:
                if self.message:
                    self.message.message("呪われていて落とせない！")
                return
            obj.in_use_flags &= ~const.BEING_WIELDED
            self.player.weapon = None
        elif obj.in_use_flags & const.BEING_WORN:
            if obj.is_cursed:
                if self.message:
                    self.message.message("呪われていて落とせない！")
                return
            obj.in_use_flags &= ~const.BEING_WORN
            self.player.armor = None
        elif obj.in_use_flags & const.ON_EITHER_HAND:
            if obj.is_cursed:
                if self.message:
                    self.message.message("呪われていて落とせない！")
                return
            if self.player.left_ring is obj:
                self.player.left_ring = None
            if self.player.right_ring is obj:
                self.player.right_ring = None
            obj.in_use_flags &= ~const.ON_EITHER_HAND

        # 数量分割（武器以外で2個以上。C版 pack.c:161）
        if obj.quantity > 1 and not (obj.item_type & const.WEAPON):
            drop_obj = entities.Item()
            drop_obj.item_type = obj.item_type
            drop_obj.which_kind = obj.which_kind
            drop_obj.item_kind = getattr(obj, 'item_kind', obj.which_kind)
            drop_obj.quantity = 1
            drop_obj.ichar = obj.ichar
            obj.quantity -= 1
        else:
            drop_obj = obj
            # インベントリから削除（先に外してから地上へ）
            self._remove_from_pack(obj)

        # 地上へ配置 (C版 place_at相当)
        drop_obj.row = self.player.row
        drop_obj.col = self.player.col
        drop_obj.next_object = current_dungeon.level_objects
        current_dungeon.level_objects = drop_obj
        current_dungeon.set_tile(self.player.row, self.player.col,
            current_dungeon.get_tile(self.player.row, self.player.col) | const.OBJECT)

        # 手数進行
        if self._movement is not None:
            try:
                self._movement.reg_move()
            except Exception:
                pass

        if self.message:
            self.message.message("アイテムを落とした")
    
    def _move_onto(self):
        """移動（アイテムを拾わない）(C版 move.c: move_onto)"""
        dirch = self._get_direction_input("どちらに移動しますか？")
        if dirch is None:
            return
        
        current_dungeon = self.dungeon_manager.get_current_level()
        movement = actions.Movement(self.player, current_dungeon, self.display, self.message, self)
        
        # pickup=Falseで移動
        movement.one_move_rogue(dirch, False)
    
    def _zapp(self):
        """杖を振る (C版 zap.c: zapp)"""
        current_dungeon = self.dungeon_manager.get_current_level()
        
        # 杖を選択
        obj = self._select_from_pack("どの杖を振りますか？", const.WAND)
        if obj is None:
            return
        
        if obj.item_type != const.WAND:
            if self.message:
                self.message.message("それは杖ではない")
            return
        
        # 方向を取得
        dirch = self._get_direction_input("どちらに向けますか？")
        if dirch is None:
            return
        
        # 方向文字を方向定数に変換
        dir_map = {
            'h': const.LEFT, 'j': const.DOWN, 'k': const.UP, 'l': const.RIGHT,
            'y': const.LEFTUP, 'u': const.UPRIGHT, 'b': const.DOWNLEFT, 'n': const.RIGHTDOWN
        }
        dir_const = dir_map.get(dirch)
        if dir_const is None:
            return
        
        # 杖アクションを実行
        wand_action = special_actions.WandAction(
            self.player, current_dungeon, self.display, self.message
        )
        wand_action.zapp(dir_const, obj)
        
        # 画面を再描画
        if self.display:
            self.display.draw_map(current_dungeon, self.player)
            self.display.draw_entities(current_dungeon, self.player,
                                        self._get_room_number(current_dungeon, self.player.row, self.player.col))
    
    def _help(self):
        """ヘルプを表示 (C版 play.c: help)"""
        if not self.display:
            return
        
        help_messages = [
            "Rogue コマンド一覧:",
            "",
            "移動: h j k l y u b n (viキー)",
            "連続移動: H J K L B Y U N",
            "",
            "アクション:",
            "  f - 戦闘    F - 死ぬまで戦う",
            "  t - 投げる  m - 移動（拾わない）",
            "  s - 探索    . - 休憩",
            "  > - 階段を降りる",
            "",
            "アイテム:",
            "  i - インベントリ  , - 拾う",
            "  e - 食べる        q - 飲む",
            "  r - 読む          z - 杖を振る",
            "  w - 武器装備      W - 鎧装備",
            "  T - 鎧脱ぐ        P - 指輪装備",
            "  R - 指輪外す      d - 落とす",
            "",
            "その他:",
            "  ? - ヘルプ    v - バージョン",
            "  S - セーブ    Q - 終了",
            "  @ - ステータス",
            "",
            "--スペースを押してください--"
        ]
        
        # 画面をクリアしてヘルプを表示
        self.display.clear()
        for i, msg in enumerate(help_messages):
            self.display.mvaddstr(i, 0, msg)
        
        self.display.refresh()
        
        # スペースキー待ち
        while True:
            ch = self._get_input()
            if ch == ' ':
                break
        
        # 画面を再描画
        current_dungeon = self.dungeon_manager.get_current_level()
        self.display.draw_map(current_dungeon, self.player)
        self.display.draw_entities(current_dungeon, self.player,
                                   self._get_room_number(current_dungeon, self.player.row, self.player.col))
    
    def _show_version(self):
        """バージョンを表示 (C版 play.c: case 'v')"""
        if self.message:
            self.message.message("Rogue2.Official Python版 v1.0")
    
    def _save_game(self):
        """ゲームをセーブ (C版 save.c: save_game)"""
        current_dungeon = self.dungeon_manager.get_current_level()
        
        try:
            save_mgr = save_manager.SaveManager()
            # GameState オブジェクトを作成して save_game に渡す
            game_state = save_manager.create_game_state(
                player=self.player,
                dungeon=current_dungeon,
                cur_level=self.dungeon_manager.current_level,
                max_level=getattr(self, 'max_level', self.dungeon_manager.current_level),
                foods=getattr(self.player, 'foods', 0),
                party_room=self.party_room,
                party_counter=self.party_counter,
                m_moves=GameState.m_moves,
                bear_trap=GameState.bear_trap,
                hunger_str=GameState.hunger_str,
                login_name=self.login_name,
                # ゲーム状態変数 (game_state.py / use.c / ring.c / move.c / trap.c)
                being_held=GameState.being_held,
                halluc=GameState.halluc,
                blind=GameState.blind,
                confused=GameState.confused,
                levitate=GameState.levitate,
                haste_self=GameState.haste_self,
                see_invisible=GameState.see_invisible,
                detect_monster=GameState.detect_monster,
                wizard=GameState.wizard,
                score_only=GameState.score_only,
                cur_room=GameState.cur_room,
                sustain_strength=GameState.sustain_strength,
                add_strength=GameState.add_strength,
                ring_exp=GameState.ring_exp,
                stealthy=GameState.stealthy,
                r_teleport=GameState.r_teleport,
                auto_search=GameState.auto_search,
                regeneration=GameState.regeneration,
                e_rings=GameState.e_rings,
                r_see_invisible=GameState.r_see_invisible,
                maintain_armor=GameState.maintain_armor,
                confused_player=GameState.confused_player,
                aggravate_monster=GameState.aggravate_monster,
                interrupted=GameState.interrupted,
                extra_hp=GameState.extra_hp,
                trap_door=GameState.trap_door,
                new_level_message=GameState.new_level_message,
                l_rings=GameState.l_rings if hasattr(GameState, 'l_rings') else 0,
                r_rings=GameState.r_rings if hasattr(GameState, 'r_rings') else 0,
                traps=current_dungeon.traps,
            )
            if save_mgr.save_game(game_state):
                # C版 save.c:148-152 成功で終了する
                if self.ai_driver is not None:
                    self.ai_driver.stop("saved")
                self._clean_up("")
                raise SystemExit(0)
            else:
                if self.message:
                    self.message.message("セーブに失敗しました")
        except Exception as e:
            logger.error(f"Save error: {e}", exc_info=True)
            if self.message:
                self.message.message(f"セーブエラー: {e}")
    
    def _options(self) -> None:
        """オプション表示・切替 (C版 play.c: options相当の最小実装)"""
        while True:
            if self.message:
                self.message.message(
                    "jump:%s pass_go:%s (j/p切替, ESC終了)" % (
                        "on" if GameState.jump else "off",
                        "on" if GameState.pass_go else "off"), False)
            ch = self._get_input()
            if ch is None:
                continue
            if ch == '\x1b':
                break
            if ch == 'j':
                GameState.jump = not GameState.jump
            elif ch == 'p':
                GameState.pass_go = not GameState.pass_go
        if self.display:
            try:
                current = self.dungeon_manager.get_current_level()
                self.display.draw_map(current, self.player)
            except Exception:
                pass

    def _input_line(self, prompt: str, maxlen: int = 24) -> Optional[str]:
        """1行入力 (C版 message.c: input_line/do_input_line の最小実装)。

        ESC→None（CANCEL）、Enter→確定、Backspace対応。
        """
        buf = ""
        while True:
            if self.message:
                self.message.message(prompt + buf, False)
            ch = self._get_input()
            if ch is None:
                continue
            if ch == '\x1b':
                return None
            if ch in ('\n', '\r'):
                return buf.strip()
            if ch in ('\x08', '\x7f'):
                buf = buf[:-1]
                continue
            if len(ch) == 1 and 32 <= ord(ch) < 127 and len(buf) < maxlen:
                buf += ch

    def _discovered(self):
        """発見済みアイテム一覧を表示 (C版 invent.c: discovered)"""
        found = []
        obj = self.player.pack
        while obj:
            slot = chr(obj.ichar) if isinstance(obj.ichar, int) else str(obj.ichar)
            identified = bool(getattr(obj, 'identified', 0)) or bool(getattr(obj, 'is_identified', False))
            called = bool(getattr(obj, 'is_called', False))
            if identified or called:
                name = getattr(obj, 'call_name', '') if called else ''
                found.append("%s: 種別%d%s" % (slot, obj.item_type, ("「%s」" % name) if name else ""))
            obj = obj.next_object
        if not found:
            if self.message:
                self.message.message("まだ何も識別していない")
            return
        for line in found:
            if self.message:
                self.message.message(line, False)
    
    def _identify_char(self):
        """文字の識別 (C版 play.c: identify)"""
        if self.message:
            self.message.message("文字を入力してください: ")
        
        ch = self._get_input()
        if ch is None:
            return
        
        # 文字の説明
        char_desc = {
            '@': 'あなた',
            '.': '床',
            '#': '通路',
            '+': 'ドア',
            '%': '床のアイテム',
            '*': '金貨',
            ':': '食料',
            '!': 'ポーション',
            '?': '巻物',
            '/': '杖',
            ')': '武器',
            ']': '防具',
            '=': '指輪',
            ',': 'アミュレット',
            '^': '罠（見えている）',
            '>': '階段',
        }
        
        # モンスター文字
        if 'A' <= ch <= 'Z':
            try:
                idx = ord(ch) - ord('A')
                from entities import M_NAMES
                if idx < len(M_NAMES):
                    desc = M_NAMES[idx]
                else:
                    desc = f"モンスター({ch})"
            except:
                desc = f"モンスター({ch})"
        else:
            desc = char_desc.get(ch, f"不明な文字: {ch}")
        
        if self.message:
            self.message.message(f"'{ch}': {desc}")
    
    def _call_it(self):
        """名前をつける (C版 pack.c: call_it)"""
        obj = self._select_from_pack("どれに名前をつけますか？", const.ALL_OBJECTS)
        if obj is None:
            return
        name = self._input_line("呼び名: ", 24)
        if not name:
            return
        obj.is_called = True
        obj.call_name = name
        # 識別テーブル側もCALLED化 (C版準拠)
        try:
            table = None
            t = obj.item_type
            if t & const.SCROL:
                table = inventory.id_scrolls
            elif t & const.POTION:
                table = inventory.id_potions
            elif t & const.WAND:
                table = inventory.id_wands
            elif t & const.RING:
                table = inventory.id_rings
            elif t & const.WEAPON:
                table = inventory.id_weapons
            elif t & const.ARMOR:
                table = inventory.id_armors
            kind = obj.which_kind if getattr(obj, 'which_kind', 0) else 0
            if table is not None and 0 <= kind < len(table):
                table[kind].id_status = const.CALLED
                table[kind].title = name
        except Exception:
            pass
    
    def _inv_weapon(self):
        """武器情報を表示 (C版 invent.c: inv_armor_weapon)"""
        if self.player.weapon:
            if self.message:
                self.message.message(f"武器: {self.player.weapon.damage}")
        else:
            if self.message:
                self.message.message("武器を装備していない")
    
    def _inv_armor(self):
        """防具情報を表示 (C版 invent.c: inv_armor_weapon)"""
        if self.player.armor:
            ac = self.player.armor.d_enchant
            if self.message:
                self.message.message(f"防具: AC {ac}")
        else:
            if self.message:
                self.message.message("防具を装備していない")
    
    def _inv_rings(self):
        """指輪情報を表示 (C版 invent.c: inv_rings)"""
        rings = []
        if self.player.left_ring:
            rings.append(f"左: 指輪")
        if self.player.right_ring:
            rings.append(f"右: 指輪")
        
        if rings:
            if self.message:
                self.message.message(" ".join(rings))
        else:
            if self.message:
                self.message.message("指輪をはめていない")
    
    def _id_trap(self):
        """罠識別 (C版 trap.c: id_trap)"""
        dirch = self._get_direction_input("どちらに？")
        if dirch is None:
            return
        offsets = {'h': (0, -1), 'j': (1, 0), 'k': (-1, 0), 'l': (0, 1),
                   'y': (-1, -1), 'u': (-1, 1), 'b': (1, -1), 'n': (1, 1)}
        dr, dc = offsets.get(dirch, (0, 0))
        row, col = self.player.row + dr, self.player.col + dc
        current = self.dungeon_manager.get_current_level()
        try:
            tile = current.get_tile(row, col)
        except Exception:
            tile = 0
        if (tile & const.TRAP) and not (tile & const.HIDDEN):
            trap = current.get_trap_at(row, col) if hasattr(current, 'get_trap_at') else None
            t = trap.trap_type if trap is not None and hasattr(trap, 'trap_type') else const.NO_TRAP
            name = actions.TRAP_MESSAGES.get(t, ("罠", ""))[0]
            if self.message:
                self.message.message(name, False)
        else:
            if self.message:
                try:
                    from text_resources import get_message
                    self.message.message(get_message(229), False)
                except Exception:
                    self.message.message("そこに罠はない", False)
    
    def _single_inv(self):
        """単一アイテム表示 (C版 invent.c: single_inv)"""
        if self.message:
            self.message.message("アイテム文字を入力: ")
        
        ch = self._get_input()
        if ch is None:
            return
        
        obj = self._get_letter_object(ch)
        if obj:
            if self.message:
                self.message.message(f"アイテム: {obj.item_type}")
        else:
            if self.message:
                self.message.message("そのアイテムはない")
    
    def _remessage(self):
        """最後のメッセージを再表示 (C版 message.c: remessage)"""
        if self.message:
            self.message.remessage()
    
    def _check_up(self) -> bool:
        """階段を上る処理 (C版 level.c: check_up)"""
        current_dungeon = self.dungeon_manager.get_current_level()
        
        # ウィザードモードでない場合、チェックを行う
        # if not game_state.wizard:
        # 階段の上にいるかチェック
        if not (current_dungeon.get_tile(self.player.row, self.player.col) & const.STAIRS):
            if self.message:
                self.message.message("ここには階段はない")  # mesg[50]
            return False
        
        # アミュレットを持っているかチェック
        if not self._has_amulet():
            if self.message:
                self.message.message("アミュレットを持っていないと上に行けない")  # mesg[51]
            return False
        
        # レベル1にいる場合は勝利
        if self.dungeon_manager.current_level == 1:
            self._win()
            return False
        
        # レベルを2つ下げる（次のループで+1されるため）
        self.dungeon_manager.current_level -= 2
        if self.message:
            self.message.message("上の階へ...")  # mesg[52]
        return True
    
    def _has_amulet(self) -> bool:
        """アミュレットを持っているかチェック (C版 pack.c: has_amulet)"""
        obj = self.player.pack
        while obj:
            if obj.item_type == const.AMULET:
                return True
            obj = obj.next_object
        return False
    
    def _win(self):
        """勝利処理 (C版 score.c: win)"""
        # スコア処理を実行（装備解除、アイテム識別、売却）
        score_mgr = score_manager.ScoreManager()
        score_mgr.win(self.player, self.display)

        if self.display:
            self.stdscr.clear()
            # 勝利バナー表示 (C版 score.c: win のバナー)
            center_row = 6
            banner = [
                "      @   @  @@@   @   @      @  @  @   @@@   @   @   @",
                "       @ @  @   @  @   @      @  @  @  @   @  @@  @   @",
                "        @   @   @  @   @      @  @  @  @   @  @ @ @   @",
                "        @   @   @  @   @      @  @  @  @   @  @  @@",
                "        @    @@@    @@@        @@ @@    @@@   @   @   @",
            ]
            congrats = [
                "おめでとう！  あなたは戦士ギルドに入会しました。",
                "",
                "あなたは家に帰り、すべての宝物を高値で売りさばき、",
                "安楽な引退生活に入りました。",
            ]
            for i, line in enumerate(banner):
                self.display.mvaddstr(center_row + i, 10, line)
            for i, line in enumerate(congrats):
                self.display.mvaddstr(center_row + len(banner) + 2 + i, 10, line)
            self.display.refresh()

            # キー入力待ち
            self.display.mvaddstr(const.ROGUE_LINES - 1, 0, "--スペースキーで終了--")
            self.display.refresh()
            while True:
                ch = self.display.getch()
                if ch == ord(' '):
                    break

        self._clean_up("")
        sys.exit(0)
    
    def _wizardize(self):
        """ウィザードモード切替 (C版 zap.c: wizardize)"""
        if GameState.wizard:
            GameState.wizard = False
            if self.message:
                self.message.message("もうウィザードではない")
        else:
            GameState.wizard = True
            GameState.score_only = True
            if self.message:
                self.message.message("ようこそ、ウィザードよ！")
    
    def _doshell(self):
        """シェル実行 (C版 play.c: doshell)"""
        import subprocess
        
        # シェルを取得
        shell = os.environ.get('SHELL', '/bin/sh')
        if sys.platform == 'win32':
            shell = os.environ.get('COMSPEC', 'cmd.exe')
        
        # cursesを一時停止
        self._end_curses()
        
        try:
            print("\nシェルを起動します。'exit' で戻ります。\n")
            subprocess.run(shell, shell=True)
        except Exception as e:
            print(f"\nシェル実行エラー: {e}")
        finally:
            # 入力待ち
            print("\nエンターキーでゲームに戻ります...")
            input()
            # cursesを再開
            self.stdscr = self._init_curses()
            if self.display:
                current_dungeon = self.dungeon_manager.get_current_level()
                self.display.draw_map(current_dungeon, self.player)
    
    def _get_count(self, first_digit: str):
        """カウント入力を取得 (C版 play.c: count処理)。

        戻り値 (count, terminator)。terminatorは消費せずプッシュバック
        する（C版 goto CH相当）。ESC時は (0, None)。
        """
        count = int(first_digit)

        while count < 100:
            ch = self._get_input()
            if ch is None:
                return count, None
            if ch.isdigit():
                count = count * 10 + int(ch)
            elif ch == '\x1b':  # ESC でキャンセル
                return 0, None
            else:
                self._pushback = ch
                return count, ch

        return count, None
    
    def _end_curses(self) -> None:
        """cursesを終了"""
        if self.stdscr:
            try:
                curses = config.get_curses_module()
                curses.nocbreak()
                self.stdscr.keypad(False)
                curses.echo()
                curses.endwin()
            except:
                pass
            self.is_initialized = False
            self.stdscr = None

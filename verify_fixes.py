import sys
import unittest
import os
from unittest.mock import MagicMock, patch

# Mock curses before importing modules that use it
sys.modules['curses'] = MagicMock()
sys.modules['windows_curses'] = MagicMock()

# Mock config to return the mocked curses
with patch.dict(sys.modules, {'config': MagicMock()}):
    import config
    config.get_curses_module = MagicMock(return_value=sys.modules['curses'])
    
    # Needs to be able to find modules in current directory
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    # Import the modules to test
    import display
    import game
    import actions
    import dungeon
    import entities
    import const

class TestRogueFixes(unittest.TestCase):
    def setUp(self):
        self.mock_stdscr = MagicMock()
        self.display = display.Display(self.mock_stdscr)
        self.dungeon_level = MagicMock(spec=dungeon.DungeonLevel)
        self.player = MagicMock(spec=entities.Player)
        self.player.row = 10
        self.player.col = 10
        # Mock dungeon grid
        self.dungeon_level.dungeon = [[const.FLOOR for _ in range(const.ROGUE_COLUMNS)] for _ in range(const.ROGUE_LINES)]
        self.dungeon_level.rooms = [MagicMock()] * const.MAXROOMS
        self.dungeon_level.get_tile.side_effect = lambda r, c: self.dungeon_level.dungeon[r][c]
        
    def test_fog_of_war_methods_exist(self):
        """Test that Fog of War methods exist in Display class"""
        print("Testing Fog of War methods in Display...")
        self.assertTrue(hasattr(self.display, 'light_up_room'), "light_up_room method missing in Display")
        self.assertTrue(hasattr(self.display, 'light_passage'), "light_passage method missing in Display")
        self.assertTrue(hasattr(self.display, 'darken_room'), "darken_room method missing in Display")
        self.assertTrue(hasattr(self.display, 'get_dungeon_char'), "get_dungeon_char method missing in Display")
        print("PASS: Fog of War methods exist.")

    def test_movement_accepts_display(self):
        """Test that Movement class accepts display parameter"""
        print("Testing Movement class init...")
        try:
            mov = actions.Movement(self.player, self.dungeon_level, self.display)
            self.assertEqual(mov.display, self.display, "Display object not stored in Movement")
            print("PASS: Movement class accepts display parameter.")
        except TypeError as e:
            self.fail(f"Movement.__init__ failed: {e}")

    def test_movement_calls_lighting(self):
        """Test that movement calls lighting methods"""
        print("Testing Movement calling lighting...")
        
        # Setup specific scenario: Tunnel to Room
        # 10,10 = TUNNEL
        # 10,11 = DOOR
        self.dungeon_level.dungeon[10][10] = const.TUNNEL
        self.dungeon_level.dungeon[10][11] = const.DOOR
        
        self.player.row = 10
        self.player.col = 10
        
        mov = actions.Movement(self.player, self.dungeon_level, self.display)
        mov.cur_room = const.PASSAGE # currently in passage
        
        # Mock helpers to allow move
        mov._can_move = MagicMock(return_value=True)
        mov._get_room_number = MagicMock(return_value=1)
        mov.is_passable = MagicMock(return_value=True)
        mov._trap_player = MagicMock()
        mov.reg_move = MagicMock()
        
        # Spy on display methods
        self.display.light_up_room = MagicMock()
        
        # Move RIGHT (l) to 10,11 (DOOR)
        # entering room from passage -> light_up_room should be called
        mov.one_move_rogue('l', True)
        
        # Check if light_up_room was called
        # actions.py: if dungeon[row][col] & DOOR and cur_room == PASSAGE: light_up_room
        self.display.light_up_room.assert_called()
        print("PASS: Movement calls light_up_room when entering room.")

    def test_signal_handler_exists(self):
        """Test that Game class has signal handler"""
        print("Testing Game class signal handler...")
        with patch('game.dungeon.DungeonManager'), patch('game.level_generator.LevelGenerator'), patch('game.actions.TrapManager'):
            g = game.Game()
            self.assertTrue(hasattr(g, '_signal_handler'), "_signal_handler missing in Game")
            print("PASS: Game class has signal handler.")

if __name__ == '__main__':
    unittest.main()

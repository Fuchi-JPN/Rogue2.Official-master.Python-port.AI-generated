"""AI攻略ロジックの単体テスト（設計書 §5.4 / Phase A1b）"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import const
from ai.schemas import AIObservation, AIStatus, IdentifyMemo
from ai import strategy


def _obs(**kw):
    obs = AIObservation()
    obs.status.hp_cur = kw.get("hp_cur", 12)
    obs.status.hp_max = kw.get("hp_max", 12)
    obs.status.moves_left = kw.get("moves_left", 1000)
    obs.player_pos = kw.get("pos", (10, 10))
    obs.visible_monsters = kw.get("monsters", [])
    obs.visible_items = kw.get("items", [])
    obs.stairs_pos = kw.get("stairs", None)
    obs.flags = kw.get("flags", {})
    # 全周FLOORのタイルキャッシュ
    cache = {}
    for r in range(const.MIN_ROW, const.ROGUE_LINES - 1):
        for c in range(const.ROGUE_COLUMNS):
            cache[(r, c)] = const.FLOOR
    obs._tile_cache = cache
    return obs


class TestStrategy(unittest.TestCase):
    def test_hunger_levels(self):
        self.assertEqual(strategy.hunger_level(1000), "ok")
        self.assertEqual(strategy.hunger_level(300), "hungry")
        self.assertEqual(strategy.hunger_level(150), "weak")
        self.assertEqual(strategy.hunger_level(20), "faint")

    def test_fight_when_advantaged(self):
        obs = _obs(monsters=[{"pos": (10, 11), "glyph": "K", "flags": 0}])
        risk = strategy.assess(obs)
        act, _ = strategy.decide(obs, risk, IdentifyMemo(), [])
        self.assertEqual(act.type, "fight")

    def test_retreat_when_weak(self):
        obs = _obs(hp_cur=2, hp_max=12,
                   monsters=[{"pos": (10, 11), "glyph": "K", "flags": 0}])
        risk = strategy.assess(obs)
        act, _ = strategy.decide(obs, risk, IdentifyMemo(), [])
        self.assertEqual(act.type, "move")  # 退避

    def test_retreat_when_outnumbered(self):
        obs = _obs(monsters=[{"pos": (10, 11), "glyph": "K", "flags": 0},
                             {"pos": (9, 10), "glyph": "O", "flags": 0}])
        risk = strategy.assess(obs)
        act, _ = strategy.decide(obs, risk, IdentifyMemo(), [])
        self.assertEqual(act.type, "move")

    def test_rest_when_hurt_and_safe(self):
        obs = _obs(hp_cur=8, hp_max=12)
        risk = strategy.assess(obs)
        act, _ = strategy.decide(obs, risk, IdentifyMemo(), [])
        self.assertEqual(act.type, "rest")

    def test_food_priority_when_weak(self):
        obs = _obs(hp_cur=8, hp_max=12, moves_left=100,
                   items=[{"pos": (10, 14), "glyph": ":", "type": const.FOOD, "slot": "a"}])
        risk = strategy.assess(obs)
        act, _ = strategy.decide(obs, risk, IdentifyMemo(), [])
        self.assertIn(act.type, ("move", "run"))  # 食料へ（回復より優先、長距離はrun）

    def test_pickup_at_feet(self):
        obs = _obs(items=[{"pos": (10, 10), "glyph": "*", "type": const.GOLD, "slot": "a"}])
        risk = strategy.assess(obs)
        act, _ = strategy.decide(obs, risk, IdentifyMemo(), [])
        self.assertEqual(act.type, "pickup")

    def test_items_before_rest(self):
        # 減HPでも可視アイテムがあれば拾得を優先（敵なし）
        obs = _obs(hp_cur=8, hp_max=12,
                   items=[{"pos": (10, 13), "glyph": "*", "type": const.GOLD, "slot": "a"}])
        risk = strategy.assess(obs)
        act, _ = strategy.decide(obs, risk, IdentifyMemo(), [])
        self.assertIn(act.type, ("move", "run"))

    def test_items_before_descend(self):
        # HP満タン・階段可視でもアイテムを優先
        obs = _obs(pos=(5, 5), stairs=(5, 8),
                   items=[{"pos": (5, 3), "glyph": "?", "type": const.SCROL, "slot": "a"}])
        risk = strategy.assess(obs)
        act, _ = strategy.decide(obs, risk, IdentifyMemo(), [])
        self.assertEqual(act.type, "move")

    def test_descend_when_on_stairs(self):
        obs = _obs(pos=(5, 5), stairs=(5, 5))
        risk = strategy.assess(obs)
        # should_descendはHP満タンで真。BFSはNone（同位）のためdescend
        act, _ = strategy.decide(obs, risk, IdentifyMemo(), [])
        self.assertEqual(act.type, "descend")

    def test_stuck_detection(self):
        hist = [(10, 10), (10, 11)] * 5
        self.assertTrue(strategy.detect_stuck(hist))
        self.assertFalse(strategy.detect_stuck([(i, i) for i in range(10)]))

    def test_bfs_unreachable(self):
        def tile_fn(r, c):
            return None
        self.assertIsNone(strategy.bfs_next_step(tile_fn, (10, 10), {(12, 12)}))

    def test_legal_moves(self):
        obs = _obs()
        # 全周FLOORなので8方向
        self.assertEqual(len(strategy.legal_moves(obs)), 8)
        # 右を壁にする
        obs._tile_cache[(10, 11)] = const.VERTWALL
        moves = strategy.legal_moves(obs)
        self.assertNotIn("l", moves)
        self.assertIn("h", moves)

    def test_legal_moves_diagonal_door(self):
        # 斜め先がFLOORでもドア角・空虚角は不可（本体_can_move準拠）
        obs = _obs()
        obs._tile_cache[(9, 9)] = const.DOOR
        moves = strategy.legal_moves(obs)
        self.assertNotIn("y", moves)
        self.assertIn("h", moves)

    def test_route_hint_stairs(self):
        obs = _obs(pos=(10, 10), stairs=(10, 13))
        d, target = strategy.route_hint(obs)
        self.assertEqual(target, "stairs")
        self.assertEqual(d, "l")

    def test_route_hint_door(self):
        # 階段なし→到達可能な扉へ
        obs = _obs(pos=(10, 10), stairs=None)
        obs._tile_cache[(10, 12)] = const.DOOR
        obs.visible_doors = [(10, 12)]
        d, target = strategy.route_hint(obs)
        self.assertEqual(target, "door")
        self.assertEqual(d, "l")

    def _tunnel_obs(self, pos=(10, 10)):
        # 全壁に通路1本（横方向）の盤面
        obs = _obs(pos=pos)
        for k in list(obs._tile_cache.keys()):
            obs._tile_cache[k] = const.VERTWALL
        for c in range(5, 16):
            obs._tile_cache[(10, c)] = const.TUNNEL
        return obs

    def test_corridor_straight(self):
        obs = self._tunnel_obs()
        self.assertEqual(strategy.corridor_step(obs, "l"), "l")

    def test_corridor_turn(self):
        # 直進が壁、右（南）のみ開通→右へ（東向きの右手は南）
        obs = self._tunnel_obs()
        obs._tile_cache[(10, 11)] = const.VERTWALL
        obs._tile_cache[(11, 10)] = const.TUNNEL
        self.assertEqual(strategy.corridor_step(obs, "l"), "j")

    def test_corridor_junction_left(self):
        # 左右とも開通→左手法で左へ（引き返さない）
        obs = self._tunnel_obs()
        obs._tile_cache[(11, 10)] = const.TUNNEL
        obs._tile_cache[(9, 10)] = const.TUNNEL
        obs._tile_cache[(10, 11)] = const.VERTWALL
        self.assertEqual(strategy.corridor_step(obs, "l"), "k")

    def test_corridor_not_on_tunnel(self):
        obs = _obs()  # FLOOR上
        self.assertIsNone(strategy.corridor_step(obs, "l"))
        self.assertIsNone(strategy.corridor_step(obs, None))

    def test_corridor_on_door(self):
        # 扉マス上でも直進継続（部屋への逆戻り防止）
        obs = self._tunnel_obs()
        obs._tile_cache[(10, 10)] = const.DOOR | const.TUNNEL
        self.assertEqual(strategy.corridor_step(obs, "l"), "l")

    def test_travel_action_run(self):
        # 長い直線路＋遠方目標→run
        obs = self._tunnel_obs(pos=(10, 6))
        act = strategy.travel_action(obs, "l", (10, 14))
        self.assertEqual(act.type, "run")
        # 近距離→move
        act = strategy.travel_action(obs, "l", (10, 7))
        self.assertEqual(act.type, "move")
        # 壁で塞がれた方向→move
        obs._tile_cache[(10, 7)] = const.VERTWALL
        act = strategy.travel_action(obs, "l", (10, 14))
        self.assertEqual(act.type, "move")

    def test_oscillating(self):
        self.assertFalse(strategy.oscillating([(1, 1), (2, 2)]))
        self.assertTrue(strategy.oscillating([(12, 50), (12, 38)] * 3))
        self.assertFalse(strategy.oscillating([(1, 1), (1, 2), (1, 3), (1, 4)]))

    def test_run_sealed_when_oscillating(self):
        # 往復中はrun封印→1歩移動で扉踏破へ
        obs = self._tunnel_obs(pos=(10, 6))
        act = strategy.travel_action(obs, "l", (10, 14), allow_run=False)
        self.assertEqual(act.type, "move")
        hist = [(10, 6), (10, 14)] * 3
        risk = strategy.assess(obs)
        obs.stairs_pos = (10, 14)
        obs.unopened_doors = []
        obs.visible_items = []
        act, _ = strategy.decide(obs, risk, IdentifyMemo(), hist, memory=None)
        self.assertEqual(act.type, "move")

    def test_exploration_memory(self):
        from ai.schemas import AIObservation
        mem = strategy.ExplorationMemory()
        obs = _obs(pos=(10, 10))
        obs.all_doors = [(10, 12), (15, 15)]
        mem.update(obs)
        self.assertEqual(sorted(mem.unopened(obs)), [(10, 12), (15, 15)])
        # 扉を踏んだら開封済み
        obs2 = _obs(pos=(10, 12))
        obs2.all_doors = [(10, 12), (15, 15)]
        mem.update(obs2)
        self.assertEqual(mem.unopened(obs2), [(15, 15)])
        # 階層変化でリセット
        obs3 = _obs(pos=(5, 5))
        obs3.status.level = 99
        obs3.all_doors = [(5, 6)]
        mem.update(obs3)
        self.assertEqual(mem.unopened(obs3), [(5, 6)])

    def test_unopened_visible_only(self):
        # 降下判断は表示中の扉のみが対象
        mem = strategy.ExplorationMemory()
        obs = _obs(pos=(10, 10))
        obs.all_doors = [(10, 12), (30, 30)]
        obs.visible_doors = [(10, 12)]
        mem.update(obs)
        self.assertEqual(mem.unopened_visible(obs), [(10, 12)])
        self.assertEqual(sorted(mem.unopened(obs)), [(10, 12), (30, 30)])

    def test_unopened_door_before_descend(self):
        # HP満タン・階段上でも未開扉があれば扉へ
        obs = _obs(pos=(5, 5), stairs=(5, 5))
        obs.all_doors = [(5, 8)]
        obs.unopened_doors = [(5, 8)]
        risk = strategy.assess(obs)
        act, _ = strategy.decide(obs, risk, IdentifyMemo(), [])
        self.assertIn(act.type, ("move", "run"))

    def test_stairs_suppressed_with_unopened(self):
        # 減HP（瀕死でない）＋未開扉→階段へ向かわない
        obs = _obs(pos=(5, 5), stairs=(5, 5), hp_cur=8, hp_max=12)
        obs.all_doors = [(5, 1)]
        obs.unopened_doors = [(5, 1)]
        risk = strategy.assess(obs)
        act, _ = strategy.decide(obs, risk, IdentifyMemo(), [])
        self.assertNotEqual(act.type, "descend")

    def test_stairs_when_dying(self):
        # 瀕死（HP15%未満）＋回復不能＋未開扉→階段へ退避する
        obs = _obs(pos=(5, 5), stairs=(5, 5), hp_cur=1, hp_max=12,
                   flags={"blind": True})
        obs.all_doors = [(5, 1)]
        obs.unopened_doors = [(5, 1)]
        risk = strategy.assess(obs)
        self.assertTrue(strategy.is_dying(obs))
        act, _ = strategy.decide(obs, risk, IdentifyMemo(), [])
        self.assertEqual(act.type, "descend")

    def test_is_dying(self):
        self.assertTrue(strategy.is_dying(_obs(hp_cur=1, hp_max=12)))
        self.assertTrue(strategy.is_dying(_obs(moves_left=100)))
        self.assertFalse(strategy.is_dying(_obs(hp_cur=8, hp_max=12, moves_left=1000)))

    def test_fight_correction(self):
        obs = _obs(pos=(17, 60),
                   monsters=[{"pos": (16, 60), "glyph": "E", "flags": 0},
                             {"pos": (17, 53), "glyph": "E", "flags": 0}])
        adj = strategy.adjacent_enemy_dirs(obs)
        self.assertEqual(adj, {"k": "E"})
        self.assertEqual(strategy.fight_correction(obs, "k"), "k")
        self.assertEqual(strategy.fight_correction(obs, "h"), "k")
        obs2 = _obs(pos=(10, 10))
        self.assertIsNone(strategy.fight_correction(obs2, "h"))

    def _deadend_obs(self, pos=(10, 10)):
        # 行き止まり通路：周囲は壁、自マスのみTUNNEL
        obs = _obs(pos=pos)
        for k in list(obs._tile_cache.keys()):
            obs._tile_cache[k] = const.VERTWALL
        obs._tile_cache[pos] = const.TUNNEL
        return obs

    def test_deadend_search_budget(self):
        from ai.schemas import AIAction
        mem = strategy.ExplorationMemory()
        obs = self._deadend_obs()
        for i in range(10):
            act = mem.deadend_action(obs, "l")
            self.assertIsNotNone(act)
            self.assertEqual(act.type, "search")
        # 11手目は打ち切り
        self.assertIsNone(mem.deadend_action(obs, "l"))
        self.assertIn((10, 10), mem.deadends)

    def test_deadend_skipped_when_enemy(self):
        mem = strategy.ExplorationMemory()
        obs = self._deadend_obs()
        obs.visible_monsters = [{"pos": (10, 11), "glyph": "K", "flags": 0}]
        self.assertIsNone(mem.deadend_action(obs, "l"))

    def test_deadend_skipped_when_passable(self):
        mem = strategy.ExplorationMemory()
        obs = self._tunnel_obs()
        self.assertIsNone(mem.deadend_action(obs, "l"))

    def test_deadend_only_back_option_searches(self):
        # 引き返し以外の選択肢がなければ探索（10手後に向き直し）
        mem = strategy.ExplorationMemory()
        obs = self._deadend_obs()
        obs._tile_cache[(10, 11)] = const.TUNNEL  # 東のみ開通
        act = mem.deadend_action(obs, "h")  # 向きは西のまま
        self.assertIsNotNone(act)
        self.assertEqual(act.type, "search")

    def test_deadend_skipped_when_fresh_option(self):
        # 引き返し以外の選択肢が2つ以上あれば行き止まりではない
        mem = strategy.ExplorationMemory()
        obs = self._deadend_obs()
        obs._tile_cache[(10, 11)] = const.TUNNEL
        obs._tile_cache[(9, 10)] = const.TUNNEL
        self.assertIsNone(mem.deadend_action(obs, "h"))


if __name__ == "__main__":
    unittest.main()

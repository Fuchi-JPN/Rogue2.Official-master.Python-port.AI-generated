"""
observer.py - 内部状態 → AIObservation の組み立て（設計書 §3）

画面パースは行わない。本体オブジェクト（Player / DungeonLevel /
GameState / Message）を直接参照する。
 game（Gameインスタンス）への依存はダックタイピングとし、
テスト時は各コンポーネントを直接渡せるようにする。
"""
try:
    from .. import const
except ImportError:
    import const

try:
    from .schemas import AIObservation, AIStatus
except ImportError:
    from schemas import AIObservation, AIStatus


def _get_gamestate():
    try:
        from ..game_state import GameState
    except ImportError:
        try:
            from game_state import GameState
        except ImportError:
            return None
    return GameState


def _tile_glyph(tile: int, item_glyph=None, mon_glyph=None) -> str:
    """タイル→表示文字（Display.get_dungeon_charと同規則の近似）"""
    if mon_glyph:
        return mon_glyph
    if tile & const.STAIRS:
        return "%"
    if item_glyph:
        return item_glyph
    if tile & const.TRAP and not (tile & const.HIDDEN):
        return "^"
    if tile & const.DOOR:
        return "+"
    if tile & const.TUNNEL:
        return "#"
    if tile & const.FLOOR:
        return "."
    if tile & const.HORWALL:
        return "-"
    if tile & const.VERTWALL:
        return "|"
    return " "


def _iter_pack(player) -> list:
    items = []
    obj = getattr(player, "pack", None)
    while obj is not None:
        items.append(obj)
        obj = getattr(obj, "next_object", None)
    return items


def _slot_of(obj) -> str:
    ich = getattr(obj, "ichar", 0)
    if isinstance(ich, int):
        try:
            return chr(ich)
        except (ValueError, OverflowError):
            return "?"
    return str(ich) if ich else "?"


def _item_glyph(item_type: int) -> str:
    mapping = {
        const.SCROL: "?", const.POTION: "!", const.GOLD: "*",
        const.FOOD: ":", const.WAND: "/", const.ARMOR: "]",
        const.WEAPON: ")", const.RING: "=", const.AMULET: ",",
    }
    return mapping.get(item_type, "~")


_KNOWN_GLYPHS = set("?!*:]/)=,^%#+.-|@")


def _ground_glyph(obj) -> str:
    """地上表示文字。描画（ichar直書き）との不一致に備え実物を優先する"""
    ich = getattr(obj, "ichar", 0)
    if isinstance(ich, int):
        try:
            ch = chr(ich)
        except (ValueError, OverflowError):
            ch = ""
    else:
        ch = str(ich) if ich else ""
    if ch in _KNOWN_GLYPHS:
        return ch
    return _item_glyph(int(getattr(obj, "item_type", 0) or 0))


def _mon_glyph(mon) -> str:
    for attr in ("m_char", "ichar"):
        v = getattr(mon, attr, None)
        if isinstance(v, int) and 65 <= v <= 90:
            return chr(v)
        if isinstance(v, str) and len(v) == 1:
            return v
    name = getattr(mon, "name", None)
    if isinstance(name, str) and name:
        return name[0].upper()
    return "M"


def _armor_class(player) -> int:
    try:
        return player.get_armor_class()
    except Exception:
        return 0


def _objects_at(dungeon) -> dict:
    """(row, col) -> item の辞書（level_objects連結リスト走査）"""
    out = {}
    obj = getattr(dungeon, "level_objects", None)
    while obj is not None:
        try:
            out[(obj.row, obj.col)] = obj
        except AttributeError:
            pass
        obj = getattr(obj, "next_object", None)
    return out


def _monsters(dungeon) -> list:
    mons = list(getattr(dungeon, "monsters", None) or [])
    # level_monsters連結リスト側も拾う（重複排除はpos+id基準）
    seen = {(getattr(m, "row", None), getattr(m, "col", None)) for m in mons}
    cur = getattr(dungeon, "level_monsters", None)
    while cur is not None:
        pos = (getattr(cur, "row", None), getattr(cur, "col", None))
        if pos not in seen and pos != (None, None):
            mons.append(cur)
            seen.add(pos)
        cur = getattr(cur, "next_object", None)
    return mons


def build_observation(player, dungeon, turn: int = 0,
                      message_text=None, mode: str = "normal",
                      view_radius: int = 10) -> AIObservation:
    """コンポーネントから観測を組み立てる（テスト容易な正本）"""
    gs = _get_gamestate()

    st = AIStatus(
        level=getattr(dungeon, "level", 1),
        gold=getattr(player, "gold", 0),
        hp_cur=getattr(player, "hp_current", 0),
        hp_max=getattr(player, "hp_max", 1),
        str_cur=getattr(player, "str_current", 0),
        str_max=getattr(player, "str_max", 0),
        armor_class=_armor_class(player),
        exp_level=getattr(player, "exp", 1),
        exp_points=getattr(player, "exp_points", 0),
        moves_left=getattr(player, "moves_left", 0),
        hunger=str(getattr(gs, "hunger_str", "") if gs else ""),
    )

    pr, pc = getattr(player, "row", 0), getattr(player, "col", 0)
    rmax = const.ROGUE_LINES
    cmax = const.ROGUE_COLUMNS

    objmap = _objects_at(dungeon)
    mons = _monsters(dungeon)
    monmap = {}
    for m in mons:
        try:
            monmap[(m.row, m.col)] = m
        except AttributeError:
            continue

    # タイルキャッシュ（strategyのBFS・退路計算用）
    tile_cache = {}
    for r in range(const.MIN_ROW, rmax - 1):
        for c in range(cmax):
            try:
                tile_cache[(r, c)] = dungeon.get_tile(r, c)
            except Exception:
                pass

    visible_monsters = []
    for (mr, mc), m in monmap.items():
        if max(abs(mr - pr), abs(mc - pc)) <= view_radius:
            visible_monsters.append({
                "pos": (mr, mc),
                "glyph": _mon_glyph(m),
                "flags": int(getattr(m, "m_flags", 0) or 0),
            })

    visible_items = []
    for (ir, ic), it in objmap.items():
        if max(abs(ir - pr), abs(ic - pc)) <= view_radius:
            itp = int(getattr(it, "item_type", 0) or 0)
            visible_items.append({
                "pos": (ir, ic),
                "glyph": _ground_glyph(it),
                "type": itp,
                "slot": _slot_of(it),
            })

    stairs_pos = None
    best = None
    for (r, c), t in tile_cache.items():
        if t & const.STAIRS:
            d = max(abs(r - pr), abs(c - pc))
            if best is None or d < best:
                best = d
                stairs_pos = (r, c)

    visible_doors = []
    for (r, c), t in tile_cache.items():
        if t & const.DOOR and max(abs(r - pr), abs(c - pc)) <= view_radius:
            visible_doors.append((r, c))

    # 階層全体の扉（未開扉判定用。踏破記憶と突合する）
    all_doors = sorted((r, c) for (r, c), t in tile_cache.items() if t & const.DOOR)

    # 局所ビュー
    local_view = []
    for r in range(pr - view_radius, pr + view_radius + 1):
        row_chars = []
        for c in range(pc - view_radius, pc + view_radius + 1):
            if (r, c) == (pr, pc):
                row_chars.append("@")
                continue
            t = tile_cache.get((r, c))
            if t is None:
                row_chars.append(" ")
                continue
            m = monmap.get((r, c))
            it = objmap.get((r, c))
            row_chars.append(_tile_glyph(
                t,
                item_glyph=_item_glyph(int(getattr(it, "item_type", 0) or 0)) if it else None,
                mon_glyph=_mon_glyph(m) if m else None,
            ))
        local_view.append("".join(row_chars))

    try:
        room_id = dungeon.get_room_number(pr, pc)
    except Exception:
        room_id = const.PASSAGE

    flags = {}
    if gs is not None:
        for k in ("blind", "halluc", "confused", "levitate", "haste_self",
                  "being_held", "bear_trap", "see_invisible", "detect_monster"):
            try:
                flags[k] = getattr(gs, k)
            except Exception:
                pass

    inv = []
    for it in _iter_pack(player):
        itp = int(getattr(it, "item_type", 0) or 0)
        fl = int(getattr(it, "in_use_flags", 0) or 0)
        equip = []
        if fl & const.BEING_WIELDED:
            equip.append("wielded")
        if fl & const.BEING_WORN:
            equip.append("worn")
        if fl & const.ON_EITHER_HAND:
            equip.append("ring")
        inv.append({
            "slot": _slot_of(it),
            "type": itp,
            "kind": int(getattr(it, "which_kind", 0) or 0),
            "qty": int(getattr(it, "quantity", 1) or 1),
            "equip": equip,
        })

    obs = AIObservation(
        turn=turn,
        player_pos=(pr, pc),
        status=st,
        local_view=local_view,
        room_id=room_id,
        visible_monsters=visible_monsters,
        visible_items=visible_items,
        stairs_pos=stairs_pos,
        message=message_text,
        mode=mode,
        flags=flags,
        inventory_summary=inv,
    )
    obs.visible_doors = visible_doors
    obs.all_doors = all_doors
    obs.unopened_doors = []  # policies側のExplorationMemoryが設定する
    obs._tile_cache = tile_cache
    obs._grid_size = (rmax, cmax)
    return obs


def build_from_game(game, turn: int = 0, with_screen: bool = True) -> AIObservation:
    """Gameインスタンスから観測を組み立てる（本番経路）"""
    player = game.player
    try:
        dungeon = game.dungeon_manager.get_current_level()
    except Exception:
        dungeon = None
    msg = None
    try:
        if getattr(game, "message", None) is not None:
            msg = game.message.msg_line or None
    except Exception:
        pass
    if dungeon is None:
        obs = AIObservation(turn=turn, mode="unknown")
        return obs
    obs = build_observation(player, dungeon, turn=turn, message_text=msg)
    if with_screen:
        try:
            display = getattr(game, "display", None)
            if display is not None:
                obs.raw_screen = display.dump_screen()
        except Exception:
            pass
    return obs

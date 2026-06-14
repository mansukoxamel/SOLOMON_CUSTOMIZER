"""Non-fatal checks shown before user-initiated ROM saves."""

from . import constants as c
from . import solomon_seal_stage
from .element import Wall


def _stage_label(index: int) -> str:
    return f"Stage {index + 1}"


def _pos_label(pos) -> str:
    try:
        x, y = pos
        return f"({int(x)}, {int(y)})"
    except Exception:
        return str(pos)


def _in_bounds(pos) -> bool:
    try:
        x, y = pos
    except Exception:
        return False
    return 0 <= int(x) < c.LEVEL_W and 0 <= int(y) < c.LEVEL_H


def _tile(level, pos):
    if not _in_bounds(pos):
        return None
    x, y = pos
    return level.tiles[int(y)][int(x)]


def _item_positions(level) -> set:
    return {tuple(getattr(item, "position", (-99, -99))) for item in getattr(level, "items", []) or []}


def _enemy_positions(level) -> list:
    return [tuple(getattr(enemy, "position", (-99, -99))) for enemy in getattr(level, "enemies", []) or []]


SHRINE_ITEM_MIN = 0x1C
SHRINE_ITEM_MAX = 0x1F
OPEN_DOOR_ITEM_NO = 0x07


def _expected_shrine_item_no(stage_no: int) -> int:
    return SHRINE_ITEM_MIN + (((stage_no // 4) - 1) % 4)


def _has_open_door_item(level) -> bool:
    return any(
        int(item.get_item_no()) == OPEN_DOOR_ITEM_NO
        for item in (getattr(level, "items", []) or [])
    )


def _has_scheduled_mirror(mirror) -> bool:
    sched = list(getattr(mirror, "schedule_data", []) or [])
    codes = list(getattr(mirror, "enemy_codes", []) or [])
    return (
        int(getattr(mirror, "schedule_no", 0) or 0) != 0
        or int(getattr(mirror, "monster_set_no", 0) or 0) != 0
        or any(int(v) != 0 for v in sched)
        or any(int(v) != 0 for v in codes)
    )


def _mirror_has_enemy_source(mirror) -> bool:
    codes = list(getattr(mirror, "enemy_codes", []) or [])
    return int(getattr(mirror, "monster_set_no", 0) or 0) != 0 or any(int(v) != 0 for v in codes)


def _collect_constellation_warnings(rom, levels: list) -> list[str]:
    warnings = []
    if not getattr(rom, "is_expanded", lambda: False)():
        return warnings
    missing = []
    mismatched = []
    for stage_no in range(4, min(len(levels), 48) + 1, 4):
        level = levels[stage_no - 1]
        expected_no = _expected_shrine_item_no(stage_no)
        shrine_items = [
            item for item in (getattr(level, "items", []) or [])
            if SHRINE_ITEM_MIN <= int(item.get_item_no()) <= SHRINE_ITEM_MAX
        ]
        if not shrine_items:
            missing.append(stage_no)
            continue
        actual_nos = sorted({int(item.get_item_no()) for item in shrine_items})
        if expected_no not in actual_nos:
            actual_names = ", ".join(f"Shrine #{no - SHRINE_ITEM_MIN + 1}" for no in actual_nos)
            expected_name = f"Shrine #{expected_no - SHRINE_ITEM_MIN + 1}"
            mismatched.append(f"Stage {stage_no} {actual_names}->{expected_name}")
    if missing:
        stages = ", ".join(str(v) for v in missing)
        warnings.append(f"星座パネル: 4の倍数面に星座パネルがありません ({stages})。")
    if mismatched:
        details = ", ".join(mismatched[:8])
        if len(mismatched) > 8:
            details += f", ...ほか {len(mismatched) - 8} 件"
        warnings.append(f"星座パネル: 対応星座と異なる面があります ({details})。")
    return warnings


def _collect_solomon_seal_warnings(rom, level_meta_items) -> list[str]:
    warnings = []
    if not getattr(rom, "is_expanded", lambda: False)():
        return warnings
    try:
        stages = solomon_seal_stage.current_stages(rom.data, rom.base_region())
        solomon_seal_stage.validate_stages(stages)
    except Exception as e:
        warnings.append(f"ソロモンの封印 出現面: {e}")
        stages = []
    if stages:
        if stages[3] > 20:
            warnings.append("ソロモンの封印: 4個目までが20面までに配置されていません。")
        if stages[5] > 44:
            warnings.append("ソロモンの封印: 6個目までが44面までに配置されていません。")
        if stages[7] > 48:
            warnings.append("ソロモンの封印: 8個目までが48面までに配置されていません。")

    if level_meta_items is not None:
        seal_items = [
            mi for mi in (level_meta_items or [])
            if 0 <= int(getattr(mi, "no", -1)) <= 7
        ]
        if len(seal_items) != 8:
            warnings.append(f"ソロモンの封印: 位置メタ情報が8個ではありません ({len(seal_items)}個)。")
    return warnings


def _seal_can_overlap_tile(level, pos) -> bool:
    wall = _tile(level, pos)
    if wall is None:
        return False
    pos = tuple(pos)
    if wall == Wall.NONE:
        return pos not in getattr(level, "invisible_solid_cells", set())
    if wall == Wall.BROWN:
        return (
            pos not in getattr(level, "passable_brown_cells", set())
            and pos not in getattr(level, "solid_brown_cells", set())
        )
    if wall == Wall.WHITE:
        return pos in getattr(level, "breakable_white_cells", set())
    if wall == Wall.BROWN_WHITE:
        return True
    return False


def _collect_level_meta_warnings(levels: list, level_meta_items) -> list[str]:
    warnings = []
    for mi in level_meta_items or []:
        no = int(getattr(mi, "no", -1))
        if not (0 <= no <= 7):
            continue
        level_no = int(getattr(mi, "level_no", -1))
        pos = tuple(getattr(mi, "position", (-99, -99)))
        if not (0 <= level_no < len(levels)):
            warnings.append(f"ソロモンの封印{no + 1}: ステージ番号が範囲外です。")
            continue
        level = levels[level_no]
        if not _in_bounds(pos):
            warnings.append(f"Stage {level_no + 1}: ソロモンの封印{no + 1}の位置が画面外です {_pos_label(pos)}。")
            continue
        if not _seal_can_overlap_tile(level, pos):
            warnings.append(f"Stage {level_no + 1}: ソロモンの封印{no + 1}が置けないブロック上にあります {_pos_label(pos)}。")
        if not level.is_door_removed() and tuple(level.fixed_door_pos) == pos:
            warnings.append(f"Stage {level_no + 1}: ソロモンの封印{no + 1}が扉と重なっています {_pos_label(pos)}。")
    return warnings


def _collect_special_block_warnings(level, stage_index: int) -> list[str]:
    warnings = []
    label = _stage_label(stage_index)
    expectations = [
        ("壊せる白ブロック", "breakable_white_cells", Wall.WHITE),
        ("すり抜ける白ブロック", "passable_white_cells", Wall.WHITE),
        ("すり抜ける茶色ブロック", "passable_brown_cells", Wall.BROWN),
        ("壊せない茶色ブロック", "solid_brown_cells", Wall.BROWN),
        ("壊せる透明ブロック", "invisible_breakable_cells", Wall.NONE),
        ("壊せない透明ブロック", "invisible_solid_cells", Wall.NONE),
    ]
    for name, attr, expected_wall in expectations:
        for pos in sorted(getattr(level, attr, set()) or []):
            if not _in_bounds(pos):
                warnings.append(f"{label}: {name}マーカーが画面外です {_pos_label(pos)}。")
                continue
            if _tile(level, pos) != expected_wall:
                warnings.append(f"{label}: {name}マーカーと実ブロックが一致していません {_pos_label(pos)}。")
    for pos in sorted(getattr(level, "visible_in_block_item_cells", set()) or []):
        if not _in_bounds(pos):
            warnings.append(f"{label}: 透明ブロック内アイテムマーカーが画面外です {_pos_label(pos)}。")
            continue
        if _tile(level, pos) != Wall.NONE:
            warnings.append(f"{label}: 透明ブロック内アイテムが空気以外のブロック上にあります {_pos_label(pos)}。")
        has_item = pos in _item_positions(level)
        has_key = (not level.is_key_removed()) and tuple(level.fixed_key_pos) == tuple(pos)
        if not has_item and not has_key:
            warnings.append(f"{label}: 透明ブロック内アイテムマーカー位置にアイテム/鍵がありません {_pos_label(pos)}。")
    return warnings


def _collect_level_warnings(level, stage_index: int) -> list[str]:
    from . import room_flags

    warnings = []
    label = _stage_label(stage_index)
    item_positions = _item_positions(level)
    enemy_positions = _enemy_positions(level)
    has_open_door_item = _has_open_door_item(level)

    if not _in_bounds(level.fixed_start_pos):
        warnings.append(f"{label}: 開始位置が画面外です {_pos_label(level.fixed_start_pos)}。")
    elif _tile(level, level.fixed_start_pos) not in (Wall.NONE,):
        warnings.append(f"{label}: 開始位置が空気以外のブロック上にあります {_pos_label(level.fixed_start_pos)}。")
    if tuple(level.fixed_start_pos) in enemy_positions:
        warnings.append(f"{label}: 開始位置に敵が重なっています {_pos_label(level.fixed_start_pos)}。")

    check_required_meta = stage_index < 48
    if level.is_key_removed():
        if check_required_meta and not has_open_door_item:
            warnings.append(f"{label}: 鍵が配置されていません。")
    elif not _in_bounds(level.fixed_key_pos):
        warnings.append(f"{label}: 鍵位置が画面外です {_pos_label(level.fixed_key_pos)}。")
    else:
        key_pos = tuple(level.fixed_key_pos)
        key_wall = _tile(level, key_pos)
        if key_pos in item_positions:
            warnings.append(f"{label}: 鍵とアイテムが重なっています {_pos_label(key_pos)}。")
        if not level.is_key_hidden() and not level.is_key_in_block() and not level.is_key_white_in_block():
            if key_wall != Wall.NONE:
                warnings.append(f"{label}: 通常鍵が空気以外のブロック上にあります {_pos_label(key_pos)}。")

    if level.is_door_removed():
        if check_required_meta and not has_open_door_item:
            warnings.append(f"{label}: 扉が配置されていません。")
    elif not _in_bounds(level.fixed_door_pos):
        warnings.append(f"{label}: 扉位置が画面外です {_pos_label(level.fixed_door_pos)}。")
    else:
        door_state = int(getattr(level, "room_flags", 0)) & room_flags.DOOR_STATE_MASK
        door_pos = tuple(level.fixed_door_pos)
        door_wall = _tile(level, door_pos)
        if door_pos in item_positions:
            warnings.append(f"{label}: 扉とアイテムが重なっています {_pos_label(door_pos)}。")
        if door_state == room_flags.DOOR_STATE_NORMAL and door_wall != Wall.NONE:
            warnings.append(f"{label}: 通常扉が空気以外のブロック上にあります {_pos_label(door_pos)}。")

    for enemy_no, pos in enumerate(enemy_positions, start=1):
        if not _in_bounds(pos):
            warnings.append(f"{label}: 敵#{enemy_no}の位置が画面外です {_pos_label(pos)}。")

    for mirror_no, mirror in enumerate(getattr(level, "demon_mirrors", []) or [], start=1):
        pos = tuple(getattr(mirror, "position", (-99, -99)))
        active = _has_scheduled_mirror(mirror)
        if active and not _in_bounds(pos):
            warnings.append(f"{label}: ミラー{mirror_no}は出現設定がありますが位置が画面外です {_pos_label(pos)}。")

    warnings.extend(_collect_special_block_warnings(level, stage_index))
    return warnings


def collect_save_warnings(rom, levels: list, level_meta_items=None) -> list[str]:
    """Return human-readable warnings that should not hard-stop ROM saving."""
    if not rom or not levels:
        return []
    warnings = []
    if len(levels) != c.LEVEL_COUNT:
        warnings.append(f"ステージ数が想定と異なります ({len(levels)} / {c.LEVEL_COUNT})。")
    warnings.extend(_collect_constellation_warnings(rom, levels))
    warnings.extend(_collect_solomon_seal_warnings(rom, level_meta_items))
    warnings.extend(_collect_level_meta_warnings(levels, level_meta_items))
    for i, level in enumerate(levels):
        warnings.extend(_collect_level_warnings(level, i))
    return warnings

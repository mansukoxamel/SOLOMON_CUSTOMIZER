"""Apply a 15x12 four-type image grid to a stage model."""

from . import constants as c
from . import room_flags
from .element import Wall


GRID_WIDTH = 15
GRID_HEIGHT = 12
AIR = 0
BROWN = 1
WHITE = 2
CRACKED = 3
VALID_KINDS = {AIR, BROWN, WHITE, CRACKED}
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff")


def validate_grid(grid) -> bool:
    return bool(
        len(grid) == GRID_HEIGHT
        and all(len(row) == GRID_WIDTH for row in grid)
        and all(cell in VALID_KINDS for row in grid for cell in row)
    )


def apply_grid_to_level(level, grid, protected_item_predicate=None) -> list[int]:
    """Replace editable cells and return mirror numbers that must be switched off."""
    if not validate_grid(grid):
        raise ValueError("grid must be a 15x12 matrix containing only 0, 1, 2, 3")
    protected_item_predicate = protected_item_predicate or (lambda _item: False)

    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            level.tiles[y][x] = Wall.NONE
    for name in (
        "breakable_white_cells",
        "cracked_block_cells",
        "invisible_breakable_cells",
        "passable_white_cells",
        "invisible_solid_cells",
        "passable_brown_cells",
        "solid_brown_cells",
        "visible_in_block_item_cells",
    ):
        cells = getattr(level, name, set())
        setattr(level, name, {pos for pos in cells if pos[0] == 15})
    level.items = [
        item for item in level.items
        if item.position[0] == 15 or protected_item_predicate(item)
    ]
    if level.constellation is not None and level.constellation.position[0] < GRID_WIDTH:
        level.constellation = None
    level.special_item_cells = {
        pos for pos in getattr(level, "special_item_cells", set()) or set()
        if pos[0] == 15
    }
    level.enemies = [enemy for enemy in level.enemies if enemy.position[0] == 15]

    start_pos = tuple(level.fixed_start_pos)
    key_pos = None if level.is_key_removed() else tuple(level.fixed_key_pos)
    door_pos = None if level.is_door_removed() else tuple(level.fixed_door_pos)
    protected_positions = {
        tuple(item.position) for item in level.items if protected_item_predicate(item)
    }
    mirror_by_pos = {}
    for mirror_no, mirror in enumerate(level.demon_mirrors):
        mirror_by_pos.setdefault(tuple(mirror.position), []).append(mirror_no)
    mirrors_to_disable = set()

    for y, row in enumerate(grid):
        for x, kind in enumerate(row):
            pos = (x, y)
            if pos == start_pos or pos in protected_positions:
                continue
            if pos == key_pos:
                level.key_status = {
                    AIR: c.KEY_STATUS_NORMAL,
                    BROWN: c.KEY_STATUS_IN_BLOCK,
                    WHITE: c.KEY_STATUS_WHITE_IN_BLOCK,
                    CRACKED: c.KEY_STATUS_HIDDEN,
                }[kind]
                if kind == CRACKED:
                    level.set_block(Wall.BROWN, pos)
                    level.cracked_block_cells.add(pos)
                continue
            if pos == door_pos:
                door_state = {
                    AIR: room_flags.DOOR_STATE_NORMAL,
                    BROWN: room_flags.DOOR_STATE_IN_BLOCK,
                    WHITE: room_flags.DOOR_STATE_WHITE_IN_BLOCK,
                    CRACKED: room_flags.DOOR_STATE_NORMAL,
                }[kind]
                level.room_flags = (
                    level.room_flags & ~room_flags.DOOR_STATE_MASK
                ) | door_state
                continue
            if kind == BROWN:
                level.set_block(Wall.BROWN, pos)
            elif kind == WHITE:
                level.set_block(Wall.WHITE, pos)
            elif kind == CRACKED:
                level.set_block(Wall.BROWN, pos)
                level.cracked_block_cells.add(pos)
            if kind != AIR:
                mirrors_to_disable.update(mirror_by_pos.get(pos, ()))

    return sorted(mirrors_to_disable)

"""拡張ROM (mapper 66) 用解析 - C++ Rom_expander.cpp の m66 名前空間を移植

拡張ROMは1レベル=256バイト固定でデータが格納される
"""
from . import constants as c
from .element import (
    LevelElement, ElementType, Wall, DemonMirror,
    position_from_byte, byte_from_position
)
from .level import Level


# M66 定数（C++ Rom_expander.h より）
COUNT_M66_LEVELS = 53
LENGTH_M66_LVL_DATA = 256
LENGTH_M66_LVL_W = 16
LENGTH_M66_LVL_H = 12
OFFSET_M66_LVL_DATA = 49168
OFFSET_M66_DROP_SCHED_DATA = OFFSET_M66_LVL_DATA + COUNT_M66_LEVELS * LENGTH_M66_LVL_DATA
LENGTH_M66_MAP_DATA = LENGTH_M66_LVL_W * LENGTH_M66_LVL_H  # 192
LENGTH_M66_BREAKABLE_WHITE_ROOM_DATA = 32
LENGTH_M66_VISIBLE_IN_BLOCK_ITEM_ROOM_DATA = LENGTH_M66_BREAKABLE_WHITE_ROOM_DATA
LENGTH_M66_VISIBLE_IN_BLOCK_ITEM_MASK_BYTES = 24
BREAKABLE_CELL_MODE_EMPTY = 0xFE
BREAKABLE_CELL_MODE_SOLID = 0xFD
CELL_EMPTY = 0x10
CELL_BROWN = 0x90
CELL_WHITE = 0xF8
CELL_INVISIBLE_SOLID = 0x40
CELL_INVISIBLE_BREAKABLE = 0x50
CELL_BREAKABLE_WHITE = 0xF9
CELL_PASSABLE_WHITE = 0xFA
CELL_PASSABLE_BROWN = 0xA3
CELL_SOLID_BROWN = 0xA4
CELL_WHITE_IN_BLOCK_KEY = c.ITEM_FLAG_WHITE_IN_BLOCK | 0x06
OFFSET_M66_LOADER_A2 = 32784
RUNTIME_BLOCK_LIST_RAM = 0x0740
SPECIAL_HIGH_ID_PRESERVE_PATCH_OFF = OFFSET_M66_LOADER_A2 + 31
SPECIAL_HIGH_ID_PRESERVE_OLD = 0xF0  # BEQ: only $F8 survives the m66 loader.
SPECIAL_HIGH_ID_PRESERVE_NEW = 0xB0  # BCS: threshold-$FF survive for special IDs.
SPECIAL_HIGH_ID_THRESHOLD_PATCH_OFF = OFFSET_M66_LOADER_A2 + 30
SPECIAL_HIGH_ID_THRESHOLD_OLD = 0xF8
SPECIAL_HIGH_ID_THRESHOLD_NEW = 0xC0
RUNTIME_BLOCK_LIST_COPY_PATCH_OFF = OFFSET_M66_LOADER_A2 + 146
RUNTIME_BLOCK_LIST_COPY_PATCH_OLD = bytes.fromhex(
    "ad28040a0a0a0a18694f8500ad28044a4a4a4a1869f88501a010b100995f0788d0f8"
)
RUNTIME_BLOCK_LIST_COPY_PATCH_NEW = bytes.fromhex(
    "ad28040a0a0a0a0a18694f8500ad28044a4a4a1869f88501a020b100993f0788d0f8"
)
RUNTIME_BLOCK_LIST_COPY_PATCH_DISABLED = bytes([0xEA] * len(RUNTIME_BLOCK_LIST_COPY_PATCH_NEW))
RUNTIME_VISIBLE_IN_BLOCK_ITEM_MASK_COPY_PATCH_OLD = bytes.fromhex(
    "ad28040a0a0a0a0a18694f8500ad28044a4a4a1869f88501a018b100994f0788d0f8"
)
RESPAWN_DIRECT_CELL_COPY_PATCH_OFF = OFFSET_M66_LOADER_A2 + 22
RESPAWN_DIRECT_CELL_COPY_OLD = bytes.fromhex("a57c")
RESPAWN_DIRECT_CELL_COPY_NEW = bytes.fromhex("d020")
VISIBLE_IN_BLOCK_MASK_COPY_HELPER_OFF = 0x8E80
VISIBLE_IN_BLOCK_MASK_COPY_HELPER_CPU = 0x8E70
VISIBLE_IN_BLOCK_MASK_COPY_HELPER = bytes.fromhex(
    "ad28040a0a0a0a0a18694f8500a90069008501ad28044a4a4a18650169f88501"
    "a018b100994f0788d0f860"
)
RUNTIME_VISIBLE_IN_BLOCK_ITEM_MASK_COPY_PATCH = (
    bytes((
        0x20,
        VISIBLE_IN_BLOCK_MASK_COPY_HELPER_CPU & 0xFF,
        VISIBLE_IN_BLOCK_MASK_COPY_HELPER_CPU >> 8,
    ))
    + bytes([0xEA] * (len(RUNTIME_VISIBLE_IN_BLOCK_ITEM_MASK_COPY_PATCH_OLD) - 3))
)
RUNTIME_VISIBLE_IN_BLOCK_ITEM_MASK_COPY_PATCH_LEN = len(RUNTIME_VISIBLE_IN_BLOCK_ITEM_MASK_COPY_PATCH)
M66_LOADER_TAIL_OFF = 0x80C4
M66_LOADER_TAIL_HOOK = bytes.fromhex("4c008a")
M66_LOADER_TAIL_GUARD_OFF = 0x80C7
M66_LOADER_TAIL_GUARD = bytes([0x00] * 9)
VISIBLE_IN_BLOCK_RESERVED_SPANS = ((VISIBLE_IN_BLOCK_MASK_COPY_HELPER_OFF, len(VISIBLE_IN_BLOCK_MASK_COPY_HELPER)),)
assert RUNTIME_VISIBLE_IN_BLOCK_ITEM_MASK_COPY_PATCH_LEN == 34
assert len(VISIBLE_IN_BLOCK_MASK_COPY_HELPER) == 43
INITIAL_DRAW_WHITE_THRESHOLD_PATCH_OFF = 0x10 + (0x9617 - 0x8000)
INITIAL_DRAW_WHITE_THRESHOLD_OLD = 0xF8
INITIAL_DRAW_WHITE_THRESHOLD_NEW = 0xC0
KEY_CELL_VALUE_PATCH_OFF = 0x17F5
KEY_CELL_VALUE_PATCH_OLD = bytes.fromhex("a90624001002a9465002a9869d0403")
KEY_CELL_VALUE_PATCH_NEW = bytes.fromhex("a5000a29809002094009069d0403ea")
OFFSET_M66_BREAKABLE_WHITE_DATA = (
    OFFSET_M66_DROP_SCHED_DATA
    + COUNT_M66_LEVELS * 2 * 8
)

OFFSET_M66_LOCAL_META = LENGTH_M66_MAP_DATA  # 192
OFFSET_M66_KEY_STATUS = OFFSET_M66_LOCAL_META + 4  # 196
OFFSET_M66_DOOR_POS = OFFSET_M66_KEY_STATUS + 1  # 197
OFFSET_M66_KEY_POS = OFFSET_M66_DOOR_POS + 1  # 198
OFFSET_M66_PLAYER_START_POS = OFFSET_M66_KEY_POS + 1  # 199
OFFSET_M66_SPAWN01_POS = OFFSET_M66_PLAYER_START_POS + 1  # 200
OFFSET_M66_SPAWN02_POS = OFFSET_M66_SPAWN01_POS + 1  # 201
OFFSET_M66_ITEM_DELIMITER = OFFSET_M66_SPAWN02_POS + 1  # 202
OFFSET_M66_CONSTELLATION_POS = OFFSET_M66_ITEM_DELIMITER + 1  # 203

OFFSET_M66_LOCAL_ENEMY_DATA = 208
LENGTH_M66_ENEMY_DATA = 1 + 15 * 2 + 1  # 32
LENGTH_M66_ENEMY_SET_DATA = 8
OFFSET_M66_LOCAL_SCHED_ENEMY_1_DATA = 240
OFFSET_M66_LOCAL_SCHED_ENEMY_2_DATA = OFFSET_M66_LOCAL_SCHED_ENEMY_1_DATA + LENGTH_M66_ENEMY_SET_DATA  # 248


def is_mirror_visible(level: Level, mirror_no: int) -> bool:
    """ミラーが可視かどうか（拡張ROM用）"""
    pos = level.demon_mirrors[mirror_no].position
    if pos[0] >= c.LEVEL_W or pos[1] < 0 or pos[1] >= c.LEVEL_H:
        return False
    return True


def parse_level(rom_data: bytes, level_no: int) -> Level:
    """拡張ROM形式でレベルデータを解析"""
    result = Level()
    offset = OFFSET_M66_LVL_DATA + LENGTH_M66_LVL_DATA * level_no

    # メタデータ
    result.set_key_status_and_time_dr(rom_data[offset + OFFSET_M66_KEY_STATUS])
    result.fixed_door_pos = position_from_byte(rom_data[offset + OFFSET_M66_DOOR_POS])
    result.fixed_key_pos = position_from_byte(rom_data[offset + OFFSET_M66_KEY_POS])
    result.fixed_start_pos = position_from_byte(rom_data[offset + OFFSET_M66_PLAYER_START_POS])

    # ミラー位置（spawn01 が index 1、spawn02 が index 0、C++ と同じ順）
    spawn02_pos = position_from_byte(rom_data[offset + OFFSET_M66_SPAWN02_POS])
    spawn01_pos = position_from_byte(rom_data[offset + OFFSET_M66_SPAWN01_POS])

    # tileset 取得
    item_delimiter = rom_data[offset + OFFSET_M66_ITEM_DELIMITER]
    result.tileset_no = (item_delimiter >> 2) & 3

    # 星座背景
    if item_delimiter >= c.ITEM_CONSTELLATION_MIN:
        const_pos = position_from_byte(rom_data[offset + OFFSET_M66_CONSTELLATION_POS])
        result.constellation = LevelElement(ElementType.ITEM, const_pos, item_delimiter)

    # マップ（ブロックとアイテムが混在配置）
    result.tiles = [[Wall.NONE for _ in range(c.LEVEL_W)] for _ in range(c.LEVEL_H)]
    result.items = []

    for j in range(LENGTH_M66_LVL_H):
        for i in range(LENGTH_M66_LVL_W):
            value = rom_data[offset + j * LENGTH_M66_LVL_W + i]
            pos = (i, j)
            is_mirror_pos = (pos == spawn01_pos or pos == spawn02_pos)

            if value == CELL_WHITE:
                result.tiles[j][i] = Wall.WHITE
            elif value == CELL_BROWN:
                result.tiles[j][i] = Wall.BROWN
            elif value == CELL_BREAKABLE_WHITE:
                result.tiles[j][i] = Wall.WHITE
                result.breakable_white_cells.add(pos)
            elif value == CELL_WHITE_IN_BLOCK_KEY:
                result.fixed_key_pos = pos
                result.key_status = c.KEY_STATUS_WHITE_IN_BLOCK
            elif (c.ITEM_WHITE_IN_BLOCK_MIN <= value <= c.ITEM_WHITE_IN_BLOCK_MAX and
                  not (pos == result.fixed_key_pos and result.key_status == c.KEY_STATUS_WHITE_IN_BLOCK)):
                result.items.append(LevelElement(ElementType.ITEM, pos, value))
            elif pos == result.fixed_key_pos and result.key_status == c.KEY_STATUS_WHITE_IN_BLOCK:
                pass
            elif value == CELL_PASSABLE_WHITE:
                result.tiles[j][i] = Wall.WHITE
                result.passable_white_cells.add(pos)
            elif value == CELL_PASSABLE_BROWN:
                result.tiles[j][i] = Wall.BROWN
                result.passable_brown_cells.add(pos)
            elif value == CELL_SOLID_BROWN:
                result.tiles[j][i] = Wall.BROWN
                result.solid_brown_cells.add(pos)
            elif value == CELL_INVISIBLE_SOLID:
                result.invisible_solid_cells.add(pos)
            elif value == CELL_INVISIBLE_BREAKABLE:
                result.invisible_breakable_cells.add(pos)
            elif value != CELL_EMPTY or is_mirror_pos:
                result.items.append(LevelElement(ElementType.ITEM, pos, value))

    # ミラー設定
    result.demon_mirrors = [
        DemonMirror(spawn02_pos, 0, 0),
        DemonMirror(spawn01_pos, 0, 0),
    ]

    # 敵データ
    enemy_offset = offset + OFFSET_M66_LOCAL_ENEMY_DATA
    l = rom_data[enemy_offset]
    result.spawn_enemy_lifetime = ((l & 31) << 3) | (l >> 5)
    i = 1
    result.enemies = []
    while True:
        enemy_no = rom_data[enemy_offset + i]
        if enemy_no == 0:
            break
        if i + 1 >= LENGTH_M66_ENEMY_DATA:
            break
        pos = position_from_byte(rom_data[enemy_offset + i + 1])
        result.enemies.append(LevelElement(ElementType.ENEMY, pos, enemy_no))
        i += 2

    # 「ミラー位置のアイテム表示」のクリーンアップ
    # 0x05（DEMON_MIRROR）アイテムがミラー位置にある場合は除外
    cleanup_mirror_items(result)

    return result


def cleanup_mirror_items(level: Level):
    """ミラー位置に重複している DEMON_MIRROR アイテムを除去"""
    items = []
    mirror_positions = [m.position for m in level.demon_mirrors]
    for item in level.items:
        if item.element_no == c.ITEM_NO_DEMON_MIRROR and item.position in mirror_positions:
            continue
        items.append(item)
    level.items = items


def _visible_in_block_table_offset(level_no: int) -> int:
    return (
        OFFSET_M66_BREAKABLE_WHITE_DATA
        + level_no * LENGTH_M66_VISIBLE_IN_BLOCK_ITEM_ROOM_DATA
    )


def _visible_in_block_cell_index(pos) -> int | None:
    x, y = pos
    if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
        return None
    return y * c.LEVEL_W + x


def _read_visible_in_block_item_mask_cells(rom_data: bytes, level_no: int) -> set:
    cells = set()
    base = _visible_in_block_table_offset(level_no)
    end = base + LENGTH_M66_VISIBLE_IN_BLOCK_ITEM_MASK_BYTES
    if len(rom_data) < end:
        return cells
    for idx in range(LENGTH_M66_MAP_DATA):
        if rom_data[base + (idx >> 3)] & (1 << (idx & 0x07)):
            cells.add((idx % c.LEVEL_W, idx // c.LEVEL_W))
    return cells


def read_visible_in_block_item_data(rom_data: bytes, count: int = COUNT_M66_LEVELS) -> list:
    return [
        _read_visible_in_block_item_mask_cells(rom_data, room_no)
        for room_no in range(max(0, min(int(count), COUNT_M66_LEVELS)))
    ]


def load_all_levels_m66(rom) -> list:
    """拡張ROMから全レベル読込"""
    levels = []
    for i in range(COUNT_M66_LEVELS):
        levels.append(parse_level(bytes(rom.data), i))
    rom_bytes = bytes(rom.data)
    from . import room_flags
    try:
        from . import stage_ext
        runtime_room_flags = stage_ext.read_runtime_room_flags(rom_bytes, len(levels))
    except Exception:
        runtime_room_flags = [0] * len(levels)
    visible_cells = read_visible_in_block_item_data(rom_bytes, len(levels))
    for i, cells in enumerate(visible_cells):
        if not (
            i < len(runtime_room_flags)
            and (runtime_room_flags[i] & room_flags.BIT_VISIBLE_INBLOCK_ITEMS)
        ):
            continue
        item_positions = {item.position for item in levels[i].items}
        levels[i].visible_in_block_item_cells = {
            pos for pos in cells
            if pos in item_positions
        }
    try:
        from . import room_flags
        flags = room_flags.read_table(bytes(rom.data), len(levels))
        for i, fl in enumerate(flags):
            levels[i].room_flags = fl
    except Exception:
        # Room Flag は拡張機能。読めないROMでもレベル本体の読込は止めない。
        pass
    try:
        from . import stage_ext
        stage_ext.read_table(bytes(rom.data), levels)
    except Exception:
        pass
    try:
        from . import panel_monster_stage_variant
        panel_monster_stage_variant.read_table(bytes(rom.data), levels)
    except Exception:
        pass
    return levels


def is_mirror_visible_m66(level, mirror_no: int) -> bool:
    """ミラーが画面内に存在するか（拡張ROM保存判定用）"""
    pos = level.demon_mirrors[mirror_no].position
    if pos[0] >= c.LEVEL_W or pos[0] < 0:
        return False
    if pos[1] < 0 or pos[1] >= c.LEVEL_H:
        return False
    return True


def save_level_m66(rom_data: bytearray, level_no: int, level):
    """1レベル分を拡張ROM形式で書き戻し（C++ patch_item_data_bytes 移植）

    書き換え対象:
    - マップデータ（ブロック+アイテム） @ +0..+191
    - メタデータヘッダ @ +192..+207
    - 敵データ @ +208..+239 (32バイト)

    維持される（書き換えない）:
    - 敵セット1 @ +240..+247 (ユーザー編集UI未対応のため)
    - 敵セット2 @ +248..+255 (同上)
    """
    offset = OFFSET_M66_LVL_DATA + LENGTH_M66_LVL_DATA * level_no

    def set_block(pos: tuple, value: int):
        x, y = pos
        if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
            rom_data[offset + y * c.LEVEL_W + x] = value & 0xff

    # マップデータ（先頭192バイト）
    for y in range(c.LEVEL_H):
        for x in range(c.LEVEL_W):
            wall = level.tiles[y][x]
            if wall.name == "BROWN":
                value = CELL_BROWN
            elif wall.name == "WHITE" or wall.name == "BROWN_WHITE":
                value = CELL_WHITE
            else:
                value = CELL_EMPTY  # 空白
            set_block((x, y), value)

    # 特殊ブロックは m66 セル値へ直接内包する。見た目はこの値で描かせ、
    # プレイ開始後の runtime が $0304 上で挙動値へ変換する。
    for pos in sorted(getattr(level, "breakable_white_cells", set()) or []):
        set_block(pos, CELL_BREAKABLE_WHITE)
    for pos in sorted(getattr(level, "passable_white_cells", set()) or []):
        set_block(pos, CELL_PASSABLE_WHITE)
    for pos in sorted(getattr(level, "invisible_solid_cells", set()) or []):
        set_block(pos, CELL_INVISIBLE_SOLID)
    for pos in sorted(getattr(level, "invisible_breakable_cells", set()) or []):
        set_block(pos, CELL_INVISIBLE_BREAKABLE)
    for pos in sorted(getattr(level, "passable_brown_cells", set()) or []):
        set_block(pos, CELL_PASSABLE_BROWN)
    for pos in sorted(getattr(level, "solid_brown_cells", set()) or []):
        set_block(pos, CELL_SOLID_BROWN)

    # ミラー位置にブロックもアイテムもなければミラーマーカー(0x05)を配置
    # ブロックやアイテムで意図的に隠されたミラーは上書きしない
    item_positions = {item.position for item in level.items}
    for m in range(2):
        if is_mirror_visible_m66(level, m):
            mx, my = level.demon_mirrors[m].position
            has_block = level.tiles[my][mx] != Wall.NONE
            has_item = (mx, my) in item_positions
            if not has_block and not has_item:
                set_block((mx, my), c.ITEM_NO_DEMON_MIRROR)

    # アイテム配置（ブロックを上書き）
    for item in level.items:
        set_block(item.position, item.element_no)

    if (getattr(level, "key_status", c.KEY_STATUS_NORMAL) == c.KEY_STATUS_WHITE_IN_BLOCK and
            not level.is_key_removed()):
        set_block(level.fixed_key_pos, CELL_WHITE_IN_BLOCK_KEY)

    # メタデータヘッダ
    rom_data[offset + OFFSET_M66_LOCAL_META + 0] = 0
    rom_data[offset + OFFSET_M66_LOCAL_META + 1] = 1
    rom_data[offset + OFFSET_M66_LOCAL_META + 2] = 0
    rom_data[offset + OFFSET_M66_LOCAL_META + 3] = 1

    key_status = level.key_status
    if key_status == c.KEY_STATUS_WHITE_IN_BLOCK:
        key_status = c.KEY_STATUS_WHITE_IN_BLOCK
    rom_data[offset + OFFSET_M66_KEY_STATUS] = (key_status + level.time_decrease_rate) & 0xff
    rom_data[offset + OFFSET_M66_DOOR_POS] = byte_from_position(level.fixed_door_pos)
    rom_data[offset + OFFSET_M66_KEY_POS] = byte_from_position(level.fixed_key_pos)
    rom_data[offset + OFFSET_M66_PLAYER_START_POS] = byte_from_position(level.fixed_start_pos)

    # ミラー位置（C++と同じく1番目=spawn01、2番目=spawn02、index 1がspawn01）
    rom_data[offset + OFFSET_M66_SPAWN01_POS] = byte_from_position(level.demon_mirrors[1].position)
    rom_data[offset + OFFSET_M66_SPAWN02_POS] = byte_from_position(level.demon_mirrors[0].position)

    # 星座 or tileset 終端
    if level.has_constellation():
        rom_data[offset + OFFSET_M66_ITEM_DELIMITER] = level.get_constellation_no()
        rom_data[offset + OFFSET_M66_CONSTELLATION_POS] = byte_from_position(level.get_constellation_pos())
    else:
        rom_data[offset + OFFSET_M66_ITEM_DELIMITER] = c.ITEM_DELIMITER_MIN + 4 * level.tileset_no

    # 敵データ（C++と同じく必要な分だけ書く、空き領域は維持）
    enemy_offset = offset + OFFSET_M66_LOCAL_ENEMY_DATA
    enemy_bytes = level.get_enemy_bytes()
    if len(enemy_bytes) > LENGTH_M66_ENEMY_DATA:
        raise ValueError(f"Too many enemies in level {level_no + 1}: {len(enemy_bytes)} > {LENGTH_M66_ENEMY_DATA}")
    for i, b in enumerate(enemy_bytes):
        rom_data[enemy_offset + i] = b


def save_all_levels_m66(rom, levels: list):
    """拡張ROM全レベルを書き戻し"""
    validate_visible_in_block_items(levels)
    for i, level in enumerate(levels):
        save_level_m66(rom.data, i, level)
    from . import stage_ext
    stage_ext.patch_table(rom.data, levels)
    patch_breakable_white_data(rom.data, levels)


def visible_in_block_items_needed(levels: list) -> bool:
    return any(bool(getattr(level, "visible_in_block_item_cells", set()) or []) for level in levels or [])


def validate_visible_in_block_items(levels: list) -> None:
    for room_no, level in enumerate(levels or []):
        cells = set(getattr(level, "visible_in_block_item_cells", set()) or [])
        if not cells:
            continue
        item_by_pos = {item.position: item for item in getattr(level, "items", []) or []}
        for pos in sorted(cells):
            if _visible_in_block_cell_index(pos) is None:
                raise ValueError(
                    f"Stage {room_no + 1}: 透明ブロック内マーカー {pos} が範囲外です"
                )
            item = item_by_pos.get(pos)
            if item is None:
                raise ValueError(
                    f"Stage {room_no + 1}: 透明ブロック内マーカー {pos} にアイテムがありません"
                )
            base = int(item.element_no) & 0x3F
            if base > c.ITEM_WHITE_IN_BLOCK_MAX_BASE:
                raise ValueError(
                    f"Stage {room_no + 1}: item 0x{base:02X} at {pos} cannot be "
                    "透明ブロック内アイテムとして保存できません"
                )
            if int(item.element_no) & 0xC0:
                raise ValueError(
                    f"Stage {room_no + 1}: 透明ブロック内アイテム {pos} は "
                    "通常アイテムとマーカーの組み合わせで保存してください"
                )


def build_breakable_white_data(levels: list) -> bytearray:
    """Build the reused PRG1 runtime side-list area.

    特殊ブロックは v0.7.72 から m66 ステージセル値へ直接保存するため、
    旧32B/room tableは通常使わない。各room slotの先頭24Bだけ、
    通常アイテムとして初期描画した後に白ブロック内アイテムへ差し替える
    192セルbitmaskとして再利用する。
    """
    data = bytearray([0x00] * (COUNT_M66_LEVELS * LENGTH_M66_BREAKABLE_WHITE_ROOM_DATA))
    for room_no, level in enumerate((levels or [])[:COUNT_M66_LEVELS]):
        cells = sorted(getattr(level, "visible_in_block_item_cells", set()) or [])
        base = _visible_in_block_table_offset(room_no) - OFFSET_M66_BREAKABLE_WHITE_DATA
        for pos in cells:
            idx = _visible_in_block_cell_index(pos)
            if idx is not None:
                data[base + (idx >> 3)] |= 1 << (idx & 0x07)
    return data


def patch_breakable_white_data(rom_data: bytearray, levels: list):
    data = build_breakable_white_data(levels)
    end = OFFSET_M66_BREAKABLE_WHITE_DATA + len(data)
    if len(rom_data) < end:
        return
    patch_runtime_block_loader(rom_data)
    rom_data[OFFSET_M66_BREAKABLE_WHITE_DATA:end] = data


def patch_runtime_block_loader(rom_data: bytearray):
    """Patch mapper66 l_a2 for direct special cell IDs.

    - Preserve $C0-$FF in the room grid so $C0-$F7 white in-block cells and
      $F9/$FA can survive to the runtime.
    - $A3/$A4 use the existing in-block item path and survive without this
      high-ID preservation branch.
    - Reuse the old PRG1 side-list copy to fill $0750-$0767 with the visible
      in-block item bitmask for the current room.
    - Treat initial room cells $C0-$FF as the white-wall draw class. This lets
      $C0-$F7 act as white breakable blocks with an item inside, while the
      existing break test still keeps $F8-$FF solid.
    - Bypass the original $7C bit0 respawn-only high-cell normalization. The
      mapper66 format already stores a full direct 192-cell room grid; applying
      the packed-stream one-shot rule on respawn turns high-ID in-block items
      into plain blocks or empty cells.
    """
    off = RESPAWN_DIRECT_CELL_COPY_PATCH_OFF
    ln = len(RESPAWN_DIRECT_CELL_COPY_NEW)
    if len(rom_data) >= off + ln:
        cur = bytes(rom_data[off:off + ln])
        if cur == RESPAWN_DIRECT_CELL_COPY_OLD:
            rom_data[off:off + ln] = RESPAWN_DIRECT_CELL_COPY_NEW
    off = SPECIAL_HIGH_ID_THRESHOLD_PATCH_OFF
    if len(rom_data) > off and rom_data[off] == SPECIAL_HIGH_ID_THRESHOLD_OLD:
        rom_data[off] = SPECIAL_HIGH_ID_THRESHOLD_NEW
    off = INITIAL_DRAW_WHITE_THRESHOLD_PATCH_OFF
    if len(rom_data) > off and rom_data[off] == INITIAL_DRAW_WHITE_THRESHOLD_OLD:
        rom_data[off] = INITIAL_DRAW_WHITE_THRESHOLD_NEW
    off = KEY_CELL_VALUE_PATCH_OFF
    ln = len(KEY_CELL_VALUE_PATCH_NEW)
    if len(rom_data) >= off + ln:
        cur = bytes(rom_data[off:off + ln])
        if cur == KEY_CELL_VALUE_PATCH_OLD:
            rom_data[off:off + ln] = KEY_CELL_VALUE_PATCH_NEW
    off = SPECIAL_HIGH_ID_PRESERVE_PATCH_OFF
    if len(rom_data) > off and rom_data[off] == SPECIAL_HIGH_ID_PRESERVE_OLD:
        rom_data[off] = SPECIAL_HIGH_ID_PRESERVE_NEW
    off = RUNTIME_BLOCK_LIST_COPY_PATCH_OFF
    ln = RUNTIME_VISIBLE_IN_BLOCK_ITEM_MASK_COPY_PATCH_LEN
    if len(rom_data) < off + ln:
        return
    cur = bytes(rom_data[off:off + ln])
    old_variants = (
        RUNTIME_BLOCK_LIST_COPY_PATCH_OLD,
        RUNTIME_BLOCK_LIST_COPY_PATCH_NEW,
        RUNTIME_BLOCK_LIST_COPY_PATCH_DISABLED,
        RUNTIME_VISIBLE_IN_BLOCK_ITEM_MASK_COPY_PATCH_OLD,
    )
    if cur in old_variants:
        rom_data[off:off + ln] = RUNTIME_VISIBLE_IN_BLOCK_ITEM_MASK_COPY_PATCH
    elif cur != RUNTIME_VISIBLE_IN_BLOCK_ITEM_MASK_COPY_PATCH:
        return
    helper_end = VISIBLE_IN_BLOCK_MASK_COPY_HELPER_OFF + len(VISIBLE_IN_BLOCK_MASK_COPY_HELPER)
    if len(rom_data) >= helper_end:
        cur_helper = bytes(rom_data[VISIBLE_IN_BLOCK_MASK_COPY_HELPER_OFF:helper_end])
        if cur_helper != VISIBLE_IN_BLOCK_MASK_COPY_HELPER:
            rom_data[VISIBLE_IN_BLOCK_MASK_COPY_HELPER_OFF:helper_end] = VISIBLE_IN_BLOCK_MASK_COPY_HELPER
    tail_end = M66_LOADER_TAIL_OFF + len(M66_LOADER_TAIL_HOOK)
    if len(rom_data) >= tail_end:
        rom_data[M66_LOADER_TAIL_OFF:tail_end] = M66_LOADER_TAIL_HOOK
    guard_end = M66_LOADER_TAIL_GUARD_OFF + len(M66_LOADER_TAIL_GUARD)
    if len(rom_data) >= guard_end:
        rom_data[M66_LOADER_TAIL_GUARD_OFF:guard_end] = M66_LOADER_TAIL_GUARD


def read_breakable_white_data(rom_data: bytes) -> list:
    result = [
        {"breakable": set(), "empty": set(), "solid": set()}
        for _ in range(COUNT_M66_LEVELS)
    ]
    end = OFFSET_M66_BREAKABLE_WHITE_DATA + COUNT_M66_LEVELS * LENGTH_M66_BREAKABLE_WHITE_ROOM_DATA
    if len(rom_data) < end:
        return result
    for room_no in range(COUNT_M66_LEVELS):
        base = OFFSET_M66_BREAKABLE_WHITE_DATA + room_no * LENGTH_M66_BREAKABLE_WHITE_ROOM_DATA
        mode = "breakable"
        for i in range(LENGTH_M66_BREAKABLE_WHITE_ROOM_DATA):
            v = rom_data[base + i]
            if v == 0xFF:
                break
            if v == BREAKABLE_CELL_MODE_EMPTY:
                mode = "empty"
                continue
            if v == BREAKABLE_CELL_MODE_SOLID:
                mode = "solid"
                continue
            x = v & 0x0F
            editor_y = (v >> 4) - 1
            if 0 <= x < c.LEVEL_W and 0 <= editor_y < c.LEVEL_H:
                result[room_no][mode].add((x, editor_y))
    return result

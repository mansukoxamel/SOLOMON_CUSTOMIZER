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
OFFSET_M66_LOADER_A2 = 32784
RUNTIME_BLOCK_LIST_RAM = 0x0740
SPECIAL_HIGH_ID_PRESERVE_PATCH_OFF = OFFSET_M66_LOADER_A2 + 31
SPECIAL_HIGH_ID_PRESERVE_OLD = 0xF0  # BEQ: only $F8 survives the m66 loader.
SPECIAL_HIGH_ID_PRESERVE_NEW = 0xB0  # BCS: $F8-$FF survive for special IDs.
RUNTIME_BLOCK_LIST_COPY_PATCH_OFF = OFFSET_M66_LOADER_A2 + 146
RUNTIME_BLOCK_LIST_COPY_PATCH_OLD = bytes.fromhex(
    "ad28040a0a0a0a18694f8500ad28044a4a4a4a1869f88501a010b100995f0788d0f8"
)
RUNTIME_BLOCK_LIST_COPY_PATCH_NEW = bytes.fromhex(
    "ad28040a0a0a0a0a18694f8500ad28044a4a4a1869f88501a020b100993f0788d0f8"
)
RUNTIME_BLOCK_LIST_COPY_PATCH_DISABLED = bytes([0xEA] * len(RUNTIME_BLOCK_LIST_COPY_PATCH_NEW))
INITIAL_DRAW_WHITE_THRESHOLD_PATCH_OFF = 0x10 + (0x9617 - 0x8000)
INITIAL_DRAW_WHITE_THRESHOLD_OLD = 0xF8
INITIAL_DRAW_WHITE_THRESHOLD_NEW = 0xC0
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
            elif c.ITEM_WHITE_IN_BLOCK_MIN <= value <= c.ITEM_WHITE_IN_BLOCK_MAX:
                result.tiles[j][i] = Wall.WHITE
                result.breakable_white_cells.add(pos)
                result.items.append(LevelElement(ElementType.ITEM, pos, value))
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


def load_all_levels_m66(rom) -> list:
    """拡張ROMから全レベル読込"""
    levels = []
    for i in range(COUNT_M66_LEVELS):
        levels.append(parse_level(bytes(rom.data), i))
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

    # メタデータヘッダ
    rom_data[offset + OFFSET_M66_LOCAL_META + 0] = 0
    rom_data[offset + OFFSET_M66_LOCAL_META + 1] = 1
    rom_data[offset + OFFSET_M66_LOCAL_META + 2] = 0
    rom_data[offset + OFFSET_M66_LOCAL_META + 3] = 1

    rom_data[offset + OFFSET_M66_KEY_STATUS] = (level.key_status + level.time_decrease_rate) & 0xff
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
    for i, level in enumerate(levels):
        save_level_m66(rom.data, i, level)
    from . import stage_ext
    stage_ext.patch_table(rom.data, levels)
    patch_breakable_white_data(rom.data, levels)


def _breakable_white_runtime_cell(pos) -> int | None:
    x, y = pos
    if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
        return None
    runtime_y = min(15, y + 1)
    return ((runtime_y << 4) | x) & 0xFF


def build_breakable_white_data(levels: list) -> bytearray:
    """旧PRG1 side-list領域を空にする。

    特殊ブロックは v0.7.72 から m66 ステージセル値へ直接保存するため、
    部屋ごとの32B runtime listは使わない。
    """
    data = bytearray([0xFF] * (COUNT_M66_LEVELS * LENGTH_M66_BREAKABLE_WHITE_ROOM_DATA))
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

    - Preserve $F8-$FF in the room grid so $F9/$FA can survive to the runtime.
    - $A3/$A4 use the existing in-block item path and survive without this
      high-ID preservation branch.
    - Disable the old 32B PRG1-to-$0740 copy; the runtime now scans $0304.
    - Treat initial room cells $C0-$FF as the white-wall draw class. This lets
      $C0-$F7 act as white breakable blocks with an item inside, while the
      existing break test still keeps $F8-$FF solid.
    """
    off = INITIAL_DRAW_WHITE_THRESHOLD_PATCH_OFF
    if len(rom_data) > off and rom_data[off] == INITIAL_DRAW_WHITE_THRESHOLD_OLD:
        rom_data[off] = INITIAL_DRAW_WHITE_THRESHOLD_NEW
    off = SPECIAL_HIGH_ID_PRESERVE_PATCH_OFF
    if len(rom_data) > off and rom_data[off] == SPECIAL_HIGH_ID_PRESERVE_OLD:
        rom_data[off] = SPECIAL_HIGH_ID_PRESERVE_NEW
    off = RUNTIME_BLOCK_LIST_COPY_PATCH_OFF
    ln = len(RUNTIME_BLOCK_LIST_COPY_PATCH_DISABLED)
    if len(rom_data) < off + ln:
        return
    cur = bytes(rom_data[off:off + ln])
    if cur == RUNTIME_BLOCK_LIST_COPY_PATCH_DISABLED:
        return
    if cur in (RUNTIME_BLOCK_LIST_COPY_PATCH_OLD, RUNTIME_BLOCK_LIST_COPY_PATCH_NEW):
        rom_data[off:off + ln] = RUNTIME_BLOCK_LIST_COPY_PATCH_DISABLED


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

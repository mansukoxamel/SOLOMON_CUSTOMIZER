"""Per-stage extension settings table.

Mapper66 ROMs keep this data in PRG1 general reserve.  It is a data foundation
only; runtime code can later copy or read the fields it needs during stage load.
"""
from __future__ import annotations


ROOM_COUNT = 64
ENTRY_SIZE = 8
HEADER_SIZE = 16
TABLE_OFFSET = 0x8800
TABLE_LENGTH = HEADER_SIZE + ROOM_COUNT * ENTRY_SIZE
TABLE_END = TABLE_OFFSET + TABLE_LENGTH
MAGIC = b"MGSTGEXT"
FORMAT = 1

FLAG_FIRE_RESET = 0x01
FLAG_KEY_ENEMY = 0x02
FLAG_ANNOUNCE = 0x04

DEFAULT_KEY_ENEMY_SLOT = 0xFF

RUNTIME_ROOM_FLAGS_OFFSET = 6
RUNTIME_DOOR_CELL_OFFSET = 7
RAM_RUNTIME_DOOR_CELL = 0x077C
RUNTIME_ROOM_FLAGS_USER_MASK = 0x9F

OFF_M66_LOADER_TAIL = 0x80C4
CPU_PRG1_STAGE_EXT_COPY = 0x8A00
OFF_PRG1_STAGE_EXT_COPY = 0x8A10
PRG1_STAGE_EXT_COPY_SLOT_SIZE = 0x60
ORIG_M66_LOADER_TAIL = bytes.fromhex("60 00 00")
HOOK_M66_LOADER_TAIL = bytes((0x4C, CPU_PRG1_STAGE_EXT_COPY & 0xFF, CPU_PRG1_STAGE_EXT_COPY >> 8))


def _blank_entry() -> bytearray:
    return bytearray((
        0x00,                   # flags
        0x00,                   # fire reset count/value
        DEFAULT_KEY_ENEMY_SLOT, # enemy slot that carries the key
        0x00,                   # key enemy mode/reserved
        0x00,                   # announcement id
        0x00,                   # announcement flags
        0x00,
        0x00,
    ))


def init_level_defaults(level) -> None:
    if not hasattr(level, "stage_ext_flags"):
        level.stage_ext_flags = 0
    if not hasattr(level, "fire_reset_value"):
        level.fire_reset_value = 0
    if not hasattr(level, "key_enemy_slot"):
        level.key_enemy_slot = DEFAULT_KEY_ENEMY_SLOT
    if not hasattr(level, "key_enemy_mode"):
        level.key_enemy_mode = 0
    if not hasattr(level, "announce_id"):
        level.announce_id = 0
    if not hasattr(level, "announce_flags"):
        level.announce_flags = 0


def _level_to_entry(level, runtime_room_flags: int = 0, door_cell: int = 0) -> bytes:
    init_level_defaults(level)
    entry = _blank_entry()
    entry[0] = int(level.stage_ext_flags) & 0xFF
    entry[1] = int(level.fire_reset_value) & 0xFF
    entry[2] = int(level.key_enemy_slot) & 0xFF
    entry[3] = int(level.key_enemy_mode) & 0xFF
    entry[4] = int(level.announce_id) & 0xFF
    entry[5] = int(level.announce_flags) & 0xFF
    entry[RUNTIME_ROOM_FLAGS_OFFSET] = int(runtime_room_flags) & 0xFF
    entry[RUNTIME_DOOR_CELL_OFFSET] = int(door_cell) & 0xFF
    return bytes(entry)


def _entry_to_level(entry: bytes, level) -> None:
    init_level_defaults(level)
    if len(entry) < ENTRY_SIZE:
        return
    level.stage_ext_flags = entry[0] & 0xFF
    level.fire_reset_value = entry[1] & 0xFF
    level.key_enemy_slot = entry[2] & 0xFF
    level.key_enemy_mode = entry[3] & 0xFF
    level.announce_id = entry[4] & 0xFF
    level.announce_flags = entry[5] & 0xFF
    level.room_flags = entry[RUNTIME_ROOM_FLAGS_OFFSET] & RUNTIME_ROOM_FLAGS_USER_MASK


def build_table(levels: list, runtime_room_flags: list = None, door_cells: list = None) -> bytes:
    table = bytearray([0xFF] * TABLE_LENGTH)
    table[:len(MAGIC)] = MAGIC
    table[len(MAGIC)] = FORMAT
    table[len(MAGIC) + 1] = ENTRY_SIZE
    table[len(MAGIC) + 2] = ROOM_COUNT
    table[len(MAGIC) + 3] = 0
    runtime_room_flags = runtime_room_flags or []
    door_cells = door_cells or []
    for i, level in enumerate(levels[:ROOM_COUNT]):
        base = HEADER_SIZE + i * ENTRY_SIZE
        flags = runtime_room_flags[i] if i < len(runtime_room_flags) else 0
        door = door_cells[i] if i < len(door_cells) else 0
        table[base:base + ENTRY_SIZE] = _level_to_entry(level, flags, door)
    for i in range(len(levels), ROOM_COUNT):
        base = HEADER_SIZE + i * ENTRY_SIZE
        table[base:base + ENTRY_SIZE] = _blank_entry()
    return bytes(table)


def patch_table(rom_data: bytearray, levels: list, runtime_room_flags: list = None,
                door_cells: list = None) -> bool:
    if len(rom_data) < TABLE_END:
        return False
    table = build_table(levels, runtime_room_flags, door_cells)
    if bytes(rom_data[TABLE_OFFSET:TABLE_END]) == table:
        return False
    rom_data[TABLE_OFFSET:TABLE_END] = table
    return True


def read_runtime_room_flags(rom_data: bytes, count: int = 53) -> list:
    count = max(0, min(int(count), ROOM_COUNT))
    if len(rom_data) < TABLE_END:
        return [0] * count
    raw = bytes(rom_data[TABLE_OFFSET:TABLE_END])
    if not raw.startswith(MAGIC):
        return [0] * count
    return [
        raw[HEADER_SIZE + i * ENTRY_SIZE + RUNTIME_ROOM_FLAGS_OFFSET] & 0xFF
        for i in range(count)
    ]


def _build_runtime_loader() -> bytes:
    # Pointer starts at StageExtTable entry byte0: bank1 CPU $8800 + room*8.
    # Keep ASL carry when computing the high byte; rooms 32+ live on $89xx.
    return bytes.fromhex(
        "a9 ff 8d 2a 07 8d 2b 07"
        "a9 00 8d 23 07 8d 24 07 8d 29 07 8d 7a 07"
        "ad 28 04 0a 0a 0a 85 00"
        "a9 88 69 00 85 01"
        "a0 02 b1 00 8d 2b 07"
        "a0 06 b1 00 8d 78 07"
        "a0 07 b1 00 8d 7c 07"
        "60"
    )


RUNTIME_LOADER = _build_runtime_loader()
RUNTIME_LOADER_SLOT = (
    RUNTIME_LOADER
    + bytes([0x00] * (PRG1_STAGE_EXT_COPY_SLOT_SIZE - len(RUNTIME_LOADER)))
)


def apply_runtime_loader(rom_data: bytearray) -> list:
    if len(rom_data) < OFF_PRG1_STAGE_EXT_COPY + len(RUNTIME_LOADER_SLOT):
        return []
    cur = bytes(rom_data[OFF_M66_LOADER_TAIL:OFF_M66_LOADER_TAIL + len(ORIG_M66_LOADER_TAIL)])
    if cur not in (ORIG_M66_LOADER_TAIL, HOOK_M66_LOADER_TAIL):
        return []
    changed = []
    if bytes(rom_data[OFF_PRG1_STAGE_EXT_COPY:OFF_PRG1_STAGE_EXT_COPY + len(RUNTIME_LOADER_SLOT)]) != RUNTIME_LOADER_SLOT:
        rom_data[OFF_PRG1_STAGE_EXT_COPY:OFF_PRG1_STAGE_EXT_COPY + len(RUNTIME_LOADER_SLOT)] = RUNTIME_LOADER_SLOT
        changed.append("StageExt runtime loader")
    if cur != HOOK_M66_LOADER_TAIL:
        rom_data[OFF_M66_LOADER_TAIL:OFF_M66_LOADER_TAIL + len(HOOK_M66_LOADER_TAIL)] = HOOK_M66_LOADER_TAIL
        changed.append("mapper66 loader StageExt hook")
    return changed


def read_table(rom_data: bytes, levels: list) -> bool:
    if len(rom_data) < TABLE_END:
        return False
    raw = bytes(rom_data[TABLE_OFFSET:TABLE_END])
    if not raw.startswith(MAGIC):
        for level in levels:
            init_level_defaults(level)
        return False
    if raw[len(MAGIC)] != FORMAT or raw[len(MAGIC) + 1] != ENTRY_SIZE:
        for level in levels:
            init_level_defaults(level)
        return False
    for i, level in enumerate(levels[:ROOM_COUNT]):
        base = HEADER_SIZE + i * ENTRY_SIZE
        _entry_to_level(raw[base:base + ENTRY_SIZE], level)
    return True


def fire_reset_enabled(level) -> bool:
    init_level_defaults(level)
    return bool(int(level.stage_ext_flags) & FLAG_FIRE_RESET)


def set_fire_reset_enabled(level, enabled: bool) -> None:
    init_level_defaults(level)
    if enabled:
        level.stage_ext_flags = int(level.stage_ext_flags) | FLAG_FIRE_RESET
        level.fire_reset_value = 0
    else:
        level.stage_ext_flags = int(level.stage_ext_flags) & ~FLAG_FIRE_RESET


def key_enemy_enabled(level) -> bool:
    init_level_defaults(level)
    return bool(int(level.stage_ext_flags) & FLAG_KEY_ENEMY)


def get_key_enemy_number(level) -> int:
    init_level_defaults(level)
    if not key_enemy_enabled(level):
        return 0
    slot = int(level.key_enemy_slot) & 0xFF
    if slot == DEFAULT_KEY_ENEMY_SLOT:
        return 0
    return slot + 1


def set_key_enemy_number(level, enemy_number: int) -> None:
    init_level_defaults(level)
    enemy_number = int(enemy_number)
    if enemy_number <= 0:
        level.stage_ext_flags = int(level.stage_ext_flags) & ~FLAG_KEY_ENEMY
        level.key_enemy_slot = DEFAULT_KEY_ENEMY_SLOT
        level.key_enemy_mode = 0
        return
    level.stage_ext_flags = int(level.stage_ext_flags) | FLAG_KEY_ENEMY
    level.key_enemy_slot = max(0, min(enemy_number - 1, 0xFE))
    level.key_enemy_mode = 0

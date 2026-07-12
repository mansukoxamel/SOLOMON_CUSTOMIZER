"""Runtime patch for per-stage key/fairy initial enemies.

The UI/stage extension stores a 1-based enemy number as a zero-based slot in
StageExtTable.  Mapper66's PRG1 loader copies that per-stage value into RAM
before the room starts; the PRG0 hooks then bind it to the matching runtime
enemy slot.  Key enemies spawn a normal key tile when defeated; fairy enemies
use the original fall-death fairy replacement path.
"""
from __future__ import annotations


class KeyEnemyRuntimeError(RuntimeError):
    pass


def _cf(cpu_addr: int) -> int:
    return cpu_addr - 0x8000 + 0x10


def _word(addr: int) -> bytes:
    return bytes((addr & 0xFF, (addr >> 8) & 0xFF))


RAM_DROP_TILE_PLUS1 = 0x0723
RAM_DROP_ACTIVE = 0x0724
RAM_PICKUP_TILE = 0x0725
RAM_SAVE_30 = 0x0726
RAM_SAVE_31 = 0x0727
RAM_DROP_TILE = 0x0728
RAM_INITIAL_COUNT = 0x0729
RAM_TARGET_RUNTIME_SLOT = 0x072A
RAM_SELECTED_INITIAL_SLOT = 0x072B
RAM_FAIRY_SELECTED_INITIAL_SLOT = 0x077E
RAM_FAIRY_TARGET_RUNTIME_SLOT = 0x077F


from . import stage_ext

OFF_M66_LOADER_TAIL = stage_ext.OFF_M66_LOADER_TAIL
CPU_PRG1_STAGE_EXT_COPY = stage_ext.CPU_PRG1_STAGE_EXT_COPY
OFF_PRG1_STAGE_EXT_COPY = stage_ext.OFF_PRG1_STAGE_EXT_COPY

OFF_HOOK_ENEMY_INIT = _cf(0x95C5)
OFF_HOOK_ENEMY_STATUS = _cf(0x95CA)
OFF_HOOK_ENEMY_DEFEAT = _cf(0xC267)
OFF_HOOK_DOOR_LIGHT_POS = _cf(0xC3A8)
OFF_HOOK_ITEM_TILE_READ = _cf(0xC54E)
OFF_HOOK_KEY_HANDLER = _cf(0xC663)
OFF_HOOK_FALL_FAIRY = _cf(0xAF06)
OFF_HOOK_FLAME_DESPAWN = _cf(0xA5CB)

CPU_ENEMY_INIT = 0xE0FE
CPU_ENEMY_STATUS = 0xE118
CPU_ENEMY_STATUS_VALUE = 0xE11E
CPU_ENEMY_DEFEAT = 0xE12D
CPU_ENEMY_DEFEAT_MATCH1 = 0xE13B
CPU_ENEMY_DEFEAT_MATCH2 = 0xE14D
CPU_ENEMY_DEFEAT_MATCH3 = 0xE15C
CPU_ENEMY_DEFEAT_MATCH4 = 0xE166
CPU_ENEMY_DEFEAT_MATCH5 = 0xE171
CPU_ENEMY_DEFEAT_MATCH6 = 0xE17E
CPU_DOOR_LIGHT_POS = 0xE185
CPU_ITEM_TILE_READ = 0xE19E
CPU_KEY_HANDLER = 0xE1A5
CPU_FALL_KEY_HANDLER = 0xE1FB
CPU_FALL_KEY_COMPARE = 0xE211
CPU_FLAME_KEY_HANDLER = 0xE21C
OFF_KEY_ENEMY_FREE = _cf(0xE21C)
KEY_ENEMY_FREE_LEN = 24

OFF_ENEMY_INIT = _cf(CPU_ENEMY_INIT)
OFF_ENEMY_STATUS = _cf(CPU_ENEMY_STATUS)
OFF_ENEMY_DEFEAT = _cf(CPU_ENEMY_DEFEAT)
OFF_ENEMY_DEFEAT_MATCH1 = _cf(CPU_ENEMY_DEFEAT_MATCH1)
OFF_ENEMY_DEFEAT_MATCH2 = _cf(CPU_ENEMY_DEFEAT_MATCH2)
OFF_ENEMY_DEFEAT_MATCH3 = _cf(CPU_ENEMY_DEFEAT_MATCH3)
OFF_ENEMY_DEFEAT_MATCH4 = _cf(CPU_ENEMY_DEFEAT_MATCH4)
OFF_ENEMY_DEFEAT_MATCH5 = _cf(CPU_ENEMY_DEFEAT_MATCH5)
OFF_ENEMY_DEFEAT_MATCH6 = _cf(CPU_ENEMY_DEFEAT_MATCH6)
OFF_DOOR_LIGHT_POS = _cf(CPU_DOOR_LIGHT_POS)
OFF_ITEM_TILE_READ = _cf(CPU_ITEM_TILE_READ)
OFF_KEY_HANDLER = _cf(CPU_KEY_HANDLER)
OFF_FALL_KEY_HANDLER = _cf(CPU_FALL_KEY_HANDLER)
OFF_ENEMY_STATUS_VALUE = _cf(CPU_ENEMY_STATUS_VALUE)
OFF_FALL_KEY_COMPARE = _cf(CPU_FALL_KEY_COMPARE)
OFF_FLAME_KEY_HANDLER = _cf(CPU_FLAME_KEY_HANDLER)

ORIG_M66_LOADER_TAIL = stage_ext.ORIG_M66_LOADER_TAIL
HOOK_M66_LOADER_TAIL = stage_ext.HOOK_M66_LOADER_TAIL

ORIG_ENEMY_INIT = bytes.fromhex("20 ea b2")
HOOK_ENEMY_INIT = bytes((0x20, CPU_ENEMY_INIT & 0xFF, CPU_ENEMY_INIT >> 8))

ORIG_ENEMY_STATUS = bytes.fromhex("a9 80 91 04")
HOOK_ENEMY_STATUS = bytes((0x20, CPU_ENEMY_STATUS & 0xFF, CPU_ENEMY_STATUS >> 8, 0xEA))

ORIG_ENEMY_DEFEAT = bytes.fromhex("20 1c 9d")
HOOK_ENEMY_DEFEAT = bytes((0x20, CPU_ENEMY_DEFEAT & 0xFF, CPU_ENEMY_DEFEAT >> 8))

ORIG_DOOR_LIGHT_POS = bytes.fromhex("b1 30 85 04")
HOOK_DOOR_LIGHT_POS = bytes((0x20, CPU_DOOR_LIGHT_POS & 0xFF, CPU_DOOR_LIGHT_POS >> 8, 0xEA))

ORIG_ITEM_TILE_READ = bytes.fromhex("bd 04 03")
HOOK_ITEM_TILE_READ = bytes((0x20, CPU_ITEM_TILE_READ & 0xFF, CPU_ITEM_TILE_READ >> 8))

ORIG_KEY_HANDLER = bytes.fromhex("a0 05 b1 30 a8")
HOOK_KEY_HANDLER = bytes((0x20, CPU_KEY_HANDLER & 0xFF, CPU_KEY_HANDLER >> 8, 0xEA, 0xEA))

ORIG_FALL_FAIRY = bytes.fromhex("a0 03 b9")
HOOK_FALL_FAIRY = bytes((0x4C, CPU_FALL_KEY_HANDLER & 0xFF, CPU_FALL_KEY_HANDLER >> 8))

ORIG_FLAME_DESPAWN = bytes.fromhex("4c 76 b3")
HOOK_FLAME_DESPAWN = bytes((0x4C, CPU_FLAME_KEY_HANDLER & 0xFF, CPU_FLAME_KEY_HANDLER >> 8))


def _build_enemy_init() -> bytes:
    return bytes.fromhex(
        # Original JSR $B2EA, then bind selected initial enemy numbers to the
        # runtime slot X. RAM $072B/$077E are zero-based initial indexes.
        "20 ea b2"
        "ad 29 07"
        "cd 2b 07 d0 03"
        "8e 2a 07"
        "cd 7e 07 d0 03"
        "8e 7f 07"
        "ee 29 07"
        "60"
    )


def _build_enemy_status() -> bytes:
    return (
        bytes((0x20, CPU_ENEMY_STATUS_VALUE & 0xFF, CPU_ENEMY_STATUS_VALUE >> 8))
        + bytes.fromhex("91 04 60")
    )


def _build_enemy_status_value() -> bytes:
    return bytes.fromhex(
        # Return A=$C0 only for the selected key or fairy runtime slot.
        # The bit6 flag is consumed by the original fall-death fairy route.
        "a9 80"
        "ec 2a 07 f0 04"
        "ec 7f 07 d0 02"
        "a9 c0"
        "60"
    )


def _jmp(addr: int) -> bytes:
    return bytes((0x4C, addr & 0xFF, addr >> 8))


def _build_enemy_defeat_chunks() -> tuple[tuple[int, bytes], ...]:
    entry = bytearray.fromhex(
        "20 1c 9d"
        "ad 2a 07 c5 02 d0 03"
    )
    entry += _jmp(CPU_ENEMY_DEFEAT_MATCH1)
    entry += b"\x60"

    match1 = bytearray.fromhex(
        "a5 02 48"
        "20 4a b1"
        "a0 07 b1 00 18 69 08 85 04"
    )
    match1 += _jmp(CPU_ENEMY_DEFEAT_MATCH2)

    match2 = bytearray.fromhex(
        "a0 0a b1 00 18 69 08 85 05"
        "20 8a 91"
    )
    match2 += _jmp(CPU_ENEMY_DEFEAT_MATCH3)

    match3 = bytearray.fromhex(
        "8a 18 69 01 8d 23 07"
    )
    match3 += _jmp(CPU_ENEMY_DEFEAT_MATCH4)

    match4 = bytearray.fromhex(
        "8d 24 07 8a 85 02 a9 06"
    )
    match4 += _jmp(CPU_ENEMY_DEFEAT_MATCH5)

    match5 = bytearray.fromhex(
        "85 03 9d 04 03 20 53 9d a9 ff"
    )
    match5 += _jmp(CPU_ENEMY_DEFEAT_MATCH6)

    match6 = bytearray.fromhex(
        "8d 2a 07 68 85 02 60"
    )
    return (
        (OFF_ENEMY_DEFEAT, bytes(entry)),
        (OFF_ENEMY_DEFEAT_MATCH1, bytes(match1)),
        (OFF_ENEMY_DEFEAT_MATCH2, bytes(match2)),
        (OFF_ENEMY_DEFEAT_MATCH3, bytes(match3)),
        (OFF_ENEMY_DEFEAT_MATCH4, bytes(match4)),
        (OFF_ENEMY_DEFEAT_MATCH5, bytes(match5)),
        (OFF_ENEMY_DEFEAT_MATCH6, bytes(match6)),
    )


def _build_door_light_pos() -> bytes:
    return bytes.fromhex(
        "c0 06 d0 10 ad 24 07 f0 0b"
        "38 e9 01 85 04 a9 00 8d 24 07 60"
        "b1 30 85 04 60"
    )


def _build_item_tile_read() -> bytes:
    return bytes.fromhex("8e 25 07 bd 04 03 60")


def _build_key_handler_at(base: int) -> bytes:
    restore_orig = base + 0x36
    orig_continue = base + 0x50
    blob = bytearray.fromhex(
        "ad 23 07 f0 4b"
        "a5 30 8d 26 07 a5 31 8d 27 07"
        "ad 23 07 38 e9 01 8d 28 07 cd 25 07 f0 0e"
        "20 00 00"
        "a9 00 8d 23 07 8d 24 07"
        "4c 00 00"
        "20 00 00"
        "a9 00 8d 23 07"
        "4c 00 00"
        "ae 28 07 86 02 a9 10 85 03 9d 04 03 20 53 9d"
        "ad 26 07 85 30 ad 27 07 85 31 60"
        "a0 05 b1 30 a8 60"
    )
    for at, addr in ((0x1E, restore_orig), (0x29, orig_continue),
                     (0x2C, restore_orig), (0x34, orig_continue)):
        blob[at:at + 2] = _word(addr)
    return bytes(blob)


def _build_key_handler() -> bytes:
    return _build_key_handler_at(CPU_KEY_HANDLER)


def _build_fall_key_handler() -> bytes:
    blob = bytearray()
    blob += bytes((0x20, CPU_FALL_KEY_COMPARE & 0xFF, CPU_FALL_KEY_COMPARE >> 8))
    blob += bytes.fromhex("d0 06")
    blob += bytes((0x20, (CPU_ENEMY_DEFEAT + 3) & 0xFF, (CPU_ENEMY_DEFEAT + 3) >> 8))
    blob += bytes.fromhex("4c 76 b3")
    blob += bytes.fromhex("a0 03 b9 11 af 91 2e 88 10 f8 60")
    return bytes(blob)


def _build_fall_key_compare() -> bytes:
    return bytes.fromhex(
        # AF06 is reached from the current enemy's sub-slot pointer in $2C.
        # $02 is not reliable there, so compare the pointer-table low byte for
        # the selected key runtime slot.  The 17 sub-slot low bytes are unique.
        "ae 2a 07"
        "86 02"
        "bd 06 b3"
        "c5 2c"
        "60"
    )


def _build_flame_key_handler() -> bytes:
    return bytes.fromhex(
        # Only Red Burn $80 uses the key-drop path. Other Flame IDs keep the
        # original despawn behavior even if they reach this shared AI exit.
        "a0 01"
        "b1 2e"
        "c9 80"
        "d0 0d"
        "ae 2a 07"
        "30 08"
        "20 11 e2"
        "d0 03"
        "20 30 e1"
        "4c 76 b3"
    )


PRG1_STAGE_EXT_COPY = stage_ext.RUNTIME_LOADER
ENEMY_INIT = _build_enemy_init()
ENEMY_STATUS = _build_enemy_status()
ENEMY_STATUS_VALUE = _build_enemy_status_value()
ENEMY_DEFEAT_CHUNKS = _build_enemy_defeat_chunks()
ENEMY_DEFEAT = ENEMY_DEFEAT_CHUNKS[0][1]
DOOR_LIGHT_POS = _build_door_light_pos()
ITEM_TILE_READ = _build_item_tile_read()
KEY_HANDLER = _build_key_handler()
FALL_KEY_HANDLER = _build_fall_key_handler()
FALL_KEY_COMPARE = _build_fall_key_compare()
FLAME_KEY_HANDLER = _build_flame_key_handler()

RESERVED_SPANS = (
    (OFF_ENEMY_INIT, len(ENEMY_INIT)),
    (OFF_ENEMY_STATUS, len(ENEMY_STATUS)),
    (OFF_ENEMY_STATUS_VALUE, len(ENEMY_STATUS_VALUE)),
    *[(off, len(blob)) for off, blob in ENEMY_DEFEAT_CHUNKS],
    (OFF_DOOR_LIGHT_POS, len(DOOR_LIGHT_POS)),
    (OFF_ITEM_TILE_READ, len(ITEM_TILE_READ)),
    (OFF_KEY_HANDLER, len(KEY_HANDLER)),
    (OFF_FALL_KEY_HANDLER, len(FALL_KEY_HANDLER)),
    (OFF_FALL_KEY_COMPARE, len(FALL_KEY_COMPARE)),
    (OFF_FLAME_KEY_HANDLER, len(FLAME_KEY_HANDLER)),
)

assert OFF_KEY_ENEMY_FREE == OFF_FALL_KEY_COMPARE + len(FALL_KEY_COMPARE)
assert KEY_ENEMY_FREE_LEN == 24
assert OFF_FLAME_KEY_HANDLER == OFF_KEY_ENEMY_FREE
assert len(FLAME_KEY_HANDLER) == 24
assert len(FLAME_KEY_HANDLER) <= KEY_ENEMY_FREE_LEN


def _expect(rom_data, off: int, orig: bytes, hook: bytes, name: str, extra: tuple[bytes, ...] = ()) -> None:
    cur = bytes(rom_data[off:off + len(orig)])
    if cur == orig or cur == hook or cur in extra:
        return
    raise KeyEnemyRuntimeError(
        f"{name} signature mismatch at file 0x{off:X}: "
        f"expected {orig.hex(' ')} or {hook.hex(' ')}, got {cur.hex(' ')}"
    )


def _write(rom_data, off: int, blob: bytes, changed: list[str], name: str) -> None:
    if bytes(rom_data[off:off + len(blob)]) != blob:
        rom_data[off:off + len(blob)] = blob
        changed.append(name)


def _ensure_available(rom_data, off: int, blob: bytes, name: str) -> None:
    cur = bytes(rom_data[off:off + len(blob)])
    if cur == blob:
        return
    if all(b in (0xEA, 0x00) for b in cur):
        return
    raise KeyEnemyRuntimeError(
        f"{name} cave overlap at file 0x{off:X}: "
        f"expected empty EA/00 or existing key code, got {cur[:16].hex(' ')}..."
    )


def apply(rom_data) -> list[str]:
    if rom_data is None or len(rom_data) < OFF_FLAME_KEY_HANDLER + len(FLAME_KEY_HANDLER):
        raise KeyEnemyRuntimeError("ROM is too short for key enemy runtime patch.")

    _expect(rom_data, OFF_M66_LOADER_TAIL, ORIG_M66_LOADER_TAIL, HOOK_M66_LOADER_TAIL, "mapper66 loader tail")
    _expect(rom_data, OFF_HOOK_ENEMY_INIT, ORIG_ENEMY_INIT, HOOK_ENEMY_INIT, "$95C5 enemy init")
    _expect(rom_data, OFF_HOOK_ENEMY_STATUS, ORIG_ENEMY_STATUS, HOOK_ENEMY_STATUS, "$95CA enemy status")
    _expect(rom_data, OFF_HOOK_ENEMY_DEFEAT, ORIG_ENEMY_DEFEAT, HOOK_ENEMY_DEFEAT, "$C267 enemy defeat")
    _expect(rom_data, OFF_HOOK_DOOR_LIGHT_POS, ORIG_DOOR_LIGHT_POS, HOOK_DOOR_LIGHT_POS, "$C3A8 door-light pos")
    _expect(rom_data, OFF_HOOK_ITEM_TILE_READ, ORIG_ITEM_TILE_READ, HOOK_ITEM_TILE_READ, "$C54E item tile read")
    _expect(rom_data, OFF_HOOK_KEY_HANDLER, ORIG_KEY_HANDLER, HOOK_KEY_HANDLER, "$C663 key handler")
    _expect(rom_data, OFF_HOOK_FALL_FAIRY, ORIG_FALL_FAIRY, HOOK_FALL_FAIRY, "$AF06 fall fairy")
    _expect(rom_data, OFF_HOOK_FLAME_DESPAWN, ORIG_FLAME_DESPAWN, HOOK_FLAME_DESPAWN, "$A5CB Flame despawn")
    changed: list[str] = []
    for off, blob, name in (
        (OFF_PRG1_STAGE_EXT_COPY, PRG1_STAGE_EXT_COPY, "key enemy StageExt loader"),
        (OFF_ENEMY_INIT, ENEMY_INIT, "key enemy initial-slot binder"),
        (OFF_ENEMY_STATUS, ENEMY_STATUS, "key enemy status writer"),
        (OFF_ENEMY_STATUS_VALUE, ENEMY_STATUS_VALUE, "key/fairy enemy status value helper"),
        *[(off, blob, "key enemy defeat dropper chunk") for off, blob in ENEMY_DEFEAT_CHUNKS],
        (OFF_DOOR_LIGHT_POS, DOOR_LIGHT_POS, "key enemy door-light helper"),
        (OFF_ITEM_TILE_READ, ITEM_TILE_READ, "key enemy pickup-tile recorder"),
        (OFF_KEY_HANDLER, KEY_HANDLER, "key enemy dropped-key handler"),
        (OFF_FALL_KEY_HANDLER, FALL_KEY_HANDLER, "key enemy fall-death handler"),
        (OFF_FALL_KEY_COMPARE, FALL_KEY_COMPARE, "key enemy fall-slot compare helper"),
        (OFF_FLAME_KEY_HANDLER, FLAME_KEY_HANDLER, "Red Burn key-drop handler"),
    ):
        _ensure_available(rom_data, off, blob, name)

    _write(rom_data, OFF_PRG1_STAGE_EXT_COPY, PRG1_STAGE_EXT_COPY, changed, "key enemy StageExt loader")
    _write(rom_data, OFF_ENEMY_INIT, ENEMY_INIT, changed, "key enemy initial-slot binder")
    _write(rom_data, OFF_ENEMY_STATUS, ENEMY_STATUS, changed, "key enemy status writer")
    _write(rom_data, OFF_ENEMY_STATUS_VALUE, ENEMY_STATUS_VALUE, changed, "key/fairy enemy status value helper")
    for off, blob in ENEMY_DEFEAT_CHUNKS:
        _write(rom_data, off, blob, changed, "key enemy defeat dropper chunk")
    _write(rom_data, OFF_DOOR_LIGHT_POS, DOOR_LIGHT_POS, changed, "key enemy door-light helper")
    _write(rom_data, OFF_ITEM_TILE_READ, ITEM_TILE_READ, changed, "key enemy pickup-tile recorder")
    _write(rom_data, OFF_KEY_HANDLER, KEY_HANDLER, changed, "key enemy dropped-key handler")
    _write(rom_data, OFF_FALL_KEY_HANDLER, FALL_KEY_HANDLER, changed, "key enemy fall-death handler")
    _write(rom_data, OFF_FALL_KEY_COMPARE, FALL_KEY_COMPARE, changed, "key enemy fall-slot compare helper")
    _write(rom_data, OFF_FLAME_KEY_HANDLER, FLAME_KEY_HANDLER, changed, "Red Burn key-drop handler")
    _write(rom_data, OFF_M66_LOADER_TAIL, HOOK_M66_LOADER_TAIL, changed, "mapper66 loader key hook")
    _write(rom_data, OFF_HOOK_ENEMY_INIT, HOOK_ENEMY_INIT, changed, "$95C5 key enemy init hook")
    _write(rom_data, OFF_HOOK_ENEMY_STATUS, HOOK_ENEMY_STATUS, changed, "$95CA key enemy status hook")
    _write(rom_data, OFF_HOOK_ENEMY_DEFEAT, HOOK_ENEMY_DEFEAT, changed, "$C267 key enemy defeat hook")
    _write(rom_data, OFF_HOOK_DOOR_LIGHT_POS, HOOK_DOOR_LIGHT_POS, changed, "$C3A8 key enemy light hook")
    _write(rom_data, OFF_HOOK_ITEM_TILE_READ, HOOK_ITEM_TILE_READ, changed, "$C54E key enemy pickup hook")
    _write(rom_data, OFF_HOOK_KEY_HANDLER, HOOK_KEY_HANDLER, changed, "$C663 key enemy handler hook")
    _write(rom_data, OFF_HOOK_FALL_FAIRY, HOOK_FALL_FAIRY, changed, "$AF06 key enemy fall hook")
    _write(rom_data, OFF_HOOK_FLAME_DESPAWN, HOOK_FLAME_DESPAWN, changed, "$A5CB Red Burn key hook")
    return changed

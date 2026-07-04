"""Shared dispatch entries for new enemy IDs in mapper66 saved ROMs."""
from __future__ import annotations

from . import ice_flame_runtime as _ice


class NewEnemyRuntimeError(ValueError):
    pass


ICE_FLAME_ID = _ice.NEW_ENEMY_ID

OFF_AI_ENTRY = 0x3BF2      # CPU $BBE2
OFF_SETUP_ENTRY = 0x3C12   # CPU $BC02
OFF_INIT_ENTRY = 0x3C32    # CPU $BC22
OFF_ANIM_ENTRY = 0x3C52    # CPU $BC42

CPU_AI_ENTRY = 0xBBE2
CPU_SETUP_ENTRY = 0xBC02
CPU_INIT_ENTRY = 0xBC22
CPU_ANIM_ENTRY = 0xBC42

AI_ENTRY_RUNTIME = bytes.fromhex(
    "48"            # PHA: preserve stock AI-dispatch input
    "18"            # CLC
    "69 14"         # ADC #$14 -> recover enemy type
    "c9 84"         # CMP #$84
    "f0 04"         # BEQ ice
    "68"            # PLA
    "4c 29 a3"      # JMP $A329 stock AI dispatcher
    "68"            # ice: PLA
    f"4c {_ice.CPU_AI_DISPATCH & 0xFF:02x} {_ice.CPU_AI_DISPATCH >> 8:02x}"
)

SETUP_ENTRY_RUNTIME = bytes.fromhex(
    "a0 01"         # LDY #$01
    "b1 08"         # LDA ($08),Y -> main-slot type
    "c9 84"         # CMP #$84
    "f0 06"         # BEQ ice
    "a4 0e"         # LDY $0E
    "b9 d3 d9"      # LDA $D9D3,Y
    "60"            # RTS
    f"4c {_ice.CPU_SETUP_META_LOAD & 0xFF:02x} {_ice.CPU_SETUP_META_LOAD >> 8:02x}"
)

INIT_ENTRY_RUNTIME = bytes.fromhex(
    "20 1c 9d"      # JSR $9D1C stock init
    "a5 05"         # LDA $05 -> current enemy type during init
    "c9 84"         # CMP #$84
    "f0 01"         # BEQ ice
    "60"            # RTS
    f"4c {_ice.CPU_INIT_STATUS & 0xFF:02x} {_ice.CPU_INIT_STATUS >> 8:02x}"
)

ANIM_ENTRY_RUNTIME = bytes.fromhex(
    "a0 01"         # LDY #$01
    "b1 08"         # LDA ($08),Y -> main-slot type
    "c9 84"         # CMP #$84
    "f0 03"         # BEQ ice
    "4c 89 87"      # JMP $8789 stock animation updater
    f"4c {_ice.CPU_ANIM_UPDATE & 0xFF:02x} {_ice.CPU_ANIM_UPDATE >> 8:02x}"
)

ENTRY_RUNTIMES = (
    (OFF_AI_ENTRY, AI_ENTRY_RUNTIME, "$BBE2 new enemy AI dispatch"),
    (OFF_SETUP_ENTRY, SETUP_ENTRY_RUNTIME, "$BC02 new enemy setup dispatch"),
    (OFF_INIT_ENTRY, INIT_ENTRY_RUNTIME, "$BC22 new enemy init dispatch"),
    (OFF_ANIM_ENTRY, ANIM_ENTRY_RUNTIME, "$BC42 new enemy animation dispatch"),
)

HOOK_AI_DISPATCH_CALL = bytes((0x20, CPU_AI_ENTRY & 0xFF, CPU_AI_ENTRY >> 8))
HOOK_SETUP_META_LOAD = bytes((0x20, CPU_SETUP_ENTRY & 0xFF, CPU_SETUP_ENTRY >> 8))
HOOK_INIT_WRITE_CALL = bytes((0x20, CPU_INIT_ENTRY & 0xFF, CPU_INIT_ENTRY >> 8))
HOOK_ANIM_UPDATE_CALL = bytes((0x20, CPU_ANIM_ENTRY & 0xFF, CPU_ANIM_ENTRY >> 8))

RESERVED_SPANS = (
    (OFF_AI_ENTRY, len(AI_ENTRY_RUNTIME)),
    (OFF_SETUP_ENTRY, len(SETUP_ENTRY_RUNTIME)),
    (OFF_INIT_ENTRY, len(INIT_ENTRY_RUNTIME)),
    (OFF_ANIM_ENTRY, len(ANIM_ENTRY_RUNTIME)),
    *_ice.RESERVED_SPANS,
)

assert len(AI_ENTRY_RUNTIME) == 16
assert len(SETUP_ENTRY_RUNTIME) == 17
assert len(INIT_ENTRY_RUNTIME) == 13
assert len(ANIM_ENTRY_RUNTIME) == 14
assert OFF_SETUP_ENTRY - OFF_AI_ENTRY == 0x20
assert OFF_INIT_ENTRY - OFF_SETUP_ENTRY == 0x20
assert OFF_ANIM_ENTRY - OFF_INIT_ENTRY == 0x20


def levels_need_runtime(levels: list) -> bool:
    return _ice.levels_need_runtime(levels)


def _expect_one(data: bytes | bytearray, off: int, allowed: tuple[bytes, ...], name: str) -> None:
    size = len(allowed[0])
    cur = bytes(data[off:off + size])
    if cur not in allowed:
        expected = " or ".join(blob.hex(" ") for blob in allowed)
        raise NewEnemyRuntimeError(
            f"{name} signature mismatch at 0x{off:X}: expected {expected}, got {cur.hex(' ')}"
        )


def _expect_blank_or(data: bytes | bytearray, off: int, blob: bytes, name: str) -> None:
    cur = bytes(data[off:off + len(blob)])
    if cur == blob or all(b in (0xEA, 0x00) for b in cur):
        return
    raise NewEnemyRuntimeError(
        f"{name} area is not blank at 0x{off:X}: expected EA/00 or {blob.hex(' ')}, got {cur.hex(' ')}"
    )


def _write(data: bytearray, off: int, blob: bytes, changed: list[str], name: str) -> None:
    cur = bytes(data[off:off + len(blob)])
    if cur != blob:
        data[off:off + len(blob)] = blob
        changed.append(name)


def apply(rom_data: bytearray) -> list[str]:
    """Apply shared new-enemy dispatch entries and the Ice Flame body."""
    max_end = max(
        _ice.OFF_RUNTIME + len(_ice.RUNTIME),
        max(off + len(blob) for off, blob, _name in ENTRY_RUNTIMES),
    )
    if rom_data is None or len(rom_data) < max_end:
        raise NewEnemyRuntimeError("ROM is too short for new enemy runtime.")

    _expect_one(
        rom_data,
        _ice.OFF_AI_DISPATCH_CALL,
        (_ice.ORIG_AI_DISPATCH_CALL, _ice.HOOK_AI_DISPATCH_CALL, HOOK_AI_DISPATCH_CALL),
        "$A1C3 new enemy AI dispatch hook",
    )
    _expect_one(
        rom_data,
        _ice.OFF_ANIM_UPDATE_CALL,
        (_ice.ORIG_ANIM_UPDATE_CALL, _ice.HOOK_ANIM_UPDATE_CALL, HOOK_ANIM_UPDATE_CALL),
        "$8676 new enemy animation hook",
    )
    _expect_one(
        rom_data,
        _ice.OFF_INIT_WRITE_CALL,
        (_ice.ORIG_INIT_WRITE_CALL, _ice.HOOK_INIT_WRITE_CALL, HOOK_INIT_WRITE_CALL),
        "$A2F2 new enemy init hook",
    )
    _expect_one(
        rom_data,
        _ice.OFF_SETUP_META_LOAD,
        (_ice.ORIG_SETUP_META_LOAD, _ice.HOOK_SETUP_META_LOAD, HOOK_SETUP_META_LOAD),
        "$8ACB new enemy setup hook",
    )
    _expect_one(rom_data, _ice.OFF_BUFFER, (bytes((0xEA,)) * _ice.BUFFER_LEN,), "Ice Flame leading buffer")
    _expect_one(
        rom_data,
        _ice.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_ice.RUNTIME), _ice.RUNTIME),
        "Ice Flame runtime area",
    )
    for off, blob, name in ENTRY_RUNTIMES:
        _expect_blank_or(rom_data, off, blob, name)

    changed: list[str] = []
    _write(rom_data, _ice.OFF_AI_DISPATCH_CALL, HOOK_AI_DISPATCH_CALL, changed, "$A1C3 new enemy AI dispatch hook")
    _write(rom_data, _ice.OFF_ANIM_UPDATE_CALL, HOOK_ANIM_UPDATE_CALL, changed, "$8676 new enemy animation hook")
    _write(rom_data, _ice.OFF_INIT_WRITE_CALL, HOOK_INIT_WRITE_CALL, changed, "$A2F2 new enemy init/status hook")
    _write(rom_data, _ice.OFF_SETUP_META_LOAD, HOOK_SETUP_META_LOAD, changed, "$8ACB new enemy setup group hook")
    for off, blob, name in ENTRY_RUNTIMES:
        _write(rom_data, off, blob, changed, name)
    _write(
        rom_data,
        _ice.OFF_RUNTIME,
        _ice.RUNTIME,
        changed,
        f"Ice Flame runtime ${_ice.CPU_AI_DISPATCH:04X}-${_ice.CPU_RUNTIME_END - 1:04X}",
    )
    return changed

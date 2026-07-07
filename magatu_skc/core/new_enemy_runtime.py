"""Shared dispatch entries for new enemy IDs in mapper66 saved ROMs."""
from __future__ import annotations

from . import ice_flame_runtime as _ice
from . import spark85_runtime as _spark85
from . import ghost86_runtime as _ghost86
from . import neul88_runtime as _neul88
from . import flying_dragon89_runtime as _flying89


class NewEnemyRuntimeError(ValueError):
    pass


ICE_FLAME_ID = _ice.NEW_ENEMY_ID
SPARK85_ID = _spark85.NEW_ENEMY_ID
GHOST86_ID = _ghost86.NEW_ENEMY_ID
NEUL88_ID = _neul88.NEW_ENEMY_ID
FLYING89_ID = _flying89.NEW_ENEMY_ID

OLD_GHOST86_OFF_RUNTIME = 0x6D88

OFF_AI_ENTRY = 0x3BF2      # CPU $BBE2
OFF_SETUP_ENTRY = 0x3C2A   # CPU $BC1A
OFF_INIT_ENTRY = 0x3C56    # CPU $BC46
OFF_ANIM_ENTRY = 0x3C88    # CPU $BC78

CPU_AI_ENTRY = 0xBBE2
CPU_SETUP_ENTRY = 0xBC1A
CPU_INIT_ENTRY = 0xBC46
CPU_ANIM_ENTRY = 0xBC78

OLD_AI_ENTRY_RUNTIME = bytes.fromhex(
    "48"
    "18"
    "69 14"
    "c9 84"
    "f0 04"
    "68"
    "4c 29 a3"
    "68"
    f"4c {_ice.CPU_AI_DISPATCH & 0xFF:02x} {_ice.CPU_AI_DISPATCH >> 8:02x}"
)

AI_ENTRY_RUNTIME = bytes.fromhex(
    "48"            # PHA: preserve stock AI-dispatch input
    "18"            # CLC
    "69 14"         # ADC #$14 -> recover enemy type
    "c9 84"         # CMP #$84
    "f0 14"         # BEQ ice
    "c9 85"         # CMP #$85
    "f0 14"         # BEQ spark85
    "c9 86"         # CMP #$86
    "f0 14"         # BEQ ghost86
    "c9 87"         # CMP #$87
    "f0 14"         # BEQ ghost87
    "c9 88"         # CMP #$88
    "f0 18"         # BEQ neul88
    "c9 89"         # CMP #$89
    "f0 18"         # BEQ flying89
    "68"            # PLA
    "4c 29 a3"      # JMP $A329 stock AI dispatcher
    "68"            # ice: PLA
    f"4c {_ice.CPU_AI_DISPATCH & 0xFF:02x} {_ice.CPU_AI_DISPATCH >> 8:02x}"
    "68"            # spark85: PLA
    f"4c {_spark85.CPU_AI_DISPATCH & 0xFF:02x} {_spark85.CPU_AI_DISPATCH >> 8:02x}"
    "68"            # ghost86: PLA
    f"4c {_ghost86.CPU_AI_DISPATCH & 0xFF:02x} {_ghost86.CPU_AI_DISPATCH >> 8:02x}"
    "68"            # ghost87: PLA
    f"4c {_ghost86.CPU_AI_DISPATCH_DOWN & 0xFF:02x} {_ghost86.CPU_AI_DISPATCH_DOWN >> 8:02x}"
    "68"            # neul88: PLA
    f"4c {_neul88.CPU_AI_DISPATCH & 0xFF:02x} {_neul88.CPU_AI_DISPATCH >> 8:02x}"
    "68"            # flying89: PLA
    f"4c {_flying89.CPU_AI_DISPATCH & 0xFF:02x} {_flying89.CPU_AI_DISPATCH >> 8:02x}"
)
PRE_PACKED_GHOST_AI_ENTRY_RUNTIME = bytes.fromhex(
    "48"
    "18"
    "69 14"
    "c9 84"
    "f0 10"
    "c9 85"
    "f0 10"
    "c9 86"
    "f0 10"
    "c9 87"
    "f0 10"
    "68"
    "4c 29 a3"
    "68"
    f"4c {_ice.CPU_AI_DISPATCH & 0xFF:02x} {_ice.CPU_AI_DISPATCH >> 8:02x}"
    "68"
    f"4c {_spark85.CPU_AI_DISPATCH & 0xFF:02x} {_spark85.CPU_AI_DISPATCH >> 8:02x}"
    "68"
    "4c 92 ed"
    "68"
    "4c 96 ed"
)

OLD_SETUP_ENTRY_RUNTIME = bytes.fromhex(
    "a0 01"
    "b1 08"
    "c9 84"
    "f0 06"
    "a4 0e"
    "b9 d3 d9"
    "60"
    f"4c {_ice.CPU_SETUP_META_LOAD & 0xFF:02x} {_ice.CPU_SETUP_META_LOAD >> 8:02x}"
)

SETUP_ENTRY_RUNTIME = bytes.fromhex(
    "a0 01"         # LDY #$01
    "b1 08"         # LDA ($08),Y -> main-slot type
    "c9 84"         # CMP #$84
    "90 1e"         # BCC stock
    "c9 88"         # CMP #$88
    "f0 14"         # BEQ neul88
    "c9 89"         # CMP #$89
    "f0 13"         # BEQ flying89
    "b0 14"         # BCS stock
    "38"            # SEC
    "e9 84"         # SBC #$84
    "aa"            # TAX
    f"bd {_ghost86.CPU_SETUP_GROUP_TABLE & 0xFF:02x} {_ghost86.CPU_SETUP_GROUP_TABLE >> 8:02x}"
    "85 0e"         # STA $0E
    "a8"            # TAY
    "b9 d3 d9"      # LDA $D9D3,Y
    "60"            # RTS
    f"4c {_neul88.CPU_SETUP_META_LOAD & 0xFF:02x} {_neul88.CPU_SETUP_META_LOAD >> 8:02x}"
    f"4c {_flying89.CPU_SETUP_META_LOAD & 0xFF:02x} {_flying89.CPU_SETUP_META_LOAD >> 8:02x}"
    "a4 0e"         # LDY $0E
    "b9 d3 d9"      # LDA $D9D3,Y
    "60"            # RTS
)
PRE_PACKED_GHOST_SETUP_ENTRY_RUNTIME = bytes.fromhex(
    "a0 01"
    "b1 08"
    "c9 84"
    "90 12"
    "c9 88"
    "b0 0e"
    "38"
    "e9 84"
    "aa"
    "bd 78 ed"
    "85 0e"
    "a8"
    "b9 d3 d9"
    "60"
    "a4 0e"
    "b9 d3 d9"
    "60"
)

OLD_INIT_ENTRY_RUNTIME = bytes.fromhex(
    "20 1c 9d"
    "a5 05"
    "c9 84"
    "f0 01"
    "60"
    f"4c {_ice.CPU_INIT_STATUS & 0xFF:02x} {_ice.CPU_INIT_STATUS >> 8:02x}"
)

INIT_ENTRY_RUNTIME = bytes.fromhex(
    "48"            # PHA: preserve stock init input
    "a5 05"         # LDA $05 -> current enemy type during init
    "c9 86"         # CMP #$86
    "f0 04"         # BEQ ghost86/87
    "c9 87"         # CMP #$87
    "d0 03"         # BNE not ghost86/87
    f"4c {_ghost86.CPU_INIT_STATUS & 0xFF:02x} {_ghost86.CPU_INIT_STATUS >> 8:02x}"
    "c9 88"         # CMP #$88
    "f0 1a"         # BEQ neul88
    "c9 89"         # CMP #$89
    "f0 19"         # BEQ flying89
    "c9 85"         # CMP #$85
    "f0 0e"         # BEQ spark85
    "68"            # PLA
    "20 1c 9d"      # JSR $9D1C stock init
    "a5 05"         # LDA $05 -> current enemy type during init
    "c9 84"         # CMP #$84
    "f0 01"         # BEQ ice
    "60"            # RTS
    f"4c {_ice.CPU_INIT_STATUS & 0xFF:02x} {_ice.CPU_INIT_STATUS >> 8:02x}"
    "68"            # spark85: PLA
    f"4c {_spark85.CPU_INIT_STATUS & 0xFF:02x} {_spark85.CPU_INIT_STATUS >> 8:02x}"
    f"4c {_neul88.CPU_INIT_STATUS & 0xFF:02x} {_neul88.CPU_INIT_STATUS >> 8:02x}"
    f"4c {_flying89.CPU_INIT_STATUS & 0xFF:02x} {_flying89.CPU_INIT_STATUS >> 8:02x}"
)
PRE_PACKED_GHOST_INIT_ENTRY_RUNTIME = bytes.fromhex(
    "48"
    "a5 05"
    "c9 86"
    "f0 04"
    "c9 87"
    "d0 03"
    "4c 7c ed"
    "c9 85"
    "f0 0e"
    "68"
    "20 1c 9d"
    "a5 05"
    "c9 84"
    "f0 01"
    "60"
    f"4c {_ice.CPU_INIT_STATUS & 0xFF:02x} {_ice.CPU_INIT_STATUS >> 8:02x}"
    "68"
    f"4c {_spark85.CPU_INIT_STATUS & 0xFF:02x} {_spark85.CPU_INIT_STATUS >> 8:02x}"
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
    (OFF_AI_ENTRY, AI_ENTRY_RUNTIME, (), "$BBE2 new enemy AI dispatch"),
    (OFF_SETUP_ENTRY, SETUP_ENTRY_RUNTIME, (), "$BC1A new enemy setup dispatch"),
    (OFF_INIT_ENTRY, INIT_ENTRY_RUNTIME, (), "$BC46 new enemy init dispatch"),
    (OFF_ANIM_ENTRY, ANIM_ENTRY_RUNTIME, (), "$BC78 new enemy animation dispatch"),
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
    *_spark85.RESERVED_SPANS,
    *_ghost86.RESERVED_SPANS,
    *_neul88.RESERVED_SPANS,
    *_flying89.RESERVED_SPANS,
)

assert len(AI_ENTRY_RUNTIME) == 56
assert len(PRE_PACKED_GHOST_AI_ENTRY_RUNTIME) == 40
assert len(SETUP_ENTRY_RUNTIME) == 44
assert len(PRE_PACKED_GHOST_SETUP_ENTRY_RUNTIME) == 32
assert len(INIT_ENTRY_RUNTIME) == 50
assert len(PRE_PACKED_GHOST_INIT_ENTRY_RUNTIME) == 36
assert len(ANIM_ENTRY_RUNTIME) == 14
assert OFF_SETUP_ENTRY == OFF_AI_ENTRY + len(AI_ENTRY_RUNTIME)
assert OFF_INIT_ENTRY == OFF_SETUP_ENTRY + len(SETUP_ENTRY_RUNTIME)
assert OFF_ANIM_ENTRY == OFF_INIT_ENTRY + len(INIT_ENTRY_RUNTIME)


def levels_need_runtime(levels: list) -> bool:
    return (
        _ice.levels_need_runtime(levels)
        or _spark85.levels_need_runtime(levels)
        or _ghost86.levels_need_runtime(levels)
        or _neul88.levels_need_runtime(levels)
        or _flying89.levels_need_runtime(levels)
    )


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


def _expect_blank_or_one_of(data: bytes | bytearray, off: int, allowed: tuple[bytes, ...], name: str) -> None:
    size = max(len(blob) for blob in allowed)
    cur = bytes(data[off:off + size])
    if all(b in (0xEA, 0x00) for b in cur):
        return
    for blob in allowed:
        if cur[:len(blob)] == blob and all(b in (0xEA, 0x00) for b in cur[len(blob):]):
            return
    expected = " or ".join(blob.hex(" ") for blob in allowed)
    raise NewEnemyRuntimeError(
        f"{name} area is not blank at 0x{off:X}: expected EA/00 or {expected}, got {cur.hex(' ')}"
    )


def _write(data: bytearray, off: int, blob: bytes, changed: list[str], name: str) -> None:
    cur = bytes(data[off:off + len(blob)])
    if cur != blob:
        data[off:off + len(blob)] = blob
        changed.append(name)


def apply(rom_data: bytearray) -> list[str]:
    """Apply shared new-enemy dispatch entries and new enemy bodies."""
    max_end = max(
        _ice.OFF_RUNTIME + len(_ice.RUNTIME),
        _spark85.OFF_RUNTIME + len(_spark85.RUNTIME),
        _ghost86.OFF_RUNTIME + len(_ghost86.RUNTIME),
        _neul88.OFF_RUNTIME + len(_neul88.RUNTIME),
        _flying89.OFF_RUNTIME + len(_flying89.RUNTIME),
        max(off + len(blob) for off, blob, _old_blobs, _name in ENTRY_RUNTIMES),
    )
    if rom_data is None or len(rom_data) < max_end:
        raise NewEnemyRuntimeError("ROM is too short for new enemy runtime.")

    changed: list[str] = []
    if OLD_GHOST86_OFF_RUNTIME != _ghost86.OFF_RUNTIME:
        old_ghost_cur = bytes(rom_data[OLD_GHOST86_OFF_RUNTIME:OLD_GHOST86_OFF_RUNTIME + len(_ghost86.RUNTIME)])
        if old_ghost_cur == _ghost86.RUNTIME:
            rom_data[OLD_GHOST86_OFF_RUNTIME:OLD_GHOST86_OFF_RUNTIME + len(_ghost86.RUNTIME)] = (
                bytes((0xEA,)) * len(_ghost86.RUNTIME)
            )
            changed.append("old Ghost86/87 runtime area cleared for packed relocation")

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
    _expect_one(
        rom_data,
        _spark85.OFF_BUFFER,
        (bytes((0xEA,)) * _spark85.BUFFER_LEN,),
        "Spark85 leading buffer",
    )
    _expect_one(
        rom_data,
        _spark85.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_spark85.RUNTIME), _spark85.RUNTIME),
        "Spark85 runtime area",
    )
    _expect_one(
        rom_data,
        _ghost86.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_ghost86.RUNTIME), _ghost86.RUNTIME),
        "Ghost86/87 runtime area",
    )
    _expect_one(
        rom_data,
        _neul88.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_neul88.RUNTIME), _neul88.RUNTIME),
        "Neul88 runtime area",
    )
    _expect_one(
        rom_data,
        _flying89.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_flying89.RUNTIME), _flying89.RUNTIME),
        "Flying Dragon89 runtime area",
    )
    for off, blob, old_blobs, name in ENTRY_RUNTIMES:
        _expect_blank_or_one_of(rom_data, off, (blob, *old_blobs), name)

    _write(rom_data, _ice.OFF_AI_DISPATCH_CALL, HOOK_AI_DISPATCH_CALL, changed, "$A1C3 new enemy AI dispatch hook")
    _write(rom_data, _ice.OFF_ANIM_UPDATE_CALL, HOOK_ANIM_UPDATE_CALL, changed, "$8676 new enemy animation hook")
    _write(rom_data, _ice.OFF_INIT_WRITE_CALL, HOOK_INIT_WRITE_CALL, changed, "$A2F2 new enemy init/status hook")
    _write(rom_data, _ice.OFF_SETUP_META_LOAD, HOOK_SETUP_META_LOAD, changed, "$8ACB new enemy setup group hook")
    for off, blob, _old_blobs, name in ENTRY_RUNTIMES:
        _write(rom_data, off, blob, changed, name)
    _write(
        rom_data,
        _ice.OFF_RUNTIME,
        _ice.RUNTIME,
        changed,
        f"Ice Flame runtime ${_ice.CPU_AI_DISPATCH:04X}-${_ice.CPU_RUNTIME_END - 1:04X}",
    )
    _write(
        rom_data,
        _spark85.OFF_RUNTIME,
        _spark85.RUNTIME,
        changed,
        f"Spark85 runtime ${_spark85.CPU_AI_DISPATCH:04X}-${_spark85.CPU_RUNTIME_END - 1:04X}",
    )
    _write(
        rom_data,
        _ghost86.OFF_RUNTIME,
        _ghost86.RUNTIME,
        changed,
        f"Ghost86/87 runtime ${_ghost86.CPU_RUNTIME:04X}-${_ghost86.CPU_RUNTIME_END - 1:04X}",
    )
    _write(
        rom_data,
        _neul88.OFF_RUNTIME,
        _neul88.RUNTIME,
        changed,
        f"Neul88 runtime ${_neul88.CPU_RUNTIME:04X}-${_neul88.CPU_RUNTIME_END - 1:04X}",
    )
    _write(
        rom_data,
        _flying89.OFF_RUNTIME,
        _flying89.RUNTIME,
        changed,
        f"Flying Dragon89 runtime ${_flying89.CPU_RUNTIME:04X}-${_flying89.CPU_RUNTIME_END - 1:04X}",
    )
    return changed

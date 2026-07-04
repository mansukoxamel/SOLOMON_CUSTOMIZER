"""Ice Flame ($84) runtime for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


class IceFlameRuntimeError(ValueError):
    pass


NEW_ENEMY_ID = 0x84

OFF_AI_DISPATCH_CALL = 0x21D3  # CPU $A1C3: JSR $A329
OFF_ANIM_UPDATE_CALL = 0x0686  # CPU $8676: JSR $8789
OFF_INIT_WRITE_CALL = 0x2302  # CPU $A2F2: JSR $9D1C
OFF_SETUP_META_LOAD = 0x0ADB  # CPU $8ACB: LDA $D9D3,Y

OFF_BUFFER = 0x69B9
BUFFER_LEN = 24
OFF_RUNTIME = 0x69D1

CPU_AI_DISPATCH = 0xE9C1
CPU_SETUP_META_LOAD = 0xE9D2
CPU_INIT_STATUS = 0xE9EB
CPU_ANIM_UPDATE = 0xEA17
CPU_CLASSIFY = 0xBBEE
CPU_SETUP_TABLE = 0xEA24
CPU_STATUS_TABLE = 0xEA25
CPU_BEHAVIOR_TABLE = 0xEA26
CPU_FRAME1_TABLE = 0xEA27
CPU_FRAME2_TABLE = 0xEA28
CPU_ATTR_TABLE = 0xEA29

ORIG_AI_DISPATCH_CALL = bytes.fromhex("20 29 a3")
HOOK_AI_DISPATCH_CALL = bytes((0x20, CPU_AI_DISPATCH & 0xFF, CPU_AI_DISPATCH >> 8))

ORIG_ANIM_UPDATE_CALL = bytes.fromhex("20 89 87")
HOOK_ANIM_UPDATE_CALL = bytes((0x20, CPU_ANIM_UPDATE & 0xFF, CPU_ANIM_UPDATE >> 8))

ORIG_INIT_WRITE_CALL = bytes.fromhex("20 1c 9d")
HOOK_INIT_WRITE_CALL = bytes((0x20, CPU_INIT_STATUS & 0xFF, CPU_INIT_STATUS >> 8))

ORIG_SETUP_META_LOAD = bytes.fromhex("b9 d3 d9")
HOOK_SETUP_META_LOAD = bytes((0x20, CPU_SETUP_META_LOAD & 0xFF, CPU_SETUP_META_LOAD >> 8))


AI_DISPATCH_RUNTIME = bytes.fromhex(
    "48"
    "18"
    "69 14"
    f"20 {CPU_CLASSIFY & 0xFF:02x} {CPU_CLASSIFY >> 8:02x}"
    "b0 04"
    "68"
    "4c a0 a5"
    "68"
    "4c 29 a3"
)

SETUP_META_RUNTIME = bytes.fromhex(
    "a0 01"
    "b1 08"
    f"20 {CPU_CLASSIFY & 0xFF:02x} {CPU_CLASSIFY >> 8:02x}"
    "b0 0a"
    f"bd {CPU_SETUP_TABLE & 0xFF:02x} {CPU_SETUP_TABLE >> 8:02x}"
    "85 0e"
    "a8"
    "b9 d3 d9"
    "60"
    "a4 0e"
    "b9 d3 d9"
    "60"
)

INIT_STATUS_RUNTIME = bytes.fromhex(
    "20 1c 9d"
    "a5 05"
    f"20 {CPU_CLASSIFY & 0xFF:02x} {CPU_CLASSIFY >> 8:02x}"
    "b0 21"
    "a0 00"
    f"bd {CPU_STATUS_TABLE & 0xFF:02x} {CPU_STATUS_TABLE >> 8:02x}"
    "91 00"
    "a0 03"
    f"bd {CPU_BEHAVIOR_TABLE & 0xFF:02x} {CPU_BEHAVIOR_TABLE >> 8:02x}"
    "91 00"
    "a0 11"
    f"bd {CPU_FRAME1_TABLE & 0xFF:02x} {CPU_FRAME1_TABLE >> 8:02x}"
    "91 00"
    "c8"
    f"bd {CPU_FRAME2_TABLE & 0xFF:02x} {CPU_FRAME2_TABLE >> 8:02x}"
    "91 00"
    "c8"
    f"bd {CPU_ATTR_TABLE & 0xFF:02x} {CPU_ATTR_TABLE >> 8:02x}"
    "91 00"
    "60"
)

ANIM_UPDATE_RUNTIME = bytes.fromhex(
    "a0 01"
    "b1 08"
    f"20 {CPU_CLASSIFY & 0xFF:02x} {CPU_CLASSIFY >> 8:02x}"
    "b0 01"
    "60"
    "4c 89 87"
)

CLASSIFICATION_TABLES = bytes((
    0x40,  # setup group: Flame/Burn
    0xE0,  # status: active, contact enabled, fireball-killable
    0x14,  # behavior/state: White Flame steady state
    0xD6,  # fixed frame tile 1
    0xD4,  # fixed frame tile 2
    0x5A,  # fixed frame attr
))

RUNTIME = (
    AI_DISPATCH_RUNTIME
    + SETUP_META_RUNTIME
    + INIT_STATUS_RUNTIME
    + ANIM_UPDATE_RUNTIME
    + CLASSIFICATION_TABLES
)

RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(AI_DISPATCH_RUNTIME) == CPU_SETUP_META_LOAD - CPU_AI_DISPATCH
assert len(SETUP_META_RUNTIME) == CPU_INIT_STATUS - CPU_SETUP_META_LOAD
assert len(INIT_STATUS_RUNTIME) == CPU_ANIM_UPDATE - CPU_INIT_STATUS
assert len(ANIM_UPDATE_RUNTIME) == CPU_SETUP_TABLE - CPU_ANIM_UPDATE
assert len(CLASSIFICATION_TABLES) == 6
assert len(RUNTIME) == 105
assert CPU_AI_DISPATCH + len(RUNTIME) == CPU_ATTR_TABLE + 1


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False


def _expect_one(data: bytes | bytearray, off: int, allowed: tuple[bytes, ...], name: str) -> None:
    size = len(allowed[0])
    cur = bytes(data[off:off + size])
    if cur not in allowed:
        expected = " or ".join(blob.hex(" ") for blob in allowed)
        raise IceFlameRuntimeError(
            f"{name} signature mismatch at 0x{off:X}: expected {expected}, got {cur.hex(' ')}"
        )


def _write(data: bytearray, off: int, blob: bytes, changed: list[str], name: str) -> None:
    cur = bytes(data[off:off + len(blob)])
    if cur != blob:
        data[off:off + len(blob)] = blob
        changed.append(name)


def apply(rom_data: bytearray) -> list[str]:
    """Apply Ice Flame through the shared new-enemy entry layer."""
    from . import new_enemy_runtime
    return new_enemy_runtime.apply(rom_data)

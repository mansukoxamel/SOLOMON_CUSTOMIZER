"""Gargoyle borrowed-ID two-bullet variant.

JP/JPC66 only.  Gargoyle #2 IDs are repurposed as a strengthened family:

  $7A/$7B -> two simultaneous Bullet shots, speed 1
  $7E/$7F -> two simultaneous Bullet shots, speed 2

This is the accepted `$AE6F` materialization-side experiment:

  TEST_GargoyleTwoBullet_AE6F_SecondXAhead16_DirVelocity_JP_v7_stage6_7B.nes

Normal Gargoyles keep the stock `$AE6F -> $AE76` path.  The borrowed IDs enter
the v7 routine, which lets the stock first Bullet materialize, allocates a
second child slot, offsets its X position 16px ahead of the firing direction,
calls `$AE76` again, and fixes the second Bullet X velocity by direction.

The current placement uses the formerly conflicting bank0 cave band.  This
variant owns the two reserved spans below.
"""
from __future__ import annotations


class GargoyleVariantError(ValueError):
    pass


def _cf(cpu: int) -> int:
    return 0x10 + (cpu - 0x8000)


def _word(cpu: int) -> bytes:
    return bytes((cpu & 0xFF, (cpu >> 8) & 0xFF))


OFF_HOOK_MATERIALIZE = _cf(0xAE6F)
OFF_HOOK_OLD_WAIT = _cf(0xAF2B)
OFF_CAVE_GATE = _cf(0xBCFF)
OFF_CAVE_TWO_BULLET = _cf(0xBD3B)

CPU_CAVE_GATE = 0xBCFF
CPU_CAVE_TWO_BULLET = 0xBD3B

SECOND_OFFSET_PRESETS = (8, 16, 24, 32)
SECOND_SPEED_PRESETS = (0x20, 0x30, 0x40)
DEFAULT_SECOND_OFFSET = 16
DEFAULT_SECOND_SPEED = 0x30

ORIG_MATERIALIZE = bytes.fromhex("b1 2e aa 09 02 91 2e")
HOOK_MATERIALIZE = bytes((0x4C, *(_word(CPU_CAVE_GATE)))) + bytes([0xEA] * 4)
OLD_GLOBAL_TWO_BULLET_HOOK = bytes((0x4C, *(_word(CPU_CAVE_TWO_BULLET)))) + bytes([0xEA] * 4)

# v0.6.159 rapid-fire experiment.  It is no longer used and must be removed if
# a ROM carrying that hook is saved again.
ORIG_WAIT = bytes.fromhex("a0 01 b1 2c c9 68 90 24")
SNAPPY_WAIT = bytes.fromhex("a0 01 b1 2c c9 01 90 24")
OLD_HOOK_WAIT = bytes((0x4C, *(_word(0xBEC7)))) + bytes([0xEA] * 5)

CAVE_GATE = bytes.fromhex(
    # Only $7A/$7B/$7E/$7F are strengthened.  Everything else replays stock $AE6F
    # prologue and jumps into $AE76.
    "a0 01 b1 2e 29 fa c9 7a f0 0c"
    "a0 03 b1 2e aa 09 02 91 2e 4c 76 ae"
    "4c 3b bd"
)
assert len(CAVE_GATE) == 25

CAVE_TWO_BULLET = bytes.fromhex(
    # Exact accepted v7 body, including the second Bullet X lead and
    # direction-correct second Bullet X velocity.  Immediate operands are
    # patched by _build_two_bullet_body().
    "a0 03 b1 2e aa 09 02 91 2e 20 76 ae 20 ea b2 90 3a"
    "a0 00 a9 80 91 04 b1 2c 09 01 91 2c 8a a0 06 91 2c"
    "a0 0a b1 2e 48 a6 03 f0 05 38 e9 10 d0 03 18 69 10"
    "91 2e a6 03 20 76 ae a0 08 a9 30 a6 03 f0 02 a9 d0"
    "91 00 68 a0 0a 91 2e 60"
)
assert len(CAVE_TWO_BULLET) == 76

OFF_SECOND_OFFSET_SUB = OFF_CAVE_TWO_BULLET + 0x2D
OFF_SECOND_OFFSET_ADD = OFF_CAVE_TWO_BULLET + 0x32
OFF_SECOND_SPEED_RIGHT = OFF_CAVE_TWO_BULLET + 0x3D
OFF_SECOND_SPEED_LEFT = OFF_CAVE_TWO_BULLET + 0x43


def _negative_byte(value: int) -> int:
    return (-int(value)) & 0xFF


def _normalize_second_offset(value: int) -> int:
    value = int(value)
    if value not in SECOND_OFFSET_PRESETS:
        raise GargoyleVariantError(f"未対応の2発目位置です: {value}px")
    return value


def _normalize_second_speed(value: int) -> int:
    value = int(value)
    if value not in SECOND_SPEED_PRESETS:
        raise GargoyleVariantError(f"未対応の2発目速度です: ${value:02X}")
    return value


def _build_two_bullet_body(second_offset=DEFAULT_SECOND_OFFSET,
                           second_speed=DEFAULT_SECOND_SPEED) -> bytes:
    second_offset = _normalize_second_offset(second_offset)
    second_speed = _normalize_second_speed(second_speed)
    body = bytearray(CAVE_TWO_BULLET)
    body[0x2D] = second_offset
    body[0x32] = second_offset
    body[0x3D] = second_speed
    body[0x43] = _negative_byte(second_speed)
    return bytes(body)

RESERVED_SPANS = (
    (OFF_CAVE_GATE, len(CAVE_GATE)),
    (OFF_CAVE_TWO_BULLET, len(CAVE_TWO_BULLET)),
)


def _expect_any(rom_data, off: int, accepted: tuple[bytes, ...], name: str) -> None:
    max_len = max(len(blob) for blob in accepted)
    cur = bytes(rom_data[off:off + max_len])
    for blob in accepted:
        if cur[:len(blob)] == blob:
            return
    exp = " or ".join(blob.hex(" ") for blob in accepted)
    raise GargoyleVariantError(
        f"{name} signature mismatch at file 0x{off:X}: expected {exp}, "
        f"got {cur.hex(' ')}"
    )


def _write(rom_data, off: int, blob: bytes, changed: list[str], name: str) -> None:
    if bytes(rom_data[off:off + len(blob)]) != blob:
        rom_data[off:off + len(blob)] = blob
        changed.append(name)


def _ensure_available(rom_data, off: int, blob: bytes, name: str) -> None:
    cur = bytes(rom_data[off:off + len(blob)])
    if cur == blob or all(b in (0xEA, 0x00) for b in cur):
        return
    raise GargoyleVariantError(
        f"{name} cave overlap at file 0x{off:X}: "
        f"expected empty EA/00 or existing Gargoyle code, got {cur[:16].hex(' ')}..."
    )


def _is_two_bullet_body(blob: bytes) -> bool:
    if len(blob) < len(CAVE_TWO_BULLET):
        return False
    return (
        blob[:0x2D] == CAVE_TWO_BULLET[:0x2D]
        and blob[0x2E:0x32] == CAVE_TWO_BULLET[0x2E:0x32]
        and blob[0x33:0x3D] == CAVE_TWO_BULLET[0x33:0x3D]
        and blob[0x3E:0x43] == CAVE_TWO_BULLET[0x3E:0x43]
        and blob[0x44:] == CAVE_TWO_BULLET[0x44:]
    )


def _has_two_bullet_body(rom_data) -> bool:
    return (
        rom_data is not None
        and len(rom_data) >= OFF_CAVE_TWO_BULLET + len(CAVE_TWO_BULLET)
        and _is_two_bullet_body(
            bytes(rom_data[OFF_CAVE_TWO_BULLET:OFF_CAVE_TWO_BULLET + len(CAVE_TWO_BULLET)])
        )
    )


def is_applied(rom_data) -> bool:
    return _has_two_bullet_body(rom_data)


def current_second_offset(rom_data) -> int:
    if not _has_two_bullet_body(rom_data):
        return DEFAULT_SECOND_OFFSET
    sub = int(rom_data[OFF_SECOND_OFFSET_SUB])
    add = int(rom_data[OFF_SECOND_OFFSET_ADD])
    if sub == add and sub in SECOND_OFFSET_PRESETS:
        return sub
    return DEFAULT_SECOND_OFFSET


def current_second_speed(rom_data) -> int:
    if not _has_two_bullet_body(rom_data):
        return DEFAULT_SECOND_SPEED
    right = int(rom_data[OFF_SECOND_SPEED_RIGHT])
    left = int(rom_data[OFF_SECOND_SPEED_LEFT])
    if left == _negative_byte(right) and right in SECOND_SPEED_PRESETS:
        return right
    return DEFAULT_SECOND_SPEED


def apply(rom_data, second_offset=None, second_speed=None) -> list[str]:
    if second_offset is None:
        second_offset = current_second_offset(rom_data)
    else:
        second_offset = _normalize_second_offset(second_offset)
    if second_speed is None:
        second_speed = current_second_speed(rom_data)
    else:
        second_speed = _normalize_second_speed(second_speed)
    cave_two_bullet = _build_two_bullet_body(second_offset, second_speed)

    min_len = max(
        OFF_CAVE_GATE + len(CAVE_GATE),
        OFF_CAVE_TWO_BULLET + len(cave_two_bullet),
        OFF_HOOK_MATERIALIZE + len(ORIG_MATERIALIZE),
        OFF_HOOK_OLD_WAIT + len(ORIG_WAIT),
    )
    if rom_data is None or len(rom_data) < min_len:
        raise GargoyleVariantError("ROM is too short for Gargoyle two-bullet patch.")

    _expect_any(
        rom_data,
        OFF_HOOK_MATERIALIZE,
        (ORIG_MATERIALIZE, HOOK_MATERIALIZE, OLD_GLOBAL_TWO_BULLET_HOOK),
        "$AE6F Gargoyle Bullet materialize hook",
    )
    _expect_any(
        rom_data,
        OFF_HOOK_OLD_WAIT,
        (ORIG_WAIT, SNAPPY_WAIT, OLD_HOOK_WAIT),
        "$AF2B old Gargoyle rapid-fire hook",
    )
    _ensure_available(rom_data, OFF_CAVE_GATE, CAVE_GATE, "Gargoyle two-bullet gate")
    cur_body = bytes(rom_data[OFF_CAVE_TWO_BULLET:OFF_CAVE_TWO_BULLET + len(cave_two_bullet)])
    if not (
        cur_body == cave_two_bullet
        or _is_two_bullet_body(cur_body)
        or all(b in (0xEA, 0x00) for b in cur_body)
    ):
        raise GargoyleVariantError(
            f"Gargoyle two-bullet body cave overlap at file 0x{OFF_CAVE_TWO_BULLET:X}: "
            f"expected empty EA/00 or existing Gargoyle code, got {cur_body[:16].hex(' ')}..."
        )

    changed: list[str] = []
    _write(rom_data, OFF_CAVE_GATE, CAVE_GATE, changed, "Gargoyle two-bullet gate $BCFF")
    _write(
        rom_data,
        OFF_CAVE_TWO_BULLET,
        cave_two_bullet,
        changed,
        "Gargoyle two-bullet body $BD3B",
    )
    _write(
        rom_data,
        OFF_HOOK_MATERIALIZE,
        HOOK_MATERIALIZE,
        changed,
        "$AE6F Gargoyle two-bullet hook",
    )
    if bytes(rom_data[OFF_HOOK_OLD_WAIT:OFF_HOOK_OLD_WAIT + len(OLD_HOOK_WAIT)]) == OLD_HOOK_WAIT:
        _write(
            rom_data,
            OFF_HOOK_OLD_WAIT,
            ORIG_WAIT,
            changed,
            "$AF2B restore old Gargoyle rapid wait hook",
        )
    return changed

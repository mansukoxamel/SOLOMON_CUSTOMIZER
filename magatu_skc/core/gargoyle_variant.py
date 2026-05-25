"""Gargoyle borrowed-ID two-bullet variant.

JP/JPC66 only.  Gargoyle speed1 #2 IDs are repurposed as a strengthened
family:

  $7A/$7B -> two simultaneous Bullet shots

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

ORIG_MATERIALIZE = bytes.fromhex("b1 2e aa 09 02 91 2e")
HOOK_MATERIALIZE = bytes((0x4C, *(_word(CPU_CAVE_GATE)))) + bytes([0xEA] * 4)
OLD_GLOBAL_TWO_BULLET_HOOK = bytes((0x4C, *(_word(CPU_CAVE_TWO_BULLET)))) + bytes([0xEA] * 4)

# v0.6.159 rapid-fire experiment.  It is no longer used and must be removed if
# a ROM carrying that hook is saved again.
ORIG_WAIT = bytes.fromhex("a0 01 b1 2c c9 68 90 24")
OLD_HOOK_WAIT = bytes((0x4C, *(_word(0xBEC7)))) + bytes([0xEA] * 5)

CAVE_GATE = bytes.fromhex(
    # Only $7A/$7B are strengthened.  Everything else replays the stock $AE6F
    # prologue and jumps into $AE76.
    "a0 01 b1 2e c9 7a f0 10 c9 7b f0 0c"
    "a0 03 b1 2e aa 09 02 91 2e 4c 76 ae"
    "4c 3b bd"
)
assert len(CAVE_GATE) == 27

CAVE_TWO_BULLET = bytes.fromhex(
    # Exact accepted v7 body, including the $10 X lead and direction-correct
    # second Bullet X velocity.
    "a0 03 b1 2e aa 09 02 91 2e 20 76 ae 20 ea b2 90 3a"
    "a0 00 a9 80 91 04 b1 2c 09 01 91 2c 8a a0 06 91 2c"
    "a0 0a b1 2e 48 a6 03 f0 05 38 e9 10 d0 03 18 69 10"
    "91 2e a6 03 20 76 ae a0 08 a9 30 a6 03 f0 02 a9 d0"
    "91 00 68 a0 0a 91 2e 60"
)
assert len(CAVE_TWO_BULLET) == 76

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


def apply(rom_data) -> list[str]:
    min_len = max(
        OFF_CAVE_GATE + len(CAVE_GATE),
        OFF_CAVE_TWO_BULLET + len(CAVE_TWO_BULLET),
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
        (ORIG_WAIT, OLD_HOOK_WAIT),
        "$AF2B old Gargoyle rapid-fire hook",
    )
    _ensure_available(rom_data, OFF_CAVE_GATE, CAVE_GATE, "Gargoyle two-bullet gate")
    _ensure_available(
        rom_data,
        OFF_CAVE_TWO_BULLET,
        CAVE_TWO_BULLET,
        "Gargoyle two-bullet body",
    )

    changed: list[str] = []
    _write(rom_data, OFF_CAVE_GATE, CAVE_GATE, changed, "Gargoyle two-bullet gate $BCFF")
    _write(
        rom_data,
        OFF_CAVE_TWO_BULLET,
        CAVE_TWO_BULLET,
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
    _write(
        rom_data,
        OFF_HOOK_OLD_WAIT,
        ORIG_WAIT,
        changed,
        "$AF2B restore old Gargoyle rapid wait hook",
    )
    return changed

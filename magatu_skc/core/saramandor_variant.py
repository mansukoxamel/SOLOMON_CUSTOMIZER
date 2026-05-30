"""Saramandor variant bullet behavior.

JP/JPC66 only.  This patch makes the unused Saramandor #2 IDs act as a
clean variant without changing the global Bullet speed table:

  $5E/$5F -> Bullet, normal speed
  $62/$63 -> Bullet, normal speed
  $66/$67 -> reserved / unchanged for now

Those active #2 IDs also use a 6-tile horizontal Dana reaction range.  The
stock Saramandor/Dragon shared distance check remains at the original range.
"""

from __future__ import annotations


class SaramandorVariantError(ValueError):
    pass


def _cf(cpu: int) -> int:
    return 0x10 + (cpu - 0x8000)


# Hooks in bank0 PRG.  These offsets are unchanged after mapper66 expansion.
OFF_HOOK_SPAWN_SETUP = _cf(0xB105)
OFF_HOOK_SUBSTATUS = _cf(0xB0A9)
OFF_HOOK_FLAME_BEHAVIOR = _cf(0xB0C6)
OFF_HOOK_CHILD_MARK = _cf(0xB121)
OFF_HOOK_BULLET_INIT = _cf(0xAFD1)
OFF_HOOK_ENTITY_SPEED_INIT = _cf(0x866D)
OFF_HOOK_DISTANCE_CHECK = _cf(0xB1E9)

ORIG_SPAWN_SETUP = bytes.fromhex("a9 04 85 05 a9 c6 85 04 66 02 a9 05 2a aa")
ORIG_SUBSTATUS = bytes.fromhex("20 d9 b0 09 02 91 00")
ORIG_FLAME_BEHAVIOR = bytes.fromhex("20 5e b0")
ORIG_CHILD_MARK = bytes.fromhex("20 1c 9d")
ORIG_BULLET_INIT = bytes.fromhex("a9 08 11 2e 91 2e 60")
ORIG_ENTITY_SPEED_INIT = bytes.fromhex("20 c0 8a")
ORIG_DISTANCE_CHECK = bytes.fromhex(
    "a0 05 b1 2c 0a b0 02 49 ff c9 14 b0 0a"
    "88 b1 2c 0a b0 02 49 ff c9 10 60"
)

HOOK_SPAWN_SETUP = bytes.fromhex("20 00 be") + bytes([0xEA] * 11)
HOOK_SUBSTATUS = bytes.fromhex("20 40 be") + bytes([0xEA] * 4)
HOOK_FLAME_BEHAVIOR = bytes.fromhex("20 80 be")
BAD_HOOK_CHILD_MARK_CLEANUP = bytes.fromhex("20 9f be")
HOOK_DISTANCE_CHECK = bytes.fromhex("4c 00 bf")
HOOK_PANEL_STAGE_SPEED_GUARD = bytes.fromhex("20 a4 e7")
HOOK_PANEL_STAGE_SPEED_GUARD_OLD = bytes.fromhex("20 76 e8")


# Cave layout.  $BE00-$BEFF is inside the JP bank0 cave and must be registered
# as a reserved span in room_flags.py.
OFF_CAVE_SPAWN_SETUP = _cf(0xBE00)
OFF_CAVE_SUBSTATUS = _cf(0xBE40)
OFF_CAVE_FLAME_BEHAVIOR = _cf(0xBE80)
OFF_CAVE_DISTANCE_CHECK = _cf(0xBF00)

CAVE_SPAWN_SETUP = bytes.fromhex(
    # If parent type is $5E/$5F/$62/$63, spawn Bullet type $20.
    # Otherwise reproduce the original Flame setup.
    "a0 01 b1 2e c9 5e 90 18 c9 64 b0 14 29 02 f0 10"
    "a9 20 85 05 a9 c0 85 04 a0 03 b1 2e 29 01 aa 60"
    "a9 04 85 05 a9 c6 85 04 66 02 a9 05 2a aa 60"
)

CAVE_SUBSTATUS = bytes.fromhex(
    # Original: JSR $B0D9 / ORA #$02 / STA ($00),Y.
    # For Bullet variants, skip ORA #$02.
    "20 d9 b0 48 a0 01 b1 2e c9 5e 90 0e c9 64 b0 0a"
    "29 02 f0 06 68 a0 00 91 00 60"
    "68 09 02 a0 00 91 00 60"
)

CAVE_FLAME_BEHAVIOR = bytes.fromhex(
    # For Bullet variants, do not run the Flame-specific behavior setup.
    "a0 01 b1 2e c9 5e 90 09 c9 64 b0 05 29 02 f0 01 60"
    "4c 5e b0"
)

CAVE_DISTANCE_CHECK = bytes.fromhex(
    # Replacement for SUB_B1E9.
    # #2 Saramandor IDs $5E/$5F/$62/$63 get X threshold $60 (6 tiles).
    # Everything else, including stock Saramandor and Dragon, uses $14.
    "a0 01 b1 2e c9 5e 90 20 c9 64 b0 1c 29 02 f0 18"
    "a0 05 b1 2c 0a b0 02 49 ff c9 60 b0 0a"
    "88 b1 2c 0a b0 02 49 ff c9 10 60"
    "a0 05 b1 2c 0a b0 02 49 ff c9 14 b0 0a"
    "88 b1 2c 0a b0 02 49 ff c9 10 60"
)

RESERVED_SPANS = (
    (OFF_CAVE_SPAWN_SETUP, len(CAVE_SPAWN_SETUP)),
    (OFF_CAVE_SUBSTATUS, len(CAVE_SUBSTATUS)),
    (OFF_CAVE_FLAME_BEHAVIOR, len(CAVE_FLAME_BEHAVIOR)),
    (OFF_CAVE_DISTANCE_CHECK, len(CAVE_DISTANCE_CHECK)),
)


def _expect_or_hooked(
    rom_data,
    off: int,
    orig: bytes,
    hook: bytes,
    name: str,
    extra_hooks: tuple[bytes, ...] = (),
) -> None:
    cur = bytes(rom_data[off:off + len(orig)])
    if cur == orig:
        return
    for accepted in (hook, *extra_hooks):
        if cur[:len(accepted)] == accepted:
            return
    raise SaramandorVariantError(
        f"{name} signature mismatch at file 0x{off:X}: "
        f"expected {orig.hex(' ')} or hook {hook.hex(' ')}, got {cur.hex(' ')}"
    )


def _write_blob(rom_data, off: int, blob: bytes, changed: list[str], name: str) -> None:
    if bytes(rom_data[off:off + len(blob)]) != blob:
        rom_data[off:off + len(blob)] = blob
        changed.append(name)


def apply(rom_data) -> list[str]:
    """Apply the always-on Saramandor variant patch."""
    if rom_data is None or len(rom_data) < OFF_CAVE_DISTANCE_CHECK + len(CAVE_DISTANCE_CHECK):
        raise SaramandorVariantError("ROM is too short for Saramandor variant patch.")

    _expect_or_hooked(rom_data, OFF_HOOK_SPAWN_SETUP, ORIG_SPAWN_SETUP, HOOK_SPAWN_SETUP, "$B105")
    _expect_or_hooked(rom_data, OFF_HOOK_SUBSTATUS, ORIG_SUBSTATUS, HOOK_SUBSTATUS, "$B0A9")
    _expect_or_hooked(rom_data, OFF_HOOK_FLAME_BEHAVIOR, ORIG_FLAME_BEHAVIOR, HOOK_FLAME_BEHAVIOR, "$B0C6")
    _expect_or_hooked(
        rom_data,
        OFF_HOOK_CHILD_MARK,
        ORIG_CHILD_MARK,
        ORIG_CHILD_MARK,
        "$B121",
        extra_hooks=(BAD_HOOK_CHILD_MARK_CLEANUP,),
    )
    _expect_or_hooked(rom_data, OFF_HOOK_BULLET_INIT, ORIG_BULLET_INIT, ORIG_BULLET_INIT, "$AFD1")
    _expect_or_hooked(
        rom_data,
        OFF_HOOK_ENTITY_SPEED_INIT,
        ORIG_ENTITY_SPEED_INIT,
        ORIG_ENTITY_SPEED_INIT,
        "$866D",
        extra_hooks=(HOOK_PANEL_STAGE_SPEED_GUARD, HOOK_PANEL_STAGE_SPEED_GUARD_OLD),
    )
    _expect_or_hooked(rom_data, OFF_HOOK_DISTANCE_CHECK, ORIG_DISTANCE_CHECK, HOOK_DISTANCE_CHECK, "$B1E9")

    changed: list[str] = []
    _write_blob(rom_data, OFF_CAVE_SPAWN_SETUP, CAVE_SPAWN_SETUP, changed, "Saramandor variant cave $BE00")
    _write_blob(rom_data, OFF_CAVE_SUBSTATUS, CAVE_SUBSTATUS, changed, "Saramandor variant cave $BE40")
    _write_blob(rom_data, OFF_CAVE_FLAME_BEHAVIOR, CAVE_FLAME_BEHAVIOR, changed, "Saramandor variant cave $BE80")
    _write_blob(rom_data, OFF_CAVE_DISTANCE_CHECK, CAVE_DISTANCE_CHECK, changed, "Saramandor variant cave $BF00")

    _write_blob(rom_data, OFF_HOOK_SPAWN_SETUP, HOOK_SPAWN_SETUP, changed, "$B105 Saramandor spawn hook")
    _write_blob(rom_data, OFF_HOOK_SUBSTATUS, HOOK_SUBSTATUS, changed, "$B0A9 Saramandor substatus hook")
    _write_blob(rom_data, OFF_HOOK_FLAME_BEHAVIOR, HOOK_FLAME_BEHAVIOR, changed, "$B0C6 Saramandor flame-behavior hook")
    _write_blob(rom_data, OFF_HOOK_CHILD_MARK, ORIG_CHILD_MARK, changed, "$B121 restore stock Saramandor child setup")
    _write_blob(rom_data, OFF_HOOK_DISTANCE_CHECK, HOOK_DISTANCE_CHECK, changed, "$B1E9 Saramandor #2 distance hook")
    return changed

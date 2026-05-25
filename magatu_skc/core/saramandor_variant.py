"""Saramandor variant bullet behavior.

JP/JPC66 only.  This patch makes the unused Saramandor #2 IDs act as a
clean variant without changing the global Bullet speed table:

  $5E/$5F -> Bullet, normal speed
  $62/$63 -> Bullet, 1/4 speed
  $66/$67 -> reserved / unchanged for now

The slow bullet is marked only on the child main-slot spawned by Saramandor.
Main-slot +12 is only a fresh-spawn hint; it is the stock animation timer and
does not persist.  Bullet state0 changes behavior after its short wait and the
generic entity loop calls $8AC0 again, so the wrapper also treats an already
quarter-speed Bullet (Xv=$10/$F0) as slow during later reinitialization.
Normal Bullet / Panel Monster Bullet entities are not affected.
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

ORIG_SPAWN_SETUP = bytes.fromhex("a9 04 85 05 a9 c6 85 04 66 02 a9 05 2a aa")
ORIG_SUBSTATUS = bytes.fromhex("20 d9 b0 09 02 91 00")
ORIG_FLAME_BEHAVIOR = bytes.fromhex("20 5e b0")
ORIG_CHILD_MARK = bytes.fromhex("20 1c 9d")
ORIG_BULLET_INIT = bytes.fromhex("a9 08 11 2e 91 2e 60")
ORIG_ENTITY_SPEED_INIT = bytes.fromhex("20 c0 8a")

HOOK_SPAWN_SETUP = bytes.fromhex("20 00 be") + bytes([0xEA] * 11)
HOOK_SUBSTATUS = bytes.fromhex("20 40 be") + bytes([0xEA] * 4)
HOOK_FLAME_BEHAVIOR = bytes.fromhex("20 80 be")
HOOK_CHILD_MARK = bytes.fromhex("20 a0 be")
HOOK_BULLET_INIT = bytes.fromhex("4c c0 be") + bytes([0xEA] * 4)
HOOK_ENTITY_SPEED_INIT = bytes.fromhex("20 00 bf")


# Cave layout.  $BE00-$BEFF is inside the JP bank0 cave and must be registered
# as a reserved span in room_flags.py.
OFF_CAVE_SPAWN_SETUP = _cf(0xBE00)
OFF_CAVE_SUBSTATUS = _cf(0xBE40)
OFF_CAVE_FLAME_BEHAVIOR = _cf(0xBE80)
OFF_CAVE_CHILD_MARK = _cf(0xBEA0)
OFF_CAVE_BULLET_INIT = _cf(0xBEC0)
OFF_CAVE_ENTITY_SPEED_INIT = _cf(0xBF00)

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

CAVE_CHILD_MARK = bytes.fromhex(
    # Wrap JSR $9D1C.  For Saramandor #2 speed 2 only ($62/$63), mark the
    # spawned Bullet's main-slot +12 as a short-lived fresh-spawn hint.
    # Main-slot +2 cannot be used because the entity loop copies current type
    # into +2 before calling $8AC0.  Main-slot +12 is later reused by animation,
    # so CAVE_ENTITY_SPEED_INIT must not rely on it as persistent state.
    "20 1c 9d"
    "a0 01 b1 2e c9 62 90 0a c9 64 b0 06"
    "a0 0c a9 a5 91 00"
    "60"
)

CAVE_BULLET_INIT = bytes.fromhex(
    # Original Bullet state0 behavior update.  Slow speed is applied later by
    # CAVE_ENTITY_SPEED_INIT, after the stock $8AC0 initializer loads velocity.
    "a9 08 11 2e 91 2e 60"
)

CAVE_ENTITY_SPEED_INIT = bytes.fromhex(
    # Wrapper for $866D: JSR $8AC0.
    # Check the +12 marker before calling $8AC0.  A/Y are part of $8AC0's input
    # contract, so they must be restored exactly before entering stock code.
    # Entity +12 is the stock animation timer and may be overwritten before
    # Bullet's behavior-transition reinit.  If the Bullet already has Xv=$10 or
    # $F0 from the first slow init, keep treating it as slow.
    "48 98 48"
    "a0 01 b1 08 c9 20 d0 31"
    "a0 0c b1 08 c9 a5 f0 0c"
    "a0 08 b1 08 c9 10 f0 04 c9 f0 d0 1d"
    "68 a8 68"
    "20 c0 8a"
    "a0 03 b1 08 29 01 aa"
    "bd 3a bf"
    "a0 08 91 08"
    "a0 05 a9 00 91 08"
    "60"
    "10 f0"
    "68 a8 68"
    "4c c0 8a"
) + bytes([0xEA] * (80 - len(bytes.fromhex(
    "48 98 48"
    "a0 01 b1 08 c9 20 d0 31"
    "a0 0c b1 08 c9 a5 f0 0c"
    "a0 08 b1 08 c9 10 f0 04 c9 f0 d0 1d"
    "68 a8 68"
    "20 c0 8a"
    "a0 03 b1 08 29 01 aa"
    "bd 3a bf"
    "a0 08 91 08"
    "a0 05 a9 00 91 08"
    "60"
    "10 f0"
    "68 a8 68"
    "4c c0 8a"
))))

RESERVED_SPANS = (
    (OFF_CAVE_SPAWN_SETUP, len(CAVE_SPAWN_SETUP)),
    (OFF_CAVE_SUBSTATUS, len(CAVE_SUBSTATUS)),
    (OFF_CAVE_FLAME_BEHAVIOR, len(CAVE_FLAME_BEHAVIOR)),
    (OFF_CAVE_CHILD_MARK, len(CAVE_CHILD_MARK)),
    (OFF_CAVE_BULLET_INIT, len(CAVE_BULLET_INIT)),
    (OFF_CAVE_ENTITY_SPEED_INIT, len(CAVE_ENTITY_SPEED_INIT)),
)


def _expect_or_hooked(rom_data, off: int, orig: bytes, hook: bytes, name: str) -> None:
    cur = bytes(rom_data[off:off + len(orig)])
    if cur == orig:
        return
    if cur[:len(hook)] == hook:
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
    if rom_data is None or len(rom_data) < OFF_CAVE_BULLET_INIT + len(CAVE_BULLET_INIT):
        raise SaramandorVariantError("ROM is too short for Saramandor variant patch.")

    _expect_or_hooked(rom_data, OFF_HOOK_SPAWN_SETUP, ORIG_SPAWN_SETUP, HOOK_SPAWN_SETUP, "$B105")
    _expect_or_hooked(rom_data, OFF_HOOK_SUBSTATUS, ORIG_SUBSTATUS, HOOK_SUBSTATUS, "$B0A9")
    _expect_or_hooked(rom_data, OFF_HOOK_FLAME_BEHAVIOR, ORIG_FLAME_BEHAVIOR, HOOK_FLAME_BEHAVIOR, "$B0C6")
    _expect_or_hooked(rom_data, OFF_HOOK_CHILD_MARK, ORIG_CHILD_MARK, HOOK_CHILD_MARK, "$B121")
    _expect_or_hooked(rom_data, OFF_HOOK_BULLET_INIT, ORIG_BULLET_INIT, HOOK_BULLET_INIT, "$AFD1")
    cur_speed_hook = bytes(rom_data[OFF_HOOK_ENTITY_SPEED_INIT:OFF_HOOK_ENTITY_SPEED_INIT + 3])
    if cur_speed_hook not in (ORIG_ENTITY_SPEED_INIT, HOOK_ENTITY_SPEED_INIT):
        raise SaramandorVariantError(
            f"$866D signature mismatch at file 0x{OFF_HOOK_ENTITY_SPEED_INIT:X}: "
            f"expected {ORIG_ENTITY_SPEED_INIT.hex(' ')} or hook "
            f"{HOOK_ENTITY_SPEED_INIT.hex(' ')}, "
            f"got {cur_speed_hook.hex(' ')}"
        )

    changed: list[str] = []
    _write_blob(rom_data, OFF_CAVE_SPAWN_SETUP, CAVE_SPAWN_SETUP, changed, "Saramandor variant cave $BE00")
    _write_blob(rom_data, OFF_CAVE_SUBSTATUS, CAVE_SUBSTATUS, changed, "Saramandor variant cave $BE40")
    _write_blob(rom_data, OFF_CAVE_FLAME_BEHAVIOR, CAVE_FLAME_BEHAVIOR, changed, "Saramandor variant cave $BE80")
    _write_blob(rom_data, OFF_CAVE_CHILD_MARK, CAVE_CHILD_MARK, changed, "Saramandor variant cave $BEA0")
    _write_blob(rom_data, OFF_CAVE_BULLET_INIT, CAVE_BULLET_INIT, changed, "Saramandor variant cave $BEC0")
    _write_blob(rom_data, OFF_CAVE_ENTITY_SPEED_INIT, CAVE_ENTITY_SPEED_INIT, changed, "Saramandor variant cave $BF00")

    _write_blob(rom_data, OFF_HOOK_SPAWN_SETUP, HOOK_SPAWN_SETUP, changed, "$B105 Saramandor spawn hook")
    _write_blob(rom_data, OFF_HOOK_SUBSTATUS, HOOK_SUBSTATUS, changed, "$B0A9 Saramandor substatus hook")
    _write_blob(rom_data, OFF_HOOK_FLAME_BEHAVIOR, HOOK_FLAME_BEHAVIOR, changed, "$B0C6 Saramandor flame-behavior hook")
    _write_blob(rom_data, OFF_HOOK_CHILD_MARK, HOOK_CHILD_MARK, changed, "$B121 Saramandor slow-marker hook")
    _write_blob(rom_data, OFF_HOOK_BULLET_INIT, HOOK_BULLET_INIT, changed, "$AFD1 Bullet slow-marker hook")
    if bytes(rom_data[OFF_HOOK_ENTITY_SPEED_INIT:OFF_HOOK_ENTITY_SPEED_INIT + 3]) != HOOK_ENTITY_SPEED_INIT:
        _write_blob(rom_data, OFF_HOOK_ENTITY_SPEED_INIT, HOOK_ENTITY_SPEED_INIT, changed, "$866D Bullet slow-speed wrapper hook")
    return changed

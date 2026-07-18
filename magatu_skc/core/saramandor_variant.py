"""Saramandor variant bullet behavior.

JP/JPC66 only.  This patch makes the unused Saramandor #2 IDs act as a
clean variant without changing the global Bullet speed table:

  $5E/$5F -> Bullet, movement speed 1, configurable flame speed
  $62-$67 -> stock behavior

Those active #2 IDs also use a 6-tile horizontal Dana reaction range.  The
stock Saramandor/Dragon shared distance check remains at the original range.
"""

from __future__ import annotations


class SaramandorVariantError(ValueError):
    pass


def _cf(cpu: int) -> int:
    return 0x10 + (cpu - 0x8000)


def _word(cpu: int) -> bytes:
    return bytes((cpu & 0xFF, (cpu >> 8) & 0xFF))


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

CPU_CAVE_SPAWN_SETUP = 0xE3C9
CPU_CAVE_SUBSTATUS = CPU_CAVE_SPAWN_SETUP + 0x29
CPU_CAVE_FLAME_BEHAVIOR = CPU_CAVE_SUBSTATUS + 0x1C
CPU_CAVE_DISTANCE_CHECK = CPU_CAVE_FLAME_BEHAVIOR + 0x0E
CPU_CAVE_CHILD_MARK = 0xE456

HOOK_SPAWN_SETUP = bytes((0x20, *(_word(CPU_CAVE_SPAWN_SETUP)))) + bytes([0xEA] * 11)
HOOK_SUBSTATUS = bytes((0x20, *(_word(CPU_CAVE_SUBSTATUS)))) + bytes([0xEA] * 4)
HOOK_FLAME_BEHAVIOR = bytes((0x20, *(_word(CPU_CAVE_FLAME_BEHAVIOR))))
HOOK_CHILD_MARK = bytes((0x20, *(_word(CPU_CAVE_CHILD_MARK))))
BAD_HOOK_CHILD_MARK_CLEANUP = bytes.fromhex("20 9f be")
HOOK_DISTANCE_CHECK = bytes((0x4C, *(_word(CPU_CAVE_DISTANCE_CHECK))))
HOOK_PANEL_STAGE_SPEED_GUARD = bytes.fromhex("20 a4 e7")
HOOK_PANEL_STAGE_SPEED_GUARD_OLD = bytes.fromhex("20 76 e8")


# Packed PRG0 cleanup layout.
OFF_CAVE_SPAWN_SETUP = _cf(CPU_CAVE_SPAWN_SETUP)
OFF_CAVE_SUBSTATUS = _cf(CPU_CAVE_SUBSTATUS)
OFF_CAVE_FLAME_BEHAVIOR = _cf(CPU_CAVE_FLAME_BEHAVIOR)
OFF_CAVE_DISTANCE_CHECK = _cf(CPU_CAVE_DISTANCE_CHECK)
OFF_CAVE_CHILD_MARK = _cf(CPU_CAVE_CHILD_MARK)

SPEED_PRESET_QUARTER = 0
SPEED_PRESET_HALF = 1
SPEED_PRESET_NORMAL = 4
SELECTABLE_SPEED_PRESETS = (
    SPEED_PRESET_NORMAL,
    SPEED_PRESET_HALF,
    SPEED_PRESET_QUARTER,
)
DEFAULT_SPEED_PRESET = SPEED_PRESET_NORMAL
SPEED_PRESET_MARKERS = {
    SPEED_PRESET_NORMAL: 0x00,
    SPEED_PRESET_HALF: 0x89,
    SPEED_PRESET_QUARTER: 0x88,
}

CAVE_SPAWN_SETUP = bytes.fromhex(
    # Only parent type $5E/$5F spawns Bullet type $20.
    # Otherwise reproduce the original Flame setup.
    "a0 01 b1 2e 29 fe c9 5e d0 10"
    "a9 20 85 05 a9 c0 85 04 a0 03 b1 2e 29 01 aa 60"
    "a9 04 85 05 a9 c6 85 04 66 02 a9 05 2a aa 60"
)

CAVE_SUBSTATUS = bytes.fromhex(
    # Original: JSR $B0D9 / ORA #$02 / STA ($00),Y.
    # For Bullet variants, skip ORA #$02.
    "20 d9 b0 48 a0 01 b1 2e 29 fe c9 5e d0 06"
    "68 a0 00 91 00 60"
    "68 09 02 a0 00 91 00 60"
)

CAVE_FLAME_BEHAVIOR = bytes.fromhex(
    # For Bullet variants, do not run the Flame-specific behavior setup.
    "a0 01 b1 2e 29 fe c9 5e d0 01 60"
    "4c 5e b0"
)

CAVE_DISTANCE_CHECK = bytes.fromhex(
    # Replacement for SUB_B1E9.
    # #2 Saramandor IDs $5E/$5F get X threshold $60 (6 tiles).
    # Everything else, including stock Saramandor and Dragon, uses $14.
    "a0 01 b1 2e 29 fe c9 5e d0 18"
    "a0 05 b1 2c 0a b0 02 49 ff c9 60 b0 0a"
    "88 b1 2c 0a b0 02 49 ff c9 10 60"
    "a0 05 b1 2c 0a b0 02 49 ff c9 14 b0 0a"
    "88 b1 2c 0a b0 02 49 ff c9 10 60"
)
CAVE_CHILD_MARK = bytes.fromhex(
    # Preserve the register state left by $9D1C.  Enhanced Saramandor
    # $5E/$5F writes its selected speed marker to the spawned Bullet's
    # sub-slot[7]; stock Saramandor and Dragon only run the original call.
    "20 1c 9d 48 8a 48 98 48"
    "a0 01 b1 2e 29 fe c9 5e d0 0d"
    "a0 07 b1 2c 20 56 b1 a9 00 a0 07 91 00"
    "68 a8 68 aa 68 60"
)
assert len(CAVE_CHILD_MARK) == 37
OFF_CAVE_SPEED_MARKER_VALUE = OFF_CAVE_CHILD_MARK + 0x1A
_CHILD_MARK_MASK = bytearray(CAVE_CHILD_MARK)
_CHILD_MARK_MASK[OFF_CAVE_SPEED_MARKER_VALUE - OFF_CAVE_CHILD_MARK] = 0x00
_CHILD_MARK_MASK = bytes(_CHILD_MARK_MASK)
assert CPU_CAVE_SUBSTATUS == CPU_CAVE_SPAWN_SETUP + len(CAVE_SPAWN_SETUP)
assert CPU_CAVE_FLAME_BEHAVIOR == CPU_CAVE_SUBSTATUS + len(CAVE_SUBSTATUS)
assert CPU_CAVE_DISTANCE_CHECK == CPU_CAVE_FLAME_BEHAVIOR + len(CAVE_FLAME_BEHAVIOR)
assert CPU_CAVE_CHILD_MARK == CPU_CAVE_DISTANCE_CHECK + len(CAVE_DISTANCE_CHECK)

RESERVED_SPANS = (
    (
        OFF_CAVE_SPAWN_SETUP,
        len(CAVE_SPAWN_SETUP)
        + len(CAVE_SUBSTATUS)
        + len(CAVE_FLAME_BEHAVIOR)
        + len(CAVE_DISTANCE_CHECK)
        + len(CAVE_CHILD_MARK),
    ),
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


def normalize_speed_preset(value) -> int:
    try:
        preset = int(value)
    except (TypeError, ValueError):
        preset = DEFAULT_SPEED_PRESET
    if preset not in SELECTABLE_SPEED_PRESETS:
        raise SaramandorVariantError(
            f"unsupported Enhanced Saramandor flame speed preset: {value!r}"
        )
    return preset


def _marker_for_speed_preset(preset: int) -> int:
    return SPEED_PRESET_MARKERS[normalize_speed_preset(preset)]


def _speed_preset_from_marker(marker: int) -> int:
    for preset, value in SPEED_PRESET_MARKERS.items():
        if int(marker) == value:
            return preset
    raise SaramandorVariantError(
        f"unsupported Enhanced Saramandor flame speed marker: ${int(marker):02X}"
    )


def _is_child_mark_blob(blob: bytes) -> bool:
    if len(blob) < len(CAVE_CHILD_MARK):
        return False
    current = bytearray(blob[:len(CAVE_CHILD_MARK)])
    current[OFF_CAVE_SPEED_MARKER_VALUE - OFF_CAVE_CHILD_MARK] = 0x00
    return bytes(current) == _CHILD_MARK_MASK


def current_speed_preset(rom_data) -> int:
    if rom_data is None or len(rom_data) < OFF_CAVE_CHILD_MARK + len(CAVE_CHILD_MARK):
        raise SaramandorVariantError("ROM is too short for Saramandor variant patch.")
    hook = bytes(rom_data[OFF_HOOK_CHILD_MARK:OFF_HOOK_CHILD_MARK + len(ORIG_CHILD_MARK)])
    if hook in (ORIG_CHILD_MARK, BAD_HOOK_CHILD_MARK_CLEANUP):
        return DEFAULT_SPEED_PRESET
    if hook != HOOK_CHILD_MARK:
        raise SaramandorVariantError(
            f"$B121 signature mismatch at file 0x{OFF_HOOK_CHILD_MARK:X}: "
            f"got {hook.hex(' ')}"
        )
    blob = bytes(rom_data[OFF_CAVE_CHILD_MARK:OFF_CAVE_CHILD_MARK + len(CAVE_CHILD_MARK)])
    if not _is_child_mark_blob(blob):
        raise SaramandorVariantError(
            f"Enhanced Saramandor speed helper mismatch at file 0x{OFF_CAVE_CHILD_MARK:X}."
        )
    return _speed_preset_from_marker(rom_data[OFF_CAVE_SPEED_MARKER_VALUE])


def _build_child_mark(speed_preset: int) -> bytes:
    body = bytearray(CAVE_CHILD_MARK)
    body[OFF_CAVE_SPEED_MARKER_VALUE - OFF_CAVE_CHILD_MARK] = _marker_for_speed_preset(speed_preset)
    return bytes(body)


def _ensure_child_mark_available(rom_data) -> None:
    current = bytes(rom_data[OFF_CAVE_CHILD_MARK:OFF_CAVE_CHILD_MARK + len(CAVE_CHILD_MARK)])
    if _is_child_mark_blob(current) or all(value in (0x00, 0xEA) for value in current):
        return
    raise SaramandorVariantError(
        f"Enhanced Saramandor speed helper area is occupied at file 0x{OFF_CAVE_CHILD_MARK:X}."
    )


def apply(rom_data, speed_preset=None) -> list[str]:
    """Apply the always-on Saramandor variant patch."""
    if rom_data is None or len(rom_data) < OFF_CAVE_CHILD_MARK + len(CAVE_CHILD_MARK):
        raise SaramandorVariantError("ROM is too short for Saramandor variant patch.")
    from . import panel_monster_stage_variant

    if speed_preset is None:
        speed_preset = current_speed_preset(rom_data)
    speed_preset = normalize_speed_preset(speed_preset)
    child_mark = _build_child_mark(speed_preset)

    _expect_or_hooked(rom_data, OFF_HOOK_SPAWN_SETUP, ORIG_SPAWN_SETUP, HOOK_SPAWN_SETUP, "$B105")
    _expect_or_hooked(rom_data, OFF_HOOK_SUBSTATUS, ORIG_SUBSTATUS, HOOK_SUBSTATUS, "$B0A9")
    _expect_or_hooked(rom_data, OFF_HOOK_FLAME_BEHAVIOR, ORIG_FLAME_BEHAVIOR, HOOK_FLAME_BEHAVIOR, "$B0C6")
    _expect_or_hooked(
        rom_data,
        OFF_HOOK_CHILD_MARK,
        ORIG_CHILD_MARK,
        HOOK_CHILD_MARK,
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
        extra_hooks=(
            panel_monster_stage_variant.HOOK_SPEED_INIT_CALL,
            panel_monster_stage_variant.PRE_COMPACT_HOOK_SPEED_INIT_CALL,
            HOOK_PANEL_STAGE_SPEED_GUARD,
            HOOK_PANEL_STAGE_SPEED_GUARD_OLD,
        ),
    )
    _expect_or_hooked(rom_data, OFF_HOOK_DISTANCE_CHECK, ORIG_DISTANCE_CHECK, HOOK_DISTANCE_CHECK, "$B1E9")
    _ensure_child_mark_available(rom_data)

    changed: list[str] = []
    _write_blob(rom_data, OFF_CAVE_SPAWN_SETUP, CAVE_SPAWN_SETUP, changed, "Saramandor variant cave $E3C9")
    _write_blob(rom_data, OFF_CAVE_SUBSTATUS, CAVE_SUBSTATUS, changed, "Saramandor variant cave $E3F2")
    _write_blob(rom_data, OFF_CAVE_FLAME_BEHAVIOR, CAVE_FLAME_BEHAVIOR, changed, "Saramandor variant cave $E40E")
    _write_blob(rom_data, OFF_CAVE_DISTANCE_CHECK, CAVE_DISTANCE_CHECK, changed, "Saramandor variant cave $E41C")
    _write_blob(rom_data, OFF_CAVE_CHILD_MARK, child_mark, changed, "Saramandor flame-speed helper $E456")

    _write_blob(rom_data, OFF_HOOK_SPAWN_SETUP, HOOK_SPAWN_SETUP, changed, "$B105 Saramandor spawn hook")
    _write_blob(rom_data, OFF_HOOK_SUBSTATUS, HOOK_SUBSTATUS, changed, "$B0A9 Saramandor substatus hook")
    _write_blob(rom_data, OFF_HOOK_FLAME_BEHAVIOR, HOOK_FLAME_BEHAVIOR, changed, "$B0C6 Saramandor flame-behavior hook")
    _write_blob(rom_data, OFF_HOOK_CHILD_MARK, HOOK_CHILD_MARK, changed, "$B121 Saramandor flame-speed marker hook")
    _write_blob(rom_data, OFF_HOOK_DISTANCE_CHECK, HOOK_DISTANCE_CHECK, changed, "$B1E9 Saramandor #2 distance hook")
    return changed

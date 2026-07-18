"""Saramandor variant bullet behavior.

JP/JPC66 only.  This patch makes the unused Saramandor #2 IDs act as a
clean variant without changing the global Bullet speed table:

  $5E/$5F -> Enhanced Saramandor A
  $62/$63 -> Enhanced Saramandor B
  $66/$67 -> Enhanced Saramandor C

Each identity has independent movement speed, flame speed, re-fire wait, and
post-fire stop settings.

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
OFF_HOOK_REFIRE_WAIT = _cf(0xB17B)
OFF_HOOK_FIRE_STATE_EXIT = _cf(0xB0B3)

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
ORIG_REFIRE_WAIT = bytes.fromhex("a0 01 b1 2c c9 20 90 05")
ORIG_FIRE_STATE_EXIT = bytes.fromhex("e0 34 90")

CPU_CAVE_SPAWN_SETUP = 0xE3C9
CPU_CAVE_SUBSTATUS = 0xE3ED
CPU_CAVE_FLAME_BEHAVIOR = 0xE402
CPU_CAVE_DISTANCE_CHECK = 0xE40B
CPU_CAVE_CHILD_MARK = 0xE430
CPU_CAVE_REFIRE_WAIT = 0xE448
CPU_CAVE_FIRE_STATE_EXIT = 0xE465
CPU_CAVE_EXTENSION = 0xE9A9

HOOK_SPAWN_SETUP = bytes((0x20, *(_word(CPU_CAVE_SPAWN_SETUP)))) + bytes([0xEA] * 11)
HOOK_SUBSTATUS = bytes((0x20, *(_word(CPU_CAVE_SUBSTATUS)))) + bytes([0xEA] * 4)
HOOK_FLAME_BEHAVIOR = bytes((0x20, *(_word(CPU_CAVE_FLAME_BEHAVIOR))))
HOOK_CHILD_MARK = bytes((0x20, *(_word(CPU_CAVE_CHILD_MARK))))
BAD_HOOK_CHILD_MARK_CLEANUP = bytes.fromhex("20 9f be")
HOOK_DISTANCE_CHECK = bytes((0x4C, *(_word(CPU_CAVE_DISTANCE_CHECK))))
HOOK_REFIRE_WAIT = bytes((0x20, *(_word(CPU_CAVE_REFIRE_WAIT)), 0x90, 0x08, 0xEA, 0xEA, 0xEA))
HOOK_FIRE_STATE_EXIT = bytes((0x4C, *(_word(CPU_CAVE_FIRE_STATE_EXIT))))
HOOK_PANEL_STAGE_SPEED_GUARD = bytes.fromhex("20 a4 e7")
HOOK_PANEL_STAGE_SPEED_GUARD_OLD = bytes.fromhex("20 76 e8")


# Packed PRG0 cleanup layout.
OFF_CAVE_SPAWN_SETUP = _cf(CPU_CAVE_SPAWN_SETUP)
OFF_CAVE_SUBSTATUS = _cf(CPU_CAVE_SUBSTATUS)
OFF_CAVE_FLAME_BEHAVIOR = _cf(CPU_CAVE_FLAME_BEHAVIOR)
OFF_CAVE_DISTANCE_CHECK = _cf(CPU_CAVE_DISTANCE_CHECK)
OFF_CAVE_CHILD_MARK = _cf(CPU_CAVE_CHILD_MARK)
OFF_CAVE_FIRE_STATE_EXIT = _cf(CPU_CAVE_FIRE_STATE_EXIT)
OFF_CAVE_EXTENSION = _cf(CPU_CAVE_EXTENSION)

VARIANT_COUNT = 3
VARIANT_NAMES = ("A", "B", "C")
MOVEMENT_SPEED_PRESETS = (1, 2, 3)
DEFAULT_MOVEMENT_SPEEDS = (1, 2, 3)
MOVEMENT_SPEED_BASE_IDS = {1: 0x5E, 2: 0x62, 3: 0x66}

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
ORIGINAL_REFIRE_WAIT = 0x20
MIN_REFIRE_WAIT = 1
MAX_REFIRE_WAIT = 0xFF
FLAME_SPAWN_COUNTER = 0x18
ORIGINAL_POST_FIRE_STOP = 0x1C
MIN_POST_FIRE_STOP = ORIGINAL_POST_FIRE_STOP
MAX_POST_FIRE_STOP = 0xFF - FLAME_SPAWN_COUNTER

CAVE_SPAWN_SETUP = bytes.fromhex(
    # Only Enhanced Saramandor A/B/C spawns Bullet type $20.
    # Otherwise reproduce the original Flame setup.
    f"20 {_word(CPU_CAVE_EXTENSION + 42).hex()} f0 10"
    "a9 20 85 05 a9 c0 85 04 a0 03 b1 2e 29 01 aa 60"
    "a9 04 85 05 a9 c6 85 04 66 02 a9 05 2a aa 60"
)
assert len(CAVE_SPAWN_SETUP) == 36

CAVE_SUBSTATUS = bytes.fromhex(
    # Original: JSR $B0D9 / ORA #$02 / STA ($00),Y.
    # For Bullet variants, skip ORA #$02.  The shared ID helper returns Y=1;
    # DEY restores the original child-status index Y=0 before the write.
    f"20 d9 b0 48 20 {_word(CPU_CAVE_EXTENSION + 42).hex()} f0 05"
    "68 88 91 00 60"
    "68 09 02 88 91 00 60"
)
assert len(CAVE_SUBSTATUS) == 21

CAVE_FLAME_BEHAVIOR = bytes.fromhex(
    # For Bullet variants, do not run the Flame-specific behavior setup.
    f"20 {_word(CPU_CAVE_EXTENSION + 42).hex()} f0 01 60"
    "4c 5e b0"
)
assert len(CAVE_FLAME_BEHAVIOR) == 9

CAVE_DISTANCE_CHECK = bytes.fromhex(
    # Replacement for SUB_B1E9.
    # Enhanced A/B/C IDs get X threshold $60 (6 tiles).
    # Everything else, including stock Saramandor and Dragon, uses $14.
    "a0 05 b1 2c 0a b0 02 49 ff aa"
    f"20 {_word(CPU_CAVE_EXTENSION + 42).hex()} f0 06"
    "e0 60 b0 11 d0 04"
    "e0 14 b0 0b"
    "a0 04 b1 2c 0a b0 02 49 ff c9 10 60"
)
assert len(CAVE_DISTANCE_CHECK) == 37
CAVE_CHILD_MARK = bytes.fromhex(
    # Enhanced Saramandor A/B/C writes its selected flame-speed marker to the
    # spawned Bullet's sub-slot[7].  Preserve the A/B/C selector on the stack
    # because $B156 replaces A/X/Y while finding the child slot.
    f"20 1c 9d 20 {_word(CPU_CAVE_EXTENSION + 42).hex()} f0 10"
    f"48 a0 07 b1 2c 20 56 b1 68 aa bd {_word(CPU_CAVE_EXTENSION + 74).hex()} 91 00 60"
)
assert len(CAVE_CHILD_MARK) == 24
CAVE_REFIRE_WAIT = bytes.fromhex(
    # Replacement for $B17B-$B182.  Before the first attack sub-slot[7] is
    # zero, so Enhanced Saramandor retains the stock #$20 threshold.  Entering
    # state 3 allocates two child slots and leaves the nonzero second index in
    # sub-slot[7]; subsequent attacks use the configured 1-255 threshold.
    # Stock IDs always retain #$20.
    "a0 01 b1 2c aa"
    f"20 {_word(CPU_CAVE_EXTENSION + 42).hex()} f0 0f"
    "48 a0 07 b1 2c f0 07"
    f"68 a8 8a d9 {_word(CPU_CAVE_EXTENSION + 77).hex()} 60"
    "68 8a c9 20 60"
)
assert len(CAVE_REFIRE_WAIT) == 29
OFF_CAVE_REFIRE_WAIT = _cf(CPU_CAVE_REFIRE_WAIT)
CAVE_FIRE_STATE_EXIT = bytes.fromhex(
    # $B0B3 replacement.  Stock IDs retain CPX #$34.  Enhanced A/B/C
    # compare against flame spawn $18 + configured post-fire stop.  Waiting
    # jumps to the original RTS; expiry enters the untouched cleanup/state-5
    # transition, which reloads the correct directional walk speed next NMI.
    f"20 {_word(CPU_CAVE_EXTENSION + 42).hex()} f0 0c"
    f"a8 8a d9 {_word(CPU_CAVE_EXTENSION + 80).hex()} 90 0e a0 00 4c b7 b0"
    "e0 34 90 05 a0 00 4c b7 b0 4c d8 b0"
)
assert len(CAVE_FIRE_STATE_EXIT) == 29

# $E9A9 extension: movement-speed normalization, A/B/C classifier, then four
# compact three-byte parameter columns.  Only these 84 bytes are reserved.
CPU_CAVE_GROUP = CPU_CAVE_EXTENSION + 42
CPU_CAVE_PARAM_TABLE = CPU_CAVE_EXTENSION + 72
OFF_CAVE_PARAM_TABLE = _cf(CPU_CAVE_PARAM_TABLE)
PARAM_MOVEMENT = 0
PARAM_FLAME = 3
PARAM_REFIRE = 6
PARAM_STOP_END = 9

CAVE_SPEED_INIT = bytes.fromhex(
    f"48 e0 5e 90 21 e0 68 b0 1d 8a 29 02 f0 18"
    f"8a 48 38 e9 5e 4a 4a a8 b9 {_word(CPU_CAVE_PARAM_TABLE).hex()}"
    "a8 68 29 01 f0 01 c8 98 aa 68 4c a0 ed"
    "68 4c a0 ed"
)
assert len(CAVE_SPEED_INIT) == 42
CAVE_GROUP = bytes.fromhex(
    "a0 01 b1 2e 38 e9 5e c9 0a b0 10"
    "48 29 02 f0 04 68 a9 00 60"
    "68 4a 4a 18 69 01 60 a9 00 60"
)
assert len(CAVE_GROUP) == 30
assert CPU_CAVE_PARAM_TABLE == 0xE9F1
assert OFF_CAVE_EXTENSION + 84 - 1 == 0x6A0C
assert CPU_CAVE_SUBSTATUS == CPU_CAVE_SPAWN_SETUP + len(CAVE_SPAWN_SETUP)
assert CPU_CAVE_FLAME_BEHAVIOR == CPU_CAVE_SUBSTATUS + len(CAVE_SUBSTATUS)
assert CPU_CAVE_DISTANCE_CHECK == CPU_CAVE_FLAME_BEHAVIOR + len(CAVE_FLAME_BEHAVIOR)
assert CPU_CAVE_CHILD_MARK == CPU_CAVE_DISTANCE_CHECK + len(CAVE_DISTANCE_CHECK)
assert CPU_CAVE_REFIRE_WAIT == CPU_CAVE_CHILD_MARK + len(CAVE_CHILD_MARK)
assert CPU_CAVE_FIRE_STATE_EXIT == CPU_CAVE_REFIRE_WAIT + len(CAVE_REFIRE_WAIT)
assert OFF_CAVE_FIRE_STATE_EXIT + len(CAVE_FIRE_STATE_EXIT) - 1 == 0x6491

RESERVED_SPANS = (
    (
        OFF_CAVE_SPAWN_SETUP,
        len(CAVE_SPAWN_SETUP)
        + len(CAVE_SUBSTATUS)
        + len(CAVE_FLAME_BEHAVIOR)
        + len(CAVE_DISTANCE_CHECK),
    ),
    (
        OFF_CAVE_CHILD_MARK,
        len(CAVE_CHILD_MARK)
        + len(CAVE_REFIRE_WAIT)
        + len(CAVE_FIRE_STATE_EXIT),
    ),
    (OFF_CAVE_EXTENSION, 84),
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


def normalize_movement_speed(value) -> int:
    try:
        preset = int(value)
    except (TypeError, ValueError) as exc:
        raise SaramandorVariantError(
            "Enhanced Saramandor movement speed must be numeric."
        ) from exc
    if preset not in MOVEMENT_SPEED_PRESETS:
        raise SaramandorVariantError(
            f"unsupported Enhanced Saramandor movement speed: {value!r}"
        )
    return preset


def _variant_index(variant) -> int:
    try:
        index = int(variant)
    except (TypeError, ValueError) as exc:
        raise SaramandorVariantError("invalid Enhanced Saramandor variant") from exc
    if not (0 <= index < VARIANT_COUNT):
        raise SaramandorVariantError("invalid Enhanced Saramandor variant")
    return index


def _original_or_hook(rom_data, off: int, original: bytes, hook: bytes) -> bool:
    current = bytes(rom_data[off:off + len(original)])
    if current == original:
        return True
    if current != hook:
        raise SaramandorVariantError(
            f"Saramandor signature mismatch at file 0x{off:X}: got {current.hex(' ')}"
        )
    return False


def _require_extension(rom_data) -> None:
    fixed = CAVE_SPEED_INIT + CAVE_GROUP
    current = bytes(rom_data[OFF_CAVE_EXTENSION:OFF_CAVE_EXTENSION + len(fixed)])
    if current != fixed:
        raise SaramandorVariantError(
            f"Enhanced Saramandor A/B/C extension mismatch at file 0x{OFF_CAVE_EXTENSION:X}."
        )


def current_movement_speed(rom_data, variant=0) -> int:
    index = _variant_index(variant)
    if _original_or_hook(rom_data, OFF_HOOK_CHILD_MARK, ORIG_CHILD_MARK, HOOK_CHILD_MARK):
        return DEFAULT_MOVEMENT_SPEEDS[index]
    _require_extension(rom_data)
    raw = int(rom_data[OFF_CAVE_PARAM_TABLE + PARAM_MOVEMENT + index])
    for preset, base_id in MOVEMENT_SPEED_BASE_IDS.items():
        if raw == base_id:
            return preset
    raise SaramandorVariantError(f"unsupported movement-speed base ID: ${raw:02X}")


def current_speed_preset(rom_data, variant=0) -> int:
    index = _variant_index(variant)
    if _original_or_hook(rom_data, OFF_HOOK_CHILD_MARK, ORIG_CHILD_MARK, HOOK_CHILD_MARK):
        return DEFAULT_SPEED_PRESET
    _require_extension(rom_data)
    return _speed_preset_from_marker(
        rom_data[OFF_CAVE_PARAM_TABLE + PARAM_FLAME + index]
    )


def normalize_post_fire_stop(value) -> int:
    try:
        frames = int(value)
    except (TypeError, ValueError) as exc:
        raise SaramandorVariantError(
            "Enhanced Saramandor post-fire stop must be numeric."
        ) from exc
    if not (MIN_POST_FIRE_STOP <= frames <= MAX_POST_FIRE_STOP):
        raise SaramandorVariantError(
            f"Enhanced Saramandor post-fire stop must be "
            f"{MIN_POST_FIRE_STOP}-{MAX_POST_FIRE_STOP}."
        )
    return frames


def current_post_fire_stop(rom_data, variant=0) -> int:
    index = _variant_index(variant)
    if _original_or_hook(
        rom_data, OFF_HOOK_FIRE_STATE_EXIT, ORIG_FIRE_STATE_EXIT, HOOK_FIRE_STATE_EXIT
    ):
        return ORIGINAL_POST_FIRE_STOP
    _require_extension(rom_data)
    end_counter = int(rom_data[OFF_CAVE_PARAM_TABLE + PARAM_STOP_END + index])
    return normalize_post_fire_stop(end_counter - FLAME_SPAWN_COUNTER)


def normalize_refire_wait(value) -> int:
    try:
        counter = int(value)
    except (TypeError, ValueError) as exc:
        raise SaramandorVariantError(
            "Enhanced Saramandor re-fire wait must be numeric."
        ) from exc
    if not (MIN_REFIRE_WAIT <= counter <= MAX_REFIRE_WAIT):
        raise SaramandorVariantError(
            f"Enhanced Saramandor re-fire wait must be "
            f"{MIN_REFIRE_WAIT}-{MAX_REFIRE_WAIT}."
        )
    return counter


def current_refire_wait(rom_data, variant=0) -> int:
    index = _variant_index(variant)
    if _original_or_hook(rom_data, OFF_HOOK_REFIRE_WAIT, ORIG_REFIRE_WAIT, HOOK_REFIRE_WAIT):
        return ORIGINAL_REFIRE_WAIT
    _require_extension(rom_data)
    return normalize_refire_wait(
        rom_data[OFF_CAVE_PARAM_TABLE + PARAM_REFIRE + index]
    )


def _ensure_child_mark_available(rom_data) -> None:
    current = bytes(rom_data[OFF_CAVE_CHILD_MARK:OFF_CAVE_CHILD_MARK + len(CAVE_CHILD_MARK)])
    if current == CAVE_CHILD_MARK or all(value in (0x00, 0xEA) for value in current):
        return
    raise SaramandorVariantError(
        f"Enhanced Saramandor speed helper area is occupied at file 0x{OFF_CAVE_CHILD_MARK:X}."
    )


def _ensure_refire_wait_available(rom_data) -> None:
    current = bytes(
        rom_data[
            OFF_CAVE_REFIRE_WAIT:
            OFF_CAVE_REFIRE_WAIT + len(CAVE_REFIRE_WAIT)
        ]
    )
    if current == CAVE_REFIRE_WAIT or all(value in (0x00, 0xEA) for value in current):
        return
    raise SaramandorVariantError(
        f"Enhanced Saramandor re-fire helper area is occupied at "
        f"file 0x{OFF_CAVE_REFIRE_WAIT:X}."
    )


def _ensure_fire_state_exit_available(rom_data) -> None:
    current_exit = bytes(
        rom_data[
            OFF_CAVE_FIRE_STATE_EXIT:
            OFF_CAVE_FIRE_STATE_EXIT + len(CAVE_FIRE_STATE_EXIT)
        ]
    )
    exit_available = current_exit == CAVE_FIRE_STATE_EXIT or all(
        value in (0x00, 0xEA) for value in current_exit
    )
    if exit_available:
        return
    raise SaramandorVariantError(
        f"Enhanced Saramandor post-fire stop area is occupied at "
        f"file 0x{OFF_CAVE_FIRE_STATE_EXIT:X}."
    )


def _ensure_extension_available(rom_data) -> None:
    current = bytes(rom_data[OFF_CAVE_EXTENSION:OFF_CAVE_EXTENSION + 84])
    fixed = CAVE_SPEED_INIT + CAVE_GROUP
    if current[:len(fixed)] == fixed:
        return
    if all(value in (0x00, 0xEA) for value in current):
        return
    raise SaramandorVariantError(
        f"Enhanced Saramandor extension area is occupied at file 0x{OFF_CAVE_EXTENSION:X}."
    )


def _normalize_settings(variant_settings) -> list[dict[str, int]]:
    if variant_settings is None or len(variant_settings) != VARIANT_COUNT:
        raise SaramandorVariantError("Enhanced Saramandor requires A/B/C settings.")
    result = []
    for item in variant_settings:
        result.append({
            "movement_speed": normalize_movement_speed(item["movement_speed"]),
            "flame_speed": normalize_speed_preset(item["flame_speed"]),
            "refire_wait": normalize_refire_wait(item["refire_wait"]),
            "post_fire_stop": normalize_post_fire_stop(item["post_fire_stop"]),
        })
    return result


def _build_extension(variant_settings) -> bytes:
    settings = _normalize_settings(variant_settings)
    table = bytes(
        [MOVEMENT_SPEED_BASE_IDS[item["movement_speed"]] for item in settings]
        + [_marker_for_speed_preset(item["flame_speed"]) for item in settings]
        + [item["refire_wait"] for item in settings]
        + [FLAME_SPAWN_COUNTER + item["post_fire_stop"] for item in settings]
    )
    assert len(table) == 12
    return CAVE_SPEED_INIT + CAVE_GROUP + table


def apply(
    rom_data,
    variant_settings=None,
) -> list[str]:
    """Apply the always-on Saramandor variant patch."""
    if rom_data is None or len(rom_data) < OFF_CAVE_EXTENSION + 84:
        raise SaramandorVariantError("ROM is too short for Saramandor variant patch.")
    from . import panel_monster_stage_variant

    if variant_settings is None:
        variant_settings = [
            {
                "movement_speed": current_movement_speed(rom_data, index),
                "flame_speed": current_speed_preset(rom_data, index),
                "refire_wait": current_refire_wait(rom_data, index),
                "post_fire_stop": current_post_fire_stop(rom_data, index),
            }
            for index in range(VARIANT_COUNT)
        ]
    extension = _build_extension(variant_settings)

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
    _expect_or_hooked(
        rom_data,
        OFF_HOOK_REFIRE_WAIT,
        ORIG_REFIRE_WAIT,
        HOOK_REFIRE_WAIT,
        "$B17B",
    )
    _expect_or_hooked(
        rom_data,
        OFF_HOOK_FIRE_STATE_EXIT,
        ORIG_FIRE_STATE_EXIT,
        HOOK_FIRE_STATE_EXIT,
        "$B0B3",
    )
    _ensure_child_mark_available(rom_data)
    _ensure_refire_wait_available(rom_data)
    _ensure_fire_state_exit_available(rom_data)
    _ensure_extension_available(rom_data)

    changed: list[str] = []
    _write_blob(rom_data, OFF_CAVE_SPAWN_SETUP, CAVE_SPAWN_SETUP, changed, "Saramandor variant cave $E3C9")
    _write_blob(rom_data, OFF_CAVE_SUBSTATUS, CAVE_SUBSTATUS, changed, "Saramandor variant cave $E3ED")
    _write_blob(rom_data, OFF_CAVE_FLAME_BEHAVIOR, CAVE_FLAME_BEHAVIOR, changed, "Saramandor variant cave $E402")
    _write_blob(rom_data, OFF_CAVE_DISTANCE_CHECK, CAVE_DISTANCE_CHECK, changed, "Saramandor variant cave $E40B")
    _write_blob(rom_data, OFF_CAVE_CHILD_MARK, CAVE_CHILD_MARK, changed, "Saramandor flame-speed helper $E430")
    _write_blob(rom_data, OFF_CAVE_REFIRE_WAIT, CAVE_REFIRE_WAIT, changed, "Saramandor re-fire helper $E448")
    _write_blob(rom_data, OFF_CAVE_FIRE_STATE_EXIT, CAVE_FIRE_STATE_EXIT, changed, "Saramandor post-fire stop helper $E465")
    _write_blob(rom_data, OFF_CAVE_EXTENSION, extension, changed, "Saramandor A/B/C extension $E9A9")

    _write_blob(rom_data, OFF_HOOK_SPAWN_SETUP, HOOK_SPAWN_SETUP, changed, "$B105 Saramandor spawn hook")
    _write_blob(rom_data, OFF_HOOK_SUBSTATUS, HOOK_SUBSTATUS, changed, "$B0A9 Saramandor substatus hook")
    _write_blob(rom_data, OFF_HOOK_FLAME_BEHAVIOR, HOOK_FLAME_BEHAVIOR, changed, "$B0C6 Saramandor flame-behavior hook")
    _write_blob(rom_data, OFF_HOOK_CHILD_MARK, HOOK_CHILD_MARK, changed, "$B121 Saramandor flame-speed marker hook")
    _write_blob(rom_data, OFF_HOOK_DISTANCE_CHECK, HOOK_DISTANCE_CHECK, changed, "$B1E9 Saramandor #2 distance hook")
    _write_blob(rom_data, OFF_HOOK_REFIRE_WAIT, HOOK_REFIRE_WAIT, changed, "$B17B Saramandor re-fire wait hook")
    _write_blob(rom_data, OFF_HOOK_FIRE_STATE_EXIT, HOOK_FIRE_STATE_EXIT, changed, "$B0B3 Saramandor post-fire stop hook")
    return changed

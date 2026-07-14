"""Gargoyle borrowed-ID enhanced-shot experiment.

JP/JPC66 only. Gargoyle #2 IDs ($7A/$7B/$7E/$7F) share configurable Bullet
speed, inter-shot gap, and post-shot cooldown settings. They fire twice when
the LIFE hundreds digit is even and three times when it is odd. Normal
Gargoyles retain stock behavior.
"""
from __future__ import annotations


class GargoyleVariantError(ValueError):
    pass


def _cf(cpu: int) -> int:
    return 0x10 + (cpu - 0x8000)


def _word(cpu: int) -> bytes:
    return bytes((cpu & 0xFF, (cpu >> 8) & 0xFF))


OFF_HOOK_MATERIALIZE = _cf(0xAE6F)
OFF_HOOK_COOLDOWN = _cf(0xAE48)
OFF_HOOK_OLD_WAIT = _cf(0xAF2B)
OFF_HOOK_STATE3 = _cf(0xAE28)
OFF_HOOK_STATE4 = _cf(0xAE2A)
OFF_CAVE_GATE = 0x634F
OFF_CAVE_SECOND_SHOT = 0x6D2D

CPU_CAVE_GATE = 0xE33F
CPU_CAVE_COOLDOWN = CPU_CAVE_GATE + 0x3E
CPU_CAVE_SECOND_SHOT = 0xED1D

BULLET_SPEED_MARKER_QUARTER = 0x88
BULLET_SPEED_MARKER_HALF = 0x89
ENHANCED_NORMAL_SPEED_MARKER = 0x01
BULLET_SPEED_PRESETS = {
    0: ("1/4", BULLET_SPEED_MARKER_QUARTER),
    1: ("1/2", BULLET_SPEED_MARKER_HALF),
    4: ("1x", ENHANCED_NORMAL_SPEED_MARKER),
}
SELECTABLE_SPEED_PRESETS = (4, 1, 0)
DEFAULT_SPEED_PRESET = 1
DEFAULT_INTER_SHOT_FRAMES = 0x0C
DEFAULT_COOLDOWN_FRAMES = 0x78
BULLET_SPEED_LABEL = "1x / 1/2 / 1/4"

ORIG_MATERIALIZE = bytes.fromhex("b1 2e aa 09 02 91 2e")
HOOK_MATERIALIZE = bytes((0x4C, *(_word(CPU_CAVE_GATE)))) + bytes([0xEA] * 4)
OLD_HOOK_MATERIALIZE = bytes((0x4C, *(_word(0xE357)))) + bytes([0xEA] * 4)
OLD_GLOBAL_TWO_BULLET_HOOK = bytes((0x4C, *(_word(0xBD3B)))) + bytes([0xEA] * 4)
ORIG_COOLDOWN = bytes.fromhex("e0 50 90 75")
HOOK_COOLDOWN = bytes((0x4C, *(_word(CPU_CAVE_COOLDOWN)), 0xEA))
OLD_HOOK_COOLDOWN = bytes((0x4C, *(_word(0xE38B)), 0xEA))
ORIG_STATE3 = _word(0xA41C)
HOOK_STATE3 = _word(CPU_CAVE_SECOND_SHOT)
ORIG_STATE4 = _word(0xA41C)
HOOK_STATE4 = _word(CPU_CAVE_SECOND_SHOT)

# v0.6.159 rapid-fire experiment. It is no longer used and must be removed if
# a ROM carrying that hook is saved again.
ORIG_WAIT = bytes.fromhex("a0 01 b1 2c c9 68 90 24")
SNAPPY_WAIT = bytes.fromhex("a0 01 b1 2c c9 01 90 24")
OLD_HOOK_WAIT = bytes((0x4C, *(_word(0xBEC7)))) + bytes([0xEA] * 5)

CAVE_GATE = bytes.fromhex(
    # Every Bullet receives an explicit child sub[7] value: normal IDs write
    # $00, enhanced IDs write the half-speed marker $89. This prevents a
    # recycled child slot from leaking enhanced speed into a normal Gargoyle.
    "a0 01 b1 2e 29 fa c9 7a f0 04 a9 00 f0 02 a9 89 48"
    "a0 03 b1 2e aa 09 02 91 2e 20 76 ae"
    "a0 06 b1 2c 20 56 b1 68 a0 07 91 00 c9 00 f0 10"
    "a0 03 b1 2e 29 03 09 0c 91 2e a9 00 a0 01 91 2c 60"
    # Normal and enhanced cooldown thresholds are stored independently.
    "a0 01 b1 2e 29 fa c9 7a f0 07"
    "e0 50 90 0a 4c 4c ae"
    "e0 78 90 03 4c 4c ae 4c c1 ae"
)
assert len(CAVE_GATE) == 89

CAVE_SECOND_SHOT = bytes.fromhex(
    # States 3 and 4 share this handler. State 3 fires shot two, then either
    # enters cooldown or resets the counter in state 4 when LIFE hundreds is
    # odd. State 4 waits the same interval, fires shot three, and cools down.
    "a0 01 b1 2e 29 fa c9 7a d0 5e"
    "b1 2c c9 0c 90 57 20 ea b2 90 42"
    "8a a0 06 91 2c a0 00 a9 80 91 04 a9 01 11 2c 91 2c"
    "a0 03 b1 2e 29 01 aa 20 76 ae"
    "a0 06 b1 2c 20 56 b1 a9 89 a0 07 91 00"
    "a0 03 b1 2e 29 10 d0 12"
    "ad 39 04 29 01 f0 0b"
    "b1 2e 29 03 09 10 91 2e 4c 7e ed"
    "a0 03 b1 2e 29 03 09 02 91 2e"
    "a9 00 a0 01 91 2c 60 4c 1c a4"
)
assert len(CAVE_SECOND_SHOT) == 107

OLD_PACKED_CAVE = bytes.fromhex(
    "a0 01 b1 2e 29 fa c9 7a f0 04 a9 00 f0 0c"
    "b1 2e 29 04 f0 04 a9 89 d0 02 a9 88 48"
    "a0 03 b1 2e aa 09 02 91 2e 20 76 ae"
    "a0 06 b1 2c 20 56 b1 68 a0 07 91 00 60"
    "a0 01 b1 2e 29 fa c9 7a f0 0a"
    "e0 50 b0 03 4c c1 ae 4c 4c ae"
    "b1 2e 29 04 d0 f7 f0 00"
    "e0 14 90 03 4c 4c ae 4c c1 ae"
)
OLD_PACKED_CAVE_OFF = _cf(0xE357)
OLD_NORMAL_COOLDOWN_OFF = OLD_PACKED_CAVE_OFF + 52 + 0x0B

OFF_CAVE_COOLDOWN_NORMAL_VALUE = OFF_CAVE_GATE + 0x49
OFF_CAVE_SPEED_MARKER_VALUE = OFF_CAVE_GATE + 0x0F
OFF_CAVE_COOLDOWN_VALUE = OFF_CAVE_GATE + 0x50
OFF_SECOND_INTER_SHOT_VALUE = OFF_CAVE_SECOND_SHOT + 0x0D
OFF_SECOND_SPEED_MARKER_VALUE = OFF_CAVE_SECOND_SHOT + 0x38
_GATE_MASK = bytearray(CAVE_GATE)
_GATE_MASK[OFF_CAVE_SPEED_MARKER_VALUE - OFF_CAVE_GATE] = 0x00
_GATE_MASK[OFF_CAVE_COOLDOWN_NORMAL_VALUE - OFF_CAVE_GATE] = 0x00
_GATE_MASK[OFF_CAVE_COOLDOWN_VALUE - OFF_CAVE_GATE] = 0x00
_GATE_MASK = bytes(_GATE_MASK)
_SECOND_MASK = bytearray(CAVE_SECOND_SHOT)
_SECOND_MASK[OFF_SECOND_INTER_SHOT_VALUE - OFF_CAVE_SECOND_SHOT] = 0x00
_SECOND_MASK[OFF_SECOND_SPEED_MARKER_VALUE - OFF_CAVE_SECOND_SHOT] = 0x00
_SECOND_MASK = bytes(_SECOND_MASK)

OLD_TWO_BULLET_BODY = bytes.fromhex(
    "a0 03 b1 2e aa 09 02 91 2e 20 76 ae 20 ea b2 90 3a"
    "a0 00 a9 80 91 04 b1 2c 09 01 91 2c 8a a0 06 91 2c"
    "a0 0a b1 2e 48 a6 03 f0 05 38 e9 10 d0 03 18 69 10"
    "91 2e a6 03 20 76 ae a0 08 a9 30 a6 03 f0 02 a9 d0"
    "91 00 68 a0 0a 91 2e 60"
)

RESERVED_SPANS = (
    (OFF_CAVE_GATE, len(CAVE_GATE)),
    (OFF_CAVE_SECOND_SHOT, len(CAVE_SECOND_SHOT)),
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


def normalize_speed_preset(value) -> int:
    try:
        preset = int(value)
    except (TypeError, ValueError):
        preset = DEFAULT_SPEED_PRESET
    if preset not in SELECTABLE_SPEED_PRESETS:
        raise GargoyleVariantError(f"unsupported Gargoyle Bullet speed preset: {value!r}")
    return preset


def normalize_cooldown(value) -> int:
    try:
        frames = int(value)
    except (TypeError, ValueError):
        frames = DEFAULT_COOLDOWN_FRAMES
    return max(0, min(0xFF, frames))


def normalize_inter_shot(value) -> int:
    try:
        frames = int(value)
    except (TypeError, ValueError):
        frames = DEFAULT_INTER_SHOT_FRAMES
    return max(0, min(0xFF, frames))


def speed_preset_label(preset: int) -> str:
    return BULLET_SPEED_PRESETS[normalize_speed_preset(preset)][0]


def _marker_for_speed_preset(preset: int) -> int:
    return BULLET_SPEED_PRESETS[normalize_speed_preset(preset)][1]


def _speed_preset_from_marker(marker: int, default: int) -> int:
    for preset, (_label, value) in BULLET_SPEED_PRESETS.items():
        if int(marker) == value:
            return preset
    return default


def _is_gate_blob(blob: bytes) -> bool:
    if len(blob) < len(CAVE_GATE):
        return False
    cur = bytearray(blob[:len(CAVE_GATE)])
    cur[OFF_CAVE_SPEED_MARKER_VALUE - OFF_CAVE_GATE] = 0x00
    cur[OFF_CAVE_COOLDOWN_NORMAL_VALUE - OFF_CAVE_GATE] = 0x00
    cur[OFF_CAVE_COOLDOWN_VALUE - OFF_CAVE_GATE] = 0x00
    return bytes(cur) == _GATE_MASK


def _is_second_blob(blob: bytes) -> bool:
    if len(blob) < len(CAVE_SECOND_SHOT):
        return False
    cur = bytearray(blob[:len(CAVE_SECOND_SHOT)])
    cur[OFF_SECOND_INTER_SHOT_VALUE - OFF_CAVE_SECOND_SHOT] = 0x00
    cur[OFF_SECOND_SPEED_MARKER_VALUE - OFF_CAVE_SECOND_SHOT] = 0x00
    return bytes(cur) == _SECOND_MASK


def _build_gate(normal_cooldown: int, speed_preset: int, cooldown_frames: int) -> bytes:
    body = bytearray(CAVE_GATE)
    body[OFF_CAVE_COOLDOWN_NORMAL_VALUE - OFF_CAVE_GATE] = int(normal_cooldown) & 0xFF
    body[OFF_CAVE_SPEED_MARKER_VALUE - OFF_CAVE_GATE] = _marker_for_speed_preset(speed_preset)
    body[OFF_CAVE_COOLDOWN_VALUE - OFF_CAVE_GATE] = normalize_cooldown(cooldown_frames)
    return bytes(body)


def _build_second(speed_preset: int, inter_shot_frames: int) -> bytes:
    body = bytearray(CAVE_SECOND_SHOT)
    body[OFF_SECOND_INTER_SHOT_VALUE - OFF_CAVE_SECOND_SHOT] = normalize_inter_shot(inter_shot_frames)
    body[OFF_SECOND_SPEED_MARKER_VALUE - OFF_CAVE_SECOND_SHOT] = _marker_for_speed_preset(speed_preset)
    return bytes(body)


def _expect_cooldown_site(rom_data) -> None:
    cur = bytes(rom_data[OFF_HOOK_COOLDOWN:OFF_HOOK_COOLDOWN + len(ORIG_COOLDOWN)])
    if cur in (HOOK_COOLDOWN, OLD_HOOK_COOLDOWN):
        return
    if cur[:1] == ORIG_COOLDOWN[:1] and cur[2:] == ORIG_COOLDOWN[2:]:
        return
    raise GargoyleVariantError(
        f"$AE48 Gargoyle cooldown hook signature mismatch at file 0x{OFF_HOOK_COOLDOWN:X}: "
        f"expected e0 NN 90 75 or {HOOK_COOLDOWN.hex(' ')}, got {cur.hex(' ')}"
    )


def _ensure_available(rom_data, off: int, blob: bytes, name: str) -> None:
    cur = bytes(rom_data[off:off + len(blob)])
    old_body = bytes(rom_data[off:off + len(OLD_TWO_BULLET_BODY)])
    if (
        cur == blob
        or (off == OFF_CAVE_GATE and _is_gate_blob(cur))
        or (off == OFF_CAVE_SECOND_SHOT and _is_second_blob(cur))
        or old_body == OLD_TWO_BULLET_BODY
        or all(b in (0xEA, 0x00) for b in cur)
    ):
        return
    if off == OFF_CAVE_GATE:
        prefix = bytes(rom_data[off:OLD_PACKED_CAVE_OFF])
        old = bytes(rom_data[OLD_PACKED_CAVE_OFF:OLD_PACKED_CAVE_OFF + len(OLD_PACKED_CAVE)])
        if all(b in (0xEA, 0x00) for b in prefix) and old == OLD_PACKED_CAVE:
            return
    raise GargoyleVariantError(
        f"{name} cave overlap at file 0x{off:X}: "
        f"expected empty EA/00 or existing Gargoyle code, got {cur[:16].hex(' ')}..."
    )


def is_applied(rom_data) -> bool:
    return (
        rom_data is not None
        and len(rom_data) >= OFF_CAVE_SECOND_SHOT + len(CAVE_SECOND_SHOT)
        and _is_gate_blob(bytes(rom_data[OFF_CAVE_GATE:OFF_CAVE_GATE + len(CAVE_GATE)]))
        and _is_second_blob(
            bytes(rom_data[OFF_CAVE_SECOND_SHOT:OFF_CAVE_SECOND_SHOT + len(CAVE_SECOND_SHOT)])
        )
        and bytes(rom_data[OFF_HOOK_STATE3:OFF_HOOK_STATE3 + 2]) == HOOK_STATE3
        and bytes(rom_data[OFF_HOOK_STATE4:OFF_HOOK_STATE4 + 2]) == HOOK_STATE4
    )


def current_speed_label(rom_data) -> str:
    return BULLET_SPEED_LABEL if is_applied(rom_data) else BULLET_SPEED_LABEL


def current_settings(rom_data) -> dict[str, int]:
    settings = {
        "speed_preset": DEFAULT_SPEED_PRESET,
        "inter_shot_frames": DEFAULT_INTER_SHOT_FRAMES,
        "cooldown_frames": DEFAULT_COOLDOWN_FRAMES,
    }
    if not is_applied(rom_data):
        return settings
    marker = int(rom_data[OFF_CAVE_SPEED_MARKER_VALUE])
    settings["speed_preset"] = _speed_preset_from_marker(marker, DEFAULT_SPEED_PRESET)
    settings["inter_shot_frames"] = int(rom_data[OFF_SECOND_INTER_SHOT_VALUE])
    settings["cooldown_frames"] = int(rom_data[OFF_CAVE_COOLDOWN_VALUE])
    return settings


def _current_normal_cooldown(rom_data) -> int:
    hooked = bytes(rom_data[OFF_HOOK_COOLDOWN:OFF_HOOK_COOLDOWN + len(HOOK_COOLDOWN)])
    if hooked == HOOK_COOLDOWN:
        return int(rom_data[OFF_CAVE_COOLDOWN_NORMAL_VALUE])
    cur = bytes(rom_data[OFF_HOOK_COOLDOWN:OFF_HOOK_COOLDOWN + len(ORIG_COOLDOWN)])
    if cur[:1] == ORIG_COOLDOWN[:1] and cur[2:] == ORIG_COOLDOWN[2:]:
        return int(cur[1])
    if hooked == OLD_HOOK_COOLDOWN:
        return int(rom_data[OLD_NORMAL_COOLDOWN_OFF])
    return 0x50


def apply(
    rom_data,
    speed_preset=None,
    inter_shot_frames=None,
    cooldown_frames=None,
) -> list[str]:
    cur_settings = current_settings(rom_data)
    if speed_preset is None:
        speed_preset = cur_settings["speed_preset"]
    if inter_shot_frames is None:
        inter_shot_frames = cur_settings["inter_shot_frames"]
    if cooldown_frames is None:
        cooldown_frames = cur_settings["cooldown_frames"]
    speed_preset = normalize_speed_preset(speed_preset)
    inter_shot_frames = normalize_inter_shot(inter_shot_frames)
    cooldown_frames = normalize_cooldown(cooldown_frames)
    gate_body = _build_gate(
        _current_normal_cooldown(rom_data),
        speed_preset,
        cooldown_frames,
    )
    second_body = _build_second(speed_preset, inter_shot_frames)
    min_len = max(
        OFF_CAVE_GATE + len(gate_body),
        OFF_CAVE_SECOND_SHOT + len(second_body),
        OFF_HOOK_MATERIALIZE + len(ORIG_MATERIALIZE),
        OFF_HOOK_COOLDOWN + len(ORIG_COOLDOWN),
        OFF_HOOK_STATE3 + len(HOOK_STATE3),
        OFF_HOOK_STATE4 + len(HOOK_STATE4),
        OFF_HOOK_OLD_WAIT + len(ORIG_WAIT),
    )
    if rom_data is None or len(rom_data) < min_len:
        raise GargoyleVariantError("ROM is too short for Gargoyle enhanced-shot patch.")

    _expect_any(
        rom_data,
        OFF_HOOK_MATERIALIZE,
        (ORIG_MATERIALIZE, HOOK_MATERIALIZE, OLD_HOOK_MATERIALIZE, OLD_GLOBAL_TWO_BULLET_HOOK),
        "$AE6F Gargoyle Bullet materialize hook",
    )
    _expect_cooldown_site(rom_data)
    _expect_any(
        rom_data,
        OFF_HOOK_STATE3,
        (ORIG_STATE3, HOOK_STATE3),
        "$AE28 Gargoyle state 3 entry",
    )
    _expect_any(
        rom_data,
        OFF_HOOK_STATE4,
        (ORIG_STATE4, HOOK_STATE4),
        "$AE2A Gargoyle state 4 entry",
    )
    _expect_any(
        rom_data,
        OFF_HOOK_OLD_WAIT,
        (ORIG_WAIT, SNAPPY_WAIT, OLD_HOOK_WAIT),
        "$AF2B old Gargoyle rapid-fire hook",
    )
    _ensure_available(rom_data, OFF_CAVE_GATE, gate_body, "Gargoyle enhanced-shot primary")
    _ensure_available(
        rom_data,
        OFF_CAVE_SECOND_SHOT,
        second_body,
        "Gargoyle second/third-shot state",
    )

    changed: list[str] = []
    _write(rom_data, OFF_CAVE_GATE, gate_body, changed, "Gargoyle enhanced-shot primary $E33F")
    _write(
        rom_data,
        OFF_CAVE_SECOND_SHOT,
        second_body,
        changed,
        "Gargoyle second/third-shot state $ED1D",
    )
    _write(
        rom_data,
        OFF_HOOK_MATERIALIZE,
        HOOK_MATERIALIZE,
        changed,
        "$AE6F Gargoyle first-shot hook",
    )
    _write(
        rom_data,
        OFF_HOOK_COOLDOWN,
        HOOK_COOLDOWN,
        changed,
        "$AE48 Gargoyle enhanced cooldown hook",
    )
    _write(
        rom_data,
        OFF_HOOK_STATE3,
        HOOK_STATE3,
        changed,
        "$AE28 Gargoyle second-shot state hook",
    )
    _write(
        rom_data,
        OFF_HOOK_STATE4,
        HOOK_STATE4,
        changed,
        "$AE2A Gargoyle third-shot state hook",
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

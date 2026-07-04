"""Gargoyle borrowed-ID slow-Bullet variant.

JP/JPC66 only. Gargoyle #2 IDs are repurposed as a strengthened family:

  $7A/$7B -> one Bullet shot at quarter speed, 20F cooldown
  $7E/$7F -> one Bullet shot at half speed, no cooldown

Normal Gargoyles keep the stock `$AE6F -> $AE76` path. The borrowed IDs still
materialize exactly one Bullet, then mark the child sub-slot with the shared
Panel Variant v2 speed marker. The actual Bullet speed runtime is shared with
the existing Panel Variant v2 Bullet path; this module only owns the
Gargoyle-side gates and marker/cooldown selection.
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
OFF_CAVE_GATE = _cf(0xE357)
OFF_CAVE_COOLDOWN = OFF_CAVE_GATE + 0x34
OFF_CAVE_COOLDOWN_TAIL = OFF_CAVE_COOLDOWN + 0x1C

CPU_CAVE_GATE = 0xE357
CPU_CAVE_COOLDOWN = CPU_CAVE_GATE + 0x34
CPU_CAVE_COOLDOWN_TAIL = CPU_CAVE_COOLDOWN + 0x1C

BULLET_SPEED_MARKER_QUARTER = 0x88
BULLET_SPEED_MARKER_HALF = 0x89
BULLET_SPEED_MARKER_2X = 0x8A
BULLET_SPEED_MARKER_3X = 0x8B
BULLET_SPEED_PRESETS = {
    0: ("1/4", BULLET_SPEED_MARKER_QUARTER),
    1: ("1/2", BULLET_SPEED_MARKER_HALF),
    2: ("2x", BULLET_SPEED_MARKER_2X),
    3: ("3x", BULLET_SPEED_MARKER_3X),
}
BULLET_SPEED_LABEL = "1/4 / 1/2 / 2x / 3x"
DEFAULT_SPEED1_PRESET = 0
DEFAULT_SPEED2_PRESET = 1
DEFAULT_SPEED1_COOLDOWN_FRAMES = 0x14
FIXED_SPEED2_COOLDOWN_FRAMES = 0x00
GATE_SPEED2_MARKER_OFFSET = 0x15
GATE_SPEED1_MARKER_OFFSET = 0x19

ORIG_MATERIALIZE = bytes.fromhex("b1 2e aa 09 02 91 2e")
HOOK_MATERIALIZE = bytes((0x4C, *(_word(CPU_CAVE_GATE)))) + bytes([0xEA] * 4)
OLD_GLOBAL_TWO_BULLET_HOOK = bytes((0x4C, *(_word(0xBD3B)))) + bytes([0xEA] * 4)
ORIG_COOLDOWN = bytes.fromhex("e0 50 90 75")
HOOK_COOLDOWN = bytes((0x4C, *(_word(CPU_CAVE_COOLDOWN)), 0xEA))

# v0.6.159 rapid-fire experiment. It is no longer used and must be removed if
# a ROM carrying that hook is saved again.
ORIG_WAIT = bytes.fromhex("a0 01 b1 2c c9 68 90 24")
SNAPPY_WAIT = bytes.fromhex("a0 01 b1 2c c9 01 90 24")
OLD_HOOK_WAIT = bytes((0x4C, *(_word(0xBEC7)))) + bytes([0xEA] * 5)

CAVE_GATE = bytes.fromhex(
    # All Gargoyles materialize one stock Bullet here. Normal IDs explicitly
    # clear child sub-slot [7]. Enhanced speed-1 IDs write the quarter marker;
    # enhanced speed-2 IDs write the half-speed marker.
    "a0 01 b1 2e 29 fa c9 7a f0 04"
    "a9 00 f0 0c b1 2e 29 04 f0 04 a9 89 d0 02 a9 88 48"
    "a0 03 b1 2e aa 09 02 91 2e 20 76 ae"
    "a0 06 b1 2c 20 56 b1 68 a0 07 91 00 60"
)
assert len(CAVE_GATE) == 52

CAVE_COOLDOWN = bytes.fromhex(
    # Normal IDs keep the currently configured global cooldown threshold.
    # Enhanced speed-1 IDs continue in CAVE_COOLDOWN_TAIL for 20F cooldown.
    # Enhanced speed-2 IDs jump directly to the original post-cooldown path.
    "a0 01 b1 2e 29 fa c9 7a f0 0a"
    "e0 50 b0 03 4c c1 ae 4c 4c ae"
    "b1 2e 29 04 d0 f7 f0 00"
)
assert len(CAVE_COOLDOWN) == 28

CAVE_COOLDOWN_TAIL = bytes.fromhex(
    "e0 14 90 03 4c 4c ae"
    "4c c1 ae"
)
assert len(CAVE_COOLDOWN_TAIL) == 10

OFF_CAVE_COOLDOWN_NORMAL_VALUE = OFF_CAVE_COOLDOWN + 0x0B
OFF_CAVE_COOLDOWN_SLOW_VALUE = OFF_CAVE_COOLDOWN_TAIL + 0x01

_GATE_MASK = bytearray(CAVE_GATE)
_GATE_MASK[GATE_SPEED2_MARKER_OFFSET] = 0x00
_GATE_MASK[GATE_SPEED1_MARKER_OFFSET] = 0x00
_GATE_MASK = bytes(_GATE_MASK)
_COOLDOWN_TAIL_MASK = bytearray(CAVE_COOLDOWN_TAIL)
_COOLDOWN_TAIL_MASK[0x01] = 0x00
_COOLDOWN_TAIL_MASK = bytes(_COOLDOWN_TAIL_MASK)

OLD_TWO_BULLET_BODY = bytes.fromhex(
    "a0 03 b1 2e aa 09 02 91 2e 20 76 ae 20 ea b2 90 3a"
    "a0 00 a9 80 91 04 b1 2c 09 01 91 2c 8a a0 06 91 2c"
    "a0 0a b1 2e 48 a6 03 f0 05 38 e9 10 d0 03 18 69 10"
    "91 2e a6 03 20 76 ae a0 08 a9 30 a6 03 f0 02 a9 d0"
    "91 00 68 a0 0a 91 2e 60"
)

RESERVED_SPANS = (
    (OFF_CAVE_GATE, len(CAVE_GATE) + len(CAVE_COOLDOWN) + len(CAVE_COOLDOWN_TAIL)),
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
        preset = DEFAULT_SPEED1_PRESET
    if preset not in BULLET_SPEED_PRESETS:
        raise GargoyleVariantError(f"unsupported Gargoyle Bullet speed preset: {value!r}")
    return preset


def normalize_cooldown(value) -> int:
    try:
        frames = int(value)
    except (TypeError, ValueError):
        frames = DEFAULT_SPEED1_COOLDOWN_FRAMES
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
    cur[GATE_SPEED2_MARKER_OFFSET] = 0x00
    cur[GATE_SPEED1_MARKER_OFFSET] = 0x00
    return bytes(cur) == _GATE_MASK


def _is_cooldown_tail_blob(blob: bytes) -> bool:
    if len(blob) < len(CAVE_COOLDOWN_TAIL):
        return False
    cur = bytearray(blob[:len(CAVE_COOLDOWN_TAIL)])
    cur[0x01] = 0x00
    return bytes(cur) == _COOLDOWN_TAIL_MASK


def _build_gate(speed1_preset: int, speed2_preset: int) -> bytes:
    body = bytearray(CAVE_GATE)
    body[GATE_SPEED1_MARKER_OFFSET] = _marker_for_speed_preset(speed1_preset)
    body[GATE_SPEED2_MARKER_OFFSET] = _marker_for_speed_preset(speed2_preset)
    return bytes(body)


def _expect_cooldown_site(rom_data) -> None:
    cur = bytes(rom_data[OFF_HOOK_COOLDOWN:OFF_HOOK_COOLDOWN + len(ORIG_COOLDOWN)])
    if cur == HOOK_COOLDOWN:
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
        or (off == OFF_CAVE_COOLDOWN_TAIL and _is_cooldown_tail_blob(cur))
        or old_body == OLD_TWO_BULLET_BODY
        or all(b in (0xEA, 0x00) for b in cur)
    ):
        return
    raise GargoyleVariantError(
        f"{name} cave overlap at file 0x{off:X}: "
        f"expected empty EA/00 or existing Gargoyle code, got {cur[:16].hex(' ')}..."
    )


def is_applied(rom_data) -> bool:
    return (
        rom_data is not None
        and len(rom_data) >= OFF_CAVE_GATE + len(CAVE_GATE)
        and _is_gate_blob(bytes(rom_data[OFF_CAVE_GATE:OFF_CAVE_GATE + len(CAVE_GATE)]))
    )


def current_speed_label(rom_data) -> str:
    return BULLET_SPEED_LABEL if is_applied(rom_data) else BULLET_SPEED_LABEL


def current_settings(rom_data) -> dict[str, int]:
    settings = {
        "speed1_preset": DEFAULT_SPEED1_PRESET,
        "cooldown1_frames": DEFAULT_SPEED1_COOLDOWN_FRAMES,
        "speed2_preset": DEFAULT_SPEED2_PRESET,
        "cooldown2_frames": FIXED_SPEED2_COOLDOWN_FRAMES,
    }
    if not is_applied(rom_data):
        return settings
    gate = bytes(rom_data[OFF_CAVE_GATE:OFF_CAVE_GATE + len(CAVE_GATE)])
    settings["speed1_preset"] = _speed_preset_from_marker(
        gate[GATE_SPEED1_MARKER_OFFSET],
        DEFAULT_SPEED1_PRESET,
    )
    settings["speed2_preset"] = _speed_preset_from_marker(
        gate[GATE_SPEED2_MARKER_OFFSET],
        DEFAULT_SPEED2_PRESET,
    )
    settings["cooldown1_frames"] = int(rom_data[OFF_CAVE_COOLDOWN_SLOW_VALUE])
    return settings


def _current_normal_cooldown(rom_data) -> int:
    hooked = bytes(rom_data[OFF_HOOK_COOLDOWN:OFF_HOOK_COOLDOWN + len(HOOK_COOLDOWN)])
    if hooked == HOOK_COOLDOWN:
        return int(rom_data[OFF_CAVE_COOLDOWN_NORMAL_VALUE])
    cur = bytes(rom_data[OFF_HOOK_COOLDOWN:OFF_HOOK_COOLDOWN + len(ORIG_COOLDOWN)])
    if cur[:1] == ORIG_COOLDOWN[:1] and cur[2:] == ORIG_COOLDOWN[2:]:
        return int(cur[1])
    return 0x50


def _build_cooldown_body(normal_cooldown: int) -> bytes:
    body = bytearray(CAVE_COOLDOWN)
    body[0x0B] = int(normal_cooldown) & 0xFF
    return bytes(body)


def _build_cooldown_tail(cooldown1_frames: int) -> bytes:
    body = bytearray(CAVE_COOLDOWN_TAIL)
    body[0x01] = normalize_cooldown(cooldown1_frames)
    return bytes(body)


def apply(
    rom_data,
    speed1_preset=None,
    cooldown1_frames=None,
    speed2_preset=None,
) -> list[str]:
    cur_settings = current_settings(rom_data)
    if speed1_preset is None:
        speed1_preset = cur_settings["speed1_preset"]
    if cooldown1_frames is None:
        cooldown1_frames = cur_settings["cooldown1_frames"]
    if speed2_preset is None:
        speed2_preset = cur_settings["speed2_preset"]
    gate_body = _build_gate(speed1_preset, speed2_preset)
    cooldown_tail = _build_cooldown_tail(cooldown1_frames)
    cooldown_body = _build_cooldown_body(_current_normal_cooldown(rom_data))
    min_len = max(
        OFF_CAVE_GATE + len(gate_body),
        OFF_CAVE_COOLDOWN + len(cooldown_body),
        OFF_CAVE_COOLDOWN_TAIL + len(cooldown_tail),
        OFF_HOOK_MATERIALIZE + len(ORIG_MATERIALIZE),
        OFF_HOOK_COOLDOWN + len(ORIG_COOLDOWN),
        OFF_HOOK_OLD_WAIT + len(ORIG_WAIT),
    )
    if rom_data is None or len(rom_data) < min_len:
        raise GargoyleVariantError("ROM is too short for Gargoyle slow-Bullet patch.")

    _expect_any(
        rom_data,
        OFF_HOOK_MATERIALIZE,
        (ORIG_MATERIALIZE, HOOK_MATERIALIZE, OLD_GLOBAL_TWO_BULLET_HOOK),
        "$AE6F Gargoyle Bullet materialize hook",
    )
    _expect_cooldown_site(rom_data)
    _expect_any(
        rom_data,
        OFF_HOOK_OLD_WAIT,
        (ORIG_WAIT, SNAPPY_WAIT, OLD_HOOK_WAIT),
        "$AF2B old Gargoyle rapid-fire hook",
    )
    _ensure_available(rom_data, OFF_CAVE_GATE, gate_body, "Gargoyle slow-Bullet gate")
    _ensure_available(rom_data, OFF_CAVE_COOLDOWN, cooldown_body, "Gargoyle enhanced cooldown gate")
    _ensure_available(
        rom_data,
        OFF_CAVE_COOLDOWN_TAIL,
        cooldown_tail,
        "Gargoyle enhanced cooldown tail",
    )

    changed: list[str] = []
    _write(rom_data, OFF_CAVE_GATE, gate_body, changed, "Gargoyle slow-Bullet gate $E357")
    _write(
        rom_data,
        OFF_CAVE_COOLDOWN,
        cooldown_body,
        changed,
        "Gargoyle enhanced cooldown gate $E38B",
    )
    _write(
        rom_data,
        OFF_CAVE_COOLDOWN_TAIL,
        cooldown_tail,
        changed,
        "Gargoyle enhanced cooldown tail $E3A7",
    )
    _write(
        rom_data,
        OFF_HOOK_MATERIALIZE,
        HOOK_MATERIALIZE,
        changed,
        "$AE6F Gargoyle slow-Bullet hook",
    )
    _write(
        rom_data,
        OFF_HOOK_COOLDOWN,
        HOOK_COOLDOWN,
        changed,
        "$AE48 Gargoyle enhanced cooldown hook",
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

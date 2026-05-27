"""Panel Monster Bullet direction-speed symmetry fix."""

from __future__ import annotations


class PanelBulletSpeedFixError(Exception):
    pass


CPU_SPEED_TABLE = 0xDB99
OFF_SPEED_TABLE = 0x10 + (CPU_SPEED_TABLE - 0x8000)

SLOW_VALUE = 0x30
FAST_VALUE = 0x41
SPEED_VALUES = (SLOW_VALUE, FAST_VALUE)

# Velocity bytes are directional around the $40 boundary.  Do not write the
# same raw byte to both directions: $41 on a right/down shot reverses it.
PRESETS = {
    SLOW_VALUE: {
        "right_down": 0x30,
        "left_up": 0x50,
    },
    FAST_VALUE: {
        "right_down": 0x3F,
        "left_up": 0x41,
    },
}

# Bullet state2 uses velocity indices 0A..0D for right, left, up, down.
TARGETS = (
    (0x0A, 1, "right_down", SLOW_VALUE, "right X"),
    (0x0B, 1, "left_up", FAST_VALUE, "left X"),
    (0x0C, 0, "left_up", FAST_VALUE, "up Y"),
    (0x0D, 0, "right_down", SLOW_VALUE, "down Y"),
)


def _off(index: int, axis: int) -> int:
    return OFF_SPEED_TABLE + index * 2 + axis


def current_state(rom_data) -> tuple[bool, int]:
    """Return (enabled, value). Original asymmetric values return (False, $30)."""
    if rom_data is None or len(rom_data) <= max(_off(i, a) for i, a, _, _, _ in TARGETS):
        raise PanelBulletSpeedFixError("ROM is too short for Panel Bullet speed table.")

    values = [rom_data[_off(index, axis)] for index, axis, _, _, _ in TARGETS]
    original = [orig for _, _, _, orig, _ in TARGETS]
    if values == original:
        return False, SLOW_VALUE
    for preset_value, preset in PRESETS.items():
        expected = [preset[slot] for _, _, slot, _, _ in TARGETS]
        if values == expected:
            return True, preset_value
    raise PanelBulletSpeedFixError(
        "Panel Bullet speed table has unexpected values: "
        + " ".join(f"{v:02X}" for v in values)
    )


def is_enabled(rom_data) -> bool:
    return current_state(rom_data)[0]


def current_value(rom_data) -> int:
    return current_state(rom_data)[1]


def apply(rom_data, enabled: bool, value: int = SLOW_VALUE) -> list[str]:
    if value not in SPEED_VALUES:
        raise PanelBulletSpeedFixError(f"Unsupported Panel Bullet speed value: ${value:02X}")
    current_state(rom_data)

    changed: list[str] = []
    preset = PRESETS[value]
    for index, axis, slot, orig, label in TARGETS:
        off = _off(index, axis)
        new_value = preset[slot] if enabled else orig
        if rom_data[off] != new_value:
            rom_data[off] = new_value
            changed.append(f"{label}=${new_value:02X}")
    return changed

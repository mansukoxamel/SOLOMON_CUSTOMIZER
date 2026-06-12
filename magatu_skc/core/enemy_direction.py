"""Enemy direction variant lookup for editor shortcuts."""

from __future__ import annotations


DIRECTION_LABELS = {
    "left": "左",
    "right": "右",
    "up": "上",
    "down": "下",
}

_PANEL_DIRECTION_GROUPS = (
    {"right": 0x52, "left": 0x53, "up": 0x56, "down": 0x57},  # 2-way
    {"right": 0x5A, "left": 0x5B, "up": 0x66, "down": 0x67},  # 3-way
    {"right": 0x41, "left": 0x43, "up": 0x45, "down": 0x47},  # A
    {"right": 0x49, "left": 0x4B, "up": 0x4D, "down": 0x4F},  # B
    {"right": 0x31, "left": 0x33, "up": 0x35, "down": 0x37},  # C
)

_PANEL_DIRECTION_LOOKUP = {
    code: group
    for group in _PANEL_DIRECTION_GROUPS
    for code in group.values()
}


def direction_from_description(description: str) -> str | None:
    text = str(description or "").lower()
    for direction in ("right", "left", "up", "down"):
        if f"({direction}" in text:
            return direction
    return None


def enemy_direction_variant(config, code: int, direction: str) -> int | None:
    """Return the same enemy facing ``direction``, or None if unsupported."""
    code = int(code) & 0xFF
    direction = str(direction).lower()
    if direction not in DIRECTION_LABELS:
        return None

    panel_group = _PANEL_DIRECTION_LOOKUP.get(code)
    if panel_group is not None:
        return panel_group.get(direction)

    bundles = getattr(config, "enemy_direction_bundles", []) if config is not None else []
    descriptions = getattr(config, "enemy_desc", {}) if config is not None else {}
    for bundle in bundles:
        if code not in bundle:
            continue
        for candidate in bundle:
            if direction_from_description(descriptions.get(candidate, "")) == direction:
                return int(candidate) & 0xFF
        return None
    return None

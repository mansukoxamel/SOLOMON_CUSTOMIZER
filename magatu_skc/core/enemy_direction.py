"""Enemy direction variant lookup for editor shortcuts."""

from __future__ import annotations


DIRECTION_LABELS = {
    "left": "左",
    "right": "右",
    "up": "上",
    "down": "下",
}

_PANEL_DIRECTION_GROUPS = (
    {"right": 0xE0, "left": 0xE1, "up": 0xE2, "down": 0xE3},  # A
    {"right": 0xE4, "left": 0xE5, "up": 0xE6, "down": 0xE7},  # B
    {"right": 0xE8, "left": 0xE9, "up": 0xEA, "down": 0xEB},  # C
    {"right": 0xEC, "left": 0xED, "up": 0xEE, "down": 0xEF},  # D
    {"right": 0xF0, "left": 0xF1, "up": 0xF2, "down": 0xF3},  # 2-way
    {"right": 0xF4, "left": 0xF5, "up": 0xF6, "down": 0xF7},  # 3-way
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

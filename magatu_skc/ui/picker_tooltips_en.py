"""English picker tooltips aligned with the reviewed Japanese picker."""

from .picker_tooltips_ja import PICKER_TOOLTIPS_JA


_DIRECTIONS_EN = ("Right", "Left", "Up", "Down")


def _direction(code):
    return _DIRECTIONS_EN[code & 3]


PICKER_TOOLTIPS_EN = {
    ("block", "none"): "(Empty)",
    ("block", "brown"): "Brown Block",
    ("block", "cracked"): "Cracked Block",
    ("block", "white"): "White Block",
    ("block", "breakable_white"): "Breakable White Block",
    ("block", "invisible_breakable"): "Invisible Brown Block",
    ("block", "passable_white"): "Passable White Block",
    ("block", "invisible_solid"): "Invisible White Block",
    ("block", "passable_brown"): "Passable Brown Block",
    ("block", "solid_brown"): "Solid Brown Block",
    ("meta", "start"): "Dana",
    ("meta", "key"): "Key",
    ("meta", "door"): "Door",
    ("item", 0x07): "0x07 Open Door",
    ("meta", "mirror1"): "Mirror of Camirror 1",
    ("meta", "mirror2"): "Mirror of Camirror 2",
    ("item", 0x04): "0x04 Demonic Seal",
    ("item", 0x05): "0x05 Mirror of Camirror (Dummy)",
    ("item", 0x08): "0x08 Diamond (Blue)",
    ("item", 0x0C): "0x0c Diamond (Orange)",
    ("item", 0x36): "0x36 Philosopher's Stone",
    ("item", 0x11): "0x11 Medicine of Edlem (Half)",
    ("item", 0x12): "0x12 Medicine of Edlem (Full)",
    ("item", 0x13): "0x13 Hour Glass of Norm (Blue)",
    ("item", 0x14): "0x14 Hour Glass of Norm (Orange)",
    ("item", 0x15): "0x15 Jar of Manda (Blue)",
    ("item", 0x34): "0x34 Jar of Manda (Gray)",
    ("item", 0x16): "0x16 Jar of Manda (Orange)",
    ("item", 0x17): "0x17 Scroll of Lyra",
    ("item", 0x18): "0x18 Bell of Lyrac",
    ("item", 0x35): "0x35 Bell of Lyrac (Gray)",
    ("item", 0x1A): "0x1a Key of Lyrac",
    ("item", 0x19): "0x19 Medicine of Meltona",
    ("item", 0x1B): "0x1b Crystal of Rad (Blue)",
    ("item", 0x0B): "0x0b Crystal of Rad (Orange)",
    ("item", 0x3A): "0x3a Crystal of Rad (Gray)",
    ("item", 0x1C): "0x1c Constellation Panel #1",
    ("item", 0x1D): "0x1d Constellation Panel #2",
    ("item", 0x1E): "0x1e Constellation Panel #3",
    ("item", 0x1F): "0x1f Constellation Panel #4",
    ("item", 0x20): "0x20 Solomon's Seal",
    ("item", 0x21): "0x21 Space Conjuration/Time Conjuration",
    ("item", 0x22): "0x22 Golden Wing",
    ("item", 0x25): "0x25 Silver Coin",
    ("item", 0x26): "0x26 Double Silver Coin",
    ("item", 0x27): "0x27 Jewel (Blue)",
    ("item", 0x28): "0x28 Gold Coin",
    ("item", 0x29): "0x29 Double Gold Coin",
    ("item", 0x2A): "0x2a Jewel (Orange)",
    ("item", 0x2B): "0x2b Star Coin",
    ("item", 0x2C): "0x2c Double Star Coin",
    ("item", 0x2D): "0x2d Jewel (Dark Orange)",
    ("item", 0x2E): "0x2e Origami Swan",
    ("item", 0x2F): "0x2f Demonhead Coin",
    ("item", 0x30): "0x30 Sphinx",
    ("item", 0x31): "0x31 Egyptian Head",
    ("item", 0x32): "0x32 Magic Lamp",
    ("item", 0x33): "0x33 Medicine of Mapros",
    ("item", 0x37): "0x37 Dana Statue",
    ("item", 0x38): "0x38 Tecmo Plate (Gray)",
    ("item", 0x39): "0x39 Tecmo Plate",
    ("enemy", 0x68): "0x68 Dragon (Right)",
    ("enemy", 0x69): "0x69 Dragon (Left)",
    ("enemy", 0x6A): "0x6a Dragon (Color Variant) (Right)",
    ("enemy", 0x6B): "0x6b Dragon (Color Variant) (Left)",
    ("enemy", 0x70): "0x70 Goblin (Right)",
    ("enemy", 0x71): "0x71 Goblin (Left)",
    ("enemy", 0x72): "0x72 Goblin (Color Variant) (Right)",
    ("enemy", 0x73): "0x73 Goblin (Color Variant) (Left)",
    ("enemy", 0x78): "0x78 Gargoil (Right)",
    ("enemy", 0x79): "0x79 Gargoil (Left)",
    ("enemy", 0x7A): "0x7a Enhanced Gargoil A (Right)",
    ("enemy", 0x7B): "0x7b Enhanced Gargoil A (Left)",
    ("enemy", 0x7E): "0x7e Enhanced Gargoil B (Right)",
    ("enemy", 0x7F): "0x7f Enhanced Gargoil B (Left)",
    ("enemy", 0x50): "0x50 Demonshead (Right)",
    ("enemy", 0x51): "0x51 Demonshead (Left)",
    ("enemy", 0x5C): "0x5c Saramandor (Right)",
    ("enemy", 0x5D): "0x5d Saramandor (Left)",
    ("enemy", 0x5E): "0x5e Enhanced Saramandor A (Right)",
    ("enemy", 0x5F): "0x5f Enhanced Saramandor A (Left)",
    ("enemy", 0x62): "0x62 Enhanced Saramandor B (Right)",
    ("enemy", 0x63): "0x63 Enhanced Saramandor B (Left)",
    ("enemy", 0x66): "0x66 Enhanced Saramandor C (Right)",
    ("enemy", 0x67): "0x67 Enhanced Saramandor C (Left)",
    ("enemy", 0x34): "0x34 Ghost (Right)",
    ("enemy", 0x36): "0x36 Ghost (Left)",
    ("enemy", 0x30): "0x30 Neul (Up)",
    ("enemy", 0x32): "0x32 Neul (Down)",
    ("enemy", 0x44): "0x44 Ghost (Instant Reversal) (Right)",
    ("enemy", 0x46): "0x46 Ghost (Instant Reversal) (Left)",
    ("enemy", 0x40): "0x40 Neul (Instant Reversal) (Up)",
    ("enemy", 0x42): "0x42 Neul (Instant Reversal) (Down)",
    **{
        ("enemy", code): f"0x{code:02x} Fireball ({_direction(code)})"
        for code in range(0x20, 0x24)
    },
    **{
        ("enemy", code): f"0x{code:02x} Sparkling Ball ({_direction(code)})"
        for code in range(0x28, 0x2C)
    },
    **{
        ("enemy", code): f"0x{code:02x} Panel Monster ({_direction(code)})"
        for code in range(0x24, 0x28)
    },
    ("enemy", 0x9D): "0x9d Seraphic Radiance",
    ("enemy", 0x9E): "0x9e Chaos Dragon",
    **{
        ("enemy", code): (
            f"0x{code:02x} Panel Monster {group} ({_direction(code)})"
        )
        for first, group in (
            (0xF0, "2-Way"),
            (0xF4, "3-Way"),
            (0xE0, "A"),
            (0xE4, "B"),
            (0xE8, "C"),
            (0xEC, "D"),
        )
        for code in range(first, first + 4)
    },
    ("enemy", 0x1C): "0x1c Fairy",
    ("enemy", 0x1D): "0x1d Fairy Princess",
    ("enemy", 0x9C): "0x9c Dark Fairy",
    ("enemy", 0x18): "0x18 Mighty Bomb Jack (Right)",
    ("enemy", 0x19): "0x19 Mighty Bomb Jack (Left)",
    ("enemy", 0x80): "0x80 Red Burn",
    ("enemy", 0x81): "0x81 Blue Burn",
    ("enemy", 0x82): "0x82 Ice Burn",
    **{
        ("enemy", code): (
            f"0x{code:02x} Enhanced Ghost "
            f"{('A', 'B', 'C', 'D', 'E', 'F')[(code - 0xB0) // 2]} "
            f"({('Right', 'Left')[code & 1]})"
        )
        for code in range(0xB0, 0xBC)
    },
    **{
        ("enemy", code): (
            f"0x{code:02x} Enhanced Neul "
            f"{('A', 'B')[(code - 0x84) // 2]} "
            f"({('Up', 'Down')[code & 1]})"
        )
        for code in range(0x84, 0x88)
    },
    **{
        ("enemy", code): (
            f"0x{code:02x} Phantom Bullet "
            f"{('A', 'B', 'C', 'D')[(code - 0xA0) // 4]} "
            f"({_direction(code)})"
        )
        for code in range(0xA0, 0xB0)
    },
    **{
        ("enemy", code): (
            f"0x{code:02x} Sparkling Ball {kind} ({_direction(code)})"
        )
        for first, kind in (
            (0xC0, "Pause"),
            (0xC8, "Transparent"),
            (0xD0, "Reverse"),
        )
        for code in range(first, first + 4)
    },
    **{
        ("enemy", code): f"0x{code:02x} Spark Trail ({_direction(code)})"
        for code in range(0xD8, 0xDC)
    },
    **{
        ("enemy", code): (
            f"0x{code:02x} Sparkling Ball Variant ({_direction(code)})"
        )
        for code in range(0xF8, 0xFC)
    },
}


if PICKER_TOOLTIPS_EN.keys() != PICKER_TOOLTIPS_JA.keys():
    raise RuntimeError("English picker tooltip keys do not match the Japanese source")


def picker_name_en(mode, value):
    """Return the English name without the picker ID prefix."""
    text = PICKER_TOOLTIPS_EN.get((mode, value))
    if text is None:
        return None
    if mode in ("item", "enemy") and text.startswith("0x"):
        _prefix, separator, name = text.partition(" ")
        if separator:
            return name
    return text

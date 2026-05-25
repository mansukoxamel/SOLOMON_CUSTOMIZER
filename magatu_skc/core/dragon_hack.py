"""Dragon behavior tweaks.

The snappy option minimizes Dragon's own pre-attack wait threshold:

  JP $A693 / file 0x26A3: CMP #$14 immediate
  US $A7D3 / file 0x27E3: CMP #$14 immediate

This is deliberately separate from the shared Saramandor flame startup wait at
$B0E8 because that route also affects Saramandor.
"""
from __future__ import annotations


_OFF = {
    "JP": {
        "wait": 0x26A3,
        "orig": 0x14,
        "sig_off": 0x265A,
        "sig": bytes.fromhex("20 01 b2 20 a9 8e 1c a4 c8 ae 5e a6"),
    },
    "US": {
        "wait": 0x27E3,
        "orig": 0x14,
        "sig_off": 0x279A,
        "sig": bytes.fromhex("20 41 b3 20 a9 8e 5c a5 08 b0 9e a7"),
    },
}

SNAPPY_VALUE = 0x01


class DragonHackError(ValueError):
    """Dragon tweak validation failed."""


def detect_region(rom_data) -> str:
    for region, o in _OFF.items():
        end = o["sig_off"] + len(o["sig"])
        if len(rom_data) < end:
            continue
        if bytes(rom_data[o["sig_off"]:end]) == o["sig"]:
            return region
    raise DragonHackError(
        "ドラゴンのコードが見つかりません。\n"
        "改造ROM/拡張ROM/破損の可能性があるため、ドラゴン改造を中止します。"
    )


def is_snappy(rom_data) -> bool:
    """Return True when the Dragon wait threshold is minimized."""
    region = detect_region(rom_data)
    return rom_data[_OFF[region]["wait"]] == SNAPPY_VALUE


def apply(rom_data, snappy: bool) -> list[str]:
    """Toggle Dragon snappy behavior."""
    region = detect_region(rom_data)
    o = _OFF[region]
    off = o["wait"]
    target = SNAPPY_VALUE if snappy else o["orig"]
    if rom_data[off] == target:
        return []
    rom_data[off] = target
    if snappy:
        return ["キビキビ動作ON (攻撃前待ち→$01)"]
    return ["キビキビ動作OFF (原作復元)"]

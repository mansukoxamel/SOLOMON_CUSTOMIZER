"""Gargoyle behavior tweaks.

The "snappy" option minimizes three Gargoyle-specific wait thresholds while
leaving the original state machine intact:

  $AE6C State0 pre-materialize wait original $10
  $AF30 State5 attack wait      original $68
  $AF7C State5 return/turn wait original $18

Setting all values to $01 gives the same style of global "キビキビ動作" as the
Golem tweak: the stop/transition logic remains, but its delay is minimized.

The post-shot cooldown at $AE49 is intentionally controlled separately because
shrinking it to one frame can flood the object pool.
"""
from __future__ import annotations


_OFF = {
    "JP": {
        "waits": [0x2E7C, 0x2F40, 0x2F8C],
        "orig": [0x10, 0x68, 0x18],
        "cooldown": 0x2E59,
        "cooldown_orig": 0x50,
        "sig_off": 0x2E2C,
        "sig": bytes.fromhex("20 01 b2 20 a9 8e 3b ae c8 ae 30 ae"),
    },
    "US": {
        "waits": [0x2FBC, 0x3080, 0x30CC],
        "orig": [0x10, 0x68, 0x18],
        "cooldown": 0x2F99,
        "cooldown_orig": 0x50,
        "sig_off": 0x2F6C,
        "sig": bytes.fromhex("20 41 b3 20 a9 8e 7b af 08 b0 70 af"),
    },
}

SNAPPY_VALUE = 0x01
COOLDOWN_MIN = 4
COOLDOWN_MAX = 255


class GargoyleHackError(ValueError):
    """Gargoyle tweak validation failed."""


def detect_region(rom_data) -> str:
    for region, o in _OFF.items():
        end = o["sig_off"] + len(o["sig"])
        if len(rom_data) < end:
            continue
        if bytes(rom_data[o["sig_off"]:end]) == o["sig"]:
            return region
    raise GargoyleHackError(
        "ガーゴイルのコードが見つかりません。\n"
        "改造ROM/拡張ROM/破損の可能性があるため、ガーゴイル改造を中止します。"
    )


def is_snappy(rom_data) -> bool:
    """Return True when all Gargoyle snappy thresholds are minimized."""
    region = detect_region(rom_data)
    o = _OFF[region]
    return all(rom_data[off] == SNAPPY_VALUE for off in o["waits"])


def current_cooldown(rom_data) -> int:
    """Return the Gargoyle post-shot cooldown frame threshold."""
    region = detect_region(rom_data)
    return int(rom_data[_OFF[region]["cooldown"]])


def apply(rom_data, snappy: bool) -> list[str]:
    """Toggle Gargoyle snappy behavior.

    snappy=True writes all wait thresholds to $01.  snappy=False restores the
    original values.
    """
    region = detect_region(rom_data)
    o = _OFF[region]
    changed: list[str] = []
    if snappy:
        for off in o["waits"]:
            if rom_data[off] != SNAPPY_VALUE:
                rom_data[off] = SNAPPY_VALUE
                changed.append(f"待ち${off:04X}→01")
        if changed:
            return ["キビキビ動作ON (待ち3箇所→$01)"]
        return []

    for off, orig in zip(o["waits"], o["orig"]):
        if rom_data[off] != orig:
            rom_data[off] = orig
            changed.append(f"待ち${off:04X}→原作")
    if changed:
        return ["キビキビ動作OFF (原作復元)"]
    return []


def apply_cooldown(rom_data, frames: int) -> list[str]:
    """Set Gargoyle post-shot cooldown.

    The original value is $50 / 80 frames.  The UI intentionally clamps this to
    at least COOLDOWN_MIN so it cannot accidentally become a 1-frame flood.
    """
    frames = int(frames)
    if not (COOLDOWN_MIN <= frames <= COOLDOWN_MAX):
        raise GargoyleHackError(
            f"ガーゴイルのクールダウンは {COOLDOWN_MIN}-{COOLDOWN_MAX} フレームで指定してください。"
        )
    region = detect_region(rom_data)
    off = _OFF[region]["cooldown"]
    if rom_data[off] == frames:
        return []
    rom_data[off] = frames & 0xFF
    return [f"発射後クールダウン→{frames}F"]

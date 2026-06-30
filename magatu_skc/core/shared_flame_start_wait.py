"""Shared Dragon/Saramandor flame startup wait tweak."""
from __future__ import annotations


OFF_WAIT_JP = 0x30F8
ORIGINAL_WAIT = 0x18
MIN_WAIT = 1
MAX_WAIT = 0xFF


class SharedFlameStartWaitError(ValueError):
    """Shared flame startup wait patch validation failed."""


def verify(rom_data) -> None:
    if len(rom_data) <= OFF_WAIT_JP + 2:
        raise SharedFlameStartWaitError("ROM が短すぎます。")
    if rom_data[OFF_WAIT_JP - 1] != 0xC9 or \
            bytes(rom_data[OFF_WAIT_JP + 1:OFF_WAIT_JP + 3]) != bytes((0x90, 0xED)):
        raise SharedFlameStartWaitError(
            "ドラゴン/サラマンダー共通の火吐き開始待ちコードが見つかりません。"
        )


def normalize_wait(frames: int) -> int:
    try:
        value = int(frames)
    except (TypeError, ValueError) as exc:
        raise SharedFlameStartWaitError("火吐き開始待ちは数値で指定してください。") from exc
    if not (MIN_WAIT <= value <= MAX_WAIT):
        raise SharedFlameStartWaitError(
            f"火吐き開始待ちは {MIN_WAIT}-{MAX_WAIT} フレームで指定してください。"
        )
    return value


def current_wait(rom_data) -> int:
    verify(rom_data)
    return int(rom_data[OFF_WAIT_JP])


def apply(rom_data, frames: int) -> list[str]:
    verify(rom_data)
    value = normalize_wait(frames)
    if rom_data[OFF_WAIT_JP] == value:
        return []
    rom_data[OFF_WAIT_JP] = value & 0xFF
    return [f"火吐き開始待ち→{value}F"]

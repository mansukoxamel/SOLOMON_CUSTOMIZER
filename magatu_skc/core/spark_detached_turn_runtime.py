"""Spark Ball direct-turn runtime for IDs $F8-$FF."""
from __future__ import annotations


class SparkDetachedTurnRuntimeError(ValueError):
    pass


FIRST_ID = 0xF8
LAST_ID = 0xFF
SLOW_FIRST_ID = 0xF8
FAST_FIRST_ID = 0xFC
NEW_ENEMY_IDS = tuple(range(FIRST_ID, LAST_ID + 1))

OFF_RUNTIME = 0x60A3
CPU_RUNTIME = 0xE093

OFF_POSITION_COMMIT_HOOK = 0x2A48
CPU_POSITION_COMMIT_HOOK = 0xAA38
ORIG_POSITION_COMMIT_HOOK = bytes.fromhex("4C 13 AB")
CPU_STOCK_POSITION_COMMIT = 0xAB13


def _build_runtime() -> bytes:
    return bytes((
        0xA0, 0x01,
        0xB1, 0x2E,
        0xC9, FIRST_ID,
        0x90, 0x12,
        0xA5, 0x07,
        0xF0, 0x0E,
        0xA5, 0x05,
        0xA0, 0x06,
        0x91, 0x2C,
        0xA5, 0x04,
        0x49, 0x01,
        0xC8,
        0x91, 0x2C,
        0x60,
        0x4C, CPU_STOCK_POSITION_COMMIT & 0xFF,
        CPU_STOCK_POSITION_COMMIT >> 8,
    ))


RUNTIME = _build_runtime()
HOOK_POSITION_COMMIT = bytes((
    0x4C,
    CPU_RUNTIME & 0xFF,
    CPU_RUNTIME >> 8,
))
RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(RUNTIME) == 29


def levels_need_runtime(levels: list) -> bool:
    return any(
        FIRST_ID <= int(getattr(enemy, "element_no", -1)) <= LAST_ID
        for level in (levels or [])
        for enemy in (getattr(level, "enemies", []) or [])
    )


def _expect_blank_or(
    data: bytes | bytearray,
    off: int,
    blob: bytes,
    name: str,
) -> None:
    current = bytes(data[off:off + len(blob)])
    if current == blob or all(value in (0x00, 0xEA) for value in current):
        return
    raise SparkDetachedTurnRuntimeError(
        f"{name} is not blank at file 0x{off:X}: got {current.hex(' ')}"
    )


def validate(rom_data: bytes | bytearray) -> None:
    min_len = max(
        OFF_RUNTIME + len(RUNTIME),
        OFF_POSITION_COMMIT_HOOK + len(HOOK_POSITION_COMMIT),
    )
    if rom_data is None or len(rom_data) < min_len:
        raise SparkDetachedTurnRuntimeError(
            "ROM is too short for Spark Ball direct-turn runtime."
        )

    current_hook = bytes(
        rom_data[
            OFF_POSITION_COMMIT_HOOK:
            OFF_POSITION_COMMIT_HOOK + len(HOOK_POSITION_COMMIT)
        ]
    )
    if current_hook not in (ORIG_POSITION_COMMIT_HOOK, HOOK_POSITION_COMMIT):
        raise SparkDetachedTurnRuntimeError(
            f"$AA38 position-commit signature mismatch: "
            f"got {current_hook.hex(' ')}"
        )
    _expect_blank_or(
        rom_data,
        OFF_RUNTIME,
        RUNTIME,
        "Spark Ball direct-turn runtime",
    )


def _write(
    data: bytearray,
    off: int,
    blob: bytes,
    changed: list[str],
    name: str,
) -> None:
    if bytes(data[off:off + len(blob)]) != blob:
        data[off:off + len(blob)] = blob
        changed.append(name)


def apply(rom_data: bytearray) -> list[str]:
    validate(rom_data)
    changed: list[str] = []
    _write(
        rom_data,
        OFF_RUNTIME,
        RUNTIME,
        changed,
        f"Spark Ball direct-turn ${CPU_RUNTIME:04X}-"
        f"${CPU_RUNTIME + len(RUNTIME) - 1:04X}",
    )
    _write(
        rom_data,
        OFF_POSITION_COMMIT_HOOK,
        HOOK_POSITION_COMMIT,
        changed,
        f"${CPU_POSITION_COMMIT_HOOK:04X} Spark Ball direct-turn hook",
    )
    return changed

"""Blue-key item $1A runtime that queues the stock Fairy Princess $1D.

Design regulation: a room may contain at most one blue-key item.  UI-side
placement enforcement is a separate task; this runtime intentionally keeps a
single pending bit and does not implement multi-key ordering or recovery.
"""
from __future__ import annotations


class BlueKeyQueenRuntimeError(ValueError):
    pass


OFF_ITEM_HANDLER = 0x460B       # CPU $C5FB, item $1A handler word
ORIG_ITEM_HANDLER = bytes.fromhex("b5 c5")

OFF_FAIRY_TYPE_LOAD = 0x1F0F    # CPU $9EFF, LDA #$1C / STA $07
ORIG_FAIRY_TYPE_LOAD = bytes.fromhex("a9 1c 85 07")

OFF_RUNTIME = 0x6066
CPU_RUNTIME = 0xE056
RAM_FAIRY_QUEUE = 0x0454
RAM_FAIRY_FLAGS = 0x0087
QUEEN_PENDING_BIT = 0x02

CPU_ITEM_HANDLER = CPU_RUNTIME
CPU_SELECT_FAIRY_TYPE = CPU_RUNTIME + 10


ITEM_HANDLER_RUNTIME = bytes.fromhex(
    "ee 54 04"     # INC $0454: use the stock retry-until-free fairy queue
    "a9 02"        # LDA #$02: queen pending marker
    "05 87"        # ORA $87
    "85 87"        # STA $87
    "60"           # RTS
)

SELECT_FAIRY_TYPE_RUNTIME = bytes.fromhex(
    "a9 02"        # LDA #$02
    "24 87"        # BIT $87
    "f0 0a"        # BEQ normal_fairy
    "a5 87"        # LDA $87
    "29 fd"        # AND #$FD: consume queen pending only
    "85 87"        # STA $87
    "a9 1d"        # LDA #$1D: stock Fairy Princess
    "d0 02"        # BNE store_type
    "a9 1c"        # normal_fairy: stock Fairy
    "85 07"        # store_type: STA $07
    "60"           # RTS
)

RUNTIME = ITEM_HANDLER_RUNTIME + SELECT_FAIRY_TYPE_RUNTIME
HOOK_ITEM_HANDLER = bytes((CPU_ITEM_HANDLER & 0xFF, CPU_ITEM_HANDLER >> 8))
HOOK_FAIRY_TYPE_LOAD = bytes(
    (0x20, CPU_SELECT_FAIRY_TYPE & 0xFF, CPU_SELECT_FAIRY_TYPE >> 8, 0xEA)
)
RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(ITEM_HANDLER_RUNTIME) == 10
assert len(SELECT_FAIRY_TYPE_RUNTIME) == 21
assert len(RUNTIME) == 31


def _accept(rom_data: bytearray, offset: int, original: bytes, patched: bytes, label: str) -> None:
    actual = bytes(rom_data[offset:offset + len(original)])
    if actual not in (original, patched):
        raise BlueKeyQueenRuntimeError(
            f"{label} signature mismatch at file 0x{offset:X}: {actual.hex(' ')}"
        )


def apply(rom_data: bytearray) -> list[str]:
    """Write the fixed runtime and its two stock-code hooks."""
    if len(rom_data) < OFF_RUNTIME + len(RUNTIME):
        raise BlueKeyQueenRuntimeError("ROM is too small for blue-key queen runtime")
    _accept(rom_data, OFF_ITEM_HANDLER, ORIG_ITEM_HANDLER, HOOK_ITEM_HANDLER, "item $1A")
    _accept(
        rom_data,
        OFF_FAIRY_TYPE_LOAD,
        ORIG_FAIRY_TYPE_LOAD,
        HOOK_FAIRY_TYPE_LOAD,
        "fairy type load",
    )
    runtime_cur = bytes(rom_data[OFF_RUNTIME:OFF_RUNTIME + len(RUNTIME)])
    if runtime_cur != RUNTIME and any(b not in (0x00, 0xEA) for b in runtime_cur):
        raise BlueKeyQueenRuntimeError(
            f"runtime cave is not blank at file 0x{OFF_RUNTIME:X}: "
            f"{runtime_cur.hex(' ')}"
        )
    rom_data[OFF_RUNTIME:OFF_RUNTIME + len(RUNTIME)] = RUNTIME
    rom_data[OFF_ITEM_HANDLER:OFF_ITEM_HANDLER + len(HOOK_ITEM_HANDLER)] = HOOK_ITEM_HANDLER
    rom_data[OFF_FAIRY_TYPE_LOAD:OFF_FAIRY_TYPE_LOAD + len(HOOK_FAIRY_TYPE_LOAD)] = HOOK_FAIRY_TYPE_LOAD
    return [
        f"blue-key queen runtime: file 0x{OFF_RUNTIME:X}, {len(RUNTIME)} bytes",
        "item $1A now queues Fairy Princess $1D via the stock fairy spawn path",
    ]

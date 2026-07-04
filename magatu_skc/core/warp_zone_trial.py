"""Stage 4 demon-mirror warp trial runtime.

This is intentionally not a UI feature yet.  It patches only the mapper66
runtime and only uses stage 4's two demon mirror positions as a proof of
concept.
"""
from __future__ import annotations

from .element import byte_from_position


class WarpZoneTrialError(ValueError):
    pass


TRIAL_STAGE_INDEX = 3

OFF_ITEM_CELL_HOOK = 0x4561   # CPU $C551: JSR $C55B
CPU_ITEM_CELL_HOOK = 0xC551
ORIG_ITEM_CELL_HOOK = bytes.fromhex("20 5b c5")

OFF_RUNTIME = 0x6A56
CPU_RUNTIME = 0xEA46
CPU_STOCK_ITEM_CHECK = 0xC55B
CPU_COMMON_CLEAR = 0x0000


def _word(cpu: int) -> bytes:
    return bytes((int(cpu) & 0xFF, (int(cpu) >> 8) & 0xFF))


HOOK_ITEM_CELL = bytes((0x20, CPU_RUNTIME & 0xFF, CPU_RUNTIME >> 8))


class _Asm:
    def __init__(self):
        self.data = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str]] = []

    def label(self, name: str) -> None:
        self.labels[name] = len(self.data)

    def b(self, *values: int) -> None:
        self.data.extend(v & 0xFF for v in values)

    def abs(self, opcode: int, addr: int) -> None:
        self.b(opcode, addr & 0xFF, addr >> 8)

    def rel(self, opcode: int, label: str) -> None:
        self.b(opcode, 0x00)
        self.fixups.append((len(self.data) - 1, label))

    def finish(self) -> bytes:
        for pos, label in self.fixups:
            if label not in self.labels:
                raise AssertionError(f"missing label: {label}")
            delta = self.labels[label] - (pos + 1)
            if not -128 <= delta <= 127:
                raise AssertionError(f"branch out of range: {label} {delta}")
            self.data[pos] = delta & 0xFF
        return bytes(self.data)


def _pixel_from_cell(cell: int, *, side: int) -> tuple[int, int]:
    x = int(cell) & 0x0F
    y = ((int(cell) >> 4) & 0x0F) - 1
    out_x = max(0, min(15, x + int(side)))
    return (out_x * 16, y * 16 + 8)


def _build_runtime(src1: int, src2: int) -> bytes:
    # Mirror1 is on the right in stock stage 4, so appear to the right of
    # mirror2.  Mirror2 appears to the left of mirror1.  This avoids instant
    # return without allocating a cooldown RAM byte.
    dst_for_src1 = _pixel_from_cell(src2, side=1)
    dst_for_src2 = _pixel_from_cell(src1, side=-1)

    a = _Asm()
    a.b(0xC9, 0x05)                    # CMP #$05
    a.rel(0xD0, "stock")               # BNE stock
    a.b(0xE0, src1)                    # CPX #src1
    a.rel(0xF0, "warp_to_2")           # BEQ warp_to_2
    a.b(0xE0, src2)                    # CPX #src2
    a.rel(0xF0, "warp_to_1")           # BEQ warp_to_1
    a.label("stock")
    a.abs(0x4C, CPU_STOCK_ITEM_CHECK)  # JMP $C55B

    a.label("warp_to_2")
    a.b(0xA9, dst_for_src1[1])         # LDA #Y
    a.abs(0x8D, 0x0586)                # STA $0586
    a.b(0xA9, dst_for_src1[0])         # LDA #X
    a.abs(0x8D, 0x0589)                # STA $0589
    a.abs(0x4C, CPU_RUNTIME + 43)      # JMP common

    a.label("warp_to_1")
    a.b(0xA9, dst_for_src2[1])         # LDA #Y
    a.abs(0x8D, 0x0586)                # STA $0586
    a.b(0xA9, dst_for_src2[0])         # LDA #X
    a.abs(0x8D, 0x0589)                # STA $0589

    a.label("common")
    a.b(0xA9, 0x00)                    # LDA #$00
    for addr in (0x0584, 0x0585, 0x0587, 0x0588):
        a.abs(0x8D, addr)              # clear velocity/subpixel
    a.b(0x85, 0x02)                    # STA $02: no item action
    a.b(0x60)                          # RTS
    runtime = a.finish()
    common_cpu = CPU_RUNTIME + a.labels["common"]
    runtime = runtime.replace(_word(CPU_RUNTIME + 43), _word(common_cpu), 1)
    return runtime


def _stage4_mirror_cells(levels: list) -> tuple[int, int] | None:
    if levels is None or len(levels) <= TRIAL_STAGE_INDEX:
        return None
    mirrors = getattr(levels[TRIAL_STAGE_INDEX], "demon_mirrors", None) or []
    if len(mirrors) < 2:
        return None
    return (
        byte_from_position(mirrors[0].position) & 0xFF,
        byte_from_position(mirrors[1].position) & 0xFF,
    )


def _expect(data: bytes | bytearray, off: int, allowed: tuple[bytes, ...], name: str) -> None:
    size = len(allowed[0])
    cur = bytes(data[off:off + size])
    if cur not in allowed:
        expected = " or ".join(blob.hex(" ") for blob in allowed)
        raise WarpZoneTrialError(
            f"{name} signature mismatch at 0x{off:X}: expected {expected}, got {cur.hex(' ')}"
        )


def _expect_blank_or(data: bytes | bytearray, off: int, blob: bytes, name: str) -> None:
    cur = bytes(data[off:off + len(blob)])
    if cur == blob or all(b in (0xEA, 0x00) for b in cur):
        return
    if (
        len(cur) == len(blob)
        and cur.startswith(bytes.fromhex("c9 05 d0 08 e0"))
        and cur[12:15] == bytes.fromhex("4c 5b c5")
        and cur[-15:] == blob[-15:]
    ):
        return
    raise WarpZoneTrialError(
        f"{name} area is not blank at 0x{off:X}: expected EA/00 or {blob.hex(' ')}, got {cur.hex(' ')}"
    )


def apply(rom_data: bytearray, levels: list) -> list[str]:
    cells = _stage4_mirror_cells(levels)
    if cells is None:
        return []
    runtime = _build_runtime(*cells)
    max_end = OFF_RUNTIME + len(runtime)
    if rom_data is None or len(rom_data) < max_end:
        raise WarpZoneTrialError("ROM is too short for warp-zone trial runtime.")

    _expect(
        rom_data,
        OFF_ITEM_CELL_HOOK,
        (ORIG_ITEM_CELL_HOOK, HOOK_ITEM_CELL),
        "$C551 warp-zone trial item-cell hook",
    )
    _expect_blank_or(rom_data, OFF_RUNTIME, runtime, "warp-zone trial runtime")

    changed: list[str] = []
    if bytes(rom_data[OFF_RUNTIME:OFF_RUNTIME + len(runtime)]) != runtime:
        rom_data[OFF_RUNTIME:OFF_RUNTIME + len(runtime)] = runtime
        changed.append(
            f"Stage 4 mirror warp trial runtime ${CPU_RUNTIME:04X}-${CPU_RUNTIME + len(runtime) - 1:04X}"
        )
    if bytes(rom_data[OFF_ITEM_CELL_HOOK:OFF_ITEM_CELL_HOOK + 3]) != HOOK_ITEM_CELL:
        rom_data[OFF_ITEM_CELL_HOOK:OFF_ITEM_CELL_HOOK + 3] = HOOK_ITEM_CELL
        changed.append("$C551 Stage 4 mirror warp trial hook")
    return changed


RESERVED_SPANS = (
    (OFF_RUNTIME, len(_build_runtime(0x3B, 0x33))),
)

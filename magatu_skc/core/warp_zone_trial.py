"""Warp Mirror Mode runtime."""
from __future__ import annotations

from . import constants as c
from . import stage_ext
from .element import Wall


class WarpZoneTrialError(ValueError):
    pass


OFF_ITEM_CELL_HOOK = 0x4561   # CPU $C551: JSR $C55B
CPU_ITEM_CELL_HOOK = 0xC551
ORIG_ITEM_CELL_HOOK = bytes.fromhex("20 5b c5")

OFF_RUNTIME = 0x6A6E
CPU_RUNTIME = 0xEA5E
CPU_STOCK_ITEM_CHECK = 0xC55B
CPU_PLAY_SE = 0x8E8D
RAM_WARP_MIRROR_STATE = 0x0770
RAM_RESERVED_SPANS = ((RAM_WARP_MIRROR_STATE, 1),)
WARP_MIRROR_MODE_BIT = 0x20
WARP_MIRROR_COOLDOWN_BIT = 0x40


def level_has_valid_warp_mirrors(level) -> bool:
    """Return whether Warp Mirror Mode has exactly two usable destinations."""
    mirrors = list(getattr(level, "demon_mirrors", []) or [])
    if len(mirrors) != 2:
        return False
    try:
        positions = [
            tuple(int(value) for value in getattr(mirror, "position", (-99, -99)))
            for mirror in mirrors
        ]
    except (TypeError, ValueError):
        return False
    if any(len(position) != 2 for position in positions):
        return False
    if positions[0] == positions[1]:
        return False
    item_positions = {
        tuple(getattr(item, "position", (-99, -99)))
        for item in (getattr(level, "items", []) or [])
    }
    blocked_positions = set().union(*(
        set(getattr(level, name, set()) or [])
        for name in (
            "breakable_white_cells",
            "cracked_block_cells",
            "passable_white_cells",
            "invisible_solid_cells",
            "invisible_breakable_cells",
            "passable_brown_cells",
            "solid_brown_cells",
        )
    ))
    for x, y in positions:
        if not (0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H):
            return False
        if level.tiles[y][x] != Wall.NONE:
            return False
        if (x, y) in blocked_positions or (x, y) in item_positions:
            return False
    return True


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


def _build_runtime() -> bytes:
    a = _Asm()
    a.b(0xC9, 0x05)                    # CMP #$05
    a.rel(0xF0, "mirror_cell")         # BEQ mirror_cell
    a.b(0x48)                          # PHA
    a.abs(0xAD, RAM_WARP_MIRROR_STATE) # LDA state
    a.b(0x29, 0xFF ^ WARP_MIRROR_COOLDOWN_BIT)
    a.abs(0x8D, RAM_WARP_MIRROR_STATE) # clear cooldown after leaving mirror
    a.b(0x68)                          # PLA
    a.abs(0x4C, CPU_STOCK_ITEM_CHECK)  # JMP $C55B

    a.label("mirror_cell")
    a.abs(0xAD, RAM_WARP_MIRROR_STATE) # LDA state
    a.b(0x29, WARP_MIRROR_MODE_BIT)
    a.rel(0xF0, "stock_mirror")        # disabled: original item path
    a.abs(0xAD, RAM_WARP_MIRROR_STATE) # LDA state
    a.b(0x29, WARP_MIRROR_COOLDOWN_BIT)
    a.rel(0xD0, "no_item")             # already touching a mirror
    a.b(0x86, 0x03)                    # STX $03: source mirror cell
    a.b(0xA0, 0xDF)                    # LDY #$DF

    a.label("scan")
    a.b(0xB9, 0x04, 0x03)              # LDA $0304,Y
    a.b(0xC9, 0x05)                    # CMP #$05
    a.rel(0xD0, "scan_next")
    a.b(0x98)                          # TYA
    a.b(0xC5, 0x03)                    # CMP $03
    a.rel(0xF0, "scan_next")
    a.b(0x85, 0x04)                    # STA $04: destination cell
    a.rel(0xD0, "warp")                # always: destination != source

    a.label("scan_next")
    a.b(0x88)                          # DEY
    a.rel(0xD0, "scan")
    a.rel(0xF0, "no_item")             # Y==0: no other mirror found

    a.label("warp")
    a.abs(0xAD, RAM_WARP_MIRROR_STATE) # LDA state
    a.b(0x09, WARP_MIRROR_COOLDOWN_BIT)
    a.abs(0x8D, RAM_WARP_MIRROR_STATE) # set cooldown, keep mode bit
    a.b(0xA5, 0x04)                    # LDA destination cell
    a.b(0x29, 0xF0)                    # row * 16
    a.b(0x18)                          # CLC
    a.b(0x69, 0x10)                    # ADC #$10
    a.abs(0x8D, 0x0586)                # STA $0586
    a.b(0xA5, 0x04)                    # LDA destination cell
    a.b(0x29, 0x0F)                    # column
    a.b(0x0A, 0x0A, 0x0A, 0x0A)        # *16
    a.b(0x18)                          # CLC
    a.b(0x69, 0x08)                    # ADC #$08
    a.abs(0x8D, 0x0589)                # STA $0589

    a.label("common")
    a.abs(0xAD, 0x0589)                # LDA $0589
    a.b(0x2A)                          # ROL A: carry = destination X bit7
    a.b(0xA9, 0x0A)                    # LDA #$0A
    a.b(0x2A)                          # ROL A: stock stage-start state $14/$15
    a.abs(0x8D, 0x0582)                # STA $0582
    a.b(0xA9, 0xFF)                    # LDA #$FF
    a.abs(0x8D, 0x0581)                # force stock velocity table refresh
    a.b(0xA0, 0x0D)                    # LDY #$0D: item pickup SE
    a.abs(0x20, CPU_PLAY_SE)           # JSR $8E8D
    a.b(0xA9, 0x00)                    # LDA #$00
    for addr in (0x0585, 0x0587, 0x0588):
        a.abs(0x8D, addr)              # clear subpixel/horizontal velocity
    a.b(0x85, 0x02)                    # STA $02: no item action
    a.b(0x60)                          # RTS

    a.label("stock_mirror")
    a.b(0xA9, 0x05)                    # LDA #$05
    a.abs(0x4C, CPU_STOCK_ITEM_CHECK)  # JMP $C55B
    a.label("no_item")
    a.b(0x60)                          # RTS
    return a.finish()


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
    raise WarpZoneTrialError(
        f"{name} area is not blank at 0x{off:X}: expected EA/00 or {blob.hex(' ')}, got {cur.hex(' ')}"
    )


def levels_need_runtime(levels: list) -> bool:
    return any(stage_ext.warp_mirror_enabled(level) for level in (levels or []))


def apply(rom_data: bytearray, levels: list) -> list[str]:
    runtime = _build_runtime()
    max_end = OFF_RUNTIME + len(runtime)
    if rom_data is None or len(rom_data) < max_end:
        raise WarpZoneTrialError("ROM is too short for Warp Mirror Mode runtime.")

    _expect(
        rom_data,
        OFF_ITEM_CELL_HOOK,
        (ORIG_ITEM_CELL_HOOK, HOOK_ITEM_CELL),
        "$C551 Warp Mirror Mode item-cell hook",
    )
    _expect_blank_or(rom_data, OFF_RUNTIME, runtime, "Warp Mirror Mode runtime")

    changed: list[str] = []
    if bytes(rom_data[OFF_RUNTIME:OFF_RUNTIME + len(runtime)]) != runtime:
        rom_data[OFF_RUNTIME:OFF_RUNTIME + len(runtime)] = runtime
        changed.append(
            f"Warp Mirror Mode runtime ${CPU_RUNTIME:04X}-${CPU_RUNTIME + len(runtime) - 1:04X}"
        )
    if bytes(rom_data[OFF_ITEM_CELL_HOOK:OFF_ITEM_CELL_HOOK + 3]) != HOOK_ITEM_CELL:
        rom_data[OFF_ITEM_CELL_HOOK:OFF_ITEM_CELL_HOOK + 3] = HOOK_ITEM_CELL
        changed.append("$C551 Warp Mirror Mode hook")
    return changed


RESERVED_SPANS = (
    (OFF_RUNTIME, len(_build_runtime())),
)

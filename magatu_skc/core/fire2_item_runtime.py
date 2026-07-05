"""Fire x2 item runtime for item $09."""
from __future__ import annotations


class Fire2ItemRuntimeError(ValueError):
    pass


ITEM_FIRE2 = 0x09

OFF_ITEM_PICKUP_HOOK = 0x456B   # CPU $C55B
CPU_ITEM_PICKUP_HOOK = 0xC55B
ORIG_ITEM_PICKUP_HOOK = bytes.fromhex("c9 38 b0")

OFF_DRAW_HOOK = 0x1DF8          # CPU $9DE8
CPU_DRAW_HOOK = 0x9DE8
ORIG_DRAW_HOOK = bytes.fromhex("0a 0a a8")

OFF_RUNTIME = 0x6C7D
CPU_RUNTIME = 0xEC6D
CPU_STOCK_ITEM_CHECK_AFTER_RANGE = 0xC55F
CPU_CONSUME_ITEM = 0xC818
CPU_PLAY_SE = 0x8E8D
CPU_ADD_FIRE_JAR = 0xC7A3
CPU_DRAW_CONTINUE = 0x9DEB


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


def _build_item_runtime() -> bytes:
    a = _Asm()
    a.b(0xC9, ITEM_FIRE2)                  # CMP #$09
    a.rel(0xF0, "fire2")                  # BEQ fire2
    a.b(0xC9, 0x38)                       # original $C55B entry
    a.rel(0xB0, "rts")
    a.abs(0x4C, CPU_STOCK_ITEM_CHECK_AFTER_RANGE)
    a.label("rts")
    a.b(0x60)

    a.label("fire2")
    a.b(0xA5, 0x87)                       # LDA $87
    a.b(0x4A)                             # LSR A
    a.rel(0xB0, "rts")                   # pickup gate busy
    a.b(0xA9, ITEM_FIRE2)
    a.abs(0x20, CPU_CONSUME_ITEM)         # remove item / action setup
    a.b(0xA0, 0x40)
    a.b(0x84, 0x02)
    a.b(0xA0, 0x0D)
    a.abs(0x20, CPU_PLAY_SE)
    a.abs(0x20, CPU_ADD_FIRE_JAR)
    a.abs(0x20, CPU_ADD_FIRE_JAR)
    a.b(0xA9, 0x01)
    a.b(0x60)
    return a.finish()


def _build_draw_runtime(custom_metatile_cpu: int) -> bytes:
    a = _Asm()
    a.b(0xC9, ITEM_FIRE2)                 # CMP #$09
    a.rel(0xD0, "normal")
    a.b(0xA9, custom_metatile_cpu & 0xFF)
    a.b(0x85, 0x06)
    a.b(0xA9, custom_metatile_cpu >> 8)
    a.b(0x85, 0x07)
    a.b(0xA9, 0x00)                       # Y=0 into custom one-entry table
    a.label("normal")
    a.b(0x0A, 0x0A, 0xA8)                 # original ASL; ASL; TAY
    a.abs(0x4C, CPU_DRAW_CONTINUE)
    return a.finish()


ITEM_RUNTIME = _build_item_runtime()
DRAW_RUNTIME_CPU = CPU_RUNTIME + len(ITEM_RUNTIME)
DRAW_RUNTIME = _build_draw_runtime(DRAW_RUNTIME_CPU + 20)
FIRE2_METATILE_BG0 = bytes.fromhex("60 65 66 67")
RUNTIME = ITEM_RUNTIME + DRAW_RUNTIME + FIRE2_METATILE_BG0

HOOK_ITEM_PICKUP = bytes((0x4C, CPU_RUNTIME & 0xFF, CPU_RUNTIME >> 8))
HOOK_DRAW = bytes((0x4C, DRAW_RUNTIME_CPU & 0xFF, DRAW_RUNTIME_CPU >> 8))


def levels_need_runtime(levels: list) -> bool:
    for level in levels or []:
        for item in getattr(level, "items", []) or []:
            try:
                if int(item.get_item_no()) == ITEM_FIRE2:
                    return True
            except AttributeError:
                if (int(getattr(item, "element_no", 0)) & 0x3F) == ITEM_FIRE2:
                    return True
    return False


def _expect(data: bytes | bytearray, off: int, allowed: tuple[bytes, ...], name: str) -> None:
    size = len(allowed[0])
    cur = bytes(data[off:off + size])
    if cur in allowed:
        return
    expected = " or ".join(blob.hex(" ") for blob in allowed)
    raise Fire2ItemRuntimeError(
        f"{name} signature mismatch at 0x{off:X}: expected {expected}, got {cur.hex(' ')}"
    )


def _expect_blank_or(data: bytes | bytearray, off: int, blob: bytes, name: str) -> None:
    cur = bytes(data[off:off + len(blob)])
    if cur == blob or all(b in (0xEA, 0x00) for b in cur):
        return
    raise Fire2ItemRuntimeError(
        f"{name} area is not blank at 0x{off:X}: expected EA/00 or existing runtime, got {cur.hex(' ')}"
    )


def apply(rom_data: bytearray) -> list[str]:
    if rom_data is None or len(rom_data) < OFF_RUNTIME + len(RUNTIME):
        raise Fire2ItemRuntimeError("ROM is too short for Fire x2 item runtime.")

    _expect(
        rom_data,
        OFF_ITEM_PICKUP_HOOK,
        (ORIG_ITEM_PICKUP_HOOK, HOOK_ITEM_PICKUP),
        "$C55B Fire x2 item hook",
    )
    _expect(
        rom_data,
        OFF_DRAW_HOOK,
        (ORIG_DRAW_HOOK, HOOK_DRAW),
        "$9DE8 Fire x2 draw hook",
    )
    _expect_blank_or(rom_data, OFF_RUNTIME, RUNTIME, "Fire x2 item runtime")

    changed: list[str] = []
    if bytes(rom_data[OFF_RUNTIME:OFF_RUNTIME + len(RUNTIME)]) != RUNTIME:
        rom_data[OFF_RUNTIME:OFF_RUNTIME + len(RUNTIME)] = RUNTIME
        changed.append(f"Fire x2 item runtime ${CPU_RUNTIME:04X}-${CPU_RUNTIME + len(RUNTIME) - 1:04X}")
    if bytes(rom_data[OFF_ITEM_PICKUP_HOOK:OFF_ITEM_PICKUP_HOOK + len(HOOK_ITEM_PICKUP)]) != HOOK_ITEM_PICKUP:
        rom_data[OFF_ITEM_PICKUP_HOOK:OFF_ITEM_PICKUP_HOOK + len(HOOK_ITEM_PICKUP)] = HOOK_ITEM_PICKUP
        changed.append("$C55B Fire x2 item hook")
    if bytes(rom_data[OFF_DRAW_HOOK:OFF_DRAW_HOOK + len(HOOK_DRAW)]) != HOOK_DRAW:
        rom_data[OFF_DRAW_HOOK:OFF_DRAW_HOOK + len(HOOK_DRAW)] = HOOK_DRAW
        changed.append("$9DE8 Fire x2 draw hook")
    return changed


RESERVED_SPANS = (
    (OFF_RUNTIME, len(RUNTIME)),
)


assert len(ITEM_RUNTIME) == 40
assert len(DRAW_RUNTIME) == 20
assert len(RUNTIME) == 64

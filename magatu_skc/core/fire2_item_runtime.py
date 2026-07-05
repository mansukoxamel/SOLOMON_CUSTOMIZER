"""Fire/Fairy x2 runtime using per-stage special item position lists."""
from __future__ import annotations

from .element import byte_from_position, position_from_byte


class Fire2ItemRuntimeError(ValueError):
    pass


# UI pseudo item IDs. These IDs are never written to the room grid anymore.
ITEM_FIRE2 = 0x34
ITEM_FAIRY2 = 0x35
ITEM_FIRE2_BASE = 0x15
ITEM_FAIRY2_BASE = 0x18
SPECIAL_ITEM_UI_TO_BASE = {
    ITEM_FIRE2: ITEM_FIRE2_BASE,
    ITEM_FAIRY2: ITEM_FAIRY2_BASE,
}
SPECIAL_ITEM_BASES = frozenset(SPECIAL_ITEM_UI_TO_BASE.values())

SPECIAL_ITEM_CELLS_PER_ROOM = 16
RAM_SPECIAL_ITEM_CELLS = 0x0740
RAM_FAIRY2_DELAY = 0x0771
FAIRY2_DELAY_FRAMES = 0x20

OFF_ITEM_PICKUP_HOOK = 0x456B   # CPU $C55B
CPU_ITEM_PICKUP_HOOK = 0xC55B
ORIG_ITEM_PICKUP_HOOK = bytes.fromhex("c9 38 b0")

OFF_DRAW_HOOK = 0x1DF8          # CPU $9DE8
CPU_DRAW_HOOK = 0x9DE8
ORIG_DRAW_HOOK = bytes.fromhex("0a 0a a8")
OLD_DRAW_HOOK = bytes.fromhex("4c f0 ec")

OFF_RUNTIME = 0x6C7D
CPU_RUNTIME = 0xEC6D
CPU_STOCK_ITEM_CHECK_AFTER_RANGE = 0xC55F
CPU_PLAY_SE = 0x8E8D
CPU_ADD_FIRE_JAR = 0xC7A3
CPU_ADD_FAIRY_QUEUE = 0xC7AA
CPU_DRAW_CONTINUE = 0x9DEB

OFF_PRG1_LOADER_HELPER = 0x9280
CPU_PRG1_LOADER_HELPER = 0x9270
OFF_PRG1_SPECIAL_ITEM_TABLE = 0x9310
CPU_PRG1_SPECIAL_ITEM_TABLE = 0x9300
PRG1_SPECIAL_ITEM_TABLE_ROOMS = 64
PRG1_SPECIAL_ITEM_TABLE_SIZE = PRG1_SPECIAL_ITEM_TABLE_ROOMS * SPECIAL_ITEM_CELLS_PER_ROOM

OLD_RUNTIME = bytes.fromhex(
    "c934f00cc935f024c938b0034c5fc560a5874ab0faa9342018c8a0408402a00d208d8e20"
    "a3c720a3c7a90160a5874ab0dea9352018c8a0408402a00d208d8e20aac720aac7a90160"
    "c934f00ac935f0120a0aa84ceb9da9db8506a9ec8507a900f0eea9df8506a9ec8507a900"
    "f0e2606566679c9d9e9f"
)


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
    # Entry: A=$0304,X cell value, X=tile index.
    a.b(0x48)                             # PHA original cell value
    a.b(0x86, 0x00)                       # STX $00
    a.b(0xA0, SPECIAL_ITEM_CELLS_PER_ROOM - 1)
    a.label("scan")
    a.b(0xB9, RAM_SPECIAL_ITEM_CELLS & 0xFF, RAM_SPECIAL_ITEM_CELLS >> 8)  # LDA $0740,Y
    a.b(0xC5, 0x00)                       # CMP $00
    a.rel(0xF0, "listed")
    a.b(0x88)                             # DEY
    a.rel(0x10, "scan")                   # BPL scan
    a.label("normal")
    a.b(0x68)                             # PLA original cell value
    a.b(0xC9, 0x38)                       # original $C55B range check
    a.rel(0xB0, "rts")
    a.abs(0x4C, CPU_STOCK_ITEM_CHECK_AFTER_RANGE)

    a.label("listed")
    a.b(0x68)                             # PLA original cell value
    a.b(0xC9, ITEM_FIRE2_BASE)
    a.rel(0xF0, "fire2")
    a.b(0xC9, ITEM_FAIRY2_BASE)
    a.rel(0xF0, "fairy2")
    a.b(0xC9, 0x38)
    a.rel(0xB0, "rts")
    a.abs(0x4C, CPU_STOCK_ITEM_CHECK_AFTER_RANGE)

    a.label("fire2")
    a.abs(0x20, CPU_STOCK_ITEM_CHECK_AFTER_RANGE)  # stock pickup/effect once
    a.b(0xA5, 0x02)
    a.rel(0xF0, "rts")
    a.abs(0x20, CPU_ADD_FIRE_JAR)          # second fire stock
    a.label("rts")
    a.b(0x60)

    a.label("fairy2")
    a.abs(0x20, CPU_STOCK_ITEM_CHECK_AFTER_RANGE)
    a.b(0xA5, 0x02)
    a.rel(0xF0, "rts2")
    a.b(0xA9, FAIRY2_DELAY_FRAMES)
    a.abs(0x8D, RAM_FAIRY2_DELAY)          # delayed second fairy queue
    a.label("rts2")
    a.b(0x60)
    return a.finish()


def _build_draw_runtime(fire_metatile_cpu: int, fairy_metatile_cpu: int) -> bytes:
    a = _Asm()
    # Entry: A=cell value, $00=draw cell index.
    a.b(0x48)                             # PHA original cell value
    a.b(0xA0, SPECIAL_ITEM_CELLS_PER_ROOM - 1)
    a.label("scan")
    a.b(0xB9, RAM_SPECIAL_ITEM_CELLS & 0xFF, RAM_SPECIAL_ITEM_CELLS >> 8)
    a.b(0xC5, 0x00)
    a.rel(0xF0, "listed")
    a.b(0x88)
    a.rel(0x10, "scan")
    a.label("normal_pop")
    a.b(0x68)
    a.label("normal")
    a.b(0x0A, 0x0A, 0xA8)                 # original ASL; ASL; TAY
    a.abs(0x4C, CPU_DRAW_CONTINUE)

    a.label("listed")
    a.b(0x68)
    a.b(0xC9, ITEM_FIRE2_BASE)
    a.rel(0xF0, "fire2")
    a.b(0xC9, ITEM_FAIRY2_BASE)
    a.rel(0xF0, "fairy2")
    a.rel(0xD0, "normal")

    a.label("fire2")
    a.b(0xA9, fire_metatile_cpu & 0xFF, 0x85, 0x06)
    a.b(0xA9, fire_metatile_cpu >> 8, 0x85, 0x07)
    a.b(0xA9, 0x00)
    a.rel(0xF0, "normal")

    a.label("fairy2")
    a.b(0xA9, fairy_metatile_cpu & 0xFF, 0x85, 0x06)
    a.b(0xA9, fairy_metatile_cpu >> 8, 0x85, 0x07)
    a.b(0xA9, 0x00)
    a.rel(0xF0, "normal")
    return a.finish()


ITEM_RUNTIME = _build_item_runtime()
OFF_DRAW_RUNTIME = OFF_RUNTIME + len(ITEM_RUNTIME)
CPU_DRAW_RUNTIME = CPU_RUNTIME + len(ITEM_RUNTIME)
DRAW_RUNTIME_PLACEHOLDER = _build_draw_runtime(CPU_DRAW_RUNTIME + 0x70, CPU_DRAW_RUNTIME + 0x74)
FIRE2_METATILE_CPU = CPU_DRAW_RUNTIME + len(DRAW_RUNTIME_PLACEHOLDER)
FAIRY2_METATILE_CPU = FIRE2_METATILE_CPU + 4
DRAW_RUNTIME = _build_draw_runtime(FIRE2_METATILE_CPU, FAIRY2_METATILE_CPU)
FIRE2_METATILE_BG0 = bytes.fromhex("60 65 66 67")
FAIRY2_METATILE_BG0 = bytes.fromhex("9C 9D 9E 9F")
RUNTIME = ITEM_RUNTIME + DRAW_RUNTIME + FIRE2_METATILE_BG0 + FAIRY2_METATILE_BG0

HOOK_ITEM_PICKUP = bytes((0x4C, CPU_RUNTIME & 0xFF, CPU_RUNTIME >> 8))
HOOK_DRAW = bytes((0x4C, CPU_DRAW_RUNTIME & 0xFF, CPU_DRAW_RUNTIME >> 8))
HOOK_PRG1_LOADER = bytes((0x4C, CPU_PRG1_LOADER_HELPER & 0xFF, CPU_PRG1_LOADER_HELPER >> 8))


def normalize_special_item_cells(level) -> set[tuple[int, int]]:
    item_by_pos = {tuple(item.position): item for item in getattr(level, "items", []) or []}
    out = set()
    for pos in getattr(level, "special_item_cells", set()) or []:
        item = item_by_pos.get(tuple(pos))
        if item is None:
            continue
        if (int(item.element_no) & 0x3F) in SPECIAL_ITEM_BASES:
            x, y = tuple(pos)
            if 0 <= x < 16 and 0 <= y < 12:
                out.add((x, y))
    return out


def levels_need_runtime(levels: list) -> bool:
    return any(bool(normalize_special_item_cells(level)) for level in levels or [])


def build_special_item_table(levels: list) -> bytes:
    table = bytearray([0xFF] * PRG1_SPECIAL_ITEM_TABLE_SIZE)
    for room_no, level in enumerate((levels or [])[:PRG1_SPECIAL_ITEM_TABLE_ROOMS]):
        cells = sorted(normalize_special_item_cells(level), key=lambda p: (p[1], p[0]))
        if len(cells) > SPECIAL_ITEM_CELLS_PER_ROOM:
            raise Fire2ItemRuntimeError(
                f"Stage {room_no + 1}: special item cells exceed "
                f"{SPECIAL_ITEM_CELLS_PER_ROOM} ({len(cells)})"
            )
        base = room_no * SPECIAL_ITEM_CELLS_PER_ROOM
        for idx, pos in enumerate(cells):
            table[base + idx] = byte_from_position(pos)
    return bytes(table)


def read_table(rom_data: bytes, levels: list) -> bool:
    if len(rom_data) < OFF_PRG1_SPECIAL_ITEM_TABLE + PRG1_SPECIAL_ITEM_TABLE_SIZE:
        return False
    raw = bytes(rom_data[OFF_PRG1_SPECIAL_ITEM_TABLE:OFF_PRG1_SPECIAL_ITEM_TABLE + PRG1_SPECIAL_ITEM_TABLE_SIZE])
    # No signature is used. Treat all 00/EA/FF as "not installed" to avoid
    # interpreting untouched reserve as author data.
    if all(b in (0x00, 0xEA, 0xFF) for b in raw):
        for level in levels or []:
            level.special_item_cells = set()
        return False
    for room_no, level in enumerate((levels or [])[:PRG1_SPECIAL_ITEM_TABLE_ROOMS]):
        cells = set()
        base = room_no * SPECIAL_ITEM_CELLS_PER_ROOM
        for value in raw[base:base + SPECIAL_ITEM_CELLS_PER_ROOM]:
            if value == 0xFF:
                continue
            pos = position_from_byte(value)
            x, y = pos
            if 0 <= x < 16 and 0 <= y < 12:
                cells.add(pos)
        level.special_item_cells = cells
    return True


def _build_loader_helper(base_loader: bytes) -> bytes:
    a = _Asm()
    a.abs(0xAD, 0x0428)                   # LDA room
    a.b(0x0A, 0x0A, 0x0A, 0x0A, 0x85, 0x00)
    a.abs(0xAD, 0x0428)
    a.b(0x4A, 0x4A, 0x4A, 0x4A)
    a.b(0x18, 0x69, CPU_PRG1_SPECIAL_ITEM_TABLE >> 8, 0x85, 0x01)
    a.b(0xA0, SPECIAL_ITEM_CELLS_PER_ROOM - 1)
    a.label("copy")
    a.b(0xB1, 0x00)                       # LDA ($00),Y
    a.b(0x99, RAM_SPECIAL_ITEM_CELLS & 0xFF, RAM_SPECIAL_ITEM_CELLS >> 8)
    a.b(0x88)
    a.rel(0x10, "copy")
    a.b(0xA9, 0x00)
    a.abs(0x8D, RAM_FAIRY2_DELAY)
    a.b(*base_loader)
    return a.finish()


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
    old = OLD_RUNTIME
    if off == OFF_RUNTIME and bytes(data[off:off + len(old)]) == old:
        return
    raise Fire2ItemRuntimeError(
        f"{name} area is not blank at 0x{off:X}: expected EA/00 or existing runtime, got {cur.hex(' ')}"
    )


def apply(rom_data: bytearray, levels: list | None = None) -> list[str]:
    if rom_data is None or len(rom_data) < OFF_PRG1_SPECIAL_ITEM_TABLE + PRG1_SPECIAL_ITEM_TABLE_SIZE:
        raise Fire2ItemRuntimeError("ROM is too short for Fire/Fairy x2 special item runtime.")

    from . import panel_monster_stage_variant

    _expect(
        rom_data,
        OFF_ITEM_PICKUP_HOOK,
        (ORIG_ITEM_PICKUP_HOOK, HOOK_ITEM_PICKUP),
        "$C55B Fire/Fairy x2 special item hook",
    )
    _expect(
        rom_data,
        OFF_DRAW_HOOK,
        (ORIG_DRAW_HOOK, OLD_DRAW_HOOK, HOOK_DRAW),
        "$9DE8 Fire/Fairy x2 special draw hook",
    )
    _expect_blank_or(rom_data, OFF_RUNTIME, RUNTIME, "Fire/Fairy x2 special item runtime")

    base_loader_slot = panel_monster_stage_variant.RUNTIME_LOADER_SLOT
    cur_loader = bytes(rom_data[panel_monster_stage_variant.OFF_PRG1_RUNTIME_LOADER:
                                panel_monster_stage_variant.OFF_PRG1_RUNTIME_LOADER + len(HOOK_PRG1_LOADER)])
    if cur_loader not in (base_loader_slot[:3], HOOK_PRG1_LOADER):
        raise Fire2ItemRuntimeError(
            "Panel Variant PRG1 runtime loader slot does not match expected entry bytes."
        )

    loader_helper = _build_loader_helper(panel_monster_stage_variant.RUNTIME_LOADER)
    _expect_blank_or(
        rom_data,
        OFF_PRG1_LOADER_HELPER,
        loader_helper,
        "Fire/Fairy x2 special item PRG1 loader helper",
    )

    table = build_special_item_table(levels or [])

    changed: list[str] = []
    if bytes(rom_data[OFF_RUNTIME:OFF_RUNTIME + len(RUNTIME)]) != RUNTIME:
        rom_data[OFF_RUNTIME:OFF_RUNTIME + len(RUNTIME)] = RUNTIME
        changed.append(
            f"Fire/Fairy x2 special item runtime ${CPU_RUNTIME:04X}-${CPU_RUNTIME + len(RUNTIME) - 1:04X}"
        )
    if bytes(rom_data[OFF_ITEM_PICKUP_HOOK:OFF_ITEM_PICKUP_HOOK + len(HOOK_ITEM_PICKUP)]) != HOOK_ITEM_PICKUP:
        rom_data[OFF_ITEM_PICKUP_HOOK:OFF_ITEM_PICKUP_HOOK + len(HOOK_ITEM_PICKUP)] = HOOK_ITEM_PICKUP
        changed.append("$C55B Fire/Fairy x2 special item hook")
    if bytes(rom_data[OFF_DRAW_HOOK:OFF_DRAW_HOOK + len(HOOK_DRAW)]) != HOOK_DRAW:
        rom_data[OFF_DRAW_HOOK:OFF_DRAW_HOOK + len(HOOK_DRAW)] = HOOK_DRAW
        changed.append("$9DE8 Fire/Fairy x2 special draw hook")
    if bytes(rom_data[OFF_PRG1_LOADER_HELPER:OFF_PRG1_LOADER_HELPER + len(loader_helper)]) != loader_helper:
        rom_data[OFF_PRG1_LOADER_HELPER:OFF_PRG1_LOADER_HELPER + len(loader_helper)] = loader_helper
        changed.append(f"Fire/Fairy x2 special item PRG1 loader ${CPU_PRG1_LOADER_HELPER:04X}")
    slot_off = panel_monster_stage_variant.OFF_PRG1_RUNTIME_LOADER
    if bytes(rom_data[slot_off:slot_off + len(HOOK_PRG1_LOADER)]) != HOOK_PRG1_LOADER:
        rom_data[slot_off:slot_off + len(HOOK_PRG1_LOADER)] = HOOK_PRG1_LOADER
        changed.append("Panel Variant loader -> Fire/Fairy x2 special item loader")
    if bytes(rom_data[OFF_PRG1_SPECIAL_ITEM_TABLE:OFF_PRG1_SPECIAL_ITEM_TABLE + len(table)]) != table:
        rom_data[OFF_PRG1_SPECIAL_ITEM_TABLE:OFF_PRG1_SPECIAL_ITEM_TABLE + len(table)] = table
        changed.append("Fire/Fairy x2 special item position table")
    return changed


RESERVED_SPANS = (
    (OFF_RUNTIME, len(RUNTIME)),
)

PRG1_RESERVED_SPANS = (
    (OFF_PRG1_LOADER_HELPER, len(_build_loader_helper(bytes.fromhex(
        "a9 ff 8d 2a 07 8d 7f 07"
        "a9 00 8d 23 07 8d 24 07 8d 29 07 8d 7a 07"
        "ad 28 04 aa bd 9b 8e 8d 7d 07"
        "8a 0a 0a 0a 85 00"
        "a9 88 69 00 85 01"
        "a0 00 b1 00 29 10 0a 0a 0a 8d 7a 07"
        "a0 06 b1 00 8d 78 07"
        "c8 b1 00 8d 7c 07"
        "a0 02 b1 00 8d 2b 07"
        "c8 b1 00 8d 7e 07"
        "4c 66 8a"
    )))),
    (OFF_PRG1_SPECIAL_ITEM_TABLE, PRG1_SPECIAL_ITEM_TABLE_SIZE),
)


assert len(ITEM_RUNTIME) == 63
assert len(DRAW_RUNTIME) == 55
assert len(RUNTIME) == 126

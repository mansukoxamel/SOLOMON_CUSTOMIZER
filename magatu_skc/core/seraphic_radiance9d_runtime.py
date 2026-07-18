"""Seraphic Radiance enemy ID $9D runtime for mapper66 saved ROMs."""
from __future__ import annotations

from .element import ElementType


NEW_ENEMY_ID = 0x9D

OFF_RUNTIME = 0x6C04
CPU_RUNTIME = 0xEBF4
RUNTIME_CAPACITY = 0x129

CPU_STOCK_INIT = 0x9D1C
CPU_MAIN_TO_SUB_PTR = 0xB156
CPU_MAIN_PTR_LO = 0xB32C
CPU_MAIN_PTR_HI = 0xB341
CPU_SUB_PTR_LO = 0xB306
CPU_SUB_PTR_HI = 0xB317
CPU_STOCK_SOUND = 0x8E8D


class _Asm:
    def __init__(self):
        self.data = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, int, str, str]] = []

    def label(self, name: str) -> None:
        self.labels[name] = len(self.data)

    def b(self, *values: int) -> None:
        self.data.extend(v & 0xFF for v in values)

    def jsr(self, addr: int) -> None:
        self.b(0x20, addr & 0xFF, addr >> 8)

    def branch(self, opcode: int, label: str) -> None:
        self.fixups.append((len(self.data), opcode & 0xFF, label, "rel"))
        self.b(opcode, 0x00)

    def finish(self, cpu_base: int) -> bytes:
        for pos, opcode, label, mode in self.fixups:
            if label not in self.labels:
                raise ValueError(f"unknown label: {label}")
            self.data[pos] = opcode
            rel = self.labels[label] - (pos + 2)
            if mode != "rel" or not -128 <= rel <= 127:
                raise ValueError(f"branch out of range: {label}")
            self.data[pos + 1] = rel & 0xFF
        return bytes(self.data)


SETUP_META_RUNTIME = bytes.fromhex(
    "a0 0e"         # LDY #$0E: stock Fairy group supplies safe no-gravity setup
    "84 0e"         # STY $0E
    "b9 d3 d9"      # LDA $D9D3,Y
    "60"            # RTS
)

OFF_SETUP_META_LOAD = OFF_RUNTIME
CPU_SETUP_META_LOAD = CPU_RUNTIME
OFF_INIT_STATUS = OFF_SETUP_META_LOAD + len(SETUP_META_RUNTIME)
CPU_INIT_STATUS = CPU_SETUP_META_LOAD + len(SETUP_META_RUNTIME)


def _build_init_runtime() -> bytes:
    a = _Asm()
    a.b(0x68)                              # PLA: discard saved stock-init input
    a.b(0xA9, 0xC4, 0x85, 0x04)          # active, visible, no gravity, fire-immune
    a.b(0xA9, NEW_ENEMY_ID, 0x85, 0x05)  # preserve type $9D
    a.b(0xA9, 0x00)
    a.jsr(CPU_STOCK_INIT)
    # Build an inward initial direction from the spawn quadrant.
    # sub[7] bit0: vertical (0=down, 1=up); bit1: horizontal (0=right, 1=left).
    # $9D1C leaves the current main-slot pointer in $00/$01.
    a.b(0xA0, 0x0A, 0xB1, 0x00, 0xC9, 0x88)  # carry = X >= center
    a.b(0xA9, 0x00, 0x2A, 0xAA)              # X = horizontal direction bit
    a.b(0xA0, 0x07, 0xB1, 0x00, 0xC9, 0x78)  # carry = Y >= center
    a.b(0x8A, 0x2A)                          # bit1=X direction, bit0=Y direction
    a.b(0x48, 0xA5, 0x06)                    # preserve direction; load slot index
    a.jsr(CPU_MAIN_TO_SUB_PTR)
    a.b(0x68)                                # restore direction
    a.b(0xA0, 0x07, 0x91, 0x00)              # store direction; phase bit2 starts clear
    a.b(0x60)
    return a.finish(CPU_INIT_STATUS)


INIT_STATUS_RUNTIME = _build_init_runtime()
OFF_PHASE_RUNTIME = OFF_INIT_STATUS + len(INIT_STATUS_RUNTIME)
CPU_PHASE_RUNTIME = CPU_INIT_STATUS + len(INIT_STATUS_RUNTIME)
PHASE_RUNTIME_SIZE = 12
OFF_AI_DISPATCH = OFF_PHASE_RUNTIME + PHASE_RUNTIME_SIZE
CPU_AI_DISPATCH = CPU_PHASE_RUNTIME + PHASE_RUNTIME_SIZE


def _build_ai_runtime() -> tuple[bytes, dict[str, int]]:
    a = _Asm()
    # Vertical 1 px/frame movement. sub[7] bit0: 0=down, 1=up.
    a.b(0xA0, 0x07, 0xB1, 0x2C, 0x29, 0x01)
    a.branch(0xD0, "move_up")
    a.b(0xA0, 0x07, 0xB1, 0x2E, 0xC9, 0xD0)
    a.branch(0xB0, "turn_up")
    a.b(0x18, 0x69, 0x01, 0x91, 0x2E)
    a.branch(0xD0, "collide")
    a.label("turn_up")
    a.b(0xA0, 0x07, 0xB1, 0x2C, 0x09, 0x01, 0x91, 0x2C)
    a.branch(0xD0, "collide")
    a.label("move_up")
    a.b(0xA0, 0x07, 0xB1, 0x2E, 0xC9, 0x21)
    a.branch(0x90, "turn_down")
    a.b(0x38, 0xE9, 0x01, 0x91, 0x2E)
    a.branch(0xD0, "collide")
    a.label("turn_down")
    a.b(0xA0, 0x07, 0xB1, 0x2C, 0x29, 0xFE, 0x91, 0x2C)

    # Horizontal 1 px/frame movement. sub[7] bit1: 0=right, 1=left.
    a.label("move_x")
    a.b(0xA0, 0x07, 0xB1, 0x2C, 0x29, 0x02)
    a.branch(0xD0, "move_left")
    a.b(0xA0, 0x0A, 0xB1, 0x2E, 0xC9, 0xE8)
    a.branch(0xB0, "turn_left")
    a.b(0x18, 0x69, 0x01, 0x91, 0x2E)
    a.branch(0xD0, "x_done")
    a.label("turn_left")
    a.b(0xA0, 0x07, 0xB1, 0x2C, 0x09, 0x02, 0x91, 0x2C)
    a.branch(0xD0, "x_done")
    a.label("move_left")
    a.b(0xA0, 0x0A, 0xB1, 0x2E, 0xC9, 0x09)
    a.branch(0x90, "turn_right")
    a.b(0x38, 0xE9, 0x01, 0x91, 0x2E)
    a.branch(0xD0, "x_done")
    a.label("turn_right")
    a.b(0xA0, 0x07, 0xB1, 0x2C, 0x29, 0xFD, 0x91, 0x2C)

    a.label("x_done")
    a.b(0x60)

    # Scan all 17 enemy slots. A 16x16 overlap clears main+paired sub slot only;
    # no stock death/drop/score route is called.
    a.label("collide")
    a.b(0xA2, 0x10)
    a.label("scan")
    a.b(0xBD, CPU_MAIN_PTR_LO & 0xFF, CPU_MAIN_PTR_LO >> 8, 0x85, 0x00)
    a.b(0xBD, CPU_MAIN_PTR_HI & 0xFF, CPU_MAIN_PTR_HI >> 8, 0x85, 0x01)
    a.b(0xA0, 0x00, 0xB1, 0x00)
    a.branch(0x10, "next")
    a.b(0xC8, 0xB1, 0x00, 0xC9, NEW_ENEMY_ID)
    a.branch(0xF0, "next")
    a.b(0xA0, 0x0A, 0xB1, 0x00, 0x38, 0xF1, 0x2E)
    a.branch(0xB0, "x_abs")
    a.b(0x49, 0xFF, 0x69, 0x01)
    a.label("x_abs")
    a.b(0xC9, 0x10)
    a.branch(0xB0, "next")
    a.b(0xA0, 0x07, 0xB1, 0x00, 0x38, 0xF1, 0x2E)
    a.branch(0xB0, "y_abs")
    a.b(0x49, 0xFF, 0x69, 0x01)
    a.label("y_abs")
    a.b(0xC9, 0x10)
    a.branch(0xB0, "next")
    a.b(0xA9, 0x00, 0xA0, 0x00, 0x91, 0x00)  # clear target main status
    a.b(0x8A, 0xA8)
    a.b(0xB9, CPU_SUB_PTR_LO & 0xFF, CPU_SUB_PTR_LO >> 8, 0x85, 0x00)
    a.b(0xB9, CPU_SUB_PTR_HI & 0xFF, CPU_SUB_PTR_HI >> 8, 0x85, 0x01)
    a.b(0xA0, 0x00, 0xA9, 0x00, 0x91, 0x00)  # clear paired sub status
    a.b(0xA0, 0x08)
    a.jsr(CPU_STOCK_SOUND)                      # stock block-removal sound
    a.label("next")
    a.b(0xCA)
    a.branch(0x10, "scan")
    a.b(0x60)
    runtime = a.finish(CPU_AI_DISPATCH)
    return runtime, {name: CPU_AI_DISPATCH + offset for name, offset in a.labels.items()}


AI_DISPATCH_RUNTIME, _AI_LABELS = _build_ai_runtime()
CPU_MOVE_X = _AI_LABELS["move_x"]


def _build_phase_runtime() -> bytes:
    branch_from = CPU_PHASE_RUNTIME + PHASE_RUNTIME_SIZE
    rel = CPU_MOVE_X - branch_from
    if not -128 <= rel <= 127:
        raise ValueError("phase-to-X branch out of range")
    return bytes.fromhex(
        "a0 07"         # LDY #$07: direction/phase byte
        "b1 2c"         # LDA (sub),Y
        "49 04"         # EOR #$04: alternate X/Y phase
        "91 2c"         # STA (sub),Y
        "29 04"         # AND #$04
        f"d0 {rel & 0xFF:02x}"  # phase set: X; clear falls through to Y
    )


PHASE_RUNTIME = _build_phase_runtime()
OFF_ANIM_UPDATE = OFF_AI_DISPATCH + len(AI_DISPATCH_RUNTIME)
CPU_ANIM_UPDATE = CPU_AI_DISPATCH + len(AI_DISPATCH_RUNTIME)


ANIM_UPDATE_RUNTIME = bytes.fromhex(
    "a5 21"         # LDA $21: global frame counter
    "29 08"         # alternate every 8 frames
    "f0 06"         # BEQ frame031
    "a9 b2"         # frame030 tile 1
    "a2 cf"         # frame030 packed attr
    "d0 04"         # always store
    "a9 b0"         # frame031 tile 1
    "a2 ce"         # frame031 packed attr
    "a0 11"         # main[17] tile 1
    "91 08"
    "c8"            # main[18] tile 2
    "91 08"
    "c8"            # main[19] attr
    "8a"
    "91 08"
    "60"
)

RUNTIME = SETUP_META_RUNTIME + INIT_STATUS_RUNTIME + PHASE_RUNTIME + AI_DISPATCH_RUNTIME + ANIM_UPDATE_RUNTIME
CPU_RUNTIME_END = CPU_RUNTIME + len(RUNTIME)
CPU_AI_ENTRY = CPU_PHASE_RUNTIME
RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert len(RUNTIME) == RUNTIME_CAPACITY
assert CPU_RUNTIME + len(RUNTIME) == CPU_RUNTIME_END
assert len(SETUP_META_RUNTIME) == 8
assert len(AI_DISPATCH_RUNTIME) == 205
assert len(RUNTIME) == 297
assert len(PHASE_RUNTIME) == PHASE_RUNTIME_SIZE


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "type", None) == ElementType.ENEMY and int(enemy.element_no) == NEW_ENEMY_ID:
                return True
    return False

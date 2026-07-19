"""Open the key door when all enemy slots are gone."""
from __future__ import annotations

from . import stage_ext


class EnemyClearKeyOpenError(ValueError):
    pass


OFF_MAIN_LOOP_HOOK = 0x1F19   # CPU $9F09
CPU_MAIN_LOOP_HOOK = 0x9F09
ORIG_MAIN_LOOP_HOOK = bytes.fromhex("ae 3e 04")
ROOM_FLAG_MAIN_LOOP_CONTINUE_HOOK = bytes.fromhex("4c c0 9e")

OFF_RUNTIME = 0x4156
CPU_RUNTIME = 0xC146
CPU_MAIN_LOOP_CONTINUE = 0x9EC0
CPU_CELL_FROM_PIXEL = 0x918A
CPU_KEY_HANDLER = 0xC663
CPU_ACTION_START = 0x8D5F

RAM_RUNTIME_STATE = 0x0770
RAM_FAIRY2_DELAY = 0x0771
RAM_ACTIVE_TASK_BITMAP = 0x0303
RAM_DANA_Y = 0x0586
RAM_DANA_X = 0x0589
RAM_KEY_LIGHT_START_CELL_PLUS1 = 0x0724

RAM_RESERVED_SPANS = (
    (RAM_KEY_LIGHT_START_CELL_PLUS1, 1),
    (RAM_RUNTIME_STATE, 1),
    (RAM_FAIRY2_DELAY, 1),
)

MODE_BIT = 0x10
LATCH_BIT = 0x80
ACTION_GROUP4_BIT = 0x10
CPU_ADD_FAIRY_QUEUE = 0xC7AA

HOOK_MAIN_LOOP = bytes((0x4C, CPU_RUNTIME & 0xFF, CPU_RUNTIME >> 8))


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
    a.abs(0xAD, RAM_FAIRY2_DELAY)       # LDA $0771
    a.rel(0xF0, "mode_check")           # BEQ mode_check
    a.abs(0xCE, RAM_FAIRY2_DELAY)       # DEC $0771
    a.rel(0xD0, "mode_check")           # BNE mode_check
    a.abs(0x20, CPU_ADD_FAIRY_QUEUE)

    a.label("mode_check")
    a.abs(0xAD, RAM_RUNTIME_STATE)     # LDA $0770
    a.b(0x29, MODE_BIT)                # AND #mode
    a.rel(0xD0, "check_latch")         # BNE check_latch
    a.abs(0x4C, CPU_MAIN_LOOP_CONTINUE)

    a.label("check_latch")
    a.abs(0xAD, RAM_RUNTIME_STATE)     # LDA $0770
    a.rel(0x10, "scan")                # BPL scan
    a.abs(0x4C, CPU_MAIN_LOOP_CONTINUE)

    a.label("scan")
    a.b(0xA2, 0x10)                    # LDX #$10
    a.label("scan_loop")
    a.b(0xBD, 0x2C, 0xB3)              # LDA $B32C,X
    a.b(0x85, 0x00)                    # STA $00
    a.b(0xBD, 0x41, 0xB3)              # LDA $B341,X
    a.b(0x85, 0x01)                    # STA $01
    a.b(0xA0, 0x00)                    # LDY #0
    a.b(0xB1, 0x00)                    # LDA ($00),Y
    a.b(0xC9, 0xC0)                    # CMP #$C0
    a.rel(0x90, "scan_next")           # inactive
    a.b(0xA0, 0x01)                    # LDY #1
    a.b(0xB1, 0x00)                    # LDA ($00),Y
    a.b(0xC9, 0x14)                    # CMP #$14
    a.rel(0xF0, "scan_next")           # item remnant is ignored
    a.b(0xC9, 0x9D)                    # CMP #$9D
    a.rel(0xF0, "scan_next")           # Seraphic Radiance is ignored
    a.b(0x29, 0xFD)                    # AND #$FD maps $81/$83 to $81
    a.b(0xC9, 0x81)                    # CMP #$81
    a.rel(0xF0, "scan_next")           # unbeatable Blue Burn is ignored
    a.abs(0x4C, CPU_MAIN_LOOP_CONTINUE)

    a.label("scan_next")
    a.b(0xCA)                          # DEX
    a.rel(0x10, "scan_loop")           # BPL scan_loop

    a.abs(0xAD, RAM_ACTIVE_TASK_BITMAP)  # wait for item pickup cleanup action $40-$4F
    a.b(0x29, ACTION_GROUP4_BIT)
    a.rel(0xF0, "latch")
    a.abs(0x4C, CPU_MAIN_LOOP_CONTINUE)

    a.label("latch")
    a.abs(0xAD, RAM_RUNTIME_STATE)     # latch
    a.b(0x09, LATCH_BIT)
    a.abs(0x8D, RAM_RUNTIME_STATE)

    a.abs(0xAD, RAM_DANA_Y)            # Dana Y + 8
    a.b(0x18, 0x69, 0x08)
    a.b(0x85, 0x04)
    a.abs(0xAD, RAM_DANA_X)            # Dana X + 8
    a.b(0x18, 0x69, 0x08)
    a.b(0x85, 0x05)
    a.abs(0x20, CPU_CELL_FROM_PIXEL)   # X = center cell
    a.b(0x8A, 0x18, 0x69, 0x01)
    a.abs(0x8D, RAM_KEY_LIGHT_START_CELL_PLUS1)

    a.abs(0x20, CPU_KEY_HANDLER)       # original/key-enemy key handler
    a.b(0xA9, 0x34)
    a.abs(0x20, CPU_ACTION_START)      # enter light animation route
    a.abs(0x4C, CPU_MAIN_LOOP_CONTINUE)
    return a.finish()


RUNTIME = _build_runtime()


def levels_need_runtime(levels: list) -> bool:
    return any(stage_ext.enemy_clear_key_open_enabled(level) for level in (levels or []))


def _expect(data: bytes | bytearray, off: int, allowed: tuple[bytes, ...], name: str) -> None:
    size = len(allowed[0])
    cur = bytes(data[off:off + size])
    if cur in allowed:
        return
    expected = " or ".join(blob.hex(" ") for blob in allowed)
    raise EnemyClearKeyOpenError(
        f"{name} signature mismatch at 0x{off:X}: expected {expected}, got {cur.hex(' ')}"
    )


def _expect_blank_or(data: bytes | bytearray, off: int, blob: bytes, name: str) -> None:
    cur = bytes(data[off:off + len(blob)])
    if cur == blob or all(b in (0xEA, 0x00) for b in cur):
        return
    raise EnemyClearKeyOpenError(
        f"{name} area is not blank at 0x{off:X}: expected EA/00 or existing runtime, got {cur.hex(' ')}"
    )


def apply(rom_data: bytearray, levels: list) -> list[str]:
    if rom_data is None or len(rom_data) < OFF_RUNTIME + len(RUNTIME):
        raise EnemyClearKeyOpenError("ROM is too short for Enemy Clear Key Open runtime.")

    _expect(
        rom_data,
        OFF_MAIN_LOOP_HOOK,
        (ORIG_MAIN_LOOP_HOOK, ROOM_FLAG_MAIN_LOOP_CONTINUE_HOOK, HOOK_MAIN_LOOP),
        "$9F09 Enemy Clear Key Open hook",
    )
    _expect_blank_or(rom_data, OFF_RUNTIME, RUNTIME, "Enemy Clear Key Open runtime")

    changed: list[str] = []
    if bytes(rom_data[OFF_RUNTIME:OFF_RUNTIME + len(RUNTIME)]) != RUNTIME:
        rom_data[OFF_RUNTIME:OFF_RUNTIME + len(RUNTIME)] = RUNTIME
        changed.append(
            f"Enemy Clear Key Open runtime ${CPU_RUNTIME:04X}-${CPU_RUNTIME + len(RUNTIME) - 1:04X}"
        )
    if bytes(rom_data[OFF_MAIN_LOOP_HOOK:OFF_MAIN_LOOP_HOOK + len(HOOK_MAIN_LOOP)]) != HOOK_MAIN_LOOP:
        rom_data[OFF_MAIN_LOOP_HOOK:OFF_MAIN_LOOP_HOOK + len(HOOK_MAIN_LOOP)] = HOOK_MAIN_LOOP
        changed.append("$9F09 Enemy Clear Key Open hook")
    return changed


RESERVED_SPANS = (
    (OFF_RUNTIME, len(RUNTIME)),
)

assert len(RUNTIME) == 130

"""Spark Trail enemy runtime for IDs $D8-$DF."""
from __future__ import annotations


class SparkTrailRuntimeError(ValueError):
    pass


FIRST_ID = 0xD8
LAST_ID = 0xDF
SLOW_FIRST_ID = 0xD8
FAST_FIRST_ID = 0xDC
NEW_ENEMY_IDS = tuple(range(FIRST_ID, LAST_ID + 1))

OFF_MAIN_RUNTIME = 0x6E19
CPU_MAIN_RUNTIME = 0xEE09
MAIN_CAPACITY = 0x6EB4 - OFF_MAIN_RUNTIME

# Spark24 grows through $BF79 when its AI dispatcher gains the Spark Trail route.
OFF_AUX_RUNTIME = 0x3F8A
CPU_AUX_RUNTIME = 0xBF7A
AUX_CAPACITY = 0x4010 - OFF_AUX_RUNTIME

OFF_GRID_READ_HOOK = 0x29B2
CPU_GRID_READ_HOOK = 0xA9A2
ORIG_GRID_READ = bytes.fromhex("BD 04 03")

CPU_STOCK_SPARK_BODY = 0xA92F
CPU_PIXEL_TO_CELL = 0x918A
CPU_CELL_TO_CENTER = 0x91A3
CPU_SLOT_OVERLAP = 0x9D34
CPU_DRAW_CELL = 0x9D53
CPU_MAIN_PTR_LO = 0xB328
CPU_MAIN_PTR_HI = 0xB33D


class _Asm:
    def __init__(self, origin: int):
        self.origin = origin
        self.data = bytearray()
        self.labels: dict[str, int] = {}
        self.branches: list[tuple[int, str]] = []
        self.absolute: list[tuple[int, str]] = []

    def b(self, *values: int) -> None:
        self.data.extend(value & 0xFF for value in values)

    def label(self, name: str) -> None:
        if name in self.labels:
            raise SparkTrailRuntimeError(f"duplicate label: {name}")
        self.labels[name] = len(self.data)

    def branch(self, opcode: int, label: str) -> None:
        self.b(opcode, 0)
        self.branches.append((len(self.data) - 1, label))

    def jsr(self, target: int | str) -> None:
        if isinstance(target, str):
            self.b(0x20, 0, 0)
            self.absolute.append((len(self.data) - 2, target))
        else:
            self.b(0x20, target & 0xFF, target >> 8)

    def jmp(self, target: int | str) -> None:
        if isinstance(target, str):
            self.b(0x4C, 0, 0)
            self.absolute.append((len(self.data) - 2, target))
        else:
            self.b(0x4C, target & 0xFF, target >> 8)

    def absolute_x(self, opcode: int, label: str) -> None:
        self.b(opcode, 0, 0)
        self.absolute.append((len(self.data) - 2, label))

    def address(self, label: str) -> int:
        return self.origin + self.labels[label]

    def finish(self) -> bytes:
        for operand, label in self.branches:
            if label not in self.labels:
                raise SparkTrailRuntimeError(f"unknown label: {label}")
            delta = self.labels[label] - (operand + 1)
            if not -128 <= delta <= 127:
                raise SparkTrailRuntimeError(f"branch to {label} is out of range")
            self.data[operand] = delta & 0xFF
        for operand, label in self.absolute:
            if label not in self.labels:
                raise SparkTrailRuntimeError(f"unknown label: {label}")
            target = self.origin + self.labels[label]
            self.data[operand] = target & 0xFF
            self.data[operand + 1] = target >> 8
        return bytes(self.data)


def _build_main_runtime() -> tuple[bytes, int]:
    a = _Asm(CPU_MAIN_RUNTIME)

    # Keep the old cell on the stack exactly as the verified V9 runtime did.
    # The stock Spark body clears zero page $00-$07, so the old cell cannot
    # survive there. The direct enemy ID's bit 2 selects stock X=$00/$04.
    a.jsr("position_to_cell")
    a.b(0x48)                        # old cell
    a.b(0xA0, 0x01, 0xB1, 0x2E)     # direct enemy ID
    a.b(0x29, 0x04, 0xAA)           # D8-DB: X=0; DC-DF: X=4
    a.jsr(CPU_STOCK_SPARK_BODY)
    a.jsr("position_to_cell")
    a.b(0x85, 0x00)                 # new cell
    a.b(0x68)                        # old cell
    a.b(0xC5, 0x00)                 # new cell == old cell?
    a.branch(0xF0, "done")
    a.b(0xA8)                       # Y = old cell
    a.b(0xB9, 0x04, 0x03)           # source cell

    # Own blocks expand one orthogonal frontier cell per revisit.
    a.b(0xC9, 0xC8)
    a.branch(0x90, "source")
    a.b(0xC9, 0xF8)
    a.branch(0xB0, "done")
    a.jmp(CPU_AUX_RUNTIME)

    # Fold $48-$77 onto $08-$37. Carry is clear after CMP #$78.
    a.label("source")
    a.b(0xC9, 0x78)
    a.branch(0xB0, "done")
    a.b(0x29, 0x3F)
    a.b(0x69, 0xF8)
    a.b(0xC9, 0x30)
    a.branch(0xB0, "done")
    a.jmp("guarded_place")

    a.label("done")
    a.b(0x60)

    a.label("position_to_cell")
    a.b(0xA0, 0x07, 0xB1, 0x2E)
    a.b(0x18, 0x69, 0x08, 0x85, 0x04)
    a.b(0xA0, 0x0A, 0xB1, 0x2E)
    a.b(0x18, 0x69, 0x08, 0x85, 0x05)
    a.jmp(CPU_PIXEL_TO_CELL)

    a.label("guarded_place")
    guarded_place = a.address("guarded_place")
    a.b(0x84, 0x02, 0x84, 0x04)
    a.jsr(CPU_CELL_TO_CENTER)
    a.b(0xA2, 0x14)                 # 21 moving sprite slots

    a.label("sprite_loop")
    a.b(0xBD, CPU_MAIN_PTR_LO & 0xFF, CPU_MAIN_PTR_LO >> 8, 0x85, 0x06)
    a.b(0xBD, CPU_MAIN_PTR_HI & 0xFF, CPU_MAIN_PTR_HI >> 8, 0x85, 0x07)
    a.b(0xA5, 0x06, 0xC5, 0x2E)
    a.branch(0xD0, "check_sprite")
    a.b(0xA5, 0x07, 0xC5, 0x2F)
    a.branch(0xF0, "next_sprite")

    a.label("check_sprite")
    a.jsr(CPU_SLOT_OVERLAP)
    a.branch(0x90, "occupied")

    a.label("next_sprite")
    a.b(0xCA)
    a.branch(0x10, "sprite_loop")

    a.b(0xA4, 0x02)
    a.b(0xB9, 0x04, 0x03)
    a.b(0x09, 0xC0)
    a.b(0x99, 0x04, 0x03)
    a.b(0xA9, 0x01, 0x85, 0x03)
    a.jsr(CPU_DRAW_CELL)

    a.label("occupied")
    a.b(0x60)

    runtime = a.finish()
    if len(runtime) > MAIN_CAPACITY:
        raise SparkTrailRuntimeError(
            f"main runtime is {len(runtime)} bytes; capacity is {MAIN_CAPACITY}"
        )
    return runtime, guarded_place


def _build_aux_runtime(guarded_place: int) -> tuple[bytes, int]:
    a = _Asm(CPU_AUX_RUNTIME)

    a.label("frontier_expand")
    a.b(0x98, 0x48, 0xA2, 0x00)

    a.label("neighbor_loop")
    a.b(0xE0, 0x02)
    a.branch(0x90, "candidate")
    a.b(0x68, 0x48, 0x29, 0x0F)
    a.b(0xE0, 0x02)
    a.branch(0xD0, "right_edge")
    a.b(0xC9, 0x00)
    a.branch(0xF0, "next_neighbor")
    a.branch(0xD0, "candidate")

    a.label("right_edge")
    a.b(0xC9, 0x0F)
    a.branch(0xF0, "next_neighbor")

    a.label("candidate")
    a.b(0x68, 0x48, 0x18)
    a.absolute_x(0x7D, "neighbor_offsets")
    a.b(0xA8, 0xB9, 0x04, 0x03)
    a.b(0xC9, 0x78)
    a.branch(0xB0, "next_neighbor")
    a.b(0x29, 0x3F, 0x69, 0xF8, 0xC9, 0x30)
    a.branch(0xB0, "next_neighbor")
    a.b(0xAA, 0x68, 0x8A)
    a.jmp(guarded_place)

    a.label("next_neighbor")
    a.b(0xE8, 0xE0, 0x04)
    a.branch(0x90, "neighbor_loop")
    a.b(0x68, 0xA8, 0x60)

    a.label("spark_map_read")
    spark_map_read = a.address("spark_map_read")
    a.b(0x98, 0x48, 0xA0, 0x01, 0xB1, 0x2E)
    a.b(0x29, 0xF8, 0xC9, FIRST_ID)
    a.branch(0xD0, "raw_map_read")
    a.b(0xBD, 0x04, 0x03)
    a.b(0xC9, 0xC8)
    a.branch(0x90, "raw_map_value")
    a.b(0xC9, 0xF8)
    a.branch(0xB0, "raw_map_value")
    a.b(0x29, 0x7F)

    a.label("raw_map_value")
    a.b(0xAA, 0x68, 0xA8, 0x8A, 0x60)

    a.label("raw_map_read")
    a.b(0xBD, 0x04, 0x03)
    a.jmp("raw_map_value")

    a.label("neighbor_offsets")
    a.b(0xF0, 0x10, 0xFF, 0x01)

    runtime = a.finish()
    if len(runtime) > AUX_CAPACITY:
        raise SparkTrailRuntimeError(
            f"aux runtime is {len(runtime)} bytes; capacity is {AUX_CAPACITY}"
        )
    return runtime, spark_map_read


MAIN_RUNTIME, CPU_GUARDED_PLACE = _build_main_runtime()
AUX_RUNTIME, CPU_SPARK_MAP_READ = _build_aux_runtime(CPU_GUARDED_PLACE)
HOOK_GRID_READ = bytes(
    (0x20, CPU_SPARK_MAP_READ & 0xFF, CPU_SPARK_MAP_READ >> 8)
)

RESERVED_SPANS = (
    (OFF_MAIN_RUNTIME, len(MAIN_RUNTIME)),
    (OFF_AUX_RUNTIME, len(AUX_RUNTIME)),
)


def levels_need_runtime(levels: list) -> bool:
    return any(
        FIRST_ID <= int(getattr(enemy, "element_no", -1)) <= LAST_ID
        for level in (levels or [])
        for enemy in (getattr(level, "enemies", []) or [])
    )


def _expect_blank_or(data: bytes | bytearray, off: int, blob: bytes, name: str) -> None:
    current = bytes(data[off:off + len(blob)])
    if current == blob or all(value in (0x00, 0xEA) for value in current):
        return
    raise SparkTrailRuntimeError(
        f"{name} is not blank at file 0x{off:X}: got {current.hex(' ')}"
    )


def _write(data: bytearray, off: int, blob: bytes, changed: list[str], name: str) -> None:
    if bytes(data[off:off + len(blob)]) != blob:
        data[off:off + len(blob)] = blob
        changed.append(name)


def validate(rom_data: bytes | bytearray) -> None:
    min_len = max(
        OFF_MAIN_RUNTIME + len(MAIN_RUNTIME),
        OFF_AUX_RUNTIME + len(AUX_RUNTIME),
        OFF_GRID_READ_HOOK + len(HOOK_GRID_READ),
    )
    if rom_data is None or len(rom_data) < min_len:
        raise SparkTrailRuntimeError("ROM is too short for Spark Trail runtime.")

    current_hook = bytes(
        rom_data[OFF_GRID_READ_HOOK:OFF_GRID_READ_HOOK + len(HOOK_GRID_READ)]
    )
    if current_hook not in (ORIG_GRID_READ, HOOK_GRID_READ):
        raise SparkTrailRuntimeError(
            f"$A9A2 grid-read signature mismatch: got {current_hook.hex(' ')}"
        )
    _expect_blank_or(
        rom_data, OFF_MAIN_RUNTIME, MAIN_RUNTIME, "Spark Trail main runtime"
    )
    _expect_blank_or(
        rom_data, OFF_AUX_RUNTIME, AUX_RUNTIME, "Spark Trail auxiliary runtime"
    )


def apply(rom_data: bytearray) -> list[str]:
    validate(rom_data)
    changed: list[str] = []
    _write(
        rom_data, OFF_MAIN_RUNTIME, MAIN_RUNTIME, changed,
        f"Spark Trail main ${CPU_MAIN_RUNTIME:04X}-"
        f"${CPU_MAIN_RUNTIME + len(MAIN_RUNTIME) - 1:04X}",
    )
    _write(
        rom_data, OFF_AUX_RUNTIME, AUX_RUNTIME, changed,
        f"Spark Trail auxiliary ${CPU_AUX_RUNTIME:04X}-"
        f"${CPU_AUX_RUNTIME + len(AUX_RUNTIME) - 1:04X}",
    )
    _write(
        rom_data, OFF_GRID_READ_HOOK, HOOK_GRID_READ, changed,
        "$A9A2 Spark Trail map-read hook",
    )
    return changed

"""Integrated 24-ID Spark Ball runtime for mapper66 saved ROMs."""
from __future__ import annotations


class Spark24RuntimeError(ValueError):
    pass


FIRST_ID = 0xC0
LAST_ID = 0xD7
PROPERTY_LAST_ID = 0xDF
PAUSE_FIRST_ID = 0xC0
TRANSPARENT_FIRST_ID = 0xC8
REVERSE_FIRST_ID = 0xD0
SPARK_TRAIL_FIRST_DISPATCH = 0xD8 - 0x14

OFF_RUNTIME = 0x3ED0
CPU_RUNTIME = 0xBEC0
RUNTIME_CAPACITY = 320

DEFAULT_PAUSE_DIGITS = (0, 3, 6, 9)
DEFAULT_REVERSE_DIGITS = (1, 8, 8, 8)
PAUSE_DIGIT_COUNT = 4
TRANSPARENCY_PERIODS = (0x20, 0x30, 0x40, 0x60, 0x80)
DEFAULT_TRANSPARENCY_PERIOD = 0x40

CPU_STOCK_SPARK_SLOW = 0xA929
CPU_STOCK_SPARK_FAST = 0xA92D
CPU_STOCK_SPEED_COMMIT = 0xAB13
CPU_PANEL_PROPERTY_HOOK = 0xE6DF
CPU_STOCK_OAM_RETURN = 0x8608
CPU_SPARK_TRAIL_AI = 0xEE09


class _Asm:
    def __init__(self, base: int):
        self.base = base
        self.code = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str]] = []

    def b(self, *values: int) -> None:
        self.code.extend(v & 0xFF for v in values)

    def label(self, name: str) -> None:
        self.labels[name] = len(self.code)

    def branch(self, opcode: int, label: str) -> None:
        self.b(opcode, 0)
        self.fixups.append((len(self.code) - 1, label))

    def jmp(self, cpu: int) -> None:
        self.b(0x4C, cpu & 0xFF, cpu >> 8)

    def finish(self) -> bytes:
        for operand, label in self.fixups:
            rel = self.labels[label] - (operand + 1)
            if not -128 <= rel <= 127:
                raise Spark24RuntimeError(f"branch to {label} is out of range")
            self.code[operand] = rel & 0xFF
        return bytes(self.code)


def normalize_digits(values) -> tuple[int, int, int, int]:
    result: list[int] = []
    for value in values:
        digit = int(value)
        if not 0 <= digit <= 9:
            raise Spark24RuntimeError("LIFE hundreds digits must be in the range 0-9")
        if digit not in result:
            result.append(digit)
        if len(result) > PAUSE_DIGIT_COUNT:
            raise Spark24RuntimeError("At most four LIFE hundreds digits can be selected")
    if not result:
        raise Spark24RuntimeError("At least one LIFE hundreds digit must be selected")
    while len(result) < PAUSE_DIGIT_COUNT:
        result.append(result[-1])
    return tuple(result)


def _build_ai_dispatch(base: int, include_spark_trail: bool = True) -> bytes:
    a = _Asm(base)
    if include_spark_trail:
        # The shared entry also sends $D8-$DF here. Keep Spark24 unchanged and
        # route that upper family to its dedicated block-trail body.
        a.b(0xC9, SPARK_TRAIL_FIRST_DISPATCH)
        a.branch(0xB0, "spark_trail")
    # The shared AI entry restores the stock dispatcher input (enemy ID - $14)
    # before jumping here, so normalize from $C0-$14 rather than from $C0.
    a.b(0x38, 0xE9, FIRST_ID - 0x14, 0x29, 0x04)  # SEC/SBC #$AC/AND #$04
    a.branch(0xF0, "slow")
    a.jmp(CPU_STOCK_SPARK_FAST)
    a.label("slow")
    a.jmp(CPU_STOCK_SPARK_SLOW)
    if include_spark_trail:
        a.label("spark_trail")
        a.jmp(CPU_SPARK_TRAIL_AI)
    return a.finish()


def _build_pause_dispatch(base: int, pause_digits, reverse_digits) -> tuple[bytes, tuple[int, ...], tuple[int, ...]]:
    pause_digits = normalize_digits(pause_digits)
    reverse_digits = normalize_digits(reverse_digits)
    a = _Asm(base)
    a.b(0xA0, 0x01, 0xB1, 0x2E)  # entity type
    a.b(0xC9, PAUSE_FIRST_ID); a.branch(0x90, "commit")
    a.b(0xC9, LAST_ID + 1); a.branch(0xB0, "commit")
    a.b(0x38, 0xE9, FIRST_ID)
    a.b(0xC9, 0x08); a.branch(0x90, "pause_check")
    a.b(0xC9, 0x10); a.branch(0x90, "commit")
    a.label("reverse_check")
    a.b(0xAD, 0x39, 0x04)
    reverse_offsets = []
    for digit in reverse_digits:
        a.b(0xC9, digit); reverse_offsets.append(len(a.code) - 1); a.branch(0xF0, "reverse")
    a.branch(0xD0, "reverse_clear")
    a.label("reverse_clear")
    a.b(0xA0, 0x00, 0xB1, 0x2C, 0x29, 0xFB, 0x91, 0x2C)
    a.b(0xA9, 0x01); a.branch(0xD0, "commit")
    a.label("pause_check")
    a.b(0xAD, 0x39, 0x04)
    pause_offsets = []
    for digit in pause_digits:
        a.b(0xC9, digit); pause_offsets.append(len(a.code) - 1); a.branch(0xF0, "stop")
    a.label("commit")
    a.b(0xA0, 0x07, 0xB5, 0x02, 0x91, 0x2E)
    a.b(0xA0, 0x0A, 0xB5, 0x03, 0x91, 0x2E, 0x60)
    a.label("reverse")
    a.b(0xA0, 0x00, 0xB1, 0x2C, 0x29, 0x04); a.branch(0xD0, "stop")
    a.b(0xB1, 0x2C, 0x09, 0x04, 0x91, 0x2C)
    a.b(0xA0, 0x06, 0xB1, 0x2C, 0x49, 0x01, 0x91, 0x2C)
    a.b(0xC8, 0xB1, 0x2C, 0x49, 0x01, 0x91, 0x2C)
    a.label("stop")
    a.b(0x60)
    blob = a.finish()
    return blob, tuple(reverse_offsets), tuple(pause_offsets)


def _build_property_dispatch(base: int) -> bytes:
    a = _Asm(base)
    a.b(0xA5, 0x05, 0xC9, FIRST_ID); a.branch(0x90, "stock")
    a.b(0xC9, PROPERTY_LAST_ID + 1); a.branch(0xB0, "stock")
    a.b(0xA9, 0x19, 0x60)
    a.label("stock")
    a.jmp(CPU_PANEL_PROPERTY_HOOK)
    return a.finish()


def _build_oam_dispatch(base: int, transparency_period: int) -> tuple[bytes, int]:
    transparency_period = int(transparency_period)
    if transparency_period not in TRANSPARENCY_PERIODS:
        raise Spark24RuntimeError(f"unsupported transparency period: ${transparency_period:02X}")
    a = _Asm(base)
    a.b(0x9D, 0x16, 0x02)
    a.b(0xA0, 0x01, 0xB1, 0x08)
    a.b(0xC9, TRANSPARENT_FIRST_ID); a.branch(0x90, "done")
    a.b(0xC9, REVERSE_FIRST_ID); a.branch(0xB0, "done")
    a.b(0xA5, 0x21, 0x29, transparency_period)
    period_offset = len(a.code) - 1
    a.branch(0xF0, "done")
    a.b(0xA9, 0xF8, 0x9D, 0x10, 0x02, 0x9D, 0x14, 0x02)
    a.label("done")
    a.jmp(CPU_STOCK_OAM_RETURN)
    return a.finish(), period_offset


def _build_runtime(pause_digits=DEFAULT_PAUSE_DIGITS,
                   reverse_digits=DEFAULT_REVERSE_DIGITS,
                   transparency_period=DEFAULT_TRANSPARENCY_PERIOD,
                   include_spark_trail: bool = True):
    chunks: list[bytes] = []
    cpu = CPU_RUNTIME

    ai = _build_ai_dispatch(cpu, include_spark_trail)
    cpu_ai = cpu
    chunks.append(ai); cpu += len(ai)

    pause, reverse_rel, pause_rel = _build_pause_dispatch(cpu, pause_digits, reverse_digits)
    cpu_pause = cpu
    chunks.append(pause); cpu += len(pause)

    prop = _build_property_dispatch(cpu)
    cpu_property = cpu
    chunks.append(prop); cpu += len(prop)

    oam, period_rel = _build_oam_dispatch(cpu, transparency_period)
    cpu_oam = cpu
    chunks.append(oam); cpu += len(oam)

    runtime = b"".join(chunks)
    if len(runtime) > RUNTIME_CAPACITY:
        raise Spark24RuntimeError(
            f"Spark24 runtime is {len(runtime)} bytes; capacity is {RUNTIME_CAPACITY} bytes")
    offsets = {
        "ai": cpu_ai,
        "pause": cpu_pause,
        "property": cpu_property,
        "oam": cpu_oam,
        "pause_digits": tuple((cpu_pause - CPU_RUNTIME) + x for x in pause_rel),
        "reverse_digits": tuple((cpu_pause - CPU_RUNTIME) + x for x in reverse_rel),
        "transparency_period": (cpu_oam - CPU_RUNTIME) + period_rel,
    }
    return runtime, offsets


def build_runtime(pause_digits=DEFAULT_PAUSE_DIGITS,
                  reverse_digits=DEFAULT_REVERSE_DIGITS,
                  transparency_period=DEFAULT_TRANSPARENCY_PERIOD):
    return _build_runtime(
        pause_digits,
        reverse_digits,
        transparency_period,
        include_spark_trail=True,
    )


def build_pre_spark_trail_runtime(pause_digits=DEFAULT_PAUSE_DIGITS,
                                  reverse_digits=DEFAULT_REVERSE_DIGITS,
                                  transparency_period=DEFAULT_TRANSPARENCY_PERIOD):
    return _build_runtime(
        pause_digits,
        reverse_digits,
        transparency_period,
        include_spark_trail=False,
    )


RUNTIME, _OFFSETS = build_runtime()
PRE_SPARK_TRAIL_RUNTIME, _PRE_SPARK_TRAIL_OFFSETS = (
    build_pre_spark_trail_runtime()
)
CPU_AI_DISPATCH = _OFFSETS["ai"]
CPU_PAUSE_DISPATCH = _OFFSETS["pause"]
CPU_PROPERTY_DISPATCH = _OFFSETS["property"]
CPU_OAM_DISPATCH = _OFFSETS["oam"]
CPU_RUNTIME_END = CPU_RUNTIME + len(RUNTIME)
RUNTIME_FREE_LEN = RUNTIME_CAPACITY - len(RUNTIME)
OFF_PAUSE_DIGITS = tuple(OFF_RUNTIME + x for x in _OFFSETS["pause_digits"])
OFF_REVERSE_DIGITS = tuple(OFF_RUNTIME + x for x in _OFFSETS["reverse_digits"])
OFF_TRANSPARENCY_PERIOD = OFF_RUNTIME + _OFFSETS["transparency_period"]

RESERVED_SPANS = ((OFF_RUNTIME, len(RUNTIME)),)

assert OFF_RUNTIME + RUNTIME_CAPACITY == 0x4010
assert CPU_RUNTIME + RUNTIME_CAPACITY == 0xC000
assert len(RUNTIME) == 186
assert RUNTIME_FREE_LEN == 134
assert len(PRE_SPARK_TRAIL_RUNTIME) == 179

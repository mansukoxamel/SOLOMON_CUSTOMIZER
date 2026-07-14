"""Four configurable Phantom Bullet presets for enemy IDs $A0-$AF."""
from __future__ import annotations


class PhantomPresetRuntimeError(ValueError):
    pass


FIRST_ID = 0xA0
LAST_ID = 0xAF
GROUP_NAMES = ("A", "B", "C", "D")
GROUP_COUNT = len(GROUP_NAMES)
IDS_PER_GROUP = 4

OFF_RUNTIME = 0x3DAC
CPU_RUNTIME = 0xBD9C
OFF_PHYSICS_CALL = 0x0680
ORIG_PHYSICS_CALL = bytes.fromhex("20 89 86")
CPU_STOCK_PHYSICS = 0x8689

MIN_SPEED_VALUE = 0x01
MAX_SPEED_VALUE = 0x3F
DEFAULT_SPEED_VALUE = 0x3F

AMPLITUDE_VALUES = tuple(range(0, 201, 25))
DEFAULT_AMPLITUDE_PERCENT = 100
PHASE_OFFSETS = tuple(range(64))
DEFAULT_PHASE_OFFSET = 0

CPU_STOCK_BULLET_STATE0 = 0xAFC7
CPU_STOCK_BULLET_STATE1 = 0xB00A
CPU_STOCK_INIT = 0x9D1C
CPU_STATE_DISPATCH = 0x8EA9
CPU_EXTRACT_STATE = 0xB201
CPU_SUB_SLOT_PTR = 0xB156
RAM_FRAME_COUNTER_LOW = 0x043C

SINE_DELTA_TABLE = bytes((
    0xFD, 0xFD, 0xFD, 0xFC, 0xFC, 0xFC, 0xFC, 0xFB,
    0xFB, 0xFB, 0xFB, 0xFB, 0xFB, 0xFB, 0xFB, 0xFC,
    0xFC, 0xFC, 0xFC, 0xFD, 0xFD, 0xFD, 0xFE, 0xFE,
    0xFF, 0xFF, 0x00, 0x00, 0x01, 0x01, 0x02, 0x02,
    0x03, 0x03, 0x03, 0x04, 0x04, 0x04, 0x04, 0x05,
    0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x04,
    0x04, 0x04, 0x04, 0x03, 0x03, 0x03, 0x02, 0x02,
    0x01, 0x01, 0x00, 0x00, 0xFF, 0xFF, 0xFE, 0xFE,
))

class _Asm:
    def __init__(self, base: int):
        self.base = int(base)
        self.code = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str]] = []

    def b(self, *values: int) -> None:
        self.code.extend(value & 0xFF for value in values)

    def label(self, name: str) -> None:
        self.labels[name] = len(self.code)

    def branch(self, opcode: int, label: str) -> None:
        self.b(opcode, 0x00)
        self.fixups.append((len(self.code) - 1, label))

    def jsr(self, cpu: int) -> None:
        self.b(0x20, cpu & 0xFF, cpu >> 8)

    def jmp(self, cpu: int) -> None:
        self.b(0x4C, cpu & 0xFF, cpu >> 8)

    def finish(self) -> bytes:
        for operand, label in self.fixups:
            if label not in self.labels:
                raise PhantomPresetRuntimeError(f"unknown label: {label}")
            rel = self.labels[label] - (operand + 1)
            if not -128 <= rel <= 127:
                raise PhantomPresetRuntimeError(f"branch to {label} is out of range")
            self.code[operand] = rel & 0xFF
        return bytes(self.code)


def normalize_speed_value(value) -> int:
    try:
        speed = int(value)
    except (TypeError, ValueError):
        speed = DEFAULT_SPEED_VALUE
    if not MIN_SPEED_VALUE <= speed <= MAX_SPEED_VALUE:
        raise PhantomPresetRuntimeError(
            f"unsupported Phantom speed value: {value!r}; expected $01-$3F"
        )
    return speed


def velocity_bytes(speed_value: int) -> bytes:
    speed = normalize_speed_value(speed_value)
    reverse = (-speed) & 0xFF
    return bytes((speed, reverse, reverse, speed))


def default_group_settings() -> tuple[dict[str, int], ...]:
    return tuple(
        {
            "speed_value": DEFAULT_SPEED_VALUE,
            "amplitude_percent": DEFAULT_AMPLITUDE_PERCENT,
            "phase_offset": DEFAULT_PHASE_OFFSET,
        }
        for _group in GROUP_NAMES
    )


def normalize_group_settings(settings) -> tuple[dict[str, int], ...]:
    if settings is None:
        return default_group_settings()
    if not isinstance(settings, (list, tuple)) or len(settings) != GROUP_COUNT:
        raise PhantomPresetRuntimeError(
            f"Phantom settings must contain exactly {GROUP_COUNT} groups"
        )
    normalized = []
    for index, raw in enumerate(settings):
        if not isinstance(raw, dict):
            raise PhantomPresetRuntimeError(
                f"Phantom group {GROUP_NAMES[index]} settings must be a mapping"
            )
        normalized.append({
            "speed_value": normalize_speed_value(raw.get("speed_value")),
            "amplitude_percent": normalize_amplitude_percent(
                raw.get("amplitude_percent")
            ),
            "phase_offset": normalize_phase_offset(raw.get("phase_offset")),
        })
    return tuple(normalized)


def normalize_amplitude_percent(value) -> int:
    try:
        amplitude = int(value)
    except (TypeError, ValueError):
        amplitude = DEFAULT_AMPLITUDE_PERCENT
    if amplitude not in AMPLITUDE_VALUES:
        raise PhantomPresetRuntimeError(
            f"unsupported Phantom amplitude: {value!r}; expected 0-200 in 25 percent steps"
        )
    return amplitude


def normalize_phase_offset(value) -> int:
    try:
        phase = int(value)
    except (TypeError, ValueError):
        phase = DEFAULT_PHASE_OFFSET
    if phase not in PHASE_OFFSETS:
        raise PhantomPresetRuntimeError(
            f"unsupported Phantom phase offset: {value!r}; expected 0-63"
        )
    return phase


def _build_setup() -> bytes:
    return bytes.fromhex("a9 10 85 0e a8 b9 d3 d9 60")


def _build_init() -> bytes:
    a = _Asm(0)
    a.b(0x68)                              # discard saved stock init input
    a.b(0xA9, 0xC0, 0x85, 0x04)          # active, gravity-free entity
    a.b(0xA5, 0x05, 0x29, 0x03)          # direction from each four-ID group
    a.jsr(CPU_STOCK_INIT)
    a.b(0xA5, 0x06)
    a.jsr(CPU_SUB_SLOT_PTR)
    a.b(0xA0, 0x06, 0xA9, 0xFF, 0x91, 0x00, 0x60)
    return a.finish()


def _build_ai(cpu_state2: int) -> bytes:
    return bytes((
        0x20, CPU_EXTRACT_STATE & 0xFF, CPU_EXTRACT_STATE >> 8,
        0x20, CPU_STATE_DISPATCH & 0xFF, CPU_STATE_DISPATCH >> 8,
        CPU_STOCK_BULLET_STATE0 & 0xFF, CPU_STOCK_BULLET_STATE0 >> 8,
        CPU_STOCK_BULLET_STATE1 & 0xFF, CPU_STOCK_BULLET_STATE1 >> 8,
        cpu_state2 & 0xFF, cpu_state2 >> 8,
    ))


def _build_state2(
    cpu_scale_delta: int,
    cpu_sine_table: int,
    cpu_amplitude_table: int,
    cpu_phase_table: int,
) -> bytes:
    a = _Asm(0)
    a.b(0x8A, 0x48)                       # preserve outer enemy-loop X
    a.b(0xA0, 0x01, 0xB1, 0x2E)
    a.b(0x4A, 0x4A, 0x29, 0x03, 0xAA)   # group = (type >> 2) & 3
    a.b(0xBD, cpu_amplitude_table & 0xFF, cpu_amplitude_table >> 8)
    a.branch(0xF0, "restore")
    a.b(0x85, 0x0E)                       # transient amplitude units
    a.b(0xAD, RAM_FRAME_COUNTER_LOW & 0xFF, RAM_FRAME_COUNTER_LOW >> 8)
    a.b(0x4A, 0x18)
    a.b(0x7D, cpu_phase_table & 0xFF, cpu_phase_table >> 8, 0x29, 0x3F)
    a.b(0xA0, 0x06, 0xD1, 0x2C)
    a.branch(0xF0, "restore")
    a.b(0x91, 0x2C, 0xAA)
    a.b(0xBD, cpu_sine_table & 0xFF, cpu_sine_table >> 8)
    a.jsr(cpu_scale_delta)
    a.b(0x48)
    a.b(0xA0, 0x01, 0xB1, 0x2E, 0x29, 0x02)
    a.branch(0xF0, "horizontal")
    a.b(0xA0, 0x0A)                       # vertical travel: wave on X
    a.branch(0xD0, "axis")
    a.label("horizontal")
    a.b(0xA0, 0x07)                       # horizontal travel: wave on Y
    a.label("axis")
    a.b(0x68, 0x18, 0x71, 0x2E, 0x91, 0x2E)
    a.label("restore")
    a.b(0x68, 0xAA)
    a.b(0x60)
    return a.finish()


def _build_scale_delta() -> bytes:
    a = _Asm(0)
    a.b(0xA0, 0x00, 0xC9, 0x80)
    a.branch(0x90, "absolute")
    a.b(0xC8, 0x49, 0xFF, 0x18, 0x69, 0x01)
    a.label("absolute")
    a.b(0x85, 0x0F, 0xA9, 0x00, 0xA6, 0x0E)
    a.branch(0xF0, "divide")
    a.label("multiply")
    a.b(0x18, 0x65, 0x0F, 0xCA)
    a.branch(0xD0, "multiply")
    a.label("divide")
    a.b(0x4A, 0x4A, 0xC0, 0x00)
    a.branch(0xF0, "done")
    a.b(0x49, 0xFF, 0x18, 0x69, 0x01)
    a.label("done")
    a.b(0x60)
    return a.finish()


def _build_apply_speed(cpu_velocity_table: int, cpu_axis_table: int) -> bytes:
    a = _Asm(0)
    a.b(0xA0, 0x01, 0xB1, 0x08, 0x29, 0x0F, 0xA8)
    a.b(0xB9, cpu_velocity_table & 0xFF, cpu_velocity_table >> 8, 0x48)
    a.b(0x98, 0x29, 0x02, 0x4A, 0xA8)
    a.b(0xB9, cpu_axis_table & 0xFF, cpu_axis_table >> 8, 0xA8)
    a.b(0x68, 0x91, 0x08, 0x60)
    return a.finish()


def _build_prephysics(cpu_apply_speed: int) -> bytes:
    a = _Asm(0)
    a.b(0xA0, 0x01, 0xB1, 0x08)
    a.b(0xC9, FIRST_ID)
    a.branch(0x90, "stock")
    a.b(0xC9, LAST_ID + 1)
    a.branch(0xB0, "stock")
    a.b(0xA0, 0x03, 0xB1, 0x08, 0x29, 0xFC, 0xC9, 0x08)
    a.branch(0xD0, "stock")
    a.jsr(cpu_apply_speed)
    a.label("stock")
    a.jmp(CPU_STOCK_PHYSICS)
    return a.finish()


def build_runtime(group_settings=None) -> tuple[bytes, dict[str, int]]:
    group_settings = normalize_group_settings(group_settings)

    setup = _build_setup()
    init_size = 24
    ai_size = 12
    state2_size = 67
    scale_size = 38
    speed_size = 24
    prephysics_size = 28
    velocity_size = 16
    axis_size = 2
    amplitude_size = GROUP_COUNT
    phase_size = GROUP_COUNT

    cpu_setup = CPU_RUNTIME
    cpu_init = cpu_setup + len(setup)
    cpu_ai = cpu_init + init_size
    cpu_state2 = cpu_ai + ai_size
    cpu_scale = cpu_state2 + state2_size
    cpu_speed = cpu_scale + scale_size
    cpu_prephysics = cpu_speed + speed_size
    cpu_velocity = cpu_prephysics + prephysics_size
    cpu_axis = cpu_velocity + velocity_size
    cpu_amplitude = cpu_axis + axis_size
    cpu_phase = cpu_amplitude + amplitude_size
    cpu_sine = cpu_phase + phase_size

    init = _build_init()
    ai = _build_ai(cpu_state2)
    state2 = _build_state2(
        cpu_scale, cpu_sine, cpu_amplitude, cpu_phase
    )
    scale = _build_scale_delta()
    speed = _build_apply_speed(cpu_velocity, cpu_axis)
    prephysics = _build_prephysics(cpu_speed)
    velocity = b"".join(
        velocity_bytes(group["speed_value"])
        for group in group_settings
    )
    axes = bytes((0x08, 0x05))
    amplitudes = bytes(
        group["amplitude_percent"] // 25
        for group in group_settings
    )
    phases = bytes(group["phase_offset"] for group in group_settings)

    if len(init) != init_size or len(ai) != ai_size:
        raise PhantomPresetRuntimeError("Phantom preset fixed section size changed")
    if len(state2) != state2_size or len(scale) != scale_size or len(speed) != speed_size:
        raise PhantomPresetRuntimeError(
            "Phantom preset generated section size changed: "
            f"state2={len(state2)}, scale={len(scale)}, speed={len(speed)}"
        )

    runtime = (
        setup + init + ai + state2 + scale + speed + prephysics
        + velocity + axes + amplitudes + phases + SINE_DELTA_TABLE
    )
    offsets = {
        "setup": cpu_setup,
        "init": cpu_init,
        "ai": cpu_ai,
        "state2": cpu_state2,
        "scale": cpu_scale,
        "apply_speed": cpu_speed,
        "prephysics": cpu_prephysics,
        "velocity_table": cpu_velocity,
        "axis_table": cpu_axis,
        "amplitude_table": cpu_amplitude,
        "phase_table": cpu_phase,
        "sine_table": cpu_sine,
    }
    return runtime, offsets


def current_settings(rom_data) -> dict[str, object]:
    if rom_data is None or len(rom_data) < OFF_RUNTIME + len(RUNTIME):
        raise PhantomPresetRuntimeError("ROM is too short for Phantom preset runtime")
    current = bytes(rom_data[OFF_RUNTIME:OFF_RUNTIME + len(RUNTIME)])
    if all(value in (0x00, 0xEA) for value in current):
        return {"groups": default_group_settings()}
    velocity_rel = _OFFSETS["velocity_table"] - CPU_RUNTIME
    amplitude_rel = _OFFSETS["amplitude_table"] - CPU_RUNTIME
    phase_rel = _OFFSETS["phase_table"] - CPU_RUNTIME
    groups = []
    for index in range(GROUP_COUNT):
        speed_value = int(current[velocity_rel + index * IDS_PER_GROUP])
        amplitude_units = int(current[amplitude_rel + index])
        phase_offset = int(current[phase_rel + index])
        if (
            speed_value == 0
            or amplitude_units > 8
            or phase_offset not in PHASE_OFFSETS
        ):
            raise PhantomPresetRuntimeError(
                f"Phantom group {GROUP_NAMES[index]} has invalid settings bytes"
            )
        groups.append({
            "speed_value": speed_value,
            "amplitude_percent": amplitude_units * 25,
            "phase_offset": phase_offset,
        })
    candidate, _offsets = build_runtime(groups)
    if current == candidate:
        return {"groups": tuple(groups)}
    raise PhantomPresetRuntimeError("Phantom preset runtime has unexpected bytes")


def apply_settings(rom_data, group_settings) -> list[str]:
    group_settings = normalize_group_settings(group_settings)
    current_settings(rom_data)
    runtime, _offsets = build_runtime(group_settings)
    current = bytes(rom_data[OFF_RUNTIME:OFF_RUNTIME + len(runtime)])
    if current == runtime:
        return []
    rom_data[OFF_RUNTIME:OFF_RUNTIME + len(runtime)] = runtime
    return [
        "Phantom group " + GROUP_NAMES[index]
        + f" speed=${group['speed_value']:02X}"
        + f" amplitude={group['amplitude_percent']}%"
        + f" phase={group['phase_offset']}"
        for index, group in enumerate(group_settings)
    ]


RUNTIME, _OFFSETS = build_runtime()
CPU_SETUP_META_LOAD = _OFFSETS["setup"]
CPU_INIT_STATUS = _OFFSETS["init"]
CPU_AI_DISPATCH = _OFFSETS["ai"]
CPU_PREPHYSICS = _OFFSETS["prephysics"]
CPU_RUNTIME_END = CPU_RUNTIME + len(RUNTIME)
HOOK_PHYSICS_CALL = bytes((0x20, CPU_PREPHYSICS & 0xFF, CPU_PREPHYSICS >> 8))
OFF_AMPLITUDE_TABLE = OFF_RUNTIME + (_OFFSETS["amplitude_table"] - CPU_RUNTIME)
OFF_PHASE_TABLE = OFF_RUNTIME + (_OFFSETS["phase_table"] - CPU_RUNTIME)
RESERVED_SPANS = ((OFF_PHYSICS_CALL, len(HOOK_PHYSICS_CALL)), (OFF_RUNTIME, len(RUNTIME)))

assert len(SINE_DELTA_TABLE) == 64
assert sum(value if value < 0x80 else value - 0x100 for value in SINE_DELTA_TABLE) == 0
assert len(RUNTIME) == 292
assert OFF_RUNTIME + len(RUNTIME) == 0x3ED0
assert CPU_RUNTIME_END == 0xBEC0

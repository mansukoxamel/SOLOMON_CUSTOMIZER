"""Parameterized Neul A/B runtime for enemy IDs $84-$87."""
from __future__ import annotations

from . import ghostb0_runtime as _ghostb0
from .element import ElementType


FIRST_ID = 0x84
LAST_ID = 0x87
NEW_ENEMY_IDS = tuple(range(FIRST_ID, LAST_ID + 1))

OFF_RUNTIME = 0x6ED1
CPU_RUNTIME = 0xEEC1
OFF_PARAMETER_TABLE = 0x6FA5
CPU_PARAMETER_TABLE = 0xEF95

CPU_STOCK_NEUL_GHOST_AI = 0xABF7
CPU_FIND_FREE_SUB_SLOT = 0xB2EA
CPU_BULLET_SPAWN = _ghostb0.CPU_BULLET_SPAWN
CPU_SUB_SLOT_PTR = 0xB156

GROUP_NAMES = ("A", "B")
GROUP_COUNT = len(GROUP_NAMES)

BODY_SPEED_NORMAL = 0x18
BODY_SPEED_FAST = 0x1C
BODY_SPEED_VALUES = (BODY_SPEED_NORMAL, BODY_SPEED_FAST)

BULLET_SPEED_STOCK = _ghostb0.BULLET_SPEED_STOCK
BULLET_SPEED_QUARTER = _ghostb0.BULLET_SPEED_QUARTER
BULLET_SPEED_HALF = _ghostb0.BULLET_SPEED_HALF
BULLET_SPEED_2X = _ghostb0.BULLET_SPEED_2X
BULLET_SPEED_3X = _ghostb0.BULLET_SPEED_3X
BULLET_SPEED_VALUES = _ghostb0.BULLET_SPEED_VALUES

COOLDOWN_ARMED = 0x80
MIN_FIRE_INTERVAL = 1
MAX_FIRE_INTERVAL = 0x7F
DEFAULT_BODY_SPEED = BODY_SPEED_NORMAL
DEFAULT_FIRE_INTERVAL = 0x40
DEFAULT_BULLET_SPEED = BULLET_SPEED_STOCK


class Neul84RuntimeError(ValueError):
    pass


def default_group_settings() -> tuple[dict[str, int], ...]:
    return (
        {
            "body_speed": BODY_SPEED_NORMAL,
            "fire_interval": 0x40,
            "bullet_speed": BULLET_SPEED_STOCK,
        },
        {
            "body_speed": BODY_SPEED_FAST,
            "fire_interval": 0x40,
            "bullet_speed": BULLET_SPEED_HALF,
        },
    )


def normalize_group_settings(settings) -> tuple[dict[str, int], ...]:
    if settings is None:
        return default_group_settings()
    if not isinstance(settings, (list, tuple)) or len(settings) != GROUP_COUNT:
        raise Neul84RuntimeError("Neul A/B settings must contain exactly two groups")
    normalized = []
    for index, raw in enumerate(settings):
        if not isinstance(raw, dict):
            raise Neul84RuntimeError(f"Neul group {GROUP_NAMES[index]} settings must be a mapping")
        try:
            body_speed = int(raw.get("body_speed", DEFAULT_BODY_SPEED))
            fire_interval = int(raw.get("fire_interval", DEFAULT_FIRE_INTERVAL))
            bullet_speed = int(raw.get("bullet_speed", DEFAULT_BULLET_SPEED))
        except (TypeError, ValueError) as exc:
            raise Neul84RuntimeError(f"Neul group {GROUP_NAMES[index]} has invalid settings") from exc
        if body_speed not in BODY_SPEED_VALUES:
            raise Neul84RuntimeError(f"Neul group {GROUP_NAMES[index]} has invalid body speed")
        if not MIN_FIRE_INTERVAL <= fire_interval <= MAX_FIRE_INTERVAL:
            raise Neul84RuntimeError(f"Neul group {GROUP_NAMES[index]} fire interval must be 1-127")
        if bullet_speed not in BULLET_SPEED_VALUES:
            raise Neul84RuntimeError(f"Neul group {GROUP_NAMES[index]} has invalid bullet speed")
        normalized.append({
            "body_speed": body_speed,
            "fire_interval": fire_interval,
            "bullet_speed": bullet_speed,
        })
    return tuple(normalized)


def _build_parameter_tables(group_settings) -> bytes:
    groups = normalize_group_settings(group_settings)
    return (
        bytes(group["body_speed"] for group in groups)
        + bytes(group["fire_interval"] for group in groups)
        + bytes(group["bullet_speed"] for group in groups)
    )


def build_parameter_tables(group_settings=None) -> bytes:
    return _build_parameter_tables(group_settings)


PARAMETER_TABLES = _build_parameter_tables(None)

OFF_SETUP_META_LOAD = OFF_RUNTIME
CPU_SETUP_META_LOAD = CPU_RUNTIME

SETUP_META_RUNTIME = bytes((
    0xA0, 0x01,                         # LDY #$01
    0xB1, 0x08,                         # LDA ($08),Y: enemy ID
    0x38, 0xE9, FIRST_ID, 0x4A, 0xAA,  # X=(ID-$84)/2: group A/B
    0xBD, CPU_PARAMETER_TABLE & 0xFF, CPU_PARAMETER_TABLE >> 8,
    0x85, 0x0E, 0xA8,                   # setup speed group
    0xB9, 0xD3, 0xD9, 0x60,
))

OFF_INIT_STATUS = OFF_SETUP_META_LOAD + len(SETUP_META_RUNTIME)
CPU_INIT_STATUS = CPU_SETUP_META_LOAD + len(SETUP_META_RUNTIME)

INIT_STATUS_RUNTIME = bytes((
    0x68,                               # discard saved stock init input
    0xA9, 0xC0, 0x85, 0x04,             # active, no gravity
    0xA5, 0x05, 0x29, 0x01, 0x0A, 0xEA, # relative even=behavior 0 (up), odd=2 (down)
    0x20, 0x1C, 0x9D,                   # stock init writer
    0xA5, 0x06, 0x20, 0x56, 0xB1,
    0xA0, 0x07, 0xA9, COOLDOWN_ARMED, 0x91, 0x00,
    0x60,
))


class _Asm:
    def __init__(self):
        self.data = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, int, str, str]] = []

    def label(self, name: str) -> None:
        self.labels[name] = len(self.data)

    def b(self, *values: int) -> None:
        self.data.extend(value & 0xFF for value in values)

    def jsr(self, addr: int) -> None:
        self.b(0x20, addr & 0xFF, addr >> 8)

    def jsr_label(self, label: str) -> None:
        self.fixups.append((len(self.data), 0x20, label, "abs"))
        self.b(0x20, 0x00, 0x00)

    def branch(self, opcode: int, label: str) -> None:
        self.fixups.append((len(self.data), opcode & 0xFF, label, "rel"))
        self.b(opcode, 0x00)

    def finish(self, cpu_base: int) -> bytes:
        for pos, opcode, label, mode in self.fixups:
            if label not in self.labels:
                raise ValueError(f"unknown label: {label}")
            target = cpu_base + self.labels[label]
            self.data[pos] = opcode
            if mode == "abs":
                self.data[pos + 1] = target & 0xFF
                self.data[pos + 2] = target >> 8
                continue
            rel = self.labels[label] - (pos + 2)
            if not -128 <= rel <= 127:
                raise ValueError(f"branch out of range: {label}")
            self.data[pos + 1] = rel & 0xFF
        return bytes(self.data)


def _build_ai_runtime() -> bytes:
    a = _Asm()
    a.b(0xA5, 0x2C, 0x48, 0xA5, 0x2D, 0x48, 0xA5, 0x2E, 0x48, 0xA5, 0x2F, 0x48)
    a.jsr(CPU_STOCK_NEUL_GHOST_AI)
    a.b(0x68, 0x85, 0x2F, 0x68, 0x85, 0x2E, 0x68, 0x85, 0x2D, 0x68, 0x85, 0x2C)
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0x0C)
    a.branch(0xD0, "done")
    a.b(0xA0, 0x07, 0xB1, 0x2C)
    a.branch(0x10, "done")
    a.b(0x29, 0x7F)
    a.branch(0xF0, "try_fire")
    a.b(0x38, 0xE9, 0x01, 0x09, COOLDOWN_ARMED, 0x91, 0x2C)
    a.branch(0xD0, "done")
    a.label("try_fire")
    a.b(0xA9, 0x00)
    a.jsr_label("fire_one")
    a.b(0xA9, 0x01)
    a.jsr_label("fire_one")
    a.b(0xA0, 0x01, 0xB1, 0x2E, 0x38, 0xE9, FIRST_ID, 0x4A, 0xAA)
    a.b(0xBD, (CPU_PARAMETER_TABLE + GROUP_COUNT) & 0xFF, (CPU_PARAMETER_TABLE + GROUP_COUNT) >> 8)
    a.b(0x09, COOLDOWN_ARMED, 0xA0, 0x07, 0x91, 0x2C)
    a.branch(0xD0, "done")
    a.label("done")
    a.b(0x60)
    a.label("fire_one")
    a.b(0x48)
    a.jsr(CPU_FIND_FREE_SUB_SLOT)
    a.branch(0x90, "no_slot")
    a.b(0xA0, 0x00, 0xA9, 0x80, 0x91, 0x04)
    a.b(0xA9, 0x01, 0x11, 0x2C, 0x91, 0x2C)
    a.b(0x8A, 0xA0, 0x06, 0x91, 0x2C)
    a.b(0x68, 0xAA)
    a.b(0xA5, 0x2C, 0x48, 0xA5, 0x2D, 0x48, 0xA5, 0x2E, 0x48, 0xA5, 0x2F, 0x48)
    a.jsr(CPU_BULLET_SPAWN)
    a.b(0x68, 0x85, 0x2F, 0x68, 0x85, 0x2E, 0x68, 0x85, 0x2D, 0x68, 0x85, 0x2C)
    a.b(0xA0, 0x01, 0xB1, 0x2E, 0x38, 0xE9, FIRST_ID, 0x4A, 0xAA)
    a.b(0xBD, (CPU_PARAMETER_TABLE + GROUP_COUNT * 2) & 0xFF, (CPU_PARAMETER_TABLE + GROUP_COUNT * 2) >> 8)
    a.branch(0xF0, "fire_done")
    a.b(0x48, 0xA0, 0x06, 0xB1, 0x2C)
    a.jsr(CPU_SUB_SLOT_PTR)
    a.b(0xA0, 0x07, 0x68, 0x91, 0x00)
    a.label("fire_done")
    a.b(0x60)
    a.label("no_slot")
    a.b(0x68, 0x60)
    return a.finish(CPU_AI_DISPATCH)


OFF_AI_DISPATCH = OFF_INIT_STATUS + len(INIT_STATUS_RUNTIME)
CPU_AI_DISPATCH = CPU_INIT_STATUS + len(INIT_STATUS_RUNTIME)
AI_DISPATCH_RUNTIME = _build_ai_runtime()


def build_runtime(group_settings=None) -> bytes:
    normalize_group_settings(group_settings)
    return SETUP_META_RUNTIME + INIT_STATUS_RUNTIME + AI_DISPATCH_RUNTIME


RUNTIME = build_runtime()
CPU_RUNTIME_END = CPU_RUNTIME + len(RUNTIME)
RESERVED_SPANS = (
    (OFF_RUNTIME, len(RUNTIME)),
    (OFF_PARAMETER_TABLE, len(PARAMETER_TABLES)),
)

assert len(SETUP_META_RUNTIME) == 19
assert len(INIT_STATUS_RUNTIME) == 26
assert len(AI_DISPATCH_RUNTIME) == 167
assert len(RUNTIME) == 212
assert len(PARAMETER_TABLES) == 6
assert OFF_RUNTIME + len(RUNTIME) == OFF_PARAMETER_TABLE
assert OFF_PARAMETER_TABLE + len(PARAMETER_TABLES) == 0x6FAB


def current_settings(rom_data) -> dict[str, object]:
    required_end = max(OFF_RUNTIME + len(RUNTIME), OFF_PARAMETER_TABLE + len(PARAMETER_TABLES))
    if rom_data is None or len(rom_data) < required_end:
        raise Neul84RuntimeError("ROM is too short for Neul A/B runtime")
    current_runtime = bytes(rom_data[OFF_RUNTIME:OFF_RUNTIME + len(RUNTIME)])
    current_parameters = bytes(rom_data[OFF_PARAMETER_TABLE:OFF_PARAMETER_TABLE + len(PARAMETER_TABLES)])
    if all(value in (0x00, 0xEA) for value in current_runtime + current_parameters):
        return {"groups": default_group_settings()}
    groups = []
    for index in range(GROUP_COUNT):
        groups.append({
            "body_speed": current_parameters[index],
            "fire_interval": current_parameters[GROUP_COUNT + index],
            "bullet_speed": current_parameters[GROUP_COUNT * 2 + index],
        })
    groups = normalize_group_settings(groups)
    if current_runtime != build_runtime(groups) or current_parameters != _build_parameter_tables(groups):
        raise Neul84RuntimeError("Neul A/B runtime has unexpected bytes")
    return {"groups": groups}


def validate_runtime_dependencies(rom_data) -> None:
    dependency_end = _ghostb0.OFF_BULLET_SPAWN + len(_ghostb0.BULLET_SPAWN_RUNTIME)
    if rom_data is None or len(rom_data) < dependency_end:
        raise Neul84RuntimeError("ROM is too short for Neul A/B runtime dependencies")
    current = bytes(rom_data[_ghostb0.OFF_BULLET_SPAWN:dependency_end])
    if current != _ghostb0.BULLET_SPAWN_RUNTIME and not all(
        value in (0x00, 0xEA) for value in current
    ):
        raise Neul84RuntimeError("Neul A/B Bullet spawn dependency has unexpected bytes")
    try:
        _ghostb0.validate_runtime_dependencies(rom_data)
    except _ghostb0.GhostB0RuntimeError as exc:
        raise Neul84RuntimeError(str(exc)) from exc


def apply_settings(rom_data, group_settings) -> list[str]:
    groups = normalize_group_settings(group_settings)
    current_settings(rom_data)
    validate_runtime_dependencies(rom_data)
    runtime = build_runtime(groups)
    parameters = _build_parameter_tables(groups)
    current_runtime = bytes(rom_data[OFF_RUNTIME:OFF_RUNTIME + len(runtime)])
    current_parameters = bytes(rom_data[OFF_PARAMETER_TABLE:OFF_PARAMETER_TABLE + len(parameters)])
    if current_runtime == runtime and current_parameters == parameters:
        return []
    rom_data[OFF_RUNTIME:OFF_RUNTIME + len(runtime)] = runtime
    rom_data[OFF_PARAMETER_TABLE:OFF_PARAMETER_TABLE + len(parameters)] = parameters
    return [
        f"Neul {GROUP_NAMES[index]} body=${group['body_speed']:02X} interval={group['fire_interval']} "
        f"bullet=${group['bullet_speed']:02X}"
        for index, group in enumerate(groups)
    ]


def levels_need_runtime(levels: list) -> bool:
    for level in levels or []:
        for enemy in getattr(level, "enemies", []) or []:
            if (
                getattr(enemy, "type", None) == ElementType.ENEMY
                and FIRST_ID <= int(enemy.element_no) <= LAST_ID
            ):
                return True
    return False

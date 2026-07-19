"""Parameterized Ghost A-F runtime for enemy IDs $B0-$BB."""
from __future__ import annotations

from .element import ElementType


FIRST_ID = 0xB0
LAST_ID = 0xBB
NEW_ENEMY_IDS = tuple(range(FIRST_ID, LAST_ID + 1))
DARK_FAIRY_ID = 0x9C
STOCK_FAIRY_PROPERTY = 0x0A

OFF_RUNTIME = 0x6268
CPU_RUNTIME = 0xE258
MAX_RUNTIME_SIZE = 218
OFF_PARAMETER_TABLE = 0x6D98
CPU_PARAMETER_TABLE = 0xED88

CPU_STOCK_GHOST_AI = 0xABF7
CPU_FIND_FREE_SUB_SLOT = 0xB2EA
CPU_STOCK_BULLET_SPAWN = 0xAE76
CPU_SUB_SLOT_PTR = 0xB156
CPU_BULLET_MARKER_WRITE = 0xE59B
CPU_BULLET_SPAWN = 0xE32A

COOLDOWN_ARMED = 0x80
GROUP_NAMES = ("A", "B", "C", "D", "E", "F")
GROUP_COUNT = len(GROUP_NAMES)

BODY_SPEED_NORMAL = 0x1A
BODY_SPEED_FAST = 0x1E
BODY_SPEED_VALUES = (BODY_SPEED_NORMAL, BODY_SPEED_FAST)

BULLET_SPEED_STOCK = 0x00
BULLET_SPEED_QUARTER = 0x88
BULLET_SPEED_HALF = 0x89
BULLET_SPEED_2X = 0x8A
BULLET_SPEED_3X = 0x8B
BULLET_SPEED_VALUES = (
    BULLET_SPEED_STOCK,
    BULLET_SPEED_QUARTER,
    BULLET_SPEED_HALF,
    BULLET_SPEED_2X,
    BULLET_SPEED_3X,
)

DIRECTION_BACKWARD = 0
DIRECTION_UP = 2
DIRECTION_DOWN = 3
DIRECTION_VALUES = (DIRECTION_BACKWARD, DIRECTION_UP, DIRECTION_DOWN)

MIN_FIRE_INTERVAL = 1
MAX_FIRE_INTERVAL = 0x7F
DEFAULT_BODY_SPEED = BODY_SPEED_NORMAL
DEFAULT_FIRE_INTERVAL = 0x40
DEFAULT_BULLET_SPEED = BULLET_SPEED_STOCK
DEFAULT_FIRE_DIRECTION = DIRECTION_DOWN

# Presets A-F each own one right/left pair.
def default_group_settings() -> tuple[dict[str, int], ...]:
    return (
        {
            "body_speed": BODY_SPEED_NORMAL,
            "fire_interval": 0x40,
            "bullet_speed": BULLET_SPEED_STOCK,
            "fire_direction": DIRECTION_DOWN,
        },
        {
            "body_speed": BODY_SPEED_FAST,
            "fire_interval": 0x30,
            "bullet_speed": BULLET_SPEED_HALF,
            "fire_direction": DIRECTION_DOWN,
        },
        {
            "body_speed": BODY_SPEED_NORMAL,
            "fire_interval": 0x40,
            "bullet_speed": BULLET_SPEED_STOCK,
            "fire_direction": DIRECTION_UP,
        },
        {
            "body_speed": BODY_SPEED_FAST,
            "fire_interval": 0x50,
            "bullet_speed": BULLET_SPEED_QUARTER,
            "fire_direction": DIRECTION_UP,
        },
        {
            "body_speed": BODY_SPEED_NORMAL,
            "fire_interval": 0x40,
            "bullet_speed": BULLET_SPEED_STOCK,
            "fire_direction": DIRECTION_BACKWARD,
        },
        {
            "body_speed": BODY_SPEED_FAST,
            "fire_interval": 0x28,
            "bullet_speed": BULLET_SPEED_STOCK,
            "fire_direction": DIRECTION_BACKWARD,
        },
    )


class GhostB0RuntimeError(ValueError):
    pass


def normalize_group_settings(settings) -> tuple[dict[str, int], ...]:
    if settings is None:
        return default_group_settings()
    if not isinstance(settings, (list, tuple)) or len(settings) != GROUP_COUNT:
        raise GhostB0RuntimeError("Ghost A-F settings must contain exactly six groups")
    normalized = []
    for index, raw in enumerate(settings):
        if not isinstance(raw, dict):
            raise GhostB0RuntimeError(f"Ghost group {GROUP_NAMES[index]} settings must be a mapping")
        try:
            body_speed = int(raw.get("body_speed", DEFAULT_BODY_SPEED))
            fire_interval = int(raw.get("fire_interval", DEFAULT_FIRE_INTERVAL))
            bullet_speed = int(raw.get("bullet_speed", DEFAULT_BULLET_SPEED))
            fire_direction = int(raw.get("fire_direction", DEFAULT_FIRE_DIRECTION))
        except (TypeError, ValueError) as exc:
            raise GhostB0RuntimeError(f"Ghost group {GROUP_NAMES[index]} has invalid settings") from exc
        if body_speed not in BODY_SPEED_VALUES:
            raise GhostB0RuntimeError(f"Ghost group {GROUP_NAMES[index]} has invalid body speed")
        if not MIN_FIRE_INTERVAL <= fire_interval <= MAX_FIRE_INTERVAL:
            raise GhostB0RuntimeError(f"Ghost group {GROUP_NAMES[index]} fire interval must be 1-127")
        if bullet_speed not in BULLET_SPEED_VALUES:
            raise GhostB0RuntimeError(f"Ghost group {GROUP_NAMES[index]} has invalid bullet speed")
        if fire_direction not in DIRECTION_VALUES:
            raise GhostB0RuntimeError(f"Ghost group {GROUP_NAMES[index]} has invalid fire direction")
        normalized.append({
            "body_speed": body_speed,
            "fire_interval": fire_interval,
            "bullet_speed": bullet_speed,
            "fire_direction": fire_direction,
        })
    return tuple(normalized)


def _build_parameter_tables(group_settings) -> bytes:
    groups = normalize_group_settings(group_settings)
    return (
        bytes(group["body_speed"] for group in groups)
        + bytes(COOLDOWN_ARMED | group["fire_interval"] for group in groups)
        + bytes(group["bullet_speed"] for group in groups)
        + bytes(group["fire_direction"] for group in groups)
    )


def build_parameter_tables(group_settings=None) -> bytes:
    return _build_parameter_tables(group_settings)


PARAMETER_TABLES = _build_parameter_tables(None)

OFF_SETUP_META_LOAD = OFF_RUNTIME
CPU_SETUP_META_LOAD = CPU_RUNTIME

SETUP_META_RUNTIME = bytes((
    0xA0, 0x01,                         # LDY #$01
    0xB1, 0x08,                         # LDA ($08),Y: reload the unmasked enemy ID
    0x29, 0x0E,                         # AND #$0E: right/left pair offset
    0x4A,                               # LSR A
    0xAA,                               # TAX
    0xBD, CPU_PARAMETER_TABLE & 0xFF, CPU_PARAMETER_TABLE >> 8,
    0x85, 0x0E,                         # STA $0E
    0xA8,                               # TAY
    0xB9, 0xD3, 0xD9,                   # LDA $D9D3,Y
    0x60,                               # RTS
))

OFF_INIT_STATUS = OFF_SETUP_META_LOAD + len(SETUP_META_RUNTIME)
CPU_INIT_STATUS = CPU_SETUP_META_LOAD + len(SETUP_META_RUNTIME)

INIT_STATUS_RUNTIME = bytes.fromhex(
    "68"            # PLA: discard saved stock init input
    "a9 c0"         # LDA #$C0: active, no gravity like stock Ghost
    "85 04"         # STA $04
    "a5 05"         # LDA $05: enemy ID
    "29 01"         # AND #$01: select right/left member
    "0a"            # ASL A: stock Ghost behavior 0=right, 2=left
    "20 1c 9d"      # JSR $9D1C stock init writer
    "a5 06"         # LDA $06: current main-slot index
    "20 56 b1"      # JSR $B156: sub-slot pointer in $00/$01
    "a0 07"         # LDY #$07
    "a9 80"         # LDA #$80: arm cooldown for the first shot
    "91 00"         # STA ($00),Y
    "60"            # RTS
)


class _Asm:
    def __init__(self):
        self.data = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, int, str]] = []

    def label(self, name: str) -> None:
        self.labels[name] = len(self.data)

    def b(self, *values: int) -> None:
        self.data.extend(v & 0xFF for v in values)

    def jsr(self, addr: int) -> None:
        self.b(0x20, addr & 0xFF, addr >> 8)

    def branch(self, opcode: int, label: str) -> None:
        self.fixups.append((len(self.data), opcode & 0xFF, label))
        self.b(opcode, 0x00)

    def finish(self) -> bytes:
        for pos, opcode, label in self.fixups:
            if label not in self.labels:
                raise ValueError(f"unknown label: {label}")
            rel = self.labels[label] - (pos + 2)
            if not -128 <= rel <= 127:
                raise ValueError(f"branch out of range: {label}")
            self.data[pos] = opcode
            self.data[pos + 1] = rel & 0xFF
        return bytes(self.data)


def _build_ai_runtime() -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E)         # parent main[1] enemy ID
    a.b(0x29, 0x0E, 0x4A, 0xAA)         # X=0..5 preset A..F
    a.b(0xBD, (CPU_PARAMETER_TABLE + GROUP_COUNT) & 0xFF, (CPU_PARAMETER_TABLE + GROUP_COUNT) >> 8, 0x48)
    a.b(0xBD, (CPU_PARAMETER_TABLE + GROUP_COUNT * 2) & 0xFF, (CPU_PARAMETER_TABLE + GROUP_COUNT * 2) >> 8, 0x48)
    a.b(0xBD, (CPU_PARAMETER_TABLE + GROUP_COUNT * 3) & 0xFF, (CPU_PARAMETER_TABLE + GROUP_COUNT * 3) >> 8, 0x48)
    a.b(0xA5, 0x2C, 0x48, 0xA5, 0x2D, 0x48, 0xA5, 0x2E, 0x48, 0xA5, 0x2F, 0x48)
    a.jsr(CPU_STOCK_GHOST_AI)
    a.b(0x68, 0x85, 0x2F, 0x68, 0x85, 0x2E, 0x68, 0x85, 0x2D, 0x68, 0x85, 0x2C)
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0x0C)
    a.branch(0xD0, "rts")
    a.b(0xA0, 0x07, 0xB1, 0x2C)
    a.branch(0x10, "rts")
    a.b(0x29, 0x7F)
    a.branch(0xF0, "try_fire")
    a.b(0x38, 0xE9, 0x01, 0x09, COOLDOWN_ARMED, 0x91, 0x2C)
    a.branch(0xD0, "rts")
    a.label("try_fire")
    a.jsr(CPU_FIND_FREE_SUB_SLOT)
    a.branch(0x90, "no_slot")
    a.b(0xA0, 0x00, 0xA9, 0x80, 0x91, 0x04)
    a.b(0xA9, 0x01, 0x11, 0x2C, 0x91, 0x2C)
    a.b(0x8A, 0xA0, 0x06, 0x91, 0x2C)
    a.b(0x68, 0xAA)
    a.branch(0xD0, "fire_direction_ready")
    a.b(0xA0, 0x08, 0xB1, 0x2E, 0xC9, 0x40, 0xA2, 0x01)
    a.branch(0x90, "fire_direction_ready")
    a.b(0xCA)                             # backward from current post-AI X velocity
    a.label("fire_direction_ready")
    a.jsr(CPU_BULLET_SPAWN)
    a.b(0x68)
    a.branch(0xF0, "skip_marker")
    a.b(0x48, 0xA0, 0x06, 0xB1, 0x2C)
    a.jsr(CPU_SUB_SLOT_PTR)
    a.b(0xA0, 0x07, 0x68, 0x91, 0x00)
    a.label("skip_marker")
    a.b(0x68, 0xA0, 0x07, 0x91, 0x2C, 0x60)
    a.label("no_slot")
    a.b(0x68, 0x68, 0x68, 0x60)
    a.label("rts")
    a.b(0x68, 0x68, 0x68)
    a.b(0x60)
    return a.finish()


OFF_AI_DISPATCH = OFF_INIT_STATUS + len(INIT_STATUS_RUNTIME)
CPU_AI_DISPATCH = CPU_INIT_STATUS + len(INIT_STATUS_RUNTIME)
AI_RUNTIME = _build_ai_runtime()

OFF_SHARED_PROPERTY_META_LOAD = OFF_AI_DISPATCH + len(AI_RUNTIME)
CPU_SHARED_PROPERTY_META_LOAD = CPU_AI_DISPATCH + len(AI_RUNTIME)

SHARED_PROPERTY_META_RUNTIME = bytes((
    0xA5, 0x05,                         # LDA $05: spawn enemy ID
    0xC9, DARK_FAIRY_ID,                # CMP #$9C: Dark Fairy
    0xF0, 0x0E,                         # BEQ Dark Fairy stock-Fairy property
    0x38,                               # SEC
    0xE9, FIRST_ID,                     # SBC #$B0
    0xC9, LAST_ID - FIRST_ID + 1,       # CMP #$0C
    0xB0, 0x03,                         # BCS stock property table
    0xA9, 0x4A,                         # LDA #$4A: same property input as $86
    0x60,                               # RTS
    0xB9, 0x0E, 0xA3,                   # LDA $A30E,Y
    0x60,                               # RTS
    0xA9, STOCK_FAIRY_PROPERTY,         # LDA #$0A: stock Fairy property input
    0x60,                               # RTS
))

OFF_BULLET_SPAWN = OFF_SHARED_PROPERTY_META_LOAD + len(SHARED_PROPERTY_META_RUNTIME)
CPU_BULLET_SPAWN = CPU_SHARED_PROPERTY_META_LOAD + len(SHARED_PROPERTY_META_RUNTIME)

BULLET_SPAWN_RUNTIME = bytes((
    0x20, CPU_STOCK_BULLET_SPAWN & 0xFF, CPU_STOCK_BULLET_SPAWN >> 8,
    0xA9, 0x00,                         # LDA #$00: clear recycled marker
    0x4C, CPU_BULLET_MARKER_WRITE & 0xFF, CPU_BULLET_MARKER_WRITE >> 8,
))

def build_runtime(group_settings=None) -> bytes:
    normalize_group_settings(group_settings)
    return (
        SETUP_META_RUNTIME
        + INIT_STATUS_RUNTIME
        + AI_RUNTIME
        + SHARED_PROPERTY_META_RUNTIME
        + BULLET_SPAWN_RUNTIME
    )


RUNTIME = build_runtime()
CPU_RUNTIME_END = CPU_RUNTIME + len(RUNTIME)
RESERVED_SPANS = (
    (OFF_RUNTIME, len(RUNTIME)),
    (OFF_PARAMETER_TABLE, len(PARAMETER_TABLES)),
)

assert len(PARAMETER_TABLES) == 24
assert len(SETUP_META_RUNTIME) == 18
assert len(INIT_STATUS_RUNTIME) == 25
assert len(AI_RUNTIME) == 144
assert len(SHARED_PROPERTY_META_RUNTIME) == 23
assert len(BULLET_SPAWN_RUNTIME) == 8
assert CPU_BULLET_SPAWN == 0xE32A
assert len(RUNTIME) == 218
assert len(RUNTIME) <= MAX_RUNTIME_SIZE
assert CPU_RUNTIME + len(RUNTIME) == CPU_RUNTIME_END


def current_settings(rom_data) -> dict[str, object]:
    required_end = max(OFF_RUNTIME + len(RUNTIME), OFF_PARAMETER_TABLE + len(PARAMETER_TABLES))
    if rom_data is None or len(rom_data) < required_end:
        raise GhostB0RuntimeError("ROM is too short for Ghost A-F runtime")
    current_runtime = bytes(rom_data[OFF_RUNTIME:OFF_RUNTIME + len(RUNTIME)])
    current_parameters = bytes(rom_data[OFF_PARAMETER_TABLE:OFF_PARAMETER_TABLE + len(PARAMETER_TABLES)])
    if all(value in (0x00, 0xEA) for value in current_runtime + current_parameters):
        return {"groups": default_group_settings()}
    groups = []
    for index in range(GROUP_COUNT):
        groups.append({
            "body_speed": current_parameters[index],
            "fire_interval": current_parameters[GROUP_COUNT + index] & 0x7F,
            "bullet_speed": current_parameters[GROUP_COUNT * 2 + index],
            "fire_direction": current_parameters[GROUP_COUNT * 3 + index],
        })
    groups = normalize_group_settings(groups)
    if current_runtime != build_runtime(groups) or current_parameters != _build_parameter_tables(groups):
        raise GhostB0RuntimeError("Ghost A-F runtime has unexpected bytes")
    return {"groups": groups}


def validate_runtime_dependencies(rom_data) -> None:
    from . import panel_monster_stage_variant as panel
    end = panel.OFF_FINAL_STATIC_MARKER_HELPER + len(panel.FINAL_STATIC_MARKER_HELPER)
    if rom_data is None or len(rom_data) < end:
        raise GhostB0RuntimeError("ROM is too short for Ghost A-F runtime dependencies")
    current = bytes(rom_data[panel.OFF_FINAL_STATIC_MARKER_HELPER:end])
    if current != panel.FINAL_STATIC_MARKER_HELPER and not all(
        value in (0x00, 0xEA) for value in current
    ):
        raise GhostB0RuntimeError("Ghost A-F Bullet marker helper has unexpected bytes")


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
        f"Ghost {GROUP_NAMES[index]} body=${group['body_speed']:02X} interval={group['fire_interval']} "
        f"bullet=${group['bullet_speed']:02X} direction={group['fire_direction']}"
        for index, group in enumerate(groups)
    ]


def levels_need_runtime(levels: list) -> bool:
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if (
                getattr(enemy, "type", None) == ElementType.ENEMY
                and FIRST_ID <= int(enemy.element_no) <= LAST_ID
            ):
                return True
    return False

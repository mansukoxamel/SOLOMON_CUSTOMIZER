"""Panel Monster stage-variant prototype patch.

This module is intentionally separate from ``panel_monster_variant.py``.
The existing module owns the production 2-way/3-way borrowed-ID Panel Monster
feature.  This module is for the newer stage-parameterized A/B/C families:

  C: $31/$33/$35/$37
  A: $41/$43/$45/$47
  B: $49/$4B/$4D/$4F

Current scope:
  - hook the state0 firing interval compare at $A575/$A579;
  - keep the state1 pre-shot mouth delay at the stock $10;
  - read the current room's A/B/C speed+interval bytes from the $0740-$074F
    cache.

This is not the final PRG1 PanelVariantStageTable implementation yet.  Keep it
out of UI wiring until the RAM interval behavior is proven clean in ROM tests.
Rhythm was removed from the design; there is intentionally no 1x speed preset
because stock Panel Monster already covers normal-speed shots.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import panel_monster_variant


class PanelMonsterStageVariantError(ValueError):
    pass


def _word(cpu: int) -> bytes:
    return bytes((cpu & 0xFF, (cpu >> 8) & 0xFF))


def _cpu(file_off: int) -> int:
    return 0x8000 + (int(file_off) - 0x10)


class _Asm:
    def __init__(self) -> None:
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

    def jsr(self, cpu: int) -> None:
        self.b(0x20, cpu & 0xFF, cpu >> 8)

    def jmp(self, cpu: int) -> None:
        self.b(0x4C, cpu & 0xFF, cpu >> 8)

    def finish(self) -> bytes:
        for off, label in self.fixups:
            target = self.labels[label]
            rel = target - (off + 1)
            if not -128 <= rel <= 127:
                raise PanelMonsterStageVariantError(f"branch to {label} is out of range")
            self.code[off] = rel & 0xFF
        return bytes(self.code)


PANEL_STAGE_VARIANT_IDS = frozenset((
    0x31, 0x33, 0x35, 0x37,
    0x41, 0x43, 0x45, 0x47,
    0x49, 0x4B, 0x4D, 0x4F,
))

GROUP_C_IDS = frozenset((0x31, 0x33, 0x35, 0x37))
GROUP_A_IDS = frozenset((0x41, 0x43, 0x45, 0x47))
GROUP_B_IDS = frozenset((0x49, 0x4B, 0x4D, 0x4F))

RAM_PV_A_SPEED = 0x0740
RAM_PV_A_INTERVAL = 0x0741
RAM_PV_B_SPEED = 0x0742
RAM_PV_B_INTERVAL = 0x0743
RAM_PV_C_SPEED = 0x0744
RAM_PV_C_INTERVAL = 0x0745

DEFAULT_C_INTERVAL = 0x90
DEFAULT_A_INTERVAL = 0x80
DEFAULT_B_INTERVAL = 0x70
DEFAULT_A_SPEED_PRESET = 0
DEFAULT_B_SPEED_PRESET = 1
DEFAULT_C_SPEED_PRESET = 2

SPEED_PRESET_QUARTER = 0
SPEED_PRESET_HALF = 1
SPEED_PRESET_FAST_2X = 2
SPEED_PRESET_FAST_3X = 3
SPEED_PRESET_NAMES = {
    SPEED_PRESET_QUARTER: "1/4",
    SPEED_PRESET_HALF: "1/2",
    SPEED_PRESET_FAST_2X: "2x",
    SPEED_PRESET_FAST_3X: "3x",
}

# Slow presets are table-only.  Fast presets keep the original Panel Bullet
# table speed and are handled by extra conversion steps in the Bullet path.
SPEED_PRESET_TABLE_VALUES = {
    SPEED_PRESET_QUARTER: {
        "right_down": 0x0C,
        "left_up": 0x74,
        "extra_steps": 0,
    },
    SPEED_PRESET_HALF: {
        "right_down": 0x18,
        "left_up": 0x68,
        "extra_steps": 0,
    },
    SPEED_PRESET_FAST_2X: {
        "right_down": 0x30,
        "left_up": 0x50,
        "extra_steps": 1,
    },
    SPEED_PRESET_FAST_3X: {
        "right_down": 0x30,
        "left_up": 0x50,
        "extra_steps": 2,
    },
}

ROOM_COUNT = 64
ENTRY_SIZE = 16
HEADER_SIZE = 16
TABLE_OFFSET = 0x8A70
TABLE_LENGTH = HEADER_SIZE + ROOM_COUNT * ENTRY_SIZE
TABLE_END = TABLE_OFFSET + TABLE_LENGTH
MAGIC = b"PANELVAR"
FORMAT = 1
ENABLE_STAGE_TABLE_INTERVAL_PROTOTYPE = False

CPU_PRG1_RUNTIME_LOADER = 0x8A00
OFF_PRG1_RUNTIME_LOADER = 0x8A10
OFF_M66_LOADER_TAIL = 0x80C4
ORIG_M66_LOADER_TAIL = bytes.fromhex("60 00 00")
HOOK_M66_LOADER_TAIL = bytes((
    0x4C,
    CPU_PRG1_RUNTIME_LOADER & 0xFF,
    CPU_PRG1_RUNTIME_LOADER >> 8,
))

# These offsets are the current v7/v4 test-ROM cave locations.  They are
# deliberately named as prototype locations, not final production reservations.
OFF_AI_WRAPPER_C_PROTO = 0x3C6B
OFF_AI_WRAPPER_AB_PROTO = 0x3D0F
OFF_STATE0_INTERVAL_HOOK = 0x2585  # CPU $A575
OFF_STATE0_INTERVAL_CMP = 0x2589   # CPU $A579
OFF_STATE0_INTERVAL_HELPER = 0x4098  # CPU $C088
OFF_STATE1_MOUTH_GATE = 0x3D52  # CPU $BD42
STATE1_MOUTH_GATE_SIZE = 0x3F
OFF_AI_RANGE_30_33 = 0xA33C - 0x8000 + 0x10
OFF_AI_RANGE_34_37 = 0xA33E - 0x8000 + 0x10
OFF_AI_RANGE_40_43 = 0xA344 - 0x8000 + 0x10
OFF_AI_RANGE_44_47 = 0xA346 - 0x8000 + 0x10
OFF_AI_RANGE_48_4B = 0xA348 - 0x8000 + 0x10
OFF_AI_RANGE_4C_4F = 0xA34A - 0x8000 + 0x10

OFF_FINAL_BULLET_SPEED_APPLY = 0x4098  # CPU $C088, 58B free gap before animation selector
CPU_FINAL_BULLET_SPEED_APPLY = 0xC088
OFF_FINAL_STAGE_DISPATCH_TAIL = 0x3D01  # CPU $BCF1, 14B gap after fire dispatch
CPU_FINAL_STAGE_DISPATCH_TAIL = _cpu(OFF_FINAL_STAGE_DISPATCH_TAIL)
OFF_FINAL_STATE0_INTERVAL_HELPER = 0x3E72  # CPU $BE62, 18B former Spark property gap
CPU_FINAL_STATE0_INTERVAL_HELPER = _cpu(OFF_FINAL_STATE0_INTERVAL_HELPER)
OFF_FINAL_GROUP_RAM_OFFSET_HELPER = 0x3EAF  # CPU $BE9F, 23B gap
CPU_FINAL_GROUP_RAM_OFFSET_HELPER = _cpu(OFF_FINAL_GROUP_RAM_OFFSET_HELPER)
OFF_FINAL_SPEED_SELECT_HELPER = 0x3ECD  # CPU $BEBD, 10B gap
CPU_FINAL_SPEED_SELECT_HELPER = _cpu(OFF_FINAL_SPEED_SELECT_HELPER)
OFF_FINAL_FIRE_MARKER_TABLE = 0x4143  # CPU $C133, 19B reclaimed runtime tail
CPU_FINAL_FIRE_MARKER_TABLE = _cpu(OFF_FINAL_FIRE_MARKER_TABLE)
OFF_FINAL_STATIC_MARKER_HELPER = 0x3F50  # CPU $BF40, 16B gap
CPU_FINAL_STATIC_MARKER_HELPER = _cpu(OFF_FINAL_STATIC_MARKER_HELPER)
OFF_FINAL_DYNAMIC_SPEED_MARKER_HELPER = 0x3FCA  # CPU $BFBA, 30B post bullet-hook gap
CPU_FINAL_DYNAMIC_SPEED_MARKER_HELPER = _cpu(OFF_FINAL_DYNAMIC_SPEED_MARKER_HELPER)
OFF_FINAL_AI_WRAPPER_CANDIDATE = panel_monster_variant.OFF_AI_DEMON_WRAPPER  # CPU $C146, 57B existing Panel AI wrapper slot
CPU_FINAL_AI_WRAPPER_CANDIDATE = _cpu(OFF_FINAL_AI_WRAPPER_CANDIDATE)
OFF_FINAL_BORROWED_SPEED_NEUTRALIZE = 0x5BC5  # CPU $DBB5
OFF_FINAL_BORROWED_SPEED_NEUTRALIZE_END = panel_monster_variant.OFF_PROPERTY_HOOK

ORIG_STATE0_INTERVAL_HOOK = bytes.fromhex("a0 02 b1 2c c9 c0")
V7_STATE0_INTERVAL_HOOK = bytes.fromhex("4c 80 c1 2c c9 c0")
V8_STATE0_INTERVAL_HOOK = bytes.fromhex("20 88 c0 ea c5 0f")
HOOK_STATE0_INTERVAL = bytes.fromhex("20 88 c0 ea ea ea")

V7_AI_WRAPPER_C_HEAD = bytes.fromhex(
    "a9 00 a0 05 91 2e a0 06 91 2e a0 08 91 2e a0 09 "
    "91 2e a0 01 b1 2e 4a 29 01 09 02 48 a0 03 b1 2e "
    "29 fc 91 2e 68 11 2e 91 2e 4c 4c a5"
)

FIXED_AI_WRAPPER_C = bytes.fromhex(
    "a9 00 a0 05 91 2e a0 06 91 2e a0 08 91 2e a0 09 "
    "91 2e a0 01 b1 2e 29 06 4a a8 b9 9d bc 48 a0 03 "
    "b1 2e 29 fc 91 2e 68 11 2e 91 2e 4c 4c a5 "
    "02 03 00 01"
)

V7_AI_WRAPPER_AB_HEAD = bytes.fromhex(
    "a9 00 a0 05 91 2e a0 06 91 2e a0 08 91 2e a0 09 "
    "91 2e a0 01 b1 2e 4a 29 01 48 a0 03 b1 2e 29 fc "
    "91 2e 68 11 2e 91 2e 4c 4c a5 2e c9 6e f0 07 "
    "c9 6f f0 06 4c 4a a6 4c 2d a9 4c 2d a9"
)

DEFAULT_ENTRY = bytes((
    DEFAULT_A_SPEED_PRESET,
    DEFAULT_A_INTERVAL,
    DEFAULT_B_SPEED_PRESET,
    DEFAULT_B_INTERVAL,
    DEFAULT_C_SPEED_PRESET,
    DEFAULT_C_INTERVAL,
    0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00,
))

def _build_state0_interval_helper(cpu_base: int) -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E, 0x29, 0xF8)
    a.b(0x4A, 0x4A, 0x4A, 0x38, 0xE9, 0x06, 0xAA)
    a.b(0xBD, 0xFF, 0xFF, 0xAA)
    a.b(0xA0, 0x02, 0xB1, 0x2C, 0xDD, 0x41, 0x07, 0x60)
    a.label("ram_offset_table")
    a.b(0x04, 0x00, 0x00, 0x02)
    blob = bytearray(a.finish())
    table_cpu = (int(cpu_base) + a.labels["ram_offset_table"]) & 0xFFFF
    for i in range(len(blob) - 2):
        if blob[i] == 0xBD and blob[i + 1:i + 3] == bytes((0xFF, 0xFF)):
            blob[i + 1:i + 3] = bytes((table_cpu & 0xFF, table_cpu >> 8))
            return bytes(blob)
    raise PanelMonsterStageVariantError("state0 interval helper placeholder mismatch")


STATE0_INTERVAL_HELPER = _build_state0_interval_helper(0xC088)
STATE1_MOUTH_GATE = (
    bytes.fromhex("a0 01 b1 2c c9 10 90 03 4c 9a bd 60")
    + bytes([0xEA] * (STATE1_MOUTH_GATE_SIZE - 12))
)


def _build_group_ram_offset_helper(cpu_base: int) -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E, 0x29, 0xF8)
    a.b(0x4A, 0x4A, 0x4A, 0x38, 0xE9, 0x06, 0xAA)
    a.b(0xBD, 0xFF, 0xFF, 0xAA, 0x60)
    a.label("ram_offset_table")
    a.b(0x04, 0x00, 0x00, 0x02)
    blob = bytearray(a.finish())
    table_cpu = (int(cpu_base) + a.labels["ram_offset_table"]) & 0xFFFF
    for i in range(len(blob) - 2):
        if blob[i] == 0xBD and blob[i + 1:i + 3] == bytes((0xFF, 0xFF)):
            blob[i + 1:i + 3] = bytes((table_cpu & 0xFF, table_cpu >> 8))
            return bytes(blob)
    raise PanelMonsterStageVariantError("group RAM offset helper placeholder mismatch")


def _build_state0_interval_helper_shared(group_offset_cpu: int) -> bytes:
    a = _Asm()
    a.jsr(group_offset_cpu)
    a.b(0xA0, 0x02, 0xB1, 0x2C, 0xDD, 0x41, 0x07, 0x60)
    return a.finish()


def _build_state1_fire_marker(speed_select_cpu: int) -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2C, 0xC9, 0x10)
    a.branch(0x90, "rts")
    a.jsr(speed_select_cpu)             # A = speed preset 0..3
    a.b(0x48)                           # PHA
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0x03, 0xAA)
    a.jsr(0xAE76)                       # materialize Bullet
    a.b(0xA0, 0x06, 0xB1, 0x2C)
    a.jsr(0xB156)                       # child sub-slot pointer -> $00/$01
    a.b(0x68, 0x09, 0x88, 0xA0, 0x07, 0x91, 0x00)
    a.b(0xA0, 0x03, 0x98, 0x31, 0x2E, 0x91, 0x2E)
    a.b(0x88, 0xA9, 0x00, 0x91, 0x2C, 0x88, 0x91, 0x2C)
    a.label("rts")
    a.b(0x60)
    return a.finish()


def _build_speed_preset_select_helper(group_offset_cpu: int) -> bytes:
    a = _Asm()
    a.jsr(group_offset_cpu)
    a.b(0xBD, 0x40, 0x07, 0x60)
    return a.finish()


SPEED_PRESET_RUNTIME_TABLE = bytes((
    SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_QUARTER]["right_down"],
    SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_QUARTER]["left_up"],
    SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_HALF]["right_down"],
    SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_HALF]["left_up"],
    SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_FAST_2X]["right_down"],
    SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_FAST_2X]["left_up"],
    SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_FAST_3X]["right_down"],
    SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_FAST_3X]["left_up"],
))


def _build_bullet_speed_apply(speed_table_cpu: int) -> bytes:
    a = _Asm()
    a.b(0xA0, 0x07, 0xB1, 0x2C, 0xC9, 0x88)
    a.branch(0x90, "rts")
    a.b(0xC9, 0x8C)
    a.branch(0xB0, "rts")
    a.b(0x38, 0xE9, 0x88, 0x0A, 0xAA)   # A=preset*2; X=velocity table offset
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0x03)
    a.b(0xA0, 0x05, 0xC9, 0x02)
    a.branch(0xB0, "vertical")
    a.b(0xA0, 0x08, 0x4A)
    a.branch(0x90, "store")
    a.branch(0xB0, "left_up")
    a.label("vertical")
    a.branch(0xF0, "left_up_y")
    a.branch(0xD0, "store")
    a.label("left_up")
    a.label("left_up_y")
    a.b(0xE8)
    a.label("store")
    a.b(0xBD, 0xFF, 0xFF, 0x91, 0x2E)
    a.label("rts")
    a.b(0x60)
    blob = bytearray(a.finish())
    index = 0
    for i in range(len(blob) - 2):
        if blob[i] == 0xBD and blob[i + 1:i + 3] == bytes((0xFF, 0xFF)):
            blob[i + 1:i + 3] = bytes((speed_table_cpu & 0xFF, speed_table_cpu >> 8))
            index += 1
    if index != 1:
        raise PanelMonsterStageVariantError("bullet speed apply placeholder mismatch")
    return bytes(blob)


def _build_bullet_speed_hook(speed_apply_cpu: int) -> bytes:
    a = _Asm()
    a.jsr(0xB201)
    a.b(0x48, 0xC9, 0x02)
    a.branch(0xD0, "done")
    a.b(0x8A, 0x48)
    a.jsr(speed_apply_cpu)
    a.b(0x68, 0xAA)
    a.label("done")
    a.b(0x68, 0x60)
    return a.finish()


def _build_merged_panel_bullet_hook(speed_apply_cpu: int) -> bytes:
    a = _Asm()
    a.jsr(0xB201)
    a.b(0x48, 0xC9, 0x02)
    a.branch(0xD0, "done")
    a.b(0x8A, 0x48)
    a.jsr(speed_apply_cpu)
    a.b(0xA0, 0x07, 0xB1, 0x2C)
    a.branch(0x10, "done_x")
    a.b(0x29, 0x7F, 0xAA)
    a.branch(0xF0, "done_x")
    a.b(0xE0, 0x05)
    a.branch(0xB0, "done_x")
    a.b(0xE0, 0x03)
    a.branch(0x90, "axis")
    a.b(0xA0, 0x01, 0xB1, 0x2C, 0x29, 0x01)
    a.branch(0xD0, "done_x")
    a.label("axis")
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0x02)
    a.branch(0xF0, "y_axis")
    a.b(0xA0, 0x0A)
    a.branch(0xD0, "axis_done")
    a.label("y_axis")
    a.b(0xA0, 0x07)
    a.label("axis_done")
    a.b(0x8A, 0x29, 0x01)
    a.branch(0xD0, "plus")
    a.b(0xB1, 0x2E, 0x38, 0xE9, 0x01, 0x91, 0x2E)
    a.b(0x68, 0xAA, 0x68, 0x60)
    a.label("plus")
    a.b(0xB1, 0x2E, 0x18, 0x69, 0x01, 0x91, 0x2E)
    a.label("done_x")
    a.b(0x68, 0xAA)
    a.label("done")
    a.b(0x68, 0x60)
    return a.finish()


def _build_final_state0_interval_helper() -> bytes:
    return _build_state0_interval_helper_shared(CPU_FINAL_GROUP_RAM_OFFSET_HELPER)


def _build_final_group_ram_offset_helper() -> bytes:
    return _build_group_ram_offset_helper(CPU_FINAL_GROUP_RAM_OFFSET_HELPER)


def _build_final_speed_select_helper() -> bytes:
    return _build_speed_preset_select_helper(CPU_FINAL_GROUP_RAM_OFFSET_HELPER)


def _build_static_marker_helper() -> bytes:
    return bytes.fromhex("48 a5 02 20 56 b1 a0 07 68 91 00 60")


def _build_dynamic_speed_marker_helper(speed_select_cpu: int) -> bytes:
    a = _Asm()
    a.b(0x8A, 0x48)
    a.jsr(speed_select_cpu)
    a.b(0x09, 0x88, 0x48)
    a.b(0xA5, 0x02, 0x20, 0x56, 0xB1, 0xA0, 0x07)
    a.b(0x68, 0x91, 0x00, 0x68, 0xAA, 0x60)
    return a.finish()


def _build_final_fire_marker_table() -> bytes:
    return bytes((0x83, 0x84, 0xFF, 0x81, 0x80, 0x82, 0xFF, 0xFE, 0xFF, 0xFF, 0xFF))


def _build_final_fire_common(
    fire_delay: int,
    marker_table_cpu: int,
    static_marker_cpu: int,
    dynamic_marker_cpu: int,
) -> bytes:
    base_cpu = panel_monster_variant.CPU_FIRE_3WAY
    a = _Asm()
    a.label("stage_entry")
    a.b(0xA2, 0x07)
    a.branch(0xD0, "start")
    a.label("normal_entry")
    a.b(0xA2, 0x09)
    a.branch(0xD0, "start")
    a.label("three_entry")
    a.b(0xA2, 0x03)
    a.branch(0xD0, "start")
    a.label("two_entry")
    a.b(0xA2, 0x00)
    a.label("start")
    a.b(0xA0, 0x01, 0xB1, 0x2C, 0xC9, fire_delay & 0xFF)
    a.branch(0x90, "rts")
    a.label("loop")
    a.b(0x8A, 0x48)
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0x03, 0xAA)
    a.b(0x20, 0x76, 0xAE)
    a.b(0x68, 0xAA)
    a.b(0xBD, marker_table_cpu & 0xFF, marker_table_cpu >> 8, 0xC9, 0xFF)
    a.branch(0xF0, "mark_done")
    a.b(0xC9, 0xFE)
    a.branch(0xD0, "static_marker")
    a.jsr(dynamic_marker_cpu)
    a.branch(0xD0, "mark_done")
    a.label("static_marker")
    a.b(0x86, 0x0F)
    a.jsr(static_marker_cpu)
    a.b(0xA6, 0x0F)
    a.label("mark_done")
    a.b(0xE8)
    a.b(0xBD, marker_table_cpu & 0xFF, marker_table_cpu >> 8, 0xC9, 0xFF)
    a.branch(0xF0, "exit")
    a.b(0x8A, 0x48)
    a.b(0x20, 0xEA, 0xB2)
    a.branch(0x90, "alloc_fail")
    a.b(0x8A, 0xA0, 0x06, 0x91, 0x2C)
    a.b(0xA0, 0x00, 0xA9, 0x80, 0x91, 0x04)
    a.b(0x68, 0xAA)
    a.jmp(base_cpu)
    a.label("alloc_fail")
    a.b(0x68, 0xAA)
    a.jmp(base_cpu + 1)
    a.label("rts")
    a.b(0x60)
    a.label("exit")
    a.b(0xA0, 0x03, 0x98, 0x31, 0x2E, 0x91, 0x2E)
    a.b(0x88, 0xA9, 0x00, 0x91, 0x2C, 0x88, 0x91, 0x2C, 0x60)
    blob = bytearray(a.finish())
    loop_cpu = base_cpu + a.labels["loop"]
    exit_cpu = base_cpu + a.labels["exit"]
    for i in range(len(blob) - 2):
        if blob[i] == 0x4C and blob[i + 1:i + 3] == _word(base_cpu):
            blob[i + 1:i + 3] = _word(loop_cpu)
        elif blob[i] == 0x4C and blob[i + 1:i + 3] == _word(base_cpu + 1):
            blob[i + 1:i + 3] = _word(exit_cpu)
    return bytes(blob)


def _build_final_stage_dispatch_tail(stage_entry_cpu: int, normal_entry_cpu: int) -> bytes:
    a = _Asm()
    a.b(0xC9, 0x30)
    a.branch(0x90, "normal")
    a.b(0xC9, 0x50)
    a.branch(0x90, "stage")
    a.label("normal")
    a.jmp(normal_entry_cpu)
    a.label("stage")
    a.jmp(stage_entry_cpu)
    return a.finish()


def _build_final_fire_dispatch(stage_tail_cpu: int, two_entry_cpu: int, three_entry_cpu: int) -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E, 0x29, 0xFE)
    a.b(0xC9, 0x52)
    a.branch(0xF0, "two")
    a.b(0xC9, 0x56)
    a.branch(0xF0, "two")
    a.b(0xC9, 0x5A)
    a.branch(0xF0, "three")
    a.b(0xC9, 0x66)
    a.branch(0xF0, "three")
    a.jmp(stage_tail_cpu)
    a.label("two")
    a.jmp(two_entry_cpu)
    a.label("three")
    a.jmp(three_entry_cpu)
    return a.finish()


def _build_final_ai_wrapper_candidate(cpu_base: int) -> tuple[bytes, dict[str, int]]:
    a = _Asm()
    a.label("entry")
    a.b(0xA0, 0x01, 0xB1, 0x2E, 0x4A, 0x29, 0x03)
    a.label("set")
    a.b(0x48)
    a.b(0xA9, 0x00, 0xA0, 0x09, 0x91, 0x2E, 0x88, 0x91, 0x2E)
    a.b(0xA0, 0x06, 0x91, 0x2E, 0x88, 0x91, 0x2E)
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0xFC, 0x91, 0x2E)
    a.b(0x68, 0x11, 0x2E, 0x91, 0x2E)
    a.jmp(0xA54C)
    blob = a.finish()
    entries = {name: (int(cpu_base) + off) & 0xFFFF for name, off in a.labels.items()}
    for alias in ("right", "left", "up", "down"):
        entries[alias] = entries["entry"]
    return blob, entries


def _build_stage_property_hook() -> bytes:
    a = _Asm()
    a.b(0xA5, 0x05)
    a.b(0xC9, 0x30)
    a.branch(0x90, "orig")
    a.b(0xC9, 0x38)
    a.branch(0x90, "panel")
    a.b(0xC9, 0x40)
    a.branch(0x90, "orig")
    a.b(0xC9, 0x50)
    a.branch(0x90, "panel")
    a.label("orig")
    a.b(0xB9, 0x0E, 0xA3, 0x60)
    a.label("panel")
    a.b(0xA9, panel_monster_variant.PANEL_PROPERTY, 0x60)
    return a.finish()


def _build_stage_anim_hook() -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x08)
    a.b(0xC9, 0x30)
    a.branch(0x90, "orig")
    a.b(0xC9, 0x38)
    a.branch(0x90, "panel")
    a.b(0xC9, 0x40)
    a.branch(0x90, "orig")
    a.b(0xC9, 0x50)
    a.branch(0x90, "panel")
    a.label("orig")
    a.b(0xA4, 0x0E)
    a.b(0xB9, 0xE8, 0xD0, 0x85, 0x0A)
    a.b(0xB9, 0xE9, 0xD0, 0x85, 0x0B)
    a.b(0x60)
    a.label("panel")
    a.b(0xA9, panel_monster_variant.PANEL_ANIM_META[0], 0x85, 0x0A)
    a.b(0xA9, panel_monster_variant.PANEL_ANIM_META[1], 0x85, 0x0B)
    a.b(0x60)
    return a.finish()


FINAL_BULLET_SPEED_APPLY = _build_bullet_speed_apply(
    CPU_FINAL_BULLET_SPEED_APPLY + len(_build_bullet_speed_apply(0))
)
FINAL_BULLET_SPEED_TABLE = SPEED_PRESET_RUNTIME_TABLE
FINAL_MERGED_PANEL_BULLET_HOOK = _build_merged_panel_bullet_hook(CPU_FINAL_BULLET_SPEED_APPLY)
FINAL_STATE0_INTERVAL_HELPER = _build_final_state0_interval_helper()
FINAL_GROUP_RAM_OFFSET_HELPER = _build_final_group_ram_offset_helper()
FINAL_SPEED_SELECT_HELPER = _build_final_speed_select_helper()
FINAL_STATIC_MARKER_HELPER = _build_static_marker_helper()
FINAL_DYNAMIC_SPEED_MARKER_HELPER = _build_dynamic_speed_marker_helper(CPU_FINAL_SPEED_SELECT_HELPER)
FINAL_FIRE_MARKER_TABLE = _build_final_fire_marker_table()
FINAL_STAGE_DISPATCH_TAIL = _build_final_stage_dispatch_tail(
    panel_monster_variant.CPU_FIRE_3WAY,
    panel_monster_variant.CPU_FIRE_3WAY + 0x04,
)
FINAL_FIRE_COMMON = _build_final_fire_common(
    panel_monster_variant.ORIG_FIRE_DELAY,
    CPU_FINAL_FIRE_MARKER_TABLE,
    CPU_FINAL_STATIC_MARKER_HELPER,
    CPU_FINAL_DYNAMIC_SPEED_MARKER_HELPER,
)
FINAL_FIRE_DISPATCH = _build_final_fire_dispatch(
    CPU_FINAL_STAGE_DISPATCH_TAIL,
    panel_monster_variant.CPU_FIRE_3WAY + 0x0C,
    panel_monster_variant.CPU_FIRE_3WAY + 0x08,
)
FINAL_HOOK_STATE0_INTERVAL = bytes.fromhex("20") + _word(CPU_FINAL_STATE0_INTERVAL_HELPER) + bytes.fromhex("ea ea ea")
FINAL_AI_WRAPPER_CANDIDATE, FINAL_AI_WRAPPER_ENTRIES = _build_final_ai_wrapper_candidate(
    CPU_FINAL_AI_WRAPPER_CANDIDATE
)
FINAL_STAGE_PROPERTY_HOOK = _build_stage_property_hook()
FINAL_STAGE_ANIM_HOOK = _build_stage_anim_hook()
FINAL_BORROWED_SPEED_NEUTRALIZE = bytes(
    OFF_FINAL_BORROWED_SPEED_NEUTRALIZE_END - OFF_FINAL_BORROWED_SPEED_NEUTRALIZE
)
assert len(FINAL_BULLET_SPEED_APPLY) + len(FINAL_BULLET_SPEED_TABLE) <= 0x3A
assert len(FINAL_MERGED_PANEL_BULLET_HOOK) <= len(panel_monster_variant.CAVE_BULLET_HOOK) + 0x21
assert len(FINAL_FIRE_COMMON) <= len(panel_monster_variant.CAVE_FIRE_3WAY)
assert len(FINAL_FIRE_DISPATCH) <= len(panel_monster_variant.CAVE_FIRE_DISPATCH)
assert len(FINAL_STAGE_DISPATCH_TAIL) <= 0x0E
assert len(FINAL_STATE0_INTERVAL_HELPER) <= 0x12
assert len(FINAL_GROUP_RAM_OFFSET_HELPER) <= 0x17
assert len(FINAL_SPEED_SELECT_HELPER) <= 0x0A
assert len(FINAL_FIRE_MARKER_TABLE) <= 0x12
assert len(FINAL_STATIC_MARKER_HELPER) <= 0x10
assert len(FINAL_DYNAMIC_SPEED_MARKER_HELPER) <= 0x1E
assert len(FINAL_AI_WRAPPER_CANDIDATE) <= len(panel_monster_variant.CAVE_AI_DEMON_WRAPPER)
assert len(FINAL_STAGE_PROPERTY_HOOK) <= len(panel_monster_variant.CAVE_PROPERTY_HOOK)
assert len(FINAL_STAGE_ANIM_HOOK) <= len(panel_monster_variant.CAVE_ANIM_HOOK)


def panel_variant_bullet_placement_candidate() -> dict[str, int]:
    return {
        "bullet_speed_apply_off": OFF_FINAL_BULLET_SPEED_APPLY,
        "bullet_speed_apply_size": len(FINAL_BULLET_SPEED_APPLY),
        "bullet_speed_table_off": OFF_FINAL_BULLET_SPEED_APPLY + len(FINAL_BULLET_SPEED_APPLY),
        "bullet_speed_table_size": len(FINAL_BULLET_SPEED_TABLE),
        "bullet_speed_gap_capacity": 0x3A,
        "merged_bullet_hook_off": panel_monster_variant.OFF_BULLET_HOOK,
        "merged_bullet_hook_size": len(FINAL_MERGED_PANEL_BULLET_HOOK),
        "existing_bullet_hook_size": len(panel_monster_variant.CAVE_BULLET_HOOK),
        "merged_bullet_hook_growth": len(FINAL_MERGED_PANEL_BULLET_HOOK) - len(panel_monster_variant.CAVE_BULLET_HOOK),
        "post_bullet_hook_gap_capacity": 0x21,
    }


def panel_variant_fire_placement_candidate() -> dict[str, int]:
    return {
        "fire_dispatch_off": panel_monster_variant.OFF_FIRE_DISPATCH,
        "fire_dispatch_size": len(FINAL_FIRE_DISPATCH),
        "fire_dispatch_capacity": len(panel_monster_variant.CAVE_FIRE_DISPATCH),
        "stage_dispatch_tail_off": OFF_FINAL_STAGE_DISPATCH_TAIL,
        "stage_dispatch_tail_size": len(FINAL_STAGE_DISPATCH_TAIL),
        "fire_common_off": panel_monster_variant.OFF_FIRE_3WAY,
        "fire_common_size": len(FINAL_FIRE_COMMON),
        "fire_common_capacity": len(panel_monster_variant.CAVE_FIRE_3WAY),
        "state0_interval_helper_off": OFF_FINAL_STATE0_INTERVAL_HELPER,
        "state0_interval_helper_size": len(FINAL_STATE0_INTERVAL_HELPER),
        "group_ram_offset_helper_off": OFF_FINAL_GROUP_RAM_OFFSET_HELPER,
        "group_ram_offset_helper_size": len(FINAL_GROUP_RAM_OFFSET_HELPER),
        "speed_select_helper_off": OFF_FINAL_SPEED_SELECT_HELPER,
        "speed_select_helper_size": len(FINAL_SPEED_SELECT_HELPER),
        "fire_marker_table_off": OFF_FINAL_FIRE_MARKER_TABLE,
        "fire_marker_table_size": len(FINAL_FIRE_MARKER_TABLE),
        "static_marker_helper_off": OFF_FINAL_STATIC_MARKER_HELPER,
        "static_marker_helper_size": len(FINAL_STATIC_MARKER_HELPER),
        "dynamic_speed_marker_helper_off": OFF_FINAL_DYNAMIC_SPEED_MARKER_HELPER,
        "dynamic_speed_marker_helper_size": len(FINAL_DYNAMIC_SPEED_MARKER_HELPER),
    }


def panel_variant_ai_wrapper_candidate() -> dict[str, int]:
    return {
        "ai_wrapper_size": len(FINAL_AI_WRAPPER_CANDIDATE),
        "ai_wrapper_candidate_off": OFF_FINAL_AI_WRAPPER_CANDIDATE,
        "ai_wrapper_candidate_capacity": len(panel_monster_variant.CAVE_AI_DEMON_WRAPPER),
        "right_entry_cpu": FINAL_AI_WRAPPER_ENTRIES["right"],
        "left_entry_cpu": FINAL_AI_WRAPPER_ENTRIES["left"],
        "up_entry_cpu": FINAL_AI_WRAPPER_ENTRIES["up"],
        "down_entry_cpu": FINAL_AI_WRAPPER_ENTRIES["down"],
        "old_separate_ai_wrappers_size": PANEL_VARIANT_BLOB.sizes["ai_wrapper_c"] + PANEL_VARIANT_BLOB.sizes["ai_wrapper_ab"],
        "candidate_reduction": PANEL_VARIANT_BLOB.sizes["ai_wrapper_c"] + PANEL_VARIANT_BLOB.sizes["ai_wrapper_ab"] - len(FINAL_AI_WRAPPER_CANDIDATE),
    }


def panel_variant_split_placement_candidate() -> dict[str, object]:
    """Return the current split placement plan without writing ROM data."""
    pieces = (
        ("fire_dispatch", panel_monster_variant.OFF_FIRE_DISPATCH, len(FINAL_FIRE_DISPATCH), len(panel_monster_variant.CAVE_FIRE_DISPATCH)),
        ("stage_dispatch_tail", OFF_FINAL_STAGE_DISPATCH_TAIL, len(FINAL_STAGE_DISPATCH_TAIL), 0x0E),
        ("fire_common", panel_monster_variant.OFF_FIRE_3WAY, len(FINAL_FIRE_COMMON), len(panel_monster_variant.CAVE_FIRE_3WAY)),
        ("state0_interval_helper", OFF_FINAL_STATE0_INTERVAL_HELPER, len(FINAL_STATE0_INTERVAL_HELPER), 0x12),
        ("group_ram_offset_helper", OFF_FINAL_GROUP_RAM_OFFSET_HELPER, len(FINAL_GROUP_RAM_OFFSET_HELPER), 0x17),
        ("speed_select_helper", OFF_FINAL_SPEED_SELECT_HELPER, len(FINAL_SPEED_SELECT_HELPER), 0x0A),
        ("static_fire_marker_helper", OFF_FINAL_STATIC_MARKER_HELPER, len(FINAL_STATIC_MARKER_HELPER), 0x10),
        ("dynamic_speed_marker_helper", OFF_FINAL_DYNAMIC_SPEED_MARKER_HELPER, len(FINAL_DYNAMIC_SPEED_MARKER_HELPER), 0x1E),
        ("bullet_speed_apply_and_table", OFF_FINAL_BULLET_SPEED_APPLY, len(FINAL_BULLET_SPEED_APPLY) + len(FINAL_BULLET_SPEED_TABLE), 0x3A),
        ("shared_ai_wrapper", OFF_FINAL_AI_WRAPPER_CANDIDATE, len(FINAL_AI_WRAPPER_CANDIDATE), len(panel_monster_variant.CAVE_AI_DEMON_WRAPPER)),
        ("fire_marker_table", OFF_FINAL_FIRE_MARKER_TABLE, len(FINAL_FIRE_MARKER_TABLE), 0x13),
        ("merged_panel_bullet_hook", panel_monster_variant.OFF_BULLET_HOOK, len(FINAL_MERGED_PANEL_BULLET_HOOK), len(panel_monster_variant.CAVE_BULLET_HOOK) + 0x21),
    )
    rows = []
    overlaps = []
    for name, off, size, capacity in pieces:
        rows.append({
            "name": name,
            "file_start": off,
            "file_end": off + size - 1,
            "cpu_start": _cpu(off),
            "cpu_end": _cpu(off + size - 1),
            "size": size,
            "capacity": capacity,
            "remaining": capacity - size,
        })
    for left_index, left in enumerate(rows):
        for right in rows[left_index + 1:]:
            if left["file_end"] >= right["file_start"] and right["file_end"] >= left["file_start"]:
                overlaps.append((left["name"], right["name"]))
    return {
        "pieces": rows,
        "overlaps": overlaps,
        "overlap_free": not overlaps,
        "prg0_growth_without_movable_data": panel_variant_prg0_prg1_budget_estimate()[
            "merged_bullet_hook_prg0_growth_without_movable_data"
        ],
    }


def apply_final_split_test_candidate(rom_data: bytearray, levels: list = None) -> list[str]:
    """Apply the split Panel Variant candidate to a test ROM only.

    This is deliberately not wired to the normal app save path.
    """
    if rom_data is None:
        raise PanelMonsterStageVariantError("ROM is missing.")
    min_len = max(
        TABLE_END,
        OFF_FINAL_BULLET_SPEED_APPLY + len(FINAL_BULLET_SPEED_APPLY) + len(FINAL_BULLET_SPEED_TABLE),
        OFF_FINAL_AI_WRAPPER_CANDIDATE + len(FINAL_AI_WRAPPER_CANDIDATE),
        panel_monster_variant.OFF_ANIM_HOOK + len(FINAL_STAGE_ANIM_HOOK),
    )
    if len(rom_data) < min_len:
        raise PanelMonsterStageVariantError("ROM is too short for final split Panel Variant test candidate.")

    changed: list[str] = []
    if patch_table(rom_data, levels):
        changed.append("PanelVariantStageTable")
    changed.extend(apply_runtime_loader(rom_data))

    _write_blob(rom_data, panel_monster_variant.OFF_HOOK_PANEL_FIRE, panel_monster_variant.HOOK_PANEL_FIRE, changed, "$A556 Panel Variant fire hook")
    _write_blob(rom_data, panel_monster_variant.OFF_HOOK_BULLET_MOVE, panel_monster_variant.HOOK_BULLET_MOVE, changed, "$AFBB Panel Variant Bullet hook")
    _write_blob(rom_data, OFF_STATE0_INTERVAL_HOOK, FINAL_HOOK_STATE0_INTERVAL, changed, "$A575 Panel Variant final interval hook")
    _write_blob(rom_data, panel_monster_variant.OFF_A2CC, panel_monster_variant.HOOK_A2CC, changed, "$A2CC Panel Variant property dispatch")
    _write_blob(rom_data, panel_monster_variant.OFF_8B05, panel_monster_variant.HOOK_8B05, changed, "$8B05 Panel Variant animation dispatch")

    ai_entry = _word(FINAL_AI_WRAPPER_ENTRIES["entry"])
    for off, name in (
        (OFF_AI_RANGE_30_33, "$A33C Panel Variant C AI"),
        (OFF_AI_RANGE_34_37, "$A33E Panel Variant C AI"),
        (OFF_AI_RANGE_40_43, "$A344 Panel Variant A AI"),
        (OFF_AI_RANGE_44_47, "$A346 Panel Variant A AI"),
        (OFF_AI_RANGE_48_4B, "$A348 Panel Variant B AI"),
        (OFF_AI_RANGE_4C_4F, "$A34A Panel Variant B AI"),
    ):
        _write_blob(rom_data, off, ai_entry, changed, name)

    for off, blob, name in (
        (panel_monster_variant.OFF_FIRE_DISPATCH, FINAL_FIRE_DISPATCH, "Panel Variant final fire dispatch"),
        (OFF_FINAL_STAGE_DISPATCH_TAIL, FINAL_STAGE_DISPATCH_TAIL, "Panel Variant final stage dispatch tail"),
        (panel_monster_variant.OFF_FIRE_3WAY, FINAL_FIRE_COMMON, "Panel Variant final common fire loop"),
        (OFF_FINAL_STATE0_INTERVAL_HELPER, FINAL_STATE0_INTERVAL_HELPER, "Panel Variant final interval helper"),
        (OFF_FINAL_GROUP_RAM_OFFSET_HELPER, FINAL_GROUP_RAM_OFFSET_HELPER, "Panel Variant final group RAM offset helper"),
        (OFF_FINAL_SPEED_SELECT_HELPER, FINAL_SPEED_SELECT_HELPER, "Panel Variant final speed select helper"),
        (OFF_FINAL_STATIC_MARKER_HELPER, FINAL_STATIC_MARKER_HELPER, "Panel Variant final static marker helper"),
        (OFF_FINAL_DYNAMIC_SPEED_MARKER_HELPER, FINAL_DYNAMIC_SPEED_MARKER_HELPER, "Panel Variant final dynamic speed marker helper"),
        (OFF_FINAL_BULLET_SPEED_APPLY, FINAL_BULLET_SPEED_APPLY + FINAL_BULLET_SPEED_TABLE, "Panel Variant final Bullet speed apply/table"),
        (OFF_FINAL_AI_WRAPPER_CANDIDATE, FINAL_AI_WRAPPER_CANDIDATE, "Panel Variant final shared AI wrapper"),
        (OFF_FINAL_FIRE_MARKER_TABLE, FINAL_FIRE_MARKER_TABLE, "Panel Variant final fire marker table"),
        (OFF_FINAL_BORROWED_SPEED_NEUTRALIZE, FINAL_BORROWED_SPEED_NEUTRALIZE, "Panel Variant final borrowed-ID speed neutralize"),
        (panel_monster_variant.OFF_BULLET_HOOK, FINAL_MERGED_PANEL_BULLET_HOOK, "Panel Variant final merged Bullet hook"),
        (panel_monster_variant.OFF_PROPERTY_HOOK, FINAL_STAGE_PROPERTY_HOOK, "Panel Variant final property hook"),
        (panel_monster_variant.OFF_ANIM_HOOK, FINAL_STAGE_ANIM_HOOK, "Panel Variant final animation hook"),
    ):
        _write_blob(rom_data, off, blob, changed, name)
    return changed


def _build_ai_wrapper_c_blob(cpu_base: int) -> bytes:
    table_offset = 46
    table_cpu = (int(cpu_base) + table_offset) & 0xFFFF
    return (
        bytes.fromhex(
            "a9 00 a0 05 91 2e a0 06 91 2e a0 08 91 2e a0 09 "
            "91 2e a0 01 b1 2e 29 06 4a a8 b9 "
        )
        + _word(table_cpu)
        + bytes.fromhex(
            "48 a0 03 b1 2e 29 fc 91 2e 68 11 2e 91 2e "
            "4c 4c a5 02 03 00 01"
        )
    )


@dataclass(frozen=True)
class PanelVariantBlob:
    """Placement-independent Panel Variant runtime block.

    This is the object to pack later.  It intentionally contains no file
    offsets and does not write ROM data.
    """

    base_cpu: int
    data: bytes
    entries: dict[str, int]
    sizes: dict[str, int]
    external_targets: dict[str, int]


def _append_blob_section(
    out: bytearray,
    entries: dict[str, int],
    sizes: dict[str, int],
    base_cpu: int,
    name: str,
    blob: bytes,
) -> None:
    entries[name] = (base_cpu + len(out)) & 0xFFFF
    sizes[name] = len(blob)
    out.extend(blob)


def build_panel_variant_blob(base_cpu: int = 0x8000) -> PanelVariantBlob:
    """Build the current A/B/C Panel Variant runtime as one packable blob.

    The blob is deliberately not wired to the app or to concrete PRG0 offsets.
    It packages the currently validated pieces as a single unit:

    - C-group direction wrapper;
    - A/B-group direction wrapper;
    - state0 interval helper reading `$0741/$0743/$0745`;
    - state1 fire marker that keeps the stock `$10` delay and tags the child
      Bullet with speed marker `$88-$8B`;
    - Bullet speed hook/apply helpers that run only in Bullet state2 and return
      control to the stock Bullet dispatcher.

    The speed selector and preset table are packed with the blob so the final
    Bullet hook can consume the same A/B/C stage cache without redefining data.
    """
    base_cpu = int(base_cpu) & 0xFFFF
    out = bytearray()
    entries: dict[str, int] = {}
    sizes: dict[str, int] = {}
    _append_blob_section(
        out,
        entries,
        sizes,
        base_cpu,
        "ai_wrapper_c",
        _build_ai_wrapper_c_blob(base_cpu + len(out)),
    )
    _append_blob_section(out, entries, sizes, base_cpu, "ai_wrapper_ab", V7_AI_WRAPPER_AB_HEAD)
    _append_blob_section(
        out,
        entries,
        sizes,
        base_cpu,
        "group_ram_offset_helper",
        _build_group_ram_offset_helper(base_cpu + len(out)),
    )
    _append_blob_section(
        out,
        entries,
        sizes,
        base_cpu,
        "state0_interval_helper",
        _build_state0_interval_helper_shared(entries["group_ram_offset_helper"]),
    )
    _append_blob_section(
        out,
        entries,
        sizes,
        base_cpu,
        "speed_preset_select_helper",
        _build_speed_preset_select_helper(entries["group_ram_offset_helper"]),
    )
    _append_blob_section(out, entries, sizes, base_cpu, "speed_preset_runtime_table", SPEED_PRESET_RUNTIME_TABLE)
    _append_blob_section(
        out,
        entries,
        sizes,
        base_cpu,
        "state1_fire_marker",
        _build_state1_fire_marker(entries["speed_preset_select_helper"]),
    )
    _append_blob_section(
        out,
        entries,
        sizes,
        base_cpu,
        "bullet_speed_apply",
        _build_bullet_speed_apply(entries["speed_preset_runtime_table"]),
    )
    _append_blob_section(
        out,
        entries,
        sizes,
        base_cpu,
        "bullet_speed_hook",
        _build_bullet_speed_hook(entries["bullet_speed_apply"]),
    )
    external_targets = {
        "stock_panel_ai": 0xA54C,
        "stock_non_panel_ai": 0xA64A,
        "stock_fast_spark_ai": 0xA92D,
        "stock_bullet_state2": 0xAFD8,
        "stock_bullet_impact_after_collision": 0xAFDF,
        "stock_bullet_no_collision_return": 0xB009,
        "stock_bullet_collision_sampler": 0xAC39,
        "state1_ready_target": 0xBD9A,
    }
    return PanelVariantBlob(
        base_cpu=base_cpu,
        data=bytes(out),
        entries=entries,
        sizes=sizes,
        external_targets=external_targets,
    )


PANEL_VARIANT_BLOB = build_panel_variant_blob()


def panel_variant_pure_growth_estimate() -> dict[str, int]:
    """Return the current byte-budget estimate before final PRG0 packing.

    This is not a placement result.  It separates the current standalone blob
    into parts that can replace existing Panel Monster runtime and parts that
    are still real growth.  Keep this conservative until the merged production
    builder exists.
    """
    ai_replacement_growth = (
        PANEL_VARIANT_BLOB.sizes["ai_wrapper_c"]
        + PANEL_VARIANT_BLOB.sizes["ai_wrapper_ab"]
        - 36  # existing Saramandor-ID wrapper
        - 57  # existing Demonhead-ID wrapper
    )
    interval_growth = PANEL_VARIANT_BLOB.sizes["state0_interval_helper"]
    speed_config_growth = (
        PANEL_VARIANT_BLOB.sizes["group_ram_offset_helper"]
        + PANEL_VARIANT_BLOB.sizes["speed_preset_select_helper"]
        + PANEL_VARIANT_BLOB.sizes["speed_preset_runtime_table"]
    )
    state1_growth = PANEL_VARIANT_BLOB.sizes["state1_fire_marker"]
    bullet_speed_growth = (
        PANEL_VARIANT_BLOB.sizes["bullet_speed_apply"]
        + PANEL_VARIANT_BLOB.sizes["bullet_speed_hook"]
    )
    current_shape_growth = (
        ai_replacement_growth
        + interval_growth
        + speed_config_growth
        + state1_growth
        + bullet_speed_growth
    )
    merged_bullet_hook_growth = current_shape_growth - PANEL_VARIANT_BLOB.sizes["bullet_speed_hook"]
    return {
        "standalone_blob": len(PANEL_VARIANT_BLOB.data),
        "ai_replacement_growth": ai_replacement_growth,
        "interval_growth": interval_growth,
        "speed_config_growth": speed_config_growth,
        "state1_growth": state1_growth,
        "bullet_speed_growth": bullet_speed_growth,
        "current_shape_growth": current_shape_growth,
        "merged_bullet_hook_growth": merged_bullet_hook_growth,
        "target_after_merge": 160,
        "must_reduce_about": max(0, merged_bullet_hook_growth - 160),
    }


def panel_variant_prg0_prg1_budget_estimate() -> dict[str, int]:
    """Return the current PRG0/PRG1 split estimate for final packing.

    The standalone blob still packs the speed preset table next to PRG0 code so
    it can be relocated as one object during tests.  For production, that table
    is data, not hot PRG0 code.  It can be moved to PRG1 or pre-expanded into
    the `$0740-$074F` stage-variant cache by the room loader.
    """
    pure = panel_variant_pure_growth_estimate()
    prg1_movable_data = PANEL_VARIANT_BLOB.sizes["speed_preset_runtime_table"]
    prg1_existing_stage_data = TABLE_LENGTH
    prg1_existing_loader = len(RUNTIME_LOADER)
    prg1_loader_reserved = 0x60
    prg0_runtime_blob_without_movable_data = len(PANEL_VARIANT_BLOB.data) - prg1_movable_data
    current_prg0_growth_without_movable_data = pure["current_shape_growth"] - prg1_movable_data
    merged_prg0_growth_without_movable_data = pure["merged_bullet_hook_growth"] - prg1_movable_data
    return {
        "standalone_blob_total": len(PANEL_VARIANT_BLOB.data),
        "standalone_prg0_code_or_hot_helpers": prg0_runtime_blob_without_movable_data,
        "standalone_prg1_or_cache_data": prg1_movable_data,
        "current_shape_prg0_growth": pure["current_shape_growth"],
        "current_shape_prg0_growth_without_movable_data": current_prg0_growth_without_movable_data,
        "merged_bullet_hook_prg0_growth": pure["merged_bullet_hook_growth"],
        "merged_bullet_hook_prg0_growth_without_movable_data": merged_prg0_growth_without_movable_data,
        "already_planned_prg1_stage_table": prg1_existing_stage_data,
        "already_planned_prg1_loader": prg1_existing_loader,
        "already_planned_prg1_loader_reserved": prg1_loader_reserved,
        "prg1_loader_hook_bytes_in_prg0_prg1_bank_switch_tail": len(HOOK_M66_LOADER_TAIL),
        "next_prg0_reduction_target": 160,
        "remaining_reduction_after_prg1_data_move": max(
            0,
            merged_prg0_growth_without_movable_data - 160,
        ),
    }
RESERVED_SPANS = (
    (OFF_AI_WRAPPER_C_PROTO, STATE1_MOUTH_GATE_SIZE),
    (OFF_PRG1_RUNTIME_LOADER, 0x60),
    (TABLE_OFFSET, TABLE_LENGTH),
    (OFF_STATE0_INTERVAL_HELPER, len(STATE0_INTERVAL_HELPER)),
    (OFF_STATE1_MOUTH_GATE, STATE1_MOUTH_GATE_SIZE),
)


def is_panel_stage_variant_id(enemy_id: int) -> bool:
    return (int(enemy_id) & 0xFF) in PANEL_STAGE_VARIANT_IDS


def has_panel_stage_variant_ids(levels: list) -> bool:
    """Return True if any level currently uses an A/B/C stage-variant ID."""
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if is_panel_stage_variant_id(getattr(enemy, "element_no", -1)):
                return True
        for mirror in getattr(lv, "demon_mirrors", []) or []:
            for code in getattr(mirror, "enemy_codes", []) or []:
                if is_panel_stage_variant_id(code):
                    return True
    return False


def _blank_entry() -> bytes:
    return build_entry()


def normalize_speed_preset(value: int) -> int:
    preset = int(value) & 0xFF
    if preset not in SPEED_PRESET_TABLE_VALUES:
        raise PanelMonsterStageVariantError(f"Unsupported Panel Variant speed preset: {value!r}")
    return preset


def speed_preset_velocity_values(value: int) -> tuple[int, int]:
    preset = SPEED_PRESET_TABLE_VALUES[normalize_speed_preset(value)]
    return preset["right_down"], preset["left_up"]


def speed_preset_extra_steps(value: int) -> int:
    return SPEED_PRESET_TABLE_VALUES[normalize_speed_preset(value)]["extra_steps"]


def build_entry(
    a_speed: int = DEFAULT_A_SPEED_PRESET,
    a_interval: int = DEFAULT_A_INTERVAL,
    b_speed: int = DEFAULT_B_SPEED_PRESET,
    b_interval: int = DEFAULT_B_INTERVAL,
    c_speed: int = DEFAULT_C_SPEED_PRESET,
    c_interval: int = DEFAULT_C_INTERVAL,
) -> bytes:
    """Build one 16-byte Panel Variant stage entry.

    The entry format is A speed/interval, B speed/interval, C speed/interval.
    There is no normal-speed preset and no rhythm field.
    """
    return bytes((
        normalize_speed_preset(a_speed),
        int(a_interval) & 0xFF,
        normalize_speed_preset(b_speed),
        int(b_interval) & 0xFF,
        normalize_speed_preset(c_speed),
        int(c_interval) & 0xFF,
        0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00,
    ))


def build_table(levels: list = None) -> bytes:
    """Build the prototype PRG1 PanelVariantStageTable.

    Entry bytes 0..5 are the current speed+interval prototype cache:
    A speed, A interval, B speed, B interval, C speed, C interval.
    Rhythm was removed from the feature.
    """
    table = bytearray([0x00] * TABLE_LENGTH)
    table[:len(MAGIC)] = MAGIC
    table[len(MAGIC)] = FORMAT
    table[len(MAGIC) + 1] = ENTRY_SIZE
    table[len(MAGIC) + 2] = ROOM_COUNT
    table[len(MAGIC) + 3] = 0
    for i in range(ROOM_COUNT):
        base = HEADER_SIZE + i * ENTRY_SIZE
        table[base:base + ENTRY_SIZE] = _blank_entry()
    return bytes(table)


def patch_table(rom_data: bytearray, levels: list = None) -> bool:
    if len(rom_data) < TABLE_END:
        return False
    table = build_table(levels)
    if bytes(rom_data[TABLE_OFFSET:TABLE_END]) == table:
        return False
    rom_data[TABLE_OFFSET:TABLE_END] = table
    return True


def read_table(rom_data: bytes) -> list[bytes]:
    if len(rom_data) < TABLE_END:
        return []
    raw = bytes(rom_data[TABLE_OFFSET:TABLE_END])
    if not raw.startswith(MAGIC):
        return []
    if raw[len(MAGIC)] != FORMAT or raw[len(MAGIC) + 1] != ENTRY_SIZE:
        return []
    return [
        raw[HEADER_SIZE + i * ENTRY_SIZE:HEADER_SIZE + (i + 1) * ENTRY_SIZE]
        for i in range(ROOM_COUNT)
    ]


def _build_runtime_loader() -> bytes:
    # This supersedes stage_ext.RUNTIME_LOADER while preserving its side effects.
    # StageExt pointer starts at entry byte2: bank1 CPU $8802 + room*8.
    # PanelVariant pointer starts at entry byte0: bank1 CPU $8A70 + room*16.
    return bytes.fromhex(
        "a9 ff 8d 2a 07 8d 2b 07"
        "a9 00 8d 23 07 8d 24 07 8d 29 07"
        "ad 28 04 0a 0a 0a 18 69 02 85 00"
        "a9 88 69 00 85 01"
        "a0 00 b1 00 8d 2b 07"
        "a0 04 b1 00 8d 78 07"
        "a0 05 b1 00 8d 7c 07"
        "ad 28 04 0a 0a 0a 0a 18 69 70 85 00"
        "a9 8a 69 00 85 01"
        "a0 0f b1 00 99 40 07 88 10 f8"
        "60"
    )


RUNTIME_LOADER = _build_runtime_loader()
assert len(RUNTIME_LOADER) <= 0x60


def apply_runtime_loader(rom_data: bytearray) -> list[str]:
    if len(rom_data) < OFF_PRG1_RUNTIME_LOADER + len(RUNTIME_LOADER):
        return []
    cur = bytes(rom_data[OFF_M66_LOADER_TAIL:OFF_M66_LOADER_TAIL + len(ORIG_M66_LOADER_TAIL)])
    if cur not in (ORIG_M66_LOADER_TAIL, HOOK_M66_LOADER_TAIL):
        return []
    changed: list[str] = []
    if bytes(rom_data[OFF_PRG1_RUNTIME_LOADER:OFF_PRG1_RUNTIME_LOADER + len(RUNTIME_LOADER)]) != RUNTIME_LOADER:
        rom_data[OFF_PRG1_RUNTIME_LOADER:OFF_PRG1_RUNTIME_LOADER + len(RUNTIME_LOADER)] = RUNTIME_LOADER
        changed.append("Panel stage-variant combined PRG1 runtime loader")
    if cur != HOOK_M66_LOADER_TAIL:
        rom_data[OFF_M66_LOADER_TAIL:OFF_M66_LOADER_TAIL + len(HOOK_M66_LOADER_TAIL)] = HOOK_M66_LOADER_TAIL
        changed.append("mapper66 loader Panel stage-variant hook")
    return changed


def _write_blob(rom_data, off: int, blob: bytes, changed: list[str], name: str) -> None:
    if bytes(rom_data[off:off + len(blob)]) != blob:
        rom_data[off:off + len(blob)] = blob
        changed.append(name)


def apply_stage_table_interval_prototype(rom_data, levels: list = None) -> list[str]:
    """Apply the table-loaded interval prototype.

    The room-load-time PRG1 loader fills $0740-$074F from
    PanelVariantStageTable.  The PRG0 hook changes only the state0 firing
    interval compare at $A575/$A579; the state1 mouth delay remains stock.
    """
    if rom_data is None or len(rom_data) < max(TABLE_END, OFF_STATE0_INTERVAL_HELPER + len(STATE0_INTERVAL_HELPER)):
        raise PanelMonsterStageVariantError("ROM is too short for PanelVariantStageTable.")
    cur_hook = bytes(rom_data[OFF_STATE0_INTERVAL_HOOK:OFF_STATE0_INTERVAL_HOOK + len(ORIG_STATE0_INTERVAL_HOOK)])
    if cur_hook not in (
        ORIG_STATE0_INTERVAL_HOOK,
        V7_STATE0_INTERVAL_HOOK,
        V8_STATE0_INTERVAL_HOOK,
        HOOK_STATE0_INTERVAL,
    ):
        raise PanelMonsterStageVariantError(
            f"$A575 state0 interval hook signature mismatch: got {cur_hook.hex(' ')}"
        )

    changed: list[str] = []
    _write_blob(
        rom_data,
        OFF_AI_WRAPPER_C_PROTO,
        FIXED_AI_WRAPPER_C + bytes([0xEA] * (STATE1_MOUTH_GATE_SIZE - len(FIXED_AI_WRAPPER_C))),
        changed,
        "Panel stage-variant C direction table wrapper",
    )
    if patch_table(rom_data, levels):
        changed.append("PanelVariantStageTable")
    changed.extend(apply_runtime_loader(rom_data))
    _write_blob(
        rom_data,
        OFF_STATE0_INTERVAL_HELPER,
        STATE0_INTERVAL_HELPER,
        changed,
        "Panel stage-variant state0 interval helper reads $0741/$0743/$0745",
    )
    _write_blob(
        rom_data,
        OFF_STATE1_MOUTH_GATE,
        STATE1_MOUTH_GATE,
        changed,
        "Panel stage-variant state1 mouth gate restored to $10",
    )
    _write_blob(
        rom_data,
        OFF_STATE0_INTERVAL_HOOK,
        HOOK_STATE0_INTERVAL,
        changed,
        "$A575 Panel stage-variant interval helper hook",
    )
    return changed


def can_apply_stage_table_interval_prototype(rom_data) -> bool:
    """Return True when the ROM already contains the ABC prototype wrappers."""
    if not ENABLE_STAGE_TABLE_INTERVAL_PROTOTYPE:
        return False
    if rom_data is None:
        return False
    cur_c = bytes(rom_data[OFF_AI_WRAPPER_C_PROTO:OFF_AI_WRAPPER_C_PROTO + len(FIXED_AI_WRAPPER_C)])
    cur_c_old = bytes(rom_data[OFF_AI_WRAPPER_C_PROTO:OFF_AI_WRAPPER_C_PROTO + len(V7_AI_WRAPPER_C_HEAD)])
    return (
        cur_c == FIXED_AI_WRAPPER_C
        or cur_c_old == V7_AI_WRAPPER_C_HEAD
    ) and (
        bytes(rom_data[OFF_AI_WRAPPER_AB_PROTO:OFF_AI_WRAPPER_AB_PROTO + len(V7_AI_WRAPPER_AB_HEAD)])
        == V7_AI_WRAPPER_AB_HEAD
    )


apply = apply_stage_table_interval_prototype

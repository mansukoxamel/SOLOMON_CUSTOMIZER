"""Panel Monster stage-variant patch.

This module is intentionally separate from ``panel_monster_variant.py``.
The existing module owns the production 2-way/3-way borrowed-ID Panel Monster
feature.  This module is for the newer global-parameterized A/B/C families:

  C: $31/$33/$35/$37
  A: $41/$43/$45/$47
  B: $49/$4B/$4D/$4F

Current scope:
  - hook the state0 firing interval compare at $A575/$A579;
  - keep the state1 pre-shot fire gate at the stock $10;
  - write one fixed PRG0 A/B/C speed+interval table on every expanded-ROM save;
  - read that PRG0 table directly from the runtime so no Panel Variant settings
    RAM is needed during rooms.

Rhythm was removed from the design; there is intentionally no 1x speed preset
because stock Panel Monster already covers normal-speed shots.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import panel_bullet_speed_fix, panel_monster_variant, spark_ball_variant, stage_ext


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

BORROWED_PANEL_RUNTIME_IDS = frozenset((0x52, 0x53, 0x56, 0x57, 0x5A, 0x5B, 0x66, 0x67))
PANEL_STAGE_RUNTIME_IDS = PANEL_STAGE_VARIANT_IDS | BORROWED_PANEL_RUNTIME_IDS
BORROWED_FIRE_2WAY_CANONICAL_IDS = (0x52, 0x56)
BORROWED_FIRE_3WAY_CANONICAL_IDS = (0x5A, 0x66)
STOCK_PANEL_IDS = frozenset((0x24, 0x25, 0x26, 0x27))

GROUP_C_IDS = frozenset((0x31, 0x33, 0x35, 0x37))
GROUP_A_IDS = frozenset((0x41, 0x43, 0x45, 0x47))
GROUP_B_IDS = frozenset((0x49, 0x4B, 0x4D, 0x4F))

DEFAULT_C_INTERVAL = 0xC0
DEFAULT_A_INTERVAL = 0xC0
DEFAULT_B_INTERVAL = 0xC0
DEFAULT_A_SPEED_PRESET = 0
DEFAULT_B_SPEED_PRESET = 1
DEFAULT_C_SPEED_PRESET = 2
LEVEL_ATTRS = {
    "a_speed": "panel_variant_a_speed",
    "a_interval": "panel_variant_a_interval",
    "b_speed": "panel_variant_b_speed",
    "b_interval": "panel_variant_b_interval",
    "c_speed": "panel_variant_c_speed",
    "c_interval": "panel_variant_c_interval",
}

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

SETTINGS_TABLE_OFFSET = 0x62ED  # CPU $E2DD, PRG0 table read directly by runtime
SETTINGS_TABLE_LENGTH = 6
SETTINGS_TABLE_END = SETTINGS_TABLE_OFFSET + SETTINGS_TABLE_LENGTH
CPU_SETTINGS_TABLE = _cpu(SETTINGS_TABLE_OFFSET)
OFF_STAGE_EXT_GAMEPLAY_FLAG_HELPER = 0x8A76
CPU_STAGE_EXT_GAMEPLAY_FLAG_HELPER = OFF_STAGE_EXT_GAMEPLAY_FLAG_HELPER - 0x10
STAGE_EXT_GAMEPLAY_FLAG_HELPER_LENGTH = 22
RAM_GAMEPLAY_STAGE_FLAGS = 0x0770
CPU_PRG1_RUNTIME_LOADER = 0x8A00
OFF_PRG1_RUNTIME_LOADER = 0x8A10
OFF_M66_LOADER_TAIL = 0x80C4
ORIG_M66_LOADER_TAIL = bytes.fromhex("60 00 00")
HOOK_M66_LOADER_TAIL = bytes((
    0x4C,
    CPU_PRG1_RUNTIME_LOADER & 0xFF,
    CPU_PRG1_RUNTIME_LOADER >> 8,
))

OFF_STATE0_INTERVAL_HOOK = 0x2585  # CPU $A575
OFF_STATE0_INTERVAL_CMP = 0x2589   # CPU $A579
OFF_STATE0_INTERVAL_THRESHOLD = OFF_STATE0_INTERVAL_CMP + 1
STATE1_MOUTH_GATE_SIZE = 0x3F
OFF_AI_RANGE_30_33 = 0xA33C - 0x8000 + 0x10
OFF_AI_RANGE_34_37 = 0xA33E - 0x8000 + 0x10
OFF_AI_RANGE_40_43 = 0xA344 - 0x8000 + 0x10
OFF_AI_RANGE_44_47 = 0xA346 - 0x8000 + 0x10
OFF_AI_RANGE_48_4B = 0xA348 - 0x8000 + 0x10
OFF_AI_RANGE_4C_4F = 0xA34A - 0x8000 + 0x10

OFF_FINAL_FIRE_DISPATCH = 0x6496  # CPU $E486, new cleanup runtime block
CPU_FINAL_FIRE_DISPATCH = _cpu(OFF_FINAL_FIRE_DISPATCH)
OFF_FINAL_FIRE_COMMON = 0x653B  # CPU $E52B, new cleanup runtime block
CPU_FINAL_FIRE_COMMON = _cpu(OFF_FINAL_FIRE_COMMON)
OFF_FINAL_BULLET_SPEED_APPLY = 0x66C9  # CPU $E6B9, new cleanup runtime block
CPU_FINAL_BULLET_SPEED_APPLY = _cpu(OFF_FINAL_BULLET_SPEED_APPLY)
OFF_FINAL_BULLET_SPEED_HOOK = 0x6747  # CPU $E737, new cleanup runtime block
CPU_FINAL_BULLET_SPEED_HOOK = _cpu(OFF_FINAL_BULLET_SPEED_HOOK)
OFF_FINAL_STAGE_PROPERTY_HOOK = 0x674A  # CPU $E73A, new cleanup runtime block
CPU_FINAL_STAGE_PROPERTY_HOOK = _cpu(OFF_FINAL_STAGE_PROPERTY_HOOK)
OFF_FINAL_STAGE_ANIM_HOOK = 0x6758  # CPU $E748, new cleanup runtime block
CPU_FINAL_STAGE_ANIM_HOOK = _cpu(OFF_FINAL_STAGE_ANIM_HOOK)
OFF_FINAL_BULLET_SPEED_EXTRA_HELPER = 0x6612  # CPU $E602, new cleanup runtime block
CPU_FINAL_BULLET_SPEED_EXTRA_HELPER = _cpu(OFF_FINAL_BULLET_SPEED_EXTRA_HELPER)
OFF_FINAL_STAGE_DISPATCH_HELPER = 0x673C  # CPU $E72C, new cleanup runtime block
CPU_FINAL_STAGE_DISPATCH_HELPER = _cpu(OFF_FINAL_STAGE_DISPATCH_HELPER)
OFF_FINAL_STATE0_INTERVAL_HELPER = 0x65AD  # CPU $E59D, new cleanup runtime block
CPU_FINAL_STATE0_INTERVAL_HELPER = _cpu(OFF_FINAL_STATE0_INTERVAL_HELPER)
OFF_FINAL_STATE0_INTERVAL_THRESHOLD = OFF_FINAL_STATE0_INTERVAL_HELPER + 0x10
OFF_FINAL_GROUP_RAM_OFFSET_HELPER = 0x65BF  # CPU $E5AF, new cleanup runtime block
CPU_FINAL_GROUP_RAM_OFFSET_HELPER = _cpu(OFF_FINAL_GROUP_RAM_OFFSET_HELPER)
OFF_FINAL_FIRE_MARKER_TABLE = OFF_FINAL_STAGE_DISPATCH_HELPER  # CPU $E72C, new cleanup runtime block
CPU_FINAL_FIRE_MARKER_TABLE = _cpu(OFF_FINAL_FIRE_MARKER_TABLE)
OFF_FINAL_STATIC_MARKER_HELPER = 0x65E5  # CPU $E5D5, new cleanup runtime block
CPU_FINAL_STATIC_MARKER_HELPER = _cpu(OFF_FINAL_STATIC_MARKER_HELPER)
OFF_FINAL_DYNAMIC_SPEED_MARKER_HELPER = 0x65F1  # CPU $E5E1, new cleanup runtime block
CPU_FINAL_DYNAMIC_SPEED_MARKER_HELPER = _cpu(OFF_FINAL_DYNAMIC_SPEED_MARKER_HELPER)
OFF_FINAL_PARENT_FIELD_CLEAR_HELPER = 0x6601  # CPU $E5F1, new cleanup runtime block
CPU_FINAL_PARENT_FIELD_CLEAR_HELPER = _cpu(OFF_FINAL_PARENT_FIELD_CLEAR_HELPER)
OFF_FINAL_BULLET_ENTRY_HELPER = 0x6662  # CPU $E652, new cleanup runtime block
CPU_FINAL_BULLET_ENTRY_HELPER = _cpu(OFF_FINAL_BULLET_ENTRY_HELPER)
OFF_FINAL_BULLET_ENTRY_HELPER_END = 0x66A9
OFF_FINAL_BULLET_ENTRY_TAIL_HELPER = 0x66A9  # CPU $E699, new cleanup runtime block
CPU_FINAL_BULLET_ENTRY_TAIL_HELPER = _cpu(OFF_FINAL_BULLET_ENTRY_TAIL_HELPER)
OFF_FINAL_SHARED_AI_WRAPPER = 0x6701  # CPU $E6F1, new cleanup runtime block
CPU_FINAL_SHARED_AI_WRAPPER = _cpu(OFF_FINAL_SHARED_AI_WRAPPER)
OFF_SPEED_INIT_CALL = 0x067D  # CPU $866D, original JSR $8AC0 speed initializer
OFF_FINAL_AI_DISPATCH_HELPER = 0x64BF  # CPU $E4AF, new cleanup runtime block
CPU_FINAL_AI_DISPATCH_HELPER = _cpu(OFF_FINAL_AI_DISPATCH_HELPER)
OFF_FINAL_AI_DISPATCH_PANEL_HELPER = 0x64D2  # CPU $E4C2, new cleanup runtime block
CPU_FINAL_AI_DISPATCH_PANEL_HELPER = _cpu(OFF_FINAL_AI_DISPATCH_PANEL_HELPER)
OFF_FINAL_PARENT_SPEED_GUARD = 0x64DE  # CPU $E4CE, new cleanup runtime block
CPU_FINAL_PARENT_SPEED_GUARD = _cpu(OFF_FINAL_PARENT_SPEED_GUARD)
FINAL_AI_DISPATCH_PANEL_HELPER_CAPACITY = 0x0C
FINAL_PARENT_FIELD_CLEAR_HELPER_CAPACITY = 0x11
FINAL_PARENT_SPEED_GUARD_CAPACITY = 0x1D
OFF_FINAL_PANEL_TYPE_CLASSIFIER = 0x64FB  # CPU $E4EB, new cleanup runtime block
CPU_FINAL_PANEL_TYPE_CLASSIFIER = _cpu(OFF_FINAL_PANEL_TYPE_CLASSIFIER)
OFF_FINAL_PANEL_TYPE_CLASSIFIER_TAIL = 0x6516  # CPU $E506, new cleanup runtime block
CPU_FINAL_PANEL_TYPE_CLASSIFIER_TAIL = _cpu(OFF_FINAL_PANEL_TYPE_CLASSIFIER_TAIL)
OFF_FINAL_PANEL_ANIM_DIR_HELPER = 0x652A  # CPU $E51A, new cleanup runtime block
CPU_FINAL_PANEL_ANIM_DIR_HELPER = _cpu(OFF_FINAL_PANEL_ANIM_DIR_HELPER)
OFF_FINAL_ABC_GROUP_OFFSET_HELPER = 0x65C7  # CPU $E5B7, new cleanup runtime block
CPU_FINAL_ABC_GROUP_OFFSET_HELPER = _cpu(OFF_FINAL_ABC_GROUP_OFFSET_HELPER)

ORIG_STATE0_INTERVAL_HOOK = bytes.fromhex("a0 02 b1 2c c9 c0")
ORIG_SPEED_INIT_CALL = bytes.fromhex("20 c0 8a")
HOOK_SPEED_INIT_CALL = bytes.fromhex("20") + _word(CPU_FINAL_PARENT_SPEED_GUARD)
HOOK_FINAL_PANEL_FIRE_HEAD = bytes.fromhex("4c") + _word(CPU_FINAL_FIRE_DISPATCH)
HOOK_FINAL_PANEL_FIRE = (
    HOOK_FINAL_PANEL_FIRE_HEAD
    + panel_monster_variant.ORIG_PANEL_FIRE[len(HOOK_FINAL_PANEL_FIRE_HEAD):]
)
HOOK_FINAL_BULLET_MOVE = bytes.fromhex("20") + _word(CPU_FINAL_BULLET_SPEED_HOOK)
HOOK_PREVIOUS_PANEL_FIRE_WITH_SPARK_PROPERTY = (
    panel_monster_variant.HOOK_PANEL_FIRE_HEAD
    + spark_ball_variant.CAVE_PROPERTY_HOOK
    + bytes([0xEA] * (
        len(panel_monster_variant.HOOK_PANEL_FIRE)
        - len(panel_monster_variant.HOOK_PANEL_FIRE_HEAD)
        - len(spark_ball_variant.CAVE_PROPERTY_HOOK)
    ))
)
ORIG_PANEL_FIRE_WITH_SPARK_PROPERTY = (
    panel_monster_variant.ORIG_PANEL_FIRE[:3]
    + spark_ball_variant.CAVE_PROPERTY_HOOK
    + panel_monster_variant.ORIG_PANEL_FIRE[
        3 + len(spark_ball_variant.CAVE_PROPERTY_HOOK):
    ]
)
HOOK_PANEL_FIRE_WITH_SPARK_PROPERTY = (
    HOOK_FINAL_PANEL_FIRE_HEAD
    + spark_ball_variant.CAVE_PROPERTY_HOOK
    + bytes([0xEA] * (
        len(panel_monster_variant.HOOK_PANEL_FIRE)
        - len(HOOK_FINAL_PANEL_FIRE_HEAD)
        - len(spark_ball_variant.CAVE_PROPERTY_HOOK)
    ))
)
HOOK_A2CC_SPARK_PROPERTY = bytes.fromhex("20") + _word(spark_ball_variant.CPU_PROPERTY_HOOK)
HOOK_8B05_SPARK_ANIM = (
    bytes.fromhex("20")
    + _word(spark_ball_variant.CPU_ANIM_HOOK)
    + bytes([0xEA] * (len(panel_monster_variant.HOOK_8B05) - 3))
)


def _retarget_spark_panel_fallback(blob: bytes, old_cpu: int, new_cpu: int) -> bytes:
    old_jmp = bytes.fromhex("4c") + _word(old_cpu)
    new_jmp = bytes.fromhex("4c") + _word(new_cpu)
    if blob.count(old_jmp) != 1:
        raise PanelMonsterStageVariantError(
            f"Spark selector fallback target mismatch: {old_jmp.hex(' ')}"
        )
    return blob.replace(old_jmp, new_jmp, 1)


FINAL_SPARK_PROPERTY_HOOK = _retarget_spark_panel_fallback(
    spark_ball_variant.CAVE_PROPERTY_HOOK,
    spark_ball_variant.CPU_PANEL_PROPERTY_HOOK,
    CPU_FINAL_STAGE_PROPERTY_HOOK,
)
FINAL_SPARK_ANIM_HOOK = _retarget_spark_panel_fallback(
    spark_ball_variant.CAVE_ANIM_HOOK,
    spark_ball_variant.CPU_PANEL_ANIM_HOOK,
    CPU_FINAL_STAGE_ANIM_HOOK,
)
def _build_group_ram_offset_helper(cpu_base: int) -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E)
    a.jsr(CPU_FINAL_ABC_GROUP_OFFSET_HELPER)
    a.b(0x60)
    return a.finish()


def _build_abc_group_offset_helper() -> bytes:
    a = _Asm()
    a.b(0x4A)
    a.branch(0x90, "orig")
    a.b(0xC9, 0x18)
    a.branch(0x90, "orig")
    a.b(0xC9, 0x1C)
    a.branch(0x90, "group_c")
    a.b(0xC9, 0x20)
    a.branch(0x90, "orig")
    a.b(0xC9, 0x28)
    a.branch(0xB0, "orig")
    a.b(0x29, 0x0C, 0x4A, 0xAA, 0x60)
    a.label("group_c")
    a.b(0xA2, 0x04, 0x60)
    a.label("orig")
    a.b(0xA2, 0xFF, 0x60)
    return a.finish()


def _build_state0_interval_helper_shared(group_offset_cpu: int) -> bytes:
    a = _Asm()
    a.jsr(group_offset_cpu)
    a.b(0xA0, 0x02, 0xB1, 0x2C, 0xE0, 0xFF)
    a.branch(0xF0, "orig")
    a.b(0xDD, (CPU_SETTINGS_TABLE + 1) & 0xFF, (CPU_SETTINGS_TABLE + 1) >> 8, 0x60)
    a.label("orig")
    a.b(0xC9, 0xC0, 0x60)
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

STATIC_SPREAD_MARKERS = bytes((0x83, 0x84, 0x81, 0x80, 0x82))
DYNAMIC_SPEED_MARKERS = bytes((0x88, 0x89, 0x8A, 0x8B))
DYNAMIC_SPEED_MARKER_BASE = DYNAMIC_SPEED_MARKERS[0]
DYNAMIC_SPEED_MARKER_END = DYNAMIC_SPEED_MARKERS[-1] + 1


def _build_final_state0_interval_helper() -> bytes:
    return _build_state0_interval_helper_shared(CPU_FINAL_GROUP_RAM_OFFSET_HELPER)


def _current_global_panel_threshold(rom_data: bytearray) -> int:
    if (
        len(rom_data) > OFF_FINAL_STATE0_INTERVAL_THRESHOLD + 1
        and rom_data[OFF_FINAL_STATE0_INTERVAL_THRESHOLD - 1] == 0xC9
        and rom_data[OFF_FINAL_STATE0_INTERVAL_THRESHOLD + 1] == 0x60
    ):
        return rom_data[OFF_FINAL_STATE0_INTERVAL_THRESHOLD]
    if len(rom_data) > OFF_STATE0_INTERVAL_THRESHOLD and rom_data[OFF_STATE0_INTERVAL_CMP] == 0xC9:
        return rom_data[OFF_STATE0_INTERVAL_THRESHOLD]
    return 0xC0


def _final_state0_interval_helper_for_rom(rom_data: bytearray) -> bytes:
    blob = bytearray(FINAL_STATE0_INTERVAL_HELPER)
    blob[OFF_FINAL_STATE0_INTERVAL_THRESHOLD - OFF_FINAL_STATE0_INTERVAL_HELPER] = _current_global_panel_threshold(rom_data)
    return bytes(blob)


def _build_final_group_ram_offset_helper() -> bytes:
    return _build_group_ram_offset_helper(CPU_FINAL_GROUP_RAM_OFFSET_HELPER)


def _build_static_marker_helper() -> bytes:
    return bytes.fromhex("48 a5 02 20 56 b1 a0 07 68 91 00 60")


def _build_dynamic_speed_marker_helper(group_offset_cpu: int, static_marker_cpu: int) -> bytes:
    a = _Asm()
    a.b(0x8A, 0x48)
    a.jsr(group_offset_cpu)
    a.b(0xBD, CPU_SETTINGS_TABLE & 0xFF, CPU_SETTINGS_TABLE >> 8, 0x09, DYNAMIC_SPEED_MARKER_BASE)
    a.jsr(static_marker_cpu)
    a.b(0x68, 0xAA, 0x60)
    return a.finish()


def _build_final_fire_marker_table() -> bytes:
    return bytes((
        STATIC_SPREAD_MARKERS[0],
        STATIC_SPREAD_MARKERS[1],
        0xFF,
        STATIC_SPREAD_MARKERS[2],
        STATIC_SPREAD_MARKERS[3],
        STATIC_SPREAD_MARKERS[4],
        0xFF, 0xFE, 0xFF, 0xFF, 0xFF,
    ))


def _build_final_fire_common(
    base_cpu: int,
    marker_table_cpu: int,
    static_marker_cpu: int,
    dynamic_marker_cpu: int,
) -> bytes:
    base_cpu = int(base_cpu) & 0xFFFF
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
    # Keep the pre-shot fire gate at the stock Panel Monster value.
    a.b(0xA0, 0x01, 0xB1, 0x2C, 0xC9, panel_monster_variant.ORIG_FIRE_DELAY)
    a.branch(0x90, "rts")
    a.label("loop")
    a.b(0x8A, 0x48)
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0x03, 0xAA)
    a.b(0x20, 0x76, 0xAE)
    a.b(0x68, 0xAA)
    a.b(0xBD, marker_table_cpu & 0xFF, marker_table_cpu >> 8, 0xC9, 0xFF)
    a.branch(0xF0, "clear_marker")
    a.b(0xC9, 0xFE)
    a.branch(0xD0, "static_marker")
    a.jsr(dynamic_marker_cpu)
    a.branch(0xD0, "mark_done")
    a.label("clear_marker")
    a.b(0xA9, 0x00)
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


def _build_previous_stage_dispatch_tail(helper_cpu: int) -> bytes:
    return bytes.fromhex("4c") + _word(helper_cpu)


def _build_previous_stage_dispatch_helper(stage_entry_cpu: int, normal_entry_cpu: int) -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E)
    a.jsr(CPU_FINAL_PANEL_TYPE_CLASSIFIER)
    a.branch(0xB0, "stage")
    a.jmp(normal_entry_cpu)
    a.label("stage")
    a.jmp(stage_entry_cpu)
    return a.finish()


def _build_final_ai_dispatch_helper(
    entry_cpu: int,
    panel_tail_cpu: int,
    panel_entry_cpu: int,
    clear_helper_cpu: int,
) -> tuple[bytes, bytes, dict[str, int]]:
    a = _Asm()
    a.label("entry")
    a.b(0x48, 0x98, 0x48)
    a.b(0xA0, 0x01, 0xB1, 0x2E, 0x4A)
    a.branch(0xB0, "panel_jump")
    a.b(0x68, 0xA8, 0x68)
    a.jmp(0xABF7)
    a.label("panel_jump")
    a.jmp(panel_tail_cpu)
    entry_blob = a.finish()

    b = _Asm()
    b.label("panel")
    b.b(0x29, 0x03, 0xAA, 0x68, 0x68)
    b.jsr(clear_helper_cpu)
    b.b(0x8A)
    b.jmp(panel_entry_cpu)
    panel_blob = b.finish()
    entries = {
        "entry": int(entry_cpu) & 0xFFFF,
        "panel": int(panel_tail_cpu) & 0xFFFF,
    }
    return entry_blob, panel_blob, entries


def _build_parent_field_clear_helper() -> bytes:
    a = _Asm()
    a.b(0xA9, 0x00)
    a.b(0xA0, 0x09, 0x91, 0x2E, 0x88, 0x91, 0x2E)
    a.b(0xA0, 0x06, 0x91, 0x2E, 0x88, 0x91, 0x2E)
    a.b(0x60)
    return a.finish()


def _build_parent_speed_guard() -> bytes:
    a = _Asm()
    a.jsr(0x8AC0)
    a.b(0xA0, 0x01, 0xB1, 0x08)
    a.jsr(CPU_FINAL_PANEL_TYPE_CLASSIFIER)
    a.branch(0x90, "done")
    a.b(0xA9, 0x00)
    a.b(0xA0, 0x09, 0x91, 0x08, 0x88, 0x91, 0x08)
    a.b(0xA0, 0x06, 0x91, 0x08, 0x88, 0x91, 0x08)
    a.label("done")
    a.b(0x60)
    return a.finish()


def _build_panel_type_classifier(tail_cpu: int) -> bytes:
    a = _Asm()
    a.b(0x4A)
    a.branch(0xB0, "stage")
    a.jmp(tail_cpu)
    a.label("stage")
    a.b(0xC9, 0x18)
    a.branch(0x90, "normal")
    a.b(0xC9, 0x1C)
    a.branch(0x90, "panel")
    a.b(0xC9, 0x20)
    a.branch(0x90, "normal")
    a.b(0xC9, 0x28)
    a.branch(0x90, "panel")
    a.label("normal")
    a.jmp(tail_cpu)
    a.label("panel")
    a.b(0x38, 0x60)
    return a.finish()


def _build_panel_type_classifier_tail() -> bytes:
    a = _Asm()
    for shifted_id in (0x29, 0x2B, 0x2D, 0x33):
        a.b(0xC9, shifted_id)
        a.branch(0xF0, "panel")
    a.label("orig")
    a.b(0x18, 0x60)
    a.label("panel")
    a.b(0x38, 0x60)
    return a.finish()


def _build_previous_fire_dispatch(stage_tail_cpu: int, two_entry_cpu: int, three_entry_cpu: int) -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E, 0x29, 0xFE)
    for enemy_id in BORROWED_FIRE_2WAY_CANONICAL_IDS:
        a.b(0xC9, enemy_id)
        a.branch(0xF0, "two")
    for enemy_id in BORROWED_FIRE_3WAY_CANONICAL_IDS:
        a.b(0xC9, enemy_id)
        a.branch(0xF0, "three")
    a.jmp(stage_tail_cpu)
    a.label("two")
    a.jmp(two_entry_cpu)
    a.label("three")
    a.jmp(three_entry_cpu)
    return a.finish()


def _build_final_fire_dispatch(
    stage_entry_cpu: int,
    normal_entry_cpu: int,
    two_entry_cpu: int,
    three_entry_cpu: int,
) -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x2E, 0xAA, 0x29, 0xFE)
    for enemy_id in BORROWED_FIRE_2WAY_CANONICAL_IDS:
        a.b(0xC9, enemy_id)
        a.branch(0xF0, "two")
    for enemy_id in BORROWED_FIRE_3WAY_CANONICAL_IDS:
        a.b(0xC9, enemy_id)
        a.branch(0xF0, "three")
    a.b(0x8A)
    a.jsr(CPU_FINAL_PANEL_TYPE_CLASSIFIER)
    a.branch(0xB0, "stage")
    a.jmp(normal_entry_cpu)
    a.label("stage")
    a.jmp(stage_entry_cpu)
    a.label("two")
    a.jmp(two_entry_cpu)
    a.label("three")
    a.jmp(three_entry_cpu)
    return a.finish()


def _build_final_shared_ai_wrapper(cpu_base: int, clear_helper_cpu: int) -> tuple[bytes, dict[str, int]]:
    a = _Asm()
    a.label("entry")
    a.b(0xA0, 0x01, 0xB1, 0x2E)
    a.b(0xC9, 0x52); a.branch(0x90, "orig")
    a.b(0xC9, 0x5C); a.branch(0xB0, "orig")
    a.b(0xC9, 0x54); a.branch(0x90, "demon_rl")
    a.b(0xC9, 0x56); a.branch(0x90, "demon_orig")
    a.b(0xC9, 0x58); a.branch(0x90, "demon_ud")
    a.b(0xC9, 0x5A); a.branch(0x90, "demon_orig")
    a.label("demon_rl")
    a.b(0x29, 0x01)
    a.branch(0x10, "set")
    a.label("demon_ud")
    a.b(0x29, 0x01, 0x09, 0x02)
    a.label("set")
    a.b(0x48)
    a.jsr(clear_helper_cpu)
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0xFC, 0x91, 0x2E)
    a.b(0x68, 0x11, 0x2E, 0x91, 0x2E)
    a.jmp(0xA54C)
    a.label("demon_orig")
    a.label("orig")
    a.jmp(0xB208)
    blob = bytearray(a.finish())
    entries = {name: (int(cpu_base) + off) & 0xFFFF for name, off in a.labels.items()}
    for alias in ("right", "left", "up", "down"):
        entries[alias] = entries["set"]
    return bytes(blob), entries


def _build_stage_property_hook() -> bytes:
    a = _Asm()
    a.b(0xA5, 0x05)
    a.jsr(CPU_FINAL_PANEL_TYPE_CLASSIFIER)
    a.branch(0xB0, "panel")
    a.label("orig")
    a.b(0xB9, 0x0E, 0xA3, 0x60)
    a.label("panel")
    a.b(0xA9, panel_monster_variant.PANEL_PROPERTY, 0x60)
    return a.finish()


def _build_stage_anim_hook() -> bytes:
    a = _Asm()
    a.b(0xA0, 0x01, 0xB1, 0x08)
    a.jsr(CPU_FINAL_PANEL_TYPE_CLASSIFIER)
    a.branch(0xB0, "panel")
    a.label("orig")
    a.b(0xA4, 0x0E)
    a.b(0xB9, 0xE8, 0xD0, 0x85, 0x0A)
    a.b(0xB9, 0xE9, 0xD0, 0x85, 0x0B)
    a.b(0x60)
    a.label("panel")
    a.b(0xA9, panel_monster_variant.PANEL_ANIM_META[0], 0x85, 0x0A)
    a.b(0xA9, panel_monster_variant.PANEL_ANIM_META[1], 0x85, 0x0B)
    a.b(0xA0, 0x01, 0xB1, 0x08)
    a.jsr(CPU_FINAL_PANEL_ANIM_DIR_HELPER)
    a.b(0x85, 0x0F)
    a.b(0x60)
    return a.finish()


def _build_panel_anim_dir_helper() -> bytes:
    a = _Asm()
    a.b(0xC9, 0x50)
    a.branch(0x90, "abc")
    a.b(0x29, 0x05, 0xC9, 0x04)
    a.branch(0x90, "done")
    a.b(0xE9, 0x02)
    a.label("done")
    a.b(0x60)
    a.label("abc")
    a.b(0x4A, 0x29, 0x03, 0x60)
    return a.finish()


FINAL_BULLET_SPEED_HOOK_CAPACITY = 0x03
FINAL_BULLET_ENTRY_HELPER_CAPACITY = OFF_FINAL_BULLET_ENTRY_HELPER_END - OFF_FINAL_BULLET_ENTRY_HELPER
FINAL_BULLET_ENTRY_TAIL_HELPER_CAPACITY = 0x20
FINAL_STATE0_INTERVAL_HELPER = _build_final_state0_interval_helper()
FINAL_GROUP_RAM_OFFSET_HELPER = _build_final_group_ram_offset_helper()
FINAL_ABC_GROUP_OFFSET_HELPER = _build_abc_group_offset_helper()
FINAL_STATIC_MARKER_HELPER = _build_static_marker_helper()
FINAL_DYNAMIC_SPEED_MARKER_HELPER = _build_dynamic_speed_marker_helper(
    CPU_FINAL_GROUP_RAM_OFFSET_HELPER,
    CPU_FINAL_STATIC_MARKER_HELPER,
)
FINAL_PARENT_FIELD_CLEAR_HELPER = _build_parent_field_clear_helper()
FINAL_FIRE_MARKER_TABLE = _build_final_fire_marker_table()
PREVIOUS_STAGE_DISPATCH_TAIL = _build_previous_stage_dispatch_tail(CPU_FINAL_STAGE_DISPATCH_HELPER)
PREVIOUS_STAGE_DISPATCH_HELPER = _build_previous_stage_dispatch_helper(
    CPU_FINAL_FIRE_COMMON,
    CPU_FINAL_FIRE_COMMON + 0x04,
)
FINAL_FIRE_COMMON = _build_final_fire_common(
    CPU_FINAL_FIRE_COMMON,
    CPU_FINAL_FIRE_MARKER_TABLE,
    CPU_FINAL_STATIC_MARKER_HELPER,
    CPU_FINAL_DYNAMIC_SPEED_MARKER_HELPER,
)
PREVIOUS_FIRE_DISPATCH = _build_previous_fire_dispatch(
    _cpu(0x3D01),
    panel_monster_variant.CPU_FIRE_3WAY + 0x0C,
    panel_monster_variant.CPU_FIRE_3WAY + 0x08,
)
FINAL_FIRE_DISPATCH = _build_final_fire_dispatch(
    CPU_FINAL_FIRE_COMMON,
    CPU_FINAL_FIRE_COMMON + 0x04,
    CPU_FINAL_FIRE_COMMON + 0x0C,
    CPU_FINAL_FIRE_COMMON + 0x08,
)
FINAL_HOOK_STATE0_INTERVAL = bytes.fromhex("20") + _word(CPU_FINAL_STATE0_INTERVAL_HELPER) + bytes.fromhex("ea ea ea")
FINAL_SHARED_AI_WRAPPER, FINAL_AI_WRAPPER_ENTRIES = _build_final_shared_ai_wrapper(
    CPU_FINAL_SHARED_AI_WRAPPER,
    CPU_FINAL_PARENT_FIELD_CLEAR_HELPER,
)
PREVIOUS_DYNAMIC_SPEED_MARKER_HELPER = bytes.fromhex(
    "8a4820bdbe098848a5022056b1a00768910068aa60"
)
PREVIOUS_INLINE_DYNAMIC_SPEED_MARKER_HELPER = bytes.fromhex(
    "8a48209fbebd4007098848a5022056b1a00768910068aa60"
)
PREVIOUS_SHARED_AI_WRAPPER = _build_final_shared_ai_wrapper(
    _cpu(0x68C1),
    CPU_FINAL_PARENT_FIELD_CLEAR_HELPER,
)[0]
PREVIOUS_SHARED_AI_WRAPPER_SHIFTED = (
    PREVIOUS_SHARED_AI_WRAPPER[0x03:] + bytes.fromhex("224748")
)
FINAL_AI_DISPATCH_HELPER, FINAL_AI_DISPATCH_PANEL_HELPER, FINAL_AI_DISPATCH_ENTRIES = _build_final_ai_dispatch_helper(
    CPU_FINAL_AI_DISPATCH_HELPER,
    CPU_FINAL_AI_DISPATCH_PANEL_HELPER,
    FINAL_AI_WRAPPER_ENTRIES["set"],
    CPU_FINAL_PARENT_FIELD_CLEAR_HELPER,
)
FINAL_PARENT_SPEED_GUARD = _build_parent_speed_guard()
FINAL_PANEL_TYPE_CLASSIFIER = _build_panel_type_classifier(CPU_FINAL_PANEL_TYPE_CLASSIFIER_TAIL)
FINAL_PANEL_TYPE_CLASSIFIER_TAIL = _build_panel_type_classifier_tail()
FINAL_PANEL_ANIM_DIR_HELPER = _build_panel_anim_dir_helper()
FINAL_STAGE_PROPERTY_HOOK = _build_stage_property_hook()
FINAL_STAGE_ANIM_HOOK = _build_stage_anim_hook()
assert len(FINAL_FIRE_COMMON) <= len(panel_monster_variant.CAVE_FIRE_3WAY)
assert len(FINAL_FIRE_DISPATCH) <= len(panel_monster_variant.CAVE_FIRE_DISPATCH) + len(PREVIOUS_STAGE_DISPATCH_TAIL) + 0x07
assert len(PREVIOUS_STAGE_DISPATCH_HELPER) <= STATE1_MOUTH_GATE_SIZE
assert len(PREVIOUS_STAGE_DISPATCH_HELPER) <= 0x13
assert len(FINAL_AI_DISPATCH_HELPER) <= 0x18
assert len(FINAL_AI_DISPATCH_PANEL_HELPER) <= FINAL_AI_DISPATCH_PANEL_HELPER_CAPACITY
assert len(FINAL_STATE0_INTERVAL_HELPER) <= 0x12
assert len(FINAL_GROUP_RAM_OFFSET_HELPER) <= 0x17
assert len(FINAL_ABC_GROUP_OFFSET_HELPER) <= 0x30
assert len(FINAL_FIRE_MARKER_TABLE) <= 0x12
assert len(FINAL_STATIC_MARKER_HELPER) <= 0x10
assert len(FINAL_DYNAMIC_SPEED_MARKER_HELPER) <= (OFF_FINAL_SHARED_AI_WRAPPER - OFF_FINAL_DYNAMIC_SPEED_MARKER_HELPER)
assert len(FINAL_PARENT_FIELD_CLEAR_HELPER) <= FINAL_PARENT_FIELD_CLEAR_HELPER_CAPACITY
assert len(FINAL_SHARED_AI_WRAPPER) <= 0xAB
assert len(FINAL_PARENT_SPEED_GUARD) <= FINAL_PARENT_SPEED_GUARD_CAPACITY
assert len(FINAL_PANEL_TYPE_CLASSIFIER) <= 0x1E
assert len(FINAL_PANEL_TYPE_CLASSIFIER_TAIL) <= 0x14
assert len(FINAL_STAGE_PROPERTY_HOOK) <= len(panel_monster_variant.CAVE_PROPERTY_HOOK)
assert len(FINAL_STAGE_ANIM_HOOK) <= len(panel_monster_variant.CAVE_ANIM_HOOK)
assert OFF_FINAL_STAGE_PROPERTY_HOOK + len(FINAL_STAGE_PROPERTY_HOOK) == OFF_FINAL_STAGE_ANIM_HOOK
assert OFF_FINAL_STAGE_ANIM_HOOK + len(FINAL_STAGE_ANIM_HOOK) <= 0x6780
assert len(FINAL_PANEL_ANIM_DIR_HELPER) <= 0x11


def panel_variant_bullet_placement_report() -> dict[str, int]:
    v2_speed = panel_monster_v2_split_speed_runtime_blobs()
    return {
        "v2_speed_decode_off": OFF_FINAL_BULLET_SPEED_APPLY,
        "v2_speed_decode_size": len(v2_speed["speed_decode"]),
        "v2_speed_decode_capacity": len(v2_speed["speed_decode"]),
        "v2_speed_tables_and_fast_loop_off": OFF_FINAL_BULLET_SPEED_EXTRA_HELPER,
        "v2_speed_tables_and_fast_loop_size": len(v2_speed["tables_and_fast_loop"]),
        "v2_speed_tables_and_fast_loop_capacity": len(v2_speed["tables_and_fast_loop"]),
        "v2_bullet_speed_hook_off": OFF_FINAL_BULLET_SPEED_HOOK,
        "v2_bullet_speed_hook_size": len(v2_speed["bullet_speed_hook"]),
        "v2_bullet_speed_hook_capacity": FINAL_BULLET_SPEED_HOOK_CAPACITY,
        "v2_bullet_entry_helper_off": OFF_FINAL_BULLET_ENTRY_HELPER,
        "v2_bullet_entry_helper_size": len(v2_speed["bullet_entry_helper"]),
        "v2_bullet_entry_helper_capacity": FINAL_BULLET_ENTRY_HELPER_CAPACITY,
        "v2_bullet_entry_tail_helper_off": OFF_FINAL_BULLET_ENTRY_TAIL_HELPER,
        "v2_bullet_entry_tail_helper_size": len(v2_speed["bullet_entry_tail_helper"]),
        "v2_bullet_entry_tail_helper_capacity": FINAL_BULLET_ENTRY_TAIL_HELPER_CAPACITY,
        "existing_bullet_hook_size": len(panel_monster_variant.CAVE_BULLET_HOOK),
        "v2_total_size": sum(len(blob) for blob in v2_speed.values()),
        "v2_total_capacity": (
            len(v2_speed["speed_decode"])
            + len(v2_speed["tables_and_fast_loop"])
            + FINAL_BULLET_SPEED_HOOK_CAPACITY
            + FINAL_BULLET_ENTRY_HELPER_CAPACITY
            + FINAL_BULLET_ENTRY_TAIL_HELPER_CAPACITY
        ),
    }


def panel_variant_fire_placement_report() -> dict[str, int]:
    return {
        "fire_dispatch_off": OFF_FINAL_FIRE_DISPATCH,
        "fire_dispatch_size": len(FINAL_FIRE_DISPATCH),
        "fire_dispatch_capacity": len(FINAL_FIRE_DISPATCH),
        "removed_stage_dispatch_tail_size": len(PREVIOUS_STAGE_DISPATCH_TAIL),
        "removed_stage_dispatch_helper_size": len(PREVIOUS_STAGE_DISPATCH_HELPER),
        "fire_common_off": OFF_FINAL_FIRE_COMMON,
        "fire_common_size": len(FINAL_FIRE_COMMON),
        "fire_common_capacity": len(panel_monster_variant.CAVE_FIRE_3WAY),
        "state0_interval_helper_off": OFF_FINAL_STATE0_INTERVAL_HELPER,
        "state0_interval_helper_size": len(FINAL_STATE0_INTERVAL_HELPER),
        "group_ram_offset_helper_off": OFF_FINAL_GROUP_RAM_OFFSET_HELPER,
        "group_ram_offset_helper_size": len(FINAL_GROUP_RAM_OFFSET_HELPER),
        "abc_group_offset_helper_off": OFF_FINAL_ABC_GROUP_OFFSET_HELPER,
        "abc_group_offset_helper_size": len(FINAL_ABC_GROUP_OFFSET_HELPER),
        "fire_marker_table_off": OFF_FINAL_FIRE_MARKER_TABLE,
        "fire_marker_table_size": len(FINAL_FIRE_MARKER_TABLE),
        "static_marker_helper_off": OFF_FINAL_STATIC_MARKER_HELPER,
        "static_marker_helper_size": len(FINAL_STATIC_MARKER_HELPER),
        "dynamic_speed_marker_helper_off": OFF_FINAL_DYNAMIC_SPEED_MARKER_HELPER,
        "dynamic_speed_marker_helper_size": len(FINAL_DYNAMIC_SPEED_MARKER_HELPER),
    }


def panel_variant_ai_wrapper_report() -> dict[str, int]:
    return {
        "ai_wrapper_size": len(FINAL_SHARED_AI_WRAPPER),
        "ai_wrapper_off": OFF_FINAL_SHARED_AI_WRAPPER,
        "ai_wrapper_capacity": len(FINAL_SHARED_AI_WRAPPER),
        "ai_dispatch_helper_off": OFF_FINAL_AI_DISPATCH_HELPER,
        "ai_dispatch_helper_size": len(FINAL_AI_DISPATCH_HELPER),
        "ai_dispatch_panel_helper_off": OFF_FINAL_AI_DISPATCH_PANEL_HELPER,
        "ai_dispatch_panel_helper_size": len(FINAL_AI_DISPATCH_PANEL_HELPER),
        "parent_field_clear_helper_off": OFF_FINAL_PARENT_FIELD_CLEAR_HELPER,
        "parent_field_clear_helper_size": len(FINAL_PARENT_FIELD_CLEAR_HELPER),
        "parent_speed_guard_off": OFF_FINAL_PARENT_SPEED_GUARD,
        "parent_speed_guard_size": len(FINAL_PARENT_SPEED_GUARD),
        "panel_anim_dir_helper_off": OFF_FINAL_PANEL_ANIM_DIR_HELPER,
        "panel_anim_dir_helper_size": len(FINAL_PANEL_ANIM_DIR_HELPER),
        "right_entry_cpu": FINAL_AI_WRAPPER_ENTRIES["right"],
        "left_entry_cpu": FINAL_AI_WRAPPER_ENTRIES["left"],
        "up_entry_cpu": FINAL_AI_WRAPPER_ENTRIES["up"],
        "down_entry_cpu": FINAL_AI_WRAPPER_ENTRIES["down"],
    }


def panel_variant_split_placement_report() -> dict[str, object]:
    """Return the current split placement without writing ROM data."""
    v2_speed_sizes = _v2_split_speed_reserved_sizes()
    pieces = (
        ("fire_dispatch", OFF_FINAL_FIRE_DISPATCH, len(FINAL_FIRE_DISPATCH), len(FINAL_FIRE_DISPATCH)),
        ("ai_dispatch_helper", OFF_FINAL_AI_DISPATCH_HELPER, len(FINAL_AI_DISPATCH_HELPER), len(FINAL_AI_DISPATCH_HELPER)),
        ("ai_dispatch_panel_helper", OFF_FINAL_AI_DISPATCH_PANEL_HELPER, len(FINAL_AI_DISPATCH_PANEL_HELPER), FINAL_AI_DISPATCH_PANEL_HELPER_CAPACITY),
        ("parent_speed_guard", OFF_FINAL_PARENT_SPEED_GUARD, len(FINAL_PARENT_SPEED_GUARD), FINAL_PARENT_SPEED_GUARD_CAPACITY),
        ("panel_type_classifier", OFF_FINAL_PANEL_TYPE_CLASSIFIER, len(FINAL_PANEL_TYPE_CLASSIFIER), len(FINAL_PANEL_TYPE_CLASSIFIER)),
        ("panel_type_classifier_tail", OFF_FINAL_PANEL_TYPE_CLASSIFIER_TAIL, len(FINAL_PANEL_TYPE_CLASSIFIER_TAIL), 0x14),
        ("panel_anim_dir_helper", OFF_FINAL_PANEL_ANIM_DIR_HELPER, len(FINAL_PANEL_ANIM_DIR_HELPER), 0x11),
        ("fire_common", OFF_FINAL_FIRE_COMMON, len(FINAL_FIRE_COMMON), len(FINAL_FIRE_COMMON)),
        ("state0_interval_helper", OFF_FINAL_STATE0_INTERVAL_HELPER, len(FINAL_STATE0_INTERVAL_HELPER), len(FINAL_STATE0_INTERVAL_HELPER)),
        ("group_ram_offset_helper", OFF_FINAL_GROUP_RAM_OFFSET_HELPER, len(FINAL_GROUP_RAM_OFFSET_HELPER), len(FINAL_GROUP_RAM_OFFSET_HELPER)),
        ("abc_group_offset_helper", OFF_FINAL_ABC_GROUP_OFFSET_HELPER, len(FINAL_ABC_GROUP_OFFSET_HELPER), len(FINAL_ABC_GROUP_OFFSET_HELPER)),
        ("static_fire_marker_helper", OFF_FINAL_STATIC_MARKER_HELPER, len(FINAL_STATIC_MARKER_HELPER), len(FINAL_STATIC_MARKER_HELPER)),
        ("dynamic_speed_marker_helper", OFF_FINAL_DYNAMIC_SPEED_MARKER_HELPER, len(FINAL_DYNAMIC_SPEED_MARKER_HELPER), len(FINAL_DYNAMIC_SPEED_MARKER_HELPER)),
        ("parent_field_clear_helper", OFF_FINAL_PARENT_FIELD_CLEAR_HELPER, len(FINAL_PARENT_FIELD_CLEAR_HELPER), FINAL_PARENT_FIELD_CLEAR_HELPER_CAPACITY),
        ("v2_speed_tables_and_fast_loop", OFF_FINAL_BULLET_SPEED_EXTRA_HELPER, v2_speed_sizes["tables_and_fast_loop"], v2_speed_sizes["tables_and_fast_loop"]),
        ("v2_bullet_entry_helper", OFF_FINAL_BULLET_ENTRY_HELPER, v2_speed_sizes["bullet_entry_helper"], FINAL_BULLET_ENTRY_HELPER_CAPACITY),
        ("v2_bullet_entry_tail_helper", OFF_FINAL_BULLET_ENTRY_TAIL_HELPER, v2_speed_sizes["bullet_entry_tail_helper"], FINAL_BULLET_ENTRY_TAIL_HELPER_CAPACITY),
        ("v2_speed_decode", OFF_FINAL_BULLET_SPEED_APPLY, v2_speed_sizes["speed_decode"], v2_speed_sizes["speed_decode"]),
        ("shared_ai_wrapper", OFF_FINAL_SHARED_AI_WRAPPER, len(FINAL_SHARED_AI_WRAPPER), len(FINAL_SHARED_AI_WRAPPER)),
        ("fire_marker_table", OFF_FINAL_FIRE_MARKER_TABLE, len(FINAL_FIRE_MARKER_TABLE), len(FINAL_FIRE_MARKER_TABLE)),
        ("v2_bullet_speed_hook", OFF_FINAL_BULLET_SPEED_HOOK, v2_speed_sizes["bullet_speed_hook"], FINAL_BULLET_SPEED_HOOK_CAPACITY),
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
    }


def _span_overlap_report(spans: tuple[tuple[int, int], ...]) -> dict[str, object]:
    rows = []
    overlaps = []
    for index, (off, size) in enumerate(spans):
        end = int(off) + int(size) - 1
        rows.append({
            "index": index,
            "file_start": int(off),
            "file_end": end,
            "size": int(size),
        })
    for left_index, left in enumerate(rows):
        for right in rows[left_index + 1:]:
            if left["file_end"] >= right["file_start"] and right["file_end"] >= left["file_start"]:
                overlaps.append((left["index"], right["index"]))
    return {
        "spans": rows,
        "overlaps": overlaps,
        "overlap_free": not overlaps,
    }


def _placement_reserved_coverage_report(
    placement_report: dict[str, object],
    reserved_report: dict[str, object],
) -> dict[str, object]:
    reserved_pairs = {
        (span["file_start"], span["size"])
        for span in reserved_report["spans"]
    }
    missing = []
    for piece in placement_report["pieces"]:
        pair = (piece["file_start"], piece["size"])
        if pair not in reserved_pairs:
            missing.append({
                "name": piece["name"],
                "file_start": piece["file_start"],
                "size": piece["size"],
            })
    return {
        "missing": missing,
        "all_placement_reserved": not missing,
    }


ORIG_FINAL_PARENT_FIELD_CLEAR_HELPER = bytes.fromhex(
    "0008210001000100010001000140010101"
)
ORIG_FINAL_PARENT_SPEED_GUARD = bytes.fromhex(
    "00010001200904410000000000000000000000000fe007e017d0183010000000"
    "00010001000100010001000110111011000105413c7900012008aaac0280701c"
    "08306f"
)
ORIG_FINAL_BULLET_SPEED_EXTRA_HELPER = bytes.fromhex(
    "000001000100010001ddc1155100012aaf000100010001000100005354449648"
    "00a494222400409204100096a014f000000001aca9b2490121524b5899450144"
    "d3201909532b09000100000000000000000000"
)
ORIG_FINAL_BULLET_ENTRY_HELPER = bytes.fromhex(
    "00000000010001000100010001000110111011000105413c7900012008aaac02"
    "80701c08306fe400006c6c00406d6cdeb620080001555320098aa33449901b"
    "244992932409929321490001a001b12e29fec972f007c976f0064c11ad"
)
ORIG_FINAL_BULLET_ENTRY_TAIL_HELPER = bytes.fromhex(
    "0000000000ffff8103e10fbffb8c63844387c3bc7b800385438003fffffffefe"
)
ORIG_FINAL_SHARED_AI_WRAPPER = bytes.fromhex(
    "000000001103d1e0410181381100610e0500190381000100e10001bfdcb5e622"
    "f0808c491837605128a0561d4416b63c5808c400014ad91a094b53"
)
ORIG_FINAL_SHARED_AI_WRAPPER_SHIFTED = bytes.fromhex(
    "001103d1e0410181381100610e0500190381000100e10001bfdcb5e622f080"
    "8c491837605128a0561d4416b63c5808c400014ad91a094b53224748"
)
ORIG_FINAL_ABC_GROUP_OFFSET_HELPER = bytes.fromhex(
    "00000000000000000000000000000000000000004004000000011c7136d9"
)
def _fill(byte: int, size: int) -> bytes:
    return bytes([byte & 0xFF] * int(size))


def _pad(blob: bytes, size: int, fill: int = 0xEA) -> bytes:
    blob = bytes(blob)
    if len(blob) >= size:
        return blob[:size]
    return blob + _fill(fill, size - len(blob))


FINAL_GROUP_RAM_OFFSET_HELPER_WRITE = FINAL_GROUP_RAM_OFFSET_HELPER
FINAL_PARENT_SPEED_GUARD_WRITE = FINAL_PARENT_SPEED_GUARD
assert len(FINAL_GROUP_RAM_OFFSET_HELPER_WRITE) == len(FINAL_GROUP_RAM_OFFSET_HELPER)
assert len(FINAL_PARENT_SPEED_GUARD_WRITE) == len(FINAL_PARENT_SPEED_GUARD)


def _unique_signatures(signatures: tuple[bytes, ...]) -> tuple[bytes, ...]:
    out: list[bytes] = []
    for sig in signatures:
        sig = bytes(sig)
        if sig not in out:
            out.append(sig)
    return tuple(out)


def _expect_signature(rom_data: bytearray, off: int, name: str,
                      signatures: tuple[bytes, ...]) -> None:
    accepted = _unique_signatures(signatures)
    if not accepted:
        raise PanelMonsterStageVariantError(f"{name} has no accepted signatures.")
    size = len(accepted[0])
    if any(len(sig) != size for sig in accepted):
        raise PanelMonsterStageVariantError(f"{name} signature table size mismatch.")
    cur = bytes(rom_data[off:off + size])
    if cur in accepted:
        return
    if 0x6010 <= off and off + size <= 0x7010 and cur == _fill(0xEA, size):
        return
    expected = " / ".join(sig.hex(" ") for sig in accepted[:3])
    if len(accepted) > 3:
        expected += " / ..."
    raise PanelMonsterStageVariantError(
        f"{name} signature mismatch at file 0x{off:X} CPU ${_cpu(off):04X}: "
        f"got {cur.hex(' ')}, expected {expected}"
    )


def _validate_runtime_loader_signature(rom_data: bytearray) -> None:
    _expect_signature(
        rom_data,
        OFF_M66_LOADER_TAIL,
        "mapper66 loader tail",
        (ORIG_M66_LOADER_TAIL, HOOK_M66_LOADER_TAIL),
    )
    cur = bytes(rom_data[OFF_PRG1_RUNTIME_LOADER:OFF_PRG1_RUNTIME_LOADER + 0x60])
    accepted = (
        _fill(0x00, 0x60),
        stage_ext.RUNTIME_LOADER + _fill(0x00, 0x60 - len(stage_ext.RUNTIME_LOADER)),
        _previous_runtime_loader_slot(),
        _runtime_loader_slot(),
    )
    if cur in accepted:
        return
    expected = " / ".join(sig[:16].hex(" ") for sig in accepted)
    raise PanelMonsterStageVariantError(
        f"Panel Variant PRG1 runtime loader signature mismatch at file "
        f"0x{OFF_PRG1_RUNTIME_LOADER:X}: got {cur[:16].hex(' ')}, expected {expected}"
    )


def _validate_final_split_signatures(
    rom_data: bytearray,
    final_state0_interval_helper: bytes,
) -> None:
    """Verify every final split writer before mutating ROM bytes."""
    _validate_runtime_loader_signature(rom_data)
    panel_bullet_speed_fix.current_state(rom_data)
    v2_speed = panel_monster_v2_split_speed_runtime_blobs()

    _expect_signature(
        rom_data,
        panel_monster_variant.OFF_HOOK_PANEL_FIRE,
        "$A556 Panel fire/property hook site",
        (
            panel_monster_variant.ORIG_PANEL_FIRE,
            panel_monster_variant.HOOK_PANEL_FIRE,
            HOOK_FINAL_PANEL_FIRE,
            ORIG_PANEL_FIRE_WITH_SPARK_PROPERTY,
            HOOK_PREVIOUS_PANEL_FIRE_WITH_SPARK_PROPERTY,
            HOOK_PANEL_FIRE_WITH_SPARK_PROPERTY,
        ),
    )
    _expect_signature(
        rom_data,
        panel_monster_variant.OFF_HOOK_BULLET_MOVE,
        "$AFBB Bullet movement hook site",
        (
            panel_monster_variant.ORIG_BULLET_MOVE_HOOK,
            panel_monster_variant.HOOK_BULLET_MOVE,
            HOOK_FINAL_BULLET_MOVE,
        ),
    )
    _expect_signature(
        rom_data,
        OFF_STATE0_INTERVAL_HOOK,
        "$A575 state0 interval hook site",
        (
            ORIG_STATE0_INTERVAL_HOOK,
            FINAL_HOOK_STATE0_INTERVAL,
        ),
    )
    _expect_signature(
        rom_data,
        panel_monster_variant.OFF_A2CC,
        "$A2CC property dispatch hook site",
        (
            panel_monster_variant.ORIG_A2CC_HEAD,
            panel_monster_variant.HOOK_A2CC,
            panel_monster_variant.HOOK_A2CC_SPARK,
            panel_monster_variant.HOOK_A2CC_SPARK_CURRENT,
            HOOK_A2CC_SPARK_PROPERTY,
        ),
    )
    _expect_signature(
        rom_data,
        panel_monster_variant.OFF_8B05,
        "$8B05 animation dispatch hook site",
        (
            panel_monster_variant.ORIG_8B05_HEAD,
            panel_monster_variant.HOOK_8B05,
            panel_monster_variant.HOOK_8B05_SPARK,
            HOOK_8B05_SPARK_ANIM,
        ),
    )
    _expect_signature(
        rom_data,
        OFF_SPEED_INIT_CALL,
        "$866D speed init hook site",
        (
            ORIG_SPEED_INIT_CALL,
            HOOK_SPEED_INIT_CALL,
        ),
    )

    ai_entry = _word(FINAL_AI_DISPATCH_ENTRIES["entry"])
    panel_ai_entry = _word(CPU_FINAL_SHARED_AI_WRAPPER)
    for off, name in (
        (panel_monster_variant.OFF_AI_DEMON_52_53, "$A34C Panel Monster 2-way borrowed AI"),
        (panel_monster_variant.OFF_AI_DEMON_56_57, "$A34E Panel Monster 2-way borrowed AI"),
        (panel_monster_variant.OFF_AI_DEMON_5A_5B, "$A350 Panel Monster 3-way borrowed AI"),
    ):
        _expect_signature(
            rom_data,
            off,
            name,
            (
                panel_monster_variant.ORIG_AI_DEMON,
                _word(panel_monster_variant.CPU_AI_DEMON_WRAPPER),
                panel_ai_entry,
            ),
        )
    for off, name in (
        (OFF_AI_RANGE_30_33, "$A33C Panel Variant C AI"),
        (OFF_AI_RANGE_34_37, "$A33E Panel Variant C AI"),
        (OFF_AI_RANGE_40_43, "$A344 Panel Variant A AI"),
        (OFF_AI_RANGE_44_47, "$A346 Panel Variant A AI"),
        (OFF_AI_RANGE_48_4B, "$A348 Panel Variant B AI"),
        (OFF_AI_RANGE_4C_4F, "$A34A Panel Variant B AI"),
    ):
        _expect_signature(rom_data, off, name, (_word(0xABF7), ai_entry))

    for off, blob, name, signatures in (
        (
            OFF_FINAL_FIRE_DISPATCH,
            FINAL_FIRE_DISPATCH,
            "Panel Variant final fire dispatch",
            (
                _fill(0xEA, len(FINAL_FIRE_DISPATCH)),
                FINAL_FIRE_DISPATCH,
                panel_monster_variant.CAVE_FIRE_DISPATCH + _fill(0xEA, len(FINAL_FIRE_DISPATCH) - len(panel_monster_variant.CAVE_FIRE_DISPATCH)),
                panel_monster_variant.CAVE_FIRE_DISPATCH + FINAL_FIRE_DISPATCH[len(panel_monster_variant.CAVE_FIRE_DISPATCH):],
                PREVIOUS_FIRE_DISPATCH + PREVIOUS_STAGE_DISPATCH_TAIL + FINAL_FIRE_MARKER_TABLE[:0x07],
            ),
        ),
        (
            OFF_FINAL_AI_DISPATCH_HELPER,
            FINAL_AI_DISPATCH_HELPER,
            "Panel Variant final AI dispatch helper",
            (_fill(0xEA, len(FINAL_AI_DISPATCH_HELPER)), _fill(0x00, len(FINAL_AI_DISPATCH_HELPER))),
        ),
        (
            OFF_FINAL_AI_DISPATCH_PANEL_HELPER,
            FINAL_AI_DISPATCH_PANEL_HELPER,
            "Panel Variant final AI dispatch panel tail",
            (_fill(0xEA, len(FINAL_AI_DISPATCH_PANEL_HELPER)), _fill(0x00, len(FINAL_AI_DISPATCH_PANEL_HELPER))),
        ),
        (
            OFF_FINAL_PARENT_SPEED_GUARD,
            FINAL_PARENT_SPEED_GUARD_WRITE,
            "Panel Variant final parent speed guard",
            (_fill(0xEA, len(FINAL_PARENT_SPEED_GUARD_WRITE)), ORIG_FINAL_PARENT_SPEED_GUARD[:len(FINAL_PARENT_SPEED_GUARD_WRITE)]),
        ),
        (
            OFF_FINAL_PANEL_TYPE_CLASSIFIER,
            FINAL_PANEL_TYPE_CLASSIFIER,
            "Panel Variant final shared Panel type classifier",
            (_fill(0xEA, len(FINAL_PANEL_TYPE_CLASSIFIER)),),
        ),
        (
            OFF_FINAL_PANEL_TYPE_CLASSIFIER_TAIL,
            FINAL_PANEL_TYPE_CLASSIFIER_TAIL,
            "Panel Variant final shared Panel type classifier tail",
            (
                _fill(0xEA, len(FINAL_PANEL_TYPE_CLASSIFIER_TAIL)),
                _fill(0x00, len(FINAL_PANEL_TYPE_CLASSIFIER_TAIL)),
                panel_monster_variant.CAVE_BULLET_HOOK[3:3 + len(FINAL_PANEL_TYPE_CLASSIFIER_TAIL)],
            ),
        ),
        (
            OFF_FINAL_PANEL_ANIM_DIR_HELPER,
            FINAL_PANEL_ANIM_DIR_HELPER,
            "Panel Variant final animation direction helper",
            (
                _fill(0xEA, len(FINAL_PANEL_ANIM_DIR_HELPER)),
            ),
        ),
        (
            OFF_FINAL_FIRE_COMMON,
            FINAL_FIRE_COMMON,
            "Panel Variant final common fire loop",
            (_fill(0xEA, len(FINAL_FIRE_COMMON)), panel_monster_variant.CAVE_FIRE_3WAY[:len(FINAL_FIRE_COMMON)]),
        ),
        (
            OFF_FINAL_STATE0_INTERVAL_HELPER,
            final_state0_interval_helper,
            "Panel Variant final interval helper",
            (
                _fill(0xEA, len(final_state0_interval_helper)),
                spark_ball_variant.CAVE_PROPERTY_HOOK[:len(final_state0_interval_helper)],
            ),
        ),
        (
            OFF_FINAL_GROUP_RAM_OFFSET_HELPER,
            FINAL_GROUP_RAM_OFFSET_HELPER_WRITE,
            "Panel Variant final group RAM offset helper",
            (_fill(0xEA, len(FINAL_GROUP_RAM_OFFSET_HELPER_WRITE)),),
        ),
        (
            OFF_FINAL_ABC_GROUP_OFFSET_HELPER,
            FINAL_ABC_GROUP_OFFSET_HELPER,
            "Panel Variant final A/B/C-only group offset helper",
            (_fill(0xEA, len(FINAL_ABC_GROUP_OFFSET_HELPER)), _fill(0x00, len(FINAL_ABC_GROUP_OFFSET_HELPER)), ORIG_FINAL_ABC_GROUP_OFFSET_HELPER),
        ),
        (
            OFF_FINAL_STATIC_MARKER_HELPER,
            FINAL_STATIC_MARKER_HELPER,
            "Panel Variant final static marker helper",
            (_fill(0xEA, len(FINAL_STATIC_MARKER_HELPER)),),
        ),
        (
            OFF_FINAL_DYNAMIC_SPEED_MARKER_HELPER,
            FINAL_DYNAMIC_SPEED_MARKER_HELPER,
            "Panel Variant final dynamic speed marker helper",
            (
                _fill(0xEA, len(FINAL_DYNAMIC_SPEED_MARKER_HELPER)),
                _fill(0x00, len(FINAL_DYNAMIC_SPEED_MARKER_HELPER)),
                PREVIOUS_DYNAMIC_SPEED_MARKER_HELPER[:len(FINAL_DYNAMIC_SPEED_MARKER_HELPER)],
                PREVIOUS_INLINE_DYNAMIC_SPEED_MARKER_HELPER[:len(FINAL_DYNAMIC_SPEED_MARKER_HELPER)],
            ),
        ),
        (
            OFF_FINAL_PARENT_FIELD_CLEAR_HELPER,
            FINAL_PARENT_FIELD_CLEAR_HELPER,
            "Panel Variant final parent field clear helper",
            (_fill(0xEA, len(FINAL_PARENT_FIELD_CLEAR_HELPER)), ORIG_FINAL_PARENT_FIELD_CLEAR_HELPER),
        ),
        (
            OFF_FINAL_BULLET_SPEED_EXTRA_HELPER,
            v2_speed["tables_and_fast_loop"],
            "Panel Variant final Bullet speed extra-step helper",
            (
                _fill(0xEA, len(v2_speed["tables_and_fast_loop"])),
                _pad(ORIG_FINAL_BULLET_SPEED_EXTRA_HELPER, len(v2_speed["tables_and_fast_loop"]), 0x00),
            ),
        ),
        (
            OFF_FINAL_BULLET_ENTRY_HELPER,
            v2_speed["bullet_entry_helper"],
            "Panel Variant v2 Bullet entry helper",
            (
                _fill(0xEA, len(v2_speed["bullet_entry_helper"])),
                ORIG_FINAL_BULLET_ENTRY_HELPER[:len(v2_speed["bullet_entry_helper"])],
            ),
        ),
        (
            OFF_FINAL_BULLET_ENTRY_TAIL_HELPER,
            v2_speed["bullet_entry_tail_helper"],
            "Panel Variant v2 Bullet entry tail helper",
            (_fill(0xEA, len(v2_speed["bullet_entry_tail_helper"])), ORIG_FINAL_BULLET_ENTRY_TAIL_HELPER[:len(v2_speed["bullet_entry_tail_helper"])]),
        ),
        (
            OFF_FINAL_BULLET_SPEED_APPLY,
            v2_speed["speed_decode"],
            "Panel Variant final Bullet speed apply/table",
            (
                _fill(0xEA, len(v2_speed["speed_decode"])),
            ),
        ),
        (
            OFF_FINAL_SHARED_AI_WRAPPER,
            FINAL_SHARED_AI_WRAPPER,
            "Panel Variant final shared AI wrapper",
            (
                _fill(0xEA, len(FINAL_SHARED_AI_WRAPPER)),
                ORIG_FINAL_SHARED_AI_WRAPPER_SHIFTED,
                PREVIOUS_SHARED_AI_WRAPPER_SHIFTED,
            ),
        ),
        (
            OFF_FINAL_FIRE_MARKER_TABLE,
            FINAL_FIRE_MARKER_TABLE,
            "Panel Variant final fire marker table",
            (
                _fill(0xEA, len(FINAL_FIRE_MARKER_TABLE)),
                _fill(0xEA, len(FINAL_FIRE_MARKER_TABLE)),
                PREVIOUS_STAGE_DISPATCH_HELPER[:len(FINAL_FIRE_MARKER_TABLE)],
            ),
        ),
        (
            OFF_FINAL_BULLET_SPEED_HOOK,
            v2_speed["bullet_speed_hook"],
            "Panel Variant final merged Bullet hook",
            (
                _fill(0xEA, len(v2_speed["bullet_speed_hook"])),
                _pad(panel_monster_variant.CAVE_BULLET_HOOK, len(v2_speed["bullet_speed_hook"])),
            ),
        ),
        (
            spark_ball_variant.OFF_PROPERTY_HOOK,
            FINAL_SPARK_PROPERTY_HOOK,
            "Spark property selector Panel fallback",
            (
                spark_ball_variant.CAVE_PROPERTY_HOOK,
            ),
        ),
        (
            spark_ball_variant.OFF_ANIM_HOOK,
            FINAL_SPARK_ANIM_HOOK,
            "Spark animation selector Panel fallback",
            (
                spark_ball_variant.CAVE_ANIM_HOOK,
            ),
        ),
        (
            OFF_FINAL_STAGE_PROPERTY_HOOK,
            FINAL_STAGE_PROPERTY_HOOK,
            "Panel Variant final property hook",
            (
                _fill(0xEA, len(FINAL_STAGE_PROPERTY_HOOK)),
                panel_monster_variant.CAVE_PROPERTY_HOOK[:len(FINAL_STAGE_PROPERTY_HOOK)],
            ),
        ),
        (
            OFF_FINAL_STAGE_ANIM_HOOK,
            FINAL_STAGE_ANIM_HOOK,
            "Panel Variant final animation hook",
            (
                _fill(0xEA, len(FINAL_STAGE_ANIM_HOOK)),
                panel_monster_variant.CAVE_ANIM_HOOK[:len(FINAL_STAGE_ANIM_HOOK)],
            ),
        ),
    ):
        _expect_signature(rom_data, off, name, (*signatures, blob))


def apply_panel_monster_v2_runtime(
    rom_data: bytearray,
    levels: list = None,
    common_settings: dict | None = None,
) -> list[str]:
    """Apply the current Panel Monster v2 runtime."""
    if rom_data is None:
        raise PanelMonsterStageVariantError("ROM is missing.")
    v2_speed = panel_monster_v2_split_speed_runtime_blobs()
    min_len = max(
        OFF_FINAL_BULLET_SPEED_APPLY + len(v2_speed["speed_decode"]),
        OFF_FINAL_BULLET_SPEED_EXTRA_HELPER + len(v2_speed["tables_and_fast_loop"]),
        OFF_FINAL_BULLET_ENTRY_HELPER + len(v2_speed["bullet_entry_helper"]),
        OFF_FINAL_BULLET_ENTRY_TAIL_HELPER + len(v2_speed["bullet_entry_tail_helper"]),
        OFF_FINAL_AI_DISPATCH_HELPER + len(FINAL_AI_DISPATCH_HELPER),
        OFF_FINAL_AI_DISPATCH_PANEL_HELPER + len(FINAL_AI_DISPATCH_PANEL_HELPER),
        OFF_FINAL_PARENT_FIELD_CLEAR_HELPER + len(FINAL_PARENT_FIELD_CLEAR_HELPER),
        OFF_FINAL_ABC_GROUP_OFFSET_HELPER + len(FINAL_ABC_GROUP_OFFSET_HELPER),
        OFF_FINAL_PARENT_SPEED_GUARD + len(FINAL_PARENT_SPEED_GUARD_WRITE),
        OFF_FINAL_GROUP_RAM_OFFSET_HELPER + len(FINAL_GROUP_RAM_OFFSET_HELPER_WRITE),
        OFF_FINAL_SHARED_AI_WRAPPER + len(FINAL_SHARED_AI_WRAPPER),
        OFF_FINAL_FIRE_MARKER_TABLE + len(FINAL_FIRE_MARKER_TABLE),
        OFF_FINAL_PANEL_ANIM_DIR_HELPER + len(FINAL_PANEL_ANIM_DIR_HELPER),
        SETTINGS_TABLE_END,
        OFF_FINAL_STAGE_ANIM_HOOK + len(FINAL_STAGE_ANIM_HOOK),
    )
    if len(rom_data) < min_len:
        raise PanelMonsterStageVariantError("ROM is too short for Panel Monster v2 runtime.")

    final_state0_interval_helper = _final_state0_interval_helper_for_rom(rom_data)
    _validate_final_split_signatures(rom_data, final_state0_interval_helper)
    _validate_pmv2_speed_core_runtime_contract()
    _validate_pmv2_settings_runtime_contract()
    _validate_pmv2_fire_marker_runtime_contract()
    _validate_pmv2_parent_runtime_contract()
    _validate_pmv2_classifier_runtime_contract()

    changed: list[str] = []
    if patch_settings_table(rom_data, common_settings):
        changed.append("Panel Variant PRG0 settings table")
    changed.extend(apply_runtime_loader(rom_data))

    _write_blob(rom_data, panel_monster_variant.OFF_HOOK_PANEL_FIRE, HOOK_FINAL_PANEL_FIRE, changed, "$A556 Panel Variant fire hook")
    _write_blob(rom_data, panel_monster_variant.OFF_HOOK_BULLET_MOVE, HOOK_FINAL_BULLET_MOVE, changed, "$AFBB Panel Variant Bullet hook")
    _write_blob(rom_data, OFF_STATE0_INTERVAL_HOOK, FINAL_HOOK_STATE0_INTERVAL, changed, "$A575 Panel Variant final interval hook")
    _write_blob(rom_data, panel_monster_variant.OFF_A2CC, HOOK_A2CC_SPARK_PROPERTY, changed, "$A2CC Spark/Panel property dispatch")
    _write_blob(rom_data, panel_monster_variant.OFF_8B05, HOOK_8B05_SPARK_ANIM, changed, "$8B05 Spark/Panel animation dispatch")
    cur_speed = bytes(rom_data[OFF_SPEED_INIT_CALL:OFF_SPEED_INIT_CALL + len(ORIG_SPEED_INIT_CALL)])
    if cur_speed not in (
        ORIG_SPEED_INIT_CALL,
        HOOK_SPEED_INIT_CALL,
    ):
        raise PanelMonsterStageVariantError(
            f"$866D speed init call signature mismatch: got {cur_speed.hex(' ')}"
        )
    _write_blob(rom_data, OFF_SPEED_INIT_CALL, HOOK_SPEED_INIT_CALL, changed, "$866D Panel Variant parent speed guard hook")

    ai_entry = _word(FINAL_AI_DISPATCH_ENTRIES["entry"])
    panel_ai_entry = _word(CPU_FINAL_SHARED_AI_WRAPPER)
    for off, name in (
        (panel_monster_variant.OFF_AI_DEMON_52_53, "$A34C Panel Monster 2-way borrowed AI"),
        (panel_monster_variant.OFF_AI_DEMON_56_57, "$A34E Panel Monster 2-way borrowed AI"),
        (panel_monster_variant.OFF_AI_DEMON_5A_5B, "$A350 Panel Monster 3-way borrowed AI"),
    ):
        _write_blob(rom_data, off, panel_ai_entry, changed, name)
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
        (OFF_FINAL_FIRE_DISPATCH, FINAL_FIRE_DISPATCH, "Panel Variant final fire dispatch"),
        (OFF_FINAL_AI_DISPATCH_HELPER, FINAL_AI_DISPATCH_HELPER, "Panel Variant final AI dispatch helper"),
        (OFF_FINAL_AI_DISPATCH_PANEL_HELPER, FINAL_AI_DISPATCH_PANEL_HELPER, "Panel Variant final AI dispatch panel tail"),
        (OFF_FINAL_PARENT_SPEED_GUARD, FINAL_PARENT_SPEED_GUARD_WRITE, "Panel Variant final parent speed guard"),
        (OFF_FINAL_PANEL_TYPE_CLASSIFIER, FINAL_PANEL_TYPE_CLASSIFIER, "Panel Variant final shared Panel type classifier"),
        (OFF_FINAL_PANEL_TYPE_CLASSIFIER_TAIL, FINAL_PANEL_TYPE_CLASSIFIER_TAIL, "Panel Variant final shared Panel type classifier tail"),
        (OFF_FINAL_PANEL_ANIM_DIR_HELPER, FINAL_PANEL_ANIM_DIR_HELPER, "Panel Variant final animation direction helper"),
        (OFF_FINAL_FIRE_COMMON, FINAL_FIRE_COMMON, "Panel Variant final common fire loop"),
        (OFF_FINAL_STATE0_INTERVAL_HELPER, final_state0_interval_helper, "Panel Variant final interval helper"),
        (OFF_FINAL_GROUP_RAM_OFFSET_HELPER, FINAL_GROUP_RAM_OFFSET_HELPER_WRITE, "Panel Variant final group RAM offset helper"),
        (OFF_FINAL_ABC_GROUP_OFFSET_HELPER, FINAL_ABC_GROUP_OFFSET_HELPER, "Panel Variant final A/B/C-only group offset helper"),
        (OFF_FINAL_STATIC_MARKER_HELPER, FINAL_STATIC_MARKER_HELPER, "Panel Variant final static marker helper"),
        (OFF_FINAL_DYNAMIC_SPEED_MARKER_HELPER, FINAL_DYNAMIC_SPEED_MARKER_HELPER, "Panel Variant final dynamic speed marker helper"),
        (OFF_FINAL_PARENT_FIELD_CLEAR_HELPER, FINAL_PARENT_FIELD_CLEAR_HELPER, "Panel Variant final parent field clear helper"),
        (OFF_FINAL_BULLET_SPEED_EXTRA_HELPER, v2_speed["tables_and_fast_loop"], "Panel Variant v2 Bullet speed tables/fast loop"),
        (OFF_FINAL_BULLET_ENTRY_HELPER, v2_speed["bullet_entry_helper"], "Panel Variant v2 Bullet entry helper"),
        (OFF_FINAL_BULLET_ENTRY_TAIL_HELPER, v2_speed["bullet_entry_tail_helper"], "Panel Variant v2 Bullet entry tail helper"),
        (OFF_FINAL_BULLET_SPEED_APPLY, v2_speed["speed_decode"], "Panel Variant v2 Bullet speed decode"),
        (OFF_FINAL_SHARED_AI_WRAPPER, FINAL_SHARED_AI_WRAPPER, "Panel Variant final shared AI wrapper"),
        (OFF_FINAL_FIRE_MARKER_TABLE, FINAL_FIRE_MARKER_TABLE, "Panel Variant final fire marker table"),
        (OFF_FINAL_BULLET_SPEED_HOOK, v2_speed["bullet_speed_hook"], "Panel Variant v2 Bullet speed hook"),
        (spark_ball_variant.OFF_PROPERTY_HOOK, FINAL_SPARK_PROPERTY_HOOK, "Spark property selector Panel fallback"),
        (spark_ball_variant.OFF_ANIM_HOOK, FINAL_SPARK_ANIM_HOOK, "Spark animation selector Panel fallback"),
        (OFF_FINAL_STAGE_PROPERTY_HOOK, FINAL_STAGE_PROPERTY_HOOK, "Panel Variant final property hook"),
        (OFF_FINAL_STAGE_ANIM_HOOK, FINAL_STAGE_ANIM_HOOK, "Panel Variant final animation hook"),
    ):
        _write_blob(rom_data, off, blob, changed, name)
    speed_changes = panel_bullet_speed_fix.apply(
        rom_data,
        True,
        panel_bullet_speed_fix.FAST_VALUE,
    )
    if speed_changes:
        changed.append("Panel Variant normal Panel Bullet symmetry fix")
    return changed


@dataclass(frozen=True)
class PanelMonsterV2Blob:
    """Placement-independent Panel Monster v2 runtime block.

    This is a build-time planning artifact.  It is intentionally not wired to
    ROM writes, save paths, or concrete PRG0 placement.
    """

    base_cpu: int
    data: bytes
    entries: dict[str, int]
    sizes: dict[str, int]
    external_targets: dict[str, int]
    notes: dict[str, str]


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


def _build_pmv2_speed_decode(
    velocity_table_cpu: int,
    extra_count_table_cpu: int,
) -> bytes:
    """Decode `$88-$8B` speed markers through one shared v2 route."""
    a = _Asm()
    a.b(0xA2, 0x00)                    # default extra count = 0
    a.b(0xA0, 0x07, 0xB1, 0x2C)        # marker = child sub[7]
    a.b(0xC9, DYNAMIC_SPEED_MARKER_BASE)
    a.branch(0x90, "rts")
    a.b(0xC9, DYNAMIC_SPEED_MARKER_END)
    a.branch(0xB0, "rts")
    a.b(0x38, 0xE9, DYNAMIC_SPEED_MARKER_BASE, 0x48)  # preset index 0..3
    a.b(0x0A, 0xAA)                    # X = preset * 2 for velocity table
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0x03)
    a.b(0xA0, 0x05, 0xC9, 0x02)
    a.branch(0xB0, "vertical")
    a.b(0xA0, 0x08, 0x4A)
    a.branch(0x90, "store_velocity")
    a.branch(0xB0, "left_up")
    a.label("vertical")
    a.branch(0xF0, "left_up_y")
    a.branch(0xD0, "store_velocity")
    a.label("left_up")
    a.label("left_up_y")
    a.b(0xE8)
    a.label("store_velocity")
    a.b(0xBD, 0xFF, 0xFF, 0x91, 0x2E)  # write velocity
    a.b(0x68, 0xAA)                    # X = preset index
    a.b(0xBD, 0xFE, 0xFF, 0xAA)        # X = extra count
    a.label("rts")
    a.b(0x60)
    blob = bytearray(a.finish())
    velocity_refs = 0
    extra_refs = 0
    for i in range(len(blob) - 2):
        if blob[i] == 0xBD and blob[i + 1:i + 3] == bytes((0xFF, 0xFF)):
            blob[i + 1:i + 3] = _word(velocity_table_cpu)
            velocity_refs += 1
        elif blob[i] == 0xBD and blob[i + 1:i + 3] == bytes((0xFE, 0xFF)):
            blob[i + 1:i + 3] = _word(extra_count_table_cpu)
            extra_refs += 1
    if velocity_refs != 1 or extra_refs != 1:
        raise PanelMonsterStageVariantError("pmv2 speed decode placeholder mismatch")
    return bytes(blob)


def _build_pmv2_bullet_step_loop(cpu_base: int) -> bytes:
    """Build the shared v2 fast-Bullet loop."""
    a = _Asm()
    a.b(0xE0, 0x00)
    a.branch(0xF0, "rts")
    a.label("loop")
    a.b(0x8A, 0x48)
    substep_cpu = (int(cpu_base) + 0xFFFF) & 0xFFFF
    substep_call_at = len(a.code)
    a.jsr(substep_cpu)
    a.jsr(0xAC39)
    a.b(0xA5, 0x07)
    a.branch(0xD0, "collision")
    a.b(0x68, 0xAA, 0xCA)
    a.branch(0xD0, "loop")
    a.label("rts")
    a.b(0x60)
    a.label("collision")
    a.b(0x68, 0x60)
    a.label("substep")
    a.b(0xA0, 0x03, 0xB1, 0x2E, 0x29, 0x03, 0xC9, 0x02)
    a.branch(0xB0, "vertical")
    a.b(0xA0, 0x08)
    a.branch(0xD0, "move")
    a.label("vertical")
    a.b(0xA0, 0x05)
    a.label("move")
    a.b(0xB1, 0x2E, 0x0A, 0x0A, 0xA2, 0x00)
    a.branch(0x90, "positive")
    a.b(0xCA)
    a.label("positive")
    a.b(0x86, 0x0A, 0x2A, 0x26, 0x0A, 0x18, 0xC8, 0x71, 0x2E, 0x91, 0x2E)
    a.b(0xC8, 0xA5, 0x0A, 0x71, 0x2E, 0x91, 0x2E, 0x60)
    blob = bytearray(a.finish())
    substep_cpu = (int(cpu_base) + a.labels["substep"]) & 0xFFFF
    blob[substep_call_at + 1:substep_call_at + 3] = _word(substep_cpu)
    return bytes(blob)


def _build_pmv2_bullet_entry_tail_helper(speed_decode_cpu: int, bullet_step_loop_cpu: int) -> bytes:
    """Build the short out-of-line tail for the v2 Bullet entry helper."""
    a = _Asm()
    a.b(0xB1, 0x2E, 0x38, 0xE9, 0x01, 0x91, 0x2E)
    a.b(0x68, 0xAA, 0x68, 0x60)
    a.b(0xB1, 0x2E, 0x18, 0x69, 0x01, 0x91, 0x2E)
    a.b(0x68, 0xAA, 0x68, 0x60)
    a.jsr(speed_decode_cpu)
    a.jsr(bullet_step_loop_cpu)
    a.b(0x68, 0xAA, 0x68, 0x60)
    return a.finish()


def _build_pmv2_bullet_entry_helper(minus_tail_cpu: int, plus_tail_cpu: int, speed_tail_cpu: int) -> bytes:
    """Build the v2 Bullet state2 body for spread and speed markers."""
    a = _Asm()
    a.jsr(0xB201)
    a.b(0x48, 0xC9, 0x02)
    a.branch(0xD0, "done")
    a.b(0x8A, 0x48)                   # Preserve caller-visible X.
    a.b(0xA0, 0x07, 0xB1, 0x2C)        # child sub[7] marker
    a.branch(0x10, "restore_x")
    a.b(0xC9, DYNAMIC_SPEED_MARKER_BASE)
    a.branch(0xB0, "speed")
    a.b(0x29, 0x7F, 0xAA)
    a.branch(0xF0, "restore_x")
    a.b(0xE0, 0x03)
    a.branch(0x90, "axis")
    a.b(0xA0, 0x01, 0xB1, 0x2C, 0x29, 0x01)
    a.branch(0xD0, "restore_x")
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
    a.jmp(minus_tail_cpu)
    a.label("done")
    a.b(0x68, 0x60)
    a.label("plus")
    a.jmp(plus_tail_cpu)
    a.label("speed")
    a.jmp(speed_tail_cpu)
    a.label("restore_x")
    a.b(0x68, 0xAA)
    a.b(0x68, 0x60)
    return a.finish()


def _build_pmv2_bullet_speed_hook(entry_helper_cpu: int) -> bytes:
    """Build the small v2 Bullet state2 entry kept in the original slot."""
    return bytes.fromhex("4c") + _word(entry_helper_cpu)


def build_panel_monster_v2_speed_core_blob(base_cpu: int = 0x8000) -> PanelMonsterV2Blob:
    """Build the first Panel Monster v2 planning blob without ROM writes."""
    base_cpu = int(base_cpu) & 0xFFFF
    out = bytearray()
    entries: dict[str, int] = {}
    sizes: dict[str, int] = {}
    _append_blob_section(out, entries, sizes, base_cpu, "speed_velocity_table", SPEED_PRESET_RUNTIME_TABLE)
    _append_blob_section(
        out,
        entries,
        sizes,
        base_cpu,
        "speed_extra_count_table",
        bytes((
            SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_QUARTER]["extra_steps"],
            SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_HALF]["extra_steps"],
            SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_FAST_2X]["extra_steps"],
            SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_FAST_3X]["extra_steps"],
        )),
    )
    _append_blob_section(
        out,
        entries,
        sizes,
        base_cpu,
        "speed_decode",
        _build_pmv2_speed_decode(
            entries["speed_velocity_table"],
            entries["speed_extra_count_table"],
        ),
    )
    loop_base = (base_cpu + len(out)) & 0xFFFF
    _append_blob_section(
        out,
        entries,
        sizes,
        base_cpu,
        "bullet_step_loop",
        _build_pmv2_bullet_step_loop(loop_base),
    )
    _append_blob_section(
        out,
        entries,
        sizes,
        base_cpu,
        "bullet_entry_tail_helper",
        _build_pmv2_bullet_entry_tail_helper(
            entries["speed_decode"],
            entries["bullet_step_loop"],
        ),
    )
    _append_blob_section(
        out,
        entries,
        sizes,
        base_cpu,
        "bullet_entry_helper",
        _build_pmv2_bullet_entry_helper(
            entries["bullet_entry_tail_helper"],
            (entries["bullet_entry_tail_helper"] + 0x0B) & 0xFFFF,
            (entries["bullet_entry_tail_helper"] + 0x16) & 0xFFFF,
        ),
    )
    _append_blob_section(
        out,
        entries,
        sizes,
        base_cpu,
        "bullet_speed_hook",
        _build_pmv2_bullet_speed_hook(entries["bullet_entry_helper"]),
    )
    return PanelMonsterV2Blob(
        base_cpu=base_cpu,
        data=bytes(out),
        entries=entries,
        sizes=sizes,
        external_targets={
            "stock_bullet_collision_sampler": 0xAC39,
        },
        notes={
            "scope": "Static v2 speed core and Bullet entry only; no ROM writer uses this blob.",
            "entry_policy": "Keep normal, 2-way/3-way, and A/B/C entries separate if that is smaller.",
            "shared_policy": "Share Bullet marker decode and 2x/3x substep loop only.",
        },
    )


PANEL_MONSTER_V2_SPEED_CORE_BLOB = build_panel_monster_v2_speed_core_blob()


def _v2_split_speed_reserved_sizes() -> dict[str, int]:
    blobs = panel_monster_v2_split_speed_runtime_blobs()
    return {
        "speed_decode": len(blobs["speed_decode"]),
        "tables_and_fast_loop": len(blobs["tables_and_fast_loop"]),
        "bullet_speed_hook": len(blobs["bullet_speed_hook"]),
        "bullet_entry_helper": len(blobs["bullet_entry_helper"]),
        "bullet_entry_tail_helper": len(blobs["bullet_entry_tail_helper"]),
    }


def panel_monster_v2_speed_core_contract() -> dict[str, object]:
    """Return the current static contract for the v2 speed-core block."""
    blob = PANEL_MONSTER_V2_SPEED_CORE_BLOB
    split_speed_runtime_size = sum(_v2_split_speed_reserved_sizes().values())
    return {
        "base_cpu": blob.base_cpu,
        "total_size": len(blob.data),
        "entries": dict(blob.entries),
        "sizes": dict(blob.sizes),
        "external_targets": dict(blob.external_targets),
        "notes": dict(blob.notes),
        "extra_counts": {
            "1/4": SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_QUARTER]["extra_steps"],
            "1/2": SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_HALF]["extra_steps"],
            "2x": SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_FAST_2X]["extra_steps"],
            "3x": SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_FAST_3X]["extra_steps"],
        },
        "split_speed_runtime_size": split_speed_runtime_size,
        "judgement": "v2 split speed runtime is the normal save path",
    }


def panel_monster_v2_split_speed_placement_report() -> dict[str, object]:
    """Return the concrete split placement for the v2 speed runtime."""
    blob = PANEL_MONSTER_V2_SPEED_CORE_BLOB
    section_sizes = dict(blob.sizes)
    decode_size = section_sizes["speed_decode"]
    table_loop_size = (
        section_sizes["speed_velocity_table"]
        + section_sizes["speed_extra_count_table"]
        + section_sizes["bullet_step_loop"]
    )
    hook_size = section_sizes["bullet_speed_hook"]
    entry_helper_size = section_sizes["bullet_entry_helper"]
    entry_tail_helper_size = section_sizes["bullet_entry_tail_helper"]
    rows = [
        {
            "name": "v2_speed_decode",
            "file_start": OFF_FINAL_BULLET_SPEED_APPLY,
            "cpu_start": CPU_FINAL_BULLET_SPEED_APPLY,
            "size": decode_size,
            "capacity": 0x3A,
        },
        {
            "name": "v2_speed_tables_and_fast_loop",
            "file_start": OFF_FINAL_BULLET_SPEED_EXTRA_HELPER,
            "cpu_start": CPU_FINAL_BULLET_SPEED_EXTRA_HELPER,
            "size": table_loop_size,
            "capacity": 0x79,
        },
        {
            "name": "v2_bullet_entry_helper",
            "file_start": OFF_FINAL_BULLET_ENTRY_HELPER,
            "cpu_start": CPU_FINAL_BULLET_ENTRY_HELPER,
            "size": entry_helper_size,
            "capacity": FINAL_BULLET_ENTRY_HELPER_CAPACITY,
        },
        {
            "name": "v2_bullet_entry_tail_helper",
            "file_start": OFF_FINAL_BULLET_ENTRY_TAIL_HELPER,
            "cpu_start": CPU_FINAL_BULLET_ENTRY_TAIL_HELPER,
            "size": entry_tail_helper_size,
            "capacity": FINAL_BULLET_ENTRY_TAIL_HELPER_CAPACITY,
        },
        {
            "name": "v2_bullet_speed_hook",
            "file_start": OFF_FINAL_BULLET_SPEED_HOOK,
            "cpu_start": CPU_FINAL_BULLET_SPEED_HOOK,
            "size": hook_size,
            "capacity": FINAL_BULLET_SPEED_HOOK_CAPACITY,
        },
    ]
    for row in rows:
        row["file_end"] = row["file_start"] + row["size"] - 1
        row["cpu_end"] = (row["cpu_start"] + row["size"] - 1) & 0xFFFF
        row["remaining"] = row["capacity"] - row["size"]
    return {
        "pieces": rows,
        "fits": all(row["remaining"] >= 0 for row in rows),
        "total_size": decode_size + table_loop_size + entry_helper_size + entry_tail_helper_size + hook_size,
        "total_capacity": sum(row["capacity"] for row in rows),
        "static_blob_size": len(blob.data),
        "layout_rule": "Put the Panel Variant v2 speed runtime in the new PRG0 cleanup block starting at $E602; keep the $AFBB hook pointing at the new $E737 entry.",
    }


def panel_monster_v2_split_speed_runtime_blobs() -> dict[str, bytes]:
    """Build the v2 speed runtime bytes for the concrete split placement."""
    velocity_table_cpu = CPU_FINAL_BULLET_SPEED_EXTRA_HELPER
    extra_count_table_cpu = velocity_table_cpu + len(SPEED_PRESET_RUNTIME_TABLE)
    loop_cpu = extra_count_table_cpu + 4
    tables_and_fast_loop = (
        SPEED_PRESET_RUNTIME_TABLE
        + bytes((
            SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_QUARTER]["extra_steps"],
            SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_HALF]["extra_steps"],
            SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_FAST_2X]["extra_steps"],
            SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_FAST_3X]["extra_steps"],
        ))
        + _build_pmv2_bullet_step_loop(loop_cpu)
    )
    return {
        "speed_decode": _build_pmv2_speed_decode(velocity_table_cpu, extra_count_table_cpu),
        "tables_and_fast_loop": tables_and_fast_loop,
        "bullet_entry_tail_helper": _build_pmv2_bullet_entry_tail_helper(CPU_FINAL_BULLET_SPEED_APPLY, loop_cpu),
        "bullet_entry_helper": _build_pmv2_bullet_entry_helper(
            CPU_FINAL_BULLET_ENTRY_TAIL_HELPER,
            CPU_FINAL_BULLET_ENTRY_TAIL_HELPER + 0x0B,
            CPU_FINAL_BULLET_ENTRY_TAIL_HELPER + 0x16,
        ),
        "bullet_speed_hook": _build_pmv2_bullet_speed_hook(CPU_FINAL_BULLET_ENTRY_HELPER),
    }


def panel_monster_v2_split_speed_save_report(rom_data: bytes | bytearray) -> dict[str, object]:
    """Report whether the split v2 speed runtime is present in saved ROM data."""
    if rom_data is None:
        raise PanelMonsterStageVariantError("ROM is missing.")
    blobs = panel_monster_v2_split_speed_runtime_blobs()
    sections = {
        "speed_decode": (
            OFF_FINAL_BULLET_SPEED_APPLY,
            blobs["speed_decode"],
        ),
        "tables_and_fast_loop": (
            OFF_FINAL_BULLET_SPEED_EXTRA_HELPER,
            blobs["tables_and_fast_loop"],
        ),
        "bullet_entry_helper": (
            OFF_FINAL_BULLET_ENTRY_HELPER,
            blobs["bullet_entry_helper"],
        ),
        "bullet_entry_tail_helper": (
            OFF_FINAL_BULLET_ENTRY_TAIL_HELPER,
            blobs["bullet_entry_tail_helper"],
        ),
        "bullet_speed_hook": (
            OFF_FINAL_BULLET_SPEED_HOOK,
            blobs["bullet_speed_hook"],
        ),
    }
    written = {
        name: bytes(rom_data[off:off + len(blob)]) == blob
        for name, (off, blob) in sections.items()
    }
    return {
        "placement": panel_monster_v2_split_speed_placement_report(),
        "written": written,
        "all_written": all(written.values()),
    }


def panel_monster_v2_runtime_save_report(
    rom_data: bytes | bytearray,
    common_settings: dict | None = None,
) -> dict[str, object]:
    """Report the current Panel Monster v2 runtime state in one place."""
    if rom_data is None:
        raise PanelMonsterStageVariantError("ROM is missing.")
    guard_results = {}
    for name, validator in (
        ("speed", _validate_pmv2_speed_core_runtime_contract),
        ("settings_table", _validate_pmv2_settings_runtime_contract),
        ("fire_marker", _validate_pmv2_fire_marker_runtime_contract),
        ("parent_cleanup", _validate_pmv2_parent_runtime_contract),
        ("classifier", _validate_pmv2_classifier_runtime_contract),
    ):
        try:
            validator()
        except PanelMonsterStageVariantError as exc:
            guard_results[name] = str(exc)
        else:
            guard_results[name] = True
    speed_report = panel_monster_v2_split_speed_save_report(rom_data)
    settings_report = panel_monster_v2_settings_save_report(rom_data, common_settings)
    placement_report = panel_variant_split_placement_report()
    reserved_report = panel_monster_v2_reserved_span_report()
    coverage_report = _placement_reserved_coverage_report(placement_report, reserved_report)
    return {
        "apply_path": apply_panel_monster_v2_runtime.__name__,
        "guards": guard_results,
        "guards_ok": all(result is True for result in guard_results.values()),
        "placement_ok": placement_report["overlap_free"],
        "reserved_ok": reserved_report["overlap_free"],
        "reserved_covers_placement": coverage_report["all_placement_reserved"],
        "speed_all_written": speed_report["all_written"],
        "settings_all_written": settings_report["all_written"],
        "all_written": speed_report["all_written"] and settings_report["all_written"],
        "speed": speed_report,
        "settings": settings_report,
        "placement": placement_report,
        "reserved": reserved_report,
        "reserved_coverage": coverage_report,
    }


def _validate_pmv2_speed_core_runtime_contract() -> None:
    """Guard the normal ROM save path against a broken Panel Monster speed core."""
    extra_counts = {
        SPEED_PRESET_QUARTER: SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_QUARTER]["extra_steps"],
        SPEED_PRESET_HALF: SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_HALF]["extra_steps"],
        SPEED_PRESET_FAST_2X: SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_FAST_2X]["extra_steps"],
        SPEED_PRESET_FAST_3X: SPEED_PRESET_TABLE_VALUES[SPEED_PRESET_FAST_3X]["extra_steps"],
    }
    expected_counts = {
        SPEED_PRESET_QUARTER: 0,
        SPEED_PRESET_HALF: 0,
        SPEED_PRESET_FAST_2X: 1,
        SPEED_PRESET_FAST_3X: 2,
    }
    if extra_counts != expected_counts:
        raise PanelMonsterStageVariantError(
            f"Panel Monster v2 speed extra-step contract mismatch: {extra_counts!r}"
        )

    split_blobs = panel_monster_v2_split_speed_runtime_blobs()
    speed_decode = split_blobs["speed_decode"]
    fast_loop = split_blobs["tables_and_fast_loop"]
    entry_helper = split_blobs["bullet_entry_helper"]
    entry_tail_helper = split_blobs["bullet_entry_tail_helper"]
    loop_cpu = CPU_FINAL_BULLET_SPEED_EXTRA_HELPER + len(SPEED_PRESET_RUNTIME_TABLE) + 4
    if tuple(DYNAMIC_SPEED_MARKERS) != tuple(range(DYNAMIC_SPEED_MARKER_BASE, DYNAMIC_SPEED_MARKER_END)):
        raise PanelMonsterStageVariantError(
            f"Panel Monster v2 dynamic speed marker range mismatch: {DYNAMIC_SPEED_MARKERS!r}"
        )
    if OFF_FINAL_BULLET_ENTRY_HELPER + len(entry_helper) > OFF_FINAL_BULLET_ENTRY_HELPER_END:
        raise PanelMonsterStageVariantError(
            "Panel Monster v2 Bullet entry helper overlaps the Spark Ball wrapper."
        )
    if OFF_FINAL_BULLET_ENTRY_TAIL_HELPER + len(entry_tail_helper) > OFF_FINAL_BULLET_SPEED_APPLY:
        raise PanelMonsterStageVariantError(
            "Panel Monster v2 Bullet entry tail helper overlaps the speed decode helper."
        )
    required_patterns = {
        "$88 lower bound": (speed_decode, bytes((0xC9, DYNAMIC_SPEED_MARKER_BASE))),
        "$8C upper bound": (speed_decode, bytes((0xC9, DYNAMIC_SPEED_MARKER_END))),
        "$88 marker index decode": (speed_decode, bytes((0x38, 0xE9, DYNAMIC_SPEED_MARKER_BASE))),
        "$AC39 collision sample": (fast_loop, bytes((0x20, 0x39, 0xAC))),
        "bullet hook jumps to entry helper": (
            split_blobs["bullet_speed_hook"],
            bytes.fromhex("4c") + _word(CPU_FINAL_BULLET_ENTRY_HELPER),
        ),
        "$80-$84 spread marker path": (
            entry_helper,
            bytes((0xC9, DYNAMIC_SPEED_MARKER_BASE, 0xB0)),
        ),
        "spread minus tail jump": (
            entry_helper,
            bytes.fromhex("4c") + _word(CPU_FINAL_BULLET_ENTRY_TAIL_HELPER),
        ),
        "spread plus tail jump": (
            entry_helper,
            bytes.fromhex("4c") + _word(CPU_FINAL_BULLET_ENTRY_TAIL_HELPER + 0x0B),
        ),
        "speed tail jump": (
            entry_helper,
            bytes.fromhex("4c") + _word(CPU_FINAL_BULLET_ENTRY_TAIL_HELPER + 0x16),
        ),
        "spread axis adjust": (
            entry_tail_helper,
            bytes((0xB1, 0x2E, 0x38, 0xE9, 0x01, 0x91, 0x2E)),
        ),
        "speed tail decode call": (
            entry_tail_helper,
            bytes.fromhex("20") + _word(CPU_FINAL_BULLET_SPEED_APPLY),
        ),
        "speed tail fast-loop call": (
            entry_tail_helper,
            bytes.fromhex("20") + _word(loop_cpu),
        ),
    }
    for name, (blob, pattern) in required_patterns.items():
        if pattern not in blob:
            raise PanelMonsterStageVariantError(
                f"Panel Monster v2 speed core is missing {name} pattern."
            )
    if bytes((0xC9, 0x8B, 0xB0)) in speed_decode:
        raise PanelMonsterStageVariantError(
            "Panel Monster v2 speed core rejects 3x before the shared extra-step loop."
        )

    contract = panel_monster_v2_speed_core_contract()
    if contract["extra_counts"] != {"1/4": 0, "1/2": 0, "2x": 1, "3x": 2}:
        raise PanelMonsterStageVariantError(
            f"Panel Monster v2 static speed contract mismatch: {contract['extra_counts']!r}"
        )
    required_sections = {
        "speed_velocity_table",
        "speed_extra_count_table",
        "speed_decode",
        "bullet_step_loop",
        "bullet_entry_tail_helper",
        "bullet_entry_helper",
        "bullet_speed_hook",
    }
    if set(contract["sizes"]) != required_sections:
        raise PanelMonsterStageVariantError(
            f"Panel Monster v2 static speed sections mismatch: {sorted(contract['sizes'])!r}"
        )
    placement = panel_monster_v2_split_speed_placement_report()
    if not placement["fits"]:
        raise PanelMonsterStageVariantError(
            f"Panel Monster v2 split speed placement does not fit: {placement!r}"
        )
    forbidden_fast_loop_patterns = {
        "stock impact path $AFDF": bytes((0x4C, 0xDF, 0xAF)),
        "stock impact helper $B016": bytes((0x20, 0x16, 0xB0)),
    }
    for name, pattern in forbidden_fast_loop_patterns.items():
        if pattern in fast_loop:
            raise PanelMonsterStageVariantError(
                f"Panel Monster v2 fast loop must not enter {name}."
            )
    required_fast_loop_patterns = {
        "$AC39 collision sample": bytes((0x20, 0x39, 0xAC)),
        "collision-return tail": bytes((0x68, 0x60)),
    }
    for name, pattern in required_fast_loop_patterns.items():
        if pattern not in fast_loop:
            raise PanelMonsterStageVariantError(
                f"Panel Monster v2 fast loop is missing {name}."
            )


def _validate_pmv2_settings_runtime_contract() -> None:
    """Guard the normal ROM save path against a widened A/B/C settings contract."""
    if SETTINGS_TABLE_LENGTH != 6:
        raise PanelMonsterStageVariantError(
            "Panel Monster v2 settings table must stay a 6-byte PRG0 image."
        )
    loader = _runtime_loader_slot()
    if bytes.fromhex("99 40 07") in loader:
        raise PanelMonsterStageVariantError(
            "Panel Monster v2 runtime loader must not copy settings to $0740-$0745."
        )
    settings_lo = CPU_SETTINGS_TABLE & 0xFF
    settings_hi = CPU_SETTINGS_TABLE >> 8
    for name, blob, pattern in (
        (
            "state0 interval helper",
            FINAL_STATE0_INTERVAL_HELPER,
            bytes((0xDD, (CPU_SETTINGS_TABLE + 1) & 0xFF, (CPU_SETTINGS_TABLE + 1) >> 8)),
        ),
        (
            "dynamic speed marker helper",
            FINAL_DYNAMIC_SPEED_MARKER_HELPER,
            bytes((0xBD, settings_lo, settings_hi)),
        ),
    ):
        if pattern not in blob:
            raise PanelMonsterStageVariantError(
                f"Panel Monster v2 {name} no longer reads the PRG0 settings table."
            )


def _validate_pmv2_fire_marker_runtime_contract() -> None:
    """Guard the Panel Monster fire path marker contract."""
    expected_marker_table = bytes((
        STATIC_SPREAD_MARKERS[0],
        STATIC_SPREAD_MARKERS[1],
        0xFF,
        STATIC_SPREAD_MARKERS[2],
        STATIC_SPREAD_MARKERS[3],
        STATIC_SPREAD_MARKERS[4],
        0xFF,
        0xFE,
        0xFF,
        0xFF,
        0xFF,
    ))
    if FINAL_FIRE_MARKER_TABLE != expected_marker_table:
        raise PanelMonsterStageVariantError(
            f"Panel Monster v2 fire marker table mismatch: {FINAL_FIRE_MARKER_TABLE!r}"
        )
    static_markers = tuple(value for value in FINAL_FIRE_MARKER_TABLE if 0x80 <= value <= 0x84)
    if static_markers != tuple(STATIC_SPREAD_MARKERS):
        raise PanelMonsterStageVariantError(
            f"Panel Monster v2 spread marker order mismatch: {static_markers!r}"
        )
    if FINAL_FIRE_MARKER_TABLE.count(0xFE) != 1:
        raise PanelMonsterStageVariantError(
            "Panel Monster v2 fire marker table must contain one dynamic speed sentinel."
        )
    marker_table_read = bytes((
        0xBD,
        CPU_FINAL_FIRE_MARKER_TABLE & 0xFF,
        CPU_FINAL_FIRE_MARKER_TABLE >> 8,
        0xC9,
        0xFF,
    ))
    if FINAL_FIRE_COMMON.count(marker_table_read) != 2:
        raise PanelMonsterStageVariantError(
            "Panel Monster v2 fire common must read the shared marker table twice."
        )
    required_patterns = {
        "static child sub+7 write": (FINAL_STATIC_MARKER_HELPER, bytes((0x20, 0x56, 0xB1, 0xA0, 0x07))),
        "dynamic speed marker base $88": (FINAL_DYNAMIC_SPEED_MARKER_HELPER, bytes((0x09, DYNAMIC_SPEED_MARKER_BASE))),
        "dynamic static marker call": (
            FINAL_DYNAMIC_SPEED_MARKER_HELPER,
            bytes((0x20, CPU_FINAL_STATIC_MARKER_HELPER & 0xFF, CPU_FINAL_STATIC_MARKER_HELPER >> 8)),
        ),
        "fire common dynamic sentinel $FE": (FINAL_FIRE_COMMON, bytes((0xC9, 0xFE))),
    }
    for name, (blob, pattern) in required_patterns.items():
        if pattern not in blob:
            raise PanelMonsterStageVariantError(
                f"Panel Monster v2 fire marker path is missing {name}."
            )


def _validate_pmv2_parent_runtime_contract() -> None:
    """Guard the Panel Monster parent-drift cleanup contract."""
    if HOOK_SPEED_INIT_CALL != bytes.fromhex("20") + _word(CPU_FINAL_PARENT_SPEED_GUARD):
        raise PanelMonsterStageVariantError(
            "Panel Monster v2 speed-init hook no longer enters the parent speed guard."
        )
    required_patterns = {
        "stock speed init call": (FINAL_PARENT_SPEED_GUARD, bytes((0x20, 0xC0, 0x8A))),
        "panel type classifier call": (
            FINAL_PARENT_SPEED_GUARD,
            bytes((0x20, CPU_FINAL_PANEL_TYPE_CLASSIFIER & 0xFF, CPU_FINAL_PANEL_TYPE_CLASSIFIER >> 8)),
        ),
        "main +9/+8 clear": (FINAL_PARENT_SPEED_GUARD, bytes((0xA0, 0x09, 0x91, 0x08, 0x88, 0x91, 0x08))),
        "main +6/+5 clear": (FINAL_PARENT_SPEED_GUARD, bytes((0xA0, 0x06, 0x91, 0x08, 0x88, 0x91, 0x08))),
        "A/B/C entry +9/+8 clear": (FINAL_PARENT_FIELD_CLEAR_HELPER, bytes((0xA0, 0x09, 0x91, 0x2E, 0x88, 0x91, 0x2E))),
        "A/B/C entry +6/+5 clear": (FINAL_PARENT_FIELD_CLEAR_HELPER, bytes((0xA0, 0x06, 0x91, 0x2E, 0x88, 0x91, 0x2E))),
    }
    for name, (blob, pattern) in required_patterns.items():
        if pattern not in blob:
            raise PanelMonsterStageVariantError(
                f"Panel Monster v2 parent cleanup is missing {name}."
            )


def _validate_pmv2_classifier_runtime_contract() -> None:
    """Guard the Panel Monster type-classification contract."""
    if PANEL_STAGE_RUNTIME_IDS != PANEL_STAGE_VARIANT_IDS | BORROWED_PANEL_RUNTIME_IDS:
        raise PanelMonsterStageVariantError(
            "Panel Monster v2 runtime ID set must include A/B/C and borrowed 2-way/3-way IDs."
        )
    expected_borrowed = frozenset((0x52, 0x53, 0x56, 0x57, 0x5A, 0x5B, 0x66, 0x67))
    if BORROWED_PANEL_RUNTIME_IDS != expected_borrowed:
        raise PanelMonsterStageVariantError(
            f"Panel Monster v2 borrowed runtime IDs mismatch: {sorted(BORROWED_PANEL_RUNTIME_IDS)!r}"
        )
    required_patterns = {
        "A/B/C lower bound $30": (FINAL_PANEL_TYPE_CLASSIFIER, bytes((0xC9, 0x18))),
        "C upper split $38": (FINAL_PANEL_TYPE_CLASSIFIER, bytes((0xC9, 0x1C))),
        "A lower bound $40": (FINAL_PANEL_TYPE_CLASSIFIER, bytes((0xC9, 0x20))),
        "B upper bound $50": (FINAL_PANEL_TYPE_CLASSIFIER, bytes((0xC9, 0x28))),
        "classifier panel return": (FINAL_PANEL_TYPE_CLASSIFIER, bytes((0x38, 0x60))),
    }
    for enemy_id in BORROWED_FIRE_2WAY_CANONICAL_IDS:
        required_patterns[f"2-way fire dispatch ${enemy_id:02X}"] = (
            FINAL_FIRE_DISPATCH,
            bytes((0xC9, enemy_id)),
        )
    for enemy_id in BORROWED_FIRE_3WAY_CANONICAL_IDS:
        required_patterns[f"3-way fire dispatch ${enemy_id:02X}"] = (
            FINAL_FIRE_DISPATCH,
            bytes((0xC9, enemy_id)),
        )
    for shifted_id in (0x29, 0x2B, 0x2D, 0x33):
        required_patterns[f"borrowed Panel tail ${shifted_id:02X}"] = (
            FINAL_PANEL_TYPE_CLASSIFIER_TAIL,
            bytes((0xC9, shifted_id)),
        )
    required_patterns["borrowed Panel animation direction mask"] = (
        FINAL_PANEL_ANIM_DIR_HELPER,
        bytes((0x29, 0x05, 0xC9, 0x04)),
    )
    required_patterns["A/B/C Panel animation direction shift"] = (
        FINAL_PANEL_ANIM_DIR_HELPER,
        bytes((0x4A, 0x29, 0x03, 0x60)),
    )
    for name, (blob, pattern) in required_patterns.items():
        if pattern not in blob:
            raise PanelMonsterStageVariantError(
                f"Panel Monster v2 classifier is missing {name}."
            )


RESERVED_SPANS = (
    (OFF_FINAL_FIRE_DISPATCH, len(FINAL_FIRE_DISPATCH)),
    (OFF_FINAL_AI_DISPATCH_HELPER, len(FINAL_AI_DISPATCH_HELPER)),
    (OFF_FINAL_AI_DISPATCH_PANEL_HELPER, len(FINAL_AI_DISPATCH_PANEL_HELPER)),
    (OFF_FINAL_PARENT_SPEED_GUARD, len(FINAL_PARENT_SPEED_GUARD)),
    (OFF_FINAL_PANEL_TYPE_CLASSIFIER, len(FINAL_PANEL_TYPE_CLASSIFIER)),
    (OFF_FINAL_PANEL_TYPE_CLASSIFIER_TAIL, len(FINAL_PANEL_TYPE_CLASSIFIER_TAIL)),
    (OFF_FINAL_PANEL_ANIM_DIR_HELPER, len(FINAL_PANEL_ANIM_DIR_HELPER)),
    (OFF_FINAL_FIRE_COMMON, len(FINAL_FIRE_COMMON)),
    (OFF_FINAL_STATE0_INTERVAL_HELPER, len(FINAL_STATE0_INTERVAL_HELPER)),
    (OFF_FINAL_GROUP_RAM_OFFSET_HELPER, len(FINAL_GROUP_RAM_OFFSET_HELPER)),
    (OFF_FINAL_ABC_GROUP_OFFSET_HELPER, len(FINAL_ABC_GROUP_OFFSET_HELPER)),
    (OFF_FINAL_STATIC_MARKER_HELPER, len(FINAL_STATIC_MARKER_HELPER)),
    (OFF_FINAL_DYNAMIC_SPEED_MARKER_HELPER, len(FINAL_DYNAMIC_SPEED_MARKER_HELPER)),
    (OFF_FINAL_PARENT_FIELD_CLEAR_HELPER, len(FINAL_PARENT_FIELD_CLEAR_HELPER)),
    (OFF_FINAL_BULLET_ENTRY_HELPER, _v2_split_speed_reserved_sizes()["bullet_entry_helper"]),
    (OFF_FINAL_BULLET_ENTRY_TAIL_HELPER, _v2_split_speed_reserved_sizes()["bullet_entry_tail_helper"]),
    (OFF_FINAL_BULLET_SPEED_EXTRA_HELPER, _v2_split_speed_reserved_sizes()["tables_and_fast_loop"]),
    (OFF_FINAL_BULLET_SPEED_APPLY, _v2_split_speed_reserved_sizes()["speed_decode"]),
    (OFF_FINAL_SHARED_AI_WRAPPER, len(FINAL_SHARED_AI_WRAPPER)),
    (OFF_FINAL_FIRE_MARKER_TABLE, len(FINAL_FIRE_MARKER_TABLE)),
    (OFF_FINAL_BULLET_SPEED_HOOK, _v2_split_speed_reserved_sizes()["bullet_speed_hook"]),
    (OFF_FINAL_STAGE_PROPERTY_HOOK, len(FINAL_STAGE_PROPERTY_HOOK)),
    (OFF_FINAL_STAGE_ANIM_HOOK, len(FINAL_STAGE_ANIM_HOOK)),
    (OFF_PRG1_RUNTIME_LOADER, 0x60),
    (SETTINGS_TABLE_OFFSET, SETTINGS_TABLE_LENGTH),
    (OFF_STAGE_EXT_GAMEPLAY_FLAG_HELPER, STAGE_EXT_GAMEPLAY_FLAG_HELPER_LENGTH),
)


def panel_monster_v2_reserved_span_report() -> dict[str, object]:
    """Return overlap status for implementation-reserved Panel Monster v2 spans."""
    return _span_overlap_report(RESERVED_SPANS)


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


def has_panel_stage_runtime_ids(levels: list) -> bool:
    """Return True when the final split Panel runtime is needed.

    This helper is kept for callers that need to inspect level contents, but
    the expanded-ROM save path writes the v2 runtime unconditionally.  A/B/C
    IDs use the PRG0 settings table, and older 2-way/
    3-way borrowed Panel IDs use the same relocated shared wrapper.
    """
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if (int(getattr(enemy, "element_no", -1)) & 0xFF) in PANEL_STAGE_RUNTIME_IDS:
                return True
        for mirror in getattr(lv, "demon_mirrors", []) or []:
            for code in getattr(mirror, "enemy_codes", []) or []:
                if (int(code) & 0xFF) in PANEL_STAGE_RUNTIME_IDS:
                    return True
    return False


def init_level_defaults(level) -> None:
    if not hasattr(level, LEVEL_ATTRS["a_speed"]):
        setattr(level, LEVEL_ATTRS["a_speed"], DEFAULT_A_SPEED_PRESET)
    if not hasattr(level, LEVEL_ATTRS["a_interval"]):
        setattr(level, LEVEL_ATTRS["a_interval"], DEFAULT_A_INTERVAL)
    if not hasattr(level, LEVEL_ATTRS["b_speed"]):
        setattr(level, LEVEL_ATTRS["b_speed"], DEFAULT_B_SPEED_PRESET)
    if not hasattr(level, LEVEL_ATTRS["b_interval"]):
        setattr(level, LEVEL_ATTRS["b_interval"], DEFAULT_B_INTERVAL)
    if not hasattr(level, LEVEL_ATTRS["c_speed"]):
        setattr(level, LEVEL_ATTRS["c_speed"], DEFAULT_C_SPEED_PRESET)
    if not hasattr(level, LEVEL_ATTRS["c_interval"]):
        setattr(level, LEVEL_ATTRS["c_interval"], DEFAULT_C_INTERVAL)


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


def normalize_common_settings(settings: dict | None = None) -> dict:
    settings = settings or {}
    return {
        "a_speed": normalize_speed_preset(settings.get("a_speed", DEFAULT_A_SPEED_PRESET)),
        "a_interval": int(settings.get("a_interval", DEFAULT_A_INTERVAL)) & 0xFF,
        "b_speed": normalize_speed_preset(settings.get("b_speed", DEFAULT_B_SPEED_PRESET)),
        "b_interval": int(settings.get("b_interval", DEFAULT_B_INTERVAL)) & 0xFF,
        "c_speed": normalize_speed_preset(settings.get("c_speed", DEFAULT_C_SPEED_PRESET)),
        "c_interval": int(settings.get("c_interval", DEFAULT_C_INTERVAL)) & 0xFF,
    }


def common_entry(settings: dict | None = None) -> bytes:
    values = normalize_common_settings(settings)
    return build_entry(
        values["a_speed"],
        values["a_interval"],
        values["b_speed"],
        values["b_interval"],
        values["c_speed"],
        values["c_interval"],
    )


def patch_settings_table(rom_data: bytearray, common_settings: dict | None = None) -> bool:
    if len(rom_data) < SETTINGS_TABLE_END:
        return False
    table = _runtime_settings_entry(common_settings)
    if bytes(rom_data[SETTINGS_TABLE_OFFSET:SETTINGS_TABLE_END]) == table:
        return False
    rom_data[SETTINGS_TABLE_OFFSET:SETTINGS_TABLE_END] = table
    return True


def _runtime_settings_entry(common_settings: dict | None = None) -> bytes:
    entry = common_entry(common_settings)
    return entry[:6]


def panel_monster_v2_settings_contract(common_settings: dict | None = None) -> dict[str, object]:
    """Return the A/B/C PRG0 settings-table contract."""
    settings_entry = _runtime_settings_entry(common_settings)
    return {
        "settings_table": {
            "off": SETTINGS_TABLE_OFFSET,
            "cpu": CPU_SETTINGS_TABLE,
            "size": SETTINGS_TABLE_LENGTH,
            "bytes": settings_entry,
        },
        "runtime_users": {
            "state0_interval_helper": CPU_FINAL_STATE0_INTERVAL_HELPER,
            "dynamic_speed_marker_helper": CPU_FINAL_DYNAMIC_SPEED_MARKER_HELPER,
            "group_ram_offset_helper": CPU_FINAL_GROUP_RAM_OFFSET_HELPER,
        },
        "entry_values": {
            "a_speed": settings_entry[0],
            "a_interval": settings_entry[1],
            "b_speed": settings_entry[2],
            "b_interval": settings_entry[3],
            "c_speed": settings_entry[4],
            "c_interval": settings_entry[5],
        },
    }


def panel_monster_v2_settings_save_report(
    rom_data: bytes | bytearray,
    common_settings: dict | None = None,
) -> dict[str, object]:
    """Report whether saved ROM data carries the current A/B/C settings path."""
    if rom_data is None:
        raise PanelMonsterStageVariantError("ROM is missing.")
    contract = panel_monster_v2_settings_contract(common_settings)
    expected_table = contract["settings_table"]["bytes"]
    actual_table = bytes(rom_data[SETTINGS_TABLE_OFFSET:SETTINGS_TABLE_END])
    loader = _runtime_loader_slot()
    actual_loader = bytes(rom_data[OFF_PRG1_RUNTIME_LOADER:OFF_PRG1_RUNTIME_LOADER + len(loader)])
    return {
        "contract": contract,
        "settings_table_written": actual_table == expected_table,
        "runtime_loader_written": actual_loader == loader,
        "all_written": actual_table == expected_table and actual_loader == loader,
    }


def _build_runtime_loader(warp_mirror_stage_flag_helper: bool = True) -> bytes:
    # This supersedes stage_ext.RUNTIME_LOADER while preserving its side effects.
    # StageExt pointer starts at entry byte0: bank1 CPU $8800 + room*8.
    # The Solomon Seal block-state table is a separate PRG1 table at CPU $8E9B;
    # keep the current room number in X and copy its byte to $077D.
    from . import solomon_seal_block
    return (
        bytes.fromhex(
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
        )
        + bytes((
            0x4C,
            (
                CPU_STAGE_EXT_GAMEPLAY_FLAG_HELPER
                if warp_mirror_stage_flag_helper
                else solomon_seal_block.CPU_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER
            ) & 0xFF,
            (
                CPU_STAGE_EXT_GAMEPLAY_FLAG_HELPER
                if warp_mirror_stage_flag_helper
                else solomon_seal_block.CPU_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER
            ) >> 8,
        ))
    )


def _build_stage_ext_gameplay_flag_helper() -> bytes:
    from . import solomon_seal_block
    return bytes((
        0xA0, 0x00,                                # LDY #$00
        0xB1, 0x00,                                # LDA ($00),Y
        0x29, stage_ext.FLAG_WARP_MIRROR,          # AND #FLAG_WARP_MIRROR
        0x85, 0x02,                                # STA $02
        0xB1, 0x00,                                # LDA ($00),Y
        0x29, stage_ext.FLAG_ENEMY_CLEAR_KEY_OPEN, # AND #FLAG_ENEMY_CLEAR_KEY_OPEN
        0x4A, 0x4A,                                # -> $0770 bit4
        0x05, 0x02,                                # ORA $02
        0x8D, RAM_GAMEPLAY_STAGE_FLAGS & 0xFF, RAM_GAMEPLAY_STAGE_FLAGS >> 8,
        0x4C,
        solomon_seal_block.CPU_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER & 0xFF,
        solomon_seal_block.CPU_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER >> 8,
    ))


RUNTIME_LOADER = _build_runtime_loader()
assert len(RUNTIME_LOADER) <= 0x60
STAGE_EXT_GAMEPLAY_FLAG_HELPER = _build_stage_ext_gameplay_flag_helper()
assert len(STAGE_EXT_GAMEPLAY_FLAG_HELPER) == STAGE_EXT_GAMEPLAY_FLAG_HELPER_LENGTH
PREVIOUS_STAGE_EXT_GAMEPLAY_FLAG_HELPER = bytes((
    0xA0, 0x00,
    0xB1, 0x00,
    0x29, stage_ext.FLAG_WARP_MIRROR,
    0x8D, RAM_GAMEPLAY_STAGE_FLAGS & 0xFF, RAM_GAMEPLAY_STAGE_FLAGS >> 8,
    0x4C,
))


def _runtime_loader_slot() -> bytes:
    loader = _build_runtime_loader()
    if len(loader) > 0x60:
        raise PanelMonsterStageVariantError(
            f"Panel Variant PRG1 runtime loader is too large: {len(loader)}B"
        )
    return loader + _fill(0x00, 0x60 - len(loader))


def _previous_runtime_loader_slot() -> bytes:
    loader = _build_runtime_loader(warp_mirror_stage_flag_helper=False)
    return loader + _fill(0x00, 0x60 - len(loader))


RUNTIME_LOADER_SLOT = _runtime_loader_slot()


def apply_runtime_loader(rom_data: bytearray) -> list[str]:
    slot = _runtime_loader_slot()
    if len(rom_data) < OFF_PRG1_RUNTIME_LOADER + len(RUNTIME_LOADER_SLOT):
        return []
    cur = bytes(rom_data[OFF_M66_LOADER_TAIL:OFF_M66_LOADER_TAIL + len(ORIG_M66_LOADER_TAIL)])
    if cur not in (ORIG_M66_LOADER_TAIL, HOOK_M66_LOADER_TAIL):
        return []
    changed: list[str] = []
    if bytes(rom_data[OFF_PRG1_RUNTIME_LOADER:OFF_PRG1_RUNTIME_LOADER + len(slot)]) != slot:
        rom_data[OFF_PRG1_RUNTIME_LOADER:OFF_PRG1_RUNTIME_LOADER + len(slot)] = slot
        changed.append("Panel Variant PRG1 runtime loader")
    helper_cur = bytes(
        rom_data[
            OFF_STAGE_EXT_GAMEPLAY_FLAG_HELPER:
            OFF_STAGE_EXT_GAMEPLAY_FLAG_HELPER + len(STAGE_EXT_GAMEPLAY_FLAG_HELPER)
        ]
    )
    from . import solomon_seal_block
    previous_helper = (
        PREVIOUS_STAGE_EXT_GAMEPLAY_FLAG_HELPER +
        bytes((
            solomon_seal_block.CPU_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER & 0xFF,
            solomon_seal_block.CPU_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER >> 8,
        )) +
        bytes([0x00] * (len(STAGE_EXT_GAMEPLAY_FLAG_HELPER) - 12))
    )
    if (
        helper_cur != STAGE_EXT_GAMEPLAY_FLAG_HELPER
        and helper_cur != previous_helper
        and not all(b in (0x00, 0xEA) for b in helper_cur)
    ):
        raise PanelMonsterStageVariantError(
            f"StageExt gameplay flag helper area is not blank at file "
            f"0x{OFF_STAGE_EXT_GAMEPLAY_FLAG_HELPER:X}: got {helper_cur.hex(' ')}"
        )
    if bytes(rom_data[OFF_STAGE_EXT_GAMEPLAY_FLAG_HELPER:OFF_STAGE_EXT_GAMEPLAY_FLAG_HELPER + len(STAGE_EXT_GAMEPLAY_FLAG_HELPER)]) != STAGE_EXT_GAMEPLAY_FLAG_HELPER:
        rom_data[OFF_STAGE_EXT_GAMEPLAY_FLAG_HELPER:OFF_STAGE_EXT_GAMEPLAY_FLAG_HELPER + len(STAGE_EXT_GAMEPLAY_FLAG_HELPER)] = STAGE_EXT_GAMEPLAY_FLAG_HELPER
        changed.append("StageExt gameplay flag helper")
    if cur != HOOK_M66_LOADER_TAIL:
        rom_data[OFF_M66_LOADER_TAIL:OFF_M66_LOADER_TAIL + len(HOOK_M66_LOADER_TAIL)] = HOOK_M66_LOADER_TAIL
        changed.append("mapper66 loader Panel stage-variant hook")
    return changed


def _write_blob(rom_data, off: int, blob: bytes, changed: list[str], name: str) -> None:
    if bytes(rom_data[off:off + len(blob)]) != blob:
        rom_data[off:off + len(blob)] = blob
        changed.append(name)


apply = apply_panel_monster_v2_runtime

"""Shared dispatch entries for new enemy IDs in mapper66 saved ROMs."""
from __future__ import annotations

from . import ice_flame_runtime as _ice
from . import spark24_runtime as _spark24
from . import spark_ball_variant as _spark_variant
from . import neul84_runtime as _neul84
from . import chaos_dragon9e_runtime as _chaos9e
from . import ghostb0_runtime as _ghostb0
from . import phantom_preset_runtime as _phantom_preset
from . import fairy9c_runtime as _fairy9c
from . import seraphic_radiance9d_runtime as _radiance9d
from . import panel_monster_stage_variant as _panel


class NewEnemyRuntimeError(ValueError):
    pass


ICE_FLAME_ID = _ice.NEW_ENEMY_ID
SPARK24_FIRST_ID = _spark24.FIRST_ID
SPARK24_LAST_ID = _spark24.LAST_ID
NEUL84_FIRST_ID = _neul84.FIRST_ID
NEUL84_LAST_ID = _neul84.LAST_ID
CHAOS9E_ID = _chaos9e.NEW_ENEMY_ID
PHANTOM_PRESET_FIRST_ID = _phantom_preset.FIRST_ID
PHANTOM_PRESET_LAST_ID = _phantom_preset.LAST_ID
FAIRY9C_ID = _fairy9c.NEW_ENEMY_ID
RADIANCE9D_ID = _radiance9d.NEW_ENEMY_ID
GHOSTB0_FIRST_ID = _ghostb0.FIRST_ID
GHOSTB0_LAST_ID = _ghostb0.LAST_ID

OFF_AI_ENTRY = 0x3BF2      # CPU $BBE2
OFF_SETUP_ENTRY = 0x3C42
OFF_INIT_ENTRY = 0x3C94
OFF_ANIM_ENTRY = 0x3CE0

CPU_AI_ENTRY = 0xBBE2
CPU_SETUP_ENTRY = 0xBC32
CPU_INIT_ENTRY = 0xBC84
CPU_ANIM_ENTRY = 0xBCD0

OFF_GHOSTB0_EXTENSION = 0x3D65
CPU_GHOSTB0_AI_CLASSIFY = 0xBD55
CPU_GHOSTB0_SETUP_CLASSIFY = 0xBD63
CPU_GHOSTB0_INIT_CLASSIFY = 0xBD73

def _build_ai_entry_runtime() -> bytes:
    data = bytearray((0x48, 0x18, 0x69, 0x14))
    data.extend((
        0xC9, 0xE0, 0x90, 0x08,
        0xC9, 0xF8, 0xB0, 0x04,
        0x68, 0x4C,
        _panel.CPU_FINAL_SHARED_AI_WRAPPER & 0xFF,
        _panel.CPU_FINAL_SHARED_AI_WRAPPER >> 8,
    ))
    fixups: list[tuple[int, int]] = []
    data.extend((0xC9, NEUL84_FIRST_ID, 0x90, 0x00))
    neul_skip_operand = len(data) - 1
    data.extend((0xC9, NEUL84_LAST_ID + 1, 0x90, 0x00))
    neul_target_operand = len(data) - 1
    neul_skip_offset = len(data)
    targets = (
        (CHAOS9E_ID, _chaos9e.CPU_AI_DISPATCH),
        (FAIRY9C_ID, _fairy9c.CPU_AI_DISPATCH),
        (RADIANCE9D_ID, _radiance9d.CPU_AI_ENTRY),
    )
    for idx, (enemy_id, _target) in enumerate(targets):
        data.extend((0xC9, enemy_id, 0xF0, 0x00))
        fixups.append((len(data) - 1, idx))
    data.extend((0xC9, PHANTOM_PRESET_FIRST_ID, 0x90, 0x08))
    data.extend((0xC9, PHANTOM_PRESET_LAST_ID + 1, 0xB0, 0x04))
    data.extend((
        0x68, 0x4C,
        _phantom_preset.CPU_AI_DISPATCH & 0xFF,
        _phantom_preset.CPU_AI_DISPATCH >> 8,
    ))
    data.extend((0xC9, SPARK24_FIRST_ID, 0x90, 0x08))
    data.extend((0xC9, SPARK24_LAST_ID + 1, 0xB0, 0x04))
    data.extend((0x68, 0x4C, _spark24.CPU_AI_DISPATCH & 0xFF, _spark24.CPU_AI_DISPATCH >> 8))
    data.extend((
        0x68, 0x4C,
        CPU_GHOSTB0_AI_CLASSIFY & 0xFF,
        CPU_GHOSTB0_AI_CLASSIFY >> 8,
    ))
    target_offsets = []
    for _enemy_id, target in targets:
        target_offsets.append(len(data))
        data.extend((0x68, 0x4C, target & 0xFF, target >> 8))
    neul_target_offset = len(data)
    data.extend((
        0x68, 0x4C,
        _neul84.CPU_AI_DISPATCH & 0xFF,
        _neul84.CPU_AI_DISPATCH >> 8,
    ))
    data[neul_skip_operand] = (neul_skip_offset - (neul_skip_operand + 1)) & 0xFF
    data[neul_target_operand] = (neul_target_offset - (neul_target_operand + 1)) & 0xFF
    for operand_pos, target_index in fixups:
        rel = target_offsets[target_index] - (operand_pos + 1)
        if not -128 <= rel <= 127:
            raise ValueError("AI entry branch out of range")
        data[operand_pos] = rel & 0xFF
    return bytes(data)


AI_ENTRY_RUNTIME = _build_ai_entry_runtime()

class _EntryAsm:
    def __init__(self):
        self.data = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, int, str]] = []

    def label(self, name: str) -> None:
        self.labels[name] = len(self.data)

    def b(self, *values: int) -> None:
        self.data.extend(v & 0xFF for v in values)

    def jmp(self, addr: int) -> None:
        self.b(0x4C, addr & 0xFF, addr >> 8)

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


def _build_setup_entry_runtime() -> bytes:
    a = _EntryAsm()
    a.b(0xA0, 0x01, 0xB1, 0x08)         # LDA ($08),Y -> main-slot type
    a.b(0xC9, 0xE0)
    a.branch(0x90, "below_panel")
    a.b(0xC9, 0xF8)
    a.branch(0x90, "panel")
    a.label("below_panel")
    a.b(0xC9, SPARK24_FIRST_ID)
    a.branch(0x90, "below_spark24")
    a.b(0xC9, SPARK24_LAST_ID + 1)
    a.branch(0x90, "spark24")
    a.label("below_spark24")
    a.b(0xC9, NEUL84_FIRST_ID)
    a.branch(0x90, "below_neul84")
    a.b(0xC9, NEUL84_LAST_ID + 1)
    a.branch(0xB0, "below_neul84")
    a.jmp(_neul84.CPU_SETUP_META_LOAD)
    a.label("below_neul84")
    a.b(0xC9, ICE_FLAME_ID + 1)          # $82 uses the stock-computed Flame group
    a.branch(0x90, "stock")
    a.b(0xC9, CHAOS9E_ID)
    a.branch(0xF0, "chaos9e")
    a.b(0xC9, FAIRY9C_ID)
    a.branch(0xF0, "fairy9c")
    a.b(0xC9, RADIANCE9D_ID)
    a.branch(0xF0, "radiance9d")
    a.b(0xC9, PHANTOM_PRESET_FIRST_ID)
    a.branch(0x90, "lower_custom")
    a.b(0xC9, PHANTOM_PRESET_LAST_ID + 1)
    a.branch(0xB0, "stock")
    a.jmp(_phantom_preset.CPU_SETUP_META_LOAD)
    a.label("lower_custom")
    a.jmp(CPU_GHOSTB0_SETUP_CLASSIFY)
    a.label("chaos9e")
    a.jmp(_chaos9e.CPU_SETUP_META_LOAD)
    a.label("fairy9c")
    a.jmp(_fairy9c.CPU_SETUP_META_LOAD)
    a.label("radiance9d")
    a.jmp(_radiance9d.CPU_SETUP_META_LOAD)
    a.label("spark24")
    a.label("panel")
    a.b(0xA9, 0x14, 0x85, 0x0E, 0xA8, 0xB9, 0xD3, 0xD9, 0x60)
    a.label("stock")
    a.jmp(CPU_GHOSTB0_SETUP_CLASSIFY)
    return a.finish()


SETUP_ENTRY_RUNTIME = _build_setup_entry_runtime()

def _build_init_entry_runtime() -> bytes:
    a = _EntryAsm()
    a.b(0x48, 0xA5, 0x05)               # PHA; LDA $05
    a.b(0xC9, 0xE0)
    a.branch(0x90, "below_panel")
    a.b(0xC9, 0xF8)
    a.branch(0xB0, "below_panel")
    a.jmp(CPU_GHOSTB0_INIT_CLASSIFY)
    a.label("below_panel")
    a.b(0xC9, SPARK24_FIRST_ID)
    a.branch(0x90, "below_spark24")
    a.b(0xC9, SPARK24_LAST_ID + 1)
    a.branch(0x90, "spark24")
    a.label("below_spark24")
    a.b(0xC9, NEUL84_FIRST_ID)
    a.branch(0x90, "below_neul84")
    a.b(0xC9, NEUL84_LAST_ID + 1)
    a.branch(0xB0, "below_neul84")
    a.jmp(_neul84.CPU_INIT_STATUS)
    a.label("below_neul84")
    a.b(0xC9, CHAOS9E_ID)
    a.branch(0xF0, "chaos9e")
    a.b(0xC9, FAIRY9C_ID)
    a.branch(0xF0, "fairy9c")
    a.b(0xC9, RADIANCE9D_ID)
    a.branch(0xF0, "radiance9d")
    a.b(0xC9, PHANTOM_PRESET_FIRST_ID)
    a.branch(0x90, "stock_init")
    a.b(0xC9, PHANTOM_PRESET_LAST_ID + 1)
    a.branch(0xB0, "stock_init")
    a.jmp(_phantom_preset.CPU_INIT_STATUS)
    a.label("stock_init")
    a.jmp(CPU_GHOSTB0_INIT_CLASSIFY)
    a.label("ice")
    a.jmp(_ice.CPU_INIT_STATUS)
    a.label("spark24")
    a.b(0x68, 0x20, 0x1C, 0x9D, 0x60)
    a.label("chaos9e")
    a.jmp(_chaos9e.CPU_INIT_STATUS)
    a.label("fairy9c")
    a.jmp(_fairy9c.CPU_INIT_STATUS)
    a.label("radiance9d")
    a.jmp(_radiance9d.CPU_INIT_STATUS)
    return a.finish()


INIT_ENTRY_RUNTIME = _build_init_entry_runtime()

def _build_anim_entry_runtime() -> bytes:
    a = _EntryAsm()
    a.b(0xA0, 0x01, 0xB1, 0x08)
    a.b(0xC9, 0xE0)
    a.branch(0x90, "below_panel")
    a.b(0xC9, 0xF8)
    a.branch(0xB0, "below_panel")
    a.jmp(0x8789)
    a.label("below_panel")
    a.b(0xC9, SPARK24_FIRST_ID)
    a.branch(0x90, "below_spark24")
    a.b(0xC9, SPARK24_LAST_ID + 1)
    a.branch(0x90, "spark24")
    a.label("below_spark24")
    a.b(0xC9, GHOSTB0_FIRST_ID)
    a.branch(0x90, "below_ghostb0")
    a.b(0xC9, GHOSTB0_LAST_ID + 1)
    a.branch(0x90, "spark24")
    a.label("below_ghostb0")
    a.b(0xC9, ICE_FLAME_ID)
    a.branch(0xF0, "ice")
    a.b(0xC9, FAIRY9C_ID)
    a.branch(0xF0, "fairy9c")
    a.b(0xC9, RADIANCE9D_ID)
    a.branch(0xF0, "radiance9d")
    a.b(0xC9, PHANTOM_PRESET_FIRST_ID)
    a.branch(0x90, "stock_variants")
    a.b(0xC9, PHANTOM_PRESET_LAST_ID + 1)
    a.branch(0x90, "bullet_palette")
    a.label("stock_variants")
    # Stock color variants: direction-pair normalize, then recolor only
    # the selected stock/borrowed-ID enemy pairs.
    a.b(0x29, 0xFE)
    a.b(0xC9, 0x5E)
    a.branch(0xF0, "stock_spr2")
    a.b(0xC9, 0x62)
    a.branch(0xF0, "stock_spr2")
    a.b(0xC9, 0x66)
    a.branch(0xF0, "stock_spr2")
    a.b(0xC9, 0x6A)
    a.branch(0xF0, "stock_spr2")
    a.b(0xC9, 0x6E)
    a.branch(0xF0, "stock_spr0")
    a.b(0xC9, 0x72)
    a.branch(0xF0, "stock_spr2")
    a.b(0xC9, 0x76)
    a.branch(0xF0, "stock_spr0")
    a.jmp(0x8789)
    a.label("ice")
    a.jmp(_ice.CPU_ANIM_UPDATE)
    a.label("fairy9c")
    a.b(0x20, 0x89, 0x87, 0xA0, 0x13, 0xB1, 0x08)
    a.b(0x29, 0x13, 0x09, 0x48, 0x91, 0x08, 0x60)
    a.label("bullet_palette")
    a.label("stock_spr2")
    a.b(0x20, 0x89, 0x87, 0xA0, 0x13, 0xB1, 0x08)
    a.b(0x29, 0x33, 0x09, 0x48, 0x91, 0x08, 0x60)
    a.label("stock_spr0")
    a.b(0x20, 0x89, 0x87, 0xA0, 0x13, 0xB1, 0x08)
    a.b(0x29, 0x33, 0x91, 0x08, 0x60)
    a.label("radiance9d")
    a.jmp(_radiance9d.CPU_ANIM_UPDATE)
    a.label("spark24")
    a.jmp(0x8789)
    return a.finish()


ANIM_ENTRY_RUNTIME = _build_anim_entry_runtime()

GHOSTB0_EXTENSION_RUNTIME = bytes.fromhex(
    # AI: the restored dispatch value is enemy ID minus $14.
    f"c9 {GHOSTB0_FIRST_ID - 0x14:02x} 90 07 "
    f"c9 {GHOSTB0_LAST_ID - 0x14 + 1:02x} b0 03 "
    f"4c {_ghostb0.CPU_AI_DISPATCH & 0xFF:02x} {_ghostb0.CPU_AI_DISPATCH >> 8:02x} "
    "4c 29 a3 "
    # Setup: A still contains the enemy ID.
    f"38 e9 {GHOSTB0_FIRST_ID:02x} c9 {GHOSTB0_LAST_ID - GHOSTB0_FIRST_ID + 1:02x} b0 03 "
    f"4c {_ghostb0.CPU_SETUP_META_LOAD & 0xFF:02x} {_ghostb0.CPU_SETUP_META_LOAD >> 8:02x} "
    "a4 0e b9 d3 d9 60 "
    # Init: the original hook input remains on the stack.
    f"a5 05 38 e9 {GHOSTB0_FIRST_ID:02x} c9 {GHOSTB0_LAST_ID - GHOSTB0_FIRST_ID + 1:02x} b0 03 "
    f"4c {_ghostb0.CPU_INIT_STATUS & 0xFF:02x} {_ghostb0.CPU_INIT_STATUS >> 8:02x} "
    "68 20 1c 9d a5 05 "
    f"c9 {ICE_FLAME_ID:02x} d0 03 "
    f"4c {_ice.CPU_INIT_STATUS & 0xFF:02x} {_ice.CPU_INIT_STATUS >> 8:02x} "
    "60"
)

ENTRY_RUNTIMES = (
    (OFF_AI_ENTRY, AI_ENTRY_RUNTIME, "$BBE2 new enemy AI dispatch"),
    (OFF_SETUP_ENTRY, SETUP_ENTRY_RUNTIME, f"${CPU_SETUP_ENTRY:04X} new enemy setup dispatch"),
    (OFF_INIT_ENTRY, INIT_ENTRY_RUNTIME, f"${CPU_INIT_ENTRY:04X} new enemy init dispatch"),
    (OFF_ANIM_ENTRY, ANIM_ENTRY_RUNTIME, f"${CPU_ANIM_ENTRY:04X} new enemy animation dispatch"),
)

HOOK_AI_DISPATCH_CALL = bytes((0x20, CPU_AI_ENTRY & 0xFF, CPU_AI_ENTRY >> 8))
HOOK_SETUP_META_LOAD = bytes((0x20, CPU_SETUP_ENTRY & 0xFF, CPU_SETUP_ENTRY >> 8))
HOOK_INIT_WRITE_CALL = bytes((0x20, CPU_INIT_ENTRY & 0xFF, CPU_INIT_ENTRY >> 8))
HOOK_ANIM_UPDATE_CALL = bytes((0x20, CPU_ANIM_ENTRY & 0xFF, CPU_ANIM_ENTRY >> 8))

RESERVED_SPANS = (
    (OFF_AI_ENTRY, len(AI_ENTRY_RUNTIME)),
    (OFF_SETUP_ENTRY, len(SETUP_ENTRY_RUNTIME)),
    (OFF_INIT_ENTRY, len(INIT_ENTRY_RUNTIME)),
    (OFF_ANIM_ENTRY, len(ANIM_ENTRY_RUNTIME)),
    (OFF_GHOSTB0_EXTENSION, len(GHOSTB0_EXTENSION_RUNTIME)),
    *_ice.RESERVED_SPANS,
    *_neul84.RESERVED_SPANS,
    *_chaos9e.RESERVED_SPANS,
    *_phantom_preset.RESERVED_SPANS,
    *_fairy9c.RESERVED_SPANS,
    *_radiance9d.RESERVED_SPANS,
    *_ghostb0.RESERVED_SPANS,
)

assert len(AI_ENTRY_RUNTIME) == 80
assert len(SETUP_ENTRY_RUNTIME) == 82
assert len(INIT_ENTRY_RUNTIME) == 76
assert len(ANIM_ENTRY_RUNTIME) == 133
assert len(GHOSTB0_EXTENSION_RUNTIME) == 56
assert OFF_SETUP_ENTRY == OFF_AI_ENTRY + len(AI_ENTRY_RUNTIME)
assert OFF_INIT_ENTRY == OFF_SETUP_ENTRY + len(SETUP_ENTRY_RUNTIME)
assert OFF_ANIM_ENTRY == OFF_INIT_ENTRY + len(INIT_ENTRY_RUNTIME)
assert OFF_GHOSTB0_EXTENSION == OFF_ANIM_ENTRY + len(ANIM_ENTRY_RUNTIME)
assert OFF_GHOSTB0_EXTENSION + len(GHOSTB0_EXTENSION_RUNTIME) == 0x3D9D


def _mirror_enemy_code_needs_runtime(enemy_code: object) -> bool:
    try:
        enemy_id = int(enemy_code)
    except (TypeError, ValueError):
        return False
    return (
        enemy_id == ICE_FLAME_ID
        or _neul84.FIRST_ID <= enemy_id <= _neul84.LAST_ID
        or enemy_id in (FAIRY9C_ID, RADIANCE9D_ID, CHAOS9E_ID)
        or PHANTOM_PRESET_FIRST_ID <= enemy_id <= PHANTOM_PRESET_LAST_ID
        or _ghostb0.FIRST_ID <= enemy_id <= _ghostb0.LAST_ID
        or _spark24.FIRST_ID <= enemy_id <= _spark24.LAST_ID
        or _panel.is_panel_stage_variant_id(enemy_id)
    )


def levels_need_runtime(levels: list) -> bool:
    return (
        any(
            _mirror_enemy_code_needs_runtime(code)
            for lv in (levels or [])
            for mirror in (getattr(lv, "demon_mirrors", []) or [])
            for code in (getattr(mirror, "enemy_codes", []) or [])
        )
        or _ice.levels_need_runtime(levels)
        or any(
            _spark24.FIRST_ID <= int(getattr(enemy, "element_no", -1)) <= _spark24.LAST_ID
            for lv in (levels or [])
            for enemy in (getattr(lv, "enemies", []) or [])
        )
        or _neul84.levels_need_runtime(levels)
        or _chaos9e.levels_need_runtime(levels)
        or any(
            PHANTOM_PRESET_FIRST_ID <= int(getattr(enemy, "element_no", -1)) <= PHANTOM_PRESET_LAST_ID
            for lv in (levels or [])
            for enemy in (getattr(lv, "enemies", []) or [])
        )
        or _fairy9c.levels_need_runtime(levels)
        or _radiance9d.levels_need_runtime(levels)
        or _ghostb0.levels_need_runtime(levels)
        or _panel.has_panel_stage_runtime_ids(levels)
    )


def _expect_one(data: bytes | bytearray, off: int, allowed: tuple[bytes, ...], name: str) -> None:
    size = len(allowed[0])
    cur = bytes(data[off:off + size])
    if cur not in allowed:
        expected = " or ".join(blob.hex(" ") for blob in allowed)
        raise NewEnemyRuntimeError(
            f"{name} signature mismatch at 0x{off:X}: expected {expected}, got {cur.hex(' ')}"
        )


def _expect_blank_or(data: bytes | bytearray, off: int, blob: bytes, name: str) -> None:
    cur = bytes(data[off:off + len(blob)])
    if cur == blob or all(b in (0xEA, 0x00) for b in cur):
        return
    raise NewEnemyRuntimeError(
        f"{name} area is not blank at 0x{off:X}: expected EA/00 or {blob.hex(' ')}, got {cur.hex(' ')}"
    )


def _write(data: bytearray, off: int, blob: bytes, changed: list[str], name: str) -> None:
    cur = bytes(data[off:off + len(blob)])
    if cur != blob:
        data[off:off + len(blob)] = blob
        changed.append(name)


def apply(rom_data: bytearray) -> list[str]:
    """Apply shared new-enemy dispatch entries and new enemy bodies."""
    max_end = max(
        _ice.OFF_RUNTIME + len(_ice.RUNTIME),
        _spark24.OFF_RUNTIME + len(_spark24.RUNTIME),
        _neul84.OFF_RUNTIME + len(_neul84.RUNTIME),
        _neul84.OFF_PARAMETER_TABLE + len(_neul84.PARAMETER_TABLES),
        _chaos9e.OFF_RUNTIME + len(_chaos9e.RUNTIME),
        _phantom_preset.OFF_RUNTIME + len(_phantom_preset.RUNTIME),
        _fairy9c.OFF_RUNTIME + len(_fairy9c.RUNTIME),
        _radiance9d.OFF_RUNTIME + len(_radiance9d.RUNTIME),
        _ghostb0.OFF_RUNTIME + len(_ghostb0.RUNTIME),
        _ghostb0.OFF_PARAMETER_TABLE + len(_ghostb0.PARAMETER_TABLES),
        _panel.OFF_FINAL_STATIC_MARKER_HELPER + len(_panel.FINAL_STATIC_MARKER_HELPER),
        OFF_GHOSTB0_EXTENSION + len(GHOSTB0_EXTENSION_RUNTIME),
        max(off + len(blob) for off, blob, _name in ENTRY_RUNTIMES),
    )
    if rom_data is None or len(rom_data) < max_end:
        raise NewEnemyRuntimeError("ROM is too short for new enemy runtime.")

    _expect_one(
        rom_data,
        _ice.OFF_AI_DISPATCH_CALL,
        (_ice.ORIG_AI_DISPATCH_CALL, HOOK_AI_DISPATCH_CALL),
        "$A1C3 new enemy AI dispatch hook",
    )
    _expect_one(
        rom_data,
        _ice.OFF_ANIM_UPDATE_CALL,
        (_ice.ORIG_ANIM_UPDATE_CALL, HOOK_ANIM_UPDATE_CALL),
        "$8676 new enemy animation hook",
    )
    _expect_one(
        rom_data,
        _ice.OFF_INIT_WRITE_CALL,
        (_ice.ORIG_INIT_WRITE_CALL, HOOK_INIT_WRITE_CALL),
        "$A2F2 new enemy init hook",
    )
    _expect_one(
        rom_data,
        _ice.OFF_SETUP_META_LOAD,
        (_ice.ORIG_SETUP_META_LOAD, HOOK_SETUP_META_LOAD),
        "$8ACB new enemy setup hook",
    )
    _expect_one(
        rom_data,
        _ice.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_ice.RUNTIME), _ice.RUNTIME),
        "Ice Flame runtime area",
    )
    neul84_settings = _neul84.current_settings(rom_data)
    neul84_runtime = _neul84.build_runtime(neul84_settings["groups"])
    neul84_parameters = _neul84.build_parameter_tables(neul84_settings["groups"])
    _expect_blank_or(
        rom_data,
        _neul84.OFF_RUNTIME,
        neul84_runtime,
        "Neul A/B runtime area",
    )
    _expect_blank_or(
        rom_data,
        _neul84.OFF_PARAMETER_TABLE,
        neul84_parameters,
        "Neul A/B parameter table area",
    )
    _expect_one(
        rom_data,
        _chaos9e.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_chaos9e.RUNTIME), _chaos9e.RUNTIME),
        "Chaos Dragon9E runtime area",
    )
    phantom_settings = _phantom_preset.current_settings(rom_data)
    phantom_runtime, _phantom_offsets = _phantom_preset.build_runtime(
        phantom_settings["groups"],
    )
    ghostb0_settings = _ghostb0.current_settings(rom_data)
    ghostb0_runtime = _ghostb0.build_runtime(ghostb0_settings["groups"])
    ghostb0_parameters = _ghostb0.build_parameter_tables(ghostb0_settings["groups"])
    _ghostb0.validate_runtime_dependencies(rom_data)
    _neul84.validate_runtime_dependencies(rom_data)
    _expect_blank_or(
        rom_data,
        _ghostb0.OFF_RUNTIME,
        ghostb0_runtime,
        "Ghost A-F runtime area",
    )
    _expect_blank_or(
        rom_data,
        _ghostb0.OFF_PARAMETER_TABLE,
        ghostb0_parameters,
        "Ghost A-F parameter table area",
    )
    _expect_blank_or(
        rom_data,
        _phantom_preset.OFF_RUNTIME,
        phantom_runtime,
        "Phantom preset runtime area",
    )
    _expect_blank_or(
        rom_data,
        _phantom_preset.OFF_VERTICAL_PHYSICS,
        _phantom_preset.VERTICAL_PHYSICS,
        "Phantom preset vertical physics helper",
    )
    _expect_one(
        rom_data,
        _phantom_preset.OFF_PHYSICS_CALL,
        (_phantom_preset.ORIG_PHYSICS_CALL, _phantom_preset.HOOK_PHYSICS_CALL),
        "Phantom preset pre-physics hook",
    )
    _expect_one(
        rom_data,
        _fairy9c.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_fairy9c.RUNTIME), _fairy9c.RUNTIME),
        "Dark Fairy9C runtime area",
    )
    _expect_one(
        rom_data,
        _radiance9d.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_radiance9d.RUNTIME), _radiance9d.RUNTIME),
        "Seraphic Radiance9D runtime area",
    )
    for off, blob, name in ENTRY_RUNTIMES:
        _expect_blank_or(rom_data, off, blob, name)
    _expect_blank_or(
        rom_data,
        OFF_GHOSTB0_EXTENSION,
        GHOSTB0_EXTENSION_RUNTIME,
        "Ghost B0-BB entry classification extension",
    )

    changed: list[str] = []
    changed.extend(_spark_variant.apply(rom_data))
    _write(rom_data, _ice.OFF_AI_DISPATCH_CALL, HOOK_AI_DISPATCH_CALL, changed, "$A1C3 new enemy AI dispatch hook")
    _write(rom_data, _ice.OFF_ANIM_UPDATE_CALL, HOOK_ANIM_UPDATE_CALL, changed, "$8676 new enemy animation hook")
    _write(rom_data, _ice.OFF_INIT_WRITE_CALL, HOOK_INIT_WRITE_CALL, changed, "$A2F2 new enemy init/status hook")
    _write(rom_data, _ice.OFF_SETUP_META_LOAD, HOOK_SETUP_META_LOAD, changed, "$8ACB new enemy setup group hook")
    for off, blob, name in ENTRY_RUNTIMES:
        _write(rom_data, off, blob, changed, name)
    _write(
        rom_data,
        OFF_GHOSTB0_EXTENSION,
        GHOSTB0_EXTENSION_RUNTIME,
        changed,
        (
            f"${CPU_GHOSTB0_AI_CLASSIFY:04X}-"
            f"${CPU_GHOSTB0_AI_CLASSIFY + len(GHOSTB0_EXTENSION_RUNTIME) - 1:04X} "
            "Ghost B0-BB entry classification extension"
        ),
    )
    _write(
        rom_data,
        _ice.OFF_RUNTIME,
        _ice.RUNTIME,
        changed,
        f"Ice Burn runtime ${_ice.CPU_INIT_STATUS:04X}-${_ice.CPU_RUNTIME_END - 1:04X}",
    )
    _write(
        rom_data,
        _neul84.OFF_RUNTIME,
        neul84_runtime,
        changed,
        f"Neul A/B runtime ${_neul84.CPU_RUNTIME:04X}-${_neul84.CPU_RUNTIME_END - 1:04X}",
    )
    _write(
        rom_data,
        _neul84.OFF_PARAMETER_TABLE,
        neul84_parameters,
        changed,
        f"Neul A/B parameters ${_neul84.CPU_PARAMETER_TABLE:04X}-${_neul84.CPU_PARAMETER_TABLE + len(neul84_parameters) - 1:04X}",
    )
    _write(
        rom_data,
        _chaos9e.OFF_RUNTIME,
        _chaos9e.RUNTIME,
        changed,
        f"Chaos Dragon9E runtime ${_chaos9e.CPU_RUNTIME:04X}-${_chaos9e.CPU_RUNTIME_END - 1:04X}",
    )
    _write(
        rom_data,
        _phantom_preset.OFF_VERTICAL_PHYSICS,
        _phantom_preset.VERTICAL_PHYSICS,
        changed,
        (
            f"Phantom vertical physics helper "
            f"${_phantom_preset.CPU_VERTICAL_PHYSICS:04X}-"
            f"${_phantom_preset.CPU_VERTICAL_PHYSICS + len(_phantom_preset.VERTICAL_PHYSICS) - 1:04X}"
        ),
    )
    _write(
        rom_data,
        _phantom_preset.OFF_RUNTIME,
        phantom_runtime,
        changed,
        f"Phantom preset runtime ${_phantom_preset.CPU_RUNTIME:04X}-${_phantom_preset.CPU_RUNTIME_END - 1:04X}",
    )
    _write(
        rom_data,
        _ghostb0.OFF_RUNTIME,
        ghostb0_runtime,
        changed,
        f"Ghost A-F runtime ${_ghostb0.CPU_RUNTIME:04X}-${_ghostb0.CPU_RUNTIME_END - 1:04X}",
    )
    _write(
        rom_data,
        _ghostb0.OFF_PARAMETER_TABLE,
        ghostb0_parameters,
        changed,
        f"Ghost A-F parameters ${_ghostb0.CPU_PARAMETER_TABLE:04X}-${_ghostb0.CPU_PARAMETER_TABLE + len(ghostb0_parameters) - 1:04X}",
    )
    _write(
        rom_data,
        _phantom_preset.OFF_PHYSICS_CALL,
        _phantom_preset.HOOK_PHYSICS_CALL,
        changed,
        f"Phantom preset pre-physics hook $8670 -> ${_phantom_preset.CPU_PREPHYSICS:04X}",
    )
    _write(
        rom_data,
        _fairy9c.OFF_RUNTIME,
        _fairy9c.RUNTIME,
        changed,
        f"Dark Fairy9C runtime ${_fairy9c.CPU_RUNTIME:04X}-${_fairy9c.CPU_RUNTIME_END - 1:04X}",
    )
    _write(
        rom_data,
        _radiance9d.OFF_RUNTIME,
        _radiance9d.RUNTIME,
        changed,
        f"Seraphic Radiance9D runtime ${_radiance9d.CPU_RUNTIME:04X}-${_radiance9d.CPU_RUNTIME_END - 1:04X}",
    )
    return changed

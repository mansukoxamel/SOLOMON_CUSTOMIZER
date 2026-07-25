"""Shared dispatch entries for new enemy IDs in mapper66 saved ROMs."""
from __future__ import annotations

from . import ice_flame_runtime as _ice
from . import spark24_runtime as _spark24
from . import spark_trail_runtime as _spark_trail
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
SPARK_TRAIL_FIRST_ID = _spark_trail.FIRST_ID
SPARK_TRAIL_LAST_ID = _spark_trail.LAST_ID
FUTURE_ENEMY_FIRST_ID = 0xF8
FUTURE_ENEMY_LAST_ID = 0xFF
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
CPU_AI_ENTRY = 0xBBE2
ENTRY_CENTER_LIMIT = 0x3D9D

LEGACY_AI_ENTRY_RUNTIME = bytes.fromhex(
    "48186914c9e09008c9f8b004684cb7e6c9849004c9889034c99ef024c99cf024"
    "c99df024c9a09008c9b0b004684cbdbdc9c09008c9e0b004684cc0be684c55bd"
    "684cbeee684c0de0684c20ec684ceeee"
)
LEGACY_SETUP_ENTRY_RUNTIME = bytes.fromhex(
    "a001b108c9e09004c9f8903ac9c09004c9e09032c9849007c988b0034cc1eec9"
    "83902cc99ef016c99cf015c99df014c9a09007c9b0b0184c9cbd4c63bd4ca4ee"
    "4c00e04c00e0a914850ea8b9d3d9604c63bd"
)
LEGACY_INIT_ENTRY_RUNTIME = bytes.fromhex(
    "48a505c9e09007c9f8b0034c73bdc9c09004c9e09028c9849007c988b0034cd4"
    "eec99ef01ec99cf01dc99df01cc9a09007c9b0b0034ca5bd4c73bd4c75e06820"
    "1c9d604caeee4c09e04cf4eb"
)
LEGACY_ANIM_ENTRY_RUNTIME = bytes.fromhex(
    "a001b108c9e09007c9f8b0034c8987c9c09004c9e0906bc9b09004c9bc9063c9"
    "82f031c99cf030c99df054c9a09004c9b0903229fec95ef02cc962f028c966f0"
    "24c96af020c96ef02ac972f018c976f0224c89874c92e0208987a013b1082913"
    "0948910860208987a013b10829330948910860208987a013b10829339108604c"
    "00ed4c8987"
)
LEGACY_GHOSTB0_EXTENSION_RUNTIME = bytes.fromhex(
    "c99c9007c9a8b0034c83e24c29a338e9b0c90cb0034c58e2a40eb9d3d960a5"
    "0538e9b0c90cb0034c6ae268201c9da505c982d0034c75e060"
)


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


def _pla_jmp(a: _EntryAsm, addr: int) -> None:
    a.b(0x68)
    a.jmp(addr)

def _build_ai_entry_runtime(
    spark_family_last_id: int = SPARK_TRAIL_LAST_ID,
) -> bytes:
    a = _EntryAsm()
    a.b(0x48, 0x18, 0x69, 0x14)        # Save dispatch A; restore enemy ID.
    a.b(0xC9, SPARK24_FIRST_ID)
    a.branch(0x90, "below_spark")
    a.b(0xC9, spark_family_last_id + 1)
    a.branch(0x90, "spark")
    a.b(0xC9, FUTURE_ENEMY_FIRST_ID)
    a.branch(0xB0, "stock")
    a.branch(0x90, "panel")
    a.label("below_spark")
    for limit, label in (
        (NEUL84_FIRST_ID, "stock"),
        (NEUL84_LAST_ID + 1, "neul84"),
        (FAIRY9C_ID, "stock"),
    ):
        a.b(0xC9, limit)
        a.branch(0x90, label)
    a.branch(0xF0, "fairy9c")
    for limit, label in (
        (CHAOS9E_ID + 1, "named_9c_9e"),
        (PHANTOM_PRESET_FIRST_ID, "stock"),
        (PHANTOM_PRESET_LAST_ID + 1, "phantom"),
        (GHOSTB0_LAST_ID + 1, "ghostb0"),
    ):
        a.b(0xC9, limit)
        a.branch(0x90, label)
    a.label("stock")
    _pla_jmp(a, 0xA329)
    a.label("neul84")
    _pla_jmp(a, _neul84.CPU_AI_DISPATCH)
    a.label("phantom")
    _pla_jmp(a, _phantom_preset.CPU_AI_DISPATCH)
    a.label("ghostb0")
    _pla_jmp(a, _ghostb0.CPU_AI_DISPATCH)
    a.label("spark")
    _pla_jmp(a, _spark24.CPU_AI_DISPATCH)
    a.label("panel")
    _pla_jmp(a, _panel.CPU_FINAL_SHARED_AI_WRAPPER)
    a.label("named_9c_9e")
    a.b(0xC9, CHAOS9E_ID)
    a.branch(0x90, "radiance9d")
    _pla_jmp(a, _chaos9e.CPU_AI_DISPATCH)
    a.label("fairy9c")
    _pla_jmp(a, _fairy9c.CPU_AI_DISPATCH)
    a.label("radiance9d")
    _pla_jmp(a, _radiance9d.CPU_AI_ENTRY)
    return a.finish()


AI_ENTRY_RUNTIME = _build_ai_entry_runtime()
OFF_SETUP_ENTRY = OFF_AI_ENTRY + len(AI_ENTRY_RUNTIME)
CPU_SETUP_ENTRY = CPU_AI_ENTRY + len(AI_ENTRY_RUNTIME)


def _build_setup_entry_runtime(
    spark_family_last_id: int = SPARK_TRAIL_LAST_ID,
) -> bytes:
    a = _EntryAsm()
    a.b(0xA0, 0x01, 0xB1, 0x08)         # LDA ($08),Y -> main-slot type
    a.b(0xC9, SPARK24_FIRST_ID)
    a.branch(0x90, "below_spark")
    a.b(0xC9, FUTURE_ENEMY_FIRST_ID)
    a.branch(0x90, "common_group")
    a.branch(0xB0, "stock")
    a.label("below_spark")
    for limit, label in (
        (NEUL84_FIRST_ID, "stock"),
        (NEUL84_LAST_ID + 1, "neul84"),
        (FAIRY9C_ID, "stock"),
    ):
        a.b(0xC9, limit)
        a.branch(0x90, label)
    a.branch(0xF0, "fairy9c")
    for limit, label in (
        (CHAOS9E_ID + 1, "named_9c_9e"),
        (PHANTOM_PRESET_FIRST_ID, "stock"),
        (PHANTOM_PRESET_LAST_ID + 1, "phantom"),
        (GHOSTB0_LAST_ID + 1, "ghostb0"),
    ):
        a.b(0xC9, limit)
        a.branch(0x90, label)
    a.label("stock")
    a.b(0xA4, 0x0E, 0xB9, 0xD3, 0xD9, 0x60)
    a.label("neul84")
    a.jmp(_neul84.CPU_SETUP_META_LOAD)
    a.label("phantom")
    a.jmp(_phantom_preset.CPU_SETUP_META_LOAD)
    a.label("ghostb0")
    a.b(0x38, 0xE9, GHOSTB0_FIRST_ID)
    a.jmp(_ghostb0.CPU_SETUP_META_LOAD)
    a.label("common_group")
    a.b(0xA9, 0x14, 0x85, 0x0E, 0xA8, 0xB9, 0xD3, 0xD9, 0x60)
    a.label("named_9c_9e")
    a.b(0xC9, CHAOS9E_ID)
    a.branch(0x90, "radiance9d")
    a.jmp(_chaos9e.CPU_SETUP_META_LOAD)
    a.label("fairy9c")
    a.jmp(_fairy9c.CPU_SETUP_META_LOAD)
    a.label("radiance9d")
    a.jmp(_radiance9d.CPU_SETUP_META_LOAD)
    return a.finish()


SETUP_ENTRY_RUNTIME = _build_setup_entry_runtime()
OFF_INIT_ENTRY = OFF_SETUP_ENTRY + len(SETUP_ENTRY_RUNTIME)
CPU_INIT_ENTRY = CPU_SETUP_ENTRY + len(SETUP_ENTRY_RUNTIME)

def _build_init_entry_runtime(
    spark_family_last_id: int = SPARK_TRAIL_LAST_ID,
) -> bytes:
    a = _EntryAsm()
    a.b(0x48, 0xA5, 0x05)               # PHA; LDA $05
    a.b(0xC9, SPARK24_FIRST_ID)
    a.branch(0x90, "below_spark")
    a.b(0xC9, spark_family_last_id + 1)
    a.branch(0x90, "spark")
    a.branch(0xB0, "stock_init")
    a.label("below_spark")
    for limit, label in (
        (NEUL84_FIRST_ID, "stock_init"),
        (NEUL84_LAST_ID + 1, "neul84"),
        (FAIRY9C_ID, "stock_init"),
    ):
        a.b(0xC9, limit)
        a.branch(0x90, label)
    a.branch(0xF0, "fairy9c")
    for limit, label in (
        (CHAOS9E_ID + 1, "named_9c_9e"),
        (PHANTOM_PRESET_FIRST_ID, "stock_init"),
        (PHANTOM_PRESET_LAST_ID + 1, "phantom"),
        (GHOSTB0_LAST_ID + 1, "ghostb0"),
    ):
        a.b(0xC9, limit)
        a.branch(0x90, label)
    a.label("stock_init")
    a.b(0x68, 0x20, 0x1C, 0x9D, 0xA5, 0x05, 0xC9, ICE_FLAME_ID)
    a.branch(0xD0, "stock_done")
    a.jmp(_ice.CPU_INIT_STATUS)
    a.label("stock_done")
    a.b(0x60)
    a.label("neul84")
    a.jmp(_neul84.CPU_INIT_STATUS)
    a.label("phantom")
    a.jmp(_phantom_preset.CPU_INIT_STATUS)
    a.label("ghostb0")
    a.b(0x38, 0xE9, GHOSTB0_FIRST_ID)
    a.jmp(_ghostb0.CPU_INIT_STATUS)
    a.label("spark")
    a.b(0x68, 0x20, 0x1C, 0x9D, 0x60)
    a.label("named_9c_9e")
    a.b(0xC9, CHAOS9E_ID)
    a.branch(0x90, "radiance9d")
    a.jmp(_chaos9e.CPU_INIT_STATUS)
    a.label("fairy9c")
    a.jmp(_fairy9c.CPU_INIT_STATUS)
    a.label("radiance9d")
    a.jmp(_radiance9d.CPU_INIT_STATUS)
    return a.finish()


INIT_ENTRY_RUNTIME = _build_init_entry_runtime()
OFF_ANIM_ENTRY = OFF_INIT_ENTRY + len(INIT_ENTRY_RUNTIME)
CPU_ANIM_ENTRY = CPU_INIT_ENTRY + len(INIT_ENTRY_RUNTIME)

def _build_anim_entry_runtime() -> bytes:
    a = _EntryAsm()
    a.b(0xA0, 0x01, 0xB1, 0x08)
    a.b(0xC9, GHOSTB0_FIRST_ID)
    a.branch(0xB0, "stock")
    a.b(0xC9, 0x5E)
    a.branch(0x90, "stock")
    a.b(0xC9, 0x78)
    a.branch(0x90, "stock_variants")
    a.b(0xC9, ICE_FLAME_ID)
    a.branch(0x90, "stock")
    a.b(0xC9, ICE_FLAME_ID)
    a.branch(0xF0, "ice")
    a.b(0xC9, FAIRY9C_ID)
    a.branch(0x90, "stock")
    a.branch(0xF0, "fairy9c")
    a.b(0xC9, RADIANCE9D_ID)
    a.branch(0xF0, "radiance9d")
    a.b(0xC9, PHANTOM_PRESET_FIRST_ID)
    a.branch(0x90, "stock")
    a.b(0xC9, PHANTOM_PRESET_LAST_ID + 1)
    a.branch(0x90, "bullet_palette")
    a.label("stock")
    a.jmp(0x8789)
    a.label("stock_variants")
    a.b(0x29, 0xFE)
    a.b(0x38, 0xE9, 0x5E, 0x48, 0x29, 0x03)
    a.branch(0xD0, "stock_variant_miss")
    a.b(0x68, 0xC9, 0x10)
    a.branch(0xF0, "stock_spr0")
    a.b(0xC9, 0x18)
    a.branch(0xF0, "stock_spr0")
    # Patch this absolute JMP after labels have been resolved.
    a.jmp(0x0000)
    stock_spr2_fixup = len(a.data) - 2
    a.label("stock_variant_miss")
    a.b(0x68)
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
    result = bytearray(a.finish())
    stock_spr2_addr = CPU_ANIM_ENTRY + a.labels["stock_spr2"]
    result[stock_spr2_fixup] = stock_spr2_addr & 0xFF
    result[stock_spr2_fixup + 1] = stock_spr2_addr >> 8
    return bytes(result)


ANIM_ENTRY_RUNTIME = _build_anim_entry_runtime()
ENTRY_CENTER_RUNTIME = (
    AI_ENTRY_RUNTIME
    + SETUP_ENTRY_RUNTIME
    + INIT_ENTRY_RUNTIME
    + ANIM_ENTRY_RUNTIME
)
ENTRY_CENTER_SIZE = len(ENTRY_CENTER_RUNTIME)
ENTRY_CENTER_CAPACITY = ENTRY_CENTER_LIMIT - OFF_AI_ENTRY
ENTRY_CENTER_FREE_SIZE = ENTRY_CENTER_CAPACITY - ENTRY_CENTER_SIZE
CURRENT_ENTRY_CENTER_IMAGE = ENTRY_CENTER_RUNTIME
LEGACY_ENTRY_CENTER_IMAGE = (
    LEGACY_AI_ENTRY_RUNTIME
    + LEGACY_SETUP_ENTRY_RUNTIME
    + LEGACY_INIT_ENTRY_RUNTIME
    + LEGACY_ANIM_ENTRY_RUNTIME
    + LEGACY_GHOSTB0_EXTENSION_RUNTIME
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
LEGACY_HOOK_SETUP_META_LOAD = bytes.fromhex("20 32 bc")
LEGACY_HOOK_INIT_WRITE_CALL = bytes.fromhex("20 84 bc")
LEGACY_HOOK_ANIM_UPDATE_CALL = bytes.fromhex("20 d0 bc")

RESERVED_SPANS = (
    (OFF_AI_ENTRY, len(AI_ENTRY_RUNTIME)),
    (OFF_SETUP_ENTRY, len(SETUP_ENTRY_RUNTIME)),
    (OFF_INIT_ENTRY, len(INIT_ENTRY_RUNTIME)),
    (OFF_ANIM_ENTRY, len(ANIM_ENTRY_RUNTIME)),
    *_ice.RESERVED_SPANS,
    *_neul84.RESERVED_SPANS,
    *_chaos9e.RESERVED_SPANS,
    *_phantom_preset.RESERVED_SPANS,
    *_fairy9c.RESERVED_SPANS,
    *_radiance9d.RESERVED_SPANS,
    *_ghostb0.RESERVED_SPANS,
    *_spark_trail.RESERVED_SPANS,
)

assert OFF_SETUP_ENTRY == OFF_AI_ENTRY + len(AI_ENTRY_RUNTIME)
assert OFF_INIT_ENTRY == OFF_SETUP_ENTRY + len(SETUP_ENTRY_RUNTIME)
assert OFF_ANIM_ENTRY == OFF_INIT_ENTRY + len(INIT_ENTRY_RUNTIME)
assert OFF_ANIM_ENTRY + len(ANIM_ENTRY_RUNTIME) <= ENTRY_CENTER_LIMIT
assert len(CURRENT_ENTRY_CENTER_IMAGE) == ENTRY_CENTER_SIZE
assert len(LEGACY_ENTRY_CENTER_IMAGE) == ENTRY_CENTER_CAPACITY


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
        or _spark_trail.FIRST_ID <= enemy_id <= _spark_trail.LAST_ID
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
        or _spark_trail.levels_need_runtime(levels)
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


def _expect_entry_center(data: bytes | bytearray) -> bool:
    current = bytes(data[OFF_AI_ENTRY:OFF_AI_ENTRY + ENTRY_CENTER_SIZE])
    full = bytes(data[OFF_AI_ENTRY:ENTRY_CENTER_LIMIT])
    if full == LEGACY_ENTRY_CENTER_IMAGE:
        return True
    if (
        current == CURRENT_ENTRY_CENTER_IMAGE
        or all(byte in (0xEA, 0x00) for byte in current)
    ):
        return False
    raise NewEnemyRuntimeError(
        f"new enemy entry center is not blank/current/legacy at "
        f"0x{OFF_AI_ENTRY:X}: got {full.hex(' ')}"
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
        _spark_trail.OFF_MAIN_RUNTIME + len(_spark_trail.MAIN_RUNTIME),
        _spark_trail.OFF_AUX_RUNTIME + len(_spark_trail.AUX_RUNTIME),
        _neul84.OFF_RUNTIME + len(_neul84.RUNTIME),
        _neul84.OFF_PARAMETER_TABLE + len(_neul84.PARAMETER_TABLES),
        _chaos9e.OFF_RUNTIME + len(_chaos9e.RUNTIME),
        _phantom_preset.OFF_RUNTIME + len(_phantom_preset.RUNTIME),
        _fairy9c.OFF_RUNTIME + len(_fairy9c.RUNTIME),
        _radiance9d.OFF_RUNTIME + len(_radiance9d.RUNTIME),
        _ghostb0.OFF_RUNTIME + len(_ghostb0.RUNTIME),
        _ghostb0.OFF_PARAMETER_TABLE + len(_ghostb0.PARAMETER_TABLES),
        _panel.OFF_FINAL_STATIC_MARKER_HELPER + len(_panel.FINAL_STATIC_MARKER_HELPER),
        ENTRY_CENTER_LIMIT,
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
        (
            _ice.ORIG_ANIM_UPDATE_CALL,
            LEGACY_HOOK_ANIM_UPDATE_CALL,
            HOOK_ANIM_UPDATE_CALL,
        ),
        "$8676 new enemy animation hook",
    )
    _expect_one(
        rom_data,
        _ice.OFF_INIT_WRITE_CALL,
        (
            _ice.ORIG_INIT_WRITE_CALL,
            LEGACY_HOOK_INIT_WRITE_CALL,
            HOOK_INIT_WRITE_CALL,
        ),
        "$A2F2 new enemy init hook",
    )
    _expect_one(
        rom_data,
        _ice.OFF_SETUP_META_LOAD,
        (
            _ice.ORIG_SETUP_META_LOAD,
            LEGACY_HOOK_SETUP_META_LOAD,
            HOOK_SETUP_META_LOAD,
        ),
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
    legacy_entry_center = _expect_entry_center(rom_data)
    _spark_trail.validate(rom_data)

    changed: list[str] = []
    changed.extend(_spark_variant.apply(rom_data))
    changed.extend(_spark_trail.apply(rom_data))
    _write(rom_data, _ice.OFF_AI_DISPATCH_CALL, HOOK_AI_DISPATCH_CALL, changed, "$A1C3 new enemy AI dispatch hook")
    _write(rom_data, _ice.OFF_ANIM_UPDATE_CALL, HOOK_ANIM_UPDATE_CALL, changed, "$8676 new enemy animation hook")
    _write(rom_data, _ice.OFF_INIT_WRITE_CALL, HOOK_INIT_WRITE_CALL, changed, "$A2F2 new enemy init/status hook")
    _write(rom_data, _ice.OFF_SETUP_META_LOAD, HOOK_SETUP_META_LOAD, changed, "$8ACB new enemy setup group hook")
    _write(
        rom_data,
        OFF_AI_ENTRY,
        CURRENT_ENTRY_CENTER_IMAGE,
        changed,
        (
            f"${CPU_AI_ENTRY:04X}-"
            f"${CPU_ANIM_ENTRY + len(ANIM_ENTRY_RUNTIME) - 1:04X} "
            "new enemy entry center"
        ),
    )
    if legacy_entry_center:
        _write(
            rom_data,
            OFF_AI_ENTRY + ENTRY_CENTER_SIZE,
            bytes((0xEA,)) * ENTRY_CENTER_FREE_SIZE,
            changed,
            "$BD50-$BD8C released entry-center space",
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

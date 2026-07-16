"""Shared dispatch entries for new enemy IDs in mapper66 saved ROMs."""
from __future__ import annotations

from . import ice_flame_runtime as _ice
from . import spark24_runtime as _spark24
from . import spark85_runtime as _spark85
from . import spark_ball_variant as _spark_variant
from . import ghost86_runtime as _ghost86
from . import neul88_runtime as _neul88
from . import flying_dragon89_runtime as _flying89
from . import afterburner90_runtime as _after90
from . import ghostb0_runtime as _ghostb0
from . import phantom_preset_runtime as _phantom_preset
from . import fairy9c_runtime as _fairy9c
from . import seraphic_radiance9d_runtime as _radiance9d


class NewEnemyRuntimeError(ValueError):
    pass


ICE_FLAME_ID = _ice.NEW_ENEMY_ID
SPARK24_FIRST_ID = _spark24.FIRST_ID
SPARK24_LAST_ID = _spark24.LAST_ID
GHOST86_ID = _ghost86.NEW_ENEMY_ID
NEUL88_ID = _neul88.NEW_ENEMY_ID
CHAOS89_ID = _flying89.NEW_ENEMY_ID
AFTER90_ID = _after90.NEW_ENEMY_ID
PHANTOM_PRESET_FIRST_ID = _phantom_preset.FIRST_ID
PHANTOM_PRESET_LAST_ID = _phantom_preset.LAST_ID
FAIRY9C_ID = _fairy9c.NEW_ENEMY_ID
RADIANCE9D_ID = _radiance9d.NEW_ENEMY_ID
GHOSTB0_FIRST_ID = _ghostb0.FIRST_ID
GHOSTB0_LAST_ID = _ghostb0.LAST_ID

OLD_GHOST86_OFF_RUNTIME = 0x6D88
LEGACY_ICE_AI_DISPATCH = 0xE9C1
LEGACY_ICE_SETUP_META_LOAD = 0xE9C4

OFF_AI_ENTRY = 0x3BF2      # CPU $BBE2
OFF_SETUP_ENTRY = 0x3C4A
OFF_INIT_ENTRY = 0x3CA5
OFF_ANIM_ENTRY = 0x3CFC

CPU_AI_ENTRY = 0xBBE2
CPU_SETUP_ENTRY = 0xBC3A
CPU_INIT_ENTRY = 0xBC95
CPU_ANIM_ENTRY = 0xBCEC

OFF_GHOSTB0_EXTENSION = 0x3D78
CPU_GHOSTB0_AI_CLASSIFY = 0xBD68
CPU_GHOSTB0_SETUP_CLASSIFY = 0xBD74
CPU_GHOSTB0_INIT_CLASSIFY = 0xBD83

OLD_AI_ENTRY_RUNTIME = bytes.fromhex(
    "48"
    "18"
    "69 14"
    "c9 84"
    "f0 04"
    "68"
    "4c 29 a3"
    "68"
    f"4c {LEGACY_ICE_AI_DISPATCH & 0xFF:02x} {LEGACY_ICE_AI_DISPATCH >> 8:02x}"
)

def _build_ai_entry_runtime() -> bytes:
    data = bytearray((0x48, 0x18, 0x69, 0x14))
    fixups: list[tuple[int, int]] = []
    targets = (
        (GHOST86_ID, _ghost86.CPU_AI_DISPATCH),
        (0x87, _ghost86.CPU_AI_DISPATCH_DOWN),
        (NEUL88_ID, _neul88.CPU_AI_DISPATCH),
        (CHAOS89_ID, _flying89.CPU_AI_DISPATCH),
        (AFTER90_ID, _after90.CPU_AI_DISPATCH),
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
    for operand_pos, target_index in fixups:
        rel = target_offsets[target_index] - (operand_pos + 1)
        if not -128 <= rel <= 127:
            raise ValueError("AI entry branch out of range")
        data[operand_pos] = rel & 0xFF
    return bytes(data)


AI_ENTRY_RUNTIME = _build_ai_entry_runtime()
PRE_PACKED_GHOST_AI_ENTRY_RUNTIME = bytes.fromhex(
    "48"
    "18"
    "69 14"
    "c9 84"
    "f0 10"
    "c9 85"
    "f0 10"
    "c9 86"
    "f0 10"
    "c9 87"
    "f0 10"
    "68"
    "4c 29 a3"
    "68"
    f"4c {LEGACY_ICE_AI_DISPATCH & 0xFF:02x} {LEGACY_ICE_AI_DISPATCH >> 8:02x}"
    "68"
    f"4c {_spark85.CPU_AI_DISPATCH & 0xFF:02x} {_spark85.CPU_AI_DISPATCH >> 8:02x}"
    "68"
    "4c 92 ed"
    "68"
    "4c 96 ed"
)

OLD_SETUP_ENTRY_RUNTIME = bytes.fromhex(
    "a0 01"
    "b1 08"
    "c9 84"
    "f0 06"
    "a4 0e"
    "b9 d3 d9"
    "60"
    f"4c {LEGACY_ICE_SETUP_META_LOAD & 0xFF:02x} {LEGACY_ICE_SETUP_META_LOAD >> 8:02x}"
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


def _build_setup_entry_runtime() -> bytes:
    a = _EntryAsm()
    a.b(0xA0, 0x01, 0xB1, 0x08)         # LDA ($08),Y -> main-slot type
    a.b(0xC9, SPARK24_FIRST_ID)
    a.branch(0x90, "below_spark24")
    a.b(0xC9, SPARK24_LAST_ID + 1)
    a.branch(0x90, "spark24")
    a.label("below_spark24")
    a.b(0xC9, ICE_FLAME_ID + 1)          # $82 uses the stock-computed Flame group
    a.branch(0x90, "stock")
    a.b(0xC9, NEUL88_ID)
    a.branch(0xF0, "neul88")
    a.b(0xC9, CHAOS89_ID)
    a.branch(0xF0, "chaos89")
    a.b(0xC9, AFTER90_ID)
    a.branch(0xF0, "after90")
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
    a.b(0x38, 0xE9, GHOST86_ID - 2, 0xAA)  # $84-$87 setup table
    a.b(0xBD, _ghost86.CPU_SETUP_GROUP_TABLE & 0xFF, _ghost86.CPU_SETUP_GROUP_TABLE >> 8)
    a.b(0x85, 0x0E, 0xA8, 0xB9, 0xD3, 0xD9, 0x60)
    a.label("neul88")
    a.jmp(_neul88.CPU_SETUP_META_LOAD)
    a.label("chaos89")
    a.jmp(_flying89.CPU_SETUP_META_LOAD)
    a.label("after90")
    a.jmp(_after90.CPU_SETUP_META_LOAD)
    a.label("fairy9c")
    a.jmp(_fairy9c.CPU_SETUP_META_LOAD)
    a.label("radiance9d")
    a.jmp(_radiance9d.CPU_SETUP_META_LOAD)
    a.label("spark24")
    a.b(0xA9, 0x14, 0x85, 0x0E, 0xA8, 0xB9, 0xD3, 0xD9, 0x60)
    a.label("stock")
    a.jmp(CPU_GHOSTB0_SETUP_CLASSIFY)
    a.b(0xEA, 0xEA, 0xEA)
    return a.finish()


SETUP_ENTRY_RUNTIME = _build_setup_entry_runtime()
PRE_PACKED_GHOST_SETUP_ENTRY_RUNTIME = bytes.fromhex(
    "a0 01"
    "b1 08"
    "c9 84"
    "90 12"
    "c9 88"
    "b0 0e"
    "38"
    "e9 84"
    "aa"
    "bd 78 ed"
    "85 0e"
    "a8"
    "b9 d3 d9"
    "60"
    "a4 0e"
    "b9 d3 d9"
    "60"
)

OLD_INIT_ENTRY_RUNTIME = bytes.fromhex(
    "20 1c 9d"
    "a5 05"
    "c9 84"
    "f0 01"
    "60"
    f"4c {_ice.CPU_INIT_STATUS & 0xFF:02x} {_ice.CPU_INIT_STATUS >> 8:02x}"
)

def _build_init_entry_runtime() -> bytes:
    a = _EntryAsm()
    a.b(0x48, 0xA5, 0x05)               # PHA; LDA $05
    a.b(0xC9, SPARK24_FIRST_ID)
    a.branch(0x90, "below_spark24")
    a.b(0xC9, SPARK24_LAST_ID + 1)
    a.branch(0x90, "spark24")
    a.label("below_spark24")
    a.b(0xC9, GHOST86_ID)
    a.branch(0xF0, "ghost")
    a.b(0xC9, 0x87)
    a.branch(0xF0, "ghost")
    a.b(0xC9, NEUL88_ID)
    a.branch(0xF0, "neul88")
    a.b(0xC9, CHAOS89_ID)
    a.branch(0xF0, "chaos89")
    a.b(0xC9, AFTER90_ID)
    a.branch(0xF0, "after90")
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
    a.b(0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA)
    a.label("ice")
    a.jmp(_ice.CPU_INIT_STATUS)
    a.label("spark24")
    a.b(0x68, 0x20, 0x1C, 0x9D, 0x60)
    a.label("ghost")
    a.jmp(_ghost86.CPU_INIT_STATUS)
    a.label("neul88")
    a.jmp(_neul88.CPU_INIT_STATUS)
    a.label("chaos89")
    a.jmp(_flying89.CPU_INIT_STATUS)
    a.label("after90")
    a.jmp(_after90.CPU_INIT_STATUS)
    a.label("fairy9c")
    a.jmp(_fairy9c.CPU_INIT_STATUS)
    a.label("radiance9d")
    a.jmp(_radiance9d.CPU_INIT_STATUS)
    return a.finish()


INIT_ENTRY_RUNTIME = _build_init_entry_runtime()
PRE_PACKED_GHOST_INIT_ENTRY_RUNTIME = bytes.fromhex(
    "48"
    "a5 05"
    "c9 86"
    "f0 04"
    "c9 87"
    "d0 03"
    "4c 7c ed"
    "c9 85"
    "f0 0e"
    "68"
    "20 1c 9d"
    "a5 05"
    "c9 84"
    "f0 01"
    "60"
    f"4c {_ice.CPU_INIT_STATUS & 0xFF:02x} {_ice.CPU_INIT_STATUS >> 8:02x}"
    "68"
    f"4c {_spark85.CPU_INIT_STATUS & 0xFF:02x} {_spark85.CPU_INIT_STATUS >> 8:02x}"
)

OLD_ANIM_ENTRY_RUNTIME = bytes.fromhex(
    "a0 01"         # LDY #$01
    "b1 08"         # LDA ($08),Y -> main-slot type
    "c9 84"         # CMP #$84
    "f0 03"         # BEQ ice
    "4c 89 87"      # JMP $8789 stock animation updater
    f"4c {_ice.CPU_ANIM_UPDATE & 0xFF:02x} {_ice.CPU_ANIM_UPDATE >> 8:02x}"
)

PRE_BULLET_PALETTE_ANIM_ENTRY_RUNTIME = bytes.fromhex(
    "a0 01"         # LDY #$01
    "b1 08"         # LDA ($08),Y -> main-slot type
    "c9 84"         # CMP #$84
    "f0 07"         # BEQ ice
    f"c9 {FAIRY9C_ID:02x}"  # CMP #$9C
    "f0 06"         # BEQ fairy9c
    "4c 89 87"      # JMP $8789 stock animation updater
    f"4c {_ice.CPU_ANIM_UPDATE & 0xFF:02x} {_ice.CPU_ANIM_UPDATE >> 8:02x}"
    "20 89 87"      # fairy9c: JSR $8789 stock animation updater
    "a0 13"         # LDY #$13
    "b1 08"         # LDA ($08),Y: stock frame attr
    "29 13"         # AND #$13: preserve Fairy flip bits used by the OAM writer
    "09 48"         # ORA #$48: force Dark Fairy palette
    "91 08"         # STA ($08),Y: overwrite frame attr after stock animation
    "60"            # RTS
)

def _build_anim_entry_runtime() -> bytes:
    a = _EntryAsm()
    a.b(0xA0, 0x01, 0xB1, 0x08)
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
    a.b(0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA)
    return a.finish()


ANIM_ENTRY_RUNTIME = _build_anim_entry_runtime()

GHOSTB0_EXTENSION_RUNTIME = bytes.fromhex(
    # AI: the restored dispatch value is enemy ID minus $14.
    f"29 fc c9 {GHOSTB0_FIRST_ID - 0x14:02x} d0 03 "
    f"4c {_ghostb0.CPU_AI_DISPATCH & 0xFF:02x} {_ghostb0.CPU_AI_DISPATCH >> 8:02x} "
    "4c 29 a3 "
    # Setup: A still contains the enemy ID.
    f"29 fc c9 {GHOSTB0_FIRST_ID:02x} d0 03 "
    f"4c {_ghostb0.CPU_SETUP_META_LOAD & 0xFF:02x} {_ghostb0.CPU_SETUP_META_LOAD >> 8:02x} "
    "a4 0e b9 d3 d9 60 "
    # Init: the original hook input remains on the stack.
    f"a5 05 29 fc c9 {GHOSTB0_FIRST_ID:02x} d0 03 "
    f"4c {_ghostb0.CPU_INIT_STATUS & 0xFF:02x} {_ghostb0.CPU_INIT_STATUS >> 8:02x} "
    "68 20 1c 9d a5 05 "
    f"c9 {ICE_FLAME_ID:02x} d0 03 "
    f"4c {_ice.CPU_INIT_STATUS & 0xFF:02x} {_ice.CPU_INIT_STATUS >> 8:02x} "
    "60"
)

PRE_GHOSTB0_AI_ENTRY_RUNTIME = bytes.fromhex(
    "48186914c986f034c987f034c988f034c989f034c98af034c99cf034c99df034"
    "c9a09008c9b0b004684cbdbdc9c09008c9d8b004684cc0be684c29a3684ca2ed"
    "684ca6ed684c25ee684cbeee684ce0ee684c1ee0684c28ec"
)
PRE_GHOSTB0_SETUP_ENTRY_RUNTIME = bytes.fromhex(
    "a001b108c9c09004c9d89040c9839045c988f029c989f028c98af027c99cf026"
    "c99df025c9a09007c9b0b0294c9cbd38e984aabd88ed850ea8b9d3d9604c06ee"
    "4ca4ee4cc1ee4c00e04cf4eba914850ea8b9d3d960a40eb9d3d960"
)
PRE_GHOSTB0_INIT_ENTRY_RUNTIME = bytes.fromhex(
    "48a505c9c09004c9d89035c986f036c987f032c988f031c989f030c98af02fc99c"
    "f02ec99df02dc9a09007c9b0b0034ca5bd68201c9da505c982f001604c75e06820"
    "1c9d604c8ced4c0fee4caeee4ccaee4c09e04cfceb"
)
PRE_GHOSTB0_ANIM_ENTRY_RUNTIME = bytes.fromhex(
    "a001b108c9c09004c9d8906dc982f02dc99cf03ac99df05ec9a09004c9b0902029"
    "fec95ef036c962f032c96af02ec96ef038c972f026c976f0304c89874c92e02089"
    "87a013b10829330948910860208987a013b10829130948910860208987a013b108"
    "29330948910860208987a013b10829339108604c01ed4c8987"
)

ENTRY_RUNTIMES = (
    (OFF_AI_ENTRY, AI_ENTRY_RUNTIME, (PRE_GHOSTB0_AI_ENTRY_RUNTIME,), "$BBE2 new enemy AI dispatch"),
    (OFF_SETUP_ENTRY, SETUP_ENTRY_RUNTIME, (PRE_GHOSTB0_SETUP_ENTRY_RUNTIME,), f"${CPU_SETUP_ENTRY:04X} new enemy setup dispatch"),
    (OFF_INIT_ENTRY, INIT_ENTRY_RUNTIME, (PRE_GHOSTB0_INIT_ENTRY_RUNTIME,), f"${CPU_INIT_ENTRY:04X} new enemy init dispatch"),
    (OFF_ANIM_ENTRY, ANIM_ENTRY_RUNTIME, (OLD_ANIM_ENTRY_RUNTIME, PRE_BULLET_PALETTE_ANIM_ENTRY_RUNTIME, PRE_GHOSTB0_ANIM_ENTRY_RUNTIME), f"${CPU_ANIM_ENTRY:04X} new enemy animation dispatch"),
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
    *_ghost86.RESERVED_SPANS,
    *_neul88.RESERVED_SPANS,
    *_flying89.RESERVED_SPANS,
    *_after90.RESERVED_SPANS,
    *_phantom_preset.RESERVED_SPANS,
    *_fairy9c.RESERVED_SPANS,
    *_radiance9d.RESERVED_SPANS,
    *_ghostb0.RESERVED_SPANS,
)

assert len(PRE_PACKED_GHOST_AI_ENTRY_RUNTIME) == 40
assert len(PRE_PACKED_GHOST_SETUP_ENTRY_RUNTIME) == 32
assert len(PRE_PACKED_GHOST_INIT_ENTRY_RUNTIME) == 36
assert len(OLD_ANIM_ENTRY_RUNTIME) == 14
assert len(PRE_BULLET_PALETTE_ANIM_ENTRY_RUNTIME) == 32
assert len(AI_ENTRY_RUNTIME) == len(PRE_GHOSTB0_AI_ENTRY_RUNTIME)
assert len(SETUP_ENTRY_RUNTIME) == len(PRE_GHOSTB0_SETUP_ENTRY_RUNTIME)
assert len(INIT_ENTRY_RUNTIME) == len(PRE_GHOSTB0_INIT_ENTRY_RUNTIME)
assert len(ANIM_ENTRY_RUNTIME) == len(PRE_GHOSTB0_ANIM_ENTRY_RUNTIME)
assert len(GHOSTB0_EXTENSION_RUNTIME) == 52
assert OFF_SETUP_ENTRY == OFF_AI_ENTRY + len(AI_ENTRY_RUNTIME)
assert OFF_INIT_ENTRY == OFF_SETUP_ENTRY + len(SETUP_ENTRY_RUNTIME)
assert OFF_ANIM_ENTRY == OFF_INIT_ENTRY + len(INIT_ENTRY_RUNTIME)


def levels_need_runtime(levels: list) -> bool:
    return (
        _ice.levels_need_runtime(levels)
        or any(
            _spark24.FIRST_ID <= int(getattr(enemy, "element_no", -1)) <= _spark24.LAST_ID
            for lv in (levels or [])
            for enemy in (getattr(lv, "enemies", []) or [])
        )
        or _ghost86.levels_need_runtime(levels)
        or _neul88.levels_need_runtime(levels)
        or _flying89.levels_need_runtime(levels)
        or _after90.levels_need_runtime(levels)
        or any(
            PHANTOM_PRESET_FIRST_ID <= int(getattr(enemy, "element_no", -1)) <= PHANTOM_PRESET_LAST_ID
            for lv in (levels or [])
            for enemy in (getattr(lv, "enemies", []) or [])
        )
        or _fairy9c.levels_need_runtime(levels)
        or _radiance9d.levels_need_runtime(levels)
        or _ghostb0.levels_need_runtime(levels)
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


def _expect_blank_or_one_of(data: bytes | bytearray, off: int, allowed: tuple[bytes, ...], name: str) -> None:
    size = max(len(blob) for blob in allowed)
    cur = bytes(data[off:off + size])
    if all(b in (0xEA, 0x00) for b in cur):
        return
    for blob in allowed:
        if cur[:len(blob)] == blob and all(b in (0xEA, 0x00) for b in cur[len(blob):]):
            return
    expected = " or ".join(blob.hex(" ") for blob in allowed)
    raise NewEnemyRuntimeError(
        f"{name} area is not blank at 0x{off:X}: expected EA/00 or {expected}, got {cur.hex(' ')}"
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
        _ghost86.OFF_RUNTIME + len(_ghost86.RUNTIME),
        _neul88.OFF_RUNTIME + len(_neul88.RUNTIME),
        _flying89.OFF_RUNTIME + len(_flying89.RUNTIME),
        _after90.OFF_RUNTIME + len(_after90.RUNTIME),
        _phantom_preset.OFF_RUNTIME + len(_phantom_preset.RUNTIME),
        _fairy9c.OFF_RUNTIME + len(_fairy9c.RUNTIME),
        _radiance9d.OFF_RUNTIME + len(_radiance9d.RUNTIME),
        _ghostb0.OFF_RUNTIME + len(_ghostb0.RUNTIME),
        OFF_GHOSTB0_EXTENSION + len(GHOSTB0_EXTENSION_RUNTIME),
        max(off + len(blob) for off, blob, _old_blobs, _name in ENTRY_RUNTIMES),
    )
    if rom_data is None or len(rom_data) < max_end:
        raise NewEnemyRuntimeError("ROM is too short for new enemy runtime.")

    changed: list[str] = []
    changed.extend(_spark_variant.apply(rom_data))
    if OLD_GHOST86_OFF_RUNTIME != _ghost86.OFF_RUNTIME:
        old_ghost_cur = bytes(rom_data[OLD_GHOST86_OFF_RUNTIME:OLD_GHOST86_OFF_RUNTIME + len(_ghost86.RUNTIME)])
        if old_ghost_cur == _ghost86.RUNTIME:
            rom_data[OLD_GHOST86_OFF_RUNTIME:OLD_GHOST86_OFF_RUNTIME + len(_ghost86.RUNTIME)] = (
                bytes((0xEA,)) * len(_ghost86.RUNTIME)
            )
            changed.append("old Bomber/Cannon Ghost runtime area cleared for packed relocation")

    _expect_one(
        rom_data,
        _ice.OFF_AI_DISPATCH_CALL,
        (_ice.ORIG_AI_DISPATCH_CALL, _ice.HOOK_AI_DISPATCH_CALL, HOOK_AI_DISPATCH_CALL),
        "$A1C3 new enemy AI dispatch hook",
    )
    _expect_one(
        rom_data,
        _ice.OFF_ANIM_UPDATE_CALL,
        (_ice.ORIG_ANIM_UPDATE_CALL, _ice.HOOK_ANIM_UPDATE_CALL, HOOK_ANIM_UPDATE_CALL),
        "$8676 new enemy animation hook",
    )
    _expect_one(
        rom_data,
        _ice.OFF_INIT_WRITE_CALL,
        (_ice.ORIG_INIT_WRITE_CALL, _ice.HOOK_INIT_WRITE_CALL, HOOK_INIT_WRITE_CALL),
        "$A2F2 new enemy init hook",
    )
    _expect_one(
        rom_data,
        _ice.OFF_SETUP_META_LOAD,
        (_ice.ORIG_SETUP_META_LOAD, _ice.HOOK_SETUP_META_LOAD, HOOK_SETUP_META_LOAD),
        "$8ACB new enemy setup hook",
    )
    _expect_one(
        rom_data,
        _ice.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_ice.RUNTIME), _ice.RUNTIME),
        "Ice Flame runtime area",
    )
    _expect_one(
        rom_data,
        _ghost86.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_ghost86.RUNTIME), _ghost86.RUNTIME),
        "Bomber/Cannon Ghost runtime area",
    )
    _expect_one(
        rom_data,
        _neul88.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_neul88.RUNTIME), _neul88.RUNTIME),
        "Neul88 runtime area",
    )
    _expect_one(
        rom_data,
        _flying89.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_flying89.RUNTIME), _flying89.RUNTIME),
        "Chaos Dragon89 runtime area",
    )
    _expect_one(
        rom_data,
        _after90.OFF_RUNTIME,
        (bytes((0xEA,)) * len(_after90.RUNTIME), _after90.RUNTIME),
        "Back Fire90 runtime area",
    )
    phantom_settings = _phantom_preset.current_settings(rom_data)
    phantom_runtime, _phantom_offsets = _phantom_preset.build_runtime(
        phantom_settings["groups"],
    )
    _expect_blank_or_one_of(
        rom_data,
        _phantom_preset.OFF_RUNTIME,
        (phantom_runtime,),
        "Phantom preset runtime area",
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
    for off, blob, old_blobs, name in ENTRY_RUNTIMES:
        _expect_blank_or_one_of(rom_data, off, (blob, *old_blobs), name)

    _write(rom_data, _ice.OFF_AI_DISPATCH_CALL, HOOK_AI_DISPATCH_CALL, changed, "$A1C3 new enemy AI dispatch hook")
    _write(rom_data, _ice.OFF_ANIM_UPDATE_CALL, HOOK_ANIM_UPDATE_CALL, changed, "$8676 new enemy animation hook")
    _write(rom_data, _ice.OFF_INIT_WRITE_CALL, HOOK_INIT_WRITE_CALL, changed, "$A2F2 new enemy init/status hook")
    _write(rom_data, _ice.OFF_SETUP_META_LOAD, HOOK_SETUP_META_LOAD, changed, "$8ACB new enemy setup group hook")
    for off, blob, _old_blobs, name in ENTRY_RUNTIMES:
        _write(rom_data, off, blob, changed, name)
    _write(
        rom_data,
        OFF_GHOSTB0_EXTENSION,
        GHOSTB0_EXTENSION_RUNTIME,
        changed,
        "$BD68-$BD9B Ghost B0-B3 entry classification extension",
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
        _ghost86.OFF_RUNTIME,
        _ghost86.RUNTIME,
        changed,
        f"Bomber/Cannon Ghost runtime ${_ghost86.CPU_RUNTIME:04X}-${_ghost86.CPU_RUNTIME_END - 1:04X}",
    )
    _write(
        rom_data,
        _neul88.OFF_RUNTIME,
        _neul88.RUNTIME,
        changed,
        f"Neul88 runtime ${_neul88.CPU_RUNTIME:04X}-${_neul88.CPU_RUNTIME_END - 1:04X}",
    )
    _write(
        rom_data,
        _flying89.OFF_RUNTIME,
        _flying89.RUNTIME,
        changed,
        f"Chaos Dragon89 runtime ${_flying89.CPU_RUNTIME:04X}-${_flying89.CPU_RUNTIME_END - 1:04X}",
    )
    _write(
        rom_data,
        _after90.OFF_RUNTIME,
        _after90.RUNTIME,
        changed,
        f"Back Fire90 runtime ${_after90.CPU_RUNTIME:04X}-${_after90.CPU_RUNTIME_END - 1:04X}",
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
    _write(
        rom_data,
        _ghostb0.OFF_RUNTIME,
        _ghostb0.RUNTIME,
        changed,
        f"Ghost B0-B3 runtime ${_ghostb0.CPU_RUNTIME:04X}-${_ghostb0.CPU_RUNTIME_END - 1:04X}",
    )
    return changed

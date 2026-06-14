"""Solomon's Seal stage dispatch editing.

This module only rewrites the original per-room special-process dispatch
table.  It updates both the 8-room section bases and per-room offsets, but it
does not add runtime code or expand ROM data.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import special_process
from .region import base_region


class SolomonSealStageError(ValueError):
    pass


@dataclass(frozen=True)
class SealSlotSpec:
    slot: int
    bit: int
    default_stage: int
    script_file: int


SLOTS: tuple[SealSlotSpec, ...] = (
    SealSlotSpec(0, 0x01, 9, 0x344B),
    SealSlotSpec(1, 0x02, 13, 0x3454),
    SealSlotSpec(2, 0x04, 17, 0x345A),
    SealSlotSpec(3, 0x08, 19, 0x3488),
    SealSlotSpec(4, 0x10, 21, 0x34A7),
    SealSlotSpec(5, 0x20, 29, 0x353A),
    SealSlotSpec(6, 0x40, 46, 0x3582),
    SealSlotSpec(7, 0x80, 47, 0x358A),
)

# 1-based stage -> original dispatch offset with the Seal call removed.
BASELINE_OFFSETS = {
    1: 0x00,
    2: 0x00,
    3: 0x00,
    4: 0x01,
    5: 0x01,
    6: 0x00,
    7: 0x01,
    8: 0x00,
    9: 0x05,
    10: 0x06,
    11: 0x05,
    12: 0x05,
    13: 0x05,
    14: 0x05,
    15: 0x05,
    16: 0x05,
    17: 0x06,
    18: 0x2C,
    19: 0x34,
    20: 0x37,
    21: 0x00,
    22: 0x00,
    23: 0x00,
    24: 0x2C,
    25: 0x00,
    26: 0x00,
    27: 0x00,
    28: 0x00,
    29: 0x00,
    30: 0x06,
    31: 0x00,
    32: 0x00,
    33: 0x00,
    34: 0x00,
    35: 0x00,
    36: 0x00,
    37: 0x00,
    38: 0x27,
    39: 0x01,
    40: 0x00,
    41: 0x00,
    42: 0x00,
    43: 0x00,
    44: 0x00,
    45: 0x00,
    46: 0x06,
    47: 0x00,
    48: 0x00,
}

ORIGINAL_SECTION_BASES = (
    0x3447,
    0x344B,
    0x3459,
    0x3539,
    0x3553,
    0x3581,
)


def supported(region: str) -> bool:
    return base_region(region) == "JP"


def _dispatch_table_offset(region: str) -> int:
    table = special_process.get_dispatch_table(base_region(region))
    if table is None:
        raise SolomonSealStageError("Solomon Seal stage editing supports JP ROMs only.")
    return table


def _dispatch_entry_offset(region: str, stage: int) -> int:
    if not (1 <= int(stage) <= special_process.NUM_LEVELS):
        raise SolomonSealStageError(f"Stage out of range: {stage}")
    return _dispatch_table_offset(region) + special_process.SECTION_HEADER_BYTES + int(stage) - 1


def _section_index(stage: int) -> int:
    return (int(stage) - 1) // 8


def _read_dispatch_offset(rom_data: bytes, region: str, stage: int) -> int:
    off = _dispatch_entry_offset(region, stage)
    if rom_data is None or off >= len(rom_data):
        raise SolomonSealStageError("ROM is too short for special-process dispatch table.")
    return int(rom_data[off]) & 0xFF


def _section_base_file(rom_data: bytes, region: str, stage: int) -> int:
    level_no = int(stage) - 1
    table = _dispatch_table_offset(region)
    section_idx = level_no // 8
    lo = rom_data[table + section_idx * 2]
    hi = rom_data[table + section_idx * 2 + 1]
    return lo + hi * 256 - special_process.RAM_TO_ROM_DIFF


def _dispatch_value_for_stage(rom_data: bytes, region: str, spec: SealSlotSpec, stage: int) -> int:
    base = _section_base_file(rom_data, region, stage)
    value = int(spec.script_file) - base
    if not (0 <= value <= 0xFF):
        raise SolomonSealStageError(
            f"封印{spec.slot + 1}は{stage}面の特殊処理範囲から参照できません。"
        )
    return value


def candidates(slot: int, rom_data: bytes, region: str) -> tuple[int, ...]:
    return tuple(range(1, 49))


def _baseline_script_file(stage: int) -> int:
    stage = int(stage)
    if stage not in BASELINE_OFFSETS:
        raise SolomonSealStageError(f"Unsupported dispatch stage: {stage}")
    return ORIGINAL_SECTION_BASES[_section_index(stage)] + BASELINE_OFFSETS[stage]


def _write_section_base(rom_data: bytearray, region: str, section_idx: int, base_file: int) -> None:
    table = _dispatch_table_offset(region)
    cpu = int(base_file) + special_process.RAM_TO_ROM_DIFF
    rom_data[table + section_idx * 2] = cpu & 0xFF
    rom_data[table + section_idx * 2 + 1] = (cpu >> 8) & 0xFF


def _dispatch_plan(stages: list[int]) -> tuple[list[int], dict[int, int]]:
    stage_to_script = {stage: _baseline_script_file(stage) for stage in range(1, 49)}
    for spec, stage in zip(SLOTS, stages):
        stage_to_script[int(stage)] = int(spec.script_file)
    section_bases: list[int] = []
    for section_idx in range(6):
        section_stages = range(section_idx * 8 + 1, section_idx * 8 + 9)
        scripts = [stage_to_script[stage] for stage in section_stages]
        base = min(scripts)
        if max(scripts) - base > 0xFF:
            raise SolomonSealStageError(
                f"{section_idx * 8 + 1}〜{section_idx * 8 + 8}面の特殊処理範囲に収まりません。"
            )
        section_bases.append(base)
    return section_bases, stage_to_script


def defaults() -> list[int]:
    return [spec.default_stage for spec in SLOTS]


def current_stages(rom_data: bytes, region: str) -> list[int]:
    if not supported(region):
        return defaults()
    stages: list[int] = []
    for spec in SLOTS:
        found = None
        for stage in range(1, 49):
            try:
                script_file = _section_base_file(rom_data, region, stage) + _read_dispatch_offset(rom_data, region, stage)
                if script_file == spec.script_file:
                    found = stage
                    break
            except SolomonSealStageError:
                break
        stages.append(found if found is not None else spec.default_stage)
    return stages


def validate_stages(stages: list[int] | tuple[int, ...]) -> list[int]:
    if len(stages) != len(SLOTS):
        raise SolomonSealStageError("Solomon Seal stage list must contain 8 stages.")
    values = [int(v) for v in stages]
    if len(set(values)) != len(values):
        raise SolomonSealStageError("同じ面に複数のソロモンの封印は配置できません。")
    if any(values[i] >= values[i + 1] for i in range(len(values) - 1)):
        raise SolomonSealStageError(
            "封印1〜8は、封印1 < 封印2 < ... < 封印8 の順に配置してください。"
        )
    for spec, stage in zip(SLOTS, values):
        if not (1 <= int(stage) <= 48):
            raise SolomonSealStageError(f"封印{spec.slot + 1}は1〜48面に配置してください。")
    if values[3] > 20:
        raise SolomonSealStageError("封印4は20面までに配置してください。")
    if values[5] > 44:
        raise SolomonSealStageError("封印6は44面までに配置してください。")
    if values[7] > 48:
        raise SolomonSealStageError("封印8は48面までに配置してください。")
    _dispatch_plan(values)
    return values


def apply(rom_data: bytearray, region: str, stages: list[int] | tuple[int, ...]) -> list[str]:
    if not supported(region):
        return []
    values = validate_stages(stages)
    before = current_stages(bytes(rom_data), region)
    section_bases, stage_to_script = _dispatch_plan(values)
    changed: list[str] = []
    for section_idx, base in enumerate(section_bases):
        _write_section_base(rom_data, region, section_idx, base)
    for stage in range(1, 49):
        off = _dispatch_entry_offset(region, stage)
        if off >= len(rom_data):
            raise SolomonSealStageError("ROM is too short for special-process dispatch table.")
        dispatch_value = stage_to_script[stage] - section_bases[_section_index(stage)]
        if rom_data[off] != dispatch_value:
            rom_data[off] = dispatch_value
    for spec, stage in zip(SLOTS, values):
        if before[spec.slot] != stage:
            changed.append(f"封印{spec.slot + 1} -> {stage}面")
    return changed

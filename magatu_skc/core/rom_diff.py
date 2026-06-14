"""Structured ROM stage comparison helpers."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from . import constants as c
from .element import Wall
from .level import load_all_levels
from .rom import Rom


@dataclass
class StageDiff:
    stage_no: int
    block_changes: int = 0
    item_changes: int = 0
    enemy_changes: int = 0
    meta_changes: int = 0
    details: list[str] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return (
            self.block_changes
            + self.item_changes
            + self.enemy_changes
            + self.meta_changes
        )

    @property
    def changed(self) -> bool:
        return self.total_changes > 0

    def summary_text(self) -> str:
        parts = []
        if self.block_changes:
            parts.append(f"ブロック{self.block_changes}")
        if self.item_changes:
            parts.append(f"アイテム{self.item_changes}")
        if self.enemy_changes:
            parts.append(f"敵{self.enemy_changes}")
        if self.meta_changes:
            parts.append(f"メタ{self.meta_changes}")
        return " / ".join(parts) if parts else "変更なし"


@dataclass
class RomDiffResult:
    left_name: str
    right_name: str
    left_crc: str
    right_crc: str
    left_region: str
    right_region: str
    left_rom: Rom = field(repr=False)
    right_rom: Rom = field(repr=False)
    left_levels: list = field(repr=False)
    right_levels: list = field(repr=False)
    stages: list[StageDiff]

    @property
    def changed_stage_count(self) -> int:
        return sum(1 for stage in self.stages if stage.changed)

    @property
    def total_changes(self) -> int:
        return sum(stage.total_changes for stage in self.stages)


def compare_rom_stage_data(left_path: str, right_path: str) -> RomDiffResult:
    left_rom = Rom.load(left_path)
    right_rom = Rom.load(right_path)
    left_levels = load_all_levels(left_rom)
    right_levels = load_all_levels(right_rom)

    stage_count = min(len(left_levels), len(right_levels))
    stages = [
        compare_levels(left_levels[i], right_levels[i], i + 1)
        for i in range(stage_count)
    ]
    if len(left_levels) != len(right_levels):
        stages.append(_level_count_diff(len(left_levels), len(right_levels)))

    return RomDiffResult(
        left_name=_display_path(left_path, left_rom.display_name),
        right_name=_display_path(right_path, right_rom.display_name),
        left_crc=left_rom.get_crc32_hex(),
        right_crc=right_rom.get_crc32_hex(),
        left_region=left_rom.region,
        right_region=right_rom.region,
        left_rom=left_rom,
        right_rom=right_rom,
        left_levels=left_levels,
        right_levels=right_levels,
        stages=stages,
    )


def compare_levels(left, right, stage_no: int) -> StageDiff:
    diff = StageDiff(stage_no=stage_no)
    _compare_blocks(diff, left, right)
    _compare_items(diff, left, right)
    _compare_enemies(diff, left, right)
    _compare_meta(diff, left, right)
    if not diff.details:
        diff.details.append("変更なし")
    return diff


def _display_path(path: str, display_name: str) -> str:
    name = display_name or Path(path).name
    return f"{name} [{Path(path).name}]"


def _level_count_diff(left_count: int, right_count: int) -> StageDiff:
    diff = StageDiff(stage_no=0, meta_changes=abs(left_count - right_count))
    diff.details.append(
        f"ステージ数: {left_count} -> {right_count}"
    )
    return diff


def _compare_blocks(diff: StageDiff, left, right):
    for y in range(c.LEVEL_H):
        for x in range(c.LEVEL_W):
            left_sig = _block_cell_signature(left, x, y)
            right_sig = _block_cell_signature(right, x, y)
            if left_sig == right_sig:
                continue
            diff.block_changes += 1
            diff.details.append(
                f"ブロック ({x},{y}): "
                f"{_block_sig_label(left_sig)} -> {_block_sig_label(right_sig)}"
            )


def _block_cell_signature(level, x: int, y: int) -> tuple:
    pos = (x, y)
    flags = []
    for attr, label in (
        ("breakable_white_cells", "breakable_white"),
        ("cracked_block_cells", "cracked_block"),
        ("invisible_breakable_cells", "invisible_breakable"),
        ("passable_white_cells", "passable_white"),
        ("invisible_solid_cells", "invisible_solid"),
        ("visible_in_block_item_cells", "visible_in_block_item"),
        ("passable_brown_cells", "passable_brown"),
        ("solid_brown_cells", "solid_brown"),
    ):
        if pos in (getattr(level, attr, set()) or set()):
            flags.append(label)
    wall = level.tiles[y][x]
    wall_name = wall.name if isinstance(wall, Wall) else str(wall)
    return (wall_name, tuple(flags))


def _block_sig_label(sig: tuple) -> str:
    wall, flags = sig
    if flags:
        return f"{wall}+{','.join(flags)}"
    return wall


def _compare_items(diff: StageDiff, left, right):
    left_items = Counter(_item_signature(item) for item in getattr(left, "items", []))
    right_items = Counter(_item_signature(item) for item in getattr(right, "items", []))
    for sig, count in sorted((left_items - right_items).items()):
        diff.item_changes += count
        diff.details.append(f"アイテム削除: {_element_sig_label(sig)} x{count}")
    for sig, count in sorted((right_items - left_items).items()):
        diff.item_changes += count
        diff.details.append(f"アイテム追加: {_element_sig_label(sig)} x{count}")


def _item_signature(item) -> tuple:
    x, y = item.position
    return (int(item.element_no), int(x), int(y))


def _element_sig_label(sig: tuple) -> str:
    element_no, x, y = sig
    return f"0x{element_no:02X}@({x},{y})"


def _compare_enemies(diff: StageDiff, left, right):
    left_enemies = list(getattr(left, "enemies", []))
    right_enemies = list(getattr(right, "enemies", []))
    max_len = max(len(left_enemies), len(right_enemies))
    for idx in range(max_len):
        left_sig = _enemy_signature(left_enemies[idx]) if idx < len(left_enemies) else None
        right_sig = _enemy_signature(right_enemies[idx]) if idx < len(right_enemies) else None
        if left_sig == right_sig:
            continue
        diff.enemy_changes += 1
        diff.details.append(
            f"敵#{idx + 1:02d}: "
            f"{_maybe_element_sig_label(left_sig)} -> {_maybe_element_sig_label(right_sig)}"
        )


def _enemy_signature(enemy) -> tuple:
    x, y = enemy.position
    return (int(enemy.element_no), int(x), int(y))


def _maybe_element_sig_label(sig: tuple | None) -> str:
    if sig is None:
        return "なし"
    return _element_sig_label(sig)


def _compare_meta(diff: StageDiff, left, right):
    attrs = (
        ("tileset_no", "タイルセット"),
        ("time_decrease_rate", "制限時間"),
        ("key_status", "鍵状態"),
        ("spawn_enemy_lifetime", "敵寿命"),
        ("fixed_start_pos", "開始位置"),
        ("fixed_key_pos", "鍵位置"),
        ("fixed_door_pos", "扉位置"),
        ("room_flags", "ステージフラグ"),
        ("stage_ext_flags", "ステージ拡張フラグ"),
        ("fire_reset_value", "開始時ファイア所持"),
        ("key_enemy_slot", "鍵持ち敵スロット"),
        ("fairy_enemy_slot", "落下死妖精敵スロット"),
        ("announce_id", "開始メッセージ"),
        ("announce_flags", "開始メッセージフラグ"),
        ("panel_variant_a_speed", "パネルA速度"),
        ("panel_variant_a_interval", "パネルA間隔"),
        ("panel_variant_b_speed", "パネルB速度"),
        ("panel_variant_b_interval", "パネルB間隔"),
        ("panel_variant_c_speed", "パネルC速度"),
        ("panel_variant_c_interval", "パネルC間隔"),
    )
    for attr, label in attrs:
        left_value = getattr(left, attr, None)
        right_value = getattr(right, attr, None)
        if left_value != right_value:
            diff.meta_changes += 1
            diff.details.append(f"{label}: {left_value} -> {right_value}")

    left_const = _constellation_signature(getattr(left, "constellation", None))
    right_const = _constellation_signature(getattr(right, "constellation", None))
    if left_const != right_const:
        diff.meta_changes += 1
        diff.details.append(
            f"星座: {_maybe_element_sig_label(left_const)} -> "
            f"{_maybe_element_sig_label(right_const)}"
        )

    for idx in range(2):
        left_mirror = _mirror_signature(left.demon_mirrors[idx])
        right_mirror = _mirror_signature(right.demon_mirrors[idx])
        if left_mirror == right_mirror:
            continue
        diff.meta_changes += 1
        diff.details.append(
            f"ミラー{idx + 1}: {_mirror_label(left_mirror)} -> "
            f"{_mirror_label(right_mirror)}"
        )


def _constellation_signature(item) -> tuple | None:
    if item is None:
        return None
    return _item_signature(item)


def _mirror_signature(mirror) -> tuple:
    x, y = mirror.position
    return (int(x), int(y), int(mirror.schedule_no), int(mirror.monster_set_no))


def _mirror_label(sig: tuple) -> str:
    x, y, sched, monster_set = sig
    return f"({x},{y}) sched={sched} set={monster_set}"

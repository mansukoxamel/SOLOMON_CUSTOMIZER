"""ROM保存機能 - レベルデータをROMバイナリに書き戻す"""
from datetime import datetime
import re

from . import constants as c
from . import rom_map
from .rom import Rom
from .level import Level


class SaveError(Exception):
    """データセクションがROM容量を超えた等のエラー"""
    pass


def _shorten(text: str, limit: int = 360) -> str:
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _summarize_failure(text: str) -> str:
    text = str(text).strip()
    for marker in (": got ", ", expected ", " expected "):
        if marker in text:
            text = text.split(marker, 1)[0]
            break
    return _shorten(text)


class SavePreflightError(SaveError):
    """Save-time ROM validation failed in a named writer step."""

    def __init__(self, step: str, cause: Exception):
        self.step = str(step)
        self.cause_type = type(cause).__name__
        self.cause_detail = str(cause)
        super().__init__(f"{self.step}: {self.cause_type}: {self.cause_detail}")

    def dialog_message(self) -> str:
        reason = _summarize_failure(self.cause_detail)
        return (
            "保存前チェックで問題が見つかったため、ROM保存を中止しました。\n\n"
            f"工程: {self.step}\n"
            f"原因: {self.cause_type}: {reason}\n\n"
            "別の改造、古い保存ROM、破損したROM、または保存データの制約に"
            "該当している可能性があります。詳細はログを確認してください。"
        )

    def log_message(self) -> str:
        return (
            f"保存前チェック失敗: step={self.step}; "
            f"cause={self.cause_type}: {self.cause_detail}"
        )

    def is_runtime_layout_mismatch(self) -> bool:
        """Return whether salvage migration is relevant to this failure."""
        step = self.step.lower()
        detail = self.cause_detail.lower()
        if "runtime" not in step:
            return False
        layout_markers = (
            "signature mismatch",
            "extension mismatch",
            "area is occupied",
            "area occupied",
            "cave overlap",
            "expected empty",
            "runtime loader signature mismatch",
        )
        return any(marker in detail for marker in layout_markers)


def _run_save_step(step: str, func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except SavePreflightError:
        raise
    except Exception as e:
        raise SavePreflightError(step, e) from e


def validate_level_consistency(levels: list):
    """Check editor-level relationships before writing them into ROM bytes."""
    from . import enemy_slot_rules
    from . import stage_ext
    from . import warp_zone_trial
    from . import final_stage_redirect

    final_stage_redirect.validate_levels(levels)

    for i, lv in enumerate(levels):
        if (
            stage_ext.warp_mirror_enabled(lv)
            and not warp_zone_trial.level_has_valid_warp_mirrors(lv)
        ):
            raise SaveError(
                f"Level {i + 1}: Warp Mirror Mode requires exactly two "
                "visible mirrors at different, unobstructed positions."
            )
        key_enemy_number = stage_ext.get_key_enemy_number(lv)
        enemy_count = len(getattr(lv, "enemies", []) or [])
        if key_enemy_number > 0 and key_enemy_number > enemy_count:
            raise SaveError(
                f"Level {i + 1}: key enemy #{key_enemy_number} is selected, "
                f"but only {enemy_count} initial enemies exist."
            )
        if key_enemy_number > 0 and not enemy_slot_rules.can_key_enemy_number(lv, key_enemy_number):
            raise SaveError(
                f"Level {i + 1}: enemy #{key_enemy_number} cannot be selected as a key enemy."
            )
        fairy_enemy_number = stage_ext.get_fairy_enemy_number(lv)
        if fairy_enemy_number <= 0:
            continue
        if fairy_enemy_number > enemy_count:
            raise SaveError(
                f"Level {i + 1}: fairy enemy #{fairy_enemy_number} is selected, "
                f"but only {enemy_count} initial enemies exist."
            )
        if key_enemy_number > 0 and fairy_enemy_number == key_enemy_number:
            raise SaveError(
                f"Level {i + 1}: enemy #{fairy_enemy_number} cannot be both "
                "key-carrying and fall-death fairy."
            )
        if not enemy_slot_rules.can_fairy_enemy_number(lv, fairy_enemy_number, key_enemy_number):
            raise SaveError(
                f"Level {i + 1}: enemy #{fairy_enemy_number} cannot be selected as a fall-death fairy enemy."
            )


_AUTO_BUILD_TITLE_RE = re.compile(r"^BUILD \d{8} \d{6}$")


def make_auto_build_title_text() -> str:
    return "BUILD " + datetime.now().strftime("%Y%m%d %H%M%S")


def is_auto_build_title_text(text: str) -> bool:
    return bool(_AUTO_BUILD_TITLE_RE.fullmatch(str(text or "").strip()))


def refresh_auto_build_title_text(
    rom: Rom,
    loaded_title_text: str | None = None,
) -> tuple[str, str] | None:
    """Insert/update the automatic BUILD title line when it is still app-owned."""
    from . import title_screen

    try:
        current = title_screen.read_title_text_line(rom.data)
    except title_screen.TitleScreenError:
        return None
    current = str(current or "").strip()
    loaded = None if loaded_title_text is None else str(loaded_title_text or "").strip()
    if current:
        if loaded is None or current != loaded or not is_auto_build_title_text(current):
            return None
    stamp = make_auto_build_title_text()
    title_screen.add_title_text_line(rom.data, stamp)
    return current, stamp


def ensure_default_title_text(rom: Rom, loaded_title_text: str | None = None):
    """Stamp date/time into the title overlay when the app-owned text needs it."""
    refresh_auto_build_title_text(rom, loaded_title_text)


def write_block_data(rom: Rom, level: Level, level_no: int):
    """ブロックデータを書き戻し"""
    region = rom.base_region()
    offset = rom_map.get_block_data_offset(region, level_no)
    data = level.get_block_bytes()
    if len(data) != c.SIZE_LEVEL_WALLS:
        raise SaveError(f"Block data size mismatch: {len(data)} != {c.SIZE_LEVEL_WALLS}")
    rom.set_bytes(offset, data)


def write_enemy_data(rom: Rom, levels: list, region: str = None):
    """敵データを書き戻し（レベル順、容量チェック付き）"""
    if region is None:
        region = rom.base_region()

    base_offset = c.ROM_OFFSETS[region]["enemy_table"]
    table_offset = base_offset
    data_section_start = rom_map.get_enemy_data_offset(rom, region, 0)

    # 全レベルの敵データを構築して連結
    write_offset = data_section_start
    table_low = bytearray(c.LEVEL_COUNT)
    table_high = bytearray(c.LEVEL_COUNT)

    for i, lv in enumerate(levels):
        bytes_data = lv.get_enemy_bytes()

        # テーブル更新（RAM addressに変換）
        ram_addr = write_offset + c.ROM_RAM_DIFF
        table_low[i] = ram_addr & 0xff
        table_high[i] = (ram_addr >> 8) & 0xff

        if write_offset + len(bytes_data) - data_section_start > c.LENGTH_ENEMY_DATA:
            raise SaveError(
                f"Enemy data overflow at level {i+1} "
                f"({write_offset + len(bytes_data) - data_section_start} > {c.LENGTH_ENEMY_DATA})"
            )

        rom.set_bytes(write_offset, bytes_data)
        write_offset += len(bytes_data)

    # データセクションの残りをゼロパディング
    while write_offset - data_section_start < c.LENGTH_ENEMY_DATA:
        rom.set_byte(write_offset, 0x00)
        write_offset += 1

    # テーブル書き戻し
    for i in range(c.LEVEL_COUNT):
        rom.set_byte(table_offset + i, table_low[i])
        rom.set_byte(table_offset + i + c.LEVEL_COUNT, table_high[i])


def write_item_data(rom: Rom, levels: list, region: str = None,
                    ignore_item_elements: dict = None):
    """アイテムデータを書き戻し"""
    if region is None:
        region = rom.base_region()
    if ignore_item_elements is None:
        ignore_item_elements = {}

    table_offset = c.ROM_OFFSETS[region]["item_table"]
    data_section_start = rom_map.get_item_data_offset(rom, region, 0)

    write_offset = data_section_start
    table_low = bytearray(c.LEVEL_COUNT)
    table_high = bytearray(c.LEVEL_COUNT)

    for i, lv in enumerate(levels):
        ignore = ignore_item_elements.get(i, [])
        bytes_data = lv.get_item_bytes(ignore)

        ram_addr = write_offset + c.ROM_RAM_DIFF
        table_low[i] = ram_addr & 0xff
        table_high[i] = (ram_addr >> 8) & 0xff

        if write_offset + len(bytes_data) - data_section_start > c.LENGTH_ITEM_DATA:
            raise SaveError(
                f"Item data overflow at level {i+1} "
                f"({write_offset + len(bytes_data) - data_section_start} > {c.LENGTH_ITEM_DATA})"
            )

        rom.set_bytes(write_offset, bytes_data)
        write_offset += len(bytes_data)

    while write_offset - data_section_start < c.LENGTH_ITEM_DATA:
        rom.set_byte(write_offset, 0x00)
        write_offset += 1

    for i in range(c.LEVEL_COUNT):
        rom.set_byte(table_offset + i, table_low[i])
        rom.set_byte(table_offset + i + c.LEVEL_COUNT, table_high[i])


def _write_standard_level_data(rom: Rom, levels: list):
    region = rom.base_region()
    for i, lv in enumerate(levels):
        write_block_data(rom, lv, i)
    write_enemy_data(rom, levels, region)
    write_item_data(rom, levels, region)


def save_levels_to_rom(
    rom: Rom,
    levels: list,
    panel_variant_settings: dict | None = None,
    loaded_title_text: str | None = None,
):
    """全レベルをROMに書き戻す（標準ROM/拡張ROM両対応）

    Args:
        rom: 書き込み先ROM
        levels: 53個のLevelリスト
    """
    _run_save_step("ステージ整合性チェック", validate_level_consistency, levels)

    if rom.is_expanded():
        # 拡張ROM (US66): 1レベル=256バイト固定の構造で書き戻し
        from . import m66, solomon_seal_block
        levels = solomon_seal_block.levels_for_save(rom.data, levels)
        _run_save_step("透明ブロック内アイテム整合性チェック", m66.validate_visible_in_block_items, levels)
        _run_save_step("ひび割れブロック内アイテム整合性チェック", m66.validate_cracked_in_block_items, levels)
        _run_save_step("mapper66ステージデータ書き込み", m66.save_all_levels_m66, rom, levels)
    else:
        from . import m66
        if m66.visible_in_block_items_needed(levels) or m66.cracked_in_block_items_needed(levels):
            raise SaveError("透明/ひび割れブロック内アイテムはmapper66拡張ROM保存専用です。")
        # 標準ROM
        _run_save_step("通常ROMステージデータ書き込み", _write_standard_level_data, rom, levels)

    # Room Flag Table 拡張 (画面ごとの挙動改造)。標準/拡張ROM 共通。
    # bank0 cave の file offset は expander が verbatim コピーするため不変。
    # 位置+署名ダブル検証付き、検証失敗時は RoomFlagError で中止 (saver
    # の SaveError と同様、呼び元でメッセージ表示)。全0なら原作復元。
    from . import (
        room_flags, saramandor_variant, panel_monster_stage_variant,
        spark_ball_variant, gargoyle_variant,
        stage_ext, key_enemy_runtime, stage_announcement, title_screen,
        drop_pickup_guard, special_process, solomon_seal_block,
        final_stage_redirect, new_enemy_runtime, warp_zone_trial,
        enemy_clear_key_open, fire2_item_runtime, blue_key_queen_runtime,
    )
    from . import gap_fix_alternative as gap_fix
    from .element import byte_from_position
    # IMPORTANT: this apply order is part of the ROM layout contract.
    # panel_monster_stage_variant owns the current Panel runtime, and its PRG1
    # loader supersedes stage_ext's loader.
    # If these calls are reordered, the later writer can overwrite the final
    # hooks/loader and break Panel Variant enemies or room-load cache copying.
    _run_save_step("Saramandor variant runtime検証/適用", saramandor_variant.apply, rom.data)
    _run_save_step("Spark Ball variant runtime検証/適用", spark_ball_variant.apply, rom.data)
    _run_save_step("drop pickup guard検証/適用", drop_pickup_guard.apply, rom.data)
    _run_save_step("Gargoyle slow-Bullet runtime検証/適用", gargoyle_variant.apply, rom.data)
    if rom.is_expanded():
        _run_save_step("Solomon Seal block-state検証/適用", solomon_seal_block.apply, rom.data, levels)
    _run_save_step(
        "Gap fix runtime固定配置検証/適用",
        gap_fix.apply,
        rom.data,
        gap_fix.is_applied(rom.data),
    )
    _run_save_step("wide-title idle demo cleanup検証/適用", title_screen.apply_wide_title_idle_demo_cleanup, rom.data)
    _run_save_step(
        "タイトル初期テキスト確認/適用",
        ensure_default_title_text,
        rom,
        loaded_title_text,
    )
    breakable_runtime_cells = []
    for lv in levels:
        breakable = set(getattr(lv, "breakable_white_cells", set()) or [])
        breakable.update(m66.cracked_block_cells(lv))
        breakable.update(getattr(lv, "invisible_breakable_cells", set()) or [])
        empty = set(getattr(lv, "passable_white_cells", set()) or [])
        empty.update(getattr(lv, "passable_brown_cells", set()) or [])
        solid = set(getattr(lv, "invisible_solid_cells", set()) or [])
        solid.update(getattr(lv, "solid_brown_cells", set()) or [])
        breakable_runtime_cells.append({
            "breakable": breakable,
            "empty": empty,
            "solid": solid,
            "visible_in_block_items": set(getattr(lv, "visible_in_block_item_cells", set()) or []),
            "cracked_in_block_items": m66.cracked_in_block_item_cells(lv),
        })
    runtime_room_flags = []
    for idx, lv in enumerate(levels):
        flags = getattr(lv, "room_flags", 0) & 0xFF
        if stage_ext.fire_reset_enabled(lv):
            flags |= room_flags.BIT_FIRE_RESET
        if getattr(lv, "visible_in_block_item_cells", set()) or m66.cracked_in_block_item_cells(lv):
            flags |= room_flags.BIT_VISIBLE_INBLOCK_ITEMS
        cells = breakable_runtime_cells[idx] if idx < len(breakable_runtime_cells) else {}
        if any(cells.get(kind) for kind in ("breakable", "empty", "solid")):
            flags |= room_flags.BIT_RUNTIME_SPECIAL_CELLS
        runtime_room_flags.append(room_flags.normalize_flags(flags))
    door_cells = [byte_from_position(lv.fixed_door_pos) for lv in levels]
    if rom.is_expanded():
        _run_save_step("StageExt table書き込み", stage_ext.patch_table, rom.data, levels, runtime_room_flags, door_cells)
        _run_save_step("StageExt runtime loader検証/適用", stage_ext.apply_runtime_loader, rom.data)
        _run_save_step("Final stage redirect runtime検証/適用", final_stage_redirect.apply, rom.data, levels)
        _run_save_step(
            "Stage 50赤い本取得判定セル座標書き込み",
            special_process.patch_stage50_book_grid_cell,
            rom.data,
            rom.base_region(),
            levels,
        )
        _run_save_step(
            "Stage 50赤い本クリア判定座標書き込み",
            special_process.patch_stage50_book_clear_trigger,
            rom.data,
            rom.base_region(),
            levels,
        )
        _run_save_step(
            "Stage 50赤い本開き表示座標書き込み",
            special_process.patch_stage50_book_open_display,
            rom.data,
            rom.base_region(),
            levels,
        )
    _run_save_step("開始画面アナウンス検証/適用", stage_announcement.apply, rom.data, levels, runtime_room_flags)
    _run_save_step(
        "Room Flag runtime検証/適用",
        room_flags.apply,
        rom.data,
        runtime_room_flags,
        door_cells,
        breakable_runtime_cells,
    )
    _run_save_step(
        "Key enemy runtime検証/適用",
        key_enemy_runtime.apply,
        rom.data,
    )
    if rom.is_expanded():
        _run_save_step(
            "New enemy runtime検証/適用",
            new_enemy_runtime.apply,
            rom.data,
        )
        _run_save_step(
            "Warp Mirror Mode runtime検証/適用",
            warp_zone_trial.apply,
            rom.data,
            levels,
        )
        _run_save_step(
            "Enemy Clear Key Open runtime検証/適用",
            enemy_clear_key_open.apply,
            rom.data,
            levels,
        )
    elif new_enemy_runtime.levels_need_runtime(levels):
        raise SaveError(
            "新敵ID ($82 / $84-$87 / $9C-$9E / $A0-$AF / $B0-$BB / $C0-$DF / $E0-$F7) "
            "はmapper66拡張ROM保存専用です。"
        )
    elif enemy_clear_key_open.levels_need_runtime(levels):
        raise SaveError("全敵消滅で扉を開く機能はmapper66拡張ROM保存専用です。")
    elif fire2_item_runtime.levels_need_runtime(levels):
        raise SaveError("Special item はmapper66拡張ROM保存専用です。")
    if rom.is_expanded():
        _run_save_step(
            "Blue key queen runtime検証/適用",
            blue_key_queen_runtime.apply,
            rom.data,
        )
        _run_save_step(
            "Panel Variant runtime検証/適用",
            panel_monster_stage_variant.apply,
            rom.data,
            levels,
            panel_variant_settings,
        )
        _run_save_step(
            "Special item runtime検証/適用",
            fire2_item_runtime.apply,
            rom.data,
            levels,
        )
    if rom.is_expanded():
        from . import rom_metadata
        _run_save_step(
            "原作item bitmap特殊処理無効化",
            special_process.disable_imported_item_bitmask_processes,
            rom.data,
            rom.base_region(),
        )
        _run_save_step(
            "原作1体目妖精化特殊処理無効化",
            special_process.disable_falling_fairy_subroutine,
            rom.data,
            rom.base_region(),
        )
        _run_save_step("Customizer metadata書き込み", rom_metadata.write_metadata, rom.data)


def build_saved_rom_data(
    rom: Rom,
    levels: list,
    panel_variant_settings: dict | None = None,
    loaded_title_text: str | None = None,
) -> bytes:
    """Validate and build saved ROM bytes without mutating the open ROM."""
    work = Rom(bytes(rom.data), rom.path)
    work.display_name = rom.display_name
    save_levels_to_rom(work, levels, panel_variant_settings, loaded_title_text)
    return bytes(work.data)


def write_rom_file(rom: Rom, path: str):
    """ROMをファイルに保存"""
    rom.save(path)


def write_rom_data(data: bytes, path: str):
    with open(path, "wb") as f:
        f.write(bytes(data))

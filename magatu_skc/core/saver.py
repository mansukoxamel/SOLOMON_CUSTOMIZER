"""ROM保存機能 - レベルデータをROMバイナリに書き戻す"""
from . import constants as c
from . import rom_map
from .rom import Rom
from .level import Level


class SaveError(Exception):
    """データセクションがROM容量を超えた等のエラー"""
    pass


def validate_level_consistency(levels: list):
    """Check editor-level relationships before writing them into ROM bytes."""
    from . import stage_ext

    for i, lv in enumerate(levels):
        key_enemy_number = stage_ext.get_key_enemy_number(lv)
        if key_enemy_number <= 0:
            continue
        enemy_count = len(getattr(lv, "enemies", []) or [])
        if key_enemy_number > enemy_count:
            raise SaveError(
                f"Level {i + 1}: key enemy #{key_enemy_number} is selected, "
                f"but only {enemy_count} initial enemies exist."
            )


def ensure_default_title_text(rom: Rom):
    """Stamp date/time into the title overlay when the overlay is still empty."""
    from datetime import datetime
    from . import title_screen

    try:
        current = title_screen.read_title_text_line(rom.data)
    except title_screen.TitleScreenError:
        return
    if current.strip():
        return
    stamp = "BUILD " + datetime.now().strftime("%Y%m%d %H%M%S")
    title_screen.add_title_text_line(rom.data, stamp)


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


def _uses_gargoyle_two_shot(levels: list) -> bool:
    for lv in levels:
        for enemy in getattr(lv, "enemies", []) or []:
            if getattr(enemy, "element_no", None) in (0x7A, 0x7B, 0x7E, 0x7F):
                return True
        for mirror in getattr(lv, "demon_mirrors", []) or []:
            for code in getattr(mirror, "enemy_codes", []) or []:
                if int(code) in (0x7A, 0x7B, 0x7E, 0x7F):
                    return True
    return False


def save_levels_to_rom(rom: Rom, levels: list):
    """全レベルをROMに書き戻す（標準ROM/拡張ROM両対応）

    Args:
        rom: 書き込み先ROM
        levels: 53個のLevelリスト
    """
    validate_level_consistency(levels)

    if rom.is_expanded():
        # 拡張ROM (US66): 1レベル=256バイト固定の構造で書き戻し
        from . import m66
        m66.save_all_levels_m66(rom, levels)
    else:
        region = rom.base_region()
        # 標準ROM
        for i, lv in enumerate(levels):
            write_block_data(rom, lv, i)        # ブロックデータ
        write_enemy_data(rom, levels, region)   # 敵データ
        write_item_data(rom, levels, region)    # アイテムデータ

    # Room Flag Table 拡張 (画面ごとの挙動改造)。標準/拡張ROM 共通。
    # bank0 cave の file offset は expander が verbatim コピーするため不変。
    # 位置+署名ダブル検証付き、検証失敗時は RoomFlagError で中止 (saver
    # の SaveError と同様、呼び元でメッセージ表示)。全0なら原作復元。
    from . import (
        room_flags, saramandor_variant, panel_monster_variant,
        panel_monster_stage_variant, spark_ball_variant, gargoyle_variant,
        stage_ext, key_enemy_runtime, stage_announcement, title_screen,
        drop_pickup_guard,
    )
    from .element import byte_from_position
    # IMPORTANT: this apply order is part of the ROM layout contract.
    # panel_monster_stage_variant is a final replacement for parts of
    # panel_monster_variant, and its PRG1 loader supersedes stage_ext's loader.
    # If these calls are reordered, the later writer can overwrite the final
    # hooks/loader and break Panel Variant enemies or room-load cache copying.
    saramandor_variant.apply(rom.data)
    panel_monster_variant.apply(rom.data)
    spark_ball_variant.apply(rom.data)
    drop_pickup_guard.apply(rom.data)
    if _uses_gargoyle_two_shot(levels):
        gargoyle_variant.apply(rom.data)
    title_screen.migrate_wide_title_trampoline_ram(rom.data)
    title_screen.apply_wide_title_idle_demo_cleanup(rom.data)
    ensure_default_title_text(rom)
    breakable_runtime_cells = []
    for lv in levels:
        breakable = set(getattr(lv, "breakable_white_cells", set()) or [])
        breakable.update(getattr(lv, "invisible_breakable_cells", set()) or [])
        empty = set(getattr(lv, "passable_white_cells", set()) or [])
        empty.update(getattr(lv, "passable_brown_cells", set()) or [])
        solid = set(getattr(lv, "invisible_solid_cells", set()) or [])
        solid.update(getattr(lv, "solid_brown_cells", set()) or [])
        breakable_runtime_cells.append({
            "breakable": breakable,
            "empty": empty,
            "solid": solid,
        })
    runtime_room_flags = []
    for lv in levels:
        flags = getattr(lv, "room_flags", 0) & 0xFF
        if stage_ext.fire_reset_enabled(lv):
            flags |= room_flags.BIT_FIRE_RESET
        runtime_room_flags.append(flags)
    door_cells = [byte_from_position(lv.fixed_door_pos) for lv in levels]
    if rom.is_expanded():
        stage_ext.patch_table(rom.data, levels, runtime_room_flags, door_cells)
        stage_ext.apply_runtime_loader(rom.data)
    stage_announcement.apply(rom.data, levels, runtime_room_flags)
    room_flags.apply(
        rom.data,
        runtime_room_flags,
        door_cells,
        breakable_runtime_cells,
    )
    key_enemy_runtime.apply(
        rom.data,
        any(stage_ext.key_enemy_enabled(lv) for lv in levels),
    )
    if rom.is_expanded() and panel_monster_stage_variant.has_panel_stage_runtime_ids(levels):
        panel_monster_stage_variant.apply(rom.data, levels)
    if rom.is_expanded():
        from . import rom_metadata
        rom_metadata.write_metadata(rom.data)


def build_saved_rom_data(rom: Rom, levels: list) -> bytes:
    """Validate and build saved ROM bytes without mutating the open ROM."""
    work = Rom(bytes(rom.data), rom.path)
    work.display_name = rom.display_name
    save_levels_to_rom(work, levels)
    return bytes(work.data)


def write_rom_file(rom: Rom, path: str):
    """ROMをファイルに保存"""
    rom.save(path)


def write_rom_data(data: bytes, path: str):
    with open(path, "wb") as f:
        f.write(bytes(data))

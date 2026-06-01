"""日本版通常ROM (mapper 3) → 拡張ROM (mapper 66) 変換

C++ skchain `Rom_expander.cpp` の change_mapper() / patch_mirror_*() / remove_blocks_behind_demon_mirrors() を移植。

通常ROMに編集を加えて保存しようとすると敵データ計726バイトの上限を超えやすいため、
このエディタでは日本版通常ROMの読込時に自動的に拡張ROM (mapper 66, 96KB) に変換する。
通常編集対象は日本版ROMのみで、US/EU版のmapper66変換は行わない。
"""
from . import constants as c
from . import m66
from . import region as region_mod
from .rom import crc32_hex, is_known_jp_original_data
from .element import Wall, byte_from_position
from .level import Level


# C++ Constants_application.h より
ROM_M66_FILE_SIZE = 98320  # 96KB + 16バイトiNESヘッダ


def _resolve_table_entry(rom_data: bytes, table_offset: int, count: int, index: int) -> int:
    """C++ get_offset_generic_data 移植

    通常ROMのポインタテーブル経由で実データのROMオフセットを得る。
    table[index]    = lo byte
    table[count+index] = hi byte
    ram_addr = hi*256 + lo
    rom_offset = ram_addr - ROM_RAM_DIFF
    """
    lo = rom_data[table_offset + index]
    hi = rom_data[table_offset + count + index]
    ram_addr = (hi << 8) | lo
    return ram_addr - c.ROM_RAM_DIFF


def parse_drop_schedules_std(rom_data: bytes, region: str) -> list:
    """通常ROMから16個のドロップスケジュール(各8バイト=64bit)をポインタテーブル経由で取り出す。"""
    table = c.ROM_OFFSETS[region]["mirror_rate_table"]
    schedules = []
    for i in range(c.MIRROR_RATE_COUNT):  # 16
        data_off = _resolve_table_entry(rom_data, table, c.MIRROR_RATE_COUNT, i)
        schedules.append(bytes(rom_data[data_off: data_off + 8]))
    return schedules


def parse_enemy_sets_std(rom_data: bytes, region: str) -> list:
    """通常ROMから17個のミラー敵セットを取り出す（ポインタテーブル経由）。

    各セットは 0x90 デリミタで終端された可変長バイト列。
    """
    table = c.ROM_OFFSETS[region]["mirror_enemy_table"]
    sets = []
    for i in range(c.MIRROR_ENEMY_COUNT):  # 17
        data_off = _resolve_table_entry(rom_data, table, c.MIRROR_ENEMY_COUNT, i)
        cur = []
        j = 0
        # 念のため上限
        while j < 64:
            b = rom_data[data_off + j]
            if b == c.MIRROR_ENEMY_SET_DELIMITER:
                break
            cur.append(b)
            j += 1
        sets.append(bytes(cur))
    return sets


_REGION_PATCH_OFFSETS = {
    "JP": {"nop3": 6162, "sub1": 6534, "zero48": 16370, "byte_0d30": 3376,
           "tbl_5c10": 23568, "tbl_5c20": 23584, "tbl_5c30": 23600, "tbl_5c41": 23617,
           "lvl_lo": 23804, "lvl_hi": 23857, "lvl2_lo": 27180, "lvl2_hi": 27233},
}


def _require_jp_region(region: str):
    if region != "JP":
        raise ValueError(
            "mapper66変換は日本版 Solomon no Kagi の通常ROM専用です。"
            f"region={region!r} は通常編集対象外です。"
        )


def _require_jp_standard_rom(src: bytes, region: str):
    _require_jp_region(region)
    try:
        detected = region_mod.detect_region(src)
    except ValueError as exc:
        raise ValueError(
            "mapper66変換は日本版 Solomon no Kagi の通常ROM専用です。"
            "ROM実体のリージョンを確認できません。"
        ) from exc
    if region_mod.is_expanded(detected):
        raise ValueError(
            "mapper66変換は日本版 Solomon no Kagi の通常ROM専用です。"
            f"region={detected!r} は既に拡張ROMです。"
        )
    detected_base = region_mod.base_region(detected)
    if detected_base != "JP":
        raise ValueError(
            "mapper66変換は日本版 Solomon no Kagi の通常ROM専用です。"
            f"ROM実体は region={detected!r} です。"
        )
    if not is_known_jp_original_data(src):
        raise ValueError(
            "mapper66変換は確認済みの日本版オリジナル通常ROM専用です。"
            f"CRC32={crc32_hex(src)} は通常編集対象外です。"
        )


def change_mapper(src: bytes, region: str = "JP") -> bytearray:
    """C++ change_mapper の移植（JP版専用）

    通常ROM (32KB PRG + 32KB CHR + 16ヘッダ = 65552B) を
    拡張ROM (64KB PRG + 32KB CHR + 16ヘッダ = 98320B) に再構成する。
    PRG 末尾16バイト(割り込みベクタ)は新PRGの末尾にコピーされる。
    複数のパッチを当てて、追加領域(32784..65536)から読むサブルーチンを差し込む。
    """
    if len(src) < 65552:
        raise ValueError(f"Standard ROM size mismatch: {len(src)} (expected >= 65552)")

    _require_jp_standard_rom(src, region)

    if region not in _REGION_PATCH_OFFSETS:
        raise ValueError(f"change_mapper: region '{region}' is not supported (JP only)")

    p = _REGION_PATCH_OFFSETS[region]

    result = bytearray(ROM_M66_FILE_SIZE)

    # 1. ヘッダ + 元PRG (16+32768=32784B) をコピー
    for i in range(32784):
        result[i] = src[i]
    # 2. 元PRGの末尾16バイト (割り込みベクタ) を新PRGの末尾(65536+16)にコピー
    for i in range(16):
        result[65536 + i] = src[32768 + i]
    # 3. 元CHR 32768B を 65552..98320 にコピー
    for i in range(32768):
        result[65552 + i] = src[32784 + i]

    # iNES ヘッダ書換: PRG=64KB(=4×16KB), mapper bits = 66
    # Keep the expanded output as NES 1.0 by clearing bytes 7-15.
    result[4] = 4
    for i in range(7, 16):
        result[i] = 0
    result[6] = 32   # mapper low nibble = 0x2
    result[7] = 64   # mapper high nibble = 0x4 → mapper = 0x42 = 66

    # アプリケーション固有パッチ群
    result[255] = 0
    result[256] = 1
    result[257] = 2
    result[258] = 3
    result[p["byte_0d30"]] = 0

    # NOP x3: 元コードの一部を無効化
    nop3 = p["nop3"]
    result[nop3] = 234
    result[nop3 + 1] = 234
    result[nop3 + 2] = 234

    # レベルテーブル (53レベル分)
    for i in range(m66.COUNT_M66_LEVELS):
        result[p["lvl_lo"] + i] = 160
        result[p["lvl_hi"] + i] = 7
        result[p["lvl2_lo"] + i] = 144
        result[p["lvl2_hi"] + i] = 7

    # サブルーチン1 (32B) — 内部に自己参照の絶対アドレスを含むため動的生成
    # The absolute self-reference depends on the final subroutine CPU address.
    sub1 = p["sub1"]
    sub1_cpu = 0x8000 + (sub1 - 16)  # ファイルオフセット → CPU アドレス
    data_addr = sub1_cpu + 13        # サブルーチン内 position 13 の CPU アドレス
    data_lo = data_addr & 0xFF
    data_hi = (data_addr >> 8) & 0xFF
    l_a1 = bytes([
        0x10, 0xBD, data_lo, data_hi, 0x9D, 0xCF, 0x07, 0xCA,
        0xD0, 0xF7, 0x4C, 0xD0, 0x07, 0x60, 0xA9, 0x13,
        0x9D, 0x11, 0x80, 0x20, 0x01, 0x80, 0xA9, 0x03,
        0x9D, 0x11, 0x80, 0x4C, data_lo, data_hi, data_lo, data_hi
    ])
    for i, b in enumerate(l_a1):
        result[sub1 + i] = b

    # サブルーチン2 (152B at offset 32784 = 拡張領域の先頭)
    l_a2 = bytes([
        64, 173, 40, 4, 24, 105, 191, 133, 1, 169, 255, 133, 0, 160, 192, 173,
        40, 4, 201, 48, 240, 34, 165, 124, 106, 144, 29, 177, 0, 201, 248, 176,
        23, 41, 63, 201, 46, 144, 17, 177, 0, 41, 128, 42, 144, 5, 169, 144, 24,
        144, 7, 169, 16, 24, 144, 2, 177, 0, 153, 19, 3, 136, 208, 207, 160, 16,
        169, 248, 153, 3, 3, 153, 211, 3, 136, 208, 247, 173, 40, 4, 24, 105,
        192, 133, 1, 169, 191, 133, 0, 160, 64, 177, 0, 153, 143, 7, 136, 208,
        248, 173, 40, 4, 10, 10, 10, 10, 24, 105, 0, 133, 0, 173, 40, 4, 74, 74,
        74, 74, 24, 105, 245, 133, 1, 56, 165, 0, 233, 1, 133, 0, 165, 1, 233,
        0, 133, 1, 160, 16, 177, 0, 153, 127, 7, 136, 208, 248,
        234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234,
        234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234,
        234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 96
    ])
    for i, b in enumerate(l_a2):
        result[32784 + i] = b

    # 追加バイト書換
    result[p["tbl_5c10"]] = 128
    result[p["tbl_5c10"] + 1] = 136
    result[p["tbl_5c20"]] = 7
    result[p["tbl_5c20"] + 1] = 7
    result[p["tbl_5c30"]] = 192
    result[p["tbl_5c30"] + 1] = 200
    result[p["tbl_5c41"]] = 7
    result[p["tbl_5c41"] + 1] = 7

    # 48バイト消去
    for i in range(48):
        result[p["zero48"] + i] = 0

    return result


def patch_mirror_drop_schedule_bytes(rom_data: bytearray,
                                     drop_schedules: list,
                                     levels: list):
    """C++ patch_mirror_drop_schedule_bytes 移植

    各レベル × 2スポーンに対応する 8バイトスケジュールを連続配置する。
    """
    out_offset = m66.OFFSET_M66_DROP_SCHED_DATA
    for lvl in levels:
        for spawn_no in range(2):
            sched_no = lvl.demon_mirrors[spawn_no].schedule_no
            if 0 <= sched_no < len(drop_schedules):
                sched = drop_schedules[sched_no]
            else:
                sched = b"\x00" * 8
            for j in range(8):
                rom_data[out_offset + j] = sched[j] if j < len(sched) else 0
            out_offset += 8


def patch_mirror_enemy_set_bytes(rom_data: bytearray,
                                 enemy_sets: list,
                                 levels: list):
    """C++ patch_mirror_enemy_set_bytes 移植

    各レベル × 2 (spawn1/spawn2) の敵セットを書き込む。最大7体、終端は 0x90。
    """
    for i, lvl in enumerate(levels):
        for nmi_set_no in range(2):
            base_off = (m66.OFFSET_M66_LVL_DATA
                        + m66.LENGTH_M66_LVL_DATA * i
                        + (m66.OFFSET_M66_LOCAL_SCHED_ENEMY_1_DATA
                           if nmi_set_no == 0
                           else m66.OFFSET_M66_LOCAL_SCHED_ENEMY_2_DATA))
            set_no = lvl.demon_mirrors[nmi_set_no].monster_set_no
            if 0 <= set_no < len(enemy_sets):
                enemies = enemy_sets[set_no]
            else:
                enemies = b""

            if len(enemies) >= m66.LENGTH_M66_ENEMY_SET_DATA:
                raise RuntimeError(
                    f"Too many enemies in mirror enemy set {set_no + 1} "
                    f"({len(enemies)} >= {m66.LENGTH_M66_ENEMY_SET_DATA})"
                )
            # 最大7体まで
            for nmi in range(min(7, len(enemies))):
                rom_data[base_off + nmi] = enemies[nmi]
            rom_data[base_off + len(enemies)] = c.MIRROR_ENEMY_SET_DELIMITER


def remove_blocks_behind_demon_mirrors(levels: list):
    """C++ remove_blocks_behind_demon_mirrors 移植

    通常ROMでは「ブロック裏のミラー」が表示されるが、
    拡張ROMではブロックが優先描画されてミラーが見えなくなる。
    そのためミラー位置のブロックを削除する。
    """
    for lvl in levels:
        for i in range(2):
            pos = lvl.demon_mirrors[i].position
            x, y = pos
            if 0 <= x < c.LEVEL_W and 0 <= y < c.LEVEL_H:
                if lvl.tiles[y][x] != Wall.NONE:
                    lvl.tiles[y][x] = Wall.NONE


def expand_rom(rom, levels: list):
    """通常ROM → 拡張ROM 変換のメインエントリ

    rom: Rom オブジェクト（事前に通常ROMとして読み込まれていること）
    levels: 既にパースされた Level オブジェクトのリスト

    in-place で rom.data を書き換え、rom.region を "JP66" に変更する。
    """
    if rom.is_expanded():
        return  # すでに拡張ROMなので何もしない

    src_region = rom.base_region()
    src_data = bytes(rom.data)
    _require_jp_standard_rom(src_data, src_region)

    # 変換前にミラー関連データを通常ROMから取り出す
    drop_schedules = parse_drop_schedules_std(src_data, src_region)
    enemy_sets = parse_enemy_sets_std(src_data, src_region)

    # ROMフレームを mapper 66 形式に再構成（JP版パッチアドレス）
    new_data = change_mapper(src_data, region=src_region)

    # ミラー裏のブロックを除去（C++と同じ前処理）
    remove_blocks_behind_demon_mirrors(levels)

    # 各レベルのデータを書き戻し
    for i, lvl in enumerate(levels):
        m66.save_level_m66(new_data, i, lvl)

    # ミラー関連データを各レベルローカルに展開
    patch_mirror_enemy_set_bytes(new_data, enemy_sets, levels)
    patch_mirror_drop_schedule_bytes(new_data, drop_schedules, levels)
    from . import stage_ext
    stage_ext.patch_table(new_data, levels)
    m66.patch_breakable_white_data(new_data, levels)

    # rom オブジェクトを書き換え
    rom.data = new_data
    # ソースリージョンに応じた拡張リージョン名（base_region で元に戻せる）
    rom.region = src_region + "66"  # "JP66"

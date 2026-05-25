"""ROMリージョン判定 — US / JP / 拡張ROM(US66/JP66) のみサポート

対応リージョンは JP版 / US版 のみ。それ以外のROMは非対応として弾く。
"""
import zlib

_INES_MAGIC = b"NES\x1a"
_STD_PRG_SIZE = 0x8000
_M66_PRG_SIZE = 0x10000
_BASE_REGION_SIG_OFF = 0x0bf2
_BASE_REGION_SIG = {
    0x00: "US",
    0xea: "JP",
}

# (offset, value) で判別 — 上から順に最初にマッチしたものを採用
REGION_RULES = [
    ("JP66", 0x8010,  0x40),  # mapper66-expanded JP loader marker
    ("US66", 0x1800f, 0x00),  # 拡張ROM (US系)
    ("US",   0x0bf2,  0x00),
    ("JP",   0x0bf2,  0xea),
]

# CHR-ROM CRC32 によるフォールバック判定
# BESK等の旧エディタが PRG を改変した結果 REGION_RULES が外れるケース対策
CHR_CRC32_TO_REGION = {
    0xFAD8A464: "US",
    0xEBCA054B: "JP",
}


def _ines_prg_size(rom_data: bytes):
    if len(rom_data) < 16 or rom_data[:4] != _INES_MAGIC:
        return None
    return rom_data[4] * 0x4000


def _base_signature_region(rom_data: bytes):
    if _BASE_REGION_SIG_OFF >= len(rom_data):
        return None
    return _BASE_REGION_SIG.get(rom_data[_BASE_REGION_SIG_OFF])


def _get_chr_crc32(rom_data: bytes):
    """iNES ヘッダから PRG/CHR サイズを読み取り、CHR-ROM の CRC32 を返す"""
    if len(rom_data) < 16 or rom_data[:4] != b"NES\x1a":
        return None
    prg_size = rom_data[4] * 0x4000
    chr_size = rom_data[5] * 0x2000
    chr_start = 0x10 + prg_size
    chr_end = chr_start + chr_size
    if chr_size == 0 or chr_end > len(rom_data):
        return None
    return zlib.crc32(rom_data[chr_start:chr_end]) & 0xffffffff


def detect_region(rom_data: bytes) -> str:
    """ROMバイナリからリージョン自動判定（US / JP / US66 / JP66）

    対応外のROMは ValueError を送出する。
    """
    prg_size = _ines_prg_size(rom_data)
    base = _base_signature_region(rom_data)
    if prg_size == _M66_PRG_SIZE and base in ("US", "JP"):
        return base + "66"
    if prg_size == _STD_PRG_SIZE and base in ("US", "JP"):
        return base

    for region, offset, expected in REGION_RULES:
        if offset < len(rom_data) and rom_data[offset] == expected:
            return region

    # フォールバック: CHR-ROM CRC32 による判定（改造ROM対応）
    chr_crc = _get_chr_crc32(rom_data)
    if chr_crc is not None and chr_crc in CHR_CRC32_TO_REGION:
        return CHR_CRC32_TO_REGION[chr_crc]

    raise ValueError("対応外のROMです。Solomon's Key の US版 または JP版 を使用してください。")


def is_expanded(region: str) -> bool:
    """拡張ROM (mapper 66) かどうか"""
    return region in ("US66", "JP66")


def base_region(region: str) -> str:
    """拡張ROMの場合、元のリージョンを返す"""
    if region == "US66":
        return "US"
    if region == "JP66":
        return "JP"
    return region

"""Stage frame CHR tile patches."""


class StageFrameError(ValueError):
    pass


FRAME_TILE_OFF = 0x174B
FRAME_TILE_LEN = 16
INES_MAGIC = b"NES\x1a"
CHR_BANK_SIZE = 0x2000
CHR_TILE_SIZE = 16
CHR_TILES_PER_BANK = CHR_BANK_SIZE // CHR_TILE_SIZE
CHR_BANK_COUNT = 4

# CPU $973B-$974A. SUB $968E writes these 4-byte patterns in reverse order
# for the side columns and bottom two nametable rows.
STOCK_STAGE_FRAME_TILES = bytes.fromhex(
    "A3 A6 A6 A4"
    " AA A2 A2 A0"
    " A4 A1 A1 A0"
    " A3 AB AB AA"
)

# Legacy v0.8.127 implementation rewrote the nametable tile-number table.
# It directly referenced the existing white block tiles $84-$87.
LEGACY_CUSTOMIZER_WHITE_FRAME_TILES = bytes.fromhex(
    "87 85 87 85"
    " 86 84 86 84"
    " 85 84 85 84"
    " 87 86 87 86"
)

# Modern handling writes white-block pixels into a small set of stock frame
# tile slots, then points the frame table at those rewritten slots.  SUB $968E
# writes each 4-byte row in reverse order, so the last two rows below appear
# on screen as A0 A1 A0 A1 / AA AB AA AB.
CUSTOMIZER_WHITE_FRAME_TILES = bytes.fromhex(
    "AB A1 AB A1"
    " AA A0 AA A0"
    " A1 A0 A1 A0"
    " AB AA AB AA"
)

# These local CHR tile IDs are in each 8KB CHR bank.  Copy white block corners
# into four stock frame tile slots, then repeat those slots through the table.
FRAME_CHR_COPY_PAIRS = (
    (0x1A0, 0x184),
    (0x1A1, 0x185),
    (0x1AA, 0x186),
    (0x1AB, 0x187),
)

# Original JP frame art for the local destination tiles above.  This is needed
# because ON overwrites those CHR tiles, so OFF cannot recover them from ROM.
STOCK_FRAME_CHR_TILE_BYTES = {
    0x1A0: bytes.fromhex("FF FF 90 D2 B2 92 9B 9E FF FF FF FF FF FF FF FF"),
    0x1A1: bytes.fromhex("FF FF 12 D6 BA 90 99 9A FF FF FF FF FF FF FF FF"),
    0x1AA: bytes.fromhex("9E 9D AD AF BB C9 80 00 FF FF FF FF FF FF FF 00"),
    0x1AB: bytes.fromhex("A9 67 59 96 D3 5A 40 00 FF FF FF FF FF FF FF 00"),
}


def _chr_start_and_banks(rom_data: bytes) -> tuple[int, int]:
    if len(rom_data) < 16 or bytes(rom_data[:4]) != INES_MAGIC:
        raise StageFrameError("ROM is not a valid iNES file.")
    prg_bytes = int(rom_data[4]) * 0x4000
    chr_banks = int(rom_data[5])
    chr_start = 16 + prg_bytes
    if chr_banks < CHR_BANK_COUNT:
        raise StageFrameError(
            f"ROM has too few CHR banks ({chr_banks}); expected {CHR_BANK_COUNT}."
        )
    if len(rom_data) < chr_start + chr_banks * CHR_BANK_SIZE:
        raise StageFrameError("ROM is too small for its iNES CHR size.")
    return chr_start, chr_banks


def _chr_tile_offset(chr_start: int, bank: int, local_tile: int) -> int:
    tile_no = bank * CHR_TILES_PER_BANK + local_tile
    return chr_start + tile_no * CHR_TILE_SIZE


def _read_tile(rom_data: bytes, chr_start: int, bank: int, local_tile: int) -> bytes:
    off = _chr_tile_offset(chr_start, bank, local_tile)
    return bytes(rom_data[off:off + CHR_TILE_SIZE])


def _source_bank_for_frame_copy(dst_bank: int) -> int:
    # CHR bank 3 does not carry the stock white-block source art; use bank 0.
    return 0 if int(dst_bank) == 3 else int(dst_bank)


def _is_chr_customizer_white(rom_data: bytes) -> bool:
    try:
        chr_start, _chr_banks = _chr_start_and_banks(rom_data)
    except StageFrameError:
        return False
    for bank in range(CHR_BANK_COUNT):
        for dst_tile, src_tile in FRAME_CHR_COPY_PAIRS:
            src_bank = _source_bank_for_frame_copy(bank)
            if _read_tile(rom_data, chr_start, bank, dst_tile) != _read_tile(
                    rom_data, chr_start, src_bank, src_tile):
                return False
    return True


def _is_chr_stock_frame(rom_data: bytes) -> bool:
    try:
        chr_start, _chr_banks = _chr_start_and_banks(rom_data)
    except StageFrameError:
        return False
    for bank in range(CHR_BANK_COUNT):
        for dst_tile, _src_tile in FRAME_CHR_COPY_PAIRS:
            if (
                    _read_tile(rom_data, chr_start, bank, dst_tile)
                    != STOCK_FRAME_CHR_TILE_BYTES[dst_tile]):
                return False
    return True


def is_supported_region(region: str) -> bool:
    return str(region or "") == "JP"


def current_state(rom_data: bytes) -> str:
    end = FRAME_TILE_OFF + FRAME_TILE_LEN
    if len(rom_data) < end:
        return "missing"
    current = bytes(rom_data[FRAME_TILE_OFF:end])
    if current == LEGACY_CUSTOMIZER_WHITE_FRAME_TILES:
        return "customizer_white"
    if current == CUSTOMIZER_WHITE_FRAME_TILES and _is_chr_customizer_white(rom_data):
        return "customizer_white"
    if current == STOCK_STAGE_FRAME_TILES and _is_chr_stock_frame(rom_data):
        return "stock"
    return "unknown"


def is_customizer_white_frame(rom_data: bytes) -> bool:
    return current_state(rom_data) == "customizer_white"


def apply_customizer_white_frame(
        rom_data: bytearray, enabled: bool = True, region: str = "JP") -> list[str]:
    if isinstance(enabled, str) and region == "JP":
        region = enabled
        enabled = True
    if region != "JP":
        return []
    end = FRAME_TILE_OFF + FRAME_TILE_LEN
    if len(rom_data) < end:
        raise StageFrameError("ROM is too small for the stage frame tile table.")
    current = bytes(rom_data[FRAME_TILE_OFF:end])
    known_tables = (
        STOCK_STAGE_FRAME_TILES,
        LEGACY_CUSTOMIZER_WHITE_FRAME_TILES,
        CUSTOMIZER_WHITE_FRAME_TILES,
    )
    if current not in known_tables:
        got = current.hex(" ").upper()
        expected = STOCK_STAGE_FRAME_TILES.hex(" ").upper()
        raise StageFrameError(
            "stage frame tile table signature mismatch: "
            f"got {got}, expected {expected}"
        )
    chr_start, _chr_banks = _chr_start_and_banks(rom_data)
    changed = []
    target_table = CUSTOMIZER_WHITE_FRAME_TILES if enabled else STOCK_STAGE_FRAME_TILES
    if current != target_table:
        rom_data[FRAME_TILE_OFF:end] = target_table
        changed.append(
            "外枠Nametableタイル列を"
            + ("白ブロック反復値へ更新" if enabled else "原作値へ復元")
        )
    for bank in range(CHR_BANK_COUNT):
        for dst_tile, src_tile in FRAME_CHR_COPY_PAIRS:
            dst = _chr_tile_offset(chr_start, bank, dst_tile)
            if enabled:
                src_bank = _source_bank_for_frame_copy(bank)
                src = _chr_tile_offset(chr_start, src_bank, src_tile)
                target = bytes(rom_data[src:src + CHR_TILE_SIZE])
            else:
                target = STOCK_FRAME_CHR_TILE_BYTES[dst_tile]
            if bytes(rom_data[dst:dst + CHR_TILE_SIZE]) != target:
                rom_data[dst:dst + CHR_TILE_SIZE] = target
                changed.append(
                    f"CHR bank {bank} tile ${dst_tile:03X}->"
                    + ("白ブロック柄" if enabled else "原作柄")
                )
    if not changed:
        return []
    return ["ステージ外枠 → " + ("白ブロック柄" if enabled else "原作柄")]


apply = apply_customizer_white_frame

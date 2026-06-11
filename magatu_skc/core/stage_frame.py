"""Stage nametable frame patches."""


class StageFrameError(ValueError):
    pass


FRAME_TILE_OFF = 0x174B
FRAME_TILE_LEN = 16

# CPU $973B-$974A. SUB $968E writes these 4-byte patterns in reverse order
# for the side columns and bottom two nametable rows.
STOCK_STAGE_FRAME_TILES = bytes.fromhex(
    "A3 A6 A6 A4"
    " AA A2 A2 A0"
    " A4 A1 A1 A0"
    " A3 AB AB AA"
)

# Use the same 2x2 white block tile IDs used by the editor canvas preview
# (skc_config tile no. 2: PPU tiles $84,$85,$86,$87).
CUSTOMIZER_WHITE_FRAME_TILES = bytes.fromhex(
    "87 85 87 85"
    " 86 84 86 84"
    " 85 84 85 84"
    " 87 86 87 86"
)


def is_supported_region(region: str) -> bool:
    return str(region or "") == "JP"


def current_state(rom_data: bytes) -> str:
    end = FRAME_TILE_OFF + FRAME_TILE_LEN
    if len(rom_data) < end:
        return "missing"
    current = bytes(rom_data[FRAME_TILE_OFF:end])
    if current == CUSTOMIZER_WHITE_FRAME_TILES:
        return "customizer_white"
    if current == STOCK_STAGE_FRAME_TILES:
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
    target = CUSTOMIZER_WHITE_FRAME_TILES if enabled else STOCK_STAGE_FRAME_TILES
    if current == target:
        return []
    if current not in (STOCK_STAGE_FRAME_TILES, CUSTOMIZER_WHITE_FRAME_TILES):
        got = current.hex(" ").upper()
        expected = STOCK_STAGE_FRAME_TILES.hex(" ").upper()
        raise StageFrameError(
            "stage frame tile table signature mismatch: "
            f"got {got}, expected {expected}"
        )
    rom_data[FRAME_TILE_OFF:end] = target
    return [
        "ステージ外枠 → "
        + ("白ブロック柄" if enabled else "原作柄")
    ]


apply = apply_customizer_white_frame

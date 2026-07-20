"""ROMバイナリ操作 - iNES形式の読み書き"""
import zipfile
import zlib
from pathlib import Path
from . import region as region_mod
from . import us_jp_normalizer


def _is_nes_file(name: str) -> bool:
    """.nes 拡張子のファイル名か判定（パス区切り無視）"""
    return name.lower().endswith(".nes")


def extract_nes_from_zip(zip_path: str) -> tuple:
    """ZIPファイル内から最初の .nes ファイルを抽出

    Args:
        zip_path: ZIPファイルパス

    Returns:
        (内部のファイル名, バイナリデータ)

    Raises:
        ValueError: ZIPに .nes が含まれていない
    """
    with zipfile.ZipFile(zip_path) as z:
        # ディレクトリ階層を辿って .nes ファイルを探す
        nes_entries = [n for n in z.namelist()
                       if not n.endswith("/") and _is_nes_file(n)]

        if not nes_entries:
            raise ValueError(f"ZIP内に.nesファイルが見つかりません: {zip_path}")

        # 最初に見つかったものを使用（複数ある場合は警告できるが今回は無視）
        target = nes_entries[0]
        with z.open(target) as f:
            data = f.read()
        return (target, data)


def load_rom_data(path: str) -> tuple:
    """パスから ROM データを読み込み（.nes または .zip 対応）

    Args:
        path: .nes または .zip ファイルパス

    Returns:
        (表示用ファイル名, バイナリデータ)
    """
    p = Path(path)

    if p.suffix.lower() == ".zip":
        inner_name, data = extract_nes_from_zip(str(p))
        inner_basename = Path(inner_name).name
        return (inner_basename, data)

    # 通常の .nes ファイル
    with open(path, "rb") as f:
        data = f.read()
    return (p.name, data)


# 既知のJPオリジナルROM CRC32値（iNESヘッダ込み）
KNOWN_JP_ORIGINAL_CRC32 = {
    "013ED497",
    "5B49FEDB",
    "2FE9E2CA",
}

# 既知ROM CRC32値（表示用）
KNOWN_CRC32 = {
    crc: "Solomon no Kagi (Japan)"
    for crc in KNOWN_JP_ORIGINAL_CRC32
}
KNOWN_CRC32.update({
    crc: "Solomon's Key (USA)"
    for crc in us_jp_normalizer.KNOWN_US_ORIGINAL_CRC32
})


def crc32_hex(data: bytes) -> str:
    return f"{zlib.crc32(bytes(data)) & 0xffffffff:08X}"


def ines_mapper_no(data: bytes):
    data = bytes(data)
    if len(data) < 8 or data[:4] != b"NES\x1a":
        return None
    return (data[6] >> 4) | (data[7] & 0xF0)


def is_known_jp_original_data(data: bytes) -> bool:
    return crc32_hex(data) in KNOWN_JP_ORIGINAL_CRC32


def is_known_editor_standard_data(data: bytes) -> bool:
    """Known mapper-3 input in the canonical JP logical layout."""
    return (
        is_known_jp_original_data(data)
        or us_jp_normalizer.is_normalized_us_data(data)
    )


def has_customizer_metadata(data: bytes) -> bool:
    from . import rom_metadata
    return rom_metadata.read_metadata(bytes(data)) is not None


_SKCHAIN_US66_HEADER = bytes.fromhex("4E45531A040420400000000000000000")
_SKCHAIN_US66_L_A1 = bytes.fromhex(
    "10BD009A9DCF07CAD0F74CD00760A9139D1180200180A9039D11804C009A009A"
)
_SKCHAIN_US66_CHECKS = (
    (0x0000, _SKCHAIN_US66_HEADER),
    (0x00FF, bytes.fromhex("00010203")),
    (0x0D30, bytes.fromhex("00")),
    (0x188F, bytes.fromhex("EAEAEA")),
    (0x1A03, _SKCHAIN_US66_L_A1),
    (0x3FF2, bytes(16)),
    (0x5C10, bytes.fromhex("8088")),
    (0x5C20, bytes.fromhex("0707")),
    (0x5C30, bytes.fromhex("C0C8")),
    (0x5C41, bytes.fromhex("0707")),
    (0x5CFC, bytes.fromhex("A0A0A0A0A0A0A0A0")),
    (0x5D31, bytes.fromhex("0707070707070707")),
    (0x6A2C, bytes.fromhex("9090909090909090")),
    (0x6A61, bytes.fromhex("0707070707070707")),
    (0x802C, bytes.fromhex("00C9F8F017293FC9")),
)


def is_skchain_us66_data(data: bytes) -> bool:
    """skchain系のUS mapper66拡張ROMかどうか。"""
    if len(data) != 98320:
        return False
    if len(data) < 0x8034:
        return False
    return all(data[off:off + len(sig)] == sig for off, sig in _SKCHAIN_US66_CHECKS)


class Rom:
    """NES ROMファイル（iNES形式）"""

    def __init__(self, data: bytes, path: str = ""):
        self.data = bytearray(data)
        self.path = path
        self.display_name = Path(path).name if path else ""
        self.region = region_mod.detect_region(bytes(data))
        self.source_data = bytes(data)
        self.source_region = self.region
        self.was_us_normalized = False
        self._crc32 = None  # 遅延計算

    @property
    def crc32(self) -> int:
        """ROMファイル全体のCRC32（iNESヘッダ含む）"""
        if self._crc32 is None:
            self._crc32 = zlib.crc32(bytes(self.data)) & 0xffffffff
        return self._crc32

    def get_crc32_hex(self) -> str:
        return f"{self.crc32:08X}"

    def get_known_name(self) -> str:
        """正規ROMの場合は名称、不明なら空文字"""
        return KNOWN_CRC32.get(self.get_crc32_hex(), "")

    def is_known_jp_original(self) -> bool:
        """確認済みの日本版オリジナル通常ROMかどうか。"""
        return is_known_jp_original_data(bytes(self.data))

    def is_known_editor_standard(self) -> bool:
        """確認済みでJP論理配置になっている通常ROMかどうか。"""
        return is_known_editor_standard_data(bytes(self.data))

    def has_customizer_metadata(self) -> bool:
        return has_customizer_metadata(bytes(self.data))

    def is_skchain_us66(self) -> bool:
        return is_skchain_us66_data(bytes(self.data))

    def ines_mapper_no(self):
        return ines_mapper_no(bytes(self.data))

    def is_mapper3(self) -> bool:
        return self.ines_mapper_no() == 3

    def is_supported_editor_input(self) -> bool:
        """通常編集入口で受け付けるROMかどうか。"""
        if self.base_region() != "JP":
            return False
        if self.is_expanded():
            return self.region == "JP66" and self.has_customizer_metadata()
        return self.is_known_editor_standard()

    def readonly_input_reason(self) -> str:
        """編集不可の閲覧/エクスポート専用入口なら理由を返す。"""
        if self.is_supported_editor_input():
            return ""
        if self.is_skchain_us66():
            return "skchain US66 mapper66 ROM"
        if not self.is_expanded() and self.is_mapper3() and self.region in ("US", "JP"):
            return f"{self.region} mapper3 ROM"
        return ""

    def is_supported_readonly_input(self) -> bool:
        return bool(self.readonly_input_reason())

    @classmethod
    def load(cls, path: str) -> "Rom":
        """ROMファイル読み込み（.nes / .zip 両対応）"""
        display_name, data = load_rom_data(path)
        source_data = bytes(data)
        source_region = region_mod.detect_region(source_data)
        was_us_normalized = us_jp_normalizer.is_supported_us_original(source_data)
        if was_us_normalized:
            data = us_jp_normalizer.normalize_us_original(source_data)
        rom = cls(data, path)
        rom.display_name = display_name
        rom.source_data = source_data
        rom.source_region = source_region
        rom.was_us_normalized = was_us_normalized
        return rom

    def save(self, path: str):
        with open(path, "wb") as f:
            f.write(bytes(self.data))

    def get_byte(self, offset: int) -> int:
        return self.data[offset]

    def set_byte(self, offset: int, value: int):
        self.data[offset] = value & 0xff

    def get_bytes(self, offset: int, length: int) -> bytes:
        return bytes(self.data[offset:offset + length])

    def set_bytes(self, offset: int, data: bytes):
        for i, b in enumerate(data):
            self.data[offset + i] = b

    def is_expanded(self) -> bool:
        return region_mod.is_expanded(self.region)

    def base_region(self) -> str:
        return region_mod.base_region(self.region)

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return f"Rom(region={self.region}, size={len(self.data)}, path={self.path})"

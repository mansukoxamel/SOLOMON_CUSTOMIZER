"""ROMバイナリ操作 - iNES形式の読み書き"""
import zipfile
import zlib
from pathlib import Path
from . import region as region_mod


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
        # 表示用: "rom.nes (in archive.zip)"
        inner_basename = Path(inner_name).name
        display_name = f"{inner_basename} (in {p.name})"
        return (display_name, data)

    # 通常の .nes ファイル
    with open(path, "rb") as f:
        data = f.read()
    return (p.name, data)


# 既知のJP ROM CRC32値（iNESヘッダ込み、表示用）
KNOWN_CRC32 = {
    "013ED497": "Solomon no Kagi (Japan)",
    "5B49FEDB": "Solomon no Kagi (Japan)",
    "2FE9E2CA": "Solomon no Kagi (Japan)",
}


class Rom:
    """NES ROMファイル（iNES形式）"""

    def __init__(self, data: bytes, path: str = ""):
        self.data = bytearray(data)
        self.path = path
        self.display_name = Path(path).name if path else ""
        self.region = region_mod.detect_region(bytes(data))
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

    @classmethod
    def load(cls, path: str) -> "Rom":
        """ROMファイル読み込み（.nes / .zip 両対応）"""
        display_name, data = load_rom_data(path)
        rom = cls(data, path)
        rom.display_name = display_name
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

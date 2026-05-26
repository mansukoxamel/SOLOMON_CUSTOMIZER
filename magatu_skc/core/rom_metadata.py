"""SOLOMON_CUSTOMIZER metadata stamp for expanded mapper66 ROMs."""
from __future__ import annotations

from .. import __version__


META_OFFSET = 0xFF00
META_LENGTH = 64
META_MAGIC = b"SOLOMON_CUSTOMIZER_META\x00"
META_FORMAT = 1


def build_metadata_blob(app_version: str | None = None) -> bytes:
    version = (app_version or __version__).encode("ascii", "replace")[:24]
    blob = bytearray([0xFF] * META_LENGTH)
    blob[:len(META_MAGIC)] = META_MAGIC
    blob[len(META_MAGIC)] = META_FORMAT
    start = len(META_MAGIC) + 1
    blob[start:start + len(version)] = version
    blob[start + len(version)] = 0
    return bytes(blob)


def write_metadata(rom_data: bytearray, app_version: str | None = None) -> bool:
    """Write the app version stamp into mapper66 PRG bank1 free space."""
    end = META_OFFSET + META_LENGTH
    if len(rom_data) < end:
        return False
    blob = build_metadata_blob(app_version)
    if bytes(rom_data[META_OFFSET:end]) == blob:
        return False
    rom_data[META_OFFSET:end] = blob
    return True


def read_metadata(rom_data: bytes) -> dict | None:
    end = META_OFFSET + META_LENGTH
    if len(rom_data) < end:
        return None
    raw = bytes(rom_data[META_OFFSET:end])
    if not raw.startswith(META_MAGIC):
        return None
    fmt = raw[len(META_MAGIC)]
    start = len(META_MAGIC) + 1
    tail = raw[start:]
    version = tail.split(b"\x00", 1)[0].decode("ascii", "replace")
    return {
        "format": fmt,
        "app_version": version,
        "offset": META_OFFSET,
        "length": META_LENGTH,
    }

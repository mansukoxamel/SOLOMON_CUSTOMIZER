"""Normalize the verified US mapper-3 ROM into the JP logical PRG layout.

The output is still a standard 32 KiB PRG / 32 KiB CHR ROM.  Program and
data blocks are rearranged to the JP addresses expected by the customizer,
while the US title-screen data and the complete US CHR remain user-owned
source bytes.  The US license block is deliberately omitted because its JP
destination is unused space.
"""
from __future__ import annotations

import base64
import hashlib
import zlib


US_ORIGINAL_SIZE = 65552
US_ORIGINAL_CRC32 = "B7A00D99"
US_ORIGINAL_SHA256 = (
    "81308ffe54c55508c143d04d0f5ef5e88e1da4d75483d8c43148011647fd0065"
)
NORMALIZED_US_CRC32 = "7A1F4515"
NORMALIZED_US_SHA256 = (
    "764ebf3bcfbff6f0b5e6e585705e562b60220c89a37c032758dfd18afcccda30"
)

# (JP target start, JP target end, US source address delta), end-exclusive.
_COPY_SPANS = (
    (0x8000, 0x9497, 0),
    (0x9497, 0x9589, 0x0A),
    (0x9589, 0x959E, 0x69),
    (0x959E, 0x9EA6, 0x7D),
    (0x9EA6, 0x9EBA, 0x69),
    (0x9EC0, 0xB3B1, 0x140),
    # Preserve the US 00/FF padding immediately after the matching RTS.
    (0xB3B1, 0xB3C0, 0x140),
    (0xB3D0, 0xBBE2, 0x430),
    (0xC200, 0xCB80, -0x100),
    (0xCB8D, 0xCBB1, -0xB3),
    (0xCBB1, 0xCBEA, -0xB1),
    (0xCBEA, 0xCFDE, -0xA9),
    (0xD000, 0x10000, 0),
)

_EA_SPANS = (
    (0x8BE2, 0x8C00),
    (0x9EBA, 0x9EC0),
    (0xB3C0, 0xB3D0),
    (0xBBE2, 0xC200),
    (0xCFDE, 0xD000),
    (0xDBDF, 0xDC00),
    (0xEFC4, 0xF000),
)

# The no-license JP-layout title entry has no byte-identical US sequence.
_BRIDGES = (
    (0xCB80, bytes.fromhex("2018cc2076cd20b6cca9008528")),
)

# Delta-varint encoded CPU addresses of 664 little-endian absolute operands.
# This is relocation metadata only; it does not contain ROM payload bytes.
_WORD_DELTA_B85 = (
    "c-nnZ%W4!s6s7w1sp{_Pn(D58PERJCp2@s44-+9e2_y@HAqgTuA%ciR7a~IlxHs+<+_+G1E3Vw=&TkL|"
    "*ZxK}?(C3pBj~BB3+J3$x2UT7)xrVJ*f$&B8QwAc(3ZvPX<Ji#WZtOftp@TQU7Jm%L!nRZ7pryrd^?K)"
    "T^{2n#iYXJt7{^UA}?2-;-@csnsnSVX5KTc=oxJnLms_lx+C?@di!wm=rbcC&be$8jjKH+lc-XY>dpax"
    "oArwOms%5TOy6C#{*5&#I-%4dN0V3cbpp(hbbSHK<Xv23A+!f(DW9?iaHW+mqnz@2qT*rPi(j)h3|r3N"
    "uOs%kY$1_opO3|M){Eo#@O*0`M36ee%W5+Srlkr)qlFoHdrB8dNK@`1MACa)Yq4mkrt%sz^;39#Bhswu"
    "k_iBTLdj;n`^WaHWEQiF9Xx`Ar=cyxg+7K2-X{<#0T(HuqjX7v6b%I@*#6FV38C=ZA(E&TXhzgQQcpH@"
    "xYEortrICDuNp*!0#8IpxEr}f2fBXw#Cb{Pm!AnEh3l#h4Er7M4S&ulgqkA<D~=#JayWU&u-nURa_58p"
    "e3HdapG>IgN^vU<9~du6Jr{)-)D6&ZKe3ao`UV7t^ZOy3_{N4T0phQibfw=wvUOdGvIwOA8!T`=Dg"
)

_RELATIVE_BRANCH_OPERANDS = (0xCBF4, 0xCC06)

# Split pointer tables, low/high immediates, layout bridges, and the unused
# IRQ-vector tail that cannot be expressed as ordinary 16-bit relocations.
_EXPLICIT_FIXUPS = (
    (0x8279, bytes.fromhex("f74b70d692af3773b420b95f03879b")),
    (0x828A, bytes.fromhex("aaaaaaaaabababaaababababababa9")),
    (0x8E2F, bytes.fromhex("bf9e")),
    (0x8E44, bytes.fromhex("c1cfb3")),
    (0x9483, bytes.fromhex("95")),
    (0x9488, bytes.fromhex("a2c7dbed078a18252a3f5c718594")),
    (0x9497, bytes.fromhex("9494")),
    (0x949D, bytes.fromhex("95")),
    (0x96A8, bytes.fromhex("3b")),
    (0x96CE, bytes.fromhex("3f")),
    (0x96F0, bytes.fromhex("43")),
    (0x96FD, bytes.fromhex("47")),
    (0xA0B4, bytes.fromhex("ec")),
    (0xA0B8, bytes.fromhex("a0")),
    (0xA0CB, bytes.fromhex("f2")),
    (0xA0CF, bytes.fromhex("a0")),
    (0xB484, bytes.fromhex("b2")),
    (0xB488, bytes.fromhex("bb")),
    (0xB533, bytes.fromhex("ca")),
    (0xB537, bytes.fromhex("bb")),
    (0xCBEA, bytes.fromhex("d0")),
    (0xCBF8, bytes.fromhex("0e")),
    (0xCCBA, bytes.fromhex("08")),
    (0xCCBE, bytes.fromhex("ce")),
    (0xCD84, bytes.fromhex("a3")),
    (0xCD88, bytes.fromhex("ce")),
)


def _crc32_hex(data: bytes) -> str:
    return f"{zlib.crc32(bytes(data)) & 0xffffffff:08X}"


def is_supported_us_original(data: bytes) -> bool:
    data = bytes(data)
    return (
        len(data) == US_ORIGINAL_SIZE
        and _crc32_hex(data) == US_ORIGINAL_CRC32
        and hashlib.sha256(data).hexdigest() == US_ORIGINAL_SHA256
    )


def is_normalized_us_data(data: bytes) -> bool:
    data = bytes(data)
    if len(data) != US_ORIGINAL_SIZE or _crc32_hex(data) != NORMALIZED_US_CRC32:
        return False
    return hashlib.sha256(data).hexdigest() == NORMALIZED_US_SHA256


def _file_offset(cpu_address: int) -> int:
    if not 0x8000 <= cpu_address <= 0xFFFF:
        raise ValueError(f"PRG CPU address out of range: 0x{cpu_address:04X}")
    return 0x10 + cpu_address - 0x8000


def _source_to_target(source_address: int) -> int | None:
    for target_start, target_end, delta in _COPY_SPANS:
        source_start = target_start + delta
        source_end = target_end + delta
        if source_start <= source_address < source_end:
            return source_address - delta
    return None


def _decode_word_offsets() -> tuple[int, ...]:
    packed = base64.b85decode(_WORD_DELTA_B85.encode("ascii"))
    encoded = zlib.decompress(packed)
    result = []
    current = 0x8000
    value = 0
    shift = 0
    for byte in encoded:
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
            continue
        current += value
        result.append(current)
        value = 0
        shift = 0
    if shift or value:
        raise RuntimeError("US relocation offset metadata is truncated.")
    if len(result) != 664 or tuple(result) != tuple(sorted(set(result))):
        raise RuntimeError("US relocation offset metadata is invalid.")
    return tuple(result)


_WORD_OPERANDS = _decode_word_offsets()


def _copy_prg_span(result: bytearray, source: bytes,
                   target_start: int, target_end: int, delta: int) -> None:
    target_off = _file_offset(target_start)
    source_off = _file_offset(target_start + delta)
    length = target_end - target_start
    result[target_off:target_off + length] = source[source_off:source_off + length]


def _relocate_word(result: bytearray, cpu_address: int) -> None:
    offset = _file_offset(cpu_address)
    source_address = result[offset] | (result[offset + 1] << 8)
    target_address = _source_to_target(source_address)
    if target_address is None:
        raise ValueError(
            f"US absolute operand at 0x{cpu_address:04X} points outside the map: "
            f"0x{source_address:04X}"
        )
    result[offset:offset + 2] = target_address.to_bytes(2, "little")


def _relocate_branch(result: bytearray, operand_address: int) -> None:
    opcode_address = operand_address - 1
    opcode_offset = _file_offset(opcode_address)
    delta = next(
        (span_delta for start, end, span_delta in _COPY_SPANS
         if start <= opcode_address < end),
        None,
    )
    if delta is None:
        raise ValueError(f"US branch at 0x{opcode_address:04X} is outside the map.")
    relative = result[opcode_offset + 1]
    if relative >= 0x80:
        relative -= 0x100
    source_pc = opcode_address + delta
    source_target = (source_pc + 2 + relative) & 0xFFFF
    target = _source_to_target(source_target)
    if target is None:
        raise ValueError(
            f"US branch at 0x{opcode_address:04X} targets outside the map: "
            f"0x{source_target:04X}"
        )
    result[opcode_offset + 1] = (target - (opcode_address + 2)) & 0xFF


def normalize_us_original(data: bytes) -> bytes:
    """Return the verified US original in the canonical JP mapper-3 layout."""
    source = bytes(data)
    if not is_supported_us_original(source):
        raise ValueError(
            "US layout normalization accepts only the verified original ROM "
            f"(size={len(source)}, CRC32={_crc32_hex(source)})."
        )

    result = bytearray(source)
    result[7:16] = bytes(9)  # Clean NES 1.0 reserved/header garbage.

    for target_start, target_end, delta in _COPY_SPANS:
        _copy_prg_span(result, source, target_start, target_end, delta)
    for start, end in _EA_SPANS:
        start_off = _file_offset(start)
        result[start_off:start_off + end - start] = bytes([0xEA]) * (end - start)
    for address, bridge in _BRIDGES:
        offset = _file_offset(address)
        result[offset:offset + len(bridge)] = bridge

    for address in _WORD_OPERANDS:
        _relocate_word(result, address)
    for address in _RELATIVE_BRANCH_OPERANDS:
        _relocate_branch(result, address)
    for address, replacement in _EXPLICIT_FIXUPS:
        offset = _file_offset(address)
        result[offset:offset + len(replacement)] = replacement

    normalized = bytes(result)
    digest = hashlib.sha256(normalized).hexdigest()
    if digest != NORMALIZED_US_SHA256:
        raise RuntimeError(
            "US layout normalization did not produce the verified canonical bytes "
            f"(SHA256={digest})."
        )
    return normalized

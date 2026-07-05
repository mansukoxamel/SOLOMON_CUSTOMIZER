"""Stage-start announcement overlay.

The gameplay start screen uses the gameplay CHR banks, so this patch installs
two missing letters into unused tiles and overlays the accepted two-column
message layout on top of the stock stage intro screen.
"""
from __future__ import annotations

from . import room_flags, stage_ext


class StageAnnouncementError(ValueError):
    pass


def _cf(cpu: int) -> int:
    return 0x10 + (cpu - 0x8000)


def _cpu(file_off: int) -> int:
    return 0x8000 + (file_off - 0x10)


def _word(cpu: int) -> bytes:
    return bytes((cpu & 0xFF, cpu >> 8))


OFF_HOOK_START_UPDATE = _cf(0x9061)
ORIG_START_UPDATE = bytes.fromhex("20 5e 91")

OLD_OFF_MAIN = 0x6010
OFF_MAIN = 0x6B06
OFF_MASK_TABLE = 0x6B24
OFF_DRAW = 0x6B29
OFF_PTR_TABLE = 0x6B42
OFF_KEY_GATE = 0x6B52
OFF_FAIRY_GATE = 0x6B5F
OFF_WARP_GATE = 0x6B6C
OFF_FREE_AFTER_STAGE_ANNOUNCEMENT = 0x6BEC
FREE_AFTER_STAGE_ANNOUNCEMENT_LEN = 24

CPU_MAIN = _cpu(OFF_MAIN)
CPU_MASK_TABLE = _cpu(OFF_MASK_TABLE)
CPU_DRAW = _cpu(OFF_DRAW)
CPU_PTR_TABLE = _cpu(OFF_PTR_TABLE)
CPU_KEY_GATE = _cpu(OFF_KEY_GATE)
CPU_FAIRY_GATE = _cpu(OFF_FAIRY_GATE)
CPU_WARP_GATE = _cpu(OFF_WARP_GATE)

HOOK_START_UPDATE = bytes((0x20, *(_word(CPU_MAIN))))
OLD_HOOK_START_UPDATE = bytes((0x20, *(_word(_cpu(OLD_OFF_MAIN)))))
OLD_MAIN_BAD_ORDER = bytes.fromhex(
    "20 5e 91 a2 00 ad 78 07 3d fa 8b f0 03 20 bc e0"
    "e8 e0 05 d0 f0 4c c0 b3 08 10 01 04 80"
)
OLD_MAIN_V164 = bytes.fromhex(
    "a2 00 ad 78 07 3d fa 8b f0 03 20 bc e0 e8 e0 05"
    "d0 f0 20 c0 b3 4c 5e 91 08 10 01 04 80"
)

K_TILE = 0x25
P_TILE = 0x27
SPACE_TILE = 0x24
CUSTOM_K_CHR = 0x125
CUSTOM_P_CHR = 0x127
K_TILE_BYTES = bytes.fromhex("f2 f4 fc f2 f2 f2 00 00 f2 f4 fc f2 f2 f2 00 00")
P_TILE_BYTES = bytes.fromhex("fc f2 f2 f2 fc f0 00 00 fc f2 f2 f2 fc f0 00 00")


SCRIPT_SPECS = (
    (0x6B79, 21, 4, "DARK ROOM"),
    (0x6B86, 23, 4, "FIRE LOSS"),
    (0x6B93, 21, 17, "HIDDEN DOOR"),
    (0x6BA2, 23, 17, "FIRE SEALED"),
    (0x6BB1, 25, 17, "SPELL SEALED"),
    (0x6BC1, 25, 4, "KEY ENEMY"),
    (0x6BCE, 27, 4, "FAIRY ENEMY"),
    (0x6BDD, 27, 17, "MIRROR LINK"),
)

ROOM_FLAG_MASKS = bytes((
    room_flags.BIT_DARK,
    room_flags.BIT_FIRE_RESET,
    room_flags.DOOR_STATE_MASK,
    room_flags.BIT_NO_BFIRE,
    room_flags.BIT_NO_ASTONE,
))


def _encode_text(text: str) -> bytes:
    out = bytearray()
    for ch in text:
        if ch == " ":
            out.append(SPACE_TILE)
        elif ch == "K":
            out.append(K_TILE)
        elif ch == "P":
            out.append(P_TILE)
        elif "A" <= ch <= "Z":
            out.append(0x0A + ord(ch) - ord("A"))
        else:
            raise StageAnnouncementError(f"Unsupported announcement character: {ch!r}")
    return bytes(out)


def _build_script(row: int, col: int, text: str) -> bytes:
    ppu = 0x2000 + row * 32 + col
    body = _encode_text(text)
    return bytes((ppu >> 8, ppu & 0xFF, 0x40 + len(body) - 1)) + body + b"\x00"


SCRIPTS = tuple((off, _build_script(row, col, text), text) for off, row, col, text in SCRIPT_SPECS)


def _build_main() -> bytes:
    b = bytearray()
    b += b"\xa2\x00"                     # LDX #0
    loop = len(b)
    b += b"\xad\x78\x07"                 # LDA $0778
    mask_addr = CPU_MASK_TABLE
    b += bytes((0x3D, mask_addr & 0xFF, mask_addr >> 8))  # AND masks,X
    b += b"\xf0\x03"                     # BEQ skip draw
    b += bytes((0x20, *(_word(CPU_DRAW)))) # JSR draw
    b += b"\xe8\xe0\x05"                 # INX / CPX #5
    b += bytes((0xD0, (loop - (len(b) + 2)) & 0xFF))
    b += bytes((0x20, *(_word(CPU_KEY_GATE))))
    b += bytes((0x20, *(_word(CPU_FAIRY_GATE))))
    b += bytes((0x20, *(_word(CPU_WARP_GATE))))
    b += b"\x4c\x5e\x91"                 # Preserve stock intro update last.
    return bytes(b)


def _build_draw() -> bytes:
    b = bytearray()
    b += b"\x8a\x48"                     # TXA / PHA: keep caller loop index.
    wait = CPU_DRAW + len(b)
    b += b"\xa5\x1b\xf0\x06"             # LDA $1B / BEQ ready
    b += b"\x20\xb4\x8d"                 # JSR $8DB4, same waiter used by $9471.
    b += bytes((0x4C, wait & 0xFF, wait >> 8))
    b += b"\x68\xaa"                     # PLA / TAX
    b += bytes((0xBD, CPU_PTR_TABLE & 0xFF, CPU_PTR_TABLE >> 8))
    b += b"\x85\x1a"
    b += bytes((0xBD, (CPU_PTR_TABLE + len(SCRIPTS)) & 0xFF, (CPU_PTR_TABLE + len(SCRIPTS)) >> 8))
    b += b"\x85\x1b\x60"
    return bytes(b)


def _build_ptr_table() -> bytes:
    addrs = [_cpu(off) for off, _script, _text in SCRIPTS]
    return bytes(a & 0xFF for a in addrs) + bytes(a >> 8 for a in addrs)


def _build_key_gate() -> bytes:
    return (
        b"\xad\x2b\x07\xc9\xff\xf0\x05" +
        b"\xa2\x05" +
        bytes((0x20, *(_word(CPU_DRAW)))) +
        b"\x60"
    )


def _build_fairy_gate() -> bytes:
    return (
        b"\xad\x7e\x07\xc9\xff\xf0\x05" +
        b"\xa2\x06" +
        bytes((0x20, *(_word(CPU_DRAW)))) +
        b"\x60"
    )


def _build_warp_gate() -> bytes:
    return (
        b"\xad\x70\x07\x29\x20\xf0\x05" +
        b"\xa2\x07" +
        bytes((0x20, *(_word(CPU_DRAW)))) +
        b"\x60"
    )


MAIN = _build_main()
DRAW = _build_draw()
PTR_TABLE = _build_ptr_table()
KEY_GATE = _build_key_gate()
FAIRY_GATE = _build_fairy_gate()
WARP_GATE = _build_warp_gate()

RESERVED_SPANS = (
    (OFF_MAIN, len(MAIN)),
    (OFF_MASK_TABLE, len(ROOM_FLAG_MASKS)),
    (OFF_DRAW, len(DRAW)),
    (OFF_PTR_TABLE, len(PTR_TABLE)),
    (OFF_KEY_GATE, len(KEY_GATE)),
    (OFF_FAIRY_GATE, len(FAIRY_GATE)),
    (OFF_WARP_GATE, len(WARP_GATE)),
    *[(off, len(script)) for off, script, _text in SCRIPTS],
)

assert OFF_FREE_AFTER_STAGE_ANNOUNCEMENT == OFF_WARP_GATE + len(WARP_GATE) + sum(
    len(script) for _off, script, _text in SCRIPTS
)
assert FREE_AFTER_STAGE_ANNOUNCEMENT_LEN == 24


def _chr_start(rom_data: bytes) -> int:
    if len(rom_data) < 16 or bytes(rom_data[:4]) != b"NES\x1a":
        raise StageAnnouncementError("Not an iNES ROM.")
    return 16 + int(rom_data[4]) * 0x4000


def _write(rom_data: bytearray, off: int, blob: bytes, changed: list[str], name: str) -> None:
    if bytes(rom_data[off:off + len(blob)]) != blob:
        rom_data[off:off + len(blob)] = blob
        changed.append(name)


def _ensure_available(
    rom_data: bytes,
    off: int,
    blob: bytes,
    name: str,
    extra: tuple[bytes, ...] = (),
) -> None:
    cur = bytes(rom_data[off:off + len(blob)])
    if cur == blob or cur in extra or all(b in (0xEA, 0x00) for b in cur):
        return
    raise StageAnnouncementError(
        f"{name} overlap at file 0x{off:X}: expected empty EA/00 or existing code, "
        f"got {cur[:16].hex(' ')}..."
    )


def is_needed(levels: list, runtime_room_flags: list[int]) -> bool:
    for i, level in enumerate(levels):
        flags = runtime_room_flags[i] if i < len(runtime_room_flags) else 0
        if flags & (room_flags.BIT_DARK | room_flags.BIT_FIRE_RESET |
                    room_flags.BIT_HIDDEN_DOOR | room_flags.BIT_IN_BLOCK_DOOR |
                    room_flags.BIT_NO_BFIRE |
                    room_flags.BIT_NO_ASTONE):
            return True
        if stage_ext.key_enemy_enabled(level):
            return True
        if stage_ext.fairy_enemy_enabled(level):
            return True
        if stage_ext.warp_mirror_enabled(level):
            return True
    return False


def apply(rom_data: bytearray, levels: list, runtime_room_flags: list[int]) -> list[str]:
    changed: list[str] = []

    cur = bytes(rom_data[OFF_HOOK_START_UPDATE:OFF_HOOK_START_UPDATE + 3])
    if cur not in (ORIG_START_UPDATE, HOOK_START_UPDATE, OLD_HOOK_START_UPDATE):
        raise StageAnnouncementError(
            f"$9061 start-screen update hook mismatch: got {cur.hex(' ')}"
        )

    for off, blob, name in (
        (OFF_MAIN, MAIN, "stage announcement main"),
        (OFF_MASK_TABLE, ROOM_FLAG_MASKS, "stage announcement mask table"),
        (OFF_DRAW, DRAW, "stage announcement draw helper"),
        (OFF_PTR_TABLE, PTR_TABLE, "stage announcement pointer table"),
        (OFF_KEY_GATE, KEY_GATE, "stage announcement key gate"),
        (OFF_FAIRY_GATE, FAIRY_GATE, "stage announcement fairy gate"),
        (OFF_WARP_GATE, WARP_GATE, "stage announcement warp gate"),
        *[(off, script, f"stage announcement script {text}") for off, script, text in SCRIPTS],
    ):
        _ensure_available(rom_data, off, blob, name)

    _write(rom_data, OFF_MAIN, MAIN, changed, "stage announcement main")
    _write(rom_data, OFF_MASK_TABLE, ROOM_FLAG_MASKS, changed, "stage announcement mask table")
    _write(rom_data, OFF_DRAW, DRAW, changed, "stage announcement draw helper")
    _write(rom_data, OFF_PTR_TABLE, PTR_TABLE, changed, "stage announcement pointer table")
    _write(rom_data, OFF_KEY_GATE, KEY_GATE, changed, "stage announcement key gate")
    _write(rom_data, OFF_FAIRY_GATE, FAIRY_GATE, changed, "stage announcement fairy gate")
    _write(rom_data, OFF_WARP_GATE, WARP_GATE, changed, "stage announcement warp gate")
    for off, script, text in SCRIPTS:
        _write(rom_data, off, script, changed, f"stage announcement script {text}")

    chr_base = _chr_start(rom_data)
    for bank in range(3):
        base = chr_base + bank * 0x2000
        _write(rom_data, base + CUSTOM_K_CHR * 16, K_TILE_BYTES, changed, f"CHR bank{bank} K tile")
        _write(rom_data, base + CUSTOM_P_CHR * 16, P_TILE_BYTES, changed, f"CHR bank{bank} P tile")

    _write(rom_data, OFF_HOOK_START_UPDATE, HOOK_START_UPDATE, changed, "$9061 stage announcement hook")
    return changed

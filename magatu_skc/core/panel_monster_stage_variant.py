"""Panel Monster stage-variant prototype patch.

This module is intentionally separate from ``panel_monster_variant.py``.
The existing module owns the production 2-way/3-way borrowed-ID Panel Monster
feature.  This module is for the newer stage-parameterized A/B/C families:

  C: $31/$33/$35/$37
  A: $41/$43/$45/$47
  B: $49/$4B/$4D/$4F

Current scope:
  - hook the state0 firing interval compare at $A575/$A579;
  - keep the state1 pre-shot mouth delay at the stock $10;
  - read the current room's C/A/B interval bytes from the $0740-$074F cache.

This is not the final PRG1 PanelVariantStageTable implementation yet.  Keep it
out of UI wiring until the RAM interval behavior is proven clean in ROM tests.
"""

from __future__ import annotations


class PanelMonsterStageVariantError(ValueError):
    pass


PANEL_STAGE_VARIANT_IDS = frozenset((
    0x31, 0x33, 0x35, 0x37,
    0x41, 0x43, 0x45, 0x47,
    0x49, 0x4B, 0x4D, 0x4F,
))

GROUP_C_IDS = frozenset((0x31, 0x33, 0x35, 0x37))
GROUP_A_IDS = frozenset((0x41, 0x43, 0x45, 0x47))
GROUP_B_IDS = frozenset((0x49, 0x4B, 0x4D, 0x4F))

RAM_PV_C_INTERVAL = 0x0740
RAM_PV_A_INTERVAL = 0x0741
RAM_PV_B_INTERVAL = 0x0742

DEFAULT_C_INTERVAL = 0x90
DEFAULT_A_INTERVAL = 0x80
DEFAULT_B_INTERVAL = 0x70

ROOM_COUNT = 64
ENTRY_SIZE = 16
HEADER_SIZE = 16
TABLE_OFFSET = 0x8A70
TABLE_LENGTH = HEADER_SIZE + ROOM_COUNT * ENTRY_SIZE
TABLE_END = TABLE_OFFSET + TABLE_LENGTH
MAGIC = b"PANELVAR"
FORMAT = 1
ENABLE_STAGE_TABLE_INTERVAL_PROTOTYPE = False

CPU_PRG1_RUNTIME_LOADER = 0x8A00
OFF_PRG1_RUNTIME_LOADER = 0x8A10
OFF_M66_LOADER_TAIL = 0x80C4
ORIG_M66_LOADER_TAIL = bytes.fromhex("60 00 00")
HOOK_M66_LOADER_TAIL = bytes((
    0x4C,
    CPU_PRG1_RUNTIME_LOADER & 0xFF,
    CPU_PRG1_RUNTIME_LOADER >> 8,
))

# These offsets are the current v7/v4 test-ROM cave locations.  They are
# deliberately named as prototype locations, not final production reservations.
OFF_AI_WRAPPER_C_PROTO = 0x3C6B
OFF_AI_WRAPPER_AB_PROTO = 0x3D0F
OFF_STATE0_INTERVAL_HOOK = 0x2585  # CPU $A575
OFF_STATE0_INTERVAL_CMP = 0x2589   # CPU $A579
OFF_STATE0_INTERVAL_HELPER = 0x4098  # CPU $C088
OFF_STATE1_MOUTH_GATE = 0x3D52  # CPU $BD42
STATE1_MOUTH_GATE_SIZE = 0x3F

ORIG_STATE0_INTERVAL_HOOK = bytes.fromhex("a0 02 b1 2c c9 c0")
V7_STATE0_INTERVAL_HOOK = bytes.fromhex("4c 80 c1 2c c9 c0")
V8_STATE0_INTERVAL_HOOK = bytes.fromhex("20 88 c0 ea c5 0f")
HOOK_STATE0_INTERVAL = bytes.fromhex("20 88 c0 ea ea ea")

V7_AI_WRAPPER_C_HEAD = bytes.fromhex(
    "a9 00 a0 05 91 2e a0 06 91 2e a0 08 91 2e a0 09 "
    "91 2e a0 01 b1 2e 4a 29 01 09 02 48 a0 03 b1 2e "
    "29 fc 91 2e 68 11 2e 91 2e 4c 4c a5"
)

FIXED_AI_WRAPPER_C = bytes.fromhex(
    "a9 00 a0 05 91 2e a0 06 91 2e a0 08 91 2e a0 09 "
    "91 2e a0 01 b1 2e 29 06 4a a8 b9 9d bc 48 a0 03 "
    "b1 2e 29 fc 91 2e 68 11 2e 91 2e 4c 4c a5 "
    "02 03 00 01"
)

V7_AI_WRAPPER_AB_HEAD = bytes.fromhex(
    "a9 00 a0 05 91 2e a0 06 91 2e a0 08 91 2e a0 09 "
    "91 2e a0 01 b1 2e 4a 29 01 48 a0 03 b1 2e 29 fc "
    "91 2e 68 11 2e 91 2e 4c 4c a5 2e c9 6e f0 07 "
    "c9 6f f0 06 4c 4a a6 4c 2d a9 4c 2d a9"
)

DEFAULT_ENTRY = bytes((
    DEFAULT_C_INTERVAL,
    DEFAULT_A_INTERVAL,
    DEFAULT_B_INTERVAL,
    0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00,
))

STATE0_INTERVAL_HELPER = bytes.fromhex(
    "a0 01"      # LDY #1
    "b1 2e"      # LDA ($2E),Y parent type
    "29 f8"      # AND #$F8
    "aa"         # TAX group base
    "a0 02"      # LDY #2
    "b1 2c"      # LDA ($2C),Y
    "e0 30"      # CPX #$30
    "d0 04"      # BNE not C
    "cd 40 07"   # CMP $0740
    "60"         # RTS
    "e0 40"      # CPX #$40
    "d0 04"      # BNE not A
    "cd 41 07"   # CMP $0741
    "60"         # RTS
    "e0 48"      # CPX #$48
    "d0 04"      # BNE not B
    "cd 42 07"   # CMP $0742
    "60"         # RTS
    "c9 c0"      # CMP #$C0 fallback
    "60"         # RTS
)
STATE1_MOUTH_GATE = (
    bytes.fromhex("a0 01 b1 2c c9 10 90 03 4c 9a bd 60")
    + bytes([0xEA] * (STATE1_MOUTH_GATE_SIZE - 12))
)

RESERVED_SPANS = (
    (OFF_AI_WRAPPER_C_PROTO, STATE1_MOUTH_GATE_SIZE),
    (OFF_PRG1_RUNTIME_LOADER, 0x60),
    (TABLE_OFFSET, TABLE_LENGTH),
    (OFF_STATE0_INTERVAL_HELPER, len(STATE0_INTERVAL_HELPER)),
    (OFF_STATE1_MOUTH_GATE, STATE1_MOUTH_GATE_SIZE),
)


def is_panel_stage_variant_id(enemy_id: int) -> bool:
    return (int(enemy_id) & 0xFF) in PANEL_STAGE_VARIANT_IDS


def has_panel_stage_variant_ids(levels: list) -> bool:
    """Return True if any level currently uses an A/B/C stage-variant ID."""
    for lv in levels or []:
        for enemy in getattr(lv, "enemies", []) or []:
            if is_panel_stage_variant_id(getattr(enemy, "element_no", -1)):
                return True
        for mirror in getattr(lv, "demon_mirrors", []) or []:
            for code in getattr(mirror, "enemy_codes", []) or []:
                if is_panel_stage_variant_id(code):
                    return True
    return False


def _blank_entry() -> bytes:
    return DEFAULT_ENTRY


def build_table(levels: list = None) -> bytes:
    """Build the prototype PRG1 PanelVariantStageTable.

    Entry bytes 0..2 are the current interval-only prototype cache:
    C interval, A interval, B interval.  The final speed/interval/rhythm layout
    should replace this once speed and rhythm are ready for integration.
    """
    table = bytearray([0x00] * TABLE_LENGTH)
    table[:len(MAGIC)] = MAGIC
    table[len(MAGIC)] = FORMAT
    table[len(MAGIC) + 1] = ENTRY_SIZE
    table[len(MAGIC) + 2] = ROOM_COUNT
    table[len(MAGIC) + 3] = 0
    for i in range(ROOM_COUNT):
        base = HEADER_SIZE + i * ENTRY_SIZE
        table[base:base + ENTRY_SIZE] = _blank_entry()
    return bytes(table)


def patch_table(rom_data: bytearray, levels: list = None) -> bool:
    if len(rom_data) < TABLE_END:
        return False
    table = build_table(levels)
    if bytes(rom_data[TABLE_OFFSET:TABLE_END]) == table:
        return False
    rom_data[TABLE_OFFSET:TABLE_END] = table
    return True


def read_table(rom_data: bytes) -> list[bytes]:
    if len(rom_data) < TABLE_END:
        return []
    raw = bytes(rom_data[TABLE_OFFSET:TABLE_END])
    if not raw.startswith(MAGIC):
        return []
    if raw[len(MAGIC)] != FORMAT or raw[len(MAGIC) + 1] != ENTRY_SIZE:
        return []
    return [
        raw[HEADER_SIZE + i * ENTRY_SIZE:HEADER_SIZE + (i + 1) * ENTRY_SIZE]
        for i in range(ROOM_COUNT)
    ]


def _build_runtime_loader() -> bytes:
    # This supersedes stage_ext.RUNTIME_LOADER while preserving its side effects.
    # StageExt pointer starts at entry byte2: bank1 CPU $8802 + room*8.
    # PanelVariant pointer starts at entry byte0: bank1 CPU $8A70 + room*16.
    return bytes.fromhex(
        "a9 ff 8d 2a 07 8d 2b 07"
        "a9 00 8d 23 07 8d 24 07 8d 29 07"
        "ad 28 04 0a 0a 0a 18 69 02 85 00"
        "a9 88 69 00 85 01"
        "a0 00 b1 00 8d 2b 07"
        "a0 04 b1 00 8d 78 07"
        "a0 05 b1 00 8d 7c 07"
        "ad 28 04 0a 0a 0a 0a 18 69 70 85 00"
        "a9 8a 69 00 85 01"
        "a0 0f b1 00 99 40 07 88 10 f8"
        "60"
    )


RUNTIME_LOADER = _build_runtime_loader()
assert len(RUNTIME_LOADER) <= 0x60


def apply_runtime_loader(rom_data: bytearray) -> list[str]:
    if len(rom_data) < OFF_PRG1_RUNTIME_LOADER + len(RUNTIME_LOADER):
        return []
    cur = bytes(rom_data[OFF_M66_LOADER_TAIL:OFF_M66_LOADER_TAIL + len(ORIG_M66_LOADER_TAIL)])
    if cur not in (ORIG_M66_LOADER_TAIL, HOOK_M66_LOADER_TAIL):
        return []
    changed: list[str] = []
    if bytes(rom_data[OFF_PRG1_RUNTIME_LOADER:OFF_PRG1_RUNTIME_LOADER + len(RUNTIME_LOADER)]) != RUNTIME_LOADER:
        rom_data[OFF_PRG1_RUNTIME_LOADER:OFF_PRG1_RUNTIME_LOADER + len(RUNTIME_LOADER)] = RUNTIME_LOADER
        changed.append("Panel stage-variant combined PRG1 runtime loader")
    if cur != HOOK_M66_LOADER_TAIL:
        rom_data[OFF_M66_LOADER_TAIL:OFF_M66_LOADER_TAIL + len(HOOK_M66_LOADER_TAIL)] = HOOK_M66_LOADER_TAIL
        changed.append("mapper66 loader Panel stage-variant hook")
    return changed


def _write_blob(rom_data, off: int, blob: bytes, changed: list[str], name: str) -> None:
    if bytes(rom_data[off:off + len(blob)]) != blob:
        rom_data[off:off + len(blob)] = blob
        changed.append(name)


def apply_stage_table_interval_prototype(rom_data, levels: list = None) -> list[str]:
    """Apply the table-loaded interval prototype.

    The room-load-time PRG1 loader fills $0740-$074F from
    PanelVariantStageTable.  The PRG0 hook changes only the state0 firing
    interval compare at $A575/$A579; the state1 mouth delay remains stock.
    """
    if rom_data is None or len(rom_data) < max(TABLE_END, OFF_STATE0_INTERVAL_HELPER + len(STATE0_INTERVAL_HELPER)):
        raise PanelMonsterStageVariantError("ROM is too short for PanelVariantStageTable.")
    cur_hook = bytes(rom_data[OFF_STATE0_INTERVAL_HOOK:OFF_STATE0_INTERVAL_HOOK + len(ORIG_STATE0_INTERVAL_HOOK)])
    if cur_hook not in (
        ORIG_STATE0_INTERVAL_HOOK,
        V7_STATE0_INTERVAL_HOOK,
        V8_STATE0_INTERVAL_HOOK,
        HOOK_STATE0_INTERVAL,
    ):
        raise PanelMonsterStageVariantError(
            f"$A575 state0 interval hook signature mismatch: got {cur_hook.hex(' ')}"
        )

    changed: list[str] = []
    _write_blob(
        rom_data,
        OFF_AI_WRAPPER_C_PROTO,
        FIXED_AI_WRAPPER_C + bytes([0xEA] * (STATE1_MOUTH_GATE_SIZE - len(FIXED_AI_WRAPPER_C))),
        changed,
        "Panel stage-variant C direction table wrapper",
    )
    if patch_table(rom_data, levels):
        changed.append("PanelVariantStageTable")
    changed.extend(apply_runtime_loader(rom_data))
    _write_blob(
        rom_data,
        OFF_STATE0_INTERVAL_HELPER,
        STATE0_INTERVAL_HELPER,
        changed,
        "Panel stage-variant state0 interval helper reads $0740-$0742",
    )
    _write_blob(
        rom_data,
        OFF_STATE1_MOUTH_GATE,
        STATE1_MOUTH_GATE,
        changed,
        "Panel stage-variant state1 mouth gate restored to $10",
    )
    _write_blob(
        rom_data,
        OFF_STATE0_INTERVAL_HOOK,
        HOOK_STATE0_INTERVAL,
        changed,
        "$A575 Panel stage-variant interval helper hook",
    )
    return changed


def can_apply_stage_table_interval_prototype(rom_data) -> bool:
    """Return True when the ROM already contains the ABC prototype wrappers."""
    if not ENABLE_STAGE_TABLE_INTERVAL_PROTOTYPE:
        return False
    if rom_data is None:
        return False
    cur_c = bytes(rom_data[OFF_AI_WRAPPER_C_PROTO:OFF_AI_WRAPPER_C_PROTO + len(FIXED_AI_WRAPPER_C)])
    cur_c_old = bytes(rom_data[OFF_AI_WRAPPER_C_PROTO:OFF_AI_WRAPPER_C_PROTO + len(V7_AI_WRAPPER_C_HEAD)])
    return (
        cur_c == FIXED_AI_WRAPPER_C
        or cur_c_old == V7_AI_WRAPPER_C_HEAD
    ) and (
        bytes(rom_data[OFF_AI_WRAPPER_AB_PROTO:OFF_AI_WRAPPER_AB_PROTO + len(V7_AI_WRAPPER_AB_HEAD)])
        == V7_AI_WRAPPER_AB_HEAD
    )


apply = apply_stage_table_interval_prototype

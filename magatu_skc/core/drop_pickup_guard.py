"""Pickup drop landing guard for the original item AI.

The original $14-$17 item/drop AI only accepts floor contact when the Y low
nibble is below 8.  In crowded custom stages, the AI can miss several collision
checks and first see the floor at phase 8-F, so it keeps falling through the
floor.  This patch keeps the original bottom-collision requirement and only
removes that late-phase rejection.

It also guards the shared physics Y-high update before a drop can visibly sink
through the bottom or write a down-to-top wrap.  The hook runs in PRG0 only and
clamps $14-$17 pickups at the bottom instead of allowing Y=$FE->$00.
"""
from __future__ import annotations


class DropPickupGuardError(ValueError):
    pass


def _cf(cpu_addr: int) -> int:
    return 0x10 + (cpu_addr - 0x8000)


CPU_SIG = 0xA3F6
OFF_SIG = _cf(CPU_SIG)
OFF_PHASE_LIMIT = _cf(0xA3FD)
CPU_Y_HIGH_HOOK = 0x86B1
OFF_Y_HIGH_HOOK = _cf(CPU_Y_HIGH_HOOK)

CPU_WRAP_TYPE_CHECK = 0xE0C1
CPU_WRAP_PICKUP_CLAMP_Y = 0xE0F9
CPU_WRAP_NONPICKUP_STORE = 0xE129
CPU_WRAP_PICKUP_ZERO_YVEL = 0xE18B
CPU_WRAP_ENTRY = 0xE1EA
CPU_WRAP_NORMAL_STORE = 0xE20C
CPU_WRAP_BOTTOM_CHECK = 0xE217

OFF_WRAP_TYPE_CHECK = _cf(CPU_WRAP_TYPE_CHECK)
OFF_WRAP_PICKUP_CLAMP_Y = _cf(CPU_WRAP_PICKUP_CLAMP_Y)
OFF_WRAP_NONPICKUP_STORE = _cf(CPU_WRAP_NONPICKUP_STORE)
OFF_WRAP_PICKUP_ZERO_YVEL = _cf(CPU_WRAP_PICKUP_ZERO_YVEL)
OFF_WRAP_ENTRY = _cf(CPU_WRAP_ENTRY)
OFF_WRAP_NORMAL_STORE = _cf(CPU_WRAP_NORMAL_STORE)
OFF_WRAP_BOTTOM_CHECK = _cf(CPU_WRAP_BOTTOM_CHECK)

SIG_PREFIX = bytes.fromhex("a0 07 b1 2e 29 0f c9")
SIG_SUFFIX = bytes.fromhex("b0 c9 c8 a9 00 91 2e a0 05 91 2e 60")
ORIG_PHASE_LIMIT = 0x08
PATCH_PHASE_LIMIT = 0x10
BOTTOM_GUARD_Y = 0xD8
BOTTOM_CLAMP_Y = 0xD0

ORIG_Y_HIGH_HOOK = bytes.fromhex("c8 a5 0a 71 08 91 08 c8 b1 08")
HOOK_Y_HIGH = bytes((0x4C, CPU_WRAP_ENTRY & 0xFF, CPU_WRAP_ENTRY >> 8))

WRAP_ENTRY = bytes((
    0xC8,                         # INY                 ; original Y high byte
    0xA5, 0x0A,                   # LDA $0A
    0x71, 0x08,                   # ADC ($08),Y
    0x90, (CPU_WRAP_BOTTOM_CHECK - (CPU_WRAP_ENTRY + 7)) & 0xFF,
    0x4C, CPU_WRAP_TYPE_CHECK & 0xFF, CPU_WRAP_TYPE_CHECK >> 8,
))

LEGACY_WRAP_ENTRY_WRAP_ONLY = bytes((
    0xC8,                         # INY                 ; original Y high byte
    0xA5, 0x0A,                   # LDA $0A
    0x71, 0x08,                   # ADC ($08),Y
    0x90, (CPU_WRAP_NORMAL_STORE - (CPU_WRAP_ENTRY + 7)) & 0xFF,
    0x4C, CPU_WRAP_TYPE_CHECK & 0xFF, CPU_WRAP_TYPE_CHECK >> 8,
))

WRAP_BOTTOM_CHECK = bytes((
    0xC9, BOTTOM_GUARD_Y,          # CMP #bottom danger Y
    0x90, (CPU_WRAP_NORMAL_STORE - (CPU_WRAP_BOTTOM_CHECK + 4)) & 0xFF,
    0x4C, CPU_WRAP_TYPE_CHECK & 0xFF, CPU_WRAP_TYPE_CHECK >> 8,
))

WRAP_NORMAL_STORE = bytes((
    0x91, 0x08,                   # STA ($08),Y
    0x4C, 0xB8, 0x86,             # JMP $86B8
))

WRAP_TYPE_CHECK = bytes((
    0x48,                         # PHA                 ; save computed Y
    0xA0, 0x01,                   # LDY #$01
    0xB1, 0x08,                   # LDA ($08),Y         ; entity type
    0xE9, 0x14,                   # SBC #$14            ; C=1 from guard path
    0xC9, 0x04,                   # CMP #$04            ; $14-$17 only
    0x90, (CPU_WRAP_PICKUP_CLAMP_Y - (CPU_WRAP_TYPE_CHECK + 11)) & 0xFF,
    0xB0, (CPU_WRAP_NONPICKUP_STORE - (CPU_WRAP_TYPE_CHECK + 13)) & 0xFF,
))

WRAP_PICKUP_CLAMP_Y = bytes((
    0x68,                         # PLA                 ; discard unsafe Y
    0xA0, 0x07,                   # LDY #$07
    0xA9, BOTTOM_CLAMP_Y,          # LDA #bottom clamp Y
    0x91, 0x08,                   # STA ($08),Y
    0x4C, CPU_WRAP_PICKUP_ZERO_YVEL & 0xFF, CPU_WRAP_PICKUP_ZERO_YVEL >> 8,
))

WRAP_PICKUP_ZERO_YVEL = bytes((
    0xA0, 0x05,                   # LDY #$05
    0xA9, 0x00,                   # LDA #$00
    0x91, 0x08,                   # STA ($08),Y
    0x4C, 0xD4, 0x86,             # JMP $86D4
))

LEGACY_WRAP_PICKUP_ZERO_YVEL_X_UPDATE = bytes((
    0xA0, 0x05,                   # LDY #$05
    0xA9, 0x00,                   # LDA #$00
    0x91, 0x08,                   # STA ($08),Y
    0x4C, 0xB8, 0x86,             # JMP $86B8
))

WRAP_NONPICKUP_STORE = bytes((
    0x68,                         # PLA                 ; restore computed Y
    0xA0, 0x07,                   # LDY #$07
    0x91, 0x08,                   # STA ($08),Y
    0x4C, 0xB8, 0x86,             # JMP $86B8
))

RESERVED_SPANS = (
    (OFF_WRAP_TYPE_CHECK, len(WRAP_TYPE_CHECK)),
    (OFF_WRAP_PICKUP_CLAMP_Y, len(WRAP_PICKUP_CLAMP_Y)),
    (OFF_WRAP_NONPICKUP_STORE, len(WRAP_NONPICKUP_STORE)),
    (OFF_WRAP_PICKUP_ZERO_YVEL, len(WRAP_PICKUP_ZERO_YVEL)),
    (OFF_WRAP_ENTRY, len(WRAP_ENTRY)),
    (OFF_WRAP_NORMAL_STORE, len(WRAP_NORMAL_STORE)),
    (OFF_WRAP_BOTTOM_CHECK, len(WRAP_BOTTOM_CHECK)),
)

LEGACY_BLOBS_BY_OFF = {
    OFF_WRAP_ENTRY: (LEGACY_WRAP_ENTRY_WRAP_ONLY,),
    OFF_WRAP_PICKUP_ZERO_YVEL: (LEGACY_WRAP_PICKUP_ZERO_YVEL_X_UPDATE,),
}


def _verify(rom_data: bytes) -> None:
    end = OFF_SIG + len(SIG_PREFIX) + 1 + len(SIG_SUFFIX)
    min_len = max(
        end,
        OFF_Y_HIGH_HOOK + len(ORIG_Y_HIGH_HOOK),
        *(off + size for off, size in RESERVED_SPANS),
    )
    if len(rom_data) < min_len:
        raise DropPickupGuardError(
            f"ROM is too small for pickup landing guard (len={len(rom_data)})."
        )
    if bytes(rom_data[OFF_SIG:OFF_SIG + len(SIG_PREFIX)]) != SIG_PREFIX:
        raise DropPickupGuardError(
            "$A3F6 pickup AI signature mismatch; aborting pickup landing guard."
        )
    phase_limit = rom_data[OFF_PHASE_LIMIT]
    if phase_limit not in (ORIG_PHASE_LIMIT, PATCH_PHASE_LIMIT):
        raise DropPickupGuardError(
            f"$A3FD phase limit mismatch: ${phase_limit:02X}."
        )
    suffix_off = OFF_PHASE_LIMIT + 1
    if bytes(rom_data[suffix_off:suffix_off + len(SIG_SUFFIX)]) != SIG_SUFFIX:
        raise DropPickupGuardError(
            "$A3FE pickup AI suffix mismatch; aborting pickup landing guard."
        )

    hook = bytes(rom_data[OFF_Y_HIGH_HOOK:OFF_Y_HIGH_HOOK + len(HOOK_Y_HIGH)])
    hook_window = bytes(rom_data[OFF_Y_HIGH_HOOK:OFF_Y_HIGH_HOOK + len(ORIG_Y_HIGH_HOOK)])
    if hook != HOOK_Y_HIGH and hook_window != ORIG_Y_HIGH_HOOK:
        raise DropPickupGuardError(
            "$86B1 physics Y-high hook signature mismatch; aborting pickup wrap guard."
        )


def _ensure_available(rom_data: bytes, off: int, blob: bytes, name: str) -> None:
    cur = bytes(rom_data[off:off + len(blob)])
    if (
        cur == blob
        or cur in LEGACY_BLOBS_BY_OFF.get(off, ())
        or all(b in (0x00, 0xEA) for b in cur)
    ):
        return
    raise DropPickupGuardError(
        f"{name} overlap at file 0x{off:X}: got {cur.hex(' ')}."
    )


def is_applied(rom_data: bytes) -> bool:
    _verify(rom_data)
    return (
        rom_data[OFF_PHASE_LIMIT] == PATCH_PHASE_LIMIT
        and bytes(rom_data[OFF_Y_HIGH_HOOK:OFF_Y_HIGH_HOOK + len(HOOK_Y_HIGH)]) == HOOK_Y_HIGH
        and bytes(rom_data[OFF_WRAP_ENTRY:OFF_WRAP_ENTRY + len(WRAP_ENTRY)]) == WRAP_ENTRY
        and bytes(rom_data[OFF_WRAP_NORMAL_STORE:OFF_WRAP_NORMAL_STORE + len(WRAP_NORMAL_STORE)]) == WRAP_NORMAL_STORE
        and bytes(rom_data[OFF_WRAP_BOTTOM_CHECK:OFF_WRAP_BOTTOM_CHECK + len(WRAP_BOTTOM_CHECK)]) == WRAP_BOTTOM_CHECK
        and bytes(rom_data[OFF_WRAP_TYPE_CHECK:OFF_WRAP_TYPE_CHECK + len(WRAP_TYPE_CHECK)]) == WRAP_TYPE_CHECK
        and bytes(rom_data[OFF_WRAP_PICKUP_CLAMP_Y:OFF_WRAP_PICKUP_CLAMP_Y + len(WRAP_PICKUP_CLAMP_Y)]) == WRAP_PICKUP_CLAMP_Y
        and bytes(rom_data[OFF_WRAP_PICKUP_ZERO_YVEL:OFF_WRAP_PICKUP_ZERO_YVEL + len(WRAP_PICKUP_ZERO_YVEL)]) == WRAP_PICKUP_ZERO_YVEL
        and bytes(rom_data[OFF_WRAP_NONPICKUP_STORE:OFF_WRAP_NONPICKUP_STORE + len(WRAP_NONPICKUP_STORE)]) == WRAP_NONPICKUP_STORE
    )


def apply(rom_data: bytearray) -> list[str]:
    _verify(rom_data)
    for off, blob, name in (
        (OFF_WRAP_ENTRY, WRAP_ENTRY, "pickup wrap guard entry"),
        (OFF_WRAP_NORMAL_STORE, WRAP_NORMAL_STORE, "pickup wrap guard normal store"),
        (OFF_WRAP_BOTTOM_CHECK, WRAP_BOTTOM_CHECK, "pickup bottom danger guard"),
        (OFF_WRAP_TYPE_CHECK, WRAP_TYPE_CHECK, "pickup wrap guard type check"),
        (OFF_WRAP_PICKUP_CLAMP_Y, WRAP_PICKUP_CLAMP_Y, "pickup wrap guard clamp"),
        (OFF_WRAP_PICKUP_ZERO_YVEL, WRAP_PICKUP_ZERO_YVEL, "pickup wrap guard velocity clear"),
        (OFF_WRAP_NONPICKUP_STORE, WRAP_NONPICKUP_STORE, "pickup wrap guard non-pickup store"),
    ):
        _ensure_available(rom_data, off, blob, name)

    changed: list[str] = []
    if rom_data[OFF_PHASE_LIMIT] == PATCH_PHASE_LIMIT:
        pass
    else:
        rom_data[OFF_PHASE_LIMIT] = PATCH_PHASE_LIMIT
        changed.append("pickup drop late-floor guard")

    for off, blob, name in (
        (OFF_WRAP_ENTRY, WRAP_ENTRY, "pickup wrap guard entry"),
        (OFF_WRAP_NORMAL_STORE, WRAP_NORMAL_STORE, "pickup wrap guard normal store"),
        (OFF_WRAP_BOTTOM_CHECK, WRAP_BOTTOM_CHECK, "pickup bottom danger guard"),
        (OFF_WRAP_TYPE_CHECK, WRAP_TYPE_CHECK, "pickup wrap guard type check"),
        (OFF_WRAP_PICKUP_CLAMP_Y, WRAP_PICKUP_CLAMP_Y, "pickup wrap guard clamp"),
        (OFF_WRAP_PICKUP_ZERO_YVEL, WRAP_PICKUP_ZERO_YVEL, "pickup wrap guard velocity clear"),
        (OFF_WRAP_NONPICKUP_STORE, WRAP_NONPICKUP_STORE, "pickup wrap guard non-pickup store"),
    ):
        if bytes(rom_data[off:off + len(blob)]) != blob:
            rom_data[off:off + len(blob)] = blob
            changed.append(name)

    if bytes(rom_data[OFF_Y_HIGH_HOOK:OFF_Y_HIGH_HOOK + len(HOOK_Y_HIGH)]) != HOOK_Y_HIGH:
        rom_data[OFF_Y_HIGH_HOOK:OFF_Y_HIGH_HOOK + len(HOOK_Y_HIGH)] = HOOK_Y_HIGH
        changed.append("pickup wrap guard physics hook")

    return changed

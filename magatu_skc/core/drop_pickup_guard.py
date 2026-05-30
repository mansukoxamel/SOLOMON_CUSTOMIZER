"""Pickup drop landing guard for the original item AI.

The original $14-$17 item/drop AI only accepts floor contact when the Y low
nibble is below 8.  In crowded custom stages, the AI can miss several collision
checks and first see the floor at phase 8-F, so it keeps falling through the
floor.  This patch keeps the original bottom-collision requirement and only
removes that late-phase rejection.
"""
from __future__ import annotations


class DropPickupGuardError(ValueError):
    pass


def _cf(cpu_addr: int) -> int:
    return 0x10 + (cpu_addr - 0x8000)


CPU_SIG = 0xA3F6
OFF_SIG = _cf(CPU_SIG)
OFF_PHASE_LIMIT = _cf(0xA3FD)

SIG_PREFIX = bytes.fromhex("a0 07 b1 2e 29 0f c9")
SIG_SUFFIX = bytes.fromhex("b0 c9 c8 a9 00 91 2e a0 05 91 2e 60")
ORIG_PHASE_LIMIT = 0x08
PATCH_PHASE_LIMIT = 0x10


def _verify(rom_data: bytes) -> None:
    end = OFF_SIG + len(SIG_PREFIX) + 1 + len(SIG_SUFFIX)
    if len(rom_data) < end:
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


def is_applied(rom_data: bytes) -> bool:
    _verify(rom_data)
    return rom_data[OFF_PHASE_LIMIT] == PATCH_PHASE_LIMIT


def apply(rom_data: bytearray) -> list[str]:
    _verify(rom_data)
    if rom_data[OFF_PHASE_LIMIT] == PATCH_PHASE_LIMIT:
        return []
    rom_data[OFF_PHASE_LIMIT] = PATCH_PHASE_LIMIT
    return ["pickup drop late-floor guard"]

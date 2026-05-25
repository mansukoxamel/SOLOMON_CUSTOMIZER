"""Warp-feather stage advance tweak.

Verified JP/JPN66 location:
  $C69E: CLC
  $C69F: LDA #$05
  $C6A1: ADC $0428
  $C6A4: STA $0428

The normal clear path later increments $0428 once, so the player-visible
advance count is operand + 1.  The original operand $05 therefore means
"advance 6 stages".  A zero-stage advance is encoded as operand $FF:
$FF + the normal +1 wraps back to the same room.
"""

ORIGINAL_STEPS = 6
MIN_STEPS = 0
MAX_STEPS = 53

SIG_OFF = 0x46AE
OPERAND_OFF = 0x46B0
_SIG_PREFIX = bytes.fromhex("18 A9")
_SIG_SUFFIX = bytes.fromhex("6D 28 04 8D 28 04")


class WarpFeatherError(ValueError):
    pass


def _verify(rom_data) -> None:
    if OPERAND_OFF + 1 > len(rom_data):
        raise WarpFeatherError("ROM is too small for the warp-feather patch.")
    if bytes(rom_data[SIG_OFF:SIG_OFF + len(_SIG_PREFIX)]) != _SIG_PREFIX:
        raise WarpFeatherError(
            "warp-feather code signature not found at file 0x46AE.")
    suffix_off = OPERAND_OFF + 1
    if bytes(rom_data[suffix_off:suffix_off + len(_SIG_SUFFIX)]) != _SIG_SUFFIX:
        raise WarpFeatherError(
            "warp-feather code signature not found after the operand.")


def is_supported(rom_data) -> bool:
    try:
        _verify(rom_data)
        return True
    except WarpFeatherError:
        return False


def current_steps(rom_data) -> int:
    _verify(rom_data)
    operand = int(rom_data[OPERAND_OFF])
    if operand == 0xFF:
        return 0
    return operand + 1


def apply(rom_data, steps: int) -> list:
    _verify(rom_data)
    steps = int(steps)
    if not (MIN_STEPS <= steps <= MAX_STEPS):
        raise WarpFeatherError(
            f"warp-feather advance must be {MIN_STEPS}-{MAX_STEPS} stages.")
    operand = 0xFF if steps == 0 else (steps - 1) & 0xFF
    if rom_data[OPERAND_OFF] != operand:
        rom_data[OPERAND_OFF] = operand
        return [f"ワープ羽の進行数 → {steps}面分 (operand ${operand:02X})"]
    return []


def restore(rom_data) -> list:
    return apply(rom_data, ORIGINAL_STEPS)

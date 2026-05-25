"""Initial Dana lives patch.

JP/JP66 only.  The original new-game setup is:

  $913F: LDX #$03
  $9141: STX $0452  ; Dana lives
  $9144: STX $042B  ; original fire-scroll max/cursor setup

Changing only the immediate at $9140 would also change $042B.  This patch
therefore replaces the first five bytes with JSR $8BF4 + NOP/NOP and writes a
small routine in the verified NOP band immediately after initial_magic's
routine.  The routine sets only $0452, restores A, and returns with X=$03 so
the following original code keeps the same contract.
"""

from __future__ import annotations


class InitialLivesError(RuntimeError):
    pass


ORIGINAL_LIVES = 3
MIN_LIVES = 1
MAX_LIVES = 99

OFF_HOOK = 0x114F          # CPU $913F: LDX #$03 / STX $0452
OFF_SUB = 0x0C04           # CPU $8BF4, after initial_magic $8BE2-$8C03

ORIGINAL_HOOK = bytes.fromhex("A2 03 8E 52 04")
HOOK = bytes.fromhex("20 F4 8B EA EA")

ROUTINE_LEN = 10
ORIGINAL_SUB = bytes([0xEA] * ROUTINE_LEN)


def _routine(lives: int) -> bytes:
    return bytes([
        0x48,                    # PHA
        0xA9, lives & 0xFF,      # LDA #lives
        0x8D, 0x52, 0x04,        # STA $0452
        0x68,                    # PLA
        0xA2, 0x03,              # LDX #$03 (preserve original contract)
        0x60,                    # RTS
    ])


def _check_bounds(data: bytes) -> None:
    need = max(OFF_HOOK + len(ORIGINAL_HOOK), OFF_SUB + ROUTINE_LEN)
    if len(data) < need:
        raise InitialLivesError("ROM is too small for the initial-lives patch.")


def _read_lives_from_sub(sub: bytes) -> int:
    if not (len(sub) == ROUTINE_LEN and sub[0] == 0x48
            and sub[1] == 0xA9 and sub[3:7] == b"\x8D\x52\x04\x68"
            and sub[7:10] == b"\xA2\x03\x60"):
        raise InitialLivesError("initial-lives routine signature mismatch.")
    return int(sub[2])


def current(data: bytes) -> int:
    _check_bounds(data)
    hook = bytes(data[OFF_HOOK:OFF_HOOK + len(ORIGINAL_HOOK)])
    sub = bytes(data[OFF_SUB:OFF_SUB + ROUTINE_LEN])
    if hook == ORIGINAL_HOOK:
        return ORIGINAL_LIVES
    if hook != HOOK:
        raise InitialLivesError("initial-lives hook is not original or custom.")
    return _read_lives_from_sub(sub)


def apply(data: bytearray, lives: int) -> list[str]:
    _check_bounds(data)
    lives = int(lives)
    if not (MIN_LIVES <= lives <= MAX_LIVES):
        raise InitialLivesError(f"initial lives must be {MIN_LIVES}-{MAX_LIVES}.")

    hook = bytes(data[OFF_HOOK:OFF_HOOK + len(ORIGINAL_HOOK)])
    sub = bytes(data[OFF_SUB:OFF_SUB + ROUTINE_LEN])
    if hook == ORIGINAL_HOOK:
        if sub != ORIGINAL_SUB:
            raise InitialLivesError("initial-lives cave is not empty.")
    elif hook == HOOK:
        _read_lives_from_sub(sub)
    else:
        raise InitialLivesError("initial-lives hook is not original or custom.")

    changed: list[str] = []
    if lives == ORIGINAL_LIVES:
        if hook == HOOK:
            data[OFF_HOOK:OFF_HOOK + len(ORIGINAL_HOOK)] = ORIGINAL_HOOK
            data[OFF_SUB:OFF_SUB + ROUTINE_LEN] = ORIGINAL_SUB
            changed.append("原作値へ復元")
        return changed

    routine = _routine(lives)
    if sub != routine:
        data[OFF_SUB:OFF_SUB + ROUTINE_LEN] = routine
        changed.append(f"初期残数{lives}")
    if hook != HOOK:
        data[OFF_HOOK:OFF_HOOK + len(ORIGINAL_HOOK)] = HOOK
        changed.append("NEW GAME残数フック")
    return changed


def restore(data: bytearray) -> list[str]:
    return apply(data, ORIGINAL_LIVES)

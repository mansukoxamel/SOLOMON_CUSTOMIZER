"""Initial magic stock/max patch.

JP/JP66 only.  New-game setup writes $042B at CPU $9144, while the later
stage-start initializer writes it again at CPU $C9E3.  Both sites are replaced
with a JSR to a small routine in the verified NOP band at $8BE2.  The routine
sets $042B/$042E/$042F and preserves A/X, so the surrounding original code
keeps working. Preserving A is required at $9144 because the original code
uses A=0 immediately afterward to clear $78-$7C.
"""

from __future__ import annotations


class InitialMagicError(RuntimeError):
    pass


OFF_SUB = 0x0BF2          # CPU $8BE2, verified NOP band
OFF_HOOK_START = 0x1154   # CPU $9144: STX $042B
OFF_HOOK_STAGE = 0x49F3   # CPU $C9E3: STX $042B
OFF_LEGACY_LEVEL = 0x3616 # CPU $B606, mistakenly hooked in v0.6.78

ORIGINAL_HOOK_START = bytes.fromhex("8E 2B 04")
ORIGINAL_HOOK_STAGE = bytes.fromhex("8E 2B 04")
ORIGINAL_LEGACY_LEVEL = bytes.fromhex("8D 2E 04")
ORIGINAL_LEGACY_LEVEL_TAIL = bytes.fromhex("8D 2F 04")
HOOK = bytes.fromhex("20 E2 8B")
ROUTINE_LEN = 18
ORIGINAL_SUB = bytes([0xEA] * ROUTINE_LEN)

ORIGINAL_MAX = 3
ORIGINAL_PATTERN = ""
MAX_COUNT_MIN = 0
MAX_COUNT_MAX = 8
MAX_PATTERN_CHARS = 8


def _routine(max_count: int, lo: int, hi: int) -> bytes:
    return bytes([
        0x48,                                           # PHA
        0xA9, max_count & 0xFF, 0x8D, 0x2B, 0x04,  # LDA #max / STA $042B
        0xA9, lo & 0xFF,        0x8D, 0x2E, 0x04,  # LDA #lo  / STA $042E
        0xA9, hi & 0xFF,        0x8D, 0x2F, 0x04,  # LDA #hi  / STA $042F
        0x68,                                           # PLA
        0x60,                                           # RTS
    ])


def _text_to_bytes(pattern: str) -> tuple[int, int]:
    s = (pattern or "").upper().replace(" ", "")
    if len(s) > MAX_PATTERN_CHARS:
        raise InitialMagicError("initial magic pattern must be 8 chars or shorter.")
    bits = []
    for ch in s:
        if ch == "F":
            bits.append("01")
        elif ch == "S":
            bits.append("10")
        else:
            raise InitialMagicError("initial magic pattern can contain only F and S.")
    bitstr = ("".join(bits)).ljust(16, "0")
    hi = int(bitstr[0:8], 2)
    lo = int(bitstr[8:16], 2)
    return lo, hi


def _bytes_to_text(lo: int, hi: int) -> str:
    bitstr = f"{hi:08b}{lo:08b}"
    out = []
    for i in range(0, 16, 2):
        pair = bitstr[i:i + 2]
        if pair == "01":
            out.append("F")
        elif pair == "10":
            out.append("S")
    return "".join(out)


def _check_bounds(data: bytes):
    need = max(
        OFF_SUB + len(ORIGINAL_SUB),
        OFF_HOOK_START + len(ORIGINAL_HOOK_START),
        OFF_HOOK_STAGE + len(ORIGINAL_HOOK_STAGE),
        OFF_LEGACY_LEVEL + len(ORIGINAL_LEGACY_LEVEL) + len(ORIGINAL_LEGACY_LEVEL_TAIL),
    )
    if len(data) < need:
        raise InitialMagicError("ROM is too small for the initial magic patch.")


def _read_hooks(data: bytes) -> tuple[bytes, bytes, bytes, bytes]:
    hook_start = bytes(data[OFF_HOOK_START:OFF_HOOK_START + 3])
    hook_stage = bytes(data[OFF_HOOK_STAGE:OFF_HOOK_STAGE + 3])
    legacy_level = bytes(data[OFF_LEGACY_LEVEL:OFF_LEGACY_LEVEL + 3])
    legacy_tail = bytes(data[OFF_LEGACY_LEVEL + 3:OFF_LEGACY_LEVEL + 6])
    return hook_start, hook_stage, legacy_level, legacy_tail


def _read_current_from_sub(sub: bytes) -> tuple[int, str]:
    # v0.6.79 wrote a 16-byte routine that did not preserve A. Accept it so
    # existing test ROMs can be migrated, but always rewrite to the 18-byte
    # A-preserving routine on apply.
    if (len(sub) >= 16 and sub[0] == 0xA9 and sub[2:5] == b"\x8D\x2B\x04"
            and sub[5] == 0xA9 and sub[7:10] == b"\x8D\x2E\x04"
            and sub[10] == 0xA9 and sub[12:16] == b"\x8D\x2F\x04\x60"):
        return sub[1], _bytes_to_text(sub[6], sub[11])
    if not (len(sub) == ROUTINE_LEN and sub[0] == 0x48
            and sub[1] == 0xA9 and sub[3:6] == b"\x8D\x2B\x04"
            and sub[6] == 0xA9 and sub[8:11] == b"\x8D\x2E\x04"
            and sub[11] == 0xA9 and sub[13:18] == b"\x8D\x2F\x04\x68\x60"):
        raise InitialMagicError("initial magic routine signature mismatch.")
    return sub[2], _bytes_to_text(sub[7], sub[12])


def is_applied(data: bytes) -> bool:
    _check_bounds(data)
    hook_start, hook_stage, legacy_level, _ = _read_hooks(data)
    return hook_start == HOOK or hook_stage == HOOK or legacy_level == HOOK


def current(data: bytes) -> tuple[int, str]:
    """Return (max_count, pattern_text)."""
    _check_bounds(data)
    hook_start, hook_stage, legacy_level, legacy_tail = _read_hooks(data)
    sub = bytes(data[OFF_SUB:OFF_SUB + ROUTINE_LEN])

    if legacy_tail != ORIGINAL_LEGACY_LEVEL_TAIL:
        raise InitialMagicError("initial magic legacy hook tail signature mismatch.")
    if hook_start == ORIGINAL_HOOK_START and hook_stage == ORIGINAL_HOOK_STAGE and legacy_level == ORIGINAL_LEGACY_LEVEL:
        return ORIGINAL_MAX, ORIGINAL_PATTERN
    if hook_start not in (ORIGINAL_HOOK_START, HOOK):
        raise InitialMagicError("initial magic start hook is not original or custom.")
    if hook_stage not in (ORIGINAL_HOOK_STAGE, HOOK):
        raise InitialMagicError("initial magic stage hook is not original or custom.")
    if legacy_level not in (ORIGINAL_LEGACY_LEVEL, HOOK):
        raise InitialMagicError("initial magic legacy hook is not original or custom.")
    if hook_start != HOOK or hook_stage != HOOK:
        raise InitialMagicError("initial magic hooks are only partially applied.")
    return _read_current_from_sub(sub)


def apply(data: bytearray, max_count: int, pattern: str) -> list[str]:
    _check_bounds(data)
    if not (MAX_COUNT_MIN <= max_count <= MAX_COUNT_MAX):
        raise InitialMagicError("initial magic max must be 0-8.")
    lo, hi = _text_to_bytes(pattern)

    hook_start, hook_stage, legacy_level, legacy_tail = _read_hooks(data)
    sub = bytes(data[OFF_SUB:OFF_SUB + ROUTINE_LEN])
    if legacy_tail != ORIGINAL_LEGACY_LEVEL_TAIL:
        raise InitialMagicError("initial magic legacy hook tail signature mismatch.")
    if hook_start not in (ORIGINAL_HOOK_START, HOOK):
        raise InitialMagicError("initial magic start hook is not original or custom.")
    if hook_stage not in (ORIGINAL_HOOK_STAGE, HOOK):
        raise InitialMagicError("initial magic stage hook is not original or custom.")
    if legacy_level not in (ORIGINAL_LEGACY_LEVEL, HOOK):
        raise InitialMagicError("initial magic legacy hook is not original or custom.")
    if hook_start == ORIGINAL_HOOK_START and hook_stage == ORIGINAL_HOOK_STAGE and legacy_level == ORIGINAL_LEGACY_LEVEL and sub != ORIGINAL_SUB:
        raise InitialMagicError("initial magic cave is not empty.")
    if hook_start == HOOK or hook_stage == HOOK or legacy_level == HOOK:
        # Validate before overwriting an existing custom routine.
        _read_current_from_sub(sub)

    default = (max_count == ORIGINAL_MAX and (pattern or "").strip() == ORIGINAL_PATTERN)
    changed = []
    if default:
        if hook_start == HOOK or hook_stage == HOOK or legacy_level == HOOK:
            data[OFF_HOOK_START:OFF_HOOK_START + 3] = ORIGINAL_HOOK_START
            data[OFF_HOOK_STAGE:OFF_HOOK_STAGE + 3] = ORIGINAL_HOOK_STAGE
            data[OFF_LEGACY_LEVEL:OFF_LEGACY_LEVEL + 3] = ORIGINAL_LEGACY_LEVEL
            data[OFF_SUB:OFF_SUB + ROUTINE_LEN] = ORIGINAL_SUB
            changed.append("原作値へ復元")
        return changed

    routine = _routine(max_count, lo, hi)
    if bytes(data[OFF_SUB:OFF_SUB + ROUTINE_LEN]) != routine:
        data[OFF_SUB:OFF_SUB + ROUTINE_LEN] = routine
        changed.append(f"最大{max_count}・初期所持{pattern or 'なし'}")
    if bytes(data[OFF_HOOK_START:OFF_HOOK_START + 3]) != HOOK:
        data[OFF_HOOK_START:OFF_HOOK_START + 3] = HOOK
        changed.append("NEW GAME初期化フック")
    if bytes(data[OFF_HOOK_STAGE:OFF_HOOK_STAGE + 3]) != HOOK:
        data[OFF_HOOK_STAGE:OFF_HOOK_STAGE + 3] = HOOK
        changed.append("ステージ開始フック")
    if bytes(data[OFF_LEGACY_LEVEL:OFF_LEGACY_LEVEL + 3]) == HOOK:
        data[OFF_LEGACY_LEVEL:OFF_LEGACY_LEVEL + 3] = ORIGINAL_LEGACY_LEVEL
        changed.append("旧誤フック除去")
    return changed


def normalize_pattern_text(pattern: str) -> str:
    # Public helper for UI preview/sanitizing.
    lo, hi = _text_to_bytes(pattern)
    return _bytes_to_text(lo, hi)

"""Neul/Ghost movement speed patch.

Neul uses Y velocity, Ghost uses X velocity. Both speed 1 and speed 2 are
kept in sync by applying the same multiplier to the four signed speed pairs.
"""

# JP/US common file offsets. The speed table itself is not relocated.
OFF_NEUL_SP1_P = 0x5BC7  # $DBB7 idx15 Yvel, down/positive
OFF_NEUL_SP1_N = 0x5BC9  # $DBB9 idx16 Yvel, up/negative
OFF_GHOST_SP1_P = 0x5BCC  # $DBBC idx17 Xvel, right/positive
OFF_GHOST_SP1_N = 0x5BCE  # $DBBE idx18 Xvel, left/negative
OFF_NEUL_SP2_P = 0x5BCF  # $DBBF idx19 Yvel, down/positive
OFF_NEUL_SP2_N = 0x5BD1  # $DBC1 idx20 Yvel, up/negative
OFF_GHOST_SP2_P = 0x5BD4  # $DBC4 idx21 Xvel, right/positive
OFF_GHOST_SP2_N = 0x5BD6  # $DBC6 idx22 Xvel, left/negative

ORIG = {
    OFF_NEUL_SP1_P: 0x1C, OFF_NEUL_SP1_N: 0x64,
    OFF_GHOST_SP1_P: 0x1C, OFF_GHOST_SP1_N: 0x64,
    OFF_NEUL_SP2_P: 0x2E, OFF_NEUL_SP2_N: 0x52,
    OFF_GHOST_SP2_P: 0x27, OFF_GHOST_SP2_N: 0x52,
}

SIG_OFF = 0x5BA9
SIG = bytes([0x00, 0x00, 0x40, 0x00, 0xC3, 0x00, 0x80, 0x00])

MULTIPLIERS = [0.5, 1.0, 1.5, 2.0]
SKIP_MARKER = 0x40


class NeulGhostSpeedError(ValueError):
    """Neul/Ghost speed patch verification failed."""


def _eff(v_byte: int) -> float:
    """Effective px/frame from the engine's signed V*8/256 conversion."""
    a = v_byte
    hi = 0
    x = (a >> 7) & 1
    a = (a << 1) & 0xFF
    x = (a >> 7) & 1
    a = (a << 1) & 0xFF
    if x:
        hi = 0xFF
    y = (a >> 7) & 1
    a = (a << 1) & 0xFF
    hi = ((hi << 1) | y) & 0xFF
    value = (hi << 8) | a
    if value >= 0x8000:
        value -= 0x10000
    return value / 256.0


_TABLE = [(v, _eff(v)) for v in range(256) if v != SKIP_MARKER]


def _find_byte(target: float) -> int:
    if target >= 0:
        candidates = [(v, e) for v, e in _TABLE if e >= 0]
    else:
        # Neul/Ghost original negative speeds use $41-$7F. Avoid unverified
        # high-bit aliases such as $C0 even if the math says they are close.
        candidates = [(v, e) for v, e in _TABLE if e < 0 and v < 0x80]
    return min(candidates, key=lambda t: abs(t[1] - target))[0]


def verify(rom_data) -> None:
    if rom_data is None or len(rom_data) < SIG_OFF + len(SIG):
        raise NeulGhostSpeedError("ROM が短すぎます。")
    actual = bytes(rom_data[SIG_OFF:SIG_OFF + len(SIG)])
    if actual != SIG:
        raise NeulGhostSpeedError(
            f"速度テーブル ($DB99) に期待バイト列がありません。\n"
            f"  期待: {SIG.hex(' ')}\n  実際: {actual.hex(' ')}\n"
            "改造ROM/別版/破損の可能性があるため移動速度の改造を中止します。"
        )


def current_multiplier(rom_data) -> float:
    verify(rom_data)
    cur = abs(_eff(rom_data[OFF_GHOST_SP1_P]))
    base = abs(_eff(ORIG[OFF_GHOST_SP1_P]))
    return round(cur / base, 2) if base else 1.0


def _apply_pair(rom_data, off_p: int, off_n: int, mult: float, changed: list):
    op, on = ORIG[off_p], ORIG[off_n]
    if abs(mult - 1.0) < 1e-6:
        np_, nn = op, on
    else:
        np_ = _find_byte(_eff(op) * mult)
        nn = _find_byte(_eff(on) * mult)
    if rom_data[off_p] != np_:
        rom_data[off_p] = np_
        changed.append(f"${0x8000 + off_p - 0x10:04X}=${np_:02X}")
    if rom_data[off_n] != nn:
        rom_data[off_n] = nn
        changed.append(f"${0x8000 + off_n - 0x10:04X}=${nn:02X}")


def apply(rom_data, multiplier: float) -> list:
    """Apply one multiplier to Neul Y speed and Ghost X speed, SP1/SP2."""
    verify(rom_data)
    changed = []
    _apply_pair(rom_data, OFF_NEUL_SP1_P, OFF_NEUL_SP1_N, multiplier, changed)
    _apply_pair(rom_data, OFF_GHOST_SP1_P, OFF_GHOST_SP1_N, multiplier, changed)
    _apply_pair(rom_data, OFF_NEUL_SP2_P, OFF_NEUL_SP2_N, multiplier, changed)
    _apply_pair(rom_data, OFF_GHOST_SP2_P, OFF_GHOST_SP2_N, multiplier, changed)
    if not changed:
        return []
    return [f"Neul/Ghost移動速度 {multiplier:g}x ({len(changed)}バイト)"]

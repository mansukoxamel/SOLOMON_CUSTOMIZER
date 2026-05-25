"""Spark Ball movement speed multiplier patch.

Spark Ball does not use the generic $DB99 velocity table. Its wall-following
movement reads two signed delta tables at $A9DF/$A9E7. The same tables are
used by the Dragon-ID Spark Ball variants that jump into $A929/$A92D.
"""

OFF_TABLE_A = 0x29EF  # CPU $A9DF
OFF_TABLE_B = 0x29F7  # CPU $A9E7
ORIG_TABLE_A = bytes.fromhex("00 00 DE 22 00 00 B4 4C")
ORIG_TABLE_B = bytes.fromhex("22 DE 00 00 4C B4 00 00")

SIG_OFF = 0x295B  # CPU $A94B: LDA $A9DF,X / STA $00 / LDA $A9E7,X / STA $01
SIG = bytes.fromhex("BD DF A9 85 00 BD E7 A9 85 01")

MULTIPLIERS = [0.5, 1.0, 1.5, 2.0]


class SparkBallSpeedError(ValueError):
    """Spark Ball speed patch verification failed."""


def _signed(v: int) -> int:
    return v if v < 0x80 else v - 0x100


def _byte(v: int) -> int:
    return v & 0xFF


def _scale_byte(v: int, multiplier: float) -> int:
    if v == 0:
        return 0
    scaled = int(round(_signed(v) * multiplier))
    scaled = max(-128, min(127, scaled))
    return _byte(scaled)


def _scale_table(table: bytes, multiplier: float) -> bytes:
    if abs(multiplier - 1.0) < 1e-6:
        return bytes(table)
    return bytes(_scale_byte(v, multiplier) for v in table)


def verify(rom_data) -> None:
    if rom_data is None or len(rom_data) < OFF_TABLE_B + len(ORIG_TABLE_B):
        raise SparkBallSpeedError("ROM が短すぎます。")
    actual = bytes(rom_data[SIG_OFF:SIG_OFF + len(SIG)])
    if actual != SIG:
        raise SparkBallSpeedError(
            "Spark Ball 移動テーブル参照コードに期待バイト列がありません。\n"
            f"  期待: {SIG.hex(' ')}\n"
            f"  実際: {actual.hex(' ')}\n"
            "別の改造と衝突している可能性があるため、速度変更を中止します。"
        )


def current_multiplier(rom_data) -> float:
    verify(rom_data)
    base = abs(_signed(ORIG_TABLE_B[0]))
    cur = abs(_signed(rom_data[OFF_TABLE_B]))
    return round(cur / base, 2) if base else 1.0


def apply(rom_data, multiplier: float) -> list:
    """Apply one multiplier to Spark Ball speed 1 and speed 2 directions."""
    verify(rom_data)
    if multiplier not in MULTIPLIERS:
        raise SparkBallSpeedError(f"未対応の倍率です: {multiplier!r}")

    table_a = _scale_table(ORIG_TABLE_A, multiplier)
    table_b = _scale_table(ORIG_TABLE_B, multiplier)
    changed = []

    for i, value in enumerate(table_a):
        off = OFF_TABLE_A + i
        if rom_data[off] != value:
            rom_data[off] = value
            changed.append(f"${0x8000 + off - 0x10:04X}=${value:02X}")
    for i, value in enumerate(table_b):
        off = OFF_TABLE_B + i
        if rom_data[off] != value:
            rom_data[off] = value
            changed.append(f"${0x8000 + off - 0x10:04X}=${value:02X}")

    if not changed:
        return []
    return [f"Spark Ball移動速度 {multiplier:g}x ({len(changed)}バイト)"]

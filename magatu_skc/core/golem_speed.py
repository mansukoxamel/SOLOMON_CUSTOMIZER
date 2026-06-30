"""ゴーレム移動速度の改造 (位置 + シグネチャ ダブル検証方式)

Mesen実機ブレークポイント解析で真のレバーを特定 (2026-05-16)。
速度テーブル本体 $DB99 は JP/US 同一 file offset (再配置されない)。
behavior→speed-index 表経由で参照される (Yvel,Xvel) ペアの Xvel を変える。

確定レバー (JP/US 共通 file offset):
  共通 s0 通常歩行                : $DBD0/$DBD2 = file 0x5BE0/0x5BE2 (原作 $0C/$74, ±0.375)

速度 = SUB_8689 の V*8/256 符号拡張。実効上限 ≈ ±2.0 px/f。
$40 ちょうどは SUB_8AC0 の「速度更新スキップ」マーカーのため使用禁止 (敵が止まる)。
※ s0 通常歩行は Golem / Dragon / Gargoyle で共有されるため、UIでも共通設定として扱う。
"""

# JP/US 共通 file offset (速度テーブル本体は再配置されない)
OFF_S0_WALK_P = 0x5BE0   # $DBD0 idx$1B Xvel
OFF_S0_WALK_N = 0x5BE2   # $DBD2 idx$1C Xvel

ORIG = {
    OFF_S0_WALK_P: 0x0C, OFF_S0_WALK_N: 0x74,
}

SIG_OFF = 0x5BA9   # $DB99 速度テーブル先頭 (改造対象不含・JP/US一意確認済)
SIG     = bytes([0x00, 0x00, 0x40, 0x00, 0xC3, 0x00, 0x80, 0x00])

MULTIPLIERS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

SKIP_MARKER = 0x40  # SUB_8AC0 のスキップマーカー (使用禁止)


class GolemSpeedError(ValueError):
    """ゴーレム速度改造の検証失敗"""


def _eff(V: int) -> float:
    """SUB_8689 の V*8/256 符号拡張による実効 px/frame"""
    a = V; hi = 0
    x = (a >> 7) & 1; a = (a << 1) & 0xFF
    x = (a >> 7) & 1; a = (a << 1) & 0xFF
    if x: hi = 0xFF
    y = (a >> 7) & 1; a = (a << 1) & 0xFF
    hi = ((hi << 1) | y) & 0xFF
    v = (hi << 8) | a
    if v >= 0x8000: v -= 0x10000
    return v / 256.0


# 速度→バイト の逆引き (全256値スキャン、$40除外)
_TABLE = [(V, _eff(V)) for V in range(256) if V != SKIP_MARKER]


def _find_byte(target: float) -> int:
    """target px/f に最も近い実効速度を持つバイト ($40除外)"""
    best = min(_TABLE, key=lambda t: abs(t[1] - target))
    return best[0]


def verify(rom_data) -> None:
    if rom_data is None or len(rom_data) < SIG_OFF + len(SIG):
        raise GolemSpeedError("ROM が短すぎます。")
    actual = bytes(rom_data[SIG_OFF:SIG_OFF + len(SIG)])
    if actual != SIG:
        raise GolemSpeedError(
            f"速度テーブル ($DB99) に期待バイト列がありません。\n"
            f"  期待: {SIG.hex(' ')}\n  実際: {actual.hex(' ')}\n"
            f"改造ROM/拡張ROM/破損の可能性のため改造を中止します。"
        )


def current_shared_walk_mult(rom_data) -> float:
    verify(rom_data)
    cur = _eff(rom_data[OFF_S0_WALK_P])
    base = _eff(ORIG[OFF_S0_WALK_P])
    return round(cur / base, 2) if base else 1.0


def _apply_pair(rom_data, off_p, off_n, mult, changed):
    """+ / - 方向ペアを倍率適用 (1.0x は原作バイト厳密復元)"""
    op, on = ORIG[off_p], ORIG[off_n]
    if abs(mult - 1.0) < 1e-6:
        np_, nn = op, on
    else:
        np_ = _find_byte(_eff(op) * mult)
        nn  = _find_byte(_eff(on) * mult)
    if rom_data[off_p] != np_:
        rom_data[off_p] = np_; changed.append(f"${0x8000+off_p-0x10:04X}=${np_:02X}")
    if rom_data[off_n] != nn:
        rom_data[off_n] = nn; changed.append(f"${0x8000+off_n-0x10:04X}=${nn:02X}")


def apply_shared_walk(rom_data, shared_walk_mult: float) -> list:
    """Golem / Dragon / Gargoyle s0 shared walk speed only."""
    verify(rom_data)
    changed = []
    _apply_pair(
        rom_data, OFF_S0_WALK_P, OFF_S0_WALK_N, shared_walk_mult, changed)
    if not changed:
        return []
    return [f"共通歩行{shared_walk_mult:g}x ({len(changed)}バイト)"]

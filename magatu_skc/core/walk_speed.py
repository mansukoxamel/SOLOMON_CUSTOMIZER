"""ダーナ歩行速度の改造 (位置 + シグネチャ ダブル検証方式)

CLAUDE.md ルール準拠:
  - JP/US 両対応だが、この領域は $C400-$CFFF 外なので両リージョン完全同一
  - 改造前に「期待位置に期待シグネチャがあるか」を必ず検証
  - 検証失敗時は ValueError でパッチ中止 (フォールバック禁止)

実機検証済み (R107):
  $DBA6 idx6 = 地上歩行 右 X速度 (原作 $18)
  $DBA8 idx7 = 地上歩行 左 X速度 (原作 $68)
  $DBAA idx8 = 空中横移動 右 X速度 (原作 $18)
  $DBAC idx9 = 空中横移動 左 X速度 (原作 $68)

速度公式: V*8/256 px/frame  (原作 $18 = 0.75 px/frame = 1.0x 基準)
$40 ちょうどは SUB_8AC0 の「速度更新スキップ」マーカーなので使用禁止。
"""

# --- CPU アドレス → iNES ファイルオフセット ---
def _off(cpu_addr: int) -> int:
    return 0x10 + (cpu_addr - 0x8000)

# 改造対象 4 バイト (JP/US 共通)
ADDR_GROUND_RIGHT = 0xDBA6
ADDR_GROUND_LEFT  = 0xDBA8
ADDR_AIR_RIGHT    = 0xDBAA
ADDR_AIR_LEFT     = 0xDBAC

OFF_GROUND_RIGHT = _off(ADDR_GROUND_RIGHT)  # 0x5BB6
OFF_GROUND_LEFT  = _off(ADDR_GROUND_LEFT)   # 0x5BB8
OFF_AIR_RIGHT    = _off(ADDR_AIR_RIGHT)     # 0x5BBA
OFF_AIR_LEFT     = _off(ADDR_AIR_LEFT)      # 0x5BBC

# 検証シグネチャ: $DB99-$DBA5 (改造対象の直前、速度テーブル先頭、不変)
SIG_ADDR  = 0xDB99
SIG_OFF   = _off(SIG_ADDR)  # 0x5BA9
SIG_BYTES = bytes([0x00, 0x00, 0x40, 0x00, 0xC3, 0x00, 0x80, 0x00,
                   0x80, 0x10, 0x80, 0x70, 0x80])  # 13 bytes

# プリセット: (倍率, 右V, 左V)  ※ 1.0x は原作バイトを厳密復元 ($18/$68)
PRESETS = [
    (0.5,  0x0C, 0xF4),
    (1.0,  0x18, 0x68),
    (1.25, 0x1E, 0xE2),
    (1.5,  0x24, 0xDC),
    (2.0,  0x30, 0xD0),
    (2.5,  0x3C, 0xC4),
    (3.0,  0x48, 0xB8),
]

ORIG_RIGHT = 0x18
ORIG_LEFT  = 0x68


class WalkSpeedError(ValueError):
    """歩行速度パッチの検証失敗"""


def verify(rom_data) -> None:
    """位置 + シグネチャ ダブル検証。失敗時 WalkSpeedError"""
    if rom_data is None or len(rom_data) < SIG_OFF + len(SIG_BYTES):
        raise WalkSpeedError("ROM が短すぎます。")
    actual = bytes(rom_data[SIG_OFF:SIG_OFF + len(SIG_BYTES)])
    if actual != SIG_BYTES:
        raise WalkSpeedError(
            f"ROM検証失敗: 速度テーブル (${SIG_ADDR:04X}) に期待バイト列がありません。\n"
            f"  期待: {SIG_BYTES.hex(' ')}\n"
            f"  実際: {actual.hex(' ')}\n"
            f"改造ROM/異版/破損の可能性があるため歩行速度の改造を中止します。"
        )


def speed_to_multiplier(right_v: int) -> float:
    """右Vバイト値 → 倍率 (原作 $18 = 1.0x)"""
    return (right_v * 8 / 256) / 0.75


def current_values(rom_data):
    """現在の (右V, 左V) を返す。検証も実施"""
    verify(rom_data)
    return rom_data[OFF_GROUND_RIGHT], rom_data[OFF_GROUND_LEFT]


def current_multiplier(rom_data) -> float:
    r, _ = current_values(rom_data)
    return speed_to_multiplier(r)


def apply(rom_data, right_v: int, left_v: int) -> list:
    """歩行速度を改造。検証 → 4バイト書込。変更項目リストを返す"""
    verify(rom_data)
    if right_v == 0x40 or left_v == 0x40:
        raise WalkSpeedError("$40 は速度更新スキップマーカーのため使用できません。")
    changed = []
    for off, val, name in (
        (OFF_GROUND_RIGHT, right_v, "地上歩行 右"),
        (OFF_GROUND_LEFT,  left_v,  "地上歩行 左"),
        (OFF_AIR_RIGHT,    right_v, "空中横移動 右"),
        (OFF_AIR_LEFT,     left_v,  "空中横移動 左"),
    ):
        if rom_data[off] != val:
            rom_data[off] = val
            changed.append(name)
    return changed


def apply_multiplier(rom_data, multiplier: float) -> list:
    """倍率プリセットで改造 (PRESETS にあるものを優先、無ければ算出)"""
    for m, r, l in PRESETS:
        if abs(m - multiplier) < 1e-6:
            return apply(rom_data, r, l)
    # プリセット外: 算出 ($18 基準) / $40 回避
    right_v = max(1, min(0x3F, round(ORIG_RIGHT * multiplier)))
    if right_v == 0x40:
        right_v = 0x3F
    left_v = (0x100 - right_v) & 0xFF
    if left_v == 0x40:
        left_v = 0x41
    return apply(rom_data, right_v, left_v)

"""パネルモンスター発射クールダウン/キビキビ動作の改造

CLAUDE.md ルール準拠:
  - JP/US 両対応。US は再配置ゾーン (JP +$140)
  - 改造前に安定シグネチャを検証、失敗時 PanelMonsterHackError でパッチ中止

Codex解析 + ROMバイト検証で確定 (2026-05-16):
  Panel Monster (type $24-$27, AI $A54C) の Bullet 発射周期 =
    (しきい値 $A57A + 発射ディレイ $A55B) / 60 秒
  原作: ($C0 + $10) / 60 = 208/60 ≈ 3.47 秒。線形比例 (カウンタ +1/frame)。
  $A57A はクールダウンしきい値としてフレーム単位で設定する。
  $A55B は発射直前ディレイで、キビキビ動作 ON のとき $01 に短縮する。
  安全下限: しきい値 $20 (それ未満は複数パネル面で sub-slot 枯渇リスク)
  Panel Monster 専用 (AI dispatch $A336 → $A54C)。
"""

ORIG_FIRE_DELAY = 0x10   # $A55B 発射ディレイ
SNAPPY_DELAY    = 0x01
ORIG_THRESHOLD  = 0xC0   # $A57A 原作クールダウンしきい値
MIN_THRESHOLD   = 0x20   # 安全下限 (sub-slot 枯渇回避)
MAX_THRESHOLD   = 0xFF

VARIANT_HOOK_OFF = 0x2566
VARIANT_HOOK = bytes.fromhex("4c d2 bc")
ORIG_PANEL_FIRE_HEAD = bytes.fromhex("a0 01 b1")
SPARK_PROPERTY_HOOK_CURRENT_BODY = bytes.fromhex(
    "a5 05 29 fe c9 6a f0 0f c9 6e f0 0b c9 72 f0 07 "
    "c9 76 f0 03 4c df db a9 19 60"
)
VARIANT_FIRE_DELAY_OFFS = (
    0x3FCE,  # normal Panel Monster fire copy, CMP operand
    0x409D,  # 2-way cave, CMP operand
    0x3D9D,  # 3-way cave, CMP operand
)

_OFF = {
    "JP": {
        "fire_delay": 0x256B,  # $A55B CMP #$10 operand
        "threshold": 0x258A,   # $A57A CMP #$C0 operand
        # sig: threshold 直後の安定領域 ($A57B-, 改造対象外, 一意確認済)
        "sig_off":   0x258B,   # $A57B: 90 22 20 EA B2 90 1D 8A A0
        "sig":       bytes.fromhex("90 22 20 ea b2 90 1d 8a a0"),
    },
    "US": {  # JP +$140 (再配置ゾーン、JSR先 $B2EA→$B42A で sig 一部差)
        "fire_delay": 0x26AB,
        "threshold": 0x26CA,
        "sig_off":   0x26CB,
        "sig":       bytes.fromhex("90 22 20 2a b4 90 1d 8a a0"),
    },
}


class PanelMonsterHackError(ValueError):
    """パネルモンスター改造の検証失敗"""


def detect_region(rom_data) -> str:
    for region, o in _OFF.items():
        end = o["sig_off"] + len(o["sig"])
        if len(rom_data) < end:
            continue
        fire_op = o["fire_delay"] - 1
        has_original_fire = fire_op >= 0 and rom_data[fire_op] == 0xC9
        has_variant_hook = (
            region == "JP"
            and len(rom_data) >= VARIANT_HOOK_OFF + len(VARIANT_HOOK)
            and bytes(rom_data[VARIANT_HOOK_OFF:VARIANT_HOOK_OFF + len(VARIANT_HOOK)]) == VARIANT_HOOK
        )
        has_orig_panel_spark_hybrid = (
            region == "JP"
            and len(rom_data) >= (
                VARIANT_HOOK_OFF
                + len(ORIG_PANEL_FIRE_HEAD)
                + len(SPARK_PROPERTY_HOOK_CURRENT_BODY)
            )
            and bytes(rom_data[VARIANT_HOOK_OFF:VARIANT_HOOK_OFF + len(ORIG_PANEL_FIRE_HEAD)])
            == ORIG_PANEL_FIRE_HEAD
            and bytes(
                rom_data[
                    VARIANT_HOOK_OFF + len(ORIG_PANEL_FIRE_HEAD):
                    VARIANT_HOOK_OFF + len(ORIG_PANEL_FIRE_HEAD) + len(SPARK_PROPERTY_HOOK_CURRENT_BODY)
                ]
            ) == SPARK_PROPERTY_HOOK_CURRENT_BODY
        )
        if (
            bytes(rom_data[o["sig_off"]:end]) == o["sig"]
            and (has_original_fire or has_variant_hook or has_orig_panel_spark_hybrid)
        ):
            return region
    raise PanelMonsterHackError(
        "パネルモンスターのコードが見つかりません。\n"
        "改造ROM/拡張ROM/破損の可能性があるため改造を中止します。"
    )


def clamp_cooldown_frames(frames: int) -> int:
    """クールダウンフレーム → しきい値バイト ($20-$FF にクランプ)"""
    return max(MIN_THRESHOLD, min(MAX_THRESHOLD, int(frames)))


def threshold_to_sec(threshold: int) -> float:
    """原作ディレイ込みの目安秒。互換表示用。"""
    return (threshold + ORIG_FIRE_DELAY) / 60.0


def total_cycle_sec(cooldown_frames: int, fire_delay: int) -> float:
    """クールダウン + 発射前ディレイの目安秒"""
    return (cooldown_frames + fire_delay) / 60.0


def current_cooldown_frames(rom_data) -> int:
    region = detect_region(rom_data)
    return rom_data[_OFF[region]["threshold"]]


def current_threshold(rom_data) -> int:
    return current_cooldown_frames(rom_data)


def current_fire_delay(rom_data) -> int:
    region = detect_region(rom_data)
    o = _OFF[region]
    fire_op = o["fire_delay"] - 1
    if fire_op >= 0 and rom_data[fire_op] == 0xC9:
        return rom_data[o["fire_delay"]]
    for off in VARIANT_FIRE_DELAY_OFFS:
        if len(rom_data) > off and rom_data[off - 1] == 0xC9:
            return rom_data[off]
    return ORIG_FIRE_DELAY


def _fire_delay_write_offsets(rom_data, region: str) -> list[int]:
    o = _OFF[region]
    fire_op = o["fire_delay"] - 1
    if fire_op >= 0 and rom_data[fire_op] == 0xC9:
        return [o["fire_delay"]]
    return [
        off for off in VARIANT_FIRE_DELAY_OFFS
        if len(rom_data) > off and rom_data[off - 1] == 0xC9
    ]


def current_interval_sec(rom_data) -> float:
    return total_cycle_sec(current_cooldown_frames(rom_data), current_fire_delay(rom_data))


def is_snappy(rom_data) -> bool:
    return current_fire_delay(rom_data) == SNAPPY_DELAY


def apply_cooldown(rom_data, frames: int) -> list:
    """クールダウンをフレーム指定で改造。検証 → 書込。変更項目リストを返す"""
    region = detect_region(rom_data)
    o = _OFF[region]
    th = clamp_cooldown_frames(frames)
    if rom_data[o["threshold"]] != th:
        rom_data[o["threshold"]] = th
        return [f"クールダウン→{th}フレーム (${th:02X})"]
    return []


def restore_cooldown(rom_data) -> list:
    """クールダウンだけを原作値へ戻す。発射前ディレイは触らない。"""
    region = detect_region(rom_data)
    o = _OFF[region]
    if rom_data[o["threshold"]] != ORIG_THRESHOLD:
        rom_data[o["threshold"]] = ORIG_THRESHOLD
        return ["クールダウン→原作 192フレーム"]
    return []


def apply_snappy(rom_data, enabled: bool) -> list:
    """発射直前ディレイを最小化する。"""
    region = detect_region(rom_data)
    val = SNAPPY_DELAY if enabled else ORIG_FIRE_DELAY
    changed = False
    for off in _fire_delay_write_offsets(rom_data, region):
        if rom_data[off] != val:
            rom_data[off] = val
            changed = True
    if changed:
        if enabled:
            return [f"キビキビ動作ON: 発射前待ち→{val}フレーム"]
        return [f"キビキビ動作OFF: 発射前待ち→{val}フレーム"]
    return []


def apply(rom_data, frames: int) -> list:
    """旧呼び出し互換: クールダウンをフレーム指定で改造。"""
    return apply_cooldown(rom_data, frames)


def restore(rom_data) -> list:
    """原作 ($C0 + $10 ≈ 3.47秒) に復元"""
    region = detect_region(rom_data)
    o = _OFF[region]
    changed = []
    if rom_data[o["threshold"]] != ORIG_THRESHOLD:
        rom_data[o["threshold"]] = ORIG_THRESHOLD
        changed.append("クールダウン→原作 192フレーム")
    delay_changed = False
    for off in _fire_delay_write_offsets(rom_data, region):
        if rom_data[off] != ORIG_FIRE_DELAY:
            rom_data[off] = ORIG_FIRE_DELAY
            delay_changed = True
    if delay_changed:
        changed.append("発射前待ち→原作 16フレーム")
    return changed

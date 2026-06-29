"""パネルモンスター発射クールダウンの改造

CLAUDE.md ルール準拠:
  - JP/US 両対応。US は再配置ゾーン (JP +$140)
  - 改造前に安定シグネチャを検証、失敗時 PanelMonsterHackError でパッチ中止

Codex解析 + ROMバイト検証で確定 (2026-05-16):
  Panel Monster (type $24-$27, AI $A54C) の発射待ちは
  しきい値 $A57A で制御される。
  $A57A はクールダウンしきい値としてフレーム単位で設定する。
  安全下限: しきい値 $20 (それ未満は複数パネル面で sub-slot 枯渇リスク)
  Panel Monster 専用 (AI dispatch $A336 → $A54C)。
"""

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
FINAL_INTERVAL_HOOK_OFF = 0x2585
FINAL_INTERVAL_HOOK = bytes.fromhex("20 62 be ea ea ea")
FINAL_THRESHOLD_OP_OFF = 0x3E81  # CPU $BE71: CMP #imm in final interval helper
FINAL_THRESHOLD_OFF = 0x3E82     # CPU $BE72: final cooldown threshold operand
FINAL_THRESHOLD_RTS_OFF = 0x3E83

_OFF = {
    "JP": {
        "fire_cmp_op": 0x256A,  # $A55A CMP opcode used as stock fire-routine signature
        "threshold": 0x258A,   # $A57A CMP #$C0 operand
        # sig: threshold 直後の安定領域 ($A57B-, 改造対象外, 一意確認済)
        "sig_off":   0x258B,   # $A57B: 90 22 20 EA B2 90 1D 8A A0
        "sig":       bytes.fromhex("90 22 20 ea b2 90 1d 8a a0"),
    },
    "US": {  # JP +$140 (再配置ゾーン、JSR先 $B2EA→$B42A で sig 一部差)
        "fire_cmp_op": 0x26AA,
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
        fire_op = o["fire_cmp_op"]
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
        has_final_interval_hook = (
            region == "JP"
            and len(rom_data) >= FINAL_INTERVAL_HOOK_OFF + len(FINAL_INTERVAL_HOOK)
            and bytes(rom_data[FINAL_INTERVAL_HOOK_OFF:FINAL_INTERVAL_HOOK_OFF + len(FINAL_INTERVAL_HOOK)])
            == FINAL_INTERVAL_HOOK
        )
        if (
            (
                bytes(rom_data[o["sig_off"]:end]) == o["sig"]
                and (has_original_fire or has_variant_hook or has_orig_panel_spark_hybrid)
            )
            or has_final_interval_hook
        ):
            return region
    raise PanelMonsterHackError(
        "パネルモンスターのコードが見つかりません。\n"
        "改造ROM/拡張ROM/破損の可能性があるため改造を中止します。"
    )


def _has_final_interval_hook(rom_data, region: str) -> bool:
    if region != "JP":
        return False
    end = FINAL_INTERVAL_HOOK_OFF + len(FINAL_INTERVAL_HOOK)
    return (
        len(rom_data) >= end
        and bytes(rom_data[FINAL_INTERVAL_HOOK_OFF:end]) == FINAL_INTERVAL_HOOK
    )


def _threshold_write_offset(rom_data, region: str) -> int:
    if _has_final_interval_hook(rom_data, region):
        if (
            len(rom_data) <= FINAL_THRESHOLD_RTS_OFF
            or rom_data[FINAL_THRESHOLD_OP_OFF] != 0xC9
            or rom_data[FINAL_THRESHOLD_RTS_OFF] != 0x60
        ):
            raise PanelMonsterHackError(
                "Panel Variant final のクールダウン比較コードが見つかりません。\n"
                "クールダウン書き込みを中止します。"
            )
        return FINAL_THRESHOLD_OFF
    return _OFF[region]["threshold"]


def clamp_cooldown_frames(frames: int) -> int:
    """クールダウンフレーム → しきい値バイト ($20-$FF にクランプ)"""
    return max(MIN_THRESHOLD, min(MAX_THRESHOLD, int(frames)))


def current_cooldown_frames(rom_data) -> int:
    region = detect_region(rom_data)
    return rom_data[_threshold_write_offset(rom_data, region)]


def current_threshold(rom_data) -> int:
    return current_cooldown_frames(rom_data)


def apply_cooldown(rom_data, frames: int) -> list:
    """クールダウンをフレーム指定で改造。検証 → 書込。変更項目リストを返す"""
    region = detect_region(rom_data)
    threshold_off = _threshold_write_offset(rom_data, region)
    th = clamp_cooldown_frames(frames)
    if rom_data[threshold_off] != th:
        rom_data[threshold_off] = th
        return [f"クールダウン→{th}フレーム (${th:02X})"]
    return []


def restore_cooldown(rom_data) -> list:
    """クールダウンだけを原作値へ戻す。発射前ディレイは触らない。"""
    region = detect_region(rom_data)
    threshold_off = _threshold_write_offset(rom_data, region)
    if rom_data[threshold_off] != ORIG_THRESHOLD:
        rom_data[threshold_off] = ORIG_THRESHOLD
        return ["クールダウン→原作 192フレーム"]
    return []


def apply(rom_data, frames: int) -> list:
    """既存API: クールダウンをフレーム指定で改造。"""
    return apply_cooldown(rom_data, frames)


def restore(rom_data) -> list:
    """クールダウンを原作値 ($C0) に復元"""
    region = detect_region(rom_data)
    threshold_off = _threshold_write_offset(rom_data, region)
    changed = []
    if rom_data[threshold_off] != ORIG_THRESHOLD:
        rom_data[threshold_off] = ORIG_THRESHOLD
        changed.append("クールダウン→原作 192フレーム")
    return changed

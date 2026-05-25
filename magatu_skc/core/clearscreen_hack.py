"""クリア画面 (THANK YOU DANA) の2体キャラ差し替え (位置+シグネチャ検証)

CLAUDE.md ルール準拠 / JP・US 同一 (ゲーム本編コード、再配置なし)。

ROM解析で確定 (Round 110/128/131/132, 全ROMバイト裏取り):
  action$14→$8EE4 が左右2体を生成 ($8F45-$8F68)。
    type   = file 0x0FBC ($8FAC, 既定 $1C=Fairy)
    state v= file 0x0F6D ($8F5D LDA #v, slot0=v*2 / slot1=v*2+1)
  status=$C0 で AI 非走行。共通アニメ $8789 が metadata で駆動。
  ★ state の behavior が beh!=0 だと共通物理 $8689 で速度が入り
    クリア画面で落下/移動して崩れる。beh=$00(速度0)の state のみ安全。

確定プリセット (type, v) — 全て beh=$00 速度ゼロ:
  Fairy(原作)  $1C / $0C  state24/25 羽ばたき
  Golem        $70 / $00  state0/1   固有歩行 3fループ
  Gargoyle(速) $78 / $00  state0/1   固有 2fループ
  Gargoyle(遅) $78 / $04  state8/9   固有 4fループ
  Demonhead    $50 / $06  state12/13 固有 idle 2fループ
  Saramandor   $5C / $06  state12/13 固有 idle 2fループ
"""

# 改造対象
TYPE_OFF = 0x0FBC      # $8FAC: クリア画面 entity type
STATE_OFF = 0x0F6D     # $8F5D: LDA #v (v=state base)

# シグネチャ (位置+パターン ダブル検証)
TBL_SIG_OFF = 0x0FBA   # $8FAA: 00 C0 1C FF 28 C8 (共通init+X座標)
TBL_SIG = bytes.fromhex("00 c0 1c ff 28 c8")
ST_SIG_OFF = 0x0F6C    # $8F5C: A9 0C 2A (LDA #v / ROL A)
ST_SIG = bytes.fromhex("a9 0c 2a")

# (ラベル: (type, v)) 全て速度ゼロ=置物として安全
PRESETS = {
    "Fairy (原作)":        (0x1C, 0x0C),
    "Golem":               (0x70, 0x00),
    "Gargoyle (速い)":     (0x78, 0x00),
    "Gargoyle (遅い)":     (0x78, 0x04),
    "Demonhead":           (0x50, 0x06),
    "Saramandor":          (0x5C, 0x06),
}


class ClearScreenHackError(ValueError):
    """クリア画面改造の検証失敗"""


PRESET_DEFS = {
    "fairy_original": {"label": "Fairy (原作)", "type": 0x1C, "state": 0x0C},
    "golem": {"label": "Golem", "type": 0x70, "state": 0x00},
    "gargoyle_fast": {"label": "Gargoyle (速い)", "type": 0x78, "state": 0x00},
    "gargoyle_slow": {"label": "Gargoyle (遅い)", "type": 0x78, "state": 0x04},
    "demonhead": {"label": "Demonhead", "type": 0x50, "state": 0x06},
    "saramandor": {"label": "Saramandor", "type": 0x5C, "state": 0x06},
}


def _validate(rom_data):
    """位置+シグネチャ ダブル検証。失敗時は例外でパッチ中止。"""
    tbl = bytes(rom_data[TBL_SIG_OFF:TBL_SIG_OFF + len(TBL_SIG)])
    st = bytes(rom_data[ST_SIG_OFF:ST_SIG_OFF + len(ST_SIG)])
    # TBL_SIG = 00 C0 [type] FF 28 C8。index2 は type 改造対象なので
    # 除外し、安定バイト (0,1,3,4,5) のみ照合 (再適用でも通る)
    stable_idx = (0, 1, 3, 4, 5)
    if any(tbl[i] != TBL_SIG[i] for i in stable_idx):
        raise ClearScreenHackError(
            f"ROM検証失敗: 0x{TBL_SIG_OFF:X} に期待バイト列がありません。"
            "改造ROM/異版/破損の可能性があるためパッチを中止します。")
    # state sig は v 部分 (offset+1) を除いて照合 (v は改造済みかも)
    if st[0] != ST_SIG[0] or st[2] != ST_SIG[2]:  # A9 .. 2A
        raise ClearScreenHackError(
            f"ROM検証失敗: 0x{ST_SIG_OFF:X} の命令列が不正です。"
            "改造ROM/異版/破損の可能性があるためパッチを中止します。")


def get_current(rom_data):
    """現在の (type, v) を返す"""
    return rom_data[TYPE_OFF], rom_data[STATE_OFF]


def current_preset_name(rom_data):
    """現在値に一致するプリセット名 (無ければ None)"""
    cur = (rom_data[TYPE_OFF], rom_data[STATE_OFF])
    for name, tv in PRESETS.items():
        if tv == cur:
            return name
    return None


def apply_preset(rom_data, preset_name):
    """プリセットを適用 (rom_data は bytearray)。検証付き。"""
    if preset_name not in PRESETS:
        raise ClearScreenHackError(f"未知のプリセット: {preset_name}")
    _validate(rom_data)
    ty, v = PRESETS[preset_name]
    rom_data[TYPE_OFF] = ty
    rom_data[STATE_OFF] = v
    return ty, v


def current_preset_id(rom_data):
    cur = (rom_data[TYPE_OFF], rom_data[STATE_OFF])
    for preset_id, preset in PRESET_DEFS.items():
        if (preset["type"], preset["state"]) == cur:
            return preset_id
    return None


def current_preset_name(rom_data):
    preset_id = current_preset_id(rom_data)
    if preset_id is None:
        return None
    return PRESET_DEFS[preset_id]["label"]


def apply_preset(rom_data, preset_id):
    """Apply a clear-screen preset by stable internal id."""
    if preset_id not in PRESET_DEFS:
        raise ClearScreenHackError(f"unknown clear-screen preset id: {preset_id}")
    _validate(rom_data)
    preset = PRESET_DEFS[preset_id]
    ty, v = preset["type"], preset["state"]
    rom_data[TYPE_OFF] = ty
    rom_data[STATE_OFF] = v
    return ty, v

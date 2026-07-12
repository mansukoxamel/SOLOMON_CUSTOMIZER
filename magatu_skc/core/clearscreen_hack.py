"""クリア画面 (THANK YOU DANA) の2体キャラ差し替え (位置+シグネチャ検証)

CLAUDE.md ルール準拠 / JP・US 同一 (ゲーム本編コード、再配置なし)。

ROM解析で確定 (Round 110/128/131/132, 全ROMバイト裏取り):
  action$14→$8EE4 が左右2体を生成 ($8F45-$8F68)。
    type   = file 0x0FBC ($8FAC, 既定 $1C=Fairy)
    state v= file 0x0F6D ($8F5D LDA #v, slot0=v*2 / slot1=v*2+1)
  status=$C0 なので共通物理 $8689 と共通アニメ $8789 は走るが、
  AI dispatch $87E0 は status>=$E0 条件のため走らない。
  ★ 安全性は「AIが走らない」だけでは決まらない。$8AC0 初期化時に
    type/state から速度テーブル $D9D3→$DB99/$DB9A を引くため、
    初期速度が 0,0 の隣接 state ペアだけをプリセット採用する。

確定プリセット (type, v) — 全て初期速度 0,0:
  Fairy(原作)  $1C / $0C  state24/25 羽ばたき
  Golem        $70 / $00  state0/1   固有歩行 3fループ
  Gargoyle(速) $78 / $00  state0/1   固有 2fループ
  Gargoyle(遅) $78 / $04  state8/9   固有 4fループ
  Saramandor   $5C / $06  state12/13 固有 idle 2fループ
  PanelMonster $24 / $00  state0/1   パネルモンスター
  Spark Ball   $28 / $00  state0/1   火球/スパーク
  Dragon       $68 / $00  state0/1   ドラゴン

補足:
  ROM上は速度ゼロの type/state 候補が他にも存在するが、グリッチ表示や
  別用途 state を含む。UIでは実画面で意味のある表示として確認済みの
  保守的なプリセットのみを出す。
"""

# 改造対象
TYPE_OFF = 0x0FBC      # $8FAC: クリア画面 entity type
STATE_OFF = 0x0F6D     # $8F5D: LDA #v (v=state base)

# シグネチャ (位置+パターン ダブル検証)
TBL_SIG_OFF = 0x0FBA   # $8FAA: 00 C0 1C FF 28 C8 (共通init+X座標)
TBL_SIG = bytes.fromhex("00 c0 1c ff 28 c8")
ST_SIG_OFF = 0x0F6C    # $8F5C: A9 0C 2A (LDA #v / ROL A)
ST_SIG = bytes.fromhex("a9 0c 2a")

class ClearScreenHackError(ValueError):
    """クリア画面改造の検証失敗"""


PRESET_DEFS = {
    "fairy_original": {"label": "Fairy (原作)", "type": 0x1C, "state": 0x0C},
    "golem": {"label": "Goblin", "type": 0x70, "state": 0x00},
    "gargoyle_fast": {"label": "Gargoyle (速い)", "type": 0x78, "state": 0x00},
    "gargoyle_slow": {"label": "Gargoyle (遅い)", "type": 0x78, "state": 0x04},
    "saramandor": {"label": "Saramandor", "type": 0x5C, "state": 0x06},
    "panel_monster": {"label": "Panel Monster", "type": 0x24, "state": 0x00},
    "spark_ball": {"label": "Spark Ball", "type": 0x28, "state": 0x00},
    "dragon": {"label": "Dragon", "type": 0x68, "state": 0x00},
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

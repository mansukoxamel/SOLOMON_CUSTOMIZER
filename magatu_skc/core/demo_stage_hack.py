"""デモプレイ(attract mode)のステージ変更 (位置 + シグネチャ ダブル検証方式)

CLAUDE.md ルール準拠:
  - JP/US 両対応。デモコードはタイトル/デモ領域 ($C400-$CFFF) =
    JP/US 再配置ゾーンのため、位置は JP/US 個別に特定済
  - 改造前に安定シグネチャを検証、失敗時 DemoStageHackError でパッチ中止

Codex解析 + ROMバイト裏取りで確定 (asm Round 113/135, 2026-05-16):
  タイトル放置で再生される ~24秒デモは既定で 3面 ($E08C/ROOM3)。
  $CBC0: LDX #$01 から X を使い回す連鎖:
    X=1   → STX $0433 / STX $80
    INX→2 → STX $0428  (デモ面 0-based。$0428=2 → ROOM3 = 3面) ★
    INX→3 → STX $042B (残機) / STX $0452
  デモ面 = $0428+1 (stage表示) = (LDX operand)+1+1 = operand+2。
  改造対象 = LDX operand 1バイト。stage = operand + 2。

制約 (X連鎖の罠):
  - operand >= 1 必須 (operand=0 だと $0433/$80=0 になる) → 最小 3面
  - 副作用: $0433(FW持続上限)/$80(次フレ上書き)/残機/$0452 が連動。
    デモは録画入力再生+タイマー終了で残機を消費しないため実害なし。
  - 録画入力は ROOM3 用。別面にすると Dana は録画通り動く=見た目で
    別面と分かる (デモ確認には十分。正規プレイには影響なし)。
"""

ORIG_OPERAND = 0x01   # 既定 (= 3面)
MIN_STAGE    = 3      # operand>=1 制約 (X連鎖)
MAX_STAGE    = 53     # $0428(0-based) 最大 room 52 → operand 51

# operand 直後の安定領域をシグネチャに使用 (改造対象バイト不含、
# JP/US でバイト列同一・位置のみ差、各ROMで一意確認済 2026-05-16)
_SIG = bytes.fromhex("8E 33 04 86 80 E8 8E 28 04 E8 8E 2B 04 8E 52 04")
_OFF = {
    "JP": {"operand": 0x4BD1, "sig_off": 0x4BD2, "sig": _SIG},
    "US": {"operand": 0x4B20, "sig_off": 0x4B21, "sig": _SIG},
}


class DemoStageHackError(ValueError):
    """デモステージ改造の検証失敗"""


def detect_region(rom_data) -> str:
    for region, o in _OFF.items():
        end = o["sig_off"] + len(o["sig"])
        if len(rom_data) < end:
            continue
        if bytes(rom_data[o["sig_off"]:end]) == o["sig"]:
            return region
    raise DemoStageHackError(
        "デモプレイのコードが見つかりません。\n"
        "改造ROM/拡張ROM/破損の可能性があるため改造を中止します。"
    )


def stage_to_operand(stage: int) -> int:
    """ステージ番号 → LDX operand ($03〜$35 にクランプ相当)"""
    stage = max(MIN_STAGE, min(MAX_STAGE, int(stage)))
    return stage - 2


def operand_to_stage(operand: int) -> int:
    """LDX operand → ステージ番号"""
    return operand + 2


def current_stage(rom_data) -> int:
    region = detect_region(rom_data)
    return operand_to_stage(rom_data[_OFF[region]["operand"]])


def apply(rom_data, stage: int) -> list:
    """デモのステージを変更。検証 → 書込。変更項目リストを返す"""
    region = detect_region(rom_data)
    o = _OFF[region]
    op = stage_to_operand(stage)
    if rom_data[o["operand"]] != op:
        rom_data[o["operand"]] = op
        return [f"デモプレイ→{operand_to_stage(op)}面 (operand${op:02X})"]
    return []


def restore(rom_data) -> list:
    """既定 (3面) に復元"""
    region = detect_region(rom_data)
    o = _OFF[region]
    if rom_data[o["operand"]] != ORIG_OPERAND:
        rom_data[o["operand"]] = ORIG_OPERAND
        return ["デモプレイ→既定 (3面)"]
    return []

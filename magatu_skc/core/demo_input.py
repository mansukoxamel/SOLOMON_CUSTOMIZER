"""デモ(attract mode)操作データ編集 (固定34step・原作方式・データ上書き)

タイトル放置で流れるデモは ROM 内の固定入力 34step を $03E4(JOY1)へ
注入して Dana を動かす方式 (asm R136/R183、docs)。録画不要で、原作の
記述方式そのまま (各 step = 入力 + 継続フレーム) を手編集する。

フォーマット (asm R183 / Codex 照合確定):
  $CF9A wait表 34B / $CFBC joy表 34B / step数 $CBF6=34(固定)
  ★実効フレーム = wait+1 (再生ループは $CF9A[X]>=$22 待機、$22>wait
    で進む)。∴ UI「Nフレーム」 ⇔ ROM wait = N-1。
  joy = NES JOY1 bit: A=$80 B=$40 上=$08 下=$04 左=$02 右=$01。
  ★Start($10)/Select($20) は再生中断判定 → デモ操作に入れない
    (write 時に $30 を強制マスクして安全化)。

JP file offset (デモ領域 $C400-$CFFF は US 再配置ゾーン=別offset。
本モジュールは JP 専用、US は署名不一致で安全中止):
  wait  $CF9A  file 0x4FAA  (34B)
  joy   $CFBC  file 0x4FCC  (34B)
  step数 $CBF6 file 0x4C06  (=34)
  署名  $CBEC  file 0x4BFC  (26B, 再生ループ核。テーブル絶対番地含み一意)

CLAUDE.md準拠: (A)位置 + (B)署名 二重検証、不一致は DemoInputError
で中止 (フォールバック禁止)。原作テーブルを同サイズ上書き(cave不要)。
"""

OFF_WAIT     = 0x4FAA
OFF_JOY      = 0x4FCC
OFF_STEPCNT  = 0x4C06
STEPS        = 34
OFF_SIG      = 0x4BFC
SIG          = bytes.fromhex(
    "a681bd9acfc522b0ede022b00ebdbccf8de403e681a9008522f0")  # 26B

# 原作 34step (clean JP 実ROM裏取り 2026-05-18)
ORIG_WAIT = bytes.fromhex(
    "c0208080203040200308201020102010682010402018102020188018202020200320")
ORIG_JOY = bytes.fromhex(
    "000040000201800900098901800180018401008001048600020002800a800a000a00")
assert len(ORIG_WAIT) == STEPS and len(ORIG_JOY) == STEPS

# 入力ビット (Start/Select はデモ操作不可)
BTN = [("A", 0x80), ("B", 0x40), ("上", 0x08), ("下", 0x04),
       ("左", 0x02), ("右", 0x01)]
JOY_VALID_MASK = 0x80 | 0x40 | 0x08 | 0x04 | 0x02 | 0x01  # = $CF


class DemoInputError(ValueError):
    """デモ操作編集の検証失敗 (改造ROM/拡張ROM/US/破損の可能性)"""


def _verify(rom_data) -> None:
    """(A)位置 + (B)署名 二重検証。失敗時 DemoInputError"""
    if len(rom_data) < OFF_JOY + STEPS:
        raise DemoInputError(
            f"ROM が小さすぎます (len={len(rom_data)})。デモ操作編集を中止。"
        )
    if bytes(rom_data[OFF_SIG:OFF_SIG + len(SIG)]) != SIG:
        raise DemoInputError(
            "$CBEC 署名不一致。改造ROM/拡張ROM/US版/破損の可能性が"
            "あるためデモ操作編集を中止します(本機能は JP 専用)。"
        )
    if rom_data[OFF_STEPCNT] != STEPS:
        raise DemoInputError(
            f"$CBF6 ステップ数が {rom_data[OFF_STEPCNT]} (期待 {STEPS})。"
            "改造ROM/破損の可能性があるため中止します。"
        )


def read_steps(rom_data) -> list:
    """34step を [(joy, frames), ...] で返す。frames = wait+1。検証付き。"""
    _verify(rom_data)
    out = []
    for i in range(STEPS):
        wait = rom_data[OFF_WAIT + i]
        joy = rom_data[OFF_JOY + i] & JOY_VALID_MASK
        out.append((joy, wait + 1))
    return out


def is_modified(rom_data) -> bool:
    _verify(rom_data)
    return (bytes(rom_data[OFF_WAIT:OFF_WAIT + STEPS]) != ORIG_WAIT or
            bytes(rom_data[OFF_JOY:OFF_JOY + STEPS]) != ORIG_JOY)


def write_steps(rom_data, steps: list) -> list:
    """[(joy, frames), ...] 34件を ROM へ。wait=frames-1, joyは$30除去。
    検証→書込。戻り値=変更説明。検証失敗/件数不正は DemoInputError。"""
    _verify(rom_data)
    if len(steps) != STEPS:
        raise DemoInputError(f"step 数不正 ({len(steps)} != {STEPS})。")
    w = bytearray(STEPS)
    j = bytearray(STEPS)
    for i, (joy, frames) in enumerate(steps):
        fr = max(1, min(256, int(frames)))
        w[i] = (fr - 1) & 0xFF                  # 実効=wait+1
        j[i] = int(joy) & JOY_VALID_MASK        # Start/Select 強制除去
    changed = []
    if bytes(rom_data[OFF_WAIT:OFF_WAIT + STEPS]) != bytes(w):
        rom_data[OFF_WAIT:OFF_WAIT + STEPS] = bytes(w)
        changed.append("デモ wait表 ($CF9A) 更新")
    if bytes(rom_data[OFF_JOY:OFF_JOY + STEPS]) != bytes(j):
        rom_data[OFF_JOY:OFF_JOY + STEPS] = bytes(j)
        changed.append("デモ joy表 ($CFBC) 更新")
    return changed


def restore(rom_data) -> list:
    """原作 34step へ完全復元"""
    _verify(rom_data)
    changed = []
    if bytes(rom_data[OFF_WAIT:OFF_WAIT + STEPS]) != ORIG_WAIT:
        rom_data[OFF_WAIT:OFF_WAIT + STEPS] = ORIG_WAIT
        changed.append("デモ wait表 → 原作復元")
    if bytes(rom_data[OFF_JOY:OFF_JOY + STEPS]) != ORIG_JOY:
        rom_data[OFF_JOY:OFF_JOY + STEPS] = ORIG_JOY
        changed.append("デモ joy表 → 原作復元")
    return changed

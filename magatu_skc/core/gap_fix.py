"""原作バグ回避: 落下中の横穴侵入を安定化 (グローバル / 位置+署名検証)

ソロモンの鍵 積年の謎「落下中に左/右を入れて横穴に入れる時と入れ
ない時がある(運ゲー)」を回避する改造。Mesen実機解析(asm R182,
docs/gap_entry_mechanism.html)で原因を確定:
  衝突マスク $058A(col) は $877F-$8786 で4隅SOLIDから確定保存され、
  col bit0=位相依存の左ブロック / bit1=右ブロック。落下中は hitbox
  (縦12px) が壁リップと横穴開口(16px)の境界をまたぎ、上隅が壁に
  1pxでも掛かると弾かれる。揃うかは落下サブピクセル位相依存=制御
  不能=運ゲー。

回避方法(実機 v8 成功確定・副作用なし):
  $8784(`A0 0B 91`=LDY#$0B/STA($08),Y先頭)を JMP cave に差替。
  cave: 落下中(state idx∈{6,2}) かつ 方向保持($03E4: 左$02/右$01)
  かつ ★その方向の縁セルがSOLID(壁)& 直下セル(index+$10)が非SOLID
  (横穴開口) の時だけ、col の bit0(左)/bit1(右) をクリアして保存。
  普通の壁(直下も壁)は無改変=原作どおり(ソフトロック等の副作用無)。
  速度($86D4/Xvel)・衝突リゾルバ・グリッド 一切非改変。
  グリッドindex は R182確定の asm 実式
  ((DanaY-13)&$F0)|((Xedge)>>4)、+$10=直下行 で算出(推測ゼロ)。

CLAUDE.md準拠: (A)位置 + (B)署名 二重検証、不一致は GapFixError で
中止(フォールバック禁止)。署名は改造対象を含まない安定並び。
注入先 $8784/$877F は本編コード=JP/US同一だが region 非依存で毎回検証。

ROM file offset (clean JP / 拡張ROM 共通。expander verbatim):
  file = 0x10 + (cpu - 0x8000)
  $8784 フック  file 0x0794  "A0 0B 91" -> "4C 79 E8" (JMP $E879)
  $877F 署名    file 0x078F  "A5 0A 6A 6A 6A"
  cave $E879    file 0x6889  (136B、RoomFlag packed cave runtime直後24Bを
                              空けた後ろへ移動)
"""

OFF_HOOK   = 0x0794                       # $8784
OFF_SIG    = 0x078F                       # $877F
SIG        = bytes.fromhex("a5 0a 6a 6a 6a")
ORIG       = bytes.fromhex("a0 0b 91")    # LDY #$0B / STA ($08),Y 先頭
HOOK       = bytes.fromhex("4c 79 e8")    # JMP $E879
OFF_CAVE   = 0x6889                       # $E879

# v8 実機成功確定 cave (位置独立=内部絶対JMP無し、$E879へ配置)
CAVE = bytes.fromhex(
 "48ad82054a4a2907c906f004c902d072a9ff850bade4032902f02c"
 "ad890538e9044a4a4a4a850cad860538e90d29f0050ca8b90403101098186910a8"
 "b904033006a50b29fe850b"
 "ade4032901f02c"
 "ad89051869034a4a4a4a850cad860538e90d29f0050ca8b90403101098186910a8"
 "b904033006a50b29fd850b"
 "68250ba00b91086068a00b910860"
)
assert len(CAVE) == 136

RESERVED_SPANS = (
    (OFF_HOOK, len(HOOK)),
    (OFF_CAVE, len(CAVE)),
)


class GapFixError(ValueError):
    """原作バグ回避(横穴侵入安定化)の検証失敗 (改造ROM/拡張ROM/破損)"""


def _verify(rom_data) -> None:
    """(A)位置 + (B)署名 二重検証。失敗時 GapFixError"""
    if len(rom_data) < OFF_CAVE + len(CAVE):
        raise GapFixError(
            f"ROM が小さすぎます (len={len(rom_data)})。横穴侵入安定化を中止。"
        )
    if bytes(rom_data[OFF_SIG:OFF_SIG + len(SIG)]) != SIG:
        raise GapFixError(
            "$877F 署名不一致。改造ROM/拡張ROM/破損の可能性があるため中止します。"
        )
    cur = bytes(rom_data[OFF_HOOK:OFF_HOOK + 3])
    if cur not in (ORIG, HOOK):
        raise GapFixError(
            f"$8784 が想定外 ({cur.hex()})。別改造と競合の可能性があるため中止します。"
        )
    # cave 空き: 原作(EA/00) または 既に本改造の cave のいずれか
    seg = bytes(rom_data[OFF_CAVE:OFF_CAVE + len(CAVE)])
    if seg != CAVE and not all(b in (0xEA, 0x00) for b in seg):
        raise GapFixError(
            "cave $E879 が空きでありません。別改造と競合の可能性があるため中止します。"
        )


def is_applied(rom_data) -> bool:
    _verify(rom_data)
    return bytes(rom_data[OFF_HOOK:OFF_HOOK + 3]) == HOOK


def apply(rom_data, enable: bool) -> list:
    """横穴侵入安定化を適用/解除。検証→書込。変更内容 list を返す。
    cave本体は保存ROM構造固定のため常に書く。
    enable=True: フック有効化 / False: フック原作復元。
    検証失敗は GapFixError (フォールバック禁止)。
    """
    _verify(rom_data)
    changed = []
    if bytes(rom_data[OFF_CAVE:OFF_CAVE + len(CAVE)]) != CAVE:
        rom_data[OFF_CAVE:OFF_CAVE + len(CAVE)] = CAVE
        changed.append("cave $E879 注入")
    if enable:
        if bytes(rom_data[OFF_HOOK:OFF_HOOK + 3]) != HOOK:
            rom_data[OFF_HOOK:OFF_HOOK + 3] = HOOK
            changed.append("$8784 フック有効化 (横穴侵入安定化)")
    else:
        # フックのみ原作復元。cave は死にコード化 (フック戻せば到達不能)
        if bytes(rom_data[OFF_HOOK:OFF_HOOK + 3]) != ORIG:
            rom_data[OFF_HOOK:OFF_HOOK + 3] = ORIG
            changed.append("$8784 フック→原作復元 (横穴侵入安定化 解除)")
    return changed

"""52/53面の呪文(Page = item $21)出現位置を ROM 直接書換で変更。

R188/R189 で確定した部屋別ハードコード特殊処理スクリプトの
`LDX #$XX`(grid cell index)オペランドを書き換える:

  面52 room$33 script $B5C8: LDX #$37 → file 0x35D9 (空間の呪文)
  面53 room$34 script $B5CC: LDX #$A7 → file 0x35DD (時の呪文)

(注: 空間/時間 の呼称はユーザーのゲーム知識による。$78 bit6/7 の
 振り分け自体は room しきい値依存=R189 [要確認] だが、本機能は
 「どのマスに Page を出すか」の位置のみを扱う。)

★JP のみ。US/US66 は当該コードの offset 未トレース → シグネチャ
不一致で自動的に未対応(無効化)になる。位置 + シグネチャ ダブル
検証、不一致は例外で中止(フォールバック禁止)。
clean JP / 自動拡張 JP66 共通(bank0 verbatim、同一 file offset)。
"""
from .element import position_from_byte, byte_from_position

OFF_S52 = 0x35D9   # 面52(空間の呪文) Page位置 = $B5C9 LDX オペランド
OFF_S53 = 0x35DD   # 面53(時の呪文)   Page位置 = $B5CD LDX オペランド
SIG_OFF = 0x35D8   # シグネチャ起点 ($B5C8)

# $B5C8: A2 ?? D0 02 A2 ?? A9 21 9D 04 03
#  ??(rel 1,5)=編集対象オペランド / それ以外は不変。$21=item Page。
_SIG_FIXED = {0: 0xA2, 2: 0xD0, 3: 0x02, 4: 0xA2,
              6: 0xA9, 7: 0x21, 8: 0x9D, 9: 0x04, 10: 0x03}
_SIG_LEN = 11

# 有効範囲: grid $0304-$03E3 (X=0..$DF)。byte=((y+1)&0xF)<<4 | (x&0xF)
X_MIN, X_MAX = 0, 15
Y_MIN, Y_MAX = 0, 12   # (y+1)<<4 が $D0 以下=grid内


class PagePosError(ValueError):
    pass


def _verify(rom_data) -> None:
    if SIG_OFF + _SIG_LEN > len(rom_data):
        raise PagePosError(
            "ROM が短すぎ(呪文位置スクリプト領域なし)。改造ROM/異版/破損")
    for rel, exp in _SIG_FIXED.items():
        got = rom_data[SIG_OFF + rel]
        if got != exp:
            raise PagePosError(
                f"ROM検証失敗: file 0x{SIG_OFF + rel:X} 期待 ${exp:02X} != "
                f"${got:02X}。改造ROM/異版/US版/破損の可能性があるため中止")


def is_supported(rom_data) -> bool:
    try:
        _verify(rom_data)
        return True
    except PagePosError:
        return False


def read_positions(rom_data):
    """((x52,y52),(x53,y53)) を返す。検証失敗は PagePosError。"""
    _verify(rom_data)
    return (position_from_byte(rom_data[OFF_S52]),
            position_from_byte(rom_data[OFF_S53]))


def _enc(pos):
    x, y = pos
    if not (X_MIN <= x <= X_MAX and Y_MIN <= y <= Y_MAX):
        raise PagePosError(
            f"位置 {pos} が範囲外 (x{X_MIN}-{X_MAX}/y{Y_MIN}-{Y_MAX})")
    return byte_from_position((x, y)) & 0xFF


def write_positions(rom_data, pos52, pos53) -> list:
    """面52/53 の呪文位置を書込。位置+シグネチャ ダブル検証。
    変更点の説明リストを返す。"""
    _verify(rom_data)
    changed = []
    b52, b53 = _enc(pos52), _enc(pos53)
    if rom_data[OFF_S52] != b52:
        rom_data[OFF_S52] = b52
        changed.append(f"52面 空間の呪文の位置 → {tuple(pos52)}")
    if rom_data[OFF_S53] != b53:
        rom_data[OFF_S53] = b53
        changed.append(f"53面 時の呪文の位置 → {tuple(pos53)}")
    return changed

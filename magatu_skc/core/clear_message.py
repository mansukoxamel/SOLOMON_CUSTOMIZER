"""クリア画面(おめでとう画面)3行メッセージ編集 (同字数・データ上書き)

ステージクリア後の "THANK YOU DANA" 等 3 行は通常フォント文字列では
なく PPU script (R135/R194)。$9471→$9488/$9495 ポインタ表→$1A/$1B→
NMI worker $8B7F が $2006/$2007 へ流す。script 形式:
  [PPU addr hi][PPU addr lo][control][文字tile...]00(終端)
文字tile: A=$0A B=$0B … Z=$23 / space=$24。

本モジュールは ★同字数置換 のみ(R135確定の安全方式)。各行の
ヘッダ3byte(PPU hi/lo・control)と終端$00 は不変、文字tile列だけを
同じ長さで差し替える(cave/ポインタ不要)。長さ変更は将来別途。

JP file offset (clean JP 実ROM裏取り 2026-05-18。3行連続配置):
  idx2 $94DB file 0x14EB  PPU$2168 ctrl$4D 14字 "THANK YOU DANA"
  idx3 $94ED file 0x14FD  PPU$21C4 ctrl$55 22字 "YOU RELEASED THIS ROOM"
  idx4 $9507 file 0x1517  PPU$2208 ctrl$4C 13字 "TRY NEXT ROOM"

CLAUDE.md準拠: (A)位置 + (B)署名(ヘッダ3byte+終端$00) 二重検証、
不一致は ClearMessageError で中止 (フォールバック禁止)。署名不一致で
US版/拡張別配置/改造ROM/破損は自動的に安全中止(JP前提)。
"""

# 各行: file offset(行頭), PPU addr, control, 文字数, 原作文字列
MESSAGES = [
    {"name": "1行目", "off": 0x14EB, "ppu": 0x2168, "ctrl": 0x4D,
     "count": 14, "orig": "THANK YOU DANA"},
    {"name": "2行目", "off": 0x14FD, "ppu": 0x21C4, "ctrl": 0x55,
     "count": 22, "orig": "YOU RELEASED THIS ROOM"},
    {"name": "3行目", "off": 0x1517, "ppu": 0x2208, "ctrl": 0x4C,
     "count": 13, "orig": "TRY NEXT ROOM"},
]

CHAR_MIN, CHAR_MAX = 0x0A, 0x23   # A..Z
SPACE_TILE = 0x24


class ClearMessageError(ValueError):
    """クリア画面メッセージ編集の検証失敗 (US/拡張別配置/改造/破損)"""


def _hdr(m):
    return bytes([(m["ppu"] >> 8) & 0xFF, m["ppu"] & 0xFF, m["ctrl"]])


def _verify(rom_data) -> None:
    """(A)位置 + (B)署名(ヘッダ3byte + 終端$00 + 現文字tile妥当) 二重検証"""
    last = MESSAGES[-1]
    need = last["off"] + 3 + last["count"] + 1
    if len(rom_data) < need:
        raise ClearMessageError(
            f"ROM が小さすぎます (len={len(rom_data)})。編集を中止。")
    for m in MESSAGES:
        o = m["off"]
        if bytes(rom_data[o:o + 3]) != _hdr(m):
            raise ClearMessageError(
                f"{m['name']} のヘッダ署名不一致 (file 0x{o:X})。"
                "US版/拡張別配置/改造ROM/破損の可能性があるため中止"
                "(本機能は JP 専用・同字数置換)。")
        term = rom_data[o + 3 + m["count"]]
        if term != 0x00:
            raise ClearMessageError(
                f"{m['name']} の終端($00)不一致 (file 0x{o + 3 + m['count']:X}"
                f" = ${term:02X})。改造ROM/破損の可能性ゆえ中止。")
        for k in range(m["count"]):
            t = rom_data[o + 3 + k]
            if not (CHAR_MIN <= t <= CHAR_MAX or t == SPACE_TILE):
                raise ClearMessageError(
                    f"{m['name']} に未知の文字tile ${t:02X} (file "
                    f"0x{o + 3 + k:X})。改造ROM/破損の可能性ゆえ中止。")


def _tile_to_ch(t: int) -> str:
    if t == SPACE_TILE:
        return " "
    return chr(ord("A") + (t - CHAR_MIN))


def _ch_to_tile(c: str) -> int:
    if c == " ":
        return SPACE_TILE
    return CHAR_MIN + (ord(c) - ord("A"))


def is_supported(rom_data) -> bool:
    try:
        _verify(rom_data)
        return True
    except ClearMessageError:
        return False


def read_messages(rom_data) -> list:
    """[(name, 現在文字列, 最大文字数, 原作文字列), ...] (3件)。検証付き。"""
    _verify(rom_data)
    out = []
    for m in MESSAGES:
        o = m["off"] + 3
        s = "".join(_tile_to_ch(rom_data[o + k]) for k in range(m["count"]))
        out.append((m["name"], s, m["count"], m["orig"]))
    return out


def is_modified(rom_data) -> bool:
    _verify(rom_data)
    for (_, cur, _cnt, orig) in read_messages(rom_data):
        if cur.rstrip() != orig:
            return True
    return False


def _encode_line(m, text: str) -> bytes:
    """text(A-Z/space, 大文字化) を count 長の tile 列へ。
    count未満は space 詰め。超過/不正文字は ClearMessageError。"""
    t = (text or "").upper()
    for c in t:
        if not (c == " " or "A" <= c <= "Z"):
            raise ClearMessageError(
                f"{m['name']}: 使えない文字 {c!r}。英大文字 A-Z と"
                "スペースのみ(同字数置換ゆえ長さは最大"
                f"{m['count']}字)。")
    if len(t) > m["count"]:
        raise ClearMessageError(
            f"{m['name']}: {len(t)}字は長すぎます(最大 {m['count']}字、"
            "同字数置換のため)。")
    t = t.ljust(m["count"], " ")          # 不足分は space 詰め(固定長)
    return bytes(_ch_to_tile(c) for c in t)


def write_messages(rom_data, texts: list) -> list:
    """texts=3行の文字列。各行を同字数で in-place 書込。検証→書込。
    戻り値=変更説明。検証失敗/不正は ClearMessageError。"""
    _verify(rom_data)
    if len(texts) != len(MESSAGES):
        raise ClearMessageError(
            f"行数不正 ({len(texts)} != {len(MESSAGES)})。")
    enc = [_encode_line(MESSAGES[i], texts[i]) for i in range(len(MESSAGES))]
    changed = []
    for i, m in enumerate(MESSAGES):
        o = m["off"] + 3
        if bytes(rom_data[o:o + m["count"]]) != enc[i]:
            rom_data[o:o + m["count"]] = enc[i]
            changed.append(f"クリア画面 {m['name']} 更新")
    return changed


def restore(rom_data) -> list:
    """3行を原作文字列へ復元"""
    return write_messages(rom_data, [m["orig"] for m in MESSAGES])

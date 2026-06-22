"""タイトル画面 抽出 / 差し替え (R196)

ソロモンの鍵のタイトル画面は単純なビットマップではなく
  ・CHR bank3 = ロゴ/バナーの 8x8 タイル絵 (8KB)
  ・$CBB3..$CEF1 ($C4xx) = 描画ルーチン + nametable + attribute + palette
の組み合わせ (romhack "Title Screen v1-1" の README / 実 dump / R196)。

★著作権方針 (ユーザー 2026-05-18):
  Nintendo graphics も特定 romhack の中身も Solomon Customizer に
  ハードコード/埋め込みしない。本モジュールがやるのは
   (a) ユーザー所有 ROM から CHR bank3 を抽出 (プレビュー/画像保存)
   (b) ユーザー所有 ROM 同士でタイトル領域を差し替え (JP↔US 等)
   (c) ユーザーが持つ .ips の汎用適用 (core/ips.apply_ips_patch)
  のみ。

★ROM 表現に依存しない設計:
  本アプリは読込時に通常 ROM(mapper3 65552) を拡張 ROM(mapper66
  98320) へ自動変換する (m66_expander)。拡張後も file 16..32783 の
  PRG は verbatim 保持されるため $CBB3..$CEF1 = file 0x4BC3..0x4F01
  は生/拡張で不変。一方 CHR は再配置されるため CHR 開始位置は
  iNES ヘッダから `16 + rom[4]*0x4000` で動的算出する
  (生 mapper3 → 0x8010 / 拡張 mapper66 → 0x10010)。

CLAUDE.md 絶対則: 位置 + 署名 二重検証、両 ROM 一致時のみ差替許可、
不一致は TitleScreenError で中止 (フォールバック禁止)。
"""
from . import region as region_mod
from . import ips as ips_mod
from ..nes.tile import load_chr_tiles, NES_GFX_TILE_BYTE_SIZE

# --- 領域定数 (clean iNES; file = 16B header 込み) ---
INES_MAGIC = b"NES\x1a"
CHR_BANK_SIZE = 0x2000          # 8KB / bank
TITLE_CHR_BANK = 3              # タイトル/ロゴが入る CHR bank
TILES_PER_BANK = CHR_BANK_SIZE // NES_GFX_TILE_BYTE_SIZE  # 512

# タイトル描画ルーチン/nametable/attribute/palette (CPU $CBB3..$CEF1)
#   romhack "Title Screen v1-1" の PRG パッチ全域を内包する連続塊。
#   テキスト微修正 ($9295/$95xx/$BExx) は「タイトル本体」ではないので
#   差し替え単位には含めない (IPS 適用に委ねる)。
TITLE_PRG_OFF = 0x4BC3          # = 0x10 + ($CBB3 - 0x8000)
TITLE_PRG_END = 0x4F01          # = 0x10 + ($CEF1 - 0x8000) (排他)
TITLE_PRG_LEN = TITLE_PRG_END - TITLE_PRG_OFF   # 830B

SUPPORTED_REGIONS = ("JP", "US", "JP66", "US66")
_INTERNAL_WIDE_BOOT_OFF = 0x10 + (0xCC4F - 0x8000)
_INTERNAL_WIDE_BOOT_SIG = bytes.fromhex("A20DBD5DCC9DC003CA10F74CC003")


class TitleScreenError(ValueError):
    """タイトル画面 抽出/差替 の検証失敗 (非対応 ROM / 破損 / 異版)"""


def _ines(rom_data):
    """iNES ヘッダから (prg_bytes, chr_banks, chr_start) を返す。検証付き。"""
    if len(rom_data) < 16 or bytes(rom_data[:4]) != INES_MAGIC:
        raise TitleScreenError(
            "iNES ヘッダがありません。Solomon's Key の ROM ではない"
            "可能性があるため中止 (フォールバック禁止)。")
    prg_units = rom_data[4]          # 16KB 単位
    chr_units = rom_data[5]          # 8KB 単位
    prg_bytes = prg_units * 0x4000
    chr_start = 16 + prg_bytes
    return prg_bytes, chr_units, chr_start


def _verify(rom_data) -> str:
    """(A)位置=iNES構造 + (B)署名=region判定 二重検証。region 名を返す。

    対応: JP / US / JP66 / US66 (本アプリ拡張)。EU・別ゲーム・破損は中止。
    """
    prg_bytes, chr_units, chr_start = _ines(rom_data)
    # (A) 位置: PRG=32KB(mapper3) または 64KB(mapper66 拡張) のみ
    if prg_bytes not in (0x8000, 0x10000):
        raise TitleScreenError(
            f"PRG サイズが想定外 ({prg_bytes}B)。Solomon's Key の "
            "通常/拡張 ROM ではないため中止。")
    # (A) CHR bank3 が ROM 内に収まるか
    if chr_units < TITLE_CHR_BANK + 1:
        raise TitleScreenError(
            f"CHR バンク数不足 ({chr_units} < {TITLE_CHR_BANK + 1})。"
            "タイトル CHR bank3 が存在しないため中止。")
    b3 = chr_start + TITLE_CHR_BANK * CHR_BANK_SIZE
    if b3 + CHR_BANK_SIZE > len(rom_data):
        raise TitleScreenError(
            f"CHR bank3 が ROM 範囲外 (need 0x{b3 + CHR_BANK_SIZE:X}, "
            f"len 0x{len(rom_data):X})。破損の可能性ゆえ中止。")
    if TITLE_PRG_END > len(rom_data):
        raise TitleScreenError("タイトル PRG 領域が ROM 範囲外。中止。")
    if (prg_bytes == 0x10000 and
            _INTERNAL_WIDE_BOOT_OFF + len(_INTERNAL_WIDE_BOOT_SIG) <= len(rom_data) and
            bytes(rom_data[_INTERNAL_WIDE_BOOT_OFF:
                           _INTERNAL_WIDE_BOOT_OFF + len(_INTERNAL_WIDE_BOOT_SIG)])
            == _INTERNAL_WIDE_BOOT_SIG):
        return "JP66"
    # (B) 署名: region 判定 (JP/US/拡張のみ)。対応外は弾く。
    try:
        region = region_mod.detect_region(bytes(rom_data))
    except ValueError as e:
        raise TitleScreenError(
            f"対応外の ROM です ({e})。本機能は Solomon's Key "
            "JP/US (および本アプリ拡張) 専用です。")
    if region not in SUPPORTED_REGIONS:
        raise TitleScreenError(
            f"対応外 region '{region}'。JP/US のみサポート。")
    return region


def chr_bank3_offset(rom_data) -> int:
    """この ROM 表現での CHR bank3 の file オフセット (生/拡張両対応)。"""
    _prg, _cu, chr_start = _ines(rom_data)
    return chr_start + TITLE_CHR_BANK * CHR_BANK_SIZE


def is_supported(rom_data) -> bool:
    try:
        _verify(rom_data)
        return True
    except TitleScreenError:
        return False


def region_of(rom_data) -> str:
    """対応 region を返す (検証付き)。非対応は TitleScreenError。"""
    return _verify(rom_data)


def get_chr_bank3_tiles(rom_data) -> list:
    """タイトル CHR bank3 の 512 タイル (NesTile) を返す。検証付き。

    描画は ui 側で実施 (グレー4階調; palette 未確定ゆえ推測しない)。
    """
    _verify(rom_data)
    off = chr_bank3_offset(rom_data)
    return load_chr_tiles(bytes(rom_data), off, TILES_PER_BANK)


def import_chr_bank3(target_rom, source_rom) -> list:
    """★タイトル画像移植 (本機能の主役): source の CHR bank3 を
    target の CHR bank3 へ ★まるごとコピー (8KB)。

    - IPS でも CRC 一致要求でもない。既知ブロックの単純コピー。
      ROM 全体パッチではないので CRC は ★無関係 (要求しない)。
    - CHR bank3 の file 位置は iNES ヘッダから動的算出
      (通常 0xE010 / 本アプリ拡張ROM 0x16010)。CHR は PRG の後ろ
      固定ゆえ JP/US 同 offset → US↔JP どちらの向きでも同じ要領。
    - 安全確認は CRC でなく ★位置+署名 (両 ROM で _verify)。
      非対応/破損は TitleScreenError で中止 (フォールバック禁止)。
    - ★リージョン一致は要求しない (US→JP / JP→US 双方を許可。
      画像=タイル絵だけの移植。配置/色は PRG 側=将来拡張)。

    戻り値=変更説明リスト。
    """
    dst_region = _verify(target_rom)
    src_region = _verify(source_rom)
    dst_off = chr_bank3_offset(target_rom)
    src_off = chr_bank3_offset(source_rom)
    if src_off + CHR_BANK_SIZE > len(source_rom):
        raise TitleScreenError("移植元 ROM の CHR bank3 が範囲外。中止。")
    if dst_off + CHR_BANK_SIZE > len(target_rom):
        raise TitleScreenError("移植先 ROM の CHR bank3 が範囲外。中止。")
    block = bytes(source_rom[src_off:src_off + CHR_BANK_SIZE])
    if bytes(target_rom[dst_off:dst_off + CHR_BANK_SIZE]) == block:
        return [f"移植元({src_region})と CHR bank3 が同一 (変更なし)。"]
    target_rom[dst_off:dst_off + CHR_BANK_SIZE] = block
    return [
        f"タイトル画像 CHR bank3 を {src_region} → {dst_region} へ移植 "
        f"(dst 0x{dst_off:X} ← src 0x{src_off:X}, {CHR_BANK_SIZE}B)。"
        " ※配置/色(PRG側)は各版のまま (将来拡張)。"]


# ============================================================
# タイトル画面トランスコード (R198 完全解明・三重裏取り)
# ============================================================
# タイトル= RLE 圧縮ピースの集合。デコーダ $CC4F(JP)/$CBA6(US) は
# 同一エンジン → ★ピース単位 verbatim コピーで US↔JP 相互移植
# (デコード/エンコード/コードコピー 不要、各版描画コードが自分の
#  位置のデータを読む)。JP/US で nametable は ★長さ完全同一
# (A155B/144w + B247B/233w = 連続402B)・内容のみ差ゆえ安全。
#
# clean 65552 file offset。nametable/attribute は PRG 領域
# (<0x8010) ゆえ mapper66 拡張後も verbatim 保持で ★同 file offset。
# CHR bank3 のみ chr_bank3_offset() で動的算出 (生0xE010/拡張0x16010)。
_TITLE_PIECES = {
    "JP": {"nametable": (0x4E18, 402), "attribute": (0x4D68, 21)},
    "US": {"nametable": (0x4D6F, 402), "attribute": (0x4CBF, 21)},
}
# 補足: パレットは小片が散在 ($CDF5 等) し全特定が未完ゆえ v1 では
# 移植対象外 (移植先の元パレットを使用=自己整合)。色精緻化は後日。


def _decode_cc4f(rom, start):
    """SUB_CC4F ($CC4F JP / $CBA6 US) を 6502 命令忠実に再現。
    1 ブロック (終端 $7F) を処理し ([(ppu_addr, tile), ...], end_off)。
    キャリーまで再現 ($60-7E の ADC は CPX#$60 で C=1 / PPUADDR の
    ROR は 2nd LSR のキャリーを引き継ぐ) → 静的導出ミスを排除。
    """
    P = start
    c2 = 0
    c3 = 0
    Y = 0xFF                  # CC52 LDY#0 ; CC58 DEY
    C = 0
    out = []
    addr = 0
    g = 0

    def consume(b, Pv, Yv):
        # CC5E: P += Y ; Y=0 ; 値域ディスパッチ。戻り (P,Y,c2,c3,done)
        Pn = Pv + Yv
        nonlocal c2, c3
        if b < 0x40:                       # CC87 $02=b
            c2 = b
        elif b < 0x60:                     # CC83 $03=b
            c3 = b
        else:
            if b == 0x7F:                  # CC74 INX→$80 BMI→RTS
                return Pn, 0, True
            c3 = (b & 0x1F) + c3 + 1       # CC7B AND#$1F / CC7D ADC$03
            c3 &= 0xFF                     #   (C=1 ← CC70 CPX#$60)
        return Pn, 0, False

    state = "CMD"
    while True:
        g += 1
        if g > 20000:
            return out, P + Y              # 安全弁
        if state == "CMD":
            Y = (Y + 1) & 0xFF             # CC59 INY
            b = rom[P + Y]                 # CC5A LDA (P),Y
            if b >= 0x80:                  # CC5C BMI CC8B
                X = c3                     # CC8B LDX $03
                v = (X + 0x10) & 0x1FF     # ADC #$10 (CLC前)
                # LSR ; LSR  → C = bit1 of v
                C = (v >> 1) & 1
                a = (v >> 2) & 0xFF
                hi = (a & 0x2B) | 0x20     # AND#$2B ORA#$20
                # TXA ; ROR ROR ROR (through C)
                a = X
                for _ in range(3):
                    nC = a & 1
                    a = ((a >> 1) | (C << 7)) & 0xFF
                    C = nC
                lo = (a & 0xC0) | c2       # AND#$C0 ORA $02
                addr = (hi << 8) | lo
                Y = (Y - 1) & 0xFF         # CCAB DEY
                state = "RUN"
                continue
            P, Y, done = consume(b, P, Y)  # CC5E
            if done:
                return out, P + 1
            continue
        else:                              # RUN (CCAC)
            Y = (Y + 1) & 0xFF             # CCAC INY
            b = rom[P + Y]                 # CCAD LDA (P),Y
            if b < 0x80:                   # CCAF BPL CC5E
                P, Y, done = consume(b, P, Y)
                if done:
                    return out, P + 1
                state = "CMD"
                continue
            out.append((addr, b))          # CCB1 STA $2007
            addr += 1
            continue


# 表示用 nametable は 1KB ($2000) にミラー集約。32x30=960 セル
_NT_CELLS = 960
# bg パターンテーブル = CHR bank3 上位4KB (tiles 256-511、ロゴ域 R196)。
# ★UI 描画 (_BG_BASE) と必ず一致させること (export↔import 往復一致)
_BG_BASE = 256

# ===== Phase2: arcade形式 広域タイトル stream (R199 確定) =====
# stream = segment* / 終端 byte $2F
# segment = [HI][LO][tile≥$30...]   HI<$30($20-$2E)=PPUADDR上位,
#   LO=PPUADDR下位(任意), tile=$30-$FF を $2007 へ生連続
#   byte<$30 で run 終了→次segment ($2F なら終端)。空白は出さない
# ★設計ロック条件: $00-$2E=制御/HI, $2F=終端, $30-$FF=描画タイル
ARCADE_TERM = 0x2F
ARCADE_TILE_MIN = 0x30
ARCADE_NT_BASE = 0x2800        # arcade 実測 PPUADDR (cell→$2800+cell)
WIDE_TITLE_FREE_BANK_TILE_RANGES = (
    (0x12C, 0x139),
    (0x13C, 0x14F),
    (0x154, 0x17F),
    (0x180, 0x18F),
    (0x190, 0x197),
    (0x199, 0x19F),
    (0x1A9, 0x1A9),
    (0x1AC, 0x1AF),
    (0x1B8, 0x1BF),
    (0x1E0, 0x1FF),
)
WIDE_TITLE_FREE_STREAM_TILES = tuple(
    bank_tile - _BG_BASE
    for start, end in WIDE_TITLE_FREE_BANK_TILE_RANGES
    for bank_tile in range(start, end + 1)
)
TITLE_BLANK_STREAM_TILE = 0x24

# New internal wide-title stream.
# segment = [HI][LO][LEN][TILE...], end = $FF.
# LEN makes all following bytes tile IDs, so $00-$2F font tiles can be drawn
# without copying glyphs into CHR bank3 high slots.
LEN_STREAM_TERM = 0xFF


def decode_arcade_stream(rom_data, start_off: int, lim: int = 6000):
    """arcade形式 stream を解析 → [(ppu_addr, tile), ...]。
    R199 のルーチン意味論を忠実に再現 (検証/プレビュー用)。
    """
    P = start_off
    Y = 0
    out = []
    g = 0
    while g < lim:
        g += 1
        b = rom_data[P + Y]
        if b == ARCADE_TERM:                 # $2F 終端
            return out
        if b < ARCADE_TILE_MIN:              # segment header HI
            hi = b
            lo = rom_data[P + Y + 1]
            addr = (hi << 8) | lo
            P = P + Y + 2
            Y = 0
            while rom_data[P + Y] >= ARCADE_TILE_MIN:   # tile run
                out.append((addr, rom_data[P + Y]))
                addr += 1
                Y += 1
            continue                         # 次 byte<$30 = 次segment
        return out                           # 想定外=安全停止
    return out


def encode_arcade_stream(cells, base: int = ARCADE_NT_BASE) -> bytes:
    """中間グリッド(960, tile値 or None=空白) → arcade形式 stream。
    非空白の連続runごとに [HI][LO][tiles...]、末尾 $2F。
    ★$30-$FF 規則を強制 (タイル外/$2F は不可 → TitleScreenError)。
    """
    if len(cells) != _NT_CELLS:
        raise TitleScreenError(
            f"cells 数不正 ({len(cells)} != {_NT_CELLS})。")
    out = bytearray()
    i = 0
    while i < _NT_CELLS:
        v = cells[i]
        if v is None:                        # 空白=出力しない
            i += 1
            continue
        run = i
        while i < _NT_CELLS and cells[i] is not None:
            i += 1
        addr = base + run
        hi = (addr >> 8) & 0xFF
        lo = addr & 0xFF
        if hi >= ARCADE_TILE_MIN or hi == ARCADE_TERM:
            raise TitleScreenError(
                f"PPUADDR HI ${hi:02X} が制御域外 (base/配置不正)。")
        out.append(hi)
        out.append(lo)
        for c in range(run, i):
            t = cells[c]
            if not (ARCADE_TILE_MIN <= t <= 0xFF):
                raise TitleScreenError(
                    f"タイル値 ${t:02X} は $30-$FF 範囲外 "
                    f"(cell {c})。$00-$2F はタイル不可 (設計ロック"
                    "条件)。CHRタイルIDを $30-$FF に割当てること。")
            out.append(t)
    out.append(ARCADE_TERM)
    return bytes(out)


def decode_len_stream(rom_data, start_off: int, lim: int = 6000):
    """LEN形式 wide stream を解析 → [(ppu_addr, tile), ...]。"""
    p = int(start_off)
    out = []
    g = 0
    while g < lim:
        g += 1
        if p >= len(rom_data):
            return out
        hi = rom_data[p]
        if hi == LEN_STREAM_TERM:
            return out
        if p + 2 >= len(rom_data):
            return out
        lo = rom_data[p + 1]
        count = rom_data[p + 2]
        if count == 0:
            return out
        p += 3
        addr = (hi << 8) | lo
        if p + count > len(rom_data):
            return out
        for i in range(count):
            out.append((addr + i, rom_data[p + i]))
        p += count
    return out


def encode_len_stream(cells, base: int = ARCADE_NT_BASE) -> bytes:
    """中間グリッド(960, tile値 or None=空白) → LEN形式 wide stream。"""
    if len(cells) != _NT_CELLS:
        raise TitleScreenError(
            f"cells 数不正 ({len(cells)} != {_NT_CELLS})。")
    out = bytearray()
    i = 0
    while i < _NT_CELLS:
        if cells[i] is None:
            i += 1
            continue
        run = i
        while i < _NT_CELLS and cells[i] is not None:
            i += 1
        while run < i:
            chunk_end = min(i, run + 255)
            addr = base + run
            hi = (addr >> 8) & 0xFF
            lo = addr & 0xFF
            if hi == LEN_STREAM_TERM:
                raise TitleScreenError(
                    f"PPUADDR HI ${hi:02X} はLEN stream終端と衝突します。")
            out.extend((hi, lo, chunk_end - run))
            for c in range(run, chunk_end):
                t = cells[c]
                if not (0 <= int(t) <= 0xFF):
                    raise TitleScreenError(
                        f"タイル値 ${int(t):02X} は $00-$FF 範囲外 (cell {c})。")
                out.append(int(t) & 0xFF)
            run = chunk_end
    out.append(LEN_STREAM_TERM)
    return bytes(out)


# 当方 wide デコーダ ($CC4F) の先頭署名 (LDY#0/LDA($00),Y/CMP#$2F)
_WA_DEC_SIG = bytes.fromhex("A000B100C92F")
_US_ARCADE_DEC_OFF = 0x10 + (0xCBA6 - 0x8000)
_US_ARCADE_DEC_SIG = bytes.fromhex("AC0220A000840284")
_US_ARCADE_ATTR_OFF = 0x10 + (0xCCAF - 0x8000)
_US_ARCADE_ATTR_LEN = 21


def _is_us_arcade_title_hack(rom_data) -> bool:
    if len(rom_data) < _US_ARCADE_DEC_OFF + len(_US_ARCADE_DEC_SIG):
        return False
    if bytes(rom_data[_US_ARCADE_DEC_OFF:
                      _US_ARCADE_DEC_OFF + len(_US_ARCADE_DEC_SIG)]) != \
            _US_ARCADE_DEC_SIG:
        return False
    try:
        return (len(decode_arcade_stream(rom_data, 0x10 + (0xCD5F - 0x8000)))
                >= 100 and
                len(decode_arcade_stream(rom_data, 0x10 + (0xCDF5 - 0x8000)))
                >= 150)
    except Exception:
        return False


def is_wide_normalized(rom_data) -> bool:
    """この ROM のタイトルが当方 wide 形式へ正規化済か。
      ・新機構 (RAM-trampoline): $CC4F = bootstrap (_WT_BOOT_SIG)
      ・旧 in-place (apply_wide_arcade_title): $CC4F = decoder
        (_WA_DEC_SIG)
    どちらでも True (decode_title_grid 側で機構を判別)。"""
    o = 0x10 + (0xCC4F - 0x8000)
    if _wt_has_ram_bootstrap(rom_data):
        return True
    return bytes(rom_data[o:o + len(_WA_DEC_SIG)]) == _WA_DEC_SIG


def decode_title_grid(rom_data) -> dict:
    """現 ROM のタイトル画面を実デコード。戻り:
       {"grid": [tile×960], "chr": chr_bank3_off, "region": base,
        "cells": 実書込セル数, "wide": bool}
    stock: nametable A→B を $CC4F 再現 (addr & $3FF)。
    wide正規化済: bank1 blockA/B streamを decoder形式に合わせてdecode。
    """
    region = _verify(rom_data)
    base = region_mod.base_region(region)

    # --- wide 正規化済ならそちらを decode (load時 自動正規化対応) ---
    if is_wide_normalized(rom_data):
        grid = [0x24] * _NT_CELLS
        fixed_live = [False] * _NT_CELLS
        _apply_wide_title_live_background_fill(grid, fixed_live)
        cells = 0
        o = _wjp_cf(0xCC4F)
        is_new = _wt_has_ram_bootstrap(rom_data)
        if is_new:
            # 新機構: blockA/B stream は ★bank1。caller の即値
            #   ポインタ ($CCBA/$CCBE, $CD84/$CD88) = bank1 CPU 番地。
            a_cpu = rom_data[_wjp_cf(_WT_PTRA_LO)] | \
                (rom_data[_wjp_cf(_WT_PTRA_HI)] << 8)
            b_cpu = rom_data[_wjp_cf(_WT_PTRB_LO)] | \
                (rom_data[_wjp_cf(_WT_PTRB_HI)] << 8)
            starts = [_wjp_b1f(cp) for cp in (a_cpu, b_cpu)
                      if 0x8000 <= cp <= 0xFFFF]
        else:
            # 旧 in-place: block2@$CEA3(bank0) + cave($CCBA/$CCBE,bank0)
            starts = [_wjp_cf(0xCEA3)]
            cave_cpu = rom_data[_wjp_cf(0xCCBA)] | \
                (rom_data[_wjp_cf(0xCCBE)] << 8)
            if 0x8000 <= cave_cpu <= 0xFFFF:
                starts.append(_wjp_cf(cave_cpu))
        for st in starts:
            decoder = decode_len_stream if _wt_uses_len_stream(rom_data) else decode_arcade_stream
            for ad, t in decoder(rom_data, st):
                idx = ad - ARCADE_NT_BASE
                if 0 <= idx < _NT_CELLS:
                    grid[idx] = t
                    fixed_live[idx] = False
                    cells += 1
        return {"grid": grid, "chr": chr_bank3_offset(rom_data),
                "region": base, "cells": cells, "wide": True}

    if base not in _TITLE_PIECES:
        raise TitleScreenError(f"region {base} 非対応。")
    nt_off, nt_len = _TITLE_PIECES[base]["nametable"]
    grid = [0x24] * _NT_CELLS              # $24=空白タイル
    cells = 0
    p = nt_off
    end_limit = nt_off + nt_len + 8
    for _blk in range(2):                  # block A, B
        w, end = _decode_cc4f(bytes(rom_data), p)
        for ad, t in w:
            idx = ad & 0x3FF
            if idx < _NT_CELLS:
                grid[idx] = t
                cells += 1
        if end <= p or end >= end_limit:
            break
        p = end
    return {"grid": grid, "chr": chr_bank3_offset(rom_data),
            "region": base, "cells": cells, "wide": False}


def _apply_wide_title_live_background_fill(grid, fixed_live=None):
    """Fill cells that the live title PPU leaves populated outside streams.

    Mesen live PPU logging confirmed NT $2800 row 28 is not blank: it uses
    $DF/$DE alternation for the orange floor band.  The wide-title stream does
    not explicitly write those cells, so a plain decoded stream grid otherwise
    shows $24 there and diverges from the emulator.
    """
    row = 28
    base = row * 32
    for col in range(32):
        idx = base + col
        grid[idx] = 0xDF if (col % 2) == 0 else 0xDE
        if fixed_live is not None:
            fixed_live[idx] = True


def _encode_2bpp(pix) -> bytes:
    """8x8 の palette index(0-3, row-major 64要素 or [8][8]) → NES 16B。
    NesTile デコードの厳密な逆 (plane0=bit0, plane1=bit1, MSB=x0)。"""
    if pix and isinstance(pix[0], (list, tuple)):
        rows = pix
    else:
        rows = [pix[i * 8:(i + 1) * 8] for i in range(8)]
    p0 = bytearray(8)
    p1 = bytearray(8)
    for y in range(8):
        a = b = 0
        r = rows[y]
        for x in range(8):
            v = r[x] & 3
            a |= (v & 1) << (7 - x)
            b |= ((v >> 1) & 1) << (7 - x)
        p0[y] = a
        p1[y] = b
    return bytes(p0) + bytes(p1)


def apply_title_image(rom_data, cells) -> list:
    """★PNG等から取り込み (export の逆): 画像から CHR bank3 を再構築。
    nametable(配置) は ROM のまま=圧縮再エンコード不要・枠超過の
    危険なし・往復厳密一致。

    cells: 960要素。各 = その画面マスの 8x8 palette index
           (0-3, 64要素 row-major)。UI が PNG を 256x240 / 4階調へ
           量子化して渡す。
    手順: 各マスの nametable タイル番号を decode_title_grid で取得 →
    同じタイル番号を使うマス群で最多パターンを採用 (食い違いは
    conflict として報告) → 2bpp化して CHR bank3 の該当タイルへ書込。
    戻り値=説明リスト。検証は decode 経由 (_verify 済)。
    """
    if len(cells) != _NT_CELLS:
        raise TitleScreenError(
            f"画像セル数不正 ({len(cells)} != {_NT_CELLS})。")
    info = decode_title_grid(rom_data)        # _verify 済
    grid = info["grid"]
    chr_off = info["chr"]
    # nametable タイル番号 → そのタイルを使う全マスのパターン
    from collections import Counter
    by_tile = {}
    for ci in range(_NT_CELLS):
        t = grid[ci]
        pat = tuple(int(v) & 3 for v in cells[ci])
        if len(pat) != 64:
            raise TitleScreenError(
                f"マス {ci} の画素数不正 ({len(pat)} != 64)。")
        by_tile.setdefault(t, []).append(pat)
    conflicts = 0
    written = 0
    for t, pats in by_tile.items():
        c = Counter(pats)
        best, n_best = c.most_common(1)[0]
        if len(c) > 1:
            conflicts += sum(v for p, v in c.items() if p != best)
        ti = (_BG_BASE + t) & 0x1FF            # 描画と同じ規則
        pos = chr_off + ti * 16
        if pos + 16 > len(rom_data):
            raise TitleScreenError(
                f"CHR タイル {ti} が ROM 範囲外。中止。")
        enc = _encode_2bpp(best)
        if bytes(rom_data[pos:pos + 16]) != enc:
            rom_data[pos:pos + 16] = enc
            written += 1
    msg = [f"画像から CHR bank3 を再構築: {len(by_tile)} タイル中 "
           f"{written} 更新 (nametable/配置は不変)。"]
    if conflicts:
        msg.append(
            f"※同一タイル番号を使う複数マスで絵が食い違うマスが "
            f"{conflicts} 個 → 各タイルは最多パターンを採用 "
            f"(export画像をそのまま編集すれば食い違いは出ません)。")
    return msg


def apply_title_stamp_cells(rom_data, patterns, start_row: int, start_col: int,
                            tile_w: int, tile_h: int) -> list:
    """Place an 8x8-tile image on the wide title using only free CHR slots."""
    if tile_w <= 0 or tile_h <= 0:
        raise TitleScreenError("貼り付け画像のタイル数が不正です。")
    if len(patterns) != tile_w * tile_h:
        raise TitleScreenError(
            f"貼り付け画像のセル数不正 ({len(patterns)} != {tile_w * tile_h})。")
    start_row = int(start_row)
    start_col = int(start_col)
    if start_row < 0 or start_col < 0 or \
            start_row + tile_h > 30 or start_col + tile_w > 32:
        raise TitleScreenError(
            f"貼り付け先が画面外です: x={start_col}, y={start_row}, "
            f"size={tile_w}x{tile_h} tiles。")

    grid_a, grid_b = _wide_title_grids_for_edit(rom_data)
    replace_cells = {
        (start_row + y) * 32 + (start_col + x)
        for y in range(tile_h)
        for x in range(tile_w)
    }
    used = {
        int(t) & 0xFF
        for ci in range(_NT_CELLS)
        if ci not in replace_cells
        for t in (grid_a[ci], grid_b[ci])
        if t is not None
    }
    available = [
        int(t) & 0xFF
        for t in WIDE_TITLE_FREE_STREAM_TILES
        if (int(t) & 0xFF) not in used
    ]

    pat_to_tile = {}
    next_tile = 0
    placed = 0
    blank = 0
    for y in range(tile_h):
        for x in range(tile_w):
            ci = (start_row + y) * 32 + (start_col + x)
            pat = tuple(int(v) & 3 for v in patterns[y * tile_w + x])
            if len(pat) != 64:
                raise TitleScreenError(
                    f"貼り付けマス ({x},{y}) の画素数不正 ({len(pat)} != 64)。")
            if all(v == 0 for v in pat):
                blank += 1
                grid_a[ci] = TITLE_BLANK_STREAM_TILE
                grid_b[ci] = None
                continue
            if pat not in pat_to_tile:
                if next_tile >= len(available):
                    raise TitleScreenError(
                        "自由CHR枠の空きが足りません。"
                        f"必要 {len(pat_to_tile) + 1} / 使用可能 {len(available)}。")
                pat_to_tile[pat] = available[next_tile]
                next_tile += 1
            grid_a[ci] = pat_to_tile[pat]
            grid_b[ci] = None
            placed += 1

    chr_off = chr_bank3_offset(rom_data)
    written = 0
    for pat, t in pat_to_tile.items():
        ti = (_BG_BASE + t) & 0x1FF
        pos = chr_off + ti * NES_GFX_TILE_BYTE_SIZE
        if pos + NES_GFX_TILE_BYTE_SIZE > len(rom_data):
            raise TitleScreenError(
                f"CHR タイル {ti} が ROM 範囲外。中止。")
        enc = _encode_2bpp(pat)
        if bytes(rom_data[pos:pos + NES_GFX_TILE_BYTE_SIZE]) != enc:
            rom_data[pos:pos + NES_GFX_TILE_BYTE_SIZE] = enc
            written += 1

    len_a, len_b = _write_wide_title_streams_for_import(
        rom_data, grid_a, grid_b)
    free_set = {int(t) & 0xFF for t in WIDE_TITLE_FREE_STREAM_TILES}
    used_free = {
        int(t) & 0xFF
        for ci in range(_NT_CELLS)
        for t in (grid_a[ci], grid_b[ci])
        if t is not None and (int(t) & 0xFF) in free_set
    }
    total_free = len(WIDE_TITLE_FREE_STREAM_TILES)
    used_free_count = len(used_free)
    return [
        f"貼り付け先: x={start_col}, y={start_row}, size={tile_w}x{tile_h} tiles",
        f"drawn cells: {placed} / blank cells: {blank}",
        f"unique tiles: {len(pat_to_tile)} / available free slots {len(available)}",
        f"自由CHR154枠: {used_free_count}/{total_free} 使用、残り {total_free - used_free_count}",
        f"CHR bank3 updated: {written} tiles",
        f"bank1 streams rewritten: A={len_a}B / B={len_b}B",
    ]


def apply_title_top_image_from_png(rom_data, cells) -> list:
    """Rebuild only the 256x64 top band from PNG pixels.

    This intentionally ignores the JSON sidecar and old tile sharing.  The PNG
    is treated as the source of truth: identical 8x8 patterns are shared, and
    different 8x8 patterns get different tile IDs.  Existing non-top title
    cells keep their stream placement and CHR tile IDs.
    """
    if len(cells) != _NT_CELLS:
        raise TitleScreenError(
            f"画像セル数不正 ({len(cells)} != {_NT_CELLS})。")
    if not is_wide_normalized(rom_data):
        raise TitleScreenError(
            "target ROM is not in the internal wide-title format. "
            "Open a JP ROM first so it is expanded and normalized.")

    top_start = _TITLE_TOP_ROW0 * 32
    top_end = (_TITLE_TOP_ROW0 + _TITLE_TOP_ROWS) * 32
    patterns = []
    for ci in range(top_start, top_end):
        pat = tuple(int(v) & 3 for v in cells[ci])
        if len(pat) != 64:
            raise TitleScreenError(
                f"マス {ci} の画素数不正 ({len(pat)} != 64)。")
        patterns.append(pat)
    msgs = apply_title_stamp_cells(
        rom_data, patterns, _TITLE_TOP_ROW0, 0, 32, _TITLE_TOP_ROWS)
    return [
        "Top PNG imported without JSON sidecar layout.",
        "PNG pixels are the source of truth; identical 8x8 tiles were shared.",
    ] + msgs


def transcode_title(target_rom, source_rom) -> list:
    """★タイトル相互移植 (本命): source のタイトルを target へ。

    リージョンを両 ROM で自動判定し、各版の ★対応ピース位置へ
    バイトを verbatim コピー:
      ・nametable (配置, 402B)  ・attribute (色区分, 21B)
      ・CHR bank3 (タイル絵, 8192B)
    コードは一切コピーしない (各版の描画コードが自分の位置の
    データを読むため、US↔JP どちらの向きでも崩れない)。

    JP/US で各ピースは ★同一長ゆえ超過不可能。位置+署名 二重検証、
    非対応/破損/長さ不一致は TitleScreenError で中止 (フォールバック
    禁止)。CRC は無関係 (既知ピースのコピーゆえ要求しない)。

    戻り値=変更説明リスト。
    """
    dst_region = _verify(target_rom)
    src_region = _verify(source_rom)
    db = region_mod.base_region(dst_region)
    sb = region_mod.base_region(src_region)
    if sb not in _TITLE_PIECES or db not in _TITLE_PIECES:
        raise TitleScreenError(
            f"タイトルピース表が無い region (src={sb}/dst={db})。"
            "JP/US のみ対応。中止。")
    src_t = _TITLE_PIECES[sb]
    dst_t = _TITLE_PIECES[db]
    changed = []
    any_diff = False

    # --- PRG ピース (nametable / attribute): file offset 不変 ---
    for name in ("nametable", "attribute"):
        s_off, s_len = src_t[name]
        d_off, d_len = dst_t[name]
        if s_len != d_len:                      # 設計上一致するはず
            raise TitleScreenError(
                f"{name} 長さ不一致 (src {s_len} != dst {d_len})。"
                "解析前提崩れのため中止。")
        if s_off + s_len > len(source_rom) or d_off + d_len > len(target_rom):
            raise TitleScreenError(
                f"{name} が ROM 範囲外。破損の可能性ゆえ中止。")
        blk = bytes(source_rom[s_off:s_off + s_len])
        if bytes(target_rom[d_off:d_off + d_len]) != blk:
            target_rom[d_off:d_off + d_len] = blk
            any_diff = True
        changed.append(
            f"{name} {sb}→{db} (dst 0x{d_off:X} ← src 0x{s_off:X}, "
            f"{s_len}B)")

    # --- CHR bank3 (タイル絵): 動的 offset ---
    s_c = chr_bank3_offset(source_rom)
    d_c = chr_bank3_offset(target_rom)
    if s_c + CHR_BANK_SIZE > len(source_rom) or \
            d_c + CHR_BANK_SIZE > len(target_rom):
        raise TitleScreenError("CHR bank3 が ROM 範囲外。中止。")
    cblk = bytes(source_rom[s_c:s_c + CHR_BANK_SIZE])
    if bytes(target_rom[d_c:d_c + CHR_BANK_SIZE]) != cblk:
        target_rom[d_c:d_c + CHR_BANK_SIZE] = cblk
        any_diff = True
    changed.append(
        f"CHR bank3 (絵) {sb}→{db} (dst 0x{d_c:X} ← src 0x{s_c:X}, "
        f"{CHR_BANK_SIZE}B)")

    if not any_diff:
        return [f"タイトルは移植元({sb})と同一でした (変更なし)。"]
    changed.append(
        "※色(パレット)は移植先の元のまま (v1)。配置・絵は移植済。")
    return changed


def _stock_title_streams_for_import(rom_data):
    """Return two stock title grids and the base region for JP/US sources."""
    region = _verify(rom_data)
    base = region_mod.base_region(region)
    if base not in _TITLE_PIECES:
        raise TitleScreenError(
            f"stock title pieces are unavailable for region {base}.")
    nt_off, nt_len = _TITLE_PIECES[base]["nametable"]
    grids = []
    p = nt_off
    end_limit = nt_off + nt_len + 8
    for _ in range(2):
        writes, end = _decode_cc4f(bytes(rom_data), p)
        grid = [None] * _NT_CELLS
        for addr, tile in writes:
            idx = addr & 0x3FF
            if 0 <= idx < _NT_CELLS and tile != 0x24:
                grid[idx] = tile
        grids.append(grid)
        if end <= p or end >= end_limit:
            break
        p = end
    while len(grids) < 2:
        grids.append([None] * _NT_CELLS)
    return base, grids[0], grids[1]


def _wide_title_streams_for_import(rom_data):
    """Fallback for already-wide sources: one sparse stream plus an empty one."""
    info = decode_title_grid(rom_data)
    grid = [None if t == 0x24 else t for t in info["grid"]]
    return grid, [None] * _NT_CELLS


def _us_arcade_title_streams_for_import(rom_data):
    """Decode the known US arcade-title hack stream layout."""
    grids = []
    for cpu in (0xCD5F, 0xCDF5):
        grid = [None] * _NT_CELLS
        for addr, tile in decode_arcade_stream(
                rom_data, 0x10 + (cpu - 0x8000)):
            idx = addr - ARCADE_NT_BASE
            if 0 <= idx < _NT_CELLS:
                grid[idx] = tile
        grids.append(grid)
    # The US arcade hack also writes an 18-cell fixed strip from code
    # ($CBC3 -> PPU $29A6, tile $63-$74). It is part of the banner art, not
    # present in either stream, so merge it into block A before transcoding.
    for k in range(18):
        grids[0][_WJP_CBC3_STRIP0 + k] = 0x63 + k
    return grids[0], grids[1]


def _wt_title_oam_table_file() -> int:
    dec = _wt_current_decoder_bytes()
    return _WT_DEC_FILE + len(dec) - _WT_TITLE_SLOT_TABLE_BYTES


def _wt_has_current_title_slot_helper(rom_data) -> bool:
    dec = _wt_current_decoder_bytes()
    attr_s = _wt_title_attr_table_file()
    attr_e = attr_s + _WT_TITLE_ATTR_TABLE_BYTES
    oam_s = _wt_title_oam_table_file()
    if oam_s <= attr_e:
        return False
    rel_attr_s = attr_s - _WT_DEC_FILE
    rel_attr_e = attr_e - _WT_DEC_FILE
    rel_oam_s = oam_s - _WT_DEC_FILE
    return (
        bytes(rom_data[_WT_DEC_FILE:attr_s]) == dec[:rel_attr_s] and
        bytes(rom_data[attr_e:oam_s]) == dec[rel_attr_e:rel_oam_s]
    )


def _wt_read_title_oam_table_or_default(rom_data) -> bytes:
    start = _wt_title_oam_table_file()
    end = start + _WT_TITLE_SLOT_TABLE_BYTES
    if _wt_has_current_title_slot_helper(rom_data) and end <= len(rom_data):
        return bytes(rom_data[start:end])
    return _wt_title_oam_default_table()


def title_character_oam_attrs(frame_attr: int) -> tuple[int, int]:
    attr = int(frame_attr) & 0xFF
    p1 = ((attr >> 7) & 0x01) | (((attr >> 6) & 0x01) << 1)
    p2 = (attr >> 2) & 0x03
    h1, v1 = (attr >> 4) & 1, (attr >> 5) & 1
    h2, v2 = (attr >> 1) & 1, (attr >> 0) & 1
    return ((v1 << 7) | (h1 << 6) | p1,
            (v2 << 7) | (h2 << 6) | p2)


def read_title_characters(rom_data) -> list:
    """Read the current 20 title character main-slot entries."""
    table = _wt_read_title_oam_table_or_default(rom_data)
    out = []
    for slot in range(_WT_TITLE_CHARACTER_MAX):
        pos = slot * _WT_TITLE_SLOT_ENTRY_BYTES
        entry = bytes(table[pos:pos + _WT_TITLE_SLOT_ENTRY_BYTES])
        attr1, attr2 = title_character_oam_attrs(entry[5])
        out.append({
            "slot": slot,
            "active": _wt_title_oam_is_active(entry),
            "y": entry[1],
            "x": entry[2],
            "tile1": entry[3],
            "tile2": entry[4],
            "attr": entry[5],
            "attr1": attr1,
            "attr2": attr2,
        })
    return out


def title_character_entry(x: int, y: int, tile1: int, tile2: int,
                          frame_attr: int, palette: int) -> bytes:
    """Build one title main-slot entry from the ROM-frame pair and palette."""
    x = max(0, min(0xFF, int(x)))
    y = max(0, min(0xEF, int(y)))
    pal = int(palette) & 0x03
    attr = int(frame_attr) & 0xFF
    h1, v1 = (attr >> 4) & 1, (attr >> 5) & 1
    h2, v2 = (attr >> 1) & 1, (attr >> 0) & 1
    slot_attr = ((pal & 1) << 7) | ((pal & 2) << 5) | \
        (v1 << 5) | (h1 << 4) | \
        ((pal & 3) << 2) | (h2 << 1) | v2
    return bytes((0x80, y & 0xFF, x & 0xFF,
                  int(tile1) & 0xFF, int(tile2) & 0xFF, slot_attr & 0xFF))


def _write_title_oam_table_with_streams(rom_data, table: bytes) -> list:
    grid_a, grid_b = _wide_title_grids_for_edit(rom_data)
    len_a, len_b = _write_wide_title_streams_for_import(
        rom_data, grid_a, grid_b, title_oam_table=table)
    active = sum(
        1 for i in range(_WT_TITLE_CHARACTER_MAX)
        if _wt_title_oam_is_active(
            table[i * _WT_TITLE_SLOT_ENTRY_BYTES:
                  (i + 1) * _WT_TITLE_SLOT_ENTRY_BYTES]))
    return [
        f"title characters updated: {active}/{_WT_TITLE_CHARACTER_MAX}",
        f"bank1 streams rewritten: A={len_a}B / B={len_b}B",
    ]


def _title_character_table_for_edit(rom_data) -> bytearray:
    return bytearray(_wt_read_title_oam_table_or_default(rom_data))


def _title_character_slot_pos(slot: int) -> int:
    slot = int(slot)
    if not (0 <= slot < _WT_TITLE_CHARACTER_MAX):
        raise TitleScreenError(
            f"title character slot must be 0..{_WT_TITLE_CHARACTER_MAX - 1}.")
    return slot * _WT_TITLE_SLOT_ENTRY_BYTES


def add_title_character(rom_data, x: int, y: int, tile1: int, tile2: int,
                        frame_attr: int, palette: int) -> list:
    table = _title_character_table_for_edit(rom_data)
    slot = None
    for i in range(_WT_TITLE_CHARACTER_MAX):
        pos = i * _WT_TITLE_SLOT_ENTRY_BYTES
        if not _wt_title_oam_is_active(table[pos:pos + _WT_TITLE_SLOT_ENTRY_BYTES]):
            slot = i
            break
    if slot is None:
        raise TitleScreenError(
            f"title character slots are full "
            f"({_WT_TITLE_CHARACTER_MAX}/{_WT_TITLE_CHARACTER_MAX}).")
    pos = slot * _WT_TITLE_SLOT_ENTRY_BYTES
    table[pos:pos + _WT_TITLE_SLOT_ENTRY_BYTES] = \
        title_character_entry(x, y, tile1, tile2, frame_attr, palette)
    msgs = _write_title_oam_table_with_streams(rom_data, bytes(table))
    msgs.insert(0, f"title character placed: slot {slot + 1}/{_WT_TITLE_CHARACTER_MAX}")
    return msgs


def set_title_character_slot(rom_data, slot: int, x: int, y: int,
                             tile1: int, tile2: int, frame_attr: int,
                             palette: int) -> list:
    table = _title_character_table_for_edit(rom_data)
    pos = _title_character_slot_pos(slot)
    table[pos:pos + _WT_TITLE_SLOT_ENTRY_BYTES] = \
        title_character_entry(x, y, tile1, tile2, frame_attr, palette)
    msgs = _write_title_oam_table_with_streams(rom_data, bytes(table))
    msgs.insert(0, f"title character slot {int(slot) + 1} updated")
    return msgs


def move_title_character(rom_data, slot: int, x: int, y: int) -> list:
    table = _title_character_table_for_edit(rom_data)
    pos = _title_character_slot_pos(slot)
    entry = bytes(table[pos:pos + _WT_TITLE_SLOT_ENTRY_BYTES])
    if not _wt_title_oam_is_active(entry):
        raise TitleScreenError(f"title character slot {int(slot) + 1} is empty.")
    table[pos + 1] = max(0, min(0xEF, int(y))) & 0xFF
    table[pos + 2] = max(0, min(0xFF, int(x))) & 0xFF
    msgs = _write_title_oam_table_with_streams(rom_data, bytes(table))
    msgs.insert(0, f"title character slot {int(slot) + 1} moved")
    return msgs


def remove_title_character(rom_data, slot: int) -> list:
    table = _title_character_table_for_edit(rom_data)
    pos = _title_character_slot_pos(slot)
    table[pos:pos + _WT_TITLE_SLOT_ENTRY_BYTES] = _WT_TITLE_SLOT_HIDDEN_ENTRY
    msgs = _write_title_oam_table_with_streams(rom_data, bytes(table))
    msgs.insert(0, f"title character slot {int(slot) + 1} removed")
    return msgs


def clear_title_characters(rom_data) -> list:
    return _write_title_oam_table_with_streams(
        rom_data, _wt_title_oam_default_table())


def _write_wide_title_streams_for_import(target_rom, grid_a, grid_b,
                                         title_oam_table: bytes | bytearray | None = None,
                                         title_attr_table: bytes | bytearray | None = None):
    """Replace the bank1 streams of a JP wide-normalized title."""
    if not is_wide_normalized(target_rom):
        raise TitleScreenError(
            "target ROM is not in the internal wide-title format. "
            "Open a JP ROM first so it is expanded and normalized.")
    if not _wt_has_ram_bootstrap(target_rom):
        raise TitleScreenError(
            "target uses the old in-place wide-title test format. "
            "Reopen a clean JP ROM and use the mapper66 wide-normalized ROM.")
    stream_a = encode_len_stream(grid_a)
    stream_b = encode_len_stream(grid_b)
    table = _wt_read_title_oam_table_or_default(target_rom) \
        if title_oam_table is None else bytes(title_oam_table)
    attr_table = _wt_read_title_attr_table_or_default(target_rom) \
        if title_attr_table is None else bytes(title_attr_table)
    boot, decoder = _wt_build_trampoline(
        _WT_DEC_CPU, title_oam_table=table, title_attr_table=attr_table)
    a_file = _WT_DEC_FILE + len(decoder)
    b_file = a_file + len(stream_a)
    end_file = b_file + len(stream_b)
    if end_file > _WT_WIDE_END:
        raise TitleScreenError(
            f"title streams are too large for bank1 title workspace "
            f"({end_file - _WT_DEC_FILE}B > {_WT_WIDE_END - _WT_DEC_FILE}B).")
    rf_s, rf_e = _RF_BAND
    for off, ln in ((a_file, len(stream_a)), (b_file, len(stream_b))):
        if off < rf_e and off + ln > rf_s:
            raise TitleScreenError(
                f"internal error: title stream write 0x{off:X}+{ln}B "
                "overlaps the Room Flag bank0 cave band.")
    target_rom[_wjp_cf(0xCC4F):_wjp_cf(0xCC4F) + len(boot)] = boot
    target_rom[_WT_DEC_FILE:_WT_DEC_FILE + len(decoder)] = decoder
    for i in range(a_file, _WT_WIDE_END):
        target_rom[i] = 0
    target_rom[a_file:a_file + len(stream_a)] = stream_a
    target_rom[b_file:b_file + len(stream_b)] = stream_b
    a_cpu = 0x8000 + (a_file - 0x8010)
    b_cpu = 0x8000 + (b_file - 0x8010)
    target_rom[_wjp_cf(_WT_PTRA_LO)] = a_cpu & 0xFF
    target_rom[_wjp_cf(_WT_PTRA_HI)] = (a_cpu >> 8) & 0xFF
    target_rom[_wjp_cf(_WT_PTRB_LO)] = b_cpu & 0xFF
    target_rom[_wjp_cf(_WT_PTRB_HI)] = (b_cpu >> 8) & 0xFF
    _wt_install_title_oam_clear(target_rom)
    _wt_install_idle_demo_cleanup(target_rom)
    return len(stream_a), len(stream_b)


_TITLE_TEXT_SUPPORTED = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ ,.\""
_TITLE_TEXT_ROW = 14
_TITLE_PUSH_TEXT_CPU = 0x955C
_TITLE_PUSH_TEXT_LEN = 17
_TITLE_PUNCT_TILE = {
    ",": 0x25,
    "\"": 0x28,
    ".": 0x29,
}


def _title_char_src_tile(ch: str) -> int:
    if ch == " ":
        return 0x24
    if ch in _TITLE_PUNCT_TILE:
        return _TITLE_PUNCT_TILE[ch]
    if "0" <= ch <= "9":
        return ord(ch) - ord("0")
    if "A" <= ch <= "Z":
        return 0x0A + (ord(ch) - ord("A"))
    raise TitleScreenError(
        f"unsupported title text character {ch!r}; "
        "use A-Z, 0-9, space, comma, period, and double quote.")


def _title_char_tile_bytes(rom_data, ch: str) -> bytes:
    """Return the 2bpp tile bytes used as source for one title-text char."""
    src = _title_char_src_tile(ch)
    chr_off = chr_bank3_offset(rom_data)
    src_pos = chr_off + (_BG_BASE + src) * NES_GFX_TILE_BYTE_SIZE
    return bytes(rom_data[src_pos:src_pos + NES_GFX_TILE_BYTE_SIZE])


def _title_char_from_src_tile(tile: int) -> str:
    tile = int(tile) & 0xFF
    if tile == 0x24:
        return " "
    for ch, val in _TITLE_PUNCT_TILE.items():
        if tile == val:
            return ch
    if 0x00 <= tile <= 0x09:
        return chr(ord("0") + tile)
    if 0x0A <= tile <= 0x23:
        return chr(ord("A") + tile - 0x0A)
    return " "


def read_title_push_start_text(rom_data) -> str:
    """Read the fixed 17-tile PUSH START BUTTON title script text."""
    pos = _wjp_cf(_TITLE_PUSH_TEXT_CPU)
    if pos + 3 + _TITLE_PUSH_TEXT_LEN > len(rom_data):
        raise TitleScreenError("title PUSH START script is outside ROM.")
    if bytes(rom_data[pos:pos + 3]) != bytes((0x29, 0xE6, 0x50)):
        raise TitleScreenError("title PUSH START script signature mismatch.")
    return "".join(
        _title_char_from_src_tile(rom_data[pos + 3 + i])
        for i in range(_TITLE_PUSH_TEXT_LEN)
    ).rstrip()


def set_title_push_start_text(rom_data, text: str) -> list:
    """Replace the fixed PUSH START BUTTON script text in-place."""
    pos = _wjp_cf(_TITLE_PUSH_TEXT_CPU)
    if pos + 3 + _TITLE_PUSH_TEXT_LEN > len(rom_data):
        raise TitleScreenError("title PUSH START script is outside ROM.")
    if bytes(rom_data[pos:pos + 3]) != bytes((0x29, 0xE6, 0x50)):
        raise TitleScreenError("title PUSH START script signature mismatch.")
    raw = (text or "").upper()
    for ch in raw:
        if ch not in _TITLE_TEXT_SUPPORTED:
            raise TitleScreenError(
                f"unsupported title text character {ch!r}; "
                "use A-Z, 0-9, space, comma, period, and double quote.")
    raw = " ".join(raw.split())
    if len(raw) > _TITLE_PUSH_TEXT_LEN:
        raise TitleScreenError(
            f"PUSH START text is too long; maximum is {_TITLE_PUSH_TEXT_LEN} characters.")
    line = raw.ljust(_TITLE_PUSH_TEXT_LEN)
    for i, ch in enumerate(line):
        rom_data[pos + 3 + i] = _title_char_src_tile(ch)
    return [f"title PUSH START text set: {raw!r}"]


def read_title_text_line(rom_data, row: int = _TITLE_TEXT_ROW) -> str:
    """Best-effort reverse read of the custom wide-stream title text row."""
    if not (0 <= int(row) < 30):
        raise TitleScreenError(f"title text row must be 0..29 (got {row}).")
    grid_a, grid_b = _wide_title_grids_for_edit(rom_data)
    chr_off = chr_bank3_offset(rom_data)
    by_bytes = {}
    for ch in _TITLE_TEXT_SUPPORTED:
        by_bytes[_title_char_tile_bytes(rom_data, ch)] = ch

    row0 = int(row) * 32
    chars = []
    for x in range(32):
        t = grid_a[row0 + x]
        if t is None:
            chars.append(" ")
            continue
        pos = chr_off + (_BG_BASE + t) * NES_GFX_TILE_BYTE_SIZE
        chars.append(by_bytes.get(bytes(rom_data[pos:pos + NES_GFX_TILE_BYTE_SIZE]), " "))
    return "".join(chars).strip()


def _wide_title_grids_for_edit(rom_data):
    """Return editable sparse grids for the current internal wide-title streams."""
    if not is_wide_normalized(rom_data):
        raise TitleScreenError(
            "target ROM is not in the internal wide-title format. "
            "Open a JP ROM first so it is expanded and normalized.")
    if not _wt_has_ram_bootstrap(rom_data):
        raise TitleScreenError(
            "target uses the old in-place wide-title test format. "
            "Reopen a clean JP ROM and use the mapper66 wide-normalized ROM.")
    a_cpu = rom_data[_wjp_cf(_WT_PTRA_LO)] | \
        (rom_data[_wjp_cf(_WT_PTRA_HI)] << 8)
    b_cpu = rom_data[_wjp_cf(_WT_PTRB_LO)] | \
        (rom_data[_wjp_cf(_WT_PTRB_HI)] << 8)
    grids = []
    for cpu in (a_cpu, b_cpu):
        if not (0x8000 <= cpu <= 0xFFFF):
            raise TitleScreenError(f"wide-title stream pointer ${cpu:04X} is invalid.")
        g = [None] * _NT_CELLS
        decoder = decode_len_stream if _wt_uses_len_stream(rom_data) else decode_arcade_stream
        for ad, t in decoder(rom_data, _wjp_b1f(cpu)):
            idx = ad - ARCADE_NT_BASE
            if 0 <= idx < _NT_CELLS and t != 0x24:
                g[idx] = t
        grids.append(g)
    return grids[0], grids[1]


_TITLE_TOP_ROW0 = 6
_TITLE_TOP_ROWS = 8


def export_title_top_layout(rom_data) -> dict:
    """Return the current wide-title placement for the 256x64 top edit band.

    The PNG contains only pixels. This sidecar keeps the stream placement so a
    top PNG exported from an imported US/arcade title can be applied to a fresh
    JP-wide title without collapsing back to the stock JP cell layout.
    """
    grid_a, grid_b = _wide_title_grids_for_edit(rom_data)
    cells = []
    for row in range(_TITLE_TOP_ROW0, _TITLE_TOP_ROW0 + _TITLE_TOP_ROWS):
        for col in range(32):
            idx = row * 32 + col
            a = grid_a[idx]
            b = grid_b[idx]
            if a is not None or b is not None:
                rec = {"cell": idx}
                if a is not None:
                    rec["a"] = int(a)
                if b is not None:
                    rec["b"] = int(b)
                cells.append(rec)
    info = decode_title_grid(rom_data)
    return {
        "format": "solomon_customizer_title_top_sidecar",
        "version": 1,
        "top_row": _TITLE_TOP_ROW0,
        "rows": _TITLE_TOP_ROWS,
        "width": 256,
        "height": 64,
        "region": info.get("region"),
        "wide": bool(info.get("wide")),
        "cell_count": int(info.get("cells", 0)),
        "cells": cells,
    }


def apply_title_top_layout(rom_data, meta: dict) -> list:
    """Apply a top-band sidecar layout to the current wide-title streams."""
    if not isinstance(meta, dict):
        raise TitleScreenError("title top sidecar is not a JSON object.")
    if meta.get("format") != "solomon_customizer_title_top_sidecar":
        raise TitleScreenError("not a Solomon Customizer title top sidecar.")
    if int(meta.get("version", 0)) != 1:
        raise TitleScreenError(
            f"unsupported title top sidecar version: {meta.get('version')!r}.")
    row0 = int(meta.get("top_row", _TITLE_TOP_ROW0))
    rows = int(meta.get("rows", _TITLE_TOP_ROWS))
    if row0 != _TITLE_TOP_ROW0 or rows != _TITLE_TOP_ROWS:
        raise TitleScreenError(
            f"unsupported title top sidecar band: row={row0}, rows={rows}.")

    grid_a, grid_b = _wide_title_grids_for_edit(rom_data)

    # Clear the whole top edit band first, then write the saved sparse cells.
    start = row0 * 32
    end = (row0 + rows) * 32
    for idx in range(start, end):
        grid_a[idx] = None
        grid_b[idx] = None

    restored = 0
    for rec in meta.get("cells", []):
        idx = int(rec.get("cell", -1))
        if not (start <= idx < end):
            raise TitleScreenError(
                f"title top sidecar cell {idx} is outside the top band.")
        if "a" in rec:
            grid_a[idx] = int(rec["a"]) & 0xFF
        if "b" in rec:
            grid_b[idx] = int(rec["b"]) & 0xFF
        restored += 1

    len_a, len_b = _write_wide_title_streams_for_import(rom_data, grid_a, grid_b)
    after = decode_title_grid(rom_data)
    return [
        f"title top layout sidecar applied: {restored} cells",
        f"bank1 streams rewritten: A={len_a}B / B={len_b}B, cells={after['cells']}",
    ]


def add_title_text_line(rom_data, text: str, row: int = _TITLE_TEXT_ROW) -> list:
    """Draw one centered custom text line through the internal wide-title stream.

    The original title text routine and CHR bank3 are left untouched. The
    internal LEN stream can write tile values $00-$2F directly, so the overlay
    uses the existing font tiles instead of copying glyphs into high CHR slots.
    The whole target row is filled with space tiles first so applying a shorter
    line clears the previous one.
    """
    dst_region = _verify(rom_data)
    if region_mod.base_region(dst_region) != "JP":
        raise TitleScreenError(
            f"title text overlay requires JP/JP66 target (target={dst_region}).")
    if not (0 <= int(row) < 30):
        raise TitleScreenError(f"title text row must be 0..29 (got {row}).")
    raw = (text or "").upper()
    for ch in raw:
        if ch not in _TITLE_TEXT_SUPPORTED:
            raise TitleScreenError(
                f"unsupported title text character {ch!r}; "
                "use A-Z, 0-9, space, comma, period, and double quote.")
    raw = " ".join(raw.split())
    if len(raw) > 32:
        raise TitleScreenError("title text is too long; maximum is 32 characters.")

    grid_a, grid_b = _wide_title_grids_for_edit(rom_data)
    row0 = int(row) * 32

    # Clear the target row in both streams. Block A will write visible spaces
    # across the row, which also clears an older overlay cleanly.
    for x in range(32):
        grid_a[row0 + x] = None
        grid_b[row0 + x] = None

    line = raw.center(32)
    for x, ch in enumerate(line):
        grid_a[row0 + x] = _title_char_src_tile(ch)

    len_a, len_b = _write_wide_title_streams_for_import(rom_data, grid_a, grid_b)
    return [
        f"title text overlay added at row {row}: {raw!r}",
        f"bank1 streams rewritten: A={len_a}B / B={len_b}B",
        "original PUSH START / TECMO text routine and CHR bank3 are untouched.",
    ]


def transcode_title(target_rom, source_rom) -> list:
    """Import a JP/US title into a JP mapper66 wide-normalized ROM.

    Public builds do not bundle third-party IPS or ROM files. The user selects
    a ROM they own, normally a clean US ROM when they want the US title.
    """
    dst_region = _verify(target_rom)
    src_region = _verify(source_rom)
    db = region_mod.base_region(dst_region)
    sb = region_mod.base_region(src_region)
    if db != "JP":
        raise TitleScreenError(
            f"title import target must be JP/JP66 (target={dst_region}).")
    if sb not in _TITLE_PIECES:
        raise TitleScreenError(
            f"source title import supports JP/US only (source={src_region}).")

    if is_wide_normalized(source_rom):
        grid_a, grid_b = _wide_title_streams_for_import(source_rom)
        source_kind = "wide"
    elif _is_us_arcade_title_hack(source_rom):
        grid_a, grid_b = _us_arcade_title_streams_for_import(source_rom)
        source_kind = "us-arcade"
    else:
        _base, grid_a, grid_b = _stock_title_streams_for_import(source_rom)
        source_kind = "stock"

    len_a, len_b = _write_wide_title_streams_for_import(
        target_rom, grid_a, grid_b)

    s_chr = chr_bank3_offset(source_rom)
    d_chr = chr_bank3_offset(target_rom)
    if s_chr + CHR_BANK_SIZE > len(source_rom) or \
            d_chr + CHR_BANK_SIZE > len(target_rom):
        raise TitleScreenError("CHR bank3 is outside the ROM range.")
    target_rom[d_chr:d_chr + CHR_BANK_SIZE] = \
        bytes(source_rom[s_chr:s_chr + CHR_BANK_SIZE])

    dst_attr_off, dst_attr_len = _TITLE_PIECES["JP"]["attribute"]
    color_msgs = []
    if source_kind == "us-arcade":
        if _US_ARCADE_ATTR_OFF + _US_ARCADE_ATTR_LEN > len(source_rom):
            raise TitleScreenError(
                "US arcade title attribute table is outside the source ROM.")
        if dst_attr_len != _US_ARCADE_ATTR_LEN:
            raise TitleScreenError(
                "internal error: JP title attribute size is not 21 bytes.")
        target_rom[dst_attr_off:dst_attr_off + dst_attr_len] = \
            bytes(source_rom[_US_ARCADE_ATTR_OFF:
                             _US_ARCADE_ATTR_OFF + _US_ARCADE_ATTR_LEN])
        color_msgs.append("arcade attribute copied: $CCAF -> $CD58")
        for off, before, after_bytes in _WJP_COLOR:
            if bytes(target_rom[off:off + len(before)]) == before:
                target_rom[off:off + len(after_bytes)] = after_bytes
                color_msgs.append(f"arcade color patch applied at 0x{off:X}")
            else:
                color_msgs.append(
                    f"arcade color patch skipped at 0x{off:X} "
                    "(signature mismatch)")
    else:
        src_attr_off, src_attr_len = _TITLE_PIECES[sb]["attribute"]
        if src_attr_len == dst_attr_len:
            target_rom[dst_attr_off:dst_attr_off + dst_attr_len] = \
                bytes(source_rom[src_attr_off:src_attr_off + src_attr_len])

    after = decode_title_grid(target_rom)
    msg = [
        f"title imported: {src_region} {source_kind} -> {dst_region} wide",
        f"bank1 streams: A={len_a}B / B={len_b}B, cells={after['cells']}",
        f"CHR bank3 copied: 0x{s_chr:X} -> 0x{d_chr:X} ({CHR_BANK_SIZE}B)",
        "target remains mapper66 wide-title; bank0 Room Flag cave is untouched.",
    ]
    msg.extend(color_msgs)
    return msg


def title_blocks(rom_data) -> list:
    """差し替え単位の (file_off, length, 名称) リスト。検証付き。"""
    _verify(rom_data)
    return [
        (chr_bank3_offset(rom_data), CHR_BANK_SIZE, "CHR bank3 (ロゴ絵)"),
        (TITLE_PRG_OFF, TITLE_PRG_LEN, "描画/nametable/attr/palette"),
    ]


def snapshot(rom_data) -> dict:
    """現在のタイトル領域バイトを退避 (「原作に戻す」用)。検証付き。"""
    snap = {}
    for off, ln, _name in title_blocks(rom_data):
        snap[off] = bytes(rom_data[off:off + ln])
    return snap


def restore(rom_data, snap: dict) -> list:
    """snapshot() で取った状態へ復元。戻り値=変更説明。"""
    _verify(rom_data)
    changed = []
    for off, data in snap.items():
        if bytes(rom_data[off:off + len(data)]) != data:
            rom_data[off:off + len(data)] = data
            changed.append(f"タイトル領域 0x{off:X} 復元")
    return changed


def copy_title_from(dst_rom, src_rom) -> list:
    """別ユーザー所有 ROM(src) のタイトルを現在の ROM(dst) へ複写。

    位置+署名を ★両 ROM で検証し、両方一致した時のみ複写。
    不一致は TitleScreenError で中止 (CLAUDE.md 絶対則・フォールバック禁止)。
    戻り値=変更説明リスト。
    """
    dst_region = _verify(dst_rom)   # 一致しなければここで例外
    src_region = _verify(src_rom)
    src_b3 = chr_bank3_offset(src_rom)
    dst_b3 = chr_bank3_offset(dst_rom)
    plan = [
        (dst_b3, src_b3, CHR_BANK_SIZE, "CHR bank3 (ロゴ絵)"),
        (TITLE_PRG_OFF, TITLE_PRG_OFF, TITLE_PRG_LEN,
         "描画/nametable/attr/palette"),
    ]
    # 事前に src 範囲が収まるか最終確認 (verify 済だが二重に)
    for _do, so, ln, _nm in plan:
        if so + ln > len(src_rom):
            raise TitleScreenError(
                "差し替え元 ROM のタイトル領域が範囲外。中止。")
    changed = []
    for do, so, ln, nm in plan:
        block = bytes(src_rom[so:so + ln])
        if bytes(dst_rom[do:do + ln]) != block:
            dst_rom[do:do + ln] = block
            changed.append(
                f"{nm} を {src_region} ROM から複写 "
                f"(dst 0x{do:X} ← src 0x{so:X}, {ln}B)")
    if not changed:
        changed.append("タイトル領域は差し替え元と同一でした (変更なし)。")
    return changed


RAW_INES_SIZE = 65552           # clean mapper3 (16 + 32KB PRG + 32KB CHR)


def patched_rom_from_ips(base_rom, ips_bytes: bytes) -> bytearray:
    """★ユーザー所有の通常 ROM(base) に .ips を適用した bytes を返す。

    ★重要 (R196): タイトル系 IPS は通常 ROM(mapper3 65552) 前提で
    オフセットが書かれている。本アプリは読込時に拡張 ROM(mapper66
    98320) へ自動変換しているため、IPS を現在の ROM に直接当てると
    CHR レコードが別領域に着弾して ROM が壊れる。よって
      (1) ユーザー所有の通常 ROM(base, 未拡張) に IPS を適用し
      (2) その結果のタイトル領域だけを copy_title_from() で現 ROM へ
    という二段で安全に取り込む。本関数は (1) を担う。

    検証: base が通常 mapper3 (len 65552 / PRG32KB / CHR>=4bank) か、
    適用後も Solomon 構造を保つか。崩れたら TitleScreenError で中止
    (フォールバック禁止)。
    """
    base = bytes(base_rom)
    if len(base) < 16 or base[:4] != INES_MAGIC:
        raise TitleScreenError(
            "原本 ROM が iNES ではありません。IPS 適用を中止。")
    if len(base) != RAW_INES_SIZE or base[4] * 0x4000 != 0x8000:
        raise TitleScreenError(
            f"原本 ROM が通常 ROM(mapper3 {RAW_INES_SIZE}B) では"
            f"ありません (len={len(base)})。タイトル系 IPS は通常 ROM "
            "前提です。市販吸い出しの未改造 .nes を指定してください。")
    # base 自体が Solomon JP/US 構造か (署名)
    _verify(bytearray(base))
    try:
        patched = ips_mod.apply_ips_patch(base, ips_bytes)
    except ips_mod.IpsError as e:
        raise TitleScreenError(f"IPS 形式エラー: {e}")
    if len(patched) != RAW_INES_SIZE:
        raise TitleScreenError(
            f"IPS 適用で ROM サイズが変化 ({RAW_INES_SIZE}→"
            f"{len(patched)})。タイトル系 IPS では想定外ゆえ中止。")
    # 適用後もタイトル領域が読める構造か (壊れ patch 防御)
    _verify(patched)
    return patched


# ============================================================
# Phase2: 広域 arcade タイトル移植 (JP) — R196-R201 / 実機確定
# ============================================================
# 確定 recipe (build_TitleWide_JP_v9.py = 実機検証済 CRC0BF323D8):
#   v3広域描画 (decoder@$CC4F / banner+$CBC3固定帯@$CEA3 /
#   山@JP cave / $CCB6 ptr→cave / CHR=arcade) + $CD58←arcade
#   $CCAF (必須) + 色4点。全パッチ ★before署名検証・不一致は中止。
# ★著作権: arcade の CHR/stream/attribute は ★ユーザー所有の
#   arcade ROM から抽出 (ツールに埋め込まない)。埋め込むのは
#   当方 6502 デコーダと色 patch 定数 (graphics でない) のみ。
# ★JP 専用: cave/番地が JP 固有。US へは適用しない (region gate)。
# ★PRG offset は file 値 (mapper66 拡張後も <0x8010 は verbatim
#   ゆえ不変)。CHR bank3 のみ chr_bank3_offset() で動的算出。

_WA_SZ = {"LDYi": 2, "CMPi": 2, "ADCi": 2, "LDAz": 2, "STAz": 2,
          "INCz": 2, "LDAiy": 2, "ADCz": 2, "LDAa": 3, "STAa": 3,
          "LDXa": 3, "JMP": 3, "JMPABS": 3, "BEQ": 2, "BNE": 2,
          "BCC": 2, "INY": 1, "CLC": 1, "TYA": 1, "TAX": 1,
          "DEX": 1, "RTS": 1}
_WA_OPC = {"LDYi": 0xA0, "CMPi": 0xC9, "ADCi": 0x69, "LDAz": 0xA5,
           "STAz": 0x85, "INCz": 0xE6, "LDAiy": 0xB1, "ADCz": 0x65,
           "LDAa": 0xAD, "STAa": 0x8D, "LDXa": 0xAE, "JMP": 0x4C,
           "JMPABS": 0x4C, "BEQ": 0xF0, "BNE": 0xD0, "BCC": 0x90,
           "INY": 0xC8, "CLC": 0x18, "TYA": 0x98, "TAX": 0xAA,
           "DEX": 0xCA, "RTS": 0x60}
_WA_ARCADE_PROG = [
    ("LDYi", 0), ("CMD",), ("LDAiy", 0), ("CMPi", 0x2F),
    ("BEQ", "DONE"), ("STAz", 3), ("INY",), ("LDAiy", 0),
    ("STAz", 2), ("LDAz", 0), ("CLC",), ("ADCi", 2),
    ("STAz", 0), ("BCC", "H1"), ("INCz", 1), ("H1",),
    ("LDAa", 0x2002), ("LDAz", 3), ("STAa", 0x2006),
    ("LDAz", 2), ("STAa", 0x2006), ("LDAa", 0x0300),
    ("STAa", 0x2000), ("LDYi", 0), ("RUN",), ("LDAiy", 0),
    ("CMPi", 0x30), ("BCC", "ENDR"), ("STAa", 0x2007), ("INY",),
    ("BNE", "RUN"), ("ENDR",), ("TYA",), ("CLC",), ("ADCz", 0),
    ("STAz", 0), ("BCC", "E1"), ("INCz", 1), ("E1",),
    ("LDYi", 0), ("JMP", "CMD"), ("DONE",), ("LDXa", 0x2002),
    ("RTS",)]
_WA_LEN_PROG = [
    ("LDYi", 0), ("CMD",), ("LDAiy", 0), ("CMPi", LEN_STREAM_TERM),
    ("BEQ", "DONE"), ("STAz", 3), ("INY",), ("LDAiy", 0),
    ("STAz", 2), ("INY",), ("LDAiy", 0), ("TAX",), ("INY",),
    ("LDAz", 0), ("CLC",), ("ADCi", 3), ("STAz", 0),
    ("BCC", "H1"), ("INCz", 1), ("H1",), ("LDAa", 0x2002),
    ("LDAz", 3), ("STAa", 0x2006), ("LDAz", 2), ("STAa", 0x2006),
    ("LDAa", 0x0300), ("STAa", 0x2000), ("LDYi", 0),
    ("RUN",), ("LDAiy", 0), ("STAa", 0x2007), ("INY",),
    ("DEX",), ("BNE", "RUN"), ("TYA",), ("CLC",), ("ADCz", 0),
    ("STAz", 0), ("BCC", "E1"), ("INCz", 1), ("E1",),
    ("LDYi", 0), ("JMP", "CMD"), ("DONE",), ("LDXa", 0x2002),
    ("RTS",)]
_WA_PROG = _WA_LEN_PROG
_WJP_SIG = {
    0xCC4F: bytes.fromhex("AC0220A0008402840388C8B10030"),
    0xCCB6: bytes.fromhex("207396A9088500A9CE8501"),
    0xCEA3: bytes.fromhex("5926D7D4D6D1"),
    0xCE08: bytes.fromhex("5306E8"),
}
_WJP_COLOR = [
    (0x156D, bytes.fromhex("E650"), bytes.fromhex("EA49")),
    (0x1579, bytes.fromhex("240B1E1D1D1817"),
     bytes.fromhex("00000000000000")),
    (0x15A6, bytes.fromhex("273C30"), bytes.fromhex("2C2716")),
    (0x15AB, bytes.fromhex("02"), bytes.fromhex("16")),
]
_WJP_CD58_BEFORE = bytes.fromhex(
    "F5F5F5F5F7FFFFFF565A5A9A77FFFFFF6FAFAFAF7F")
_WJP_CBC3_STRIP0 = 0x29A6 - ARCADE_NT_BASE      # =422 (固定帯先頭cell)


def _wjp_cf(cpu):
    """PRG bank0 file offset (= mapper3 と同じ。<0x8010 は拡張後も verbatim)"""
    return 0x10 + (cpu - 0x8000)


def _wjp_b1f(cpu):
    """PRG bank1 file offset (mapper66 拡張後の 2 本目 32KB)。
    bank1 有効時 CPU $8000-$FFFF = file 0x8010-0x10010。"""
    return 0x8010 + (cpu - 0x8000)


def _word(cpu):
    """6502 absolute operand bytes, little endian."""
    return bytes((cpu & 0xFF, (cpu >> 8) & 0xFF))


# ===== JP wide title : RAM-trampoline 機構 (2026-05-19 確定) =====
# 設計詳細: docs/wide_title_trampoline_design.html /
#   memory project_wide_title_trampoline_design.md / Codex_Exchange/
# ・twin-stub 案は破棄 (bank1 の CPU $CC4F 像 = expander level data)。
# ・RAM 実行は PRG bank 切替の影響を受けない (定石) → RAM に小型
#   stub だけ置く。decoder 本体 + stream は bank1 空き (file 0x80D0〜)。
# ・SW = STA $BB86: bank0[file 0x3B96]=$FF (=LDX #$FF 即値・不変ROM
#   定数, 読むだけ) / bank1[file 0xBB96]=予約$FF。bus競合: A AND $FF=A。
#   $13=PRG1+CHR3 / $03=PRG0+CHR3 (CHR3固定=タイトル絵不変)。
# ・呼出元 $CCB6 / $CD76 が JSR $CC4F 前に $9673(NMI off・$0300整合)、
#   後に $965F(on)。trampoline は NMI off 窓の内側・$2000/$0300 不可侵。
# ・JSR $CC4F は純サブルーチン: bootstrap→RAM_IN→bank1 decoder→
#   RAM_OUT→RTS。スタック未改変で呼出元へ復帰。
_WT_SW_CPU      = 0xBB86               # bus-conflict bank-switch 書込先
_WT_SW_B0_OFF   = 0x3B96               # bank0 file (=$FF 固定・検証のみ)
_WT_WIDE_END    = 0x8800               # bank1 wide-title end-exclusive
_WT_SW_B1_OFF   = 0xBB96               # bank1 file (=$FF 予約・書込)
_WT_RAM_IN      = 0x072C               # RAM trampoline IN  (8B)
_WT_RAM_OUT     = 0x0734               # RAM trampoline OUT (6B、IN直後)
_WT_RAM_END     = 0x0739               # 予約 $072C-$0739 (14B)
_WT_DEC_FILE    = 0x80D0               # bank1 decoder 配置 file (m66 loader直後)
_WT_DEC_CPU     = 0x8000 + (_WT_DEC_FILE - 0x8010)   # = $80C0
_WT_TITLE_CHARACTER_MAX = 20
_WT_TITLE_SLOT0_BASE = 0x057F
_WT_TITLE_SLOT_STRIDE = 20
_WT_TITLE_SLOT_ENTRY_BYTES = 6
_WT_TITLE_SLOT_TABLE_BYTES = _WT_TITLE_CHARACTER_MAX * _WT_TITLE_SLOT_ENTRY_BYTES
_WT_TITLE_SLOT_HIDDEN_ENTRY = bytes((0x00, 0xF8, 0x00, 0x00, 0x00, 0x00))
_WT_TITLE_ATTR_BLOCK_W = 16
_WT_TITLE_ATTR_BLOCK_H = 15
_WT_TITLE_ATTR_BLOCK_COUNT = _WT_TITLE_ATTR_BLOCK_W * _WT_TITLE_ATTR_BLOCK_H
_WT_TITLE_ATTR_TABLE_BYTES = 64
_WT_TITLE_ATTR_PPU = 0x2BC0
_WT_TITLE_ATTR_WRITER_CODE_BYTES = 29
_WT_TITLE_OAM_CLEAR_CPU = 0xCC6B
_WT_TITLE_START_CLEAR_CPU = 0xCBB3
_RF_BAND        = (0x3BEE, 0x4210)     # Room Flag 占有 file 帯 [start,end)
# 呼出元 stream ポインタ即値 (block A=$CCB6 / block B=$CD76)
_WT_PTRA_LO, _WT_PTRA_HI = 0xCCBA, 0xCCBE
_WT_PTRB_LO, _WT_PTRB_HI = 0xCD84, 0xCD88
# caller-B ($CD80) 列署名 (repoint 対象を含む・clean JP 確定)
#   $CD80: 20 73 96 / A9 A3 85 00 / A9 CE 85 01 / 20 4F CC
_WT_CALLERB_CPU = 0xCD80
_WT_CALLERB_SIG = bytes.fromhex("207396A9A38500A9CE8501204FCC")
# bootstrap コード部 (template を除く 14B・完全決定論=正規化済判定に使用)
#   $CC4F: A2 0D / BD 5D CC / 9D 2C 07 / CA / 10 F7 / 4C 2C 07
_WT_BOOT_SIG = bytes.fromhex("A20DBD5DCC9D2C07CA10F74C2C07")
_WT_BOOT_SIG_LEGACY_03C0 = bytes.fromhex("A20DBD5DCC9DC003CA10F74CC003")
_WT_IDLE_DEMO_TIMEOUT_CPU = 0xCB9E
_WT_IDLE_DEMO_CLEAR_STUB_CPU = 0xBC0E
_WT_IDLE_DEMO_TIMEOUT_ORIG = bytes.fromhex("A918205F8D")
_WT_IDLE_DEMO_TIMEOUT_HOOK = bytes.fromhex("200EBCEAEA")
_WT_IDLE_DEMO_CLEAR_STUB = (
    bytes.fromhex("20") + _word(_WT_TITLE_OAM_CLEAR_CPU) +
    bytes.fromhex("A918205F8D60")
)
assert len(_WT_IDLE_DEMO_CLEAR_STUB) == 9


def _wt_has_current_ram_bootstrap(rom_data) -> bool:
    o = _wjp_cf(0xCC4F)
    return bytes(rom_data[o:o + len(_WT_BOOT_SIG)]) == _WT_BOOT_SIG


def _wt_has_legacy_03c0_bootstrap(rom_data) -> bool:
    o = _wjp_cf(0xCC4F)
    return bytes(rom_data[o:o + len(_WT_BOOT_SIG_LEGACY_03C0)]) == \
        _WT_BOOT_SIG_LEGACY_03C0


def _wt_has_ram_bootstrap(rom_data) -> bool:
    return _wt_has_current_ram_bootstrap(rom_data) or \
        _wt_has_legacy_03c0_bootstrap(rom_data)


def title_character_max() -> int:
    return _WT_TITLE_CHARACTER_MAX


def _wt_title_oam_default_table() -> bytes:
    return _WT_TITLE_SLOT_HIDDEN_ENTRY * _WT_TITLE_CHARACTER_MAX


def _wt_title_oam_is_active(entry: bytes) -> bool:
    return len(entry) >= _WT_TITLE_SLOT_ENTRY_BYTES and bool(entry[0] & 0x80)


def migrate_wide_title_trampoline_ram(rom_data) -> list:
    """Move existing JP66 wide-title RAM trampoline out of block-grid RAM.

    Older internal mapper66 wide-title ROMs copied the bank-switch stub to
    $03C0-$03CD. That overlaps the room block grid ($0304-$03E3) and can leak
    transient garbage into demo/start/clear transitions. New ROMs use the
    quiet post-entity band $072C-$0739 instead.
    """
    if not _wt_has_legacy_03c0_bootstrap(rom_data):
        return []
    boot, _decoder = _wt_build_trampoline(_WT_DEC_CPU)
    rom_data[_wjp_cf(0xCC4F):_wjp_cf(0xCC4F) + len(boot)] = boot
    return [
        "wide-title RAM trampoline migrated: $03C0-$03CD -> $072C-$0739"
    ]


def _wt_install_idle_demo_cleanup(rom_data) -> bool:
    """Clear wide-title nametable leftovers before title-idle demo startup.

    The stock title timeout path schedules action $18 directly and skips the
    $CC18 clear that the manual start path uses. Wide titles fill much more of
    the nametable, so the old title appears for a frame under demo/start CHR.
    Patch only the timeout call site at $CB9E; the shared action entry remains
    untouched.
    """
    hook_off = _wjp_cf(_WT_IDLE_DEMO_TIMEOUT_CPU)
    stub_off = _wjp_cf(_WT_IDLE_DEMO_CLEAR_STUB_CPU)
    cur_hook = bytes(rom_data[hook_off:hook_off + len(_WT_IDLE_DEMO_TIMEOUT_ORIG)])
    if cur_hook not in (_WT_IDLE_DEMO_TIMEOUT_ORIG, _WT_IDLE_DEMO_TIMEOUT_HOOK):
        raise TitleScreenError(
            f"title idle demo timeout signature mismatch at "
            f"${_WT_IDLE_DEMO_TIMEOUT_CPU:04X}: got {cur_hook.hex(' ')}")
    cur_stub = bytes(rom_data[stub_off:stub_off + len(_WT_IDLE_DEMO_CLEAR_STUB)])
    if cur_stub != _WT_IDLE_DEMO_CLEAR_STUB and \
            not all(b in (0xEA, 0x00) for b in cur_stub):
        raise TitleScreenError(
            f"title idle demo cleanup stub cave is not free at "
            f"${_WT_IDLE_DEMO_CLEAR_STUB_CPU:04X}: got {cur_stub.hex(' ')}")
    changed = cur_hook != _WT_IDLE_DEMO_TIMEOUT_HOOK or \
        cur_stub != _WT_IDLE_DEMO_CLEAR_STUB
    rom_data[hook_off:hook_off + len(_WT_IDLE_DEMO_TIMEOUT_HOOK)] = \
        _WT_IDLE_DEMO_TIMEOUT_HOOK
    rom_data[stub_off:stub_off + len(_WT_IDLE_DEMO_CLEAR_STUB)] = \
        _WT_IDLE_DEMO_CLEAR_STUB
    return changed


def _wt_title_oam_clear_helper() -> bytes:
    """Clear the title-only OAM sprites and run the stock title clear first."""
    return (
        bytes.fromhex("20") + _word(0xCC18) +
        bytes.fromhex("20") + _word(0xCB5A) +
        bytes((0x60,))
    )


def _wt_install_title_oam_clear(rom_data) -> bool:
    """Install the title-exit OAM clear hook in wide-title-owned code."""
    helper = _wt_title_oam_clear_helper()
    helper_off = _wjp_cf(_WT_TITLE_OAM_CLEAR_CPU)
    start_off = _wjp_cf(_WT_TITLE_START_CLEAR_CPU)
    start_orig = bytes.fromhex("2018CC")
    start_hook = bytes.fromhex("20") + _word(_WT_TITLE_OAM_CLEAR_CPU)
    cur_helper = bytes(rom_data[helper_off:helper_off + len(helper)])
    cur_start = bytes(rom_data[start_off:start_off + len(start_orig)])
    if cur_start not in (start_orig, start_hook):
        raise TitleScreenError(
            f"title start clear hook signature mismatch at "
            f"${_WT_TITLE_START_CLEAR_CPU:04X}: got {cur_start.hex(' ')}")
    changed = cur_helper != helper or cur_start != start_hook
    rom_data[helper_off:helper_off + len(helper)] = helper
    rom_data[start_off:start_off + len(start_hook)] = start_hook
    return changed


def apply_wide_title_idle_demo_cleanup(rom_data) -> list:
    """Install the timeout-only demo clear hook on current wide-title ROMs."""
    if not _wt_has_current_ram_bootstrap(rom_data):
        return []
    changed = _wt_install_title_oam_clear(rom_data)
    changed = _wt_install_idle_demo_cleanup(rom_data) or changed
    if not changed:
        return []
    return [
        "wide-title title/demo OAM cleanup installed"
    ]


def _wt_title_oam_helper(cpu_base: int, return_cpu: int,
                         table: bytes | bytearray | None = None) -> bytes:
    """Build the PRG1-only title main-slot writer.

    It copies a fixed 20-slot title character table into main entity slots
    1-20. The stock per-frame OAM writer then draws those slots normally.
    """
    raw = bytes(_wt_title_oam_default_table() if table is None else table)
    if len(raw) != _WT_TITLE_SLOT_TABLE_BYTES:
        raise TitleScreenError(
            f"title character slot table must be {_WT_TITLE_SLOT_TABLE_BYTES}B.")
    code_len = _WT_TITLE_CHARACTER_MAX * (2 + 6 * 6) + 3
    table_cpu = (int(cpu_base) + code_len) & 0xFFFF
    code = bytearray()
    dst_fields = (0, 7, 10, 17, 18, 19)
    for slot in range(_WT_TITLE_CHARACTER_MAX):
        src = slot * _WT_TITLE_SLOT_ENTRY_BYTES
        dst = _WT_TITLE_SLOT0_BASE + (slot + 1) * _WT_TITLE_SLOT_STRIDE
        code += bytes((0xA2, src & 0xFF))  # LDX #table entry offset
        for rel, field in enumerate(dst_fields):
            addr = (table_cpu + rel) & 0xFFFF
            code += bytes((0xBD, addr & 0xFF, (addr >> 8) & 0xFF))
            daddr = (dst + field) & 0xFFFF
            code += bytes((0x8D, daddr & 0xFF, (daddr >> 8) & 0xFF))
    code += bytes((0x4C, return_cpu & 0xFF, (return_cpu >> 8) & 0xFF))
    assert len(code) == code_len
    return bytes(code) + raw


def _attr_palette_no_from_expanded(attr, row, col) -> int:
    if len(attr) >= _WT_TITLE_ATTR_BLOCK_COUNT:
        br = int(row) // 2
        bc = int(col) // 2
        bi = br * _WT_TITLE_ATTR_BLOCK_W + bc
        if 0 <= br < _WT_TITLE_ATTR_BLOCK_H and 0 <= bc < _WT_TITLE_ATTR_BLOCK_W:
            return int(attr[bi]) & 0x03
        return 0
    ai = (int(row) // 4) * 8 + (int(col) // 4)
    if not (0 <= ai < len(attr)):
        return 0
    qx = (int(col) % 4) // 2
    qy = (int(row) % 4) // 2
    return (int(attr[ai]) >> ((qy * 2 + qx) * 2)) & 0x03


def _expanded_attr_from_table(table: bytes | bytearray) -> list[int]:
    raw = bytes(table)
    if len(raw) != _WT_TITLE_ATTR_TABLE_BYTES:
        raise TitleScreenError(
            f"title attribute table must be {_WT_TITLE_ATTR_TABLE_BYTES}B.")
    attr = [0] * _WT_TITLE_ATTR_BLOCK_COUNT
    for br in range(_WT_TITLE_ATTR_BLOCK_H):
        for bc in range(_WT_TITLE_ATTR_BLOCK_W):
            ai = (br // 2) * 8 + (bc // 2)
            qx = bc & 1
            qy = br & 1
            shift = (qy * 2 + qx) * 2
            attr[br * _WT_TITLE_ATTR_BLOCK_W + bc] = (
                raw[ai] >> shift) & 0x03
    return attr


def _pack_expanded_attr_table(attr) -> bytes:
    out = bytearray(_WT_TITLE_ATTR_TABLE_BYTES)
    for br in range(_WT_TITLE_ATTR_BLOCK_H):
        for bc in range(_WT_TITLE_ATTR_BLOCK_W):
            pal = _attr_palette_no_from_expanded(attr, br * 2, bc * 2)
            ai = (br // 2) * 8 + (bc // 2)
            qx = bc & 1
            qy = br & 1
            out[ai] |= (pal & 0x03) << ((qy * 2 + qx) * 2)
    return bytes(out)


def _legacy_title_attr_expanded(rom_data) -> list[int]:
    region = _verify(rom_data)
    base = region_mod.base_region(region)
    attr = [0xFF] * 64
    if base in _TITLE_PIECES:
        off, ln = _TITLE_PIECES[base]["attribute"]
        if off + ln <= len(rom_data):
            src = bytes(rom_data[off:off + ln])
            for i in range(min(21, ln)):
                attr[9 + i] = src[20 - i]
    if base == "JP":
        off2 = 0x10 + (0xCDF5 - 0x8000)
        if off2 + 7 <= len(rom_data):
            src = bytes(rom_data[off2:off2 + 7])
            for i in range(7):
                attr[48 + i] = src[6 - i]
        for i in range(8):
            attr[56 + i] = 0xF5
    return attr


def _wt_attr_table_default(rom_data) -> bytes:
    return _pack_expanded_attr_table(_legacy_title_attr_expanded(rom_data))


def _wt_title_attr_helper(cpu_base: int, next_cpu: int,
                          table: bytes | bytearray) -> bytes:
    raw = bytes(table)
    if len(raw) != _WT_TITLE_ATTR_TABLE_BYTES:
        raise TitleScreenError(
            f"title attribute table must be {_WT_TITLE_ATTR_TABLE_BYTES}B.")
    table_cpu = (int(cpu_base) + _WT_TITLE_ATTR_WRITER_CODE_BYTES) & 0xFFFF
    ppu = _WT_TITLE_ATTR_PPU
    code = bytes((
        0xAD, 0x02, 0x20,                    # LDA $2002
        0xA9, (ppu >> 8) & 0xFF,             # LDA #>PPU
        0x8D, 0x06, 0x20,                    # STA $2006
        0xA9, ppu & 0xFF,                    # LDA #<PPU
        0x8D, 0x06, 0x20,                    # STA $2006
        0xA0, 0x00,                          # LDY #0
        0xB9, table_cpu & 0xFF, (table_cpu >> 8) & 0xFF,
        0x8D, 0x07, 0x20,                    # STA $2007
        0xC8,                                # INY
        0xC0, 0x40,                          # CPY #64
        0xD0, 0xF5,                          # BNE loop
        0x4C, next_cpu & 0xFF, (next_cpu >> 8) & 0xFF,
    ))
    assert len(code) == _WT_TITLE_ATTR_WRITER_CODE_BYTES
    return code + raw


def _wt_title_attr_table_file() -> int:
    core = _assemble_wa_decoder(_WT_DEC_CPU, prog=list(_WA_PROG[:-1]))
    return _WT_DEC_FILE + len(core) + _WT_TITLE_ATTR_WRITER_CODE_BYTES


def _wt_has_current_title_attr_helper(rom_data) -> bool:
    core = _assemble_wa_decoder(_WT_DEC_CPU, prog=list(_WA_PROG[:-1]))
    attr_cpu = (_WT_DEC_CPU + len(core)) & 0xFFFF
    next_cpu = (attr_cpu + _WT_TITLE_ATTR_WRITER_CODE_BYTES +
                _WT_TITLE_ATTR_TABLE_BYTES) & 0xFFFF
    helper = _wt_title_attr_helper(
        attr_cpu, next_cpu, bytes(_WT_TITLE_ATTR_TABLE_BYTES))
    code = helper[:_WT_TITLE_ATTR_WRITER_CODE_BYTES]
    start = _WT_DEC_FILE + len(core)
    end = start + len(code)
    return end <= len(rom_data) and bytes(rom_data[start:end]) == code


def _wt_read_title_attr_table_or_default(rom_data) -> bytes:
    start = _wt_title_attr_table_file()
    end = start + _WT_TITLE_ATTR_TABLE_BYTES
    if _wt_has_current_title_attr_helper(rom_data) and end <= len(rom_data):
        return bytes(rom_data[start:end])
    return _wt_attr_table_default(rom_data)


def read_title_attribute_expanded(rom_data) -> list[int]:
    if is_wide_normalized(rom_data):
        return _expanded_attr_from_table(
            _wt_read_title_attr_table_or_default(rom_data))
    return _legacy_title_attr_expanded(rom_data)


def set_title_attribute_expanded(rom_data, attr) -> list:
    grid_a, grid_b = _wide_title_grids_for_edit(rom_data)
    table = _pack_expanded_attr_table(attr)
    len_a, len_b = _write_wide_title_streams_for_import(
        rom_data, grid_a, grid_b, title_attr_table=table)
    return [
        f"title attribute blocks updated: {_WT_TITLE_ATTR_BLOCK_COUNT}",
        f"bank1 streams rewritten: A={len_a}B / B={len_b}B",
    ]


def _wt_build_trampoline(decoder_cpu, *, title_oam: bool = True,
                         title_oam_table: bytes | bytearray | None = None,
                         title_attr_table: bytes | bytearray | None = None):
    """bootstrap(bank0 $CC4F) と bank1 decoder バイト列を生成。

    戻り: (boot_bytes, decoder_bytes)
      boot_bytes  : $CC4F に置く 28B (コピーstub14B + RAM template14B)
      decoder_bytes: bank1 $80C0 に置く arcade decoder (末尾 JMP RAM_OUT)
    RAM template (boot 内に同梱・実行時 $072C へコピー):
      RAM_IN  @$072C 8B: A9 13 / 8D 86 BB / 4C <declo> <dechi>
      RAM_OUT @$0734 6B: A9 03 / 8D 86 BB / 60
    """
    sw_lo, sw_hi = _WT_SW_CPU & 0xFF, (_WT_SW_CPU >> 8) & 0xFF
    d_lo, d_hi = decoder_cpu & 0xFF, (decoder_cpu >> 8) & 0xFF
    ram_tmpl = bytes([
        0xA9, 0x13, 0x8D, sw_lo, sw_hi, 0x4C, d_lo, d_hi,   # RAM_IN 8B
        0xA9, 0x03, 0x8D, sw_lo, sw_hi, 0x60,               # RAM_OUT 6B
    ])
    assert len(ram_tmpl) == 14
    tmpl_cpu = 0xCC4F + 14                 # template はコード14B直後
    t_lo, t_hi = tmpl_cpu & 0xFF, (tmpl_cpu >> 8) & 0xFF
    ri_lo, ri_hi = _WT_RAM_IN & 0xFF, (_WT_RAM_IN >> 8) & 0xFF
    boot_code = bytes([
        0xA2, 0x0D,                        # LDX #$0D  (14B, X=13..0)
        0xBD, t_lo, t_hi,                  # LDA tmpl,X
        0x9D, ri_lo, ri_hi,                # STA $072C,X
        0xCA,                              # DEX                ($CC57)
        0x10, 0xF7,                        # BPL $CC51 (disp -9) ($CC58)
        0x4C, ri_lo, ri_hi,                # JMP $072C (RAM_IN)  ($CC5A)
    ])
    assert len(boot_code) == 14
    boot_bytes = boot_code + ram_tmpl      # 28B
    # decoder: _WA_PROG の末尾 RTS を RAM_OUT への復帰に差替え
    prog = list(_WA_PROG[:-1])
    decoder_bytes = _assemble_wa_decoder(decoder_cpu, prog=prog)
    attr_table = bytes(_WT_TITLE_ATTR_TABLE_BYTES
                       ) if title_attr_table is None else bytes(title_attr_table)
    if len(attr_table) != _WT_TITLE_ATTR_TABLE_BYTES:
        raise TitleScreenError(
            f"title attribute table must be {_WT_TITLE_ATTR_TABLE_BYTES}B.")
    attr_cpu = (decoder_cpu + len(decoder_bytes)) & 0xFFFF
    oam_cpu = (attr_cpu + _WT_TITLE_ATTR_WRITER_CODE_BYTES +
               _WT_TITLE_ATTR_TABLE_BYTES) & 0xFFFF
    decoder_bytes += _wt_title_attr_helper(attr_cpu, oam_cpu, attr_table)
    if title_oam:
        decoder_bytes += _wt_title_oam_helper(
            (decoder_cpu + len(decoder_bytes)) & 0xFFFF, _WT_RAM_OUT,
            title_oam_table)
    else:
        decoder_bytes += bytes((
            0x4C, _WT_RAM_OUT & 0xFF, (_WT_RAM_OUT >> 8) & 0xFF))
    return boot_bytes, decoder_bytes


def _wt_current_decoder_bytes(*, title_oam: bool = True,
                              title_oam_table: bytes | bytearray | None = None,
                              title_attr_table: bytes | bytearray | None = None) -> bytes:
    _boot, decoder = _wt_build_trampoline(
        _WT_DEC_CPU, title_oam=title_oam, title_oam_table=title_oam_table,
        title_attr_table=title_attr_table)
    return decoder


def _wt_uses_len_stream(rom_data) -> bool:
    """True when the installed bank1 decoder is the LEN-stream decoder."""
    if not _wt_has_current_ram_bootstrap(rom_data):
        return False
    dec = _wt_current_decoder_bytes()
    cur = bytes(rom_data[_WT_DEC_FILE:_WT_DEC_FILE + len(dec)])
    if len(cur) != len(dec):
        return False
    core_len = len(_assemble_wa_decoder(
        _WT_DEC_CPU, prog=list(_WA_PROG[:-1])))
    return cur[:core_len] == dec[:core_len]


def _assemble_wa_decoder(base_cpu=0xCC4F, prog=None):
    """wide デコーダを base_cpu 基準でアセンブル。
    prog=None なら _WA_PROG (末尾 RTS = in-place/legacy)。
    prog 指定で末尾を JMPABS に差替えた版 (bank1 trampoline) を生成。
    JMPABS = ("JMPABS", 絶対CPUアドレス) — ラベルでなく即値 JMP。
    """
    if prog is None:
        prog = _WA_PROG
    lab, pc = {}, base_cpu
    for it in prog:
        if len(it) == 1 and it[0] not in _WA_OPC:
            lab[it[0]] = pc
        else:
            pc += _WA_SZ[it[0]]
    code, pc = bytearray(), base_cpu
    for it in prog:
        op = it[0]
        if len(it) == 1 and op not in _WA_OPC:
            continue
        code.append(_WA_OPC[op])
        if _WA_SZ[op] == 1:
            pc += 1
        elif op in ("BEQ", "BNE", "BCC"):
            code.append((lab[it[1]] - (pc + 2)) & 0xFF)
            pc += 2
        elif op == "JMP":
            code += bytes([lab[it[1]] & 0xFF, (lab[it[1]] >> 8) & 0xFF])
            pc += 3
        elif _WA_SZ[op] == 2:
            code.append(it[1] & 0xFF)
            pc += 2
        else:
            code += bytes([it[1] & 0xFF, (it[1] >> 8) & 0xFF])
            pc += 3
    return bytes(code)


def _wa_grid(src, start_cpu):
    w = decode_arcade_stream(src, _wjp_cf(start_cpu))
    g = [None] * _NT_CELLS
    for a, t in w:
        i = a - ARCADE_NT_BASE
        if 0 <= i < _NT_CELLS:
            g[i] = t
    return g, len(w)


def apply_wide_arcade_title(target_rom, source_rom) -> list:
    """★広域 arcade タイトルを ★JP ROM(target) へ移植。
    arcade の絵/配置(CHR bank3 / stream block1+2 / $CCAF
    attribute)は ★source_rom(ユーザー所有の arcade-wide-title
    ROM)から抽出。当方 6502 デコーダ + 色 patch 定数のみ埋め込み。
    全パッチ before 署名検証、不一致は TitleScreenError で中止
    (フォールバック禁止)。確定 recipe(R201 /
    build_TitleWide_JP_v9.py、実機検証 CRC0BF323D8)と byte 等価。

    制約: target は ★JP/JP66 のみ (cave/番地が JP 固有。US$9604
    相当を JP 同番地に当てると破壊ゆえ US 不可)。
    """
    raise TitleScreenError(
        "apply_wide_arcade_title is disabled: the old v9 recipe writes to "
        "the bank0 Room Flag cave. Use normalize_title_to_wide() and "
        "transcode_title() instead.")
    tgt_region = _verify(target_rom)
    src_region = _verify(source_rom)
    if region_mod.base_region(tgt_region) != "JP":
        raise TitleScreenError(
            "広域 arcade タイトルは ★JP ROM 専用です "
            f"(対象 region={tgt_region})。US 等には適用不可"
            "(cave/番地が JP 固有)。")

    g1, n1 = _wa_grid(source_rom, 0xCD5F)
    g2, n2 = _wa_grid(source_rom, 0xCDF5)
    if n1 < 100 or n2 < 150:
        raise TitleScreenError(
            f"移植元が arcade 広域タイトル ROM ではありません "
            f"(block1={n1}/block2={n2} writes、期待 ≳135/≳233)。"
            "アーケード版バナー適用済の所有 ROM を指定してください。")
    s_chr = chr_bank3_offset(source_rom)
    s_ccaf = _wjp_cf(0xCCAF)
    if s_chr + CHR_BANK_SIZE > len(source_rom) or \
            s_ccaf + 21 > len(source_rom):
        raise TitleScreenError("移植元 ROM が小さすぎます。中止。")

    for cpu, sig in _WJP_SIG.items():
        o = _wjp_cf(cpu)
        if bytes(target_rom[o:o+len(sig)]) != sig:
            raise TitleScreenError(
                f"対象 JP ROM の ${cpu:04X} が想定(clean JP)と"
                "不一致。改造/別版の可能性ゆえ中止 (本機能は "
                "clean JP / 本アプリ把握の JP のみ)。")
    cd58_o = _wjp_cf(0xCD58)
    if bytes(target_rom[cd58_o:cd58_o+21]) != _WJP_CD58_BEFORE:
        raise TitleScreenError(
            "$CD58(attribute)が clean JP と不一致。中止。")
    for off, before, _aft in _WJP_COLOR:
        if bytes(target_rom[off:off+len(before)]) != before:
            raise TitleScreenError(
                f"色 patch 0x{off:X} が想定 before と不一致。中止。")

    o, e, r0, best = _wjp_cf(0xBBDE), _wjp_cf(0xC200), None, None
    while o < e:
        if target_rom[o] == 0xEA:
            if r0 is None:
                r0 = o
            if o - r0 + 1 >= 280:
                best = r0
                break
        else:
            r0 = None
        o += 1
    if best is None:
        raise TitleScreenError(
            "JP cave ($BBDE-$C1FF 280B 連続$EA) 未確保。中止。")
    cave_cpu = 0x8000 + (best - 0x10)

    code = _assemble_wa_decoder(0xCC4F)
    if len(code) > _wjp_cf(0xCCB6) - _wjp_cf(0xCC4F):
        raise TitleScreenError("内部エラー: デコーダ枠超過。")

    gb = list(g1)
    for k in range(18):
        gb[_WJP_CBC3_STRIP0 + k] = 0x63 + k          # tile $63..$74
    banner = encode_arcade_stream(gb)
    mount = encode_arcade_stream(g2)
    cap_cea3 = _wjp_cf(0xCF9A) - _wjp_cf(0xCEA3)
    ci, carun = best, 0
    while target_rom[ci] == 0xEA:
        carun += 1
        ci += 1
    if len(banner) > cap_cea3:
        raise TitleScreenError(
            f"banner {len(banner)}B が枠 {cap_cea3}B 超過。中止。")
    if len(mount) > carun:
        raise TitleScreenError(
            f"山 {len(mount)}B が cave {carun}B 超過。中止。")

    t_chr = chr_bank3_offset(target_rom)
    if t_chr + CHR_BANK_SIZE > len(target_rom):
        raise TitleScreenError("対象 CHR bank3 が範囲外。中止。")
    target_rom[_wjp_cf(0xCC4F):_wjp_cf(0xCC4F)+len(code)] = code
    target_rom[_wjp_cf(0xCEA3):_wjp_cf(0xCEA3)+len(banner)] = banner
    target_rom[best:best+len(mount)] = bytes(mount)
    target_rom[_wjp_cf(0xCCBA)] = cave_cpu & 0xFF
    target_rom[_wjp_cf(0xCCBE)] = (cave_cpu >> 8) & 0xFF
    target_rom[t_chr:t_chr+CHR_BANK_SIZE] = \
        bytes(source_rom[s_chr:s_chr+CHR_BANK_SIZE])
    target_rom[cd58_o:cd58_o+21] = \
        bytes(source_rom[s_ccaf:s_ccaf+21])
    for off, _bf, after in _WJP_COLOR:
        target_rom[off:off+len(after)] = after

    return [
        f"広域 arcade タイトルを JP へ移植 ({src_region}→"
        f"{tgt_region})。decoder@$CC4F / banner@$CEA3 "
        f"({len(banner)}B) / 山@${cave_cpu:04X} ({len(mount)}B) / "
        f"$CCB6→cave / CHR bank3 / $CD58←$CCAF / 色4点。",
        "※実機/エミュで要確認 (タイトル / 1面前 SHRINE-ROOM / "
        "ゲーム内 / デモ・コンティニュー)。",
    ]


def _grid_from_cc4f(rom, start_cpu):
    """ROM 自身の stock タイトルブロックを stock $CC4F 形式で
    decode し (grid[960], writes数)。decode_title_grid と同じ
    セル化 (addr & $3FF)。外部 ROM 不要。"""
    w, _end = _decode_cc4f(bytes(rom), _wjp_cf(start_cpu))
    g = [None] * _NT_CELLS
    n = 0
    for ad, t in w:
        c = ad & 0x3FF
        if c < _NT_CELLS:
            g[c] = t
            n += 1
    return g, n


def normalize_title_to_wide(rom) -> list:
    """★その ROM 自身の stock タイトルを ★見た目そのまま 当方
    wide(arcade)形式へ正規化 (外部 ROM 不要・読込時自動)。

    機構 = RAM-trampoline + bank1 (2026-05-19 確定。設計詳細=
    docs/wide_title_trampoline_design.html / memory)。
      ・decoder 本体 + blockA/B stream は ★PRG bank1 空き
        (file 0x80D0〜) に配置。bank0 cave ($BBDE-$C1FF=Room Flag
        占有) は ★一切使わない。
      ・$CC4F = bootstrap (RAM へ 14B trampoline をコピー→JMP)。
        RAM_IN が PRG bank1 へ切替 ($BB86 bus競合) → bank1 decoder
        → RAM_OUT が bank0 復帰 → RTS (純サブルーチン・スタック
        不可侵)。RAM 実行ゆえ bank 切替免疫。
      ・呼出元 $CCB6/$CD76 の stream ポインタ即値を bank1 アドレス
        へ repoint。NMI off 窓 ($9673/$965F) の内側・$2000/$0300
        不可侵。CHR=bank3 固定ゆえタイトル絵不変。
    ★視覚完全同一 (attribute $CD58 / palette / CHR / 色 ★非改変)。
    ★JP 拡張ROM (JP66) 専用。全署名検証・round-trip 自己検証、
    不一致は TitleScreenError で中止 (フォールバック/部分書込禁止)。
    """
    region = _verify(rom)
    if region_mod.base_region(region) != "JP":
        raise TitleScreenError(
            "タイトル wide 正規化は ★JP 専用です "
            f"(region={region})。US は非対応 (本アプリ JP 専用方針)。")
    if len(rom) != 0x18010:                      # 98320 = mapper66 拡張ROM
        raise TitleScreenError(
            f"タイトル wide 正規化は ★拡張ROM (mapper66) 専用です "
            f"(size={len(rom)}B != 98320)。先に m66 拡張が必要 "
            "(bank1 が無いと配置不可)。中止。")

    # --- (1) 署名検証 (clean JP stock title 機構) ---
    for cpu, sig in _WJP_SIG.items():
        o = _wjp_cf(cpu)
        if bytes(rom[o:o+len(sig)]) != sig:
            raise TitleScreenError(
                f"${cpu:04X} が stock JP タイトル機構と不一致 "
                "(既に改造済/別版の可能性)。正規化を中止。")
    cbo = _wjp_cf(_WT_CALLERB_CPU)
    if bytes(rom[cbo:cbo+len(_WT_CALLERB_SIG)]) != _WT_CALLERB_SIG:
        raise TitleScreenError(
            f"${_WT_CALLERB_CPU:04X} (block-B 呼出列) が stock JP と"
            "不一致。正規化を中止。")
    if rom[_WT_SW_B0_OFF] != 0xFF:
        raise TitleScreenError(
            f"SW bank0 (file 0x{_WT_SW_B0_OFF:X} = $BB86) が $FF で"
            "ありません。改造/別版の可能性ゆえ中止。")

    # --- (2) stock タイトル 2 ブロックを decode (見た目の真実) ---
    gA, nA = _grid_from_cc4f(rom, 0xCE08)        # block A (caller $CCB6)
    gB, nB = _grid_from_cc4f(rom, 0xCEA3)        # block B (caller $CD76)
    if nA < 50 or nB < 50:
        raise TitleScreenError(
            f"stock タイトル decode 異常 (A={nA}/B={nB})。中止。")
    orig = {}
    for c in range(_NT_CELLS):
        if gA[c] is not None:
            orig[c] = gA[c]
        if gB[c] is not None:
            orig[c] = gB[c]
    blkA = encode_len_stream(gA)
    blkB = encode_len_stream(gB)

    # --- (3) bootstrap / bank1 decoder 生成 + bank1 レイアウト ---
    boot, decoder = _wt_build_trampoline(_WT_DEC_CPU)
    if len(boot) > _wjp_cf(0xCCB6) - _wjp_cf(0xCC4F):
        raise TitleScreenError("内部エラー: bootstrap 枠超過。")
    dec_file = _WT_DEC_FILE
    blkA_file = dec_file + len(decoder)
    blkB_file = blkA_file + len(blkA)
    region_end = blkB_file + len(blkB)
    if region_end > _WT_WIDE_END:                # wide-title reserved range only
        raise TitleScreenError(
            f"bank1 widetitle ({region_end - dec_file}B) が reserved range "
            f"(file 0x{_WT_WIDE_END:X}) を超過。中止。")
    blkA_cpu = 0x8000 + (blkA_file - 0x8010)
    blkB_cpu = 0x8000 + (blkB_file - 0x8010)

    # --- (4) bank1 配置域が全0 (他改造未使用) / SW 予約 byte 検証 ---
    if any(rom[dec_file:region_end]):
        raise TitleScreenError(
            f"bank1 配置域 (file 0x{dec_file:X}-0x{region_end:X}) に "
            "既存データ。他改造と競合の恐れゆえ中止。")
    if rom[_WT_SW_B1_OFF] != 0x00:
        raise TitleScreenError(
            f"bank1 SW 予約 byte (file 0x{_WT_SW_B1_OFF:X}) が空きで"
            "ありません。中止。")

    # --- (5) Room Flag 占有帯に書込が一切無いことを保証 ---
    writes = [
        (_wjp_cf(0xCC4F), len(boot)),
        (dec_file, len(decoder)),
        (blkA_file, len(blkA)),
        (blkB_file, len(blkB)),
        (_WT_SW_B1_OFF, 1),
        (_wjp_cf(_WT_PTRA_LO), 1), (_wjp_cf(_WT_PTRA_HI), 1),
        (_wjp_cf(_WT_PTRB_LO), 1), (_wjp_cf(_WT_PTRB_HI), 1),
    ]
    rf_s, rf_e = _RF_BAND
    for off, ln in writes:
        if off < rf_e and off + ln > rf_s:
            raise TitleScreenError(
                f"内部エラー: 書込 0x{off:X}+{ln}B が Room Flag 帯 "
                f"[0x{rf_s:X},0x{rf_e:X}) と交差。中止。")

    # --- (6) 全署名 OK。ここで初めて一括書込 (部分書込なし) ---
    out = bytearray(rom)
    out[_wjp_cf(0xCC4F):_wjp_cf(0xCC4F)+len(boot)] = boot
    out[dec_file:dec_file+len(decoder)] = decoder
    out[blkA_file:blkA_file+len(blkA)] = blkA
    out[blkB_file:blkB_file+len(blkB)] = blkB
    out[_WT_SW_B1_OFF] = 0xFF                     # bank1 SW = $FF 予約
    out[_wjp_cf(_WT_PTRA_LO)] = blkA_cpu & 0xFF
    out[_wjp_cf(_WT_PTRA_HI)] = (blkA_cpu >> 8) & 0xFF
    out[_wjp_cf(_WT_PTRB_LO)] = blkB_cpu & 0xFF
    out[_wjp_cf(_WT_PTRB_HI)] = (blkB_cpu >> 8) & 0xFF
    _wt_install_title_oam_clear(out)
    _wt_install_idle_demo_cleanup(out)
    # ★$CD58 / palette / CHR / 色 は ★非改変 (視覚同一)。
    # Title OAM clear uses the wide-title-owned title code at $CC6B.
    # NMI hook / DARK code / generic bank0 cave are not used for this display.

    # --- (7) round-trip 自己検証: bank1 stream 再decode == 元 stock ---
    rt = {}
    for st in (blkA_file, blkB_file):
        for ad, t in decode_len_stream(out, st):
            c = ad - ARCADE_NT_BASE
            if 0 <= c < _NT_CELLS:
                rt[c] = t
    if rt != orig:
        raise TitleScreenError(
            "正規化 round-trip 不一致 (視覚が変わる恐れ)。中止。")

    rom[:] = out
    return [
        f"タイトルを stock→当方wide形式へ正規化 ({region}・"
        "見た目そのまま)。RAM-trampoline + bank1 機構: "
        f"bootstrap@$CC4F ({len(boot)}B) / decoder@$"
        f"{_WT_DEC_CPU:04X} / blockA@${blkA_cpu:04X} ({len(blkA)}B) "
        f"/ blockB@${blkB_cpu:04X} ({len(blkB)}B) / SW=$BB86 / "
        f"RAM $072C。title OAM clear $CC6B ({len(_wt_title_oam_clear_helper())}B)・"
        "attribute/palette/CHR 非改変・round-trip "
        f"{len(rt)}セル一致で視覚同一を確認。",
        "※実機で要確認 (タイトルが stock と同一表示か / Room Flag/"
        "暗闇/隠し扉 併用 / テストプレイ / SHRINE-ROOM / デモ / "
        "START / continue)。",
    ]

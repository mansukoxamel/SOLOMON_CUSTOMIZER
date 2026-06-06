"""特殊処理 (Per-Room Special Process) の解析

BESK (Binary Editor for Solomon's Key) を逆コンパイルして判明した構造:

- 各ルームごとに 6502 アセンブラのサブルーチンが ROM に格納されている
- ディスパッチテーブル: 14バイト (7セクション×lo/hi byte) + 53バイト (各レベルのオフセット)
- レベル N の特殊処理 ROM オフセット:
    section_idx = N // 8
    section_base = rom[table + section_idx*2] + rom[table + section_idx*2 + 1] * 256 - 0x7FF0
    level_offset = rom[table + 14 + N]
    addr = section_base + level_offset
- 終端: 0x60 (RTS) または 0x4C ** ** (JMP abs)

リージョン別ディスパッチテーブル先頭:
- JP:  0x3404
- USA: 0x3834

============================================================
BESK のパースアルゴリズムとの対応関係:
============================================================

BESK のソース (BinaryEditor.cs) には以下の検出関数があり、本モジュールはそれと
等価な検出ロジックを実装している:

【SP1 (BESK)】= 「アイテム複数配置（位置テーブル経由）」
  パターン:
    LDA #$F8; STA $0304; LDA #$??; LDX #$??; LDY $????,X; STA $0304,Y; DEX; BPL -9
  (BESK: SP1Check / SP1LengAdd / SP1Initial)
  → 本モジュール: find_marks() の「LDY $XXXX,X → STA $0304,Y」検出ロジックで対応
  → 例: Level 49 の 12マス連動配置 (位置テーブル $BBA6 = ROM 0x3BB6 経由)

【SP2 (BESK)】= 「アイテムビットマップ配置」
  パターン:
    JSR $BB9E; LDA #?; STA $00; LDA #?; STA $01; LDA #?; (JMP/JSR) $99CE
  (BESK: SP2Check / SP2Add / SP2Initial)
  → 16×12 ビットマップ (24バイト) に従って指定アイテムコードを一括配置
  → 例: Level 20 で Bat Symbol (0x04) を bitmap で配置
  → 本モジュール: 壊せる壁マーカーには影響しないため未対応 (主にアイテム用)

【その他】
  本モジュール独自の検出:
  - 直接 STA: LDA #$XX; STA $03YY
  - 範囲 STA (X): LDX #N; STA $03YY,X; DEX; BPL -k
  - 前方分岐 (BEQ/BNE/BPL/BMI/BCC/BCS) を追跡して RTS 後のコードも探索
  → これにより Level 52 の (6,3)(7,3)(8,3) のような「BEQ で飛んで Part 2 が実行」
    というパターンも捕捉可能 (BESK 自体はビューアなのでこのレベルの解析は不要)
"""
from . import constants as c


# リージョン別ディスパッチテーブル先頭
DISPATCH_TABLE_OFFSET = {
    "JP":  0x3404,
    "US":  0x3834,
}

NUM_LEVELS = 53
SECTION_HEADER_BYTES = 14  # 7セクション × 2バイト (lo/hi)
RAM_TO_ROM_DIFF = 0x7FF0


# ---- 6502 オペコード長テーブル (256要素) ----
_LEN = [3] * 256  # 既定: absolute 系 = 3バイト

# 1バイト命令 (implied / accumulator)
for _op in [0x00, 0x08, 0x0a, 0x18, 0x28, 0x2a, 0x38, 0x40, 0x48, 0x4a,
            0x58, 0x60, 0x68, 0x6a, 0x78, 0x88, 0x8a, 0x98, 0x9a, 0xa8,
            0xaa, 0xb8, 0xba, 0xc8, 0xca, 0xd8, 0xe8, 0xea, 0xf8]:
    _LEN[_op] = 1

# 2バイト命令 (immediate / zp / zp,X / zp,Y / (zp,X) / (zp),Y / relative)
for _op in [
    # immediate
    0x09, 0x29, 0x49, 0x69, 0x89, 0xa9, 0xc9, 0xe9, 0xa0, 0xa2, 0xc0, 0xe0,
    # zero page
    0x05, 0x25, 0x45, 0x65, 0x85, 0xa5, 0xc5, 0xe5,
    0x06, 0x26, 0x46, 0x66, 0x86, 0xa6, 0xc6, 0xe6,
    0x24, 0x84, 0xa4, 0xc4, 0xe4,
    # zp,X
    0x15, 0x35, 0x55, 0x75, 0x95, 0xb5, 0xd5, 0xf5,
    0x16, 0x36, 0x56, 0x76, 0xd6, 0xf6, 0x94, 0xb4,
    # zp,Y
    0x96, 0xb6,
    # (zp,X) / (zp),Y
    0x01, 0x21, 0x41, 0x61, 0x81, 0xa1, 0xc1, 0xe1,
    0x11, 0x31, 0x51, 0x71, 0x91, 0xb1, 0xd1, 0xf1,
    # branch
    0x10, 0x30, 0x50, 0x70, 0x90, 0xb0, 0xd0, 0xf0,
]:
    _LEN[_op] = 2


def _opcode_length(opcode: int) -> int:
    return _LEN[opcode & 0xff]


def special_length(rom_data: bytes, start: int) -> int:
    """特殊処理ルーチンの長さを計算。0x60 (RTS) または 0x4C (JMP abs) で終端。"""
    i = start
    while i < len(rom_data):
        b = rom_data[i]
        if b == 0x60:  # RTS
            return i + 1 - start
        if b == 0x4c:  # JMP abs (3バイト)
            return i + 3 - start
        i += _opcode_length(b)
    return len(rom_data) - start


def get_dispatch_table(region: str) -> int:
    """リージョンからディスパッチテーブル先頭オフセットを返す。未知なら None。"""
    return DISPATCH_TABLE_OFFSET.get(region)


def get_special_process_address(rom_data: bytes, region: str, level_no: int) -> int:
    """レベル N (0-indexed) の特殊処理開始ROMアドレスを計算。

    Returns:
        ROM オフセット (int) または -1 (リージョン未対応時)
    """
    table = get_dispatch_table(region)
    if table is None:
        return -1
    section_idx = level_no // 8
    lo = rom_data[table + section_idx * 2]
    hi = rom_data[table + section_idx * 2 + 1]
    section_base = lo + hi * 256 - RAM_TO_ROM_DIFF
    level_offset = rom_data[table + SECTION_HEADER_BYTES + level_no]
    return section_base + level_offset


def get_special_process_bytes(rom_data: bytes, region: str, level_no: int):
    """レベル N の特殊処理バイト列と開始アドレスを返す。

    Returns:
        (addr, bytes) または (None, None) (未対応リージョン)
    """
    addr = get_special_process_address(rom_data, region, level_no)
    if addr < 0:
        return None, None
    length = special_length(rom_data, addr)
    return addr, bytes(rom_data[addr:addr + length])


ITEM_BITMASK_SP2_SIGNATURES = {
    ("JP", 19): bytes.fromhex("20 9e bb a9 b2 85 00 a9 bb 85 01 a9 04 20 ce 99"),
    ("JP", 29): bytes.fromhex("20 9e bb a9 ca 85 00 a9 bb 85 01 a9 27 20 ce 99"),
    ("US", 19): bytes.fromhex("20 ce bf a9 e2 85 00 a9 bf 85 01 a9 04 20 ce 99"),
    ("US", 29): bytes.fromhex("20 ce bf a9 fa 85 00 a9 bf 85 01 a9 27 20 ce 99"),
}


def disable_imported_item_bitmask_processes(rom_data: bytearray, region: str) -> list[str]:
    """Disable original SP2 bitmap item placement after importing it as level data.

    Level 20 Bat Symbol and Level 30 Blue Opal are imported into editable stage
    data on raw-ROM load. In mapper66 saves the original bitmap routine must not
    run again, especially because later code caves can occupy the old bitmap
    byte range.
    """
    changed = []
    for level_no in (19, 29):
        sig = ITEM_BITMASK_SP2_SIGNATURES.get((region, level_no))
        if sig is None:
            continue
        addr = get_special_process_address(rom_data, region, level_no)
        if addr < 0:
            continue
        cur = bytes(rom_data[addr:addr + len(sig)])
        nops = bytes([0xEA] * len(sig))
        if cur == nops:
            continue
        if cur != sig:
            raise ValueError(
                f"Level {level_no + 1} item bitmap special process signature mismatch "
                f"at 0x{addr:04X}: got {cur.hex(' ')}"
            )
        rom_data[addr:addr + len(sig)] = nops
        changed.append(f"Stage {level_no + 1}")
    return changed


# ---- 既知のサブルーチン呼び出しパターン (注釈用) ----
# (region, ROMオフセット差) を考慮するために RAM アドレスベースで持つ
# RAM addr → 説明

KNOWN_SUBROUTINES_JP = {
    0xB9BA: "アイテムを背景に隠す (直前配置を白壁化)",
    0xBB7A: "ソロモン封印 配置 (引数 A = フラグbit)",
    0xB49C: "テクモプレート 配置 (座標は $88)",
    0xB4F4: "敵リスト1体目 落下死→妖精出現フラグ有効化",
    0xB500: "マイティボンジャック 出現処理",
    0xBB9E: "アイテム複数配置 (テーブル参照)",
    0x99CE: "アイテム個別配置 (座標=$00/$01, アイテム=A)",
    0x8DB4: "プレイヤー位置同期/待機 (換石フラグ判定)",
    0xB636: "エンディングへジャンプ",
}

# USA は JP から +0x430 シフト (ROM)、RAM では +0x430 シフトされる
KNOWN_SUBROUTINES_USA = {
    0xBDEA: "アイテムを背景に隠す (直前配置を白壁化)",
    0xBFAA: "ソロモン封印 配置 (引数 A = フラグbit)",
    0xB8CC: "テクモプレート 配置 (座標は $88)",
    0xB924: "敵リスト1体目 落下死→妖精出現フラグ有効化",
    0xB930: "マイティボンジャック 出現処理",
    0xBFCE: "アイテム複数配置 (テーブル参照)",
    0x99CE: "アイテム個別配置 (座標=$00/$01, アイテム=A)",
    0x8DB4: "プレイヤー位置同期/待機 (換石フラグ判定)",
    0xBA66: "エンディングへジャンプ",
}


def get_known_subroutines(region: str) -> dict:
    if region == "JP":
        return KNOWN_SUBROUTINES_JP
    if region == "US":
        return KNOWN_SUBROUTINES_USA
    return {}


def annotate_bytes(rom_bytes: bytes, region: str) -> str:
    """特殊処理バイト列を人間可読な擬似アセンブラに変換する。

    既知のサブルーチンには日本語注釈を付ける。
    """
    known = get_known_subroutines(region)
    lines = []
    i = 0
    while i < len(rom_bytes):
        b = rom_bytes[i]
        if b == 0x60:
            lines.append(f"  RTS                  ; ★終了 (RTS)")
            i += 1
            break
        if b == 0x4c and i + 2 < len(rom_bytes):
            ram_addr = rom_bytes[i + 1] + rom_bytes[i + 2] * 256
            note = known.get(ram_addr, "")
            note_str = f"  ; {note}" if note else ""
            lines.append(f"  JMP ${ram_addr:04X}         ; ★ジャンプ終了{note_str}")
            i += 3
            break
        op_len = _opcode_length(b)
        if op_len == 1:
            lines.append(f"  {_opcode_name(b)}")
        elif op_len == 2:
            arg = rom_bytes[i + 1] if i + 1 < len(rom_bytes) else 0
            lines.append(f"  {_opcode_name(b)} ${arg:02X}")
        else:  # 3バイト
            arg_lo = rom_bytes[i + 1] if i + 1 < len(rom_bytes) else 0
            arg_hi = rom_bytes[i + 2] if i + 2 < len(rom_bytes) else 0
            ram_addr = arg_lo + arg_hi * 256
            note = ""
            if b == 0x20:  # JSR
                note = known.get(ram_addr, "")
                note = f"  ; {note}" if note else ""
            lines.append(f"  {_opcode_name(b)} ${ram_addr:04X}{note}")
        i += op_len
    return "\n".join(lines)


# 6502 オペコード名（よく使うもののみ、その他は HEX 表示）
_OPNAME = {
    0x60: "RTS", 0x40: "RTI", 0x00: "BRK", 0xea: "NOP",
    0x18: "CLC", 0x38: "SEC", 0x58: "CLI", 0x78: "SEI", 0xb8: "CLV", 0xd8: "CLD", 0xf8: "SED",
    0xa9: "LDA #", 0xa2: "LDX #", 0xa0: "LDY #",
    0xa5: "LDA z,", 0xb5: "LDA z,X", 0xad: "LDA", 0xbd: "LDA ,X", 0xb9: "LDA ,Y",
    0xa1: "LDA (z,X)", 0xb1: "LDA (z),Y",
    0xa6: "LDX z", 0xae: "LDX", 0xbe: "LDX ,Y",
    0xa4: "LDY z", 0xb4: "LDY z,X", 0xac: "LDY", 0xbc: "LDY ,X",
    0x85: "STA z", 0x95: "STA z,X", 0x8d: "STA", 0x9d: "STA ,X", 0x99: "STA ,Y",
    0x81: "STA (z,X)", 0x91: "STA (z),Y",
    0x86: "STX z", 0x96: "STX z,Y", 0x8e: "STX",
    0x84: "STY z", 0x94: "STY z,X", 0x8c: "STY",
    0xaa: "TAX", 0xa8: "TAY", 0x8a: "TXA", 0x98: "TYA", 0xba: "TSX", 0x9a: "TXS",
    0xe6: "INC z", 0xee: "INC", 0xfe: "INC ,X", 0xc6: "DEC z", 0xce: "DEC", 0xde: "DEC ,X",
    0xe8: "INX", 0xc8: "INY", 0xca: "DEX", 0x88: "DEY",
    0x29: "AND #", 0x25: "AND z", 0x09: "ORA #", 0x05: "ORA z",
    0x69: "ADC #", 0x65: "ADC z", 0xe9: "SBC #", 0xe5: "SBC z",
    0xc9: "CMP #", 0xc5: "CMP z", 0xcd: "CMP", 0xe0: "CPX #", 0xe4: "CPX z", 0xc0: "CPY #",
    0x4a: "LSR A", 0x0a: "ASL A", 0x2a: "ROL A", 0x6a: "ROR A",
    0x10: "BPL", 0x30: "BMI", 0x50: "BVC", 0x70: "BVS",
    0x90: "BCC", 0xb0: "BCS", 0xd0: "BNE", 0xf0: "BEQ",
    0x20: "JSR", 0x4c: "JMP", 0x6c: "JMP ()",
    0x48: "PHA", 0x68: "PLA", 0x08: "PHP", 0x28: "PLP",
    0x24: "BIT z", 0x2c: "BIT",
}


def _opcode_name(b: int) -> str:
    return _OPNAME.get(b, f"DB ${b:02X}")


# ============================================================
# 特殊処理マーカー抽出: 編集画面に「特殊処理で動的配置されるブロック位置」を表示する
# ============================================================

# マーカー種別
MARK_BREAKABLE = "breakable"  # 0x90 = 壊せるブロック動的配置 (無条件)
MARK_BREAKABLE_CONDITIONAL = "breakable_conditional"  # トリガーが必要
MARK_EMPTY_FORCED = "empty_forced"  # 0x10 = 空 (ブロック消去) 強制配置
MARK_TRIGGER = "trigger"  # プレイヤーアクションを待つ位置
MARK_BOMB_JACK_TRIGGER = "bomb_jack_trigger"  # マイティボンジャック頭突き判定位置
MARK_HIDDEN_BOMB_JACK = "hidden_bomb_jack"  # マイティボンジャック出現位置 (隠し)


def find_marks(rom_bytes: bytes, full_rom: bytes = None) -> dict:
    """特殊処理バイト列から動的配置マスを抽出。

    検出パターン:
    1. 直接配置: LDA #$XX; ...; STA $03YY
    2. 範囲配置(X): LDX #N; ...; STA $03YY,X; DEX; BPL/BNE -k
    3. テーブル経由配置: LDX #N; LDY $TABLE,X; STA $0304,Y; DEX; BPL -k
       (full_rom が渡されていれば $TABLE を ROM から読んで位置として展開)
    4. 前方分岐 (BEQ/BNE/BPL/BMI/BCC/BCS) も辿る

    検出値:
    - XX=0x90 → 壊せるブロック (breakable)
    - XX=0x10 → 空 (empty_forced)

    Returns:
        {(x, y): mark_type} の dict
    """
    marks = {}
    links = []  # [(trigger_pos, target_pos), ...] - トリガーと壊せる化対象の対応

    def decode_pos_byte(pos_byte):
        """位置バイト → (x, y) または None"""
        if not (0x10 <= pos_byte < 0xD0):
            return None
        x = pos_byte & 0xF
        y = (pos_byte >> 4) - 1
        if not (0 <= x < 16 and 0 <= y < 12):
            return None
        return (x, y)

    def add_pos(pos_byte: int, a_value, current_trigger):
        pos = decode_pos_byte(pos_byte)
        if pos is None:
            return
        x, y = pos
        if a_value == 0x90:
            if current_trigger is not None:
                marks[(x, y)] = MARK_BREAKABLE_CONDITIONAL
                marks[current_trigger] = MARK_TRIGGER
                links.append((current_trigger, (x, y)))
            else:
                # 既に conditional として記録されていれば上書きしない
                if marks.get((x, y)) not in (MARK_BREAKABLE_CONDITIONAL, MARK_TRIGGER):
                    marks[(x, y)] = MARK_BREAKABLE
        elif a_value == 0x10:
            if marks.get((x, y)) is None:
                marks[(x, y)] = MARK_EMPTY_FORCED

    # 分岐対応: 「これから辿る位置」を queue で管理
    # 各エントリは (offset, a_value, x_value, y_table, current_trigger)
    # current_trigger: 直前の wait パターン (A5 7E C9 XX D0 -k) で検出した (tx, ty) または None
    visited = set()
    queue = [(0, None, None, None, None)]
    end = len(rom_bytes)

    def ram_to_rom(ram_addr):
        # NES PRG (mapper 3 等で $8000-$FFFF 固定) を ROM file offset に変換
        if ram_addr < 0x8000:
            return -1
        return ram_addr - 0x8000 + 0x10  # +iNES header

    while queue:
        i, a_value, x_value, y_table, current_trigger = queue.pop(0)
        if i in visited:
            continue

        while i < end:
            if i in visited:
                break
            visited.add(i)
            b = rom_bytes[i]

            # 終端
            if b == 0x60:  # RTS
                break
            if b == 0x4c:  # JMP abs - 終了 (絶対ジャンプ先は外部)
                break

            # 【特殊パターン】マイティボンジャック出現
            # BESK 資料より:
            #   20 B4 8D A5 7F C9 X1 D0 F7 ... A9 X2 85 88 4C 00 B5/30 B9
            #   X1 = 叩く場所の座標 (CMP #X1)
            #   X2 = 出現する場所の座標 (LDA #X2 → STA $88)
            #
            # X1 が頭突き判定位置、X2 が出現位置。
            # 条件付き壊せる白ブロックと同じく、X1 -> X2 のリンクとして表示する。
            #
            # X1 は CMP #imm でアイテムバッファ形式の位置バイト (y = (b>>4)-1)。
            if (b == 0xA9 and i + 6 < end
                    and rom_bytes[i + 2] == 0x85
                    and rom_bytes[i + 3] == 0x88
                    and rom_bytes[i + 4] == 0x4C):
                jmp_target = rom_bytes[i + 5] + rom_bytes[i + 6] * 256
                if jmp_target in (0xB500, 0xB930):
                    # 直前を遡って "A5 7F C9 X1 D0 F7" を探す
                    x1_byte = None
                    for back in range(i - 6, max(-1, i - 40), -1):
                        if (back >= 0 and back + 5 < len(rom_bytes)
                                and rom_bytes[back] == 0xA5
                                and rom_bytes[back + 1] == 0x7F
                                and rom_bytes[back + 2] == 0xC9
                                and rom_bytes[back + 4] == 0xD0):
                            x1_byte = rom_bytes[back + 3]
                            break
                    if x1_byte is not None:
                        trigger_pos = decode_pos_byte(x1_byte)
                        spawn_pos = decode_pos_byte(rom_bytes[i + 1])
                        if trigger_pos is not None:
                            marks[trigger_pos] = MARK_BOMB_JACK_TRIGGER
                        if spawn_pos is not None:
                            marks[spawn_pos] = MARK_HIDDEN_BOMB_JACK
                        if trigger_pos is not None and spawn_pos is not None:
                            links.append((trigger_pos, spawn_pos))
                    for k in range(1, 7):
                        visited.add(i + k)
                    break

            # 【特殊パターン】wait for player at position
            # 2種類のバリエーション:
            #   (A) A5 7E C9 XX D0 NN  = LDA $7E; CMP #$XX; BNE -k
            #   (B) A6 7E E0 XX D0 NN  = LDX $7E; CPX #$XX; BNE -k
            # ($7E = player の何らかの位置/アクション対象座標バイト)
            if (i + 5 < end
                    and rom_bytes[i + 1] == 0x7E
                    and rom_bytes[i + 4] == 0xD0
                    and rom_bytes[i + 5] >= 0x80  # backward
                    and ((b == 0xA5 and rom_bytes[i + 2] == 0xC9)
                         or (b == 0xA6 and rom_bytes[i + 2] == 0xE0))):
                trigger_byte = rom_bytes[i + 3]
                t_pos = decode_pos_byte(trigger_byte)
                if t_pos is not None:
                    current_trigger = t_pos
                # 6バイト分まとめてスキップ + visited 記録
                for k in range(1, 6):
                    visited.add(i + k)
                i += 6
                continue

            # LDA #imm
            if b == 0xA9 and i + 1 < end:
                a_value = rom_bytes[i + 1]
                i += 2
                continue

            # LDX #imm
            if b == 0xA2 and i + 1 < end:
                x_value = rom_bytes[i + 1]
                i += 2
                continue

            # LDY $XXXX,X (3バイト) - 位置テーブル参照
            if b == 0xBC and i + 2 < end:
                lo = rom_bytes[i + 1]
                hi = rom_bytes[i + 2]
                y_table = (hi << 8) | lo
                i += 3
                continue

            # STA abs (直接配置)
            if b == 0x8D and i + 2 < end:
                lo = rom_bytes[i + 1]
                hi = rom_bytes[i + 2]
                if hi == 0x03 and a_value is not None:
                    add_pos(lo - 0x04, a_value, current_trigger)
                i += 3
                continue

            # STA abs,X (範囲配置, X インデックス)
            if b == 0x9D and i + 2 < end:
                lo = rom_bytes[i + 1]
                hi = rom_bytes[i + 2]
                if hi == 0x03 and a_value is not None and x_value is not None:
                    for k in range(x_value, -1, -1):
                        add_pos((lo + k) - 0x04, a_value, current_trigger)
                i += 3
                continue

            # STA abs,Y (Y インデックス) - 位置テーブル経由
            if b == 0x99 and i + 2 < end:
                lo = rom_bytes[i + 1]
                hi = rom_bytes[i + 2]
                if (hi == 0x03 and a_value is not None
                        and y_table is not None and x_value is not None
                        and full_rom is not None):
                    table_rom = ram_to_rom(y_table)
                    if table_rom >= 0 and table_rom + x_value < len(full_rom):
                        for k in range(x_value, -1, -1):
                            y_val = full_rom[table_rom + k]
                            pos_byte = (lo + y_val) - 0x04
                            add_pos(pos_byte & 0xFF, a_value, current_trigger)
                i += 3
                continue

            # 前方/後方分岐
            if b in (0x10, 0x30, 0x50, 0x70, 0x90, 0xb0, 0xd0, 0xf0):
                if i + 1 < end:
                    offset_signed = rom_bytes[i + 1]
                    if offset_signed >= 0x80:
                        offset_signed -= 0x100
                    target = i + 2 + offset_signed
                    if 0 <= target < end and target not in visited:
                        queue.append((target, a_value, x_value, y_table, current_trigger))
                i += 2
                continue

            # JSR
            if b == 0x20:
                i += 3
                continue

            # その他: opcode 長でスキップ
            i += _opcode_length(b)

    # marks dict は変更せず、links は別属性として返したいが、
    # 既存呼出元の互換のため (x, y) -> kind の dict として返す。
    # links は marks の特殊エントリ ('__links__' キー) として埋め込む。
    marks['__links__'] = links
    return marks


def find_marks_for_level(rom_data: bytes, region: str, level_no: int,
                         max_bytes: int = 512) -> dict:
    """指定レベルの特殊処理から動的配置マスを抽出（ワンショット便利関数）

    BinaryDistSpecial の長さに依らず、開始アドレスから max_bytes 分の領域を渡し、
    find_marks 側で分岐追跡しながら到達可能なすべての配置を検出する。
    位置テーブル参照 (LDY $XXXX,X) のためにフルROMも渡す。
    """
    addr = get_special_process_address(rom_data, region, level_no)
    if addr < 0:
        return {}
    end = min(addr + max_bytes, len(rom_data))
    return find_marks(bytes(rom_data[addr:end]), full_rom=bytes(rom_data))

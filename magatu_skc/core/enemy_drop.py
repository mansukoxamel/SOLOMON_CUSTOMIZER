"""敵ドロップ効果表 編集 (グローバル / 位置+署名ダブル検証)

敵を★ダーナ火球で倒した時に出る「拾得アイテム entity $14」の中身は
SUB $C200 が決める (R180 / Codex ENEMY_DROP_PROBABILITY 実機確定):
  X = (敵type>>2)-6 → $C278,X = 行offset → $03
  A = (PRNG $C2E3) AND #$07 ; A += 行offset → $C293,X = ドロップ効果値

★重要 (R180 / feedback_drop_namespace_static_error):
  $C293 の値は「$A373 拾得AI のドロップ効果値」であって ★通常の
  床アイテムID ($C55B/$C5D3) ではない。$06 はここでは 1UP であって
  鍵ではない。このモジュールで設定できるのは下記 DROP_EFFECTS の
  効果値のみ。通常アイテムを落とさせるには code-cave 変換層が要る
  (別案件・本モジュール対象外)。

確率 = 行8枠中の出現数 (例 4/8 = 50%)。行は複数の敵グループで
共有される (例: 行$18 = Neul 各系 / 行$30 = Saramandor s3 + Dragon
s1)。編集は「行」単位 = その行を使う全グループに反映される。

CLAUDE.md 準拠:
  - (A)ハードコード file offset + (B)安定署名 を両方検証
  - 不一致は EnemyDropError で中止 (フォールバック禁止)
  - 署名は $C200 ルーチン内のコード列 (改造対象 $C278/$C293 を含まない)
  - 注入先は本編コード = JP/US 同一だが region 同一性に依存せず毎回検証

ROM file offset (clean JP / 拡張ROM 共通。expander verbatim):
  file = 0x10 + (cpu - 0x8000)
  $C278 行割当表  file 0x4288  27B
  $C293 ドロップ値表 file 0x42A3  80B (行 $00,$08,..,$48 = 10行×8)
  署名 $C248 file 0x4258 / $C20F file 0x421F
"""

OFF_C278 = 0x4288   # $C278 行割当 (index=(type>>2)-6)
LEN_C278 = 27
OFF_C293 = 0x42A3   # $C293 ドロップ値表
ROW_COUNT = 10      # 行 $00,$08,$10,$18,$20,$28,$30,$38,$40,$48
ROW_LEN = 8
LEN_C293 = ROW_COUNT * ROW_LEN  # 80

OFF_SIG_C248 = 0x4258
SIG_C248 = bytes.fromhex("20 e3 c2 29 07 18 65 03 aa")          # JSR$C2E3/AND#7/CLC/ADC$03/TAX
OFF_SIG_C20F = 0x421F
SIG_C20F = bytes.fromhex("4a 90 58 c8 b1 00 4a 4a 38 e9 06 90")  # $C20F 安定コード

# 原作テーブル (clean JP 実機裏取り / Codex ENEMY_DROP_PROBABILITY と一致)
ORIG_C278 = bytes.fromhex(
    "00 00 00 48 08 08 18 10 18 10 18 10 18 10 20 20 20 28 28 28 "
    "30 30 38 38 40 40 00"
)
ORIG_C293 = bytes.fromhex(
    "00 00 00 00 00 00 00 00 "  # row $00
    "04 08 08 08 09 09 09 09 "  # row $08
    "04 08 08 08 09 09 09 0a "  # row $10
    "08 08 09 09 09 09 0a 0a "  # row $18
    "04 0b 0b 0b 0b 0c 0c 0c "  # row $20
    "0b 0b 0c 0c 0c 0d 0d 02 "  # row $28
    "0b 0b 0b 0c 0c 03 03 06 "  # row $30
    "04 0b 0c 0c 0d 0d 02 02 "  # row $38
    "0e 0e 0e 0e 0f 05 05 05 "  # row $40
    "0e 0e 0e 0f 0f 0f 05 05"   # row $48
)
assert len(ORIG_C278) == LEN_C278 and len(ORIG_C293) == LEN_C293

ROW_LABELS = ["$00", "$08", "$10", "$18", "$20",
              "$28", "$30", "$38", "$40", "$48"]

# ドロップ効果値 → (短縮名, 説明)。
# 名前はユーザー実機ゲーム知識を一次情報として採用 (2026-05-17):
#   $02 = マガドラの壺 / $03 = ライラックの鐘。
# $01,$07 は静的解析でも未確定 → 実機確認用に選択可能化 (推測命名せず
#   「未確定」表示)。$A373/$A41D の <8 値処理経路には乗るので test 可。
DROP_EFFECTS = {
    0x00: ("なし", "ドロップ無し"),
    0x01: ("未確定$01", "★未確定: 要実機確認 ($A41D <8値経路)"),
    0x02: ("マガドラの壺", "特殊クリスタル/星座bit ($A46E)。実機=マガドラの壺"),
    0x03: ("ライラックの鐘", "特殊カウンタ $042B++ ($C798)。実機=ライラックの鐘"),
    0x04: ("ファイア距離+", "firewall 到達距離 +$10 ($C7C0)"),
    0x05: ("妖精予約", "fairy 出現予約 $0454++ ($C7AA)"),
    0x06: ("1UP", "ライフ +1 / SE$06 ($C5A1) ※鍵ではない"),
    0x07: ("未確定$07", "★未確定: 要実機確認 ($A41D <8値経路)"),
    0x08: ("スコア+10", "score +10"),
    0x09: ("スコア+20", "score +20"),
    0x0A: ("スコア+50", "score +50"),
    0x0B: ("スコア+100", "score +100"),
    0x0C: ("スコア+200", "score +200"),
    0x0D: ("スコア+500", "score +500"),
    0x0E: ("スコア+1000", "score +1000"),
    0x0F: ("スコア+2000", "score +2000"),
}
VALID_VALUES = frozenset(DROP_EFFECTS)

# 行offset値 → その行を使う敵グループ (表示用。$C278 原作割当より)
ROW_USERS = {
    0x00: "Bomb Jack系/Fairy系/Bullet/Gargoyle s2/Flame (ドロップ無)",
    0x08: "Fireball s1・s2",
    0x10: "Ghost 各系",
    0x18: "Neul 各系",
    0x20: "Demonhead s1・s2",
    0x28: "Demonhead s3 / Saramandor s1・s2",
    0x30: "Saramandor s3 / Dragon s1",
    0x38: "Dragon s2 / Golem s1",
    0x40: "Golem s2 / Gargoyle s1",
    0x48: "Panel Monster",
}


class EnemyDropError(ValueError):
    """敵ドロップ表 改造の検証失敗 (改造ROM/拡張ROM/破損の可能性)"""


def _verify(rom_data) -> None:
    """(A)位置 + (B)署名 ダブル検証。失敗時 EnemyDropError"""
    if len(rom_data) < OFF_C293 + LEN_C293:
        raise EnemyDropError(
            f"ROM が小さすぎます (len={len(rom_data)})。敵ドロップ改造を中止。"
        )
    if bytes(rom_data[OFF_SIG_C248:OFF_SIG_C248 + len(SIG_C248)]) != SIG_C248:
        raise EnemyDropError(
            "$C248 署名不一致。改造ROM/拡張ROM/破損の可能性があるため中止します。"
        )
    if bytes(rom_data[OFF_SIG_C20F:OFF_SIG_C20F + len(SIG_C20F)]) != SIG_C20F:
        raise EnemyDropError(
            "$C20F 署名不一致。改造ROM/拡張ROM/破損の可能性があるため中止します。"
        )


def read_rows(rom_data) -> list:
    """$C293 を 10行×8 の二次元 list で返す。検証付き"""
    _verify(rom_data)
    flat = list(rom_data[OFF_C293:OFF_C293 + LEN_C293])
    return [flat[i * ROW_LEN:(i + 1) * ROW_LEN] for i in range(ROW_COUNT)]


def read_c278(rom_data) -> list:
    """$C278 行割当表 (27B) を list で返す"""
    _verify(rom_data)
    return list(rom_data[OFF_C278:OFF_C278 + LEN_C278])


def is_modified(rom_data) -> bool:
    """原作から変更されているか"""
    _verify(rom_data)
    return (bytes(rom_data[OFF_C293:OFF_C293 + LEN_C293]) != ORIG_C293 or
            bytes(rom_data[OFF_C278:OFF_C278 + LEN_C278]) != ORIG_C278)


def probabilities(row: list) -> dict:
    """8枠 list → {効果値: 出現数} (確率 = count/8)"""
    out = {}
    for v in row:
        out[v] = out.get(v, 0) + 1
    return out


def write_rows(rom_data, rows: list, c278: list = None) -> list:
    """編集した行 (10×8) を $C293 へ書込。c278 指定時は行割当も。
    値は DROP_EFFECTS のキーのみ許可。戻り値=変更説明 list。
    検証失敗/不正値は EnemyDropError (フォールバック禁止)。
    """
    _verify(rom_data)
    if len(rows) != ROW_COUNT or any(len(r) != ROW_LEN for r in rows):
        raise EnemyDropError(
            f"行数/列数不正 (期待 {ROW_COUNT}行×{ROW_LEN})。"
        )
    flat = bytearray()
    for ri, r in enumerate(rows):
        for v in r:
            if v not in VALID_VALUES:
                raise EnemyDropError(
                    f"行{ROW_LABELS[ri]} に未対応値 ${v:02X}。"
                    f"設定可能値: {sorted(VALID_VALUES)}"
                )
            flat.append(v)
    changed = []
    if bytes(rom_data[OFF_C293:OFF_C293 + LEN_C293]) != bytes(flat):
        rom_data[OFF_C293:OFF_C293 + LEN_C293] = bytes(flat)
        changed.append("ドロップ値表 $C293 更新")
    if c278 is not None:
        if len(c278) != LEN_C278:
            raise EnemyDropError(f"$C278 長さ不正 (期待 {LEN_C278})。")
        if bytes(rom_data[OFF_C278:OFF_C278 + LEN_C278]) != bytes(bytearray(c278)):
            rom_data[OFF_C278:OFF_C278 + LEN_C278] = bytes(bytearray(c278))
            changed.append("行割当表 $C278 更新")
    return changed


def restore(rom_data) -> list:
    """原作テーブルへ完全復元"""
    _verify(rom_data)
    changed = []
    if bytes(rom_data[OFF_C293:OFF_C293 + LEN_C293]) != ORIG_C293:
        rom_data[OFF_C293:OFF_C293 + LEN_C293] = ORIG_C293
        changed.append("ドロップ値表 $C293 → 原作復元")
    if bytes(rom_data[OFF_C278:OFF_C278 + LEN_C278]) != ORIG_C278:
        rom_data[OFF_C278:OFF_C278 + LEN_C278] = ORIG_C278
        changed.append("行割当表 $C278 → 原作復元")
    return changed

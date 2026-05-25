"""サラマンダー火球発射化 改造 (位置 + シグネチャ ダブル検証方式)

CLAUDE.md ルール準拠:
  - JP/US 両対応。US は再配置ゾーンのため JP +$140 の別オフセット
  - 改造前に安定シグネチャ2点を検証、失敗時 SalamanderHackError でパッチ中止

実機検証済み (2026-05-15):
  原作: サラマンダーが口から1マス火を出す (子type $04, 上下方向, 28F で despawn)
  改造: 水平に火球(Bullet $20)を発射、強制despawn除去で壁まで飛ぶ

改造内容:
  - 子entity type  $04 → $20 (Bullet, AI $AFBB)         ※必須セット
  - 発射方向       $05 → $04 (behavior下位2bit 上下→左右)  ※必須セット
  - 強制despawn除去  JSR → NOP×3                          ※ON/OFF
  - X反応距離      $14 → 任意 (SUB_B1E9 しきい値A $B1F3, pixel距離)  ※選択
  - Y反応許容      $10 → 任意 (SUB_B1E9 しきい値B $B1FF, pixel距離)  ※選択

★重要 (2026-05-15 Codex解析+SUB_A134実コードで訂正):
  - SUB_B1E9 しきい値A ($B1F3, file 0x3203) = X距離ゲート (sub-slot[5]=X距離)
  - SUB_B1E9 しきい値B ($B1FF, file 0x320F) = Y距離ゲート (sub-slot[4]=Y距離)
  - 旧実装は X/Y を逆に割当てていた (sub-slot[4]/[5] のR67コメント誤りが原因)
  - SUB_A134 で相対距離を /2 して保存し、SUB_B1E9 側の ASL で戻して比較する。
    そのため CMP 即値は実質 pixel 距離。1マス=16px、5マス=80px=$50
  - ⚠ SUB_B1E9 は Dragon State5 ($A669) も共有。即値変更は Dragon の
    反応距離にも影響する (サラマンダー専用にするには専用routine差替が必要=将来課題)
"""

# region → 各 file offset
_OFF = {
    "JP": {
        "type":    0x3116,   # $B106 子type operand
        "dir":     0x3120,   # $B110 方向 operand
        "despawn": 0x30D6,   # $B0C6 JSR (3B)
        "xdist":   0x3203,   # $B1F3 SUB_B1E9 しきい値A = X距離ゲート
        "ydist":   0x320F,   # $B1FF SUB_B1E9 しきい値B = Y距離ゲート
        "status":  0x311A,   # $B10A 子status operand ($C6→$C0 で被弾有効)
        "ora02":   0x30BD,   # $B0AD ORA #$02 operand (bit1再セット抑制 $02→$00)
        # 安定シグネチャ (改造対象バイトを一切含まない / 一意確認済)
        "sig1_off": 0x310E,  # $B0FE: 20 4A B1 B1 2E 91 00 (JSR$B14A/LDA($2E)/STA($00))
        "sig1":     bytes.fromhex("20 4a b1 b1 2e 91 00"),
        "sig2_off": 0x31F9,  # $B1E9: A0 05 B1 2C 0A B0 02 49 FF (SUB_B1E9先頭)
        "sig2":     bytes.fromhex("a0 05 b1 2c 0a b0 02 49 ff"),
        "despawn_orig": bytes.fromhex("20 5e b0"),  # JSR $B05E
    },
    "US": {  # 全項目 JP +$140 (再配置ゾーン)
        "type":    0x3256,
        "dir":     0x3260,
        "despawn": 0x3216,
        "xdist":   0x3343,   # しきい値A = X距離 (JP 0x3203 +$140)
        "ydist":   0x334F,   # しきい値B = Y距離 (JP 0x320F +$140)
        "status":  0x325A,   # JP 0x311A +$140
        "ora02":   0x31FD,   # JP 0x30BD +$140
        "sig1_off": 0x324E,  # JP 0x310E +$140 (US は JSR先 $B28A で 20 8a b2)
        "sig1":     bytes.fromhex("20 8a b2 b1 2e 91 00"),
        "sig2_off": 0x3339,
        "sig2":     bytes.fromhex("a0 05 b1 2c 0a b0 02 49 ff"),
        "despawn_orig": bytes.fromhex("20 9e b1"),  # JSR $B19E (US再配置先)
    },
}

NOP3 = bytes([0xEA, 0xEA, 0xEA])

ORIG_TYPE   = 0x04
ORIG_DIR    = 0x05
ORIG_XDIST  = 0x14  # SUB_B1E9 しきい値A 原作 (X距離ゲート)
ORIG_YDIST  = 0x10  # SUB_B1E9 しきい値B 原作 (Y距離ゲート)
ORIG_STATUS = 0xC6  # 子status 原作 (親紐付き炎用)
ORIG_ORA    = 0x02  # $B0AC ORA #$02 原作 (bit1再セット)
HACK_TYPE   = 0x20  # Bullet
HACK_DIR    = 0x04  # 水平化
HACK_STATUS = 0xC0  # 通常Bullet同 ($C0&$03=0 → ダーナ被弾有効)
HACK_ORA    = 0x00  # ORA #$00 (bit1再セット抑制、被弾を維持)

# しきい値A = X距離ゲート (pixel距離、1マス=16px)。Dragon State5 と共有。
XDIST_PRESETS = [
    ("原作 (水平20px = 1.25マス)", 0x14),
    ("中距離 (水平64px = 4マス)",  0x40),
    ("遠距離 (水平80px = 5マス)",  0x50),
    ("超遠距離 (水平96px = 6マス)", 0x60),
]
# しきい値B = Y距離ゲート (pixel距離、上下の許容)。$10=16px、$18=24px。
YDIST_PRESETS = [
    ("原作 (上下16px = 1マス)", 0x10),
    ("やや広い (上下24px = 1.5マス)", 0x18),
]


class SalamanderHackError(ValueError):
    """サラマンダー改造の検証失敗"""


def detect_region(rom_data) -> str:
    """ROM が JP/US どちらのサラマンダー配置か判定。不明なら SalamanderHackError"""
    for region, o in _OFF.items():
        if len(rom_data) < o["sig2_off"] + len(o["sig2"]):
            continue
        s1 = bytes(rom_data[o["sig1_off"]:o["sig1_off"] + len(o["sig1"])])
        s2 = bytes(rom_data[o["sig2_off"]:o["sig2_off"] + len(o["sig2"])])
        if s1 == o["sig1"] and s2 == o["sig2"]:
            return region
    raise SalamanderHackError(
        "サラマンダーのコードが見つかりません。\n"
        "改造ROM/拡張ROM/破損の可能性があるためサラマンダー改造を中止します。"
    )


def is_hacked(rom_data) -> bool:
    """既にサラマンダー火球化が適用されているか (type/dir で判定)"""
    region = detect_region(rom_data)
    o = _OFF[region]
    return rom_data[o["type"]] == HACK_TYPE and rom_data[o["dir"]] == HACK_DIR


def is_despawn_removed(rom_data) -> bool:
    region = detect_region(rom_data)
    o = _OFF[region]
    return bytes(rom_data[o["despawn"]:o["despawn"] + 3]) == NOP3


def current_xdist(rom_data) -> int:
    region = detect_region(rom_data)
    return rom_data[_OFF[region]["xdist"]]


def current_ydist(rom_data) -> int:
    region = detect_region(rom_data)
    return rom_data[_OFF[region]["ydist"]]


def apply_distance(rom_data, xdist: int, ydist: int) -> list:
    """Only update the shared Saramandor/Dragon reaction distance bytes.

    This intentionally does not apply the old global Saramandor fireball hack.
    The modern Saramandor #2 bullet behavior is ID-based; these two bytes are
    kept as independent global tuning values.
    """
    region = detect_region(rom_data)
    o = _OFF[region]
    changed = []
    if rom_data[o["xdist"]] != xdist:
        rom_data[o["xdist"]] = xdist
        changed.append(f"X距離→{xdist:02X}")
    if rom_data[o["ydist"]] != ydist:
        rom_data[o["ydist"]] = ydist
        changed.append(f"Y許容→{ydist:02X}")
    return changed


def apply(rom_data, enable: bool, remove_despawn: bool,
          xdist: int, ydist: int) -> list:
    """サラマンダー改造を適用。検証 → 書込。変更項目リストを返す

    enable=True: 火球化 (type=$20, dir=$04)
    enable=False: 原作復元 (type=$04, dir=$05, despawn復元, dist原作)
    """
    region = detect_region(rom_data)
    o = _OFF[region]
    changed = []

    if not enable:
        # 原作復元
        if rom_data[o["type"]] != ORIG_TYPE:
            rom_data[o["type"]] = ORIG_TYPE; changed.append("子type→原作")
        if rom_data[o["dir"]] != ORIG_DIR:
            rom_data[o["dir"]] = ORIG_DIR; changed.append("方向→原作")
        if bytes(rom_data[o["despawn"]:o["despawn"]+3]) != o["despawn_orig"]:
            rom_data[o["despawn"]:o["despawn"]+3] = o["despawn_orig"]
            changed.append("despawn→原作")
        if rom_data[o["xdist"]] != ORIG_XDIST:
            rom_data[o["xdist"]] = ORIG_XDIST; changed.append("X距離→原作")
        if rom_data[o["ydist"]] != ORIG_YDIST:
            rom_data[o["ydist"]] = ORIG_YDIST; changed.append("Y距離→原作")
        if rom_data[o["status"]] != ORIG_STATUS:
            rom_data[o["status"]] = ORIG_STATUS; changed.append("status→原作")
        if rom_data[o["ora02"]] != ORIG_ORA:
            rom_data[o["ora02"]] = ORIG_ORA; changed.append("ORA#$02→原作")
        return changed

    # 火球化 (type/dir/status/ORA抑制 は必須セット = ダーナ被弾を有効化)
    if rom_data[o["type"]] != HACK_TYPE:
        rom_data[o["type"]] = HACK_TYPE; changed.append("子type→火球($20)")
    if rom_data[o["dir"]] != HACK_DIR:
        rom_data[o["dir"]] = HACK_DIR; changed.append("発射方向→水平")
    if rom_data[o["status"]] != HACK_STATUS:
        rom_data[o["status"]] = HACK_STATUS; changed.append("status→$C0(被弾有効)")
    if rom_data[o["ora02"]] != HACK_ORA:
        rom_data[o["ora02"]] = HACK_ORA; changed.append("bit1再セット抑制")

    # despawn除去 ON/OFF
    cur_despawn = bytes(rom_data[o["despawn"]:o["despawn"]+3])
    if remove_despawn:
        if cur_despawn != NOP3:
            rom_data[o["despawn"]:o["despawn"]+3] = NOP3
            changed.append("強制despawn除去(壁まで飛ぶ)")
    else:
        if cur_despawn == NOP3:
            rom_data[o["despawn"]:o["despawn"]+3] = o["despawn_orig"]
            changed.append("強制despawn復元(時間で消滅)")

    # 距離 (SUB_B1E9 は CMP 即値、特別な禁止値なし)
    if rom_data[o["xdist"]] != xdist:
        rom_data[o["xdist"]] = xdist; changed.append(f"X距離→${xdist:02X}")
    if rom_data[o["ydist"]] != ydist:
        rom_data[o["ydist"]] = ydist; changed.append(f"Y距離→${ydist:02X}")

    return changed

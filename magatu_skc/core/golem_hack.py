"""ゴーレム動作改造 (位置 + シグネチャ ダブル検証方式)

CLAUDE.md ルール準拠:
  - JP/US 両対応。US は再配置ゾーン (JP +$140)
  - 改造前に AI_GOLEM シグネチャを検証、失敗時 GolemHackError でパッチ中止

Codex解析 + ROMバイト全項目検証で確定 (2026-05-16):
  ゴーレム (type $70-$77, AI $AD11) の State 遷移には4つの「待ちフレーム」がある。
  これを最小化すると「視認→即反応・方向転換・移動再開」= キビキビ動作になる。
  ※ 移動速度そのもの ($AD5F/$AD95/$AE0F の #$01) は速度値兼 behavior bit
    マスクのため $02 にすると無限ループ。触らない。速度UPは別途 (golem speed)。

キビキビ4箇所 (CMP/CPX #imm / BCC 待ちしきい値):
  $AD33 State0 初期待ち   原作 $0C
  $AD41 State0 起動待ち   原作 $1B
  $AD90 State4 視認後復帰  原作 $0C
  $AE0A State5 復帰/反転   原作 $18
  → 全て $01 で実質待ちゼロ (実機確認: 正常動作・劇的に機敏)
"""

# region → wait offsets / 原作値 / シグネチャ
_OFF = {
    "JP": {
        "waits":  [0x2D43, 0x2D51, 0x2DA0, 0x2E1A],
        "orig":   [0x0C,   0x1B,   0x0C,   0x18],
        "sig_off": 0x2D21,  # AI_GOLEM $AD11 dispatch (待ちバイト不含・一意)
        "sig":     bytes.fromhex("20 01 b2 20 a9 8e 25 ad c8 ae 30 ae"),
    },
    "US": {  # JP +$140 (再配置ゾーン、JSR先差で sig 別)
        "waits":  [0x2E83, 0x2E91, 0x2EE0, 0x2F5A],
        "orig":   [0x0C,   0x1B,   0x0C,   0x18],
        "sig_off": 0x2E61,
        "sig":     bytes.fromhex("20 41 b3 20 a9 8e 65 ae 08 b0 70 af"),
    },
}

SNAPPY_VALUE = 0x01  # 全待ちをこの値に (実質待ちゼロ)


class GolemHackError(ValueError):
    """ゴーレム改造の検証失敗"""


def detect_region(rom_data) -> str:
    for region, o in _OFF.items():
        end = o["sig_off"] + len(o["sig"])
        if len(rom_data) < end:
            continue
        if bytes(rom_data[o["sig_off"]:end]) == o["sig"]:
            return region
    raise GolemHackError(
        "ゴーレムのコードが見つかりません。\n"
        "改造ROM/拡張ROM/破損の可能性があるため改造を中止します。"
    )


def is_snappy(rom_data) -> bool:
    """キビキビ動作が適用済みか (4箇所すべて SNAPPY_VALUE か)"""
    region = detect_region(rom_data)
    o = _OFF[region]
    return all(rom_data[off] == SNAPPY_VALUE for off in o["waits"])


def apply(rom_data, snappy: bool) -> list:
    """キビキビ ON/OFF。snappy=True で全待ち→$01、False で原作復元"""
    region = detect_region(rom_data)
    o = _OFF[region]
    changed = []
    if snappy:
        for off in o["waits"]:
            if rom_data[off] != SNAPPY_VALUE:
                rom_data[off] = SNAPPY_VALUE
                changed.append(f"待ち${off:04X}→$01")
        if changed:
            return ["キビキビ動作ON (待ち4箇所→$01)"]
        return []
    else:
        for off, orig in zip(o["waits"], o["orig"]):
            if rom_data[off] != orig:
                rom_data[off] = orig
                changed.append(f"待ち${off:04X}→原作")
        if changed:
            return ["キビキビ動作OFF (原作復元)"]
        return []

"""ROM書換アドレス情報 - Phase 9 の汎用ROM改造で使用

Game Genie コードを decoder で解析した結果。
通常ROM (NROM/mapper 3) 用。拡張ROM (mapper 66) では一部使用不可。

参考: gamegenie.com / libretro-database
"""

# (ROM offset, original byte, hack name → list[(value, description)])
# value のリストの最初がデフォルト改造値

HACK_ADDRESSES = {
    # [開始ステージ系]
    "starting_stage_value": {
        "offset": 0x1145,
        "original": 0x00,
        "description": "開始ステージ番号 (要 stage_select_common1 + common2 同時改変)",
        "presets": [
            (0x00, "ステージ1から (デフォルト)"),
            (0x09, "ステージ10から"),
            (0x13, "ステージ20から"),
            (0x1D, "ステージ30から"),
            (0x27, "ステージ40から"),
        ],
        "depends_on": ["stage_select_common1", "stage_select_common2"],
    },
    "stage_select_common1": {
        "offset": 0x1149,
        "original": 0x8D,
        "description": "ステージセレクト有効化 (共通1)",
        "presets": [(0xAD, "有効化")],
    },
    "stage_select_common2": {
        "offset": 0x114B,
        "original": 0x04,
        "description": "ステージセレクト有効化 (共通2)",
        "presets": [(0x93, "有効化")],
    },
    "start_from_last_or_next": {
        "offset": 0x1146,
        "original": 0x8D,
        "description": "前回到達ステージ・次ステージから開始",
        "presets": [
            (0x8D, "デフォルト (ステージ1から)"),
            (0x2C, "前回到達ステージから開始"),
            (0xEE, "次のステージから開始"),
        ],
    },

    # [ゲーム挙動系]
    "fairy_spawn": {
        "offset": 0x2035,
        "original": 0x23,
        "description": "フェアリー出現条件",
        "presets": [
            (0x23, "デフォルト"),
            (0x00, "連続フェアリー出現"),
        ],
    },
    "invincible_fireball": {
        "offset": 0x202B,
        "original": 0x20,
        "description": "ファイアボールに無敵 (ON/OFF)",
        "presets": [
            (0x20, "通常"),
            (0x2C, "無敵"),
        ],
    },

    # [コンティニュー制限ステージ]
    # 原作の「42面以降コンティニュー不可」問題を解決する1バイトハック
    # ROM 0x4A58 = 即値の比較値 (LDX #$XX のオペランド)
    # 値はゼロインデックス: 0x28 = stage 41, 0x34 = stage 53 (最終)
    "continue_max_stage": {
        "offset": 0x4A58,
        "original": 0x28,
        "description": "コンティニュー可能な最大ステージ (0x28=41面、0x34=53面まで)",
        "presets": [
            (0x28, "ステージ41まで（原作デフォルト）"),
            (0x29, "ステージ42まで"),
            (0x2F, "ステージ48まで"),
            (0x30, "PRINSESS まで"),
            (0x31, "SOLOMON まで"),
            (0x32, "HIDDEN まで"),
            (0x34, "時間の間まで（全ステージ・最終）"),
        ],
    },

    # [拡張ROMでは使用不可]
    "infinite_lives": {
        "offset": 0x4885C,
        "original": 0xCA,
        "description": "無限残機 (CPU 0xC84C - 通常ROMのみ)",
        "presets": [
            (0xCA, "通常 (残機減る)"),
            (0xEA, "残機減らない"),
        ],
        "expanded_rom_unsupported": True,
    },
}


# Game Genie コード（参考用、emulator入力に使える）
GAME_GENIE_CODES = [
    ("XTKKKEXK", "無限ライフ"),
    ("GZOXLAAX", "無敵ファイアボール"),
    ("AAXZIALZ", "連続フェアリー出現"),
    ("KAXOOEVE", "開始時 40,000ライフポイント"),
    ("GZUPTOSE", "前回到達ステージから開始"),
    ("VTUPTOSE", "次のステージから開始"),
    # 3コード組合せのステージセレクト
    ("SZUOPOSE+UPUOLPGA+PAUPIPAE", "ステージ10から開始"),
    ("SZUOPOSE+UPUOLPGA+LPUPIPAA", "ステージ20から開始"),
    ("SZUOPOSE+UPUOLPGA+IPUPIPAE", "ステージ30から開始"),
    ("SZUOPOSE+UPUOLPGA+YZUPIPAA", "ステージ40から開始"),
]


def apply_hack(rom_data: bytearray, hack_name: str, value: int) -> bool:
    """ROMバイト列にハックを適用"""
    info = HACK_ADDRESSES.get(hack_name)
    if not info:
        return False
    offset = info["offset"]
    if offset >= len(rom_data):
        return False
    rom_data[offset] = value & 0xff
    return True



def get_continue_max_offset(rom_region: str) -> int:
    """コンティニュー上限ステージの即値が格納されているROMオフセット"""
    base = rom_region.upper().rstrip("66").rstrip()
    if "JP" in base:
        return 0x4A58
    return 0x4958


def list_presets(hack_name: str) -> list:
    """指定ハックのプリセット一覧"""
    info = HACK_ADDRESSES.get(hack_name)
    if not info:
        return []
    return info.get("presets", [])

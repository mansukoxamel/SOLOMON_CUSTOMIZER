"""Room Flag Table 拡張 - 画面(部屋)ごとの挙動改造基盤

「今後のアイデア.txt」の room flag table 拡張仕様を本編に統合。
level data を一切壊さず、部屋番号($0428)で引く 64 バイトのフラグ表を
bank0 のコードケーブに注入し、部屋別の改造を実現する。

実機実証済み (TEST_RoomFlag_P1/P2, TEST_HiddenDoor.nes / 2026-05-17):
  - $9071 ローダフック + $C1C0 RoomFlagTable(64B) + $0778 ROOMFLAGS
    (★旧 $0460 はサウンドch0状態RAMと衝突→暗闇面で妖精音ループ。
     2026-05-18 $0778/$0779 へ移設。詳細は下 DARK_CAVE 注記)
  - $8326 MAGICGATE フック (bit2 = B火球禁止、A換石は常に可)

フラグ bit 割当 (project_room_flag_extension.md):
  bit0 = 隠し扉            (扉セルにbit6を立て、開始前扉描画を抑止)
  bit1 = ブロック内扉      (扉セルにbit7を立て、開始前扉描画を抑止)
  bit0+bit1 = 白ブロック内扉 (扉セルにbit6+bit7を立てる)
  bit2 = B火球(魔法)禁止   ← ステップ1で実装
  bit5 = 透明ブロック内アイテムruntime maskあり (保存時に自動付与)
  bit6 = 特殊セルruntime変換あり (保存時に自動付与)
  他bit は将来拡張

CLAUDE.md 準拠:
  - (A) ハードコード file offset + (B) 安定シグネチャ を両方検証
  - 検証失敗時は RoomFlagError を投げてパッチ中止 (フォールバック禁止)
  - シグネチャは改造対象バイトを一切含まない並びを採用 (再適用しても安全)
  - 注入先 $9071/$8326/$91CC は本編コード = JP/US 同一だが region
    同一性に依存せず、毎回 位置+署名 を検証する

ROM レイアウト (clean JP / mapper66 拡張ROM 共通。expander は元 32KB PRG を
verbatim コピーするため file offset 不変):
  file = 0x10 + (cpu - 0x8000)
  $9071 フック        file 0x1081  "20 4B 97" -> "20 88 E7" (LOADER)
  $8326 フック        file 0x0336  "A5 28 6A" -> "20 B6 E7" (MAGICGATE)
  $91CC フック        file 0x11DC  "20 53 9D" -> "20 D8 E7" (DOORPREDRAW)
  LOADER     cave $E788  file 0x6798  (46B; wide-title idle cleanup now $E861)
  MAGICGATE  cave $E7B6  file 0x67C6  (34B)
  DOORPREDRAW cave $E7D8 file 0x67E8  (11B)
  DoorCellTable  $C180  file 0x4190  (64B、扉マスindex)
  RoomFlagTable  $C1C0  file 0x41D0  (64B、$0428 直接index、全$00=無改変)

隠し扉 (bit0): TEST_HiddenDoor.nes 実機確定(2026-05-17)を部屋別へ一般化。
  扉マス = $0304 + byte_from_position(level.fixed_door_pos) (エディタの
  扉位置。ステージ1=(7,9)→$A7→$03AB と実証版一致)。LOADER が面ロード後
  その扉マスに $40(隠し)を立て、$91CC 扉先行描画を抑止 (開始前画面の扉
  インジケータ消去)。石作成($46)/破壊($9BE3 AND#$3F→$06復元)は既存
  bit6 機構がそのまま動き、復元後は通常扉として開閉/クリアに乗る。
ブロック内扉 (bit1): 扉マスに $80 を立てて $86(扉|ブロック内) にする。
  原作の扉variantとして存在するため、石を壊すと通常扉へ復元される。
白ブロック内扉 (bit0+bit1): 扉マスに $C0 を立てて $C6 にする。
  本アプリの白ブロック内アイテム/鍵と同じ初期描画経路で、白い壊せる
  ブロックとして見せ、壊すと通常扉へ復元される。
"""

# ======================================================================
# ★★ CUSTOM RAM RESERVE (予約台帳) ★★  ── 勝手に空き扱いしない ──
# ======================================================================
# 改造で常駐RAMが要るとき、毎回ゼロから探すのは危険($0461 事故=
# サウンドch0状態RAMを"空き"と誤判定し暗闇面で妖精音が無限ループ。
# 2026-05-18)。新規RAMは ★必ずこの台帳を見て・追記してから 使うこと。
#
#   addr        name            用途                         状態
#   ----------  --------------  ---------------------------  ----------
#   $0723-$072B KEY_ENEMY_RUNTIME 鍵持ち敵runtime           予約済(使用中)
#   $072C-$0739 WIDETITLE_TRAMP wide title RAM-trampoline      予約済(★一時)
#                               ・title_screen.normalize_title_to_wide
#                                 専用。RAM_IN $072C(8B)/RAM_OUT $0734(6B)。
#                               ・★常駐でない: タイトル $CC4F 描画中
#                                 (NMI off窓 $9673〜$965F)だけ存在。grid
#                                 $0304-$03E3 末尾だが、静止タイトルは
#                                 level未ロードで未使用、demo/START の
#                                 level load で grid 全再init される前提。
#                               ・他機能はこの帯を ★title描画中に触らない。
#   $073A-$073F ENTITY_TAIL_CANDIDATE 補助候補6B          要probe
#   $0740-$074F PANEL_VARIANT_SETTINGS Panel stage-variant settings copy 予約中
#                               ・panel_monster_stage_variant.py が部屋ロード時に
#                                 PRG1 settings table からコピー。
#                               ・現在は speed+interval:
#                                 $0740=A speed / $0741=A interval /
#                                 $0742=B speed / $0743=B interval /
#                                 $0744=C speed / $0745=C interval。
#   $0750-$0767 VISIBLE_INBLOCK_ITEM_MASK 透明ブロック内アイテムbitmask 予約済(使用中)
#                               ・mapper66 loader がPRG1 0xF860 tableから24Bコピー。
#                               ・$E234 helper がNMI中に破壊的shiftで参照。
#   $0768-$076F CRACKED_INBLOCK_LIST ひび割れブロック内アイテム位置リスト
#                               予約済(使用中)
#                               ・mapper66 loader がPRG1 visible-item slot末尾8B
#                                 からコピー。死亡後one-shot skipで消えた
#                                 ひび割れ下地を描画前に$01へ戻し、
#                                 対応mask bitも消して中身再注入を防ぐ。
#   $0770-$0777 ENTITY_TAIL_CANDIDATE 補助候補8B          要probe
#   $0778       ROOMFLAGS       room flag table cache         予約済(使用中)
#   $0779       DARK_PHASE      暗闇 明滅フェーズカウンタ      予約済(使用中)
#   $077A       FINAL_STAGE_REDIRECT  current room final-stage redirect bit7,
#                                     copied by mapper66 room-load runtime
#                               ・bit7=この面クリア後に次ステージを最終面へ差し替え。
#   $077B       BLOCK_OVERRIDE_WORK 旧一時値候補              予約済(互換)
#   $077C       RUNTIME_DOOR_CELL 現在部屋の扉セル            予約済(使用中)
#   $077D       SEAL_BLOCK_VALUE Solomon's Seal block-state value 予約済(使用中)
#                               ・mapper66 StageExt loader がPRG1の部屋別表から
#                                 コピー。$00=原作$60 / $A0=茶ブロック内 /
#                                 $E0=白ブロック内。
#   $077E-$077F FAIRY_ENEMY_RUNTIME 落下死妖精化敵runtime 予約済(使用中)
#                               $077E=対象初期敵番号 / $077F=実行slot。
#
# ▼ ★bank1 (mapper66 拡張2本目PRG) 予約
#   ・file 0x80D0-0x87FF : wide decoder + blockA/B stream
#   ・file 0x8800-0x8A0F : StageExtTable
#   ・file 0x8A10-0x8A6F : Panel Variant combined runtime loader
#   ・file 0x8A70-0x8A75 : Panel Variant settings table
#   ・file 0x8A76-0x8E7F : PanelVariant PRG1 reserve
#   ・file 0x8E80-0x8EAA : visible item mask copy helper
#   ・file 0x8EAB-0x8EEA : Solomon Seal block-state table
#     (64B, 1 byte/room。StageExt loader が $077D へコピー)
#   ・file 0x8EEB-0x9018 : Transparent Solomon Seal suppress tables/helpers
#     (透明壊せるブロック内の取得済み紋章を再配置しないため、room load
#      後に $0304+cell を $50 へ戻し、$0750-$0767 のmask bitを消す)
#   ・file 0x9019-0x904C : mapper66 respawn direct-cell copy helper
#   ・file 0x904D-0x908F : cracked in-block one-shot respawn helper
#   ・file 0x9090-0x927F : wide-title ending renderer
#   ・file 0x9280-0xBB95 : PRG1 general reserve
#     (bank1 を使う改造を足すときは必ず上記予約を避ける)。
#   ・file 0xBB96   : SW byte = $FF 固定 (bank-switch bus-conflict
#     用。CPU $BB86。title_screen._WT_SW_B1_OFF)。データで踏まない。
#
# ▼ 安全域の根拠 (2026-05-18 実機接地)
#   ・entity main-slot = ★ちょうど21slot $057F-$0722 (実ROM
#     $B328/$B33D ポインタ表で確定。slot20=$070F 終端$0722)。
#   ・$0723-$077F = entity終端後の隙間。ramfree3_probe 285秒・
#     面$02/$04/$05/$08・妖精×4・死亡 で実機沈黙確認。
#     → v0.7.72で旧特殊ブロック32Bリストを廃止し、v0.7.149時点で
#        $0740-$074F はPanel Variant settings copyとして予約済み。
#        $0750-$0767 は透明ブロック内アイテムruntime maskとして予約済み。
#        $073A-$073F / $0768-$0777 は補助候補だが、
#        沈黙でも構造保証は弱いので正式使用前に用途別probe必須。
#   ・$0780-$07DF = probe で書込検出 = ★使用禁止。
#
# ▼ ★絶対に使ってはいけない領域 (間接/毎フレ衝突=症状が見えにくい)
#   $0200-$02FF OAM/DMA転送 / $0304-$03E3 blockグリッド /
#   $03E4-$03E5 JOY / $041F-$0425 action/sound queue /
#   $0426-$0455 room/timer/score/life/fairy 等ゲーム状態 /
#   ★$0456-$04D5 サウンド8ch状態($0456+$10*N、間接$0456,X) /
#   $04F7-$057E sub-slot / $057F-$0722 entity 21slot /
#   $07F0-$07FF highscore/GDV。
#   ※リテラル参照ゼロでも間接($base,X / ($zp),Y)で使われる。
#     「逆アセンブルに出ない=空き」は誤り(=$0461事故の本質)。
#
# ▼ 新規RAMが必要になったときの手順 (優先順)
#   1. ★まず "増やさない" を検討。既存値から再計算できないか?
#      例: room flag は $0428→$C1C0,X ROMテーブル再読込で RAM不要化可。
#          暗闇周期も $043C/$043D(global frame counter)から導出余地。
#   2. まとまったRAMが必要 → $0768-$0777 を候補にする。
#      小フラグだけでも予約済み範囲は使わない。
#      用途名を決めて上の表に追記してからコードで使う。
#   3. 長期保存 / 毎NMI書込 / 複数バイト連続使用 → ★再プローブ必須
#      (ramfree3_probe 流儀: 無音蓄積+低頻度要約、バグ再現シナリオ込み、
#       feedback_probe_no_flood_no_shared_lim.md 準拠)。
#   4. NMI中に毎フレ触るRAMは特に厳格に(サウンド/PPU/入力/DMA/slot
#      と衝突すると症状が分かりにくい。$0461事故がまさにこれ)。
# ======================================================================

# ---- bit 割当 ---------------------------------------------------------
# Current custom RAM ledger (ASCII mirror, keep this in sync with docs/ram_map_current.html):
#   $0723-$072B KEY_ENEMY_RUNTIME      key-carrying enemy runtime, reserved in use
#   $073A-$073F ENTITY_TAIL_CANDIDATE  secondary 6-byte candidate, probe before use
#   $0740-$074F PANEL_VARIANT_SETTINGS Panel stage-variant runtime settings copy, reserved in use
#   $0750-$0767 VISIBLE_INBLOCK_ITEM_MASK visible item in-block runtime mask, reserved in use
#   $0768-$076F CRACKED_INBLOCK_LIST   cracked in-block item cell list, reserved in use
#   $0770-$0777 ENTITY_TAIL_CANDIDATE  secondary 8-byte candidate, probe before use
#   $0778       ROOMFLAGS              room flag table cache, reserved in use
#   $0779       DARK_PHASE             dark-room phase counter, reserved in use
#   $077A       FINAL_STAGE_REDIRECT   bit7 redirects next stage to final room after clear
#   $077B       BLOCK_OVERRIDE_WORK    legacy temporary candidate, reserved for compatibility
#   $077C       RUNTIME_DOOR_CELL      current room door cell, reserved in use
#   $077D       SEAL_BLOCK_VALUE       Solomon's Seal block-state value from PRG1 table
#   $077E-$077F FAIRY_ENEMY_RUNTIME    fall-death fairy enemy initial slot/runtime slot
#
# Current ROM cave ledger lives in docs/rom_map_jp_mapper66_current.html.
# Do not add or move a hard-coded ROM/RAM address without updating the HTML
# ledgers in the same change. Overlapping reservations are release blockers.

BIT_HIDDEN_DOOR = 0x01  # bit0: 隠し扉 (扉マスに$40、開始前画面の扉描画抑止)
BIT_IN_BLOCK_DOOR = 0x02  # bit1: 茶ブロック内扉 (扉マスに$80、開始前画面の扉描画抑止)
DOOR_STATE_MASK = BIT_HIDDEN_DOOR | BIT_IN_BLOCK_DOOR
DOOR_STATE_NORMAL = 0x00
DOOR_STATE_HIDDEN = BIT_HIDDEN_DOOR
DOOR_STATE_IN_BLOCK = BIT_IN_BLOCK_DOOR
DOOR_STATE_WHITE_IN_BLOCK = DOOR_STATE_MASK  # 扉マスに$C0
BIT_NO_BFIRE    = 0x04  # bit2: B火球(魔法)禁止 (SE $08==$13 のみ却下)
BIT_NO_ASTONE   = 0x80  # bit7: A換石(石作成)禁止 (SE $08==$11 のみ却下)
                        #   ※A禁止は階段が作れず進行不能になり得る独立option
BIT_DARK        = 0x08  # bit3: 暗闇面 (この面プレイ中 BGを明滅で消す。
                        #   明/暗フレーム数は全体共通テンポ。必ず明から)
BIT_VISIBLE_INBLOCK_ITEMS = 0x20  # bit5: runtime-only visible item -> white in-block mask present
BIT_RUNTIME_SPECIAL_CELLS = 0x40  # bit6: runtime-only direct special cells present
RUNTIME_ONLY_FLAGS = BIT_VISIBLE_INBLOCK_ITEMS | BIT_RUNTIME_SPECIAL_CELLS
PRG0_EFFECT_FLAGS = 0xFF & ~RUNTIME_ONLY_FLAGS

ROOM_COUNT = 64  # RoomFlagTable サイズ ($0428 = $00..$34 / 53面+特殊)


def _cpu(file_off: int) -> int:
    raw = int(file_off) - 0x10
    if raw < 0x4000:
        return 0x8000 + raw
    return 0xC000 + (raw & 0x3FFF)


def _word(cpu: int) -> bytes:
    return bytes((int(cpu) & 0xFF, (int(cpu) >> 8) & 0xFF))

# ---- file offset (clean JP = 拡張ROM 共通) ----------------------------
OFF_HOOK_9071   = 0x1081   # JSR $974B (3B)
OFF_SIG_9074    = 0x1084   # 署名: 改造対象を含まない $9074〜
SIG_9074        = bytes.fromhex("a9 02 05 7c 85 7c 20 b9 91 20 5e 91")
ORIG_9071       = bytes.fromhex("20 4b 97")  # JSR $974B

OFF_HOOK_8326   = 0x0336   # LDA $28 / ROR A (3B)
OFF_SIG_8329    = 0x0339   # 署名: 改造対象を含まない $8329〜
SIG_8329        = bytes.fromhex("b0 42 29 08 d0 3e ad 82 05 aa 38 e9")
ORIG_8326       = bytes.fromhex("a5 28 6a")  # LDA $28 / ROR A

OFF_HOOK_91CC   = 0x11DC   # JSR $9D53 (3B) = 扉の先行描画 (R179: $91CC=扉)
OFF_SIG_91C1    = 0x11D1   # 署名: 改造対象を含まない $91C1〜 (11B)
SIG_91C1        = bytes.fromhex("a2 02 c8 b1 30 d0 02 a2 35 86 03")
ORIG_91CC       = bytes.fromhex("20 53 9d")  # JSR $9D53 (扉先行描画)
OFF_HOOK_909A   = 0x10AA   # JSR $95E4 (grid -> nametable)
ORIG_909A       = bytes.fromhex("20 e4 95")

# ---- cave / table レイアウト (clean JP = 拡張ROM 共通) ----------------
# 空き領域 $BBDE-$C1FF (file 0x3BEE-0x4210, 1570B, 全 EA/00 実機裏取り)
OFF_LOADER_CAVE = 0x6798   # $E788  LOADER (46B)
OFF_MAGIC_CAVE  = 0x67C6   # $E7B6  MAGICGATE (34B)
OFF_DOOR_CAVE   = 0x67E8   # $E7D8  DOORPREDRAW (11B)
OFF_DOORTAB     = 0x4190   # $C180  DoorCellTable (64B; mapper66ではStageExtへ移設)
OFF_TABLE       = 0x41D0   # $C1C0  RoomFlagTable (64B; mapper66ではStageExtへ移設)
OFF_DARK_CAVE   = 0x67F3   # $E7E3  DARK / runtime dispatch
OFF_TEMPO       = 0x682B   # $E81B  全体共通テンポ 2B [LIGHT, PERIOD]
OFF_VISIBLE_INBLOCK_HELPER = 0x6244  # $E234  visible item bitmask -> white in-block helper
VISIBLE_INBLOCK_HELPER_CAPACITY = 0x18
OFF_WHITE_INBLOCK_RUNTIME_EXT = OFF_VISIBLE_INBLOCK_HELPER + VISIBLE_INBLOCK_HELPER_CAPACITY  # $E24C
OFF_BW_CAVE     = 0x682D   # $E81D  runtime special-cell scanner
OFF_CAVE_FREE0  = 0x3BEE   # $BBDE  (cave 空き判定の起点)
OFF_CAVE_FREE1  = 0x4210   # $C200  (cave 空き判定の終点)
OFF_TITLE_IDLE_DEMO_CLEAR = 0x6871  # $E861  wide-title idle demo cleanup (9B)
OFF_TITLE_IDLE_DEMO_CLEAR_OLD = 0x3C1E  # $BC0E old wide-title idle cleanup slot
TITLE_IDLE_DEMO_CLEAR_SIZE = 9

CPU_LOADER_CAVE = _cpu(OFF_LOADER_CAVE)
CPU_MAGIC_CAVE = _cpu(OFF_MAGIC_CAVE)
CPU_DOOR_CAVE = _cpu(OFF_DOOR_CAVE)
CPU_DARK_CAVE = _cpu(OFF_DARK_CAVE)
CPU_TEMPO_LIGHT = _cpu(OFF_TEMPO)
CPU_TEMPO_PERIOD = CPU_TEMPO_LIGHT + 1
CPU_BW_CAVE = _cpu(OFF_BW_CAVE)
HOOK_909A_NEW = bytes.fromhex("20") + _word(CPU_BW_CAVE)

# 暗闇 NMI フック: $8055 LDA $0301 (PPUMASK shadow読込、毎フレNMI)
OFF_HOOK_8055   = 0x0065   # $8055
OFF_SIG_804B    = 0x005B   # 署名: 改造対象を含まない $804B〜 (10B)
SIG_804B        = bytes.fromhex("bd ef 80 9d ef 80 a9 80 85 7d")
ORIG_8055       = bytes.fromhex("ad 01 03")  # LDA $0301
HOOK_8055_NEW   = bytes.fromhex("20") + _word(CPU_DARK_CAVE)

# DARK cave @ $E7E3: ROOMFLAGS bit3 & Dana実プレイ($057F>=$C0)
#   の時だけ フェーズカウンタ $0779 を進め、$E81B(LIGHT)未満=明
#   (原 $0301)/ 以上=暗(bit3クリアでBG-off) / $E81C(PERIOD)で0復帰。
#   非該当時は $0779=0 リセット → 暗闇面は必ず「明」から開始。
#   LOADER は非改変(独立)。$8058 STA $2001 が返り A を書く。
#   ★R-fix(2026-05-18): ROOMFLAGS/フェーズカウンタを $0460/$0461 から
#     $0778/$0779 へ移設。$0460/$0461 はサウンドch0状態RAM
#     ($0456+$10*N の ch0 +$0A/+$0B)で、暗闇面で毎NMI $0461 を踏み
#     妖精取得音($0F)が無限ループした(実機 PC=$F2F7 サウンドが$0461
#     書込を確認)。$0778/$0779 = entity 21slot 終端$0722 の後ろ +
#     ramfree3_probe 285秒 沈黙確認の二重安全域。
DARK_CAVE = (
    bytes.fromhex("ad78072908f025ae7f05e0c0901eee7907ad7907cd")
    + _word(CPU_TEMPO_PERIOD)
    + bytes.fromhex("9005a9008d7907ad7907cd")
    + _word(CPU_TEMPO_LIGHT)
    + bytes.fromhex("900bad010329f760a9008d7907ad010360")
)
assert len(DARK_CAVE) == 53
# 0x3CC8-0x3CDF is reserved by key_enemy_runtime's fall-death handler.
DARK_CAVE_RESERVED_SIZE = 0x38
DARK_CAVE_BLOB = DARK_CAVE + bytes([0xEA] * (DARK_CAVE_RESERVED_SIZE - len(DARK_CAVE)))
assert len(DARK_CAVE_BLOB) == DARK_CAVE_RESERVED_SIZE

# Runtime block override routine @ $E81D.
# Replaces the stage-start $909A JSR $95E4 call. It first calls the original
# grid -> nametable renderer, then converts the grid values before the screen is
# shown. This preserves the special IDs for visual rendering while still giving
# the live grid the normal collision/break values.
# It converts direct m66 special cell IDs:
#   $F9 -> $90  breakable white
#   $FA -> $10  passable white
#   $01 -> $D0  cracked brown block
#   $40 -> $F8  invisible solid
#   $50 -> $90  invisible breakable
#   $A3 -> $10  passable brown
#   $A4 -> $F8  solid brown
# Direct white in-block item lowering must not use the apparent $DB61 zero area:
# it is enemy state-speed data reached through the $D9D3 pointer table.
# $E234 consumes the visible-item mask for every cell. When the mask bit is set,
# the original path still converts normal/cracked mask cells to $C0+item. When
# the mask bit is clear, it branches to $E24C; direct $C0-$F7 white in-block
# item cells have already been drawn as white, so only the live grid is lowered
# to $80-$B7 for the normal two-hit block-item flow. Existing $80-$BF cells are
# stored back unchanged by the same path.
BW_CAVE = bytes.fromhex(
    "20e495ad78072960f026a018a2c02034e2c901f024c940"
    "f018c9a4f014c950f014c9f9f010c9faf014c9a3f010"
    "cad0de60a9f8d00aa990d006a9d0d002a9109d1303d0e9"
)
BW_CAVE_RESERVED_SIZE = 68
assert len(BW_CAVE) <= BW_CAVE_RESERVED_SIZE
BW_CAVE_BLOB = BW_CAVE + bytes([0xEA] * (BW_CAVE_RESERVED_SIZE - len(BW_CAVE)))
assert len(BW_CAVE_BLOB) == BW_CAVE_RESERVED_SIZE

VISIBLE_INBLOCK_HELPER = bytes.fromhex(
    "8a2907d00188b950070a995007bd1303900609c09d130360"
)
assert len(VISIBLE_INBLOCK_HELPER) <= VISIBLE_INBLOCK_HELPER_CAPACITY
WHITE_INBLOCK_RUNTIME_EXT = bytes.fromhex("1009c9f8b00529bf9d130360")
assert len(WHITE_INBLOCK_RUNTIME_EXT) == 12
OFF_VISIBLE_INBLOCK_FREE = OFF_WHITE_INBLOCK_RUNTIME_EXT + len(WHITE_INBLOCK_RUNTIME_EXT)
VISIBLE_INBLOCK_FREE_LEN = 24
assert OFF_WHITE_INBLOCK_RUNTIME_EXT == OFF_VISIBLE_INBLOCK_HELPER + len(VISIBLE_INBLOCK_HELPER)
assert VISIBLE_INBLOCK_FREE_LEN == 24
# 全体共通テンポ既定: 明45フレ / 暗100フレ → PERIOD=145
TEMPO_DEFAULT = bytes([45, 145])  # [LIGHT, PERIOD(=LIGHT+DARK)]

# ---- フック差替バイト -------------------------------------------------
HOOK_9071_NEW = bytes.fromhex("20") + _word(CPU_LOADER_CAVE)
HOOK_8326_NEW = bytes.fromhex("20") + _word(CPU_MAGIC_CAVE)
HOOK_91CC_NEW = bytes.fromhex("20") + _word(CPU_DOOR_CAVE)

# LOADER cave @ $E788 (46B):
#   JSR $974B            ; 原処理(level load)再現
#   LDX $0428 / LDA $C1C0,X / STA $0778   ; ROOMFLAGS ロード
#   AND #$10             ; bit4 = ステージ開始時ファイヤー所持リセット?
#   BEQ +11              ;   立ってなければ何もしない
#   LDA #$00 / STA $042E / STA $042F
#   JSR $A1CC            ; HUD fire stock redraw. $042B(max/cursor)は触らない
#   LDA $0778 / AND #$03 ; bit0=隠し / bit1=茶ブロック内 / 両方=白ブロック内
#   BEQ +17 (->RTS)      ;   立ってなければ何もしない
#   ASL x6               ; bit0->$40 / bit1->$80 / 両方->$C0
#   PHA / LDX $077C / PLA
#   ORA $0304,X / STA $0304,X             ; 扉マスに状態bitを立てる
#   RTS
#   ★R-fix: ROOMFLAGS $0460→$0778 (サウンドRAM衝突回避、上の DARK 注記)
LOADER_CAVE = bytes.fromhex(
    "20 4b 97 ad 78 07 "
    "29 10 f0 0b a9 00 8d 2e 04 8d 2f 04 20 cc a1 "
    "ad 78 07 29 03 f0 11 0a 0a 0a 0a 0a 0a 48 "
    "ae 7c 07 68 1d 04 03 9d 04 03 60"
)
assert len(LOADER_CAVE) == 46
assert 10 + LOADER_CAVE[9] == 21  # fire-reset skip lands on the door-state load.
assert 28 + LOADER_CAVE[27] == len(LOADER_CAVE) - 1  # no-door skip lands on RTS.
assert LOADER_CAVE[-1] == 0x60

# MAGICGATE cave @ $E7B6 (34B): bit2=B火球禁止 / bit7=A換石禁止 (独立)
#   SE id $08: $13=B火球 / $11=A換石。該当 bit & 該当 SE のみ却下
#         LDA $0778 / AND #$04 / BEQ chkA   ; bit2 B禁止?
#         LDA $08 / CMP #$13 / BEQ reject    ; B火球なら却下
#   chkA: LDA $0778 / AND #$80 / BEQ pass   ; bit7 A禁止?
#         LDA $08 / CMP #$11 / BEQ reject    ; A換石なら却下
#   pass:   LDA $28 / ROR A / RTS           ; 原 $8326 再現→$8329 復帰
#   reject: PLA / PLA / SEC / RTS           ; $8326 呼び元へ却下
#   ★R-fix: ROOMFLAGS $0460→$0778 (サウンドRAM衝突回避)
MAGIC_CAVE = bytes.fromhex(
    "ad 78 07 29 04 f0 06 a5 08 c9 13 f0 11 "
    "ad 78 07 29 80 f0 06 a5 08 c9 11 f0 04 "
    "a5 28 6a 60 68 68 38 60"
)

# DOORPREDRAW cave @ $E7D8 (11B): 隠し/ブロック内扉は開始前画面の扉描画を抑止
#   LDA $0778 / AND #$03 / BNE skip       ; bit0/1 立ってたら扉を描かない
#   JSR $9D53                              ; 通常=扉先行描画
# skip: RTS                                ; ($91CF へ復帰)
#   ★R-fix: ROOMFLAGS $0460→$0778 (サウンドRAM衝突回避)
DOOR_CAVE = bytes.fromhex("ad 78 07 29 03 d0 03 20 53 9d 60")

assert OFF_MAGIC_CAVE == OFF_LOADER_CAVE + len(LOADER_CAVE)
assert OFF_DOOR_CAVE == OFF_MAGIC_CAVE + len(MAGIC_CAVE)
assert OFF_DARK_CAVE == OFF_DOOR_CAVE + len(DOOR_CAVE)
assert OFF_TEMPO == OFF_DARK_CAVE + DARK_CAVE_RESERVED_SIZE
assert OFF_BW_CAVE == OFF_TEMPO + 2
assert OFF_BW_CAVE + BW_CAVE_RESERVED_SIZE == 0x6871


BIT_FIRE_RESET = 0x10  # stage load clears carried fire scroll stock.


def normalize_flags(flags: int) -> int:
    """Runtime room flags normalization.

    Door bits are a compact 2-bit state:
    0=normal, bit0=hidden, bit1=brown in-block, bit0+bit1=white in-block.
    """
    return int(flags) & 0xFF


class RoomFlagError(ValueError):
    """Room Flag Table 改造の検証失敗 (改造ROM/拡張ROM/破損の可能性)"""


def _verify(rom_data) -> None:
    """(A)位置 + (B)署名 のダブル検証。失敗時 RoomFlagError"""
    need = OFF_TABLE + ROOM_COUNT
    if len(rom_data) < need:
        raise RoomFlagError(
            f"ROM が小さすぎます (len={len(rom_data)} < {need})。"
            "Room Flag 改造を中止します。"
        )
    # (B) 署名: 改造対象を含まない安定並び
    if bytes(rom_data[OFF_SIG_9074:OFF_SIG_9074 + len(SIG_9074)]) != SIG_9074:
        raise RoomFlagError(
            "$9074 署名不一致。改造ROM/拡張ROM/破損の可能性があるため中止します。"
        )
    if bytes(rom_data[OFF_SIG_8329:OFF_SIG_8329 + len(SIG_8329)]) != SIG_8329:
        raise RoomFlagError(
            "$8329 署名不一致。改造ROM/拡張ROM/破損の可能性があるため中止します。"
        )
    if bytes(rom_data[OFF_SIG_91C1:OFF_SIG_91C1 + len(SIG_91C1)]) != SIG_91C1:
        raise RoomFlagError(
            "$91C1 署名不一致。改造ROM/拡張ROM/破損の可能性があるため中止します。"
        )
    if bytes(rom_data[OFF_SIG_804B:OFF_SIG_804B + len(SIG_804B)]) != SIG_804B:
        raise RoomFlagError(
            "$804B 署名不一致。改造ROM/拡張ROM/破損の可能性があるため中止します。"
        )
    # (A) フック位置: 原作バイト または 既適用バイト のいずれか
    for off, orig, new, name in (
        (OFF_HOOK_9071, ORIG_9071, HOOK_9071_NEW, "$9071"),
        (OFF_HOOK_8326, ORIG_8326, HOOK_8326_NEW, "$8326"),
        (OFF_HOOK_91CC, ORIG_91CC, HOOK_91CC_NEW, "$91CC"),
        (OFF_HOOK_8055, ORIG_8055, HOOK_8055_NEW, "$8055 (暗闇)"),
        (OFF_HOOK_909A, ORIG_909A, HOOK_909A_NEW, "$909A (特殊セル変換)"),
    ):
        cur = bytes(rom_data[off:off + 3])
        if cur not in (orig, new):
            raise RoomFlagError(
                f"{name} が想定外 ({cur.hex()})。別改造と競合の可能性が"
                "あるため中止します。"
            )
    # cave 空き: 原作(EA/00) / 既注入の各 cave・table は許容。
    # ★gap_fix(原作バグ回避 横穴侵入安定化) の cave も4096B跡地側に
    #   置くため、両機能を同時適用できるよう許容スパンに含める。
    from . import gap_fix as _gf
    from . import gargoyle_variant as _gv
    from . import panel_monster_variant as _pmv
    from . import panel_monster_stage_variant as _pmsv
    from . import saramandor_variant as _sv
    from . import spark_ball_variant as _sbv
    from . import key_enemy_runtime as _ker
    from . import final_stage_redirect as _fsr
    from . import new_enemy_runtime as _ner
    expanded = len(rom_data) == 0x18010
    table_spans = ((OFF_DOORTAB, ROOM_COUNT * 2),) if expanded else (
        (OFF_DOORTAB, ROOM_COUNT),
        (OFF_TABLE, ROOM_COUNT),
    )
    pmsv_capacity_spans = (
        (_pmsv.OFF_FINAL_PANEL_TYPE_CLASSIFIER, len(_pmsv.FINAL_PANEL_TYPE_CLASSIFIER)),
        (_pmsv.OFF_FINAL_FIRE_MARKER_TABLE, len(_pmsv.FINAL_FIRE_MARKER_TABLE)),
        (_pmsv.OFF_FINAL_GROUP_RAM_OFFSET_HELPER, len(_pmsv.FINAL_GROUP_RAM_OFFSET_HELPER)),
        (_pmsv.OFF_FINAL_STATIC_MARKER_HELPER, len(_pmsv.FINAL_STATIC_MARKER_HELPER)),
        (
            _pmsv.OFF_FINAL_BULLET_SPEED_APPLY,
            _pmsv._v2_split_speed_reserved_sizes()["speed_decode"],
        ),
    )
    _spans = (
        (OFF_LOADER_CAVE, len(LOADER_CAVE)),
        (OFF_MAGIC_CAVE, len(MAGIC_CAVE)),
        (OFF_DOOR_CAVE, len(DOOR_CAVE)),
        (OFF_TITLE_IDLE_DEMO_CLEAR, TITLE_IDLE_DEMO_CLEAR_SIZE),
        (OFF_TITLE_IDLE_DEMO_CLEAR_OLD, TITLE_IDLE_DEMO_CLEAR_SIZE),
        *table_spans,
        (_gf.OFF_CAVE, len(_gf.CAVE)),       # gap_fix 共存
        (OFF_DARK_CAVE, DARK_CAVE_RESERVED_SIZE),  # 暗闇 cave
        (OFF_TEMPO, 2),                      # 暗闇テンポ
        (OFF_BW_CAVE, BW_CAVE_RESERVED_SIZE),
        (OFF_WHITE_INBLOCK_RUNTIME_EXT, len(WHITE_INBLOCK_RUNTIME_EXT)),
        *_sv.RESERVED_SPANS,                 # Saramandor #2 bullet variant
        *_gv.RESERVED_SPANS,                 # Gargoyle #2 slow-Bullet variant
        *_pmv.RESERVED_SPANS,                # Panel Monster borrowed-ID variants
        *_pmsv.RESERVED_SPANS,               # Panel Variant A/B/C split runtime
        *pmsv_capacity_spans,                # Panel Variant legacy tail compatibility
        *_sbv.RESERVED_SPANS,                # Spark Ball Dragon-ID variants
        *_ner.RESERVED_SPANS,                # New enemy dispatcher and Ice Flame runtime
        *_ker.RESERVED_SPANS,                # Key-carrying initial enemy runtime
        *_fsr.RESERVED_SPANS,                # Clear this room, then load final room
    )
    for i in range(OFF_CAVE_FREE0, OFF_CAVE_FREE1):
        if rom_data[i] in (0xEA, 0x00):
            continue
        if any(o <= i < o + ln for o, ln in _spans):
            continue
        raise RoomFlagError(
            f"bank0 cave (file 0x{i:X}) が空きでありません。"
            "別改造と競合の可能性があるため Room Flag 改造を中止します。"
        )
    helper_cur = bytes(
        rom_data[
            OFF_VISIBLE_INBLOCK_HELPER:
            OFF_VISIBLE_INBLOCK_HELPER + len(VISIBLE_INBLOCK_HELPER)
        ]
    )
    if helper_cur != VISIBLE_INBLOCK_HELPER and any(
        b not in (0xEA, 0x00) for b in helper_cur
    ):
        raise RoomFlagError(
            f"VisibleInBlock helper (file 0x{OFF_VISIBLE_INBLOCK_HELPER:X}) "
            "が空きでありません。別改造と競合の可能性があるため中止します。"
        )
    white_ext_cur = bytes(
        rom_data[
            OFF_WHITE_INBLOCK_RUNTIME_EXT:
            OFF_WHITE_INBLOCK_RUNTIME_EXT + len(WHITE_INBLOCK_RUNTIME_EXT)
        ]
    )
    if white_ext_cur != WHITE_INBLOCK_RUNTIME_EXT and any(
        b not in (0xEA, 0x00) for b in white_ext_cur
    ):
        raise RoomFlagError(
            f"WhiteInBlock runtime extension (file 0x{OFF_WHITE_INBLOCK_RUNTIME_EXT:X}) "
            "が空きでありません。別改造と競合の可能性があるため中止します。"
        )

def build_table(room_flags: list) -> bytearray:
    """levels の room_flags(list[int]) から 64B RoomFlagTable を構築"""
    tbl = bytearray(ROOM_COUNT)
    for i, fl in enumerate(room_flags):
        if i >= ROOM_COUNT:
            break
        tbl[i] = normalize_flags(fl)
    return tbl


def read_table(rom_data, count: int = 53) -> list:
    """ROM内の RoomFlagTable を Level.room_flags 用に復元する。

    原作ROM/未適用ROMでは table 領域が空き/残骸の可能性があるため、
    Room Flag 系フックが1つでも有効な時だけ表を信用する。
    """
    count = max(0, min(int(count), ROOM_COUNT))
    if rom_data is None or len(rom_data) < OFF_TABLE + ROOM_COUNT:
        return [0] * count
    if len(rom_data) == 0x18010:
        try:
            from . import stage_ext
            flags = stage_ext.read_runtime_room_flags(bytes(rom_data), count)
            return [f & ~RUNTIME_ONLY_FLAGS for f in flags]
        except Exception:
            pass
    hooks = (
        (OFF_HOOK_9071, HOOK_9071_NEW),
        (OFF_HOOK_8326, HOOK_8326_NEW),
        (OFF_HOOK_91CC, HOOK_91CC_NEW),
        (OFF_HOOK_8055, HOOK_8055_NEW),
    )
    active = any(bytes(rom_data[o:o + 3]) == sig for o, sig in hooks)
    if not active:
        return [0] * count
    return [
        (rom_data[OFF_TABLE + i] & 0xFF) & ~RUNTIME_ONLY_FLAGS
        for i in range(count)
    ]


def build_door_table(door_cells: list) -> bytearray:
    """各レベルの扉マス index ($0304 基準の位置バイト) から 64B 表を構築"""
    tbl = bytearray(ROOM_COUNT)
    for i, dc in enumerate(door_cells or []):
        if i >= ROOM_COUNT:
            break
        tbl[i] = dc & 0xFF
    return tbl


def is_needed(room_flags: list) -> bool:
    """1部屋でもフラグが立っていれば注入が必要"""
    return any((f & PRG0_EFFECT_FLAGS) for f in room_flags)


def _breakable_white_needed(bw_cells_by_room: list = None) -> bool:
    for cells in (bw_cells_by_room or []):
        if isinstance(cells, dict):
            if any(bool(v) for v in cells.values()):
                return True
        elif cells:
            return True
    return False


def _dark_needed(room_flags: list) -> bool:
    """暗闇ビットが1部屋でも立っているか"""
    return any((f & BIT_DARK) for f in room_flags)


def get_tempo(rom_data) -> tuple:
    """暗闇の全体共通テンポ (light_frames, dark_frames) を取得。
    DARK cave 未注入(テンポ領域が空き)なら既定値を返す。"""
    seg = bytes(rom_data[OFF_TEMPO:OFF_TEMPO + 2])
    if all(b in (0xEA, 0x00) for b in seg):
        L, P = TEMPO_DEFAULT[0], TEMPO_DEFAULT[1]
    else:
        L, P = seg[0], seg[1]
    light = max(1, L)
    dark = max(1, P - L)
    return (light, dark)


def set_tempo(rom_data, light_frames: int, dark_frames: int) -> None:
    """暗闇テンポを設定 (フレーム単位、明→暗 の順で必ず明から始まる)。
    内部は [LIGHT, PERIOD(=LIGHT+DARK)] の2バイト。1..254 にクランプ
    (PERIOD<=255 のため light+dark<=255)。"""
    _verify(rom_data)
    light = max(1, min(200, int(light_frames)))
    dark = max(1, min(254 - light, int(dark_frames)))
    rom_data[OFF_TEMPO] = light & 0xFF
    rom_data[OFF_TEMPO + 1] = (light + dark) & 0xFF


# 原作復元時に戻す3フック
_HOOKS = (
    (OFF_HOOK_9071, ORIG_9071, HOOK_9071_NEW, "$9071"),
    (OFF_HOOK_8326, ORIG_8326, HOOK_8326_NEW, "$8326"),
    (OFF_HOOK_91CC, ORIG_91CC, HOOK_91CC_NEW, "$91CC (扉先行描画)"),
)


def apply(rom_data, room_flags: list, door_cells: list = None,
          breakable_white_cells: list = None) -> list:
    """Room Flag Table 改造を rom_data に適用。

    room_flags: レベル順の int リスト (各 = その部屋のフラグバイト)。
                bit0=隠し扉 / bit2=B火球禁止。全0=原作復元。
    door_cells: レベル順の扉マス index リスト (= byte_from_position(
                level.fixed_door_pos))。bit0 の部屋でのみ参照。
    戻り値: 変更内容の説明リスト。検証失敗時 RoomFlagError (フォールバック禁止)。
    """
    _verify(rom_data)
    changed = []
    tbl = build_table(room_flags)
    dtab = build_door_table(door_cells)
    prg0_needed = is_needed(room_flags)
    runtime_needed = any((f & RUNTIME_ONLY_FLAGS) for f in room_flags or [])
    expanded = len(rom_data) == 0x18010
    fixed_runtime = expanded

    if not fixed_runtime and not prg0_needed and not runtime_needed:
        # 原作復元: フック3点のみ原作へ戻す。cave/表は死にコード化で
        # 触らない (フックを戻せば二度と到達しない=挙動は原作と完全同一。
        # cave 空きは元 00/EA 混在で per-byte 原型不明、一律埋めは逆効果)
        for off, orig, _new, name in _HOOKS:
            if bytes(rom_data[off:off + 3]) != orig:
                rom_data[off:off + 3] = orig
                changed.append(f"{name} フック→原作復元 (cave は死にコード化)")
        if bytes(rom_data[OFF_HOOK_8055:OFF_HOOK_8055 + 3]) != ORIG_8055:
            rom_data[OFF_HOOK_8055:OFF_HOOK_8055 + 3] = ORIG_8055
            changed.append("$8055 (暗闇) フック→原作復元")
        if bytes(rom_data[OFF_HOOK_909A:OFF_HOOK_909A + 3]) != ORIG_909A:
            rom_data[OFF_HOOK_909A:OFF_HOOK_909A + 3] = ORIG_909A
            changed.append("$909A (特殊セル変換) フック→原作復元")
        return changed

    if fixed_runtime or prg0_needed:
        # cave コード注入
        for off, blob, name in (
            (OFF_LOADER_CAVE, LOADER_CAVE, "LOADER ($E788)"),
            (OFF_MAGIC_CAVE, MAGIC_CAVE, "MAGICGATE ($E7B6)"),
            (OFF_DOOR_CAVE, DOOR_CAVE, "DOORPREDRAW ($E7D8)"),
        ):
            if bytes(rom_data[off:off + len(blob)]) != blob:
                rom_data[off:off + len(blob)] = blob
                changed.append(f"{name} cave 注入")
    # DoorCellTable / RoomFlagTable 書込。mapper66では同じ情報をPRG1
    # StageExtTableへ移し、PRG0 $C180-$C1FF はコード用に空ける。
    if prg0_needed and not expanded and bytes(rom_data[OFF_DOORTAB:OFF_DOORTAB + ROOM_COUNT]) != bytes(dtab):
        rom_data[OFF_DOORTAB:OFF_DOORTAB + ROOM_COUNT] = bytes(dtab)
        changed.append("DoorCellTable 書込")
    if prg0_needed and not expanded and bytes(rom_data[OFF_TABLE:OFF_TABLE + ROOM_COUNT]) != bytes(tbl):
        rom_data[OFF_TABLE:OFF_TABLE + ROOM_COUNT] = bytes(tbl)
        n = sum(1 for b in tbl if b)
        changed.append(f"RoomFlagTable 書込 ({n}部屋にフラグ)")
    # フック有効化
    if fixed_runtime or prg0_needed:
        for off, _orig, new, name in _HOOKS:
            if bytes(rom_data[off:off + 3]) != new:
                rom_data[off:off + 3] = new
                changed.append(f"{name} フック有効化")
    else:
        for off, orig, _new, name in _HOOKS:
            if bytes(rom_data[off:off + 3]) != orig:
                rom_data[off:off + 3] = orig
                changed.append(f"{name} フック→原作復元")

    if fixed_runtime or runtime_needed:
        if bytes(rom_data[OFF_VISIBLE_INBLOCK_HELPER:OFF_VISIBLE_INBLOCK_HELPER + len(VISIBLE_INBLOCK_HELPER)]) != VISIBLE_INBLOCK_HELPER:
            rom_data[OFF_VISIBLE_INBLOCK_HELPER:OFF_VISIBLE_INBLOCK_HELPER + len(VISIBLE_INBLOCK_HELPER)] = VISIBLE_INBLOCK_HELPER
            changed.append("VisibleInBlock helper 注入 ($E234)")
        if bytes(rom_data[OFF_WHITE_INBLOCK_RUNTIME_EXT:OFF_WHITE_INBLOCK_RUNTIME_EXT + len(WHITE_INBLOCK_RUNTIME_EXT)]) != WHITE_INBLOCK_RUNTIME_EXT:
            rom_data[OFF_WHITE_INBLOCK_RUNTIME_EXT:OFF_WHITE_INBLOCK_RUNTIME_EXT + len(WHITE_INBLOCK_RUNTIME_EXT)] = WHITE_INBLOCK_RUNTIME_EXT
            changed.append("WhiteInBlock runtime extension 注入 ($E24C)")
        if bytes(rom_data[OFF_BW_CAVE:OFF_BW_CAVE + BW_CAVE_RESERVED_SIZE]) != BW_CAVE_BLOB:
            rom_data[OFF_BW_CAVE:OFF_BW_CAVE + BW_CAVE_RESERVED_SIZE] = BW_CAVE_BLOB
            changed.append("BreakableWhite cave 注入 ($E81D)")
        if bytes(rom_data[OFF_HOOK_909A:OFF_HOOK_909A + 3]) != HOOK_909A_NEW:
            rom_data[OFF_HOOK_909A:OFF_HOOK_909A + 3] = HOOK_909A_NEW
            changed.append("$909A (特殊セル変換) フック有効化")
    else:
        if bytes(rom_data[OFF_HOOK_909A:OFF_HOOK_909A + 3]) != ORIG_909A:
            rom_data[OFF_HOOK_909A:OFF_HOOK_909A + 3] = ORIG_909A
            changed.append("$909A (特殊セル変換) フック→原作復元")

    # 暗闇: dark ビットが1部屋でもあれば DARK cave + テンポ + $8055 フック。
    # 無ければ $8055 は原作のまま(暗闇未使用時は NMI 非フック=完全無影響)。
    if fixed_runtime or _dark_needed(room_flags):
        if bytes(rom_data[OFF_DARK_CAVE:OFF_DARK_CAVE + DARK_CAVE_RESERVED_SIZE]) != DARK_CAVE_BLOB:
            rom_data[OFF_DARK_CAVE:OFF_DARK_CAVE + DARK_CAVE_RESERVED_SIZE] = DARK_CAVE_BLOB
            changed.append("DARK cave 注入 ($E7E3)")
        # テンポ: 空き(未設定)なら既定。設定済みなら保持(ユーザー値尊重)
        tseg = bytes(rom_data[OFF_TEMPO:OFF_TEMPO + 2])
        if all(b in (0xEA, 0x00) for b in tseg):
            rom_data[OFF_TEMPO:OFF_TEMPO + 2] = TEMPO_DEFAULT
            changed.append("暗闇テンポ 既定設定 (明45/暗100)")
        if bytes(rom_data[OFF_HOOK_8055:OFF_HOOK_8055 + 3]) != HOOK_8055_NEW:
            rom_data[OFF_HOOK_8055:OFF_HOOK_8055 + 3] = HOOK_8055_NEW
            changed.append("$8055 (暗闇) フック有効化")
    else:
        if bytes(rom_data[OFF_HOOK_8055:OFF_HOOK_8055 + 3]) != ORIG_8055:
            rom_data[OFF_HOOK_8055:OFF_HOOK_8055 + 3] = ORIG_8055
            changed.append("$8055 (暗闇) フック→原作復元 (暗闇面なし)")

    return changed

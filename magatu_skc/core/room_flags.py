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
  bit0 = 隠し扉            (ステップ2で cave 拡張、本モジュールは枠のみ)
  bit1 = ブロック内扉      (扉セルにbit7を立て、開始前扉描画を抑止)
  bit2 = B火球(魔法)禁止   ← ステップ1で実装
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
  $9071 フック        file 0x1081  "20 4B 97" -> "20 E0 BB" (LOADER)
  $8326 フック        file 0x0336  "A5 28 6A" -> "20 20 BC" (MAGICGATE)
  $91CC フック        file 0x11DC  "20 53 9D" -> "20 50 BC" (DOORPREDRAW)
  LOADER     cave $BBE0  file 0x3BF0  (46B; plus 9B idle-demo cleanup at $BC0E)
  MAGICGATE  cave $BC20  file 0x3C30  (34B)
  DOORPREDRAW cave $BC50 file 0x3C60  (11B)
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
#   $0740-$074F PANEL_VARIANT_CACHE Panel stage-variant cache 予約中
#                               ・panel_monster_stage_variant.py が部屋ロード時に
#                                 PRG1 PanelVariantStageTable からコピー。
#                               ・現在は speed+interval:
#                                 $0740=A speed / $0741=A interval /
#                                 $0742=B speed / $0743=B interval /
#                                 $0744=C speed / $0745=C interval。
#   $0750-$075F OLD_RUNTIME_BLOCK_LIST 旧特殊ブロックlist 残り候補16B
#                               ・v0.7.72で特殊ブロックはm66セルID直書き化。
#                               ・旧PRG1→$0740コピーは無効化済み。
#                               ・Panel stage variant が $0740-$074F を予約。
#   $0760-$0777 ENTITY_TAIL_CANDIDATE 補助候補24B         要probe
#   $0778       ROOMFLAGS       room flag table cache         予約済(使用中)
#   $0779       DARK_PHASE      暗闇 明滅フェーズカウンタ      予約済(使用中)
#   $077A-$077B BLOCK_OVERRIDE_WORK 一時フラグ/値             予約済(使用中)
#   $077C       RUNTIME_DOOR_CELL 現在部屋の扉セル            予約済(使用中)
#   $077D-$077F FREE_CANDIDATE  (未割当・小フラグ/カウンタ用)  補助候補3B
#                               まとまったRAMは$0750-$075Fを優先。
#                               使用前に必ず再probe・用途名を決めて追記。
#
# ▼ ★bank1 (mapper66 拡張2本目PRG) 予約
#   ・file 0x80D0-0x87FF : wide decoder + blockA/B stream
#   ・file 0x8800-0x8A0F : StageExtTable
#   ・file 0x8A10-0x8A6F : Panel Variant combined runtime loader
#   ・file 0x8A70-0x8E7F : PanelVariantStageTable
#   ・file 0x8E80-0xBB95 : PRG1 general reserve
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
#        $0740-$074F はPanel Variant cacheとして予約済み。
#        まとまったcustom RAMは$0750-$075Fを第一候補にする。
#        $073A-$073F / $0760-$0777 / $077D-$077F は補助候補だが、
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
#   2. まとまったRAMが必要 → $0750-$075F を第一候補として予約。
#      小フラグだけなら $077D-$077F も候補。
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
#   $0740-$074F PANEL_VARIANT_CACHE    Panel stage-variant runtime cache, reserved in use
#   $0750-$075F OLD_RUNTIME_BLOCK_LIST remaining 16-byte freed candidate, probe before use
#   $0760-$0777 ENTITY_TAIL_CANDIDATE  secondary 24-byte candidate, probe before use
#   $0778       ROOMFLAGS              room flag table cache, reserved in use
#   $0779       DARK_PHASE             dark-room phase counter, reserved in use
#   $077A-$077B BLOCK_OVERRIDE_WORK    temporary NMI work bytes, reserved in use
#   $077C       RUNTIME_DOOR_CELL      current room door cell, reserved in use
#   $077D-$077F FREE_CANDIDATE         secondary 3-byte tail candidate
#
# Current ROM cave ledger lives in docs/rom_map_jp_mapper66_current.html.
# Do not add or move a hard-coded ROM/RAM address without updating the HTML
# ledgers in the same change. Overlapping reservations are release blockers.

BIT_HIDDEN_DOOR = 0x01  # bit0: 隠し扉 (扉マスに$40、開始前画面の扉描画抑止)
BIT_IN_BLOCK_DOOR = 0x02  # bit1: ブロック内扉 (扉マスに$80、開始前画面の扉描画抑止)
BIT_NO_BFIRE    = 0x04  # bit2: B火球(魔法)禁止 (SE $08==$13 のみ却下)
BIT_NO_ASTONE   = 0x80  # bit7: A換石(石作成)禁止 (SE $08==$11 のみ却下)
                        #   ※A禁止は階段が作れず進行不能になり得る独立option
BIT_DARK        = 0x08  # bit3: 暗闇面 (この面プレイ中 BGを明滅で消す。
                        #   明/暗フレーム数は全体共通テンポ。必ず明から)

ROOM_COUNT = 64  # RoomFlagTable サイズ ($0428 = $00..$34 / 53面+特殊)

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

# ---- cave / table レイアウト (clean JP = 拡張ROM 共通) ----------------
# 空き領域 $BBDE-$C1FF (file 0x3BEE-0x4210, 1570B, 全 EA/00 実機裏取り)
OFF_LOADER_CAVE = 0x3BF0   # $BBE0  LOADER (46B)
OFF_MAGIC_CAVE  = 0x3C30   # $BC20  MAGICGATE (34B)
OFF_DOOR_CAVE   = 0x3C60   # $BC50  DOORPREDRAW (11B)
OFF_DOORTAB     = 0x4190   # $C180  DoorCellTable (64B; mapper66ではStageExtへ移設)
OFF_TABLE       = 0x41D0   # $C1C0  RoomFlagTable (64B; mapper66ではStageExtへ移設)
OFF_DARK_CAVE   = 0x3C90   # $BC80  DARK (56B、明滅BG制御)
OFF_TEMPO       = 0x3CE0   # $BCD0  全体共通テンポ 2B [LIGHT, PERIOD]
OFF_BW_CAVE     = 0x4100   # $C0F0  breakable-white one-shot NMI routine
OFF_CAVE_FREE0  = 0x3BEE   # $BBDE  (cave 空き判定の起点)
OFF_CAVE_FREE1  = 0x4210   # $C200  (cave 空き判定の終点)
OFF_TITLE_IDLE_DEMO_CLEAR = 0x3C1E  # $BC0E  wide-title idle demo cleanup (9B)
TITLE_IDLE_DEMO_CLEAR_SIZE = 9

# 暗闇 NMI フック: $8055 LDA $0301 (PPUMASK shadow読込、毎フレNMI)
OFF_HOOK_8055   = 0x0065   # $8055
OFF_SIG_804B    = 0x005B   # 署名: 改造対象を含まない $804B〜 (10B)
SIG_804B        = bytes.fromhex("bd ef 80 9d ef 80 a9 80 85 7d")
ORIG_8055       = bytes.fromhex("ad 01 03")  # LDA $0301
HOOK_8055_NEW   = bytes.fromhex("20 80 bc")  # JSR $BC80 (DARK cave)

# DARK cave @ $BC80 (56B): ROOMFLAGS bit3 & Dana実プレイ($057F>=$C0)
#   の時だけ フェーズカウンタ $0779 を進め、$BCD0(LIGHT)未満=明
#   (原 $0301)/ 以上=暗(bit3クリアでBG-off) / $BCD1(PERIOD)で0復帰。
#   非該当時は $0779=0 リセット → 暗闇面は必ず「明」から開始。
#   LOADER は非改変(独立)。$8058 STA $2001 が返り A を書く。
#   ★R-fix(2026-05-18): ROOMFLAGS/フェーズカウンタを $0460/$0461 から
#     $0778/$0779 へ移設。$0460/$0461 はサウンドch0状態RAM
#     ($0456+$10*N の ch0 +$0A/+$0B)で、暗闇面で毎NMI $0461 を踏み
#     妖精取得音($0F)が無限ループした(実機 PC=$F2F7 サウンドが$0461
#     書込を確認)。$0778/$0779 = entity 21slot 終端$0722 の後ろ +
#     ramfree3_probe 285秒 沈黙確認の二重安全域。
DARK_CAVE = bytes.fromhex(
    "20f0c0"
    "ad78072908f025ae7f05e0c0901eee7907ad7907cdd1bc9005a9008d7907"
    "ad7907cdd0bc900bad010329f760a9008d7907ad010360"
)
assert len(DARK_CAVE) == 56

# Runtime block override NMI routine @ $C0F0.
# Runs once after Dana is active. It intentionally clobbers A/X; DARK_CAVE
# already clobbers them before returning to the original NMI path. It scans the
# visible $0304 room grid after the nametable has already been drawn, then
# converts direct m66 special cell IDs:
#   $F9 -> $90  breakable white
#   $FA -> $10  passable white
#   $40 -> $F8  invisible solid
#   $50 -> $90  invisible breakable
#   $A3 -> $10  passable brown
#   $A4 -> $F8  solid brown
BW_CAVE = bytes.fromhex(
    "ad7f05c9c0902aad7a07d025a2c0bd1303c940f01dc9a4f019"
    "c950f019c9f9f015c9faf015c9a3f011cad0e2a9018d7a0760"
    "a9f8d006a990d002a9109d1303d0e8"
)
assert len(BW_CAVE) == 65
BW_CAVE_RESERVED_SIZE = 67
BW_CAVE_BLOB = BW_CAVE + bytes([0xEA] * (BW_CAVE_RESERVED_SIZE - len(BW_CAVE)))
assert len(BW_CAVE_BLOB) == BW_CAVE_RESERVED_SIZE
# 全体共通テンポ既定: 明45フレ / 暗100フレ → PERIOD=145
TEMPO_DEFAULT = bytes([45, 145])  # [LIGHT, PERIOD(=LIGHT+DARK)]

# ---- フック差替バイト -------------------------------------------------
HOOK_9071_NEW = bytes.fromhex("20 e0 bb")  # JSR $BBE0 (LOADER)
HOOK_8326_NEW = bytes.fromhex("20 20 bc")  # JSR $BC20 (MAGICGATE)
HOOK_91CC_NEW = bytes.fromhex("20 50 bc")  # JSR $BC50 (DOORPREDRAW)

# LOADER cave @ $BBE0 (46B):
#   JSR $974B            ; 原処理(level load)再現
#   LDX $0428 / LDA $C1C0,X / STA $0778   ; ROOMFLAGS ロード
#   AND #$10             ; bit4 = ステージ開始時ファイヤー所持リセット?
#   BEQ +11              ;   立ってなければ何もしない
#   LDA #$00 / STA $042E / STA $042F
#   JSR $A1CC            ; HUD fire stock redraw. $042B(max/cursor)は触らない
#   LDA $0778 / AND #$03 ; bit0=隠し扉 / bit1=ブロック内扉?
#   BEQ +14 (->RTS)      ;   立ってなければ何もしない
#   ASL x6               ; bit0->$40 / bit1->$80
#   PHA / LDX $077C / PLA
#   ORA $0304,X / STA $0304,X             ; 扉マスに状態bitを立てる
#   RTS
#   ★R-fix: ROOMFLAGS $0460→$0778 (サウンドRAM衝突回避、上の DARK 注記)
LOADER_CAVE = bytes.fromhex(
    "20 4b 97 ad 78 07 "
    "29 10 f0 0b a9 00 8d 2e 04 8d 2f 04 20 cc a1 "
    "ad 78 07 29 03 f0 0e 0a 0a 0a 0a 0a 0a 48 "
    "ae 7c 07 68 1d 04 03 9d 04 03 60"
)

# MAGICGATE cave @ $BC20 (34B): bit2=B火球禁止 / bit7=A換石禁止 (独立)
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

# DOORPREDRAW cave @ $BC40 (11B): 隠し/ブロック内扉は開始前画面の扉描画を抑止
#   LDA $0778 / AND #$03 / BNE skip       ; bit0/1 立ってたら扉を描かない
#   JSR $9D53                              ; 通常=扉先行描画
# skip: RTS                                ; ($91CF へ復帰)
#   ★R-fix: ROOMFLAGS $0460→$0778 (サウンドRAM衝突回避)
DOOR_CAVE = bytes.fromhex("ad 78 07 29 03 d0 03 20 53 9d 60")


BIT_FIRE_RESET = 0x10  # stage load clears carried fire scroll stock.


def normalize_flags(flags: int) -> int:
    """Runtime room flags normalization.

    Hidden-door and in-block-door both modify the same door cell. If both are
    present (for example from hand-edited project data), prefer in-block-door so
    the runtime never ORs both bits into the door cell.
    """
    flags = int(flags) & 0xFF
    if flags & BIT_IN_BLOCK_DOOR:
        flags &= ~BIT_HIDDEN_DOOR
    return flags


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
    ):
        cur = bytes(rom_data[off:off + 3])
        if cur not in (orig, new):
            raise RoomFlagError(
                f"{name} が想定外 ({cur.hex()})。別改造と競合の可能性が"
                "あるため中止します。"
            )
    # cave 空き: 原作(EA/00) / 既注入の各 cave・table は許容。
    # ★gap_fix(原作バグ回避 横穴侵入安定化) の cave も同 bank0 予約帯
    #   ($BBDE-$C1FF)内の room_flags 非使用中間帯 $C000(file0x4010,136B)
    #   に置くため、両機能を同時適用できるよう許容スパンに含める。
    from . import gap_fix as _gf
    from . import gargoyle_variant as _gv
    from . import panel_monster_variant as _pmv
    from . import panel_monster_stage_variant as _pmsv
    from . import saramandor_variant as _sv
    from . import spark_ball_variant as _sbv
    from . import key_enemy_runtime as _ker
    expanded = len(rom_data) == 0x18010
    table_spans = ((OFF_DOORTAB, ROOM_COUNT * 2),) if expanded else (
        (OFF_DOORTAB, ROOM_COUNT),
        (OFF_TABLE, ROOM_COUNT),
    )
    _spans = (
        (OFF_LOADER_CAVE, len(LOADER_CAVE)),
        (OFF_MAGIC_CAVE, len(MAGIC_CAVE)),
        (OFF_DOOR_CAVE, len(DOOR_CAVE)),
        (OFF_TITLE_IDLE_DEMO_CLEAR, TITLE_IDLE_DEMO_CLEAR_SIZE),
        *table_spans,
        (_gf.OFF_CAVE, len(_gf.CAVE)),       # gap_fix 共存
        (OFF_DARK_CAVE, len(DARK_CAVE)),     # 暗闇 cave
        (OFF_TEMPO, 2),                      # 暗闇テンポ
        (OFF_BW_CAVE, BW_CAVE_RESERVED_SIZE),
        *_sv.RESERVED_SPANS,                 # Saramandor #2 bullet variant
        *_gv.RESERVED_SPANS,                 # Gargoyle #2 two-Bullet variant
        *_pmv.RESERVED_SPANS,                # Panel Monster borrowed-ID variants
        *_pmsv.RESERVED_SPANS,               # Panel Variant A/B/C split runtime
        *_sbv.RESERVED_SPANS,                # Spark Ball Dragon-ID variants
        *_ker.RESERVED_SPANS,                # Key-carrying initial enemy runtime
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
            if any(flags):
                return flags
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
    return [rom_data[OFF_TABLE + i] & 0xFF for i in range(count)]


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
    return any((f & 0xFF) for f in room_flags)


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
    bw_needed = _breakable_white_needed(breakable_white_cells)

    if not is_needed(room_flags) and not bw_needed:
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
        return changed

    # cave コード注入
    for off, blob, name in (
        (OFF_LOADER_CAVE, LOADER_CAVE, "LOADER ($BBE0)"),
        (OFF_MAGIC_CAVE, MAGIC_CAVE, "MAGICGATE ($BC20)"),
        (OFF_DOOR_CAVE, DOOR_CAVE, "DOORPREDRAW ($BC40)"),
    ):
        if bytes(rom_data[off:off + len(blob)]) != blob:
            rom_data[off:off + len(blob)] = blob
            changed.append(f"{name} cave 注入")
    expanded = len(rom_data) == 0x18010
    # DoorCellTable / RoomFlagTable 書込。mapper66では同じ情報をPRG1
    # StageExtTableへ移し、PRG0 $C180-$C1FF はコード用に空ける。
    if not expanded and bytes(rom_data[OFF_DOORTAB:OFF_DOORTAB + ROOM_COUNT]) != bytes(dtab):
        rom_data[OFF_DOORTAB:OFF_DOORTAB + ROOM_COUNT] = bytes(dtab)
        changed.append("DoorCellTable 書込")
    if not expanded and bytes(rom_data[OFF_TABLE:OFF_TABLE + ROOM_COUNT]) != bytes(tbl):
        rom_data[OFF_TABLE:OFF_TABLE + ROOM_COUNT] = bytes(tbl)
        n = sum(1 for b in tbl if b)
        changed.append(f"RoomFlagTable 書込 ({n}部屋にフラグ)")
    # フック有効化
    for off, _orig, new, name in _HOOKS:
        if bytes(rom_data[off:off + 3]) != new:
            rom_data[off:off + 3] = new
            changed.append(f"{name} フック有効化")

    # 暗闇: dark ビットが1部屋でもあれば DARK cave + テンポ + $8055 フック。
    # 無ければ $8055 は原作のまま(暗闇未使用時は NMI 非フック=完全無影響)。
    if _dark_needed(room_flags) or bw_needed:
        if bytes(rom_data[OFF_BW_CAVE:OFF_BW_CAVE + BW_CAVE_RESERVED_SIZE]) != BW_CAVE_BLOB:
            rom_data[OFF_BW_CAVE:OFF_BW_CAVE + BW_CAVE_RESERVED_SIZE] = BW_CAVE_BLOB
            changed.append("BreakableWhite cave 注入 ($C0F0)")
        if bytes(rom_data[OFF_DARK_CAVE:OFF_DARK_CAVE + len(DARK_CAVE)]) != DARK_CAVE:
            rom_data[OFF_DARK_CAVE:OFF_DARK_CAVE + len(DARK_CAVE)] = DARK_CAVE
            changed.append("DARK cave 注入 ($BC80)")
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

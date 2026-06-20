# PRG0 padding / cave audit for JP mapper66 ROM

Last updated: 2026-06-18

This document is the PRG0-specific safety ledger for places that look like
padding in the original Japanese ROM. It exists because `00`/`EA` bytes are not
enough evidence that an address is free.

The normal editing target is the app-generated Japanese mapper66 wide-title
expanded ROM. CPU addresses below are PRG0 fixed-bank addresses. File offsets
include the iNES header, matching implementation constants:

```text
NES file offset = 0x10 + (CPU - 0x8000)
```

## Hard Rules

- Do not place new PRG0 code/data only because the original byte is `00`, `EA`,
  `FF`, `20`, `80`, `FE`, or another repeated value.
- A PRG0 address is usable only when it is listed here or in
  `docs/rom_map_jp_mapper66_current.html` as reserved/candidate and the matching
  implementation `OFF_*` / `RESERVED_SPANS` is updated in the same change.
- If the row says `NG` or `unknown`, do not use it without a new ASM/runtime
  proof and a ledger update in the same commit.
- Prefer PRG1 reserve for new mapper66-only tables/helpers. PRG0 is effectively
  full and should be used only for hooks, tiny fixed-bank helpers, or code that
  must run while PRG1 is not mapped.
- When a candidate lies between two existing helpers, reserve only the exact
  bytes used. Do not absorb adjacent bytes that are not confirmed padding.

## Byte Meanings

| Byte | Typical meaning | PRG0 policy |
|---|---|---|
| `00` | `BRK` opcode if executed; very often zero-valued data, pointer table filler, speed/state index, bit table padding, or script terminator. | Treat as data unless ASM/runtime proves it is unused. The `$DB61-$DB74` bug came from treating meaningful zero data as free space. |
| `EA` | Official 6502 `NOP`. Long runs are often intentional code caves or disabled code. | Better candidate than `00`, but still not automatically free. It may already be reserved by another module or kept for alignment/compatibility. |
| `FF` | Illegal opcode on NMOS 6502; also common as data sentinel/fill. | Not a safe code cave marker. Treat as data unless proven otherwise. |
| `EF` | Illegal opcode value, not a standard padding byte. | Do not treat as padding. If seen in a table or stream, assume data. |

## Other Fill Patterns To Check

These patterns are rarer in this ROM than `00`/`EA`, but they are important
because they can look like padding while still being meaningful data or code.

| Pattern | Why it can appear | PRG0 policy |
|---|---|---|
| Repeated `20` or game-font blank codes | Text/PPU/script data can use a space or blank tile value as visible padding. On 6502, `20` is also `JSR abs` if executed. | Never treat as free space without proving the surrounding bytes are not text, PPU script, or executable code. |
| Repeated terminators such as `FF`, `FE`, `80`, or game-specific end markers | Enemy/item/music/script streams may use terminator values after the real payload. The repeated bytes can be part of the parser contract. | Treat as table/stream data until the owning parser and pointer boundaries are confirmed. |
| Instruction-skip padding such as `2C` (`BIT abs`) | Some 6502 code uses multi-byte instructions to intentionally consume following bytes or align timing. | Disassemble from the real entry point before claiming the bytes. A byte that looks like data may be an operand of a previous instruction. |
| Any repeated nonzero value | Could be a lookup table, speed table, pointer high byte, tile ID, metatile ID, or sentinel. | Mark `unknown` unless ASM context and runtime reads prove it is unused. |

## Known PRG0 Padding Runs In The Original JP ROM

Mechanical scan of original JP PRG0 for runs of at least 4 identical bytes:

- `00`: 119 runs, total 1129 bytes.
- `EA`: 8 runs, total 1751 bytes.
- `FF`: 1 run, total 8 bytes.
- `20`: 1 run, total 4 bytes.
- `80`: 1 run, total 8 bytes.
- `EF`: 1 run, total 10 bytes.
- `2C` / `FE`: no runs of 4+ bytes found.

This count is diagnostic only. Most `00` runs are not free, and nonzero runs
are even more likely to be table/script data unless proven otherwise. The
tables below are the authority.

## Safe / Reserved PRG0 Areas Already Used By The App

These ranges are owned by current implementation. They are not free, but they
are legitimate examples of confirmed PRG0 use. Any move/resize must update this
document, `docs/rom_map_jp_mapper66_current.html`, and implementation constants.

| File offset | CPU | Size | Owner | Original bytes | Status / notes |
|---|---:|---:|---|---|---|
| `0x0BF2-0x0C0D` | `$8BE2-$8BFD` | 28B | `initial_magic.py`, `initial_lives.py` | `EA` run | Confirmed NOP band. Start magic and initial lives routines. |
| `0x17F5-0x1803` | `$97E5-$97F3` | 15B | `m66.py` | original code | Existing code patch for mapper66 key cell values. Not free. |
| `0x2569-0x257D` | `$A559-$A56D` | 21B | `spark_ball_variant.py` | original code/data | Spark Ball property selector compression. Not free. |
| `0x33D0-0x33DC` | `$B3C0-$B3CC` | 13B | `stage_announcement.py` | `EA` run | KEY ENEMY gate. |
| `0x3BEE-0x420F` | `$BBDE-$C1FF` | 1570B | multiple modules | `00`/`EA` cave | Main bank0 cave. Almost full; see dedicated table below. |
| `0x4FEE-0x5004` | `$CFDE-$CFF4` | 23B | `spark_ball_variant.py` | `EA` run | Spark Ball animation hook. |
| `0x5AC9-0x5ADC` | `$DAB9-$DACC` | 20B | `panel_monster_stage_variant.py` | `00` run | Panel Variant type classifier tail. Uses meaningful area near enemy state-speed data; do not extend blindly. |
| `0x5BC5-0x5BEE` | `$DBB5-$DBDE` | 42B | original / patchable table | speed table | Original enemy speed table. Only specific known bytes may be patched by speed features. |
| `0x5BEF-0x5C0A` | `$DBDF-$DBFA` | 28B | `panel_monster_variant.py` | `EA` run | Panel/Spark property selector. |
| `0x60CC-0x60D0` | `$E0BC-$E0C0` | 5B | `stage_announcement.py` | `00` run | Announcement mask table. |
| `0x60FC-0x6108` | `$E0EC-$E0F8` | 13B | `stage_announcement.py` | `00` run | DARK ROOM script. |
| `0x612C-0x6138` | `$E11C-$E128` | 13B | `stage_announcement.py` | `00` run | FIRE LOSS script. |
| `0x618C-0x619A` | `$E17C-$E18A` | 15B | `stage_announcement.py` | `00` run | HIDDEN DOOR script. |
| `0x61BC-0x61C8` | `$E1AC-$E1B8` | 13B | `stage_announcement.py` | `00` run | KEY ENEMY script. |
| `0x61EC-0x61F7` | `$E1DC-$E1E7` | 12B | `stage_announcement.py` | `00` run | Script pointer table. |
| `0x62ED-0x62F4` | `$E2DD-$E2E4` | 8B | `m66.py` | `00` run | Cracked in-block initial draw bit table. |
| `0x63FC-0x6403` | `$E3EC-$E3F3` | 8B | `m66.py` | `00` run | Cracked in-block initial draw continuation. |
| `0x639C-0x63B4` | `$E38C-$E3A4` | 25B | `stage_announcement.py` | `00` run | Draw helper. |
| `0x63CC-0x63E3` | `$E3BC-$E3D3` | 24B | `stage_announcement.py` | `00` run | Announcement main routine. |
| `0x6465-0x6473` | `$E455-$E463` | 15B | `key_enemy_runtime.py` | `00` run | Key/Fairy selected status helper. |
| `0x657C-0x658A` | `$E56C-$E57A` | 15B | `stage_announcement.py` | `00` run | FIRE SEALED script. |
| `0x66FC-0x670B` | `$E6EC-$E6FB` | 16B | `stage_announcement.py` | `00` run | SPELL SEALED script. |
| `0x675C-0x6773` | `$E74C-$E763` | 24B | `room_flags.py` | `00` run | Visible item in-block mask helper. |
| `0x6774-0x6789` | `$E764-$E779` | 22B | `m66.py` | mixed / adjacent to `00` | Cracked in-block initial draw helper. Not extendable without checking neighboring bytes. |
| `0x678C-0x6797` | `$E77C-$E787` | 12B | `room_flags.py` | `00` run | White in-block runtime extension. Starts at `$E77C` deliberately; `$E77A-$E77B` are not included. |
| `0x6798-0x67A1` | `$E788-$E791` | 10B | `m66.py` | `00` run | Cracked in-block initial draw continuation. |
| `0x67B4-0x67D0` | `$E7A4-$E7C0` | 29B | `panel_monster_stage_variant.py` | mixed / rewritten | Panel Variant parent speed guard. Uses the shared Panel type classifier after `$8AC0`. |
| `0x67D1-0x681B` | `$E7C1-$E80B` | 75B | emergency reserve | mixed / untouched by saver | Recovered from the old parent speed guard span. Do not use for normal feature work; re-probe/review before emergency use. |
| `0x681C-0x6832` | `$E80C-$E822` | 23B | `spark_ball_variant.py` | `00` run | Transparent Spark Ball Golem-ID AI wrapper. |
| `0x6833-0x6882` | `$E823-$E872` | 80B | `panel_monster_stage_variant.py` | `00` run | Panel Monster v2 Bullet speed tables plus shared fast loop. |
| `0x68AC-0x68C0` | `$E89C-$E8B0` | 21B | `panel_monster_stage_variant.py` | `00` run | Dynamic speed marker helper. |
| `0x693C-0x6959` | `$E92C-$E949` | 30B | `panel_monster_stage_variant.py` | `00` / mixed | Panel Variant A/B/C group offset helper. Former emergency candidate band; now used. |
| `0x696C-0x697E` | `$E95C-$E96E` | 19B | `panel_monster_stage_variant.py` | `00` run | Panel Variant final AI dispatch helper. Former emergency candidate band; now used. |
| `0x69D4-0x69DF` | `$E9C4-$E9CF` | 12B | `panel_monster_stage_variant.py` | `00` run | Panel Variant final AI dispatch panel tail. Static scan found no original absolute/indexed operand or pointer reference before reservation. |
| `0x6FD4-0x7004` | `$EFC4-$EFF4` | 49B | `spark_ball_variant.py` | `EA` run | Spark Ball pause hook. |
| `0x7005-0x700F` | `$EFF5-$EFFF` | 11B | `solomon_seal_block.py` | `EA` run | Solomon Seal block helper. |

## Known NG: Looks Like Padding But Is Data

These ranges must not be used as caves. They contain meaningful data or are
inside data structures, even when the bytes are `00`.

| File offset | CPU | Size | Original bytes | Why NG |
|---|---:|---:|---|---|
| `0x5A25-0x5B9C` | `$DA15-$DB8C` | many zero runs | `00` | Enemy state-speed index data reached through the `$D9D3` pointer table and read by `$8AC0`. Many zero bytes mean speed-index 0, not free space. |
| `0x5B71-0x5B84` | `$DB61-$DB74` | 20B | `00` | Specific bug source: overwriting this with code made Gargoyle enter a smoke/death-like loop. It is state-speed data, not a cave. |
| `0x5BA9-0x5BEE` | `$DB99-$DBDE` | 70B | speed bytes | Enemy speed table. Shared by Golem/Demonhead and others. Patch only documented entries. |
| `0x5C10-0x5C21` | `$DC00-$DC11` | pointer/table area | mixed / `00` | Mirror rate tables; mapper66 conversion patches pointers here. |
| `0x5C30-0x5C49` | `$DC20-$DC39` | pointer/table area | mixed / `00` | Mirror enemy pointer table; mapper66 conversion patches pointers here. |
| `0x5C82-0x5CB2` | `$DC72-$DCA2` | table area | `FF`/`00` runs | Original table/sentinel data. Do not use `FF` or `00` runs here as cave. |
| `0x5CFC-0x5D64` | `$DCEC-$DD54` | 105B | pointer table | Enemy data pointer table. Mapper66 conversion writes fixed staging pointers. |
| `0x6A2C-0x6A94` | `$EA1C-$EA84` | 105B | pointer table | Item data pointer table. Mapper66 conversion writes fixed staging pointers. |
| Nearby small `00` runs around item/enemy tables | varies | small runs | `00` | Adjacent to item/enemy pointer/data structures; treat as unknown data unless separately proven. |

## Bank0 Cave `$BBDE-$C1FF`

This is the main PRG0 cave used by current runtime features. It is almost full.
Do not allocate here by eye; use `room_flags._verify()` and module
`RESERVED_SPANS`.

Current state from `docs/rom_map_jp_mapper66_current.html`:

- Total cave: 1570B.
- Production-reserved/used: 1535B.
- Unreserved bank0 cave fragments: 35B total.
- PRG0 later-bank emergency reserve newly recovered from Panel Variant parent speed guard: 75B at `0x67D1-0x681B` / `$E7C1-$E80B`.
- Maximum contiguous fragment: 5B.

Remaining fragments after current production reservations:

| File offset | CPU | Size | Status |
|---|---:|---:|---|
| `0x3BEE-0x3BEF` | `$BBDE-$BBDF` | 2B | candidate fragment only |
| `0x3C2E-0x3C2F` | `$BC1E-$BC1F` | 2B | candidate fragment only |
| `0x3C5E-0x3C5F` | `$BC4E-$BC4F` | 2B | candidate fragment only |
| `0x3C8F` | `$BC7F` | 1B | candidate fragment only |
| `0x3D32-0x3D35` | `$BD22-$BD25` | 4B | candidate fragment only |
| `0x3D46-0x3D4A` | `$BD36-$BD3A` | 5B | candidate fragment only |
| `0x3D97` | `$BD87` | 1B | candidate fragment only |
| `0x3E4D-0x3E4F` | `$BE3D-$BE3F` | 3B | candidate fragment only |
| `0x3E8E-0x3E8F` | `$BE7E-$BE7F` | 2B | candidate fragment only |
| `0x3EB7-0x3EBB` | `$BEA7-$BEAB` | 5B | recovered from Panel Variant group helper compression |
| `0x3EF9` | `$BEE9` | 1B | candidate fragment only |
| `0x3FF8-0x3FFC` | `$BFE8-$BFEC` | 5B | candidate fragment only |
| `0x400F` | `$BFFF` | 1B | candidate fragment only |
| `0x418F` | `$C17F` | 1B | candidate fragment only |

These fragments are too small for normal helpers. Use them only for deliberate
byte-level patches after updating the cave ledger.

## Emergency Reserve Policy

PRG0 is now an emergency reserve, not normal feature space.

- Normal feature work must prefer PRG1 reserve or an existing verified helper.
- Do not spend a PRG0 run only to make an implementation easier.
- A PRG0 reserve may be used only for a release-blocking runtime bug that cannot
  be fixed in PRG1 or by shrinking/reusing an existing helper.
- Before using a reserve candidate, prove both sides:
  1. Static proof: check the surrounding ASM and all pointer/table references.
  2. Runtime proof: run a Mesen read/exec probe on the candidate in stages that
     exercise the related system.
- If a candidate is consumed, move it to the reserved table in this document,
  update `docs/rom_map_jp_mapper66_current.html`, and update the implementation
  constants in the same commit.

Current emergency candidates are intentionally not classified as free. They are
only places worth investigating first if PRG0 is absolutely unavoidable.

### Former Primary Emergency Candidates

Mesen focus probe result on 2026-06-17:
`mesen_probes/lua/prg0_emergency_candidates_focus_probe_v099.lua`

- Probe ran through at least frame 23100.
- No `READ` or `EXEC` events were logged for either primary candidate.
- This proved only "not touched in this test coverage", not universal safety.
- These ranges are no longer candidates in the current production layout.

| Priority | File offset | CPU | Size | Original bytes | Latest runtime observation | Status |
|---:|---|---:|---:|---|---|---|
| - | `0x696C-0x697E` | `$E95C-$E96E` | 19B | `00` run | No READ/EXEC through frame 23100 in old focus probe. | Used by `panel_monster_stage_variant.py`; not free. |
| - | `0x693C-0x6959` | `$E92C-$E949` | 30B | `00` / mixed | No READ/EXEC through frame 23100 in old focus probe for `$E92C-$E93F`. | Used by `panel_monster_stage_variant.py`; not free. |

### Current Emergency Candidates

There is no current primary PRG0 emergency reserve candidate large enough to
trust without new work. Run `tools/prg0_free_space_audit.py` and then perform
ASM boundary review before promoting any row to this section.

### Tiny / Last-Resort Candidate

| File offset | CPU | Size | Original bytes | Status |
|---|---:|---:|---|---|
| `0x1ECA-0x1ECF` | `$9EBA-$9EBF` | 6B | `EA` run | Not a main reserve. Keep only as a last-resort tiny patch fragment; NOP does not mean unconditional safety. |

The `0x4FC6-0x4FC9` / `$CFB6-$CFB9` `20` run is not listed as a reserve
candidate: the ASM context decodes it as instructions/operands near `$2003`, so
it must be treated as code/data context until proven otherwise.

## PRG0 Areas To Prefer Avoiding

The following are not all proven dangerous byte-for-byte, but they are poor
targets for new work because they are table-dense, pointer-dense, or already
under active patch pressure.

| CPU / file | Reason |
|---|---|
| `$D9D3-$DBDE` / `0x59E3-0x5BEE` | Enemy init pointer/state-speed/speed data. Zeroes often mean valid speed index 0. |
| `$DC00-$DD54` / `0x5C10-0x5D64` | Mirror/enemy pointer tables and mapper66 pointer patches. |
| `$EA1C-$EA84` / `0x6A2C-0x6A94` | Item pointer tables and mapper66 pointer patches. |
| `$E000-$EFFF` small `00` runs not listed above | Script/table-heavy region. Many runs are PPU scripts, pointer tables, or already used by announcement/runtime helpers. |
| Any `FF` run | Treat as data/sentinel until proven otherwise. |

## Allocation Checklist

Before using a new PRG0 span:

1. Check this document and `docs/rom_map_jp_mapper66_current.html`.
2. Check the implementation owner constants:
   `OFF_*`, `CPU_*`, `RESERVED_SPANS`, and `room_flags._verify()` spans.
3. Check `解析資料/ROM完全解析/solomon_commented.asm` around the CPU address.
   If the bytes are reached by a pointer table or indexed table, they are not
   free even if they are all `00`.
4. If still not proven, write a Mesen probe or static read/write trace before
   reserving it.
5. In the same commit, update this document, the HTML ROM map, and the owning
   code constants.

## Current Recommendation

For any new feature that needs more than 5 bytes, do not search PRG0 first.
Use PRG1 reserve or redesign the patch to reuse an existing verified helper.
PRG0 should now be treated as fixed-bank emergency space, not general storage.

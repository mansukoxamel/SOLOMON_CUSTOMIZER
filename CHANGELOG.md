# SOLOMON_CUSTOMIZER CHANGELOG

## v0.7.100 (2026-05-26) Group enemy settings visually
- Reordered the Enemy settings dialog by monster family so related controls are
  closer together.
- Added monster sprites to Enemy settings groups when a ROM renderer is
  available.

## v0.7.99 (2026-05-26) Accept Gargoyle snappy wait in variant patch
- Fixed strengthened Gargoyle patch validation to accept the app's own snappy
  Gargoyle `$AF2B` wait value `$01`.
- Stopped the strengthened Gargoyle patch from restoring `$AF2B` to `$68`
  unless it is removing the old rapid-fire experiment hook.

## v0.7.98 (2026-05-26) Remove Gargoyle speed tuning UI
- Removed the strengthened Gargoyle second-shot speed control because the
  runtime value is not a reliable user-facing speed setting.
- Kept the strengthened Gargoyle second-shot position control and apply the
  internal second-shot velocity correction at its standard value.

## v0.7.97 (2026-05-26) Fix Gargoyle two-shot gate branch
- Fixed the strengthened Gargoyle `$7A/$7B/$7E/$7F` gate so matching IDs jump
  to the two-shot routine instead of into the stock materialization tail.

## v0.7.96 (2026-05-26) Add strengthened Gargoyle tuning
- Added enemy UI controls for strengthened Gargoyle second-shot offset and
  second-shot speed.
- Preserved custom strengthened Gargoyle tuning when the variant patch is
  reapplied during ROM save.

## v0.7.95 (2026-05-26) Add Gargoyle two-shot speed 2
- Added strengthened Gargoyle two-shot speed-2 IDs `$7E/$7F`, including picker
  speed switching, enemy labels, save detection, and the runtime gate.

## v0.7.94 (2026-05-26) Detect panel hack spark hybrid state
- Updated the Panel Monster behavior-control detector to accept the same
  stock-panel/current-Spark hybrid state handled by the variant patch, so the
  Enemy dialog no longer disables Panel Monster controls for that ROM state.

## v0.7.93 (2026-05-26) Accept orig-panel spark hybrid state
- Fixed Panel Monster variant verification to accept ROMs where the stock
  Panel fire code head remains at `$A556` while the current Spark property hook
  body starts at `$A559`, allowing the save/test pipeline to restore the Panel
  dispatch before Spark is reapplied.

## v0.7.92 (2026-05-26) Accept panel and spark hook overlap
- Fixed Panel Monster variant verification to accept the current layout where
  the Panel fire dispatch jump at `$A556` coexists with the Spark Ball property
  hook starting at `$A559`.

## v0.7.91 (2026-05-26) Fix hidden behavior dialog widgets
- Kept hidden behavior-dialog groups alive so opening the Enemy-only view no
  longer deletes widgets that shared apply/export code may read.

## v0.7.90 (2026-05-26) Add strengthened Spark Ball tuning
- Added enemy UI controls for strengthened Spark Ball pause digits and
  transparent Spark Ball blink mask tuning.
- Preserved custom strengthened Spark Ball tuning when the variant patch is
  reapplied during ROM save.

## v0.7.89 (2026-05-26) Hide salamander behavior group
- Removed the Salamander behavior group from the visible enemy behavior UI.

## v0.7.88 (2026-05-26) Hide salamander Y tolerance
- Removed the Salamander Y tolerance control from the visible enemy behavior UI.

## v0.7.87 (2026-05-26) Split enemy behavior entry
- Added a top-level Enemy button beside game behavior editing, and separated
  enemy AI settings from the general game behavior dialog.

## v0.7.86 (2026-05-26) Flatten behavior dialog layout
- Removed the game behavior dialog tabs so enemy and non-enemy settings appear
  together, and moved the special process viewer into the dialog.

## v0.7.85 (2026-05-26) Move related edit buttons
- Moved enemy drop, demo input, and clear message editing into the game behavior
  dialog, and removed those buttons from the left edit-tools panel.

## v0.7.84 (2026-05-26) Apply font settings immediately
- Fixed settings dialog font changes so edited spin-box values are committed and
  the font is reapplied to existing windows immediately after OK/Apply.

## v0.7.83 (2026-05-26) Add stage selector pane toggle
- Added a display option to show or hide the right-side stage selector pane,
  preserving space on smaller screens.

## v0.7.82 (2026-05-26) Unify visible stage labels
- Unified visible UI/manual wording from レベル/Level to ステージ/Stage where it
  refers to the playable stage, leaving internal names unchanged.

## v0.7.81 (2026-05-26) Rename global time setting
- Renamed the global time-rate section in the behavior dialog to
  ステージ制限時間.

## v0.7.80 (2026-05-26) Round time limit seconds
- Renamed the level time selector display to 制限時間 and rounded its estimated
  seconds to whole numbers.

## v0.7.79 (2026-05-26) Move mirror lifetime hint
- Moved the mirror enemy lifetime seconds estimate to a second line so the field
  label stays compact.

## v0.7.78 (2026-05-26) Show time-rate seconds
- Replaced the level time decrease hint with estimated seconds calculated from
  the current ROM time-rate table.

## v0.7.77 (2026-05-26) Show mirror lifetime seconds
- Updated the mirror enemy lifetime label to show the approximate seconds in
  real time as the value changes.

## v0.7.76 (2026-05-26) Emphasize test play button
- Made the test play button larger and green so it stands out as the playback
  action in the file panel.

## v0.7.75 (2026-05-26) Rename window title
- Changed the main window title from `MAGATU_SOLOMON_CUSTOMIZER` to
  `SOLOMON_CUSTOMIZER`.
- Changed the Windows AppUserModelID from `Chaos.MAGATU.SOLOMON_CUSTOMIZER`
  to `Chaos.SOLOMON_CUSTOMIZER`.
- Changed the mapper66 ROM metadata magic from `MAGATU_SC_META` to
  `SOLOMON_CUSTOMIZER_META`.
- Changed the session log header to `SOLOMON_CUSTOMIZER セッションログ`.
- Changed the PNG-embedded XML root from `magatu_solomon_customizer` to
  `solomon_customizer`, and renamed the format-version constant accordingly.
- Updated user-facing README/MANUAL/docs names from `MAGATU_SOLOMON_CUSTOMIZER`
  to `SOLOMON_CUSTOMIZER`; the internal `magatu_skc` package name is unchanged.

## v0.7.74 (2026-05-26) Correct freed ROM byte counts
- Corrected `docs/rom_map_jp_mapper66_current.html` after the special-cell
  runtime rewrite: bank0 cave free bytes are now 81B total with a 19B largest
  contiguous gap.
- Clarified that the old PRG1 runtime block override table frees a 1,696B
  candidate reserve, increasing the practical PRG1 reserve total.

## v0.7.73 (2026-05-26) Clarify freed RAM candidates
- Updated `docs/ram_map_current.html` and the `room_flags.py` RAM ledger mirror
  to show `$0740-$075F` as the primary 32-byte freed candidate after the direct
  m66 special-cell migration.
- Removed the stale wording that implied only the `$077D-$077F` 3-byte tail was
  available for future custom RAM.

## v0.7.72 (2026-05-26) Store special blocks as m66 cell IDs
- Changed mapper66 special blocks to be stored directly in stage map cells:
  `0xF9` breakable white, `0xFA` passable white, `0x40` invisible solid,
  and `0x50` invisible breakable.
- Replaced the old 32-byte `$0740-$075F` runtime block override list with a
  `$0304` grid scanner that converts those direct cell IDs after drawing.
- Disabled the old PRG1 runtime block override copy and clears the legacy
  per-room cell table on save.

## v0.7.71 (2026-05-26) Record EA fill candidates
- Added remaining PRG0 original `EA` fill candidates to
  `docs/rom_map_jp_mapper66_current.html`.

## v0.7.70 (2026-05-26) Inventory module ROM writes
- Added a PRG0 module-by-module write ledger to
  `docs/rom_map_jp_mapper66_current.html`.
- Marked original `00`/`EA` fill areas already overwritten by app modules so
  they are not mistaken for free space.
- Moved the Transparent Spark Ball Golem-ID AI wrapper from `$8BE2` to the
  original `00` fill at `$E80C`, leaving `$8BE2-$8BFD` for initial magic/lives.
- Recorded the main remaining PRG0 original `00` fill candidates for small
  future routines.

## v0.7.69 (2026-05-26) Remove personal path references
- Removed local user/path references from tracked source comments and changelog
  entries while preserving the technical meaning.

## v0.7.68 (2026-05-26) Add GitHub README
- Added `README.md` as the GitHub landing document with setup, launch, ROM
  policy, supported outputs, and links to the full manual.
- Added `README.md` to the repository whitelist.

## v0.7.67 (2026-05-26) Remove local file dialog dependency
- Replaced the machine-local `file_dialog` imports with an in-repository
  `QFileDialog` compatibility wrapper.
- Removed the hard-coded startup `sys.path` entry for a machine-local helper
  directory.
- Added `requirements.txt` so a fresh checkout declares the external `PyQt5`
  dependency.

## v0.7.66 (2026-05-25) Fix vertical Panel Monster spread axis
- Fixed Panel Monster 2-way/3-way spread so vertical variants offset bullet X
  while horizontal variants continue to offset bullet Y.
- Confirmed the issue with Mesen logs: `PM3_DOWN` shots were still reaching
  the `$BF69` spread hook and writing `ptr2E+7/Y` at `$BF98`.
- Expanded the Panel Monster bullet hook from 70B to 74B, consuming 4B from
  the small `$BFAF-$BFB8` gap without overlapping the normal fire copy.

## v0.7.65 (2026-05-25) Show bank0 cave free bytes
- Added exact bank0 cave free-space accounting to the ROM map:
  `$BBDE-$C1FF` has 1,570B total, 1,504B reserved, 66B unreserved, and the
  largest contiguous gap is 18B.
- Listed each remaining unreserved fragment so future ROM allocations do not
  rely on the visual bar alone.

## v0.7.64 (2026-05-25) Refresh ROM/RAM ledgers
- Updated the ROM/RAM ledger documents with explicit operation rules: no new
  address use without checking the ledgers and implementation reservation
  spans, and no release with unresolved overlap or undocumented reservations.
- Refreshed stale Spark Ball / Panel Monster ROM-map entries around `$BE62`,
  `$A559`, `$C0C2`, and `$DBDF` based on the current implementation.
- Fixed the RAM ledger mirror in `room_flags.py` so only `$077D-$077F` remains
  a free candidate; `$077A-$077B` is documented as block override work.

## v0.7.63 (2026-05-25) Add encoding safety rules
- Added Japanese-file and encoding safety rules to `AGENTS.md` to prevent
  unnoticed mojibake, comment loss, or accidental full-file rewrites.
- The rules require UTF-8 reads for Japanese files, ASCII-only patch anchors,
  minimal diffs, and post-edit UTF-8 checks before continuing.

## v0.7.62 (2026-05-25) Localize agent rules
- Rewrote `AGENTS.md` in Japanese so project operating rules are easier to
  review and less likely to be misunderstood in this Japanese-led workflow.
- Preserved the existing backup/version/changelog, no-backward-compatibility,
  and JP mapper66 wide-title ROM support policies.

## v0.7.61 (2026-05-25) Record original ROM CRC
- Added `original_rom_crc32` and `original_rom_size` to the ROM-save global
  sidecar so the source ROM used for reconstruction can be identified later.
- These fields are metadata only; import/rebuild logic does not depend on them.

## v0.7.60 (2026-05-25) Compact global byte data
- Changed global sidecar byte-table fields from long decimal arrays to compact
  uppercase hex strings:
  `main_palette_hex`, `demo_input_wait_hex`, `demo_input_joy_hex`,
  `enemy_drop_c278_hex`, `enemy_drop_c293_hex`, and `clear_message_hex`.
- Import now expects the new hex-string fields only, with no compatibility path
  for the short-lived decimal-array format.

## v0.7.59 (2026-05-25) Add missing global byte tables
- Added ROM-backed global tables to the common settings JSON so ROM save sidecars
  preserve more non-level edits:
  `main_palette_bytes`, `demo_input_wait_bytes`, `demo_input_joy_bytes`,
  `enemy_drop_c278_bytes`, `enemy_drop_c293_bytes`, and `clear_message_bytes`.
- Importing common settings now restores those byte tables directly and fails on
  invalid lengths rather than attempting old-format compatibility.
- Rechecked Game Behavior settings export: combo values are stored as numeric
  data or stable ids, not UI labels.

## v0.7.58 (2026-05-25) Store clear-screen preset by id
- Added the project rule that backward compatibility is intentionally ignored
  until the user explicitly declares a compatibility baseline version.
- Changed `clear_screen_preset` in global settings JSON from UI label text to
  the stable internal id such as `fairy_original`.
- Clear-screen preset UI labels can now change without changing the saved JSON
  value.

## v0.7.57 (2026-05-25) Save project data with ROM
- ROM save now also writes the reproducible project sidecars next to the saved
  ROM: `<rom>_global_settings.json` and `<rom>_stage_data/level_01.png` through
  `level_53.png`.
- The stage PNG files reuse the existing embedded XML format, and the JSON file
  reuses the existing common-settings export format with the saved ROM name,
  stage-data folder name, and current title extra text included.
- If sidecar export fails after the ROM file was written, the app warns without
  pretending the ROM file itself failed.

## v0.7.56 (2026-05-25) Stamp empty title text on save
- When saving ROM data, the title extra-text line is now checked. If it is
  empty, the save output receives a `BUILD YYYYMMDD HHMMSS` timestamp so the
  build can be identified from the game's title screen.
- Existing title extra text is preserved unchanged.

## v0.7.55 (2026-05-25) Validate save consistency
- Added save-time level consistency validation for key-carrying enemies: saving
  now stops if a stage selects key enemy #N while the stage has fewer than N
  initial enemies.
- Built ROM/IPS save data on a temporary ROM copy before writing output, so a
  failed validation or later save error does not leave the open ROM data
  partially modified.

## v0.7.54 (2026-05-25) Add fast-start testplay only
- Added an F9 testplay-only title/start-screen shortcut based on the confirmed
  raw-JP 3-byte title skip plus three start-screen wait skips.
- The shortcut is applied only to the temporary testplay ROM and is restored
  from `rom.data` immediately afterward, so normal ROM save and IPS export do
  not receive the fast-start patch.

## v0.7.53 (2026-05-25) Add invisible Spark Ball variants
- Added transparent Spark Ball variants on the borrowed Golem #2 IDs:
  `$72/$73/$76/$77`.
- Routed those IDs through the confirmed Spark Ball movement routines and added
  an OAM post-draw hide hook for the accepted slow blink effect.
- Placed the new runtime code only in confirmed EA padding spans, avoiding the
  `0x500C` data area that corrupts stage graphics if overwritten.
- Updated enemy picker/config labels and speed mapping for the new variants.

## v0.7.52 (2026-05-24) Move Spark Ball and Demonhead settings
- Moved the Spark Ball speed and Demonhead snappy controls into the enemy
  settings tab.
- No ROM patch behavior changed.

## v0.7.51 (2026-05-24) Document JP66 editing policy
- Added the core ROM support policy to `AGENTS.md`: raw Japanese ROMs are only
  the input entry point, and normal editing targets the app-converted Japanese
  mapper66 wide-title expanded ROM.
- Clarified that US ROMs are source material only, such as title import, and
  should not receive edit-compatibility maintenance unless explicitly requested.

## v0.7.50 (2026-05-24) Keep Demonhead tweak JP66-only
- Restricted the Demonhead snappy wait patch back to the JP bank0 layout used
  by the customizer instead of maintaining shifted US-style edit support.
- This keeps US ROM handling aligned with the manual: US assets can be used as
  title material, but US ROMs are not normal edit targets.

## v0.7.49 (2026-05-24) Add Demonhead snappy turn wait
- Added a Demonhead snappy setting that minimizes the post-spawn/post-turn
  startup wait from `$0F` to `$01`.
- The patch locates the Demonhead wait instruction sequence dynamically, so it
  works with the JP address `$B2A7` and shifted US-style layouts.

## v0.7.48 (2026-05-24) Add Spark Ball speed multiplier
- Added a Spark Ball movement speed multiplier setting for the dedicated
  `$A9DF/$A9E7` signed delta tables.
- The setting updates both speed 1 and speed 2 directions, affecting stock
  Spark Balls and the Dragon-ID Spark Ball variants that enter `$A929/$A92D`.

## v0.7.47 (2026-05-24) Fix Panel Monster snappy variant save
- Fixed Panel Monster borrowed-ID variant application failing when the snappy
  pre-shot delay had already changed `$A55B` from `$10` to `$01`.
- Propagated the snappy delay into the Panel Monster normal/2-way/3-way cave
  routines after the variant hook is installed, so the setting keeps working
  after save/testplay preparation.

## v0.7.46 (2026-05-24) Add Neul and Ghost speed setting
- Added a "ゴースト＆ヌエル移動速度" enemy-AI setting that applies one
  multiplier to Ghost X speed and Neul Y speed.
- The setting updates both SP1 and SP2 speed-table pairs, so normal and
  noslow variants stay consistent with the picker speed system.
- Avoids `$40`, the engine's speed-update skip marker, and keeps negative
  speeds in the verified `$41-$7F` range when calculating multiplier-derived
  speed bytes.

## v0.7.45 (2026-05-24) Always edit Panel Monster cooldown
- Removed the extra Panel Monster cooldown-enable checkbox; the frame value is
  now the setting itself, with the original 192F shown as the default.
- Clarified the warning for very short cooldown values: the risk is exhausting
  the 17 shared sub-slots, which can cause missed shots or inconsistent bullet
  spawning in rooms with multiple firing enemies.

## v0.7.44 (2026-05-24) Add Panel Monster snappy fire wait
- Added a Panel Monster "キビキビ動作" setting that changes the pre-shot wait
  at `$A55B` from `$10` to `$01`.
- Renamed the existing Panel Monster interval control to cooldown and changed
  the UI to edit `$A57A` directly in frame units.
- Kept cooldown restoration separate from the snappy toggle so each setting can
  be changed independently.

## v0.7.43 (2026-05-24) Move shared monster speed out of Golem
- Moved the shared Golem/Dragon/Gargoyle s0 walk-speed control into its own
  enemy-AI group instead of keeping it inside the Golem group.
- Removed the Golem-only walk-speed and charge-speed controls from the dialog
  for now to avoid confusing shared speed with Golem-specific speed.
- Applying the dialog now changes only the shared s0 walk-speed pair
  `0x5BE0/0x5BE2` for that setting.

## v0.7.42 (2026-05-24) Split shared monster walk speed
- Split the former Golem walk-speed control into a shared s0 walk speed for
  Golem/Dragon/Gargoyle and a separate Golem s1 walk speed.
- Kept Golem charge speed as its own s1-only control.
- Updated global settings export/import to include the shared monster walk
  speed separately.

## v0.7.41 (2026-05-24) Add Dragon snappy behavior
- Added a Dragon "キビキビ動作" global setting that minimizes the Dragon-only
  pre-attack wait at `$A693` / file `0x26A3` to `$01`.
- Kept the shared Saramandor flame startup wait `$B0E8` unchanged so the
  setting affects Dragon's own wait without changing Saramandor timing.
- Included the new Dragon setting in global settings export/import and reset.

## v0.7.40 (2026-05-24) Split Gargoyle cooldown setting
- Added Gargoyle's pre-materialize wait `$AE6C` to the "キビキビ動作" toggle,
  so the snappy setting now minimizes three non-cooldown waits.
- Added a separate Gargoyle post-shot cooldown control for `$AE49`, keeping it
  out of the one-frame snappy toggle to avoid object-pool flooding.
- Included the cooldown value in global settings export/import and reset.

## v0.7.39 (2026-05-24) Hide top canvas border
- Removed the editor-only top decorative wall row from level canvas rendering
  while keeping the left and bottom decorative walls.
- Updated object-label positioning so labels stay aligned with the new
  border layout.

## v0.7.38 (2026-05-24) Add Gargoyle snappy behavior
- Added a Gargoyle "キビキビ動作" global setting that writes both confirmed
  Gargoyle wait thresholds to `$01`.
- The tweak restores the original `$68/$18` values when disabled and is kept
  separate from the borrowed-ID Gargoyle two-bullet variant.
- Included the new setting in global settings export/import and reset handling.

## v0.7.37 (2026-05-24) Simplify demo stage setting
- Removed the extra "change demo stage" checkbox from the game-behavior dialog.
- The demo stage spinbox now defaults to the ROM's current value, so an
  unmodified ROM shows the original 3面 instead of 6面.
- Applying the dialog now writes the selected demo stage directly; selecting
  3面 naturally restores the original value.

## v0.7.36 (2026-05-24) Clear wide title before attract demo
- Added a title-timeout-only hook at `$CB9E` that clears the stale wide-title
  nametable with `$CC18` before scheduling the original attract-demo action
  `$18`.
- Reserved the 9-byte `$BC0E-$BC16` / file `0x3C1E-0x3C26` stub in the PRG0
  cave ledger so it does not collide with room flags or the key-enemy runtime.
- Existing current wide-title ROMs receive the cleanup hook on save; fresh
  wide-title normalization writes it immediately.

## v0.7.35 (2026-05-24) Move wide-title RAM trampoline
- Moved the mapper66 wide-title RAM trampoline from `$03C0-$03CD` to
  `$072C-$0739` after static analysis confirmed `$03C0-$03DF` is inside the
  room block grid `$0304-$03E3`.
- Added save-time migration for already-normalized internal wide-title ROMs
  that still contain the old `$03C0` bootstrap.
- Updated the RAM ledger/map to reserve `$072C-$0739` and mark the old block
  grid overlap as forbidden.

## v0.7.34 (2026-05-24) Revert CHR0 wide-title return
- Reverted v0.7.33 after testing showed that returning the wide-title
  trampoline to `PRG0+CHR0` corrupts the following game/start screen.
- Restored the previous `PRG0+CHR3` return byte and removed the automatic
  CHR0 normalization.

## v0.7.33 (2026-05-24) Return wide title to CHR0
- Changed the mapper66 wide-title RAM trampoline return bank from
  `PRG0+CHR3` to `PRG0+CHR0`, so title rendering does not leave CHR bank3
  selected for demo pre-start, start, or clear screens.
- Added load/save normalization for already-wide ROMs that still contain the
  old `PRG0+CHR3` return byte.

## v0.7.32 (2026-05-24) Revert title idle demo cleanup patch
- Removed the action `$18` demo cleanup reroute and the `$BC0E` stub after it
  caused non-demo screen transitions and the clear screen to render incorrectly.
- Restored fresh wide-title normalization/saves to leave the original `$CBBB`
  attract-demo entry unchanged.
- Removed the temporary stub reservation from the ROM map and overlap ledger.

## v0.7.31 (2026-05-24) Keep attract demo mode after title cleanup
- Replaced the v0.7.30 direct `$CBB3` action-table route with a 6-byte stub at
  `$BC0E` / file `0x3C1E` that runs only `JSR $CC18` and then jumps back to the
  original `$CBBB` attract-demo entry.
- This keeps title-idle demo playback from turning into a normal auto-start
  while still clearing wide-title nametable leftovers before the SHRINE/ROOM
  screen.
- Added the stub span to the bank0 cave reservation ledger and ROM map.

## v0.7.30 (2026-05-24) Fix wide-title demo start cleanup
- Routed the title-idle demo action through the same `$CBB3` start-screen
  cleanup path used by manual Start, so wide-title nametable remnants do not
  leak into the SHRINE/ROOM demo pre-start screen.
- Applied the repair when JP mapper66 ROMs are loaded/saved, including ROMs
  that were already in the internal wide-title format.

## v0.7.29 (2026-05-24) Isolate title top PNG palette import
- Changed 4-color Top PNG import so imported PNG colors are assigned only to a
  title palette slot that is unused outside the imported top band.
- Kept the universal background color and existing lower title palette usage
  untouched so the mountain/shrine area is not recolored by a top-only import.

## v0.7.28 (2026-05-24) Fix 4-color title top PNG import
- Added a dedicated 4-color Top PNG import path that maps PNG colors directly
  to title CHR pixel indices instead of re-quantizing through the existing
  title attribute palettes.
- The importer now updates title palette #0 and forces the stored top title
  attributes to palette #0 so clean 4-color 256x64 title art stays intact.

## v0.7.27 (2026-05-24) Move wall colors into palette editor
- Moved the 4-stage wall color controls from the game-behavior dialog into the
  palette editor so they use the same 64-color picker workflow.
- Palette Apply now refreshes the wall-color preview on the canvas and
  regenerates the level thumbnails.

## v0.7.26 (2026-05-24) Match bundled palette file
- Replaced the shared NES RGB palette with the exact raw RGB values from
  a 192-byte palette reference file.
- This supersedes the previous hand-entered palette table after binary
  verification showed that it did not match the palette file.

## v0.7.25 (2026-05-24) Use Mesen NES palette
- Replaced the shared NES RGB palette with the Mesen palette values supplied
  from emulator data.
- Palette-dependent previews now use the same color basis across the canvas,
  pickers, palette editor, sprite viewer, title preview, and wall-color swatches.

## v0.7.24 (2026-05-24) Preview stage wall colors
- Replaced the stage wall color numeric fields with NES color swatch selectors.
- Synced edited wall colors into the main canvas and the right-side level
  thumbnails after applying game-behavior changes.

## v0.7.23 (2026-05-24) Add stage wall color table editor
- Added game-behavior controls for the 12 normal-stage wall color table entries
  at ROM `$9122` / file offset `0x1132`.
- The editor changes stages 1-48 in four-stage groups and intentionally leaves
  the trailing `$80/$80` special-stage markers untouched.

## v0.7.22 (2026-05-24) Fix canvas label overlay placement
- Fixed object label background rectangles being placed with mixed scene/local
  coordinates, which caused black label boxes to appear offset from the text.
- Tightened stacked label spacing for labels on the same tile.

## v0.7.21 (2026-05-24) Render object labels as UI overlay
- Changed canvas object labels from burned-in image text to QGraphicsView overlay
  text so labels stay crisp when the level canvas is scaled.
- Removed the internal image-rendered label path to avoid pixelated text.

## v0.7.20 (2026-05-24) Color mirror enemy row labels
- Colored the mirror enemy row labels in the picker: M1 is red and M2 is blue.

## v0.7.19 (2026-05-24) Add canvas object labels
- Added a display option that overlays short labels on canvas objects such as
  items, enemies, key, door, mirrors, start position, constellation, and special
  meta items.
- Current-level and all-level PNG exports include the object labels when the
  display option is enabled.

## v0.7.18 (2026-05-24) Limit title text input
- Limited the title additional-text dialog input field to 32 characters so
  overlong text cannot be typed or pasted in the UI.

## v0.7.17 (2026-05-24) Fix US66 title source detection
- Fixed mapper66-expanded US ROMs being detected as JP66 during title import,
  which caused the imported title preview to use the wrong nametable layout.
- Expanded ROM region detection now prefers the original PRG JP/US signature
  before the shared mapper66 loader marker.

## v0.7.16 (2026-05-24) Remove legacy title image buttons
- Removed the old full-screen title image save/import buttons from the title
  migration dialog.  The focused Top PNG controls remain available.

## v0.7.15 (2026-05-24) Limit per-level time-rate selector
- Restricted the per-level time decrease selector to 0-2 because values 3 and
  above are not valid table selectors.

## v0.7.14 (2026-05-24) Show time-rate duration estimates
- Added real-time duration estimates beside the three global LIFE decrease
  table values in the game-behavior dialog.

## v0.7.13 (2026-05-24) Add global time decrease table hack
- Added game-behavior controls for the three global LIFE decrease table values:
  fast, normal, and slow.
- The controls edit the original `$9942` table directly without using PRG0
  cave space.

## v0.7.12 (2026-05-24) Split time decrease hint label
- Moved the time decrease rate value guide onto a second line so the level
  settings form no longer stretches horizontally.

## v0.7.11 (2026-05-24) Clarify time decrease rate labels
- Updated the level setting label to show the meaning of the time decrease
  values: 0 is fast, 1 is normal, and 2 is slow.

## v0.7.10 (2026-05-24) Fix stats lifetime column lookup
- Fixed the all-level stats dialog crash caused by renaming the enemy lifetime
  column header without updating its internal column lookup.

## v0.7.9 (2026-05-24) Simplify game-hack dialog tabs
- Reduced the game behavior hack dialog from five tabs to two tabs: enemy and
  non-enemy settings.
- Existing enemy/AI controls now appear under the enemy tab; all other controls
  are grouped under non-enemy.

## v0.7.8 (2026-05-24) Clarify mirror enemy lifetime units
- Updated the level settings and mirror detail labels to show that enemy
  lifetime is roughly 0.5 seconds multiplied by the configured value.
- Added tooltips with measured examples and adjusted the stats/manual wording.

## v0.7.7 (2026-05-24) Reframe distribution manual as user guide
- Revised the distribution HTML manual as an operation-focused user guide.
- Added a prominent feature summary and Japanese-first headings with English
  labels for GitHub-style presentation.

## v0.7.6 (2026-05-24) Add distribution HTML manual
- Added `docs/distribution_manual.html` as a GitHub-style user manual for
  distribution.
- The manual explains supported ROMs, the Japanese-ROM basis, basic editing,
  stage settings, enhanced enemies, start-screen announcements, and output
  guidance.

## v0.7.5 (2026-05-24) Add adjustable gray UI setting
- Added a settings control for the application-wide gray UI tone.
- The gray tone is now stored in the app config and applied immediately from
  the settings dialog.

## v0.7.4 (2026-05-24) Add softer gray UI theme
- Added a shared Qt stylesheet that changes the default white UI surfaces to a
  softer gray palette while keeping the editor canvas unchanged.

## v0.7.3 (2026-05-24) Merge level info into settings
- Removed the separate level-info group and moved the remaining summary into
  the level-settings group.
- Hid redundant key position, door position, start position, and key-enemy
  number text from the summary because those are edited or visible elsewhere.

## v0.7.2 (2026-05-24) Show loaded ROM metadata version
- Display the embedded MAGATU_SOLOMON_CUSTOMIZER version in the ROM info panel
  when loading a ROM that already contains the metadata stamp.

## v0.7.1 (2026-05-24) Constrain key enemy selector
- Limited the key-carrying enemy selector to the number of enemies currently
  placed in the selected stage.
- When enemy deletion makes the saved key enemy number invalid, the setting is
  cleared and a warning is shown instead of leaving an out-of-range target.

## v0.7.0 (2026-05-24) Minimum feature milestone
- Marked the first 0.7 release as the milestone where the current minimum
  target feature set is in place.
- This release includes the accepted stage settings foundation, key-carrying
  enemy support, start-of-stage fire reset, stage-start announcements, and the
  current enhanced enemy variants.

## v0.6.173 (2026-05-24) Fix key-enemy announcement gate branch
- Fixed the stage-start announcement key-enemy gate at `$B3C0`: the no-key
  branch now lands on the routine `RTS` instead of one byte after it.
- This fixes room 4+ test play freezing on the start screen when the
  announcement overlay is installed but the current room has no key enemy.

## v0.6.172 (2026-05-24) Add room4 start-freeze probe
- Added `mesen_probes/lua/start_screen_room4_freeze_probe.lua` to capture the
  room 4+ test-play start-screen freeze after the announcement overlay work.
- The probe logs the actual ROM bytes at `$9061`, `$8BE2`, `$E3BC`, `$E38C`,
  and `$B3C0`, then traces the stage-start path through `$915E`, `$9BD5`,
  `$9071`, `$974B`, PPU queue writes, and the key startup RAM values.

## v0.6.171 (2026-05-24) Move start announcement main cave
- Moved the stage-start announcement main routine from `0x0BF2 / $8BE2` to
  `0x63CC / $E3BC`, and split its mask table to `0x60CC / $E0BC`.
- This removes the overlap with the initial magic routine at `$8BE2`, which was
  breaking the stage-start initializer and freezing test play on room 4+ even
  when the room had no announcement flags.

## v0.6.170 (2026-05-24) Improve start-screen stall probe
- Reduced `$8DB4` PPU-wait log spam in `start_screen_stall_probe.lua` so later
  stage-start freezes are not hidden by the previous room's wait loop.
- Added relative-frame periodic snapshots and an automatic nametable dump once
  the probe reaches room `$03`.

## v0.6.169 (2026-05-24) Add start-screen stall probe
- Added `mesen_probes/lua/start_screen_stall_probe.lua` to capture the frozen
  stage-start screen state after the announcement overlay patch.
- The probe logs the custom announcement hook path, stock start-screen update,
  PPU script/wait calls, room flags, key-enemy marker, and nametable snapshots.

## v0.6.168 (2026-05-24) Remove Golem charge dash boost
- Removed the Golem charge-only dash boost module and its hack-dialog control.
- Removed the Golem charge dash reserved spans from the PRG0 overlap ledger;
  the accepted Gargoyle 2-shot cave now owns those occupied ranges without a
  mutual-exclusion warning.
- Simplified the Saramandor `$866D` hook compatibility check back to the active
  slow-Bullet wrapper path.

## v0.6.167 (2026-05-24) Restore map document encoding
- Restored the ROM/RAM map HTML files from the last clean UTF-8 backup and
  reapplied the v0.6.166 inventory changes without re-encoding the Japanese
  text through PowerShell defaults.
- Kept the key-enemy RAM ledger and Gargoyle/Golem mutual-exclusion inventory
  notes while removing the mojibake introduced during the previous map edit.

## v0.6.166 (2026-05-24) Refresh ROM/RAM maps
- Updated the ROM/RAM map docs from the current inventory check, including the
  stage-start announcement PRG/CHR spans.
- Recorded key-enemy runtime RAM `$0723-$072B` and split the remaining
  entity-tail candidate range to `$072C-$073F`.
- Added the current code-cave overlap result: only the known Gargoyle two-shot
  / Golem charge-dash mutual-exclusion spans overlap; stage announcements do
  not overlap existing patches.

## v0.6.165 (2026-05-24) Fix announcement draw loop index
- Fixed the stage-start announcement flag branch by replacing the per-label
  `$915E` call with a `$9471`-style PPU script wait helper.
- Preserved the caller's `X` register while drawing each label so the room-flag
  announcement loop no longer runs past its five flag entries.
- Added migration tolerance for ROMs saved by the v0.6.164 announcement hook.

## v0.6.164 (2026-05-24) Fix stage-start announcement order
- Fixed the stage-start announcement hook so custom labels are drawn before
  returning to the stock `$915E` intro update, matching the accepted test-ROM
  call order.
- This fixes the v0.6.163 freeze on the start screen where the shrine marker
  and announcement labels were not displayed.

## v0.6.163 (2026-05-24) Add stage-start announcements
- Added a stage-start announcement overlay that displays active level settings
  on the intro screen using the accepted two-column layout:
  `DARK ROOM`, `FIRE LOSS`, `KEY ENEMY`, `HIDDEN DOOR`, `FIRE SEALED`, and
  `SPELL SEALED`.
- Installed custom gameplay CHR tiles for the missing `K` and `P` letters in
  banks 0/1/2 at tile bytes `$25` and `$27`.
- Wired the overlay into ROM saves from existing room flags, fire-reset state,
  and key-enemy settings without adding new per-stage UI fields.
- Added verification ROM
  `ROM/TEST_StartScreen_AnnouncementAppSave_All6_v163_stage1.nes`.

## v0.6.162 (2026-05-23) Add Gargoyle two-shot variant
- Added the accepted `$AE6F` two-Bullet materialization routine for borrowed
  Gargoyle IDs `$7A/$7B`, matching
  `TEST_GargoyleTwoBullet_AE6F_SecondXAhead16_DirVelocity_JP_v7_stage6_7B.nes`.
- Kept stock Gargoyles `$78/$79` on the original single-Bullet path by adding a
  type gate before the two-shot body.
- Wired the Gargoyle variant into ROM saves when `$7A/$7B` are present in stage
  or mirror enemy data, and updated picker/config labels for the new 2-shot
  Gargoyle entries.
- Updated the ROM map to document the Gargoyle 2-shot cave placement and its
  current mutual exclusion with the Golem charge dash cave layout.
- Added a guard so the Golem charge dash hack does not silently overwrite an
  already-applied Gargoyle 2-shot ROM.

## v0.6.161 (2026-05-23) Add Gargoyle two-bullet probe
- Added `mesen_probes/lua/gargoyle_two_bullet_v5_probe.lua` for the successful
  v5 Gargoyle two-bullet experiment. The probe groups each attack, counts the
  two `$AE76` materialization calls, logs Bullet writes at `$9D1C/$9D33`, and
  traces early Bullet lifecycle paths to catch the occasional one-shot-looking
  case.

## v0.6.160 (2026-05-23) Disable broken Gargoyle rapid-fire patch
- Disabled the v0.6.159 Gargoyle rapid-fire runtime hook from normal ROM saves
  after validation showed it prevented Gargoyle bullets from materializing and
  could interfere with item pickup handling.
- Restored `$7A/$7B` enemy picker descriptions to neutral Gargoyle #2 labels
  until the firing path is re-tested with a dedicated probe.
- Added `mesen_probes/lua/gargoyle_fire_trace_probe.lua` to capture the real
  Gargoyle child-slot reservation and Bullet materialization path before the
  next rapid-fire attempt.

## v0.6.159 (2026-05-23) Add Gargoyle rapid fire
- Added a Gargoyle speed1 #2 rapid-fire variant for `$7A/$7B`; the first shot
  keeps attack state active and the second shot follows shortly after before
  the stock reset resumes.
- Reclaimed the unused padding after the Saramandor Bullet state0 cave and
  placed the new Gargoyle reset wrapper at `$BEC7-$BEF2`, ahead of the
  key-enemy split chunks.
- Updated the enemy picker labels for `$7A/$7B` to describe the rapid-fire
  Gargoyle variant.

## v0.6.158 (2026-05-23) Clear key enemy gap_fix overlap
- Relocated the key-enemy initial-slot binder from `$C000` to reclaimed PRG0
  tail space at `$C1D6`.
- Split the key-enemy defeat dropper across small verified PRG0 cave gaps,
  moving its entry from `$C029` to `$BE2F` and clearing the old `$C000/$C029`
  bytes during migration.
- Removed the remaining PRG0 overlap with `gap_fix` `$C000-$C087`, allowing
  key-carrying enemies and the horizontal-gap stabilization patch to coexist.

## v0.6.157 (2026-05-23) Move room flag data to PRG1
- Moved mapper66 runtime room flags and hidden-door cell data into the PRG1
  StageExt table, copied during the mapper66 loader tail into `$0778` and
  `$077C`.
- Freed PRG0 `$C180-$C1FF` from the old DoorCellTable/RoomFlagTable role and
  relocated the key-enemy dropped-key handler from `$C0F0` to `$C180`.
- Returned `$C0F0-$C155` to the runtime block override cave, removing the
  collision between key-carrying enemies and special block/dark-room runtime
  handling.

## v0.6.156 (2026-05-23) Fix fall key drop entry
- Fixed the fall-death key handler to call the relocated key-drop body at
  `$C02C` instead of the old `$C024` entry. The previous v0.6.155 layout could
  fall through into the fire-defeat-only `$9D1C` setup and crash when an enemy
  died by falling.

## v0.6.155 (2026-05-23) Add key enemy fall-death drops
- Added fall-death support for key-carrying initial enemies. The selected
  initial enemy now receives the existing fall-death replacement flag during
  room enemy load, so dropping its footing can trigger the key path.
- Hooked the original fall-fairy replacement entry to spawn the configured key
  and then despawn the falling enemy normally. Rooms without an active key
  target preserve the original fairy replacement behavior.
- Moved the key enemy defeat and door-light helper caves to make room for the
  fall-death flagging logic, and added migration from the v0.6.153-v0.6.154
  cave layout during save.

## v0.6.154 (2026-05-23) Balance key enemy slot hook stack
- Fixed the production key-enemy initial-slot binder to match the successful
  v12 experiment: every branch now balances the saved X register with exactly
  one PLA before returning.
- Prevented non-target initial enemies from leaking one stack byte each during
  room setup, which could make stages with multiple enemies immediately clear
  or otherwise corrupt startup flow.
- Allowed ROMs saved with the previous v0.6.153 key-enemy binder to be
  overwritten by the corrected binder during the next save.

## v0.6.153 (2026-05-23) Fix key enemy entry clear
- Split the configured key-carrying initial enemy slot from the dropped-key
  runtime state. The StageExt slot now lives in RAM `$072B`, while `$0723`
  remains only the dropped-key active/tile marker.
- Fixed a bug where entering a stage could immediately flow into key/clear
  handling because the configured enemy number was misread as an active dropped
  key.

## v0.6.152 (2026-05-23) Wire key enemy runtime
- Added the production runtime patch for per-stage key-carrying initial
  enemies. Mapper66 stage load now copies the StageExt key enemy slot into RAM,
  binds that initial placement number to the runtime enemy slot, and drops a
  key when that enemy is defeated.
- Added dropped-key pickup handling so the generated key opens the door through
  the normal key flow without reusing Demon Mirror spawned enemies.
- Added ROM/RAM overlap guards for the key runtime cave spans. The patch refuses
  to overwrite non-empty unrelated code instead of silently colliding.

## v0.6.151 (2026-05-23) Add key enemy UI
- Added enemy order numbers to the tile hover/status-bar enemy text, shown as
  `敵#N`, so the initial placement index can be identified from the canvas.
- Added a per-level `鍵持ち敵 (#)` setting that writes the existing stage
  extension key-enemy slot field. `0` means none; `1-15` correspond to the
  initial placed enemy order.
- Added stage extension helper accessors for key-enemy enable/read/write
  handling.

## v0.6.150 (2026-05-23) Isolate borrowed-ID visual metadata
- Replaced the v0.6.121 Panel Monster group-wide property/animation rewrites
  with type-specific hooks, so only the borrowed Panel IDs receive Panel
  metadata.
- Chained the Spark Ball property/animation hooks through the Panel selectors
  so both borrowed-ID systems coexist without reverting each other.
- Restored the original shared Demonhead/Saramandor group metadata, preventing
  stock Demon Mirror spawns such as `$50/$51` from inheriting Panel Monster
  metadata.

## v0.6.149 (2026-05-23) Trace Demon Mirror slot writes
- Extended the Demon Mirror fire reset probe to log writes to the first four
  main/sub entity slots. This checks whether mirror-spawned enemies are created
  and then immediately cleared before the next active-enemy scan.

## v0.6.148 (2026-05-23) Expand Demon Mirror spawn probe
- Reduced repeated PPU-submit noise in the Demon Mirror fire reset probe and
  added tracing for the real mirror enemy spawn path (`$9F0C`, `$9F40`,
  `$9F61`, `$A2B8`) plus the first four entity slots.

## v0.6.147 (2026-05-23) Add Demon Mirror fire reset probe
- Added a Mesen Lua probe for the per-stage fire reset investigation. It logs
  the Demon Mirror spawn path, active enemy gate, free-slot result, fire stock
  bytes, and PPU/HUD update state so the mirror-spawn regression can be
  separated from the HUD redraw fix.

## v0.6.146 (2026-05-23) Revert post-HUD fire reset hook
- Reverted the v0.6.145 `$90E6` post-HUD hook because it worsened stage-start
  behavior and still did not restore Demon Mirror spawning.
- Restored the v0.6.144-style loader-based fire reset implementation while the
  Demon Mirror interaction is investigated separately.

## v0.6.145 (2026-05-23) Move fire reset after stage setup
- Moved the per-stage fire reset runtime out of the `$9071` level-loader cave.
  The loader now only caches `ROOMFLAGS` and handles hidden doors again.
- Added a new `$C0C2` post-HUD cave hooked from `$90E6`. It runs after level
  ready, enemy placement, and HUD buffer setup, then clears `$042E/$042F` and
  redraws the HUD when `ROOMFLAGS` bit4 is set. This avoids interrupting Demon
  Mirror setup.

## v0.6.144 (2026-05-23) Fix per-stage fire reset target
- Fixed the stage fire reset runtime so it no longer clears `$042B`. That byte
  is part of the HUD/max/cursor state, not just carried stock, and clearing it
  caused impossible scroll-count display behavior.
- The reset now clears only `$042E/$042F` and immediately calls `$A1CC` to
  redraw the fire stock HUD for the new stage.

## v0.6.143 (2026-05-23) Add per-stage fire reset
- Added a stage setting that resets carried fire / super-fire stock at stage
  start. The UI stores the setting in `StageExtTable`, while the runtime mirrors
  it into `RoomFlagTable` bit4 so bank0 stage-load code can apply it without PRG
  bank switching.
- Expanded the `$BBE0` room loader cave from 37B to 55B. When bit4 is set for
  the current room, the loader clears `$042B/$042E/$042F` before play begins.
- Updated ROM/RAM maps. The bank0 cave fragmented free total is now 218B, with
  the largest continuous fragment still 46B.

## v0.6.142 (2026-05-23) Add StageExtTable foundation
- Added a PRG1 `StageExtTable` at `0x8800-0x8A0F`: 16B header plus 64 rooms
  x 8B. This is the shared per-stage settings foundation for future fire
  reset, key-carrying enemies, and stage-start announcement features.
- Added read/write plumbing so mapper66 expansion and mapper66 saves preserve
  the table, and XML export/import keeps the new per-level fields.
- Updated the visual ROM map. PRG1 general reserve now starts at `0x8A10` and
  remains 12,678B.

## v0.6.141 (2026-05-23) Share Panel Monster fire tail
- Shared the identical Panel Monster marker-write helper and fire-exit tail
  between the 2-way and 3-way fire caves. The 2-way cave now jumps to the
  3-way cave's common tail and keeps only a local ready-timer RTS.
- Reduced the Panel Monster borrowed-ID reservation by another 27B. Borrowed-ID
  runtime reservations are now 819B total, and the bank0 cave fragmented free
  total is 238B with a 46B largest fragment.

## v0.6.140 (2026-05-23) Free unused Borrowed-ID reserves
- Removed the unused `$BF50-$BF68` NOP-only Saramandor variant reservation from
  the Borrowed-ID runtime span list. This frees 25B in the PRG0 bank0 cave
  without changing Saramandor, Panel Monster, or Spark Ball behavior.
- Split the Panel Monster bullet hook and normal fire copy reservations so the
  unused 10B gap at `$BFAF-$BFB8` is no longer treated as occupied.
- Updated the visual ROM map: the bank0 cave fragmented free total is now
  211B, with the largest continuous fragment still 27B.

## v0.6.139 (2026-05-23) Split PRG1 wide-title reserve
- Reduced the wide-title PRG1 reservation from `0x80D0-0xBB95` to
  `0x80D0-0x87FF`, leaving a 1,840B title workspace. The confirmed imported
  title uses 589B.
- Reclassified `0x8800-0xBB95` as a 13,206B PRG1 general reserve for future
  stage-load-time tables and non-gameplay-screen code/data.

## v0.6.138 (2026-05-23) Restore visual ROM map layout
- Rebuilt the current mapper66 ROM map with visual bars for the full ROM,
  PRG0, the bank0 cave range, and PRG1 so occupied, custom, and reserve regions
  are easier to inspect.
- Added a planning section that separates PRG0 runtime code from PRG1-friendly
  tables and stage-load-time data.

## v0.6.137 (2026-05-23) Move Spark Ball variant caves away from gap_fix
- Relocated the Dragon-ID Spark Ball variant runtime caves out of the
  `$C000-$C087` gap_fix cave range. The Spark Ball variant now uses smaller
  PRG0 free fragments at `$BD26`, `$BE62`, `$BEEA`, `$BFD8`, `$CFDE`, and
  `$EFC4`.
- Verified that gap_fix and the Spark Ball variants can be applied together
  without overlapping reserved PRG spans.

## v0.6.136 (2026-05-23) Preserve normal animation table lookup
- Restored the animation metadata hook's normal path to reload the original
  type-group index before reading `$D0E8/$D0E9`. This prevents non-variant
  characters from using the wrong animation metadata after the Spark Ball
  variant type check.

## v0.6.135 (2026-05-23) Fix Spark Ball variant animation detection
- Fixed the Dragon-ID Spark Ball animation hook to read the entity type byte
  from the active main slot instead of using the animation state scratch value.
  This keeps normal Dragons rendered as Dragons while allowing `$6A/$6B/$6E/$6F`
  to render as Spark Balls.

## v0.6.134 (2026-05-23) Restore normal Dragon rendering
- Reworked the Dragon-ID Spark Ball variants so `$6A/$6B/$6E/$6F` get Spark
  Ball property and animation metadata through type-specific hooks instead of
  changing the shared Dragon groups.
- Restored the shared Dragon property and animation table bytes so normal
  Dragons `$68/$69/$6C/$6D` no longer turn into Spark Balls.

## v0.6.133 (2026-05-23) Correct Spark Ball pause direction labels
- Updated picker/config labels for the Dragon-ID Spark Ball pause variants to
  match confirmed behavior: `$6A/$6E` are up, `$6B/$6F` are down.

## v0.6.132 (2026-05-23) Keep Dragon IDs for Spark Ball pause detection
- Changed the Dragon-ID Spark Ball variants to keep their original
  `$6A/$6B/$6E/$6F` type bytes while routing their AI into the stock Spark Ball
  routines. This leaves a stable identity for the pause hook to inspect.
- Replaced the sub-slot `+3` marker check with a direct main-slot type check at
  the `$AB13` Spark Ball speed commit. Stock `$28-$2F` Spark Balls bypass the
  pause hook path.

## v0.6.131 (2026-05-23) Isolate Spark Ball pause variants
- Added a marker-based `$AB13` pause hook for the Dragon-ID Spark Ball variants.
  The wrapper marks sub-slot `+3` with `$A6`, and only marked enemies use the
  LIFE-hundreds mod3 stop behavior.
- Moved the fast Dragon-ID wrapper to `$C008` and placed the pause hook at
  `$C038` so the larger marker-aware wrappers do not overlap.
- Restored picker/config labels to "Spark Ball pause" for `$6A/$6B/$6E/$6F`.

## v0.6.130 (2026-05-23) Stabilize Dragon-ID Spark Ball variants
- Added the missing Spark Ball property and animation metadata patches for the
  borrowed Dragon `$6A/$6B/$6E/$6F` groups. This matches the confirmed test ROM
  setup more closely and prevents the borrowed IDs from initializing/rendering
  as unrelated enemies.
- Kept the LIFE-hundreds pause hook disabled for now because the confirmed
  marker-free hook also changes original `$28-$2F` Spark Balls.
- Renamed picker/config labels from "pause" to "variant" until the stop behavior
  can be isolated cleanly.

## v0.6.129 (2026-05-23) Remove unsafe Spark Ball variant marker
- Removed the unsafe Spark Ball pause marker experiment. Both main-slot `+2`
  and sub-slot `+2` could corrupt the borrowed Dragon-ID Spark Ball variants.
- The Dragon-ID Spark Ball variants now only convert `$6A/$6B/$6E/$6F` into
  the confirmed stock Spark Ball phases. The global `$AB13` pause hook is no
  longer applied, so original `$28-$2F` Spark Balls are untouched.

## v0.6.128 (2026-05-23) Move Spark Ball variant marker to sub-slot
- Moved the Spark Ball pause variant marker off main-slot `+2`, which can affect
  enemy appearance/initialization.
- The Dragon-ID Spark Ball variants now mark sub-slot `+2` instead, while
  original `$28-$2F` Spark Balls still bypass the pause hook.

## v0.6.127 (2026-05-23) Isolate Spark Ball pause variants
- Fixed the enemy picker so the Dragon-ID Spark Ball pause variants appear as
  selectable monster entries.
- Changed the Spark Ball pause hook to check a borrowed-ID marker before
  applying the LIFE-hundreds mod3 stop. Original `$28-$2F` Spark Balls now keep
  their stock movement.

## v0.6.126 (2026-05-23) Add Dragon-ID Spark Ball variants
- Added an always-on Spark Ball variant patch for the accepted Dragon #2 IDs:
  `$6A/$6B/$6E/$6F`.
- `$6A/$6E` enter the stock Spark Ball up phase, while `$6B/$6F` enter the
  accepted right-hand/down phase; slow/fast pairs use the confirmed stock Spark
  AI entry points.
- Added the LIFE-hundreds mod3 pause hook at the Spark Ball position commit and
  updated enemy definitions so the reused Dragon IDs appear as Spark Ball pause
  variants in the editor.

## v0.6.125 (2026-05-23) Document Spark Ball wall-follow orientation
- Updated the commented ASM notes for Spark Ball movement to clarify that
  `cw/ccw` is not always the visible screen rotation.
- Added the safer wall-follow wording: `$28/$2B` move with the wall on the
  right-hand side, while `$29/$2A` move with the wall on the left-hand side;
  the visible loop direction can reverse between inner-wall and outer-wall
  layouts.

## v0.6.124 (2026-05-23) Revert unstable Panel Monster velocity-sync experiment
- Reverted the v0.6.123 Panel Monster diagonal Bullet velocity-sync change.
  It corrupted spawned-enemy behavior, including demon mirror spawns, and made
  Panel Monster firing/orientation unreliable.
- Restored the v0.6.122 move-gated Bullet Y hook, which keeps the fixed mouth
  drift behavior without touching spawned Bullet velocity or mirror spawn flow.

## v0.6.123 (2026-05-23) Use Y velocity for Panel Monster diagonal Bullets
- Reworked Panel Monster variant diagonal shots to set the spawned Bullet's
  Y velocity instead of moving Y manually from the Bullet AI hook.
- Restored the stock Bullet AI entry at `$AFBB`, while keeping the accepted
  2-way/3-way spawn patterns through a shared diagonal velocity helper.
- This keeps diagonal motion tied to the stock entity physics path, reducing
  angle drift when enemy load changes.

## v0.6.122 (2026-05-23) Gate Panel Monster diagonal Y movement on Bullet motion
- Fixed the production Panel Monster variant Bullet hook so diagonal Y movement
  is applied only when the stock Bullet movement routine reports active motion.
- This prevents newly spawned Panel Monster Bullets from drifting vertically
  while they are still waiting at the mouth before horizontal movement begins.

## v0.6.121 (2026-05-23) Add Panel Monster 2-way and 3-way variants
- Added an always-on Panel Monster borrowed-ID patch for `$52/$53/$56/$57`
  as 2-way diagonal shot panels and `$5A/$5B/$66/$67` as 3-way shot panels.
- The patch keeps the borrowed IDs intact, but routes their AI through Panel
  Monster wrappers, applies Panel Monster init properties/animations, and
  hooks Panel Bullet Y movement for the accepted diagonal behavior.
- Updated the enemy picker and enemy definitions so the borrowed IDs appear as
  Panel Monster variants instead of Demonhead/Saramandor entries.

## v0.6.120 (2026-05-23) Add Golem charge dash boost to Customizer
- Added `core/golem_charge_dash.py` and a Golem charge dash boost selector in
  the game behavior dialog. The selector offers OFF/2x/3x/4x/5x, with 5x
  matching the accepted test behavior.
- The production patch chains through the existing Saramandor speed wrapper so
  Saramandor bullet variants and the Golem charge boost can coexist.
- The boost targets only the confirmed Golem rush speeds `$26/$5A`; normal
  walking speeds remain controlled by the existing Golem speed settings.

## v0.6.119 (2026-05-23) Add Golem charge-only 5x dash test ROM
- Added `TEST_GolemChargeOnly5xMove_JP_v5_stage6.nes`.
- This keeps the confirmed charge-only `$26/$5A -> $3F/$41` speed remap, but
  reduces the extra X movement loop from nine passes to four passes, for five
  total X movements per frame during the rush.

## v0.6.118 (2026-05-23) Fix Golem charge-only branch offsets
- Added `TEST_GolemChargeOnly10xMove_JP_v4_branchfix_stage6.nes`.
- The trace confirmed the visible Golem rush uses type `$74`, behavior `$10`,
  state 4, and X velocity `$26`. The previous v3 test targeted `$26/$5A`, but
  its branch offsets skipped the `$3F/$41` writes; v4 corrects those branches.

## v0.6.117 (2026-05-23) Add Golem charge trace probe
- Added `mesen_probes/lua/golem_charge_trace_probe.lua` to capture the real
  Golem rush/charge moment in Mesen, including behavior/state transitions,
  X-velocity writes, stock speed-table writes, and actual X-position commits.

## v0.6.116 (2026-05-23) Add Golem charge-only 10x dash test ROM
- Added `TEST_GolemChargeOnly10xMove_JP_v3_stage6.nes` to keep normal Golem
  walking speeds unchanged while testing the 10x movement wrapper only on the
  known charge/attack X-speed bytes `$26/$5A`.

## v0.6.115 (2026-05-23) Fix Golem 10x dash test target speeds
- Added `TEST_GolemDashMax10xMove_AllSpeeds_JP_v2_stage6.nes`, which expands
  the Golem speed override from only `$0C/$74` to all known Golem X-speed bytes
  `$13/$6D/$0C/$74/$26/$5A`.
- Added `mesen_probes/lua/golem_dash_probe.lua` to log Golem speed-init,
  stock X commits, and the extra X wrapper entry while testing in Mesen.

## v0.6.114 (2026-05-23) Add Golem max dash 10x-move test ROM
- Added `TEST_GolemDashMax10xMove_JP_v1_stage6.nes` for the stronger Golem dash
  experiment.
- The ROM keeps the max dash speed override from v0.6.113, but the `$86D2`
  wrapper now applies nine extra X movement passes after the stock movement,
  for ten total X movements per frame during max-speed Golem dash only.

## v0.6.113 (2026-05-23) Add Golem max dash double-move test ROM
- Added `TEST_GolemDashMaxDoubleMove_JP_v1_stage6.nes` to test a Golem dash
  variant that goes beyond speed-table-only tuning.
- The ROM wraps `$866D -> $8AC0` to raise Golem dash X speeds to `$3F/$41`,
  then wraps the `$86D2` X-position commit so only those max-speed Golem dashes
  receive one extra X movement application per frame.

## v0.6.112 (2026-05-23) Add right-facing Ghost right-speed test ROM
- Added `TEST_GhostRightFacing_RightSpeedOnly_JP_v1_stage6.nes` to verify a
  type-gated Ghost speed override.
- The test wraps the stock `$866D -> $8AC0` speed initialization through a
  `$BEEF` cave and only changes X speed `$1C` to `$38` for right-facing Ghost
  speed 0 types `$34/$35`, leaving `$36/$37` untouched.

## v0.6.111 (2026-05-23) Add Ghost slowest-speed test ROM
- Added `TEST_GhostSpeed_Slowest01_7F_JP_v1_stage6.nes` to verify the slowest
  nonzero Ghost speed 0 values.
- The test sets right movement to `$01` and left movement to `$7F`, with the
  existing stage 6 start bytes.

## v0.6.110 (2026-05-23) Add Ghost left-speed limit test ROM
- Added `TEST_GhostSpeed_LeftOnly64to41_JP_v1_stage6.nes` to test the fastest
  practical left-movement value for Ghost speed 0.
- The test leaves the right-movement byte unchanged and changes only the left
  speed byte from `$64` to `$41`; `$40` remains avoided because it is the stock
  speed-update skip marker.

## v0.6.109 (2026-05-23) Add Ghost left-speed isolation test ROM
- Added `TEST_GhostSpeed_LeftOnly64to48_JP_v1_stage6.nes` to verify the Ghost
  left-movement speed byte independently.
- The ROM leaves the right-speed byte unchanged and only changes the left
  speed pair from `$64` to `$48`, plus the existing stage 6 start bytes.

## v0.6.108 (2026-05-23) Log actual Ghost X movement commits
- Extended the Ghost speed Mesen probe to also hook `$86D2`, where X pixel
  movement is committed.
- Replaced the inferred direction label with raw `behLow` logging so left/right
  conclusions can be made from actual X deltas instead of guessed labels.

## v0.6.107 (2026-05-23) Add Ghost speed write probe
- Added a Mesen Lua probe that hooks the Ghost/Neul speed initialization write
  at ASM `$8B01`.
- The probe logs the active entity slot, type, behavior, speed index, and X
  velocity value so Ghost speed changes can be verified from emulator traces.

## v0.6.106 (2026-05-22) Explain why the distribution manual uses JP ROMs
- Expanded the distribution manual intro draft with the rationale for using
  the Japanese ROM as the normal editing base.
- Documented the US ROM tradeoffs: the extra license screen adds a step before
  gameplay and consumes some ROM space, while US-style title visuals can still
  be imported into a JP-based ROM.

## v0.6.105 (2026-05-22) Stamp exported data and mapper66 ROMs with app version
- Added a mapper66 ROM metadata stamp at PRG bank1 file `0xFF00-0xFF3F`,
  using the free area after the runtime block override table and before the
  copied vectors.
- ROM saves now write the current `MAGATU_SOLOMON_CUSTOMIZER` app version into
  that metadata slot for expanded mapper66 ROMs only.
- Added `customizer_app_version` to skchain-compatible level XML exports while
  keeping the legacy `app_version="1.1"` value for compatibility.
- Confirmed the MAGATU PNG-embedded stage XML and global settings JSON already
  carry `app_version`; this change keeps those paths versioned.

## v0.6.104 (2026-05-22) Add Codex workflow guard
- Added the project `AGENTS.md` guidance file for future Codex sessions.
- Documented the required edit workflow: create a `BUP/` backup before editing,
  then bump the application version and add a `CHANGELOG.md` entry before
  considering the work complete.

## v0.6.103 (2026-05-22) Keep slow Saramandor bullets through animation timer reuse
- Fixed the v0.6.102 slow-bullet fix after Mesen logging confirmed main-slot
  `+12` is the stock Bullet animation timer, not persistent storage.
- The `$866D` wrapper now recognizes a slow Bullet either by the fresh-spawn
  marker (`+12=$A5`) or by its already-overridden quarter-speed X velocity
  (`Xv=$10/$F0`) during later Bullet behavior reinitialization.
- Stopped depending on persistent marker state in `+12`; the slow-speed wrapper
  cave now spans `$BF00-$BF4F`, with unused filler moved to `$BF50`.

## v0.6.102 (2026-05-22) Keep slow Saramandor bullets slow after reinit
- Fixed Saramandor #2 speed 2 bullets potentially returning to normal speed
  after Bullet state0 changes behavior and the generic entity loop calls
  `$8AC0` a second time.
- The `$866D` wrapper now re-stores the slow marker after each slow Bullet
  speed init, so later Bullet reinitialization keeps the 1/4-speed override.
- The cave span remains bounded at `$BF00-$BF3F` and still ends before the
  next registered Saramandor variant cave at `$BF40`.

## v0.6.101 (2026-05-22) Clarify Salamander/Dragon reaction distance labels
- Re-checked `SUB_B1E9` against ROM bytes and the `SUB_A134` distance updater.
- Confirmed `$B1F3` / file `0x3203` is the X reaction threshold and `$B1FF` /
  file `0x320F` is the Y allowance threshold.
- Updated the game-behavior dialog wording from firing range to reaction
  distance and changed the preset labels to explicit pixel/tile values.

## v0.6.100 (2026-05-22) Keep Salamander distance tuning without legacy toggle
- Restored applying the Salamander/Dragon X/Y reaction distance controls.
- The removed legacy global fireball/despawn checkboxes remain gone; only the
  two distance bytes are written.
- Added a distance-only core helper so the UI no longer calls the old global
  Salamander fireball patch.

## v0.6.99 (2026-05-22) Remove legacy global Salamander bullet toggles
- Removed the obsolete global Salamander fireball enable/despawn checkboxes
  from the game behavior dialog.
- The current implementation uses Saramandor #2 enemy IDs instead of a global
  toggle, so the old two options were confusing and could write legacy patches.
- Global settings export/import now ignores those removed legacy keys.

## v0.6.98 (2026-05-22) Saramandor #2 slow marker survives until speed init
- Fixed the v0.6.97 slow-bullet runtime miss: main-slot +2 is overwritten by
  the entity loop before `$8AC0`, so the slow marker now uses main-slot +12.
- The `$866D` speed wrapper checks that one-shot marker before stock `$8AC0`
  clears +12, then overwrites only marked `$62/$63` bullets to quarter speed.
- The wrapper now preserves the original A/Y inputs before entering `$8AC0`;
  `$8AC0` depends on those registers, so touching them first breaks normal
  entity initialization.
- Normal Saramandor #2 speed 1 (`$5E/$5F`) and normal game Bullets remain
  unmarked and unchanged.

## v0.6.97 (2026-05-22) Saramandor #2 slow bullet speed fix
- Fixed Saramandor #2 speed 2 (`$62/$63`) bullets keeping normal Bullet speed.
- The patch now marks only the child sub-slot created by Saramandor #2 speed 2
  and wraps the stock entity speed initializer at `$866D`; after `$8AC0`
  loads the normal Bullet velocity, marked Bullet entities are overridden to
  quarter speed (`Xvel=$10/$F0`).
- Normal Bullets, Panel Monster Bullets, and Saramandor #2 speed 1 (`$5E/$5F`)
  remain unchanged.

## v0.6.96 (2026-05-22) Mirror picker applies enemy speed
- Fixed mirror enemy drag-and-drop so the current enemy speed radio button is
  applied when dropping an enemy into a mirror spawn slot.
- This makes Saramandor #2 speed 2 place `$62/$63` instead of leaving the slot
  as `$5E/$5F`, so the 1/4-speed Bullet variant is actually selected.

## v0.6.95 (2026-05-21) Saramandor #2 bullet variants
- Added always-on ROM patching for the unused Saramandor #2 IDs.
- `$5E/$5F` now spawn normal-speed Bullet entities, while `$62/$63` spawn
  1/4-speed Bullet entities. `$66/$67` remain reserved and unchanged.
- Added Saramandor #2 right/left entries to the monster picker and speed-radio
  mapping (`5E/62/66`, `5F/63/67`).
- Registered the Saramandor variant cave ranges with the Room Flag cave
  verifier so the patch coexists with hidden doors, dark rooms, breakable white
  walls, and gap-fix patches.

## v0.6.94 (2026-05-21) Restore room flags when loading ROMs
- Modified ROM loading now restores the Room Flag Table back into each
  `Level.room_flags`.
- Per-room settings such as hidden door, no B-fire, no A-stone, and dark room
  now reappear in the level settings checkboxes when reopening a patched ROM.
- Existing breakable white / invisible breakable cell restoration remains
  unchanged.

## v0.6.93 (2026-05-21) Global settings import/export
- Added JSON export/import buttons to the game behavior/global settings dialog.
- Export captures the current dialog values for shared ROM behavior settings:
  start/continue stage, warp feather, initial magic/lives, player speed,
  enemy behavior tweaks, clear-screen character, gap fix, and dark-room tempo.
- Import updates the dialog controls only. The ROM is changed after pressing
  `Apply` or `OK`, matching the rest of the dialog's workflow.

## v0.6.92 (2026-05-21) Top PNG rebuilds from pixels
- `Top PNG読込` now ignores same-name JSON sidecar layout data.
- The imported PNG is treated as the source of truth for the 256x64 top band:
  identical 8x8 tiles are shared, different 8x8 tiles are assigned separate
  title tile IDs, and the wide-title stream is rebuilt for that band.
- This avoids preserving old tile-sharing relationships when the PNG has been
  edited into a different picture.

## v0.6.91 (2026-05-21) Color Top PNG round-trip
- `Top PNG保存` now exports the title top band as color RGB PNG instead of
  collapsing it to 4-level grayscale.
- PNG import now maps each pixel back to the nearest valid color within that
  cell's actual title palette/attribute context, preserving multi-palette title
  art instead of flattening it globally.
- Verified color export/import logic by round-tripping the rendered title image
  back to all 960 tile pixel patterns with zero mismatches.

## v0.6.90 (2026-05-20) Title palette apply button
- Added `OK / Cancel / Apply` behavior to the title palette editor.
- `Apply` writes the selected title colors and refreshes the preview without
  closing the dialog.
- `Cancel` restores the colors from when the title palette editor was opened.

## v0.6.89 (2026-05-20) Title palette editor
- Added a `タイトル色...` button to the title migration dialog.
- The dialog edits the title BG palette bytes written to PPU `$3F00-$3F0F`
  through the ROM's title palette script.
- Only slots whose effective NES color number changes are written back, so
  equivalent existing bytes such as `$FF` are not unnecessarily normalized.

## v0.6.88 (2026-05-20) Title preview PPU attributes
- Reverted the incorrect `$24` clear-tile special case in the color title
  preview. `$24` is now rendered through the real CHR tile, attribute, and
  palette path like the PPU does.
- Added the JP title's later hardcoded attribute writes (`$2BEA`, `$2BF0-$2BF6`,
  `$2BF8-$2BFF`) to the preview attribute map so the preview matches the
  final title attribute state more closely.

## v0.6.87 (2026-05-20) Title preview backdrop color
- Fixed the color title preview so clear/background cells (`$24`) are rendered
  as the title backdrop instead of being treated as ordinary CHR tile art.
- The title attribute preview now starts from the original `$FF` attribute fill
  before applying the 21-byte title attribute table.

## v0.6.86 (2026-05-20) Color title preview
- The title migration dialog preview now renders with the title palette and
  attribute data instead of fixed grayscale.
- PNG export/import paths still use the existing 4-level grayscale renderer so
  editing round-trips are not changed by this preview-only improvement.

## v0.6.85 (2026-05-20) Top PNG sidecar layout
- `Top PNG保存` now uses a timestamped default filename and writes a same-name
  `.json` sidecar.
- `Top PNG読込` reads that sidecar when present and restores the title top-band
  layout before applying pixels.
- This fixes the fresh-JP `377 cells` vs imported arcade `386 cells` mismatch
  for Top PNG round-trips.

## v0.6.84 (2026-05-20) Remove duplicate Page position controls
- Removed the 52/53 Page position spin boxes from the game behavior dialog.
- The same JP ROM offsets (`0x35D9` / `0x35DD`) are already edited by the
  canvas meta-item drag path, so keeping both UIs could overwrite a dragged
  position with stale dialog values.
- `page_pos.py` remains available as the low-level ROM helper, but the user
  facing operation is now the canvas drag workflow.

## v0.6.83 (2026-05-20) Organize game behavior settings
- Reworked the game behavior dialog into category tabs:
  `基本`, `プレイヤー`, `敵・AI`, `画面・演出`, and `保守・特殊`.
- This is a UI organization change only. Patch logic and ROM formats are
  unchanged from v0.6.82.

## v0.6.82 (2026-05-20) Add initial lives setting
- Added a global initial Dana lives setting to the game behavior dialog.
- The patch changes only `$0452` by installing a small `$8BF4` routine and
  returns with `X=$03`, so the original `$042B` fire-scroll setup is not
  accidentally changed.
- The setting restores cleanly to the original `3` lives.

## v0.6.81 (2026-05-20) Polish initial magic UI
- Improved the initial magic controls in the game behavior dialog with clearer
  tooltips and help text.
- Changed the apply log messages for the initial magic patch to Japanese user
  facing text.
- No ROM patch format change from v0.6.80.

## v0.6.80 (2026-05-20) Preserve A in initial magic routine
- Fixed the side effect introduced by v0.6.79 where the score/status area
  became corrupted during the shrine intro.
- The `$9144` call site expects `A=0` immediately after returning and uses it
  to clear `$78-$7C`. The custom `$8BE2` routine now wraps its writes with
  `PHA/PLA`, preserving A while still leaving X untouched.
- v0.6.79 test ROMs with the non-preserving routine are accepted and rewritten
  to the safe 18-byte routine when the setting is applied again.

## v0.6.79 (2026-05-20) Move initial magic hook to new-game setup
- Fixed the initial magic patch again. The v0.6.78 `$B606` hook was based on
  a misread: `$B604` is the Solomon room / ending path, not normal stage
  startup.
- The patch now hooks CPU `$9144` (`STX $042B`) in the new-game setup and
  CPU `$C9E3` (`STX $042B`) in the later stage-start initializer. Both call
  the same `$8BE2` routine, which writes `$042B/$042E/$042F` and preserves X.
- ROMs that received the mistaken v0.6.78 `$B606` hook are cleaned up when the
  setting is applied or restored.

## v0.6.78 (2026-05-20) Fix initial magic late reset
- Fixed the initial magic patch not taking effect in actual stage startup.
- v0.6.77 hooked CPU `$C9E3`, but the later stage-build path at CPU `$B604`
  cleared `$042E/$042F` again. The patch now also replaces CPU `$B606`
  (`STA $042E`) with `JSR $8BE2` while leaving the following original
  `$B609: STA $042F` intact. The custom routine returns with `A=hi`, so the
  original `$B609` store writes the intended high byte again.
- The default setting restores both hooks and the `$8BE2` NOP band.

## v0.6.77 (2026-05-20) Add common initial magic settings
- Added a global "初期魔法" setting to the game behavior dialog.
- It controls the common stage-start magic max (`$042B`) and initial F/S
  stock (`$042E/$042F`) without adopting the old BESK three-row
  demo/start/continue expansion model.
- The patch uses the verified `$8BE2` NOP band and replaces only CPU `$C9E3`
  (`STX $042B`) with `JSR $8BE2`.  The `$042C/$042D` fire elapsed-counter
  clear remains intact, avoiding the unsafe "remove the whole zero-clear"
  shortcut.
- Default max `3` + empty stock restores the original hook and NOP band.

## v0.6.76 (2026-05-20) Allow zero-stage warp feather
- Extended the warp feather advance setting to `0-53`.
- `0` is encoded as operand `$FF`, which combines with the normal stage-clear
  `+1` and wraps to the same room. This allows a "take the feather and return
  to the same stage" behavior.

## v0.6.75 (2026-05-20) Add warp feather advance setting
- Added a global "ワープ羽" setting to the game behavior dialog.
- The setting edits the verified JP/JPN66 operand at CPU `$C6A0`
  (file `0x46B0`). The original operand `$05` combines with the normal
  stage-clear increment to produce the original 6-stage advance.
- The patch is signature-verified and can re-edit already changed values.

## v0.6.74 (2026-05-20) Add current RAM map
- Added `docs/ram_map_current.html`, a working RAM map for JP/customizer
  development.
- The map separates confirmed game RAM, current customizer reservations,
  unsafe regions, and small free candidates. It also documents the `$0460/$0461`
  sound RAM collision lesson and the current `$0778/$0779` reservation.

## v0.6.73 (2026-05-20) Fix constellation mirror placement
- Fixed selection horizontal/vertical flip for the normal level constellation
  background graphic. It is a 3x2 background object, so the editor now mirrors
  the 3-cell-wide top-left position by its center cell instead of treating the
  left cell as a single point.
- Other mirrored meta positions, items, enemies, demon mirrors, breakable white
  markers, and invisible breakable markers keep their existing behavior.

## v0.6.72 (2026-05-20) Improve title text overlay editing
- The title "追加文字..." dialog now reads the current overlay line back from
  the wide-title stream and uses it as the initial edit text, instead of always
  showing a hard-coded version string.
- Added support for comma, period, and double quote in title overlay text.
  These punctuation glyphs reuse the ROM's existing low font tiles and are
  copied into unused high CHR tile slots so the original title text routine
  remains untouched.
- Verified repeated edits with `VERSION 0.6.72, TEST` and
  `DARKNESS MIRROR "A"` while keeping the Room Flag bank0 cave band unchanged.

## v0.6.71 (2026-05-20) Add title text overlay through wide-title stream
- Added a title-screen "追加文字..." action that writes one centered line of
  A-Z / 0-9 / space text through the internal wide-title stream instead of
  modifying the original PUSH START / TECMO text routine.
- Copied the ROM font glyphs into unused high CHR tile IDs so the wide stream
  can draw them safely despite reserving `$00-$2F` as control bytes.
- Moved the wide-title bank1 workspace start from `0x80A8` to `0x80D0`,
  because mapper66 loader code actually occupies `0x8010-0x80C5`; verified
  clean JP expansion -> wide normalization -> text overlay without touching
  the Room Flag bank0 cave band.
- Updated the mapper66 ROM map and title manual notes to match the current
  JP-wide workflow.

## v0.6.70 (2026-05-20) Refresh F1 shortcut help
- Reworked the F1 shortcut/help dialog into clearer sections for basic keys,
  mouse actions, hover quick placement, item flags, selection editing, and file
  loading.
- Updated outdated entries for block quick placement, transparent breakable
  walls, full mirror behavior, and the current `SOLOMON_CUSTOMIZER.py` command
  line entry point.

## v0.6.69 (2026-05-20) Mirror level meta items
- Selection flip now also mirrors `level_meta_items` with ROM-backed position
  bytes, including Solomon's seal markers and JP Page of Time/Space markers.
- The flip updates both the in-memory marker position used by the editor and
  the underlying ROM position byte at each `rom_offset`.

## v0.6.68 (2026-05-20) Complete selection mirror behavior
- Extended selection horizontal/vertical flip to include stage meta positions:
  start, key, door, constellation panel, and demon mirrors.
- Horizontal flip now also swaps left/right enemy variants while preserving
  speed variants where applicable.
- Existing selection flip already handled terrain, items, enemies, breakable
  white markers, and invisible breakable markers; this makes full-room mirror
  editing practical by selecting the whole room and pressing `F`.

## v0.6.67 (2026-05-19) Harden invisible breakable wall placement
- Hardened block replacement so generic block changes clear stale invisible
  breakable markers before the UI deliberately re-adds them.
- Generated `ROM/TEST_InvisibleBreakable_JP_v1_editor_3_8.nes` and verified
  editor `(3,8)` stays visually empty (`$10`) while the mapper66 runtime table
  stores `$93` for `$90` breakable-block conversion.

## v0.6.66 (2026-05-19) Add invisible breakable wall marker
- Added an editor block type for invisible breakable walls: visually empty in
  the room map, but converted to normal breakable stone at runtime.
- Reused the v0.6.65 bank1 breakable-cell table and `$0760-$076F` runtime list,
  so white breakable walls and invisible breakable walls share the same safe
  storage path without adding new bank0 data.
- Persisted invisible breakable cells in XML and ROM read/write. The editor
  marks them with a yellow inner outline only in edit view.
- Updated placement guards so items and enemies cannot be placed on invisible
  breakable cells, matching their runtime solidity.

## v0.6.65 (2026-05-19) Move breakable white wall data out of bank0
- Moved breakable-white cell storage from the bank0 RoomFlag cave area to PRG
  bank1 expanded data at file `0xF860-0xFBAF` (`$F850-$FB9F` in bank1).
- Updated the mapper66 loader to copy the current room's 16-byte breakable-white
  list into RAM `$0760-$076F`; the NMI runtime now reads that RAM list and writes
  `$90` to the selected `$0304` cells after the room is drawn.
- Removed the old bank0 `0x3D00-0x40FF` breakable-white table and bit1 room flag,
  eliminating the collision with `gap_fix` at `0x4010-0x4097`.
- Verified compile, ROM generation, readback of editor `(3,8)` as runtime `$93`,
  and no overlap between `gap_fix` and breakable-white runtime.

## v0.6.64 (2026-05-19) Keep JP66 after US title import and gate breakable white per room
- Fixed region detection for JP mapper66 ROMs whose title/CHR was replaced
  from a US or patched US title ROM. The JP66 loader marker is now checked
  before the weaker US66 marker, so JP-expanded ROMs remain `JP66`.
- Added an internal room flag bit for breakable-white cells. The runtime
  breakable-white routine now exits immediately unless the current room has
  breakable-white cells, preventing accidental invisible `$90` blocks in rooms
  with empty breakable-white tables.
- Kept readback compatibility with the v0.6.63 unguarded breakable-white
  routine, so already-saved test ROMs can still restore their marked cells.

## v0.6.63 (2026-05-19) Fix breakable white wall boot regression
- Fixed a boot hang/green-screen regression from v0.6.62. The breakable-white
  runtime routine moved from `$BF50` to `$C0F0`, but the dark-stage NMI cave
  still called the old `$BF50` address.
- Updated the dark-stage cave to call `$C0F0`, so breakable-white processing
  runs from the new 16-cell-capable routine instead of jumping into table data.
- Regenerated `ROM/TEST_BreakableWhite_JP_v5_10cells_fixed.nes` for Mesen
  validation.

## v0.6.62 (2026-05-19) Expand breakable white wall capacity
- Increased breakable-white wall capacity from 8 to 16 cells per room.
- Reworked the runtime table format from count+cells to `$FF`-padded 16-byte
  room slots. This keeps the feature inside the existing bank0 reserved area
  without overlapping DoorCellTable/RoomFlagTable.
- Replaced the runtime routine with an indexed pointer reader, so rooms beyond
  the first page do not depend on an 8-bit absolute-X table assumption.
- Verified compile and generated `ROM/TEST_BreakableWhite_JP_v4_10cells.nes`
  with 10 cells in room 1.

## v0.6.61 (2026-05-19) Breakable white wall editor support
- Added a block picker entry for breakable white walls: the editor draws them
  as white walls but marks them with a green outline.
- Persisted breakable-white cells in XML and ROM save data. ROM output keeps
  the visual cell as white, then uses a one-shot NMI routine to change selected
  `$0304` cells to `$90` after the room is active.
- The implementation shares the existing room flag infrastructure and avoids
  the title wide bank0 cave collision. Current limit: 8 breakable-white cells
  per room.
- Verified compile and generated `ROM/TEST_BreakableWhite_JP_v3_editor_3_8.nes`.
  Mesen/user validation confirmed editor `(3,8)` must encode runtime grid `$93`
  (one row lower), so save/readback now converts between editor coordinates and
  `$0304` grid coordinates.
- Fixed JP66 ROM detection. Expanded JP test ROMs were previously detected as
  plain `JP` because only the US66 marker existed, so the app tried to expand
  them again on load. JP66 is now detected before the plain JP rule.

## v0.6.60 (2026-05-19) Dark stage tempo default 45/100
- Changed the global dark-stage tempo default to light 45 frames and dark 100
  frames. The stored ROM bytes are `[45, 145]` because the second byte is the
  total period (`light + dark`).
- Updated the hack dialog reset/default values and hint text to match.
- Verified `room_flags.get_tempo()` returns `(45, 100)` for an uninitialized
  tempo area and for `[45,145]`.

## v0.6.59 (2026-05-19) Fix Top PNG crop vertical offset
- Fixed the 256x64 Top PNG export/import band being one pixel too high. The
  title preview image has a one-pixel vertical display correction, but the Top
  PNG crop still used the pre-correction `y=48` start.
- Top PNG now uses display-corrected `y=49..112`, so the top blank row is gone
  and the bottom pixel row is no longer clipped.
- Verified by exporting `ROM/TEST_title_top_256x64_y49_v059.png`.

## v0.6.58 (2026-05-19) Include arcade title fixed banner strip
- Fixed the missing lower strip of the imported US arcade title banner. The
  patched US title writes 18 cells from code (`$CBC3`, PPU `$29A6`, tiles
  `$63-$74`) in addition to its two stream blocks.
- The US arcade import path now merges that fixed strip into block A before
  transcoding to the JP internal wide-title stream.
- Verified: patched US arcade import now writes 386 cells, including the full
  `$63-$74` strip, with exact grid match.

## v0.6.57 (2026-05-19) Import patched US arcade title ROMs correctly
- Fixed title import from the known "Title Screen v1-1 / arcade" patched US
  ROM. It is not a stock US title stream, so the stock decoder interpreted the
  title data as garbage and the preview became scrambled.
- Added detection for the patched US arcade title decoder at `$CBA6` and decode
  its two arcade-format streams at `$CD5F` and `$CDF5` before writing them into
  the JP internal wide-title bank1 streams.
- For that arcade source, copy the arcade attribute table `$CCAF -> $CD58` and
  apply the known JP-side color adjustments only when their signatures match.
- Verified: clean JP load -> auto mapper66/wide normalize -> import patched US
  arcade title gives 368 expected cells with exact grid match, keeps the target
  `JP66`, and does not touch the Room Flag bank0 cave.

## v0.6.56 (2026-05-19) Keep JP wide targets JP after US title import
- Fixed title import after a US title had already been imported. Copying the
  US title CHR into the JP wide-title ROM made the generic binary region
  detector report `US66`, so a later import from a JP raw ROM failed with
  `title import target must be JP/JP66 (target=US66)`.
- `title_screen._verify()` now treats the customizer's internal JP wide-title
  bootstrap signature as a stronger invariant than CHR-based region detection.
  A mapper66 ROM with that signature is classified as `JP66`.
- Verified sequence: clean JP load -> import clean US title -> import clean JP
  title again. Both imports now succeed and the target remains JP wide.

## v0.6.55 (2026-05-19) Fix JP load wide-normalization regression
- Fixed a regression in `MainWindow.load_rom()`: the mapper66 expansion call
  had been accidentally removed while cleaning a stale log block. Clean JP ROMs
  were therefore left as mapper3, and title import failed with
  "target ROM is not in the internal wide-title format".
- Restored the load sequence: save original raw ROM bytes, expand mapper3 JP
  ROMs to mapper66, then run JP wide-title normalization.
- Verified the user path: clean JP load -> `JP66` / wide title true -> import
  title from `Solomons Key (USA).zip` -> `US stock -> JP wide`, with the Room
  Flag bank0 cave untouched.

## v0.6.54 (2026-05-19) Design safety pass
- Removed a stale load-time log block that still said title wide
  normalization was disabled even though the current load path does normalize
  JP ROMs after mapper66 expansion.
- Disabled the old experimental `apply_wide_arcade_title()` API. That v9
  recipe writes to the bank0 Room Flag cave and is unsafe for the integrated
  customizer. The supported path is now `normalize_title_to_wide()` plus
  `transcode_title()`, which keeps the Room Flag cave untouched.
- Re-ran core smoke checks: JP mapper66 expansion, wide-title normalization,
  Room Flag cave band preservation, full Python compile, and offscreen
  MainWindow layout creation.

## v0.6.53 (2026-05-19) Layout restore guard
- Added guards for restored window size and splitter sizes. Saved settings from
  another monitor or an oversized desktop can no longer collapse the central
  level editor to an unusably small width.
- The restored window size is clamped to the available screen, with practical
  minimums. Splitter restore now falls back to safe panel widths if any panel
  is too small or the central editor is squeezed.
- Side panels now have maximum widths and the level editor has a minimum width,
  preventing long labels/tool groups from forcing the central editor down to a
  tiny strip.

## v0.6.52 (2026-05-19) Limited top-title PNG edit
- Added title-screen dialog buttons for the upper title graphic band:
  - `Top PNG保存...`: exports `x=0..255, y=48..111` as a 256x64 grayscale
    PNG/BMP.
  - `Top PNG読込...`: imports a 256x64 image into that same band and leaves
    the lower mountain/temple half untouched.
- The edit target is NES tile rows 6..13, which covers the title logo/banner
  area and avoids the lower compressed-looking scenery area.
- Verified an export/import round trip on a JP mapper66 wide-normalized ROM:
  title grid unchanged and `apply_title_image()` reported 0 CHR updates.

## v0.6.51 (2026-05-19) JP wide title import from user-owned ROM
- Public-build policy change: do not bundle the third-party US title-screen
  IPS or any ROM. Users can select a ROM they own. If they want the US title,
  they select a clean US ROM; if they privately have an IPS-patched US ROM,
  that ROM can be selected too.
- Reworked `title_screen.transcode_title()` for the mapper66 JP wide-title
  format. It no longer copies stock PRG title blocks into bank0. Instead it
  decodes the source title and re-encodes the title streams into the target
  JP wide-title bank1 workspace.
- Verified static imports:
  - clean US title -> JP wide: grid equality true, 377 cells.
  - user-owned US arcade-title ROM -> JP wide: grid equality true, 220 cells.
  - old JP v9 wide-title ROM -> JP wide: grid equality true, 386 cells.
- Safety check: Room Flag bank0 cave band `0x3BEE-0x4210` is untouched by
  title import. The target remains mapper66 wide-title after import.

## v0.6.50 (2026-05-19) JP wide title auto-normalize test path fix
- Fixed the root cause of `TEST_TitleWideTramp_JP_v2.nes` showing a broken
  stage 1: the test builder used `m66_expander.change_mapper()` directly.
  That creates the mapper66 shell but does not populate the fixed m66 level
  data area (`0xC010-0xF510`). Stage 1 therefore read zero-filled room data.
- Added `build_TitleWideTramp_JP_v3.py`, which uses the real application path:
  `load_all_levels()` -> `m66_expander.expand_rom()` -> `normalize_title_to_wide()`.
  Static checks confirm that m66 level data, CHR bank3, `$CD58`, and the Room
  Flag bank0 cave band are preserved.
- Re-enabled JP load-time title normalization after mapper66 expansion in
  `main_window.py`, with fail-safe logging if normalization is not applicable.
  The normalization runs after `expand_rom()`, not after bare `change_mapper()`.
- Generated `ROM/TEST_TitleWideTramp_JP_v3_expand.nes` for Mesen verification.

## v0.6.49 (2026-05-19) ★JP wide タイトル RAM-trampoline 機構 (再設計・実装)
- ★v0.6.48 で無効化した「読込時タイトル自動wide正規化」を、
  bank0 cave を一切使わない新機構で ★再実装 (US は対象外=JP専用)。
- 機構: ★RAM-trampoline + PRG bank1。decoder本体+blockA/B stream
  を mapper66 拡張の bank1 空き (file 0x80A8〜) に配置。$CC4F=
  bootstrap → RAM($03C0) の小型stub → PRG bank1 切替($BB86 bus
  競合・bank0=$FF不変ROM定数/bank1=予約$FF) → bank1 decoder →
  bank0 復帰 → RTS (純サブルーチン・スタック不可侵)。RAM 実行ゆえ
  PRG bank 切替の影響を受けない (定石)。
- ★twin-stub 案は破棄: bank1 の CPU $CC4F 像 = expander level
  data ゆえ同番地 stub 不可。skchain l_a1 も実は PRG 非切替
  (bank0[$8011]=$AD で $13 AND=$01) と判明。設計を Codex と
  往復レビュー (Codex_Exchange/) し RAM-trampoline に収束。
- ★Room Flag/暗闇/隠し扉/gap_fix と ★完全共存 (静的検証: 
  normalize↔Room Flag↔gap_fix 全順序で RoomFlagError 無し・
  Room Flag 占有帯 file 0x3BEE-0x4210 が素拡張とバイト完全一致)。
- 視覚完全同一: $CD58/palette/CHR bank3/色/bank0 cave ★非改変。
  round-trip 377セル一致で stock と同一描画を自己検証。
- 安全: 署名10点 (stock $CC4F/$CCB6/$CE08/$CEA3/$CD80 caller-B/
  SW両bank/bank1域全0/l_a2・vector/Room Flag帯非交差)、不一致は
  TitleScreenError で ★out 無改変中止 (フォールバック/部分書込禁止)。
- room_flags.py 台帳に bank1 widetitle・SW・RAM $03C0-$03DF を
  ★追記 (二重管理防止=前回事故の根因対策)。
- ★bugfix: bootstrap copy-loop の BPL 変位 0xF6→0xF7。v1 は分岐先が
  LDX 即値オペランドにずれループ後ゴミ実行→★起動不可 (ユーザー報告
  「うごかない」)。6502 実行シミュレーションで copy14B+JMP$03C0 実証。
- TEST ROM: v1 ROM/TEST_TitleWideTramp_JP_v1.nes (crc 3C4D3F8A=★BPL
  不具合・保持) / ★v2 ROM/TEST_TitleWideTramp_JP_v2.nes (crc
  7A32E62A=修正版)。恒久再現 build_TitleWideTramp_JP_v{1,2}.py。
- ★未完: 実機(Mesen)で v2 の trampoline 実行・タイトル表示・Room
  Flag 併用テストプレイ を要確認。確認が通って初めて load時自動
  正規化フックを再有効化する。
- 設計: docs/wide_title_trampoline_design.html / Codex_Exchange/。

## v0.6.48 (2026-05-18) ★リグレッション修正
- ★重大: v0.6.47 の読込時タイトル自動wide正規化が、bank0 cave
  ($BBDE-$C200) を ★Room Flag 機能群 (LOADER$BBE0/MAGICGATE
  $BC20/DOORPREDRAW$BC40/DARK$BC80/gap_fix) と奪い合い、
  clean JP 読込→テストプレイで RoomFlagError(別改造競合)発生。
  二重管理: room_flags.py の PRG cave台帳を確認せず「最初のEA
  列」を取った私の過失
- 修正: ★読込時の自動正規化を一時無効化 (load_rom のフックを
  no-op化)。clean JP 読込は従来どおり stock のまま=cave非妨害=
  ★テストプレイ復旧 (bank0 cave帯が plain拡張と完全一致を検証)
- ★訂正: 「Phase A 完了」は誤り。標準build_TitleWide_JP_v9 が
  実機OKだったのは Room Flag 未適用の単体ROMだったため。
  Customizer ではテストプレイが Room Flag を当てる→cave衝突。
  真の修正 = 山streamを ★bank0 cave不使用 で stock タイトル
  自身の領域 $CE08..$CF9A(402B) に in-place で収める
  (現エンコーダは stock JP で +9B 超過→エンコーダ圧縮改善が
  必要)。これが出来てから自動正規化 再有効化 & Phase B
- core の wide 系関数 / build script は保持 (再設計の土台)

## v0.6.47 (2026-05-18)
- ★ROM読込時 タイトル内部自動正規化 (方針: アプリ内部処理)
  - clean JP 読込 → (既存)mapper66拡張 → ★自動で当方wide形式へ
    正規化 (確認UIなし・外部ROM不要・ユーザー操作不要)。★見た目
    は元タイトルのまま (視覚同一: 描画377セル完全一致を round-
    trip 検証。プレビューも画素完全一致を確認)
  - 二重適用防止 (is_wide_normalized で判定→既wideはskip)。
    US/unknown/改造済/内部例外 は ★skip し ★読込は絶対壊さない
    (try/except・level編集等に影響なし)
  - decode_title_grid を wide 対応化 (正規化後 ROM のプレビュー
    が正しく表示)。core: is_wide_normalized 追加
  - 私の二転三転で混入した orphan ボタン(_on_wide_arcade 参照)を
    除去しダイアログ構築クラッシュを修正
  - ★未完(次スライス・正直申告): 「別ROMから移植」「PNGから
    取り込む」等はまだ stock 形式前提 → 正規化後(wide)ROMでは
    要 wide 対応化。US の wide 正規化も未実装(現状US読込はskip
    =stockのまま)。これらは継続作業

## v0.6.46 (2026-05-18)
- タイトル移植ダイアログから「広域arcadeタイトル移植(JP)」と
  「独自形式に正規化(見た目そのまま)」の2ボタン+ハンドラを
  ★削除(ユーザー判断)。「正規化」は押しても見た目不変=UXとして
  無意味/混乱、「広域arcade」はGUI露出が特殊(外部arcade ROM必須)
  - core の apply_wide_arcade_title / normalize_title_to_wide は
    ★検証済 Phase2 API として保持(解析R201/memory/build script
    群が参照・無害な不使用ライブラリ。GUI非露出)。広域arcade
    再現は build_TitleWide_JP_v9.py で恒久・独立に可能
  - 残ボタン: 画像保存 / PNG取込 / 別ROMから移植 / 取消 / OK等

## v0.6.45 (2026-05-18)
- 「独自形式に正規化(見た目そのまま)」を追加(タイトル移植ダイアログ)
  - ★JP/JP66専用・外部ROM不要・★明示操作(load時自動書換はしない=
    合意どおり)。この ROM 自身の stock タイトルを ★視覚を変えず
    当方wide形式へ正規化 → 以後アプリ内でタイトル編集が統一・容易
  - core.title_screen.normalize_title_to_wide。stock $CC4F で
    自タイトルを decode→当方arcade形式へ re-encode、decoder@
    $CC4F + block1@$CEA3 + block2@JP cave + $CCB6→cave。
    ★attribute($CD58)/palette/CHR は ★一切非改変=視覚同一
  - ★round-trip 自己検証: 正規化後の描画セルが元 stock と完全
    一致(clean JP 377セル一致)を確認、不一致なら中止(視覚が
    変わる改変は出さない・フォールバック禁止)
  - 全署名二重検証。clean JP/把握済stock JP のみ。改造済/別版/
    US/再適用 は安全に中止。拡張ROM(mapper66)対応(PRG offset
    不変・CHR非改変)
  - 実機確認用 TEST_TitleNorm_JP_v1.nes 生成(stockと同一表示か)

## v0.6.44 (2026-05-18)
- 「広域arcadeタイトル移植(JP)」を追加(タイトル移植ダイアログ)
  - ★JP ROM 専用。所有する arcade版バナー適用済 ROM から、
    広域タイトル(当方arcade形式 6502デコーダ@$CC4F + banner
    +$CBC3固定帯@$CEA3 + 山@JP cave + $CCB6 ptr→cave +
    CHR bank3 + $CD58←arcade$CCAF + 色4点)を移植
  - 実機検証済 recipe(解析 R201 / build_TitleWide_JP_v9.py)。
    core.title_screen.apply_wide_arcade_title。clean JP+arcade
    で ★CRC 0BF323D8 一致を smoke 検証(実機確認版とbyte等価)
  - 全パッチ ★before署名二重検証・不一致は中止(フォールバック
    禁止)。region gate=JP/JP66のみ(US$9604相当をJP同番地に
    当てると破壊ゆえ US 不可)。改造済/別版/非arcade source/
    再適用 は全て安全に中止
  - 拡張ROM(mapper66)対応: PRG patch は file offset 不変、
    CHR bank3 のみ動的算出
  - ★著作権: arcade の CHR/stream/attribute は ★ユーザー所有
    ROM から抽出(ツール非埋込)。埋め込みは当方デコーダ+色
    patch定数のみ
  - 再現用 build script: プロジェクト直下 build_TitleWide_JP_
    v1..v4.py / v9.py (診断・比較・恒久保存)

## v0.6.43 (2026-05-18)
- Phase2 基盤(UI未接続): arcade形式 広域タイトル stream の
  codec を core に追加 (decode_arcade_stream /
  encode_arcade_stream)。$30-$FF タイル規則・$2F終端を強制
  - 実 arcade ROM ストリームで ★往復完全一致を検証
    (135 writes ⇄ 再エンコード、PPUADDR $28C5..$2997、118タイル)
  - 設計/地固めは解析CHANGELOG R199 / memory に恒久化
    (cave撤回→in-place置換、JP hook $CB80、共有$CDFC/$CD76保全)

## v0.6.42 (2026-05-18)
- タイトル画像 位置補正の縦方向を修正: 「上1px→下」ではなく
  ★「下1px→上」が正しい (横8px→左は変更なし)。出力/取り込み
  両方の縦符号を反転。往復は画素完全一致を維持(0/61440・CHR0)

## v0.6.41 (2026-05-18)
- タイトル画像の位置補正 (出力/入力時のみ・ROM内部ロジック不変)
  - 出力(プレビュー/画像保存): 右8px を左へ巡回 + 上1px を
    下へ巡回 → 実画面と整列(バナー/神殿が中央に来る)
  - 取り込み(PNGから取り込む): 上記の逆を適用
  - export→import の往復は画素完全一致を維持(0/61440・CHR0)
  - ※デコード/移植/CHR再構築等の内部処理は一切変更なし

## v0.6.40 (2026-05-18)
- タイトル移植ダイアログ: 「PNGから取り込む」を追加(exportの逆)
  - 画像(PNG/BMP)を 256x240 / 4階調へ自動量子化し、各マスの
    8x8 を 2bpp 化して CHR bank3 を再構築
  - ★nametable(配置)は不変方式: RLE 再圧縮しないので圧縮枠
    超過の危険なし・往復が厳密一致(画素完全一致を検証)
  - core に apply_title_image / _encode_2bpp 追加。同一タイル
    番号を使う複数マスで絵が食い違う場合は最多パターン採用
    +個数を報告(export画像をそのまま編集すれば食い違い無)
  - 検証(描画目視+画素比較): JP export→import→再export が
    画素完全一致(0/61440)・CHR変化0。US画像→JP取り込みで
    「SOLOMON'S KEY」正しく描画
  - 自由レイアウト(配置自体を画像で変える)取り込みは RLE
    エンコーダが要るため将来拡張。v1 は絵の再構築(配置不変)

## v0.6.39 (2026-05-18)
- タイトル移植ダイアログ: デフォルト表示倍率を x3 → ★x2 に変更

## v0.6.38 (2026-05-18)
- タイトル移植ダイアログ: プレビューを ★実タイトル画面の合成
  表示に変更 (従来は CHR 素タイル並びだった)
  - core に decode_title_grid 追加: $CC4F デコーダを 6502 命令
    忠実に再現 (PPUADDR の ROR キャリーまで) し nametable を復元
  - CHR bank3 上位256タイル + 暗背景4階調で 256x240 合成。
    開いた瞬間に「今読み込んでいる ROM のタイトル画面」が
    そのまま見える。移植後は結果が即プレビュー反映
  - 画像保存も実タイトル 256x240 を出力
  - 検証: JP=「ソロモンの鍵」/ US=「SOLOMON'S KEY」/ US→JP
    移植後=JP に SOLOMON'S KEY が正しく合成 (バラバラ解消) を
    描画目視で確認。各 377 セル(=144+233)完全一致
  - ※色は未確定ゆえ白黒4階調 (形は正確、色精緻化は後日)

## v0.6.37 (2026-05-18)
- 「タイトル移植 (US↔JP)」: 配置も含む完全移植に進化(解析 R198)
  - タイトル= RLE 圧縮ピースの集合と解明。デコーダ $CC4F(JP)/
    $CBA6(US) は同一エンジン → ★ピース単位 verbatim コピーで
    US↔JP 相互移植 (コードは一切改変しない)
  - 移植ピース: nametable(配置 402B) + attribute(色区分 21B) +
    CHR bank3(絵 8192B)。JP/US でピース長が完全同一ゆえ安全
  - 「バラバラになる」を解消: 絵だけでなく配置(nametable)も
    各版の対応位置へ移すため正しく表示される
  - core に _TITLE_PIECES(JP/US offset表) + transcode_title 追加。
    リージョン自動判定・CRC不要・位置+署名二重検証・長さ不一致は
    中止(フォールバック禁止)
  - ダイアログのボタンを「別ROMからタイトルを移植」に更新
  - ※色(パレット)は v1 では移植先のまま (配置・絵は移植済、
    パレット片が散在し全特定が未完のため色精緻化は後日)
  - 解析知見は asm $CC4F 注記 / 解析CHANGELOG R198 /
    memory に恒久保存 (前回のタイトルメモ紛失の再発防止)

## v0.6.36 (2026-05-18)
- 「タイトルグラフィック移植」に方針変更・簡素化(編集ツール)
  - タイトル画像= CHR bank3 (8KB) を別 ROM から ★まるごと
    取り込む単純ブロックコピーに一本化。IPS でも CRC 一致
    要求でもない (既知ブロックcopyゆえ CRC は無関係)
  - JP/US 自動判定。CHR は両版同 offset(0xE010、本アプリ拡張
    ROM では 0x16010 を動的算出)ゆえ ★US↔JP どちらの向きも可
  - 配置/色 (PRG 側 nametable/attribute/palette) は各版のまま
    = 将来拡張 (今回は画像のみ)。core に import_chr_bank3 追加
  - UI 簡素化: 旧「別ROMから差替(PRG込)」「IPS+原本差替」を
    撤去し「別ROMからタイトル画像を取り込む」1本に。位置+署名
    二重検証で両 ROM 確認、不一致は中止(フォールバック禁止)
  - プレビュー(グレー4階調)/画像保存(PNG/BMP)/取り消しは継続
  - 解析 R197: 既存タイトル系 IPS は US 版専用(JPに当てると
    タイトル描画コード破壊で起動不可)。本機能は IPS を使わず
    CHR ブロックコピーゆえ region 非依存で安全

## v0.6.35 (2026-05-18)
- 「タイトル画面 抽出/差替」を追加(編集ツール)
  - タイトルのロゴ絵(CHR bank3, 512タイル)をグレー4階調で
    プレビュー / 128x256 PNG・BMP で保存
  - 「別ROMから差し替え」: 所有する別 ROM(.nes/.zip)の
    タイトル領域(CHR bank3 + 描画/nametable/attr/palette)を複写
    (例: 所有 US 版から英語ロゴを移植)
  - 「IPS+原本ROMから差替」: 所有の未改造 ROM に .ips を当て
    そのタイトルだけ取り込む安全二段方式
  - core/title_screen.py 新規 / core/ips.py に apply_ips_patch 追加
    / ui/title_screen_dialog.py 新規
  - ★著作権配慮: 画像も IPS の中身もツールに埋め込まない。
    ユーザー所有 ROM からの抽出/差替/適用のみ
  - ★読込時の mapper66 自動拡張に対応: CHR/タイトル位置を iNES
    ヘッダから動的算出し生/拡張どちらでも正しい位置を扱う。
    raw用 IPS の現ROM直接適用(破損経路)は二段方式で排除
  - 位置+署名 二重検証 / 両ROM一致時のみ差替 / 不一致は中止
    (フォールバック禁止・JP/US 専用)。解析 R196
  - ※実機確認推奨。色精密描画・別region描画コード差替は今後

## v0.6.34 (2026-05-18)
- クリア画面メッセージ編集: 「字数」列を追加し入力中の文字数を
  リアルタイム表示(現在 / 最大)。上限到達=赤・空=灰で視認性UP

## v0.6.33 (2026-05-18)
- 「クリア画面メッセージ編集」を追加(編集ツール)
  - おめでとう画面3行(THANK YOU DANA / YOU RELEASED THIS ROOM /
    TRY NEXT ROOM)を編集。R135/R194確定の PPU script を ★同字数
    置換(安全方式)。英大文字A-Z+スペース、原作と同字数まで
    (超過不可・不足はスペース詰め)
  - core/clear_message.py 新規 + ui/clear_message_dialog.py 新規
  - 位置+署名(各行ヘッダ3byte+終端$00+現tile妥当) 二重検証。
    不一致は中止(US版/拡張別配置/改造/破損=自動安全停止、JP前提)
  - 「原作に戻す」/OK/キャンセル/適用。ヘッダ・終端は不変で安全

## v0.6.32 (2026-05-18)
- Page面対応ラベル訂正(ユーザー100%確定): skc_config.xml の
  level_meta_item を **面52=Page of Space / 面53=Page of Time** に
  (旧ラベルは逆だった。JP/US66 両方)。page_pos/HackDialogの呼称
  (52=空間/53=時)は元から正しく整合。asm/解析CHANGELOG R190 記録

## v0.6.31 (2026-05-18)
- ゲーム挙動改造に「呪文(Page)の出現位置」を追加
  - 52面 空間の呪文 / 53面 時の呪文 を単純X/Yで変更(ROM直接書換)
  - core/page_pos.py 新規: R188/R189確定の特殊処理スクリプト
    LDX #$XX オペランド (file 0x35D9/0x35DD) を書換
  - 位置+シグネチャ ダブル検証(SIG_OFF基準、item$21=$21含む
    不変パターン)。不一致は例外で中止(フォールバック禁止)。
    US/US66 はoffset未トレース→シグネチャ不一致で自動無効化
  - 範囲ガード(grid内 X0-15/Y0-12)。原作値=52面(7,2)/53面(7,9)
  - キャンバスのPageマーカードラッグ(v0.6.30)と同一ROM箇所、併用可

## v0.6.30 (2026-05-18)
- Page of Time/Space (item$21) を決め打ち→★実ROM読みに変更
  - skc_config.xml level_meta_item no=12/13 (JP): position直書きを
    やめ offset 化。$B5C9=file 0x35d9(面52)/$B5CD=file 0x35dd
    (面53)=R188特殊処理スクリプトの LDX #$XX オペランドを読む
  - 効果: 改造ROMでも正しい位置を表示(ハードコード排除)＋
    rom_offset≥0 になり★ドラッグ移動可(書戻し=LDXオペランド
    書換=実機R188機構で実際に面内Page位置が動く。round-trip検証済)
  - US/US66 は当該offset未トレースゆえ従来 position 据置
    (既存 Solomon's seal meta と同じ region 分割方式・JP優先)

## v0.6.29 (2026-05-18)
- ★アイテム名を単一ソース化 (2重管理禁止) — 0x21修正が全UIに
  伝播しなかった根本原因を解消
  - 正本 = skc_config.xml item_definitions (cfg.item_desc) のみ
  - element_picker.ITEMS_LIST / stats_dialog.IMPORTANT_ITEMS を
    ★コード一覧のみ(どれを/順序)に変更。名前は保持しない
  - 名前解決は item_name(code, config) 1関数に集約 (ピッカー本体/
    ボーナスパネル/レベル設定数字キー/全レベル統計 すべて経由)
  - 効果: 今後アイテム名は skc_config.xml 1箇所修正で全UI反映
  - 回帰確認: ITEMS_LIST全46件が item_desc と一致・敵0x21無事
  - 注: ENEMIES_LIST(敵名)は同型の2重管理だが今回スコープ外(別途)

## v0.6.28 (2026-05-18)
- アイテム名訂正(ユーザー確定): skc_config.xml の `0x21` を
  "Egyptian Head" → **"Page of Time / Space"**(0x31 は
  "Egyptian Head" のまま確定)。config自身の level_meta_item
  (Page of Time/Space を面52/53に配置, animation=30)とも整合
  - 注: stats_dialog.py IMPORTANT_ITEMS の 0x21 ハードコードは
    別系統で未変更(指示「ここだけ・まず」に従い flag のみ)

## v0.6.27 (2026-05-18)
- キャンバスのホバー情報(ステータスバー)に★アイテム番号を表示
  - `アイテム:0xXX 名前[タグ]` 形式。base コード(item_desc準拠)を併記
  - 隠し/ブロック内など flag 付きは `0xXX(raw 0xYY)` で実バイトも併記

## v0.6.26 (2026-05-18)
- 左パネルを2列化(縦長を圧縮)
  - ファイル: 「改造ROMとして保存」「IPSパッチ出力」を横2列に
  - 編集ツール: 7ボタン+レベルクリアを 4行×2列グリッドに
    (列幅均等)。機能・接続・ツールチップは不変

## v0.6.25 (2026-05-18)
- ★暗闇面バグ修正: 妖精取得音($0F)が無限ループする副作用を解消
  - 原因: room_flags の ROOMFLAGS/暗闇フェーズカウンタが $0460/$0461
    に在ったが、ここはサウンドドライバ ch0 状態RAM($0456+$10*N の
    ch0 +$0A/+$0B)。暗闇面で毎NMI $0461 を踏み、数フレーム継続する
    妖精音の再生状態を壊して終われなくなっていた(実機 PC=$F2F7 で
    サウンドが $0461 を書込むのを確認)
  - 対策: ROOMFLAGS=$0778 / 暗闇フェーズ=$0779 へ移設(LOADER/
    MAGICGATE/DOORPREDRAW/DARK 全cave)。$0778/$0779 は entity 21slot
    終端 $0722 の後ろ かつ ramfree3_probe 285秒沈黙の二重安全域
    (実ROM $B328/$B33D ポインタ表で 21slot/$057F-$0722 を接地確認)
  - 隠し扉/B火球禁止/A換石禁止/暗闇 すべて同一移設で継続動作
  - 確認ROM: ROM/TEST_DarkFix_v1.nes (stage1&3 暗闇)
  - ★再発防止: room_flags.py 冒頭に「CUSTOM RAM RESERVE 予約台帳」を
    新設(現割当/禁止域/新規RAM手順)。今後 常駐RAMは台帳を見て追記
    してから使う運用に(毎回ゼロ探索を禁止)。memory にも横断記録

## v0.6.24 (2026-05-18)
- 全レベル統計に3列追加: 「タイル」(tileset_no)/「時間減少」
  (time_decrease_rate)/「敵寿命」(spawn_enemy_lifetime)。
  レベル設定パネルと同一データ源、敵数の右に配置・中央寄せ
- 内部改善: 列インデックスをCOLUMNSのヘッダ名から解決する方式に
  変更(列追加・並べ替えで他処理が壊れないよう堅牢化)

## v0.6.23 (2026-05-18)
- 全レベル統計「敵種類」列を2列に分離 (すっきり表示)
  - 「配置敵」= 面に配置された敵 (実数 ×N)
  - 「ミラー敵」= デーモンミラーから出る敵 (種類のみ presence=1、
    無スケジュールのミラーは除外)
  - CSV出力も配置敵/ミラー敵を別カラムで出力

## v0.6.22 (2026-05-18)
- 全レベル統計「敵種類」: デーモンミラーから出る敵も集計対象に
  - 配置敵に加え、各ミラーの敵セットを読み出して加算
  - 出現数は不明なため presence=1 (基底名で重複排除し各 +1)
  - ★スケジュール(出現タイミング)に1つもチェックが無いミラーは
    実際には出ないので除外 (先頭2tickのゲーム無視分を考慮)
  - 読出経路は main_window._sync_enemy_codes_from_rom /
    MirrorDialog._read_schedule と同一 (m66 layout、rom を受領)

## v0.6.21 (2026-05-18)
- 全レベル統計「敵種類」: 方向/速度違いを同一モンスターとして合算
  - グループキー = enemy_desc の基底名(括弧 "(...)" 以降と末尾
    " #N" を除去)。代表 element_no のスプライトを表示し ×N で合計
  - 例: `Gargoyle(right)×4 / Gargoyle(left)×4` → `Gargoyle×8`

## v0.6.20 (2026-05-18)
- 全レベル統計
  - 「重要アイテム」から Star Coin/Star Coin(W)/Bell/Diamond青/
    Diamond橙/Scroll の6件を除外 (13件に整理)
  - 「敵種類」列を新設: 出現する敵をスプライト表示(個数 ×N、
    hoverで名前内訳、CSV出力対応)。element_picker と同一ルート
    (config.enemy_map → TileRenderer)を流用

## v0.6.19 (2026-05-18)
- 全レベル統計の列構成見直し
  - 座標表示を全廃 (鍵・星座は名前/状態のみ)
  - ミラー列を撤去
  - 部屋フラグ4列を追加: A禁止 / B禁止 / 暗闇 / 隠し扉
    (lv.room_flags を参照、ONは ● + 薄い着色で一目表示)

## v0.6.18 (2026-05-18)
- 全レベル統計の表示改善
  - 「…」省略を全廃 (ElideNone)。鍵/ミラー/星座などを全文表示
    (改行を空白区切りの1行に統一して全部見えるように)
  - 列幅を保存/復元 (config: stats_dlg_col_w)。ヘッダで自由に
    リサイズ可、次回起動時に復元
  - ミラー列の「同位置かどうか」判定(●同位置マーク/着色)を撤去。
    位置を `m1 / m2` でそのまま表示

## v0.6.17 (2026-05-18)
- 全レベル統計の改善
  - ウィンドウのサイズ/位置を復元 (HackDialog と同一方式、
    config: stats_dlg_x/y/w/h)
  - 「重要アイテム」列はスプライトのみ表示に変更(文字を撤去)。
    内訳テキストは hover ツールチップ + CSV出力で保持(情報落ち無し)

## v0.6.16 (2026-05-18)
- 全レベル統計: 「重要アイテム」列をスプライト表示化
  - element_picker と同一の実証ルート (config.item_map →
    TileRenderer.get_tile_image) を流用してアイコン描画
  - 各アイテムを横並びサムネイル帯で表示。状態を枠色で表現
    (隠し=黄/ブロック内=緑/通常のみ=灰)、複数個は ×N
  - 元のテキスト内訳はツールチップ＋CSV出力用に保持(情報落ち無し)
  - 列幅はスプライト帯の最大幅に自動追従

## v0.6.15 (2026-05-18)
- デモ操作編集に編集上の注記を追加(簡潔): 最後に死ぬ動きは不要、
  34ステップ使い切りでデモ終了(ダイアログ説明＋MANUAL)

## v0.6.14 (2026-05-18)
- デモ操作編集 (attract mode 入力データ) を追加
  - 「デモ操作編集...」ボタン → 34ステップ固定の表で各ステップの
    入力(A/B/上下左右チェック)＋継続フレーム数を編集
  - 録画不要・原作の記述方式そのまま手入力。原作値を初期表示、
    「原作に戻す」で完全復元
  - $CF9A(wait)/$CFBC(joy) を同サイズ上書き(cave不要)。実効フレーム
    =wait+1 のため UI「Nフレーム」→ wait=N-1 で書込(asm R183)
  - Start/Selectはデモ中断判定のため選択不可(書込時$30強制除去)
  - core/demo_input.py 新規: 位置+署名($CBEC 26B)二重検証、不一致は
    DemoInputError で中止。デモ領域は US 再配置ゾーン=JP専用
    (US は署名不一致で安全中止)。標準/拡張ROM共通(自動テスト確認)
  - 確認ROM: ROM/TEST_DemoInput_v1.nes (右移動↔ジャンプの単純デモ)

## v0.6.13 (2026-05-18)
- ゲーム挙動改造ダイアログのサイズ/位置を記憶・復元
  - 閉じる時に サイズ/位置 を config に保存、次回開いた時に復元
  - 保存はコンフィグファイル (config/magatu_skc_config.json、
    レジストリ不使用)。hack_dlg_x/y/w/h を DEFAULT_CONFIG に追加
  - done() で OK/キャンセル/Esc/×閉じ すべての経路をカバー

## v0.6.12 (2026-05-18)
- ゲーム挙動改造ダイアログを 2列グリッド + 縦スクロール化
  - 項目増で縦長になり画面に収まらない問題を解消
  - グループ群を2列(均等)・縦スクロール領域に配置。冒頭説明は上、
    「オリジナル値に戻す」/OK/キャンセル/適用 は下に常時固定
  - 呼び出し側(各 layout.addWidget)は非改変、収集→組立方式で最小差分
  - 既定サイズ 940x720

## v0.6.11 (2026-05-17)
- 暗闇面 (明滅) を Room Flag Table に統合
  - レベル設定パネルに「この画面を暗闇にする (明滅・敵とDanaのみ)」
    追加 = $0428 部屋別 ON (bit3=BIT_DARK)。XML永続化済
  - ゲーム挙動改造に「暗闇テンポ (全体共通)」明/暗フレーム設定追加
    (60フレ≒1秒、既定 明30/暗180≒0.5s見え3s暗、必ず明から開始)
  - 実装: NMI PPUMASK 書込点 $8055 を独立フック (LOADER非改変)。
    DARK cave $BC80(53B): ROOMFLAGS bit3 & Dana実プレイ($057F>=$C0)
    の時だけ位相カウンタ $0461 を進め、テンポ $BCD0/$BCD1 で
    明($0301)/暗(PPUMASK bit3クリア=BG-off)を明滅。非該当は
    $0461=0 リセット→暗闇面は必ず明から。タイトル/紹介/クリア/
    非暗闇面は通常表示
  - $0461 は $0460(確定空き)隣接・asm 静的参照ゼロで確定使用
  - 位置+署名($804B)二重検証、暗闇面なし時は $8055 非フック
    (NMI完全無影響)。gap_fix と双方向 非破壊 共存(自動テスト確認)
  - core/room_flags.py 拡張 (BIT_DARK/DARK_CAVE/get_tempo/
    set_tempo)、main_window/hack_dialog UI、標準/拡張ROM共通
  - 実機実験: TEST_Dark_v1〜v4 で常時/明滅/ゲート確認済

## v0.6.10 (2026-05-17)
- ゲーム挙動改造に「原作バグ回避: 落下中の横穴侵入を安定化」を追加
  - ソロモンの鍵 積年の謎「落下中に左/右で横穴に入れる/入れないが
    運任せ」を機構解明(Mesen実機解析 asm R182)→回避。サブピクセル
    位相依存の col bit0(左)/bit1(右)を、横穴開口がある時だけ
    クリアして除去。通常の壁・歩行・着地は原作どおり(副作用なし、
    実機v8で確認済・左右対応・ソフトロック無し)
  - core/gap_fix.py 新規: 位置+署名($877F)二重検証、cave $C000
    (136B、room_flags予約帯内の非使用中間帯)、apply/restore、
    不一致は GapFixError で中止(フォールバック禁止)
  - room_flags._verify を更新し gap_fix cave span を許容→両機能を
    同時適用可能(拡張ROM・双方向で非破壊を自動テスト確認)
  - ゲーム挙動改造ダイアログに ON/OFF チェックボックス追加
  - 標準/拡張ROM共通(cave は bank0 verbatim 領域 file 0x4010)
  - 詳細 docs/gap_entry_mechanism.html / 解析 asm Round 182

## v0.6.9 (2026-05-17)
- 敵ドロップ編集: 効果名をユーザー実機知識で確定 + 未確定値を検証用に開放
  - $02 = 「マガドラの壺」/ $03 = 「ライラックの鐘」(ユーザー一次情報)
  - $01 / $07 を「未確定$01/$07」として選択可能に (実機確認用。
    $A373/$A41D の <8値経路に乗るのでテスト可。推測命名はしない)

## v0.6.8 (2026-05-17)
- 敵ドロップ効果表エディタ (グローバル) を新設
  - 「敵ドロップ編集...」ボタン → ダイアログで $C293 (10行×8枠) を
    効果コンボで編集。確率(枠数/8)と「その行を使う敵」を各行表示
  - 設定可能値は実機確定の14効果のみ (なし/特殊/$042B++/ファイア
    距離+/妖精予約/1UP/スコア+10〜+2000)。★$06=1UP であって鍵では
    ない (拾得AIのドロップ効果値であり通常item IDではない=R180)
  - 行は複数の敵グループで共有 (Neul各系/Saramandor+Dragon等)。
    UIに使用敵を明示
  - core/enemy_drop.py 新設: 位置+署名($C248/$C20F)ダブル検証、
    不一致/不正値は EnemyDropError で中止 (フォールバック禁止)、
    「原作に戻す」で完全復元。Codex ENEMY_DROP_PROBABILITY と
    相互検証一致
  - ROM直書き(既存挙動改造hackと同様、project非依存)。標準/拡張
    ROM共通 (table は bank0 verbatim 領域 file 0x4288/0x42A3)
  - 通常アイテムを落とさせるには別途 code-cave 変換層が必要(非対応)

## v0.6.7 (2026-05-17)
- アイテムピッカーの不足を解消 (Codex指摘13)
  - skc_config.xml <item_definitions> を正本に自前抽出した「配置可能」
    46件へ ITEMS_LIST を拡張 (旧36件)。追加=$05 Demon Mirror /
    $09・$0A・$0B・$0D・$0F modifiable系 / $21 Egyptian Head /
    $37 Mini-Dana / $38・$39 Tecmo Bunny の10件
  - glitch/garbage/Nothing 18件は配置で壊れ得るため従来どおり非表示
  - 抽出は PRG_SPRITE_USAGE_STATIC と相互検証 (gameplayキャラ群
    自前27 ⇔ Codex 27 で独立一致)。Codex compact を写さず自前再構成
  - 抽出物を output/PICKER_EXTRACT_20260517.txt/csv に保存
  - カテゴリ追加なし・既存 _populate_all パイプラインそのまま (UX非破壊)

## v0.6.6 (2026-05-17)
- Room Flag Table 拡張: A換石(石作成)禁止 (bit7) を追加
  - レベル設定パネルに「この画面でA換石(石作成)禁止」を追加。
    Bファイア禁止とは独立トグル (A+B 任意の組合せ可)
  - MAGICGATE cave 拡張 (21B→34B): SE id $08 で判別、
    bit2&$08==$13(B火球) / bit7&$08==$11(A換石) を各々却下
  - cave 再配置: MAGICGATE 34B 化に伴い DOORPREDRAW を $BC50 へ、
    $91CC フックを "20 50 BC" に変更 (非重複を自動検証)
  - ※A禁止は階段が作れず進行不能になり得る独立option (tooltip警告)
  - 自己テスト: A/B/A+B 全組合せで apply・冪等・原作復元 OK
  - 確認ROM: ROM/TEST_RoomFlag_AB.nes (ステージ1 A+B両禁止)

## v0.6.5 (2026-05-17)
- Room Flag Table 拡張 — ステップ2: 隠し扉 (bit0) を統合
  - レベル設定パネルに「この画面の扉を隠す (石を壊すと出現)」を追加
  - エディタの扉位置(fixed_door_pos)をそのまま使用。扉を動かせば追従
  - 統合cave化: $9071 LOADER を拡張し、面ロード後に
    DoorCellTable[room] が指す扉マス($0304+扉位置byte)へ隠しフラグ
    $40 を付与。$91CC(扉先行描画=R179確定)を新フックし、隠し扉の
    部屋は開始前画面の扉インジケータを抑止
  - cave 再配置 (LOADER 32B→$BBE0 / MAGICGATE→$BC20 /
    DOORPREDRAW→$BC40 / DoorCellTable→$C180 / RoomFlagTable→$C1C0)。
    全て bank0 空き $BBDE-$C1FF 内、非重複を自動検証
  - 原作復元はフック3点($9071/$8326/$91CC)のみ戻す死にコード方式
  - $91C1 署名検証を追加 (位置+署名トリプル検証)
  - 実機実証 TEST_HiddenDoor.nes と同一機構を部屋別へ一般化
  - 確認ROM: ROM/TEST_HiddenDoor_APP.nes (ステージ1隠し扉)

## v0.6.4 (2026-05-17)
- Room Flag Table 拡張 (画面ごとの挙動改造) を本編に統合 — ステップ1
  - レベル設定パネルに「この画面でBファイア禁止 (A換石は可)」を追加
  - 部屋ごと(レベル単位)に挙動フラグを設定。原作 level data は非破壊
  - ROM保存/テストプレイ時、bank0 のコードケーブへ自動注入
    ($9071 ローダフック + $C1C0 RoomFlagTable 64B + $0460 ROOMFLAGS
     + $8326 MAGICGATE。bit2=B火球禁止、A換石は常に可)
  - 位置+署名ダブル検証付き、不一致時 RoomFlagError で保存中止
    (フォールバック禁止)。全画面OFF=原作フック復元
  - 標準ROM/拡張ROM(mapper66)共通。expander が bank0 を verbatim
    コピーするため file offset 不変
  - プロジェクトXMLに room_flags 属性を永続化 (後方互換: 既定0)
  - 実機実証: TEST_RoomFlag_P1/P2 と同一 cave 構造。確認ROMで
    一面=B火球不可/A換石可、二面=復活 をユーザー実機確認済
  - core/room_flags.py 新規、level.py / xml_io.py / saver.py /
    ui/main_window.py 拡張
  - 隠し扉(bit0)は同 RoomFlagTable のステップ2で実装予定

## v0.6.3 (2026-05-16)
- 設定画面(F9)にフォント設定を実装
  - フォントファミリー(QFontComboBox)+「既定に戻す」ボタン
  - 太字(チェックボックス)
  - 既存のフォントサイズと合わせ MAGATU標準3項目が完成
  - 空ファミリー/サイズ0=アプリ標準。アプリ全体に即時反映
  - settings_dialog.py / main_window._apply_font_size 拡張
  - 「今後追加予定」からフォント設定を削除

## v0.6.2 (2026-05-16)
- ゲーム挙動改造に「デモプレイのステージ」追加
  - タイトル放置で流れるデモ(既定3面)を任意の面に変更
  - 3面以上のみ(内部のX連鎖制約。$CBC0 LDX operandを共用)
  - stage = operand + 2。OFFで3面復元、冪等
  - ROM解析(asm Round 113/135)で確定。デモコードはJP/US再配置
    ゾーン($C400-$CFFF)のため位置はJP/US個別特定
    (JP file 0x4BD1 / US 0x4B20)。位置+シグネチャ ダブル検証
  - core/demo_stage_hack.py 新規、hack_dialog に項目追加
  - 確認ROM ROM/TEST_Demo_Stage6.nes
  - 副作用: $0433/$80/残機/$0452 連動するがデモ(attract)では無害

## v0.6.1 (2026-05-16)
- ゲーム挙動改造に「クリア画面のキャラ」追加
  - おめでとう画面(THANK YOU DANA)の左右2体を差し替え
  - プリセット: Fairy(原作)/Golem/Gargoyle速/Gargoyle遅/
    Demonhead/Saramandor (全て beh=/usr/bin/bash0 速度ゼロ=落下せず置物表示)
  - ROM解析(Round 110/128/131/132)で確定。type=0x0FBC /
    state base=0x0F6D。位置+シグネチャ ダブル検証、改造ROM再適用可
  - core/clearscreen_hack.py 新規、hack_dialog に項目追加
  - 確認ROM ROM/TEST_CS_Golem_v00.nes / TEST_CS_Gargoyle_v04.nes


## v0.6.0 (2026-05-16)
- スプライトビューアに「★ROMフレームデータ」モード追加(既定)
  - 検証済み $D0E8 機構(group表→metadata→frame data 3byte)で
    ROMから全1391フレームを直接抽出・16x16描画
  - NES 8x16スプライト方式(left=tile1/right=tile2)で本来の姿
  - CHRバンク/SPRパレット(attr&3自動)/拡大 切替
  - skc_config(tile_def約105)に依存しない=editor用configを
    壊さずビューアの抜けを構造的に解消(主人公死亡/しゃがみ等
    従来欠落フレームも表示)
  - ラベル gGGsSSfF (group/state/frame)
  - 検証用スタンドアロン 解析資料/gen_sprite_sample.py も同梱
  - キャラクターモードに「★ROM由来 全キャラ(組立16x16)」カテゴリ
    追加(既定): 全1391キャラを$D0E8由来で組み立て、CHRバンク自動
    補正+group意味名(妖精/Demonhead/Saramandor等)付きで表示。
    editor用 skc_config.xml は不変=編集機能無傷で組立表示を全網羅
  - [要Mesen] attr の palette/flip bit 正確な意味は未確定


## v0.5.0 (2026-05-16)
- スプライト/キャラクタービューア追加（読込専用）
  - **キャラクターモード**: skc_config のメタタイル定義で組み立てた
    実キャラを名前付き一覧（アイテム/敵/メタ/全メタタイル）。
    生8x8タイルでなく組み上がった姿で表示。tileset/拡大切替
  - **★全網羅カテゴリ**: 全 tile_def(105) × 全 tileset(15) = 1575枚
    をフィルタ無しで列挙（curated map に載らない物も漏れなく表示）。
    既定カテゴリに設定
  - tileset「全部(網羅)」+「背景不透明」追加: 透過/誤パレットで
    見えず抜けて見える問題を解消（不透明灰背景で必ず可視化）
  - **生CHRタイルモード**: CHR-ROM の 8x8 を素のまま一覧
    （バンク・パレット・拡大・グリッド線、上級者向け）
  - iNESヘッダからCHR位置自動算出（JP: 0x8010 / 2048タイル / 4バンク）
  - 拡張ROM(m66)はヘッダ不正時に残り全域をCHR扱いでフォールバック
  - 編集機能の左ペインに「スプライトビューア...」ボタン追加
  - ROM未読込時は無効、読込で有効化

## v0.4.6 (2026-05-16)
- ゴーレムグループに「歩行速度」「特攻速度」倍率を追加 (0.5〜3.0x)
  - Mesen実機ブレークポイント解析で真のレバーを特定（静的解析3連敗後）
  - 速度テーブル本体 $DB99 は JP/US 同一 file offset（再配置されない）
  - s1歩行 $DBC8/$DBCA, s1特攻 $DBD4/$DBD6, s0歩行 $DBD0/$DBD2
  - 歩行倍率はs0+s1両方、特攻倍率はs1に適用。1.0xで原作厳密復元
  - 実効上限±2.0px/f (V*8/256符号拡張の限界)
  - $40 (速度更新スキップマーカー) を逆引きから除外（敵停止バグ回避）
- 新モジュール `core/golem_speed.py`: 位置+シグネチャ ダブル検証
  - $DB99先頭8B シグネチャでJP/US判定（同一offset・一意確認済）
  - 速度→バイト逆引きは全256値スキャンで実効速度最近接（$40除外）
- 教訓: 過去3連敗の真因はGolem s0(type$70-73)を弄っていたが検証面のGolemは
  s1(type$74)で別speed-indexだったこと。Mesen実機解析(ユーザー操作)で解決

## v0.4.5 (2026-05-16)
- ゲーム挙動改造ダイアログに「ゴーレム」グループ追加
  - 「キビキビ動作」ON/OFFチェックボックス1個
  - ON=State遷移待ち4箇所($AD33/$AD41/$AD90/$AE0A)を$01に、OFF=原作復元
  - 実機検証で正常動作・劇的に機敏を確認
- 新モジュール `core/golem_hack.py`: 位置+シグネチャ ダブル検証
  - AI_GOLEM $AD11 dispatch シグネチャ(待ちバイト不含)でJP/US自動判定
  - US=JP+$140。検証失敗時 GolemHackError でパッチ中止
- 【重要】Golem 移動速度は $AD5F/$AD95/$AE0F の #$01 が速度値兼behaviorビット
  マスクのため変更不可($02で無限ループ)。Codex解析+ROMバイト検証で確定。
  速度UPは別アプローチ(speed-index表/速度表)が必要、別途調整予定

## v0.4.4 (2026-05-16)
- ゲーム挙動改造ダイアログに「パネルモンスター発射間隔」を追加
  - 秒指定スピンボックス (0.8〜4.5秒、0.1刻み) + ON/OFFチェック
  - OFFで原作(約3.47秒)復元
  - Codex解析+ROMバイト検証で確定: 周期=(しきい値$A57A+発射ディレイ$10)/60秒
  - 設定式 しきい値=round(秒*60)-16、安全下限$20でclamp
- 新モジュール `core/panel_monster_hack.py`: 位置+シグネチャ ダブル検証
  - threshold直後の安定領域でJP/US自動判定 (US=JP+$140, JSR先差で別sig)
  - 検証失敗時 PanelMonsterHackError でパッチ中止 (フォールバック禁止)
  - Panel Monster ($24-$27, AI $A54C) 専用、他AI非影響

## v0.4.3 (2026-05-16)
- サラマンダー火球化に「ダーナ被弾」を追加（実機検証で完成）
  - Codex解析+ROMバイト検証: ダーナ被弾判定 SUB_81B1 は status & $03 != 0 を除外
  - status $C6→$C0 (file 0x311A/$B10A): $C0&$03=0 で被弾有効化
  - $B0AC ORA #$02 → ORA #$00 (file 0x30BD/$B0AD): bit1再セット抑制で被弾を維持
  - これらを火球化ON時に必須セット、OFFで原作復元
  - US offset: status JP+$140=0x325A, ora02 JP+$140=0x31FD
- 【バグ修正】検証シグネチャ sig1 が status バイトを含んでいた問題
  - 火球化(status→$C0)するとsig1不一致でdetect_region失敗→復元不能だった
  - 改造対象を一切含まない安定領域へ変更 (JP $B0FE / US 同+$140、一意確認済)
- 確定改造7バイト: type$20 / dir$04 / despawn NOP / status$C0 / ORA#$00 / X$50 / Y$10

## v0.4.2 (2026-05-15)
- 【重要修正】サラマンダー改造の X/Y 距離しきい値が逆だったのを訂正
  - Codex解析 + SUB_A134 実コード検証で sub-slot[4]=Y距離 / sub-slot[5]=X距離 と判明
    (解析資料 Round 67 のコメントが X/Y 逆で誤っていた → asm も訂正)
  - SUB_B1E9 しきい値A ($B1F3 file 0x3203) = X距離ゲート (原作$14)
  - SUB_B1E9 しきい値B ($B1FF file 0x320F) = Y距離ゲート (原作$10)
  - `salamander_hack.py` の xdist/ydist offset を入替修正 (JP/US 両方)
  - 発射距離プリセット刷新: X=原作/4/5/6マス、Y=同高さ限定/やや甘い
  - 誤った $40 禁止チェック削除 (SUB_B1E9 に特別禁止値なし)
  - ⚠ SUB_B1E9 は Dragon State5 ($A669) も共有 → 距離変更は Dragon にも影響
    (サラマンダー専用化は専用routine差替が必要、将来課題)

## v0.4.1 (2026-05-15)
- ゲーム挙動改造ダイアログに「サラマンダー強化（火球発射化）」を追加
  - 火球発射化 ON/OFF（口から1マス火 → 水平に火球$20を発射）
  - 強制消滅除去 ON/OFF（弾が壁まで飛び続ける / 時間で消滅）
  - 発射距離X（原作=隣接 / 遠距離=最大約5マス）※非線形のため2択
  - 発射許容Y（標準 / 緩め）
  - OFF で全バイト原作復元
- 新モジュール `core/salamander_hack.py`: 位置 + シグネチャ ダブル検証方式
  - 安定シグネチャ2点（spawn部 $B107 + SUB_B1E9 $B1E9）で JP/US 自動判定
  - US版はサラマンダーが再配置ゾーン (JP +$140) のため別オフセットを内蔵
  - 検証失敗時は SalamanderHackError でパッチ中止（フォールバック禁止）
  - 実機検証済: type$04→$20 / 方向$05→$04 / despawn JSR→NOP / X距離 $10↔$FF

## v0.4.0 (2026-05-15)
- ゲーム挙動改造ダイアログに「ダーナ歩行速度」を追加
  - プリセット: 0.5x / 1.0x(原作) / 1.25x / 1.5x / 2.0x / 2.5x / 3.0x
  - 地上歩行・空中横移動の左右4方向すべてに適用 ($DBA6/$DBA8/$DBAA/$DBAC)
  - 原作 1.0x = 0.75 px/frame (実機検証済 R107)
- 新モジュール `core/walk_speed.py`: 位置 + シグネチャ ダブル検証方式
  - 速度テーブル先頭 ($DB99) の13バイトシグネチャで改造ROM/異版/破損を検出
  - 検証失敗時は WalkSpeedError でパッチ中止 (フォールバック禁止)
  - $40 (速度更新スキップマーカー) を使用値から除外
  - JP/US 共通アドレス (ゲーム本編領域なので両リージョン完全同一)

## v0.3.3 (2026-05-15)
- 対応リージョンを JP / US のみに整理（EU版は完全に非対応として明示）
  - `region.py`: EU専用エラーパス削除、対応外ROMは統一エラーメッセージへ
  - `special_process.py`: EU未確認コメント削除
  - `skc_config.xml`: `<region name="EU">` 削除、EU専用 offset 行削除、複合 region 属性から `EU` を除去（22箇所）
  - XML 構文・JP/US の参照は無変更（XML パース確認済み）

## v0.3.2 (2026-05-13)
- パレット編集ダイアログ: BGパレット(#0〜#3)にもプレビューアイコンを追加
  - BG#0=白壁, BG#1=茶ブロック, BG#2=ファイアジャー青, BG#3=ファイアジャーオレンジ
  - パレット色変更時にBGアイコンもリアルタイム再描画

## v0.3.1 (2026-05-13)
- ソロモンの紋章（六芒星）をキャンバス上でCtrl+ドラッグ移動可能に
  - MetaItemDefにrom_offsetを保持、ドラッグ終了時にROMへ書き戻し
  - 位置はROMから動的に読み込み（ステージ割り当ては固定）
- バグ修正: PNG埋め込みステージデータにミラー敵セットの実データが含まれていなかった
  - DemonMirrorにenemy_codesフィールド追加
  - エクスポート時: ROMからenemy_codesを取得してXMLに含める
  - インポート時: enemy_codesをDemonMirrorに復元しROMに書き戻す
  - これにより他のステージのミラー設定をPNG経由でインポートした時に敵セットも正しく反映される
- バグ修正: JP版拡張ROM(JP66)でソロモンの紋章がキャンバスに表示されなかった
  - config_loader._load_meta_items() のregionフィルタにbase_regionフォールバックが無かった

## v0.3.0 (2026-05-12)
- ピッカーを4カテゴリに分割: ブロック / キャラ / アイテム / モンスター
  - カテゴリラベル付きで視認性向上
  - スクロールエリア内に縦配置
  - カテゴリ間の排他選択（1つ選ぶと他カテゴリの選択が解除）
- ミラーのキャンバス表示を改善: 数字テキスト → 色枠（1=赤, 2=青）

## v0.2.9 (2026-05-12)
- ミラーダイアログ: ドロップスケジュール先頭2tickをグレーアウト
  - ゲーム側6502コードの初期化処理で先頭2tickが「処理済み」判定されスキップされる仕様
  - チェックボックスを無効化し、ツールチップで理由を表示
- ミラーダイアログから敵セット編集コードを完全削除（メインウィンドウに一本化）
- 特殊処理ビューアのサブルーチン注釈を追加・修正
  - $B4F4(JP)/$B924(US): 敵リスト1体目 落下死→妖精出現フラグ有効化
  - $B500(JP)/$B930(US): マイティボンジャック出現処理
  - 全既存エントリの説明文を改善
- 技術文書 (docs/rom_analysis.html): ドロップスケジュール デッドティック解析を追加
  - 全16パターンのビットマップ可視化
  - 6502スケジュール読み取りルーチン ($A0B0〜$A130) の逆アセンブル
  - デッドティック発生メカニズムの完全解明（$043C/$043E初期化問題）
  - 世界初文書化候補としてマーク

## v0.2.8 (2026-05-12)
- ゲーム挙動改造ダイアログの整理
  - BESK方式ステージセレクトを廃止（簡易3バイト方式に統一）
  - 開始ライフポイント変更機能を削除
  - ROM編集方針をMANUAL.mdに文書化（データ値書換えのみ、プログラム命令書換え極力回避）
- パレット編集の強化
  - パレットプリセット保存/読込機能（JSON形式）
  - スプライトパレットにキャラクター名ラベル追加（主人公/サラマンダー/ガーゴイル/ゴブリン）
  - スプライトパレット行にキャラクタープレビューアイコン表示
- hack_data.pyからBESK関連コード・開始ライフ関連を削除

## v0.2.7 (2026-05-12)
- ボーナスステージ(Level 51)テーブル編集ダイアログを実装（BESK hidden.cs互換）
  - 出現アイテム16種をコンボボックスで編集（アイコン付き）
  - 出現位置32箇所をX/Y座標スピンボックスで編集
  - OK/キャンセル/適用ボタン、リージョン別ROMアドレス対応
  - Level 51表示時のみ「ボーナスステージ編集...」ボタンが有効化
- Level 51表示時、ピッカー下部をボーナスアイテム16種パネルに切替
  - アイテムピッカーからD&Dでアイテムを直接入れ替え可能
  - 変更は即座にROMに反映、キャンバスも再描画
  - 他のレベルでは通常のお気に入りバーを表示

## v0.2.6 (2026-05-11)
- 星座とタイルセットの排他制御を実装（BESK互換）
  - 星座パネルがある場合: タイルセットは星座グループに強制決定、spinboxをグレーアウト
  - 星座パネルなしの場合: タイルセットは自由選択可
  - 星座選択時にタイルセットを連動更新（グループ0=tileset0, グループ1=tileset1, グループ2=tileset2）
  - タイルセット変更時の星座グループ連動も実装（C++ skchain互換、グループ内相対位置保持）

## v0.2.5 (2026-05-11)
- EU版ROM非対応を明確化
  - EU版を読み込んだ場合「ヨーロッパ版は非対応です」とエラー表示
  - リージョン判定を US / JP / US66(拡張) の3種に限定
  - EU関連のROMオフセット・パッチアドレスを削除

## v0.2.4 (2026-05-11)
- ROM拡張(mapper 66)のリージョン対応（JP版修正）
  - `change_mapper()` のパッチアドレスがUS版ハードコードだった問題を修正
  - JP版: NOP x3 → offset 6162、サブルーチン注入 → offset 6534（US比 delta -125）
  - サブルーチン1内の絶対アドレス($9A00)をリージョン別に動的計算
  - EU版は未対応（パッチアドレス特定が必要）

## v0.2.3 (2026-05-11)
- ボーナスステージ(51面)のアイテム表示に対応
  - ROM内の専用テーブル(位置32箇所 + アイテム16種)を読み込みキャンバスに描画
  - ROM 0x1955: アイテム出現位置テーブル(32byte)
  - ROM 0x1975: アイテムIDリスト(16byte)
  - サムネイル・PNGエクスポートにも反映

## v0.2.2 (2026-05-11)
- レベルビューに装飾ボーダー追加（上・下・左に壊せない白ブロック）
  - 実機と同様にレベルがブロック枠で囲まれた見た目に
  - 右辺は既存の16列目が担当、3辺を追加
  - ボーダー部分は編集不可（クリック・ホバー無反応）

## v0.2.1 (2026-05-11)
- Pキーでテストプレイ（エミュレータ起動）のショートカット追加
- F1キーマップにPキーの説明を追加
- XML・PNG出力先を `exports/ROM名_YYYYMMDD_HHMMSS/` フォルダに変更
  - XML出力時のファイルダイアログを廃止（即座に出力）
  - 出力先パスをスクリプト基準の絶対パスに修正（CWD依存を排除）
- F9設定画面にフォントサイズ設定を追加（0=デフォルト、「適用」で即時反映）
- レベル選択スピンボックスの上下矢印をサムネイル順に合わせて反転
- IPS出力: 原本ROM（市販吸出し）を毎回選択する方式に変更
  - 改造ROM→改造ROMの無意味な差分ではなく、ピュアな原本からの完全な差分を生成

## v0.2.0 (2026-05-11) ★ マイルストーン

### ドキュメント更新（バージョン据え置き）
- `MANUAL.md` を v0.2.0 仕様に更新
  - ショートカット (F1/Ctrl+F1/F9/F10/1-0キー) 補足
  - BROWN_WHITE 廃止の注記
  - 敵セクションに SP1/SP2/SP3・noslow 版の説明追加
  - ROM自動拡張・特殊処理ビューワ・パレット編集・テストプレイ・履歴セクション新規
  - 制限事項を最新状態に整理

### 区切り
- **コア機能完成版として v0.2.0 を確定**
- v0.1.x からの累積成果:
  - レベル編集（タイル/敵/アイテム/メタ/ミラー/星座）
  - ROM自動拡張 (mapper 3 → mapper 66)
  - パレット編集（NES 64色ピッカー）
  - 特殊処理ビューワ + Canvas上のマーカー表示（壊せる隠しブロック・トリガー・MBJ）
  - 全53レベルのSP解析（条件付きブロック・テーブル参照・分岐対応）
  - item_bitmasks サポート（Lv20 Bat Symbol・Lv30 Opal の一括配置）
  - noslowフラグ解析完了（ピッカー登録済み）
  - サムネイル付きレベル選択・お気に入りバー・パレット編集
  - テストプレイ連携・IPS出力
  - 改造ROM 10作品で動作検証済（skchain互換）
  - BROWN_WHITE廃止整理（実機で意味なしと確定）
- **検証済み互換性**: skchain v1.1 製の改造ROM全10作品で正常動作
- **今後の方針**: `docs/future_plan.html` 参照（v0.2.0以降のロードマップ）

### 今回の変更
- バージョン 0.1.99 → 0.2.0
- `docs/future_plan.html` を新規作成（特殊処理エディタの実装方針・残タスク）

## v0.1.99 (2026-05-11)

### 仕様変更（廃止）
- **BROWN_WHITE (壊せる白ブロック) を廃止**
  - ユーザー検証により実機で「壊せない白壁」と完全に同じ挙動と判明
  - 両ビットONでも brown bit による破壊判定は発動しない（白bitが優先）→ 冗長表現
  - 10作品の改造ROM(skchain製)でも誰一人使用していない死にスペック
- **変更内容**
  - `Level._walls_to_wall_type`: 両ビットON時 BROWN_WHITE → WHITE へ正規化
  - `LevelRenderer`: 青フィルター除去、WHITE と同等に描画
  - `stats_dialog`: 「壊白」列を削除（列インデックス前倒し）
  - `main_window`: ホバー表示の「壊せる白」表記を削除、m66展開後コメント整理
  - `element_picker`: 既に v0.1.x で削除済みのまま維持
  - 互換性: 過去データに BROWN_WHITE があっても WHITE として扱われる（情報落ち＝挙動上は等価）
- `docs/roadmap.html` 9-14 を WONTFIX に変更

## v0.1.98 (2026-05-11)

### 追加
- **ピッカーにnoslow版Neul/Ghost (0x40-0x4F) を追加**
  - ピッカー `ENEMIES_LIST` に Ghost(right/left, noslow)・Neul(up/down, noslow) 4種を追加
  - `ENEMY_SPEED_TABLE` も拡張: 0x40/0x42/0x44/0x46 をbase codeとして sp1/sp2 を選択可能に
  - 既存の通常版0x30-0x3F 4種と並んで合計8種選択可能（×sp1/sp2 = 実質16種）

## v0.1.97 (2026-05-11)

### ドキュメント
- **noslowフラグの正体を解明**
  - 0x40-0x4F の "noslow" 版 Neul/Ghost は「壁にぶつかって反転する時に減速しない」特性
  - 通常版 0x30-0x3F は壁反転時に一瞬減速、noslow版はトップスピードのまま反転（凶悪化）
  - 独立フラグではなく敵コード自体に埋め込み済み → ピッカーから直接選択可能（UI追加不要）
  - 出典: `solomon's_key_rom_map.html` L424
  - `docs/rom_analysis.html` の敵コード表を分割して説明追記
  - `docs/roadmap.html` 9-13 をDONEに変更

## v0.1.96 (2026-05-11)

### 修正
- **item_bitmasks 読み出しバグ修正**（Level 20/30 でアイテムが表示されない問題）
  - 拡張ROM変換後の `rom.data` を参照していたため bitmap バイトがゼロクリアされ取得失敗していた
  - `original_rom_data`（変換前バイト列）から bitmap を読むよう修正
  - JP ROM の region フィルタ修正: 拡張後 `JP66` でも XML 側 `region="JP"` にマッチするよう `base_region` で補助判定
  - 検証: US/JP どちらも Lv20=129個・Lv30=34個 の bit を正しく取得

## v0.1.95 (2026-05-11)

### 追加
- **item_bitmasks のサポート**（Level 20: Bat Symbol、Level 30: Opal の一括配置）
  - skchain と同じ仕組み: 24バイト (16×12 ビット) の bitmap で同種アイテムを多数配置
  - 標準ROMの容量節約のための仕組み（通常のアイテムストリームでは入りきらないため）
  - `SkcConfig` に `item_bitmasks` 属性を追加、XML から読み込み
  - `MainWindow._apply_item_bitmasks()` で ROM data の bitmap を解読し、各レベルの items に追加
- Level 20 に約 129個の Bat Symbol、Level 30 に約 34個の Opal が表示されるように
- JP/USA 両方対応（オフセットが異なるが XML の region 設定で自動切替）

## v0.1.94 (2026-05-11)

### 修正
- **MBJ 位置検出を X2 (内部状態用) から X1 (叩く場所 = 出現位置) に変更**
  - BESK のドキュメント参照: 「X1 = 叩く場所の座標 / X2 = 出現する場所の座標」
  - 実機検証では MBJ は X1 の位置に出現するため、X1 を使う
  - X1 は通常のアイテムバッファ形式 `y = (b >> 4) - 1` で復元できるシンプルな式
- ハードコードオーバーライドテーブルを撤廃、純粋な解析ロジックに戻した
- 検証:
  - Level 17 X1=$7E → (14, 6) ✓
  - Level 39 X1=$56 → (6, 4) ✓

## v0.1.93 (2026-05-11)

### 修正
- **MBJ位置をユーザー実機検証に基づくオーバーライドテーブルで指定**
  - `$91A3` で計算した座標が `$A2B8` 内の `STY $04` で再上書きされるため、簡単な式で復元不可能と判明
  - 実機検証ベースの対応表で固定:
    - $36 → (6, 4) (Level 39)
    - $6E → (14, 6) (Level 17)
  - 未知のバイト値は暫定計算式 (`y = high_nibble + 1`) でフォールバック

## v0.1.92 (2026-05-11)

### 修正
- **MBJ位置のデコード式が間違っていたのを修正**
  - $91A3 ルーチン (MBJ表示処理) を逆解析した結果、MBJ の位置バイトはアイテムバッファとは違うエンコーディングだった
  - アイテムバッファ: `y = (b >> 4) - 1` (基底 $0304+P 用)
  - **MBJ ($91A3経由)**: **`y = (b >> 4) + 1`** ← こちらが正しい
  - 修正結果:
    - Level 17: (14, 5) → **(14, 7)** に訂正
    - Level 39: (6, 2) → **(6, 4)** に訂正

## v0.1.91 (2026-05-11)

### 修正
- マイティボンジャック隠し配置の描画順を改善
  - 旧仕様: MBJスプライト(不透明) → 白壁(55%)上書き → 結果: 白く曇って MBJ が見えにくい
  - 新仕様: 既存白壁(不透明) → MBJスプライト(55%)上書き → 結果: 白壁の中に MBJ が透けて見える
  - その位置が白壁でない場合は白壁を下地として補完描画

## v0.1.90 (2026-05-11)

### 追加
- **マイティボンジャック（MBJ）出現位置を可視化** (Level 17, 39)
  - 検出パターン: `A9 XX 85 88 4C YY ZZ` (LDA #pos; STA $88; JMP $B500/B930)
  - JP: JMP $B500 / USA: JMP $B930 両方対応
- **描画**: MBJ スプライト (enemy 0x18) + 半透明白壁オーバーレイ + 黄色枠
  - 既存の隠しアイテム表現と同じスタイル
- 検出結果:
  - Level 17: (14, 5)
  - Level 39: (6, 2)

## v0.1.89 (2026-05-11)

### 追加
- **特殊処理トリガー検出**を実装（待機パターン認識）
  - `A5 7E C9 XX D0 -k` (LDA $7E; CMP #$XX; BNE) 検出
  - `A6 7E E0 XX D0 -k` (LDX $7E; CPX #$XX; BNE) 検出
  - トリガー位置 → 条件付き壊せる位置 の対応を抽出
- **マーカー種別を拡張**:
  - 緑実線: 即壊せる (無条件)
  - **緑点線: 条件付き壊せる**
  - **ピンク: トリガー位置（プレイヤーアクション待機点）**
- **トリガー→ターゲット間に点線**で対応関係を可視化
- 検証結果:
  - Level 49: (13,9)→(2,7), (7,4)→(5,5)
  - Level 50: (12,5)→(9,5)
  - Level 52, 53: (1,9)→(7,11)

## v0.1.88 (2026-05-11)

### ドキュメント
- `special_process.py` モジュールに BESK のパースアルゴリズム (SP1/SP2) との対応関係を明記
- BESK の SP1Check (位置テーブル経由配置) と等価な検出を実装済みであることを記載

## v0.1.87 (2026-05-11)

### 修正・追加
- **特殊処理マーカー検出を大幅強化** (Level 52 のユーザー報告 (6,3)(7,3)(8,3) が見落とされていたため)
  - **前方分岐 (BEQ/BNE/BPL/BMI/BCC/BCS) を追跡**: RTS の先にあるコードでも分岐で到達するなら検出
  - **範囲配置 (`STA $03YY,X`) を認識**: `LDX #N; ...; STA $03YY,X; DEX; BPL -k` パターン
  - **位置テーブル経由配置 (`LDY $XXXX,X; STA $0304,Y`) を認識**: テーブル先頭のRAMアドレスをROM変換して該当バイト列を読み取り、各 X について Y を取得して位置展開
- 検出範囲拡大: BinaryDistSpecial の長さ制限を撤廃、最大512バイトまで分岐追跡

### 検証結果（修正後の検出位置）
- Level 49: 14箇所（左列5+右列5+中央2+直接配置2）
- Level 50 SOLOMON: 4箇所
- Level 52, 53: 5箇所（うち (6,3)(7,3)(8,3) はユーザー報告と一致）

## v0.1.86 (2026-05-11)

### 変更
- 特殊処理マーカーから「強制白 (white_forced)」検出を廃止（既存白壁とノイズになるため）
- 「強制空 (empty_forced)」を黄→水色に変更
- 結果として2種類のみ: **緑=壊せるブロック / 水色=強制クリア**

## v0.1.85 (2026-05-11)

### 変更
- 特殊処理マーカーの「破/白/空」ラベルバッジを廃止、色枠のみ表示
  - 色で種類を区別: 緑=壊せる / 水色=強制白 / 黄=強制空

## v0.1.84 (2026-05-11)

### 追加
- **Level 50 SOLOMON の壊せる隠し壁などを編集画面で可視化**（Phase 1.5）
  - 表示オプションに「特殊処理マーカー表示」チェックボックス追加（デフォルトON）
  - レベルの特殊処理ROMコードから動的配置マスを自動抽出:
    - 緑[破] = 壊せるブロック (LDA #$90; STA $03XX)
    - 水色[白] = 強制白壁 (LDA #$F8; STA $03XX)
    - 黄[空] = 強制クリア (LDA #$10; STA $03XX)
  - 例: Level 50 SOLOMON の (7,1), (12,7), (3,3), (9,5), (10,5) 等が緑[破]として表示される
- 新機能: `special_process.find_marks()` / `find_marks_for_level()`
- 検出: `LDA #$XX` の直近 A 値を追跡しながら `STA $03YY` を解釈

## v0.1.83 (2026-05-11)

### 削除
- **エディタ画面の BROWN_WHITE 青フィルター描画を削除**
  - 「壊せる白壁」は実は特殊処理ROM側で実現されており、レベルデータの BROWN_WHITE は実ゲームで意味を持たない
  - 青フィルター表示はミスリーディングだったため廃止
  - BROWN_WHITE データは引き続き白として描画（区別なし）

## v0.1.82 (2026-05-11)

### 削除
- **「壊せる白ブロック (BROWN_WHITE)」をピッカーから削除**
  - 自動拡張ROM運用では普通の白ブロック (0xf8) に圧縮されるため、配置しても効果なし
  - 「白く見えて壊せる」効果は実は **Level 50 特殊処理ROM** 側で実現されている（レベルデータ機構ではない）
  - 既存データ (Level 41/47/48) の読込・表示は引き続き level_renderer 側で対応（青フィルター表示）

## v0.1.81 (2026-05-11)

### 修正
- **JP ROM 読込時に特殊処理ビューアが「未対応」表示になる**不具合修正
  - 原因: m66_expander が `rom.region = "US66"` をハードコードしていたため、JP源泉ROMでも `base_region()` が "US" を返していた
  - 修正: ソースリージョンに応じて `"US66"` / `"JP66"` / `"EU66"` に設定
  - `region.is_expanded()` / `base_region()` を新 region に対応
  - `Rom.is_expanded()` も汎用化（hardcoded "US66" → `region_mod.is_expanded()`）
- これで JP ROM の特殊処理ビューアが JP のテーブル位置 (0x3404) を参照するようになる

## v0.1.80 (2026-05-11)

### 追加
- **特殊処理ビューア (Phase 1, 読込専用)** を実装
  - 編集ツールに「特殊処理ビューア...」ボタン追加
  - 各レベルの ROM ハードコードルーチンを表示
    - 生バイト (アドレス付き)
    - 擬似アセンブラ（既知サブルーチンに日本語注釈）
  - 全53レベルの一覧 + サイズ別カテゴリ (empty / JMP only / 短い / 中 / ★大規模)
  - 対応リージョン: **JP (0x3404), USA (0x3834)** — EU は未対応
- BESK を逆コンパイルして得た解析データを実装に反映
- 新ファイル:
  - `magatu_skc/core/special_process.py` (ディスパッチ計算 + 6502長さ + 注釈)
  - `magatu_skc/ui/special_process_dialog.py` (ビューアUI)

### 注意
- Phase 1 は読込専用。編集は Phase 2 (プリセット投入) / Phase 4 (拡張ROM対応) で実装予定
- Phase 3 (自由バイト編集) は需要次第で後回し

## v0.1.79 (2026-05-11)

### 修正
- **壊せる白ブロック (BROWN_WHITE) がエディタに表示されない不具合**を修正
  - 原因: 自動拡張変換後の再パースで BROWN_WHITE が WHITE に変質していた
  - 通常ROMでは BROWN/WHITE のビットマップ独立で BROWN_WHITE 表現可能
  - 拡張ROM (mapper 66) は 1バイト/マスのグリッドフォーマットで `0x90`(brown)/`0xf8`(white) のみ
  - `save_level_m66` は BROWN_WHITE を `0xf8` (普通の白) として書き出すため、再パースで情報消失していた
  - 修正: 自動拡張変換後の再パースを廃止し、通常ROMから読んだ `levels` をそのまま使用
  - これによりエディタ上で BROWN_WHITE が青フィルター付きで正しく表示される
- 既知の制約: 改造ROM保存時、拡張形式に書き出す段階で BROWN_WHITE は普通の白 (0xf8) になる
  - skchain (C++) も同じ制約あり。拡張ROMフォーマットでの BROWN_WHITE 表現は未解明
  - 解析タスクとして 9-14 にロードマップ追加予定

## v0.1.78 (2026-05-11)

### 変更
- **敵スピードをフラグ化**（アイテムフラグ Hidden/InBlock と同形式の UI）
  - ピッカーに「敵スピード (対応する敵のみ)」の SP1 / SP2 / SP3 ラジオを追加
  - `ENEMIES_LIST` を sp1 ベースのみに整理（重複バリアント削除）
  - 敵配置時にベースコード + 選択中スピード → 実コードに変換
    - Demonhead/Saramandor: SP1/2/3 すべて対応
    - Dragon/Golem/Gargoyle/Fireball/Neul/Ghost: SP1/2 対応
    - Mighty Bomb Jack/Bullet/Panel Monster/Fairy/Flame: スピード無関係（無視）
  - スピード非対応 sp が選ばれた場合、一段下のスピードへフォールバック
- スポイト (Alt+Click) で敵を取った時、ベースコード+スピードを逆引きしてピッカーに反映

### 内部
- `element_picker.py` に `ENEMY_SPEED_TABLE`, `apply_enemy_speed()`, `base_code_from_actual()` を新設
- `ElementPicker.get_enemy_speed()` / `set_enemy_speed()` API追加
- バックアップ: `BUP/20260511_enemy_speed/`

## v0.1.77 (2026-05-11)

### 修正・追加
- ミラー詳細設定ダイアログの Phase 1 / Phase 2 のチェックボックス位置ずれを修正
  - ラベル幅を 110px に固定して桁を揃える
- 敵リスト (`ENEMIES_LIST`) に以下を追加:
  - **Fireball sp2** (0x2C-0x2F, 4方向)
  - **Demonhead sp2/sp3** (0x54-0x55, 0x58-0x59)
  - **Saramandor sp2/sp3** (0x60-0x61, 0x64-0x65)
  - **Dragon sp2** (0x6C-0x6D)
  - **Bullet** (0x20-0x23, 4方向)
- これによりピッカー・ミラー詳細設定の両方で選択可能に

## v0.1.76 (2026-05-11)

### 追加
- レベル画面のミラーアイコンに **番号ラベル ("1" / "2")** を重ね描き
  - 黒縁取り + 黄色文字で視認性確保
  - 「ミラー詳細設定」ダイアログのミラー1/ミラー2と対応がつくように

## v0.1.75 (2026-05-11)

### 追加
- **ミラー詳細設定ダイアログ** (Phase 2-4 / 2-5 / 4-7 を統合)
  - 「レベル設定」グループに「ミラー詳細設定...」ボタンを追加
  - 1ダイアログ内で 2ミラー分まとめて編集:
    - **出現タイミング**: 64ビット = Phase 1 (32) + Phase 2 ループ (32) のチェックボックス
    - **出現する敵**: 最大7体ぶんのコンボボックス（敵アイコン + 名前）
    - **クイック操作**: スケジュール全クリア/全ON、敵セットクリア
  - スポーン敵の生存時間 (Saramander/DemonHead 用 TTL) スピンボックス
- skchain 風 UI に寄せて 16進数を見ずに編集可能
- 拡張ROM (mapper 66) のレイアウトに直接読み書き

### 内部
- 新ファイル: `magatu_skc/ui/mirror_dialog.py`
- バックアップ: `BUP/20260511_mirror_dialog/`

## v0.1.74 (2026-05-11)

### 修正
- 敵配置上限の不整合を解消
  - `ENEMY_COUNT_MAX` を 16 → **15** に変更（拡張ROM運用に統一）
  - 旧仕様: 16体まで配置できるが保存時に SaveError、もしくは編集中に16体目以降がサイレント無視
  - 新仕様: 16体目を置こうとした時点でステータスバーに「敵は1レベル 15 体まで（拡張ROM形式の制限）」と表示
  - `Level.add_enemy` が bool を返すようになり、上限到達を呼出側で検知可能に
- アイテムは引き続き上限なし（マップ192マスが事実上の上限）

## v0.1.73 (2026-05-11)

### 修正
- パレット編集 Apply 後、エディタ画面の色がおかしくなる不具合を修正
  - 原因: ROMの 4バイト `[c1, c2, c3, separator]` をそのまま XML 形式に流していた
  - XML 形式は 3バイト `[c1, c2, c3]` で `SubPalette` が先頭に 0x0F (透明) を補完する仕組み
  - 4バイト渡すと色が1スロットずれて表示されていた
  - 修正: ROM の先頭3バイトのみを XML に流す
- ダイアログの「リセット」ボタンが現在のROM値に戻していた不具合を修正
  - 起動時のスナップショットを保存し、Apply済みでもそこに戻れるように

## v0.1.72 (2026-05-11)

### 追加
- パレット編集 Apply 後、エディタ画面に **リアルタイム反映**
  - ROM 0xED4 の 32バイトを `config.palettes` (XML由来の40パレット) に同期
  - 5グループ (red/cyan/purple/dgreen/gray) のうち:
    - BGパレット slot 0 はグループ固有なので red のみ更新
    - BGパレット slot 1/2、SPRパレット全色は全グループ共通として全部更新
  - `tile_renderer.clear_cache()` + `picker._populate_all()` + `_refresh_view()` で
    メイン画面・ピッカー両方を再描画
  - レベル選択サムネイルは手動再生成ボタンから更新可能

## v0.1.71 (2026-05-11)

### 追加
- **パレット編集機能** を新設（試作）
  - 編集ツール群に「パレット編集...」ボタンを追加
  - ROM offset `0xED4` の 32バイト = 8パレット (背景4 + スプライト4) を編集可能
  - 各パレット: 編集可能な色3スロット (4バイト目はセパレータ 0x0F/0x00 で維持)
  - NES 64色から色選択（4×16グリッドのカラーピッカー）
  - リセットボタンでダイアログ起動時の値に戻せる
  - 主人公の色は SPR #0〜#3 のいずれか（テストプレイで確認しながら特定）
- 新ファイル: `magatu_skc/ui/palette_dialog.py`

### 注意
- パレット変更は ROMバイトに直接書き込み、テストプレイ/保存で反映
- エディタ画面（マップ表示）のパレットは XML設定ベースなのでリアルタイム反映はされない

## v0.1.70 (2026-05-11)

### 追加
- **セッション操作ログ**を実装
  - 主要操作をメモリに蓄積し、アプリ終了時に `logs/session_YYYYMMDD_HHMMSS.log` へ保存
  - 記録対象:
    - セッション開始/終了
    - ROM読込（自動拡張変換の有無を含む）
    - ROM保存 / IPS保存 / XML出力(現在/全) / XML読込(現在/全)
    - 編集開始（クリーン→ダーティに変わった瞬間 + 対象レベル）
    - レベルクリア（モード別）
    - ゲーム挙動改造（HACK ダイアログでROMが変わったとき）
    - テストプレイ起動
    - 各種失敗時のエラー情報
  - 何も操作がないセッション（開始/終了のみ）はファイル出力しない
- 旧 ROADMAP 10-4「改造履歴ログ」を消化

### 内部
- `_session_log: list[str]`、`_log(msg)`、`_save_session_log()` を新設
- バックアップ: `BUP/20260511_session_log/`

## v0.1.69 (2026-05-11)

### 修正
- 自動拡張時の `Too many enemies in mirror enemy set 1 (42 >= 8)` エラー修正
  - 通常ROMのミラーデータはポインタテーブル経由（lo/hi 各17バイト → RAMアドレス → ROMオフセット）で読む構造だった
  - C++ `SKC_Config::get_offset_generic_data` を `_resolve_table_entry` として移植
  - `parse_drop_schedules_std` / `parse_enemy_sets_std` を書き直し

## v0.1.68 (2026-05-11)

### 追加
- **ROM読込時の自動拡張変換 (mapper 3 → 66)**
  - 通常ROMを読み込むと自動的に拡張ROM形式 (96KB, mapper 66) に変換される
  - 容量制約 (敵726バイト / アイテム1402バイト) が事実上無くなる（1レベル=256バイト固定 × 53レベル）
  - C++ skchain `Rom_expander.cpp` の `change_mapper / patch_mirror_*` を完全移植
  - `core/m66_expander.py` 新設
- **ROM情報表示**: 自動変換時に「⚙ 拡張ROMに自動変換 (mapper 66)」を表示
- **IPS出力を拡張ROMでも有効化**:
  - 旧仕様: 拡張ROMだとIPSボタン無効化
  - 新仕様: `original_rom_data` (変換前=通常ROM) を基準にIPS生成。配布の唯一の手段なので残す
  - `core/ips.py` の `create_ips_patch` をサイズ拡張対応に更新（modified が original より大きくてもOK）

### 内部
- `MainWindow.load_rom` で `m66_expander.expand_rom(rom, levels)` 呼び出し
- 変換後 `load_all_levels(rom)` で拡張ROM形式から再パース
- `_auto_expanded` フラグを保持
- バックアップ: `BUP/20260511_rom_expander/`

## v0.1.67 (2026-05-11)

### 修正
- テストプレイ時の例外（`SaveError` 等）を `QMessageBox` で表示するよう修正（無言クラッシュ防止）

## v0.1.66 (2026-05-11)

### 追加
- **エミュレータ連携 / テストプレイ機能**
  - F9設定画面に「外部連携 → エミュレータ」項目を追加（参照ボタンで.exe選択）
  - 左ペインに「▶ テストプレイ (現在レベル)」ボタンを追加
  - 動作:
    1. 現在の編集中レベル群をROMデータに反映
    2. ステージセレクトパッチを現在レベルに設定（BESK利用可ならBESK、不可なら簡易方式）
    3. 一時ROMを `%TEMP%/magatu_skc_testplay/testplay.nes` に書き出し
    4. 設定したエミュレータをそのROMを引数にして起動
  - rom.dataは作業後に元の状態に復元（テストプレイ用の改変は永続化しない）

## v0.1.65 (2026-05-11)

### 修正（D&D問題完全解決）
- お気に入りへのD&Dが効かない問題を最終解決:
  - **MainWindow**: 内部D&D(`PICKER_MIME`)を `dragEnterEvent` で accept するよう修正（旧: URL以外を ignore してウィンドウ侵入を阻止していた）
  - **ElementPicker**: 親ウィジェットでドロップを受けて、ドロップ位置がお気に入りバーの矩形内なら `FavoritesBar.handle_drop()` に手動振り分け
  - **DraggablePickerList**: `startDrag()` + `mouseMoveEvent` の二重経路で確実にドラッグ起動
  - **FavoritesBar**: 各スロットに明示的な `setSizeHint` でアイコン全体を表示
- 高さを 86px → 92px に微調整（2行 + マージン）

### 内部
- デバッグ用 print を削除

## v0.1.60 (2026-05-11)

### 修正（再）
- お気に入りへのD&Dが効かない不具合を修正
  - 前回(v0.1.58)のマウスイベントオーバーライド方式は、QAbstractItemViewの選択処理と競合して動作しなかった
  - **`startDrag()` メソッドのオーバーライド方式に変更**
    - `setDragEnabled(True)` + `setDragDropMode(DragOnly)` でフレームワークの標準ドラッグ起動経路を使う
    - フレームワークが startDrag を呼んだ瞬間にカスタムMIMEで `QDrag.exec_()`
  - これがQtの正規ルートで最も確実

## v0.1.59 (2026-05-11)

### 追加
- **ウィンドウ状態の保存・復元**
  - 終了時に以下を `magatu_skc_config.json` に保存:
    - ウィンドウ位置 (X, Y)
    - ウィンドウサイズ (幅, 高さ)
    - 最大化状態
    - 4ペインのスプリッター幅 (`[LEFT, CENTER, PICKER, LEVEL_SELECT]`)
  - 起動時に自動復元
  - 画面構成変更時（モニター切替等）に画面外に出ないよう簡易チェックあり
  - 最大化状態のサイズは記録せず、復元時は最大化フラグのみ反映

## v0.1.58 (2026-05-11)

### 修正
- お気に入りへのD&Dが効かない不具合を修正
  - QListWidget標準のstartDragはモード設定との相互作用で発動しないことがある
  - 明示的にマウスイベントを処理してQDragを発動する `DraggablePickerList` を新設
  - カスタムMIMEタイプ `application/x-magatu-picker-item` で確実に受信側へ伝達

## v0.1.57 (2026-05-11)

### 追加
- **ピッカーお気に入り機能**を新設（10スロット）
  - メイングリッドからD&Dで登録
  - **1〜9 / 0 キーでクイック選択**（旧「ホバー位置に配置」機能を置換）
  - スロット選択時、メインリスト側も同期して選択状態に
  - **お気に入りはJSON永続化** (`magatu_skc_config.json`)
  - 選択中スロットで Del/BackSpace → スロットクリア
  - タイルセット変更時はお気に入りアイコンも自動更新

### 変更
- ピッカーのアイコン間スペースを大幅圧縮（`setGridSize` で密に配置）
- メイングリッドはドラッグソース（DragOnly）として動作
- お気に入りバーは2行分の固定高さ

### 内部
- `FavoritesBar`(QListWidget) クラスを `element_picker.py` に新設
- `ElementPicker.trigger_favorite_key(n)`, `get_favorites()`, `restore_favorites()` API追加
- `core/config.py` の `DEFAULT_CONFIG` に `picker_favorites` 追加

## v0.1.56 (2026-05-11)

### 変更
- **要素ピッカーを統合グリッド化**
  - ブロック / メタ（鍵・扉・スタート・ミラー）/ アイテム / 敵を **1つのIconModeグリッド**にまとめて表示
  - 各アイコンは画像のみ・テキストなし、説明はマウスホバーの**ツールチップ**
  - 「編集対象」ラジオボタン群（ブロック/アイテム/敵/鍵扉スタート）を**廃止**
    - アイコンクリックで自動的にモードが切り替わる（UserRoleに `(mode, value)` を格納）
  - **配置フラグ（通常/隠し/ブロック内）は常時表示**に変更（旧: アイテムモード時のみ）
  - 一覧性が大幅向上（モード切替なしで全要素にアクセス可能）

### 内部
- `ElementPicker._populate_all()` 新設、旧 `_populate_blocks/items/enemies/meta` と `_on_mode_changed` を統合
- `_set_picker_value(value, mode=...)` でモード指定検索可能に（スポイト機能用）

## v0.1.55 (2026-05-11)

### 変更
- レベル選択リストを **画像のみ表示**（IconMode + ラップ）に変更
  - 「Level N」のテキストラベルは削除
  - レベル番号はマウスホバーで **ツールチップ表示**
  - グリッド状に並ぶので一覧性アップ

## v0.1.54 (2026-05-11)

### 追加
- **サムネイル付きレベル選択ペイン**を実装（Phase 4-8）
  - レイアウト変更: `LEFT（諸々）| CENTER（メイン）| ピッカー | レベル選択（最右）`
  - レベル選択リスト（QListWidget）の各行にレベル画像のサムネイル（160×120px）を表示
  - レベル選択グループは左ペインから最右ペインへ移動
  - サムネイル生成タイミング:
    - **ROM読込時**: 全53レベルを一括生成（`_generate_all_thumbnails`）
    - **レベル切替時**: 「離れる側」のサムネだけ更新（`_refresh_thumbnail`）
    - **手動再生成ボタン**: 念のため全レベル再生成可能
  - 編集中の現在レベルはリアルタイム更新せず、別レベルへ移動した瞬間に反映 → 軽量

### 変更
- スプリッタを3ペイン → 4ペイン構成に変更（初期サイズ `[280, 700, 250, 220]`）

## v0.1.53 (2026-05-11)

### 追加
- **F9 設定画面**を新規実装（Phase 3-1 部分着手）
  - 設定ダイアログ `magatu_skc/ui/settings_dialog.py`
  - 設定永続化 `magatu_skc/core/config.py` → `magatu_skc_config.json`
  - 現状の設定項目:
    - **未保存マーク**（プリセット: ●/*/[未保存]/♦/•/✱/[edited] + 自由入力）
  - OK / Apply / Cancel ボタン（Applyは閉じずに即時反映）
  - 今後追加予定: フォント、アイコンパス、通知音、クラウドバックアップ等（プレースホルダ表示）

## v0.1.52 (2026-05-11)

### 追加
- **未保存マーク + 終了時確認** (Phase 4-14)
  - 編集すると **タイトルバーに ● マーク** が表示される
  - ROM/IPS/XML 保存で消える
  - ROM ロード時もリセット（読込直後はクリーン）
  - **ウィンドウ閉じる時、未保存があれば確認ダイアログ**
    - 「本当に終了しますか？」 Yes/No、デフォルトはNo
  - ゲーム挙動改造ダイアログでROMバイト変更があった場合も dirty 化

## v0.1.51 (2026-05-11)

### 修正
- Ctrl+ドラッグでブロックを移動した際、通り過ぎたタイルの既存ブロックが消える不具合を修正
  - 原因: 「現在の描画位置」をNONEで上書きしてから新位置に置く実装で、通り過ぎたタイルが他のブロック持ちだった場合にそれを破壊していた
  - 修正: 各タイルの「元の壁」を保存し、ドラッグが離れる際に復元するように変更

## v0.1.50 (2026-05-11)

### 追加
- **選択範囲のドラッグ移動**
  - 選択範囲の内側で **Ctrl+左ドラッグ** すると、範囲全体（ブロック/アイテム/敵）が追従移動
  - 元の位置は空白に、新位置に貼り直し
  - 選択枠も新位置に同期
  - Undo は1ストロークで1エントリ
- 内部リファクタ: `_build_clipboard_from_selection` / `_paste_clipboard_at` を切り出し、
  コピペとドラッグ移動でロジック共有

## v0.1.49 (2026-05-11)

### 追加
- **選択範囲操作 一式実装**
  - **Ctrl+C** コピー（ブロック/アイテム/敵 まとめて）
  - **Ctrl+V** ペースト（選択範囲の左上 or ホバー位置 を起点）
  - **Ctrl+X** 切り取り（コピー+削除）
  - **Delete** 範囲一括削除（範囲なしならホバー位置の従来動作）
  - **F** 左右反転
  - **Shift+F** 上下反転
  - 全操作 Undo 対応
  - F1ヘルプも更新

## v0.1.48 (2026-05-11)

### 修正
- 範囲選択中とリリース後にマウスを動かすと選択枠が消えるバグを修正
  - 原因: `_on_tile_hovered` 内の軽量再描画で `selection_rect` を渡していなかった
  - これでドラッグ中の選択範囲も滑らかに更新される

## v0.1.47 (2026-05-11)

### 追加
- **Shift+左ドラッグで矩形範囲選択**
  - 黄色の点線枠＋半透明黄色フィルで範囲をハイライト
  - ステータスバーに範囲座標と幅×高さ表示
  - **Esc** で選択解除
  - 通常の左クリックでも選択解除
  - 選択範囲を使った操作（コピー/ペースト/反転/削除等）は今後追加予定

## v0.1.46 (2026-05-11)

### 追加
- **Ctrl+ドラッグでブロックも移動可能に**（実装漏れ対応）
  - 茶ブロック / 白ブロック / 壊せる白ブロックを掴んでドラッグ可能
  - 移動優先順: アイテム > 敵 > メタ要素 > **ブロック**（最後）
  - 元位置は移動開始時に空白化、ドラッグ中は新位置に追従
  - Undoで一発戻し

## v0.1.45 (2026-05-11)

### 追加
- 🎯 **スポイト機能** (Alt+左クリック)
  - その位置の要素をピッカーに取り込む
  - 優先順: 敵 > アイテム > メタ要素 > ブロック
  - アイテムの場合はフラグ（隠し/in_block）も自動反映
  - 編集モードも該当モードへ自動切替
  - ステータスバーで通知

## v0.1.44 (2026-05-10)

### 修正
- **スタート位置・扉位置にブロックが置けてしまう不具合を修正**
  - スタート位置にブロック → 主人公が埋まってクリア不能
  - 扉位置にブロック → 出られなくてクリア不能
  - どちらも配置を拒否、ステータスバーで通知
- 配置レギュレーションマトリックス（rom_analysis.html）も同期更新

## v0.1.43 (2026-05-10)

### 追加
- **ピッカー選択中のアイコンをマウスカーソル形状に表示**
  - レベルビュー上のカーソルが、ピッカーで選んだアイテム/敵/ブロックの絵に変わる
  - 32x32 ピクセル、ホットスポット中央
  - 選択変更で即座にカーソル更新
  - レベル切替時もタイルセット色に追従して再描画

## v0.1.42 (2026-05-10)

### 追加
- **ステータスバーにマウス下部のタイル情報を常時表示**
  - 右側固定エリアに専用ラベル
  - 表示内容:
    - 座標 `(x, y)`
    - ブロック種類（茶/白/壊せる白）
    - アイテム名 + フラグ（隠し/in_block）
    - 敵名（同位置複数なら全部）
    - メタ要素（スタート/鍵/扉/ミラー1/ミラー2）
    - 星座
  - ステータスバー左の `showMessage()` とは独立（操作通知に上書きされない）

## v0.1.41 (2026-05-10)

### 追加
- **ドラッグ塗り** & **ドラッグ消し**
  - **左ボタン押しっぱなし＋移動** = 連続配置（ドラッグ塗り）
  - **右ボタン押しっぱなし＋移動** = 連続削除（ドラッグ消し）
  - 既存の Ctrl+左ドラッグ（要素移動）と共存
- Undo は1回のドラッグ全体で**1エントリ**にまとめる
  - 押下時に1回だけスナップショット → Ctrl+Zで全戻し
  - `_suppress_next_undo` フラグで実装
- F1ヘルプにドラッグ系の操作を追記

## v0.1.40 (2026-05-10)

### 追加
- アイテムフラグ切替のショートカット追加
  - **N**: 通常 (0x00)
  - **H**: 隠し (0x40)
  - **B**: ブロック内 (0x80)
  - 押下するとピッカーのラジオボタンが切替＋ステータスバー表示
- F1ヘルプにフラグ切替も追記

## v0.1.39 (2026-05-10)

### 追加
- **キーボードショートカットでホバー位置にクイック編集**
  - **Delete / Backspace**: ホバー位置の要素削除
  - **0-9 数字キー**: モードに応じて配置
    - BLOCK: 0=消去 / 1=茶 / 2=白 / 3=壊せる白
    - ITEM: 1-9 = ITEMS_LIST 先頭から N 番目のアイテム / 0 = 既存削除
    - ENEMY: 1-9 = ENEMIES_LIST 先頭から N 番目の敵 / 0 = 既存削除
    - META: 1=スタート 2=鍵 3=扉 4=ミラー1 5=ミラー2
  - 配置時はピッカーの選択も自動で同期（次回の左クリック配置にも反映）
- F1ヘルプにキーバインド一覧を追記

## v0.1.38 (2026-05-10)

### 追加
- ブロック × アイテムの配置レギュレーション実装
  - **白ブロック (壊せない) 内アイテム**: **禁止**（取れなくなるため）
    - アイテム配置時に白ブロックタイル → 拒否
    - 白ブロック配置時にアイテムあり → 拒否
  - **茶ブロック / 壊せる白ブロック + アイテム**: **自動で in_block フラグ付与**
    - アイテム配置時に該当タイル → ピッカー選択に関わらず in_block 強制
    - ブロック配置時にアイテムあり → 既存アイテムを in_block に自動変換
    - ステータスバーで通知
  - 壊せる白ブロックは原作には無いが、ユーザーがアイテム配置できるように許可

## v0.1.37 (2026-05-10)

### 追加
- **敵 × ブロック同位置の配置禁止**（原作USA ROMで事実上皆無の組み合わせ）
  - 敵がいる位置にブロック（茶/白/壊せる白）配置 → ステータスバー警告 + 配置キャンセル
  - ブロックがある位置に敵を配置 → 同様に警告 + キャンセル
  - 「消去」（ブロック削除）は許可（敵は残る）
  - 誤って積んだUndo履歴も自動で取り消し

## v0.1.36 (2026-05-10)

### 修正
- 16列目非表示時の左右非対称な見た目を改善
  - 右に黒列がある分、**左にも同じ幅の黒パディング**を追加（17列幅のキャンバス）
  - クリック・ホバー座標は LevelView 側で自動補正（画像幅から推定）
  - これでプレイ画面のように上下中央＋左右対称に表示される

## v0.1.35 (2026-05-10)

### 修正
- 16列目を非表示にしてもマウスホバーで再描画した瞬間に復活する不具合を修正
  - ホバー再描画ルートが `show_col15` を渡していなかった

## v0.1.34 (2026-05-10)

### 追加
- **16列目（右端列）の表示・編集ON/OFFオプション**
  - 表示オプションに「16列目を表示・編集」チェックボックス追加
  - **デフォルトOFF**（実画面に出ない列なので非表示）
  - OFF時: 16列目は黒で塗りつぶし、クリック編集も無効化
  - ON時: 通常表示・編集可能

## v0.1.33 (2026-05-10)

### 修正
- **コンティニュー上限のアドレスが USA で間違っていた不具合を修正**
  - 旧: USA/JP 共通で 0x4A58 を使用 → USAでは別のデータ位置（値=2）を読んでた
  - 新: リージョン別アドレス
    - USA: ROM 0x4958 (LDX #$28; CPX $0428; BCS のパターンで特定)
    - JP : ROM 0x4A58
  - `get_continue_max_offset(region)` ヘルパー関数を追加

### 検証
- USA ROM ロード時: コンティニュー上限が「41」と正しく表示される
- JP ROM ロード時: 同じく「41」

## v0.1.32 (2026-05-10)

### 変更
- ゲーム挙動改造ダイアログを**完全に数字入力のみ**に整理
  - 「おおよそ」プレビューラベル削除
  - 開始ステージ: 「面目」サフィックス削除、純粋な数字 1〜53
  - コンティニュー上限: ドロップダウンを廃止、**スピンボックス 1〜53** に統一
  - 補足説明文（「※ステージ1を選べば〜」等）も削除
  - 全項目が **数字スピンボックスだけ** のシンプル構成

## v0.1.31 (2026-05-10)

### 変更
- アイコン読込優先順を **PNG → ICO** に変更
  - `assets/dana.png` (64×64) が存在すれば優先使用
  - ICO は低解像度だったため、ユーザーが任意のPNGに差し替え可能
  - `assets/` フォルダにファイル名 `dana.png` で置けば自動採用

## v0.1.30 (2026-05-10)

### 追加
- **アプリアイコンを設定** — `assets/dana.ico`
  - JP ROM の CHR-ROM からダーナ（主人公）スプライトを直接抽出
  - 16×16〜256×256 の複数解像度を埋込
  - タスクバー・ウィンドウタイトル両方に反映（マルチモニタ対策の AppUserModelID も既設定済）
  - ライセンス的にクリーン（自分のROMから自分で抽出した素材）

## v0.1.29 (2026-05-10)

### 変更
- 開始LIFE スピンボックスの範囲を **0〜9 → 1〜9** に変更（即死 0 を除外）
- 表示を「約 N 万」形式に変更（実機検証で約+5,000のオフセットがあるため）
  - 例: 設定 7 → 「約 75,000」
- USA/JP 実機検証で動作確認済み

## v0.1.28 (2026-05-10)

### 変更
- **開始ライフポイントの実装を全面刷新**
  - 旧: Game Genie由来のプリセット（3000/40000/330000）— 不正確、JPで効かない
  - 新: **10000の位 (0〜9) のスピンボックス** — 1バイト改造で確実に動作
  - **リージョン別アドレスに対応**:
    - USA: ROM 0x1835 (LDX #$01 即値)
    - JP: ROM 0x17B8 (USA 等価位置)
  - 設定値プレビュー表示（例: 9 → 「90,000」）
  - 0 を選ぶと「0（即死）」表示で警告
- 古い hack_data.py の `starting_life_points` (誤った 0x1839) は廃止し、
  リージョン別の `starting_life_10k_digit_USA` / `_JP` に置換
- `get_life_10k_offset(region)` ヘルパー関数を追加

### 検証
- USA ROMで KAXOOEVE 改造値（0x8C → ライフ40,000）と一致するメカニズムを解析
- 10000の位の値（ROM 0x1835/0x17B8）がそのままLIFE表示の万の位として反映されることを確認

## v0.1.27 (2026-05-10)

### 修正
- ゲーム挙動改造ダイアログのコンボボックス表示を改善
  - 「カスタム値（現在のROM値を保持）」等の曖昧な表記を廃止
  - **コンティニュー上限**: ROMの現在値がプリセット外なら **「ステージNまで」** と具体的に表示
  - **開始ライフ**: プリセット外なら **「その他の設定 (値 N)」** と表示
  - 常に現在のROM状態が一目で分かるように

## v0.1.26 (2026-05-10)

### 変更
- 「ステージセレクトを有効化」チェックボックスを **削除**（UI簡素化）
  - 代わりに **開始ステージのスピンボックス値だけで挙動が決まる**
  - **ステージ1**: パッチなし（原作通り）→ 既存パッチがあれば自動的に元に戻す
  - **ステージ2〜53**: ハック自動適用（BESK方式 or 簡易方式）
  - スピンボックスの上限を50→**53**に拡張（PRINSESS/SOLOMON/HIDDEN/空間の間/時間の間 まで指定可）

## v0.1.25 (2026-05-10)

### 修正
- **JPでBESKパッチ済みROMを読み込んだ際に「副作用あり」警告が誤表示される不具合を修正**
  - 原因: `has_besk_free_space()` が「領域が0xEA連続か」のみ判定していたため、既にパッチ済みROMだと False を返していた
  - 対応: 「BESKパッチが既に適用済」のケースも判定に追加（領域が `BESK_STAGE_SUBROUTINE` と `BESK_STAGE_TABLE` のパッチ内容と一致すれば True）

### 変更
- 「家族の呪い解除」「鬼畜仕様」等の煽り表現を全廃
  - UI: コンボボックス見出しを「コンティニュー上限」に変更
  - CHANGELOG / MANUAL / rom_analysis.html からも該当表現を削除
  - 機能名は事実ベースのニュートラルな表現に統一

## v0.1.24 (2026-05-10)

### 追加
- **コンティニュー制限解除（コンティニュー上限拡張）** ハックを実装 🌟
  - 原作の「ステージ42以降コンティニュー不可」鬼畜仕様の正体を解明
  - **ROM 0x4A58 のたった1バイト**を変更するだけで上限を最終ステージ(53)まで拡張可能
  - ゲーム挙動改造ダイアログにコンボボックス追加:
    - 41まで（原作デフォルト）
    - 42 / 48 / PRINSESS / SOLOMON / HIDDEN まで
    - **時間の間まで（全ステージ・最終）**
  - JP/USA/EU 全リージョン共通で動作（基本ゲームロジック領域）

### 解析
- BESK で test42.nes を生成→差分1バイト確認で完全特定
- 6502 アセンブリ逆解析:
  - 0x4A57: `LDX #$28` の即値オペランドが上限値
  - 0x4A59: `CPX $0428` で現在ステージRAM比較
  - 0x4A5C: `BCS` で範囲内なら継続OK分岐
- ネット上には未文書化、世界初文書化候補
- `docs/rom_analysis.html` の「ロストテクノロジー候補3」を「解析完了」に格上げ

## v0.1.23 (2026-05-10)

### 変更
- **ステージ選択をBESK方式に置き換え**（副作用なし、JP版で完全動作）
  - 旧: 0x1145 + 0x1149/0x114B のみ書換 → スコア・残機等が未初期化
  - 新: BESKが採用する**完全パッチ方式**を実装
    - 0x1145: ステージ番号
    - 0x1149-0x1157 (15B): 初期化コード差替
    - 0x0BF2-0x0C0A (25B): カスタムサブルーチン挿入
    - 0x5BEF-0x5BFB (13B): ステージ別初期値テーブル
  - JP版で BESK 出力と**バイト単位で完全一致**を確認
  - 「ステージセレクト無効化」で全パッチを元に戻す機能も実装
- **Resume (擬似セーブ) 機能を削除**
  - 0x1146 の編集を取りやめ、UIから関連コンボボックスを除去
- USA/EU 等の未使用領域がない ROM では従来の簡易方式にフォールバック（警告表示）
- `magatu_skc/core/hack_data.py` に BESK 方式パッチデータと `apply_besk_stage_select()` / `revert_besk_stage_select()` / `has_besk_free_space()` 関数を追加

## v0.1.22 (2026-05-10)

### 変更
- ROM/IPS 保存ダイアログのデフォルトファイル名を **「元ROM名_YYYYMMDD_HHMMSS.拡張子」** 形式に変更
  - 旧: `modified.nes` / `patch.ips`
  - 新: `Solomon's Key (USA)_20260510_193857.nes` / `.ips`
  - 上書き事故防止 + 改造履歴の自然な記録
  - ZIP内ROMの場合は内部ファイル名（"xxx.nes"部分）から派生

## v0.1.21 (2026-05-10)

### 変更
- ゲーム挙動改造ダイアログのUI改善（16進数表示を全廃）
  - 開始ライフポイント: 生バイト入力を削除、**プリセットドロップダウンのみ**（デフォルト/40,000/330,000）
  - 開始ステージ: 「書込み値」プレビューラベル削除（1〜50面表示で十分）
  - Resume挙動: 16進バイト値を非表示、わかりやすい説明に変更
    - 「無効 (常に最初から)」
    - 「前回到達ステージから再開（擬似セーブ）」
    - 「前回の次のステージから再開（擬似セーブ）」
  - Resume下に補足説明「電源OFFで初期化される擬似セーブ機能」を追記
  - 適用結果メッセージも数字ベースのわかりやすい表記に変更

## v0.1.20 (2026-05-10)

### 追加
- **ゲーム挙動改造ダイアログ** を実装 (Phase 9-1, 9-2 / B-1, B-2)
  - 編集ツールに「ゲーム挙動改造...」ボタン追加
  - **B-1: 開始ライフポイント変更** (ROM 0x1839)
    - プリセット: デフォルト3000 / 40000 (0x8C) / 330000 (0x83)
    - 生バイト値スピンボックスで自由設定 (0x00〜0xFF)
  - **B-2: 開始ステージ変更** (ROM 0x1145 + 0x1149 + 0x114B)
    - 「ステージセレクト有効化」チェックボックスで 0x1149/0x114B を切替
    - 1〜50面のスピンボックスで開始面選択
    - 0x1146 (Resume挙動) のドロップダウン: デフォルト/前回到達ステージ/次ステージ
  - 「オリジナル値に戻す」ボタンでデフォルト復元
  - OK/Apply/Cancel ボタン（Applyは閉じずに適用）
  - 適用結果を箇所別にメッセージ表示
  - ROM保存（改造ROMとして保存）するまでは未永続化、再読込で復元可

### 注意
- ROMバイナリを直接書き換えるため、Undo履歴とは別系統
- 改造ROMとして保存しないとファイルには反映されない

## v0.1.19 (2026-05-10)

### 変更
- **壊せる白ブロック (BROWN_WHITE) の表示を青フィルター方式に変更**
  - 旧: 白ブロック描画 + 緑枠ハイライト（隠し強調ON時のみ）
  - 新: 白ブロック描画 + **青フィルター半透明レイヤーを常時重ねる**
  - 緑枠は廃止
  - ピッカーアイコンも同じ青フィルターを適用 → 配置時とアイコンで完全一致

## v0.1.18 (2026-05-10)

### 追加
- **ホバーハイライト** (Phase 4-4): マウス位置のタイルを白枠で強調
- **レベル設定UI** (Phase 2-7, 2-8, 2-6 / skchain移植):
  - **タイルセット切替** スピンボックス (0-2)
  - **時間減少率** スピンボックス (0-15)
  - **敵寿命** スピンボックス (0-255)
  - **星座** ドロップダウン + 位置スピンボックス（X/Y）
  - 全項目が**Undo対応** (Ctrl+Z で戻せる)
  - レベル切替時に自動でUI同期

## v0.1.17 (2026-05-10)

### 変更
- 「隠し要素強調 (黄色枠)」チェックボックスのデフォルトを **OFF** に変更（旧: ON）

## v0.1.16 (2026-05-10)

### 追加
- **全レベル統計** ダイアログを実装
  - 編集ツールに「全レベル統計」ボタン追加
  - 53レベル分を1表で一覧:
    - アイテム数（通常/隠し/in_block）
    - 敵数 / 壊せる白ブロック数
    - 鍵の状態と位置
    - ミラー位置（同位置なら●強調）
    - 星座
    - **重要アイテム一覧** (Bell, ソロモンの紋章, Warp, Shrine#1〜4, Star Coin系, Origami Swan, Demonhead Coin, Sphinx, Egyptian Head, Magic Lamp, E-bottle, Modifiable系)
  - 雑魚アイテム（Coin/Opal/Jewels/Hourglass等）は除外
  - セルダブルクリックでそのレベルへジャンプ
  - **CSV出力**ボタンで集計結果をエクスポート
  - 状態別に色付け（隠し=黄, in_block=緑, ミラー同位置=青）

## v0.1.15 (2026-05-10)

### 追加
- **レベルクリア（ブランクキャンバス）機能** を実装 (Phase 4-6)
  - 左パネルに「編集ツール」グループ追加、ドロップダウン式の **「レベルクリア ▼」** ボタン
  - 4種類のクリアモード:
    - **すべてクリア**（ブロック+アイテム+敵を一括削除、鍵/扉/スタート/ミラー/星座は保持）
    - **ブロックのみクリア**
    - **アイテムのみクリア**
    - **モンスターのみクリア**
  - 削除前に確認ダイアログ
  - Undo履歴に積むので **Ctrl+Z で戻せる**

## v0.1.14 (2026-05-10)

### 追加
- **Undo / Redo** 機能を実装 (Phase 4-1)
  - キーバインド:
    - **Ctrl+Z** = Undo（編集取り消し）
    - **Ctrl+Y** または **Ctrl+Shift+Z** = Redo（やり直し）
  - 履歴上限: **50件**（古いものから自動破棄）
  - レベル単位のスナップショット (deepcopy) 方式
  - 対象操作: 左クリック配置 / 右クリック削除 / Ctrl+ドラッグ移動 / 単一XML上書き読込
  - ドラッグ移動は drag_start で1回だけ履歴を積む（drag_move では積まない）
  - Undo/Redoで他レベルの状態も復元される（自動でレベル切替）
  - ROM/XML一括読込時はUndo履歴をクリア
  - ステータスバーに残履歴件数を表示

## v0.1.13 (2026-05-10)

### 追加
- **skchain互換 XML 入出力** を実装
  - 新規モジュール `magatu_skc/core/xml_io.py`
  - 4ボタン追加（ファイル欄）:
    - **XML出力(現在)**: 現在のレベルを skchain 形式 XML として保存
    - **XML出力(全)**: 全53レベルを `level-NN.xml` ファイル群でフォルダ保存
    - **XML読込(現在)**: XMLから読み込んで現在のレベルに上書き
    - **XML読込(全)**: フォルダから `level-NN.xml` を一括読み込み
  - skchain v1.1 のXMLフォーマット完全互換（相互運用可能）
  - 53レベル全てで round-trip 完全一致を検証済み

### XMLフォーマット
```xml
<skchain app_version="1.1">
  <level start_position="..." door_position="..." key_position="..."
         key_status="..." spawn_enemy_lifetime="..." time_decrease_rate="..."
         constellation_no="..." constellation_position="..." tileset="...">
    <blocks><block_row no="0" value="2,2,..."/>...</blocks>
    <items><item no="0" element_no="N" position="x,y"/>...</items>
    <enemies><enemy no="0" element_no="N" position="x,y"/>...</enemies>
    <mirrors><mirror no="0" position="x,y" schedule="N" enemy_set="N"/>...</mirrors>
  </level>
</skchain>
```

## v0.1.12 (2026-05-10)

### 追加
- ピッカーのアイテム一覧に **不足していた12種類**を追加
  - 0x08 Diamond (blue, modifiable)
  - 0x0c Diamond (orange, modifiable)
  - 0x0e Scroll (modifiable)
  - 0x11 Timebottle (half)
  - 0x1c Shrine #1
  - 0x1d Shrine #2
  - 0x1e Shrine #3
  - 0x1f Shrine #4
  - 0x26 Double Coin (silver)
  - 0x29 Double Coin (gold)
  - 0x2d Opal (dark orange)
  - 0x2f Demonhead Coin
  - 0x30 Sphinx, 0x31 Egyptian Head（拡充）
  - これでUSA ROM原作で使われている全実用アイテムを網羅（合計36種類）
  - L36の Shrine #1 等、原作にあるのにピッカーから配置できなかった問題を解消

## v0.1.11 (2026-05-10)

### 追加
- ファイル欄に **「再読込」** ボタンと **「履歴」** ボタンを追加
  - 再読込: 現在のROMを再ロード（編集を破棄、初期状態に戻す）
  - 履歴: 最近開いたROM最大15件のメニューを表示。クリックで読み込み。「履歴をクリア」あり
  - 履歴は `rom_history.json` に永続保存

## v0.1.10 (2026-05-10)

### 変更
- **敵 × 敵 の同位置重複を許可**（USA ROM検証で原作に8件あり、意図的な配置と確認）
  - 旧: 同位置に既存の敵がいると上書き削除
  - 新: 上書きせず追加。複数体が同じマスに置ける
  - ステータスバーに「このマスに{N}体」と表示
- アイテム × アイテム の重複は引き続き禁止（原作0件、レギュレーション準拠）
  - 既存アイテムを置き換える際にステータスバーで通知
- 右クリック削除はループで全要素削除するため、同マスに複数の敵があっても一括で消せる

### 検証データ
USA ROM 全53レベルの重複パターン調査:

| パターン | 件数 | 対応方針 |
|---|---:|---|
| アイテム × アイテム | 0 | 禁止（既存削除→置換） |
| 敵 × 敵 | 8 | **許可（重複OK）** |
| アイテム + 敵 | 6 | 自由配置可能 |
| 白ブロック内アイテム | 0 | 暗黙ルール |

## v0.1.9 (2026-05-10)

### 追加
- アイテム配置時のフラグ選択UIを追加
  - ピッカー上部に **「通常 / 隠し (0x40) / ブロック内 (0x80)」** のラジオボタン
  - 「アイテム」モード時のみ表示（他モードでは非表示）
  - 配置時に選択中のフラグを `element_no` に OR して書き込み
  - **配置レギュレーション自動適用**: 隠し専用アイテム（Warp/Origami Swan/Demonhead Coin/Sphinx/Egyptian Head/Magic Lamp）を選択すると **自動で「隠し」ラジオに切替**
  - 既存アイテムのフラグ変更UIは無し（削除→再配置 or 上書き配置で対応）

## v0.1.8 (2026-05-10)

### 変更
- 右クリック削除を**編集モード非依存**に変更
  - 旧: 「アイテム」モードのときはアイテムしか消えない / 「ブロック」モードのときはブロックしか消えない
  - 新: モード関係なく、その位置にある **アイテム/敵/ブロック を全て削除**
  - メタ要素（鍵/扉/スタート/ミラー）は移動が原則のため削除対象外
  - 削除内容をステータスバーに表示

## v0.1.7 (2026-05-10)

### 追加
- ピッカーの「ブロック」モードに **「壊せる白ブロック (見た目=白/実体=壊せる)」** を追加
  - `Wall.BROWN_WHITE` (茶＋白の両ビットON) を配置可能に
  - 描画は通常の白ブロックだが、隠し要素強調 (G で切替) 時に**緑枠**で強調表示
  - 緑枠＝「ブロック系の罠的要素」、黄色枠＝「アイテム系の隠し」と色で区別
  - USA ROMで10件存在（L47に3個集中、その他は右端列の壁が大半）

## v0.1.6 (2026-05-10)

### 変更
- Ctrl+左クリック移動を「2回クリック方式」から「ドラッグ&ドロップ方式」に変更
  - **Ctrl押下しながら左ボタンで掴む** → そのままマウス移動で要素が追従 → **Ctrl解放 or ボタン解放で確定**
  - 直感的でシンプル。skchain本家のShift+クリックよりも自然
  - 旧方式（2回クリック）は廃止

## v0.1.5 (2026-05-10)

### 追加
- **Ctrl+左クリックで要素移動**機能を追加
  - 1回目のCtrl+クリック: その位置の要素を掴む（アイテム/敵/鍵/扉/スタート/ミラー1/ミラー2）
  - 2回目のCtrl+クリック: 移動先タイルへドロップ（隠し/ブロック内フラグ等は保持）
  - 通常の左クリック / 同じ位置をCtrl+クリック で移動操作キャンセル
  - 移動先に既存アイテムや敵がある場合は中止（誤上書き防止）
  - ステータスバーに状態表示

## v0.1.4 (2026-05-10)

### 修正
- メタアイテム（ソロモンの紋章/テクモバニー等）の隠し/in_block 描画処理を追加
  - 該当位置に茶色ブロックがある → in_block 表現（アイテム → 半透明ブロックを上に重ねる）
  - ブロックなし & `transparent="true"` → 半透明アイテム（隠し表現）
  - 隠し要素強調（黄色枠）にも対応
  - 通常アイテムと同じ「いつもの形」に統一

## v0.1.3 (2026-05-10)

### 修正
- ピッカー（編集対象リスト）のアイテム/敵アイコンの色がおかしい不具合を修正
  - 原因1: `mask_brick_color=True` がスプライトの本体色（palette index 1）まで透明化していたため、本体ピクセルが消失して全アイテムが青っぽく/スカスカに見えていた
  - 原因2: ピッカーのアイコンが常にタイルセット0で描画されていた（skchainは現在レベルのタイルセットで描画）
  - 対応: マスク廃止 + `tile_renderer.get_tile_image()` を経由して描画。`set_current_tileset_no()` を追加し、レベル切替時にアイコンを現在レベルのタイルセットで再描画するように変更
  - 結果: 配置時とピッカーの色が完全一致（skchain互換）

## v0.1.2 (2026-05-10)

### 修正
- メタアイテム（ソロモンの紋章＝六芒星パネル、ボムジャック、テクモバニー、Page of Time/Space）が表示されない不具合を修正
  - 原因: `level_meta_items` の読み込み・描画処理が未実装だった
  - 対応: `config_loader.py` に `MetaItemDef` を追加し、リージョンごとに ROM オフセットから位置をデコード。`level_renderer.py` で該当レベルにのみ描画
  - 確認: JP版で14個のメタアイテムが正常に配置される（六芒星×8、ボムジャック×2、テクモバニー×2、Page×2）

## v0.1.1 (2026-05-10)

### 修正
- BESK等の旧エディタで改造されたROMが「Unknown ROM region」で読み込めない不具合を修正
  - 原因: BESKがリージョン判定オフセット (0x0bf2) も上書きするため、skchain互換のルールベース判定が外れる
  - 対策: ルールが外れた場合、CHR-ROM の CRC32 によるフォールバック判定を追加（CHR-ROM はエディタが触らないので信頼できる）
  - 既知CHR CRC32: US=`FAD8A464`, JP=`EBCA054B`（EU は未確認）

## v0.1.0 (2026-05-10)

初回リリース。skchain (kaimitai作 C++) の主要機能を Python に移植。

### 機能
- ROM読み込み (US / JP / EU / 拡張ROM US66 自動判別)
- 全53レベル解析・表示
- レベル可視化 (ブロック・アイテム・敵・鍵・扉・スタート位置・ミラー・星座背景)
- ブロック編集 (左クリックで配置、右クリックで削除)
- アイテム配置 (主要20種)
- 敵配置 (主要20種)
- 鍵/扉/スタート/ミラー位置の変更
- 通常ROM保存 (.nes)
- IPSパッチ生成 (.ips)
- 単一レベル / 全レベル PNG エクスポート
- グリッド表示切替
- 隠し要素オーバーレイ表示
- skchain互換 skc_config.xml の流用

### キーバインド
- F1: ヘルプ
- F9: 設定画面 (未実装)
- PageUp/Down: レベル切替
- G: グリッド表示切替

### 既知の制限
- 拡張ROM(US66)の保存は未対応
- 設定画面 (F9) 未実装
- アイテムの「隠し」「ブロック内」フラグの編集UI未実装
- デーモンミラーのドロップスケジュール・敵セット編集UI未実装
- アイテム/敵の選択UIが英語表記のみ
- 起動時自動バックアップ未実装

### 移植元
[skchain v1.1](https://github.com/kaimitai/skchain) by kaimitai
- 対象: Solomon's Key (NES) ROMエディタ
- 元実装: C++20 + Dear ImGui + SDL2

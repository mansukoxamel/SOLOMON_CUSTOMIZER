# Panel Monster ASM analysis

Date: 2026-05-27
Target ROM: raw JP / bank0 addresses. Mapper66-expanded JP keeps these bank0 CPU
addresses unless another patch has already hooked them.

This note exists because the 2026-05-27 fast Panel Monster Bullet experiments
were not based on enough ASM analysis. In particular, running generic physics
extra times made Bullets pass through walls because the Bullet wall-collision
path was not run for each extra movement step.

## Address summary

| Area | CPU | file offset | Role |
|---|---:|---:|---|
| AI dispatch entry for Bullet | `$AFBB` | `0x2FCB` | Bullet state dispatcher |
| AI dispatch entry for Panel Monster | `$A54C` | `0x255C` | Panel Monster state dispatcher |
| Panel fire routine | `$A556` | `0x2566` | Spawns Bullet via `$AE76` |
| Panel idle/cooldown routine | `$A575` | `0x2585` | Allocates child sub-slot and arms fire state |
| Bullet materialize helper | `$AE76` | `0x2E86` | Creates type `$20` Bullet |
| Entity writer | `$9D1C` | `0x1D2C` | Writes main-slot bytes from `$04/$05/A` |
| State extractor | `$B201` | `0x3211` | Returns `behavior >> 2` |
| Main-slot pointer helper | `$B14A` | `0x315A` | Slot index `A` to `$00/$01` main slot ptr |
| Sub-slot pointer helper | `$B156` | `0x3166` | Slot index `A` to `$00/$01` sub slot ptr |
| Free sub-slot search | `$B2EA` | `0x32FA` | Returns slot index `X`, carry set on success |
| Despawn | `$B376` | `0x3386` | Clears main/sub slot and moves sprite offscreen |
| Speed initializer | `$8AC0` | `0x0AD0` | Loads `+5/+8` speeds from `$DB99` table |
| Common physics | `$8689` | `0x0699` | Applies `+5/+8` velocity to position |
| Bullet collision sampler | `$AC39` | `0x2C49` | Samples 4 block corners into `$07` |
| Bullet impact tile target | `$B016` | `0x3026` | Converts collision bit to impact coordinate |

## Entity slot model used here

The active entity loop uses two pointers:

| Pointer | Meaning |
|---|---|
| `($2C)` | current sub-slot |
| `($2E)` | current main slot |
| `($08)` | current main slot during the shared loop / physics initializer |

Important offsets:

| Offset | Slot | Meaning |
|---:|---|---|
| `+0` | both | active/status byte; bit7 means active |
| `+1` | main | entity type, e.g. `$20` Bullet, `$24-$27` Panel Monster |
| `+1` | sub | frame/state counter used by many AIs |
| `+2` | main | previous type/state helper used by the shared entity loop |
| `+3` | main | behavior; low 2 bits are direction, upper bits are AI state |
| `+5` | main | Y velocity |
| `+6` | sub | child slot index used by Panel Monster after `$B2EA` |
| `+7` | main | Y position |
| `+8` | main | X velocity |
| `+10` | main | X position |
| `+12` | main | animation timer in stock Bullet; not safe as persistent marker |

## Panel Monster state flow

Panel Monster IDs:

| ID | Direction |
|---:|---|
| `$24` | right |
| `$25` | left |
| `$26` | up |
| `$27` | down |

The AI dispatch table routes `$24-$27` to `$A54C`.

`$A54C`:

```asm
$A54C: JSR $B201      ; A = main[3] >> 2
$A54F: JSR $8EA9      ; jump through inline state table
$A552: .word $A575    ; state 0: idle/cooldown
$A554: .word $A556    ; state 1: fire
```

### State 0: idle/cooldown `$A575`

```asm
$A575: LDY #$02
$A577: LDA ($2C),Y
$A579: CMP #$C0
$A57B: BCC $A59F      ; wait until sub[2] >= $C0
$A57D: JSR $B2EA      ; find free sub-slot
$A580: BCC $A59F      ; no free slot, keep waiting
$A582: TXA
$A583: LDY #$06
$A585: STA ($2C),Y    ; sub[6] = child slot index
$A587: LDY #$00
$A589: LDA #$80
$A58B: STA ($04),Y    ; mark child sub-slot active
$A58D: LDY #$03
$A58F: LDA #$03
$A591: AND ($2E),Y    ; keep direction bits
$A593: ORA #$04       ; set behavior state 1
$A595: STA ($2E),Y
$A597: DEY
$A598: LDA #$00
$A59A: STA ($2C),Y    ; clear sub[2]
$A59C: DEY
$A59D: STA ($2C),Y    ; clear sub[1]
$A59F: RTS
```

Facts:

- The firing interval has two parts: idle threshold `$A57A` (`#$C0`) and pre-shot
  wait `$A55B` (`#$10`).
- `$B2EA` allocates the sub-slot that will become the child Bullet.
- `sub[6]` stores that child slot index. `$AE76` later consumes it.
- The parent main behavior keeps direction in bits 0-1 and enters state 1 by
  setting bit 2.

### State 1: fire `$A556`

```asm
$A556: LDY #$01
$A558: LDA ($2C),Y
$A55A: CMP #$10
$A55C: BCC $A574      ; pre-shot wait
$A55E: LDY #$03
$A560: LDA ($2E),Y
$A562: AND #$03       ; direction 0..3
$A564: TAX
$A565: JSR $AE76      ; materialize Bullet
$A568: LDY #$03
$A56A: TYA            ; A = 3
$A56B: AND ($2E),Y    ; clear state bits, keep low direction bits
$A56D: STA ($2E),Y
$A56F: DEY
$A570: LDA #$00
$A572: STA ($2C),Y    ; clear sub[2]
$A574: RTS
```

Facts:

- `$AE76` is called with `X = direction`.
- After firing, Panel Monster returns to state 0 by masking behavior with `#3`.
- No Bullet speed is written directly here. Speed comes from the normal entity
  initialization path after the Bullet exists.

## Bullet materialization `$AE76`

`$AE76` is the shared Bullet-spawn helper used by Panel Monster and other
enemies.

```asm
$AE76: STX $03              ; direction
$AE78: LDA $AEC4,X          ; Y spawn offset
$AE7B: STA $04
$AE7D: LDA $AEC2,X          ; X spawn offset
$AE80: STA $05
$AE82: LDY #$06
$AE84: LDA ($2C),Y          ; child slot index from parent sub[6]
$AE86: STA $02
$AE88: JSR $B156            ; child sub-slot ptr -> $00/$01
$AE8B: LDY #$00
$AE8D: LDA #$FE
$AE8F: AND ($2C),Y
$AE91: STA ($2C),Y          ; clear parent bit0
$AE93: INY
$AE94: LDA #$00
$AE96: STA ($00),Y          ; child sub[1] = 0
$AE98: LDA $02
$AE9A: JSR $B14A            ; child main-slot ptr -> $00/$01
$AE9D: LDY #$07
$AE9F: LDA ($2E),Y
$AEA1: CLC
$AEA2: ADC $04
$AEA4: STA ($00),Y          ; child Y
$AEA6: LDY #$0A
$AEA8: LDA ($2E),Y
$AEAA: CLC
$AEAB: ADC $05
$AEAD: STA ($00),Y          ; child X
$AEAF: LDA #$C0
$AEB1: STA $04              ; status
$AEB3: LDA #$20
$AEB5: STA $05              ; type Bullet
$AEB7: LDA $03              ; behavior = direction
$AEB9: JSR $9D1C            ; write child entity
$AEBC: LDY #$17
$AEBE: JSR $8E8D            ; animation/sprite init side effect
$AEC1: RTS
```

Spawn offset tables:

| CPU | Bytes | Meaning |
|---:|---|---|
| `$AEC2` | `06 FA 00 00` | X offset table |
| `$AEC4` | `00 00 FA 06` | Y offset table |

Inferred direction mapping from `$AE76`:

| Direction | X offset | Y offset |
|---:|---:|---:|
| `0` | `+$06` | `0` |
| `1` | `-$06` | `0` |
| `2` | `0` | `-$06` |
| `3` | `0` | `+$06` |

This matches Panel Monster direction bits: right, left, up, down.

Important consequence:

- A robust Panel-specific Bullet change should identify the child slot via
  parent `sub[6]` and `$AE76`/`$9D1C`, not by globally changing all Bullet
  table entries.

## Bullet AI `$AFBB`

`$AFBB` is the Bullet AI for type `$20-$23`. It has three effective states:

```asm
$AFBB: JSR $B201
$AFBE: JSR $8EA9
$AFC1: .word $AFC7    ; state 0: short delay before movement state
$AFC3: .word $B00A    ; state 1: despawn countdown
$AFC5: .word $AFD8    ; state 2: moving/collision state
```

### Bullet state 0 `$AFC7`

```asm
$AFC7: LDY #$01
$AFC9: LDA ($2C),Y
$AFCB: CMP #$0A
$AFCD: BCC $AFD7
$AFCF: LDY #$03
$AFD1: LDA #$08
$AFD3: ORA ($2E),Y
$AFD5: STA ($2E),Y    ; behavior |= $08, enter state 2
$AFD7: RTS
```

Facts:

- The Bullet does not immediately enter the moving collision state.
- After about 10 frames it enters state 2.
- This is why a one-shot marker in `main+12` is fragile: stock Bullet later
  reinitializes and stock animation uses that byte.

### Bullet state 2 `$AFD8`

```asm
$AFD8: JSR $AC39      ; sample four collision corners into $07
$AFDB: LDA $07
$AFDD: BEQ $B009      ; no collision: return
$AFDF: JSR $B016      ; choose impact point from collision bits
$AFE2: JSR $918A      ; coordinate -> grid index
$AFE5: TAY
$AFE6: LDA $0304,Y
$AFE9: CMP #$F8
$AFEB: BCC $AFF0
$AFED: JMP $B376      ; invalid/sentinel tile -> despawn
$AFF0: STY $04
$AFF2: LDX $2E
$AFF4: STX $00
$AFF6: LDX $2F
$AFF8: STX $01
$AFFA: JSR $9BE3      ; block hit / tile effect
$AFFD: LDY #$01
$AFFF: LDA #$20
$B001: STA ($2E),Y
$B003: LDY #$03
$B005: LDA #$04
$B007: STA ($2E),Y    ; enter state 1
$B009: RTS
```

Facts:

- Wall collision is not inside `$8689`.
- `$8689` only applies velocity to position and related position bookkeeping.
- Bullet-specific wall handling is `$AC39 -> $B016 -> $918A -> $9BE3`.
- Calling `$8689` extra times without calling `$AC39` between substeps can
  move the Bullet past a wall before the next Bullet AI collision sample.
  This caused the failed wall-piercing test ROMs.

### Bullet state 1 `$B00A`

```asm
$B00A: LDY #$01
$B00C: LDA ($2C),Y
$B00E: CMP #$0F
$B010: BCS $B013
$B012: RTS
$B013: JMP $B376
```

This is the post-impact/despawn countdown.

## Bullet collision sampler `$AC39`

`$AC39` samples four corners around the Bullet and shifts tile solidity into
`$07`.

```asm
$AC39: LDY #$07
$AC3B: LDA ($2E),Y
$AC3D: STA $02        ; Y position
$AC3F: LDY #$0A
$AC41: LDA ($2E),Y
$AC43: STA $03        ; X position
$AC45: LDA #$00
$AC47: STA $07        ; collision bitfield
$AC49: LDY #$03
loop:
$AC4B: LDA $ACD9,Y
$AC4E: CLC
$AC4F: ADC $02
$AC51: STA $04        ; sample Y
$AC53: LDA $ACDA,Y
$AC56: CLC
$AC57: ADC $03
$AC59: STA $05        ; sample X
$AC5B: JSR $918A      ; sample coordinate -> grid index X
$AC5E: LDA $0304,X
$AC61: ASL A
$AC62: ROL $07        ; roll solidity/collision into $07
$AC64: DEY
$AC65: BPL loop
$AC67: RTS
```

The exact corner offset table is still not fully labeled here, but the important
behavior is confirmed: `$07 != 0` means the Bullet has detected a blocking
condition and must run the impact path in `$AFD8`.

## Bullet impact helper `$B016`

`$B016` converts collision bits in `$07` into a single impact coordinate in
`$04/$05`.

```asm
$B016: AND #$0F
$B018: LDX #$FF
loop:
$B01A: INX
$B01B: LSR A
$B01C: BCC loop
$B01E: LDY #$07
$B020: LDA $B033,X
$B023: CLC
$B024: ADC ($2E),Y
$B026: STA $04        ; impact Y
$B028: LDY #$0A
$B02A: LDA $B034,X
$B02D: CLC
$B02E: ADC ($2E),Y
$B030: STA $05        ; impact X
$B032: RTS
```

Facts:

- `$07` is a bitfield. `$B016` picks the first set bit and applies an offset.
- `$AFD8` then passes `$04/$05` through `$918A` to choose the tile affected by
  the hit.
- If a fast Bullet design substeps movement, it must preserve this impact
  selection path or the hit effect can occur at the wrong tile.

## Bullet rebound / alternate collision code near `$AC68`

The code after `$AC68` is not the normal Panel Bullet path, but it is relevant
when considering other projectile-like enemies.

Key observations:

```asm
$AC68: LDY #$03
$AC6A: LDA ($2E),Y
$AC6C: LSR A
$AC6D: STA $00
$AC6F: LDY #$05
$AC71: LDA ($2C),Y
$AC73: ROL A
$AC74: LDA $00
$AC76: ROL A
$AC77: LDY #$03
$AC79: STA ($2E),Y
$AC7B: JSR $AC39
$AC7E: LDA $07
$AC80: BNE $AC92
```

Facts:

- This path changes behavior from previous direction/state and then samples
  collision with `$AC39`.
- On collision it zeros `main+5/main+8`, can allocate a child sub-slot, and may
  branch into direction-flip logic around `$ACF4`.
- It proves a useful pattern: direction/state update and collision sampling must
  remain coupled. Moving first and sampling later is not a safe projectile
  design in this engine.

## Speed initializer `$8AC0` and physics `$8689`

`$8AC0` loads velocities from the state/velocity tables:

```asm
$8ACB: LDA $D9D3,Y    ; state velocity table pointer low
$8AD0: LDA $D9D4,Y    ; state velocity table pointer high
...
$8AEB: ASL A
$8AEC: TAX
$8AED: LDY #$05
$8AEF: LDA $DB99,X
$8AF2: CMP #$40
$8AF4: BEQ skip_y
$8AF6: STA ($08),Y    ; main+5 = Y velocity
...
$8AF8: LDY #$08
$8AFA: LDA $DB9A,X
$8AFD: CMP #$40
$8AFF: BEQ skip_x
$8B01: STA ($08),Y    ; main+8 = X velocity
```

Facts:

- `$40` is a "do not update this velocity byte" marker in `$8AC0`, not a usable
  speed.
- Velocity values in this engine are not a simple unbounded speed field.
- Table-only tuning hits a practical cap near `$3F/$41`. That cap is not enough
  for the "clearly fast Bullet" goal.

`$8689` applies velocity:

```asm
$8689: LDY #$05       ; Y velocity
...
$86B6: STA ($08),Y    ; Y position high/commit area
...
$86B8: INY            ; reaches +8 X velocity path
...
$86D2: STA ($08),Y    ; X position high/commit area
```

Facts:

- `$8689` is generic movement, not Bullet movement logic.
- Re-running `$8689` is only safe if the caller also preserves the object's
  collision contract. Bullet does not.

## Current custom Panel Monster variant patch

The production customizer already patches Panel Monster behavior in
`magatu_skc/core/panel_monster_variant.py`. This is important for future work:
new fast-Bullet logic must coexist with these hooks.

### Borrowed IDs

| IDs | Meaning |
|---|---|
| `$52/$53/$56/$57` | Panel Monster 2-way variants |
| `$5A/$5B/$66/$67` | Panel Monster 3-way variants |

The borrowed IDs keep their own entity type. Wrapper code rewrites direction
bits and jumps into stock Panel AI `$A54C`.

### Hook / cave layout

| Hook or cave | CPU | Role |
|---|---:|---|
| Panel fire hook | `$A556` | Jump to fire dispatch |
| Bullet AI head hook | `$AFBB` | `JSR $BF69` Bullet movement-position hook |
| Fire dispatch | `$BCD2` | Select normal / 2-way / 3-way fire routine |
| Saramandor-ID wrapper | `$BC5B` | Route `$66/$67` to Panel AI |
| Common fire loop | `$BD88` | Shared normal / 2-way / 3-way shot routine; entries are normal `$BD88`, 3-way `$BD8C`, 2-way `$BD90` |
| Bullet hook | `$BF69` | Diagonal bullet visual-position correction |
| Reclaimed normal fire area | `$BFB3-$BFD7` | Free after common fire loop conversion |
| Reclaimed 2-way fire area | `$C088-$C0C1` | Free after common fire loop conversion |
| Animation selector | `$C0C2` | Panel visuals for borrowed IDs |
| Demonhead-ID wrapper | `$C146` | Route `$52-$5B` ranges to Panel AI |
| Property selector | `$DBDF` | Panel properties for borrowed IDs |

### Existing Bullet hook behavior

The current `CAVE_BULLET_HOOK` does this:

1. calls stock `$B201`;
2. only acts when the Bullet state index is `2`, i.e. moving/collision state;
3. reads marker from the Bullet sub-slot;
4. offsets `main+7` or `main+10` by 1 pixel for diagonal spread correction;
5. restores registers and returns to the stock Bullet AI.

Important distinction:

- This hook does not speed up Bullet.
- It intentionally touches position only while the stock Bullet movement state
  is active.
- It does not bypass `$AFD8/$AC39`; this is why the accepted 2-way/3-way
  variants do not wall-pierce.

Future fast Bullet work should chain through this existing hook or replace it
with a superset. It must not blindly overwrite `$AFBB` without preserving the
diagonal correction behavior.

## Full behavior map for common edit requests

| Request | Correct target | Notes |
|---|---|---|
| Faster firing interval | `$A57A` threshold and `$A55B` pre-shot wait | Already supported by cooldown/snappy logic |
| More bullets per shot | Common Panel fire loop `$BD88` marker-table style | Existing 2-way/3-way implementation is the model |
| Change shot mouth offset | `$AE76` offset tables or fire-cave post-spawn adjustment | Must handle all four directions |
| Make shot visibly faster | Bullet state2 substep with collision after each substep | Do not use `$8689` alone |
| Make only strengthened Panel shots faster | Mark child slot from Panel fire cave and gate Bullet state2 logic | Must coexist with `$BF69` diagonal hook |
| Make every Bullet faster | Global Bullet AI `$AFBB` state2 replacement | High blast radius: Saramandor/Gargoyle/Bullet pickups affected |
| Change Bullet lifetime after impact | `$B00A` / state1 threshold `$0F` | Separate from travel speed |
| Change Bullet activation delay | `$AFCB` threshold `$0A` | Separate from travel speed |

## Safe fast-Bullet implementation sketch

The next test ROM should not use `$866D` or `$8689` as the primary hook. The
least risky target is Bullet state2 at `$AFD8`, because that is where collision
and impact are already handled.

Pseudo-flow for a fast Panel-only Bullet:

```text
Bullet state2 wrapper:
  if not marked fast Panel Bullet:
      run stock $AFD8 path

  repeat N times:
      run one normal movement step
      run $AC39 collision sample
      if $07 != 0:
          run the same impact path as stock $AFD8
          stop
      if bullet despawned or changed state:
          stop
  return
```

Implementation detail that still needs byte-level design:

- "one normal movement step" can be either:
  - call a small axis-specific position update using `main+5/main+8`; or
  - call a carefully isolated movement routine that does not also advance
    unrelated global/animation side effects.
- Calling full `$8689` may still be too broad because it also runs generic
  position bookkeeping. It is safer to write a dedicated Bullet substep for the
  active axis only.
- The stock impact path starts after `$AFDB` once `$07` is known:
  `$B016 -> $918A -> tile check -> $9BE3 -> state1`.

## Candidate marking strategies

| Strategy | Pros | Cons |
|---|---|---|
| Use child sub-slot marker | Natural because Panel fire owns `sub[6]`; does not alter global Bullet type | Need verify which sub-slot byte survives until state2 |
| Use main-slot velocity value | Survives some reinit cases, used by Saramandor slow Bullet | Ambiguous if another enemy can produce same speed |
| Use main-slot `+12` one-shot marker | Easy immediately after spawn | Stock Bullet animation timer reuses it, not persistent |
| Use borrowed Bullet type | Cleanest runtime discrimination | Requires property/AI table work and consumes more design space |

Current recommendation:

1. For a test ROM, use a child sub-slot marker plus a fallback velocity check.
2. For production, prefer a dedicated strengthened Panel Bullet marker/type if
   byte budget allows.

## Remaining unknowns before final production code

These are now narrow, concrete unknowns rather than broad "Panel Monster is not
understood" unknowns:

- exact best byte in the child sub-slot that survives from spawn to Bullet state2;
- smallest safe dedicated Bullet substep routine that preserves collision;
- whether the existing `$BF69` diagonal hook should be extended or replaced by a
  combined fast/diagonal hook;
- final byte budget in bank0 cave after combining with the existing Panel caves.

If the next request is "make fast strengthened Panel Bullet", start from this
section, not from `$DB99` table edits or generic `$8689` repeats.

## Why the failed fast-Bullet tests failed

### 1. Writing speed immediately after `$AE76`

This can be overwritten because Bullet state changes later cause the shared
entity loop to call `$8AC0` again. Saramandor slow Bullet handles this by
wrapping `$866D -> $8AC0` and recognizing the Bullet after reinitialization.

### 2. Editing `$DB99` values directly

This can prove which table entries are involved, but it is a poor user-facing
control. It also runs into the `$40` skip marker and the practical `$3F/$41`
limit. It should not be the final design for a fast strengthened Panel Monster.

### 3. Re-running `$8689` for extra speed

This made the Bullet pass through walls. The reason is precise:

- normal frame order: one movement update, then Bullet state 2 collision sample;
- failed test: multiple movement updates before one collision sample;
- result: Bullet can step over a blocking tile between collision samples.

This is not acceptable.

## Safe design direction for a fast Panel Monster Bullet

The next implementation should be based on one of these, in order of preference.

### Option A: substep movement with collision after each substep

For a fast Panel Bullet, run a small loop:

1. apply one movement step using the stock velocity/physics path or an equivalent
   axis-limited step;
2. call the same Bullet collision sampler path (`$AC39`);
3. if `$07 != 0`, run the normal impact path or jump back into `$AFD8` after
   `$AFDB`;
4. only continue to the next substep if no collision occurred.

This preserves wall collision. It costs more bytes than table tuning, but it
matches the desired behavior.

### Option B: create a separate fast Bullet state

Create a new Bullet-like state for Panel-only Bullet IDs/markers:

- use stock `$AFD8` collision code as the skeleton;
- move, sample, and impact in the same routine;
- do not globally change `$20-$23` behavior unless the design intentionally
  wants every Bullet to become faster.

### Option C: table-only multiplier

This is only useful for small speed changes. It will not deliver a clearly fast
shot and should not be used for the current strengthened Panel Monster goal.

## Concrete rules for future edits

- Do not hook `$8689` alone for Bullet speed.
- Do not rely on main-slot `+12` as a persistent marker unless the wrapper also
  recognizes the resulting velocity/state after stock code reuses `+12`.
- Do not globally edit `$DB99` unless the feature is explicitly global Bullet
  speed.
- For Panel-only behavior, start from the parent `$A556/$AE76` path and child
  slot stored in `sub[6]`.
- Any fast Bullet test must verify wall collision before it is considered
  successful.
- Any `$AFBB` hook must preserve the current `$BF69` diagonal-correction logic
  or deliberately replace it with a superset.
- A "fast" implementation must keep movement and `$AC39` collision sampling
  paired per substep.

## Stage-parameterized A/B/C Panel Variant test status

This is still a test-ROM-only feature.  Do not wire it into the app save path
until the user explicitly asks for integration.

Accepted borrowed ID groups:

| Group | IDs | Directions |
|---|---|---|
| C | `$31/$33/$35/$37` | right / left / up / down |
| A | `$41/$43/$45/$47` | right / left / up / down |
| B | `$49/$4B/$4D/$4F` | right / left / up / down |

The shared AI wrapper direction formula that passed tests is:

```text
direction = (type >> 1) & 3
```

The wrapper must clear Panel work bytes before entering stock Panel AI `$A54C`:

```text
main+9 = 0
main+8 = 0
main+6 = 0
main+5 = 0
main+3 = (main+3 & $FC) | direction
```

Do not also clear `main+2/main+4`; that test made the monsters move worse.

The accepted no-drift fix for these borrowed IDs is to neutralize the original
borrowed-family speed table range `$DBB5-$DBDE` (`file 0x5BC5-0x5BEE`).  Stop
before `$DBDF`, because `$DBDF` is the Panel/Spark property selector hook.

Passing ROM checkpoints:

| ROM | Result |
|---|---|
| `TEST_OrigJP_Stage3_PanelVariant_FINAL_SPLIT_Right3_v5_NoDrift_FROM_ORIGINAL.nes` | Three right-facing variants, no drift |
| `TEST_OrigJP_Stage3_PanelVariant_FINAL_SPLIT_DirCheck_UD_v2_WideNoDrift_FROM_ORIGINAL.nes` | Up/down variants, no left drift |
| `TEST_OrigJP_Stage3_PanelVariant_FINAL_SPLIT_DirCheck_UD_v3_SourceNoDrift_FROM_ORIGINAL.nes` | Same bytes as v2, regenerated from source |

Implementation note: `apply_final_split_test_candidate()` now writes this
neutralized range as part of the test candidate so source regeneration matches
the accepted ROM.

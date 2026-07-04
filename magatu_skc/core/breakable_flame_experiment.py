"""Build an experimental ROM with enemy ID $84 as a Flame-family enemy.

This is intentionally not wired into the normal editor save path. It is a
branch-local experiment for proving that a new enemy ID can reach the runtime
without borrowing an existing ID.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import new_enemy_runtime, m66_expander, saver
from .element import ElementType, LevelElement
from .level import load_all_levels
from .rom import Rom


NEW_ENEMY_ID = 0x84
STAGE_NO = 0
ENEMY_POS = (13, 7)
COMPARE_ENEMIES = (
    (0x80, (11, 7)),
    (0x81, (12, 7)),
    (0x84, (13, 7)),
)

OFF_AI_DISPATCH_CALL = 0x21D3  # CPU $A1C3: JSR $A329
OFF_ANIM_UPDATE_CALL = 0x0686  # CPU $8676: JSR $8789
OFF_INIT_WRITE_CALL = 0x2302  # CPU $A2F2: JSR $9D1C
OFF_SETUP_META_LOAD = 0x0ADB  # CPU $8ACB: LDA $D9D3,Y

OFF_BUFFER = 0x69B9
BUFFER_LEN = 24
OFF_EXPERIMENT_RUNTIME = 0x69D1
CPU_EXPERIMENT_AI_DISPATCH = 0xE9C1
CPU_EXPERIMENT_SETUP_META_LOAD = 0xE9D0
CPU_EXPERIMENT_INIT_STATUS = 0xE9E9
CPU_EXPERIMENT_ANIM_UPDATE = 0xEA15
CPU_EXPERIMENT_CLASSIFY = 0xEA22
CPU_EXPERIMENT_SETUP_TABLE = 0xEA2E
CPU_EXPERIMENT_STATUS_TABLE = 0xEA2F
CPU_EXPERIMENT_BEHAVIOR_TABLE = 0xEA30
CPU_EXPERIMENT_FRAME1_TABLE = 0xEA31
CPU_EXPERIMENT_FRAME2_TABLE = 0xEA32
CPU_EXPERIMENT_ATTR_TABLE = 0xEA33

ORIG_AI_DISPATCH_CALL = bytes.fromhex("20 29 a3")
HOOK_AI_DISPATCH_CALL = bytes((
    0x20,
    CPU_EXPERIMENT_AI_DISPATCH & 0xFF,
    CPU_EXPERIMENT_AI_DISPATCH >> 8,
))

ORIG_ANIM_UPDATE_CALL = bytes.fromhex("20 89 87")
HOOK_ANIM_UPDATE_CALL = bytes((
    0x20,
    CPU_EXPERIMENT_ANIM_UPDATE & 0xFF,
    CPU_EXPERIMENT_ANIM_UPDATE >> 8,
))

ORIG_INIT_WRITE_CALL = bytes.fromhex("20 1c 9d")
HOOK_INIT_WRITE_CALL = bytes((
    0x20,
    CPU_EXPERIMENT_INIT_STATUS & 0xFF,
    CPU_EXPERIMENT_INIT_STATUS >> 8,
))

ORIG_SETUP_META_LOAD = bytes.fromhex("b9 d3 d9")
HOOK_SETUP_META_LOAD = bytes((
    0x20,
    CPU_EXPERIMENT_SETUP_META_LOAD & 0xFF,
    CPU_EXPERIMENT_SETUP_META_LOAD >> 8,
))

CUR_ANIM_META_LOAD_HOOK = (
    bytes.fromhex("20 d8 e2") + bytes((0xEA,)) * 7
)

AI_DISPATCH_RUNTIME = bytes.fromhex(
    # A is (entity_type - $14). Preserve that stock dispatcher input while
    # classifying the real type, because defeated enemies become type $14 and
    # must still reach the original pickup/death-effect AI as A=$00.
    "48"
    "18"
    "69 14"
    f"20 {CPU_EXPERIMENT_CLASSIFY & 0xFF:02x} {CPU_EXPERIMENT_CLASSIFY >> 8:02x}"
    "b0 02"
    "68"
    "60"
    "68"
    "4c 29 a3"
)

SETUP_META_RUNTIME = bytes.fromhex(
    # Read entity +1 type, classify it, and replace the setup group only for
    # registered new enemies. The group feeds both $D9D3 speed/setup and the
    # later $D0E8 animation metadata path.
    "a0 01"
    "b1 08"
    f"20 {CPU_EXPERIMENT_CLASSIFY & 0xFF:02x} {CPU_EXPERIMENT_CLASSIFY >> 8:02x}"
    "b0 0a"
    f"bd {CPU_EXPERIMENT_SETUP_TABLE & 0xFF:02x} {CPU_EXPERIMENT_SETUP_TABLE >> 8:02x}"
    "85 0e"
    "a8"
    "b9 d3 d9"
    "60"
    "a4 0e"
    "b9 d3 d9"
    "60"
)

INIT_STATUS_RUNTIME = bytes.fromhex(
    # Run original JSR $9D1C, then use the new-enemy classification tables to
    # pin status, behavior, and the fixed visible frame for registered IDs.
    "20 1c 9d"
    "a5 05"
    f"20 {CPU_EXPERIMENT_CLASSIFY & 0xFF:02x} {CPU_EXPERIMENT_CLASSIFY >> 8:02x}"
    "b0 21"
    "a0 00"
    f"bd {CPU_EXPERIMENT_STATUS_TABLE & 0xFF:02x} {CPU_EXPERIMENT_STATUS_TABLE >> 8:02x}"
    "91 00"
    "a0 03"
    f"bd {CPU_EXPERIMENT_BEHAVIOR_TABLE & 0xFF:02x} {CPU_EXPERIMENT_BEHAVIOR_TABLE >> 8:02x}"
    "91 00"
    "a0 11"
    f"bd {CPU_EXPERIMENT_FRAME1_TABLE & 0xFF:02x} {CPU_EXPERIMENT_FRAME1_TABLE >> 8:02x}"
    "91 00"
    "c8"
    f"bd {CPU_EXPERIMENT_FRAME2_TABLE & 0xFF:02x} {CPU_EXPERIMENT_FRAME2_TABLE >> 8:02x}"
    "91 00"
    "c8"
    f"bd {CPU_EXPERIMENT_ATTR_TABLE & 0xFF:02x} {CPU_EXPERIMENT_ATTR_TABLE >> 8:02x}"
    "91 00"
    "60"
)

ANIM_UPDATE_SKIP_RUNTIME = bytes.fromhex(
    # $08/$09 points at the current main-slot in the $8640-$8679 entity loop.
    # Registered new enemies skip stock SUB_8789 so fixed frames survive.
    # Other entities tail-jump to the original animation engine.
    "a0 01"
    "b1 08"
    f"20 {CPU_EXPERIMENT_CLASSIFY & 0xFF:02x} {CPU_EXPERIMENT_CLASSIFY >> 8:02x}"
    "b0 01"
    "60"
    "4c 89 87"
)

CLASSIFY_RUNTIME = bytes.fromhex(
    # Input A = enemy type. Output C clear and X = new-enemy index when the
    # type is in the registered contiguous new-ID range. Otherwise C set.
    "38"
    "e9 84"
    "c9 01"
    "b0 03"
    "aa"
    "18"
    "60"
    "38"
    "60"
)

CLASSIFICATION_TABLES = bytes((
    0x40,  # setup group: Flame/Burn
    0xE0,  # status: active, fireball-hit and Dana-contact masks clear
    0x00,  # behavior/state
    0xD6,  # fixed frame tile 1
    0xD4,  # fixed frame tile 2
    0x5A,  # fixed frame attr
))

EXPERIMENT_RUNTIME = (
    AI_DISPATCH_RUNTIME
    + SETUP_META_RUNTIME
    + INIT_STATUS_RUNTIME
    + ANIM_UPDATE_SKIP_RUNTIME
    + CLASSIFY_RUNTIME
    + CLASSIFICATION_TABLES
)

assert len(AI_DISPATCH_RUNTIME) == (
    CPU_EXPERIMENT_SETUP_META_LOAD - CPU_EXPERIMENT_AI_DISPATCH
)
assert len(SETUP_META_RUNTIME) == (
    CPU_EXPERIMENT_INIT_STATUS - CPU_EXPERIMENT_SETUP_META_LOAD
)
assert len(INIT_STATUS_RUNTIME) == (
    CPU_EXPERIMENT_ANIM_UPDATE - CPU_EXPERIMENT_INIT_STATUS
)
assert len(ANIM_UPDATE_SKIP_RUNTIME) == (
    CPU_EXPERIMENT_CLASSIFY - CPU_EXPERIMENT_ANIM_UPDATE
)
assert len(CLASSIFY_RUNTIME) == (
    CPU_EXPERIMENT_SETUP_TABLE - CPU_EXPERIMENT_CLASSIFY
)
assert len(CLASSIFICATION_TABLES) == 6
assert len(EXPERIMENT_RUNTIME) == 115
assert CPU_EXPERIMENT_AI_DISPATCH + len(EXPERIMENT_RUNTIME) == CPU_EXPERIMENT_ATTR_TABLE + 1


class BreakableFlameExperimentError(RuntimeError):
    pass


def _expect(data: bytes | bytearray, off: int, expected: bytes, name: str) -> None:
    cur = bytes(data[off:off + len(expected)])
    if cur != expected:
        raise BreakableFlameExperimentError(
            f"{name} signature mismatch at 0x{off:X}: "
            f"expected {expected.hex(' ')}, got {cur.hex(' ')}"
        )


def _write(data: bytearray, off: int, blob: bytes) -> None:
    data[off:off + len(blob)] = blob


def apply_runtime_patch(rom_data: bytearray) -> list[str]:
    """Patch the generated mapper66 ROM for the $84 killable-Flame test."""
    changed = new_enemy_runtime.apply(rom_data)
    if changed:
        return changed
    return [
        "New enemy runtime already present",
    ]


def build_experiment_rom(
    source_path: str | Path = Path("ROM") / "Solomon no Kagi (J).nes",
    output_path: str | Path = Path("output") / "flame84_stage1_flame84_only_x13.nes",
    enemy_specs: tuple[tuple[int, tuple[int, int]], ...] = ((NEW_ENEMY_ID, ENEMY_POS),),
) -> tuple[Path, list[str]]:
    source_path = Path(source_path)
    output_path = Path(output_path)

    rom = Rom.load(str(source_path))
    levels = load_all_levels(rom)
    m66_expander.expand_rom(rom, levels)

    level = levels[STAGE_NO]
    level.enemies = []
    for enemy_no, pos in enemy_specs:
        level.enemies.append(LevelElement(ElementType.ENEMY, pos, enemy_no))

    saved = bytearray(saver.build_saved_rom_data(rom, levels))
    changes = apply_runtime_patch(saved)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    saver.write_rom_data(bytes(saved), str(output_path))
    changes.extend(
        f"stage 1 enemy ${enemy_no:02X} placed at {pos}"
        for enemy_no, pos in enemy_specs
    )
    return output_path, changes


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outputs = (
        (
            Path("output") / f"flame84_stage1_flame84_only_x13_common_classifier_ai_fallback_restore_{stamp}.nes",
            ((NEW_ENEMY_ID, ENEMY_POS),),
        ),
        (
            Path("output") / f"flame84_compare_80_81_84_common_classifier_ai_fallback_restore_{stamp}.nes",
            COMPARE_ENEMIES,
        ),
    )
    for out_path, enemy_specs in outputs:
        out, changes = build_experiment_rom(output_path=out_path, enemy_specs=enemy_specs)
        print(out)
        for change in changes:
            print(f"- {change}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

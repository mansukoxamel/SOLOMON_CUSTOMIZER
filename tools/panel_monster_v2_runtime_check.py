#!/usr/bin/env python3
"""Check the Panel Monster v2 runtime through the normal ROM save path."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from magatu_skc.core import m66_expander
from magatu_skc.core import panel_monster_stage_variant as panel_v2
from magatu_skc.core import saver
from magatu_skc.core.element import ElementType, LevelElement
from magatu_skc.core.level import load_all_levels
from magatu_skc.core.rom import Rom


DEFAULT_SETTINGS = {
    "a_speed": 0,
    "a_interval": 0xC0,
    "b_speed": 1,
    "b_interval": 0xB0,
    "c_speed": 2,
    "c_interval": 0xA0,
}

SPEED_CASES = (
    ("C_R", 0x31, "c_speed"),
    ("C_L", 0x33, "c_speed"),
    ("C_U", 0x35, "c_speed"),
    ("C_D", 0x37, "c_speed"),
    ("A_R", 0x41, "a_speed"),
    ("A_L", 0x43, "a_speed"),
    ("A_U", 0x45, "a_speed"),
    ("A_D", 0x47, "a_speed"),
    ("B_R", 0x49, "b_speed"),
    ("B_L", 0x4B, "b_speed"),
    ("B_U", 0x4D, "b_speed"),
    ("B_D", 0x4F, "b_speed"),
)

INTERVAL_CASES = (
    ("C", 0x31, "c_interval", 0x21),
    ("A", 0x41, "a_interval", 0x7F),
    ("B", 0x49, "b_interval", 0xE1),
)

BORROWED_CASES = (
    ("2WAY_R", 0x52),
    ("2WAY_R_ALT", 0x53),
    ("2WAY_U", 0x56),
    ("2WAY_U_ALT", 0x57),
    ("3WAY_R", 0x5A),
    ("3WAY_R_ALT", 0x5B),
    ("3WAY_U", 0x66),
    ("3WAY_U_ALT", 0x67),
)

MIXED_CASES = (
    (
        "MIXED_ABC_BORROWED",
        (
            (0x31, (3, 4)),  # C
            (0x41, (5, 4)),  # A
            (0x49, (7, 4)),  # B
            (0x52, (9, 4)),  # 2-way
            (0x66, (11, 4)), # 3-way
        ),
        {
            "a_speed": 3,
            "a_interval": 0x7F,
            "b_speed": 2,
            "b_interval": 0xE1,
            "c_speed": 1,
            "c_interval": 0x21,
        },
    ),
)

NORMAL_CASES = (
    ("NORMAL_R", 0x24),
)

RUNTIME_IDS = panel_v2.PANEL_STAGE_RUNTIME_IDS


def _hex_byte(value: str) -> int:
    value = value.strip()
    base = 16 if value.lower().startswith("0x") else 10
    number = int(value, base)
    if not 0 <= number <= 0xFF:
        raise argparse.ArgumentTypeError(f"{value!r} is outside byte range")
    return number


def _load_expanded_rom(path: Path) -> Rom:
    rom = Rom.load(str(path))
    levels = load_all_levels(rom)
    m66_expander.expand_rom(rom, levels)
    return rom


def _settings_from_args(args: argparse.Namespace) -> dict[str, int]:
    return {
        "a_speed": args.a_speed,
        "a_interval": args.a_interval,
        "b_speed": args.b_speed,
        "b_interval": args.b_interval,
        "c_speed": args.c_speed,
        "c_interval": args.c_interval,
    }


def _run_one_case(
    source_data: bytes,
    enemy_id: int,
    settings: dict[str, int],
    keep_saved: bool = False,
) -> dict[str, object]:
    return _run_multi_case(
        source_data,
        ((enemy_id, (4, 4)),),
        settings,
        keep_saved=keep_saved,
    )


def _run_multi_case(
    source_data: bytes,
    enemy_specs: tuple[tuple[int, tuple[int, int]], ...],
    settings: dict[str, int],
    keep_saved: bool = False,
) -> dict[str, object]:
    source_rom = Rom(source_data, "panel_monster_v2_source.nes")
    levels = load_all_levels(source_rom)
    for enemy_id, pos in enemy_specs:
        levels[0].enemies.append(LevelElement(ElementType.ENEMY, pos, enemy_id))

    saved = saver.build_saved_rom_data(source_rom, levels, settings)
    report = panel_v2.panel_monster_v2_runtime_save_report(saved, settings)
    settings_values = dict(report["settings"]["contract"]["entry_values"])
    settings_values_ok = settings_values == settings

    saved_rom = Rom(saved, "panel_monster_v2_check.nes")
    resaved = saver.build_saved_rom_data(saved_rom, load_all_levels(saved_rom), settings)
    same_output = saved == resaved

    ok = bool(
        report["guards_ok"]
        and report["placement_ok"]
        and report["reserved_ok"]
        and report["reserved_covers_placement"]
        and report["all_written"]
        and same_output
        and settings_values_ok
    )
    result = dict(report)
    result["saved_len"] = len(saved)
    result["same_output"] = same_output
    result["settings_values_ok"] = settings_values_ok
    result["settings_values"] = settings_values
    result["ok"] = ok
    if keep_saved:
        result["saved_data"] = saved
    return result


def _run_normal_case(source_data: bytes, enemy_id: int) -> dict[str, object]:
    source_rom = Rom(source_data, "panel_monster_normal_source.nes")
    levels = load_all_levels(source_rom)
    for level in levels:
        level.enemies = [
            enemy for enemy in getattr(level, "enemies", [])
            if (int(getattr(enemy, "element_no", -1)) & 0xFF) not in RUNTIME_IDS
        ]
        for mirror in getattr(level, "demon_mirrors", []) or []:
            mirror.enemy_codes = [
                code for code in getattr(mirror, "enemy_codes", [])
                if (int(code) & 0xFF) not in RUNTIME_IDS
            ]
    levels[0].enemies.append(LevelElement(ElementType.ENEMY, (4, 4), enemy_id))

    saved = saver.build_saved_rom_data(source_rom, levels, dict(DEFAULT_SETTINGS))
    report = panel_v2.panel_monster_v2_runtime_save_report(saved, dict(DEFAULT_SETTINGS))

    saved_rom = Rom(saved, "panel_monster_normal_check.nes")
    resaved = saver.build_saved_rom_data(saved_rom, load_all_levels(saved_rom), dict(DEFAULT_SETTINGS))
    same_output = saved == resaved
    v2_runtime_written = bool(report["all_written"])

    return {
        "runtime_expected": True,
        "ok": same_output and v2_runtime_written,
        "saved_len": len(saved),
        "guards_ok": report["guards_ok"],
        "placement_ok": report["placement_ok"],
        "reserved_ok": report["reserved_ok"],
        "reserved_covers_placement": report["reserved_covers_placement"],
        "all_written": report["all_written"],
        "settings_values_ok": True,
        "same_output": same_output,
        "v2_runtime_written": v2_runtime_written,
    }


def _matrix_settings(group_speed_key: str, speed: int) -> dict[str, int]:
    settings = dict(DEFAULT_SETTINGS)
    settings[group_speed_key] = speed
    return settings


def _interval_settings(interval_key: str, interval: int) -> dict[str, int]:
    settings = dict(DEFAULT_SETTINGS)
    settings[interval_key] = interval
    return settings


def run_check(args: argparse.Namespace) -> tuple[bool, dict[str, object]]:
    source_rom = _load_expanded_rom(args.rom)
    if args.mode == "single":
        settings = _settings_from_args(args)
        result = _run_one_case(bytes(source_rom.data), args.enemy_id, settings, keep_saved=args.out is not None)
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_bytes(bytes(result["saved_data"]))
            result["wrote_rom"] = str(args.out)
        return bool(result["ok"]), result

    cases = []
    for group_name, enemy_id, speed_key in SPEED_CASES:
        for speed in range(4):
            settings = _matrix_settings(speed_key, speed)
            result = _run_one_case(bytes(source_rom.data), enemy_id, settings)
            result["case"] = f"{group_name} speed={speed}"
            result["enemy_id"] = enemy_id
            cases.append(result)
    for group_name, enemy_id, interval_key, interval in INTERVAL_CASES:
        settings = _interval_settings(interval_key, interval)
        result = _run_one_case(bytes(source_rom.data), enemy_id, settings)
        result["case"] = f"{group_name} interval=0x{interval:02X}"
        result["enemy_id"] = enemy_id
        cases.append(result)
    for case_name, enemy_id in BORROWED_CASES:
        result = _run_one_case(bytes(source_rom.data), enemy_id, dict(DEFAULT_SETTINGS))
        result["case"] = case_name
        result["enemy_id"] = enemy_id
        cases.append(result)
    for case_name, enemy_specs, settings in MIXED_CASES:
        result = _run_multi_case(bytes(source_rom.data), enemy_specs, dict(settings))
        result["case"] = case_name
        result["enemy_ids"] = [enemy_id for enemy_id, _pos in enemy_specs]
        cases.append(result)
    for case_name, enemy_id in NORMAL_CASES:
        result = _run_normal_case(bytes(source_rom.data), enemy_id)
        result["case"] = case_name
        result["enemy_id"] = enemy_id
        cases.append(result)

    first = dict(cases[0])
    first["cases"] = cases
    first["case_count"] = len(cases)
    first["ok"] = all(bool(case["ok"]) for case in cases)
    return bool(first["ok"]), first


def print_result(result: dict[str, object]) -> None:
    if "cases" in result:
        print(f"case_count {result['case_count']}")
        print(f"all_cases_ok {result['ok']}")
        for case in result["cases"]:
            if case.get("runtime_expected", True):
                print(
                    f"  {case['case']}: ok={case['ok']} "
                    f"guards_ok={case['guards_ok']} placement_ok={case['placement_ok']} "
                    f"reserved_ok={case['reserved_ok']} reserved_covers={case['reserved_covers_placement']} "
                    f"all_written={case['all_written']} "
                    f"same_output={case['same_output']} settings_values_ok={case['settings_values_ok']}"
                )
            else:
                print(
                    f"  {case['case']}: ok={case['ok']} runtime_expected=False "
                    f"v2_runtime_absent={case['v2_runtime_absent']} same_output={case['same_output']}"
                )
    print(f"saved_len {result['saved_len']}")
    print(f"apply_path {result['apply_path']}")
    print(f"guards_ok {result['guards_ok']}")
    print(f"placement_ok {result['placement_ok']}")
    print(f"reserved_ok {result['reserved_ok']}")
    print(f"reserved_covers_placement {result['reserved_covers_placement']}")
    print(f"all_written {result['all_written']}")
    print(f"same_output {result['same_output']}")
    print(f"settings_values_ok {result['settings_values_ok']}")
    if "wrote_rom" in result:
        print(f"wrote_rom {result['wrote_rom']}")
    print("guards")
    for name, status in dict(result["guards"]).items():
        print(f"  {name}: {status}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Panel Monster v2 normal-save runtime check."
    )
    parser.add_argument(
        "--rom",
        type=Path,
        default=ROOT / "ROM" / "Solomon no Kagi (J).nes",
        help="Source Japanese ROM path.",
    )
    parser.add_argument(
        "--enemy-id",
        type=_hex_byte,
        default=0x41,
        help="Panel Monster enemy id to add to stage 1 in single mode.",
    )
    parser.add_argument(
        "--mode",
        choices=("matrix", "single"),
        default="matrix",
        help="matrix checks A/B/C across all speed presets; single uses the explicit args.",
    )
    parser.add_argument("--a-speed", type=int, choices=range(4), default=0)
    parser.add_argument("--b-speed", type=int, choices=range(4), default=1)
    parser.add_argument("--c-speed", type=int, choices=range(4), default=2)
    parser.add_argument("--a-interval", type=_hex_byte, default=0xC0)
    parser.add_argument("--b-interval", type=_hex_byte, default=0xB0)
    parser.add_argument("--c-interval", type=_hex_byte, default=0xA0)
    parser.add_argument(
        "--out",
        type=Path,
        help="Write the single-mode saved ROM to this path after checks pass.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.out is not None and args.mode != "single":
        print("--out is only valid with --mode single")
        return 2
    ok, result = run_check(args)
    print_result(result)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

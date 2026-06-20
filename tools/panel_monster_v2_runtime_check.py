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

MATRIX_CASES = (
    ("C", 0x31, "c_speed"),
    ("A", 0x41, "a_speed"),
    ("B", 0x49, "b_speed"),
)


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
) -> dict[str, object]:
    source_rom = Rom(source_data, "panel_monster_v2_source.nes")
    levels = load_all_levels(source_rom)
    levels[0].enemies.append(LevelElement(ElementType.ENEMY, (4, 4), enemy_id))

    saved = saver.build_saved_rom_data(source_rom, levels, settings)
    report = panel_v2.panel_monster_v2_runtime_save_report(saved, settings)

    saved_rom = Rom(saved, "panel_monster_v2_check.nes")
    resaved = saver.build_saved_rom_data(saved_rom, load_all_levels(saved_rom), settings)
    same_output = saved == resaved

    ok = bool(report["guards_ok"] and report["all_written"] and same_output)
    result = dict(report)
    result["saved_len"] = len(saved)
    result["same_output"] = same_output
    result["ok"] = ok
    return result


def _matrix_settings(group_speed_key: str, speed: int) -> dict[str, int]:
    settings = dict(DEFAULT_SETTINGS)
    settings[group_speed_key] = speed
    return settings


def run_check(args: argparse.Namespace) -> tuple[bool, dict[str, object]]:
    source_rom = _load_expanded_rom(args.rom)
    if args.mode == "single":
        settings = _settings_from_args(args)
        result = _run_one_case(bytes(source_rom.data), args.enemy_id, settings)
        return bool(result["ok"]), result

    cases = []
    for group_name, enemy_id, speed_key in MATRIX_CASES:
        for speed in range(4):
            settings = _matrix_settings(speed_key, speed)
            result = _run_one_case(bytes(source_rom.data), enemy_id, settings)
            result["case"] = f"{group_name} speed={speed}"
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
            print(
                f"  {case['case']}: ok={case['ok']} "
                f"guards_ok={case['guards_ok']} all_written={case['all_written']} "
                f"same_output={case['same_output']}"
            )
    print(f"saved_len {result['saved_len']}")
    print(f"apply_path {result['apply_path']}")
    print(f"guards_ok {result['guards_ok']}")
    print(f"all_written {result['all_written']}")
    print(f"same_output {result['same_output']}")
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    ok, result = run_check(args)
    print_result(result)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

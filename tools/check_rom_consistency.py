from __future__ import annotations

import ast
import importlib
import re
import sys
import unittest
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = ROOT / "magatu_skc" / "core"
LEDGER_PATH = ROOT / "docs" / "rom_map_jp_mapper66_current.html"
INACTIVE_RESERVATION_MODULES = {"gap_fix"}

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class ReservedSpan:
    module: str
    start: int
    end: int

    @property
    def size(self) -> int:
        return self.end - self.start + 1

    def label(self) -> str:
        return f"{self.module}: 0x{self.start:X}-0x{self.end:X} ({self.size}B)"


@dataclass(frozen=True)
class LedgerRow:
    kind: str
    start: int
    end: int

    @property
    def size(self) -> int:
        return self.end - self.start + 1

    def label(self) -> str:
        return f"{self.kind}: 0x{self.start:X}-0x{self.end:X} ({self.size}B)"


class LedgerParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[LedgerRow] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "tr":
            return
        values = dict(attrs)
        kind = values.get("class")
        start = values.get("data-start")
        end = values.get("data-end")
        if kind not in {"used", "free"} or start is None or end is None:
            return
        self.rows.append(LedgerRow(kind, int(start, 16), int(end, 16)))


def _module_defines_reserved_spans(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "RESERVED_SPANS" for target in node.targets):
                return True
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "RESERVED_SPANS":
                return True
    return False


def collect_reserved_spans() -> list[ReservedSpan]:
    spans: list[ReservedSpan] = []
    for path in sorted(CORE_DIR.glob("*.py")):
        if path.stem in INACTIVE_RESERVATION_MODULES:
            continue
        if not _module_defines_reserved_spans(path):
            continue
        module = importlib.import_module(f"magatu_skc.core.{path.stem}")
        for raw_start, raw_size in module.RESERVED_SPANS:
            start = int(raw_start)
            size = int(raw_size)
            if start < 0:
                raise AssertionError(f"{path.stem}: negative start {start}")
            if size <= 0:
                raise AssertionError(f"{path.stem}: invalid size {size} at 0x{start:X}")
            spans.append(ReservedSpan(path.stem, start, start + size - 1))
    return spans


def collect_ram_reserved_spans() -> list[ReservedSpan]:
    spans: list[ReservedSpan] = []
    for path in sorted(CORE_DIR.glob("*.py")):
        module = importlib.import_module(f"magatu_skc.core.{path.stem}")
        for raw_start, raw_size in getattr(module, "RAM_RESERVED_SPANS", ()):
            start = int(raw_start)
            size = int(raw_size)
            if start < 0 or start > 0x07FF:
                raise AssertionError(f"{path.stem}: invalid RAM start 0x{start:X}")
            if size <= 0 or start + size > 0x0800:
                raise AssertionError(f"{path.stem}: invalid RAM size {size} at 0x{start:X}")
            spans.append(ReservedSpan(path.stem, start, start + size - 1))
    return spans


def unique_reserved_spans(spans: list[ReservedSpan]) -> list[ReservedSpan]:
    unique: dict[tuple[int, int], ReservedSpan] = {}
    for span in spans:
        unique.setdefault((span.start, span.end), span)
    return sorted(unique.values(), key=lambda span: (span.start, span.end))


def read_ledger() -> tuple[str, list[LedgerRow]]:
    text = LEDGER_PATH.read_text(encoding="utf-8", errors="strict")
    parser = LedgerParser()
    parser.feed(text)
    parser.close()
    return text, parser.rows


class RomReservationTests(unittest.TestCase):
    def test_reserved_spans_do_not_overlap(self) -> None:
        collected = collect_reserved_spans()
        grouped: dict[tuple[int, int], list[ReservedSpan]] = {}
        for span in collected:
            grouped.setdefault((span.start, span.end), []).append(span)

        aggregators = {"new_enemy_runtime", "spark_ball_variant"}
        shared_direct_owners = {
            frozenset(("panel_monster_stage_variant", "stage_ext")),
        }
        for duplicates in grouped.values():
            if len(duplicates) == 1:
                continue
            aggregate_copies = [span for span in duplicates if span.module in aggregators]
            direct_owners = [span for span in duplicates if span.module not in aggregators]
            if not aggregate_copies and frozenset(span.module for span in direct_owners) in shared_direct_owners:
                continue
            self.assertEqual(
                len(aggregate_copies),
                1,
                "An exact duplicate is not owned by one known runtime aggregator: "
                + " / ".join(span.label() for span in duplicates),
            )
            self.assertEqual(
                len(direct_owners),
                1,
                "Multiple direct runtime owners use the same ROM range: "
                + " / ".join(span.label() for span in duplicates),
            )

        spans = unique_reserved_spans(collected)
        self.assertGreater(len(spans), 0, "No RESERVED_SPANS were found")
        for previous, current in zip(spans, spans[1:]):
            self.assertGreater(
                current.start,
                previous.end,
                f"ROM reservation overlap: {previous.label()} / {current.label()}",
            )


class RomLedgerTests(unittest.TestCase):
    def test_ledger_matches_reserved_spans(self) -> None:
        text, rows = read_ledger()
        self.assertGreater(len(rows), 0, "No ROM ledger rows were found")

        ordered_rows = sorted(rows, key=lambda row: (row.start, row.end))
        for previous, current in zip(ordered_rows, ordered_rows[1:]):
            self.assertGreater(
                current.start,
                previous.end,
                f"ROM ledger overlap: {previous.label()} / {current.label()}",
            )

        used_rows = [row for row in rows if row.kind == "used"]
        free_rows = [row for row in rows if row.kind == "free"]
        for span in unique_reserved_spans(collect_reserved_spans()):
            self.assertTrue(
                any(row.start <= span.start and span.end <= row.end for row in used_rows),
                f"RESERVED_SPANS is not covered by a used ledger row: {span.label()}",
            )
            self.assertFalse(
                any(span.start <= row.end and row.start <= span.end for row in free_rows),
                f"RESERVED_SPANS intersects a free ledger row: {span.label()}",
            )

        summary_match = re.search(
            r'<div class="summary">.*?'
            r'<strong>(\d+)</strong> ranges.*?'
            r'<strong>(\d+)</strong> used.*?'
            r'<strong>(\d+)</strong> free.*?'
            r'<strong>(\d+)B</strong> explicitly free.*?</div>',
            text,
        )
        self.assertIsNotNone(summary_match, "ROM ledger summary was not found")
        declared = tuple(int(value) for value in summary_match.groups())
        actual = (
            len(rows),
            len(used_rows),
            len(free_rows),
            sum(row.size for row in free_rows),
        )
        self.assertEqual(declared, actual, "ROM ledger summary does not match its rows")


class RamReservationTests(unittest.TestCase):
    def test_custom_ram_reservations_are_complete_and_overlap_only_by_contract(self) -> None:
        spans = collect_ram_reserved_spans()
        self.assertGreater(len(spans), 0, "No RAM_RESERVED_SPANS were found")

        owners_by_byte: dict[int, set[str]] = {}
        for span in spans:
            for address in range(span.start, span.end + 1):
                owners_by_byte.setdefault(address, set()).add(span.module)

        expected_bytes = (
            set(range(0x0723, 0x073A))
            | set(range(0x0740, 0x0774))
            | set(range(0x0774, 0x0777))
            | set(range(0x0778, 0x077B))
            | set(range(0x077C, 0x0780))
        )
        self.assertEqual(set(owners_by_byte), expected_bytes, "Customizer RAM allocation changed")

        shared_owners = {
            0x0724: {"enemy_clear_key_open", "key_enemy_runtime"},
            0x0770: {"enemy_clear_key_open", "panel_monster_stage_variant", "warp_zone_trial"},
            0x0771: {"enemy_clear_key_open", "fire2_item_runtime"},
            0x077C: {"fire2_item_runtime", "stage_ext"},
            0x077D: {"solomon_seal_block", "stage_ext"},
        }
        actual_shared = {
            address: owners for address, owners in owners_by_byte.items() if len(owners) > 1
        }
        self.assertEqual(actual_shared, shared_owners, "Customizer RAM sharing contract changed")


class NewEnemyRegistrationTests(unittest.TestCase):
    def test_enemy_ids_and_runtimes_are_registered(self) -> None:
        from magatu_skc.core import chaos_dragon9e_runtime
        from magatu_skc.core import fairy9c_runtime
        from magatu_skc.core import ghostb0_runtime
        from magatu_skc.core import ice_flame_runtime
        from magatu_skc.core import neul84_runtime
        from magatu_skc.core import new_enemy_runtime
        from magatu_skc.core import phantom_preset_runtime
        from magatu_skc.core import panel_monster_stage_variant
        from magatu_skc.core import seraphic_radiance9d_runtime
        from magatu_skc.core import spark24_runtime
        from magatu_skc.core import spark_ball_variant

        families = {
            "ice_flame": (ice_flame_runtime.NEW_ENEMY_ID,),
            "neul_ab": tuple(neul84_runtime.NEW_ENEMY_IDS),
            "dark_fairy": (fairy9c_runtime.NEW_ENEMY_ID,),
            "seraphic_radiance": (seraphic_radiance9d_runtime.NEW_ENEMY_ID,),
            "chaos_dragon": (chaos_dragon9e_runtime.NEW_ENEMY_ID,),
            "phantom_preset": tuple(range(phantom_preset_runtime.FIRST_ID, phantom_preset_runtime.LAST_ID + 1)),
            "enhanced_ghost": tuple(ghostb0_runtime.NEW_ENEMY_IDS),
            "spark24": tuple(range(spark24_runtime.FIRST_ID, spark24_runtime.LAST_ID + 1)),
            "panel_monster": tuple(panel_monster_stage_variant.PANEL_STAGE_RUNTIME_IDS),
        }
        expected = {
            "ice_flame": (0x82,),
            "neul_ab": tuple(range(0x84, 0x88)),
            "dark_fairy": (0x9C,),
            "seraphic_radiance": (0x9D,),
            "chaos_dragon": (0x9E,),
            "phantom_preset": tuple(range(0xA0, 0xB0)),
            "enhanced_ghost": tuple(range(0xB0, 0xBC)),
            "spark24": tuple(range(0xC0, 0xD8)),
            "panel_monster": tuple(range(0xE0, 0xF8)),
        }
        self.assertEqual(families, expected, "A formal enemy ID assignment changed")

        owners: dict[int, str] = {}
        for family, enemy_ids in families.items():
            for enemy_id in enemy_ids:
                self.assertGreaterEqual(enemy_id, 0)
                self.assertLessEqual(enemy_id, 0xFF)
                self.assertNotIn(
                    enemy_id,
                    owners,
                    f"Enemy ID ${enemy_id:02X} is shared by {owners.get(enemy_id)} and {family}",
                )
                owners[enemy_id] = family

        exported_ids = {
            "ice_flame": (new_enemy_runtime.ICE_FLAME_ID,),
            "neul_ab": tuple(range(new_enemy_runtime.NEUL84_FIRST_ID, new_enemy_runtime.NEUL84_LAST_ID + 1)),
            "dark_fairy": (new_enemy_runtime.FAIRY9C_ID,),
            "seraphic_radiance": (new_enemy_runtime.RADIANCE9D_ID,),
            "chaos_dragon": (new_enemy_runtime.CHAOS9E_ID,),
            "phantom_preset": tuple(range(new_enemy_runtime.PHANTOM_PRESET_FIRST_ID, new_enemy_runtime.PHANTOM_PRESET_LAST_ID + 1)),
            "enhanced_ghost": tuple(range(new_enemy_runtime.GHOSTB0_FIRST_ID, new_enemy_runtime.GHOSTB0_LAST_ID + 1)),
            "spark24": tuple(range(new_enemy_runtime.SPARK24_FIRST_ID, new_enemy_runtime.SPARK24_LAST_ID + 1)),
        }
        expected_common = {name: ids for name, ids in expected.items() if name != "panel_monster"}
        self.assertEqual(exported_ids, expected_common, "new_enemy_runtime exports the wrong enemy IDs")

        common_spans = {tuple(span) for span in new_enemy_runtime.RESERVED_SPANS}
        common_modules = (
            ice_flame_runtime,
            neul84_runtime,
            fairy9c_runtime,
            seraphic_radiance9d_runtime,
            chaos_dragon9e_runtime,
            phantom_preset_runtime,
            ghostb0_runtime,
        )
        for module in common_modules:
            missing = {tuple(span) for span in module.RESERVED_SPANS} - common_spans
            self.assertFalse(missing, f"{module.__name__} runtime is missing from new_enemy_runtime: {missing}")

        spark_spans = {tuple(span) for span in spark_ball_variant.RESERVED_SPANS}
        missing_spark = {tuple(span) for span in spark24_runtime.RESERVED_SPANS} - spark_spans
        self.assertFalse(missing_spark, f"Spark24 runtime is missing from spark_ball_variant: {missing_spark}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

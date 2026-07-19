from __future__ import annotations

import unittest

from magatu_skc.core import gargoyle_variant as target


def _applied_rom() -> bytearray:
    rom = bytearray([0xEA] * 0x7000)
    rom[target.OFF_CAVE_GATE:target.OFF_CAVE_GATE + len(target.CAVE_GATE)] = target.CAVE_GATE
    rom[
        target.OFF_CAVE_SECOND_SHOT:
        target.OFF_CAVE_SECOND_SHOT + len(target.CAVE_SECOND_SHOT)
    ] = target.CAVE_SECOND_SHOT
    rom[
        target.OFF_CAVE_HELPERS:
        target.OFF_CAVE_HELPERS + len(target.CAVE_HELPERS)
    ] = target.CAVE_HELPERS
    rom[target.OFF_HOOK_STATE3:target.OFF_HOOK_STATE3 + 2] = target.HOOK_STATE3
    rom[target.OFF_HOOK_STATE4:target.OFF_HOOK_STATE4 + 2] = target.HOOK_STATE4
    return rom


class GargoyleVariantRuntimeTests(unittest.TestCase):
    def test_all_supported_markers_round_trip(self) -> None:
        for preset, (_label, marker) in target.BULLET_SPEED_PRESETS.items():
            self.assertEqual(target._speed_preset_from_marker(marker), preset)

    def test_unknown_marker_is_rejected(self) -> None:
        with self.assertRaisesRegex(target.GargoyleVariantError, r"marker: \$02"):
            target._speed_preset_from_marker(0x02)

    def test_current_settings_rejects_unknown_rom_marker(self) -> None:
        rom = _applied_rom()
        rom[target.OFF_MARKER_A_VALUE] = 0x02
        with self.assertRaisesRegex(target.GargoyleVariantError, r"marker: \$02"):
            target.current_settings(rom, "a")

    def test_runtime_layout_is_stable(self) -> None:
        self.assertEqual(len(target.CAVE_GATE), 71)
        self.assertEqual(len(target.CAVE_SECOND_SHOT), 105)
        self.assertEqual(len(target.CAVE_HELPERS), 105)
        self.assertEqual(target.OFF_CAVE_HELPERS + len(target.CAVE_HELPERS), 0x6E19)

    def test_speed_normalizer_restores_stock_state_field_offset(self) -> None:
        self.assertEqual(len(target.CAVE_SPEED_INIT), 41)
        self.assertIn(bytes.fromhex("68 a0 04 4c c0 8a"), target.CAVE_SPEED_INIT)
        self.assertNotIn(bytes.fromhex("c8 98 aa 68 4c c0 8a"), target.CAVE_SPEED_INIT)


if __name__ == "__main__":
    unittest.main()

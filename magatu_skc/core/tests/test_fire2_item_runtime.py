from __future__ import annotations

import unittest

from magatu_skc.core import fire2_item_runtime as target
from magatu_skc.core import panel_monster_stage_variant


class SpecialItemRuntimeTests(unittest.TestCase):
    def _fresh_mapper66_rom(self) -> bytearray:
        rom = bytearray(target.OFF_PRG1_SPECIAL_ITEM_TABLE + target.PRG1_SPECIAL_ITEM_TABLE_SIZE)
        rom[target.OFF_ITEM_PICKUP_HOOK:target.OFF_ITEM_PICKUP_HOOK + 3] = target.ORIG_ITEM_PICKUP_HOOK
        rom[target.OFF_DRAW_HOOK:target.OFF_DRAW_HOOK + 3] = target.ORIG_DRAW_HOOK
        rom[target.OFF_FIRE_HIT_HOOK:target.OFF_FIRE_HIT_HOOK + 10] = target.ORIG_FIRE_HIT_HOOK
        rom[target.OFF_FIRE_RANGE_CAP] = target.ORIG_FIRE_RANGE_CAP
        rom[target.OFF_RUNTIME:target.OFF_RUNTIME + len(target.RUNTIME)] = b"\xEA" * len(target.RUNTIME)
        loader_off = panel_monster_stage_variant.OFF_PRG1_RUNTIME_LOADER
        rom[loader_off:loader_off + 3] = panel_monster_stage_variant.RUNTIME_LOADER_SLOT[:3]
        helper_end = target.OFF_PRG1_LOADER_HELPER + len(target.CURRENT_PRG1_LOADER_HELPER)
        rom[target.OFF_PRG1_LOADER_HELPER:helper_end] = b"\xEA" * len(target.CURRENT_PRG1_LOADER_HELPER)
        return rom

    def test_deleted_door_guard_covers_only_visible_cell_range(self) -> None:
        sequence = bytes.fromhex("ae 7c 07 e0 10 90")
        start = target.ITEM_RUNTIME.index(sequence)
        self.assertEqual(target.ITEM_RUNTIME.count(sequence), 1)
        self.assertEqual(target.ITEM_RUNTIME[start + 7:start + 10], bytes.fromhex("e0 d0 b0"))

        targets = []
        for operand in (start + 6, start + 10):
            displacement = target.ITEM_RUNTIME[operand]
            if displacement >= 0x80:
                displacement -= 0x100
            targets.append(operand + 1 + displacement)
        self.assertEqual(targets[0], targets[1])
        self.assertEqual(
            target.ITEM_RUNTIME[targets[0]:targets[0] + 7],
            bytes.fromhex("a9 40 85 02 a9 01 60"),
        )

    def test_layout_stays_within_existing_326_byte_prg0_span(self) -> None:
        self.assertEqual(len(target.ITEM_RUNTIME), 213)
        self.assertEqual(len(target.DRAW_RUNTIME), 84)
        self.assertEqual(len(target.RUNTIME), 326)
        self.assertEqual(target.OFF_RUNTIME + len(target.RUNTIME) - 1, 0x4155)
        self.assertEqual(target.CPU_DRAW_RUNTIME, 0xC0D5)

    def test_normal_range_growth_cap_remains_intentional_extended_value(self) -> None:
        self.assertEqual(target.ORIG_FIRE_RANGE_CAP, 0x02)
        self.assertEqual(target.FIRE_RANGE_CAP_HIGH, 0x0F)
        self.assertEqual(target.MAX_FIRE_RANGE_BYTE, 0x1F)

    def test_apply_installs_current_runtime_into_fresh_mapper66_layout(self) -> None:
        rom = self._fresh_mapper66_rom()
        changed = target.apply(rom, [])
        self.assertTrue(changed)
        self.assertEqual(bytes(rom[target.OFF_RUNTIME:target.OFF_RUNTIME + 326]), target.RUNTIME)
        self.assertEqual(bytes(rom[target.OFF_DRAW_HOOK:target.OFF_DRAW_HOOK + 3]), target.HOOK_DRAW)
        self.assertEqual(rom[target.OFF_FIRE_RANGE_CAP], 0x0F)
        self.assertEqual(
            bytes(rom[target.OFF_PRG1_LOADER_HELPER:target.OFF_PRG1_LOADER_HELPER + 140]),
            target.CURRENT_PRG1_LOADER_HELPER,
        )

    def test_prg1_reservation_uses_the_current_panel_loader(self) -> None:
        expected = target._build_loader_helper(panel_monster_stage_variant.RUNTIME_LOADER)
        self.assertEqual(target.CURRENT_PRG1_LOADER_HELPER, expected)
        self.assertEqual(target.PRG1_RESERVED_SPANS[0], (target.OFF_PRG1_LOADER_HELPER, len(expected)))

    def test_legacy_draw_hook_is_rejected(self) -> None:
        legacy_draw_hook = bytes.fromhex("4c 0d ed")
        rom = bytearray(target.OFF_DRAW_HOOK + len(legacy_draw_hook))
        rom[target.OFF_DRAW_HOOK:target.OFF_DRAW_HOOK + len(legacy_draw_hook)] = legacy_draw_hook
        with self.assertRaises(target.Fire2ItemRuntimeError):
            target._expect(
                rom,
                target.OFF_DRAW_HOOK,
                (target.ORIG_DRAW_HOOK, target.HOOK_DRAW),
                "draw hook",
            )


if __name__ == "__main__":
    unittest.main()

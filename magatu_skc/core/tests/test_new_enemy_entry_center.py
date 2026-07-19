from __future__ import annotations

import unittest
from types import SimpleNamespace

from magatu_skc.core.element import ElementType
from magatu_skc.core import new_enemy_runtime as target


class NewEnemyEntryCenterTests(unittest.TestCase):
    @staticmethod
    def _branch_target(blob: bytes, opcode_pos: int) -> int:
        displacement = blob[opcode_pos + 1]
        if displacement >= 0x80:
            displacement -= 0x100
        return opcode_pos + 2 + displacement

    def test_all_enhanced_saramandor_groups_use_the_same_spr2_branch(self) -> None:
        targets = []
        for enemy_id in (0x5E, 0x62, 0x66):
            sequence = bytes((0xC9, enemy_id, 0xF0))
            compare_pos = target.ANIM_ENTRY_RUNTIME.index(sequence)
            targets.append(self._branch_target(target.ANIM_ENTRY_RUNTIME, compare_pos + 2))
        self.assertEqual(targets[0], targets[1])
        self.assertEqual(targets[1], targets[2])
        self.assertEqual(
            target.ANIM_ENTRY_RUNTIME[targets[0]:targets[0] + 3],
            bytes.fromhex("20 89 87"),
        )

    def test_ghost_extension_and_all_internal_entries_move_four_bytes(self) -> None:
        self.assertEqual(target.OFF_GHOSTB0_EXTENSION, 0x3D65)
        self.assertEqual(target.CPU_GHOSTB0_AI_CLASSIFY, 0xBD55)
        self.assertEqual(target.CPU_GHOSTB0_SETUP_CLASSIFY, 0xBD63)
        self.assertEqual(target.CPU_GHOSTB0_INIT_CLASSIFY, 0xBD73)
        self.assertIn(bytes.fromhex("4c 55 bd"), target.AI_ENTRY_RUNTIME)
        self.assertIn(bytes.fromhex("4c 63 bd"), target.SETUP_ENTRY_RUNTIME)
        self.assertIn(bytes.fromhex("4c 73 bd"), target.INIT_ENTRY_RUNTIME)

    def test_entry_center_uses_427_bytes_and_leaves_15_byte_gap(self) -> None:
        self.assertEqual(len(target.ANIM_ENTRY_RUNTIME), 133)
        self.assertEqual(len(target.GHOSTB0_EXTENSION_RUNTIME), 56)
        self.assertEqual(target.OFF_GHOSTB0_EXTENSION + len(target.GHOSTB0_EXTENSION_RUNTIME), 0x3D9D)
        self.assertEqual(0x3DAC - 0x3D9D, 15)

    def test_short_legacy_prefix_is_not_accepted(self) -> None:
        rom = bytearray(target.OFF_ANIM_ENTRY + len(target.ANIM_ENTRY_RUNTIME))
        legacy_prefix = bytes.fromhex("a0 01 b1 08 c9 84 f0 03 4c 89 87 4c 92 e0")
        rom[target.OFF_ANIM_ENTRY:target.OFF_ANIM_ENTRY + len(legacy_prefix)] = legacy_prefix
        before = bytes(rom)
        with self.assertRaises(target.NewEnemyRuntimeError):
            target._expect_blank_or(
                rom,
                target.OFF_ANIM_ENTRY,
                target.ANIM_ENTRY_RUNTIME,
                "animation entry",
            )
        self.assertEqual(bytes(rom), before)

    def test_legacy_ice_only_hook_is_not_accepted(self) -> None:
        rom = bytearray(target._ice.OFF_AI_DISPATCH_CALL + 3)
        rom[target._ice.OFF_AI_DISPATCH_CALL:target._ice.OFF_AI_DISPATCH_CALL + 3] = (
            target._ice.HOOK_AI_DISPATCH_CALL
        )
        with self.assertRaises(target.NewEnemyRuntimeError):
            target._expect_one(
                rom,
                target._ice.OFF_AI_DISPATCH_CALL,
                (target._ice.ORIG_AI_DISPATCH_CALL, target.HOOK_AI_DISPATCH_CALL),
                "AI hook",
            )

    def test_mirror_enemy_sets_detect_every_new_enemy_family(self) -> None:
        new_enemy_ids = (
            0x82, 0x84, 0x87, 0x9C, 0x9D, 0x9E,
            0xA0, 0xAF, 0xB0, 0xBB, 0xC0, 0xD7, 0xE0, 0xF7,
        )
        for enemy_id in new_enemy_ids:
            with self.subTest(enemy_id=enemy_id):
                mirror = SimpleNamespace(enemy_codes=[enemy_id])
                level = SimpleNamespace(enemies=[], demon_mirrors=[mirror])
                self.assertTrue(target.levels_need_runtime([level]))

    def test_stock_mirror_enemy_set_does_not_require_new_enemy_runtime(self) -> None:
        mirror = SimpleNamespace(enemy_codes=[0x14, 0x80, 0x81, 0x83])
        level = SimpleNamespace(enemies=[], demon_mirrors=[mirror])
        self.assertFalse(target.levels_need_runtime([level]))

    def test_direct_ice_burn_still_requires_new_enemy_runtime(self) -> None:
        enemy = SimpleNamespace(type=ElementType.ENEMY, element_no=0x82)
        level = SimpleNamespace(enemies=[enemy], demon_mirrors=[])
        self.assertTrue(target.levels_need_runtime([level]))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from magatu_skc.core import enemy_clear_key_open as target


class EnemyClearKeyOpenRuntimeTests(unittest.TestCase):
    def _blank_rom(self) -> bytearray:
        rom = bytearray(target.OFF_RUNTIME + len(target.RUNTIME))
        rom[target.OFF_RUNTIME:target.OFF_RUNTIME + len(target.RUNTIME)] = b"\xEA" * len(target.RUNTIME)
        rom[target.OFF_MAIN_LOOP_HOOK:target.OFF_MAIN_LOOP_HOOK + 3] = target.ORIG_MAIN_LOOP_HOOK
        return rom

    def test_unbeatable_blue_burn_ids_are_ignored_by_one_masked_check(self) -> None:
        sequence = bytes.fromhex("29 fd c9 81 f0")
        start = target.RUNTIME.index(sequence)
        self.assertEqual(target.RUNTIME.count(sequence), 1)

        branch_operand = start + len(sequence)
        displacement = target.RUNTIME[branch_operand]
        if displacement >= 0x80:
            displacement -= 0x100
        branch_target = branch_operand + 1 + displacement
        self.assertEqual(target.RUNTIME[branch_target], 0xCA)  # DEX at scan_next

        ignored = lambda enemy_id: (enemy_id & 0xFD) == 0x81
        self.assertTrue(ignored(0x81))
        self.assertTrue(ignored(0x83))
        self.assertFalse(ignored(0x80))
        self.assertFalse(ignored(0x82))
        self.assertFalse(ignored(0x84))

    def test_runtime_is_130_bytes_and_installs_into_blank_area(self) -> None:
        rom = self._blank_rom()
        changed = target.apply(rom, [])
        self.assertEqual(bytes(rom[target.OFF_RUNTIME:target.OFF_RUNTIME + 130]), target.RUNTIME)
        self.assertEqual(bytes(rom[target.OFF_MAIN_LOOP_HOOK:target.OFF_MAIN_LOOP_HOOK + 3]), target.HOOK_MAIN_LOOP)
        self.assertEqual(len(changed), 2)

    def test_nonblank_noncurrent_runtime_is_rejected_before_mutation(self) -> None:
        rom = self._blank_rom()
        rom[target.OFF_RUNTIME] = 0x01
        before = bytes(rom)
        with self.assertRaises(target.EnemyClearKeyOpenError):
            target.apply(rom, [])
        self.assertEqual(bytes(rom), before)


if __name__ == "__main__":
    unittest.main()

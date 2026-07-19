from __future__ import annotations

import unittest

from magatu_skc.core import fairy9c_runtime as fairy
from magatu_skc.core import key_enemy_runtime
from magatu_skc.core import new_enemy_runtime
from magatu_skc.core import seraphic_radiance9d_runtime as target


class SeraphicRadianceRuntimeTests(unittest.TestCase):
    @staticmethod
    def _branch_target(blob: bytes, opcode_pos: int) -> int:
        displacement = int.from_bytes(blob[opcode_pos + 1:opcode_pos + 2], signed=True)
        return opcode_pos + 2 + displacement

    def test_setup_reuses_the_shared_fairy_group_helper(self) -> None:
        self.assertEqual(target.CPU_SETUP_META_LOAD, fairy.CPU_SETUP_META_LOAD)
        self.assertIn(bytes.fromhex("4c 00 e0"), new_enemy_runtime.SETUP_ENTRY_RUNTIME)

    def test_init_clears_stock_y_velocity_without_rewriting_type(self) -> None:
        self.assertIn(
            bytes.fromhex("a9 00 a0 05 91 00 20 1c 9d"),
            target.INIT_STATUS_RUNTIME,
        )
        self.assertNotIn(bytes.fromhex("a9 9d 85 05"), target.INIT_STATUS_RUNTIME)
        self.assertEqual(len(target.INIT_STATUS_RUNTIME), 44)

    def test_top_turn_always_reaches_collision_scan(self) -> None:
        runtime = target.AI_DISPATCH_RUNTIME
        sequence = bytes.fromhex("a0 07 b1 2c 29 fe 91 2c 10")
        start = runtime.index(sequence)
        branch_pos = start + len(sequence) - 1
        target_pos = self._branch_target(runtime, branch_pos)
        self.assertEqual(target_pos, target._AI_LABELS["collide"] - target.CPU_AI_DISPATCH)

    def test_collision_scan_skips_the_selected_key_slot(self) -> None:
        runtime = target.AI_DISPATCH_RUNTIME
        compare = bytes((
            0xEC,
            key_enemy_runtime.RAM_TARGET_RUNTIME_SLOT & 0xFF,
            key_enemy_runtime.RAM_TARGET_RUNTIME_SLOT >> 8,
            0xF0,
        ))
        start = runtime.index(compare)
        branch_pos = start + 3
        target_pos = self._branch_target(runtime, branch_pos)
        self.assertEqual(target_pos, target._AI_LABELS["next"] - target.CPU_AI_DISPATCH)

    def test_runtime_shrinks_one_byte_and_leaves_the_next_runtime_fixed(self) -> None:
        self.assertEqual(len(target.RUNTIME), 296)
        self.assertEqual(target.RUNTIME_CAPACITY - len(target.RUNTIME), 1)
        self.assertEqual(target.OFF_RUNTIME + len(target.RUNTIME), 0x6D2C)
        self.assertEqual(target.CPU_RUNTIME_END, 0xED1C)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from magatu_skc.core import chaos_dragon9e_runtime as target


class ChaosDragonRuntimeTests(unittest.TestCase):
    def test_runtime_layout_is_stable(self) -> None:
        self.assertEqual(target.OFF_RUNTIME, 0x6EB4)
        self.assertEqual(target.CPU_RUNTIME, 0xEEA4)
        self.assertEqual(len(target.SETUP_META_RUNTIME), 10)
        self.assertEqual(len(target.INIT_STATUS_RUNTIME), 16)
        self.assertEqual(len(target.AI_DISPATCH_RUNTIME), 3)
        self.assertEqual(len(target.RUNTIME), 29)
        self.assertEqual(target.CPU_RUNTIME_END, 0xEEC1)

    def test_setup_uses_dragon_visuals_and_speed_group_zero(self) -> None:
        self.assertEqual(
            target.SETUP_META_RUNTIME,
            bytes.fromhex("a9 34 85 0e a0 00 b9 d3 d9 60"),
        )

    def test_init_clears_property_velocity_and_enters_dragon_state_five(self) -> None:
        self.assertEqual(
            target.INIT_STATUS_RUNTIME,
            bytes.fromhex("68 a9 c0 85 04 a0 05 a9 00 91 00 a9 14 4c 1c 9d"),
        )

    def test_ai_tail_calls_stock_dragon(self) -> None:
        self.assertEqual(target.AI_DISPATCH_RUNTIME, bytes.fromhex("4c 4a a6"))


if __name__ == "__main__":
    unittest.main()

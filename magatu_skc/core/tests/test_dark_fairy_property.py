from __future__ import annotations

import unittest

from magatu_skc.core import fairy9c_runtime as fairy
from magatu_skc.core import ghostb0_runtime as shared
from magatu_skc.core import new_enemy_runtime
from magatu_skc.core import panel_monster_stage_variant as panel


class DarkFairyPropertyTests(unittest.TestCase):
    def test_shared_property_tail_returns_stock_fairy_property_for_9c(self) -> None:
        runtime = shared.SHARED_PROPERTY_META_RUNTIME
        self.assertEqual(runtime[:6], bytes.fromhex("a5 05 c9 9c f0 0e"))
        branch_target = 6 + int.from_bytes(runtime[5:6], signed=True)
        self.assertEqual(runtime[branch_target:branch_target + 3], bytes.fromhex("a9 0a 60"))

    def test_ghost_and_stock_property_fallbacks_remain_present(self) -> None:
        runtime = shared.SHARED_PROPERTY_META_RUNTIME
        self.assertIn(bytes.fromhex("e9 b0 c9 0c b0 03 a9 4a 60"), runtime)
        self.assertIn(bytes.fromhex("b9 0e a3 60"), runtime)

    def test_dark_fairy_init_tail_calls_stock_writer(self) -> None:
        self.assertEqual(fairy.INIT_STATUS_RUNTIME, bytes.fromhex("68 4c 1c 9d"))
        self.assertEqual(fairy.CPU_AI_DISPATCH, 0xE00D)
        self.assertEqual(len(fairy.RUNTIME), 74)
        self.assertIn(bytes.fromhex("4c 0d e0"), new_enemy_runtime.AI_ENTRY_RUNTIME)

    def test_dark_fairy_poison_delay_uses_nmi_frame_accumulator(self) -> None:
        runtime = fairy.AI_DISPATCH_RUNTIME
        self.assertIn(bytes.fromhex("a0 02 b1 2c c9 3c b0 01 60"), runtime)
        self.assertIn(bytes.fromhex("a0 02 a9 00 91 2c a0 07 a9 01 91 2c"), runtime)

    def test_shared_tail_uses_the_complete_ghost_capacity(self) -> None:
        self.assertEqual(len(shared.SHARED_PROPERTY_META_RUNTIME), 23)
        self.assertEqual(shared.CPU_BULLET_SPAWN, 0xE32A)
        self.assertEqual(len(shared.RUNTIME), shared.MAX_RUNTIME_SIZE)
        self.assertIn(bytes.fromhex("20 2a e3"), shared.AI_RUNTIME)

    def test_ghost_a_to_f_defaults_match_the_approved_presets(self) -> None:
        self.assertEqual(
            shared.PARAMETER_TABLES,
            bytes.fromhex(
                "1a 1e 1a 1e 1a 1e "
                "c0 b0 c0 d0 c0 a8 "
                "00 89 00 88 00 00 "
                "03 03 02 02 00 00"
            ),
        )

    def test_panel_property_fallback_calls_the_shared_tail(self) -> None:
        expected = bytes((
            0x20,
            shared.CPU_SHARED_PROPERTY_META_LOAD & 0xFF,
            shared.CPU_SHARED_PROPERTY_META_LOAD >> 8,
        ))
        self.assertIn(expected, panel.FINAL_STAGE_PROPERTY_HOOK)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from magatu_skc.core import phantom_preset_runtime as target


class PhantomPresetRuntimeTests(unittest.TestCase):
    def test_upward_velocity_compensates_stock_gravity(self) -> None:
        for speed in (1, 2, 3, 4, 0x3F):
            velocity = target.velocity_bytes(speed)
            self.assertEqual(velocity[0], speed)
            self.assertEqual(velocity[1], (-speed) & 0xFF)
            self.assertEqual((velocity[2] + 3) & 0xFF, (-speed) & 0xFF)
            self.assertEqual(velocity[3], speed)

    def test_last_phase_is_stored_with_non_property_marker(self) -> None:
        runtime, offsets = target.build_runtime()
        state2_start = offsets["state2"] - target.CPU_RUNTIME
        scale_start = offsets["scale"] - target.CPU_RUNTIME
        state2 = runtime[state2_start:scale_start]
        self.assertIn(bytes.fromhex("aa 09 40 a0 06 d1 2c"), state2)
        self.assertEqual(len(state2), 69)

    def test_scale_helper_relies_on_nonzero_amplitude_gate(self) -> None:
        runtime, offsets = target.build_runtime()
        scale_start = offsets["scale"] - target.CPU_RUNTIME
        speed_start = offsets["apply_speed"] - target.CPU_RUNTIME
        scale = runtime[scale_start:speed_start]
        self.assertEqual(len(scale), 36)
        self.assertNotIn(bytes.fromhex("a6 0e f0"), scale)

    def test_total_layout_does_not_grow(self) -> None:
        runtime, offsets = target.build_runtime()
        self.assertEqual(len(runtime), 292)
        self.assertEqual(offsets["apply_speed"], 0xBE32)
        self.assertEqual(offsets["velocity_table"], 0xBE66)
        self.assertEqual(target.CPU_RUNTIME_END, 0xBEC0)


if __name__ == "__main__":
    unittest.main()

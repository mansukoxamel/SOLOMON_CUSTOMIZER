from __future__ import annotations

import unittest

from magatu_skc.core import phantom_preset_runtime as target


class PhantomPresetRuntimeTests(unittest.TestCase):
    def test_defaults_match_the_approved_a_to_d_presets(self) -> None:
        self.assertEqual(
            target.default_group_settings(),
            (
                {"speed_value": 0x3F, "amplitude_percent": 100, "phase_offset": 0},
                {"speed_value": 0x18, "amplitude_percent": 75, "phase_offset": 32},
                {"speed_value": 0x2A, "amplitude_percent": 50, "phase_offset": 45},
                {"speed_value": 0x3F, "amplitude_percent": 25, "phase_offset": 0},
            ),
        )

    def test_direction_velocities_are_symmetric(self) -> None:
        for speed in range(1, 0x40):
            velocity = target.velocity_bytes(speed)
            self.assertEqual(velocity[0], speed)
            self.assertEqual(velocity[1], (-speed) & 0xFF)
            self.assertEqual(velocity[2], (-speed) & 0xFF)
            self.assertEqual(velocity[3], speed)

    def test_vertical_physics_bypasses_stock_gravity(self) -> None:
        self.assertEqual(target.OFF_VERTICAL_PHYSICS, 0x3D9D)
        self.assertEqual(target.CPU_VERTICAL_PHYSICS, 0xBD8D)
        self.assertEqual(
            target.VERTICAL_PHYSICS,
            bytes.fromhex("c0 05 f0 03 4c 89 86 85 0a 0a 4c 99 86"),
        )
        runtime, offsets = target.build_runtime()
        prephysics_start = offsets["prephysics"] - target.CPU_RUNTIME
        velocity_start = offsets["velocity_table"] - target.CPU_RUNTIME
        prephysics = runtime[prephysics_start:velocity_start]
        self.assertTrue(prephysics.endswith(bytes.fromhex("4c 8d bd")))

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
        self.assertEqual(target.OFF_VERTICAL_PHYSICS + len(target.VERTICAL_PHYSICS), 0x3DAA)


if __name__ == "__main__":
    unittest.main()

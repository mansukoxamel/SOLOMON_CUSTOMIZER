from __future__ import annotations

import unittest

from magatu_skc.core import spark24_runtime as runtime
from magatu_skc.core import spark_ball_variant as variant


def _blank_rom() -> bytearray:
    size = max(
        runtime.OFF_RUNTIME + len(runtime.RUNTIME),
        variant.OFF_AB13 + len(variant.ORIG_AB13_HEAD),
        variant.OFF_A2CC + len(variant.ORIG_A2CC_HEAD),
        variant.OFF_85FA + len(variant.ORIG_85FA),
    )
    rom = bytearray(size)
    rom[variant.OFF_AB13:variant.OFF_AB13 + 3] = variant.ORIG_AB13_HEAD
    rom[variant.OFF_A2CC:variant.OFF_A2CC + 3] = variant.ORIG_A2CC_HEAD
    rom[variant.OFF_85FA:variant.OFF_85FA + len(variant.ORIG_85FA)] = variant.ORIG_85FA
    return rom


class SparkBallVariantTests(unittest.TestCase):
    def test_default_reverse_digits_are_one_and_eight(self) -> None:
        rom = _blank_rom()
        variant.apply(rom)

        self.assertEqual(set(variant.current_reverse_digits(rom)), {1, 8})

    def test_existing_runtime_can_be_reconfigured(self) -> None:
        rom = _blank_rom()
        variant.apply(
            rom,
            pause_digits=(0, 3, 6, 9),
            reverse_digits=(0, 3, 6, 9),
            transparency_period=0x40,
        )

        changed = variant.apply(
            rom,
            pause_digits=(1, 2, 7, 8),
            reverse_digits=(2, 4, 6, 8),
            transparency_period=0x60,
        )

        self.assertIn("Spark24 integrated runtime", changed)
        self.assertEqual(variant.current_pause_digits(rom), (1, 2, 7, 8))
        self.assertEqual(variant.current_reverse_digits(rom), (2, 4, 6, 8))
        self.assertEqual(variant.current_transparency_period(rom), 0x60)

    def test_corrupt_existing_runtime_is_still_rejected(self) -> None:
        rom = _blank_rom()
        variant.apply(rom)
        rom[runtime.OFF_RUNTIME + 10] ^= 0x01

        with self.assertRaisesRegex(
            variant.SparkBallVariantError,
            "runtime area is not blank",
        ):
            variant.apply(rom, pause_digits=(1, 2, 7, 8))

    def test_pre_spark_trail_runtime_preserves_user_settings(self) -> None:
        rom = _blank_rom()
        old_runtime, old_offsets = runtime.build_pre_spark_trail_runtime(
            pause_digits=(1, 2, 7, 8),
            reverse_digits=(2, 4, 6, 8),
            transparency_period=0x60,
        )
        rom[runtime.OFF_RUNTIME:runtime.OFF_RUNTIME + len(old_runtime)] = old_runtime
        rom[variant.OFF_AB13:variant.OFF_AB13 + 3] = bytes((
            0x4C, old_offsets["pause"] & 0xFF, old_offsets["pause"] >> 8,
        ))
        rom[variant.OFF_A2CC:variant.OFF_A2CC + 3] = bytes((
            0x20, old_offsets["property"] & 0xFF, old_offsets["property"] >> 8,
        ))
        rom[variant.OFF_85FA:variant.OFF_85FA + 6] = bytes((
            0x4C, old_offsets["oam"] & 0xFF, old_offsets["oam"] >> 8,
            0xEA, 0xEA, 0xEA,
        ))

        variant.apply(rom)

        self.assertEqual(variant.current_pause_digits(rom), (1, 2, 7, 8))
        self.assertEqual(variant.current_reverse_digits(rom), (2, 4, 6, 8))
        self.assertEqual(variant.current_transparency_period(rom), 0x60)

    def test_pre_final_enemy_runtime_preserves_user_settings(self) -> None:
        rom = _blank_rom()
        old_runtime, old_offsets = runtime.build_pre_final_enemy_runtime(
            pause_digits=(1, 2, 7, 8),
            reverse_digits=(2, 4, 6, 8),
            transparency_period=0x60,
        )
        self.assertEqual(old_offsets, runtime._OFFSETS)
        rom[runtime.OFF_RUNTIME:runtime.OFF_RUNTIME + len(old_runtime)] = old_runtime
        rom[variant.OFF_AB13:variant.OFF_AB13 + 3] = bytes((
            0x4C, old_offsets["pause"] & 0xFF, old_offsets["pause"] >> 8,
        ))
        rom[variant.OFF_A2CC:variant.OFF_A2CC + 3] = bytes((
            0x20, old_offsets["property"] & 0xFF, old_offsets["property"] >> 8,
        ))
        rom[variant.OFF_85FA:variant.OFF_85FA + 6] = bytes((
            0x4C, old_offsets["oam"] & 0xFF, old_offsets["oam"] >> 8,
            0xEA, 0xEA, 0xEA,
        ))

        variant.apply(rom)

        self.assertEqual(variant.current_pause_digits(rom), (1, 2, 7, 8))
        self.assertEqual(variant.current_reverse_digits(rom), (2, 4, 6, 8))
        self.assertEqual(variant.current_transparency_period(rom), 0x60)


if __name__ == "__main__":
    unittest.main()

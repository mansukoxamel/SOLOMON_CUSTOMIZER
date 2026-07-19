from __future__ import annotations

import unittest

from magatu_skc.core import spark_ball_speed as target


def _valid_rom() -> bytearray:
    rom = bytearray(target.OFF_TABLE_B + len(target.ORIG_TABLE_B))
    rom[target.SIG_OFF:target.SIG_OFF + len(target.SIG)] = target.SIG
    rom[target.OFF_TABLE_A:target.OFF_TABLE_A + len(target.ORIG_TABLE_A)] = target.ORIG_TABLE_A
    rom[target.OFF_TABLE_B:target.OFF_TABLE_B + len(target.ORIG_TABLE_B)] = target.ORIG_TABLE_B
    return rom


class SparkBallSpeedTests(unittest.TestCase):
    def test_only_safe_multipliers_are_supported(self) -> None:
        self.assertEqual(target.MULTIPLIERS, [0.5, 1.0])

    def test_unsafe_multipliers_are_rejected(self) -> None:
        for multiplier in (1.5, 2.0):
            with self.subTest(multiplier=multiplier):
                with self.assertRaises(target.SparkBallSpeedError):
                    target.apply(_valid_rom(), multiplier)


if __name__ == "__main__":
    unittest.main()

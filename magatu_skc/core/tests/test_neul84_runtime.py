from __future__ import annotations

import unittest

from magatu_skc.core import neul84_runtime as target


class Neul84RuntimeTests(unittest.TestCase):
    def test_defaults_match_the_approved_a_and_b_presets(self) -> None:
        self.assertEqual(
            target.default_group_settings(),
            (
                {
                    "body_speed": target.BODY_SPEED_NORMAL,
                    "fire_interval": 0x40,
                    "bullet_speed": target.BULLET_SPEED_STOCK,
                },
                {
                    "body_speed": target.BODY_SPEED_FAST,
                    "fire_interval": 0x40,
                    "bullet_speed": target.BULLET_SPEED_HALF,
                },
            ),
        )
        self.assertEqual(
            target.PARAMETER_TABLES,
            bytes.fromhex("18 1c 40 40 00 89"),
        )


if __name__ == "__main__":
    unittest.main()

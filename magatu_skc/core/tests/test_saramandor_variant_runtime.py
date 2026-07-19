import unittest

from magatu_skc.core import saramandor_variant as sv


class SaramandorVariantRuntimeTests(unittest.TestCase):
    def test_tuned_defaults(self) -> None:
        self.assertEqual(
            [sv.default_settings(index) for index in range(sv.VARIANT_COUNT)],
            [
                {"movement_speed": 1, "flame_speed": 4, "refire_wait": 32, "post_fire_stop": 60},
                {"movement_speed": 1, "flame_speed": 1, "refire_wait": 60, "post_fire_stop": 80},
                {"movement_speed": 3, "flame_speed": 4, "refire_wait": 45, "post_fire_stop": 120},
            ],
        )

    def test_speed_normalizer_restores_stock_state_field_offset(self) -> None:
        self.assertEqual(len(sv.CAVE_SPEED_INIT), 42)
        self.assertIn(bytes.fromhex("68 a0 04 4c a0 ed"), sv.CAVE_SPEED_INIT)
        self.assertNotIn(bytes.fromhex("c8 98 aa 68 4c a0 ed"), sv.CAVE_SPEED_INIT)


if __name__ == "__main__":
    unittest.main()

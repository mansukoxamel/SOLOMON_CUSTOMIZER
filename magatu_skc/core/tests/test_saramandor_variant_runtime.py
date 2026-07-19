import unittest

from magatu_skc.core import saramandor_variant as sv


class SaramandorVariantRuntimeTests(unittest.TestCase):
    def test_speed_normalizer_restores_stock_state_field_offset(self) -> None:
        self.assertEqual(len(sv.CAVE_SPEED_INIT), 42)
        self.assertIn(bytes.fromhex("68 a0 04 4c a0 ed"), sv.CAVE_SPEED_INIT)
        self.assertNotIn(bytes.fromhex("c8 98 aa 68 4c a0 ed"), sv.CAVE_SPEED_INIT)


if __name__ == "__main__":
    unittest.main()

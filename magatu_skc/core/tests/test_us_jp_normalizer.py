import unittest

from magatu_skc.core import us_jp_normalizer as normalizer


class UsJpNormalizerTest(unittest.TestCase):
    def test_absolute_operand_metadata_is_complete_and_ordered(self):
        offsets = normalizer._WORD_OPERANDS
        self.assertEqual(len(offsets), 664)
        self.assertEqual(offsets, tuple(sorted(set(offsets))))
        self.assertEqual(offsets[0], 0x8139)
        self.assertEqual(offsets[-1], 0xCDF3)

    def test_source_addresses_translate_to_jp_targets(self):
        self.assertEqual(normalizer._source_to_target(0x8000), 0x8000)
        self.assertEqual(normalizer._source_to_target(0x9EC0 + 0x140), 0x9EC0)
        self.assertEqual(normalizer._source_to_target(0xB4F1), 0xB3B1)
        self.assertEqual(normalizer._source_to_target(0xC200 - 0x100), 0xC200)
        self.assertEqual(normalizer._source_to_target(0xCBEA - 0xA9), 0xCBEA)
        self.assertIsNone(normalizer._source_to_target(0xC012))

    def test_unverified_rom_is_rejected(self):
        data = b"NES\x1a" + bytes(normalizer.US_ORIGINAL_SIZE - 4)
        self.assertFalse(normalizer.is_supported_us_original(data))
        with self.assertRaisesRegex(ValueError, "verified original ROM"):
            normalizer.normalize_us_original(data)

    def test_us_owned_non_relocation_bytes_are_not_replaced(self):
        self.assertEqual(tuple(address for address, _data in normalizer._BRIDGES), (0xCB80,))
        explicit_addresses = {
            address for address, _data in normalizer._EXPLICIT_FIXUPS
        }
        self.assertNotIn(0x9583, explicit_addresses)
        self.assertNotIn(0xFFFE, explicit_addresses)


if __name__ == "__main__":
    unittest.main()

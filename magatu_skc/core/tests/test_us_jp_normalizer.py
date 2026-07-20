import unittest
from unittest import mock

from magatu_skc.core import us_jp_normalizer as normalizer


class UsJpNormalizerTest(unittest.TestCase):
    def test_verified_full_rom_crc32_values_are_registered(self):
        self.assertEqual(
            normalizer.KNOWN_US_ORIGINAL_CRC32,
            frozenset({"B7A00D99", "99773BC4"}),
        )

    def test_matching_prg_and_chr_are_accepted_as_header_variant(self):
        data = bytearray(normalizer.US_ORIGINAL_SIZE)
        data[:4] = b"NES\x1a"
        data[4:16] = bytes.fromhex("A55AFFFFFFFFFFFFFFFFFFFF")
        prg_crc, chr_crc = normalizer._payload_crc32s(data)
        with mock.patch.object(
            normalizer,
            "KNOWN_US_ORIGINAL_CRC32",
            frozenset(),
        ), mock.patch.object(
            normalizer,
            "US_ORIGINAL_PRG_CRC32",
            prg_crc,
        ), mock.patch.object(
            normalizer,
            "US_ORIGINAL_CHR_CRC32",
            chr_crc,
        ):
            self.assertTrue(normalizer.is_supported_us_original(data))

            data[normalizer._US_PRG_START] ^= 0x01
            self.assertFalse(normalizer.is_supported_us_original(data))

    def test_canonical_header_ignores_input_header_metadata(self):
        source = bytearray(normalizer.US_ORIGINAL_SIZE)
        source[:16] = bytes.fromhex("4E45531A0204FFFFFFFFFFFFFFFFFFFF")
        result = normalizer._canonicalize_us_header(source)
        self.assertEqual(
            result[:16],
            bytes.fromhex("4E45531A020430000000000000000000"),
        )

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

import unittest

from magatu_skc.core import solomon_seal_block as target


def _blank_rom(size=0x9019):
    rom = bytearray(size)
    rom[target.OFF_SEAL_WRITE:target.OFF_SEAL_WRITE + len(target.ORIG_SEAL_WRITE)] = (
        target.ORIG_SEAL_WRITE
    )
    return rom


class SolomonSealBlockLayoutTests(unittest.TestCase):
    def test_panel_tail_owns_only_its_three_instruction_bytes(self):
        self.assertEqual(len(target.TRANSPARENT_SEAL_PANEL_TAIL_HELPER), 3)
        self.assertIn(
            (
                target.OFF_PRG1_TRANSPARENT_SEAL_PANEL_TAIL_HELPER,
                3,
            ),
            target.RESERVED_SPANS,
        )

    def test_writer_preserves_the_ten_bytes_after_panel_tail(self):
        rom = _blank_rom()
        free_start = (
            target.OFF_PRG1_TRANSPARENT_SEAL_PANEL_TAIL_HELPER
            + len(target.TRANSPARENT_SEAL_PANEL_TAIL_HELPER)
        )
        sentinel = bytes(range(1, 11))
        rom[free_start:free_start + len(sentinel)] = sentinel

        target.apply(rom, [])

        self.assertEqual(bytes(rom[free_start:free_start + len(sentinel)]), sentinel)

    def test_legacy_suppress_helper_is_not_accepted(self):
        rom = _blank_rom()
        legacy = bytes.fromhex(
            "bd db 8e 30 19 a8 bd 1b 8f 25 7a f0 11 a9 50 99 04 03 "
            "bc 5b 8f b9 50 07 3d 9b 8f 99 50 07 60"
        )
        start = target.OFF_PRG1_TRANSPARENT_SEAL_SUPPRESS_HELPER
        rom[start:start + len(legacy)] = legacy
        with self.assertRaises(target.SolomonSealBlockError):
            target._verify(rom)


if __name__ == "__main__":
    unittest.main()

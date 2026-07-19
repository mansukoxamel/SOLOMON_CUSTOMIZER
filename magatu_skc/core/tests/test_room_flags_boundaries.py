import unittest

from magatu_skc.core import room_flags as target


def _valid_rom(size):
    rom = bytearray(size)
    for offset, signature in (
        (target.OFF_SIG_9074, target.SIG_9074),
        (target.OFF_SIG_8329, target.SIG_8329),
        (target.OFF_SIG_91C1, target.SIG_91C1),
        (target.OFF_SIG_804B, target.SIG_804B),
        (target.OFF_HOOK_9071, target.ORIG_9071),
        (target.OFF_HOOK_8326, target.ORIG_8326),
        (target.OFF_HOOK_91CC, target.ORIG_91CC),
        (target.OFF_HOOK_909A, target.ORIG_909A),
        (target.OFF_HOOK_8055, target.ORIG_8055),
    ):
        rom[offset:offset + len(signature)] = signature
    return rom


class RoomFlagsBoundaryTests(unittest.TestCase):
    def test_required_end_includes_last_runtime_byte(self):
        self.assertEqual(target.REQUIRED_ROM_END, 0x686B)

    def test_verify_rejects_rom_truncated_before_runtime_end(self):
        rom = _valid_rom(target.OFF_TABLE + target.ROOM_COUNT)
        with self.assertRaisesRegex(target.RoomFlagError, "ROM"):
            target._verify(rom)

    def test_verify_accepts_complete_blank_runtime_ranges(self):
        rom = _valid_rom(target.REQUIRED_ROM_END)
        target._verify(rom)

    def test_set_tempo_reports_domain_error_for_truncated_rom(self):
        rom = _valid_rom(target.OFF_TABLE + target.ROOM_COUNT)
        with self.assertRaises(target.RoomFlagError):
            target.set_tempo(rom, 45, 100)


if __name__ == "__main__":
    unittest.main()

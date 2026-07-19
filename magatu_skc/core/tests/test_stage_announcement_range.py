import unittest

from magatu_skc.core import stage_announcement as target


def _blank_mapper66_rom():
    rom = bytearray(0x18010)
    rom[:4] = b"NES\x1a"
    rom[4] = 4
    rom[5] = 4
    rom[
        target.OFF_HOOK_START_UPDATE:
        target.OFF_HOOK_START_UPDATE + len(target.ORIG_START_UPDATE)
    ] = target.ORIG_START_UPDATE
    return rom


class StageAnnouncementRangeTests(unittest.TestCase):
    def test_range_gate_is_exactly_ten_bytes_before_main(self):
        self.assertEqual(len(target.STAGE_RANGE_GATE), 10)
        self.assertEqual(
            target.OFF_STAGE_RANGE_GATE + len(target.STAGE_RANGE_GATE),
            target.OFF_MAIN,
        )
        self.assertEqual(target.STAGE_RANGE_GATE, bytes.fromhex("ad 28 04 c9 30 90 03 4c 5e 91"))
        self.assertEqual(target.HOOK_START_UPDATE, bytes.fromhex("20 ec ea"))

    def test_less_than_stage_49_branch_falls_through_to_main(self):
        branch_pos = 5
        displacement = target.STAGE_RANGE_GATE[branch_pos + 1]
        branch_target = target.OFF_STAGE_RANGE_GATE + branch_pos + 2 + displacement
        self.assertEqual(branch_target, target.OFF_MAIN)

    def test_short_rom_is_rejected_before_any_runtime_write(self):
        rom = bytearray(target.OFF_HOOK_START_UPDATE + 3)
        rom[:4] = b"NES\x1a"
        rom[4] = 4
        rom[5] = 4
        before = bytes(rom)
        with self.assertRaises(target.StageAnnouncementError):
            target.apply(rom, [], [])
        self.assertEqual(bytes(rom), before)

    def test_apply_does_not_write_chr_bank_three(self):
        rom = _blank_mapper66_rom()
        chr_base = 0x10010
        bank3_k = chr_base + 3 * 0x2000 + target.CUSTOM_K_CHR * 16
        bank3_p = chr_base + 3 * 0x2000 + target.CUSTOM_P_CHR * 16
        before_k = bytes(rom[bank3_k:bank3_k + 16])
        before_p = bytes(rom[bank3_p:bank3_p + 16])

        target.apply(rom, [], [])

        self.assertEqual(bytes(rom[bank3_k:bank3_k + 16]), before_k)
        self.assertEqual(bytes(rom[bank3_p:bank3_p + 16]), before_p)

    def test_previous_direct_main_hook_is_not_accepted(self):
        rom = _blank_mapper66_rom()
        rom[target.OFF_HOOK_START_UPDATE:target.OFF_HOOK_START_UPDATE + 3] = bytes.fromhex(
            "20 f6 ea"
        )
        with self.assertRaises(target.StageAnnouncementError):
            target.apply(rom, [], [])


if __name__ == "__main__":
    unittest.main()

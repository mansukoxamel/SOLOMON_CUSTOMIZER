import unittest

from magatu_skc.core import m66_expander
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

    def test_apply_does_not_rewrite_gameplay_font_tiles(self):
        rom = _blank_mapper66_rom()
        watched = []
        for bank in range(m66_expander.GAMEPLAY_FONT_BANK_COUNT):
            base = (
                m66_expander.M66_CHR_BASE
                + bank * m66_expander.GAMEPLAY_FONT_BANK_SIZE
            )
            for tile in (
                m66_expander.GAMEPLAY_K_CHR,
                m66_expander.GAMEPLAY_P_CHR,
            ):
                off = base + tile * 16
                marker = bytes([0x40 + bank * 2 + (tile & 1)]) * 16
                rom[off:off + 16] = marker
                watched.append((off, marker))

        target.apply(rom, [], [])

        for off, marker in watched:
            self.assertEqual(bytes(rom[off:off + 16]), marker)

    def test_previous_direct_main_hook_is_not_accepted(self):
        rom = _blank_mapper66_rom()
        rom[target.OFF_HOOK_START_UPDATE:target.OFF_HOOK_START_UPDATE + 3] = bytes.fromhex(
            "20 f6 ea"
        )
        with self.assertRaises(target.StageAnnouncementError):
            target.apply(rom, [], [])


if __name__ == "__main__":
    unittest.main()

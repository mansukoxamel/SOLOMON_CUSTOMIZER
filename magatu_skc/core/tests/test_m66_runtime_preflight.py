import unittest

from magatu_skc.core import m66


def _base_loader_rom():
    rom = bytearray(0x9100)
    for offset, patch in (
        (m66.RESPAWN_DIRECT_CELL_COPY_PATCH_OFF, m66.RESPAWN_DIRECT_CELL_COPY_SKCHAIN),
        (m66.INITIAL_DRAW_LOW_CLASSIFIER_PATCH_OFF, m66.INITIAL_DRAW_LOW_CLASSIFIER_OLD),
        (m66.KEY_CELL_VALUE_PATCH_OFF, m66.KEY_CELL_VALUE_PATCH_OLD),
        (m66.RUNTIME_BLOCK_LIST_COPY_PATCH_OFF, m66.RUNTIME_BLOCK_LIST_COPY_PATCH_OLD),
    ):
        rom[offset:offset + len(patch)] = patch
    rom[m66.INITIAL_DRAW_WHITE_THRESHOLD_PATCH_OFF] = (
        m66.INITIAL_DRAW_WHITE_THRESHOLD_OLD
    )
    rom[m66.KEY_CELL_VALUE_NO_KEY_BRANCH_OFF] = m66.KEY_CELL_VALUE_NO_KEY_BRANCH_OLD
    rom[m66.M66_LOADER_TAIL_OFF:m66.M66_LOADER_TAIL_OFF + 3] = bytes.fromhex(
        "60 00 00"
    )
    return rom


def _helper_pointer(room):
    low_product = (room << 5) & 0xFF
    high_product = room >> 3
    low_sum = low_product + 0x4F
    return (((0xF8 + high_product + (low_sum >> 8)) & 0xFF) << 8) | (low_sum & 0xFF)


class M66RuntimePreflightTests(unittest.TestCase):
    def test_visible_mask_helper_builds_all_53_room_pointers(self):
        self.assertEqual(len(m66.VISIBLE_IN_BLOCK_MASK_COPY_HELPER), 42)
        self.assertEqual(
            m66.VISIBLE_IN_BLOCK_MASK_COPY_HELPER,
            bytes.fromhex(
                "ad 28 04 0a 0a 0a 0a 0a 85 00 ad 28 04 4a 4a 4a 85 01 "
                "18 a5 00 69 4f 85 00 a5 01 69 f8 85 01 "
                "a0 20 b1 00 99 4f 07 88 d0 f8 60"
            ),
        )
        for room in range(m66.COUNT_M66_LEVELS):
            with self.subTest(stage=room + 1):
                self.assertEqual(_helper_pointer(room), 0xF84F + room * 32)

    def test_helper_releases_one_byte_before_seal_table(self):
        from magatu_skc.core import solomon_seal_block

        helper_end = (
            m66.VISIBLE_IN_BLOCK_MASK_COPY_HELPER_OFF
            + len(m66.VISIBLE_IN_BLOCK_MASK_COPY_HELPER)
        )
        self.assertEqual(helper_end, 0x8EAA)
        self.assertEqual(solomon_seal_block.OFF_PRG1_SEAL_BLOCK_TABLE, 0x8EAB)

    def test_full_preflight_accepts_and_converts_mapper66_base_loader(self):
        rom = _base_loader_rom()

        m66._preflight_runtime_block_loader(rom)
        m66.patch_runtime_block_loader(rom)

        start = m66.RESPAWN_DIRECT_CELL_COPY_PATCH_OFF
        patch = m66.RESPAWN_DIRECT_CELL_COPY_F0_F3_GATE_HELPER
        self.assertEqual(bytes(rom[start:start + len(patch)]), patch)
        start = m66.VISIBLE_IN_BLOCK_MASK_COPY_HELPER_OFF
        helper = m66.VISIBLE_IN_BLOCK_MASK_COPY_HELPER
        self.assertEqual(bytes(rom[start:start + len(helper)]), helper)

    def test_intermediate_respawn_layout_is_rejected(self):
        rom = _base_loader_rom()
        intermediate = bytes.fromhex(
            "ad2804c930f022a57c6a901db100c9c0b017293fc92e9011b10029802a9005"
            "a990189007a910189002b10099130388d0cf"
        )
        start = m66.RESPAWN_DIRECT_CELL_COPY_PATCH_OFF
        rom[start:start + len(intermediate)] = intermediate
        with self.assertRaises(m66.M66RuntimePatchError):
            m66._preflight_runtime_block_loader(rom)

    def test_buggy_43_byte_helper_is_rejected(self):
        rom = _base_loader_rom()
        buggy = bytes.fromhex(
            "ad28040a0a0a0a0a18694f8500a90069008501ad28044a4a4a18650169f88501"
            "a020b100994f0788d0f860"
        )
        start = m66.VISIBLE_IN_BLOCK_MASK_COPY_HELPER_OFF
        rom[start:start + len(buggy)] = buggy
        with self.assertRaises(m66.M66RuntimePatchError):
            m66._preflight_runtime_block_loader(rom)


if __name__ == "__main__":
    unittest.main()

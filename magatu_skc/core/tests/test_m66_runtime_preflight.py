import unittest

from magatu_skc.core import m66


class M66SpecialHighIdPreflightTests(unittest.TestCase):
    def _rom_with_patch(self, patch: bytes) -> bytearray:
        end = m66.RESPAWN_DIRECT_CELL_COPY_PATCH_OFF + len(patch)
        rom_data = bytearray(end)
        start = m66.RESPAWN_DIRECT_CELL_COPY_PATCH_OFF
        rom_data[start:end] = patch
        return rom_data

    def test_current_f0_f3_gate_uses_complete_signature(self):
        rom_data = self._rom_with_patch(m66.RESPAWN_DIRECT_CELL_COPY_F0_F3_GATE)
        self.assertEqual(
            rom_data[m66.SPECIAL_HIGH_ID_THRESHOLD_PATCH_OFF],
            0xC9,
        )
        m66._preflight_special_high_id_fields(
            rom_data,
            m66.RESPAWN_DIRECT_CELL_COPY_F0_F3_GATE,
        )

    def test_current_helper_uses_complete_signature(self):
        rom_data = self._rom_with_patch(
            m66.RESPAWN_DIRECT_CELL_COPY_F0_F3_GATE_HELPER
        )
        m66._preflight_special_high_id_fields(
            rom_data,
            m66.RESPAWN_DIRECT_CELL_COPY_F0_F3_GATE_HELPER,
        )

    def test_legacy_layout_still_checks_fixed_fields(self):
        rom_data = self._rom_with_patch(m66.RESPAWN_DIRECT_CELL_COPY_SKCHAIN)
        m66._preflight_special_high_id_fields(
            rom_data,
            m66.RESPAWN_DIRECT_CELL_COPY_SKCHAIN,
        )
        rom_data[m66.SPECIAL_HIGH_ID_THRESHOLD_PATCH_OFF] = 0xC9
        with self.assertRaises(m66.M66RuntimePatchError):
            m66._preflight_special_high_id_fields(
                rom_data,
                m66.RESPAWN_DIRECT_CELL_COPY_SKCHAIN,
            )

    def test_full_preflight_accepts_mapper66_base_loader(self):
        rom_data = bytearray(0x9100)
        start = m66.RESPAWN_DIRECT_CELL_COPY_PATCH_OFF
        patch = m66.RESPAWN_DIRECT_CELL_COPY_F0_F3_GATE
        rom_data[start:start + len(patch)] = patch
        start = m66.INITIAL_DRAW_LOW_CLASSIFIER_PATCH_OFF
        patch = m66.INITIAL_DRAW_LOW_CLASSIFIER_OLD
        rom_data[start:start + len(patch)] = patch
        rom_data[m66.INITIAL_DRAW_WHITE_THRESHOLD_PATCH_OFF] = (
            m66.INITIAL_DRAW_WHITE_THRESHOLD_OLD
        )
        start = m66.KEY_CELL_VALUE_PATCH_OFF
        patch = m66.KEY_CELL_VALUE_PATCH_OLD
        rom_data[start:start + len(patch)] = patch
        rom_data[m66.KEY_CELL_VALUE_NO_KEY_BRANCH_OFF] = (
            m66.KEY_CELL_VALUE_NO_KEY_BRANCH_OLD
        )
        start = m66.RUNTIME_BLOCK_LIST_COPY_PATCH_OFF
        patch = m66.RUNTIME_BLOCK_LIST_COPY_PATCH_OLD
        rom_data[start:start + len(patch)] = patch
        start = m66.M66_LOADER_TAIL_OFF
        rom_data[start:start + 3] = bytes.fromhex("60 00 00")

        m66._preflight_runtime_block_loader(rom_data)
        m66.patch_runtime_block_loader(rom_data)

        start = m66.RESPAWN_DIRECT_CELL_COPY_PATCH_OFF
        patch = m66.RESPAWN_DIRECT_CELL_COPY_F0_F3_GATE_HELPER
        self.assertEqual(bytes(rom_data[start:start + len(patch)]), patch)


if __name__ == "__main__":
    unittest.main()

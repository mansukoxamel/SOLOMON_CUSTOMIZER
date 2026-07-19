import unittest
from unittest import mock

from magatu_skc.core import m66, m66_expander


class M66ExpanderRuntimeOrderTests(unittest.TestCase):
    def test_change_mapper_only_relocates_stock_kp_tiles(self):
        source = bytearray(65552)
        raw_chr_base = 0x8010
        markers = []
        for bank in range(m66_expander.GAMEPLAY_FONT_BANK_COUNT):
            for tile in (
                m66_expander.GAMEPLAY_K_CHR,
                m66_expander.GAMEPLAY_P_CHR,
            ):
                src_off = (
                    raw_chr_base
                    + bank * m66_expander.GAMEPLAY_FONT_BANK_SIZE
                    + tile * 16
                )
                marker = bytes([0x60 + bank * 2 + (tile & 1)]) * 16
                source[src_off:src_off + 16] = marker
                markers.append((bank, tile, marker))

        with mock.patch.object(m66_expander, "_require_jp_standard_rom"):
            expanded = m66_expander.change_mapper(bytes(source), "JP")

        for bank, tile, marker in markers:
            dst_off = (
                m66_expander.M66_CHR_BASE
                + bank * m66_expander.GAMEPLAY_FONT_BANK_SIZE
                + tile * 16
            )
            self.assertEqual(bytes(expanded[dst_off:dst_off + 16]), marker)

    def test_expand_rom_installs_kp_tiles_after_mapper_conversion(self):
        class FakeRom:
            def __init__(self):
                self.data = bytearray(65552)
                self.region = "JP"

            def is_expanded(self):
                return False

            def base_region(self):
                return "JP"

        rom = FakeRom()
        with mock.patch.object(
            m66_expander, "_require_jp_standard_rom"
        ), mock.patch.object(
            m66_expander, "parse_drop_schedules_std", return_value=[]
        ), mock.patch.object(
            m66_expander, "parse_enemy_sets_std", return_value=[]
        ), mock.patch.object(
            m66_expander, "_install_loadtime_runtimes"
        ), mock.patch(
            "magatu_skc.core.stage_ext.patch_table"
        ), mock.patch(
            "magatu_skc.core.special_process.disable_falling_fairy_subroutine"
        ):
            m66_expander.expand_rom(rom, [])

        for bank in range(m66_expander.GAMEPLAY_FONT_BANK_COUNT):
            base = (
                m66_expander.M66_CHR_BASE
                + bank * m66_expander.GAMEPLAY_FONT_BANK_SIZE
            )
            k_off = base + m66_expander.GAMEPLAY_K_CHR * 16
            p_off = base + m66_expander.GAMEPLAY_P_CHR * 16
            self.assertEqual(
                bytes(rom.data[k_off:k_off + 16]),
                m66_expander.GAMEPLAY_K_TILE_BYTES,
            )
            self.assertEqual(
                bytes(rom.data[p_off:p_off + 16]),
                m66_expander.GAMEPLAY_P_TILE_BYTES,
            )

    def test_change_mapper_emits_the_canonical_respawn_base_layout(self):
        source = bytes(65552)
        with mock.patch.object(m66_expander, "_require_jp_standard_rom"):
            expanded = m66_expander.change_mapper(source, "JP")

        start = m66.RESPAWN_DIRECT_CELL_COPY_PATCH_OFF
        expected = m66.RESPAWN_DIRECT_CELL_COPY_MAPPER66_BASE
        self.assertEqual(bytes(expanded[start:start + len(expected)]), expected)
        start = m66.RUNTIME_BLOCK_LIST_COPY_PATCH_OFF
        expected = m66.RUNTIME_BLOCK_LIST_COPY_MAPPER66_BASE
        self.assertEqual(bytes(expanded[start:start + len(expected)]), expected)

    def test_prg0_clear_runs_before_runtime_preflight_and_install(self):
        calls = []
        rom_data = bytearray()
        levels = []

        with mock.patch.object(
            m66_expander,
            "_clear_legacy_prg0_level_area",
            side_effect=lambda data: calls.append(("clear", data)),
        ), mock.patch.object(
            m66,
            "patch_breakable_white_data",
            side_effect=lambda data, value: calls.append(
                ("install", data, value)
            ),
        ):
            m66_expander._install_loadtime_runtimes(rom_data, levels)

        self.assertEqual(
            calls,
            [("clear", rom_data), ("install", rom_data, levels)],
        )

    def test_prg0_clear_makes_classifier_cave_available_and_keeps_l_a1(self):
        rom_data = bytearray(0x7010)
        start = m66_expander.LOADTIME_PRG0_CLEAR_START
        end = start + m66_expander.LOADTIME_PRG0_CLEAR_LENGTH
        rom_data[start:end] = bytes([0x55]) * (end - start)
        pointer_off = 0x1000
        pointer = m66_expander.ITEM_POINTER_LOADER_OLD
        rom_data[pointer_off:pointer_off + len(pointer)] = pointer
        l_a1 = m66_expander._build_l_a1(m66_expander.L_A1_NEW_CPU)
        l_a1_off = m66_expander.L_A1_NEW_OFF
        rom_data[l_a1_off:l_a1_off + len(l_a1)] = l_a1

        m66_expander._clear_legacy_prg0_level_area(rom_data)

        cave_off = m66.INITIAL_DRAW_LOW_CLASSIFIER_HELPER_OFF
        cave_end = cave_off + len(m66.INITIAL_DRAW_LOW_CLASSIFIER_HELPER)
        self.assertEqual(
            bytes(rom_data[cave_off:cave_end]),
            bytes([0xEA]) * (cave_end - cave_off),
        )
        self.assertEqual(bytes(rom_data[l_a1_off:l_a1_off + len(l_a1)]), l_a1)
        self.assertEqual(
            bytes(rom_data[pointer_off:pointer_off + len(pointer)]),
            m66_expander.ITEM_POINTER_LOADER_CONST_0790,
        )


if __name__ == "__main__":
    unittest.main()

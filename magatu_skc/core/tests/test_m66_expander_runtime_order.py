import unittest
from unittest import mock

from magatu_skc.core import m66, m66_expander


class M66ExpanderRuntimeOrderTests(unittest.TestCase):
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

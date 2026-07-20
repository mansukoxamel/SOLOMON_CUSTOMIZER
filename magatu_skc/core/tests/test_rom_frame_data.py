import unittest

from magatu_skc.ui.rom_frame_data import (
    packed_sprite_palette_numbers,
    read_rom_frame_records,
)
from magatu_skc.core import ice_flame_runtime
from magatu_skc.ui.title_screen_dialog import TitleCharacterPickerDialog


class RomFrameDataTests(unittest.TestCase):
    @staticmethod
    def _rom_data():
        data = bytearray(0x8000)

        def offset(address):
            return 0x10 + (address - 0x8000)

        def write_word(address, value):
            start = offset(address)
            data[start:start + 2] = int(value).to_bytes(2, "little")

        for group in range(32):
            write_word(0xD0E8 + group * 2, 0xD12A)

        direct = offset(0xD12A)
        data[direct:direct + 4] = bytes((0x08, 0x00, 0x00, 0xD6))
        for frame in range(9):
            start = offset(0xD600 + frame * 3)
            data[start:start + 3] = bytes((frame, frame + 1, frame + 2))

        indirect = offset(0xD12E)
        data[indirect:indirect + 4] = bytes((0x00, 0x01, 0x00, 0xD2))
        for variant, pointer in enumerate((0xD630, 0xD633, 0xD636, 0xD639)):
            write_word(0xD200 + variant * 2, pointer)
            start = offset(pointer)
            data[start:start + 3] = bytes((0x20 + variant, 0x30 + variant, 0x40 + variant))
        return data

    def test_left_palette_bits_match_original_rol_decoder(self):
        self.assertEqual(packed_sprite_palette_numbers(0x80), (1, 0))
        self.assertEqual(packed_sprite_palette_numbers(0x40), (2, 0))
        self.assertEqual(packed_sprite_palette_numbers(0x86), (1, 1))
        self.assertEqual(packed_sprite_palette_numbers(0x4C), (2, 3))

    def test_ninth_frame_is_not_truncated(self):
        records = read_rom_frame_records(self._rom_data())
        direct = [
            record for record in records
            if record.group == 0 and record.state == 0
        ]
        self.assertEqual(len(direct), 9)
        self.assertEqual(direct[-1].frame, 8)
        self.assertEqual(direct[-1].edit_key, (8, 9, 10))

    def test_all_four_indirect_type_variants_are_read(self):
        records = read_rom_frame_records(self._rom_data())
        indirect = [
            record for record in records
            if record.group == 0 and record.state == 1
        ]
        self.assertEqual([record.type_variant for record in indirect], [0, 1, 2, 3])
        self.assertEqual(
            [record.edit_key for record in indirect],
            [(0x20 + value, 0x30 + value, 0x40 + value) for value in range(4)],
        )

    def test_installed_ice_flame_runtime_adds_its_unique_frame(self):
        data = self._rom_data()
        start = ice_flame_runtime.OFF_RUNTIME
        data[start:start + len(ice_flame_runtime.RUNTIME)] = ice_flame_runtime.RUNTIME

        records = read_rom_frame_records(data)
        ice_records = [record for record in records if record.enemy_type == 0x82]

        self.assertEqual(len(ice_records), 1)
        self.assertEqual(ice_records[0].edit_key, (0xD6, 0xD4, 0x5A))

    def test_title_character_picker_uses_the_complete_shared_extraction(self):
        data = self._rom_data()
        records = read_rom_frame_records(data)
        title_items = TitleCharacterPickerDialog._romframe_items_for_rom(data)

        self.assertEqual(len(title_items), len(records))
        self.assertIn((0, 0, 8, 8, 9, 10), title_items)


if __name__ == "__main__":
    unittest.main()

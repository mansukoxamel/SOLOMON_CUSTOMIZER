import unittest

from magatu_skc.core import stage_ext as target


def _rom_with_table(table):
    rom = bytearray(target.TABLE_END)
    rom[target.TABLE_OFFSET:target.TABLE_END] = table
    return rom


class StageExtHeaderValidationTests(unittest.TestCase):
    def test_runtime_flags_reader_accepts_current_header(self):
        table = bytearray(target.build_table([]))
        table[target.HEADER_SIZE + target.RUNTIME_ROOM_FLAGS_OFFSET] = 0x9F
        self.assertEqual(target.read_runtime_room_flags(_rom_with_table(table), 1), [0x9F])

    def test_runtime_flags_reader_accepts_supported_format_one(self):
        table = bytearray(target.build_table([]))
        table[len(target.MAGIC)] = 1
        table[target.HEADER_SIZE + target.RUNTIME_ROOM_FLAGS_OFFSET] = 0x10
        self.assertEqual(target.read_runtime_room_flags(_rom_with_table(table), 1), [0x10])

    def test_runtime_flags_reader_rejects_unknown_format(self):
        table = bytearray(target.build_table([]))
        table[len(target.MAGIC)] = 0x7F
        table[target.HEADER_SIZE + target.RUNTIME_ROOM_FLAGS_OFFSET] = 0x9F
        self.assertEqual(target.read_runtime_room_flags(_rom_with_table(table), 1), [0])

    def test_runtime_flags_reader_rejects_wrong_entry_size(self):
        table = bytearray(target.build_table([]))
        table[len(target.MAGIC) + 1] = target.ENTRY_SIZE - 1
        table[target.HEADER_SIZE + target.RUNTIME_ROOM_FLAGS_OFFSET] = 0x9F
        self.assertEqual(target.read_runtime_room_flags(_rom_with_table(table), 1), [0])


if __name__ == "__main__":
    unittest.main()

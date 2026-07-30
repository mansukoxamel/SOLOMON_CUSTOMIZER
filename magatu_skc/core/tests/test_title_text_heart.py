import unittest

from magatu_skc.core import title_screen


class TitleTextHeartTests(unittest.TestCase):
    def test_heart_uses_title_chr_tile_72b_stream_value(self):
        self.assertIn("♥", title_screen._TITLE_TEXT_SUPPORTED)
        self.assertEqual(title_screen._title_char_src_tile("♥"), 0x2B)

    def test_heart_tile_round_trips_to_unicode_character(self):
        self.assertEqual(title_screen._title_char_from_src_tile(0x2B), "♥")


if __name__ == "__main__":
    unittest.main()

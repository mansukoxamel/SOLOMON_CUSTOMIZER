import unittest

from magatu_skc.core import title_screen


class TitleTextApostropheTests(unittest.TestCase):
    def test_apostrophe_uses_stream_tile_3b(self):
        self.assertIn("'", title_screen._TITLE_TEXT_SUPPORTED)
        self.assertEqual(title_screen._title_char_src_tile("'"), 0x3B)

    def test_apostrophe_tile_round_trips(self):
        self.assertEqual(title_screen._title_char_from_src_tile(0x3B), "'")


if __name__ == "__main__":
    unittest.main()

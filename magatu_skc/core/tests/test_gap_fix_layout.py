import unittest

from magatu_skc.core import gap_fix as target


class GapFixLayoutTests(unittest.TestCase):
    def test_hook_and_cave_are_registered(self):
        self.assertEqual(
            target.RESERVED_SPANS,
            (
                (target.OFF_HOOK, len(target.HOOK)),
                (target.OFF_CAVE, len(target.CAVE)),
            ),
        )

    def test_current_layout_is_unchanged(self):
        self.assertEqual(target.OFF_HOOK, 0x0794)
        self.assertEqual(target.HOOK, bytes.fromhex("4c 79 e8"))
        self.assertEqual(target.OFF_CAVE, 0x6889)
        self.assertEqual(len(target.CAVE), 136)
        self.assertEqual(target.OFF_CAVE + len(target.CAVE), 0x6911)


if __name__ == "__main__":
    unittest.main()

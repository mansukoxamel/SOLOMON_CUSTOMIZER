import unittest

from magatu_skc.core import gap_fix
from magatu_skc.core import gap_fix_alternative as target


class GapFixAlternativeTests(unittest.TestCase):
    PREVIOUS_TRIAL_HASH = "a90a0a23206931b96be41648729f5516a9d34930fe7e47a71c2eb019b8b8a890"
    RIGHT_ONLY_TRIAL_HASH = "04047f73e56ddfe97b30d0cf613e393eebdc74522458d229bc31ba79cc902d95"

    def _blank_rom(self):
        rom = bytearray([0xEA]) * 0x18010
        rom[target.INPUT_SIG_OFF:target.INPUT_SIG_OFF + len(target.INPUT_SIG)] = target.INPUT_SIG
        rom[target.OFF_INPUT_HOOK:target.OFF_INPUT_HOOK + 3] = target.INPUT_ORIG
        rom[target.OFF_COLLISION_SIG:target.OFF_COLLISION_SIG + len(target.COLLISION_SIG)] = target.COLLISION_SIG
        rom[target.OFF_COLLISION_HOOK:target.OFF_COLLISION_HOOK + 3] = target.COLLISION_ORIG
        return rom

    def test_runtime_fits_inside_legacy_cave(self):
        self.assertEqual(len(target.CAVE), 120)
        self.assertEqual(target.OFF_CAVE + len(target.CAVE), 0x6901)
        self.assertEqual(target.LEGACY_CAVE_SIZE - len(target.CAVE), 16)
        self.assertEqual(target.DEFAULT_WINDOW_FRAMES, 20)
        self.assertEqual(target.CPU_COLLISION_ENTRY, 0xE8C2)
        self.assertEqual(target.COLLISION_HOOK, bytes.fromhex("4c c2 e8"))
        self.assertIn(self.PREVIOUS_TRIAL_HASH, target.KNOWN_REPLACEABLE_CAVE_SHA256)
        self.assertIn(self.RIGHT_ONLY_TRIAL_HASH, target.KNOWN_REPLACEABLE_CAVE_SHA256)

    def test_current_cave_accepts_any_configured_window(self):
        cave = bytearray(target.CAVE_WRITE_IMAGE)
        for offset in target.CAVE_WINDOW_OPERAND_OFFSETS:
            cave[offset] = 37
        self.assertTrue(target._is_current_cave(bytes(cave)))
        self.assertIn(bytes.fromhex("68 48 29 06 c9 02"), target.CAVE)
        self.assertIn(bytes.fromhex("68 48 29 09 c9 01"), target.CAVE)

    def test_all_runtime_spans_are_registered(self):
        self.assertEqual(
            target.RESERVED_SPANS,
            (
                (target.OFF_INPUT_HOOK, 3),
                (target.OFF_COLLISION_HOOK, 3),
                (target.OFF_CAVE, 120),
            ),
        )

    def test_enable_and_disable_use_only_alternative_runtime(self):
        rom = self._blank_rom()
        target.apply(rom, True)
        self.assertEqual(rom[target.OFF_INPUT_HOOK:target.OFF_INPUT_HOOK + 3], target.INPUT_HOOK)
        self.assertEqual(rom[target.OFF_COLLISION_HOOK:target.OFF_COLLISION_HOOK + 3], target.COLLISION_HOOK)
        self.assertEqual(rom[target.OFF_CAVE:target.OFF_CAVE + target.LEGACY_CAVE_SIZE], target.CAVE_WRITE_IMAGE)
        self.assertTrue(target.is_applied(rom))
        self.assertEqual(target.get_window_frames(rom), 20)

        target.apply(rom, True, 17)
        self.assertEqual(target.get_window_frames(rom), 17)
        for offset in target.CAVE_WINDOW_OPERAND_OFFSETS:
            self.assertEqual(rom[target.OFF_CAVE + offset], 17)
        target.apply(rom, True)
        self.assertEqual(target.get_window_frames(rom), 17)

        target.apply(rom, False)
        self.assertEqual(rom[target.OFF_INPUT_HOOK:target.OFF_INPUT_HOOK + 3], target.INPUT_ORIG)
        self.assertEqual(rom[target.OFF_COLLISION_HOOK:target.OFF_COLLISION_HOOK + 3], target.COLLISION_ORIG)
        self.assertFalse(target.is_applied(rom))

    def test_legacy_enabled_state_switches_to_alternative(self):
        rom = self._blank_rom()
        rom[target.OFF_COLLISION_HOOK:target.OFF_COLLISION_HOOK + 3] = target.COLLISION_HOOK
        rom[target.OFF_CAVE:target.OFF_CAVE + len(gap_fix.CAVE)] = gap_fix.CAVE
        self.assertFalse(target.is_applied(rom))
        target.apply(rom, True)
        self.assertEqual(rom[target.OFF_INPUT_HOOK:target.OFF_INPUT_HOOK + 3], target.INPUT_HOOK)
        self.assertEqual(rom[target.OFF_COLLISION_HOOK:target.OFF_COLLISION_HOOK + 3], target.COLLISION_HOOK)
        self.assertEqual(rom[target.OFF_CAVE:target.OFF_CAVE + target.LEGACY_CAVE_SIZE], target.CAVE_WRITE_IMAGE)


if __name__ == "__main__":
    unittest.main()

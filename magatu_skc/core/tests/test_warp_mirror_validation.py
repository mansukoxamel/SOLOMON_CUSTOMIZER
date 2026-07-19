from __future__ import annotations

from types import SimpleNamespace
import unittest

from magatu_skc.core import constants as c
from magatu_skc.core import saver
from magatu_skc.core import stage_ext
from magatu_skc.core import warp_zone_trial as target
from magatu_skc.core.element import Wall


def _level(positions=((2, 3), (12, 8))):
    return SimpleNamespace(
        demon_mirrors=[SimpleNamespace(position=position) for position in positions],
        items=[],
        enemies=[],
        tiles=[[Wall.NONE for _x in range(c.LEVEL_W)] for _y in range(c.LEVEL_H)],
        breakable_white_cells=set(),
        cracked_block_cells=set(),
        passable_white_cells=set(),
        invisible_solid_cells=set(),
        invisible_breakable_cells=set(),
        passable_brown_cells=set(),
        solid_brown_cells=set(),
        stage_ext_flags=stage_ext.FLAG_WARP_MIRROR,
        key_enemy_slot=stage_ext.DEFAULT_KEY_ENEMY_SLOT,
        fairy_enemy_slot=stage_ext.DEFAULT_FAIRY_ENEMY_SLOT,
    )


class WarpMirrorValidationTests(unittest.TestCase):
    def test_two_clear_distinct_mirrors_are_valid(self) -> None:
        self.assertTrue(target.level_has_valid_warp_mirrors(_level()))

    def test_invalid_counts_and_duplicate_positions_are_rejected(self) -> None:
        self.assertFalse(target.level_has_valid_warp_mirrors(_level(((2, 3),))))
        self.assertFalse(target.level_has_valid_warp_mirrors(_level(((2, 3),) * 2)))
        self.assertFalse(target.level_has_valid_warp_mirrors(_level(((1, 1), (2, 2), (3, 3)))))

    def test_obstructed_mirror_is_rejected(self) -> None:
        level = _level()
        level.tiles[3][2] = Wall.BROWN
        self.assertFalse(target.level_has_valid_warp_mirrors(level))
        level.tiles[3][2] = Wall.NONE
        level.items = [SimpleNamespace(position=(2, 3))]
        self.assertFalse(target.level_has_valid_warp_mirrors(level))
        level.items = []
        level.invisible_solid_cells.add((2, 3))
        self.assertFalse(target.level_has_valid_warp_mirrors(level))

    def test_save_preflight_rejects_mode_after_data_becomes_invalid(self) -> None:
        level = _level(((2, 3),))
        with self.assertRaisesRegex(saver.SaveError, "Warp Mirror Mode"):
            saver.validate_level_consistency([level])


if __name__ == "__main__":
    unittest.main()

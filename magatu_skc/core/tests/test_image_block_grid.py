import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PIL.PngImagePlugin import PngInfo
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from magatu_skc.core import constants, room_flags
from magatu_skc.core.element import ElementType, LevelElement, Wall
from magatu_skc.core.image_block_grid import apply_grid_to_level, validate_grid
from magatu_skc.core.level import Level
from magatu_skc.ui.main_window import MainWindow
from tools.image_to_block_grid import open_converter_window


def empty_grid():
    return [[0 for _x in range(15)] for _y in range(12)]


class ImageBlockGridApplyTests(unittest.TestCase):
    def test_actor_precedence_cleanup_mirror_off_and_column_16_preserved(self):
        level = Level()
        level.fixed_start_pos = (1, 1)
        level.fixed_key_pos = (2, 1)
        level.fixed_door_pos = (3, 1)
        level.demon_mirrors[0].position = (4, 1)
        level.demon_mirrors[1].position = (5, 1)
        level.tiles[1][15] = Wall.WHITE
        level.items = [
            LevelElement(ElementType.ITEM, (6, 1), 1),
            LevelElement(ElementType.ITEM, (15, 1), 2),
        ]
        level.enemies = [
            LevelElement(ElementType.ENEMY, (7, 1), 1),
            LevelElement(ElementType.ENEMY, (15, 2), 2),
        ]
        level.constellation = LevelElement(ElementType.ITEM, (8, 1), 0x18)

        grid = empty_grid()
        grid[1][1] = 2
        grid[1][2] = 2
        grid[1][3] = 3
        grid[1][4] = 1
        disabled = apply_grid_to_level(level, grid)

        self.assertEqual(level.tiles[1][1], Wall.NONE)
        self.assertEqual(level.key_status, constants.KEY_STATUS_WHITE_IN_BLOCK)
        self.assertEqual(level.tiles[1][2], Wall.NONE)
        self.assertEqual(
            level.room_flags & room_flags.DOOR_STATE_MASK,
            room_flags.DOOR_STATE_NORMAL,
        )
        self.assertEqual(level.tiles[1][3], Wall.NONE)
        self.assertEqual(level.tiles[1][4], Wall.BROWN)
        self.assertEqual(disabled, [0])
        self.assertEqual([item.position for item in level.items], [(15, 1)])
        self.assertEqual([enemy.position for enemy in level.enemies], [(15, 2)])
        self.assertIsNone(level.constellation)
        self.assertEqual(level.tiles[1][15], Wall.WHITE)

    def test_key_cracked_becomes_hidden_in_cracked_brown_block(self):
        level = Level()
        level.fixed_key_pos = (2, 2)
        grid = empty_grid()
        grid[2][2] = 3

        apply_grid_to_level(level, grid)

        self.assertEqual(level.key_status, constants.KEY_STATUS_HIDDEN)
        self.assertEqual(level.tiles[2][2], Wall.BROWN)
        self.assertIn((2, 2), level.cracked_block_cells)

    def test_grid_validation(self):
        self.assertTrue(validate_grid(empty_grid()))
        self.assertFalse(validate_grid([[0] * 16 for _ in range(12)]))
        self.assertFalse(validate_grid([[0] * 15 for _ in range(11)]))
        bad = empty_grid()
        bad[0][0] = 4
        self.assertFalse(validate_grid(bad))


class StagePngRoutingTests(unittest.TestCase):
    def _write_png(self, path: Path, xml_text=None):
        info = PngInfo()
        if xml_text is not None:
            info.add_itxt("msc_level", xml_text)
        Image.new("RGB", (2, 2), "black").save(path, pnginfo=info)

    def test_plain_png_routes_to_image_converter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "plain.png"
            self._write_png(path)
            self.assertEqual(MainWindow._png_stage_data_state(path), "absent")

    def test_valid_stage_png_routes_to_stage_loader(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "stage.png"
            self._write_png(path, "<solomon_customizer />")
            self.assertEqual(MainWindow._png_stage_data_state(path), "valid")

    def test_invalid_stage_chunk_does_not_fall_through_to_converter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "broken.png"
            self._write_png(path, "<solomon_customizer>")
            self.assertEqual(MainWindow._png_stage_data_state(path), "invalid")


class ImageBlockGridSelectionUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_hover_cursor_and_drag_switch_to_selection_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "source.png"
            Image.new("RGB", (320, 240), "white").save(path)
            window = open_converter_window(path, language="ja")
            window.show()
            self.app.processEvents()
            source = window.source_preview
            point = source.rect().center()

            QTest.mouseMove(source, point)
            self.app.processEvents()
            self.assertNotEqual(source.cursor().shape(), Qt.ArrowCursor)
            selection_index = window.fit_combo.findData("selection")
            window.fit_combo.setCurrentIndex(selection_index)
            selection_rect = source._selection_rect()
            left_edge = QPoint(
                round(selection_rect.left()),
                round(selection_rect.center().y()),
            )
            QTest.mouseMove(source, left_edge)
            self.app.processEvents()
            self.assertEqual(source.cursor().shape(), Qt.SizeHorCursor)

            crop_index = window.fit_combo.findData("crop")
            window.fit_combo.setCurrentIndex(crop_index)
            QTest.mousePress(source, Qt.LeftButton, pos=point)
            self.app.processEvents()
            self.assertEqual(window.fit_combo.currentData(), "selection")
            self.assertEqual(source._drag_mode, "new")
            QTest.mouseRelease(source, Qt.LeftButton, pos=point)
            window.close()


if __name__ == "__main__":
    unittest.main()

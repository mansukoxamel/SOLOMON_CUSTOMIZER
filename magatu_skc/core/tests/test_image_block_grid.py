import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image, ImageOps
from PIL.PngImagePlugin import PngInfo
from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from magatu_skc.core import constants, room_flags
from magatu_skc.core.element import ElementType, LevelElement, Wall
from magatu_skc.core.image_block_grid import apply_grid_to_level, validate_grid
from magatu_skc.core.level import Level
from magatu_skc.ui.main_window import MainWindow
from tools.image_to_block_grid import (
    AIR as GRID_AIR,
    BROWN as GRID_BROWN,
    CRACKED as GRID_CRACKED,
    WHITE as GRID_WHITE,
    _four_level_grid,
    _counts_to_thresholds,
    _redistribute_counts,
    _thresholds_to_counts,
    open_converter_window,
)


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
            actual_counts = [
                sum(cell == kind for row in window.result_grid for cell in row)
                for kind in (GRID_AIR, GRID_CRACKED, GRID_BROWN, GRID_WHITE)
            ]
            self.assertEqual(actual_counts, window._block_counts)
            self.assertEqual(window._block_counts, [1, 1, 1, 177])
            self.assertEqual(window.status.text(), "変換完了")
            self.assertTrue(window.reload_image_button.isEnabled())
            window.block_count_sliders[0].setValue(72)
            self.assertNotEqual(window._block_counts, [1, 1, 1, 177])
            window.reload_image_button.click()
            self.assertEqual(window._block_counts, [1, 1, 1, 177])
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

    def test_four_count_sliders_redistribute_and_total_180(self):
        window = open_converter_window(language="ja")
        self.assertFalse(window.reload_image_button.isEnabled())
        self.assertEqual(window._block_counts, [45, 45, 45, 45])
        self.assertTrue(
            all(slider.minimum() == 0 and slider.maximum() == 180
                for slider in window.block_count_sliders)
        )
        window.block_count_sliders[0].setValue(180)
        self.assertEqual(window._block_counts[0], 177)

        window.block_count_sliders[0].setValue(72)
        self.app.processEvents()

        self.assertEqual(window._block_counts, [72, 36, 36, 36])
        self.assertEqual(
            [slider.value() for slider in window.block_count_sliders],
            [72, 36, 36, 36],
        )
        self.assertEqual(
            _counts_to_thresholds(window._block_counts),
            (0.4, 0.6, 0.8),
        )
        window.block_count_sliders[0].setValue(0)
        self.assertEqual(window._block_counts[0], 0)
        self.assertEqual(sum(window._block_counts), 180)
        window.block_count_sliders[1].setValue(72)
        self.assertEqual(window._block_counts[0], 0)
        self.assertEqual(sum(window._block_counts), 180)
        window.block_count_sliders[1].setValue(0)
        window.block_count_sliders[2].setValue(0)
        self.assertEqual(window._block_counts, [0, 0, 0, 180])
        self.assertEqual(window.block_count_sliders[3].value(), 180)
        label_widths = [label.width() for label, _key in window.block_count_labels]
        self.assertEqual(len(set(label_widths)), 1)
        window.equal_counts_button.click()
        self.assertEqual(window._block_counts, [45, 45, 45, 45])
        self.assertEqual(
            [label.width() for label, _key in window.block_count_labels],
            label_widths,
        )
        window.close()

    def test_drag_keeps_the_other_three_ratios_from_drag_start(self):
        window = open_converter_window(language="ja")
        window._block_counts = [18, 72, 54, 36]
        for slider, value in zip(window.block_count_sliders, window._block_counts):
            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)
        window.update_block_count_labels()

        window.begin_count_drag(0)
        for value in range(19, 55):
            window.block_count_sliders[0].setValue(value)
        window.end_count_drag()

        self.assertEqual(window._block_counts, [54, 56, 42, 28])
        self.assertEqual(sum(window._block_counts), 180)
        window.close()


class BlockCountMathTests(unittest.TestCase):
    def test_default_thresholds_become_four_equal_counts(self):
        self.assertEqual(_thresholds_to_counts(0.25, 0.50, 0.75), [45] * 4)

    def test_changed_count_redistributes_all_other_counts_proportionally(self):
        self.assertEqual(
            _redistribute_counts([45, 45, 45, 45], 0, 72),
            [72, 36, 36, 36],
        )
        self.assertEqual(
            _redistribute_counts([18, 36, 54, 72], 0, 45),
            [45, 30, 45, 60],
        )

    def test_changed_count_stops_at_177_and_keeps_other_counts_positive(self):
        self.assertEqual(
            _redistribute_counts([45, 45, 45, 45], 3, 180),
            [1, 1, 1, 177],
        )

    def test_only_the_operated_count_can_be_lowered_to_zero(self):
        values = _redistribute_counts([45, 45, 45, 45], 0, 0)
        self.assertEqual(values, [0, 60, 60, 60])
        values = _redistribute_counts(values, 1, 72)
        self.assertEqual(values[1], 72)
        self.assertEqual(values[0], 0)
        self.assertTrue(all(values[index] >= 1 for index in (2, 3)))

    def test_zero_percent_band_produces_none_of_that_type(self):
        gray = Image.new("L", (15, 12))
        gray.putdata(range(180))
        _tone, brown_grid = _four_level_grid(gray, False, 0.0, 0.0, 1.0)
        self.assertTrue(all(cell == GRID_BROWN for row in brown_grid for cell in row))
        _tone, air_grid = _four_level_grid(gray, False, 1.0, 1.0, 1.0)
        self.assertTrue(all(cell == GRID_AIR for row in air_grid for cell in row))

    def test_positive_band_is_guaranteed_at_least_one_cell(self):
        gray = Image.new("L", (15, 12))
        gray.putdata([0] * 90 + [255] * 90)
        _tone, grid = _four_level_grid(gray, False, 0.33, 0.34, 0.67)
        counts = {
            kind: sum(cell == kind for row in grid for cell in row)
            for kind in (GRID_AIR, GRID_CRACKED, GRID_BROWN, GRID_WHITE)
        }
        self.assertTrue(all(count >= 1 for count in counts.values()))

    def test_exact_target_counts_survive_identical_brightness_ties(self):
        source = Image.new("RGB", (15, 12), (240, 240, 240))
        gray = ImageOps.grayscale(source)
        requested = [1, 177, 1, 1]
        _tone, grid = _four_level_grid(
            gray,
            False,
            0.01,
            178 / 180,
            179 / 180,
            source_rgb=source,
            target_counts=requested,
        )
        actual = [
            sum(cell == kind for row in grid for cell in row)
            for kind in (GRID_AIR, GRID_CRACKED, GRID_BROWN, GRID_WHITE)
        ]
        self.assertEqual(actual, requested)

    def test_natural_initial_counts_follow_absolute_image_brightness(self):
        dark = Image.new("L", (15, 12), 0)
        bright = Image.new("L", (15, 12), 255)
        _tone, dark_grid = _four_level_grid(
            dark, False, 0.25, 0.50, 0.75, normalize_range=False
        )
        _tone, bright_grid = _four_level_grid(
            bright, False, 0.25, 0.50, 0.75, normalize_range=False
        )
        dark_counts = [
            sum(cell == kind for row in dark_grid for cell in row)
            for kind in (GRID_AIR, GRID_CRACKED, GRID_BROWN, GRID_WHITE)
        ]
        bright_counts = [
            sum(cell == kind for row in bright_grid for cell in row)
            for kind in (GRID_AIR, GRID_CRACKED, GRID_BROWN, GRID_WHITE)
        ]
        self.assertEqual(dark_counts, [177, 1, 1, 1])
        self.assertEqual(bright_counts, [1, 1, 1, 177])


if __name__ == "__main__":
    unittest.main()

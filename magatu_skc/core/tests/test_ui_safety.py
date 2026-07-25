import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from magatu_skc.core import config, saver
from magatu_skc.core.element import ElementType, LevelElement, Wall
from magatu_skc.core.level import Level
from magatu_skc.core.i18n import get_language, set_language
from magatu_skc.ui.element_picker import (
    DEVELOPER_ONLY_PICKER_ITEMS,
    ENEMIES_LIST,
    ENEMY_PICKER_PALETTE_OVERRIDE,
    ENEMY_VISUAL_SOURCE,
    MODE_ENEMY,
    ElementPicker,
    apply_enemy_speed,
    base_code_from_actual,
)
from magatu_skc.ui.picker_tooltips_en import PICKER_TOOLTIPS_EN
from magatu_skc.ui.picker_tooltips_ja import PICKER_TOOLTIPS_JA
from magatu_skc.gfx.level_renderer import (
    ENEMY_PALETTE_OVERRIDE as RENDER_PALETTE_OVERRIDE,
    ENEMY_VISUAL_SOURCE as RENDER_VISUAL_SOURCE,
)
from magatu_skc.ui.hack_dialog import HackDialog
from magatu_skc.ui.main_window import MainWindow
from magatu_skc.ui.settings_dialog import SettingsDialog
from magatu_skc.ui.sprite_viewer import SpriteViewer
from magatu_skc.ui.title_screen_dialog import TitleScreenDialog
from magatu_skc.ui.dialog_geometry import (
    restore_dialog_geometry_values,
    store_dialog_geometry,
)
from magatu_skc.ui.dialog_buttons import localize_dialog_buttons


class SpriteViewerControlLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _rom():
        data = bytearray(16 + 0x8000 + 0x2000)
        data[4] = 2
        data[5] = 1
        return SimpleNamespace(data=data)

    def test_dynamic_control_rows_are_sized_after_rebuild(self):
        dialog = SpriteViewer(self._rom())
        dialog.show()
        self.app.processEvents()

        self.assertGreater(dialog.ctrl_host.width(), 0)
        self.assertGreater(dialog.ctrl_host.height(), 0)
        self.assertGreaterEqual(dialog.rb_bank.minimumWidth(), 88)
        self.assertGreater(dialog.rb_pal.width(), 0)

        raw_index = dialog.mode_combo.findData("raw")
        dialog.mode_combo.setCurrentIndex(raw_index)
        self.app.processEvents()

        self.assertGreater(dialog.ctrl_host.width(), 0)
        self.assertGreaterEqual(dialog.bank_combo.minimumWidth(), 88)
        self.assertGreater(dialog.pal_combo.width(), 0)
        dialog.close()


class ConfigSaveSafetyTests(unittest.TestCase):
    def test_replace_failure_keeps_existing_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(config, "APP_ROOT", Path(temp_dir)):
                self.assertTrue(config.save_config({"language": "en", "value": 1}))
                path = config.get_config_path()
                before = path.read_bytes()
                with patch.object(config.os, "replace", side_effect=OSError("test")):
                    self.assertFalse(
                        config.save_config({"language": "ja", "value": 2})
                    )
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(list(path.parent.glob("*.tmp")), [])


class LiveRetranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_existing_widget_text_is_retranslated(self):
        old_language = get_language()
        try:
            window = QMainWindow()
            root = QWidget(window)
            layout = QVBoxLayout(root)
            label = QLabel("制限時間:", root)
            checkbox = QCheckBox("Bボタン（ファイア）禁止", root)
            combo = QComboBox(root)
            combo.addItem("一般")
            tabs = QTabWidget(root)
            tabs.addTab(QWidget(), "ショートカット")
            for widget in (label, checkbox, combo, tabs):
                layout.addWidget(widget)
            window.setCentralWidget(root)

            set_language("en")
            MainWindow._retranslate_widget_tree(window)

            self.assertEqual(label.text(), "Time Limit:")
            self.assertEqual(checkbox.text(), "Disable B Button (Fire)")
            self.assertEqual(combo.itemText(0), "General")
            self.assertEqual(tabs.tabText(0), "Shortcuts")
        finally:
            set_language(old_language)

    def test_open_settings_dialog_is_retranslated(self):
        old_language = get_language()
        try:
            set_language("ja")
            window = QMainWindow()
            dialog = SettingsDialog(dict(config.DEFAULT_CONFIG), window)

            set_language("en")
            MainWindow._retranslate_widget_tree(window)

            self.assertEqual(dialog.windowTitle(), "Settings (F9)")
            self.assertEqual(dialog.tabs.tabText(0), "General")
            labels = {label.text() for label in dialog.findChildren(QLabel)}
            self.assertIn("Unsaved mark:", labels)
            self.assertIn("Open ROM:", labels)

            set_language("ja")
            MainWindow._retranslate_widget_tree(window)

            self.assertEqual(dialog.windowTitle(), "設定 (F9)")
            self.assertEqual(dialog.tabs.tabText(0), "一般")
            labels = {label.text() for label in dialog.findChildren(QLabel)}
            self.assertIn("未保存マーク:", labels)
            self.assertIn("ROMを開く:", labels)
        finally:
            set_language(old_language)


class FavoritesVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_setting_is_gathered_without_losing_favorites(self):
        cfg = dict(config.DEFAULT_CONFIG)
        cfg["picker_favorites"] = [["item", 1]] + [None] * 9
        dialog = SettingsDialog(cfg)
        dialog.chk_favorites_visible.setChecked(False)
        dialog._gather()
        gathered = dialog.get_config()
        self.assertFalse(gathered["picker_favorites_visible"])
        self.assertEqual(gathered["picker_favorites"], cfg["picker_favorites"])

    def test_bonus_panel_remains_visible_when_favorites_are_hidden(self):
        picker = ElementPicker()
        picker.set_favorites_visible(False)
        self.assertTrue(picker._bottom_stack.isHidden())
        picker.set_bonus_mode(True)
        self.assertFalse(picker._bottom_stack.isHidden())
        picker.set_bonus_mode(False)
        self.assertTrue(picker._bottom_stack.isHidden())

    def test_developer_enemies_are_hidden_without_developer_mode(self):
        picker = ElementPicker()
        picker.set_app_config({"developer_mode": False})
        visible_codes = {
            item.data(Qt.UserRole)[1]
            for index in range(picker._picker_lists[3].count())
            for item in (picker._picker_lists[3].item(index),)
            if item.data(Qt.UserRole)
            and item.data(Qt.UserRole)[0] == MODE_ENEMY
        }
        expected = {
            code for code, _name in ENEMIES_LIST
            if (MODE_ENEMY, code) not in DEVELOPER_ONLY_PICKER_ITEMS
        }
        self.assertEqual(visible_codes, expected)
        self.assertTrue(set(range(0xD8, 0xDC)).isdisjoint(visible_codes))
        self.assertTrue(set(range(0xF8, 0xFC)).isdisjoint(visible_codes))

    def test_spark_trail_is_visible_in_developer_mode(self):
        picker = ElementPicker()
        picker.set_app_config({"developer_mode": True})
        visible_codes = {
            item.data(Qt.UserRole)[1]
            for index in range(picker._picker_lists[3].count())
            for item in (picker._picker_lists[3].item(index),)
            if item.data(Qt.UserRole)
            and item.data(Qt.UserRole)[0] == MODE_ENEMY
        }
        self.assertTrue(set(range(0xD8, 0xDC)).issubset(visible_codes))
        self.assertTrue(set(range(0xF8, 0xFC)).issubset(visible_codes))

    def test_japanese_picker_tooltips_match_all_reviewed_entries(self):
        old_language = get_language()
        try:
            set_language("ja")
            picker = ElementPicker()
            picker.set_app_config({"developer_mode": True})
            actual = {
                item.data(Qt.UserRole): item.toolTip()
                for picker_list in picker._picker_lists
                for index in range(picker_list.count())
                for item in (picker_list.item(index),)
                if item.data(Qt.UserRole) is not None
            }
            self.assertEqual(len(PICKER_TOOLTIPS_JA), 191)
            self.assertEqual(actual, PICKER_TOOLTIPS_JA)
        finally:
            set_language(old_language)

    def test_english_picker_tooltips_match_japanese_source_structure(self):
        old_language = get_language()
        try:
            set_language("en")
            picker = ElementPicker()
            picker.set_app_config({"developer_mode": True})
            actual = {
                item.data(Qt.UserRole): item.toolTip()
                for picker_list in picker._picker_lists
                for index in range(picker_list.count())
                for item in (picker_list.item(index),)
                if item.data(Qt.UserRole) is not None
            }
            self.assertEqual(len(PICKER_TOOLTIPS_EN), 191)
            self.assertEqual(PICKER_TOOLTIPS_EN.keys(), PICKER_TOOLTIPS_JA.keys())
            self.assertEqual(actual, PICKER_TOOLTIPS_EN)
            self.assertEqual(
                actual[("block", "brown")],
                "Brown Block",
            )
            self.assertEqual(
                actual[(MODE_ENEMY, 0x68)],
                "0x68 Dragon (Right)",
            )
            self.assertEqual(
                actual[(MODE_ENEMY, 0x78)],
                "0x78 Gargoil (Right)",
            )
            self.assertEqual(
                actual[(MODE_ENEMY, 0x28)],
                "0x28 Sparkling Ball (Right)",
            )
        finally:
            set_language(old_language)

    def test_japanese_canvas_popup_uses_picker_names(self):
        class PopupHarness:
            _build_hover_info_popup_text = MainWindow._build_hover_info_popup_text
            _hover_enemy_hits = MainWindow._hover_enemy_hits
            _block_info_for_tile = MainWindow._block_info_for_tile
            _item_state_label = MainWindow._item_state_label
            _key_state_label = MainWindow._key_state_label
            _door_state_label = MainWindow._door_state_label
            _enemy_speed_info = MainWindow._enemy_speed_info
            _canvas_picker_name = staticmethod(MainWindow._canvas_picker_name)

            @staticmethod
            def _display_enemy_desc(_code):
                return "fallback enemy"

            @staticmethod
            def _display_item_desc(_code):
                return "fallback item"

            @staticmethod
            def _solomon_seal_meta_at(_level_no, _tile):
                return object()

        old_language = get_language()
        try:
            set_language("ja")
            tile = (1, 1)
            level = Level()
            level.fixed_start_pos = tile
            level.fixed_key_pos = tile
            level.fixed_door_pos = tile
            for mirror in level.demon_mirrors:
                mirror.position = tile
            level.enemies = [LevelElement(ElementType.ENEMY, tile, 0x6C)]
            level.items = [LevelElement(ElementType.ITEM, tile, 0x48)]
            level.invisible_solid_cells.add(tile)

            harness = PopupHarness()
            harness.levels = [level]
            harness.current_level_no = 0
            popup = harness._build_hover_info_popup_text(tile)

            for expected in (
                "ドラゴン（右）",
                "SP2",
                "ダイヤモンド（ブルー）",
                "[隠し]",
                "透明な白ブロック",
                "Meta ダーナ, 鍵, 扉, カミーラの鏡1, カミーラの鏡2",
                "ソロモンの封印",
            ):
                with self.subTest(expected=expected):
                    self.assertIn(expected, popup)
            self.assertNotIn("fallback enemy", popup)
            self.assertNotIn("fallback item", popup)
        finally:
            set_language(old_language)

    def test_english_canvas_popup_uses_picker_names(self):
        class PopupHarness:
            _build_hover_info_popup_text = MainWindow._build_hover_info_popup_text
            _hover_enemy_hits = MainWindow._hover_enemy_hits
            _block_info_for_tile = MainWindow._block_info_for_tile
            _item_state_label = MainWindow._item_state_label
            _key_state_label = MainWindow._key_state_label
            _door_state_label = MainWindow._door_state_label
            _enemy_speed_info = MainWindow._enemy_speed_info
            _canvas_picker_name = staticmethod(MainWindow._canvas_picker_name)

            @staticmethod
            def _display_enemy_desc(_code):
                return "fallback enemy"

            @staticmethod
            def _display_item_desc(_code):
                return "fallback item"

            @staticmethod
            def _solomon_seal_meta_at(_level_no, _tile):
                return object()

        old_language = get_language()
        try:
            set_language("en")
            tile = (1, 1)
            level = Level()
            level.fixed_start_pos = tile
            level.fixed_key_pos = tile
            level.fixed_door_pos = tile
            for mirror in level.demon_mirrors:
                mirror.position = tile
            level.enemies = [LevelElement(ElementType.ENEMY, tile, 0x6C)]
            level.items = [LevelElement(ElementType.ITEM, tile, 0x48)]
            level.invisible_solid_cells.add(tile)

            harness = PopupHarness()
            harness.levels = [level]
            harness.current_level_no = 0
            popup = harness._build_hover_info_popup_text(tile)

            for expected in (
                "Dragon (Right)",
                "SP2",
                "Diamond (Blue)",
                "[Hidden]",
                "Invisible White Block",
                "Meta Dana, Key, Door, Mirror of Camirror 1, "
                "Mirror of Camirror 2",
                "Solomon&#x27;s Seal",
            ):
                with self.subTest(expected=expected):
                    self.assertIn(expected, popup)
            self.assertNotIn("fallback enemy", popup)
            self.assertNotIn("fallback item", popup)
        finally:
            set_language(old_language)

    def test_spark_trail_speed_and_visual_mappings_cover_all_eight_ids(self):
        for direction in range(4):
            base = 0xD8 + direction
            fast = 0xDC + direction
            with self.subTest(direction=direction):
                self.assertEqual(apply_enemy_speed(base, 1), base)
                self.assertEqual(apply_enemy_speed(base, 2), fast)
                self.assertEqual(base_code_from_actual(base), (base, 1))
                self.assertEqual(base_code_from_actual(fast), (base, 2))
                self.assertEqual(ENEMY_VISUAL_SOURCE[base], 0x28 + direction)
                self.assertEqual(ENEMY_VISUAL_SOURCE[fast], 0x2C + direction)
                self.assertEqual(RENDER_VISUAL_SOURCE[base], 0x28 + direction)
                self.assertEqual(RENDER_VISUAL_SOURCE[fast], 0x2C + direction)
                self.assertEqual(ENEMY_PICKER_PALETTE_OVERRIDE[base], 6)
                self.assertEqual(ENEMY_PICKER_PALETTE_OVERRIDE[fast], 6)
                self.assertEqual(RENDER_PALETTE_OVERRIDE[base], 6)
                self.assertEqual(RENDER_PALETTE_OVERRIDE[fast], 6)

    def test_spark_direct_turn_speed_and_visual_mappings_cover_all_eight_ids(self):
        for direction in range(4):
            base = 0xF8 + direction
            fast = 0xFC + direction
            with self.subTest(direction=direction):
                self.assertEqual(apply_enemy_speed(base, 1), base)
                self.assertEqual(apply_enemy_speed(base, 2), fast)
                self.assertEqual(base_code_from_actual(base), (base, 1))
                self.assertEqual(base_code_from_actual(fast), (base, 2))
                self.assertEqual(ENEMY_VISUAL_SOURCE[base], 0x28 + direction)
                self.assertEqual(ENEMY_VISUAL_SOURCE[fast], 0x2C + direction)
                self.assertEqual(RENDER_VISUAL_SOURCE[base], 0x28 + direction)
                self.assertEqual(RENDER_VISUAL_SOURCE[fast], 0x2C + direction)


class TitleScreenDialogCloseSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _dialog():
        class Harness(TitleScreenDialog):
            def __init__(self):
                QDialog.__init__(self)
                self._rom = bytearray(b"original")
                self._snap = bytes(self._rom)
                self._app_config = None

        return Harness()

    def test_reject_restores_open_snapshot(self):
        dialog = self._dialog()
        dialog._rom[:] = b"modified"
        dialog.reject()
        self.assertEqual(bytes(dialog._rom), b"original")

    def test_window_close_restores_open_snapshot(self):
        dialog = self._dialog()
        dialog.show()
        self.app.processEvents()
        dialog._rom[:] = b"modified"
        dialog.close()
        self.app.processEvents()
        self.assertEqual(bytes(dialog._rom), b"original")

    def test_escape_restores_open_snapshot(self):
        dialog = self._dialog()
        dialog.show()
        self.app.processEvents()
        dialog._rom[:] = b"modified"
        QTest.keyClick(dialog, Qt.Key_Escape)
        self.app.processEvents()
        self.assertEqual(bytes(dialog._rom), b"original")

    def test_accept_keeps_edits(self):
        dialog = self._dialog()
        dialog._rom[:] = b"modified"
        dialog.accept()
        self.assertEqual(bytes(dialog._rom), b"modified")


class DialogGeometrySafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_offscreen_position_is_moved_into_available_geometry(self):
        dialog = QDialog()
        dialog.resize(700, 500)
        restore_dialog_geometry_values(dialog, 700, 500, 5000, 5000)
        available = self.app.primaryScreen().availableGeometry()
        self.assertTrue(available.contains(dialog.geometry().topLeft()))
        self.assertTrue(available.contains(dialog.geometry().bottomRight()))

    def test_oversized_saved_geometry_is_clamped_to_screen(self):
        dialog = QDialog()
        restore_dialog_geometry_values(dialog, 5000, 5000, 0, 0)
        available = self.app.primaryScreen().availableGeometry()
        self.assertLessEqual(dialog.width(), available.width())
        self.assertLessEqual(dialog.height(), available.height())

    def test_negative_monitor_coordinates_are_preserved_when_stored(self):
        class GeometrySource:
            @staticmethod
            def x():
                return -1200

            @staticmethod
            def y():
                return -40

            @staticmethod
            def width():
                return 800

            @staticmethod
            def height():
                return 600

        state = {}
        store_dialog_geometry(GeometrySource(), state, "test_dlg")
        self.assertEqual(state["test_dlg_x"], -1200)
        self.assertEqual(state["test_dlg_y"], -40)


class DialogButtonLocalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_standard_buttons_follow_active_language(self):
        old_language = get_language()
        try:
            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok
                | QDialogButtonBox.Cancel
                | QDialogButtonBox.Apply
                | QDialogButtonBox.Close
            )
            set_language("ja")
            localize_dialog_buttons(buttons)
            self.assertEqual(buttons.button(QDialogButtonBox.Ok).text(), "OK")
            self.assertEqual(
                buttons.button(QDialogButtonBox.Cancel).text(), "キャンセル"
            )
            self.assertEqual(buttons.button(QDialogButtonBox.Apply).text(), "適用")
            self.assertEqual(buttons.button(QDialogButtonBox.Close).text(), "閉じる")

            set_language("en")
            localize_dialog_buttons(buttons)
            self.assertEqual(buttons.button(QDialogButtonBox.Ok).text(), "OK")
            self.assertEqual(buttons.button(QDialogButtonBox.Cancel).text(), "Cancel")
            self.assertEqual(buttons.button(QDialogButtonBox.Apply).text(), "Apply")
            self.assertEqual(buttons.button(QDialogButtonBox.Close).text(), "Close")
        finally:
            set_language(old_language)


class GlobalSettingsImportSafetyTests(unittest.TestCase):
    def test_failed_import_restores_rom_meta_ui_and_dirty_state(self):
        class Parent:
            def __init__(self):
                self._dirty = False
                self._session_log = ["before"]

            def _sync_wall_color_preview(self):
                pass

            def _load_bonus_stage_table(self, _rom):
                pass

            def _refresh_view(self):
                pass

            def _generate_all_thumbnails(self):
                pass

            def _set_dirty(self, value):
                self._dirty = bool(value)

        class FakeDialog:
            def __init__(self):
                self.rom = SimpleNamespace(data=bytearray(b"abc"))
                self.meta = SimpleNamespace(position=(1, 2), level_no=3)
                self.owner = Parent()
                self.ui_state = "old"

            def parent(self):
                return self.owner

            def _level_meta_config(self):
                return SimpleNamespace(level_meta_items=[self.meta])

            def _collect_global_settings(self):
                return {"settings": {"old": 1}}

            def _apply_imported_global_settings(self, settings):
                if "old" in settings:
                    self.ui_state = "old"
                    return []
                self.rom.data[0] = ord("z")
                self.meta.position = (9, 9)
                self.meta.level_no = 8
                self.ui_state = "new"
                self.owner._dirty = True
                self.owner._session_log.append("partial import")
                raise ValueError("test")

        dialog = FakeDialog()
        with self.assertRaises(ValueError):
            HackDialog._apply_imported_global_settings_transaction(
                dialog,
                {"invalid": 1},
            )
        self.assertEqual(bytes(dialog.rom.data), b"abc")
        self.assertEqual(dialog.meta.position, (1, 2))
        self.assertEqual(dialog.meta.level_no, 3)
        self.assertEqual(dialog.ui_state, "old")
        self.assertFalse(dialog.owner._dirty)
        self.assertEqual(dialog.owner._session_log, ["before"])


class SaveFailureMigrationOfferTests(unittest.TestCase):
    @staticmethod
    def _window_state(*, metadata=True, loaded=True):
        rom = SimpleNamespace(has_customizer_metadata=lambda: metadata) if loaded else None
        return SimpleNamespace(rom=rom, levels=[object()] if loaded else [])

    def test_all_save_failure_types_offer_migration(self):
        errors = (
            saver.SavePreflightError(
                "ステージデータ検証",
                RuntimeError("extension mismatch"),
            ),
            saver.SavePreflightError(
                "Saramandor variant runtime検証/適用",
                RuntimeError("not enough space"),
            ),
            saver.SavePreflightError(
                "Spark Ball variant runtime検証/適用",
                RuntimeError(
                    "Spark24 runtime area is not blank at file 0x3ED0"
                ),
            ),
            OSError("disk full"),
            RuntimeError("unexpected save failure"),
        )
        for error in errors:
            with self.subTest(error=error):
                self.assertTrue(
                    MainWindow._should_offer_data_migration(
                        self._window_state(),
                        error,
                    )
                )

    def test_metadata_is_not_required_but_loaded_editor_state_is(self):
        error = saver.SavePreflightError(
            "Gargoyle runtime検証/適用",
            RuntimeError("signature mismatch"),
        )
        self.assertTrue(
            MainWindow._should_offer_data_migration(
                self._window_state(metadata=False),
                error,
            )
        )
        self.assertFalse(
            MainWindow._should_offer_data_migration(
                self._window_state(loaded=False),
                error,
            )
        )

    def test_migration_autosaves_then_reloads_through_workstate_path(self):
        calls = []

        class FakeWindow:
            def __init__(self):
                self.rom = SimpleNamespace(display_name="base.nes")
                self._loaded_source_path = "base.nes"

            def _autosave_workstate(self):
                calls.append(
                    (
                        "save",
                        self.rom.display_name,
                        self._loaded_source_path,
                    )
                )
                return "autosave/workstate/workstate_test.nes"

            def _load_autosave_workstate(self, path, add_history=True):
                calls.append(("load", path, add_history))
                return True

        window = FakeWindow()
        result = MainWindow._autosave_and_reload_migrated_workstate(
            window,
            {
                "source_name": "legacy_custom.nes",
                "source_path": "legacy/legacy_custom.nes",
            },
        )

        self.assertEqual(result, "autosave/workstate/workstate_test.nes")
        self.assertEqual(
            calls,
            [
                (
                    "save",
                    "legacy_custom.nes",
                    "legacy/legacy_custom.nes",
                ),
                (
                    "load",
                    "autosave/workstate/workstate_test.nes",
                    False,
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()

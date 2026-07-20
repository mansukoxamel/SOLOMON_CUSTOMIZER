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
from magatu_skc.core.i18n import get_language, set_language
from magatu_skc.ui.element_picker import ENEMIES_LIST, MODE_ENEMY, ElementPicker
from magatu_skc.ui.hack_dialog import HackDialog
from magatu_skc.ui.main_window import MainWindow
from magatu_skc.ui.settings_dialog import SettingsDialog
from magatu_skc.ui.title_screen_dialog import TitleScreenDialog
from magatu_skc.ui.dialog_geometry import (
    restore_dialog_geometry_values,
    store_dialog_geometry,
)
from magatu_skc.ui.dialog_buttons import localize_dialog_buttons


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

    def test_all_completed_enemies_are_visible_without_developer_mode(self):
        picker = ElementPicker()
        picker.set_app_config({"developer_mode": False})
        visible_codes = {
            item.data(Qt.UserRole)[1]
            for index in range(picker._picker_lists[3].count())
            for item in (picker._picker_lists[3].item(index),)
            if item.data(Qt.UserRole)
            and item.data(Qt.UserRole)[0] == MODE_ENEMY
        }
        self.assertEqual(visible_codes, {code for code, _name in ENEMIES_LIST})


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


class LegacyRomMigrationOfferTests(unittest.TestCase):
    @staticmethod
    def _window_state(*, metadata=True, loaded=True):
        rom = SimpleNamespace(has_customizer_metadata=lambda: metadata) if loaded else None
        return SimpleNamespace(rom=rom, levels=[object()] if loaded else [])

    def test_runtime_extension_mismatch_is_migration_relevant(self):
        error = saver.SavePreflightError(
            "Saramandor variant runtime検証/適用",
            RuntimeError(
                "Saramandor A/B/C extension mismatch at file 0x69B9"
            ),
        )
        self.assertTrue(error.is_runtime_layout_mismatch())
        self.assertTrue(
            MainWindow._should_offer_data_migration(self._window_state(), error)
        )

    def test_runtime_signature_mismatch_is_migration_relevant(self):
        error = saver.SavePreflightError(
            "Dark Fairy runtime検証/適用",
            RuntimeError("runtime loader signature mismatch at file 0x6010"),
        )
        self.assertTrue(error.is_runtime_layout_mismatch())

    def test_non_runtime_save_constraints_do_not_offer_migration(self):
        errors = (
            saver.SavePreflightError(
                "ステージデータ検証",
                RuntimeError("extension mismatch"),
            ),
            saver.SavePreflightError(
                "Saramandor variant runtime検証/適用",
                RuntimeError("not enough space"),
            ),
            OSError("disk full"),
        )
        for error in errors:
            with self.subTest(error=error):
                self.assertFalse(
                    MainWindow._should_offer_data_migration(
                        self._window_state(),
                        error,
                    )
                )

    def test_metadata_and_loaded_editor_state_are_required(self):
        error = saver.SavePreflightError(
            "Gargoyle runtime検証/適用",
            RuntimeError("signature mismatch"),
        )
        self.assertFalse(
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


if __name__ == "__main__":
    unittest.main()

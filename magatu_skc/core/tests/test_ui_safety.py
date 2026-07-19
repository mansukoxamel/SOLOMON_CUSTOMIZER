import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QLabel,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from magatu_skc.core import config
from magatu_skc.core.i18n import get_language, set_language
from magatu_skc.ui.hack_dialog import HackDialog
from magatu_skc.ui.main_window import MainWindow
from magatu_skc.ui.settings_dialog import SettingsDialog


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


if __name__ == "__main__":
    unittest.main()

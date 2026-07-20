import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from magatu_skc.ui.pixel_editor_dialog import PixelEditorDialog


class PixelEditorCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        PixelEditorDialog._shared_clipboard_pixels = None

    @staticmethod
    def _rom():
        data = bytearray(16 + 0x8000 + 0x8000)
        data[4] = 2
        data[5] = 4

        def cpu_offset(address):
            return 0x10 + (address - 0x8000)

        for group in range(32):
            offset = cpu_offset(0xD0E8 + group * 2)
            data[offset:offset + 2] = (0xD100).to_bytes(2, "little")
        state = cpu_offset(0xD100)
        data[state:state + 4] = bytes((0x00, 0x00, 0x00, 0xD6))
        frame = cpu_offset(0xD600)
        data[frame:frame + 3] = bytes((0x00, 0x02, 0x00))
        return SimpleNamespace(data=data)

    @staticmethod
    def _pattern(seed):
        return [[(x + y + seed) & 3 for x in range(16)] for y in range(16)]

    def test_copy_is_kept_across_bank_change_and_paste_is_undoable(self):
        dialog = PixelEditorDialog(self._rom())
        source = self._pattern(1)
        dialog._set_working_pixels(source)
        dialog._copy_16x16()

        dialog._chr_bank = 1
        dialog.bank_combo.blockSignals(True)
        dialog.bank_combo.setCurrentIndex(1)
        dialog.bank_combo.blockSignals(False)
        dialog._load_current_frame()
        before = dialog._copy_pixels(dialog._pixels)

        dialog._paste_16x16()
        self.assertEqual(dialog._pixels, source)
        self.assertTrue(dialog._has_pending_changes())
        self.assertTrue(dialog.undo_btn.isEnabled())

        dialog._undo()
        self.assertEqual(dialog._pixels, before)
        self.assertFalse(dialog._has_pending_changes())
        dialog.close()

    def test_copy_is_shared_with_another_editor_window(self):
        source_dialog = PixelEditorDialog(self._rom())
        target_dialog = PixelEditorDialog(self._rom())
        source = self._pattern(3)
        source_dialog._set_working_pixels(source)

        source_dialog._copy_16x16()
        target_dialog._paste_16x16()

        self.assertEqual(target_dialog._pixels, source)
        target_dialog._undo()
        source_dialog._load_current_frame()
        source_dialog.close()
        target_dialog.close()

    def test_copy_to_all_banks_writes_the_same_visible_pixels(self):
        dialog = PixelEditorDialog(self._rom())
        source = self._pattern(2)
        dialog._set_working_pixels(source)
        before = bytes(dialog.rom.data)

        signals = []
        dialog.rom_changed.connect(lambda: signals.append(True))
        dialog._copy_to_all_banks()

        self.assertEqual(signals, [True])
        self.assertFalse(dialog._has_pending_changes())
        for bank in range(dialog.bank_count):
            dialog._chr_bank = bank
            self.assertEqual(dialog._decode_entry_pixels(dialog._entry), source)
        changed_offsets = {
            offset
            for offset, (old, new) in enumerate(zip(before, dialog.rom.data))
            if old != new
        }
        allowed_offsets = set()
        for bank in range(dialog.bank_count):
            for tile_no in dialog._entry_tiles(dialog._entry, bank):
                start = dialog.chr_start + tile_no * 16
                allowed_offsets.update(range(start, start + 16))
        self.assertTrue(changed_offsets)
        self.assertLessEqual(changed_offsets, allowed_offsets)
        dialog.close()

    def test_copy_to_all_banks_rolls_back_every_bank_on_failure(self):
        dialog = PixelEditorDialog(self._rom())
        dialog._set_working_pixels(self._pattern(1))
        before = bytes(dialog.rom.data)
        original_write = dialog._write_entry_pixels

        def fail_after_first_bank(entry, pixels=None, bank=None):
            if bank == 1:
                raise RuntimeError("injected failure")
            return original_write(entry, pixels, bank)

        with patch.object(dialog, "_write_entry_pixels", side_effect=fail_after_first_bank):
            with patch("magatu_skc.ui.pixel_editor_dialog.QMessageBox.critical") as critical:
                dialog._copy_to_all_banks()

        self.assertEqual(bytes(dialog.rom.data), before)
        critical.assert_called_once()
        dialog._load_current_frame()
        dialog.close()

    def test_chr_bank_controls_have_readable_minimum_width(self):
        dialog = PixelEditorDialog(self._rom())
        self.assertGreaterEqual(dialog.bank_combo.minimumWidth(), 88)
        dialog.close()


if __name__ == "__main__":
    unittest.main()

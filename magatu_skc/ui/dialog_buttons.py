"""Shared localization for standard dialog buttons."""

from PyQt5.QtWidgets import QDialogButtonBox

from ..core.i18n import t


_STANDARD_BUTTON_TEXT = (
    (QDialogButtonBox.Ok, "common.ok", "OK"),
    (QDialogButtonBox.Cancel, "common.cancel", "キャンセル"),
    (QDialogButtonBox.Apply, "common.apply", "適用"),
    (QDialogButtonBox.Close, "common.close", "閉じる"),
)


def localize_dialog_buttons(button_box):
    """Apply the active UI language to standard buttons present in the box."""
    for standard_button, key, fallback in _STANDARD_BUTTON_TEXT:
        button = button_box.button(standard_button)
        if button is not None:
            button.setText(t(key, fallback))

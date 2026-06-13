"""Item bulk replace dialog."""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core import constants as c
from .element_picker import MODE_ITEM, PICKER_MIME


ITEM_REPLACE_STATE_OPTIONS = [
    (c.ITEM_FLAG_NORMAL, "通常"),
    (c.ITEM_FLAG_HIDDEN, "隠し"),
    (c.ITEM_FLAG_IN_BLOCK, "ブロック内"),
    (c.ITEM_FLAG_WHITE_IN_BLOCK, "白ブロック内"),
    (c.ITEM_FLAG_VISIBLE_IN_BLOCK, "透明ブロック内"),
]
STATE_LABELS = dict(ITEM_REPLACE_STATE_OPTIONS)


class _ItemSpecDrop(QWidget):
    changed = pyqtSignal()

    def __init__(self, title, item_name_resolver, icon_provider, parent=None):
        super().__init__(parent)
        self._item_name = item_name_resolver
        self._icon_provider = icon_provider
        self._item = None
        self._state = c.ITEM_FLAG_NORMAL
        self._show_state = True
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(title)
        layout.addWidget(title_label)

        row = QHBoxLayout()
        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(48, 48)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet(
            "QLabel { border: 1px solid #2f6f3a; background: #07130a; }"
        )
        row.addWidget(self.lbl_icon)
        self.lbl_value = QLabel("未指定")
        self.lbl_value.setMinimumHeight(44)
        self.lbl_value.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.lbl_value.setStyleSheet(
            "QLabel { border: 1px solid #2f6f3a; background: #07130a; "
            "color: #54ff4d; padding: 6px; }"
        )
        row.addWidget(self.lbl_value, 1)
        layout.addLayout(row)

        hint = QLabel("ピッカーからここへドラッグすると変更できます")
        hint.setStyleSheet("color:#9aa;")
        layout.addWidget(hint)

    def set_spec(self, item_no, state):
        self._item = int(item_no) & 0x3F
        self._state = int(state)
        self._refresh_label()
        self.changed.emit()

    def set_state_visible(self, visible: bool):
        self._show_state = bool(visible)
        self._refresh_label()

    def spec(self):
        if self._item is None:
            return None
        return self._item, self._state

    def _refresh_label(self):
        if self._item is None:
            self.lbl_value.setText("未指定")
            self.lbl_icon.clear()
            return
        name = self._item_name(self._item)
        text = f"{name} (0x{self._item:02X})"
        if self._show_state:
            state = STATE_LABELS.get(self._state, f"0x{self._state:X}")
            text = f"{text} / {state}"
        self.lbl_value.setText(text)
        icon = self._icon_provider(self._item)
        pixmap = icon.pixmap(40, 40)
        self.lbl_icon.setPixmap(pixmap)

    def dragEnterEvent(self, event):
        if self._mime_to_spec(event.mimeData()) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._mime_to_spec(event.mimeData()) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        spec = self._mime_to_spec(event.mimeData())
        if spec is None:
            event.ignore()
            return
        item_no, state = spec
        self.set_spec(item_no, state)
        event.acceptProposedAction()

    @staticmethod
    def _mime_to_spec(mime):
        if not mime.hasFormat(PICKER_MIME):
            return None
        try:
            payload = bytes(mime.data(PICKER_MIME)).decode("utf-8")
            parts = payload.split("|")
            if len(parts) < 2 or parts[0] != MODE_ITEM:
                return None
            item_no = int(parts[1])
            state = int(parts[2]) if len(parts) >= 3 else c.ITEM_FLAG_NORMAL
        except Exception:
            return None
        return item_no, state


class ItemReplaceDialog(QDialog):
    """Select item/state/scope for a bulk replacement."""

    replace_requested = pyqtSignal(dict)

    def __init__(
        self,
        item_name_resolver,
        icon_provider,
        selection_available=False,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("アイテム一括置換")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        note = QLabel(
            "検索元と置換先は、開いた時点のピッカー状態で初期化されます。"
            "変更する場合はピッカーからドラッグしてください。"
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.from_spec = _ItemSpecDrop(
            "検索するアイテム（状態込み）",
            item_name_resolver,
            icon_provider,
            self,
        )
        self.to_spec = _ItemSpecDrop(
            "置換後アイテム（状態込み）",
            item_name_resolver,
            icon_provider,
            self,
        )
        layout.addWidget(self.from_spec)
        layout.addWidget(self.to_spec)

        self.chk_ignore_state = QCheckBox("検索時は状態を無視する")
        self.chk_ignore_state.setToolTip(
            "ONの場合、検索元が隠し/ブロック内などでもアイテム番号だけで検索します。"
            "置換後は上で指定した状態になります。"
        )
        self.chk_ignore_state.toggled.connect(self._on_ignore_state_toggled)
        self.chk_ignore_state.stateChanged.connect(
            lambda _state: self._on_ignore_state_toggled(self.chk_ignore_state.isChecked())
        )
        layout.addWidget(self.chk_ignore_state)

        scope_row = QHBoxLayout()
        scope_row.addWidget(QLabel("対象範囲:"))
        self.cmb_scope = QComboBox()
        if selection_available:
            self.cmb_scope.addItem("選択範囲", "selection")
        self.cmb_scope.addItem("現在ステージ", "current")
        self.cmb_scope.addItem("全ステージ", "all")
        scope_row.addWidget(self.cmb_scope, 1)
        layout.addLayout(scope_row)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.btn_replace = QPushButton("置換")
        self.btn_replace.clicked.connect(self._request_replace)
        buttons.addWidget(self.btn_replace)
        self.btn_close = QPushButton("閉じる")
        self.btn_close.clicked.connect(self.close)
        buttons.addWidget(self.btn_close)
        layout.addLayout(buttons)

        self.from_spec.changed.connect(self._update_replace_enabled)
        self.to_spec.changed.connect(self._update_replace_enabled)
        self._update_replace_enabled()

    def set_initial_from_spec(self, spec):
        if spec is not None:
            self.from_spec.set_spec(*spec)

    def set_initial_to_spec(self, spec):
        if spec is not None:
            self.to_spec.set_spec(*spec)

    def set_selection_available(self, available: bool):
        current = self.cmb_scope.currentData()
        self.cmb_scope.blockSignals(True)
        self.cmb_scope.clear()
        if available:
            self.cmb_scope.addItem("選択範囲", "selection")
        self.cmb_scope.addItem("現在ステージ", "current")
        self.cmb_scope.addItem("全ステージ", "all")
        idx = self.cmb_scope.findData(current)
        if idx >= 0:
            self.cmb_scope.setCurrentIndex(idx)
        self.cmb_scope.blockSignals(False)

    def options(self):
        self._sync_ignore_state_display()
        from_spec = self.from_spec.spec()
        to_spec = self.to_spec.spec()
        if from_spec is None or to_spec is None:
            return None
        from_item, from_state = from_spec
        to_item, to_state = to_spec
        return {
            "from_item": int(from_item),
            "to_item": int(to_item),
            "match_state": not bool(self.chk_ignore_state.isChecked()),
            "from_state": int(from_state),
            "to_state": int(to_state),
            "scope": self.cmb_scope.currentData(),
        }

    def _request_replace(self):
        self._sync_ignore_state_display()
        opts = self.options()
        if opts is not None:
            self.replace_requested.emit(opts)

    def _on_ignore_state_toggled(self, checked: bool):
        self.from_spec.set_state_visible(not bool(checked))

    def _sync_ignore_state_display(self):
        self.from_spec.set_state_visible(not self.chk_ignore_state.isChecked())

    def _update_replace_enabled(self):
        self.btn_replace.setEnabled(
            self.from_spec.spec() is not None and self.to_spec.spec() is not None
        )

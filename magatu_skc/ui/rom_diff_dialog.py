"""改造ROM差分比較ダイアログ."""
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton, QPlainTextEdit, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..core import constants as c
from ..core.rom_diff import compare_rom_stage_data
from ..gfx.level_renderer import LevelRenderer
from ..gfx.tile_renderer import TileRenderer
from ..nes.config_loader import SkcConfig
from ..nes.tile import load_chr_tiles


SORT_ROLE = Qt.UserRole + 1
DIFF_ROLE = Qt.UserRole + 2


class RomDiffDialog(QDialog):
    COLUMNS = (
        ("stage", "Stage"),
        ("total", "合計"),
        ("blocks", "ブロック"),
        ("items", "アイテム"),
        ("enemies", "敵"),
        ("meta", "メタ"),
        ("summary", "概要"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("改造ROM差分比較")
        self.resize(1120, 820)
        self.setAcceptDrops(True)
        self._result = None
        self._left_renderer = None
        self._right_renderer = None
        self._left_preview_image = None
        self._right_preview_image = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        note = QLabel(
            "ROM/ZIPを2つ選んで、ロード後のステージデータとして比較します。"
            "バイナリ差分ではなく、面ごとのブロック/アイテム/敵/メタ差分を表示します。"
            "ファイルはこの画面へドラッグ&ドロップできます。"
        )
        note.setWordWrap(True)
        root.addWidget(note)

        file_grid = QGridLayout()
        self.left_path = QLineEdit()
        self.right_path = QLineEdit()
        self.left_path.setPlaceholderText("比較元 ROM/ZIP")
        self.right_path.setPlaceholderText("比較先 ROM/ZIP")
        self.btn_left = QPushButton("参照...")
        self.btn_right = QPushButton("参照...")
        self.btn_left.clicked.connect(lambda: self._browse(self.left_path))
        self.btn_right.clicked.connect(lambda: self._browse(self.right_path))
        file_grid.addWidget(QLabel("比較元:"), 0, 0)
        file_grid.addWidget(self.left_path, 0, 1)
        file_grid.addWidget(self.btn_left, 0, 2)
        file_grid.addWidget(QLabel("比較先:"), 1, 0)
        file_grid.addWidget(self.right_path, 1, 1)
        file_grid.addWidget(self.btn_right, 1, 2)
        root.addLayout(file_grid)

        btn_row = QHBoxLayout()
        self.btn_compare = QPushButton("比較")
        self.btn_compare.clicked.connect(self._compare)
        self.lbl_result = QLabel("-")
        btn_row.addWidget(self.btn_compare)
        btn_row.addWidget(self.lbl_result, 1)
        root.addLayout(btn_row)

        self.table = QTableWidget(0, len(self.COLUMNS), self)
        self.table.setHorizontalHeaderLabels([label for _, label in self.COLUMNS])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(
            len(self.COLUMNS) - 1, QHeaderView.Stretch
        )
        self.table.itemSelectionChanged.connect(self._show_selected_details)
        root.addWidget(self.table, 3)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("表の行を選択すると、ここに詳細差分を表示します。")
        root.addWidget(self.details, 2)

        preview_group = QGroupBox("選択ステージの画像")
        preview_layout = QHBoxLayout(preview_group)
        self.left_preview = self._make_preview_panel("比較元")
        self.right_preview = self._make_preview_panel("比較先")
        preview_layout.addWidget(self.left_preview["root"], 1)
        preview_layout.addWidget(self.right_preview["root"], 1)
        root.addWidget(preview_group, 3)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        root.addLayout(close_row)

    def _make_preview_panel(self, title: str) -> dict:
        root = QWidget()
        layout = QVBoxLayout(root)
        label = QLabel(title)
        label.setAlignment(Qt.AlignCenter)
        image = QLabel("比較後、変更ステージを選択すると表示します")
        image.setAlignment(Qt.AlignCenter)
        image.setMinimumSize(384, 288)
        image.setStyleSheet("QLabel { background: #000; color: #888; }")
        layout.addWidget(label)
        layout.addWidget(image, 1)
        return {"root": root, "title": label, "image": image}

    def _browse(self, target: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "比較するROM/ZIPを選択",
            "",
            "NES ROM / ZIP (*.nes *.zip);;All files (*.*)",
        )
        if path:
            target.setText(path)

    def dragEnterEvent(self, event):
        if self._event_paths(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = self._event_paths(event)
        if not paths:
            event.ignore()
            return
        if len(paths) >= 2:
            self.left_path.setText(paths[0])
            self.right_path.setText(paths[1])
        elif not self.left_path.text().strip():
            self.left_path.setText(paths[0])
        elif not self.right_path.text().strip():
            self.right_path.setText(paths[0])
        else:
            self.right_path.setText(paths[0])
        event.acceptProposedAction()

    def _event_paths(self, event) -> list[str]:
        mime = event.mimeData()
        if not mime.hasUrls():
            return []
        paths = []
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if Path(path).suffix.lower() in (".nes", ".zip"):
                paths.append(path)
        return paths

    def _compare(self):
        left = self.left_path.text().strip()
        right = self.right_path.text().strip()
        if not left or not right:
            QMessageBox.warning(self, "ROM差分比較", "比較元と比較先を両方選択してください。")
            return
        if left == right:
            QMessageBox.warning(self, "ROM差分比較", "別々のROM/ZIPを選択してください。")
            return

        self.btn_compare.setEnabled(False)
        self.lbl_result.setText("比較中...")
        self.table.setRowCount(0)
        self.details.clear()
        self._clear_previews()
        try:
            self._result = compare_rom_stage_data(left, right)
            self._left_renderer = self._make_renderer(self._result.left_rom)
            self._right_renderer = self._make_renderer(self._result.right_rom)
        except Exception as exc:
            self._result = None
            self._left_renderer = None
            self._right_renderer = None
            QMessageBox.critical(self, "ROM差分比較", f"比較に失敗しました。\n{exc}")
            self.lbl_result.setText("比較失敗")
            return
        finally:
            self.btn_compare.setEnabled(True)

        self._populate_table()

    def _populate_table(self):
        result = self._result
        self.table.setSortingEnabled(False)
        changed = [stage for stage in result.stages if stage.changed]
        self.table.setRowCount(len(changed))

        for row, stage in enumerate(changed):
            values = {
                "stage": "全体" if stage.stage_no == 0 else str(stage.stage_no),
                "total": stage.total_changes,
                "blocks": stage.block_changes,
                "items": stage.item_changes,
                "enemies": stage.enemy_changes,
                "meta": stage.meta_changes,
                "summary": stage.summary_text(),
            }
            for col, (key, _label) in enumerate(self.COLUMNS):
                item = DiffTableItem(str(values[key]))
                sort_value = values[key] if isinstance(values[key], int) else stage.stage_no
                item.setData(SORT_ROLE, sort_value)
                item.setData(DIFF_ROLE, stage)
                if key != "summary":
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col, item)

        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.AscendingOrder)
        self.lbl_result.setText(
            f"{result.left_region} {result.left_crc} -> "
            f"{result.right_region} {result.right_crc} / "
            f"変更ステージ {result.changed_stage_count} / "
            f"差分 {result.total_changes}"
        )
        if changed:
            self.table.selectRow(0)
        else:
            self.details.setPlainText("ステージデータ差分はありません。")
            self._clear_previews()

    def _show_selected_details(self):
        items = self.table.selectedItems()
        if not items:
            return
        stage = items[0].data(DIFF_ROLE)
        if stage is None:
            return
        title = "全体" if stage.stage_no == 0 else f"Stage {stage.stage_no}"
        lines = [
            title,
            f"合計: {stage.total_changes} / "
            f"ブロック: {stage.block_changes} / "
            f"アイテム: {stage.item_changes} / "
            f"敵: {stage.enemy_changes} / メタ: {stage.meta_changes}",
            "",
        ]
        lines.extend(stage.details)
        self.details.setPlainText("\n".join(lines))
        self._update_previews(stage.stage_no)

    def _make_renderer(self, rom):
        cfg_path = Path(__file__).parent.parent / "skc_config.xml"
        config = SkcConfig.load(str(cfg_path), rom_data=bytes(rom.data), region=rom.region)
        from ..core.constants import ROM_OFFSETS
        gfx_offset = ROM_OFFSETS[rom.base_region()]["gfx"]
        if rom.is_expanded():
            gfx_offset = 0x10010
        nes_tiles = load_chr_tiles(bytes(rom.data), gfx_offset, c.NES_TILE_COUNT)
        return LevelRenderer(TileRenderer(config, nes_tiles), config)

    def _update_previews(self, stage_no: int):
        if not self._result or stage_no <= 0:
            self._clear_previews()
            return
        idx = stage_no - 1
        if idx >= len(self._result.left_levels) or idx >= len(self._result.right_levels):
            self._clear_previews()
            return
        self._left_preview_image = self._left_renderer.render(
            self._result.left_levels[idx],
            level_no=idx,
            show_grid=False,
            show_hidden_overlay=True,
            show_col15=True,
        )
        self._right_preview_image = self._right_renderer.render(
            self._result.right_levels[idx],
            level_no=idx,
            show_grid=False,
            show_hidden_overlay=True,
            show_col15=True,
        )
        self.left_preview["title"].setText(f"比較元 Stage {stage_no}")
        self.right_preview["title"].setText(f"比較先 Stage {stage_no}")
        self._refresh_preview_labels()

    def _refresh_preview_labels(self):
        self._set_preview_image(self.left_preview["image"], self._left_preview_image)
        self._set_preview_image(self.right_preview["image"], self._right_preview_image)

    def _set_preview_image(self, label: QLabel, image):
        if image is None or image.isNull():
            label.setText("画像なし")
            label.setPixmap(QPixmap())
            return
        pixmap = QPixmap.fromImage(image).scaled(
            label.size(),
            Qt.KeepAspectRatio,
            Qt.FastTransformation,
        )
        label.setText("")
        label.setPixmap(pixmap)

    def _clear_previews(self):
        self._left_preview_image = None
        self._right_preview_image = None
        self.left_preview["title"].setText("比較元")
        self.right_preview["title"].setText("比較先")
        self.left_preview["image"].setPixmap(QPixmap())
        self.right_preview["image"].setPixmap(QPixmap())
        self.left_preview["image"].setText("比較後、変更ステージを選択すると表示します")
        self.right_preview["image"].setText("比較後、変更ステージを選択すると表示します")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._left_preview_image is not None or self._right_preview_image is not None:
            self._refresh_preview_labels()


class DiffTableItem(QTableWidgetItem):
    def __lt__(self, other):
        left = self.data(SORT_ROLE)
        right = other.data(SORT_ROLE)
        if left is not None and right is not None:
            return left < right
        return super().__lt__(other)

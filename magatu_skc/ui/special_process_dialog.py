"""特殊処理ビューア (Phase 1 - 読込専用)

現在ROMから全53ステージの特殊処理を読み出し、生バイト列と注釈付き擬似アセンブラを表示する。
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialogButtonBox,
    QPlainTextEdit, QSplitter, QListWidget, QListWidgetItem, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from ..core import special_process as sp
from ..core.i18n import t
from .dialog_geometry import restore_dialog_geometry, save_dialog_geometry
from .dialog_buttons import localize_dialog_buttons


class SpecialProcessDialog(QDialog):
    """特殊処理ビューア（読込専用）"""

    def __init__(self, rom, initial_level_no: int = 0, parent=None,
                 app_config=None):
        super().__init__(parent)
        if parent is not None:
            self.setFont(parent.font())
        self.setWindowTitle(t(
            "special_process_dialog.title",
            "特殊処理ビューア (Phase 1 - 読込専用)",
        ))
        self.resize(1000, 600)
        self._app_config = app_config
        self.rom = rom
        self.region = rom.base_region()
        self.rom_data = bytes(rom.data)
        self.initial_level_no = initial_level_no

        self._build_ui()
        self._populate_level_list()
        # 初期ステージを選択
        if 0 <= initial_level_no < sp.NUM_LEVELS:
            self.list_levels.setCurrentRow(initial_level_no)
        restore_dialog_geometry(self, self._app_config, "special_process_dlg")

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 上部情報
        info_text = (
            t("special_process_dialog.region_html", "<b>リージョン:</b> {region}").format(
                region=self.region
            )
        )
        table_off = sp.get_dispatch_table(self.region)
        if table_off is None:
            info_text += (
                "<br>"
                + t(
                    "special_process_dialog.unsupported_html",
                    "<span style='color:#ef4444'><b>⚠ 未対応リージョン</b>: "
                    "このリージョンの特殊処理テーブル位置は未確認です。</span>",
                )
            )
        else:
            info_text += " / " + t(
                "special_process_dialog.dispatch_html",
                "<b>ディスパッチテーブル:</b> 0x{offset:04X}",
            ).format(offset=table_off)
            info_text += (
                "<br>"
                + t(
                    "special_process_dialog.source_html",
                    "<span style='color:#888;font-size:11px'>"
                    "出典: BESK (Binary Editor for Solomon's Key) を逆コンパイル + JP/USA ROM 直接検証"
                    "</span>",
                )
            )
        lbl_info = QLabel(info_text)
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        # スプリッタ: 左=ステージ一覧、右=詳細
        splitter = QSplitter(Qt.Horizontal)

        # 左: ステージ一覧
        self.list_levels = QListWidget()
        self.list_levels.setMinimumWidth(220)
        self.list_levels.currentRowChanged.connect(self._on_level_selected)
        splitter.addWidget(self.list_levels)

        # 右: 詳細表示
        right_widget = QSplitter(Qt.Vertical)

        # 右上: 生バイト
        bytes_group = QGroupBox(t(
            "special_process_dialog.bytes.group",
            "生バイト (ROM)",
        ))
        bg_layout = QVBoxLayout(bytes_group)
        self.txt_bytes = QPlainTextEdit()
        self.txt_bytes.setReadOnly(True)
        self.txt_bytes.setFont(QFont("Consolas", 10))
        self.txt_bytes.setLineWrapMode(QPlainTextEdit.NoWrap)
        bg_layout.addWidget(self.txt_bytes)
        right_widget.addWidget(bytes_group)

        # 右下: 擬似アセンブラ + 注釈
        asm_group = QGroupBox(t(
            "special_process_dialog.asm.group",
            "擬似アセンブラ + 注釈",
        ))
        ag_layout = QVBoxLayout(asm_group)
        self.txt_asm = QPlainTextEdit()
        self.txt_asm.setReadOnly(True)
        self.txt_asm.setFont(QFont("Consolas", 10))
        self.txt_asm.setLineWrapMode(QPlainTextEdit.NoWrap)
        ag_layout.addWidget(self.txt_asm)
        right_widget.addWidget(asm_group)

        right_widget.setSizes([200, 400])

        splitter.addWidget(right_widget)
        splitter.setSizes([220, 780])

        layout.addWidget(splitter, 1)

        # 閉じる
        btnbox = QDialogButtonBox(QDialogButtonBox.Close)
        localize_dialog_buttons(btnbox)
        btnbox.rejected.connect(self.reject)
        layout.addWidget(btnbox)

    def _populate_level_list(self):
        """全53ステージの概要をリストに表示"""
        self.list_levels.clear()
        for N in range(sp.NUM_LEVELS):
            addr, data = sp.get_special_process_bytes(self.rom_data, self.region, N)
            if addr is None:
                label = t(
                    "special_process_dialog.level.unsupported",
                    "L{level:2d}  (未対応)",
                ).format(level=N + 1)
            else:
                length = len(data)
                # サイズで分類
                if length <= 1:
                    kind = "empty"
                elif length <= 3:
                    kind = "JMP only"
                elif length <= 8:
                    kind = t("special_process_dialog.kind.short", "短い")
                elif length <= 50:
                    kind = t("special_process_dialog.kind.medium", "中")
                else:
                    kind = t("special_process_dialog.kind.large", "★大規模")
                label = f"L{N + 1:2d}  0x{addr:04X}  {length:3d}B  [{kind}]"
            item = QListWidgetItem(label)
            self.list_levels.addItem(item)

    def _on_level_selected(self, row: int):
        if row < 0:
            return
        addr, data = sp.get_special_process_bytes(self.rom_data, self.region, row)
        if addr is None:
            self.txt_bytes.setPlainText(t(
                "special_process_dialog.unsupported_text",
                "(リージョン未対応のため表示できません)",
            ))
            self.txt_asm.setPlainText("")
            return

        # 生バイト表示 (16バイトずつ + アドレス付き)
        lines = []
        lines.append(t(
            "special_process_dialog.bytes.stage_comment",
            "; Stage {stage} 特殊処理",
        ).format(stage=row + 1))
        lines.append(f"; ROM offset: 0x{addr:04X}")
        lines.append(f"; Length: {len(data)} bytes")
        lines.append("")
        for k in range(0, len(data), 16):
            chunk = data[k:k + 16]
            hex_str = " ".join(f"{b:02X}" for b in chunk)
            lines.append(f"0x{addr + k:04X}: {hex_str}")
        self.txt_bytes.setPlainText("\n".join(lines))

        # 擬似アセンブラ表示
        asm_text = sp.annotate_bytes(data, self.region)
        self.txt_asm.setPlainText(asm_text)

    def done(self, r):
        save_dialog_geometry(self, self._app_config, "special_process_dlg")
        super().done(r)

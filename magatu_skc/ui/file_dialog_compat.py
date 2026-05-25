"""Small QFileDialog wrapper used instead of local machine-only helpers."""

from __future__ import annotations

from PyQt5.QtWidgets import QFileDialog


def _qt_filter(filter: str) -> str:
    text = (filter or "").strip()
    if not text:
        return "All files (*)"
    if ";;" in text or "(" in text:
        return text
    return f"Files ({text});;All files (*)"


def get_file(parent=None, *, title: str = "ファイルを選択", filter: str = "*", directory: str = "") -> str:
    path, _ = QFileDialog.getOpenFileName(parent, title, directory, _qt_filter(filter))
    return path


def get_folder(parent=None, *, title: str = "フォルダを選択", directory: str = "") -> str:
    return QFileDialog.getExistingDirectory(parent, title, directory)


def get_path(
    parent=None,
    *,
    title: str = "保存先を選択",
    filter: str = "*",
    mode: str = "open",
    directory: str = "",
) -> str:
    if mode == "save":
        path, _ = QFileDialog.getSaveFileName(parent, title, directory, _qt_filter(filter))
        return path
    return get_file(parent, title=title, filter=filter, directory=directory)

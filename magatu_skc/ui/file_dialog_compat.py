"""Small QFileDialog wrapper used instead of local machine-only helpers."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtWidgets import QFileDialog

from ..core.config import save_config
from ..core.i18n import t


def _qt_filter(filter: str) -> str:
    text = (filter or "").strip()
    if not text:
        return "All files (*)"
    if ";;" in text or "(" in text:
        return text
    return f"Files ({text});;All files (*)"


def _stored_dialog_dir(app_config: dict | None, config_key: str | None) -> Path | None:
    if not isinstance(app_config, dict) or not config_key:
        return None
    dirs = app_config.get("last_file_dialog_dirs")
    if not isinstance(dirs, dict):
        return None
    raw = str(dirs.get(config_key, "") or "").strip()
    if not raw:
        return None
    try:
        path = Path(raw)
        if path.exists() and path.is_dir():
            return path
    except Exception:
        return None
    return None


def _initial_dialog_path(
    directory: str,
    app_config: dict | None,
    config_key: str | None,
) -> str:
    stored = _stored_dialog_dir(app_config, config_key)
    default = str(directory or "")
    if stored is None:
        return default
    if not default:
        return str(stored)
    try:
        default_path = Path(default)
        if default_path.name and not default_path.exists():
            return str(stored / default_path.name)
    except Exception:
        pass
    return str(stored)


def _remember_dialog_path(
    selected_path: str,
    app_config: dict | None,
    config_key: str | None,
    *,
    is_folder: bool = False,
    persist_config: bool = True,
) -> None:
    if not selected_path or not isinstance(app_config, dict) or not config_key:
        return
    try:
        path = Path(selected_path)
        folder = path if is_folder else path.parent
        if not folder.exists() or not folder.is_dir():
            return
        dirs = app_config.get("last_file_dialog_dirs")
        if not isinstance(dirs, dict):
            dirs = {}
            app_config["last_file_dialog_dirs"] = dirs
        dirs[config_key] = str(folder)
        if persist_config:
            save_config(app_config)
    except Exception:
        pass


def get_file(
    parent=None,
    *,
    title: str = "ファイルを選択",
    filter: str = "*",
    directory: str = "",
    app_config: dict | None = None,
    config_key: str | None = None,
    persist_config: bool = True,
) -> str:
    if title == "ファイルを選択":
        title = t("file_dialog.select_file", "ファイルを選択")
    directory = _initial_dialog_path(directory, app_config, config_key)
    path, _ = QFileDialog.getOpenFileName(parent, title, directory, _qt_filter(filter))
    _remember_dialog_path(path, app_config, config_key, persist_config=persist_config)
    return path


def get_folder(
    parent=None,
    *,
    title: str = "フォルダを選択",
    directory: str = "",
    app_config: dict | None = None,
    config_key: str | None = None,
    persist_config: bool = True,
) -> str:
    if title == "フォルダを選択":
        title = t("file_dialog.select_folder", "フォルダを選択")
    directory = _initial_dialog_path(directory, app_config, config_key)
    path = QFileDialog.getExistingDirectory(parent, title, directory)
    _remember_dialog_path(
        path,
        app_config,
        config_key,
        is_folder=True,
        persist_config=persist_config,
    )
    return path


def get_path(
    parent=None,
    *,
    title: str = "保存先を選択",
    filter: str = "*",
    mode: str = "open",
    directory: str = "",
    app_config: dict | None = None,
    config_key: str | None = None,
    persist_config: bool = True,
) -> str:
    if title == "保存先を選択":
        title = t("file_dialog.select_save_path", "保存先を選択")
    directory = _initial_dialog_path(directory, app_config, config_key)
    if mode == "save":
        path, _ = QFileDialog.getSaveFileName(parent, title, directory, _qt_filter(filter))
        _remember_dialog_path(path, app_config, config_key, persist_config=persist_config)
        return path
    return get_file(
        parent,
        title=title,
        filter=filter,
        directory=directory,
        app_config=app_config,
        config_key=config_key,
        persist_config=persist_config,
    )

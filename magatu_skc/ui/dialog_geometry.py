"""Shared dialog geometry restore/save helpers."""

from ..core.config import save_config


def _as_int(value, default=-1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def restore_dialog_geometry(dialog, app_config, prefix: str, min_w=100, min_h=100):
    if app_config is None:
        return
    w = _as_int(app_config.get(f"{prefix}_w"))
    h = _as_int(app_config.get(f"{prefix}_h"))
    x = _as_int(app_config.get(f"{prefix}_x"))
    y = _as_int(app_config.get(f"{prefix}_y"))
    if w > min_w and h > min_h:
        dialog.resize(w, h)
    if x >= 0 and y >= 0:
        dialog.move(x, y)


def save_dialog_geometry(dialog, app_config, prefix: str):
    if app_config is None:
        return
    try:
        app_config[f"{prefix}_x"] = max(0, dialog.x())
        app_config[f"{prefix}_y"] = max(0, dialog.y())
        app_config[f"{prefix}_w"] = dialog.width()
        app_config[f"{prefix}_h"] = dialog.height()
        save_config(app_config)
    except Exception:
        pass

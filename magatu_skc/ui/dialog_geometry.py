"""Shared dialog geometry restore/save helpers."""

from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QApplication

from ..core.config import save_config


def _as_int(value, default=-1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fallback_screen(dialog):
    parent = dialog.parentWidget()
    if parent is not None:
        try:
            screen = parent.screen()
            if screen is not None:
                return screen
        except (AttributeError, RuntimeError):
            pass
    return QApplication.primaryScreen()


def _screen_for_rect(dialog, rect):
    screens = QApplication.screens()
    if not screens:
        return None, False
    best_screen = None
    best_area = 0
    for screen in screens:
        intersection = screen.availableGeometry().intersected(rect)
        area = max(0, intersection.width()) * max(0, intersection.height())
        if area > best_area:
            best_screen = screen
            best_area = area
    if best_screen is not None and best_area > 0:
        return best_screen, True
    return _fallback_screen(dialog) or screens[0], False


def restore_dialog_geometry_values(
    dialog,
    width,
    height,
    x,
    y,
    min_w=100,
    min_h=100,
):
    """Restore a dialog inside the currently connected screen work areas."""
    stored_w = _as_int(width, None)
    stored_h = _as_int(height, None)
    stored_x = _as_int(x, None)
    stored_y = _as_int(y, None)
    if stored_x == -1 and stored_y == -1:
        stored_x = None
        stored_y = None

    desired_w = stored_w if stored_w is not None and stored_w > min_w else dialog.width()
    desired_h = stored_h if stored_h is not None and stored_h > min_h else dialog.height()
    have_position = stored_x is not None and stored_y is not None
    probe = QRect(
        stored_x if have_position else dialog.x(),
        stored_y if have_position else dialog.y(),
        max(1, desired_w),
        max(1, desired_h),
    )
    screen, intersects = _screen_for_rect(dialog, probe)
    if screen is None:
        dialog.resize(desired_w, desired_h)
        if have_position:
            dialog.move(stored_x, stored_y)
        return

    available = screen.availableGeometry()
    restored_w = min(max(1, desired_w), available.width())
    restored_h = min(max(1, desired_h), available.height())
    dialog.resize(restored_w, restored_h)
    if not have_position:
        return

    if intersects:
        restored_x = max(
            available.left(),
            min(stored_x, available.right() - restored_w + 1),
        )
        restored_y = max(
            available.top(),
            min(stored_y, available.bottom() - restored_h + 1),
        )
    else:
        restored_x = available.left() + max(0, (available.width() - restored_w) // 2)
        restored_y = available.top() + max(0, (available.height() - restored_h) // 2)
    dialog.move(restored_x, restored_y)


def restore_dialog_geometry(dialog, app_config, prefix: str, min_w=100, min_h=100):
    if app_config is None:
        return
    restore_dialog_geometry_values(
        dialog,
        app_config.get(f"{prefix}_w"),
        app_config.get(f"{prefix}_h"),
        app_config.get(f"{prefix}_x"),
        app_config.get(f"{prefix}_y"),
        min_w=min_w,
        min_h=min_h,
    )


def store_dialog_geometry(dialog, app_config, prefix: str):
    if app_config is None:
        return
    app_config[f"{prefix}_x"] = int(dialog.x())
    app_config[f"{prefix}_y"] = int(dialog.y())
    app_config[f"{prefix}_w"] = int(dialog.width())
    app_config[f"{prefix}_h"] = int(dialog.height())


def save_dialog_geometry(dialog, app_config, prefix: str):
    if app_config is None:
        return
    try:
        store_dialog_geometry(dialog, app_config, prefix)
        save_config(app_config)
    except Exception:
        pass

"""Application-wide Qt stylesheet helpers."""


DEFAULT_THEME_GRAY = 222
MIN_THEME_GRAY = 190
MAX_THEME_GRAY = 245


def _clamp_gray(value: int) -> int:
    try:
        gray = int(value)
    except (TypeError, ValueError):
        gray = DEFAULT_THEME_GRAY
    return max(MIN_THEME_GRAY, min(MAX_THEME_GRAY, gray))


def _gray(value: int) -> str:
    value = max(0, min(255, int(value)))
    return f"#{value:02x}{value:02x}{value:02x}"


def build_app_stylesheet(theme_gray: int = DEFAULT_THEME_GRAY) -> str:
    """Build the global Qt stylesheet from a single gray-base setting."""
    base = _clamp_gray(theme_gray)
    window = _gray(base - 7)
    widget = _gray(base)
    group = _gray(base + 5)
    field = _gray(base + 16)
    button = _gray(base + 10)
    hover = _gray(base + 19)
    pressed = _gray(base - 14)
    border = _gray(base - 38)
    header = _gray(base - 14)

    return f"""
QWidget {{
    background: {widget};
    color: #111111;
}}
QMainWindow, QDialog {{
    background: {window};
}}
QGroupBox {{
    background: {group};
    border: 1px solid {border};
    border-radius: 3px;
    margin-top: 13px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 7px;
    padding: 0 3px;
}}
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit,
QListWidget, QTableWidget, QTreeWidget {{
    background: {field};
    border: 1px solid {border};
    selection-background-color: #8aa7c7;
    selection-color: #101010;
}}
QPushButton, QToolButton {{
    background: {button};
    border: 1px solid {border};
    border-radius: 2px;
    padding: 2px 6px;
}}
QPushButton:hover, QToolButton:hover {{
    background: {hover};
}}
QPushButton:pressed, QToolButton:pressed {{
    background: {pressed};
}}
QPushButton#testPlayButton {{
    background: #168f3f;
    color: #ffffff;
    border: 1px solid #0c5f28;
    font-weight: 700;
    padding: 5px 8px;
}}
QPushButton#testPlayButton:hover {{
    background: #1fab50;
}}
QPushButton#testPlayButton:pressed {{
    background: #0f6f31;
}}
QPushButton#testPlayButton:disabled {{
    background: #b8d8c0;
    color: #5f7b66;
    border: 1px solid #8eaa95;
}}
QPushButton:disabled, QToolButton:disabled,
QRadioButton:disabled, QCheckBox:disabled, QLabel:disabled {{
    color: #777777;
}}
QScrollArea, QSplitter, QStatusBar {{
    background: {window};
}}
QHeaderView::section {{
    background: {header};
    border: 1px solid {border};
    padding: 2px;
}}
"""

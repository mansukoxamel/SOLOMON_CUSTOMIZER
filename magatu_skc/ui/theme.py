"""Application-wide Qt stylesheet helpers."""


DEFAULT_THEME_GRAY = 18
MIN_THEME_GRAY = 8
MAX_THEME_GRAY = 44


def _clamp_gray(value: int) -> int:
    try:
        gray = int(value)
    except (TypeError, ValueError):
        gray = DEFAULT_THEME_GRAY
    if gray > 100:
        # v0.7.152 and earlier stored light-theme gray values around 222.
        # Treat those legacy values as "use the dark theme default".
        return DEFAULT_THEME_GRAY
    return max(MIN_THEME_GRAY, min(MAX_THEME_GRAY, gray))


def normalize_theme_gray(value: int) -> int:
    return _clamp_gray(value)


def _rgb(r: int, g: int, b: int) -> str:
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return f"#{r:02x}{g:02x}{b:02x}"


def build_app_stylesheet(theme_gray: int = DEFAULT_THEME_GRAY) -> str:
    """Build the global dark Qt stylesheet from a single brightness setting."""
    base = _clamp_gray(theme_gray)
    window = _rgb(base - 11, base - 7, base - 10)
    widget = _rgb(base, base + 3, base)
    group = _rgb(base + 3, base + 10, base + 4)
    field = _rgb(base - 7, base - 4, base - 6)
    button = _rgb(base + 2, base + 42, base + 10)
    hover = _rgb(base + 6, base + 61, base + 16)
    pressed = _rgb(base - 2, base + 28, base + 7)
    border = _rgb(base + 33, base + 70, base + 36)
    header = _rgb(base + 5, base + 45, base + 9)
    text = "#18ff2a"
    muted = "#95d79d"
    strong = "#6dff75"
    selection = "#21ff36"

    return f"""
QWidget {{
    background: {widget};
    color: {text};
}}
QMainWindow, QDialog {{
    background: {window};
}}
QGroupBox {{
    background: {group};
    border: 1px solid {border};
    border-radius: 3px;
    margin-top: 13px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 7px;
    padding: 0 3px;
    color: {strong};
    background: {window};
}}
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit, QTextEdit,
QListWidget, QTableWidget, QTreeWidget {{
    background: {field};
    border: 1px solid {border};
    color: {text};
    selection-background-color: {selection};
    selection-color: #050805;
}}
QPushButton, QToolButton {{
    background: {button};
    border: 1px solid {border};
    border-radius: 2px;
    padding: 2px 6px;
    color: {text};
    font-weight: 600;
}}
QPushButton:hover, QToolButton:hover {{
    background: {hover};
}}
QPushButton:pressed, QToolButton:pressed {{
    background: {pressed};
}}
QPushButton#testPlayButton {{
    background: #008f22;
    color: #ffffff;
    border: 1px solid #20ff42;
    font-weight: 700;
    padding: 5px 8px;
}}
QPushButton#testPlayButton:hover {{
    background: #00b82e;
}}
QPushButton#testPlayButton:pressed {{
    background: #006d1b;
}}
QPushButton#testPlayButton:disabled {{
    background: #12331a;
    color: #5b8b62;
    border: 1px solid #2e5b35;
}}
QPushButton:disabled, QToolButton:disabled,
QRadioButton:disabled, QCheckBox:disabled, QLabel:disabled {{
    color: #4b6d50;
}}
QPushButton:disabled, QToolButton:disabled {{
    background: #111a12;
    border: 1px solid #263b29;
}}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled,
QPlainTextEdit:disabled, QTextEdit:disabled,
QListWidget:disabled, QTableWidget:disabled, QTreeWidget:disabled {{
    background: #090c09;
    color: #4b6d50;
    border: 1px solid #263b29;
}}
QLabel#stageSelectTitle {{
    color: #6dff75;
    font-weight: 800;
    padding: 1px 2px;
}}
QSpinBox#stageSelectSpin {{
    background: #008f22;
    color: #ffffff;
    border: 1px solid #20ff42;
    border-radius: 2px;
    font-weight: 800;
    min-height: 30px;
    padding: 3px 8px;
    selection-background-color: #21ff36;
    selection-color: #050805;
}}
QSpinBox#stageSelectSpin:hover {{
    background: #00b82e;
}}
QSpinBox#stageSelectSpin:focus {{
    background: #006d1b;
}}
QSpinBox#stageSelectSpin::up-button, QSpinBox#stageSelectSpin::down-button {{
    border-left: 1px solid #20ff42;
    background: #006d1b;
}}
QScrollArea, QSplitter, QStatusBar {{
    background: {window};
    color: {muted};
}}
QHeaderView::section {{
    background: {header};
    border: 1px solid {border};
    padding: 2px;
    color: {strong};
}}
QTabWidget::pane {{
    border: 1px solid {border};
    background: {window};
}}
QTabBar::tab {{
    background: {button};
    color: {text};
    border: 1px solid {border};
    padding: 5px 10px;
    margin-right: 2px;
    font-weight: 700;
}}
QTabBar::tab:selected {{
    background: {hover};
    color: #ffffff;
}}
QRadioButton, QCheckBox {{
    color: {text};
}}
QCheckBox::indicator {{
    width: 13px;
    height: 13px;
    background: #050805;
    border: 1px solid #3d8f48;
    border-radius: 2px;
}}
QCheckBox::indicator:hover {{
    border: 1px solid #6dff75;
    background: #071407;
}}
QCheckBox::indicator:checked {{
    background: #00b82e;
    border: 1px solid #8dff93;
}}
QCheckBox::indicator:disabled {{
    background: #090c09;
    border: 1px solid #263b29;
}}
QComboBox::drop-down {{
    border-left: 1px solid {border};
    background: {button};
}}
QMenu {{
    background: {field};
    color: {text};
    border: 1px solid {border};
}}
QMenu::item:selected {{
    background: {selection};
    color: #050805;
}}
QToolTip {{
    background: #071007;
    color: {text};
    border: 1px solid {border};
}}
QScrollBar:vertical, QScrollBar:horizontal {{
    background: {window};
    border: 1px solid {border};
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {button};
    border: 1px solid {border};
    min-height: 24px;
    min-width: 24px;
}}
"""

"""SOLOMON_CUSTOMIZER エントリポイント"""
import sys
from pathlib import Path

# Windows タスクバーで独立アプリとして認識させる（マルチモニタ対策）
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Chaos.SOLOMON_CUSTOMIZER"
        )
    except Exception as e:
        print(f"AppUserModelID set failed: {e}")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from magatu_skc.core.config import load_config
from magatu_skc.ui.main_window import MainWindow
from magatu_skc.ui.theme import build_app_stylesheet, DEFAULT_THEME_GRAY


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # スタイルシート互換確保
    cfg = load_config()
    app.setStyleSheet(
        build_app_stylesheet(cfg.get("theme_gray", DEFAULT_THEME_GRAY))
    )
    icon_path = cfg.get("icon_path", "")
    if icon_path and Path(icon_path).exists():
        app.setWindowIcon(QIcon(icon_path))

    win = MainWindow()
    if icon_path and Path(icon_path).exists():
        win.setWindowIcon(QIcon(icon_path))
    win.show()

    # コマンドライン引数でROMが渡された場合は読み込む
    if len(sys.argv) > 1:
        rom_path = sys.argv[1]
        if Path(rom_path).exists():
            win.load_rom(rom_path)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

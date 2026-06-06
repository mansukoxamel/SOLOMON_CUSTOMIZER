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
from PyQt5.QtCore import QTimer
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

from magatu_skc.core.config import load_config, resolve_project_path
from magatu_skc.ui.main_window import MainWindow
from magatu_skc.ui.theme import build_app_stylesheet, DEFAULT_THEME_GRAY

SINGLE_INSTANCE_SERVER = "Chaos.SOLOMON_CUSTOMIZER.SingleInstance"


def _notify_existing_instance() -> bool:
    socket = QLocalSocket()
    socket.connectToServer(SINGLE_INSTANCE_SERVER)
    if not socket.waitForConnected(200):
        return False
    socket.write(b"activate\n")
    socket.flush()
    socket.waitForBytesWritten(200)
    socket.disconnectFromServer()
    return True


def _create_single_instance_server(win: MainWindow) -> QLocalServer:
    server = QLocalServer(win)

    def activate_window():
        while server.hasPendingConnections():
            conn = server.nextPendingConnection()
            conn.readAll()
            conn.disconnectFromServer()
        if win.isMinimized():
            win.showNormal()
        win.raise_()
        win.activateWindow()
        win.statusBar().showMessage(
            "既に起動中のSOLOMON_CUSTOMIZERを前面に表示しました", 3000
        )

    server.newConnection.connect(activate_window)
    QLocalServer.removeServer(SINGLE_INSTANCE_SERVER)
    if not server.listen(SINGLE_INSTANCE_SERVER):
        raise RuntimeError(f"single instance server listen failed: {server.errorString()}")
    return server


def main():
    app = QApplication(sys.argv)
    if _notify_existing_instance():
        return

    app.setStyle("Fusion")  # スタイルシート互換確保
    cfg = load_config()
    app.setStyleSheet(
        build_app_stylesheet(cfg.get("theme_gray", DEFAULT_THEME_GRAY))
    )
    icon_path = cfg.get("icon_path", "")
    resolved_icon_path = resolve_project_path(icon_path) if icon_path else None
    if resolved_icon_path and resolved_icon_path.exists():
        app.setWindowIcon(QIcon(str(resolved_icon_path)))

    win = MainWindow()
    if resolved_icon_path and resolved_icon_path.exists():
        win.setWindowIcon(QIcon(str(resolved_icon_path)))
    single_instance_server = _create_single_instance_server(win)
    app.aboutToQuit.connect(single_instance_server.close)
    win.show()

    # コマンドライン引数でROMが渡された場合は読み込む。
    # 指定が無い通常起動では、前回終了時の自動保存ROMを復元する。
    if len(sys.argv) > 1:
        rom_path = sys.argv[1]
        if Path(rom_path).exists():
            win.load_rom(rom_path)
    else:
        win.restore_previous_workstate_if_available()

    QTimer.singleShot(0, win.raise_)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

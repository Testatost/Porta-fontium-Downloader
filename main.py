from __future__ import annotations

import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyleFactory
from pfdownloader.app_constants import APP_DISPLAY_NAME
from pfdownloader.icons import get_app_icon, resource_path, set_windows_app_id, find_linux_desktop_file_basename
from pfdownloader.main_window import MainWindow


def main() -> int:
    set_windows_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)

    # Windows: keep the platform style selection used by the original v1.6.
    if sys.platform.startswith("win"):
        for name in ("windowsvista", "WindowsVista", "windows11", "Windows11", "windows", "Windows", "Fusion"):
            style = QStyleFactory.create(name)
            if style:
                app.setStyle(style)
                break
    else:
        name = find_linux_desktop_file_basename()
        if name:
            app.setDesktopFileName(name)
        style = QStyleFactory.create("Fusion")
        if style:
            app.setStyle(style)

    # Under Windows use only the bundled static PNG file for the application
    # icon (as in v1.6); do not generate QPainter icon pixmaps at startup.
    win_legacy_ui = sys.platform.startswith("win") and os.environ.get("PF_17_FULL_ICONS") != "1"
    icon = QIcon(resource_path("icon.png")) if win_legacy_ui else get_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)

    window = MainWindow(windows_safe_mode=win_legacy_ui)
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

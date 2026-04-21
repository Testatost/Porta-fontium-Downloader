from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QStyleFactory

from pfdownloader.app_constants import APP_DISPLAY_NAME
from pfdownloader.icons import get_app_icon, set_windows_app_id
from pfdownloader.main_window import MainWindow


def main() -> int:
    set_windows_app_id()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)

    if sys.platform.startswith("win"):
        for style_name in ("windowsvista", "WindowsVista", "windows11", "Windows11", "windows", "Windows", "Fusion"):
            style = QStyleFactory.create(style_name)
            if style:
                app.setStyle(style)
                break
    else:
        style = QStyleFactory.create("Fusion")
        if style:
            app.setStyle(style)

    app_icon = get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    window = MainWindow()
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

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
    app.setStyle(QStyleFactory.create("Fusion"))

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

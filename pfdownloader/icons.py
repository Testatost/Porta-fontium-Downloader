from __future__ import annotations

import ctypes
import os
import sys

from PySide6.QtGui import QIcon

from pfdownloader.app_constants import APP_ID


def resource_path(filename: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))
    return os.path.join(base_path, filename)


def get_app_icon() -> QIcon:
    icon = QIcon()

    for filename in ("icon.ico", "icon.png", "logo.png"):
        path = resource_path(filename)
        if os.path.exists(path):
            icon.addFile(path)

    return icon


def set_windows_app_id() -> None:
    if sys.platform.startswith("win"):
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass

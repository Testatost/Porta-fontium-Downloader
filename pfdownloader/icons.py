from __future__ import annotations

import ctypes
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPen, QPixmap

from pathlib import Path

from pfdownloader.app_constants import APP_DISPLAY_NAME, APP_ID, LINUX_DESKTOP_FILE_BASENAME


def resource_path(filename: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))
    return os.path.join(base_path, filename)


def get_app_icon() -> QIcon:
    icon = QIcon()

    icon_candidates = ("icon.png", "icon.ico", "logo.png") if sys.platform.startswith("linux") else ("icon.ico", "icon.png", "logo.png")

    for filename in icon_candidates:
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


def find_linux_desktop_file_basename() -> str | None:
    if not sys.platform.startswith("linux"):
        return None

    candidates = []
    xdg_home = os.environ.get("XDG_DATA_HOME", "").strip()
    if xdg_home:
        candidates.append(Path(xdg_home) / "applications" / f"{LINUX_DESKTOP_FILE_BASENAME}.desktop")
    candidates.append(Path.home() / ".local/share/applications" / f"{LINUX_DESKTOP_FILE_BASENAME}.desktop")

    for data_dir in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":"):
        data_dir = data_dir.strip()
        if data_dir:
            candidates.append(Path(data_dir) / "applications" / f"{LINUX_DESKTOP_FILE_BASENAME}.desktop")

    for path in candidates:
        try:
            if path.is_file():
                return LINUX_DESKTOP_FILE_BASENAME
        except Exception:
            continue

    return None


def get_banner_pixmap(width: int = 680, height: int = 120) -> QPixmap:
    for filename in ("banner.png", "banner.jpg", "banner.jpeg", "header.png"):
        path = resource_path(filename)
        if os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                return pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#00000000"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, QColor("#16324f"))
    gradient.setColorAt(1.0, QColor("#2f6da3"))
    painter.setBrush(gradient)
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, width, height, 18, 18)

    painter.setPen(QPen(QColor("#ffffff")))
    title_font = QFont("Sans Serif" if sys.platform.startswith("linux") else "Segoe UI", max(14, height // 5), QFont.Bold)
    painter.setFont(title_font)
    painter.drawText(28, 24, width - 56, height - 48, int(Qt.AlignLeft | Qt.AlignVCenter), APP_DISPLAY_NAME)

    subtitle_font = QFont("Sans Serif" if sys.platform.startswith("linux") else "Segoe UI", max(9, height // 10))
    painter.setFont(subtitle_font)
    painter.drawText(30, height - 36, width - 60, 24, int(Qt.AlignLeft | Qt.AlignVCenter), "GitHub • Porta Fontium • GUI Downloader")

    painter.end()
    return pixmap

from __future__ import annotations

import sys

from PySide6.QtGui import QFont

APP_DISPLAY_NAME = "Porta fontium Downloader"
APP_TITLE = f" {APP_DISPLAY_NAME}"
APP_HOME_LABEL = "Porta fontium"
SETTINGS_ORG = "PFDownloader"
SETTINGS_APP = "PortaFontiumDownloader"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36",
    "Referer": "https://www.portafontium.eu/",
}
if sys.platform.startswith("linux"):
    APP_FONT = QFont()
    APP_FONT.setPointSize(10)
else:
    APP_FONT = QFont("Segoe UI", 10)

LINUX_DESKTOP_FILE_BASENAME = "porta-fontium-downloader"

APP_VERSION = "1.7"
APP_AUTHOR = "Sebastian (Testatost)"
APP_GITHUB_URL = "https://github.com/Testatost/Porta-Fontium-Downloader"
APP_ID = "Sebastian.Testatost.PFDownloader.1.7"

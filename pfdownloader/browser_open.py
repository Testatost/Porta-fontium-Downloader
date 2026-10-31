"""Open external web links from source and PyInstaller desktop builds.

On Linux a frozen Qt application may change library and Qt plugin paths.
Those paths must not leak into a separately launched system browser.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def _external_environment() -> dict[str, str]:
    """Make the child process use the host's libraries rather than bundled Qt."""
    env = os.environ.copy()
    if getattr(sys, "frozen", False):
        # PyInstaller preserves the original value, if there was one.
        original = env.pop("LD_LIBRARY_PATH_ORIG", None)
        if original is None:
            env.pop("LD_LIBRARY_PATH", None)
        else:
            env["LD_LIBRARY_PATH"] = original
        env.pop("LD_PRELOAD", None)

    # Qt's plugin directory in a frozen application is often incompatible
    # with xdg-open's helpers, e.g. KDE's kioexec / an installed browser.
    for name in (
        "QT_QPA_PLATFORM_PLUGIN_PATH", "QT_QPA_FONTDIR", "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM", "QTWEBENGINEPROCESS_PATH", "QTWEBENGINE_RESOURCES_PATH",
    ):
        env.pop(name, None)
    return env


def _open_linux(url: str) -> bool:
    env = _external_environment()
    for command in (("xdg-open", url), ("gio", "open", url)):
        if shutil.which(command[0], path=env.get("PATH")) is None:
            continue
        try:
            # Do not block the GUI thread while the browser is running.
            process = subprocess.Popen(
                command,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            # A process that has started may hand the URL to the desktop
            # portal and exit immediately with status 0.
            if process.poll() in (None, 0):
                return True
        except OSError:
            continue
    return False


def open_external_url(url: str) -> bool:
    """Request the system's default browser for an HTTP(S) URL."""
    parsed = QUrl(url)
    if not url or not parsed.isValid() or parsed.scheme().lower() not in ("http", "https"):
        return False

    if sys.platform.startswith("linux"):
        if _open_linux(url):
            return True
    elif sys.platform == "win32":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        except (OSError, AttributeError):
            pass

    try:
        if QDesktopServices.openUrl(parsed):
            return True
    except Exception:
        pass

    try:
        return bool(webbrowser.open(url, new=2))
    except Exception:
        return False

# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

PROJECT_ROOT = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
APP_NAME = "Porta fontium Downloader"

hiddenimports = collect_submodules("pfdownloader")

datas = []
for filename in (
    "icon.png",
    "icon.ico",
    "logo.png",
    "banner.png",
    "banner.jpg",
    "banner.jpeg",
    "header.png",
):
    path = PROJECT_ROOT / filename
    if path.exists():
        datas.append((str(path), "."))

icon_file = None
for candidate in ("icon.ico", "icon.png", "logo.png"):
    candidate_path = PROJECT_ROOT / candidate
    if candidate_path.exists():
        icon_file = str(candidate_path)
        break

a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

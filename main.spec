# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo,
    FixedFileInfo,
    StringFileInfo,
    StringTable,
    StringStruct,
    VarFileInfo,
    VarStruct,
)

block_cipher = None

PROJECT_ROOT = Path.cwd()
APP_NAME = "Porta fontium Downloader"

hiddenimports = collect_submodules("pfdownloader")

datas = []
for filename in (
    "icon.ico",
    "icon.png",
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

version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(1, 6, 0, 0),
        prodvers=(1, 6, 0, 0),
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040704B0",
                    [
                        StringStruct("CompanyName", "Sebastian (Testatost)"),
                        StringStruct("FileDescription", "Porta fontium Downloader"),
                        StringStruct("FileVersion", "1.6.0.0"),
                        StringStruct("InternalName", "Porta fontium Downloader"),
                        StringStruct("OriginalFilename", "Porta fontium Downloader.exe"),
                        StringStruct("ProductName", "Porta fontium Downloader"),
                        StringStruct("ProductVersion", "1.6.0.0"),
                        StringStruct("Comments", "Written by Sebastian (Testatost)"),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [1031, 1200])]),
    ],
)

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
    version=version_info,
)
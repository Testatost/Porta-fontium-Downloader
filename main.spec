# -*- mode: python ; coding: utf-8 -*-

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

hiddenimports = collect_submodules("pfdownloader")

version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(1, 5, 0, 0),
        prodvers=(1, 5, 0, 0),
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
                        StringStruct("FileDescription", "Porta fontium Downloader - Sebastian (Testatost)"),
                        StringStruct("FileVersion", "1.5"),
                        StringStruct("InternalName", "Porta fontium Downloader"),
                        StringStruct("OriginalFilename", "Porta fontium Downloader.exe"),
                        StringStruct("ProductName", "Porta fontium Downloader"),
                        StringStruct("ProductVersion", "1.5"),
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
    pathex=["."],
    binaries=[],
    datas=[
        ("icon.ico", "."),
        ("icon.png", "."),
        ("logo.png", "."),
    ],
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
    name="Porta fontium Downloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico",
    version=version_info,
)

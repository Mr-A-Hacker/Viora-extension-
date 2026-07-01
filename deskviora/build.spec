# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller build.spec
# Output:      dist/DeskViora.exe   (single file, no console window)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pyautogui', 'pygetwindow', 'mss', 'PIL', 'pyperclip'],
    hookspath=[],
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
    name='deskviora-source',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no terminal window behind the GUI
    icon=None,              # point this at an .ico file if you want a custom icon
    onefile=True,
)

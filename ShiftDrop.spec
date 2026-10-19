# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

datas = [('assets/icon.ico', 'assets')]
binaries = []
hiddenimports = [
    'win32gui',
    'win32process',
    'win32com',
    'win32com.client',
    'pythoncom',
    'pynput',
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'reportlab',
    'reportlab.lib',
    'reportlab.platypus',
    'charset_normalizer',
    'docx',
    'pdf2docx',
    'pymupdf',
    'fitz',
    'PIL',
    'pypdf',
]

# Collect all dynamic libraries and data packages
for pkg in ['imageio_ffmpeg', 'pypdfium2', 'pdf2docx', 'pymupdf', 'reportlab']:
    try:
        d, b, h = collect_all(pkg)
        datas.extend(d)
        binaries.extend(b)
        hiddenimports.extend(h)
    except Exception as e:
        print(f"Warning collecting {pkg}: {e}")

# Explicitly ensure bundled FFmpeg is also available at root
try:
    import imageio_ffmpeg
    ffmpeg_src = imageio_ffmpeg.get_ffmpeg_exe()
    if ffmpeg_src and Path(ffmpeg_src).is_file():
        binaries.append((ffmpeg_src, '.'))
except Exception:
    pass

a = Analysis(
    ['shiftdrop/main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'unittest', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Single-file standalone executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ShiftDrop',
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
    icon='assets/icon.ico',
)

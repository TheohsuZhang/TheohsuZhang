# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# Pin project root so builds are reproducible regardless of where PyInstaller is invoked from.
# Use sys.argv[0] fallback for embedded Python where __file__ may not be defined
if 'embed' in sys.executable.lower() or '__file__' not in dir():
    _project_root = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    _project_root = os.path.dirname(os.path.abspath(__file__))

a = Analysis(
    ['command_Backup.py'],
    pathex=[_project_root],
    binaries=[],
    datas=[('config.ini', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='command_Backup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX can produce builds that behave differently across machines and can trigger AV false positives.
    # Prefer disabling by default; enable explicitly if you know you want it.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    # Keep explicit to avoid ambiguity; set to 'x86' or 'x64' intentionally if you ever need it.
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.ico'],
    version='file_version_info_calc.txt',
)

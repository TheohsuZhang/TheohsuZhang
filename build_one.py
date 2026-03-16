#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Single-arch build helper for command_Backup.

Goals:
- Optional version/date bump (do it once per release, not twice for x86/x64)
- Invoke PyInstaller using the current interpreter environment
- Validate produced EXE architecture (x86 vs x64) via PE header inspection
- Provide actionable, “anti-footgun” output
- Allow the orchestrator to specify the expected output executable name/path

Typical usage:
  python build_one.py --arch x64 --bump
  python build_one.py --arch x86 --no-bump
  python build_one.py --arch x64 --name command_Backup --dist-exe dist/command_Backup.exe

Notes:
- PyInstaller cannot cross-compile architectures. Your Python interpreter arch
  determines the output arch.
- For dual-arch support, run this script twice from 32-bit and 64-bit Python.
- This script does not attempt to rewrite the .spec file; --name affects validation
  defaults and artifact expectations (and should match the .spec name).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import struct
import subprocess
import sys
from datetime import datetime
from typing import List, Optional, Tuple


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(SCRIPT_DIR, "command_Backup.py")
SPEC_FILE_DEFAULT = os.path.join(SCRIPT_DIR, "command_Backup.spec")

DEFAULT_APP_NAME = "command_Backup"
DIST_EXE_DEFAULT = os.path.join(SCRIPT_DIR, "dist", f"{DEFAULT_APP_NAME}.exe")


def _python_arch_bits() -> int:
    return struct.calcsize("P") * 8


def _py_arch_label() -> str:
    return "x64" if _python_arch_bits() == 64 else "x86"


def _is_windows() -> bool:
    return os.name == "nt"


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_text(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _log_environment() -> None:
    print("[Environment]")
    print(f"  - OS: {os.name} / platform: {sys.platform}")
    print(f"  - Python exe: {sys.executable}")
    print(f"  - Python version: {sys.version.split()[0]}")
    print(f"  - Python arch: {_python_arch_bits()}-bit ({_py_arch_label()})")
    if _is_windows():
        arch = os.environ.get("PROCESSOR_ARCHITECTURE", "")
        wow64 = os.environ.get("PROCESSOR_ARCHITEW6432", "")
        detail = arch
        if wow64:
            detail = f"{arch} (WOW64 -> {wow64})"
        print(f"  - Windows env arch: {detail or 'unknown'}")
    print("")


def _require_pyinstaller_cmd() -> List[str]:
    """
    Determine how to invoke PyInstaller.
    Always use the PyInstaller installed in the current Python environment.
    """
    # Prefer using -m PyInstaller from current Python environment
    try:
        import PyInstaller  # noqa: F401
        return [sys.executable, "-m", "PyInstaller"]
    except Exception:
        pass

    # Fallback to PATH
    if shutil.which("pyinstaller"):
        return ["pyinstaller"]

    raise SystemExit(
        "ERROR: PyInstaller not found.\n"
        "Install it into the SAME Python environment you are using to run this script:\n"
        "  python -m pip install pyinstaller\n"
        "Then re-run."
    )


def get_current_version() -> Tuple[int, int, int]:
    """
    Read current version from MAIN_SCRIPT header:
      # Version:    v1.2.3
    """
    try:
        content = _read_text(MAIN_SCRIPT)
        match = re.search(r"#\s*Version:\s*v(\d+)\.(\d+)\.(\d+)", content)
        if match:
            major, minor, patch = map(int, match.groups())
            return major, minor, patch
    except Exception:
        pass
    return 1, 0, 0


def bump_version_and_date() -> Tuple[str, str]:
    """
    Increment patch version and update date in MAIN_SCRIPT header:
      # Version:    v1.2.3
      # Date:       2026-03-05
    """
    major, minor, patch = get_current_version()
    new_patch = patch + 1
    new_version = f"v{major}.{minor}.{new_patch}"
    new_date = datetime.now().strftime("%Y-%m-%d")

    print("[Bump]")
    print(f"  - Version: v{major}.{minor}.{patch} -> {new_version}")
    print(f"  - Date: -> {new_date}")

    content = _read_text(MAIN_SCRIPT)

    content2 = re.sub(
        r"#\s*Version:\s*v\d+\.\d+\.\d+",
        f"# Version:    {new_version}",
        content,
    )
    content2 = re.sub(
        r"#\s*Date:\s*\d{4}-\d{2}-\d{2}",
        f"# Date:       {new_date}",
        content2,
    )

    if content2 == content:
        print("  - Warning: Version/Date patterns not found; no changes applied.")
    else:
        _write_text(MAIN_SCRIPT, content2)
        print("  - Updated successfully.")
    
    # Also update file_version_info.txt if it exists
    update_file_version_info(major, minor, new_patch)
    
    print("")
    return new_version, new_date


def update_file_version_info(major, minor, patch):
    """Update version tuple in file_version_info_calc.txt (using robust regex)"""
    info_file = os.path.join(SCRIPT_DIR, "file_version_info_calc.txt")
    if not os.path.exists(info_file):
        print("  - Warning: file_version_info_calc.txt not found, skipping version injection.")
        return

    try:
        with open(info_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 1. Update numeric versions
        ver_tuple = f"({major}, {minor}, {patch}, 0)"
        content = re.sub(r'filevers=\(\d+, \d+, \d+, \d+\)', f'filevers={ver_tuple}', content)
        content = re.sub(r'prodvers=\(\d+, \d+, \d+, \d+\)', f'prodvers={ver_tuple}', content)
        
        # 2. Update string fields
        # Define the fields we want to enforce
        replacements = {
            'CompanyName': 'Command Backup Project',
            'FileDescription': 'Command Backup Utility',
            'FileVersion': f"{major}.{minor}.{patch}.0",
            'InternalName': 'command_Backup',
            'LegalCopyright': 'Copyright (c) ZhangXiaoxu',
            'OriginalFilename': 'command_Backup.exe',
            'ProductName': 'command_backup',
            'ProductVersion': f"{major}.{minor}.{patch}.0"
        }

        for key, value in replacements.items():
            # Flexible regex to match u'Key' or 'Key', and u'Value' or 'Value'
            # We enforce single quotes for the replacement to match file style
            pattern = r"StringStruct\([uU]?['\"]{}['\"],\s*[uU]?['\"][^'\"]+['\"]\)" .format(key)
            replacement = "StringStruct('{}', '{}')".format(key, value)
            
            content, count = re.subn(pattern, replacement, content)
            if count > 0:
                print(f"  - Updated {key} -> {value}")
            else:
                print(f"  - Warning: Could not find key {key} in version info file")
        
        with open(info_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"  - Updated file_version_info_calc.txt to version {major}.{minor}.{patch}.0")
    except Exception as e:
        print(f"  - Warning: Failed to update version info: {e}")



def _read_pe_machine_type(exe_path: str) -> str:
    """
    Return 'x86', 'x64', or 'unknown' by reading PE headers (Windows exe).
    """
    try:
        with open(exe_path, "rb") as f:
            mz = f.read(64)
            if len(mz) < 64 or mz[:2] != b"MZ":
                return "unknown"

            # e_lfanew at offset 0x3C
            e_lfanew = int.from_bytes(mz[0x3C:0x40], "little", signed=False)
            f.seek(e_lfanew, os.SEEK_SET)

            pe_sig = f.read(4)
            if pe_sig != b"PE\0\0":
                return "unknown"

            machine = int.from_bytes(f.read(2), "little", signed=False)

        if machine == 0x014C:
            return "x86"
        if machine == 0x8664:
            return "x64"
        return "unknown"
    except Exception:
        return "unknown"


def _validate_exe_arch(exe_path: str, expected_arch: str) -> None:
    if not os.path.exists(exe_path):
        raise SystemExit(
            "ERROR: Build reported success but output EXE not found:\n"
            f"  {exe_path}\n"
            "Check PyInstaller spec name ('command_Backup') and dist settings."
        )

    exe_arch = _read_pe_machine_type(exe_path)
    py_arch = _py_arch_label()

    print("[Output]")
    print(f"  - EXE: {exe_path}")
    print(f"  - Detected EXE arch: {exe_arch}")
    print(f"  - Builder Python arch: {py_arch}")
    print(f"  - Expected arch (arg): {expected_arch}")
    print("")

    if expected_arch not in ("x86", "x64"):
        raise SystemExit(f"ERROR: Invalid expected arch: {expected_arch}")

    # Primary guardrail: if you asked for x86 but you're running x64 Python, fail early.
    if py_arch != expected_arch:
        raise SystemExit(
            "ERROR: Architecture mismatch.\n"
            f"  - You requested: {expected_arch}\n"
            f"  - But this script is running under: {py_arch} Python\n\n"
            "PyInstaller output architecture is determined by the Python interpreter.\n"
            "Fix: run this script using the correct Python (32-bit for x86, 64-bit for x64)."
        )

    # Secondary check: the produced exe should match Python arch.
    if exe_arch in ("x86", "x64") and exe_arch != expected_arch:
        raise SystemExit(
            "ERROR: Produced EXE architecture does not match expectation.\n"
            f"  - EXE arch: {exe_arch}\n"
            f"  - Expected: {expected_arch}\n"
            "This indicates a mixed build environment or unexpected tooling behavior."
        )

    if expected_arch == "x64":
        print(
            "NOTE: This EXE is x64. It will NOT run on 32-bit Windows.\n"
        )


def build(spec_file: str, clean: bool, noconfirm: bool) -> None:
    pyinstaller_cmd = _require_pyinstaller_cmd()

    cmd = pyinstaller_cmd[:]
    if clean:
        cmd.append("--clean")
    if noconfirm:
        cmd.append("--noconfirm")
    cmd.append(spec_file)

    print("[Build]")
    print("  - PyInstaller command:")
    print(f"    {' '.join(cmd)}")
    print("")

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if result.returncode != 0:
        raise SystemExit("ERROR: PyInstaller build failed. See output above.")


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Single-arch build helper for command_Backup")

    p.add_argument(
        "--arch",
        required=True,
        choices=["x86", "x64"],
        help="Expected output architecture. Must match the Python interpreter architecture.",
    )
    p.add_argument(
        "--spec",
        default=SPEC_FILE_DEFAULT,
        help="Path to the PyInstaller .spec file (default: command_Backup.spec)",
    )

    # Optional name used to derive the default dist exe path.
    # This does NOT rewrite the .spec; it only changes what we expect/validate.
    p.add_argument(
        "--name",
        default=DEFAULT_APP_NAME,
        help="Executable base name (without .exe). Used to derive default --dist-exe.",
    )

    # If not specified, we will derive it from --name after parsing and absolutize it.
    p.add_argument(
        "--dist-exe",
        default=None,
        help="Expected output exe path for validation (default: dist/<name>.exe).",
    )

    p.add_argument(
        "--bump",
        dest="bump",
        action="store_true",
        help="Bump patch version and update date in command_Backup.py before building.",
    )
    p.add_argument(
        "--no-bump",
        dest="bump",
        action="store_false",
        help="Do not modify version/date.",
    )
    p.set_defaults(bump=False)

    p.add_argument(
        "--clean",
        action="store_true",
        default=True,
        help="Pass --clean to PyInstaller (default: on).",
    )
    p.add_argument(
        "--no-clean",
        dest="clean",
        action="store_false",
        help="Do not pass --clean to PyInstaller.",
    )
    p.add_argument(
        "--noconfirm",
        action="store_true",
        default=True,
        help="Pass --noconfirm to PyInstaller (default: on).",
    )
    p.add_argument(
        "--confirm",
        dest="noconfirm",
        action="store_false",
        help="Allow PyInstaller to ask for confirmation.",
    )

    args = p.parse_args(argv)

    # Normalize name
    args.name = (args.name or DEFAULT_APP_NAME).strip()
    if args.name.lower().endswith(".exe"):
        args.name = args.name[:-4]

    # Derive/normalize dist exe
    if not args.dist_exe:
        args.dist_exe = os.path.join(SCRIPT_DIR, "dist", f"{args.name}.exe")
    elif not os.path.isabs(args.dist_exe):
        args.dist_exe = os.path.join(SCRIPT_DIR, args.dist_exe)

    return args


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)

    print("=" * 60)
    print("  command_Backup - build_one")
    print("=" * 60)
    print("")
    _log_environment()

    print("[Settings]")
    print(f"  - arch: {args.arch}")
    print(f"  - name: {args.name}")
    print(f"  - spec: {args.spec}")
    print(f"  - dist-exe: {args.dist_exe}")
    print("")

    # Basic path validation
    spec_file = args.spec
    if not os.path.isabs(spec_file):
        spec_file = os.path.join(SCRIPT_DIR, spec_file)
    if not os.path.exists(spec_file):
        raise SystemExit(f"ERROR: Spec file not found:\n  {spec_file}")

    if args.bump:
        bump_version_and_date()

    # Fail fast before building if arch doesn't match
    if _py_arch_label() != args.arch:
        _validate_exe_arch(args.dist_exe, args.arch)  # will raise with clear message

    build(spec_file=spec_file, clean=args.clean, noconfirm=args.noconfirm)

    # Validate output exe architecture
    _validate_exe_arch(args.dist_exe, args.arch)

    print("=" * 60)
    print("  Build finished successfully")
    print("=" * 60)


if __name__ == "__main__":
    main()
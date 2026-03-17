#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Multi-arch build orchestrator for command_Backup

Goal:
- Build BOTH x86 and x64 executables (you cannot cross-compile with PyInstaller).
- Uses configured Python interpreters for each arch.
- Produces release artifacts:
    release/command_Backup-x86.exe
    release/command_Backup-x64.exe
    release/config.ini

How it works:
- Reads build_config.ini (preferred) or environment variables.
- Runs build_one.py twice (once per arch) with the chosen interpreters.
- build_one.py is expected to perform the actual PyInstaller build and validation.

Configuration (choose one):

A) build_config.ini (recommended, next to this file)
--------------------------------
[python]
python_x86 = C:\\Path\\To\\Python32\\python.exe
python_x64 = C:\\Path\\To\\Python64\\python.exe

[build]
spec_file = command_Backup.spec
onefile_name = command_Backup
release_dir = release

B) Environment variables
--------------------------------
COMMAND_BACKUP_PYTHON_X86
COMMAND_BACKUP_PYTHON_X64
(optional) COMMAND_BACKUP_SPEC_FILE
(optional) COMMAND_BACKUP_RELEASE_DIR
(optional) COMMAND_BACKUP_ONEFILE_NAME

Exit codes:
- 0 success
- non-zero if any build fails
"""

from __future__ import annotations

import configparser
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_FILE = PROJECT_DIR / "build_config.ini"
DEFAULT_SPEC_FILE = PROJECT_DIR / "command_Backup.spec"
DEFAULT_RELEASE_DIR = PROJECT_DIR / "release"
DEFAULT_ONEFILE_NAME = "command_Backup"


@dataclass(frozen=True)
class BuildConfig:
    python_x86: Path
    python_x64: Path
    spec_file: Path = DEFAULT_SPEC_FILE
    release_dir: Path = DEFAULT_RELEASE_DIR
    onefile_name: str = DEFAULT_ONEFILE_NAME


def _sync_version_info() -> None:
    main_py = PROJECT_DIR / "command_Backup.py"
    info_file = PROJECT_DIR / "file_version_info_calc.txt"
    if not main_py.exists() or not info_file.exists():
        return

    content = main_py.read_text(encoding="utf-8")
    version_match = re.search(r"# Version:\s*v([\d\.]+)", content)
    date_match = re.search(r"# Date:\s*([\d-]+)", content)

    if not version_match or not date_match:
        return

    version_str = version_match.group(1)
    date_str = date_match.group(1)

    parts = version_str.split('.')
    while len(parts) < 4:
        parts.append("0")
    ver_tuple = f"({parts[0]}, {parts[1]}, {parts[2]}, {parts[3]})"
    ver_str = f"{parts[0]}.{parts[1]}.{parts[2]}.{parts[3]}"

    info_content = info_file.read_text(encoding="utf-8")
    info_content = re.sub(r'filevers=\(\d+,\s*\d+,\s*\d+,\s*\d+\)', f'filevers={ver_tuple}', info_content)
    info_content = re.sub(r'prodvers=\(\d+,\s*\d+,\s*\d+,\s*\d+\)', f'prodvers={ver_tuple}', info_content)
    info_content = re.sub(r"StringStruct\([uU]?['\"]FileVersion['\"],\s*[uU]?['\"][^'\"]+['\"]\)", f"StringStruct('FileVersion', '{ver_str}')", info_content)
    info_content = re.sub(r"StringStruct\([uU]?['\"]ProductVersion['\"],\s*[uU]?['\"][^'\"]+['\"]\)", f"StringStruct('ProductVersion', '{ver_str}')", info_content)
    info_content = re.sub(r"StringStruct\([uU]?['\"]FileDescription['\"],\s*[uU]?['\"][^'\"]+['\"]\)", f"StringStruct('FileDescription', 'Command Backup Utility (Build Date: {date_str})')", info_content)

    info_file.write_text(info_content, encoding="utf-8")
    
    readme_path = PROJECT_DIR / "README.md"
    if readme_path.exists():
        readme_content = readme_path.read_text(encoding="utf-8")
        readme_content = re.sub(r"\*\*版本 \(Version\)\*\*: v\d+\.\d+\.\d+", f"**版本 (Version)**: v{version_str}", readme_content)
        readme_content = re.sub(r"\*\*更新日期 \(Date\)\*\*: \d{4}-\d{2}-\d{2}", f"**更新日期 (Date)**: {date_str}", readme_content)
        readme_path.write_text(readme_content, encoding="utf-8")

    print(f"Synced Version (v{version_str}) and Date ({date_str}) to info file and README.\n")


def _print_header() -> None:
    print("=" * 60)
    print(" command_Backup Multi-Arch Build Orchestrator (x86 + x64)")
    print("=" * 60)
    print(f"Project dir : {PROJECT_DIR}")
    print(f"Runner      : {sys.executable}")
    print("")


def _read_ini(path: Path) -> configparser.ConfigParser:
    cp = configparser.ConfigParser()
    cp.read(path, encoding="utf-8-sig")
    return cp


def _env(name: str) -> Optional[str]:
    v = os.environ.get(name)
    return v.strip() if v and v.strip() else None


def _resolve_path_must_exist(p: Path, label: str) -> Path:
    if not p.exists():
        raise SystemExit(f"ERROR: {label} does not exist:\n  {p}")
    return p


def _load_config() -> BuildConfig:
    # 1) Try INI
    if DEFAULT_CONFIG_FILE.exists():
        cp = _read_ini(DEFAULT_CONFIG_FILE)

        py_x86 = cp.get("python", "python_x86", fallback="").strip()
        py_x64 = cp.get("python", "python_x64", fallback="").strip()
        if not py_x86 or not py_x64:
            raise SystemExit(
                "ERROR: build_config.ini found but missing python paths.\n"
                "Expected:\n"
                "  [python]\n"
                "  python_x86 = C:\\\\Path\\\\To\\\\Python32\\\\python.exe\n"
                "  python_x64 = C:\\\\Path\\\\To\\\\Python64\\\\python.exe\n"
            )

        spec_file = cp.get("build", "spec_file", fallback=str(DEFAULT_SPEC_FILE)).strip()
        release_dir = cp.get("build", "release_dir", fallback=str(DEFAULT_RELEASE_DIR)).strip()
        # Backward/forward compatible naming:
        # - Prefer app_name (matches build_config.ini)
        # - Fall back to onefile_name (older key used by build_all.py earlier)
        onefile_name = (
            cp.get("build", "app_name", fallback="").strip()
            or cp.get("build", "onefile_name", fallback=DEFAULT_ONEFILE_NAME).strip()
            or DEFAULT_ONEFILE_NAME
        )

        cfg = BuildConfig(
            python_x86=Path(py_x86),
            python_x64=Path(py_x64),
            spec_file=Path(spec_file) if Path(spec_file).is_absolute() else (PROJECT_DIR / spec_file),
            release_dir=Path(release_dir) if Path(release_dir).is_absolute() else (PROJECT_DIR / release_dir),
            onefile_name=onefile_name,
        )
    else:
        # 2) Env vars
        py_x86 = _env("COMMAND_BACKUP_PYTHON_X86")
        py_x64 = _env("COMMAND_BACKUP_PYTHON_X64")
        if not py_x86 or not py_x64:
            raise SystemExit(
                "ERROR: Missing Python interpreter paths for x86/x64 builds.\n"
                "Provide either:\n"
                "  - build_config.ini next to build_all.py (recommended), OR\n"
                "  - environment variables:\n"
                "      COMMAND_BACKUP_PYTHON_X86\n"
                "      COMMAND_BACKUP_PYTHON_X64\n"
            )

        spec_file = _env("COMMAND_BACKUP_SPEC_FILE") or str(DEFAULT_SPEC_FILE)
        release_dir = _env("COMMAND_BACKUP_RELEASE_DIR") or str(DEFAULT_RELEASE_DIR)
        # Environment-variable override for exe base name
        onefile_name = _env("COMMAND_BACKUP_ONEFILE_NAME") or DEFAULT_ONEFILE_NAME

        cfg = BuildConfig(
            python_x86=Path(py_x86),
            python_x64=Path(py_x64),
            spec_file=Path(spec_file) if Path(spec_file).is_absolute() else (PROJECT_DIR / spec_file),
            release_dir=Path(release_dir) if Path(release_dir).is_absolute() else (PROJECT_DIR / release_dir),
            onefile_name=onefile_name,
        )

    # Validate required paths
    _resolve_path_must_exist(cfg.python_x86, "python_x86")
    _resolve_path_must_exist(cfg.python_x64, "python_x64")
    _resolve_path_must_exist(cfg.spec_file, "spec_file")

    return cfg


def _run(cmd: Sequence[str], cwd: Path) -> None:
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(list(cmd), cwd=str(cwd))
    if result.returncode != 0:
        raise SystemExit(f"ERROR: Command failed ({result.returncode}).")


def _clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)


def _copy_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _collect_artifacts(cfg: BuildConfig, arch: str) -> Path:
    """
    Collect dist artifact produced by PyInstaller default layout:
      dist/<onefile_name>.exe

    We rely on build_one.py to have built in PROJECT_DIR so dist/ is under it.
    """
    dist_exe = PROJECT_DIR / "dist" / f"{cfg.onefile_name}.exe"
    if not dist_exe.exists():
        raise SystemExit(
            f"ERROR: Expected EXE not found after {arch} build:\n"
            f"  {dist_exe}\n"
            f"Check build_one.py output above."
        )

    out = cfg.release_dir / f"{cfg.onefile_name}-{arch}.exe"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dist_exe, out)
    print(f"Collected: {out}")
    return out


def _write_default_build_config_template(path: Path) -> None:
    if path.exists():
        return
    template = (
        "[python]\n"
        "# IMPORTANT: You must provide both interpreters.\n"
        "# x86 build requires 32-bit Python; x64 build requires 64-bit Python.\n"
        "python_x86 = C:\\\\Path\\\\To\\\\Python32\\\\python.exe\n"
        "python_x64 = C:\\\\Path\\\\To\\\\Python64\\\\python.exe\n"
        "\n"
        "[build]\n"
        "spec_file = command_Backup.spec\n"
        "onefile_name = command_Backup\n"
        "release_dir = release\n"
    )
    path.write_text(template, encoding="utf-8")


def main(argv: list[str]) -> int:
    _print_header()

    _sync_version_info()

    # Help the user by creating a template config if missing
    _write_default_build_config_template(DEFAULT_CONFIG_FILE)

    cfg = _load_config()

    print("[Config]")
    print(f"  python_x86 : {cfg.python_x86}")
    print(f"  python_x64 : {cfg.python_x64}")
    print(f"  spec_file  : {cfg.spec_file}")
    print(f"  onefile    : {cfg.onefile_name}")
    print(f"  release_dir: {cfg.release_dir}")
    print("")

    # Ensure a clean release dir; keep dist/ intact per-build (build_one can --clean).
    _clean_dir(cfg.release_dir)

    build_one = PROJECT_DIR / "build_one.py"
    if not build_one.exists():
        raise SystemExit(
            "ERROR: build_one.py not found next to build_all.py.\n"
            "This orchestrator expects build_one.py to exist and handle one-arch builds.\n"
        )

    # Build x86 (no bump) then x64 (no bump) to avoid double bump.
    # You can bump once by running build_one.py directly with --bump, or we can extend this later.
    print("[1/2] Building x86 ...")
    _run(
        [
            str(cfg.python_x86),
            str(build_one),
            "--arch",
            "x86",
            "--spec",
            str(cfg.spec_file),
            "--name",
            cfg.onefile_name,
            "--no-bump",
        ],
        cwd=PROJECT_DIR,
    )
    x86_exe = _collect_artifacts(cfg, "x86")
    print("")

    print("[2/2] Building x64 ...")
    _run(
        [
            str(cfg.python_x64),
            str(build_one),
            "--arch",
            "x64",
            "--spec",
            str(cfg.spec_file),
            "--name",
            cfg.onefile_name,
            "--no-bump",
        ],
        cwd=PROJECT_DIR,
    )
    x64_exe = _collect_artifacts(cfg, "x64")
    print("")

    # Copy config.ini into release (nice for distribution)
    _copy_if_exists(PROJECT_DIR / "config.ini", cfg.release_dir / "config.ini")

    print("=" * 60)
    print("Build complete. Release artifacts:")
    print(f"  - {x86_exe}")
    print(f"  - {x64_exe}")
    cfg_ini = cfg.release_dir / "config.ini"
    if cfg_ini.exists():
        print(f"  - {cfg_ini}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
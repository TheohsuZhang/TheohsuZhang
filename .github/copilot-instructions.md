# Copilot Instructions for command_Backup

This repository contains a Python utility for backing up data files (specifically ASAM MDF4 `.mf4`) from automotive test benches (Vector CANoe, INCA, etc.).

## Build Commands

The project uses PyInstaller to create standalone Windows executables.

- **Build for current architecture**:
  ```powershell
  python build.py
  ```
  *Auto-increments patch version and updates date in `command_Backup.py`.*

- **Build for release (x86 & x64)**:
  ```powershell
  python build_all.py
  ```
  *Requires `build_config.ini` to be configured with paths to both 32-bit and 64-bit Python interpreters.*

- **Build single architecture manually**:
  ```powershell
  python build_one.py --arch x86 --no-bump
  ```

## High-Level Architecture

1.  **Core Script (`command_Backup.py`)**:
    - **Singleton Design**: On startup, it identifies and terminates any other running instances of itself (by name/PID) to prevent conflicts during automated test sequences.
    - **Monitor Mode**: Can run as a daemon (`_run_monitor_mode`) watching a directory for new files, or as a one-shot task (`_run_once_mode`).
    - **Configuration**: Runtime behavior is controlled by `config.ini` (source/backup paths, file extensions, timeouts).

2.  **Legacy Support (Critical)**:
    - Many target machines run **Windows 7 32-bit**.
    - The build system is designed to produce valid x86 executables using Python 3.8 (last version supporting Win7).
    - **Do not upgrade dependencies** to versions incompatible with Windows 7 without verifying.

3.  **Build System**:
    - `build_all.py`: Orchestrator that calls `build_one.py` using specific Python interpreters defined in `build_config.ini`.
    - `build_one.py`: Wrapper around PyInstaller that validates the output PE header machine type (x86 vs x64) to prevent shipping the wrong architecture.

## Key Conventions

- **Version Management**:
    - The `command_Backup.py` header contains the source of truth for `Version` and `Date`.
    - **Do not manually edit version numbers**; use `build.py` or `build_one.py --bump` to handle this.

- **File Handling**:
    - **Temp Files**: The script explicitly ignores files ending in `.tmp` or containing `.tmp.` to avoid moving open/incomplete recordings.
    - **Renaming**: Files are renamed with a timestamp prefix (`YYYYMMDD-HHMMSS_`) during backup to ensure uniqueness.

- **Console Output**:
    - The script forces console encoding to UTF-8 (`cp65001`) to ensure log readability on various Windows localizations. Maintain this boilerplate in `command_Backup.py`.

- **Paths**:
    - Windows backslashes (`\`) are expected in `config.ini` and internal path handling.

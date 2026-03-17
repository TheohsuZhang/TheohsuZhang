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
  *Requires `build_config.ini` with paths to both 32-bit and 64-bit Python interpreters.*

- **Build single architecture manually**:
  ```powershell
  python build_one.py --arch x86 --no-bump
  ```

## High-Level Architecture

1.  **Core Script (`command_Backup.py`)**:
    - **Singleton Design**: Uses Windows `tasklist` and `taskkill` to identify and terminate other running instances of itself (by name/PID) on startup.
    - **Monitor Mode**: Controlled by `monitor_timeout_seconds` in `config.ini`. If > 0, runs as a daemon watching for files; otherwise performs a single scan.
    - **Command Line Arguments**: Accepts an optional first argument (`sys.argv[1]`) as the filename prefix (e.g., Test Case ID). If omitted, defaults to current timestamp.

2.  **Legacy Support (Critical)**:
    - Target machines often run **Windows 7 32-bit**.
    - **Must use Python 3.8** (or compatible) for x86 builds to ensure `api-ms-win-core-path-l1-1-0.dll` compatibility.
    - `build_one.py` validates the output PE header machine type (x86 vs x64).

3.  **Build System**:
    - `build_all.py`: Orchestrator that calls `build_one.py` using specific Python interpreters defined in `build_config.ini`.

## Key Conventions

- **Version Management**:
    - The build orchestrator (`build_all.py`) automatically reads the Version and Date from the header of `command_Backup.py`.
    - It seamlessly syncs this information into `README.md` and `file_version_info_calc.txt` so the compiled executable properties stay up-to-date without any manual prompts.

- **File Handling**:
    - **Strict Exclusions**: 
        - 0-byte (empty) files are rejected.
        - Filenames with multiple dots (`.`) are rejected.
        - Files containing `tmp` or `temp` (case-insensitive) anywhere in the name are rejected.
        - Filenames must strictly contain only alphanumeric characters, dashes, underscores, spaces, and parentheses.
    - **Renaming**: Format: `{timestamp}_{prefix}_{original_name}_{index}{ext}`.

- **Console Output**:
    - Forces `cp65001` (UTF-8) via `ctypes` on startup. **Preserve this boilerplate** to ensure log readability on localized Windows systems.

- **Paths**:
    - Use Windows backslashes (`\`) for all paths in code and `config.ini`.

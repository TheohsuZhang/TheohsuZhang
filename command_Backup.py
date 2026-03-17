# =============================================================================
# Program:    command_Backup.py
# Version:    v1.0.1
# Date:       2026-03-17
# Description: Backup files with specified extensions from source to backup directory
# =============================================================================

import os
import sys
import shutil
import ctypes
import configparser
import time
import subprocess
import re
from datetime import datetime

# Constants
CREATE_NO_WINDOW = 0x08000000  # subprocess.CREATE_NO_WINDOW for hiding console windows

# Windows console encoding configuration (supports multi-language systems)
if sys.platform == 'win32':
    try:
        import io
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        try:
            import io
            import locale
            enc = locale.getpreferredencoding()
            if enc:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=enc, errors='replace')
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding=enc, errors='replace')
        except Exception:
            pass

# Default configuration
DEFAULT_CONFIG = {
    'source_dir': r"Q:\TEMP",
    'backup_dir': r"Q:\TEMP\backup",
    'file_extensions': ['.mf4'],
    'time_range_minutes': 0,
    'scan_delay_seconds': 0,
    'monitor_timeout_seconds': 0,
    'monitor_interval_seconds': 0.5
}

def get_app_dir():
    """Get application directory"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_other_instance_pids():
    """Get PIDs of other running instances"""
    try:
        if getattr(sys, 'frozen', False):
            current_exe = os.path.basename(sys.executable)
        else:
            current_exe = os.path.basename(sys.argv[0]) if sys.argv else 'python.exe'
        current_pid = os.getpid()

        result = subprocess.run(
            ['tasklist', '/FI', f'IMAGENAME eq {current_exe}', '/FO', 'CSV', '/NH'],
            capture_output=True, text=True, creationflags=CREATE_NO_WINDOW
        )

        other_pids = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split(',')
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1].strip('"'))
                        if pid != current_pid:
                            other_pids.append(pid)
                    except ValueError:
                        continue
        return other_pids
    except Exception as e:
        print(f"Failed to get process list: {e}")
        return []

def terminate_other_instances():
    """Terminate other running instances"""
    other_pids = get_other_instance_pids()
    closed_count = 0
    for pid in other_pids:
        try:
            print(f"Closing previous instance (PID: {pid})...")
            subprocess.run(
                ['taskkill', '/PID', str(pid), '/F'],
                capture_output=True, text=True, creationflags=CREATE_NO_WINDOW
            )
            closed_count += 1
        except Exception as e:
            print(f"Failed to close process {pid}: {e}")
    return closed_count

def get_config():
    """Read INI configuration file"""
    config = configparser.ConfigParser()
    config_file = os.path.join(get_app_dir(), "config.ini")

    if not os.path.exists(config_file):
        print(f"Note: config.ini not found, using default settings")
        return DEFAULT_CONFIG.copy()

    try:
        config.read(config_file, encoding='utf-8-sig')
    except Exception as e:
        print(f"Warning: Failed to read config - {e}, using default settings")
        return DEFAULT_CONFIG.copy()

    if 'paths' not in config.sections():
        print("Warning: [paths] section not found, using default settings")
        return DEFAULT_CONFIG.copy()

    extensions_str = config.get('paths', 'file_extensions', fallback='.mf4')
    file_extensions = [ext.strip().lower() for ext in extensions_str.split(',') if ext.strip()] or ['.mf4']

    return {
        'source_dir': config.get('paths', 'source_dir', fallback=DEFAULT_CONFIG['source_dir']),
        'backup_dir': config.get('paths', 'backup_dir', fallback=DEFAULT_CONFIG['backup_dir']),
        'file_extensions': file_extensions,
        'time_range_minutes': config.getfloat('paths', 'time_range_minutes', fallback=0),
        'scan_delay_seconds': config.getfloat('paths', 'scan_delay_seconds', fallback=0),
        'monitor_timeout_seconds': config.getfloat('paths', 'monitor_timeout_seconds', fallback=0),
        'monitor_interval_seconds': config.getfloat('paths', 'monitor_interval_seconds', fallback=0.5)
    }

def match_extension(filename, file_extensions):
    """Check if file extension matches (ultra-strict validation)"""
    filename_lower = filename.lower()
    
    # 1. Must exactly match one of the target extensions at the very end
    if not any(filename_lower.endswith(ext) for ext in file_extensions):
        return False

    # 2. Exclude any temporary markers
    if 'tmp' in filename_lower or 'temp' in filename_lower:
        return False
        
    # 3. Only ONE dot allowed in the entire filename (the extension dot)
    if filename_lower.count('.') != 1:
        return False
        
    # 4. Exclude multiple occurrences of the extension string
    for ext in file_extensions:
        if filename_lower.count(ext) > 1:
            return False

    # 5. Regex validation: strict filename characters (alphanumeric, -, _, spaces, parentheses)
    # This prevents invisible characters or extremely malformed paths from passing
    if not re.match(r'^[\w\-\s\(\)]+\.[a-z0-9]+$', filename_lower):
        return False
        
    return True

def is_within_time_range(filepath, time_range_minutes):
    """Check if file is within specified time range"""
    if time_range_minutes <= 0:
        return True
    try:
        mtime = os.path.getmtime(filepath)
        cutoff_time = datetime.now().timestamp() - (time_range_minutes * 60)
        return mtime >= cutoff_time
    except Exception:
        return False

def check_backup_dir_writable(backup_dir):
    """Check if backup directory is writable"""
    try:
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        test_file = os.path.join(backup_dir, ".write_test")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        return True
    except Exception as e:
        print(f"Error: Backup directory not writable - {backup_dir}, {e}")
        return False

def _find_matched_files(source_dir, file_extensions, time_range_minutes):
    """Find matched files"""
    try:
        valid_files = []
        for f in os.listdir(source_dir):
            filepath = os.path.join(source_dir, f)
            
            # Check 1: Is it an actual file?
            if not os.path.isfile(filepath):
                continue
                
            # Check 2: File size must be strictly > 0 bytes (ignore empty/broken files)
            if os.path.getsize(filepath) == 0:
                continue
                
            # Check 3: Strict extension and name matching
            if not match_extension(f, file_extensions):
                continue
                
            # Check 4: Time range condition
            if not is_within_time_range(filepath, time_range_minutes):
                continue
                
            valid_files.append(f)
            
        return sorted(valid_files)
    except Exception as e:
        print(f"  Error scanning directory: {e}")
        return []

def _move_files(matched_files, source_dir, backup_dir, new_name_prefix, file_extensions):
    """Move files to backup directory"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    move_count = error_count = 0

    if not file_extensions:
        print("  Error: No file extensions specified")
        return 0, 1

    target_ext = file_extensions[0]

    for i, original_file in enumerate(matched_files):
        source_path = os.path.join(source_dir, original_file)
        name_without_ext = os.path.splitext(original_file)[0]
        new_filename = f"{timestamp}_{new_name_prefix}_{name_without_ext}_{i+1}{target_ext}"
        dest_path = os.path.join(backup_dir, new_filename)

        try:
            shutil.move(source_path, dest_path)
            print(f"  [{i+1}] {original_file} -> {new_filename}")
            move_count += 1
        except Exception as e:
            print(f"  Failed to move [{original_file}]: {e}")
            error_count += 1

    return move_count, error_count

def _run_monitor_mode(source_dir, backup_dir, file_extensions, time_range_minutes, new_name_prefix, timeout, interval):
    """Monitor mode - scan repeatedly until files found or timeout"""
    print(f"\nEntering monitor mode, timeout: {timeout} seconds")
    start_time = time.time()
    total_moved = 0
    last_countdown = -1

    while True:
        remaining = int(timeout - (time.time() - start_time))
        if remaining <= 0:
            print(f"\nMonitor timeout ({timeout} seconds), exiting")
            break

        if remaining != last_countdown:
            print(f"\r  Remaining: {remaining} seconds    ", end='', flush=True)
            last_countdown = remaining

        matched = _find_matched_files(source_dir, file_extensions, time_range_minutes)
        if matched:
            print(f"\r  Remaining: {remaining} seconds    ")
            print(f"\n[{time.time()-start_time:.1f}s] Found {len(matched)} file(s):")
            moved, failed = _move_files(matched, source_dir, backup_dir, new_name_prefix, file_extensions)
            total_moved += moved
            print(f"\nTask Complete! Total {total_moved} files moved" + (f", {failed} failed" if failed else " successfully") + ", exiting")
            break

        time.sleep(interval)

def _run_once_mode(source_dir, backup_dir, file_extensions, time_range_minutes, new_name_prefix):
    """Single scan mode"""
    print(f"\n[Starting Scan]")
    print(f"Scanning directory: {source_dir}")

    matched = _find_matched_files(source_dir, file_extensions, time_range_minutes)
    if not matched:
        print("\nNo matching files found")
        print(f"  - Extensions: {', '.join(file_extensions)}")
        if time_range_minutes > 0:
            print(f"  - Time Range: Last {time_range_minutes} minutes")
            print(f"  - Suggestion: Set time_range_minutes=0 or ensure files are within time range")
        else:
            print(f"  - Suggestion: Create .mf4 files (without '.tmp') in source directory")
        print("\nExiting")
        return

    print(f"\nFound {len(matched)} file(s):")
    moved, failed = _move_files(matched, source_dir, backup_dir, new_name_prefix, file_extensions)
    print(f"\nDone! Moved {moved} files" + (f", {failed} failed" if failed else f" to {backup_dir}"))

def main():
    # Close other instances
    closed = terminate_other_instances()
    print(f"Closed {closed} previous instance(s)" if closed > 0 else "No other running instances detected", flush=True)

    config = get_config()
    source_dir = config['source_dir']
    backup_dir = config['backup_dir']
    file_extensions = config['file_extensions']
    time_range_minutes = config['time_range_minutes']
    scan_delay = config['scan_delay_seconds']
    monitor_timeout = config['monitor_timeout_seconds']
    monitor_interval = config['monitor_interval_seconds']

    print(f"\n[Configuration]")
    print(f"Source Directory: {source_dir}")
    print(f"  - Exists: {os.path.exists(source_dir)}")
    print(f"Backup Directory: {backup_dir}")
    print(f"File Extensions: {', '.join(file_extensions)}")
    print(f"Time Range: {'No limit' if time_range_minutes <= 0 else f'Last {time_range_minutes} minutes'}")
    if scan_delay > 0:
        print(f"Start Delay: {scan_delay} seconds")
    if monitor_timeout > 0:
        print(f"Monitor Timeout: {monitor_timeout} seconds ({monitor_interval}s interval)")

    if not os.path.exists(source_dir):
        print(f"\nERROR: Source directory does not exist - {source_dir}")
        print("Please check source_dir in config.ini")
        sys.exit(1)

    if not check_backup_dir_writable(backup_dir):
        print("Please check backup_dir in config.ini")
        sys.exit(1)

    print(f"\n[Startup Check Passed]")

    new_name_prefix = sys.argv[1].strip() if len(sys.argv) >= 2 and sys.argv[1].strip() else datetime.now().strftime("%Y%m%d%H%M%S")
    print(f"\nFilename Prefix: {new_name_prefix}")

    if scan_delay > 0:
        print(f"\nWaiting {scan_delay} seconds before scanning...")
        time.sleep(scan_delay)

    if monitor_timeout > 0:
        _run_monitor_mode(source_dir, backup_dir, file_extensions, time_range_minutes, new_name_prefix, monitor_timeout, monitor_interval)
    else:
        _run_once_mode(source_dir, backup_dir, file_extensions, time_range_minutes, new_name_prefix)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Extract required game files from a FUComplete MHFU ISO.

Place your .iso file in the data/ folder, then run:
    python extract_iso.py

Extracts:
    PSP_GAME/USRDIR/DATA.BIN   -> data/DATA.BIN
    PSP_GAME/SYSDIR/EBOOT.BIN  -> data/EBOOT.BIN
    FUC/NATIVEPSP/FILE.BIN     -> data/FILE.BIN
"""

import glob
import os
import platform
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

FILES_TO_EXTRACT = [
    ("PSP_GAME/USRDIR/DATA.BIN", "DATA.BIN"),
    ("PSP_GAME/SYSDIR/EBOOT.BIN", "EBOOT.BIN"),
    ("FUC/NATIVEPSP/FILE.BIN", "FILE.BIN"),
]


def find_iso():
    """Find a .iso file in data/ (case-insensitive)."""
    for f in os.listdir(DATA_DIR):
        if f.lower().endswith(".iso"):
            return os.path.join(DATA_DIR, f)
    return None


def extract_macos(iso_path):
    """Extract using hdiutil (macOS)."""
    print("  Using hdiutil to mount ISO...")
    result = subprocess.run(
        ["hdiutil", "mount", "-nobrowse", "-readonly", iso_path],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  Error mounting ISO: {result.stderr.strip()}")
        return False

    # Parse mount point from output (last column of last line)
    mount_point = result.stdout.strip().split("\t")[-1].strip()
    print(f"  Mounted at: {mount_point}")

    try:
        for iso_path_rel, output_name in FILES_TO_EXTRACT:
            src = os.path.join(mount_point, iso_path_rel)
            dst = os.path.join(DATA_DIR, output_name)
            if os.path.exists(src):
                print(f"  Extracting {output_name}...")
                shutil.copy2(src, dst)
            else:
                print(f"  Warning: {iso_path_rel} not found in ISO")
    finally:
        print("  Unmounting ISO...")
        subprocess.run(["hdiutil", "detach", mount_point], capture_output=True)

    return True


def extract_7z(iso_path):
    """Extract using 7z (cross-platform)."""
    print("  Using 7z to extract from ISO...")
    for iso_path_rel, output_name in FILES_TO_EXTRACT:
        dst = os.path.join(DATA_DIR, output_name)
        result = subprocess.run(
            ["7z", "e", "-y", f"-o{DATA_DIR}", iso_path, iso_path_rel],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  Warning: could not extract {iso_path_rel}")
            continue
        # 7z extracts with the original filename; rename if needed
        extracted = os.path.join(DATA_DIR, os.path.basename(iso_path_rel))
        if extracted != dst and os.path.exists(extracted):
            shutil.move(extracted, dst)
        print(f"  Extracted {output_name}")
    return True


def main():
    print("=== MHFU ISO Extractor ===\n")

    iso_path = find_iso()
    if not iso_path:
        print(f"No .iso file found in {DATA_DIR}/")
        print("Place your FUComplete MHFU ISO in the data/ folder and try again.")
        sys.exit(1)

    print(f"Found ISO: {os.path.basename(iso_path)}")

    # Check which files already exist
    existing = [name for _, name in FILES_TO_EXTRACT if os.path.exists(os.path.join(DATA_DIR, name))]
    if existing:
        print(f"Already extracted: {', '.join(existing)}")
        answer = input("Re-extract and overwrite? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    success = False
    if platform.system() == "Darwin":
        success = extract_macos(iso_path)
    if not success:
        if shutil.which("7z"):
            success = extract_7z(iso_path)

    if not success:
        print("\nCould not extract ISO. Install 7-Zip (7z) and try again.")
        sys.exit(1)

    # Verify
    print()
    all_ok = True
    for _, name in FILES_TO_EXTRACT:
        path = os.path.join(DATA_DIR, name)
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f"  {name}: {size_mb:.1f} MB")
        else:
            print(f"  {name}: MISSING")
            all_ok = False

    if all_ok:
        print("\nDone! All files extracted successfully.")
    else:
        print("\nSome files are missing. The ISO may not be a FUComplete MHFU image.")


if __name__ == "__main__":
    main()

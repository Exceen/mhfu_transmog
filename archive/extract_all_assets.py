#!/usr/bin/env python3
"""Extract all player asset files from MHFU DATA.BIN.

Extracts faces, hair/head armor, body armor, arm armor, waist armor,
leg armor, and weapons for both male and female characters.
"""

import array
import os
import sys
import time

DATA_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DATA.BIN")

# Category definitions: (prefix, base_id, end_id_exclusive, subfolder)
# end_id is the start of the next category or a known boundary
CATEGORIES = [
    # Female assets
    ("f_reg",  62,   406,  "female/leg"),
    ("f_hair", 406,  746,  "female/head"),
    ("f_body", 746,  1086, "female/body"),
    ("f_arm",  1086, 1419, "female/arm"),
    ("f_wst",  1419, 1715, "female/waist"),
    # Male assets
    ("m_reg",  1715, 2059, "male/leg"),
    ("m_hair", 2059, 2400, "male/head"),
    ("m_body", 2400, 2742, "male/body"),
    ("m_arm",  2742, 3080, "male/arm"),
    ("m_wst",  3080, 3388, "male/waist"),
    # Weapons (shared)
    ("we",     3388, None,  "weapons"),
]


def read_toc(data_file):
    """Read the DATA.BIN table of contents."""
    with open(data_file, 'rb') as f:
        raw = f.read(4)
        toc_blocks = array.array('I', raw)[0]
        toc_size = toc_blocks * 2048

        file_size = f.seek(0, os.SEEK_END)

        f.seek(0)
        toc = array.array('I', f.read(toc_size))

        # Find file count
        target = file_size // 2048
        file_count = None
        for i in range(len(toc)):
            if toc[i] == target:
                file_count = i
                break

        if file_count is None:
            print("ERROR: Could not determine file count from TOC.")
            sys.exit(1)

        # Build extended TOC lookup (file_id -> actual_size)
        ext_sizes = {}
        for i in range(file_count + 1, len(toc) - 1, 2):
            ext_sizes[toc[i]] = toc[i + 1]

        return toc, file_count, ext_sizes, file_size


def extract_file_data(data_fh, toc, file_count, ext_sizes, index):
    """Extract a single file by index. Returns bytes or None if empty."""
    if index >= file_count:
        return None

    offset = toc[index] * 2048
    block_size = (toc[index + 1] - toc[index]) * 2048

    if block_size == 0:
        return None

    actual_size = ext_sizes.get(index, block_size)
    if actual_size == 0:
        return None

    data_fh.seek(offset)
    return data_fh.read(actual_size)


def main():
    output_base = os.path.expanduser("~/Downloads/mhfucomplete_assets")

    print(f"DATA.BIN:  {DATA_BIN}")
    print(f"Output:    {output_base}")
    print()

    # Read TOC once
    print("Reading DATA.BIN table of contents...")
    toc, file_count, ext_sizes, data_size = read_toc(DATA_BIN)
    print(f"  File count: {file_count}")
    print(f"  DATA.BIN size: {data_size:,} bytes ({data_size // (1024*1024)} MB)")
    print()

    # For weapons, determine end by scanning for zero-size files
    weapon_base = 3388
    weapon_end = weapon_base
    for i in range(weapon_base, file_count):
        block_size = (toc[i + 1] - toc[i]) * 2048
        if block_size > 0:
            weapon_end = i + 1
        else:
            # Allow small gaps (some weapon IDs might be unused)
            # Stop after 50 consecutive empty entries
            gap = 0
            for j in range(i, min(i + 50, file_count)):
                bs = (toc[j + 1] - toc[j]) * 2048
                if bs > 0:
                    break
                gap += 1
            if gap >= 50:
                break
            weapon_end = i + 1

    # Update weapons end
    for cat in CATEGORIES:
        if cat[0] == "we":
            idx = CATEGORIES.index(cat)
            CATEGORIES[idx] = ("we", 3388, weapon_end, "weapons")
            break

    total_extracted = 0
    total_skipped = 0
    total_bytes = 0
    start_time = time.time()

    with open(DATA_BIN, 'rb') as data_fh:
        for prefix, base_id, end_id, subfolder in CATEGORIES:
            out_dir = os.path.join(output_base, subfolder)
            os.makedirs(out_dir, exist_ok=True)

            cat_count = 0
            cat_skipped = 0
            cat_bytes = 0

            for file_id in range(base_id, end_id):
                num = file_id - base_id
                filename = f"{prefix}{num:03d}.pac"

                data = extract_file_data(data_fh, toc, file_count, ext_sizes, file_id)
                if data is None or len(data) == 0:
                    cat_skipped += 1
                    continue

                out_path = os.path.join(out_dir, filename)
                with open(out_path, 'wb') as f:
                    f.write(data)

                cat_count += 1
                cat_bytes += len(data)

            total_extracted += cat_count
            total_skipped += cat_skipped
            total_bytes += cat_bytes

            print(f"  {subfolder:20s}  {prefix:8s}  IDs {base_id:5d}-{end_id-1:5d}  "
                  f"extracted: {cat_count:4d}  skipped: {cat_skipped:3d}  "
                  f"size: {cat_bytes / (1024*1024):.1f} MB")

    elapsed = time.time() - start_time
    print()
    print(f"Done in {elapsed:.1f}s")
    print(f"  Total extracted: {total_extracted} files")
    print(f"  Total skipped (empty): {total_skipped} files")
    print(f"  Total size: {total_bytes / (1024*1024):.1f} MB")
    print(f"  Output: {output_base}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Extract all .pac files from DATA.BIN using the filelist.csv mapping."""

import array
import csv
import os
import sys

DATA_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DATA.BIN")
FILELIST = "/Users/Exceen/Downloads/FUComplete_v1.4.0/res/filelist.csv"
OUTPUT_DIR = os.path.expanduser("~/Downloads/mhfucomplete_assets")


def read_toc(data_file):
    with open(data_file, 'rb') as f:
        toc_blocks = array.array('I', f.read(4))[0]
        toc_size = toc_blocks * 2048
        file_size = f.seek(0, os.SEEK_END)
        f.seek(0)
        toc = array.array('I', f.read(toc_size))
        target = file_size // 2048
        file_count = None
        for i in range(len(toc)):
            if toc[i] == target:
                file_count = i
                break
        return toc, file_count, file_size


def main():
    print(f"Reading TOC from {DATA_BIN}...")
    toc, file_count, file_size = read_toc(DATA_BIN)
    print(f"File count: {file_count}")

    # Build extraction list from filelist.csv
    entries = []
    with open(FILELIST, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            fid = int(row[0])
            path = row[1]
            if path.endswith('.pac'):
                entries.append((fid, path))

    print(f"Found {len(entries)} .pac files to extract")

    # Open DATA.BIN once and extract all
    extracted = 0
    errors = 0
    with open(DATA_BIN, 'rb') as data:
        for fid, path in entries:
            if fid >= file_count:
                print(f"  SKIP: {path} (ID {fid} out of range)")
                errors += 1
                continue

            offset = toc[fid] * 2048
            # Get actual file size from extended TOC
            size = (toc[fid + 1] - toc[fid]) * 2048
            for i in range(file_count + 1, len(toc), 2):
                if i >= len(toc):
                    break
                if toc[i] == fid:
                    size = toc[i + 1]
                    break

            out_path = os.path.join(OUTPUT_DIR, path)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            data.seek(offset)
            file_data = data.read(size)

            with open(out_path, 'wb') as out:
                out.write(file_data)

            extracted += 1
            if extracted % 500 == 0:
                print(f"  Extracted {extracted}/{len(entries)}...")

    print(f"\nDone: {extracted} files extracted, {errors} errors")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()

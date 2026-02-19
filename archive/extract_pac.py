#!/usr/bin/env python3
"""Extract a specific file from MHFU DATA.BIN by its file index."""

import array
import os
import sys

DATA_BIN = os.path.join(os.path.dirname(__file__), "DATA.BIN")

def read_toc(data_file):
    with open(data_file, 'rb') as f:
        raw = f.read(4)
        toc_blocks = array.array('I', raw)[0]
        toc_size = toc_blocks * 2048
        print(f"TOC blocks: {toc_blocks}, TOC size: {toc_size} bytes")

        file_size = f.seek(0, os.SEEK_END)
        print(f"DATA.BIN size: {file_size} bytes ({file_size // (1024*1024)} MB)")

        f.seek(0)
        toc = array.array('I', f.read(toc_size))

        # Find file count: the entry whose value equals the total file size in blocks
        target = file_size // 2048
        file_count = None
        for i in range(len(toc)):
            if toc[i] == target:
                file_count = i
                break

        if file_count is None:
            print("WARNING: Could not determine file count from TOC.")
            print(f"  Looking for block value: {target}")
            print(f"  First 20 TOC entries: {list(toc[:20])}")
            return None, 0

        print(f"File count: {file_count}")
        return toc, file_count

def extract_file(data_file, index):
    toc, file_count = read_toc(data_file)
    if toc is None:
        return None
    if index >= file_count:
        print(f"ERROR: Index {index} out of range (max: {file_count - 1})")
        return None

    offset = toc[index] * 2048
    size = (toc[index + 1] - toc[index]) * 2048
    print(f"File {index}: offset=0x{offset:X} ({offset}), raw_size={size} bytes")

    # Check the extended TOC for actual file size
    actual_size = size
    for i in range(file_count + 1, len(toc), 2):
        if i >= len(toc):
            break
        if toc[i] == index:
            actual_size = toc[i + 1]
            print(f"  Actual file size from extended TOC: {actual_size} bytes")
            break

    with open(data_file, 'rb') as f:
        f.seek(offset)
        data = f.read(actual_size)

    return data

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <file_index> <output_file>")
        print(f"  Example: {sys.argv[0]} 621 blu_guild_guard.pac")
        sys.exit(1)

    index = int(sys.argv[1])
    output = sys.argv[2]

    print(f"Extracting file index {index} from {DATA_BIN}...")
    data = extract_file(DATA_BIN, index)

    if data is None:
        print("Extraction failed.")
        sys.exit(1)

    with open(output, 'wb') as f:
        f.write(data)

    print(f"Saved to {output} ({len(data)} bytes)")

if __name__ == '__main__':
    main()

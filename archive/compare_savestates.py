#!/usr/bin/env python3
"""Compare PPSSPP save states to find memory differences for CWCheat research.

Decompresses zstd-compressed save states and diffs the RAM sections
to find where armor model indices are stored.
"""

import struct
import sys
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"

def parse_ppsspp_state(filepath):
    """Parse a PPSSPP .ppst save state file and extract decompressed sections."""
    with open(filepath, 'rb') as f:
        data = f.read()

    print(f"  File size: {len(data)} bytes")

    # Find the zstd compressed data - look for magic bytes 0x28B52FFD
    zstd_offsets = []
    for i in range(len(data) - 4):
        if data[i:i+4] == b'\x28\xb5\x2f\xfd':
            zstd_offsets.append(i)

    print(f"  Found {len(zstd_offsets)} zstd frame(s) at offsets: {[hex(o) for o in zstd_offsets]}")

    # Try to decompress the first (and likely only) zstd frame
    if not zstd_offsets:
        print("  ERROR: No zstd frames found!")
        return None

    dctx = zstandard.ZstdDecompressor()

    for idx, offset in enumerate(zstd_offsets):
        compressed = data[offset:]
        try:
            decompressed = dctx.decompress(compressed, max_output_size=128 * 1024 * 1024)
            print(f"  Zstd frame {idx} at 0x{offset:X}: decompressed to {len(decompressed)} bytes ({len(decompressed) / (1024*1024):.1f} MB)")
            return decompressed
        except Exception as e:
            print(f"  Zstd frame {idx} at 0x{offset:X}: decompression failed: {e}")
            # Try with streaming decompressor
            try:
                reader = dctx.stream_reader(compressed)
                chunks = []
                while True:
                    chunk = reader.read(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                decompressed = b''.join(chunks)
                print(f"  Zstd frame {idx} at 0x{offset:X} (streaming): decompressed to {len(decompressed)} bytes ({len(decompressed) / (1024*1024):.1f} MB)")
                return decompressed
            except Exception as e2:
                print(f"  Streaming also failed: {e2}")

    return None


def find_sections(data):
    """Find named sections in PPSSPP decompressed state data."""
    sections = {}
    # Look for common section names
    for name in [b"Memory", b"RAM", b"HLE", b"GPU", b"sceCtrl", b"sceGe", b"sceDisplay"]:
        idx = 0
        while True:
            pos = data.find(name, idx)
            if pos == -1:
                break
            sections.setdefault(name.decode(), []).append(pos)
            idx = pos + 1
    return sections


def compare_ram(data0, data1, min_addr=0x08800000):
    """Compare two decompressed state buffers and find differences.

    PSP user memory starts at 0x08800000 (after kernel space).
    PPSSPP typically stores 32MB or 64MB of RAM.
    """
    size = min(len(data0), len(data1))
    print(f"\nComparing {size} bytes ({size / (1024*1024):.1f} MB)...")

    diffs = []
    i = 0
    while i < size:
        if data0[i] != data1[i]:
            # Found a difference - capture the range
            start = i
            while i < size and data0[i] != data1[i]:
                i += 1
            end = i
            diffs.append((start, end, data0[start:end], data1[start:end]))
        else:
            i += 1

    print(f"Found {len(diffs)} different regions")
    return diffs


def analyze_diffs_for_armor(diffs, data0, data1):
    """Analyze diffs looking for armor-related patterns.

    Known values:
    - Rathalos Soul Cap: f_hair096 (file ID 502, model index likely 96 or 502)
    - Mafumofu Hood: f_hair013 (file ID 419, model index likely 13 or 419)

    Head armor data table offset for USA: 0x001633A8
    Head armor entries: 435, stride: 40 bytes

    PSP base address: 0x08800000
    So armor table in PSP memory: 0x08800000 + 0x001633A8 = 0x089633A8
    """

    # Values we're looking for in state 0 (Rathalos Soul Cap)
    # Could be model index (96), file ID (502), or item ID
    target_values_0 = {
        96: "model_idx_96 (f_hair096 number)",
        502: "file_id_502 (f_hair096 DATA.BIN index)",
        # Rathalos Soul Cap item IDs (various possible encodings)
    }

    # Values we expect in state 1 (Mafumofu Hood)
    target_values_1 = {
        13: "model_idx_13 (f_hair013 number)",
        419: "file_id_419 (f_hair013 DATA.BIN index)",
    }

    print("\n=== Analyzing differences for armor model values ===")
    print(f"Looking for state0 values: {list(target_values_0.keys())}")
    print(f"Looking for state1 values: {list(target_values_1.keys())}")

    # Check each diff region for interesting value transitions
    interesting = []
    for start, end, d0, d1 in diffs:
        region_len = end - start

        # Check 16-bit and 32-bit values at aligned positions
        for offset in range(0, region_len - 1, 1):
            abs_offset = start + offset

            # 16-bit little-endian
            if offset + 2 <= region_len:
                val0_16 = struct.unpack_from('<H', d0, offset)[0]
                val1_16 = struct.unpack_from('<H', d1, offset)[0]

                if val0_16 in target_values_0 and val1_16 in target_values_1:
                    interesting.append({
                        'offset': abs_offset,
                        'psp_addr': 0x08800000 + abs_offset,
                        'bits': 16,
                        'val0': val0_16,
                        'val1': val1_16,
                        'desc0': target_values_0[val0_16],
                        'desc1': target_values_1[val1_16],
                    })

            # 32-bit little-endian
            if offset + 4 <= region_len:
                val0_32 = struct.unpack_from('<I', d0, offset)[0]
                val1_32 = struct.unpack_from('<I', d1, offset)[0]

                if val0_32 in target_values_0 and val1_32 in target_values_1:
                    interesting.append({
                        'offset': abs_offset,
                        'psp_addr': 0x08800000 + abs_offset,
                        'bits': 32,
                        'val0': val0_32,
                        'val1': val1_32,
                        'desc0': target_values_0[val0_32],
                        'desc1': target_values_1[val1_32],
                    })

    if interesting:
        print(f"\n*** Found {len(interesting)} interesting value transitions! ***")
        for item in interesting:
            print(f"  RAM offset: 0x{item['offset']:08X}")
            print(f"  PSP addr:   0x{item['psp_addr']:08X}")
            print(f"  Bits:       {item['bits']}")
            print(f"  State 0:    {item['val0']} ({item['desc0']})")
            print(f"  State 1:    {item['val1']} ({item['desc1']})")
            print()
    else:
        print("\nNo direct value matches found. Dumping all small-value diffs...")

    return interesting


def dump_small_diffs(diffs, max_val=2000):
    """Dump all diffs where both values are small (potential model indices or item IDs)."""
    print(f"\n=== All diff regions where 16-bit values are both < {max_val} ===")
    count = 0
    results = []
    for start, end, d0, d1 in diffs:
        region_len = end - start
        if region_len > 256:
            continue  # Skip large diff regions (probably textures/framebuffer)

        for offset in range(0, min(region_len, 64), 2):
            if offset + 2 > region_len:
                break
            val0 = struct.unpack_from('<H', d0, offset)[0]
            val1 = struct.unpack_from('<H', d1, offset)[0]

            if val0 != val1 and val0 < max_val and val1 < max_val:
                abs_offset = start + offset
                psp_addr = 0x08800000 + abs_offset
                results.append((abs_offset, psp_addr, val0, val1))
                count += 1

    # Sort by PSP address
    results.sort(key=lambda x: x[1])

    for abs_offset, psp_addr, val0, val1 in results[:200]:
        print(f"  0x{psp_addr:08X} (RAM+0x{abs_offset:07X}): {val0:5d} (0x{val0:04X}) -> {val1:5d} (0x{val1:04X})  delta={val1-val0:+d}")

    if count > 200:
        print(f"  ... and {count - 200} more")
    print(f"  Total: {count} small-value diffs")
    return results


def main():
    state0_path = f"{STATE_DIR}/ULJM05500_1.01_0.ppst"
    state1_path = f"{STATE_DIR}/ULJM05500_1.01_1.ppst"

    print("=== State 0 (Rathalos Soul Cap) ===")
    decomp0 = parse_ppsspp_state(state0_path)

    print("\n=== State 1 (Mafumofu Hood) ===")
    decomp1 = parse_ppsspp_state(state1_path)

    if decomp0 is None or decomp1 is None:
        print("Failed to decompress one or both states!")
        sys.exit(1)

    # Find sections
    print("\n=== Sections in State 0 ===")
    sections0 = find_sections(decomp0)
    for name, offsets in sorted(sections0.items()):
        print(f"  {name}: {[hex(o) for o in offsets]}")

    print("\n=== Sections in State 1 ===")
    sections1 = find_sections(decomp1)
    for name, offsets in sorted(sections1.items()):
        print(f"  {name}: {[hex(o) for o in offsets]}")

    # Compare the full decompressed data
    diffs = compare_ram(decomp0, decomp1)

    # Print diff statistics
    total_diff_bytes = sum(end - start for start, end, _, _ in diffs)
    print(f"Total differing bytes: {total_diff_bytes} ({total_diff_bytes/1024:.1f} KB)")

    # Show distribution of diff sizes
    small = sum(1 for s, e, _, _ in diffs if e - s <= 4)
    medium = sum(1 for s, e, _, _ in diffs if 4 < e - s <= 64)
    large = sum(1 for s, e, _, _ in diffs if e - s > 64)
    print(f"Diff size distribution: {small} small (<=4B), {medium} medium (5-64B), {large} large (>64B)")

    # Look for armor values
    interesting = analyze_diffs_for_armor(diffs, decomp0, decomp1)

    # Dump all small-value diffs
    small_diffs = dump_small_diffs(diffs)


if __name__ == '__main__':
    main()

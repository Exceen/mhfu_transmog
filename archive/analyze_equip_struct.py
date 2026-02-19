#!/opt/homebrew/bin/python3
"""Analyze equipment data structure around known model index locations."""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"

# Known Rathalos Soul model indices (state 0)
RATHALOS_SOUL_MODELS = {
    'head': 96,   # f_hair096
    'body': 90,   # f_body090
    'arm': 88,    # f_arm088
    'waist': 76,  # f_wst076
    'leg': 66,    # f_reg066
}

# Candidate offsets where model index 96 was found
MODEL_OFFSETS = [
    0x00B2769E, 0x00B4D068, 0x010AF702, 0x011C773E,
    0x011EF450, 0x011F0010, 0x011F0050, 0x017906C0,
    0x01791280, 0x017912C0, 0x01A0A07E, 0x020EC592,
    0x024C9910, 0x024D78AA, 0x024E70BE, 0x024FB24E,
    0x02505FEE, 0x02508196, 0x025087AA, 0x02509D70,
    0x0250F028, 0x0250FE16, 0x02512C8C, 0x0251564C,
]

# File ID offsets where 502 was found
FILEID_OFFSETS = [
    0x00A358D8, 0x0112F594,
]


def decompress_state(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(data[0xB0:], max_output_size=128 * 1024 * 1024)


def search_nearby(data, center, target_vals, search_range=512):
    """Search for target values within search_range bytes of center."""
    results = []
    start = max(0, center - search_range)
    end = min(len(data) - 1, center + search_range)
    for offset in range(start, end, 2):
        val = struct.unpack_from('<H', data, offset)[0]
        if val in target_vals:
            results.append((offset, val, target_vals[val]))
    return results


def main():
    print("=== Decompressing state 0 (Rathalos Soul Cap) ===")
    data0 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")
    print(f"Size: {len(data0)} bytes")

    print("=== Decompressing state 1 (Mafumofu Hood) ===")
    data1 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_1.ppst")

    target_vals = {v: k for k, v in RATHALOS_SOUL_MODELS.items()}

    print("\n" + "=" * 70)
    print("CHECKING EACH MODEL INDEX CANDIDATE FOR NEARBY EQUIPMENT VALUES")
    print("=" * 70)
    print(f"Looking for: {RATHALOS_SOUL_MODELS}")

    for center in MODEL_OFFSETS:
        nearby = search_nearby(data0, center, target_vals, search_range=256)
        # Count how many different armor piece types we found
        found_types = set(name for _, _, name in nearby)

        if len(found_types) >= 3:  # Found at least 3 of 5 armor pieces nearby
            print(f"\n*** PROMISING: 0x{center:08X} has {len(found_types)} armor types nearby ***")
            for off, val, name in sorted(nearby):
                # Also check what state1 has at this offset
                val1 = struct.unpack_from('<H', data1, off)[0]
                delta = off - center
                print(f"  0x{off:08X} (delta={delta:+d}): {val:5d} -> {val1:5d}  ({name}, model f_*{val:03d} -> f_*{val1:03d})")
        elif len(found_types) >= 2:
            print(f"\n  Partial: 0x{center:08X} has {len(found_types)} armor types: {found_types}")

    # Now check file ID offsets for nearby file IDs
    print("\n" + "=" * 70)
    print("CHECKING FILE ID OFFSETS FOR NEARBY EQUIPMENT FILE IDS")
    print("=" * 70)

    # File IDs for Rathalos Soul set
    fileid_targets = {
        502: 'head (f_hair096)',     # 406 + 96
        836: 'body (f_body090)',     # 746 + 90
        1174: 'arm (f_arm088)',      # 1086 + 88
        1495: 'waist (f_wst076)',    # 1419 + 76
        128: 'leg (f_reg066)',       # 62 + 66
    }

    for center in FILEID_OFFSETS:
        nearby = search_nearby(data0, center, fileid_targets, search_range=256)
        found_types = set(name for _, _, name in nearby)

        if len(found_types) >= 2:
            print(f"\n*** MATCH: 0x{center:08X} has {len(found_types)} file ID types nearby ***")
            for off, val, name in sorted(nearby):
                val1 = struct.unpack_from('<H', data1, off)[0]
                delta = off - center
                print(f"  0x{off:08X} (delta={delta:+d}): {val:5d} -> {val1:5d}  ({name})")

    # Also: search more broadly for clusters of Rathalos Soul model indices
    # If all 5 model indices appear within 100 bytes, that's the equipment struct
    print("\n" + "=" * 70)
    print("BROAD SEARCH: clusters of all 5 model indices")
    print("=" * 70)

    all_model_vals = set(RATHALOS_SOUL_MODELS.values())
    # First find all locations of model index 96 (head)
    head_locs = []
    for off in range(0, len(data0) - 1, 2):
        if struct.unpack_from('<H', data0, off)[0] == 96:
            head_locs.append(off)

    for head_off in head_locs:
        # Check ±100 bytes for other model indices
        found = set()
        found_details = []
        for check_off in range(max(0, head_off - 100), min(len(data0) - 1, head_off + 100), 2):
            val = struct.unpack_from('<H', data0, check_off)[0]
            if val in all_model_vals:
                found.add(val)
                found_details.append((check_off, val))

        if len(found) >= 4:  # At least 4 of 5 found
            print(f"\n*** CLUSTER at ~0x{head_off:08X}: found {len(found)}/5 model values ***")
            for off, val in sorted(found_details):
                name = target_vals.get(val, '?')
                val1 = struct.unpack_from('<H', data1, off)[0]
                print(f"  0x{off:08X}: {val:5d} -> {val1:5d}  ({name})")

    # Additionally, let's try 32-bit values for armor IDs
    # Maybe the armor ID is stored as a 32-bit value
    print("\n" + "=" * 70)
    print("32-bit search for armor ID 101 -> 251")
    print("=" * 70)
    for off in range(0, min(len(data0), len(data1)) - 3, 4):
        v0 = struct.unpack_from('<I', data0, off)[0]
        v1 = struct.unpack_from('<I', data1, off)[0]
        if v0 == 101 and v1 == 251:
            print(f"  0x{off:08X}: {v0} -> {v1}")

    # Try byte-aligned 16-bit
    print("\n=== Byte-aligned 16-bit search for 101 -> 251 ===")
    for off in range(0, min(len(data0), len(data1)) - 1, 1):
        v0 = struct.unpack_from('<H', data0, off)[0]
        v1 = struct.unpack_from('<H', data1, off)[0]
        if v0 == 101 and v1 == 251:
            print(f"  0x{off:08X}: {v0} -> {v1}")
            # Show context
            s = max(0, off - 16)
            e = min(len(data0), off + 16)
            hex0 = ' '.join(f'{b:02X}' for b in data0[s:e])
            hex1 = ' '.join(f'{b:02X}' for b in data1[s:e])
            print(f"    state0: {hex0}")
            print(f"    state1: {hex1}")


if __name__ == '__main__':
    main()

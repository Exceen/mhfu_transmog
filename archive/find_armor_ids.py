#!/opt/homebrew/bin/python3
"""Find armor IDs by searching the decompressed save state for armor name tables."""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"


def decompress_state(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(data[0xB0:], max_output_size=128 * 1024 * 1024)


def search_string(data, pattern):
    """Search for a string pattern and print context."""
    pattern_bytes = pattern.encode('ascii')
    results = []
    idx = 0
    while True:
        pos = data.find(pattern_bytes, idx)
        if pos == -1:
            break
        results.append(pos)
        idx = pos + 1
    return results


def analyze_head_armor_table(data, table_start):
    """Parse the head armor name string table starting from 'Nothing equipped.'

    In MH games, armor name tables are null-terminated strings packed sequentially.
    The index in the table corresponds to the armor ID.
    """
    pos = table_start
    names = []
    for i in range(500):  # Read up to 500 names
        # Find next null terminator
        end = data.find(b'\x00', pos)
        if end == -1 or end - pos > 200:  # Safety check
            break
        name = data[pos:end].decode('ascii', errors='replace')
        if not name or len(name) < 2:
            break
        # Check if it looks like an armor name (printable ASCII)
        if all(32 <= c < 127 for c in data[pos:end]):
            names.append((i, pos, name))
        else:
            break
        pos = end + 1
    return names


def main():
    print("=== Decompressing state 0 ===")
    data = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")
    print(f"Size: {len(data)} bytes")

    # Search for Mafumofu
    print("\n=== Searching for 'Mafumofu' ===")
    mafumofu_locs = search_string(data, "Mafumofu")
    for loc in mafumofu_locs:
        # Show context
        start = max(0, loc - 32)
        end = min(len(data), loc + 64)
        context = data[start:end]
        print(f"  0x{loc:08X}: {context}")
        # Also show as ASCII
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in context)
        print(f"    ASCII: {ascii_str}")

    # Search for "Rathalos Soul"
    print("\n=== Searching for 'Rathalos Soul' ===")
    rathsoul_locs = search_string(data, "Rathalos Soul")
    for loc in rathsoul_locs[:20]:
        start = max(0, loc - 32)
        end = min(len(data), loc + 64)
        context = data[start:end]
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in context)
        print(f"  0x{loc:08X}: {ascii_str}")

    # Search for "Chakra" (invisible armor)
    print("\n=== Searching for 'Chakra' ===")
    chakra_locs = search_string(data, "Chakra")
    for loc in chakra_locs[:20]:
        start = max(0, loc - 32)
        end = min(len(data), loc + 64)
        context = data[start:end]
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in context)
        print(f"  0x{loc:08X}: {ascii_str}")

    # Search for piercing headpieces
    print("\n=== Searching for 'Piercing' ===")
    piercing_locs = search_string(data, "Piercing")
    for loc in piercing_locs[:20]:
        start = max(0, loc - 32)
        end = min(len(data), loc + 64)
        context = data[start:end]
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in context)
        print(f"  0x{loc:08X}: {ascii_str}")

    # Find the head armor name table that starts with "Nothing equipped."
    # followed by armor names. Look at 0x00A026BD which had:
    # "Nothing equipped.\0Leather Helm\0..."
    print("\n=== Head armor name tables ===")
    nothing_locs = search_string(data, "Nothing equipped.")
    for loc in nothing_locs:
        # Check what follows
        end_of_nothing = loc + len("Nothing equipped.") + 1  # +1 for null
        next_64 = data[end_of_nothing:end_of_nothing + 64]
        ascii_next = ''.join(chr(b) if 32 <= b < 127 else '.' for b in next_64)

        # Determine what type of table this is based on what follows
        print(f"\n  Table at 0x{loc:08X}, followed by: {ascii_next}")

        # Parse the full name list
        names = analyze_head_armor_table(data, end_of_nothing)
        if len(names) > 5:
            print(f"    Found {len(names)} armor names:")
            # Print first 20 and look for Mafumofu/Rathalos Soul
            for idx, offset, name in names[:20]:
                print(f"      [{idx:3d}] 0x{offset:08X}: {name}")
            print(f"      ...")
            # Find specific armors
            for idx, offset, name in names:
                if "Mafumofu" in name or "Rathalos Soul" in name or "Chakra" in name or "Piercing" in name:
                    print(f"      [{idx:3d}] 0x{offset:08X}: {name}  <-- INTERESTING")

    # Also check: what's right before "Nothing equipped." ?
    # Usually there's a pointer table or count before the name table
    print("\n=== Data before head armor name tables ===")
    for loc in nothing_locs:
        pre_data = data[max(0, loc-64):loc]
        hex_str = ' '.join(f'{b:02X}' for b in pre_data[-32:])
        print(f"  Before 0x{loc:08X}: {hex_str}")
        # Check for 32-bit values that could be string offsets
        for i in range(0, min(32, len(pre_data)), 4):
            val = struct.unpack_from('<I', pre_data, len(pre_data) - 32 + i)[0]
            if val < 0x10000:  # Reasonable string offset
                print(f"    u32 at -{32-i}: {val} (0x{val:04X})")


if __name__ == '__main__':
    main()

#!/opt/homebrew/bin/python3
"""Targeted comparison of PPSSPP save states for specific armor ID transitions."""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"

# Armor table indices (from name table analysis)
RATHALOS_SOUL_CAP = 101   # state 0
MAFUMOFU_HOOD = 251       # state 1

# Model file numbers (from f_hair### naming)
RATHALOS_SOUL_MODEL = 96  # f_hair096
# Mafumofu model unknown, but likely low number (13?)

# File IDs in DATA.BIN
RATHALOS_SOUL_FILEID = 502  # 406 + 96
# Mafumofu file ID unknown

def decompress_state(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(data[0xB0:], max_output_size=128 * 1024 * 1024)


def search_value_transitions(data0, data1, val0, val1, bits=16):
    """Search for locations where data0 has val0 and data1 has val1."""
    fmt = '<H' if bits == 16 else '<I'
    size = 2 if bits == 16 else 4
    results = []

    min_len = min(len(data0), len(data1))
    for offset in range(0, min_len - size + 1, 1):  # Check every byte, not just aligned
        v0 = struct.unpack_from(fmt, data0, offset)[0]
        v1 = struct.unpack_from(fmt, data1, offset)[0]
        if v0 == val0 and v1 == val1:
            results.append(offset)

    return results


def show_context(data0, data1, offset, label, size=64):
    """Show hex context around an offset in both states."""
    start = max(0, offset - size)
    end = min(len(data0), offset + size)

    print(f"\n  {label} at offset 0x{offset:08X}:")
    # Show nearby bytes in both states
    chunk0 = data0[start:end]
    chunk1 = data1[start:end]

    # Show a few 16-bit values before and after in both states
    print(f"  State 0 (Rathalos Soul Cap):")
    vals = []
    for i in range(max(0, offset - 20), min(len(data0) - 1, offset + 20), 2):
        v = struct.unpack_from('<H', data0, i)[0]
        marker = " <<" if i == offset else ""
        vals.append(f"    0x{i:08X}: {v:5d} (0x{v:04X}){marker}")
    print('\n'.join(vals))

    print(f"  State 1 (Mafumofu Hood):")
    vals = []
    for i in range(max(0, offset - 20), min(len(data1) - 1, offset + 20), 2):
        v = struct.unpack_from('<H', data1, i)[0]
        marker = " <<" if i == offset else ""
        vals.append(f"    0x{i:08X}: {v:5d} (0x{v:04X}){marker}")
    print('\n'.join(vals))


def main():
    print("=== Decompressing save states ===")
    data0 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")
    data1 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_1.ppst")
    print(f"State 0: {len(data0)} bytes, State 1: {len(data1)} bytes")

    # Search for armor ID transition: 101 -> 251
    print(f"\n=== Searching for armor ID transition: {RATHALOS_SOUL_CAP} -> {MAFUMOFU_HOOD} ===")

    print("\n--- 16-bit search ---")
    results_16 = search_value_transitions(data0, data1, RATHALOS_SOUL_CAP, MAFUMOFU_HOOD, 16)
    print(f"Found {len(results_16)} matches")
    for off in results_16[:20]:
        show_context(data0, data1, off, "16-bit match")

    print("\n--- 32-bit search ---")
    results_32 = search_value_transitions(data0, data1, RATHALOS_SOUL_CAP, MAFUMOFU_HOOD, 32)
    print(f"Found {len(results_32)} matches")
    for off in results_32[:20]:
        show_context(data0, data1, off, "32-bit match")

    # Also try the reverse (item ID might be stored differently)
    # Try 16-bit: 101 -> 251 as bytes
    print(f"\n=== Also searching for model transition: {RATHALOS_SOUL_MODEL} -> ??? ===")
    # Look for any location where state0 has 96 and state1 has a different small value
    # This could help us find the model index and determine Mafumofu's model number
    fmt = '<H'
    model_candidates = []
    min_len = min(len(data0), len(data1))
    for offset in range(0, min_len - 1, 2):  # 2-byte aligned
        v0 = struct.unpack_from(fmt, data0, offset)[0]
        v1 = struct.unpack_from(fmt, data1, offset)[0]
        if v0 == RATHALOS_SOUL_MODEL and v1 != v0 and v1 < 500:
            model_candidates.append((offset, v0, v1))

    print(f"Found {len(model_candidates)} locations where state0 has {RATHALOS_SOUL_MODEL}")
    # Filter for plausible model indices (small positive values)
    plausible = [(off, v0, v1) for off, v0, v1 in model_candidates if 0 < v1 < 300]
    print(f"  {len(plausible)} with plausible replacement value (1-299)")
    for off, v0, v1 in plausible[:30]:
        print(f"  0x{off:08X}: {v0} -> {v1}")

    # Check file ID transition (502 -> ???)
    print(f"\n=== Searching for file ID: state0 has {RATHALOS_SOUL_FILEID} ===")
    fileid_candidates = []
    for offset in range(0, min_len - 1, 2):
        v0 = struct.unpack_from(fmt, data0, offset)[0]
        v1 = struct.unpack_from(fmt, data1, offset)[0]
        if v0 == RATHALOS_SOUL_FILEID and v1 != v0:
            fileid_candidates.append((offset, v0, v1))
    print(f"Found {len(fileid_candidates)} locations")
    for off, v0, v1 in fileid_candidates[:20]:
        print(f"  0x{off:08X}: {v0} -> {v1} (delta={v1-v0:+d})")
        if v1 > 406:
            print(f"    -> Could be f_hair{v1-406:03d}")

    # Specifically search for body/arm/waist/leg transitions too
    # Rathalos Soul set:
    #   head: armor_id=101, model=f_hair096
    #   body: armor_id=98 (Rathalos Soul Mail), model=f_body090
    #   arm:  armor_id=96, model=f_arm088
    #   waist: armor_id=96, model=f_wst076
    #   leg: armor_id=93, model=f_reg066
    # User has Rathalos Soul equipped in state 0
    # In state 1, head changed to Mafumofu Hood but other pieces may also differ

    # Let's also try byte-level search for the armor ID
    print(f"\n=== Byte-level search: where does byte {RATHALOS_SOUL_CAP} appear in state0 ===")
    print(f"    and byte {MAFUMOFU_HOOD} at same position in state1?")
    # 101 = 0x65, 251 = 0xFB
    byte_matches = []
    for i in range(min_len):
        if data0[i] == RATHALOS_SOUL_CAP and data1[i] == MAFUMOFU_HOOD:
            byte_matches.append(i)
    print(f"Found {len(byte_matches)} single-byte matches")
    for off in byte_matches[:20]:
        # Show surrounding bytes
        s = max(0, off - 8)
        e = min(min_len, off + 8)
        hex0 = ' '.join(f'{b:02X}' for b in data0[s:e])
        hex1 = ' '.join(f'{b:02X}' for b in data1[s:e])
        print(f"  0x{off:08X}: state0=[{hex0}] state1=[{hex1}]")


if __name__ == '__main__':
    main()

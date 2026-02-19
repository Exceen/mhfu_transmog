#!/opt/homebrew/bin/python3
"""Find the model lookup table indexed by u16[18] from armor data entries.

Known mappings:
  table[61] = 1    (Leather Helm)
  table[62] = 2    (Chainmail)
  table[133] = 223 (Mafumofu Hood v1)
  table[134] = 223 (Mafumofu Hood v2)
  table[186] = 96  (Rathalos Soul Cap)
  table[187] = 97  (Rathalos Soul Helm)
  table[275] = 0   (Nothing equipped)
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
RAM_BASE_IN_STATE = 0x48
PSP_RAM_START = 0x08000000

KNOWN = {
    61: 1,
    62: 2,
    133: 223,
    134: 223,
    186: 96,
    187: 97,
    275: 0,
}


def decompress_state(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(data[0xB0:], max_output_size=128 * 1024 * 1024)


def state_to_psp(off):
    return off - RAM_BASE_IN_STATE + PSP_RAM_START


def main():
    data = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")
    print(f"Decompressed: {len(data)} bytes")

    max_idx = max(KNOWN.keys())

    # Search for 16-bit lookup table
    print(f"\n=== Searching for 16-bit lookup table ===")
    print(f"Constraints: {KNOWN}")
    print(f"Max index: {max_idx}, need at least {max_idx*2+2} bytes from base")

    results_16 = []
    for base in range(0, len(data) - (max_idx * 2 + 2)):
        match = True
        for idx, expected in KNOWN.items():
            val = struct.unpack_from('<H', data, base + idx * 2)[0]
            if val != expected:
                match = False
                break
        if match:
            psp = state_to_psp(base)
            results_16.append((base, psp))

    print(f"Found {len(results_16)} matches")
    for base, psp in results_16[:10]:
        print(f"\n  Base: state 0x{base:08X} (PSP 0x{psp:08X})")
        # Dump some values
        for idx in sorted(KNOWN.keys()):
            val = struct.unpack_from('<H', data, base + idx * 2)[0]
            expected = KNOWN[idx]
            ok = "✓" if val == expected else "✗"
            print(f"    [{idx:3d}] = {val:5d} (expected {expected:5d}) {ok}")
        # Also show some unknown entries
        print(f"    First 20 values:")
        vals = [struct.unpack_from('<H', data, base + i * 2)[0] for i in range(20)]
        print(f"    {vals}")
        # Show piercing entries (410-413 from u16[18])
        if base + 413 * 2 + 1 < len(data):
            print(f"    Piercing indices [410-413]:")
            for i in [410, 411, 412, 413]:
                v = struct.unpack_from('<H', data, base + i * 2)[0]
                print(f"      [{i}] = {v}")

    # Search for 8-bit lookup table
    print(f"\n=== Searching for 8-bit lookup table ===")
    results_8 = []
    for base in range(0, len(data) - (max_idx + 1)):
        match = True
        for idx, expected in KNOWN.items():
            if expected > 255:
                match = False
                break
            if data[base + idx] != expected:
                match = False
                break
        if match:
            psp = state_to_psp(base)
            results_8.append((base, psp))

    print(f"Found {len(results_8)} matches")
    for base, psp in results_8[:10]:
        print(f"\n  Base: state 0x{base:08X} (PSP 0x{psp:08X})")
        for idx in sorted(KNOWN.keys()):
            val = data[base + idx]
            expected = KNOWN[idx]
            ok = "✓" if val == expected else "✗"
            print(f"    [{idx:3d}] = {val:3d} (expected {expected:3d}) {ok}")
        print(f"    First 20 values: {list(data[base:base+20])}")
        if base + 413 < len(data):
            print(f"    Piercing [410-413]: {list(data[base+410:base+414])}")

    # If no direct table found, try with file IDs instead of model numbers
    # file_id = base_id + model_number
    # For head: base = 406
    FILE_KNOWN = {
        61: 407,   # 406 + 1
        62: 408,   # 406 + 2
        133: 629,  # 406 + 223
        134: 629,  # same model
        186: 502,  # 406 + 96
        187: 503,  # 406 + 97
        275: 406,  # 406 + 0
    }

    print(f"\n=== Searching for file ID lookup table (head file IDs) ===")
    print(f"Constraints: {FILE_KNOWN}")

    results_fid = []
    for base in range(0, len(data) - (max_idx * 2 + 2)):
        match = True
        for idx, expected in FILE_KNOWN.items():
            val = struct.unpack_from('<H', data, base + idx * 2)[0]
            if val != expected:
                match = False
                break
        if match:
            psp = state_to_psp(base)
            results_fid.append((base, psp))

    print(f"Found {len(results_fid)} matches")
    for base, psp in results_fid[:10]:
        print(f"\n  Base: state 0x{base:08X} (PSP 0x{psp:08X})")
        for idx in sorted(FILE_KNOWN.keys()):
            val = struct.unpack_from('<H', data, base + idx * 2)[0]
            expected = FILE_KNOWN[idx]
            print(f"    [{idx:3d}] = {val:5d} (expected {expected:5d})")
        vals = [struct.unpack_from('<H', data, base + i * 2)[0] for i in range(20)]
        print(f"    First 20: {vals}")


if __name__ == '__main__':
    main()

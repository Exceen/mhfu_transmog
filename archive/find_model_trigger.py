#!/opt/homebrew/bin/python3
"""Search comprehensively for ALL differences between save states
that could be related to head model rendering.

Focus areas:
1. FUComplete memory area (0x099xxxxx) - wide search
2. Player entity rendering state
3. Model cache / loaded model pointers
4. Any "dirty" or "needs reload" flags
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

def read_u16(data, psp_addr):
    off = psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<H', data, off)[0]

def read_u32(data, psp_addr):
    off = psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


def main():
    print("Loading both save states...")
    data1 = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)
    data2 = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_1.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)
    print(f"  State 1 (Rath Soul):  {len(data1)} bytes")
    print(f"  State 2 (Mafumofu):   {len(data2)} bytes")

    # === 1. Comprehensive diff of FUComplete memory area ===
    # Base pointer is 0x099959A0, search a wide area around it
    print("\n" + "=" * 70)
    print("  ALL diffs in FUComplete memory 0x09990000 - 0x099B0000")
    print("  (base pointer is at 0x099959A0)")
    print("=" * 70)
    diff_count = 0
    for psp in range(0x09990000, 0x099B0000, 2):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 1 >= len(data1) or off + 1 >= len(data2): break
        v1 = struct.unpack_from('<H', data1, off)[0]
        v2 = struct.unpack_from('<H', data2, off)[0]
        if v1 != v2:
            diff_count += 1
            rel = psp - 0x099959A0
            print(f"  0x{psp:08X} (base+0x{rel:04X}): {v1:04X} ({v1:5d}) vs {v2:04X} ({v2:5d})")
    print(f"\n  Total diffs: {diff_count}")

    # === 2. Search for diffs in the EBOOT code/data area ===
    # Specifically around model tables and rendering data
    print("\n" + "=" * 70)
    print("  Diffs in model table area 0x08960000 - 0x089A0000")
    print("=" * 70)
    diff_count = 0
    for psp in range(0x08960000, 0x089A0000, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 3 >= len(data1) or off + 3 >= len(data2): break
        v1 = struct.unpack_from('<I', data1, off)[0]
        v2 = struct.unpack_from('<I', data2, off)[0]
        if v1 != v2:
            diff_count += 1
            if diff_count <= 30:
                print(f"  0x{psp:08X}: {v1:08X} vs {v2:08X}")
    print(f"  Total diffs: {diff_count}")
    if diff_count > 30:
        print("  (showing first 30)")

    # === 3. Search for diffs in player entity area ===
    # Player entities might be around 0x08A00000-0x08B00000
    print("\n" + "=" * 70)
    print("  Diffs in player entity area 0x08A00000 - 0x08C00000")
    print("=" * 70)
    diff_count = 0
    diff_addrs = []
    for psp in range(0x08A00000, 0x08C00000, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 3 >= len(data1) or off + 3 >= len(data2): break
        v1 = struct.unpack_from('<I', data1, off)[0]
        v2 = struct.unpack_from('<I', data2, off)[0]
        if v1 != v2:
            diff_count += 1
            diff_addrs.append(psp)
            if diff_count <= 30:
                print(f"  0x{psp:08X}: {v1:08X} vs {v2:08X}")
    print(f"  Total diffs: {diff_count}")

    # === 4. Wider search: find ALL 32-bit diffs in 0x08800000-0x09A00000 ===
    print("\n" + "=" * 70)
    print("  Summary of ALL diffs across entire game RAM")
    print("  (0x08800000 - 0x09A00000, grouped by 64KB region)")
    print("=" * 70)
    region_diffs = {}
    for psp in range(0x08800000, 0x09A00000, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 3 >= len(data1) or off + 3 >= len(data2): break
        v1 = struct.unpack_from('<I', data1, off)[0]
        v2 = struct.unpack_from('<I', data2, off)[0]
        if v1 != v2:
            region = psp & 0xFFFF0000
            if region not in region_diffs:
                region_diffs[region] = 0
            region_diffs[region] += 1
    for region in sorted(region_diffs.keys()):
        count = region_diffs[region]
        bar = "#" * min(count, 50)
        print(f"  0x{region:08X}: {count:6d} diffs {bar}")

    # === 5. Focus on regions with FEW diffs (more likely to be key values) ===
    print("\n" + "=" * 70)
    print("  Detailed diffs in regions with < 20 differences")
    print("  (these are most likely to be key rendering values)")
    print("=" * 70)
    for region in sorted(region_diffs.keys()):
        count = region_diffs[region]
        if count < 20:
            print(f"\n  Region 0x{region:08X} ({count} diffs):")
            for psp in range(region, region + 0x10000, 4):
                off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
                if off + 3 >= len(data1) or off + 3 >= len(data2): break
                v1 = struct.unpack_from('<I', data1, off)[0]
                v2 = struct.unpack_from('<I', data2, off)[0]
                if v1 != v2:
                    print(f"    0x{psp:08X}: {v1:08X} vs {v2:08X}")


if __name__ == '__main__':
    main()

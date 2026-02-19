#!/opt/homebrew/bin/python3
"""Investigate the third equip copy at 0x090AF682 and its surrounding structure."""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

def read_u16(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<H', data, off)[0]

def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


def main():
    print("Loading both save states...")
    data1 = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)
    data2 = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_1.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

    THIRD_COPY = 0x090AF682
    ENTITY_BASE = 0x099959A0
    ENTITY_COPY1 = ENTITY_BASE + 0x78
    ENTITY_COPY2 = ENTITY_BASE + 0x4D8

    # === 1. Full context around third copy ===
    print("=" * 70)
    print(f"  Memory dump around third equip copy (0x{THIRD_COPY:08X})")
    print("=" * 70)
    # Show 128 bytes before and 128 bytes after
    for off in range(-128, 128, 2):
        addr = THIRD_COPY + off
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        diff = " <<<" if v1 != v2 else ""
        marker = " [HEAD_EQUIP_ID]" if off == 0 else ""
        # Check if this looks like an equip slot boundary (type bytes 01-05 followed by 01)
        if off >= -4 and off <= 0 and off % 2 == 0:
            marker += f" (type?)"
        print(f"  +{off:+4d} (0x{addr:08X}): {v1:04X}/{v2:04X}{diff}{marker}")

    # === 2. Check if there are full 5 equip slots at the third copy ===
    print("\n" + "=" * 70)
    print("  Check for 5 equip slots starting at third copy - 2")
    print("=" * 70)
    base = THIRD_COPY - 2  # Start at type bytes
    for slot in range(5):
        slot_addr = base + slot * 12
        fields_1 = []
        fields_2 = []
        for f in range(0, 12, 2):
            v1 = read_u16(data1, slot_addr + f)
            v2 = read_u16(data2, slot_addr + f)
            fields_1.append(f"{v1:04X}")
            fields_2.append(f"{v2:04X}")
        slot_names = ["Head", "Body", "Arms", "Waist", "Legs"]
        name = slot_names[slot] if slot < 5 else f"Slot{slot}"
        match = "MATCH" if fields_1 == fields_2 else "DIFF"
        print(f"  {name:6s} at 0x{slot_addr:08X}: [{' '.join(fields_1)}]")
        print(f"  {'':6s}                    [{' '.join(fields_2)}] {match}")

    # === 3. Compare with entity copies ===
    print("\n" + "=" * 70)
    print("  Comparison: all three equip copies (State 1 only)")
    print("=" * 70)
    for slot in range(5):
        slot_names = ["Head", "Body", "Arms", "Waist", "Legs"]
        c1_addr = ENTITY_COPY1 + slot * 12
        c2_addr = ENTITY_COPY2 + slot * 12
        c3_addr = base + slot * 12
        for copy, addr, label in [
            (1, c1_addr, "Entity Copy 1"),
            (2, c2_addr, "Entity Copy 2"),
            (3, c3_addr, "Third Copy"),
        ]:
            fields = []
            for f in range(0, 12, 2):
                v = read_u16(data1, addr + f)
                fields.append(f"{v:04X}")
            print(f"  {slot_names[slot]:6s} {label:14s} (0x{addr:08X}): [{' '.join(fields)}]")
        print()

    # === 4. Find the base of the structure containing the third copy ===
    print("=" * 70)
    print("  Searching for structure base (pointer to this area)")
    print("=" * 70)
    # Search for pointers to the third copy area
    target_ranges = [
        (THIRD_COPY - 0x100, THIRD_COPY + 0x100),  # Direct pointer to this area
    ]
    for tgt_start, tgt_end in target_ranges:
        for psp in range(0x08800000, 0x09A00000, 4):
            off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
            if off + 3 >= len(data1): break
            v = struct.unpack_from('<I', data1, off)[0]
            if tgt_start <= v <= tgt_end:
                print(f"  0x{psp:08X} contains 0x{v:08X} (points near third copy)")

    # === 5. ALL diffs in the 0x090AF000-0x090B0000 area ===
    print("\n" + "=" * 70)
    print("  All diffs in 0x090AF000-0x090B0000")
    print("=" * 70)
    for psp in range(0x090AF000, 0x090B0000, 2):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 1 >= len(data1) or off + 1 >= len(data2): break
        v1 = struct.unpack_from('<H', data1, off)[0]
        v2 = struct.unpack_from('<H', data2, off)[0]
        if v1 != v2:
            rel = psp - THIRD_COPY
            print(f"  0x{psp:08X} (third+{rel:+5d}): {v1:04X}/{v2:04X}")

    # === 6. Check the model cache file_id more carefully ===
    print("\n" + "=" * 70)
    print("  Model cache file_id investigation")
    print("=" * 70)
    cache_addr = 0x08B1CDA4
    fid1 = read_u32(data1, cache_addr)
    fid2 = read_u32(data2, cache_addr)
    print(f"  State 1 (Rath Soul): file_id=0x{fid1:08X}, upper16=0x{(fid1>>16):04X}, lower16=0x{(fid1&0xFFFF):04X}")
    print(f"  State 2 (Mafumofu): file_id=0x{fid2:08X}, upper16=0x{(fid2>>16):04X}, lower16=0x{(fid2&0xFFFF):04X}")

    # Check if file_id upper16 is unique across all cache entries
    print("\n  All valid cache entries and their file_id upper16:")
    for i in range(20):
        entry_addr = 0x08B1CCA4 + i * 0x20
        off = entry_addr - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 0x20 > len(data1): break
        vals1 = struct.unpack_from('<8I', data1, off)
        vals2 = struct.unpack_from('<8I', data2, off)
        if vals1[6] == 0x01010100:  # valid entry
            fid1 = vals1[0]
            fid2 = vals2[0]
            diff = " DIFF" if fid1 != fid2 else ""
            head = " <<<HEAD" if entry_addr == cache_addr else ""
            print(f"    [{i:2d}] 0x{entry_addr:08X}: s1=0x{fid1:08X} (upper=0x{fid1>>16:04X}) "
                  f"s2=0x{fid2:08X} (upper=0x{fid2>>16:04X}){diff}{head}")


if __name__ == '__main__':
    main()

#!/opt/homebrew/bin/python3
"""Find the render-time value for head armor.

Compare two save states (Rath Soul vs Mafumofu head) to find the specific
value(s) the renderer reads to determine which head model to draw.

We DON'T want equip_id diffs - we already know those.
We want downstream render values: model cache entries, file group IDs,
model pointers, texture references, etc.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

KNOWN_EQUIP_ADDRS = {
    0x09995A1A,  # entity copy 1
    0x09995E7A,  # entity copy 2
    0x090AF682,  # third copy
}


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

    max_psp = min(
        PSP_RAM_START + len(data1) - RAM_BASE_IN_STATE,
        PSP_RAM_START + len(data2) - RAM_BASE_IN_STATE
    )

    # === 1. FUComplete table values for equip_ids 102 and 252 ===
    print("=" * 70)
    print("  FUComplete table values")
    print("=" * 70)
    tables = [
        ("A", 0x089972AC, "file group"),
        ("B", 0x08997BA8, "model index"),
        ("C", 0x08997E6C, "identity?"),
        ("D", 0x089981D4, "stats?"),
        ("E", 0x0899851C, "texture?"),
    ]
    for name, base, desc in tables:
        v102 = read_u16(data1, base + 102 * 2)
        v252 = read_u16(data1, base + 252 * 2)
        print(f"  Table {name} ({desc}): [{102}]={v102} (0x{v102:04X}), [{252}]={v252} (0x{v252:04X})")

    # === 2. Model cache area (comprehensive dump) ===
    print("\n" + "=" * 70)
    print("  Model cache area diffs (0x08B1CC00-0x08B1CE40)")
    print("=" * 70)
    for psp in range(0x08B1CC00, 0x08B1CE40, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        v1 = struct.unpack_from('<I', data1, off)[0]
        v2 = struct.unpack_from('<I', data2, off)[0]
        if v1 != v2:
            # Check if this is part of a cache entry
            entry_offset = (psp - 0x08B1CC00) % 0x20
            entry_idx = (psp - 0x08B1CC00) // 0x20
            field_names = {0: "file_id", 4: "data_ptr", 8: "size", 12: "unk0C",
                           16: "size2", 20: "unk14", 24: "flags", 28: "unk1C"}
            field = field_names.get(entry_offset, f"+{entry_offset:02X}")
            print(f"  0x{psp:08X} [entry {entry_idx}, {field}]: "
                  f"s1=0x{v1:08X} s2=0x{v2:08X}")

    # === 3. Comprehensive diff scan for render-related values ===
    # Search key areas for ALL u32 diffs (not just equip_id)
    print("\n" + "=" * 70)
    print("  All u32 diffs in 0x08B00000-0x08B20000 (model/rendering area)")
    print("=" * 70)
    count = 0
    for psp in range(0x08B00000, 0x08B20000, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 3 >= len(data1) or off + 3 >= len(data2):
            break
        v1 = struct.unpack_from('<I', data1, off)[0]
        v2 = struct.unpack_from('<I', data2, off)[0]
        if v1 != v2:
            count += 1
            if count <= 50:
                print(f"  0x{psp:08X}: s1=0x{v1:08X} s2=0x{v2:08X}")
    print(f"  Total diffs: {count}")

    # === 4. Search for file_group values (0x01F7 for Rath Soul, 0x0080 for Mafumofu) ===
    print("\n" + "=" * 70)
    print("  Locations where u16 = file_group of Rath Soul (0x01F7) in state1")
    print("  and differs from state2")
    print("=" * 70)
    count = 0
    for psp in range(0x08800000, max_psp - 1, 2):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 1 >= len(data1) or off + 1 >= len(data2):
            break
        v1 = struct.unpack_from('<H', data1, off)[0]
        v2 = struct.unpack_from('<H', data2, off)[0]
        if v1 == 0x01F7 and v2 != 0x01F7:
            # Skip known FUComplete table entries
            in_table = False
            for _, tbase, _ in tables:
                if tbase + 102 * 2 == psp:
                    in_table = True
            label = " [FUComplete]" if in_table else ""
            count += 1
            if count <= 30:
                print(f"  0x{psp:08X}: 0x{v1:04X} vs 0x{v2:04X}{label}")
    print(f"  Total: {count}")

    # === 5. Search for model data pointer diffs ===
    print("\n" + "=" * 70)
    print("  Locations containing Rath Soul model ptr (0x091EE8A0) in state1")
    print("=" * 70)
    count = 0
    for psp in range(0x08800000, max_psp - 3, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 3 >= len(data1):
            break
        v1 = struct.unpack_from('<I', data1, off)[0]
        if v1 == 0x091EE8A0:
            v2 = struct.unpack_from('<I', data2, off)[0]
            diff = " DIFF" if v1 != v2 else ""
            count += 1
            if count <= 30:
                print(f"  0x{psp:08X}: 0x{v1:08X} (s2: 0x{v2:08X}){diff}")
    print(f"  Total: {count}")

    # === 6. Third copy area diffs (detailed) ===
    print("\n" + "=" * 70)
    print("  All diffs around third equip copy (0x090AF500-0x090B0000)")
    print("=" * 70)
    count = 0
    for psp in range(0x090AF500, 0x090B0000, 2):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 1 >= len(data1) or off + 1 >= len(data2):
            break
        v1 = struct.unpack_from('<H', data1, off)[0]
        v2 = struct.unpack_from('<H', data2, off)[0]
        if v1 != v2:
            known = " [EQUIP_ID]" if psp in KNOWN_EQUIP_ADDRS else ""
            # Also check as u32
            if psp % 4 == 0 and off + 3 < len(data1):
                w1 = struct.unpack_from('<I', data1, off)[0]
                w2 = struct.unpack_from('<I', data2, off)[0]
                print(f"  0x{psp:08X}: u16={v1:04X}/{v2:04X}  u32=0x{w1:08X}/0x{w2:08X}{known}")
            else:
                print(f"  0x{psp:08X}: u16={v1:04X}/{v2:04X}{known}")
            count += 1
    print(f"  Total diffs: {count}")

    # === 7. Entity structure diffs (comprehensive) ===
    ENTITY_BASE = 0x099959A0
    print("\n" + "=" * 70)
    print(f"  Entity diffs (0x{ENTITY_BASE:08X} + 0x0000 to +0x5000)")
    print("=" * 70)
    count = 0
    for off in range(0, 0x5000, 2):
        psp = ENTITY_BASE + off
        foff = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if foff + 1 >= len(data1) or foff + 1 >= len(data2):
            break
        v1 = struct.unpack_from('<H', data1, foff)[0]
        v2 = struct.unpack_from('<H', data2, foff)[0]
        if v1 != v2:
            known = " [EQUIP_ID]" if psp in KNOWN_EQUIP_ADDRS else ""
            count += 1
            if count <= 40:
                print(f"  +0x{off:04X} (0x{psp:08X}): 0x{v1:04X}/0x{v2:04X}{known}")
    print(f"  Total diffs: {count}")

    # === 8. Search broader area for ANY render-related structure ===
    # Look for diffs that contain pointer-like values (0x08-0x09 range)
    print("\n" + "=" * 70)
    print("  u32 diffs that look like pointer changes (0x08/09xxxxxx)")
    print("  in range 0x08900000-0x09A00000")
    print("=" * 70)
    count = 0
    for psp in range(0x08900000, min(0x09A00000, max_psp - 3), 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 3 >= len(data1) or off + 3 >= len(data2):
            break
        v1 = struct.unpack_from('<I', data1, off)[0]
        v2 = struct.unpack_from('<I', data2, off)[0]
        if v1 != v2:
            # Both should look like PSP pointers
            if (0x08000000 <= v1 <= 0x0A000000 and 0x08000000 <= v2 <= 0x0A000000):
                count += 1
                if count <= 50:
                    print(f"  0x{psp:08X}: 0x{v1:08X} -> 0x{v2:08X}")
    print(f"  Total pointer-like diffs: {count}")


if __name__ == '__main__':
    main()

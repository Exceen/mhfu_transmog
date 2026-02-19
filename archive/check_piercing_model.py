#!/opt/homebrew/bin/python3
"""Check the armor data table to find what model index piercings use.

Head armor data table (from MH research):
  Base: 0x001633A8 relative to user RAM (0x08800000)
  Entries: 435
  Stride: 40 bytes

  Known entries (from name table):
    52: Red Piercing
    53: Blue Piercing
    54: Yellow Piercing
    55: Black Piercing
    101: Rathalos Soul Cap (model=96)
    233: White Piercing
    251: Mafumofu Hood (model=223)
    381: Chakra Piercing
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
RAM_BASE_IN_STATE = 0x48  # State offset where PSP 0x08000000 starts


def decompress_state(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(data[0xB0:], max_output_size=128 * 1024 * 1024)


def psp_to_state(psp_addr):
    return psp_addr - 0x08000000 + RAM_BASE_IN_STATE


def main():
    data = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")

    # Head armor data table
    table_psp = 0x08800000 + 0x001633A8
    table_state = psp_to_state(table_psp)
    stride = 40
    num_entries = 435

    print(f"Head armor data table at PSP 0x{table_psp:08X}, state offset 0x{table_state:08X}")
    print(f"Stride: {stride} bytes, {num_entries} entries")

    # First, let's look at a known entry to figure out the field layout
    # Entry 101 = Rathalos Soul Cap, model = 96 (0x60)
    interesting = [
        (0, "Nothing equipped"),
        (1, "Leather Helm"),
        (52, "Red Piercing"),
        (53, "Blue Piercing"),
        (54, "Yellow Piercing"),
        (55, "Black Piercing"),
        (100, "Rathalos Soul Helm"),
        (101, "Rathalos Soul Cap"),
        (233, "White Piercing"),
        (239, "Silence Piercing"),
        (240, "Piercing of Rage"),
        (245, "Kirin Piercing"),
        (248, "Echo Piercing"),
        (251, "Mafumofu Hood"),
        (308, "Sword Saint Piercing"),
        (309, "Barrage Piercing"),
        (310, "Protection Piercing"),
        (337, "Rathalos Soul Helm Z"),
        (381, "Chakra Piercing"),
        (432, "Ambitious Piercing"),
        (433, "Comrade Piercing"),
        (434, "Hawkeye Piercing"),
    ]

    # First, dump entry 101 to understand the 40-byte structure
    print("\n=== Rathalos Soul Cap (entry 101) - full dump ===")
    off = table_state + 101 * stride
    entry_data = data[off:off + stride]
    hex_str = ' '.join(f'{b:02X}' for b in entry_data)
    print(f"  Raw: {hex_str}")

    # Show as 16-bit values
    vals_16 = [struct.unpack_from('<H', entry_data, i)[0] for i in range(0, stride, 2)]
    print(f"  u16: {vals_16}")

    # Show as 32-bit values
    vals_32 = [struct.unpack_from('<I', entry_data, i)[0] for i in range(0, stride, 4)]
    print(f"  u32: {vals_32}")

    # Show as signed 8-bit values
    vals_s8 = [struct.unpack_from('<b', entry_data, i)[0] for i in range(stride)]
    print(f"  s8:  {vals_s8}")

    # We know model=96 for entry 101. Where is 96 in the 40-byte entry?
    for i in range(stride):
        if entry_data[i] == 96:
            print(f"  Byte value 96 at offset +{i}")
    for i in range(0, stride - 1, 2):
        if struct.unpack_from('<H', entry_data, i)[0] == 96:
            print(f"  u16 value 96 at offset +{i}")

    # Also check Mafumofu Hood (entry 251, model=223)
    print("\n=== Mafumofu Hood (entry 251) - full dump ===")
    off = table_state + 251 * stride
    entry_data = data[off:off + stride]
    hex_str = ' '.join(f'{b:02X}' for b in entry_data)
    print(f"  Raw: {hex_str}")
    vals_16 = [struct.unpack_from('<H', entry_data, i)[0] for i in range(0, stride, 2)]
    print(f"  u16: {vals_16}")

    for i in range(stride):
        if entry_data[i] == 223:
            print(f"  Byte value 223 at offset +{i}")
    for i in range(0, stride - 1, 2):
        if struct.unpack_from('<H', entry_data, i)[0] == 223:
            print(f"  u16 value 223 at offset +{i}")

    # Now dump all interesting entries
    print("\n=== Comparing entries to find model index field ===")
    print(f"{'Index':>5} {'Name':<25} ", end="")
    for i in range(0, stride, 2):
        print(f"  +{i:02d}", end="")
    print()
    print("-" * 120)

    for idx, name in interesting:
        off = table_state + idx * stride
        entry_data = data[off:off + stride]
        vals = [struct.unpack_from('<H', entry_data, i)[0] for i in range(0, stride, 2)]
        print(f"{idx:5d} {name:<25} ", end="")
        for v in vals:
            print(f" {v:5d}", end="")
        print()

    # Look at entries specifically for model index field
    # Known pairs: entry 101 has model 96, entry 251 has model 223
    # entry 100 (Rathalos Soul Helm) likely has model 95 or 96 too
    # Leather Helm (entry 1) likely has model 0 or 1
    print("\n=== Looking for model index field ===")
    print("Known: entry 101 -> model 96, entry 251 -> model 223, entry 100 -> model ~95")

    # For each 16-bit field position, check if entry 101 has 96 and entry 251 has 223
    for field_offset in range(0, stride, 2):
        off101 = table_state + 101 * stride + field_offset
        off251 = table_state + 251 * stride + field_offset
        val101 = struct.unpack_from('<H', data, off101)[0]
        val251 = struct.unpack_from('<H', data, off251)[0]
        if val101 == 96 and val251 == 223:
            print(f"  ** Field at offset +{field_offset}: entry 101={val101}, entry 251={val251} -> MODEL INDEX FIELD!")

            # Now read piercing model values
            print("\n=== Piercing model values (field offset +{}) ===".format(field_offset))
            for idx, name in interesting:
                off = table_state + idx * stride + field_offset
                val = struct.unpack_from('<H', data, off)[0]
                print(f"  [{idx:3d}] {name:<25}: model = {val} (0x{val:04X})")

    # Also try byte-level for model index
    for field_offset in range(stride):
        off101 = table_state + 101 * stride + field_offset
        off251 = table_state + 251 * stride + field_offset
        val101 = data[off101]
        val251 = data[off251]
        if val101 == 96 and val251 == 223:
            print(f"\n  Byte field at offset +{field_offset}: entry 101={val101}, entry 251={val251}")


if __name__ == '__main__':
    main()

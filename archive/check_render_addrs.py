#!/opt/homebrew/bin/python3
"""Check values at rendering-related addresses in both save states."""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

def read_u16(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    if off < 0 or off + 1 >= len(data): return None
    return struct.unpack_from('<H', data, off)[0]

def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    if off < 0 or off + 3 >= len(data): return None
    return struct.unpack_from('<I', data, off)[0]

def main():
    print("Loading both save states...")
    data1 = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)
    data2 = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_1.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

    ENTITY_BASE = 0x099959A0

    print("\n=== Rendering data table (read by 0x08818F30) ===")
    for addr, label in [
        (0x089385AA, "Head equip_id table"),
        (0x089385AC, "Next slot table"),
        (0x089385AE, "Next slot table"),
        (0x089385B0, "Next slot table"),
    ]:
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        diff = "DIFF" if v1 != v2 else "same"
        print(f"  0x{addr:08X} ({label}): {v1} vs {v2} [{diff}]")

    print("\n=== Entity rendering state (written by 0x08826C3C) ===")
    for off in range(0x590, 0x5C0, 2):
        addr = ENTITY_BASE + off
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        diff = "DIFF <<<" if v1 != v2 else ""
        print(f"  +0x{off:03X} (0x{addr:08X}): {v1:5d} (0x{v1:04X}) vs {v2:5d} (0x{v2:04X}) {diff}")

    print("\n=== Entity equip copies (known) ===")
    for off, label in [(0x78, "First copy"), (0x4D8, "Second copy")]:
        for field_off, field_name in [(0, "type bytes"), (2, "equip_id"), (4, "deco1"), (6, "deco2")]:
            addr = ENTITY_BASE + off + field_off
            v1 = read_u16(data1, addr)
            v2 = read_u16(data2, addr)
            diff = "DIFF" if v1 != v2 else "same"
            print(f"  {label} +{field_off} ({field_name}) at 0x{addr:08X}: 0x{v1:04X} vs 0x{v2:04X} [{diff}]")

    print("\n=== Broader search: ALL diffs in entity 0x500-0x700 range ===")
    diff_count = 0
    for off in range(0x500, 0x700, 2):
        addr = ENTITY_BASE + off
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        if v1 is not None and v2 is not None and v1 != v2:
            diff_count += 1
            print(f"  +0x{off:03X} (0x{addr:08X}): 0x{v1:04X} ({v1}) vs 0x{v2:04X} ({v2})")
    print(f"  Total diffs in 0x500-0x700: {diff_count}")

    print("\n=== Check area around 0x08A6DD20 (referenced by rendering code) ===")
    for off in range(0, 0x20, 4):
        addr = 0x08A6DD20 + off
        v1 = read_u32(data1, addr)
        v2 = read_u32(data2, addr)
        diff = "DIFF" if v1 != v2 else ""
        if v1 is not None:
            print(f"  0x{addr:08X}: 0x{v1:08X} vs 0x{v2:08X} {diff}")

    print("\n=== Search for equip_id 102 (0x0066) as u16 in 0x0893-0x0895 area ===")
    print("  (finding all locations that store the current head equip_id)")
    count = 0
    for psp in range(0x08930000, 0x08950000, 2):
        v1 = read_u16(data1, psp)
        v2 = read_u16(data2, psp)
        if v1 is not None and v1 == 0x0066 and v2 == 0x00FC:
            count += 1
            print(f"  0x{psp:08X}: 0x{v1:04X} vs 0x{v2:04X}  <<<  equip_id location!")
    print(f"  Found {count} locations where value is 102 in state1 and 252 in state2")

    print("\n=== Search ALL RAM for rendering equip_id (102 vs 252) ===")
    print("  Range: 0x08800000-0x089F0000 (EBOOT data area)")
    count = 0
    for psp in range(0x08800000, 0x089F0000, 2):
        v1 = read_u16(data1, psp)
        v2 = read_u16(data2, psp)
        if v1 is not None and v1 == 0x0066 and v2 == 0x00FC:
            count += 1
            if count <= 30:
                # Check surrounding context
                ctx = ""
                for c_off in [-2, 2]:
                    cv1 = read_u16(data1, psp + c_off)
                    cv2 = read_u16(data2, psp + c_off)
                    if cv1 is not None:
                        ctx += f"  [+{c_off}: {cv1:04X}/{cv2:04X}]"
                print(f"  0x{psp:08X}: 102 vs 252 {ctx}")
    print(f"  Total: {count} locations")

if __name__ == '__main__':
    main()

#!/opt/homebrew/bin/python3
"""Check the validated equipment slots and all related addresses.

From code analysis:
  base = *(0x089C7508) = 0x099959A0
  $a1 = base + 0x4A0
  Head equip_id read from: $a1 + 0x3A = base + 0x4DA = 0x09995E7A
  Validated head stored to: $a1 + 0x4024 = base + 0x44C4 = 0x09999E64

Also check:
  - What gets stored in the 16420-16426 offsets
  - The equip rendering data at base + 0xA8 + equip_id*12
  - Other rendering data structures
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
RAM_BASE_IN_STATE = 0x48
PSP_RAM_START = 0x08000000

def psp_to_state(psp): return psp - PSP_RAM_START + RAM_BASE_IN_STATE
def read_u16(data, psp):
    off = psp_to_state(psp)
    if off < 0 or off + 1 >= len(data): return None
    return struct.unpack_from('<H', data, off)[0]
def read_u32(data, psp):
    off = psp_to_state(psp)
    if off < 0 or off + 3 >= len(data): return None
    return struct.unpack_from('<I', data, off)[0]

def decompress_state(filepath):
    with open(filepath, 'rb') as f:
        raw = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(raw[0xB0:], max_output_size=128 * 1024 * 1024)

def main():
    data1 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")  # Rath
    data2 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_1.ppst")  # Mafu

    base = 0x099959A0  # from *(0x089C7508)

    print("=" * 70)
    print("Structure at base = 0x099959A0 (from *(0x089C7508))")
    print("=" * 70)

    # Dump validated equip ID slots
    print("\n--- Validated equip slots (base + 0x4A0 + 0x402x) ---")
    a1_base = base + 0x4A0  # = 0x09995E40
    for name, sh_off in [("Legs", 16418), ("Head", 16420), ("Body", 16422),
                          ("Waist", 16424), ("Arm", 16426)]:
        addr = a1_base + sh_off
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        diff = " <<< DIFF" if v1 != v2 else ""
        cw = addr - 0x08800000
        print(f"  {name:5s}: PSP 0x{addr:08X} = {v1:5d} → {v2:5d}  CW: _L 0x1{cw:07X}{diff}")

    # Also check the "weapon" slot: base + 0x4A0 + 0x44C0 (= base + 0x8960?)
    # Actually check the main equip slot area
    print("\n--- Raw equip slots from base + 0x4A0 + 0x3A (head visual area) ---")
    for name, off in [("Legs", 0x2E), ("Head", 0x3A), ("Body", 0x46),
                       ("Waist", 0x52), ("Arm", 0x5E)]:
        addr = a1_base + off
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        diff = " <<< DIFF" if v1 != v2 else ""
        cw = addr - 0x08800000
        print(f"  {name:5s}: PSP 0x{addr:08X} = {v1:5d} → {v2:5d}  CW: _L 0x1{cw:07X}{diff}")

    # Check the entire validation result area
    print("\n--- Full validated area (base + 0x44C0 range) ---")
    val_base = base + 0x44C0
    for i in range(0, 20, 2):
        addr = val_base + i
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        diff = " <<< DIFF" if v1 != v2 else ""
        print(f"  PSP 0x{addr:08X} (+{i:2d}): {v1:5d} → {v2:5d}{diff}")

    # Check rendering data area at base + 0xA8
    print("\n--- Rendering data area (base + 0x80 to base + 0x120) ---")
    for i in range(0x80, 0x120, 2):
        addr = base + i
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        diff = " <<< DIFF" if v1 != v2 else ""
        if diff:
            print(f"  PSP 0x{addr:08X} (+0x{i:03X}): {v1:5d} → {v2:5d}{diff}")

    # Search the entire structure (base to base+0x10000) for ALL differences
    print("\n--- ALL u16 differences in structure (base to base+0x10000) ---")
    diff_count = 0
    for i in range(0, 0x10000, 2):
        addr = base + i
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        if v1 is None or v2 is None: break
        if v1 != v2:
            diff_count += 1
            if diff_count <= 60:
                cw = addr - 0x08800000
                print(f"  PSP 0x{addr:08X} (+0x{i:04X}): {v1:5d} → {v2:5d}  CW: _L 0x1{cw:07X}")
    print(f"  Total diffs in base-relative range: {diff_count}")

    # Also check the other known base pointer
    print("\n\n" + "=" * 70)
    print("=== Structure at 0x090AF660 (near HP) ===")
    print("=" * 70)
    hp_base = 0x090AF400
    print("\n--- ALL u16 differences near HP/equip area ---")
    for i in range(0, 0x400, 2):
        addr = hp_base + i
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        if v1 is None or v2 is None: break
        if v1 != v2:
            cw = addr - 0x08800000
            print(f"  PSP 0x{addr:08X} (+0x{i:03X}): {v1:5d} → {v2:5d}  CW: _L 0x1{cw:07X}")


if __name__ == '__main__':
    main()

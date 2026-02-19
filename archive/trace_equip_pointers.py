#!/opt/homebrew/bin/python3
"""Trace pointer chains used by the equipment/model loading code.

The equip iterator at 0x0884AEB0 loads from:
  $a0 = *(0x089C6CBC)    [player object pointer]
  $s2 = $s0 + slot*40 + 24
  equip_index = lhu $a1, 0($s2)

We need to find $s0 by tracing back through the function.

Also: the code calls jal 0x08851448 with equip_index.
Let's find what address the game ACTUALLY uses for equipment data.

And: trace all pointer chains to find the REAL equip IDs.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
RAM_BASE_IN_STATE = 0x48
PSP_RAM_START = 0x08000000

def psp_to_state(psp_addr):
    return psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE

def state_to_psp(off):
    return off - RAM_BASE_IN_STATE + PSP_RAM_START

def read_u16(data, psp):
    off = psp_to_state(psp)
    return struct.unpack_from('<H', data, off)[0]

def read_u32(data, psp):
    off = psp_to_state(psp)
    return struct.unpack_from('<I', data, off)[0]

def decompress_state(filepath):
    with open(filepath, 'rb') as f:
        raw = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(raw[0xB0:], max_output_size=128 * 1024 * 1024)

def main():
    data1 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")  # Rath Helm
    data2 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_1.ppst")  # Mafu Hood

    print(f"State 1 (Rath Helm): {len(data1)} bytes")
    print(f"State 2 (Mafu Hood): {len(data2)} bytes")

    # === 1. Follow the global pointer at 0x089C6CBC ===
    ptr1 = read_u32(data1, 0x089C6CBC)
    ptr2 = read_u32(data2, 0x089C6CBC)
    print(f"\n=== Global pointer at PSP 0x089C6CBC ===")
    print(f"  State 1: 0x{ptr1:08X}")
    print(f"  State 2: 0x{ptr2:08X}")

    # Follow other potential global pointers
    for name, addr in [
        ("0x089C7508", 0x089C7508),
        ("0x089C6CB8", 0x089C6CB8),
        ("0x08A6DD84", 0x08A6DD84),  # from 0x08A6 + offset in code
        ("0x08A6E278", 0x08A6E278),  # from lui 0x08A6, lw -7560
    ]:
        try:
            v1 = read_u32(data1, addr)
            v2 = read_u32(data2, addr)
            same = "SAME" if v1 == v2 else "DIFF"
            print(f"  {name}: 0x{v1:08X} / 0x{v2:08X} [{same}]")
        except:
            print(f"  {name}: out of range")

    # === 2. Follow pointer chain from 0x089C6CBC ===
    if ptr1 == ptr2:
        ptr = ptr1
        print(f"\n=== Following pointer chain from 0x{ptr:08X} ===")
        # Dump structure at ptr
        print(f"  First 256 bytes of object at 0x{ptr:08X}:")
        for i in range(0, 256, 16):
            vals = []
            for j in range(0, 16, 4):
                v = read_u32(data1, ptr + i + j)
                vals.append(f"{v:08X}")
            print(f"    +0x{i:03X}: {' '.join(vals)}")

        # Check if ptr+0x10 or ptr+0x14 or ptr+0x18 has equip data
        # The equip iterator uses $s0 which might be derived from this ptr
        print(f"\n  Searching for equip_id 102 (Rath) in object structure...")
        for off in range(0, 0x10000, 2):
            try:
                v1 = read_u16(data1, ptr + off)
                v2 = read_u16(data2, ptr + off)
                if v1 == 102 and v2 == 252:
                    print(f"    FOUND at ptr+0x{off:04X} (PSP 0x{ptr+off:08X}): {v1} → {v2}")
            except:
                break

        # Also search for model numbers
        print(f"\n  Searching for model index 97→223 in object structure...")
        for off in range(0, 0x10000, 2):
            try:
                v1 = read_u16(data1, ptr + off)
                v2 = read_u16(data2, ptr + off)
                if v1 == 97 and v2 == 223:
                    print(f"    FOUND at ptr+0x{off:04X} (PSP 0x{ptr+off:08X}): {v1} → {v2}")
            except:
                break

    # === 3. Search broadly for equip_id 102→252 transition ===
    # Check the FULL save state for the 102→252 transition at ALL addresses
    # (re-do more carefully)
    print(f"\n=== Comprehensive search: u16 value 102→252 ===")
    matches = []
    min_len = min(len(data1), len(data2))
    for off in range(0, min_len - 1, 2):
        v1 = struct.unpack_from('<H', data1, off)[0]
        v2 = struct.unpack_from('<H', data2, off)[0]
        if v1 == 102 and v2 == 252:
            psp = state_to_psp(off)
            matches.append(psp)
    print(f"  Found {len(matches)} locations")
    for psp in matches:
        print(f"    PSP 0x{psp:08X}")

    # === 4. Search for model 97→223 ===
    print(f"\n=== Comprehensive search: u16 value 97→223 ===")
    matches = []
    for off in range(0, min_len - 1, 2):
        v1 = struct.unpack_from('<H', data1, off)[0]
        v2 = struct.unpack_from('<H', data2, off)[0]
        if v1 == 97 and v2 == 223:
            psp = state_to_psp(off)
            matches.append(psp)
    print(f"  Found {len(matches)} locations")
    for psp in matches:
        print(f"    PSP 0x{psp:08X}")

    # === 5. Search for file ID 503→629 ===
    print(f"\n=== Comprehensive search: u16 value 503→629 ===")
    matches = []
    for off in range(0, min_len - 1, 2):
        v1 = struct.unpack_from('<H', data1, off)[0]
        v2 = struct.unpack_from('<H', data2, off)[0]
        if v1 == 503 and v2 == 629:
            psp = state_to_psp(off)
            matches.append(psp)
    print(f"  Found {len(matches)} locations")
    for psp in matches:
        print(f"    PSP 0x{psp:08X}")

    # === 6. Check if equip-ID addresses are pointer-relative ===
    # Known equip_id addresses: 0x090AF682, 0x09995A1A, 0x09995E7A
    # Check if any of these are at known ptr + known_offset
    known_equip = [0x090AF682, 0x09995A1A, 0x09995E7A]
    ptrs_to_check = [ptr1, ptr2] if ptr1 != ptr2 else [ptr1]

    # Also check pointer at 0x089C7508
    try:
        ptr7508_1 = read_u32(data1, 0x089C7508)
        ptrs_to_check.append(ptr7508_1)
    except:
        pass

    print(f"\n=== Check equip addresses relative to pointers ===")
    for p in ptrs_to_check:
        for eq in known_equip:
            diff = eq - p
            if 0 < diff < 0x100000:
                print(f"  0x{eq:08X} = ptr(0x{p:08X}) + 0x{diff:04X} ({diff})")


if __name__ == '__main__':
    main()

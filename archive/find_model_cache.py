#!/opt/homebrew/bin/python3
"""Find the actual model cache/pointer storage for head armor.

Strategy:
1. Find what the dispatch system resolves to for equip_id 102 vs 252
2. Search for those model pointers in RAM
3. Find all u32 diffs in the model cache area (0x08A00000-0x09A00000)
   that look like pointers (0x08xxxxxx or 0x09xxxxxx)
4. Focus on areas with FEW diffs (cache entries, not bulk data)
"""

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
    print(f"  State 1 (Rath Soul):  {len(data1)} bytes")
    print(f"  State 2 (Mafumofu):   {len(data2)} bytes")

    # === 1. Check model cache area at 0x08B1CDA4 ===
    print("\n" + "=" * 70)
    print("  Model cache area around 0x08B1CDA4")
    print("=" * 70)
    for off in range(-0x40, 0x80, 4):
        addr = 0x08B1CDA4 + off
        v1 = read_u32(data1, addr)
        v2 = read_u32(data2, addr)
        if v1 is not None:
            diff = " DIFF <<<" if v1 != v2 else ""
            print(f"  0x{addr:08X} (+{off:+04X}): 0x{v1:08X} vs 0x{v2:08X}{diff}")

    # === 2. Dispatch system resolution ===
    print("\n" + "=" * 70)
    print("  Dispatch system: resolve model pointers for equip 102 vs 252")
    print("=" * 70)
    ptr_table = 0x089C7510
    # Check all slots
    for slot in range(14):
        idx = slot + 2
        addr = ptr_table + idx * 4
        off1 = read_u32(data1, addr)
        off2 = read_u32(data2, addr)
        if off1 is not None:
            diff = " DIFF" if off1 != off2 else ""
            print(f"  Slot {slot:2d}: 0x{off1:08X} vs 0x{off2:08X}{diff}")

    # === 3. FUComplete lookup table results ===
    print("\n" + "=" * 70)
    print("  FUComplete lookup results for equip 102 vs 252")
    print("=" * 70)
    tables = [
        (0x089972AC, "Table A"),
        (0x08997BA8, "Table B"),
        (0x08997E6C, "Table C"),
        (0x089981D4, "Table D"),
        (0x0899851C, "Table E"),
    ]
    for tbl, name in tables:
        v102_s1 = read_u16(data1, tbl + 102 * 2)
        v252_s1 = read_u16(data1, tbl + 252 * 2)
        v102_s2 = read_u16(data2, tbl + 102 * 2)
        v252_s2 = read_u16(data2, tbl + 252 * 2)
        print(f"  {name}: [102]={v102_s1}/{v102_s2}  [252]={v252_s1}/{v252_s2}")

    # === 4. Comprehensive diff search: find model pointer diffs ===
    # Search 0x08A00000-0x09A00000 for u32 diffs that look like PSP pointers
    print("\n" + "=" * 70)
    print("  ALL u32 pointer-like diffs in 0x08A00000-0x09A00000")
    print("  (values that look like PSP addresses: 0x08xxxxxx-0x09xxxxxx)")
    print("=" * 70)

    # First, get region summary
    region_diffs = {}
    ptr_diffs = {}
    for psp in range(0x08A00000, 0x09A00000, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 3 >= len(data1) or off + 3 >= len(data2): break
        v1 = struct.unpack_from('<I', data1, off)[0]
        v2 = struct.unpack_from('<I', data2, off)[0]
        if v1 != v2:
            region = psp & 0xFFFF0000
            region_diffs[region] = region_diffs.get(region, 0) + 1
            # Check if both values look like PSP pointers
            if (0x08000000 <= v1 <= 0x0A000000) and (0x08000000 <= v2 <= 0x0A000000):
                if region not in ptr_diffs:
                    ptr_diffs[region] = []
                ptr_diffs[region].append((psp, v1, v2))

    print("\n  Region diff summary (total diffs | pointer diffs):")
    for region in sorted(region_diffs.keys()):
        total = region_diffs[region]
        ptrs = len(ptr_diffs.get(region, []))
        if ptrs > 0:
            print(f"  0x{region:08X}: {total:6d} total | {ptrs:4d} pointer diffs  <<<")
        elif total < 50:
            print(f"  0x{region:08X}: {total:6d} total")

    # Show all pointer diffs in regions with few total diffs
    print("\n  Detailed pointer diffs in regions with < 50 total diffs:")
    for region in sorted(ptr_diffs.keys()):
        total = region_diffs[region]
        if total < 50:
            print(f"\n  Region 0x{region:08X} ({total} total diffs, {len(ptr_diffs[region])} ptr diffs):")
            for addr, v1, v2 in ptr_diffs[region]:
                print(f"    0x{addr:08X}: 0x{v1:08X} -> 0x{v2:08X}")

    # === 5. Entity area: find ALL diffs in full entity structure ===
    ENTITY_BASE = 0x099959A0
    print("\n" + "=" * 70)
    print(f"  ALL diffs in full entity (0x099959A0 + 0x000 to 0xA00)")
    print("=" * 70)
    for off in range(0, 0xA00, 2):
        addr = ENTITY_BASE + off
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        if v1 is not None and v2 is not None and v1 != v2:
            # Check if it's in a known equip slot
            label = ""
            if 0x78 <= off < 0x78 + 60:
                slot = (off - 0x78) // 12
                field = (off - 0x78) % 12
                label = f" [equip_copy1 slot{slot} +{field}]"
            elif 0x4D8 <= off < 0x4D8 + 60:
                slot = (off - 0x4D8) // 12
                field = (off - 0x4D8) % 12
                label = f" [equip_copy2 slot{slot} +{field}]"
            print(f"  +0x{off:03X} (0x{addr:08X}): 0x{v1:04X} vs 0x{v2:04X}{label}")

    # === 6. Search for FUComplete-specific rendering structures ===
    # FUComplete memory is at 0x0991xxxx-0x099Bxxxx
    print("\n" + "=" * 70)
    print("  ALL diffs in FUComplete memory (0x09910000-0x099C0000)")
    print("  grouped by 4KB page")
    print("=" * 70)
    page_diffs = {}
    for psp in range(0x09910000, 0x099C0000, 2):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 1 >= len(data1) or off + 1 >= len(data2): break
        v1 = struct.unpack_from('<H', data1, off)[0]
        v2 = struct.unpack_from('<H', data2, off)[0]
        if v1 != v2:
            page = psp & 0xFFFFF000
            page_diffs[page] = page_diffs.get(page, 0) + 1

    for page in sorted(page_diffs.keys()):
        count = page_diffs[page]
        print(f"  0x{page:08X}: {count:4d} diffs")

    # Show detailed diffs for pages with < 20 diffs
    print("\n  Detailed diffs in low-count FUComplete pages:")
    for page in sorted(page_diffs.keys()):
        count = page_diffs[page]
        if count < 20:
            print(f"\n  Page 0x{page:08X} ({count} diffs):")
            for psp in range(page, page + 0x1000, 2):
                off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
                if off + 1 >= len(data1) or off + 1 >= len(data2): break
                v1 = struct.unpack_from('<H', data1, off)[0]
                v2 = struct.unpack_from('<H', data2, off)[0]
                if v1 != v2:
                    rel = psp - ENTITY_BASE
                    print(f"    0x{psp:08X} (entity+0x{rel:04X}): 0x{v1:04X} vs 0x{v2:04X}")

    # === 7. Search for model file pointers ===
    # The visual table dispatch for slot 7 gives us model offsets
    # Check what model data those resolve to
    print("\n" + "=" * 70)
    print("  Dispatch slot 7 (head model) resolution in both states")
    print("=" * 70)
    slot7_ptr_addr = ptr_table + (7 + 2) * 4
    slot7_off1 = read_u32(data1, slot7_ptr_addr)
    slot7_off2 = read_u32(data2, slot7_ptr_addr)
    print(f"  Slot 7 offset: 0x{slot7_off1:08X} / 0x{slot7_off2:08X}")

    slot7_base1 = ptr_table + slot7_off1
    slot7_base2 = ptr_table + slot7_off2
    print(f"  Slot 7 base: 0x{slot7_base1:08X} / 0x{slot7_base2:08X}")

    # What equip_id is stored in each entity?
    eid1 = read_u16(data1, ENTITY_BASE + 0x4D8 + 2)
    eid2 = read_u16(data2, ENTITY_BASE + 0x4D8 + 2)
    print(f"  Entity equip_id: {eid1} / {eid2}")

    # Resolve via slot 7 for each equip_id
    for eid, label, data, base in [
        (eid1, "State1 (Rath Soul)", data1, slot7_base1),
        (eid2, "State2 (Mafumofu)", data2, slot7_base2),
    ]:
        entry_addr = base + eid * 4
        val = read_u32(data, entry_addr)
        if val is not None and val != 0xFFFFFFFF:
            model_ptr = base + val
            print(f"  {label}: slot7[{eid}] at 0x{entry_addr:08X} = 0x{val:08X} -> model=0x{model_ptr:08X}")
            # Read first 16 bytes of model data
            for moff in range(0, 32, 4):
                mv = read_u32(data, model_ptr + moff)
                if mv is not None:
                    print(f"    model+{moff:02X}: 0x{mv:08X}")

    # === 8. Search for the loaded 3D model pointers ===
    # After model loading, the game stores loaded model file pointers somewhere
    # Search for pointer-like values that differ and point into model data areas
    print("\n" + "=" * 70)
    print("  Search for all diffs in 0x08B00000-0x08C00000 (model data area)")
    print("=" * 70)
    diff_count = 0
    for psp in range(0x08B00000, 0x08C00000, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 3 >= len(data1) or off + 3 >= len(data2): break
        v1 = struct.unpack_from('<I', data1, off)[0]
        v2 = struct.unpack_from('<I', data2, off)[0]
        if v1 != v2:
            diff_count += 1
            if diff_count <= 60:
                print(f"  0x{psp:08X}: 0x{v1:08X} vs 0x{v2:08X}")
    print(f"  Total diffs: {diff_count}")


if __name__ == '__main__':
    main()

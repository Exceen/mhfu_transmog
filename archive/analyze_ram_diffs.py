#!/opt/homebrew/bin/python3
"""Deep analysis of General RAM differences between Rath Soul and Mafumofu states.
Categorize changes by type (pointers, indices, bulk data, etc.) to find
the key model reference that controls per-frame rendering."""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
ENTITY_BASE = 0x099959A0


def load_state(slot):
    return zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_{slot}.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)


def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


def read_u16(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<H', data, off)[0]


def main():
    print("Loading save states...")
    data1 = load_state(0)  # Rath Soul
    data2 = load_state(1)  # Mafumofu

    # === 1. Scan ALL RAM for differences, categorize them ===
    print("\n=== Full RAM scan: categorizing all differences ===\n")

    # Define regions
    regions = [
        (0x08800000, 0x08960000, "EBOOT Code"),
        (0x08960000, 0x089A0000, "Data Tables (VT/FUC)"),
        (0x089A0000, 0x08A00000, "Data Region 1"),
        (0x08A00000, 0x08B00000, "General RAM 1"),
        (0x08B00000, 0x08C00000, "General RAM 2"),
        (0x08C00000, 0x09000000, "General RAM 3"),
        (0x09000000, 0x09400000, "General RAM 4"),
        (0x09400000, 0x09800000, "General RAM 5"),
        (0x09800000, 0x09990000, "Pre-Entity"),
        (0x09990000, 0x099A0000, "Entity Core"),
        (0x099A0000, 0x09A10000, "Entity Extended 1"),
        (0x09A10000, 0x0A000000, "Entity Extended 2"),
    ]

    all_diffs = []
    region_counts = {}

    for rstart, rend, rname in regions:
        count = 0
        for addr in range(rstart, rend, 4):
            off = addr - PSP_RAM_START + RAM_BASE_IN_STATE
            if off + 4 > len(data1) or off + 4 > len(data2):
                break
            v1 = read_u32(data1, addr)
            v2 = read_u32(data2, addr)
            if v1 != v2:
                all_diffs.append((addr, v1, v2))
                count += 1
        region_counts[rname] = count
        print(f"  {rname:25s} ({rstart:#010x}-{rend:#010x}): {count:>6} diffs")

    print(f"\n  Total differences: {len(all_diffs)}")

    # === 2. Categorize diffs by type ===
    print("\n=== Categorize differences by value type ===\n")

    ram_ptrs = []       # Values that look like RAM pointers (0x08-0x0A range)
    vram_ptrs = []      # Values that look like VRAM pointers (0x04xxxxxx)
    small_ints = []     # Small integer changes (both values < 1000)
    file_offsets = []   # Large values that could be file offsets
    same_diff = []      # Values where both states have the same type of value

    for addr, v1, v2 in all_diffs:
        # Check if either value is a RAM pointer
        if (0x08000000 <= v1 <= 0x0A000000 or 0x08000000 <= v2 <= 0x0A000000):
            if (0x08000000 <= v1 <= 0x0A000000 and 0x08000000 <= v2 <= 0x0A000000):
                ram_ptrs.append((addr, v1, v2))
            elif v1 == 0 or v2 == 0:
                ram_ptrs.append((addr, v1, v2))  # Pointer created/destroyed
        # VRAM pointers
        if (0x04000000 <= v1 <= 0x04400000 or 0x04000000 <= v2 <= 0x04400000):
            vram_ptrs.append((addr, v1, v2))
        # Small integers
        if v1 < 1000 and v2 < 1000:
            small_ints.append((addr, v1, v2))

    print(f"  RAM pointer-like diffs: {len(ram_ptrs)}")
    print(f"  VRAM pointer-like diffs: {len(vram_ptrs)}")
    print(f"  Small integer diffs: {len(small_ints)}")

    # === 3. Show RAM pointer diffs (most interesting) ===
    print(f"\n=== RAM pointer diffs (both values in 0x08-0x0A range) ===\n")
    for addr, v1, v2 in ram_ptrs[:50]:
        delta = v2 - v1 if v2 > v1 else v1 - v2
        region = ""
        for rstart, rend, rname in regions:
            if rstart <= addr < rend:
                region = rname
                break
        print(f"  {addr:#010x} [{region:20s}]: {v1:#010x} -> {v2:#010x} (delta={delta:#x})")

    # === 4. Show VRAM pointer diffs ===
    if vram_ptrs:
        print(f"\n=== VRAM pointer diffs ===\n")
        for addr, v1, v2 in vram_ptrs[:30]:
            print(f"  {addr:#010x}: {v1:#010x} -> {v2:#010x}")

    # === 5. Investigate what's AT the pointer targets ===
    print(f"\n=== Data at pointer targets from isolated pointer 0x08B08598 ===\n")
    ptr1 = 0x08A94FA4  # Rath Soul
    ptr2 = 0x08A968E4  # Mafumofu
    print(f"  Rath Soul pointer target: {ptr1:#010x}")
    print(f"  Mafumofu pointer target: {ptr2:#010x}")
    for label, ptr in [("Rath Soul", ptr1), ("Mafumofu", ptr2)]:
        print(f"\n  {label} ({ptr:#010x}) - first 64 bytes:")
        for i in range(0, 64, 4):
            v = read_u32(data1, ptr + i)
            print(f"    +{i:3d} ({ptr+i:#010x}): {v:#010x}")

    # === 6. Find dense clusters of small diffs that might be pointer arrays ===
    print(f"\n=== Dense clusters of pointer-like RAM diffs ===\n")
    # Group RAM pointer diffs by proximity
    if ram_ptrs:
        clusters = []
        current = [ram_ptrs[0]]
        for i in range(1, len(ram_ptrs)):
            if ram_ptrs[i][0] - ram_ptrs[i-1][0] <= 32:
                current.append(ram_ptrs[i])
            else:
                if len(current) >= 3:
                    clusters.append(current)
                current = [ram_ptrs[i]]
        if len(current) >= 3:
            clusters.append(current)

        for ci, cluster in enumerate(clusters[:10]):
            start = cluster[0][0]
            end = cluster[-1][0]
            print(f"  Cluster {ci}: {start:#010x}-{end:#010x} ({len(cluster)} ptr diffs, {end-start} bytes)")
            for addr, v1, v2 in cluster[:5]:
                print(f"    {addr:#010x}: {v1:#010x} -> {v2:#010x}")
            if len(cluster) > 5:
                print(f"    ... ({len(cluster)-5} more)")

    # === 7. Look for equip_id-related values in wider range ===
    print(f"\n=== Search for equip_id 102/252 in wider memory ===\n")
    for addr in range(0x08800000, 0x0A000000, 2):
        off = addr - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 2 > len(data1) or off + 2 > len(data2):
            break
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        if v1 == 102 and v2 == 252:
            # Check if this is in a known region
            region = "unknown"
            for rstart, rend, rname in regions:
                if rstart <= addr < rend:
                    region = rname
                    break
            print(f"  {addr:#010x} [{region}]: {v1} -> {v2}")

    # === 8. Check for GE display list pointers ===
    # PSP GE display list base addresses are typically set via sceGeListEnQueue
    # Look for changes in display list command buffers
    print(f"\n=== Search for GE command patterns (0x04xxxxxx textures) ===\n")
    for addr, v1, v2 in all_diffs:
        # GE texture address command: upper byte indicates GE command
        # texaddr0 = 0xA0, texaddr1 = 0xA8
        if (v1 >> 24) in (0xA0, 0xA8) or (v2 >> 24) in (0xA0, 0xA8):
            print(f"  {addr:#010x}: {v1:#010x} -> {v2:#010x} (possible GE tex cmd)")
        # vertex pointer: 0x12 (vaddr), 0x13 (iaddr)
        if (v1 >> 24) in (0x12, 0x13) or (v2 >> 24) in (0x12, 0x13):
            print(f"  {addr:#010x}: {v1:#010x} -> {v2:#010x} (possible GE vtx/idx cmd)")

    # === 9. Check FUComplete table values for model file refs ===
    print(f"\n=== FUComplete table values for head equip_ids 102 vs 252 ===\n")
    TABLE_A = 0x089972AC  # file_group
    TABLE_B = 0x08997BA8  # model_index
    TABLE_E = 0x0899851C  # texture

    for eid, name in [(102, "Rath Soul"), (252, "Mafumofu")]:
        a = read_u16(data1, TABLE_A + eid * 2)
        b = read_u16(data1, TABLE_B + eid * 2)
        e = read_u16(data1, TABLE_E + eid * 2)
        print(f"  {name} (eid={eid}): file_group={a}, model_index={b}, texture={e}")

    # Search for file_group values (74 and 189) in RAM
    print(f"\n  Search for file_group values 74/189 in General RAM:")
    for addr in range(0x08A00000, 0x09000000, 2):
        off = addr - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 2 > len(data1):
            break
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        if (v1 == 74 and v2 == 189) or (v1 == 189 and v2 == 74):
            print(f"    {addr:#010x}: {v1} -> {v2}")


if __name__ == '__main__':
    main()

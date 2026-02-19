import struct
import zstandard as zstd

PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

STATE_PATH = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"
MAX_RAM = 128 * 1024 * 1024  # 128 MB

def load_ram():
    with open(STATE_PATH, "rb") as f:
        raw = f.read()
    compressed = raw[0xB0:]
    dctx = zstd.ZstdDecompressor()
    decompressed = dctx.decompress(compressed, max_output_size=MAX_RAM)
    ram = decompressed[RAM_BASE_IN_STATE:]
    print(f"RAM loaded: {len(ram)} bytes ({len(ram)/1024/1024:.1f} MB)")
    return ram

def addr_to_offset(addr):
    return addr - PSP_RAM_START

def read_u16(ram, addr):
    off = addr_to_offset(addr)
    if 0 <= off < len(ram) - 1:
        return struct.unpack_from("<H", ram, off)[0]
    return None

def read_u32(ram, addr):
    off = addr_to_offset(addr)
    if 0 <= off < len(ram) - 3:
        return struct.unpack_from("<I", ram, off)[0]
    return None

def main():
    ram = load_ram()

    # =========================================================================
    # TASK 1: Search for u16 value 21 in FUComplete table area
    # =========================================================================
    print("\n" + "="*80)
    print("TASK 1: Search for u16 value 21 in 0x08997000 - 0x089A0000")
    print("="*80)

    search_start = 0x08997000
    search_end = 0x089A0000
    target = 21
    hits = []

    for addr in range(search_start, search_end, 2):
        val = read_u16(ram, addr)
        if val == target:
            prev_val = read_u16(ram, addr - 2)
            next_val = read_u16(ram, addr + 2)
            in_table = (prev_val is not None and 1 <= prev_val <= 300 and
                        next_val is not None and 1 <= next_val <= 300)
            marker = " <-- TABLE CANDIDATE" if in_table else ""
            print(f"  0x{addr:08X}: value={val}, prev={prev_val}, next={next_val}{marker}")
            hits.append((addr, in_table))

    print(f"\nTotal hits: {len(hits)}, table candidates: {sum(1 for _, t in hits if t)}")

    # =========================================================================
    # TASK 2: Search for u16 value 242 in the same range
    # =========================================================================
    print("\n" + "="*80)
    print("TASK 2: Search for u16 value 242 in 0x08997000 - 0x089A0000")
    print("="*80)

    target = 242
    hits = []

    for addr in range(search_start, search_end, 2):
        val = read_u16(ram, addr)
        if val == target:
            prev_val = read_u16(ram, addr - 2)
            next_val = read_u16(ram, addr + 2)
            in_table = (prev_val is not None and 1 <= prev_val <= 300 and
                        next_val is not None and 1 <= next_val <= 300)
            marker = " <-- TABLE CANDIDATE" if in_table else ""
            print(f"  0x{addr:08X}: value={val}, prev={prev_val}, next={next_val}{marker}")
            hits.append((addr, in_table))

    print(f"\nTotal hits: {len(hits)}, table candidates: {sum(1 for _, t in hits if t)}")

    # =========================================================================
    # TASK 3: Search EBOOT data for cluster of known weapon model IDs
    # =========================================================================
    print("\n" + "="*80)
    print("TASK 3: Search 0x08960000-0x089A0000 for tables with multiple known model IDs")
    print("="*80)

    known_models = {21, 242, 334, 541, 542, 543, 544}
    eboot_start = 0x08960000
    eboot_end = 0x089A0000
    window = 1000  # entries to check

    results = []
    # Check every 2-byte aligned address as a potential table start
    for base_addr in range(eboot_start, eboot_end, 2):
        # Count how many known model IDs appear in a window of 'window' u16 entries
        found = set()
        for i in range(window):
            val = read_u16(ram, base_addr + i * 2)
            if val in known_models:
                found.add(val)
        if len(found) >= 3:
            results.append((base_addr, found))

    # Deduplicate: only print if this is a new cluster (not within 2000 bytes of previous)
    printed = []
    for addr, found in results:
        if not printed or addr - printed[-1] > 2000:
            printed.append(addr)
            print(f"  Base 0x{addr:08X}: found {len(found)} known models: {sorted(found)}")
            # Print where each was found
            for i in range(window):
                val = read_u16(ram, addr + i * 2)
                if val in known_models:
                    print(f"    [+{i*2}] 0x{addr+i*2:08X} = {val}")

    print(f"\nTotal clusters found: {len(printed)}")

    # =========================================================================
    # TASK 4: Read full 40-byte weapon stat entries
    # =========================================================================
    print("\n" + "="*80)
    print("TASK 4: Read 40-byte entries for Sieglinde and Black Fatalis Blade")
    print("="*80)

    entries = [
        ("Sieglinde (model 21)", 0x089712AA),
        ("Black Fatalis Blade (model 242)", 0x08973AFA),
    ]

    field_values = {}
    for name, base in entries:
        print(f"\n  {name} at 0x{base:08X}:")
        vals = []
        for off in range(0, 40, 2):
            val = read_u16(ram, base + off)
            vals.append(val)
            print(f"    offset +{off:2d} (0x{base+off:08X}): {val:5d}  (0x{val:04X})")
        field_values[name] = vals

    # Compare fields
    print("\n  Field comparison (looking for model ID fields):")
    print(f"  {'Offset':>8s}  {'Sieglinde':>10s}  {'BFB':>10s}  {'Match?':>8s}")
    sieg = field_values["Sieglinde (model 21)"]
    bfb = field_values["Black Fatalis Blade (model 242)"]
    for i in range(20):
        off = i * 2
        s_val = sieg[i]
        b_val = bfb[i]
        note = ""
        if s_val == 21 and b_val == 242:
            note = " *** MODEL FIELD ***"
        elif s_val == 21:
            note = " (Sieg=21)"
        elif b_val == 242:
            note = " (BFB=242)"
        print(f"  +{off:2d}        {s_val:5d}        {b_val:5d}      {note}")

    # =========================================================================
    # TASK 5: Scan for contiguous u16 arrays of plausible model IDs
    # =========================================================================
    print("\n" + "="*80)
    print("TASK 5: Scan 0x08990000-0x089B0000 for contiguous u16 arrays (1-600)")
    print("="*80)

    scan_start = 0x08990000
    scan_end = 0x089B0000
    hit_count = 0

    for addr in range(scan_start, scan_end, 2):
        v0 = read_u16(ram, addr)
        v1 = read_u16(ram, addr + 2)
        v2 = read_u16(ram, addr + 4)
        if (v0 is not None and v1 is not None and v2 is not None and
            1 <= v0 <= 600 and 1 <= v1 <= 600 and 1 <= v2 <= 600):
            # Show a run of values
            vals = []
            for j in range(10):
                v = read_u16(ram, addr + j * 2)
                if v is not None:
                    vals.append(v)
            print(f"  0x{addr:08X}: {vals}")
            hit_count += 1
            if hit_count >= 30:
                break

    print(f"\nShowed first {hit_count} hits")

    print("\n" + "="*80)
    print("DONE")
    print("="*80)

if __name__ == "__main__":
    main()

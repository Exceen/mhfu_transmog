#!/opt/homebrew/bin/python3
"""Investigate CHEST, ARMS (Gunner), and LEGS armor table entries.

Goals:
- CHEST: Dump entries 90-110 looking for Rathalos Soul chest models (m_body092/093, f_body090/091)
- ARMS: Find the Gunner variant (expected model 90/90), check if it's at a different eid
- LEGS: Brute-force locate the legs table base and dump entries
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
ENTRY_SIZE = 40

# Known table bases
HEAD_TABLE   = 0x08960750
CHEST_TABLE  = 0x08964B70
ARMS_TABLE   = 0x08968D10
WAIST_TABLE  = 0x0896CD48

def psp_to_offset(psp_addr):
    return psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE

def load_state(slot=0):
    path = f"{STATE_DIR}/ULJM05500_1.01_{slot}.ppst"
    with open(path, 'rb') as f:
        raw = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(raw[0xB0:], max_output_size=128 * 1024 * 1024)

def read_s16(data, psp_addr):
    off = psp_to_offset(psp_addr)
    return struct.unpack_from('<h', data, off)[0]

def read_u16(data, psp_addr):
    off = psp_to_offset(psp_addr)
    return struct.unpack_from('<H', data, off)[0]

def read_u32(data, psp_addr):
    off = psp_to_offset(psp_addr)
    return struct.unpack_from('<I', data, off)[0]

def read_bytes(data, psp_addr, count):
    off = psp_to_offset(psp_addr)
    return data[off:off + count]

def dump_entries(data, table_base, eid_start, eid_end, label):
    """Dump armor table entries showing model IDs and raw hex."""
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  Table base: 0x{table_base:08X}")
    print(f"  Entries {eid_start} to {eid_end}")
    print(f"{'='*70}")
    print(f"  {'eid':>4}  {'addr':>12}  {'model_m':>8}  {'model_f':>8}  first_8_bytes_hex")
    print(f"  {'-'*4}  {'-'*12}  {'-'*8}  {'-'*8}  {'-'*24}")
    for eid in range(eid_start, eid_end + 1):
        addr = table_base + eid * ENTRY_SIZE
        model_m = read_s16(data, addr)
        model_f = read_s16(data, addr + 2)
        raw8 = read_bytes(data, addr, 8)
        print(f"  {eid:>4}  0x{addr:08X}  {model_m:>8}  {model_f:>8}  {raw8.hex()}")

def search_model_in_table(data, table_base, target_model_m, max_entries, label):
    """Search all entries in a table for a specific model_m value."""
    print(f"\n--- Searching {label} (0x{table_base:08X}) for model_m == {target_model_m} ---")
    found = []
    for eid in range(max_entries):
        addr = table_base + eid * ENTRY_SIZE
        model_m = read_s16(data, addr)
        if model_m == target_model_m:
            model_f = read_s16(data, addr + 2)
            raw8 = read_bytes(data, addr, 8)
            print(f"  FOUND at eid={eid} addr=0x{addr:08X}: model_m={model_m}, model_f={model_f}, raw={raw8.hex()}")
            found.append(eid)
    if not found:
        print(f"  Not found in entries 0-{max_entries-1}")
    return found


def main():
    print("Loading save state 0...")
    data = load_state(0)
    print(f"Decompressed: {len(data)} bytes")

    # =====================================================================
    # SECTION 1: CHEST TABLE
    # =====================================================================
    print("\n" + "#"*70)
    print("# SECTION 1: CHEST TABLE INVESTIGATION")
    print("#"*70)

    dump_entries(data, CHEST_TABLE, 90, 110, "CHEST TABLE - Entries 90-110")

    # Search for models in the Rathalos Soul range (85-100) in chest table
    print("\n--- Searching CHEST table for model_m in range 85-100 ---")
    for target in range(85, 101):
        for eid in range(0, 436):  # CHEST has ~436 entries based on spacing
            addr = CHEST_TABLE + eid * ENTRY_SIZE
            model_m = read_s16(data, addr)
            if model_m == target:
                model_f = read_s16(data, addr + 2)
                raw8 = read_bytes(data, addr, 8)
                print(f"  model_m={target}: eid={eid} addr=0x{addr:08X} model_f={model_f} raw={raw8.hex()}")

    # =====================================================================
    # SECTION 2: ARMS TABLE (looking for Gunner variant)
    # =====================================================================
    print("\n" + "#"*70)
    print("# SECTION 2: ARMS TABLE INVESTIGATION (Gunner variant)")
    print("#"*70)

    dump_entries(data, ARMS_TABLE, 90, 110, "ARMS TABLE - Entries 90-110")

    # Search for model_m == 90 across all entries
    search_model_in_table(data, ARMS_TABLE, 90, 420, "ARMS TABLE")

    # Also search for model_m == 89 to confirm BM location
    search_model_in_table(data, ARMS_TABLE, 89, 420, "ARMS TABLE")

    # =====================================================================
    # SECTION 3: LEGS TABLE INVESTIGATION
    # =====================================================================
    print("\n" + "#"*70)
    print("# SECTION 3: LEGS TABLE INVESTIGATION")
    print("#"*70)

    # Table spacing analysis
    print("\n--- Table spacing analysis ---")
    spacing_ch = CHEST_TABLE - HEAD_TABLE
    spacing_ac = ARMS_TABLE - CHEST_TABLE
    spacing_wa = WAIST_TABLE - ARMS_TABLE
    print(f"  HEAD  -> CHEST: 0x{spacing_ch:04X} = {spacing_ch} bytes / 40 = {spacing_ch // 40} entries")
    print(f"  CHEST -> ARMS:  0x{spacing_ac:04X} = {spacing_ac} bytes / 40 = {spacing_ac // 40} entries")
    print(f"  ARMS  -> WAIST: 0x{spacing_wa:04X} = {spacing_wa} bytes / 40 = {spacing_wa // 40} entries")

    avg_spacing = (spacing_ch + spacing_ac + spacing_wa) // 3
    predicted_legs = WAIST_TABLE + avg_spacing
    print(f"\n  Average spacing: 0x{avg_spacing:04X} = {avg_spacing}")
    print(f"  Predicted LEGS base (WAIST + avg): 0x{predicted_legs:08X}")

    # Also try WAIST + each individual spacing
    for label, sp in [("WAIST+CH_spacing", spacing_ch), ("WAIST+AC_spacing", spacing_ac), ("WAIST+WA_spacing", spacing_wa)]:
        pred = WAIST_TABLE + sp
        print(f"  {label}: 0x{pred:08X}")

    # Check pointer table entries around 0x08975970
    print("\n--- Pointer table entries ---")
    print("  Reading pointer table area around 0x08975970:")
    for i in range(16):
        addr = 0x08975970 + i * 4
        val = read_u32(data, addr)
        print(f"    [index={i}] 0x{addr:08X}: 0x{val:08X}", end="")
        if 0x08900000 < val < 0x09000000:
            print("  <-- looks like a valid PSP address", end="")
        print()

    # Candidate LEGS bases
    candidates = [
        0x0896DFE0,               # brute-force found model(67,67) here
        WAIST_TABLE + spacing_wa,  # WAIST + same spacing as ARMS->WAIST
        WAIST_TABLE + spacing_ac,  # WAIST + CHEST->ARMS spacing
        WAIST_TABLE + spacing_ch,  # WAIST + HEAD->CHEST spacing
        predicted_legs,            # WAIST + average spacing
        0x08970D48,               # WAIST + 0x4000
    ]
    # Remove duplicates while preserving order
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique_candidates.append(c)

    # Known addresses where model(67,67) was found
    model67_addrs = [0x08961A88, 0x089699B8, 0x0896DFE0]

    print("\n--- Model(67,67) addresses and possible eid calculations ---")
    for addr_67 in model67_addrs:
        print(f"\n  Address 0x{addr_67:08X} (model 67,67):")
        for cand_base in unique_candidates:
            offset = addr_67 - cand_base
            if offset >= 0 and offset % ENTRY_SIZE == 0:
                eid = offset // ENTRY_SIZE
                print(f"    If base=0x{cand_base:08X}: eid={eid} (offset=0x{offset:04X}={offset})")
            elif offset >= 0:
                eid_approx = offset / ENTRY_SIZE
                print(f"    If base=0x{cand_base:08X}: offset={offset}, NOT aligned (eid~={eid_approx:.2f})")
            else:
                print(f"    If base=0x{cand_base:08X}: BEFORE base (offset={offset})")

    # Also check what table each model(67,67) address falls into
    print("\n--- Which known table does each model(67,67) address fall into? ---")
    tables = [
        ("HEAD",  HEAD_TABLE,  spacing_ch // ENTRY_SIZE),
        ("CHEST", CHEST_TABLE, spacing_ac // ENTRY_SIZE),
        ("ARMS",  ARMS_TABLE,  spacing_wa // ENTRY_SIZE),
        ("WAIST", WAIST_TABLE, 450),
    ]
    for addr_67 in model67_addrs:
        for tname, tbase, max_eid in tables:
            offset = addr_67 - tbase
            if 0 <= offset < max_eid * ENTRY_SIZE and offset % ENTRY_SIZE == 0:
                eid = offset // ENTRY_SIZE
                print(f"  0x{addr_67:08X} is in {tname} table at eid={eid}")

    # Dump entries from the candidate LEGS base at 0x0896DFE0
    print("\n--- Trying LEGS base = 0x0896DFE0 ---")
    LEGS_CAND1 = 0x0896DFE0
    dump_entries(data, LEGS_CAND1, 0, 10, "LEGS candidate 0x0896DFE0 - Entries 0-10")
    dump_entries(data, LEGS_CAND1, 90, 110, "LEGS candidate 0x0896DFE0 - Entries 90-110")

    # Search for model_m == 67 in the candidate legs table
    print("\n--- Searching candidate LEGS (0x0896DFE0) for model_m == 67 ---")
    for eid in range(0, 450):
        addr = LEGS_CAND1 + eid * ENTRY_SIZE
        model_m = read_s16(data, addr)
        if model_m == 67:
            model_f = read_s16(data, addr + 2)
            raw8 = read_bytes(data, addr, 8)
            print(f"  eid={eid} addr=0x{addr:08X}: model_m={model_m}, model_f={model_f}, raw={raw8.hex()}")

    # Try different WAIST + N*40 candidates for LEGS base
    # HEAD->CHEST = 436 entries, CHEST->ARMS = 420, ARMS->WAIST = 411
    # Pattern: decreasing by ~14, ~9... next might be ~400-405 entries
    print("\n--- Trying WAIST + N*ENTRY_SIZE for various N ---")
    for n_entries in [400, 405, 410, 411, 415, 420, 436]:
        legs_base = WAIST_TABLE + n_entries * ENTRY_SIZE
        m0 = read_s16(data, legs_base)
        f0 = read_s16(data, legs_base + 2)
        m1 = read_s16(data, legs_base + ENTRY_SIZE)
        f1 = read_s16(data, legs_base + ENTRY_SIZE + 2)
        raw0 = read_bytes(data, legs_base, 8)
        raw1 = read_bytes(data, legs_base + ENTRY_SIZE, 8)
        marker = ""
        if m0 == 0 and f0 == 0:
            marker = " ** entry0=(0,0) - possible table start! **"
        print(f"  N={n_entries:>3} base=0x{legs_base:08X}: entry0=({m0},{f0}) raw={raw0.hex()}, entry1=({m1},{f1}) raw={raw1.hex()}{marker}")
        if m0 == 0 and f0 == 0:
            dump_entries(data, legs_base, 0, 5, f"LEGS candidate (WAIST+{n_entries}) - Entries 0-5")
            dump_entries(data, legs_base, 90, 110, f"LEGS candidate (WAIST+{n_entries}) - Entries 90-110")
            for eid in range(0, 400):
                a = legs_base + eid * ENTRY_SIZE
                mm = read_s16(data, a)
                if mm == 67:
                    mf = read_s16(data, a + 2)
                    print(f"    Model 67 at eid={eid}, model_f={mf}")

    # Read the pointer table entry at 0x08975970 for type2=0
    print("\n--- Reading value at 0x08975970 (pointer table entry for type2=0) ---")
    val = read_u32(data, 0x08975970)
    print(f"  0x08975970 = 0x{val:08X}")
    if 0x08900000 < val < 0x09000000:
        print(f"  This looks like a valid PSP address! Trying as table base...")
        dump_entries(data, val, 0, 5, f"Table at 0x{val:08X} - Entries 0-5")

    # Scan for table start pattern (0,0 then 1,1) between WAIST end and +0x8000
    print("\n--- Scanning for table start pattern (0,0 then 1,1) between WAIST end and +0x8000 ---")
    scan_start = WAIST_TABLE + 400 * ENTRY_SIZE
    scan_end = WAIST_TABLE + 0x8000
    found_tables = []
    for addr in range(scan_start, scan_end, 4):
        m0 = read_s16(data, addr)
        f0 = read_s16(data, addr + 2)
        m1 = read_s16(data, addr + ENTRY_SIZE)
        f1 = read_s16(data, addr + ENTRY_SIZE + 2)
        if m0 == 0 and f0 == 0 and m1 == 1 and f1 == 1:
            m2 = read_s16(data, addr + 2 * ENTRY_SIZE)
            f2 = read_s16(data, addr + 2 * ENTRY_SIZE + 2)
            print(f"  MATCH at 0x{addr:08X}: entry0=({m0},{f0}), entry1=({m1},{f1}), entry2=({m2},{f2})")
            found_tables.append(addr)
            if m2 == 2:
                print(f"    ** Strong match! This looks like a valid armor table at 0x{addr:08X} **")
                dump_entries(data, addr, 0, 5, f"Discovered table at 0x{addr:08X}")
                dump_entries(data, addr, 90, 110, f"Discovered table at 0x{addr:08X} - Entries 90-110")
                for eid in range(0, 450):
                    a = addr + eid * ENTRY_SIZE
                    mm = read_s16(data, a)
                    if mm == 67:
                        mf = read_s16(data, a + 2)
                        print(f"    Model 67 at eid={eid}, model_f={mf}")

    if not found_tables:
        print("  No (0,0)+(1,1) pattern found in scan range.")
        # Broaden scan: try just looking for (0,0) followed by small positive values
        print("\n--- Broadened scan: looking for (0,0) followed by (1,x) where x in 0-5 ---")
        for addr in range(scan_start, scan_end, 4):
            m0 = read_s16(data, addr)
            f0 = read_s16(data, addr + 2)
            m1 = read_s16(data, addr + ENTRY_SIZE)
            if m0 == 0 and f0 == 0 and m1 == 1:
                f1 = read_s16(data, addr + ENTRY_SIZE + 2)
                if 0 <= f1 <= 5:
                    m2 = read_s16(data, addr + 2 * ENTRY_SIZE)
                    f2 = read_s16(data, addr + 2 * ENTRY_SIZE + 2)
                    print(f"  Candidate at 0x{addr:08X}: e0=({m0},{f0}), e1=({m1},{f1}), e2=({m2},{f2})")

    print("\n" + "#"*70)
    print("# DONE")
    print("#"*70)


if __name__ == "__main__":
    main()

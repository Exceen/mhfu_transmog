#!/usr/bin/env python3
"""
verify_weapon_table.py - FINAL weapon table verification.

CONFIRMED FINDINGS:
- Entry size: 40 bytes (autocorrelation peak 0.483 at lag=40)
- model_id at offset +0 as u16
- Byte +2 encodes weapon category (0x07=variant_A, 0x0B=variant_B) 
- Byte +3 encodes weapon class (0x03, 0x04, 0x05, 0x07)
- Bytes +18 to +25: sharpness segments (monotonically non-decreasing)
- u32 at +6: price in zenny
- u16 at +38: related/next model_id

Two tables found:
  Table 1: 8-byte model->flags at 0x08976984 (83 entries)
  Table 2: 40-byte weapon stats - base TBD (must scan wider)
"""

import struct
import zstandard as zstd
from collections import Counter

PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
STATE_HEADER_SIZE = 0xB0
MAX_DECOMP = 128 * 1024 * 1024

STATE_PATH = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"
ENTRY_SIZE = 40

def psp_to_ram(psp_addr):
    return (psp_addr - PSP_RAM_START) + RAM_BASE_IN_STATE

def load_ram():
    print(f"Loading state: {STATE_PATH}")
    with open(STATE_PATH, "rb") as f:
        raw = f.read()
    compressed = raw[STATE_HEADER_SIZE:]
    dctx = zstd.ZstdDecompressor()
    ram = dctx.decompress(compressed, max_output_size=MAX_DECOMP)
    print(f"Decompressed: {len(ram)} bytes (0x{len(ram):X})")
    return ram

def read_bytes(ram, psp_addr, count):
    off = psp_to_ram(psp_addr)
    if off < 0 or off + count > len(ram):
        return None
    return ram[off:off+count]

def hex_line(data):
    return " ".join(f"{b:02X}" for b in data)

def is_valid_weapon_entry(data):
    """Heuristic: check if 40-byte chunk looks like a weapon entry."""
    if len(data) < 40:
        return False
    model_id = struct.unpack_from("<H", data, 0)[0]
    byte1 = data[1]  # High byte of model_id -- should be 0 for id<256, small for id<500
    byte2 = data[2]  # Weapon variant type
    byte3 = data[3]  # Weapon class
    byte4 = data[4]
    byte5 = data[5]
    
    # model_id should be 1-500
    if model_id < 1 or model_id > 500:
        return False
    # Byte +4 and +5 are always 0
    if byte4 != 0 or byte5 != 0:
        return False
    # Byte +2 should be one of the known values (3,4,5,6,7,8,9,10,11,12,13,14)
    if byte2 < 1 or byte2 > 20:
        return False
    # Byte +3 should be a small weapon class value (1-15)
    if byte3 < 1 or byte3 > 15:
        return False
    # Sharpness bytes at +18 to +24 should be monotonically non-decreasing
    sharpness = data[18:25]
    for j in range(len(sharpness) - 1):
        if sharpness[j] > sharpness[j+1]:
            return False
    return True


def main():
    ram = load_ram()

    # =========================================================================
    # STEP 1: Find all valid 40-byte weapon entries by scanning a wide region
    # =========================================================================
    print("\n" + "="*80)
    print("STEP 1: Scan region 0x0896F000 - 0x08980000 for valid 40-byte entries")
    print("="*80)
    
    # We know one entry at 0x08973AFA. Scan aligned to that.
    REF_ADDR = 0x08973AFA
    SCAN_START = 0x0896F000
    SCAN_END = 0x08980000
    
    # We need to find the correct alignment. Since we know REF_ADDR contains
    # a valid entry, all valid entries should be at REF_ADDR + N*40 for integer N
    # Alignment = REF_ADDR % 40 = 0x08973AFA % 40
    alignment = REF_ADDR % ENTRY_SIZE
    
    # Scan all aligned positions
    valid_entries = []
    first_aligned = SCAN_START + ((alignment - (SCAN_START % ENTRY_SIZE)) % ENTRY_SIZE)
    
    for addr in range(first_aligned, SCAN_END, ENTRY_SIZE):
        data = read_bytes(ram, addr, ENTRY_SIZE)
        if data and is_valid_weapon_entry(data):
            model_id = struct.unpack_from("<H", data, 0)[0]
            valid_entries.append((addr, model_id, data))
    
    print(f"Found {len(valid_entries)} valid weapon entries")
    
    if valid_entries:
        print(f"First entry: {valid_entries[0][0]:#010x} (model {valid_entries[0][1]})")
        print(f"Last entry:  {valid_entries[-1][0]:#010x} (model {valid_entries[-1][1]})")
    
    # Check for contiguous runs
    print("\n--- Contiguous runs of valid entries ---")
    runs = []
    current_run_start = None
    current_run_end = None
    for addr, mid, data in valid_entries:
        if current_run_end is None or addr == current_run_end + ENTRY_SIZE:
            if current_run_start is None:
                current_run_start = addr
            current_run_end = addr
        else:
            run_count = (current_run_end - current_run_start) // ENTRY_SIZE + 1
            runs.append((current_run_start, current_run_end, run_count))
            current_run_start = addr
            current_run_end = addr
    if current_run_start is not None:
        run_count = (current_run_end - current_run_start) // ENTRY_SIZE + 1
        runs.append((current_run_start, current_run_end, run_count))
    
    for start, end, count in runs:
        print(f"  {start:#010x} - {end:#010x}: {count} contiguous entries")
    
    # Find the largest contiguous block
    if runs:
        main_run = max(runs, key=lambda r: r[2])
        TABLE_START = main_run[0]
        TABLE_END = main_run[1] + ENTRY_SIZE
        TABLE_COUNT = main_run[2]
        print(f"\nLargest block: {TABLE_START:#010x} - {TABLE_END:#010x} ({TABLE_COUNT} entries)")
    
    # =========================================================================
    # STEP 2: Also check non-contiguous entries
    # =========================================================================
    print("\n" + "="*80)
    print("STEP 2: Check gaps between runs")
    print("="*80)
    
    for i in range(len(runs) - 1):
        end_of_prev = runs[i][1]
        start_of_next = runs[i+1][0]
        gap_bytes = start_of_next - end_of_prev - ENTRY_SIZE
        gap_entries = gap_bytes // ENTRY_SIZE
        print(f"\n  Gap: {end_of_prev + ENTRY_SIZE:#010x} - {start_of_next:#010x} "
              f"({gap_bytes} bytes = {gap_entries} entries)")
        # Show what's in the gap
        for j in range(min(3, gap_entries)):
            gap_addr = end_of_prev + ENTRY_SIZE + j * ENTRY_SIZE
            data = read_bytes(ram, gap_addr, ENTRY_SIZE)
            if data:
                mid = struct.unpack_from("<H", data, 0)[0]
                print(f"    {gap_addr:#010x}: mid={mid:4d} | {hex_line(data[:20])}...")
    
    # =========================================================================
    # STEP 3: The table might span multiple contiguous runs if there are 
    # "separator" entries. Let's merge runs that are close together.
    # =========================================================================
    print("\n" + "="*80)
    print("STEP 3: Merge nearby runs (allowing small gaps)")
    print("="*80)
    
    merged = [list(runs[0])]
    for start, end, count in runs[1:]:
        prev_end = merged[-1][1]
        gap = start - prev_end - ENTRY_SIZE
        if gap <= ENTRY_SIZE * 5:  # Allow up to 5 invalid entries gap
            merged[-1][1] = end
            merged[-1][2] = (end - merged[-1][0]) // ENTRY_SIZE + 1
        else:
            merged.append([start, end, count])
    
    for start, end, count in merged:
        actual_valid = sum(1 for a, m, d in valid_entries if start <= a <= end)
        print(f"  {start:#010x} - {end + ENTRY_SIZE:#010x}: "
              f"{(end - start) // ENTRY_SIZE + 1} slots, {actual_valid} valid")
    
    # Use the largest merged block as the table
    main_block = max(merged, key=lambda r: r[2])
    FULL_TABLE_START = main_block[0]
    FULL_TABLE_END = main_block[1] + ENTRY_SIZE
    
    # Collect all valid entries in the main block
    main_entries = [(addr, mid, data) for addr, mid, data in valid_entries 
                    if FULL_TABLE_START <= addr <= main_block[1]]
    
    print(f"\nMain table: {FULL_TABLE_START:#010x} - {FULL_TABLE_END:#010x}")
    print(f"Valid entries in main block: {len(main_entries)}")
    
    # =========================================================================
    # STEP 4: Dump all entries in the main table
    # =========================================================================
    print("\n" + "="*80)
    print("STEP 4: All weapon entries dump")
    print("="*80)
    
    print(f"\n{'#':>4} {'Addr':>12} {'MID':>4} b2 b3 {'Price':>8} | Sharp(18-25)     "
          f"{'b24':>3} {'b26':>4} | +28  +30  +32  +34 | +38  | Raw")
    
    for idx, (addr, mid, data) in enumerate(main_entries):
        byte2, byte3 = data[2], data[3]
        price = struct.unpack_from("<I", data, 6)[0]
        sharp = data[18:25]
        b24 = data[24]
        b26 = struct.unpack_from("<H", data, 26)[0]
        f28 = struct.unpack_from("<H", data, 28)[0]
        f30 = struct.unpack_from("<H", data, 30)[0]
        f32 = struct.unpack_from("<H", data, 32)[0]
        f34 = struct.unpack_from("<H", data, 34)[0]
        f38 = struct.unpack_from("<H", data, 38)[0]
        
        marker = ""
        if mid == 21: marker = " <== SIEGLINDE"
        elif mid == 242: marker = " <== BFB"
        
        print(f"{idx:4d} {addr:#010x} {mid:4d} {byte2:2d} {byte3:2d} {price:8d} | "
              f"{' '.join(f'{b:02X}' for b in sharp)} {b24:3d} {b26:4d} | "
              f"{f28:4d} {f30:4d} {f32:5d} {f34:5d} | {f38:4d} |{marker}")
    
    # =========================================================================
    # STEP 5: Search for model 21 entries everywhere
    # =========================================================================
    print("\n" + "="*80)
    print("STEP 5: Search for model_id==21 across ALL valid entries")
    print("="*80)
    
    m21 = [(a, m, d) for a, m, d in valid_entries if m == 21]
    print(f"Found {len(m21)} entries with model_id=21")
    for addr, mid, data in m21:
        print(f"  {addr:#010x}: {hex_line(data)}")
        byte2, byte3 = data[2], data[3]
        price = struct.unpack_from("<I", data, 6)[0]
        sharp = data[18:25]
        print(f"    b2={byte2} b3={byte3} price={price} sharp={list(sharp)}")
    
    # =========================================================================
    # STEP 6: If model 21 not in valid entries, do a brute force u16 scan
    # =========================================================================
    if not m21:
        print("\nModel 21 not found with validation. Doing brute-force u16==21 scan...")
        print("Checking at every aligned position in 0x08970000-0x08980000:")
        
        for addr in range(first_aligned, 0x08980000, ENTRY_SIZE):
            data = read_bytes(ram, addr, ENTRY_SIZE)
            if data:
                mid = struct.unpack_from("<H", data, 0)[0]
                if mid == 21:
                    print(f"  u16==21 at {addr:#010x}: {hex_line(data)}")
                    print(f"    is_valid_entry={is_valid_weapon_entry(data)}")
                    sharp = data[18:25]
                    print(f"    sharpness={list(sharp)} mono={all(sharp[j]<=sharp[j+1] for j in range(len(sharp)-1))}")
        
        # Also scan for u16==21 at EVERY 2-byte position (maybe alignment is different)
        print("\n  Also scanning u16==21 at every 2-byte offset in 0x08970000-0x08975000:")
        for addr in range(0x08970000, 0x08975000, 2):
            data = read_bytes(ram, addr, 2)
            if data and struct.unpack_from("<H", data, 0)[0] == 21:
                # Check if this could be a weapon entry
                entry_data = read_bytes(ram, addr, 40)
                if entry_data and is_valid_weapon_entry(entry_data):
                    print(f"  VALID entry with u16==21 at {addr:#010x}: {hex_line(entry_data)}")
                    # Check if this offset alignment differs
                    diff = addr - REF_ADDR
                    print(f"    Offset from REF_ADDR: {diff} bytes, {diff/40:.2f} entries")
    
    # =========================================================================
    # STEP 7: The u16==21 hits from earlier scan were at specific addresses.
    # Let's check those directly.
    # =========================================================================
    print("\n" + "="*80)
    print("STEP 7: Check known u16==21 hit addresses with 40-byte alignment")
    print("="*80)
    
    # From the earlier scan, u16==21 was found at:
    known_21_addrs = [0x0897318A, 0x0897336A, 0x089735EA, 0x0897363A, 
                      0x089738BA, 0x0897390A, 0x08973B3A, 0x08974E72]
    
    for hit_addr in known_21_addrs:
        # This hit has u16==21 at this address, but is it at offset+0 of an entry?
        # Check offset relative to our reference
        diff = hit_addr - REF_ADDR
        entries_off = diff / ENTRY_SIZE
        remainder = diff % ENTRY_SIZE
        print(f"\n  u16==21 at {hit_addr:#010x}: {diff:+d} bytes from REF ({entries_off:+.2f} entries, remainder={remainder})")
        
        # If remainder != 0, model_id 21 is at a different field offset in this entry
        # The entry would start at hit_addr - remainder
        if remainder < 0:
            remainder += ENTRY_SIZE
        entry_base = hit_addr - remainder
        
        print(f"    Entry would start at: {entry_base:#010x} (field offset of 21 = +{remainder})")
        entry_data = read_bytes(ram, entry_base, ENTRY_SIZE)
        if entry_data:
            print(f"    Entry data: {hex_line(entry_data)}")
            u16_0 = struct.unpack_from("<H", entry_data, 0)[0]
            print(f"    u16@+0 = {u16_0} (this is the actual model_id)")
            
            # Check: maybe 21 at this position means something else 
            # (like sharpness value, or tree link)
            print(f"    Field at +{remainder} = 21 -> this is NOT model_id, it's field +{remainder}")
    
    # =========================================================================
    # STEP 8: Hmm, model 21 appears at field offsets like +24 (b24 = sharpness sum?)
    # Let's check what field offset 24 means for model 242 entries
    # =========================================================================
    print("\n" + "="*80)
    print("STEP 8: What value is at offset +24 for entries? (from STEP 4 data)")
    print("="*80)
    
    # Offset 24 is 'b24' in our dump = the last sharpness-related byte
    # The u16==21 hits might be at THIS offset, not at offset +0
    # meaning 21 is a sharpness level or rarity, not a model_id!
    
    # Let's reconsider: maybe model 21 at the WEAPON STATS table level doesn't exist.
    # The model->flags table has 21, but the stats table uses different numbering.
    
    # Let's check: does model 21 exist as a weapon in this save state?
    # The u16==21 at 0x08973B3A: let's find what field that maps to
    hit = 0x08973B3A
    diff = hit - REF_ADDR
    remainder = diff % ENTRY_SIZE
    if remainder < 0:
        remainder += ENTRY_SIZE
    print(f"\n  0x08973B3A: field offset = +{remainder}")
    # Entry containing this address:
    entry_start = hit - remainder
    entry_data = read_bytes(ram, entry_start, ENTRY_SIZE)
    if entry_data:
        mid = struct.unpack_from("<H", entry_data, 0)[0]
        print(f"  Entry @ {entry_start:#010x}: model_id = {mid}")
        print(f"  Full: {hex_line(entry_data)}")
        # offset 24 is byte 24, which we called b24
        print(f"  Byte at +{remainder} = {entry_data[remainder]} = 0x{entry_data[remainder]:02X}")
        # Actually let's check as u16
        if remainder + 2 <= ENTRY_SIZE:
            v = struct.unpack_from("<H", entry_data, remainder)[0]
            print(f"  u16 at +{remainder} = {v}")
    
    # =========================================================================
    # STEP 9: Maybe the table has more sections or our alignment is off for 
    # earlier parts. Let's look at the u16==21 hits where model_id is at +0
    # by trying different alignments.
    # =========================================================================
    print("\n" + "="*80)
    print("STEP 9: Try alternative alignments for the weapon table")
    print("="*80)
    
    # The table might not be one giant block. Different weapon classes might
    # be in different sub-tables with different bases.
    # Let's check each u16==21 hit as a potential entry start
    
    for hit_addr in known_21_addrs:
        print(f"\n--- If entry starts at {hit_addr:#010x} (model_id=21 at +0): ---")
        data = read_bytes(ram, hit_addr, ENTRY_SIZE)
        if not data:
            continue
        print(f"  Raw: {hex_line(data)}")
        
        # Check validity
        valid = is_valid_weapon_entry(data)
        print(f"  Valid entry? {valid}")
        
        if not valid:
            # Show why not
            b2, b3, b4, b5 = data[2], data[3], data[4], data[5]
            sharp = data[18:25]
            mono = all(sharp[j] <= sharp[j+1] for j in range(len(sharp)-1))
            print(f"    b2={b2} b3={b3} b4={b4} b5={b5}")
            print(f"    sharpness={list(sharp)} mono={mono}")
        
        if valid:
            # This alignment works! Check neighbors
            print(f"  Checking neighbors:")
            for delta in [-3, -2, -1, 1, 2, 3]:
                naddr = hit_addr + delta * ENTRY_SIZE
                ndata = read_bytes(ram, naddr, ENTRY_SIZE)
                if ndata:
                    nmid = struct.unpack_from("<H", ndata, 0)[0]
                    nvalid = is_valid_weapon_entry(ndata)
                    print(f"    [{delta:+d}] {naddr:#010x}: mid={nmid:4d} valid={nvalid}")
    
    # =========================================================================
    # STEP 10: Final comprehensive scan with the correct alignment for model 21
    # =========================================================================
    print("\n" + "="*80)
    print("STEP 10: Scan multiple alignment phases")
    print("="*80)
    
    # There might be TWO weapon tables with different alignment
    # Phase 1: alignment from REF_ADDR (model 242)
    # Phase 2: alignment from 0x0897318A (model 21) if valid
    
    all_alignments = set()
    all_alignments.add(REF_ADDR % ENTRY_SIZE)
    
    for hit_addr in known_21_addrs:
        data = read_bytes(ram, hit_addr, ENTRY_SIZE)
        if data and is_valid_weapon_entry(data):
            all_alignments.add(hit_addr % ENTRY_SIZE)
    
    print(f"Alignment phases to try: {all_alignments}")
    
    all_valid = []
    for align in all_alignments:
        first = SCAN_START + ((align - (SCAN_START % ENTRY_SIZE)) % ENTRY_SIZE)
        count = 0
        for addr in range(first, SCAN_END, ENTRY_SIZE):
            data = read_bytes(ram, addr, ENTRY_SIZE)
            if data and is_valid_weapon_entry(data):
                mid = struct.unpack_from("<H", data, 0)[0]
                all_valid.append((addr, mid, data, align))
                count += 1
        print(f"  Alignment {align}: found {count} valid entries")
    
    # Deduplicate
    seen = set()
    unique_valid = []
    for addr, mid, data, align in all_valid:
        if addr not in seen:
            seen.add(addr)
            unique_valid.append((addr, mid, data, align))
    
    unique_valid.sort()
    print(f"\nTotal unique valid entries across all alignments: {len(unique_valid)}")
    
    # Find model 21 entries
    m21_final = [(a, m, d) for a, m, d, al in unique_valid if m == 21]
    m242_final = [(a, m, d) for a, m, d, al in unique_valid if m == 242]
    
    print(f"\nModel 21 entries: {len(m21_final)}")
    for addr, mid, data in m21_final:
        byte2, byte3 = data[2], data[3]
        price = struct.unpack_from("<I", data, 6)[0]
        sharp = list(data[18:25])
        f10 = struct.unpack_from("<H", data, 10)[0]
        f12 = struct.unpack_from("<H", data, 12)[0]
        f14 = struct.unpack_from("<H", data, 14)[0]
        f26 = struct.unpack_from("<H", data, 26)[0]
        f38 = struct.unpack_from("<H", data, 38)[0]
        print(f"  {addr:#010x}: b2={byte2} b3={byte3} price={price} sharp={sharp}")
        print(f"    +10={f10} +12={f12} +14={f14} +26={f26} +38={f38}")
        print(f"    {hex_line(data)}")
    
    print(f"\nModel 242 entries: {len(m242_final)}")
    for addr, mid, data in m242_final:
        byte2, byte3 = data[2], data[3]
        price = struct.unpack_from("<I", data, 6)[0]
        sharp = list(data[18:25])
        f10 = struct.unpack_from("<H", data, 10)[0]
        f26 = struct.unpack_from("<H", data, 26)[0]
        f38 = struct.unpack_from("<H", data, 38)[0]
        print(f"  {addr:#010x}: b2={byte2} b3={byte3} price={price} sharp={sharp}")
        print(f"    +10={f10} +26={f26} +38={f38}")
        print(f"    {hex_line(data)}")
    
    # =========================================================================
    # STEP 11: Model frequency table
    # =========================================================================
    print("\n" + "="*80)
    print("STEP 11: Model frequency across ALL valid entries")
    print("="*80)
    
    model_freq = Counter(m for _, m, _, _ in unique_valid)
    
    print(f"Total entries: {len(unique_valid)}")
    print(f"Unique models: {len(model_freq)}")
    
    # Models with 2+ entries (paired variant A/B entries)
    multi = {m: c for m, c in model_freq.items() if c >= 2}
    print(f"\nModels with 2+ entries ({len(multi)}):")
    for mid, cnt in sorted(multi.items()):
        print(f"  Model {mid:4d}: {cnt} entries")
    
    # Check if every model has exactly 2 entries (variant A at byte2=7, variant B at byte2=11)
    print(f"\nPair analysis (byte2=7 vs byte2=11):")
    pair_ok = 0
    pair_bad = 0
    for mid in sorted(model_freq):
        entries_for_mid = [(a, d) for a, m, d, al in unique_valid if m == mid]
        b2_vals = [d[2] for _, d in entries_for_mid]
        if sorted(b2_vals) == [7, 11]:
            pair_ok += 1
        else:
            pair_bad += 1
            if len(entries_for_mid) <= 4:
                print(f"  Model {mid}: byte2 values = {b2_vals}")
    print(f"  Models with exactly byte2=[7,11] pair: {pair_ok}")
    print(f"  Models with different pattern: {pair_bad}")

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    # Count entries by byte3 (weapon class)
    class_counts = Counter(d[3] for _, _, d, _ in unique_valid)
    print(f"\nWeapon class distribution (byte +3):")
    for cls, cnt in sorted(class_counts.items()):
        print(f"  Class {cls:2d}: {cnt:4d} entries")
    
    print(f"""
WEAPON STATS TABLE:
  Entry size: 40 bytes
  Total valid entries found: {len(unique_valid)}
  Model 21 (Sieglinde) entries: {len(m21_final)}
  Model 242 (BFB) entries: {len(m242_final)}

  Entry structure (40 bytes):
    +0:  u16 model_id  (weapon visual model PAC number)
    +2:  u8  variant    (7=variant_A, 11=variant_B -- likely low/high rank or similar)
    +3:  u8  class      (weapon type: 3-8+ = GS/LS/SnS/DB/Hammer/HH/Lance/GL/...)
    +4:  u16 zero
    +6:  u32 price      (zenny cost)
    +10: u16 stat_1     (attack-related?)
    +12: u16 stat_2     (affinity/element?)
    +14: u16 stat_3
    +16: u16 stat_4     
    +18: u8[7] sharpness segments (monotonically non-decreasing)
    +25: u8  zero
    +26: u16 sort_index (sequential within weapon class)
    +28: u16 tree_data_1
    +30: u16 tree_data_2
    +32: u16 tree_data_3
    +34: u16 tree_data_4
    +36: u16 zero
    +38: u16 related_model_id (upgrade tree link?)
""")

    print("="*80)
    print("DONE")
    print("="*80)


if __name__ == "__main__":
    main()

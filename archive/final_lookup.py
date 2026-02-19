#!/usr/bin/env python3
"""
MHFU Transmog - Final Lookup Script
Reads armor entries from PPSSPP save state to find Black and Rath Soul armor data,
then generates CWCheat lines to transmog Rath Soul -> Black appearance.
"""

import struct
import zstandard as zstandard

# === CONSTANTS ===
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
ENTRY_SIZE = 40

STATE_PATH = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"
ZSTD_SKIP = 0xB0
MAX_RAM = 128 * 1024 * 1024  # 128 MB

# === TABLE BASE ADDRESSES (PSP addresses) ===
TABLES = {
    "HEAD":  0x08960750,
    "CHEST": 0x08964B70,
    "ARMS":  0x08968D10,
    "WAIST": 0x0896CD48,
    "LEGS":  0x08970D30,
}

# === LOAD SAVE STATE ===
def load_ram():
    print(f"Loading save state: {STATE_PATH}")
    with open(STATE_PATH, "rb") as f:
        raw = f.read()
    
    compressed = raw[ZSTD_SKIP:]
    dctx = zstandard.ZstdDecompressor()
    decompressed = dctx.decompress(compressed, max_output_size=MAX_RAM)
    print(f"  Decompressed size: {len(decompressed):,} bytes ({len(decompressed)/1024/1024:.1f} MB)")
    
    # RAM starts at offset RAM_BASE_IN_STATE within decompressed data
    ram = decompressed[RAM_BASE_IN_STATE:]
    print(f"  RAM data size: {len(ram):,} bytes")
    return ram

def psp_to_ram_offset(psp_addr):
    """Convert PSP address to offset within our RAM buffer."""
    return psp_addr - PSP_RAM_START

def read_entry(ram, table_name, eid):
    """Read a single armor entry and return parsed data."""
    table_base = TABLES[table_name]
    entry_psp_addr = table_base + eid * ENTRY_SIZE
    ram_offset = psp_to_ram_offset(entry_psp_addr)
    
    entry_data = ram[ram_offset:ram_offset + ENTRY_SIZE]
    
    # Parse fields
    model_m = struct.unpack_from('<h', entry_data, 0)[0]  # s16 at +0
    model_f = struct.unpack_from('<h', entry_data, 2)[0]  # s16 at +2
    flag_byte = entry_data[4]                               # u8 at +4
    rarity = entry_data[5]                                  # u8 at +5
    raw_first8 = entry_data[:8].hex().upper()
    
    return {
        'eid': eid,
        'table': table_name,
        'psp_addr': entry_psp_addr,
        'model_m': model_m,
        'model_f': model_f,
        'flag': flag_byte,
        'rarity': rarity,
        'raw8': raw_first8,
        'entry_data': entry_data,
    }

def fmt_entry(e):
    return (f"  {e['table']:5s} eid={e['eid']:>4d}  model_m={e['model_m']:>4d}  model_f={e['model_f']:>4d}  "
            f"flag=0x{e['flag']:02X}  rarity={e['rarity']}  raw8={e['raw8']}  addr=0x{e['psp_addr']:08X}")

def cwcheat_line(entry_psp_addr, target_model_m, target_model_f):
    """Generate a CWCheat line to overwrite model_m and model_f at entry_psp_addr."""
    offset = entry_psp_addr - 0x08800000
    value = ((target_model_f & 0xFFFF) << 16) | (target_model_m & 0xFFFF)
    return f"_L 0x2{offset:07X} 0x{value:08X}"

def main():
    ram = load_ram()
    
    # =========================================================================
    # SECTION 1: BLACK ARMOR BM entries
    # =========================================================================
    print("\n" + "="*80)
    print("SECTION 1: BLACK ARMOR BM ENTRIES")
    print("="*80)
    
    bm_checks = [
        ("HEAD",  71),
        ("CHEST", 66),
        ("ARMS",  64),
        ("LEGS",  64),
    ]
    black_bm = {}
    for table, eid in bm_checks:
        e = read_entry(ram, table, eid)
        print(fmt_entry(e))
        black_bm[table] = e
    
    # =========================================================================
    # SECTION 2: BLACK ARMOR GN entries (verify)
    # =========================================================================
    print("\n" + "="*80)
    print("SECTION 2: BLACK ARMOR GN ENTRIES (verify)")
    print("="*80)
    
    gn_checks = [
        ("HEAD",  72),
        ("CHEST", 67),
        ("ARMS",  65),
        ("LEGS",  65),
    ]
    black_gn = {}
    for table, eid in gn_checks:
        e = read_entry(ram, table, eid)
        print(fmt_entry(e))
        black_gn[table] = e
    
    # =========================================================================
    # SECTION 3: RATH SOUL LEGS entries
    # =========================================================================
    print("\n" + "="*80)
    print("SECTION 3: RATH SOUL LEGS INVESTIGATION")
    print("="*80)
    
    print("\nLEGS eid=90..100:")
    for eid in range(90, 101):
        e = read_entry(ram, "LEGS", eid)
        print(fmt_entry(e))
    
    print("\nLEGS eid=110..116:")
    for eid in range(110, 117):
        e = read_entry(ram, "LEGS", eid)
        print(fmt_entry(e))
    
    print("\nLEGS eid=288 (known duplicate):")
    e = read_entry(ram, "LEGS", 288)
    print(fmt_entry(e))
    
    # =========================================================================
    # SECTION 4: ARMS Rath Soul GN investigation
    # =========================================================================
    print("\n" + "="*80)
    print("SECTION 4: ARMS RATH SOUL GN INVESTIGATION")
    print("="*80)
    
    print("\nARMS eid=99:")
    e = read_entry(ram, "ARMS", 99)
    print(fmt_entry(e))
    
    print("\nARMS eid=113..118:")
    for eid in range(113, 119):
        e = read_entry(ram, "ARMS", eid)
        print(fmt_entry(e))
    
    # =========================================================================
    # SECTION 5: CHEST Rath Soul entries expanded
    # =========================================================================
    print("\n" + "="*80)
    print("SECTION 5: CHEST RATH SOUL ENTRIES (eid=97..103)")
    print("="*80)
    
    for eid in range(97, 104):
        e = read_entry(ram, "CHEST", eid)
        print(fmt_entry(e))
    
    # =========================================================================
    # SECTION 6: COMPLETE SUMMARY
    # =========================================================================
    print("\n" + "="*80)
    print("SECTION 6: COMPLETE SUMMARY")
    print("="*80)
    
    # We need to identify the Rath Soul BM/GN entries from the dumps above.
    # Rath Soul armor typically has specific model IDs. Let's collect candidates.
    # Known: Rath Soul uses model IDs around 88-90 range.
    # We'll scan more broadly to identify them.
    
    # Let's do a broader scan for each table to find Rath Soul entries
    # by looking for entries whose names would correspond (we can't read names,
    # but we can look for model patterns consistent with Rath Soul).
    
    # From typical MHFU data:
    # Rath Soul Head BM: model ~88/89, GN: nearby
    # Let's dump HEAD eid=90..100 and eid=110..116 as well for completeness
    
    print("\n--- Additional HEAD scan (eid=90..100, 110..116) ---")
    for eid in list(range(90, 101)) + list(range(110, 117)):
        e = read_entry(ram, "HEAD", eid)
        print(fmt_entry(e))
    
    print("\n--- Additional WAIST scan (eid=90..100, 110..116) ---")
    for eid in list(range(90, 101)) + list(range(110, 117)):
        e = read_entry(ram, "WAIST", eid)
        print(fmt_entry(e))
    
    # Now let's also scan HEAD eid=96..103 for Rath Soul
    print("\n--- HEAD eid=96..103 ---")
    for eid in range(96, 104):
        e = read_entry(ram, "HEAD", eid)
        print(fmt_entry(e))
    
    # WAIST eid=96..103
    print("\n--- WAIST eid=96..103 ---")
    for eid in range(96, 104):
        e = read_entry(ram, "WAIST", eid)
        print(fmt_entry(e))
    
    # Now attempt to identify Rath Soul entries.
    # Rath Soul model IDs: head ~88, chest ~88, arms ~88/90, waist ~88, legs ~88
    # We'll look for model_m around 88-90 in the ranges we scanned.
    
    print("\n" + "="*80)
    print("IDENTIFYING RATH SOUL ENTRIES (model_m in 85..95 range)")
    print("="*80)
    
    rath_soul_candidates = {}
    for table_name in TABLES:
        candidates = []
        for eid in range(80, 300):
            try:
                e = read_entry(ram, table_name, eid)
                if 85 <= e['model_m'] <= 95 or 85 <= e['model_f'] <= 95:
                    candidates.append(e)
            except (IndexError, struct.error):
                break
        if candidates:
            rath_soul_candidates[table_name] = candidates
            print(f"\n{table_name} candidates:")
            for c in candidates:
                print(fmt_entry(c))
    
    # =========================================================================
    # Based on dump data, assemble the final mapping
    # =========================================================================
    print("\n" + "="*80)
    print("FINAL RATH SOUL + BLACK ARMOR SUMMARY")
    print("="*80)
    
    # We'll print whatever we found and then try to generate CWCheat lines.
    # The user will need to confirm the exact eids based on the dump output.
    
    # For now, let's try common MHFU Rath Soul eids and see which have
    # model values in the expected range.
    
    # Attempt to identify BM vs GN by flag byte:
    # flag & 0x01 or flag & 0x02 might distinguish BM/GN
    # Or BM comes before GN (BM at eid N, GN at eid N+1)
    
    # Let's collect all Rath Soul entries more carefully
    rath_soul_bm = {}
    rath_soul_gn = {}
    
    for table_name, candidates in rath_soul_candidates.items():
        # Group by model similarity
        for c in candidates:
            m, f = c['model_m'], c['model_f']
            flag = c['flag']
            eid = c['eid']
            
            # Rath Soul: model_m should be around 88-90
            # BM entries typically have flag with certain bits
            # GN entries have different flag bits
            # BM: flag & 0x01 == 0, GN: flag & 0x01 == 1 (or vice versa)
            # Actually in MHFU: 0x00 = BM, 0x02 = GN (or similar)
            
            # We'll just store them and let the output speak
            if m >= 85 and m <= 95:
                # Check if it's likely BM or GN
                # BM usually has flag=0x00..0x01, GN has 0x02..0x03
                if flag in (0x00, 0x01):
                    rath_soul_bm[table_name] = c
                elif flag in (0x02, 0x03):
                    rath_soul_gn[table_name] = c
                else:
                    # Just guess based on even/odd eid
                    if eid % 2 == 0:
                        if table_name not in rath_soul_bm:
                            rath_soul_bm[table_name] = c
                    else:
                        if table_name not in rath_soul_gn:
                            rath_soul_gn[table_name] = c
    
    # Print summary
    for slot in ["HEAD", "CHEST", "ARMS", "WAIST", "LEGS"]:
        print(f"\n--- {slot} ---")
        
        if slot in rath_soul_bm:
            e = rath_soul_bm[slot]
            print(f"  Rath Soul BM: eid={e['eid']}, model=({e['model_m']},{e['model_f']}), flag=0x{e['flag']:02X}, addr=0x{e['psp_addr']:08X}")
        else:
            print(f"  Rath Soul BM: NOT FOUND")
        
        if slot in rath_soul_gn:
            e = rath_soul_gn[slot]
            print(f"  Rath Soul GN: eid={e['eid']}, model=({e['model_m']},{e['model_f']}), flag=0x{e['flag']:02X}, addr=0x{e['psp_addr']:08X}")
        else:
            print(f"  Rath Soul GN: NOT FOUND")
        
        if slot in black_bm:
            e = black_bm[slot]
            print(f"  Black BM:     eid={e['eid']}, model=({e['model_m']},{e['model_f']}), flag=0x{e['flag']:02X}")
        else:
            print(f"  Black BM:     NOT FOUND")
        
        if slot in black_gn:
            e = black_gn[slot]
            print(f"  Black GN:     eid={e['eid']}, model=({e['model_m']},{e['model_f']}), flag=0x{e['flag']:02X}")
        else:
            print(f"  Black GN:     NOT FOUND")
    
    # =========================================================================
    # CWCHEAT GENERATION
    # =========================================================================
    print("\n" + "="*80)
    print("CWCHEAT LINES: Rath Soul -> Black Appearance")
    print("="*80)
    print("_S ULJM-05500")
    print("_G Monster Hunter Freedom Unite")
    print("_C0 Transmog Rath Soul to Black")
    
    for slot in ["HEAD", "CHEST", "ARMS", "WAIST", "LEGS"]:
        # BM -> BM
        if slot in rath_soul_bm and slot in black_bm:
            rs = rath_soul_bm[slot]
            bk = black_bm[slot]
            line = cwcheat_line(rs['psp_addr'], bk['model_m'], bk['model_f'])
            print(f"{line}  // {slot} BM: Rath Soul eid={rs['eid']} -> Black model ({bk['model_m']},{bk['model_f']})")
        
        # GN -> GN
        if slot in rath_soul_gn and slot in black_gn:
            rs = rath_soul_gn[slot]
            bk = black_gn[slot]
            line = cwcheat_line(rs['psp_addr'], bk['model_m'], bk['model_f'])
            print(f"{line}  // {slot} GN: Rath Soul eid={rs['eid']} -> Black model ({bk['model_m']},{bk['model_f']})")
    
    print("\n" + "="*80)
    print("DONE")
    print("="*80)

if __name__ == "__main__":
    main()

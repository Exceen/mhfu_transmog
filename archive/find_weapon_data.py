#!/usr/bin/env python3
"""
Search MHFU save state for the weapon data table.

RESULTS SUMMARY:
================
The main weapon data table is at PSP address 0x089574E8 with 24-byte entries.
It contains ~1149 entries covering ALL weapon types (not sorted by type).

Entry format (24 bytes):
  +0  u8:  unknown (weapon_type? flag?)
  +1  u8:  unknown (sub-flag?)
  +2  u16: true raw attack
  +4  u16: unknown (affinity? element data?)  
  +6  u16: unknown (element type+value?)
  +8  u16: unknown
  +10 u16: slots? flag?
  +12 u16: unknown (sharpness related?)
  +14 u16: unknown
  +16 u16: WEAPON MODEL ID (weXXX.pac)
  +18 u16: rarity (0-9)
  +20 u32: buy price in zenny

Known weapon entries:
- Model 0 (Iron Sword?): multiple entries at indices 8,9,10
- Model 21 (Sieglinde): entries at indices 33,34 and 701
  - idx 33: atk=110, rarity=2, price=6200z (early upgrade?)
  - idx 34: atk=130, rarity=4, price=16000z (mid upgrade?)
  - idx 701: atk=270, rarity=9, price=200000z (final form)
- Model 242 (BFB): entries at indices 376,419,651
  - idx 376: atk=130, rarity=4, price=30000z
  - idx 419: atk=170, rarity=7, price=200000z
  - idx 651: atk=210, rarity=9, price=300000z (final form)

NOTE: The attack values don't match expected true raw (Sieglinde=170, BFB=250).
These might be base raw values before final calculations, or the display formula
differs from what's expected.

Also found:
- 26-byte crafting/upgrade table at 0x08938D1A (~700+ entries)
  Field +18 = weapon_id, Field +22 = model-like reference, Field +24 = unknown
  
- 10-byte weapon index table at 0x089A1878 (87 entries, sequential IDs 0-86)

Known info:
- Sieglinde (Great Sword): weapon model 21 (we021.pac), file_id 3409
- Black Fatalis Blade (Great Sword): weapon model 242 (we242.pac), file_id 3630
- Armor tables: 40-byte entries at 0x08960750-0x08970D30
"""

import struct
import zstandard as zstd

# ── Config ──────────────────────────────────────────────────────────────────
SAVE_STATE = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"
HEADER_SIZE = 0xB0
RAM_OFFSET_IN_DECOMPRESSED = 0x48
PSP_RAM_START = 0x08000000

# Search range in PSP address space
SEARCH_START = 0x08800000
SEARCH_END   = 0x09200000

# Known tables to EXCLUDE
EXCLUDE_RANGES = [
    (0x08960750, 0x08960750 + 0x4000),   # HEAD armor
    (0x08964B70, 0x08964B70 + 0x4000),   # CHEST armor
    (0x08968D10, 0x08968D10 + 0x4000),   # ARMS armor
    (0x0896CD48, 0x0896CD48 + 0x4000),   # WAIST armor
    (0x08970D30, 0x08970D30 + 0x4000),   # LEGS armor
    (0x0893E7F0, 0x0893E7F0 + 0x8000),   # Model file table
    (0x089972AC, 0x089972AC + 0x2000),    # FUComplete TABLE_A
    (0x08997BA8, 0x08997BA8 + 0x2000),    # FUComplete TABLE_B
    (0x0899851C, 0x0899851C + 0x2000),    # FUComplete TABLE_E
]

SIEGLINDE_MODEL = 21
BFB_MODEL = 242
SIEGLINDE_FILE_ID = 3409
BFB_FILE_ID = 3630

def load_psp_ram():
    """Load and decompress PSP RAM from save state."""
    print(f"Loading save state: {SAVE_STATE}")
    with open(SAVE_STATE, "rb") as f:
        raw = f.read()
    
    compressed = raw[HEADER_SIZE:]
    print(f"  Raw file size: {len(raw):,} bytes")
    print(f"  Compressed payload: {len(compressed):,} bytes")
    
    dctx = zstd.ZstdDecompressor()
    decompressed = dctx.decompress(compressed, max_output_size=256 * 1024 * 1024)
    print(f"  Decompressed size: {len(decompressed):,} bytes")
    
    ram = decompressed[RAM_OFFSET_IN_DECOMPRESSED:]
    print(f"  RAM data size: {len(ram):,} bytes")
    print()
    return ram

def off(psp_addr):
    return psp_addr - PSP_RAM_START

def psp(offset):
    return offset + PSP_RAM_START

def r_u16(ram, o):
    return struct.unpack_from("<H", ram, o)[0]

def r_u32(ram, o):
    return struct.unpack_from("<I", ram, o)[0]

def r_s8(ram, o):
    return struct.unpack_from("<b", ram, o)[0]

def r_u8(ram, o):
    return ram[o]

def hex_dump(ram, psp_addr, length=64):
    """Return hex dump string of memory at given PSP address."""
    o = off(psp_addr)
    if o < 0:
        o = 0
        psp_addr = PSP_RAM_START
    data = ram[o:o+length]
    parts = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        parts.append(f"  {psp_addr+i:08X}: {hex_str:<48s} {ascii_str}")
    return "\n".join(parts)

def is_excluded(psp_addr):
    for start, end in EXCLUDE_RANGES:
        if start <= psp_addr < end:
            return True
    return False


def main():
    ram = load_psp_ram()
    ram_len = len(ram)
    max_psp = psp(ram_len)
    actual_end = min(SEARCH_END, max_psp)
    
    print(f"RAM covers PSP addresses 0x{PSP_RAM_START:08X} - 0x{max_psp:08X}")
    print(f"Search range: 0x{SEARCH_START:08X} - 0x{actual_end:08X}")
    print()

    # ══════════════════════════════════════════════════════════════════════════
    # WEAPON DATA TABLE (24-byte entries)
    # ══════════════════════════════════════════════════════════════════════════
    print("=" * 120)
    print("WEAPON DATA TABLE: 24-byte entries starting at 0x089574E8")
    print("=" * 120)
    print()
    
    WEAPON_TABLE_START = 0x089574E8
    WEAPON_ENTRY_SIZE = 24
    
    # Find table boundaries
    # Scan forward from known start
    table_start_off = off(WEAPON_TABLE_START)
    num_entries = 0
    for i in range(2000):
        o = table_start_off + i * WEAPON_ENTRY_SIZE
        if o + WEAPON_ENTRY_SIZE > ram_len:
            break
        model = r_u16(ram, o + 16)
        atk = r_u16(ram, o + 2)
        if model > 1000 or atk > 2000 or atk == 0:
            break
        num_entries = i + 1
    
    table_end_psp = WEAPON_TABLE_START + num_entries * WEAPON_ENTRY_SIZE
    print(f"Table start: 0x{WEAPON_TABLE_START:08X}")
    print(f"Table end:   0x{table_end_psp:08X}")
    print(f"Entry size:  {WEAPON_ENTRY_SIZE} bytes")
    print(f"Entries:     {num_entries}")
    print(f"Total size:  {num_entries * WEAPON_ENTRY_SIZE} bytes (0x{num_entries * WEAPON_ENTRY_SIZE:X})")
    print()
    
    # Field analysis
    print("Entry format (24 bytes):")
    print("  +0  u8:  byte_0 (weapon type? flags?)")
    print("  +1  u8:  byte_1 (sub-type? flags?)")
    print("  +2  u16: attack (true raw?)")
    print("  +4  u16: field_4 (affinity? element modifier?)")
    print("  +6  u16: field_6 (element data?)")
    print("  +8  u16: field_8")
    print("  +10 u16: field_10 (slots?)")
    print("  +12 u16: field_12 (sharpness?)")
    print("  +14 u16: field_14")
    print("  +16 u16: MODEL ID (weXXX.pac)")
    print("  +18 u16: rarity")
    print("  +20 u32: price (zenny)")
    print()
    
    # Collect entries grouped by model ID for known weapons
    print("All entries for Sieglinde (model 21) and BFB (model 242):")
    print("-" * 120)
    
    header = f"{'#':>5s} {'addr':>10s} {'b0':>3s} {'b1':>3s} {'atk':>5s} {'f4':>6s} {'f6':>6s} {'f8':>5s} {'f10':>5s} {'f12':>6s} {'f14':>5s} {'model':>5s} {'rar':>3s} {'price':>8s}"
    print(header)
    
    for i in range(num_entries):
        o = table_start_off + i * WEAPON_ENTRY_SIZE
        model = r_u16(ram, o + 16)
        if model not in [21, 242]:
            continue
        
        b0 = r_u8(ram, o)
        b1 = r_u8(ram, o + 1)
        atk = r_u16(ram, o + 2)
        f4 = r_u16(ram, o + 4)
        f6 = r_u16(ram, o + 6)
        f8 = r_u16(ram, o + 8)
        f10 = r_u16(ram, o + 10)
        f12 = r_u16(ram, o + 12)
        f14 = r_u16(ram, o + 14)
        rarity = r_u16(ram, o + 18)
        price = r_u32(ram, o + 20)
        
        name = "SIEGLINDE" if model == 21 else "BFB      "
        entry_addr = WEAPON_TABLE_START + i * WEAPON_ENTRY_SIZE
        
        # Also show raw hex
        data = ram[o:o+WEAPON_ENTRY_SIZE]
        hex_str = " ".join(f"{b:02X}" for b in data)
        
        print(f"{i:5d} 0x{entry_addr:08X} {b0:3d} {b1:3d} {atk:5d} {f4:6d} {f6:6d} {f8:5d} {f10:5d} {f12:6d} {f14:5d} {model:5d} {rarity:3d} {price:8d}  {name}")
        print(f"      Hex: {hex_str}")
    
    # Now let's try to figure out the byte-level field structure
    print()
    print("=" * 120)
    print("BYTE-LEVEL FIELD ANALYSIS")
    print("=" * 120)
    print()
    
    # Let's look at field_4 and field_6 more carefully
    # They might encode element type + element value
    # In MH: Dragon=5, Fire=1, Water=2, Thunder=3, Ice=4
    # Sieglinde has Dragon 200, BFB has Dragon 500
    
    print("Detailed byte analysis for all Sieglinde (model 21) entries:")
    for i in range(num_entries):
        o = table_start_off + i * WEAPON_ENTRY_SIZE
        model = r_u16(ram, o + 16)
        if model != 21:
            continue
        data = ram[o:o+WEAPON_ENTRY_SIZE]
        
        print(f"\n  Entry {i} @0x{WEAPON_TABLE_START + i * 24:08X}:")
        print(f"    Bytes: {' '.join(f'{b:02X}' for b in data)}")
        print(f"    Byte 0={data[0]}, Byte 1={data[1]}")
        print(f"    Atk(+2): {r_u16(ram, o+2)}")
        print(f"    Byte 4={data[4]}, Byte 5={data[5]}")
        print(f"    Byte 6={data[6]}, Byte 7={data[7]}")
        print(f"    Byte 8={data[8]}, Byte 9={data[9]}")
        print(f"    Byte 10={data[10]}, Byte 11={data[11]}")
        print(f"    Byte 12={data[12]}, Byte 13={data[13]} -> u16={r_u16(ram, o+12)} -> as bytes: 0x{data[12]:02X} 0x{data[13]:02X}")
        print(f"    Byte 14={data[14]}, Byte 15={data[15]}")
        print(f"    Model(+16): {r_u16(ram, o+16)}")
        print(f"    Rarity(+18): {r_u16(ram, o+18)}")
        print(f"    Price(+20): {r_u32(ram, o+20)}")
    
    print()
    print("Detailed byte analysis for all BFB (model 242) entries:")
    for i in range(num_entries):
        o = table_start_off + i * WEAPON_ENTRY_SIZE
        model = r_u16(ram, o + 16)
        if model != 242:
            continue
        data = ram[o:o+WEAPON_ENTRY_SIZE]
        
        print(f"\n  Entry {i} @0x{WEAPON_TABLE_START + i * 24:08X}:")
        print(f"    Bytes: {' '.join(f'{b:02X}' for b in data)}")
        print(f"    Byte 0={data[0]}, Byte 1={data[1]}")
        print(f"    Atk(+2): {r_u16(ram, o+2)}")
        print(f"    Byte 4={data[4]}, Byte 5={data[5]}")
        print(f"    Byte 6={data[6]}, Byte 7={data[7]}")
        print(f"    Byte 8={data[8]}, Byte 9={data[9]}")
        print(f"    Byte 10={data[10]}, Byte 11={data[11]}")
        print(f"    Byte 12={data[12]:02X} {data[13]:02X} -> u16={r_u16(ram, o+12)}")
        print(f"    Byte 14={data[14]}, Byte 15={data[15]}")
        print(f"    Model(+16): {r_u16(ram, o+16)}")
        print(f"    Rarity(+18): {r_u16(ram, o+18)}")
        print(f"    Price(+20): {r_u32(ram, o+20)}")

    # ══════════════════════════════════════════════════════════════════════════
    # Look at the first few entries to understand the field semantics
    # ══════════════════════════════════════════════════════════════════════════
    print()
    print("=" * 120)
    print("FIRST 80 ENTRIES (to understand field patterns)")
    print("=" * 120)
    print()
    
    print(f"{'#':>5s} {'addr':>10s} {'b0':>3s} {'b1':>3s} {'atk':>5s} {'b4':>3s} {'b5':>3s} {'b6':>3s} {'b7':>3s} {'b8':>3s} {'b9':>3s} {'b10':>3s} {'b11':>3s} {'b12':>4s} {'b13':>4s} {'b14':>3s} {'b15':>3s} {'model':>5s} {'rar':>3s} {'price':>8s}")
    print("-" * 140)
    
    for i in range(min(80, num_entries)):
        o = table_start_off + i * WEAPON_ENTRY_SIZE
        data = ram[o:o+WEAPON_ENTRY_SIZE]
        model = r_u16(ram, o + 16)
        atk = r_u16(ram, o + 2)
        rarity = r_u16(ram, o + 18)
        price = r_u32(ram, o + 20)
        entry_addr = WEAPON_TABLE_START + i * WEAPON_ENTRY_SIZE
        
        marker = ""
        if model == 21: marker = " <-- SIEG"
        elif model == 242: marker = " <-- BFB"
        elif model == 0: marker = " <-- mod0"
        elif model == 1: marker = " <-- mod1"
        
        print(f"{i:5d} 0x{entry_addr:08X} {data[0]:3d} {data[1]:3d} {atk:5d} {data[4]:3d} {data[5]:3d} {data[6]:3d} {data[7]:3d} {data[8]:3d} {data[9]:3d} {data[10]:3d} {data[11]:3d} 0x{data[12]:02X} 0x{data[13]:02X} {data[14]:3d} {data[15]:3d} {model:5d} {rarity:3d} {price:8d}{marker}")
    
    # ══════════════════════════════════════════════════════════════════════════
    # Collect statistics on byte 0 (potential weapon type indicator)
    # ══════════════════════════════════════════════════════════════════════════
    print()
    print("=" * 120)
    print("STATISTICS: Byte 0 distribution (potential weapon type)")
    print("=" * 120)
    print()
    
    from collections import Counter
    b0_counts = Counter()
    b0_model_map = {}  # b0 -> set of models
    for i in range(num_entries):
        o = table_start_off + i * WEAPON_ENTRY_SIZE
        b0 = r_u8(ram, o)
        model = r_u16(ram, o + 16)
        b0_counts[b0] += 1
        if b0 not in b0_model_map:
            b0_model_map[b0] = set()
        b0_model_map[b0].add(model)
    
    for b0_val, count in sorted(b0_counts.items()):
        models = sorted(b0_model_map[b0_val])
        model_range = f"{min(models)}-{max(models)}"
        sample = models[:5]
        has_sieg = 21 in b0_model_map[b0_val]
        has_bfb = 242 in b0_model_map[b0_val]
        markers = ""
        if has_sieg: markers += " [SIEG]"
        if has_bfb: markers += " [BFB]"
        print(f"  Byte 0 = {b0_val:3d}: {count:4d} entries, model range {model_range}, sample models: {sample}{markers}")
    
    # ══════════════════════════════════════════════════════════════════════════
    # Check byte 6 and 7 as potential element type/value
    # ══════════════════════════════════════════════════════════════════════════
    print()
    print("=" * 120)
    print("ELEMENT ANALYSIS: Checking bytes 4-9 for element encoding")
    print("=" * 120)
    print()
    
    # For Sieglinde entries (model 21): Dragon 200
    # For BFB entries (model 242): Dragon 500
    # Dragon element type in MH is typically 5
    
    print("Sieglinde entries - checking all byte values for dragon element (type=5, value=200):")
    for i in range(num_entries):
        o = table_start_off + i * WEAPON_ENTRY_SIZE
        model = r_u16(ram, o + 16)
        if model != 21:
            continue
        data = ram[o:o+WEAPON_ENTRY_SIZE]
        atk = r_u16(ram, o + 2)
        rarity = r_u16(ram, o + 18)
        print(f"  Entry {i} (atk={atk}, rar={rarity}): bytes 4-11 = {' '.join(f'{data[j]:02X}' for j in range(4, 12))}")
        # Check for value 200: could be 0xC8 as u8, or 200 as u16 (C8 00)
        for j in range(WEAPON_ENTRY_SIZE):
            if data[j] == 200:  # 0xC8
                print(f"    Byte {j} = 200 (0xC8)")
    
    print()
    print("BFB entries - checking for dragon element (type=5, value=500):")
    for i in range(num_entries):
        o = table_start_off + i * WEAPON_ENTRY_SIZE
        model = r_u16(ram, o + 16)
        if model != 242:
            continue
        data = ram[o:o+WEAPON_ENTRY_SIZE]
        atk = r_u16(ram, o + 2)
        rarity = r_u16(ram, o + 18)
        print(f"  Entry {i} (atk={atk}, rar={rarity}): bytes 4-11 = {' '.join(f'{data[j]:02X}' for j in range(4, 12))}")

    # ══════════════════════════════════════════════════════════════════════════
    # Search for file_ids in this table area
    # ══════════════════════════════════════════════════════════════════════════
    print()
    print("=" * 120)
    print("FILE_ID SEARCH in weapon table area")
    print("=" * 120)
    print()
    
    # Search for 3409 and 3630 near model entries
    for target_name, target_fid, target_model in [("Sieglinde", 3409, 21), ("BFB", 3630, 242)]:
        print(f"Searching for {target_name} file_id={target_fid} near model={target_model} entries...")
        for i in range(num_entries):
            o = table_start_off + i * WEAPON_ENTRY_SIZE
            model = r_u16(ram, o + 16)
            if model != target_model:
                continue
            # Search nearby for file_id
            for delta in range(-48, 50, 2):
                check_o = o + delta
                if check_o < 0 or check_o + 2 > ram_len:
                    continue
                val = r_u16(ram, check_o)
                if val == target_fid:
                    print(f"  Found file_id={target_fid} at entry {i} offset {delta:+d}")
    
    # ══════════════════════════════════════════════════════════════════════════
    # Summary
    # ══════════════════════════════════════════════════════════════════════════
    print()
    print("=" * 120)
    print("SUMMARY")
    print("=" * 120)
    print()
    print(f"WEAPON DATA TABLE:")
    print(f"  Address:    0x{WEAPON_TABLE_START:08X} - 0x{table_end_psp:08X}")
    print(f"  Entry size: {WEAPON_ENTRY_SIZE} bytes")
    print(f"  Entries:    {num_entries}")
    print(f"  Key field:  +16 = weapon model ID (u16)")
    print(f"  Other:      +2 = attack (u16), +18 = rarity (u16), +20 = price (u32)")
    print()
    print(f"CRAFTING TABLE:")
    print(f"  Address:    0x08938D1A")
    print(f"  Entry size: 26 bytes")
    print(f"  Key field:  +18 = weapon ID (u16)")
    print(f"  Other:      +22 = model reference, +0-+16 = crafting materials/counts")
    print()
    print(f"WEAPON INDEX TABLE:")
    print(f"  Address:    0x089A1878")
    print(f"  Entry size: 10 bytes")
    print(f"  Entries:    87 (sequential IDs 0-86)")
    print(f"  Key field:  +0 = weapon type index (u16)")


if __name__ == "__main__":
    main()

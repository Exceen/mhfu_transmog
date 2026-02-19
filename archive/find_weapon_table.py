#!/usr/bin/env python3
"""
Search for weapon data tables in MHFU PSP RAM dump (from PPSSPP save state).

Known info:
- Armor tables at HEAD=0x08960750, CHEST=0x08964B70, ARMS=0x08968D10, WAIST=0x0896CD48, LEGS=0x08970D30
- Each armor entry: 40 bytes, model_m(s16) at +0, model_f(s16) at +2
- Weapon models: Sieglinde = we021 (model 21), Black Fatalis Blade = we242 (model 242)
- Weapons use single model file (no male/female split)
"""

import struct
import zstandard as zstandard

PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
STATE_PATH = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"
MAX_RAM = 128 * 1024 * 1024  # 128 MB

# --- Load RAM from save state ---
print("Loading save state...")
with open(STATE_PATH, "rb") as f:
    raw = f.read()

# Skip 0xB0 header, then zstd decompress
compressed = raw[0xB0:]
dctx = zstandard.ZstdDecompressor()
ram = dctx.decompress(compressed, max_output_size=MAX_RAM)
print(f"RAM size: {len(ram)} bytes (0x{len(ram):X})")

def psp_to_offset(addr):
    """Convert PSP address to offset in RAM buffer."""
    return addr - PSP_RAM_START + RAM_BASE_IN_STATE

def read_u32(addr):
    off = psp_to_offset(addr)
    return struct.unpack_from("<I", ram, off)[0]

def read_s16(addr):
    off = psp_to_offset(addr)
    return struct.unpack_from("<h", ram, off)[0]

def read_u16(addr):
    off = psp_to_offset(addr)
    return struct.unpack_from("<H", ram, off)[0]

def read_bytes(addr, n):
    off = psp_to_offset(addr)
    return ram[off:off+n]


# ============================================================
# TASK 1: Brute-force search for weapon table with model 21
# ============================================================
print("\n" + "="*80)
print("TASK 1: Brute-force search for weapon tables (looking for model_id=21)")
print("="*80)

SEARCH_START = 0x08960000
SEARCH_END   = 0x089A0000
ENTRY_SIZES  = [24, 28, 32, 36, 40, 44, 48]
TARGET_MODEL = 21  # Sieglinde = we021

for entry_size in ENTRY_SIZES:
    hits = 0
    print(f"\n--- Entry size: {entry_size} bytes ---")
    for base in range(SEARCH_START, SEARCH_END, 4):
        if hits >= 20:
            break
        # For each potential equipment ID (eid) in range 10-200
        for eid in range(10, 201):
            addr = base + eid * entry_size
            # Make sure we don't read out of bounds
            if psp_to_offset(addr + entry_size) >= len(ram):
                continue
            val = read_s16(addr)
            if val != TARGET_MODEL:
                continue
            # Check neighbors: eid-1 and eid+1
            if eid < 1:
                continue
            prev_addr = base + (eid - 1) * entry_size
            next_addr = base + (eid + 1) * entry_size
            if psp_to_offset(next_addr + 2) >= len(ram):
                continue
            prev_val = read_s16(prev_addr)
            next_val = read_s16(next_addr)
            if not (1 <= prev_val <= 300 and 1 <= next_val <= 300):
                continue
            # Check 3 consecutive: eid-1, eid, eid+1 all in range
            # (eid itself is 21 which is in range, so just check prev and next)
            # Also check eid-2 or eid+2 for extra confidence
            extra_ok = 0
            if eid >= 2:
                v = read_s16(base + (eid - 2) * entry_size)
                if 1 <= v <= 300:
                    extra_ok += 1
            v2 = read_s16(base + (eid + 2) * entry_size)
            if psp_to_offset(base + (eid + 2) * entry_size + 2) < len(ram) and 1 <= v2 <= 300:
                extra_ok += 1

            print(f"  HIT: base=0x{base:08X} eid={eid:3d} "
                  f"model[eid-1]={prev_val:4d} model[eid]={val:4d} model[eid+1]={next_val:4d} "
                  f"(extra_neighbors_ok={extra_ok})")
            hits += 1
            break  # Move to next base address after finding a hit for this base
    if hits == 0:
        print("  No hits found.")


# ============================================================
# TASK 2: Check pointer table at 0x08975970
# ============================================================
print("\n" + "="*80)
print("TASK 2: Pointer table at 0x08975970 (type2 indices 0-20)")
print("="*80)

PTR_TABLE = 0x08975970
for i in range(21):
    addr = PTR_TABLE + i * 4
    ptr = read_u32(addr)
    label = ""
    if ptr == 0x08960750: label = " <-- HEAD"
    elif ptr == 0x08964B70: label = " <-- CHEST"
    elif ptr == 0x08968D10: label = " <-- ARMS"
    elif ptr == 0x0896CD48: label = " <-- WAIST"
    elif ptr == 0x08970D30: label = " <-- LEGS"
    print(f"  type2={i:2d}: ptr=0x{ptr:08X}{label}")


# ============================================================
# TASK 3: Read entries at 0x0896E098 with 28-byte entry size
# ============================================================
print("\n" + "="*80)
print("TASK 3: Entries at 0x0896E098 (28-byte entry size, first 10 entries)")
print("="*80)

TABLE_ADDR = 0x0896E098
ENTRY_SZ = 28
for i in range(10):
    addr = TABLE_ADDR + i * ENTRY_SZ
    data = read_bytes(addr, 8)
    s16_val = read_s16(addr)
    print(f"  entry[{i:2d}] @ 0x{addr:08X}: {data.hex(' ')} ...  s16@+0={s16_val}")

# Also read with different offsets for the s16
print("\n  Full first 3 entries (all 28 bytes):")
for i in range(3):
    addr = TABLE_ADDR + i * ENTRY_SZ
    data = read_bytes(addr, ENTRY_SZ)
    s16_0 = read_s16(addr)
    s16_2 = read_s16(addr + 2)
    s16_4 = read_s16(addr + 4)
    s16_6 = read_s16(addr + 6)
    print(f"  entry[{i}] @ 0x{addr:08X}: {data.hex(' ')}")
    print(f"    s16 @+0={s16_0} @+2={s16_2} @+4={s16_4} @+6={s16_6}")


# ============================================================
# TASK 4: Search after LEGS table for weapon-like sequences
# ============================================================
print("\n" + "="*80)
print("TASK 4: Search after LEGS table (0x08974000 - 0x08990000)")
print("="*80)

SCAN_START = 0x08974000
SCAN_END   = 0x08990000

for entry_size in [36, 40]:
    print(f"\n--- Scanning with entry_size={entry_size} ---")
    hits = 0
    # Slide through every 4 bytes as potential table start
    for base in range(SCAN_START, SCAN_END, 4):
        if hits >= 15:
            break
        # Check if 8 consecutive entries starting from entry 0 all have s16@+0 in range 1-300
        consecutive = 0
        vals = []
        for idx in range(20):
            a = base + idx * entry_size
            if psp_to_offset(a + 2) >= len(ram):
                break
            v = read_s16(a)
            if 1 <= v <= 300:
                consecutive += 1
                vals.append(v)
            else:
                break
        if consecutive >= 8:
            print(f"  base=0x{base:08X}: {consecutive} consecutive entries with model in 1-300")
            print(f"    first values: {vals[:15]}")
            # Check if target 21 appears
            if TARGET_MODEL in vals:
                idx21 = vals.index(TARGET_MODEL)
                print(f"    *** model 21 found at entry index {idx21}! ***")
            hits += 1

# Also try smaller entry sizes for weapons specifically
for entry_size in [20, 24, 28, 32]:
    print(f"\n--- Scanning with entry_size={entry_size} ---")
    hits = 0
    for base in range(SCAN_START, SCAN_END, 4):
        if hits >= 15:
            break
        consecutive = 0
        vals = []
        for idx in range(20):
            a = base + idx * entry_size
            if psp_to_offset(a + 2) >= len(ram):
                break
            v = read_s16(a)
            if 1 <= v <= 300:
                consecutive += 1
                vals.append(v)
            else:
                break
        if consecutive >= 8:
            print(f"  base=0x{base:08X}: {consecutive} consecutive entries with model in 1-300")
            print(f"    first values: {vals[:15]}")
            if TARGET_MODEL in vals:
                idx21 = vals.index(TARGET_MODEL)
                print(f"    *** model 21 found at entry index {idx21}! ***")
            hits += 1

print("\n" + "="*80)
print("Search complete.")
print("="*80)

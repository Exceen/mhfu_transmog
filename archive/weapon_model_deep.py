#!/usr/bin/env python3
"""
Deep investigation of weapon model loading in MHFU (FUComplete).
Examines FUComplete tables, weapon pointer tables, weapon stats entries,
and runtime equipment data to understand how weapon models are loaded.
"""

import struct
import zstandard

# Constants
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
STATE_PATH = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"
SKIP_BYTES = 0xB0
MAX_RAM = 128 * 1024 * 1024  # 128 MB

# Known addresses
TABLE_A = 0x089972AC
TABLE_B = 0x08997BA8
TABLE_E = 0x0899851C

# Load RAM from save state
def load_ram():
    with open(STATE_PATH, "rb") as f:
        raw = f.read()
    # Skip header, then decompress
    compressed = raw[SKIP_BYTES:]
    dctx = zstandard.ZstdDecompressor()
    decompressed = dctx.decompress(compressed, max_output_size=MAX_RAM)
    # RAM starts at offset RAM_BASE_IN_STATE
    ram = decompressed[RAM_BASE_IN_STATE:]
    print(f"RAM loaded: {len(ram)} bytes ({len(ram)/1024/1024:.1f} MB)")
    return ram

def psp_to_offset(addr):
    return addr - PSP_RAM_START

def read_u8(ram, addr):
    off = psp_to_offset(addr)
    return ram[off]

def read_u16(ram, addr):
    off = psp_to_offset(addr)
    return struct.unpack_from("<H", ram, off)[0]

def read_s16(ram, addr):
    off = psp_to_offset(addr)
    return struct.unpack_from("<h", ram, off)[0]

def read_u32(ram, addr):
    off = psp_to_offset(addr)
    return struct.unpack_from("<I", ram, off)[0]

def read_bytes(ram, addr, n):
    off = psp_to_offset(addr)
    return ram[off:off+n]

# ============================================================
# TASK 1: Check FUComplete tables for weapon entries
# ============================================================
def task1(ram):
    print("=" * 80)
    print("TASK 1: Search FUComplete tables for weapon model IDs")
    print("=" * 80)
    
    tables = {
        "TABLE_A": TABLE_A,
        "TABLE_B": TABLE_B,
        "TABLE_E": TABLE_E,
    }
    
    search_values = {21: "Sieglinde model", 242: "BFB model"}
    max_index = 2000
    
    for tname, tbase in tables.items():
        print(f"\n--- {tname} at 0x{tbase:08X} ---")
        for idx in range(max_index):
            addr = tbase + idx * 2
            try:
                val = read_u16(ram, addr)
            except (IndexError, struct.error):
                print(f"  [Stopped at index {idx} - out of range]")
                break
            
            if val in search_values:
                # Get neighbors
                prev_val = read_u16(ram, addr - 2) if idx > 0 else None
                next_val = read_u16(ram, addr + 2) if idx < max_index - 1 else None
                prev_str = f"{prev_val}" if prev_val is not None else "N/A"
                next_str = f"{next_val}" if next_val is not None else "N/A"
                print(f"  FOUND: index={idx}, value={val} ({search_values[val]}), "
                      f"addr=0x{addr:08X}, prev={prev_str}, next={next_str}")
        
        # Also print size info: how many entries until we hit the next table
        sorted_bases = sorted(tables.values())
        tidx = sorted_bases.index(tbase)
        if tidx < len(sorted_bases) - 1:
            next_base = sorted_bases[tidx + 1]
            entry_count = (next_base - tbase) // 2
            print(f"  Max entries before next table: {entry_count}")
        else:
            print(f"  (Last table, unknown end)")

# ============================================================
# TASK 2: Check for weapon pointer table after armor pointer table
# ============================================================
def task2(ram):
    print("\n" + "=" * 80)
    print("TASK 2: Search for weapon pointer table after armor pointer table (0x08975970)")
    print("=" * 80)
    
    # First, print the known armor pointer table entries
    print("\n--- Known armor pointer table entries (0x08975970+) ---")
    for i in range(40):  # Read 40 u32 entries
        addr = 0x08975970 + i * 4
        if addr >= 0x08976000:
            break
        val = read_u32(ram, addr)
        is_ptr = 0x08800000 <= val <= 0x08A00000
        marker = " <-- VALID PSP PTR" if is_ptr else ""
        if is_ptr:
            # Check what's at the pointed-to address
            first_u16 = read_u16(ram, val)
            print(f"  [{i:2d}] 0x{addr:08X}: 0x{val:08X}{marker} -> first u16={first_u16}")
        else:
            print(f"  [{i:2d}] 0x{addr:08X}: 0x{val:08X}{marker}")
    
    # Extend search further
    print("\n--- Extended search 0x08976000 to 0x08976100 ---")
    for i in range(64):
        addr = 0x08976000 + i * 4
        val = read_u32(ram, addr)
        is_ptr = 0x08800000 <= val <= 0x08A00000
        if is_ptr:
            first_u16 = read_u16(ram, val)
            print(f"  0x{addr:08X}: 0x{val:08X} <-- VALID PSP PTR -> first u16={first_u16}")
        elif val != 0:
            print(f"  0x{addr:08X}: 0x{val:08X}")

# ============================================================
# TASK 3: Find all weapon entries with byte+3 == 2 (Great Sword type?)
# ============================================================
def task3(ram):
    print("\n" + "=" * 80)
    print("TASK 3: Find all 40-byte weapon entries with byte+3 == 2 (Great Sword category)")
    print("=" * 80)
    
    ENTRY_SIZE = 40
    KNOWN_ENTRY = 0x089712AA  # Sieglinde stats entry
    
    # First, let's see what's at the known entry
    print(f"\n--- Sieglinde entry at 0x{KNOWN_ENTRY:08X} ---")
    data = read_bytes(ram, KNOWN_ENTRY, ENTRY_SIZE)
    print(f"  Raw bytes: {data.hex()}")
    print(f"  u16 at +0 (model_id?): {struct.unpack_from('<H', data, 0)[0]}")
    print(f"  byte at +2: {data[2]}")
    print(f"  byte at +3: {data[3]}")
    print(f"  u16 at +2: {struct.unpack_from('<H', data, 2)[0]}")
    print(f"  u16 at +4: {struct.unpack_from('<H', data, 4)[0]}")
    
    # Find the first entry by going backwards from Sieglinde
    # Calculate how many entries back to reach 0x0896F000
    entries_back = (KNOWN_ENTRY - 0x0896F000) // ENTRY_SIZE
    start_addr = KNOWN_ENTRY - entries_back * ENTRY_SIZE
    
    # Calculate forward to 0x08975000
    entries_forward = (0x08975000 - KNOWN_ENTRY) // ENTRY_SIZE
    end_addr = KNOWN_ENTRY + entries_forward * ENTRY_SIZE
    
    print(f"\nScanning from 0x{start_addr:08X} to 0x{end_addr:08X}")
    print(f"Total entries to scan: {(end_addr - start_addr) // ENTRY_SIZE}")
    
    # Find all with byte+3 == 2
    gs_entries = []
    addr = start_addr
    entry_idx = 0
    while addr < end_addr:
        try:
            data = read_bytes(ram, addr, ENTRY_SIZE)
            b3 = data[3]
            if b3 == 2:
                model_id = struct.unpack_from('<H', data, 0)[0]
                gs_entries.append((addr, model_id, entry_idx))
        except (IndexError, struct.error):
            break
        addr += ENTRY_SIZE
        entry_idx += 1
    
    print(f"\nFound {len(gs_entries)} entries with byte+3 == 2:")
    # Print first 30
    for i, (addr, mid, eidx) in enumerate(gs_entries[:30]):
        marker = " <-- SIEGLINDE" if addr == KNOWN_ENTRY else ""
        data = read_bytes(ram, addr, 8)
        print(f"  #{i:3d}: addr=0x{addr:08X}, entry_idx={eidx:4d}, "
              f"model_id={mid:5d}, first8={data.hex()}{marker}")
    
    if len(gs_entries) > 30:
        print(f"  ... and {len(gs_entries) - 30} more entries")
    
    # Also print a summary of ALL unique byte+3 values to understand weapon types
    print("\n--- Distribution of byte+3 values across all entries ---")
    type_counts = {}
    addr = start_addr
    while addr < end_addr:
        try:
            data = read_bytes(ram, addr, ENTRY_SIZE)
            b3 = data[3]
            if b3 not in type_counts:
                type_counts[b3] = 0
            type_counts[b3] += 1
        except:
            break
        addr += ENTRY_SIZE
    
    for t in sorted(type_counts.keys()):
        print(f"  byte+3={t:3d}: {type_counts[t]} entries")

# ============================================================
# TASK 4: Try different entry sizes around model_id=21 address
# ============================================================
def task4(ram):
    print("\n" + "=" * 80)
    print("TASK 4: Test different entry sizes around 0x089712AA")
    print("=" * 80)
    
    KNOWN_ADDR = 0x089712AA  # address where model_id=21 lives
    
    for entry_size in [32, 36, 40, 44, 48]:
        print(f"\n--- Entry size: {entry_size} bytes ---")
        # For each entry size, show a few entries before and after
        for delta in range(-3, 4):
            addr = KNOWN_ADDR + delta * entry_size
            try:
                model_id = read_u16(ram, addr)
                byte2 = read_u8(ram, addr + 2)
                byte3 = read_u8(ram, addr + 3)
                u16_2 = read_u16(ram, addr + 2)
                data = read_bytes(ram, addr, min(entry_size, 16))
                marker = " <-- KNOWN" if delta == 0 else ""
                print(f"  delta={delta:+d}: addr=0x{addr:08X}, u16[0]={model_id:5d}, "
                      f"u16[1]={u16_2:5d}, first_bytes={data.hex()}{marker}")
            except:
                print(f"  delta={delta:+d}: addr=0x{addr:08X}, OUT OF RANGE")

# ============================================================
# TASK 5: Search runtime equipment data near 0x08A35890
# ============================================================
def task5(ram):
    print("\n" + "=" * 80)
    print("TASK 5: Runtime equipment data near player structure")
    print("=" * 80)
    
    # Print u16 values in the vicinity
    print("\n--- u16 values from 0x08A35800 to 0x08A35940 (non-zero only) ---")
    for i in range(0, 0x140, 2):
        addr = 0x08A35800 + i
        try:
            val = read_u16(ram, addr)
            # Mark interesting values
            markers = []
            if val == 21:
                markers.append("Sieglinde model")
            if val == 242:
                markers.append("BFB model")
            if addr == 0x08A35890:
                markers.append("HEAD_MODEL_RUNTIME")
            marker_str = f"  <-- {', '.join(markers)}" if markers else ""
            if val != 0 or marker_str:  # Only print non-zero or marked
                print(f"  0x{addr:08X}: {val:5d} (0x{val:04X}){marker_str}")
        except:
            pass
    
    # Also search a wider range for value 21 specifically
    print("\n--- Search 0x08A30000-0x08A40000 for u16 value 21 ---")
    for i in range(0, 0x10000, 2):
        addr = 0x08A30000 + i
        try:
            val = read_u16(ram, addr)
            if val == 21:
                # Print context
                ctx_vals = []
                for d in range(-4, 5):
                    cv = read_u16(ram, addr + d * 2)
                    ctx_vals.append(f"{cv}")
                print(f"  0x{addr:08X}: 21 | context: [{', '.join(ctx_vals)}]")
        except:
            pass
    
    # Search for the currently equipped weapon equip_id
    # The weapon equip_id is likely a small number (0-2000ish)
    # Let's also look at what's near the head model runtime address
    print("\n--- Detailed dump around 0x08A35880-0x08A358C0 (u32 view) ---")
    for i in range(0, 0x40, 4):
        addr = 0x08A35880 + i
        try:
            val_u32 = read_u32(ram, addr)
            val_u16_lo = read_u16(ram, addr)
            val_u16_hi = read_u16(ram, addr + 2)
            is_ptr = 0x08800000 <= val_u32 <= 0x08A00000
            marker = " <-- PTR" if is_ptr else ""
            print(f"  0x{addr:08X}: u32=0x{val_u32:08X}, u16=[{val_u16_lo:5d}, {val_u16_hi:5d}]{marker}")
        except:
            pass
    
    # Search for weapon equip slot data - might be near other equipment slots
    # In MH games, equipment data is often stored together
    # The head model was at 0x08A35890. Let's check what's at regular offsets before/after
    print("\n--- Equipment slot search: checking offsets from 0x08A35890 ---")
    for offset in range(-0x100, 0x100, 4):
        addr = 0x08A35890 + offset
        try:
            val = read_u32(ram, addr)
            u16_lo = val & 0xFFFF
            u16_hi = (val >> 16) & 0xFFFF
            # Flag if either u16 matches known model IDs
            flags = []
            if u16_lo == 21 or u16_hi == 21:
                flags.append("has 21 (Sieglinde)")
            if u16_lo == 242 or u16_hi == 242:
                flags.append("has 242 (BFB)")
            if 0x08800000 <= val <= 0x08A00000:
                flags.append("PSP PTR")
            if flags:
                print(f"  0x{addr:08X} (offset {offset:+5d}): u32=0x{val:08X}, "
                      f"u16=[{u16_lo}, {u16_hi}] | {', '.join(flags)}")
        except:
            pass

# ============================================================
# MAIN
# ============================================================
def main():
    ram = load_ram()
    task1(ram)
    task2(ram)
    task3(ram)
    task4(ram)
    task5(ram)

if __name__ == "__main__":
    main()

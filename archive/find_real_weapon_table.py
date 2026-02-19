#!/usr/bin/env python3
"""
Search for real weapon table in MHFU save state, excluding known armor table regions.
"""

import struct
import zstandard as zstd

# Constants
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
STATE_PATH = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"
MAX_DECOMPRESS = 128 * 1024 * 1024  # 128 MB
SKIP_HEADER = 0xB0

# Known armor table regions to EXCLUDE
ARMOR_TABLES = [
    (0x08960750, 0x089645D0, "HEAD"),
    (0x08964B70, 0x089689F0, "CHEST"),
    (0x08968D10, 0x0896CB90, "ARMS"),
    (0x0896CD48, 0x08970BC8, "WAIST"),
    (0x08970D30, 0x08974BB0, "LEGS"),
]

def in_armor_table(psp_addr):
    for start, end, name in ARMOR_TABLES:
        if start <= psp_addr < end:
            return name
    return None

def psp_addr_to_offset(psp_addr):
    return (psp_addr - PSP_RAM_START) + RAM_BASE_IN_STATE

def offset_to_psp_addr(offset):
    return (offset - RAM_BASE_IN_STATE) + PSP_RAM_START

def read_u16(data, offset):
    if offset < 0 or offset + 2 > len(data):
        return None
    return struct.unpack_from('<H', data, offset)[0]

def load_state():
    print(f"Loading state from: {STATE_PATH}")
    with open(STATE_PATH, 'rb') as f:
        raw = f.read()
    print(f"  Raw file size: {len(raw)} bytes")
    
    compressed = raw[SKIP_HEADER:]
    dctx = zstd.ZstdDecompressor()
    data = dctx.decompress(compressed, max_output_size=MAX_DECOMPRESS)
    print(f"  Decompressed size: {len(data)} bytes (0x{len(data):X})")
    print(f"  PSP address range: 0x{PSP_RAM_START:08X} to 0x{PSP_RAM_START + len(data) - RAM_BASE_IN_STATE:08X}")
    return data

def search_u16_value(data, value, label, limit=30, exclude_armor=True):
    """Search entire state for a u16 value, excluding armor tables."""
    print(f"\n{'='*80}")
    print(f"Searching for u16 value {value} (0x{value:04X}) - {label}")
    print(f"{'='*80}")
    
    hits = []
    max_offset = len(data) - 1
    
    for offset in range(RAM_BASE_IN_STATE, max_offset, 2):
        v = struct.unpack_from('<H', data, offset)[0]
        if v == value:
            psp_addr = offset_to_psp_addr(offset)
            armor = in_armor_table(psp_addr)
            if exclude_armor and armor:
                continue
            hits.append((offset, psp_addr))
            if len(hits) >= limit:
                break
    
    print(f"Found {len(hits)} hits (limit {limit}):")
    for offset, psp_addr in hits:
        ctx = []
        for delta in [-4, -2, 0, 2, 4]:
            v = read_u16(data, offset + delta)
            if v is not None:
                ctx.append(f"[{delta:+d}]=0x{v:04X}({v})")
            else:
                ctx.append(f"[{delta:+d}]=N/A")
        print(f"  PSP 0x{psp_addr:08X}  offset 0x{offset:08X}  {' '.join(ctx)}")
    
    return hits

def search_model_number_in_regions(data, model_num, label, limit_per_region=30):
    """Search for weapon model number in specific regions, checking neighbors."""
    print(f"\n{'='*80}")
    print(f"Searching for model number {model_num} (0x{model_num:04X}) - {label}")
    print(f"Checking neighbors for weapon-like IDs (1-600)")
    print(f"{'='*80}")
    
    regions = [
        (0x08974BB0, 0x08997000, "After LEGS, before FUComplete"),
        (0x08800000, 0x08960750, "EBOOT code/data"),
        (0x08997000, 0x089A0000, "FUComplete tables area"),
        (0x08A00000, 0x08C00000, "Runtime heap"),
    ]
    
    all_hits = {}
    
    for reg_start, reg_end, reg_name in regions:
        off_start = psp_addr_to_offset(reg_start)
        off_end = psp_addr_to_offset(reg_end)
        
        # Clamp to data bounds
        off_start = max(off_start, RAM_BASE_IN_STATE)
        off_end = min(off_end, len(data) - 1)
        
        if off_start >= len(data):
            print(f"\n  Region '{reg_name}' (0x{reg_start:08X}-0x{reg_end:08X}): BEYOND STATE DATA")
            continue
        
        print(f"\n  Region '{reg_name}' (0x{reg_start:08X}-0x{reg_end:08X}):")
        
        hits = []
        for offset in range(off_start, off_end, 2):
            v = struct.unpack_from('<H', data, offset)[0]
            if v == model_num:
                psp_addr = offset_to_psp_addr(offset)
                
                # Check neighbors at various spacings for weapon-like values
                # Try common struct sizes
                neighbor_info = []
                for spacing in [2, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40]:
                    prev_v = read_u16(data, offset - spacing)
                    next_v = read_u16(data, offset + spacing)
                    if prev_v is not None and next_v is not None:
                        if 1 <= prev_v <= 600 and 1 <= next_v <= 600:
                            neighbor_info.append(f"spacing={spacing}: prev={prev_v}, next={next_v}")
                
                if neighbor_info:
                    hits.append((offset, psp_addr, neighbor_info))
                    if len(hits) >= limit_per_region:
                        break
        
        print(f"    Hits with weapon-like neighbors: {len(hits)}")
        for offset, psp_addr, neighbors in hits:
            ctx_vals = []
            for delta in [-4, -2, 0, 2, 4]:
                v = read_u16(data, offset + delta)
                if v is not None:
                    ctx_vals.append(f"[{delta:+d}]=0x{v:04X}({v})")
            print(f"    PSP 0x{psp_addr:08X}  {' '.join(ctx_vals)}")
            for ni in neighbors:
                print(f"      -> {ni}")
        
        all_hits[reg_name] = hits
    
    return all_hits

def search_paired_table(data, val_a, val_b, label_a, label_b):
    """Search for tables with regular spacing containing both values."""
    print(f"\n{'='*80}")
    print(f"TASK 5: Looking for tables containing BOTH {val_a} ({label_a}) and {val_b} ({label_b})")
    print(f"{'='*80}")
    
    entry_sizes = [2, 4, 8, 12, 16, 20, 24, 28, 32, 36]
    
    regions = [
        (0x08974BB0, 0x08997000, "After LEGS"),
        (0x08800000, 0x08960000, "EBOOT"),
        (0x08997000, 0x089A0000, "FUComplete tables"),
        (0x08A00000, 0x08C00000, "Runtime heap"),
    ]
    
    # First, find all occurrences of val_a and val_b in each region
    for reg_start, reg_end, reg_name in regions:
        off_start = psp_addr_to_offset(reg_start)
        off_end = psp_addr_to_offset(reg_end)
        off_start = max(off_start, RAM_BASE_IN_STATE)
        off_end = min(off_end, len(data) - 1)
        
        if off_start >= len(data):
            continue
        
        print(f"\n  Region '{reg_name}' (0x{reg_start:08X}-0x{reg_end:08X}):")
        
        # Find all val_a positions
        positions_a = []
        for offset in range(off_start, off_end, 2):
            v = struct.unpack_from('<H', data, offset)[0]
            if v == val_a:
                positions_a.append(offset)
        
        # Find all val_b positions
        positions_b = set()
        for offset in range(off_start, off_end, 2):
            v = struct.unpack_from('<H', data, offset)[0]
            if v == val_b:
                positions_b.add(offset)
        
        print(f"    Found {len(positions_a)} occurrences of {val_a}, {len(positions_b)} occurrences of {val_b}")
        
        if not positions_a or not positions_b:
            continue
        
        found_any = False
        for entry_size in entry_sizes:
            for off_a in positions_a:
                # Check if val_b exists at off_a + N*entry_size for N in range
                for n in range(1, 501):
                    off_b_candidate = off_a + n * entry_size
                    if off_b_candidate in positions_b:
                        psp_a = offset_to_psp_addr(off_a)
                        psp_b = offset_to_psp_addr(off_b_candidate)
                        
                        # Try to infer a table base: assume val_a is at index=val_a
                        # So base = off_a - val_a * entry_size
                        possible_base = off_a - val_a * entry_size
                        psp_base = offset_to_psp_addr(possible_base) if possible_base >= RAM_BASE_IN_STATE else 0
                        
                        # Verify: does val_b appear at base + val_b * entry_size?
                        expected_b_off = possible_base + val_b * entry_size
                        verified = (expected_b_off in positions_b)
                        
                        # Also check: N = val_b - val_a
                        index_diff = val_b - val_a
                        expected_diff_match = (n == index_diff)
                        
                        print(f"    MATCH: entry_size={entry_size}, {label_a} at 0x{psp_a:08X}, "
                              f"{label_b} at 0x{psp_b:08X}, N={n}")
                        print(f"      If indices are model numbers: base=0x{psp_base:08X}, "
                              f"verified={verified}, N==diff({index_diff})={expected_diff_match}")
                        
                        # Print some entries around to see the pattern
                        if entry_size >= 4:
                            print(f"      Entries around {label_a} (model {val_a}):")
                            for idx_delta in range(-3, 4):
                                check_off = off_a + idx_delta * entry_size
                                if RAM_BASE_IN_STATE <= check_off < len(data) - entry_size:
                                    vals = []
                                    for b in range(0, min(entry_size, 16), 2):
                                        vv = read_u16(data, check_off + b)
                                        vals.append(f"0x{vv:04X}({vv})" if vv is not None else "N/A")
                                    check_psp = offset_to_psp_addr(check_off)
                                    print(f"        [{val_a + idx_delta:+4d}] 0x{check_psp:08X}: {' '.join(vals)}")
                        
                        found_any = True
                        break  # Found for this off_a and entry_size
                if found_any and entry_size <= 4:
                    break  # For small entry sizes, one match is enough
        
        if not found_any:
            print(f"    No paired matches found in this region.")

def main():
    data = load_state()
    
    # TASK 1: Search for Sieglinde File ID 3409 (0x0D51)
    hits_3409 = search_u16_value(data, 3409, "Sieglinde File ID (we021.pac)")
    
    # TASK 2: Search for Black Fatalis Blade File ID 3630 (0x0E2E)
    hits_3630 = search_u16_value(data, 3630, "Black Fatalis Blade File ID (we242.pac)")
    
    # TASK 3: Search for model number 21 in specific regions
    hits_21 = search_model_number_in_regions(data, 21, "Sieglinde model number")
    
    # TASK 4: Search for model number 242 in specific regions
    hits_242 = search_model_number_in_regions(data, 242, "Black Fatalis Blade model number")
    
    # TASK 5: Look for tables containing both 21 and 242
    search_paired_table(data, 21, 242, "model_21", "model_242")
    
    # Also try with file IDs
    print(f"\n{'='*80}")
    print("BONUS: Also checking paired search with File IDs 3409 and 3630")
    print(f"{'='*80}")
    search_paired_table(data, 3409, 3630, "fileID_3409", "fileID_3630")
    
    print("\nDone.")

if __name__ == '__main__':
    main()

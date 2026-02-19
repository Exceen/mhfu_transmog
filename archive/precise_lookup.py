#!/usr/bin/env python3
"""
Precise lookup of armor entry data from MHFU save state.
Reads specific entries from HEAD/CHEST/ARMS/WAIST/LEGS tables
and computes CWCheat lines for Rath Soul -> Black transmog.
"""

import struct
import zstandard as zstd

# Constants
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
ENTRY_SIZE = 40
CWCHEAT_BASE = 0x08800000

STATE_PATH = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"

# Table definitions: name, PSP base address, list of entry IDs to read
TABLES = [
    ("HEAD",  0x08960750, [71, 72, 99, 100, 101, 102]),
    ("CHEST", 0x08964B70, [66, 67, 97, 98, 99, 100, 101]),
    ("ARMS",  0x08968D10, [64, 65, 96, 97, 98, 99, 100]),
    ("WAIST", 0x0896CD48, [63, 64, 65, 66, 96, 97, 98, 99]),
    ("LEGS",  0x08970D30, [63, 64, 65, 66, 93, 94, 95, 96, 97]),
]

def psp_addr_to_state_offset(psp_addr):
    """Convert a PSP address to an offset within the decompressed save state."""
    ram_offset = psp_addr - PSP_RAM_START
    return RAM_BASE_IN_STATE + ram_offset

def read_entry(data, psp_addr):
    """Read model_m (s16), model_f (s16), flag (u8), rarity (u8) from entry at psp_addr."""
    off = psp_addr_to_state_offset(psp_addr)
    model_m = struct.unpack_from('<h', data, off)[0]      # s16 at offset 0
    model_f = struct.unpack_from('<h', data, off + 2)[0]   # s16 at offset 2
    flag    = struct.unpack_from('<B', data, off + 4)[0]   # u8 at offset 4
    rarity  = struct.unpack_from('<B', data, off + 5)[0]   # u8 at offset 5
    return model_m, model_f, flag, rarity

def main():
    # Load and decompress save state
    print(f"Loading state: {STATE_PATH}")
    with open(STATE_PATH, 'rb') as f:
        raw = f.read()

    # Skip 0xB0 header, then zstd decompress
    compressed = raw[0xB0:]
    dctx = zstd.ZstdDecompressor()
    data = dctx.decompress(compressed, max_output_size=128 * 1024 * 1024)
    print(f"Decompressed size: {len(data)} bytes ({len(data) / (1024*1024):.1f} MB)\n")

    # Store all entries keyed by (table_name, eid)
    all_entries = {}

    for table_name, table_base, eids in TABLES:
        print("=" * 80)
        print(f"  {table_name}  (table base: 0x{table_base:08X})")
        print("=" * 80)
        print(f"  {'eid':>4s}  {'model_m':>8s}  {'model_f':>8s}  {'flag':>4s}  {'rarity':>6s}  {'PSP_addr':>12s}  {'CWCheat_off':>12s}")
        print(f"  {'----':>4s}  {'-------':>8s}  {'-------':>8s}  {'----':>4s}  {'------':>6s}  {'--------':>12s}  {'-----------':>12s}")

        for eid in eids:
            psp_addr = table_base + eid * ENTRY_SIZE
            cwcheat_offset = psp_addr - CWCHEAT_BASE
            model_m, model_f, flag, rarity = read_entry(data, psp_addr)
            all_entries[(table_name, eid)] = {
                'model_m': model_m,
                'model_f': model_f,
                'flag': flag,
                'rarity': rarity,
                'psp_addr': psp_addr,
                'cwcheat_offset': cwcheat_offset,
            }
            print(f"  {eid:4d}  {model_m:8d}  {model_f:8d}  0x{flag:02X}  {rarity:6d}  0x{psp_addr:08X}  0x{cwcheat_offset:08X}")
        print()

    # =========================================================================
    # FINAL MAPPING: Rath Soul -> Black
    # =========================================================================
    # Pairing logic:
    #   Rath Soul S (BM) / Rath Soul S (GN) -> Black S (BM) / Black S (GN)
    #   Rath Soul U (BM) / Rath Soul U (GN) -> Black (BM) / Black (GN)
    #   etc.
    #
    # Pairs are identified by consecutive eids. BM first, GN second.
    # Exception: if both have flag 0x0F, they are both gender-neutral (HEAD).
    #
    # We define explicit pairings per table:
    #   (rath_soul_eid, black_eid) for each table

    # Define Rath Soul -> Black pairings per table
    # Based on the equip IDs provided:
    # HEAD:  Rath Soul = 71,72  | Black = 99,100,101,102
    #   71->99, 72->100  (or 71->101, 72->102 if there are S/U variants)
    # CHEST: Rath Soul = 66,67  | Black = 97,98,99,100,101
    # ARMS:  Rath Soul = 64,65  | Black = 96,97,98,99,100
    # WAIST: Rath Soul = 63,64,65,66 | Black = 96,97,98,99
    # LEGS:  Rath Soul = 63,64,65,66 | Black = 93,94,95,96,97

    # Let's figure out pairings by examining the data we read.
    # We'll group entries by flag to identify BM/GN/neutral patterns.

    print("=" * 80)
    print("  PAIRING ANALYSIS")
    print("=" * 80)

    # For each table, separate into "rath soul range" and "black range"
    # based on the eid clusters (lower cluster = rath soul, higher = black)
    pairing_defs = {
        "HEAD":  {"rath": [71, 72],         "black": [99, 100, 101, 102]},
        "CHEST": {"rath": [66, 67],         "black": [97, 98, 99, 100, 101]},
        "ARMS":  {"rath": [64, 65],         "black": [96, 97, 98, 99, 100]},
        "WAIST": {"rath": [63, 64, 65, 66], "black": [96, 97, 98, 99]},
        "LEGS":  {"rath": [63, 64, 65, 66], "black": [93, 94, 95, 96, 97]},
    }

    # We'll collect all CWCheat lines
    cwcheat_lines = []

    for table_name in ["HEAD", "CHEST", "ARMS", "WAIST", "LEGS"]:
        rath_eids = pairing_defs[table_name]["rath"]
        black_eids = pairing_defs[table_name]["black"]

        print(f"\n  {table_name}:")
        print(f"    Rath Soul eids: {rath_eids}")
        for eid in rath_eids:
            e = all_entries[(table_name, eid)]
            print(f"      eid {eid}: model_m={e['model_m']}, model_f={e['model_f']}, flag=0x{e['flag']:02X}, rarity={e['rarity']}")
        print(f"    Black eids: {black_eids}")
        for eid in black_eids:
            e = all_entries[(table_name, eid)]
            print(f"      eid {eid}: model_m={e['model_m']}, model_f={e['model_f']}, flag=0x{e['flag']:02X}, rarity={e['rarity']}")

        # Build sub-groups based on consecutive eids with matching model patterns
        # A "pair" is two consecutive eids where one is BM (flag != 0x0F) and one is GN
        # Or both are 0x0F (gender-neutral, like HEAD)

        def group_consecutive_pairs(eids, table_name):
            """Group eids into pairs/singles based on flag patterns."""
            groups = []
            i = 0
            while i < len(eids):
                e1 = all_entries[(table_name, eids[i])]
                if i + 1 < len(eids):
                    e2 = all_entries[(table_name, eids[i+1])]
                    # Check if they form a BM/GN pair (consecutive eids, same model values)
                    # BM typically has flag that differs from GN
                    # Or both 0x0F for gender-neutral sets
                    if eids[i+1] == eids[i] + 1:
                        # Consecutive - likely a pair
                        groups.append((eids[i], eids[i+1]))
                        i += 2
                        continue
                # Single entry
                groups.append((eids[i],))
                i += 1
            return groups

        rath_groups = group_consecutive_pairs(rath_eids, table_name)
        black_groups = group_consecutive_pairs(black_eids, table_name)

        print(f"    Rath Soul groups: {rath_groups}")
        print(f"    Black groups: {black_groups}")

        # Match rath groups to black groups
        # Strategy: pair them in order; if black has more groups, skip extras
        for ri, rg in enumerate(rath_groups):
            if ri >= len(black_groups):
                print(f"    WARNING: No matching black group for rath group {rg}")
                continue
            bg = black_groups[ri]

            # Pair entries within groups
            for ji in range(len(rg)):
                rath_eid = rg[ji]
                if ji < len(bg):
                    black_eid = bg[ji]
                else:
                    black_eid = bg[-1]  # fallback to last in group

                re = all_entries[(table_name, rath_eid)]
                be = all_entries[(table_name, black_eid)]

                # Target u32: (black_model_f & 0xFFFF) << 16 | (black_model_m & 0xFFFF)
                target_u32 = ((be['model_f'] & 0xFFFF) << 16) | (be['model_m'] & 0xFFFF)

                # CWCheat line: _L 0x2AAAAAAA 0xBBBBBBBB
                # where AAAAAAA = cwcheat_offset of the rath soul entry
                cwcheat_off = re['cwcheat_offset']

                line = f"_L 0x2{cwcheat_off:07X} 0x{target_u32:08X}"
                cwcheat_lines.append((table_name, rath_eid, black_eid, line))

                print(f"    PAIR: {table_name} eid {rath_eid} (Rath Soul) -> eid {black_eid} (Black)")
                print(f"      Rath Soul: model_m={re['model_m']}, model_f={re['model_f']}")
                print(f"      Black:     model_m={be['model_m']}, model_f={be['model_f']}")
                print(f"      target_u32 = 0x{target_u32:08X}")
                print(f"      {line}")

    # Print final CWCheat block
    print("\n" + "=" * 80)
    print("  FINAL CWCHEAT BLOCK - Rath Soul -> Black Transmog")
    print("=" * 80)
    print("_S ULJM-05500")
    print("_G Monster Hunter Freedom Unite")
    print("_C0 Rath Soul to Black Transmog")
    for table_name, rath_eid, black_eid, line in cwcheat_lines:
        print(f"{line}  # {table_name} eid {rath_eid} -> {black_eid}")
    print()

    # Also print without comments for clean paste
    print("--- Clean (no comments) ---")
    print("_S ULJM-05500")
    print("_G Monster Hunter Freedom Unite")
    print("_C0 Rath Soul to Black Transmog")
    for _, _, _, line in cwcheat_lines:
        print(line)

if __name__ == '__main__':
    main()

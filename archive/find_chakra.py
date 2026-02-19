#!/usr/bin/env python3
"""
Search the MHFU HEAD armor table for Chakra Piercing and other notable entries.

Field layout (40 bytes per entry):
  +0  s16  model_m (male model ID)
  +2  s16  model_f (female model ID)
  +4  u8   flags
  +5  u8   rarity
  +6  u16  (unknown / padding)
  +8  u32  sell price
  +12 u8   defense
  +13 u8   fire res
  +14 u8   water res
  +15 u8   thunder res
  +16 u8   dragon res
  +17 u8   ice res
  +18 u8   slots
  ... skills etc.
"""

import struct
import zstandard as zstd
from collections import Counter

# === Constants ===
PSP_RAM_START      = 0x08000000
RAM_BASE_IN_STATE  = 0x48
ENTRY_SIZE         = 40
HEAD_TABLE         = 0x08960750
STATE_PATH         = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"
SKIP_HEADER        = 0xB0
MAX_DECOMPRESS     = 128 * 1024 * 1024  # 128 MB

SEARCH_MAX_EID = 401  # 0..400 inclusive


def load_ram(path):
    with open(path, "rb") as f:
        raw = f.read()
    dctx = zstd.ZstdDecompressor()
    data = dctx.decompress(raw[SKIP_HEADER:], max_output_size=MAX_DECOMPRESS)
    return data


def psp_to_offset(psp_addr):
    return (psp_addr - PSP_RAM_START) + RAM_BASE_IN_STATE


def read_s16(data, psp_addr):
    off = psp_to_offset(psp_addr)
    return struct.unpack_from('<h', data, off)[0]

def read_u8(data, psp_addr):
    return data[psp_to_offset(psp_addr)]

def read_u32(data, psp_addr):
    off = psp_to_offset(psp_addr)
    return struct.unpack_from('<I', data, off)[0]


def read_entry(data, table_addr, eid):
    addr = table_addr + eid * ENTRY_SIZE
    model_m = read_s16(data, addr)
    model_f = read_s16(data, addr + 2)
    flags   = read_u8(data, addr + 4)
    rarity  = read_u8(data, addr + 5)
    sell    = read_u32(data, addr + 8)
    defense = read_u8(data, addr + 12)
    fire    = read_u8(data, addr + 13)
    water   = read_u8(data, addr + 14)
    thunder = read_u8(data, addr + 15)
    dragon  = read_u8(data, addr + 16)
    ice     = read_u8(data, addr + 17)
    slots   = read_u8(data, addr + 18)

    # Raw hex dump for debugging
    off = psp_to_offset(addr)
    raw_hex = data[off:off+ENTRY_SIZE].hex()

    return {
        "eid": eid,
        "model_m": model_m,
        "model_f": model_f,
        "flags": flags,
        "rarity": rarity,
        "sell": sell,
        "defense": defense,
        "fire": fire,
        "water": water,
        "thunder": thunder,
        "dragon": dragon,
        "ice": ice,
        "slots": slots,
        "raw_hex": raw_hex,
    }


def fmt_entry(e):
    return (
        f"  eid={e['eid']:4d}  model_m={e['model_m']:>5d}  model_f={e['model_f']:>5d}  "
        f"flags=0x{e['flags']:02X}  rarity={e['rarity']:>2d}  "
        f"def={e['defense']:>3d}  sell={e['sell']:>6d}  slots={e['slots']}  "
        f"res=[fi={e['fire']:+d} wa={e['water']:+d} th={e['thunder']:+d} dr={e['dragon']:+d} ic={e['ice']:+d}]"
    )


def main():
    print("Loading save state...")
    data = load_ram(STATE_PATH)
    print(f"  Decompressed size: {len(data):,} bytes")
    print(f"  HEAD table PSP addr: 0x{HEAD_TABLE:08X}")
    print(f"  HEAD table offset in file: 0x{psp_to_offset(HEAD_TABLE):X}")
    print()

    # Read all entries 0..400
    entries = []
    for eid in range(SEARCH_MAX_EID):
        e = read_entry(data, HEAD_TABLE, eid)
        entries.append(e)

    # =========================================================================
    # TASK 1: Entries with rarity >= 8 (Chakra Piercing has rarity 10)
    # =========================================================================
    print("=" * 100)
    print("TASK 1: Entries with rarity >= 8 (Chakra Piercing has rarity 10)")
    print("=" * 100)
    matches = [e for e in entries if e["rarity"] >= 8]
    for e in matches:
        print(fmt_entry(e))
    print(f"  Total: {len(matches)} entries")
    print()

    # =========================================================================
    # TASK 2: Entries with model_m == 0 or model_m <= 5
    # =========================================================================
    print("=" * 100)
    print("TASK 2: Entries with model_m = 0 or model_m <= 5")
    print("=" * 100)
    matches = [e for e in entries if e["model_m"] <= 5]
    for e in matches:
        print(fmt_entry(e))
    print(f"  Total: {len(matches)} entries")
    print()

    # =========================================================================
    # TASK 3: Entries where model_m == model_f and model_m < 20
    # =========================================================================
    print("=" * 100)
    print("TASK 3: Entries where model_m == model_f and model_m < 20")
    print("=" * 100)
    matches = [e for e in entries if e["model_m"] == e["model_f"] and e["model_m"] < 20]
    for e in matches:
        print(fmt_entry(e))
    print(f"  Total: {len(matches)} entries")
    print()

    # =========================================================================
    # TASK 4: Dump entries eid 340-400
    # =========================================================================
    print("=" * 100)
    print("TASK 4: Entries eid 340-400 (end of table, rare items)")
    print("=" * 100)
    for e in entries:
        if 340 <= e["eid"] <= 400:
            print(fmt_entry(e))
    print()

    # =========================================================================
    # TASK 5: Check eid=0 — is model_m=0 "Nothing Equipped"?
    # =========================================================================
    print("=" * 100)
    print("TASK 5: Entry at eid=0 (Nothing Equipped check)")
    print("=" * 100)
    e0 = entries[0]
    print(fmt_entry(e0))
    if e0["model_m"] == 0 and e0["model_f"] == 0:
        print("  -> model_m=0 and model_f=0: YES, this is 'Nothing Equipped' / bare head")
    else:
        print("  -> model_m != 0 or model_f != 0: eid=0 is NOT 'nothing equipped'")
    print()

    # =========================================================================
    # BONUS: Entries with high rarity and small model IDs (piercings/earrings)
    # =========================================================================
    print("=" * 100)
    print("BONUS: Entries with rarity >= 5 AND model_m < 30 (possible piercings/earrings)")
    print("=" * 100)
    matches = [e for e in entries if e["rarity"] >= 5 and 0 < e["model_m"] < 30]
    for e in matches:
        print(fmt_entry(e))
    print(f"  Total: {len(matches)} entries")
    print()

    # =========================================================================
    # BONUS 2: Known piercing entries (from dump_armor_table.py)
    # =========================================================================
    print("=" * 100)
    print("BONUS 2: Known piercing/special entries (eids 52-56, 233, 381)")
    print("=" * 100)
    for eid in [52, 53, 54, 55, 56, 233, 381]:
        if eid < len(entries):
            e = entries[eid]
            print(fmt_entry(e))
            print(f"         raw hex: {e['raw_hex']}")
    print()

    # =========================================================================
    # STATS
    # =========================================================================
    print("=" * 100)
    print("STATS: model_m distribution for eid 0-400")
    print("=" * 100)
    model_counts = Counter(e["model_m"] for e in entries)
    for model_id, count in sorted(model_counts.items())[:40]:
        print(f"  model_m={model_id:>5d}: {count} entries")
    print(f"  ... ({len(model_counts)} distinct model_m values total)")
    print()

    rarity_counts = Counter(e["rarity"] for e in entries)
    print("Rarity distribution:")
    for r, count in sorted(rarity_counts.items()):
        print(f"  rarity={r:>2d}: {count} entries")
    print()

    # Find the entry with model_m=0 that is NOT eid=0 (piercings with invisible model?)
    print("Entries with model_m=0 (excluding eid=0):")
    for e in entries:
        if e["model_m"] == 0 and e["eid"] != 0:
            print(fmt_entry(e))


if __name__ == "__main__":
    main()

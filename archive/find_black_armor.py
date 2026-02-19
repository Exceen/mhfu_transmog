#!/usr/bin/env python3
"""
Find Black armor entries in all ArmorData tables from MHFU save state.
Also dumps Rath Soul entries for reference and searches by model ID.
"""

import struct
import zstandard as zstd

# === Constants ===
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
ENTRY_SIZE = 40
STATE_PATH = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"
SKIP_BYTES = 0xB0
MAX_RAM = 128 * 1024 * 1024  # 128 MB

# === Table addresses ===
TABLES = {
    "HEAD":  0x08960750,
    "CHEST": 0x08964B70,
    "ARMS":  0x08968D10,
    "WAIST": 0x0896CD48,
    "LEGS":  0x08970D30,
}

# === Flag byte meanings ===
FLAG_NAMES = {
    0x07: "BM(both)",
    0x0B: "GN(both)",
    0x05: "male?",
    0x06: "female?",
}

def load_ram():
    """Load and decompress the PSP RAM from the save state."""
    print(f"Loading state: {STATE_PATH}")
    with open(STATE_PATH, "rb") as f:
        raw = f.read()
    print(f"  Raw file size: {len(raw):,} bytes")

    compressed = raw[SKIP_BYTES:]
    dctx = zstd.ZstdDecompressor()
    decompressed = dctx.decompress(compressed, max_output_size=MAX_RAM)
    print(f"  Decompressed size: {len(decompressed):,} bytes")
    return decompressed

def psp_to_offset(psp_addr):
    """Convert PSP address to offset in decompressed RAM."""
    return (psp_addr - PSP_RAM_START) + RAM_BASE_IN_STATE

def read_entry(ram, table_psp_addr, eid):
    """Read a single armor entry from RAM."""
    base = psp_to_offset(table_psp_addr) + eid * ENTRY_SIZE
    if base + ENTRY_SIZE > len(ram):
        return None
    return ram[base:base + ENTRY_SIZE]

def parse_entry(data):
    """Parse key fields from a 40-byte armor entry."""
    # First 8 bytes for display
    raw8 = data[:8]
    # model_m = u16 at +0, model_f = u16 at +2
    model_m = struct.unpack_from("<H", data, 0)[0]
    model_f = struct.unpack_from("<H", data, 2)[0]
    flag = data[4]
    rarity = data[5]
    return model_m, model_f, flag, rarity, raw8

def dump_range(ram, table_name, table_addr, eid_start, eid_end, label=""):
    """Dump a range of entries from a table."""
    hdr = f"  {table_name} eid {eid_start}-{eid_end}"
    if label:
        hdr += f"  ({label})"
    print(hdr)
    print(f"  {'eid':>5}  {'model_m':>7}  {'model_f':>7}  {'flag':>6}  {'flag_name':<10}  {'rarity':>6}  raw_first_8_bytes")
    print(f"  {'-'*5}  {'-'*7}  {'-'*7}  {'-'*6}  {'-'*10}  {'-'*6}  {'-'*24}")

    for eid in range(eid_start, eid_end + 1):
        entry = read_entry(ram, table_addr, eid)
        if entry is None:
            print(f"  {eid:>5}  (out of bounds)")
            continue
        model_m, model_f, flag, rarity, raw8 = parse_entry(entry)
        fname = FLAG_NAMES.get(flag, f"0x{flag:02X}?")
        hex8 = " ".join(f"{b:02X}" for b in raw8)
        print(f"  {eid:>5}  {model_m:>7}  {model_f:>7}  0x{flag:02X}    {fname:<10}  {rarity:>6}  {hex8}")
    print()

def search_models(ram, table_name, table_addr, target_models, max_eid=400):
    """Search for entries where model_m or model_f matches target models."""
    print(f"  {table_name}: searching eid 0-{max_eid} for models {sorted(target_models)}")
    found = []
    for eid in range(max_eid + 1):
        entry = read_entry(ram, table_addr, eid)
        if entry is None:
            break
        model_m, model_f, flag, rarity, raw8 = parse_entry(entry)
        if model_m in target_models or model_f in target_models:
            found.append((eid, model_m, model_f, flag, rarity, raw8))

    if not found:
        print(f"    No matches found.\n")
        return

    print(f"    {'eid':>5}  {'model_m':>7}  {'model_f':>7}  {'flag':>6}  {'flag_name':<10}  {'rarity':>6}  raw_first_8_bytes")
    print(f"    {'-'*5}  {'-'*7}  {'-'*7}  {'-'*6}  {'-'*10}  {'-'*6}  {'-'*24}")
    for eid, model_m, model_f, flag, rarity, raw8 in found:
        fname = FLAG_NAMES.get(flag, f"0x{flag:02X}?")
        hex8 = " ".join(f"{b:02X}" for b in raw8)
        print(f"    {eid:>5}  {model_m:>7}  {model_f:>7}  0x{flag:02X}    {fname:<10}  {rarity:>6}  {hex8}")
    print(f"    ({len(found)} matches)\n")

def main():
    ram = load_ram()
    print()

    # ========================================================
    # PART 1: Dump ranges around expected Black armor entries
    # ========================================================
    print("=" * 80)
    print("PART 1: Dump entries around expected Black armor locations")
    print("=" * 80)
    print()

    black_ranges = {
        "HEAD":  (65, 75,  "Black head models ~50-51"),
        "CHEST": (60, 75,  "Black chest models ~48-49"),
        "ARMS":  (55, 70,  "Black arms models ~47-48"),
        "WAIST": (55, 70,  "Black waist models ~35-37"),
        "LEGS":  (55, 70,  "Black legs model ~35"),
    }

    for tname in ["HEAD", "CHEST", "ARMS", "WAIST", "LEGS"]:
        eid_s, eid_e, label = black_ranges[tname]
        dump_range(ram, tname, TABLES[tname], eid_s, eid_e, label)

    # ========================================================
    # PART 2: Dump Rath Soul entries for reference
    # ========================================================
    print("=" * 80)
    print("PART 2: Rath Soul entries for reference")
    print("=" * 80)
    print()

    rath_ranges = {
        "HEAD":  [(99, 105)],
        "CHEST": [(97, 103)],
        "ARMS":  [(95, 100)],
        "WAIST": [(95, 100)],
        "LEGS":  [(90, 100), (110, 115)],
    }

    for tname in ["HEAD", "CHEST", "ARMS", "WAIST", "LEGS"]:
        for eid_s, eid_e in rath_ranges[tname]:
            dump_range(ram, tname, TABLES[tname], eid_s, eid_e, "Rath Soul reference")

    # ========================================================
    # PART 3: Search by model ID
    # ========================================================
    print("=" * 80)
    print("PART 3: Search for Black armor by model ID (eid 0-400)")
    print("=" * 80)
    print()

    search_targets = {
        "HEAD":  {50, 51},
        "CHEST": {48, 49},
        "ARMS":  {47, 48},
        "WAIST": {34, 35, 36, 37},
        "LEGS":  {35},
    }

    for tname in ["HEAD", "CHEST", "ARMS", "WAIST", "LEGS"]:
        search_models(ram, tname, TABLES[tname], search_targets[tname])

    print("Done.")

if __name__ == "__main__":
    main()

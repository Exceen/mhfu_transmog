#!/usr/bin/env python3
"""
Definitive mapping of Rath Soul and Black armor entries in MHFU equip tables.
Searches each armor slot table for model_m values matching known FUComplete file names.
"""

import struct
import zstandard as zstd

# === Constants ===
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
ENTRY_SIZE = 40
MAX_RAM = 128 * 1024 * 1024  # 128 MB

STATE_PATH = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"

# === Table addresses (PSP virtual addresses) ===
TABLES = {
    "HEAD":  0x08960750,
    "CHEST": 0x08964B70,
    "ARMS":  0x08968D10,
    "WAIST": 0x0896CD48,
    "LEGS":  0x08970D30,
}

# === Search targets per table ===
SEARCHES = {
    "HEAD": [
        ("Rath Soul", {96, 97}),
        ("Black",     {50, 51}),
    ],
    "CHEST": [
        ("Rath Soul", {89, 90, 91, 92, 93}),
        ("Black",     {46, 47, 48, 49}),
    ],
    "ARMS": [
        ("Rath Soul", {89, 90}),
        ("Black",     {47, 48}),
    ],
    "WAIST": [
        ("Rath Soul", {76, 77}),
        ("Black",     {34, 35, 36, 37}),
    ],
    "LEGS": [
        ("Rath Soul", {66, 67}),
        ("Black",     {34, 35}),
    ],
}

# Model file name prefixes per slot
MODEL_PREFIX = {
    "HEAD":  "m_hair",
    "CHEST": "m_body",
    "ARMS":  "m_arm",
    "WAIST": "m_wst",
    "LEGS":  "m_reg",
}

MAX_EID = 400


def load_ram():
    """Load and decompress the PPSSPP save state, return raw RAM bytes."""
    print(f"Loading save state: {STATE_PATH}")
    with open(STATE_PATH, "rb") as f:
        raw = f.read()

    # Skip 0xB0 header bytes, then zstd decompress
    compressed = raw[0xB0:]
    dctx = zstd.ZstdDecompressor()
    decompressed = dctx.decompress(compressed, max_output_size=MAX_RAM)
    print(f"Decompressed size: {len(decompressed):,} bytes ({len(decompressed) / (1024*1024):.1f} MB)")

    # RAM starts at offset RAM_BASE_IN_STATE within decompressed data
    ram = decompressed[RAM_BASE_IN_STATE:]
    print(f"RAM data size: {len(ram):,} bytes")
    return ram


def psp_to_ram_offset(psp_addr):
    """Convert a PSP virtual address to an offset into our RAM buffer."""
    return psp_addr - PSP_RAM_START


def read_entry(ram, table_psp_addr, eid):
    """Read a single equip table entry and return parsed fields."""
    base = psp_to_ram_offset(table_psp_addr) + eid * ENTRY_SIZE
    if base + ENTRY_SIZE > len(ram):
        return None

    entry = ram[base:base + ENTRY_SIZE]

    # Parse key fields:
    # Offset 0: model_m (u16)
    # Offset 2: model_f (u16)
    # Offset 4: flag byte
    # Offset 5: rarity byte
    model_m = struct.unpack_from("<H", entry, 0)[0]
    model_f = struct.unpack_from("<H", entry, 2)[0]
    flag = entry[4]
    rarity = entry[5]

    psp_addr = table_psp_addr + eid * ENTRY_SIZE
    cwcheat_offset = psp_addr - PSP_RAM_START

    return {
        "eid": eid,
        "model_m": model_m,
        "model_f": model_f,
        "flag": flag,
        "rarity": rarity,
        "psp_addr": psp_addr,
        "cwcheat_offset": cwcheat_offset,
        "raw": entry,
    }


def main():
    ram = load_ram()
    print()

    all_results = {}  # table_name -> list of (label, entry_dict)

    for table_name in ["HEAD", "CHEST", "ARMS", "WAIST", "LEGS"]:
        table_addr = TABLES[table_name]
        searches = SEARCHES[table_name]
        prefix = MODEL_PREFIX[table_name]

        print("=" * 90)
        print(f"  TABLE: {table_name}  (base: 0x{table_addr:08X})")
        print("=" * 90)

        table_results = []

        for label, target_models in searches:
            print(f"\n  Searching for {label}: model_m in {sorted(target_models)}")
            print(f"  {'eid':>5}  {'model_m':>8}  {'model_f':>8}  {'flag':>6}  {'rarity':>6}  {'PSP addr':>12}  {'CWC offset':>12}  file")
            print(f"  {'-'*5}  {'-'*8}  {'-'*8}  {'-'*6}  {'-'*6}  {'-'*12}  {'-'*12}  {'-'*20}")

            found = False
            for eid in range(MAX_EID + 1):
                e = read_entry(ram, table_addr, eid)
                if e is None:
                    break
                if e["model_m"] in target_models:
                    found = True
                    fname = f"{prefix}{e['model_m']:03d}"
                    print(f"  {e['eid']:5d}  {e['model_m']:8d}  {e['model_f']:8d}  "
                          f"  0x{e['flag']:02X}  {e['rarity']:6d}  "
                          f"0x{e['psp_addr']:08X}  0x{e['cwcheat_offset']:08X}  {fname}")

                    # Also dump raw hex for inspection
                    raw_hex = " ".join(f"{b:02X}" for b in e["raw"][:12])
                    print(f"         raw[0:12]: {raw_hex}")

                    table_results.append((label, e))

            if not found:
                print(f"         (no matches found)")

        all_results[table_name] = table_results
        print()

    # === SUMMARY ===
    print()
    print("=" * 90)
    print("  SUMMARY: Identified BM/GN Pairs")
    print("=" * 90)
    print()
    print("  BM/GN pairing rule:")
    print("    - Consecutive eids usually form BM/GN pairs")
    print("    - Lower eid + flag 0x07 = BM (Blademaster)")
    print("    - Higher eid + flag 0x0B = GN (Gunner)")
    print("    - HEAD: both use flag 0x0F")
    print()

    for table_name in ["HEAD", "CHEST", "ARMS", "WAIST", "LEGS"]:
        results = all_results[table_name]
        prefix = MODEL_PREFIX[table_name]

        print(f"  --- {table_name} ---")

        for armor_name in ["Rath Soul", "Black"]:
            entries = [(label, e) for label, e in results if label == armor_name]
            if not entries:
                print(f"    {armor_name}: NO MATCHES FOUND")
                continue

            # Sort by eid
            entries.sort(key=lambda x: x[1]["eid"])

            bm_entries = []
            gn_entries = []

            if table_name == "HEAD":
                # Both use 0x0F; lower eid = BM (helm), higher = GN (cap)
                for label, e in entries:
                    if e["flag"] == 0x0F:
                        if not bm_entries:
                            bm_entries.append(e)
                        else:
                            gn_entries.append(e)
                    else:
                        print(f"    {armor_name}: eid {e['eid']} has unexpected flag 0x{e['flag']:02X}")
            else:
                for label, e in entries:
                    if e["flag"] == 0x07:
                        bm_entries.append(e)
                    elif e["flag"] == 0x0B:
                        gn_entries.append(e)
                    else:
                        print(f"    {armor_name}: eid {e['eid']} has unexpected flag 0x{e['flag']:02X}")

            for bm in bm_entries:
                fname_m = f"{prefix}{bm['model_m']:03d}"
                role = "BM (Helm)" if table_name == "HEAD" else "BM"
                print(f"    {armor_name} {role}: eid={bm['eid']:3d}  model_m={bm['model_m']:3d} ({fname_m})  "
                      f"model_f={bm['model_f']:3d}  flag=0x{bm['flag']:02X}  rarity={bm['rarity']}  "
                      f"CWC=0x{bm['cwcheat_offset']:08X}")

            for gn in gn_entries:
                fname_m = f"{prefix}{gn['model_m']:03d}"
                role = "GN (Cap)" if table_name == "HEAD" else "GN"
                print(f"    {armor_name} {role}:  eid={gn['eid']:3d}  model_m={gn['model_m']:3d} ({fname_m})  "
                      f"model_f={gn['model_f']:3d}  flag=0x{gn['flag']:02X}  rarity={gn['rarity']}  "
                      f"CWC=0x{gn['cwcheat_offset']:08X}")

            if not bm_entries and not gn_entries:
                print(f"    {armor_name}: found entries but could not classify BM/GN:")
                for label, e in entries:
                    print(f"      eid={e['eid']}  model_m={e['model_m']}  flag=0x{e['flag']:02X}  rarity={e['rarity']}")

        print()

    # === Final quick-reference table ===
    print()
    print("=" * 90)
    print("  QUICK REFERENCE: CWCheat Offsets for model_m field (offset +0 of entry)")
    print("=" * 90)
    print()
    print(f"  {'Slot':<8} {'Armor':<12} {'Type':<6} {'eid':>5} {'model_m':>8} {'CWC offset':>14}")
    print(f"  {'-'*8} {'-'*12} {'-'*6} {'-'*5} {'-'*8} {'-'*14}")

    for table_name in ["HEAD", "CHEST", "ARMS", "WAIST", "LEGS"]:
        results = all_results[table_name]
        for label, e in sorted(results, key=lambda x: (x[0], x[1]["eid"])):
            flag = e["flag"]
            if table_name == "HEAD":
                same_label = [x[1] for x in results if x[0] == label]
                same_label.sort(key=lambda x: x["eid"])
                atype = "BM" if e["eid"] == same_label[0]["eid"] else "GN"
            else:
                atype = "BM" if flag == 0x07 else ("GN" if flag == 0x0B else f"0x{flag:02X}")
            print(f"  {table_name:<8} {label:<12} {atype:<6} {e['eid']:5d} {e['model_m']:8d} 0x{e['cwcheat_offset']:08X}")

    print()
    print("Done.")


if __name__ == "__main__":
    main()

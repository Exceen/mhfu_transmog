#!/usr/bin/env python3
"""Check byte +19 as pigment flag candidate across all slots."""

import struct
import json
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
HEADER_SIZE = 0xB0
RAM_OFFSET = 0x48
PSP_RAM_START = 0x08000000
ARMOR_ENTRY_SIZE = 40

ARMOR_TABLES = {
    "head":  0x08960750,
    "chest": 0x08964B70,
    "arms":  0x08968D10,
    "waist": 0x0896CD48,
    "legs":  0x08970D30,
}


def load_ram(slot_file):
    path = f"{STATE_DIR}/ULJM05500_1.01_{slot_file}.ppst"
    with open(path, "rb") as f:
        raw = f.read()
    data = zstandard.ZstdDecompressor().decompress(raw[HEADER_SIZE:], max_output_size=256 * 1024 * 1024)
    return data[RAM_OFFSET:]


def off(psp_addr):
    return psp_addr - PSP_RAM_START


def main():
    ram = load_ram(5)

    with open("transmog_data.json") as f:
        tdata = json.load(f)

    eid_names = {}
    for slot in ARMOR_TABLES:
        eid_names[slot] = {}
        for s in tdata["armor"][slot]["sets"]:
            for v in s["variants"]:
                for eid in v["eids"]:
                    name = s["names"][-1] if s["names"] else "???"
                    vname = v.get("names", [""])[-1] if v.get("names") else ""
                    eid_names[slot][eid] = vname if vname else name

    # Focus on WAIST since we know Mafumofu Coat / Coat S
    # Show byte +19 for all entries, grouped by value
    slot = "waist"
    base = off(ARMOR_TABLES[slot])

    by_val = {}
    for eid in range(400):
        o = base + eid * ARMOR_ENTRY_SIZE
        entry = ram[o:o + ARMOR_ENTRY_SIZE]
        model_m = struct.unpack_from("<h", entry, 0)[0]
        if model_m == 0 and entry[4] == 0:
            continue
        b19 = entry[19]
        rarity = entry[5]
        name = eid_names[slot].get(eid, f"(eid {eid})")
        by_val.setdefault(b19, []).append((eid, name, rarity))

    print(f"WAIST - byte +19 distribution:")
    for val in sorted(by_val):
        entries = by_val[val]
        print(f"\n  Value {val}: {len(entries)} entries")
        for eid, name, rar in entries[:15]:
            print(f"    eid {eid:3d}: rar={rar} {name}")
        if len(entries) > 15:
            print(f"    ... and {len(entries) - 15} more")

    # Also check other slots
    for slot in ["head", "chest", "arms", "legs"]:
        base = off(ARMOR_TABLES[slot])
        by_val = {}
        for eid in range(400):
            o = base + eid * ARMOR_ENTRY_SIZE
            entry = ram[o:o + ARMOR_ENTRY_SIZE]
            model_m = struct.unpack_from("<h", entry, 0)[0]
            if model_m == 0 and entry[4] == 0:
                continue
            b19 = entry[19]
            rarity = entry[5]
            name = eid_names[slot].get(eid, f"(eid {eid})")
            by_val.setdefault(b19, []).append((eid, name, rarity))

        print(f"\n{'='*60}")
        print(f"{slot.upper()} - byte +19 distribution:")
        for val in sorted(by_val):
            entries = by_val[val]
            sample = entries[:5]
            names = ', '.join(f"{n}(r{r})" for _, n, r in sample)
            more = f" +{len(entries)-5} more" if len(entries) > 5 else ""
            print(f"  Value {val}: {len(entries):3d} entries — {names}{more}")


if __name__ == "__main__":
    main()

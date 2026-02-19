#!/opt/homebrew/bin/python3
"""Comprehensive search of ALL armor tables for Rath Soul and Black armor entries.
Searches LEGS, CHEST, ARMS, WAIST, HEAD tables and generates CWCheat lines."""

import struct
import zstandard

# ─── Constants ────────────────────────────────────────────────────────────────
STATE_PATH = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
ENTRY_SIZE = 40

# Table base addresses (PSP addresses)
TABLES = {
    "HEAD":  0x08960750,
    "CHEST": 0x08964B70,
    "ARMS":  0x08968D10,
    "WAIST": 0x0896CD48,
    "LEGS":  0x08970D30,
}

# Expected model IDs from website filenames
RATH_SOUL_MODELS = {
    "HEAD":  {"BM": {"m": 96, "f": 96}, "GN": {"m": 97, "f": 97}},
    "CHEST": {"BM": {"m": 92, "f": 90}, "GN": {"m": 93, "f": 91}},
    "ARMS":  {"BM": {"m": 89, "f": 89}, "GN": {"m": 90, "f": 90}},
    "WAIST": {"BM": {"m": 76, "f": 76}, "GN": {"m": 77, "f": 77}},
    "LEGS":  {"BM": {"m": 67, "f": 67}, "GN": {"m": 67, "f": 67}},
}

BLACK_MODELS = {
    "HEAD":  {"BM": {"m": 50, "f": 50}, "GN": {"m": 51, "f": 51}},
    "CHEST": {"BM": {"m": 48, "f": 48}, "GN": {"m": 49, "f": 49}},
    "ARMS":  {"BM": {"m": 47, "f": 47}, "GN": {"m": 48, "f": 48}},
    "WAIST": {"BM": {"m": 36, "f": 34}, "GN": {"m": 35, "f": 37}},
    "LEGS":  {"BM": {"m": 35, "f": 35}, "GN": {"m": 35, "f": 35}},
}


# ─── Helpers ──────────────────────────────────────────────────────────────────
def psp_to_state(psp_addr):
    return psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE


def load_state():
    with open(STATE_PATH, 'rb') as f:
        raw = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(raw[0xB0:], max_output_size=128 * 1024 * 1024)


def read_s16(data, psp):
    off = psp_to_state(psp)
    return struct.unpack_from('<h', data, off)[0]


def read_u8(data, psp):
    off = psp_to_state(psp)
    return data[off]


def read_raw(data, psp, size):
    off = psp_to_state(psp)
    return data[off:off + size]


def dump_entry(data, table_base, eid, label=""):
    addr = table_base + eid * ENTRY_SIZE
    raw = read_raw(data, addr, ENTRY_SIZE)
    model_m = struct.unpack_from('<h', raw, 0)[0]
    model_f = struct.unpack_from('<h', raw, 2)[0]
    flag = raw[4]
    rarity = raw[5]
    first8_hex = raw[:8].hex()

    print(f"  [{eid:>3}] {label:<30s} addr=0x{addr:08X}  model_m={model_m:>4}  model_f={model_f:>4}"
          f"  flag=0x{flag:02X}  rarity={rarity}  first8={first8_hex}")
    return model_m, model_f, addr, raw


def search_table(data, table_name, table_base, target_models_m, target_models_f=None,
                 max_entries=401, label=""):
    """Search a table for entries where model_m or model_f matches given sets."""
    if target_models_f is None:
        target_models_f = target_models_m
    matches = []
    for eid in range(max_entries):
        addr = table_base + eid * ENTRY_SIZE
        raw = read_raw(data, addr, ENTRY_SIZE)
        model_m = struct.unpack_from('<h', raw, 0)[0]
        model_f = struct.unpack_from('<h', raw, 2)[0]
        if model_m in target_models_m or model_f in target_models_f:
            flag = raw[4]
            first8_hex = raw[:8].hex()
            print(f"  [{eid:>3}] model_m={model_m:>4}  model_f={model_f:>4}"
                  f"  flag=0x{flag:02X}  first8={first8_hex}  {label}")
            matches.append((eid, model_m, model_f, addr, raw))
    return matches


def dump_raw_entry(data, table_base, eid, label=""):
    addr = table_base + eid * ENTRY_SIZE
    raw = read_raw(data, addr, ENTRY_SIZE)
    model_m = struct.unpack_from('<h', raw, 0)[0]
    model_f = struct.unpack_from('<h', raw, 2)[0]
    print(f"  [{eid:>3}] {label}")
    print(f"    addr=0x{addr:08X}  model_m={model_m}  model_f={model_f}")
    print(f"    raw 40 bytes: {raw.hex()}")
    # Also show as u16 array
    u16s = [struct.unpack_from('<H', raw, i)[0] for i in range(0, 40, 2)]
    print(f"    u16: {u16s}")
    return model_m, model_f, addr, raw


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("Loading save state...")
    data = load_state()
    print(f"Decompressed: {len(data)} bytes\n")

    # Collect all found Rath Soul and Black entries for CWCheat generation
    rath_entries = {}  # key: (slot, variant) -> (eid, model_m, model_f, addr)
    black_entries = {}

    # ════════════════════════════════════════════════════════════════════════
    # TASK 1: Search LEGS table for Rathalos Soul legs (model 67)
    # ════════════════════════════════════════════════════════════════════════
    print("=" * 80)
    print("TASK 1: Search LEGS table (0x08970D30) for Rath Soul legs (model 67)")
    print("=" * 80)
    matches = search_table(data, "LEGS", TABLES["LEGS"], {67}, label="(model 67 = Rath Soul Legs)")
    print(f"  Found {len(matches)} entries with model 67\n")
    for eid, mm, mf, addr, raw in matches:
        # Determine BM vs GN (if they differ)
        # For legs, BM and GN might share model 67
        # We check the flag byte for clues: typically BM=0x01, GN=0x02 or similar
        flag = raw[4]
        variant = "BM" if flag in (0x00, 0x01) else "GN" if flag == 0x02 else f"flag=0x{flag:02X}"
        if ("LEGS", "BM") not in rath_entries and mm == 67:
            rath_entries[("LEGS", "BM")] = (eid, mm, mf, addr)
        elif ("LEGS", "GN") not in rath_entries and mm == 67:
            rath_entries[("LEGS", "GN")] = (eid, mm, mf, addr)

    # ════════════════════════════════════════════════════════════════════════
    # TASK 2: Search LEGS table for Black armor legs (model 35)
    # ════════════════════════════════════════════════════════════════════════
    print("=" * 80)
    print("TASK 2: Search LEGS table for Black armor legs (model 35)")
    print("=" * 80)
    matches = search_table(data, "LEGS", TABLES["LEGS"], {35}, label="(model 35 = Black Legs)")
    print(f"  Found {len(matches)} entries with model 35\n")
    for eid, mm, mf, addr, raw in matches:
        flag = raw[4]
        if ("LEGS", "BM") not in black_entries and mm == 35:
            black_entries[("LEGS", "BM")] = (eid, mm, mf, addr)
        elif ("LEGS", "GN") not in black_entries and mm == 35:
            black_entries[("LEGS", "GN")] = (eid, mm, mf, addr)

    # ════════════════════════════════════════════════════════════════════════
    # TASK 3: Verify CHEST table entries
    # ════════════════════════════════════════════════════════════════════════
    print("=" * 80)
    print("TASK 3: Verify CHEST table (0x08964B70)")
    print("=" * 80)

    print("\n  --- Rath Soul CHEST entries (eid=99 BM, eid=100 GN from earlier) ---")
    mm99, mf99, addr99, _ = dump_entry(data, TABLES["CHEST"], 99, "Rath Soul Mail (BM)?")
    mm100, mf100, addr100, _ = dump_entry(data, TABLES["CHEST"], 100, "Rath Soul Vest (GN)?")
    if mm99 in (92, 93):
        rath_entries[("CHEST", "BM")] = (99, mm99, mf99, addr99)
    if mm100 in (92, 93):
        rath_entries[("CHEST", "GN")] = (100, mm100, mf100, addr100)

    print("\n  --- Search CHEST for Black armor (model_m in {48, 49}) ---")
    matches = search_table(data, "CHEST", TABLES["CHEST"], {48, 49}, label="(Black Chest)")
    print(f"  Found {len(matches)} entries\n")
    for eid, mm, mf, addr, raw in matches:
        if mm == 48 and ("CHEST", "BM") not in black_entries:
            black_entries[("CHEST", "BM")] = (eid, mm, mf, addr)
        elif mm == 49 and ("CHEST", "GN") not in black_entries:
            black_entries[("CHEST", "GN")] = (eid, mm, mf, addr)
        elif mm == 48 and ("CHEST", "BM") in black_entries:
            # Could be GN with same model? Or duplicate
            pass

    # ════════════════════════════════════════════════════════════════════════
    # TASK 4: Verify ARMS table entries
    # ════════════════════════════════════════════════════════════════════════
    print("=" * 80)
    print("TASK 4: Verify ARMS table (0x08968D10)")
    print("=" * 80)

    print("\n  --- Rath Soul ARMS eid=98 (BM confirmed model 89/89) ---")
    mm98, mf98, addr98, _ = dump_entry(data, TABLES["ARMS"], 98, "Rath Soul Braces (BM)")
    rath_entries[("ARMS", "BM")] = (98, mm98, mf98, addr98)

    print("\n  --- Rath Soul ARMS eid=115 (GN, reported model_f=0 issue) ---")
    dump_raw_entry(data, TABLES["ARMS"], 115, "Rath Soul Guards (GN)?")

    print("\n  --- Search ARMS for model_m==90 (Rath Soul GN expected) ---")
    matches = search_table(data, "ARMS", TABLES["ARMS"], {90}, label="(model 90 = Rath Soul GN Arms?)")
    print(f"  Found {len(matches)} entries\n")
    for eid, mm, mf, addr, raw in matches:
        if mm == 90 and ("ARMS", "GN") not in rath_entries:
            rath_entries[("ARMS", "GN")] = (eid, mm, mf, addr)

    print("  --- Search ARMS for Black arms (model_m in {47, 48}) ---")
    matches = search_table(data, "ARMS", TABLES["ARMS"], {47, 48}, label="(Black Arms)")
    print(f"  Found {len(matches)} entries\n")
    for eid, mm, mf, addr, raw in matches:
        if mm == 47 and ("ARMS", "BM") not in black_entries:
            black_entries[("ARMS", "BM")] = (eid, mm, mf, addr)
        elif mm == 48 and ("ARMS", "GN") not in black_entries:
            black_entries[("ARMS", "GN")] = (eid, mm, mf, addr)

    # ════════════════════════════════════════════════════════════════════════
    # Also search HEAD and WAIST for completeness
    # ════════════════════════════════════════════════════════════════════════
    print("=" * 80)
    print("BONUS: Search HEAD table (0x08960750)")
    print("=" * 80)

    print("\n  --- Search HEAD for Rath Soul (model_m in {96, 97}) ---")
    matches = search_table(data, "HEAD", TABLES["HEAD"], {96, 97}, label="(Rath Soul Head)")
    for eid, mm, mf, addr, raw in matches:
        if mm == 96 and ("HEAD", "BM") not in rath_entries:
            rath_entries[("HEAD", "BM")] = (eid, mm, mf, addr)
        elif mm == 97 and ("HEAD", "GN") not in rath_entries:
            rath_entries[("HEAD", "GN")] = (eid, mm, mf, addr)

    print("\n  --- Search HEAD for Black armor (model_m in {50, 51}) ---")
    matches = search_table(data, "HEAD", TABLES["HEAD"], {50, 51}, label="(Black Head)")
    for eid, mm, mf, addr, raw in matches:
        if mm == 50 and ("HEAD", "BM") not in black_entries:
            black_entries[("HEAD", "BM")] = (eid, mm, mf, addr)
        elif mm == 51 and ("HEAD", "GN") not in black_entries:
            black_entries[("HEAD", "GN")] = (eid, mm, mf, addr)

    print()
    print("=" * 80)
    print("BONUS: Search WAIST table (0x0896CD48)")
    print("=" * 80)

    print("\n  --- Search WAIST for Rath Soul (model_m in {76, 77}) ---")
    matches = search_table(data, "WAIST", TABLES["WAIST"], {76, 77}, label="(Rath Soul Waist)")
    for eid, mm, mf, addr, raw in matches:
        if mm == 76 and ("WAIST", "BM") not in rath_entries:
            rath_entries[("WAIST", "BM")] = (eid, mm, mf, addr)
        elif mm == 77 and ("WAIST", "GN") not in rath_entries:
            rath_entries[("WAIST", "GN")] = (eid, mm, mf, addr)

    print("\n  --- Search WAIST for Black armor ---")
    # Black waist: BM m=36 f=34, GN m=35 f=37
    matches = search_table(data, "WAIST", TABLES["WAIST"], {35, 36}, label="(Black Waist)")
    for eid, mm, mf, addr, raw in matches:
        if mm == 36 and ("WAIST", "BM") not in black_entries:
            black_entries[("WAIST", "BM")] = (eid, mm, mf, addr)
        elif mm == 35 and ("WAIST", "GN") not in black_entries:
            black_entries[("WAIST", "GN")] = (eid, mm, mf, addr)

    # ════════════════════════════════════════════════════════════════════════
    # TASK 5: Generate CWCheat lines
    # ════════════════════════════════════════════════════════════════════════
    print()
    print("=" * 80)
    print("TASK 5: CWCheat Lines - Rath Soul -> Black Armor Transmog")
    print("=" * 80)

    print("\n  --- All Rath Soul entries found ---")
    for key in sorted(rath_entries.keys()):
        eid, mm, mf, addr = rath_entries[key]
        print(f"  {key[0]:>5s} {key[1]:>2s}: eid={eid:>3}  model_m={mm:>4}  model_f={mf:>4}  addr=0x{addr:08X}")

    print("\n  --- All Black armor entries found ---")
    for key in sorted(black_entries.keys()):
        eid, mm, mf, addr = black_entries[key]
        print(f"  {key[0]:>5s} {key[1]:>2s}: eid={eid:>3}  model_m={mm:>4}  model_f={mf:>4}  addr=0x{addr:08X}")

    print("\n  --- CWCheat Patch Lines ---")
    print()

    all_cheats = []
    slot_order = ["HEAD", "CHEST", "ARMS", "WAIST", "LEGS"]
    variant_order = ["BM", "GN"]

    for slot in slot_order:
        for variant in variant_order:
            key = (slot, variant)
            if key not in rath_entries:
                print(f"  {slot:>5s} {variant:>2s}: *** NOT FOUND in rath_entries ***")
                continue
            if key not in black_entries:
                # Try to find a fallback - for LEGS where BM and GN may share model
                fallback = (slot, "BM") if variant == "GN" else None
                if fallback and fallback in black_entries:
                    print(f"  {slot:>5s} {variant:>2s}: Using {fallback} Black entry as fallback")
                    black_entries[key] = black_entries[fallback]
                else:
                    print(f"  {slot:>5s} {variant:>2s}: *** NOT FOUND in black_entries ***")
                    continue

            r_eid, r_mm, r_mf, r_addr = rath_entries[key]
            b_eid, b_mm, b_mf, b_addr = black_entries[key]

            # CWCheat: write Black model IDs over Rath Soul model IDs
            # Address: r_addr is where model_m (s16) and model_f (s16) are stored
            # We write a 32-bit value: (target_model_f << 16) | (target_model_m & 0xFFFF)
            target_m = b_mm
            target_f = b_mf
            value = ((target_f & 0xFFFF) << 16) | (target_m & 0xFFFF)
            offset = r_addr - 0x08800000
            cheat_line = f"_L 0x2{offset:07X} 0x{value:08X}"

            desc = (f"{slot:>5s} {variant:>2s}: eid={r_eid:>3} (m={r_mm:>3},f={r_mf:>3}) "
                    f"-> Black (m={b_mm:>3},f={b_mf:>3})  {cheat_line}")
            print(f"  {desc}")
            all_cheats.append((slot, variant, cheat_line, r_eid, r_mm, r_mf, b_mm, b_mf))

    # ════════════════════════════════════════════════════════════════════════
    # Final summary
    # ════════════════════════════════════════════════════════════════════════
    print()
    print("=" * 80)
    print("FINAL SUMMARY: CWCheat lines for Rath Soul -> Black transmog")
    print("=" * 80)
    print()
    print("_S ULJM-05500")
    print("_G Monster Hunter Freedom Unite")
    print("_C0 Rath Soul -> Black Transmog")
    for slot, variant, line, r_eid, r_mm, r_mf, b_mm, b_mf in all_cheats:
        print(f"{line}  // {slot} {variant}: eid={r_eid} ({r_mm},{r_mf})->({b_mm},{b_mf})")

    print()
    print(f"Total cheat lines: {len(all_cheats)}")
    print()

    # ════════════════════════════════════════════════════════════════════════
    # Extra debug: show what we think each Rath Soul entry is
    # ════════════════════════════════════════════════════════════════════════
    print("=" * 80)
    print("DEBUG: Full entry dump for all Rath Soul entries found")
    print("=" * 80)
    for key in sorted(rath_entries.keys()):
        eid, mm, mf, addr = rath_entries[key]
        slot = key[0]
        print(f"\n  {key[0]} {key[1]} (eid={eid}):")
        dump_raw_entry(data, TABLES[slot], eid, f"Rath Soul {slot} {key[1]}")


if __name__ == "__main__":
    main()

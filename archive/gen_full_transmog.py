#!/opt/homebrew/bin/python3
"""Generate CWCheat for full Rathalos Soul -> Black armor transmog.
Search ArmorData tables for all slots to find equip_ids by model ID."""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
ENTRY_SIZE = 40

def load_state(slot):
    return zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_{slot}.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

def read_s16(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<h', data, off)[0]

def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]

def main():
    data = load_state(0)

    # Pointer table at 0x08975970
    PTR_TABLE = 0x08975970
    SLOT_INFO = {
        1: ("HEAD",  "hair"),
        2: ("CHEST", "body"),
        3: ("ARMS",  "arm"),
        4: ("WAIST", "wst"),
        5: ("LEGS",  "reg"),  # type2=5 might not use this ptr table
    }

    # From website - model numbers from filenames
    # Rathalos Soul (Blademaster / Gunner variants)
    rath_soul_models = {
        "HEAD":  {"BM": {"m": 96, "f": 96}, "GN": {"m": 97, "f": 97}},  # Helm / Cap
        "CHEST": {"BM": {"m": 92, "f": 90}, "GN": {"m": 93, "f": 91}},  # Mail / Vest
        "ARMS":  {"BM": {"m": 89, "f": 89}, "GN": {"m": 90, "f": 90}},  # Braces / Guards
        "WAIST": {"BM": {"m": 76, "f": 76}, "GN": {"m": 77, "f": 77}},  # Coil / Coat
        "LEGS":  {"BM": {"m": 67, "f": 67}, "GN": {"m": 67, "f": 67}},  # Leggings (same model?)
    }

    # Black armor
    black_models = {
        "HEAD":  {"BM": {"m": 50, "f": 50}, "GN": {"m": 51, "f": 51}},  # Head / Face
        "CHEST": {"BM": {"m": 48, "f": 48}, "GN": {"m": 49, "f": 49}},  # Hide / Skin
        "ARMS":  {"BM": {"m": 47, "f": 47}, "GN": {"m": 48, "f": 48}},  # Claw / Fist
        "WAIST": {"BM": {"m": 36, "f": 34}, "GN": {"m": 35, "f": 37}},  # Scale/Spine
        "LEGS":  {"BM": {"m": 35, "f": 35}, "GN": {"m": 35, "f": 35}},  # Legs (same model?)
    }

    # Search each slot's ArmorData table
    print("=== Searching ArmorData tables for Rathalos Soul entries ===\n")

    all_patches = []

    for type2 in range(1, 5):  # HEAD, CHEST, ARMS, WAIST (skip LEGS for now)
        slot_name = SLOT_INFO[type2][0]
        table_ptr = read_u32(data, PTR_TABLE + type2 * 4)
        print(f"--- {slot_name} (type2={type2}), table at 0x{table_ptr:08X} ---")

        # Search for Rath Soul entries by matching model IDs
        rath_models = rath_soul_models[slot_name]
        blk_models = black_models[slot_name]

        for eid in range(400):
            addr = table_ptr + eid * ENTRY_SIZE
            model_m = read_s16(data, addr)
            model_f = read_s16(data, addr + 2)

            # Check BM variant
            if model_m == rath_models["BM"]["m"] and model_f == rath_models["BM"]["f"]:
                target_m = blk_models["BM"]["m"]
                target_f = blk_models["BM"]["f"]
                target_u32 = (target_f << 16) | (target_m & 0xFFFF)
                offset = addr - 0x08800000
                print(f"  eid={eid}: model_m={model_m}, model_f={model_f} -> "
                      f"Rath Soul {slot_name} (Blademaster)")
                print(f"    Replace with Black model_m={target_m}, model_f={target_f}")
                print(f"    CWCheat: _L 0x2{offset:07X} 0x{target_u32:08X}")
                all_patches.append((slot_name, "BM", eid, addr, offset, target_u32,
                                    model_m, model_f, target_m, target_f))

            # Check GN variant
            if model_m == rath_models["GN"]["m"] and model_f == rath_models["GN"]["f"]:
                target_m = blk_models["GN"]["m"]
                target_f = blk_models["GN"]["f"]
                target_u32 = (target_f << 16) | (target_m & 0xFFFF)
                offset = addr - 0x08800000
                print(f"  eid={eid}: model_m={model_m}, model_f={model_f} -> "
                      f"Rath Soul {slot_name} (Gunner)")
                print(f"    Replace with Black model_m={target_m}, model_f={target_f}")
                print(f"    CWCheat: _L 0x2{offset:07X} 0x{target_u32:08X}")
                all_patches.append((slot_name, "GN", eid, addr, offset, target_u32,
                                    model_m, model_f, target_m, target_f))
        print()

    # LEGS uses a different table (type2=5 handler is different)
    # Let's search anyway with the pointer from the table
    # Actually type2=5 in the pointer table had 0x02030007 which is NOT a valid address
    # Legs use a different code path. Let me search all tables for the leg model IDs
    print("--- LEGS (type2=5, different code path) ---")
    print("  Legs uses separate handler. Searching HEAD table area for leg-like entries...")

    # The legs table might be at a completely different location
    # Let me search the EBOOT data section for the leg model values
    # Legs: Rath Soul m_reg067 = model 67
    # Let me try to find it by scanning wider data range
    for base_addr in range(0x08960000, 0x08980000, 4):
        # Try if this could be a table base where entry*40 gives model_m=67
        # For some equip_id around 100, addr = base + eid * 40
        for eid in range(80, 130):
            addr = base_addr + eid * ENTRY_SIZE
            off = addr - PSP_RAM_START + RAM_BASE_IN_STATE
            if off + 4 > len(data):
                continue
            model_m = read_s16(data, addr)
            model_f = read_s16(data, addr + 2)
            if model_m == 67 and model_f == 67:
                # Could be Rath Soul Legs - verify by checking neighboring entries
                # Check if eid-1 has a reasonable model ID too
                prev_m = read_s16(data, addr - ENTRY_SIZE)
                next_m = read_s16(data, addr + ENTRY_SIZE)
                if 0 < prev_m < 400 and 0 < next_m < 400:
                    if base_addr not in [0x08960750, 0x08964B70, 0x08968D10, 0x0896CD48]:
                        print(f"  Possible LEGS table: base=0x{base_addr:08X}, eid={eid}, "
                              f"model_m={model_m}, model_f={model_f}")
                        print(f"    prev_eid model_m={prev_m}, next_eid model_m={next_m}")

    # Alternative approach: search for type2=5 handler's table reference
    # Let's look at the LEGS handler code at 0x0885D0D0
    print(f"\n  Examining LEGS handler at 0x0885D0D0:")
    print(f"  This handler reads decorations (lhu at +6), not model IDs.")
    print(f"  The actual LEGS model loading likely uses the same ArmorData approach.")

    # Let me check the other pointer table entries more carefully
    # type2=0 table was at 0x08970D30 - let's check if legs data is there
    type0_table = read_u32(data, PTR_TABLE + 0 * 4)
    print(f"\n  type2=0 table at 0x{type0_table:08X}:")
    for eid in range(80, 130):
        addr = type0_table + eid * ENTRY_SIZE
        model_m = read_s16(data, addr)
        model_f = read_s16(data, addr + 2)
        if model_m == 67:
            print(f"    eid={eid}: model_m={model_m}, model_f={model_f}")

    # Also check what the legs handler actually does
    # type2=5 at PTR_TABLE: value was 0x02030007 - not a valid address!
    # type2=6 at PTR_TABLE: value was 0x04030002 - not valid either!
    # These look like flag values, not pointers. type2=5,6 use different code.
    # But the jump table sends type2=5 and type2=6 to handler 0x0885D0D0
    # which handles decorations, not model lookup.

    # For model lookup, legs probably use a separate table.
    # Let me search ALL of data area for model_m=67 paired with model_f=67
    print(f"\n  Brute-force search for model pair (67,67) in data area:")
    for addr in range(0x08960000, 0x089A0000, 2):
        m = read_s16(data, addr)
        f = read_s16(data, addr + 2)
        if m == 67 and f == 67:
            print(f"    0x{addr:08X}: model_m=67, model_f=67")

    # Print summary
    print(f"\n{'='*80}")
    print(f"=== SUMMARY: CWCheat lines for Rath Soul -> Black transmog ===")
    print(f"{'='*80}\n")
    for slot, variant, eid, addr, offset, target, om, of, tm, tf in all_patches:
        vname = "Blademaster" if variant == "BM" else "Gunner"
        print(f"  ; {slot} ({vname}) eid={eid}: model ({om},{of}) -> ({tm},{tf})")
        print(f"  _L 0x2{offset:07X} 0x{target:08X}")

if __name__ == '__main__':
    main()

#!/opt/homebrew/bin/python3
"""Analyze the invisible Mafumofu HEAD cheat to understand memory layout.

Cheat for invisible Mafumofu HEAD:
  Line 1: writes 0x00000275 to PSP 0x08A35890  (runtime data area)
  Line 2: writes 0x03440275 to PSP 0x0912F54C  (could be a table)

0x0275 = 629, 0x0344 = 836

Known FUComplete tables (u16 entries, indexed by equip_id):
  TABLE_A (file_group):  0x089972AC
  TABLE_B (model_index): 0x08997BA8
  TABLE_E (texture):     0x0899851C
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

# FUComplete tables
TABLE_A = 0x089972AC  # file_group (u16 entries)
TABLE_B = 0x08997BA8  # model_index (u16 entries)
TABLE_E = 0x0899851C  # texture (u16 entries)

# Cheat addresses
CHEAT_ADDR_1 = 0x08A35890  # runtime data - writes 0x00000275
CHEAT_ADDR_2 = 0x0912F54C  # table area  - writes 0x03440275
CHEAT_VAL_1  = 0x00000275
CHEAT_VAL_2  = 0x03440275

# Key equip IDs
MAFUMOFU_HEAD = 252
RATH_SOUL_CAP = 101
RATH_SOUL_HELM = 102


def psp_to_state(psp_addr):
    return psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE


def decompress_state(filepath):
    with open(filepath, 'rb') as f:
        raw = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(raw[0xB0:], max_output_size=128 * 1024 * 1024)


def read_u32(data, psp_addr):
    off = psp_to_state(psp_addr)
    if off < 0 or off + 4 > len(data):
        return None
    return struct.unpack_from('<I', data, off)[0]


def read_u16(data, psp_addr):
    off = psp_to_state(psp_addr)
    if off < 0 or off + 2 > len(data):
        return None
    return struct.unpack_from('<H', data, off)[0]


def hex_dump_region(data, psp_start, psp_end, step=4, label=""):
    """Dump u32 values in a PSP address range."""
    if label:
        print(f"\n  {label}")
    for addr in range(psp_start, psp_end, step):
        val = read_u32(data, addr)
        if val is None:
            print(f"    0x{addr:08X}: OUT OF RANGE")
        else:
            hi16 = (val >> 16) & 0xFFFF
            lo16 = val & 0xFFFF
            print(f"    0x{addr:08X}: 0x{val:08X}  (u16: {lo16:5d}, {hi16:5d}  |  dec: {val})")


def main():
    print("=" * 78)
    print("  MHFU Invisible Mafumofu HEAD Cheat Analysis")
    print("=" * 78)
    print()
    print("Cheat code:")
    print(f"  Line 1: PSP 0x{CHEAT_ADDR_1:08X} = 0x{CHEAT_VAL_1:08X}  (u16 lo={CHEAT_VAL_1 & 0xFFFF} hi={CHEAT_VAL_1 >> 16})")
    print(f"  Line 2: PSP 0x{CHEAT_ADDR_2:08X} = 0x{CHEAT_VAL_2:08X}  (u16 lo={CHEAT_VAL_2 & 0xFFFF} hi={CHEAT_VAL_2 >> 16})")
    print()

    # Load both states
    print("Loading state 0 (Rath Soul equipped)...")
    state0 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")
    print(f"  Decompressed: {len(state0)} bytes ({len(state0)/(1024*1024):.1f} MB)")

    print("Loading state 1 (Mafumofu equipped)...")
    state1 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_1.ppst")
    print(f"  Decompressed: {len(state1)} bytes ({len(state1)/(1024*1024):.1f} MB)")

    # =========================================================================
    # TASK 1: Examine the runtime address 0x08A35890
    # =========================================================================
    print()
    print("=" * 78)
    print("  TASK 1: Runtime address 0x08A35890 (cheat writes 0x00000275)")
    print("=" * 78)

    hex_dump_region(state0, 0x08A35880, 0x08A358C4, label="State 0 (Rath Soul equipped) -- 0x08A35880..0x08A358C0:")
    hex_dump_region(state1, 0x08A35880, 0x08A358C4, label="State 1 (Mafumofu equipped) -- 0x08A35880..0x08A358C0:")

    # Highlight the specific address
    val0 = read_u32(state0, CHEAT_ADDR_1)
    val1 = read_u32(state1, CHEAT_ADDR_1)
    print(f"\n  ** 0x{CHEAT_ADDR_1:08X} comparison:")
    print(f"     State 0 (Rath Soul): 0x{val0:08X}  (lo={val0 & 0xFFFF}, hi={val0 >> 16})")
    print(f"     State 1 (Mafumofu):  0x{val1:08X}  (lo={val1 & 0xFFFF}, hi={val1 >> 16})")
    print(f"     Cheat writes:        0x{CHEAT_VAL_1:08X}  (lo=629, hi=0)")
    if val0 != val1:
        print(f"     => VALUES DIFFER between states -- this is equipment-dependent!")
    else:
        print(f"     => Values are THE SAME in both states.")

    # =========================================================================
    # TASK 2: Examine the table address 0x0912F54C
    # =========================================================================
    print()
    print("=" * 78)
    print("  TASK 2: Table address 0x0912F54C (cheat writes 0x03440275)")
    print("=" * 78)

    hex_dump_region(state0, 0x0912F540, 0x0912F564, label="State 0 -- 0x0912F540..0x0912F560:")
    hex_dump_region(state1, 0x0912F540, 0x0912F564, label="State 1 -- 0x0912F540..0x0912F560:")

    val0_t2 = read_u32(state0, CHEAT_ADDR_2)
    val1_t2 = read_u32(state1, CHEAT_ADDR_2)
    print(f"\n  ** 0x{CHEAT_ADDR_2:08X} comparison:")
    print(f"     State 0: 0x{val0_t2:08X}")
    print(f"     State 1: 0x{val1_t2:08X}")
    print(f"     Cheat:   0x{CHEAT_VAL_2:08X}")
    if val0_t2 == val1_t2:
        print(f"     => Values are THE SAME -- likely a static table.")
    else:
        print(f"     => VALUES DIFFER -- runtime data, changes with equipment.")

    # --- Hypothesis A: 4-byte entries, table indexed by equip_id ---
    base_4byte = CHEAT_ADDR_2 - MAFUMOFU_HEAD * 4
    print(f"\n  Hypothesis A: 4-byte entries indexed by equip_id")
    print(f"    base = 0x{CHEAT_ADDR_2:08X} - {MAFUMOFU_HEAD}*4 = 0x{base_4byte:08X}")

    print(f"\n    Entries at base 0x{base_4byte:08X}:")
    test_eids_a = [0, 1, 2, 3, 4, 5, 101, 102, 250, 251, 252, 253]
    for eid in test_eids_a:
        addr = base_4byte + eid * 4
        val = read_u32(state0, addr)
        if val is not None:
            lo = val & 0xFFFF
            hi = (val >> 16) & 0xFFFF
            # Also read FUComplete TABLE_A and TABLE_B for comparison
            tbl_a = read_u16(state0, TABLE_A + eid * 2)
            tbl_b = read_u16(state0, TABLE_B + eid * 2)
            match_str = ""
            if tbl_a is not None and tbl_b is not None:
                if lo == tbl_b and hi == tbl_a:
                    match_str = " <-- MATCH: lo=TABLE_B, hi=TABLE_A"
                elif lo == tbl_a and hi == tbl_b:
                    match_str = " <-- MATCH: lo=TABLE_A, hi=TABLE_B"
                elif lo == tbl_a:
                    match_str = " (lo matches TABLE_A)"
                elif lo == tbl_b:
                    match_str = " (lo matches TABLE_B)"
            print(f"    eid={eid:4d}: 0x{val:08X}  lo={lo:5d} hi={hi:5d}  "
                  f"TABLE_A={tbl_a if tbl_a is not None else '?':>5}  "
                  f"TABLE_B={tbl_b if tbl_b is not None else '?':>5}{match_str}")

    # --- Hypothesis B: 2-byte entries, table indexed by equip_id ---
    base_2byte = CHEAT_ADDR_2 - MAFUMOFU_HEAD * 2
    print(f"\n  Hypothesis B: 2-byte entries indexed by equip_id")
    print(f"    base = 0x{CHEAT_ADDR_2:08X} - {MAFUMOFU_HEAD}*2 = 0x{base_2byte:08X}")
    print(f"    (u32 write would cover eid={MAFUMOFU_HEAD} and eid={MAFUMOFU_HEAD + 1})")

    print(f"\n    Entries at base 0x{base_2byte:08X}:")
    test_eids_b = [0, 1, 2, 3, 4, 5, 101, 102, 250, 251, 252, 253]
    for eid in test_eids_b:
        addr = base_2byte + eid * 2
        val = read_u16(state0, addr)
        if val is not None:
            tbl_a = read_u16(state0, TABLE_A + eid * 2)
            tbl_b = read_u16(state0, TABLE_B + eid * 2)
            match_str = ""
            if tbl_a is not None and tbl_b is not None:
                if val == tbl_a:
                    match_str = " <-- matches TABLE_A"
                elif val == tbl_b:
                    match_str = " <-- matches TABLE_B"
            print(f"    eid={eid:4d}: {val:5d} (0x{val:04X})  "
                  f"TABLE_A={tbl_a if tbl_a is not None else '?':>5}  "
                  f"TABLE_B={tbl_b if tbl_b is not None else '?':>5}{match_str}")

    # --- Hypothesis C: Check if any FUComplete table leads to 0x0912F54C ---
    print(f"\n  Hypothesis C: Does a FUComplete table point to 0x{CHEAT_ADDR_2:08X}?")
    fuc_tables = [
        ("TABLE_A (file_group)", TABLE_A),
        ("TABLE_B (model_index)", TABLE_B),
        ("TABLE_E (texture)", TABLE_E),
    ]
    for name, base in fuc_tables:
        for entry_size in [2, 4]:
            needed_offset = CHEAT_ADDR_2 - base
            if needed_offset >= 0 and needed_offset % entry_size == 0:
                implied_eid = needed_offset // entry_size
                print(f"    {name} + {MAFUMOFU_HEAD}*{entry_size} = 0x{base + MAFUMOFU_HEAD * entry_size:08X}"
                      f"  (target: 0x{CHEAT_ADDR_2:08X})")
                print(f"      If entry_size={entry_size}: implied eid for target = {implied_eid}")

    # --- Hypothesis D: Combined table (u16 file_group, u16 model_index) ---
    print(f"\n  Hypothesis D: Combined 4-byte table (u16 model_index, u16 file_group)")
    print(f"    Cheat writes 0x{CHEAT_VAL_2:08X} = (lo=0x0275={CHEAT_VAL_2 & 0xFFFF}, hi=0x0344={CHEAT_VAL_2 >> 16})")
    print(f"    If lo=model_index=629, hi=file_group=836:")

    # Read FUComplete values for Mafumofu HEAD (eid=252)
    mafu_tbl_a = read_u16(state0, TABLE_A + MAFUMOFU_HEAD * 2)
    mafu_tbl_b = read_u16(state0, TABLE_B + MAFUMOFU_HEAD * 2)
    print(f"    FUComplete TABLE_A[{MAFUMOFU_HEAD}] = {mafu_tbl_a}  (file_group)")
    print(f"    FUComplete TABLE_B[{MAFUMOFU_HEAD}] = {mafu_tbl_b}  (model_index)")
    print(f"    Cheat lo (0x0275) = {0x0275}  vs TABLE_B = {mafu_tbl_b}")
    print(f"    Cheat hi (0x0344) = {0x0344}  vs TABLE_A = {mafu_tbl_a}")

    if mafu_tbl_b == 0x0275:
        print(f"    => Cheat lo MATCHES TABLE_B (model_index)!")
    if mafu_tbl_a == 0x0344:
        print(f"    => Cheat hi MATCHES TABLE_A (file_group)!")

    # =========================================================================
    # TASK 3: Read entries from hypothesized table at base_4byte
    # =========================================================================
    print()
    print("=" * 78)
    print("  TASK 3: Validate table structure (base 0x{:08X}, 4-byte entries)".format(base_4byte))
    print("=" * 78)

    # Broader set of known armors
    known_armors = [
        (0, "Nothing"),
        (1, "Leather Helm"),
        (2, "Chainmail Head"),
        (3, "Alloy Helm"),
        (10, "Battle Helm"),
        (20, "Cephalos Cap"),
        (50, "Hunter's Helm"),
        (52, "Red Piercing"),
        (101, "Rath Soul Cap BM"),
        (102, "Rath Soul Helm GN"),
        (150, "Unknown150"),
        (200, "Unknown200"),
        (250, "Unknown250"),
        (251, "Mafumofu Hood v1"),
        (252, "Mafumofu Hood v2"),
        (253, "Unknown253"),
        (300, "Unknown300"),
        (350, "Unknown350"),
        (400, "Unknown400"),
        (434, "Last head armor?"),
    ]

    print(f"\n  Reading entries: base=0x{base_4byte:08X}, 4 bytes each")
    print(f"  {'eid':>5s}  {'addr':>10s}  {'value':>10s}  {'lo(u16)':>7s}  {'hi(u16)':>7s}  "
          f"{'TBL_A':>6s}  {'TBL_B':>6s}  {'TBL_E':>6s}  match?")
    print(f"  {'-'*5}  {'-'*10}  {'-'*10}  {'-'*7}  {'-'*7}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*20}")

    for eid, name in known_armors:
        addr = base_4byte + eid * 4
        val = read_u32(state0, addr)
        tbl_a = read_u16(state0, TABLE_A + eid * 2)
        tbl_b = read_u16(state0, TABLE_B + eid * 2)
        tbl_e = read_u16(state0, TABLE_E + eid * 2)

        if val is None:
            print(f"  {eid:5d}  0x{addr:08X}  OUT OF RANGE")
            continue

        lo = val & 0xFFFF
        hi = (val >> 16) & 0xFFFF

        matches = []
        if tbl_a is not None and tbl_b is not None:
            if lo == tbl_b and hi == tbl_a:
                matches.append("lo=B hi=A")
            else:
                if lo == tbl_a: matches.append("lo=A")
                if lo == tbl_b: matches.append("lo=B")
                if hi == tbl_a: matches.append("hi=A")
                if hi == tbl_b: matches.append("hi=B")
        if tbl_e is not None:
            if lo == tbl_e: matches.append("lo=E")
            if hi == tbl_e: matches.append("hi=E")

        match_str = ", ".join(matches) if matches else ""
        ta_str = f"{tbl_a:5d}" if tbl_a is not None else "    ?"
        tb_str = f"{tbl_b:5d}" if tbl_b is not None else "    ?"
        te_str = f"{tbl_e:5d}" if tbl_e is not None else "    ?"

        print(f"  {eid:5d}  0x{addr:08X}  0x{val:08X}  {lo:7d}  {hi:7d}  "
              f"{ta_str}  {tb_str}  {te_str}  {match_str}  ({name})")

    # =========================================================================
    # TASK 4: Check if table at 0x0912F54C is static (compare states)
    # =========================================================================
    print()
    print("=" * 78)
    print("  TASK 4: Is the table static? Compare states 0 and 1")
    print("=" * 78)

    # Check a range of entries around our target
    diff_count = 0
    same_count = 0
    test_range = range(0, min(435, 435))  # All head armors
    for eid in test_range:
        addr = base_4byte + eid * 4
        v0 = read_u32(state0, addr)
        v1 = read_u32(state1, addr)
        if v0 is not None and v1 is not None:
            if v0 != v1:
                diff_count += 1
                if diff_count <= 20:
                    print(f"  DIFF eid={eid:4d}: state0=0x{v0:08X} vs state1=0x{v1:08X}")
            else:
                same_count += 1

    print(f"\n  Total entries checked: {same_count + diff_count}")
    print(f"  Same: {same_count}, Different: {diff_count}")
    if diff_count == 0:
        print(f"  => Table is STATIC between the two states (equipment-independent).")
    else:
        print(f"  => Table has {diff_count} differences -- NOT fully static.")

    # Also specifically check the cheat target
    v0_cheat = read_u32(state0, CHEAT_ADDR_2)
    v1_cheat = read_u32(state1, CHEAT_ADDR_2)
    print(f"\n  0x{CHEAT_ADDR_2:08X} (eid={MAFUMOFU_HEAD}):")
    print(f"    State 0: 0x{v0_cheat:08X}")
    print(f"    State 1: 0x{v1_cheat:08X}")

    # =========================================================================
    # EXTRA: Look at runtime address more carefully
    # =========================================================================
    print()
    print("=" * 78)
    print("  EXTRA: Wider context around runtime address 0x08A35890")
    print("=" * 78)

    # Check what structure this might be part of
    # Typical equipment struct might have equip_id, visual_id, model data etc.
    # Read a wider region
    print("\n  State 0 (Rath Soul) - region 0x08A35860..0x08A35900:")
    for addr in range(0x08A35860, 0x08A35904, 4):
        val = read_u32(state0, addr)
        if val is not None:
            lo = val & 0xFFFF
            hi = (val >> 16) & 0xFFFF
            marker = " <-- CHEAT TARGET" if addr == CHEAT_ADDR_1 else ""
            print(f"    0x{addr:08X}: 0x{val:08X}  (u16: {lo:5d}, {hi:5d}){marker}")

    print("\n  State 1 (Mafumofu) - region 0x08A35860..0x08A35900:")
    for addr in range(0x08A35860, 0x08A35904, 4):
        val = read_u32(state1, addr)
        if val is not None:
            lo = val & 0xFFFF
            hi = (val >> 16) & 0xFFFF
            marker = " <-- CHEAT TARGET" if addr == CHEAT_ADDR_1 else ""
            print(f"    0x{addr:08X}: 0x{val:08X}  (u16: {lo:5d}, {hi:5d}){marker}")

    # Try to identify the struct by looking at diffs between states
    print("\n  Differences between states in 0x08A35800..0x08A35A00:")
    diff_addrs = []
    for addr in range(0x08A35800, 0x08A35A00, 4):
        v0 = read_u32(state0, addr)
        v1 = read_u32(state1, addr)
        if v0 is not None and v1 is not None and v0 != v1:
            diff_addrs.append(addr)
            lo0, hi0 = v0 & 0xFFFF, (v0 >> 16) & 0xFFFF
            lo1, hi1 = v1 & 0xFFFF, (v1 >> 16) & 0xFFFF
            marker = " <-- CHEAT TARGET" if addr == CHEAT_ADDR_1 else ""
            print(f"    0x{addr:08X}: 0x{v0:08X} -> 0x{v1:08X}  "
                  f"(lo: {lo0}->{lo1}, hi: {hi0}->{hi1}){marker}")

    if not diff_addrs:
        print("    No differences found in this range.")
    else:
        print(f"\n    Total diffs: {len(diff_addrs)}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print()
    print("=" * 78)
    print("  SUMMARY")
    print("=" * 78)
    print()
    print(f"  Cheat Line 1: 0x{CHEAT_ADDR_1:08X} = 0x{CHEAT_VAL_1:08X}")
    print(f"    State 0 value: 0x{val0:08X}")
    print(f"    State 1 value: 0x{val1:08X}")
    print(f"    This address {'DIFFERS' if val0 != val1 else 'is SAME'} between states.")
    print()
    print(f"  Cheat Line 2: 0x{CHEAT_ADDR_2:08X} = 0x{CHEAT_VAL_2:08X}")
    print(f"    State 0 value: 0x{v0_cheat:08X}")
    print(f"    State 1 value: 0x{v1_cheat:08X}")
    print(f"    This address {'DIFFERS' if v0_cheat != v1_cheat else 'is SAME'} between states.")
    print()

    # Final interpretation
    print("  Interpretation of cheat value 0x03440275:")
    print(f"    0x0275 = {0x0275} = model_index / TABLE_B value")
    print(f"    0x0344 = {0x0344} = file_group / TABLE_A value")
    print()

    # Check what "invisible" means -- 629 is the Mafumofu model_index
    # The cheat makes it invisible by writing Mafumofu's own values? That seems wrong.
    # Unless 629 is NOT what makes it invisible -- let's check what 275 means:
    # 0x0275 = 629 decimal. If this is a model_index, that's Mafumofu's model.
    # Wait - the cheat makes it INVISIBLE. So maybe 0x00000275 at the runtime addr
    # forces a specific value that the rendering code interprets as "no model"?
    # Or maybe the table entry is being replaced with a value that maps to empty model.

    # Let's check: what is at eid=0 (Nothing equipped)?
    nothing_val = read_u32(state0, base_4byte + 0 * 4)
    if nothing_val is not None:
        print(f"  Entry for eid=0 (Nothing): 0x{nothing_val:08X}")
        print(f"    lo={nothing_val & 0xFFFF}, hi={nothing_val >> 16}")

    # What about TABLE_A[0] and TABLE_B[0]?
    ta0 = read_u16(state0, TABLE_A + 0)
    tb0 = read_u16(state0, TABLE_B + 0)
    print(f"  TABLE_A[0] = {ta0}, TABLE_B[0] = {tb0}")
    print()

    # Check: for Rath Soul (eid=101), what does the table entry look like?
    rs_val = read_u32(state0, base_4byte + RATH_SOUL_CAP * 4)
    if rs_val is not None:
        print(f"  Entry for eid={RATH_SOUL_CAP} (Rath Soul Cap): 0x{rs_val:08X}")
        print(f"    lo={rs_val & 0xFFFF}, hi={rs_val >> 16}")
        rs_ta = read_u16(state0, TABLE_A + RATH_SOUL_CAP * 2)
        rs_tb = read_u16(state0, TABLE_B + RATH_SOUL_CAP * 2)
        print(f"    TABLE_A[{RATH_SOUL_CAP}]={rs_ta}, TABLE_B[{RATH_SOUL_CAP}]={rs_tb}")


if __name__ == "__main__":
    main()

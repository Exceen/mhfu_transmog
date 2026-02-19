#!/usr/bin/env python3
"""
Verify candidate weapon table at 0x0893E7F0 in MHFU save state.
Entry size = 8 bytes, indexed by weapon model number.
"""

import struct
import zstandard as zstd

PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
WEAPON_TABLE_PSP = 0x0893E7F0

STATE_0 = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"
STATE_1 = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_1.ppst"

MAX_DECOMPRESS = 128 * 1024 * 1024  # 128 MB
SKIP = 0xB0
ENTRY_SIZE = 8


def load_ram(path):
    """Load and decompress a PPSSPP save state, return RAM bytes."""
    with open(path, "rb") as f:
        raw = f.read()
    dctx = zstd.ZstdDecompressor()
    data = dctx.decompress(raw[SKIP:], max_output_size=MAX_DECOMPRESS)
    return data


def psp_to_offset(psp_addr):
    """Convert PSP address to offset in decompressed state data."""
    return (psp_addr - PSP_RAM_START) + RAM_BASE_IN_STATE


def read_entry(ram, index):
    """Read 8-byte entry at given index from the weapon table."""
    psp_addr = WEAPON_TABLE_PSP + index * ENTRY_SIZE
    off = psp_to_offset(psp_addr)
    raw = ram[off:off + ENTRY_SIZE]
    u16s = struct.unpack_from("<4H", raw)
    return psp_addr, raw, u16s


def main():
    print("=" * 70)
    print("Loading state 0...")
    ram0 = load_ram(STATE_0)
    print(f"  Decompressed size: {len(ram0):,} bytes")

    # =========================================================================
    # TASK 1: Dump entries at indices 0-25 and 240-245
    # =========================================================================
    print("\n" + "=" * 70)
    print("TASK 1: Dump entries at indices 0-25 and 240-245")
    print("=" * 70)

    for label, idx_range in [("Indices 0-25", range(0, 26)),
                              ("Indices 240-245", range(240, 246))]:
        print(f"\n--- {label} ---")
        print(f"{'Idx':>5}  {'PSP Addr':>10}  {'Raw Hex':>20}  {'u16[0]':>7} {'u16[1]':>7} {'u16[2]':>7} {'u16[3]':>7}")
        for i in idx_range:
            psp_addr, raw, u16s = read_entry(ram0, i)
            hex_str = raw.hex().upper()
            print(f"{i:5d}  0x{psp_addr:08X}  {hex_str:>20s}  {u16s[0]:7d} {u16s[1]:7d} {u16s[2]:7d} {u16s[3]:7d}")

    # =========================================================================
    # TASK 2: Verify with known weapons
    # =========================================================================
    print("\n" + "=" * 70)
    print("TASK 2: Verify with known weapons")
    print("=" * 70)

    known_weapons = [
        (21,  "Sieglinde (we021.pac)"),
        (242, "Black Fatalis Blade (we242.pac)"),
        (334, "Fatalis Buster (we334.pac)"),
    ]
    # Add indices 541-547
    for i in range(541, 548):
        known_weapons.append((i, f"Fatalis weapon? (we{i:03d}.pac)"))

    for idx, name in known_weapons:
        psp_addr, raw, u16s = read_entry(ram0, idx)
        hex_str = raw.hex().upper()
        print(f"\n  Index {idx}: {name}")
        print(f"    PSP addr: 0x{psp_addr:08X}")
        print(f"    Raw hex:  {hex_str}")
        print(f"    u16 vals: {u16s[0]:5d}  {u16s[1]:5d}  {u16s[2]:5d}  {u16s[3]:5d}")
        # Check if any u16 matches the index
        matches = [j for j, v in enumerate(u16s) if v == idx]
        if matches:
            print(f"    ** u16[{matches}] matches model index {idx}! **")
        else:
            print(f"    (no u16 field matches model index {idx})")

    # =========================================================================
    # TASK 3: Check if table is static (compare with state 1)
    # =========================================================================
    print("\n" + "=" * 70)
    print("TASK 3: Check if table is static (compare state 0 vs state 1)")
    print("=" * 70)

    try:
        print("Loading state 1...")
        ram1 = load_ram(STATE_1)
        print(f"  Decompressed size: {len(ram1):,} bytes")

        # Compare a wide range of entries (0-600)
        max_idx = 600
        diffs = 0
        for i in range(max_idx):
            _, raw0, _ = read_entry(ram0, i)
            psp_addr = WEAPON_TABLE_PSP + i * ENTRY_SIZE
            off = psp_to_offset(psp_addr)
            raw1 = ram1[off:off + ENTRY_SIZE]
            if raw0 != raw1:
                if diffs < 20:
                    print(f"  DIFF at index {i}: state0={raw0.hex()} vs state1={raw1.hex()}")
                diffs += 1
        if diffs == 0:
            print(f"  Table is IDENTICAL across states for indices 0-{max_idx-1}. Likely static!")
        else:
            print(f"  Found {diffs} differences across indices 0-{max_idx-1}.")
    except FileNotFoundError:
        print("  State 1 file not found, skipping comparison.")

    # =========================================================================
    # TASK 4: Read the 8 bytes at index 242
    # =========================================================================
    print("\n" + "=" * 70)
    print("TASK 4: Read entry at index 242 (Black Fatalis Blade)")
    print("=" * 70)

    idx242_addr = WEAPON_TABLE_PSP + 242 * ENTRY_SIZE
    print(f"  Computed PSP address: 0x{idx242_addr:08X}")
    print(f"  Expected:             0x0893EF80")
    psp_addr, raw, u16s = read_entry(ram0, 242)
    print(f"  Raw hex:  {raw.hex().upper()}")
    print(f"  u16 vals: {u16s[0]:5d}  {u16s[1]:5d}  {u16s[2]:5d}  {u16s[3]:5d}")
    print(f"  These 8 bytes would be written to replace index 21 (Sieglinde) for transmog.")

    # =========================================================================
    # TASK 5: Search for pointer-based weapon table structure
    # =========================================================================
    print("\n" + "=" * 70)
    print("TASK 5: Search for pointer-based weapon table (like armor)")
    print("=" * 70)
    print("  Scanning 0x08930000-0x08960000 for u32 pointers to tables")
    print("  with 40-byte entries where u16[0] at ptr and ptr+40 are in 1-600...")

    search_start_psp = 0x08930000
    search_end_psp = 0x08960000

    # Known armor table regions to exclude (approximate)
    # We'll just look for candidates
    candidates = []
    ram_len = len(ram0)

    for psp_scan in range(search_start_psp, search_end_psp, 4):
        off_scan = psp_to_offset(psp_scan)
        if off_scan + 4 > ram_len:
            break
        ptr_val = struct.unpack_from("<I", ram0, off_scan)[0]

        # Must be a valid PSP RAM pointer
        if ptr_val < 0x08800000 or ptr_val > 0x09F00000:
            continue
        # Must be 4-byte aligned
        if ptr_val & 3:
            continue

        target_off = psp_to_offset(ptr_val)
        if target_off + 42 > ram_len or target_off < 0:
            continue

        # Read u16[0] at target
        val0 = struct.unpack_from("<H", ram0, target_off)[0]
        # Read u16[0] at target + 40 (next entry if 40-byte stride)
        val40 = struct.unpack_from("<H", ram0, target_off + 40)[0]

        if 1 <= val0 <= 600 and 1 <= val40 <= 600:
            candidates.append((psp_scan, ptr_val, val0, val40))
            if len(candidates) >= 10:
                break

    if candidates:
        print(f"\n  Found {len(candidates)} candidates:")
        print(f"  {'Scan Addr':>12}  {'Ptr Value':>12}  {'u16@ptr':>8}  {'u16@ptr+40':>10}")
        for scan_addr, ptr_val, v0, v40 in candidates:
            print(f"  0x{scan_addr:08X}  0x{ptr_val:08X}  {v0:8d}  {v40:10d}")

        # For each candidate, dump the first few 40-byte entries
        for scan_addr, ptr_val, v0, v40 in candidates[:3]:
            print(f"\n  --- Candidate at scan 0x{scan_addr:08X} -> ptr 0x{ptr_val:08X} ---")
            print(f"  Dumping first 5 entries (40 bytes each):")
            for ei in range(5):
                entry_off = psp_to_offset(ptr_val) + ei * 40
                if entry_off + 40 > ram_len:
                    break
                entry_raw = ram0[entry_off:entry_off + 40]
                u16_vals = struct.unpack_from("<20H", entry_raw)
                entry_psp = ptr_val + ei * 40
                print(f"    Entry {ei} @ 0x{entry_psp:08X}: {entry_raw.hex()}")
                print(f"      u16: {list(u16_vals)}")
    else:
        print("  No candidates found with 40-byte stride.")

    # Also try other common entry sizes: 8, 12, 16, 20, 24, 28, 32, 36, 44, 48
    print("\n  Also trying other entry sizes (8,12,16,20,24,28,32,36,44,48)...")
    for entry_try in [8, 12, 16, 20, 24, 28, 32, 36, 44, 48]:
        candidates2 = []
        for psp_scan in range(search_start_psp, search_end_psp, 4):
            off_scan = psp_to_offset(psp_scan)
            if off_scan + 4 > ram_len:
                break
            ptr_val = struct.unpack_from("<I", ram0, off_scan)[0]
            if ptr_val < 0x08800000 or ptr_val > 0x09F00000:
                continue
            if ptr_val & 3:
                continue
            target_off = psp_to_offset(ptr_val)
            if target_off + entry_try + 2 > ram_len or target_off < 0:
                continue
            val0 = struct.unpack_from("<H", ram0, target_off)[0]
            val_next = struct.unpack_from("<H", ram0, target_off + entry_try)[0]
            if 1 <= val0 <= 600 and 1 <= val_next <= 600:
                candidates2.append((psp_scan, ptr_val, val0, val_next))
                if len(candidates2) >= 5:
                    break
        if candidates2:
            print(f"\n  Entry size {entry_try}: found {len(candidates2)} pointer candidates")
            for scan_addr, ptr_val, v0, vn in candidates2[:3]:
                print(f"    0x{scan_addr:08X} -> 0x{ptr_val:08X}  u16@0={v0}  u16@+{entry_try}={vn}")

    print("\n" + "=" * 70)
    print("Done.")


if __name__ == "__main__":
    main()

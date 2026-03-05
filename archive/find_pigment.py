#!/usr/bin/env python3
"""Compare 3 save states with different pigment colors to find the pigment address.

Slot 6 (file _5): orange pigment
Slot 7 (file _6): pink pigment
Slot 8 (file _7): red pigment
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
HEADER_SIZE = 0xB0
RAM_OFFSET = 0x48
PSP_RAM_START = 0x08000000

# Known equipment structure area (from modify_equip_id.py)
EQUIP_AREA_START = 0x090AF668
EQUIP_AREA_END = 0x090AF6C2


def load_ram(slot_file):
    path = f"{STATE_DIR}/ULJM05500_1.01_{slot_file}.ppst"
    print(f"  Loading {path}")
    with open(path, "rb") as f:
        raw = f.read()
    data = zstandard.ZstdDecompressor().decompress(raw[HEADER_SIZE:], max_output_size=256 * 1024 * 1024)
    return data[RAM_OFFSET:]


def off(psp_addr):
    return psp_addr - PSP_RAM_START


def main():
    print("Loading save states...")
    ram_orange = load_ram(5)  # slot 6 = orange
    ram_pink = load_ram(6)    # slot 7 = pink
    ram_red = load_ram(7)     # slot 8 = red

    size = min(len(ram_orange), len(ram_pink), len(ram_red))
    print(f"RAM size: {size:,} bytes\n")

    # Strategy: find bytes that differ across all 3 states
    # Focus on the area near the equipment structure first, then broaden
    # Color values are likely 1-4 bytes (RGB, RGBA, or a single hue byte)

    # Phase 1: Search near equipment structure (±4KB)
    search_ranges = [
        ("Near equipment (±4KB)", off(EQUIP_AREA_START) - 4096, off(EQUIP_AREA_END) + 4096),
        ("Near equipment (±16KB)", off(EQUIP_AREA_START) - 16384, off(EQUIP_AREA_END) + 16384),
        ("Character data area (0x090A0000-0x090C0000)", off(0x090A0000), off(0x090C0000)),
        ("Save data area (0x08880000-0x08900000)", off(0x08880000), off(0x08900000)),
    ]

    all_diffs = []

    for label, start, end in search_ranges:
        start = max(0, start)
        end = min(size, end)
        print(f"=== {label} (0x{start + PSP_RAM_START:08X} - 0x{end + PSP_RAM_START:08X}) ===")

        diffs = []
        for i in range(start, end):
            o = ram_orange[i]
            p = ram_pink[i]
            r = ram_red[i]
            if o != p or o != r or p != r:
                # All three different = most interesting for color
                all_three_diff = (o != p and o != r and p != r)
                diffs.append((i, o, p, r, all_three_diff))

        if not diffs:
            print("  No differences found.\n")
            continue

        three_way = [d for d in diffs if d[4]]
        two_way = [d for d in diffs if not d[4]]
        print(f"  {len(diffs)} differing bytes ({len(three_way)} all-three-different, {len(two_way)} two-way)")

        # Show all-three-different bytes (most likely color candidates)
        if three_way:
            print(f"\n  All-three-different bytes (best candidates):")
            for i, o, p, r, _ in three_way[:100]:
                psp = i + PSP_RAM_START
                print(f"    0x{psp:08X}: orange={o:3d} (0x{o:02X}), pink={p:3d} (0x{p:02X}), red={r:3d} (0x{r:02X})")

        # Also check for grouped diffs (consecutive bytes = likely a color struct)
        if diffs:
            groups = []
            current_group = [diffs[0]]
            for d in diffs[1:]:
                if d[0] == current_group[-1][0] + 1:
                    current_group.append(d)
                else:
                    if len(current_group) >= 2:
                        groups.append(current_group)
                    current_group = [d]
            if len(current_group) >= 2:
                groups.append(current_group)

            if groups:
                print(f"\n  Grouped consecutive diffs (likely structs):")
                for group in groups[:20]:
                    psp_start = group[0][0] + PSP_RAM_START
                    psp_end = group[-1][0] + PSP_RAM_START
                    print(f"    0x{psp_start:08X}-0x{psp_end:08X} ({len(group)} bytes):")
                    for i, o, p, r, three in group:
                        psp = i + PSP_RAM_START
                        marker = " ***" if three else ""
                        print(f"      0x{psp:08X}: orange={o:3d} (0x{o:02X}), pink={p:3d} (0x{p:02X}), red={r:3d} (0x{r:02X}){marker}")

        all_diffs.extend(diffs)
        print()

        # If we found good candidates in the first range, don't need to search further
        if three_way and label.startswith("Near equipment"):
            break

    # Summary: show best candidates (groups of 3-4 consecutive all-different bytes)
    if all_diffs:
        print("=" * 60)
        print("SUMMARY: Best pigment color candidates")
        print("=" * 60)
        # Deduplicate
        seen = set()
        unique = []
        for d in all_diffs:
            if d[0] not in seen:
                seen.add(d[0])
                unique.append(d)
        unique.sort(key=lambda x: x[0])

        # Find groups of 3-4 consecutive bytes where all three states differ
        groups_3way = []
        i = 0
        while i < len(unique):
            if unique[i][4]:  # all-three-different
                group = [unique[i]]
                j = i + 1
                while j < len(unique) and unique[j][0] == group[-1][0] + 1:
                    group.append(unique[j])
                    j += 1
                if len(group) >= 2:
                    groups_3way.append(group)
                i = j
            else:
                i += 1

        if groups_3way:
            for group in groups_3way:
                psp = group[0][0] + PSP_RAM_START
                vals_o = [d[1] for d in group]
                vals_p = [d[2] for d in group]
                vals_r = [d[3] for d in group]
                print(f"\n  0x{psp:08X} ({len(group)} bytes):")
                print(f"    Orange: {vals_o}")
                print(f"    Pink:   {vals_p}")
                print(f"    Red:    {vals_r}")

                # Check if these look like RGB values
                if len(group) >= 3:
                    print(f"    As RGB: orange=({vals_o[0]},{vals_o[1]},{vals_o[2]}), "
                          f"pink=({vals_p[0]},{vals_p[1]},{vals_p[2]}), "
                          f"red=({vals_r[0]},{vals_r[1]},{vals_r[2]})")
        else:
            print("  No strong candidates found. Try widening search or ensuring")
            print("  save states differ ONLY in pigment color.")


if __name__ == "__main__":
    main()

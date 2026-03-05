#!/usr/bin/env python3
"""Dump the area around the pigment candidates to understand the structure."""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
HEADER_SIZE = 0xB0
RAM_OFFSET = 0x48
PSP_RAM_START = 0x08000000


def load_ram(slot_file):
    path = f"{STATE_DIR}/ULJM05500_1.01_{slot_file}.ppst"
    with open(path, "rb") as f:
        raw = f.read()
    data = zstandard.ZstdDecompressor().decompress(raw[HEADER_SIZE:], max_output_size=256 * 1024 * 1024)
    return data[RAM_OFFSET:]


def off(psp_addr):
    return psp_addr - PSP_RAM_START


def dump_region(label, rams, psp_start, length):
    names = ["orange", "pink", "red"]
    print(f"\n{'=' * 70}")
    print(f"{label}: 0x{psp_start:08X} - 0x{psp_start + length:08X} ({length} bytes)")
    print(f"{'=' * 70}")

    for idx, (ram, name) in enumerate(zip(rams, names)):
        o = off(psp_start)
        data = ram[o:o + length]
        # Hex dump with 16 bytes per line
        print(f"\n  {name}:")
        for row_start in range(0, length, 16):
            row = data[row_start:row_start + 16]
            addr = psp_start + row_start
            hex_str = ' '.join(f'{b:02X}' for b in row)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
            print(f"    0x{addr:08X}: {hex_str:<48s} {ascii_str}")

    # Show diffs
    print(f"\n  Diff markers (X = differs between states):")
    for row_start in range(0, length, 16):
        addr = psp_start + row_start
        markers = []
        for i in range(min(16, length - row_start)):
            o_val = rams[0][off(psp_start) + row_start + i]
            p_val = rams[1][off(psp_start) + row_start + i]
            r_val = rams[2][off(psp_start) + row_start + i]
            if o_val != p_val or o_val != r_val:
                markers.append('XX')
            else:
                markers.append('..')
        print(f"    0x{addr:08X}: {' '.join(markers)}")


def main():
    print("Loading save states...")
    rams = [load_ram(5), load_ram(6), load_ram(7)]

    # Dump around the RGB candidates
    dump_region("Pigment RGB area", rams, 0x090B02D0, 32)

    # Wider context
    dump_region("Wider pigment context", rams, 0x090B02C0, 64)

    # Also check the 2-byte candidates
    dump_region("2-byte candidate at 0x090AF210", rams, 0x090AF200, 32)
    dump_region("2-byte candidate at 0x090AF250", rams, 0x090AF240, 32)

    # Check if there's a 4th byte (alpha?) after the RGB
    print(f"\n\n{'=' * 70}")
    print("Byte-by-byte around 0x090B02E0:")
    print(f"{'=' * 70}")
    for i in range(0x090B02DC, 0x090B02F0):
        o = off(i)
        vals = [ram[o] for ram in rams]
        diff = "***" if not (vals[0] == vals[1] == vals[2]) else "   "
        print(f"  0x{i:08X}: orange={vals[0]:3d} (0x{vals[0]:02X}), pink={vals[1]:3d} (0x{vals[1]:02X}), red={vals[2]:3d} (0x{vals[2]:02X})  {diff}")

    # Check if the color might be stored as HSV/HSB instead
    # MHFU uses a hue wheel, so let's see if any single-byte values match hue
    # Orange hue ~30°, Pink ~340°, Red ~0° (out of 360)
    # As 0-255: Orange ~21, Pink ~241, Red ~0
    print(f"\n\n{'=' * 70}")
    print("Single-byte candidates that could be hue (orange~21, pink~241, red~0):")
    print(f"{'=' * 70}")
    # Look at the 2-byte candidates - 0x090AF212 had orange=244, pink=133, red=40
    # That doesn't match hue well. Let's check the 0x090B0250 area too
    dump_region("Counter-like area at 0x090B0248", rams, 0x090B0248, 32)


if __name__ == "__main__":
    main()

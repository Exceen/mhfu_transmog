#!/opt/homebrew/bin/python3
"""Disassemble code around the two lui instructions that reference the
third equipment copy area at ~0x090AF680."""

import struct
import zstandard
import sys

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

sys.path.insert(0, '/Users/Exceen/Downloads/mhfu_transmog')
from disasm_equip_code import disasm, rn


def load_state(slot):
    return zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_{slot}.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)


def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


def disasm_range(data, start, count, label=""):
    if label:
        print(f"\n{'='*80}")
        print(f"  {label}")
        print(f"{'='*80}")
    for i in range(count):
        addr = start + i * 4
        instr = read_u32(data, addr)
        print(f"  0x{addr:08X}: [{instr:08X}] {disasm(instr, addr)}")


def main():
    data = load_state(0)

    # Code at 0x0891C948 (lui $t0, 0x090A)
    disasm_range(data, 0x0891C948 - 40*4, 100,
        "Code around lui $t0, 0x090A at 0x0891C948")

    # Code at 0x0891CD38 (lui $t1, 0x090B)
    disasm_range(data, 0x0891CD38 - 40*4, 100,
        "Code around lui $t1, 0x090B at 0x0891CD38")

    # Also search for lw/lhu instructions that could load from
    # a pointer to this area (the area might be accessed via a pointer
    # stored somewhere rather than hardcoded address)
    print(f"\n{'='*80}")
    print(f"  Search: pointer to 0x090AF680 in RAM")
    print(f"{'='*80}")
    # Look for the 32-bit value 0x090AF680 anywhere in RAM
    target = 0x090AF680
    target_bytes = struct.pack('<I', target)
    for region_start, region_end in [
        (0x08800000, 0x08960000),  # code area
        (0x08960000, 0x08A00000),  # data area
        (0x09990000, 0x099A0000),  # entity area
    ]:
        for psp in range(region_start, region_end, 4):
            off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
            if off + 4 <= len(data):
                val = struct.unpack_from('<I', data, off)[0]
                if val == target:
                    print(f"  Found 0x{target:08X} at 0x{psp:08X}")
                # Also check for nearby addresses (the pointer might be to the start
                # of the equipment array, which could be before head)
                for delta in [-24, -12, 0]:
                    if val == target + delta:
                        print(f"  Found 0x{target+delta:08X} at 0x{psp:08X} (target{delta:+d})")


if __name__ == '__main__':
    main()

#!/opt/homebrew/bin/python3
"""Generate CWCheat that overwrites the head model data in Extended Entity
with Mafumofu's model data, WITHOUT changing the equip_id.

This preserves stats and equipment menu functionality while changing only the visual.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
ENTITY_BASE = 0x099959A0


def load_state(slot):
    return zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_{slot}.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)


def read_u16(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<H', data, off)[0]


def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


def main():
    data1 = load_state(0)  # Rath Soul
    data2 = load_state(1)  # Mafumofu

    print("=== Extended Entity differences (entity+0x6CD00 - entity+0x72000) ===\n")

    # Dump ALL differences in the Extended Entity model area
    diffs_32 = []
    for eo in range(0x6CD00, 0x72000, 4):
        addr = ENTITY_BASE + eo
        v1 = read_u32(data1, addr)
        v2 = read_u32(data2, addr)
        if v1 != v2:
            diffs_32.append((eo, addr, v1, v2))
            print(f"  entity+0x{eo:05X} (0x{addr:08X}): 0x{v1:08X} -> 0x{v2:08X}")

    print(f"\n  Total 32-bit differences: {len(diffs_32)}")

    # Group contiguous differences
    print("\n=== Contiguous blocks of changes ===\n")
    blocks = []
    current_block = []
    for eo, addr, v1, v2 in diffs_32:
        if current_block and eo - current_block[-1][0] > 8:
            blocks.append(current_block)
            current_block = []
        current_block.append((eo, addr, v1, v2))
    if current_block:
        blocks.append(current_block)

    for i, block in enumerate(blocks):
        start_eo = block[0][0]
        end_eo = block[-1][0] + 4
        size = end_eo - start_eo
        print(f"  Block {i}: entity+0x{start_eo:05X} - entity+0x{end_eo:05X} ({size} bytes, {len(block)} dwords)")

    # Generate CWCheat lines for each block
    # Write Mafumofu values (from state 2) to override Rath Soul model data
    print("\n=== CWCheat: Overwrite model data with Mafumofu values ===\n")

    total_lines = 0
    for i, block in enumerate(blocks):
        start_eo = block[0][0]
        print(f"  ; Block {i}: entity+0x{start_eo:05X} ({len(block)} lines)")
        for eo, addr, v1, v2 in block:
            offset = addr - 0x08800000
            print(f"  _L 0x2{offset:07X} 0x{v2:08X}")
            total_lines += 1

    print(f"\n  Total CWCheat lines: {total_lines}")

    # Also dump the 58951 General RAM differences summary
    # Focus on finding small, isolated differences that could be model pointers
    print("\n=== General RAM: Looking for isolated pointer-like differences ===\n")
    prev_addr = 0
    isolated = []
    all_diffs = []
    for addr in range(0x08A00000, 0x09000000, 4):
        off = addr - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 4 > len(data1) or off + 4 > len(data2):
            break
        v1 = read_u32(data1, addr)
        v2 = read_u32(data2, addr)
        if v1 != v2:
            all_diffs.append((addr, v1, v2))

    # Find isolated changes (gaps > 64 bytes on both sides)
    for i, (addr, v1, v2) in enumerate(all_diffs):
        prev_gap = addr - all_diffs[i-1][0] if i > 0 else 9999
        next_gap = all_diffs[i+1][0] - addr if i < len(all_diffs)-1 else 9999
        if prev_gap > 64 and next_gap > 64:
            isolated.append((addr, v1, v2))

    print(f"  Total General RAM diffs: {len(all_diffs)}")
    print(f"  Isolated diffs (>64 byte gaps): {len(isolated)}")
    for addr, v1, v2 in isolated[:30]:
        print(f"    0x{addr:08X}: 0x{v1:08X} -> 0x{v2:08X}")


if __name__ == '__main__':
    main()

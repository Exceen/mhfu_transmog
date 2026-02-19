#!/opt/homebrew/bin/python3
"""Disassemble the FUComplete lookup handler at 0x088513CC and the model
loading function at 0x088174F0 to understand rendering data flow."""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

def load_state(slot):
    return zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_{slot}.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]

import sys
sys.path.insert(0, '/Users/Exceen/Downloads/mhfu_transmog')
from disasm_equip_code import disasm, rn


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
    print("Loading save state...")
    data = load_state(0)

    # 1. Disassemble the common handler at 0x088513CC
    # This is where all FUComplete property lookups jump to
    disasm_range(data, 0x088513CC - 40*4, 80,
        "FUComplete handler (0x088513CC)")

    # 2. Disassemble function 0x088174F0 more thoroughly
    disasm_range(data, 0x088174F0, 80,
        "Model loading function 0x088174F0")

    # 3. Search for all callers of each FUComplete table lookup entry point
    CODE_START = 0x08804000
    CODE_END = 0x08960000

    entry_points = {
        0x0885143C: "prop 0 (equip_id)",
        0x08851448: "prop 1 (equip_id)",
        0x08851454: "prop 2 (equip_id)",
        0x08851460: "prop 3 (equip_id)",
        0x0885146C: "prop 4 (TABLE_A file_group)",
        0x0885148C: "prop 5 (equip_id)",
        0x08851498: "prop 6 (TABLE_B model_index)",
        0x088514B8: "prop 7 (equip_id)",
        0x088514C4: "prop 8 (TABLE_C)",
        0x088514E4: "prop 9 (equip_id)",
        0x088514F0: "prop 10 (TABLE_D)",
        0x08851510: "prop 11 (equip_id)",
        0x0885151C: "prop 12 (TABLE_E texture)",
    }

    print(f"\n{'='*80}")
    print(f"  CALLERS OF EACH FUCOMPLETE ENTRY POINT")
    print(f"{'='*80}")

    for target, desc in entry_points.items():
        target_encoded = 0x0C000000 | ((target >> 2) & 0x03FFFFFF)
        count = 0
        for psp in range(CODE_START, CODE_END, 4):
            instr = read_u32(data, psp)
            if instr == target_encoded:
                count += 1
        print(f"  0x{target:08X} ({desc}): {count} callers")

    # 4. Show context for TABLE_A entry point callers (file_group)
    target = 0x0885146C
    target_encoded = 0x0C000000 | ((target >> 2) & 0x03FFFFFF)
    print(f"\n{'='*80}")
    print(f"  CALLERS OF TABLE_A LOOKUP (0x{target:08X})")
    print(f"{'='*80}")
    count = 0
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        if instr == target_encoded:
            count += 1
            print(f"\n  Call site #{count}: 0x{psp:08X}")
            for d in range(-10, 6):
                a = psp + d * 4
                i = read_u32(data, a)
                arrow = " <<<" if d == 0 else ""
                print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")

    # 5. Show context for TABLE_B entry point callers (model_index)
    target = 0x08851498
    target_encoded = 0x0C000000 | ((target >> 2) & 0x03FFFFFF)
    print(f"\n{'='*80}")
    print(f"  CALLERS OF TABLE_B LOOKUP (0x{target:08X})")
    print(f"{'='*80}")
    count = 0
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        if instr == target_encoded:
            count += 1
            print(f"\n  Call site #{count}: 0x{psp:08X}")
            for d in range(-10, 6):
                a = psp + d * 4
                i = read_u32(data, a)
                arrow = " <<<" if d == 0 else ""
                print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")

    # 6. Show context for TABLE_E entry point callers (texture)
    target = 0x0885151C
    target_encoded = 0x0C000000 | ((target >> 2) & 0x03FFFFFF)
    print(f"\n{'='*80}")
    print(f"  CALLERS OF TABLE_E LOOKUP (0x{target:08X})")
    print(f"{'='*80}")
    count = 0
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        if instr == target_encoded:
            count += 1
            print(f"\n  Call site #{count}: 0x{psp:08X}")
            for d in range(-10, 6):
                a = psp + d * 4
                i = read_u32(data, a)
                arrow = " <<<" if d == 0 else ""
                print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")


if __name__ == '__main__':
    main()

#!/opt/homebrew/bin/python3
"""Verify the vanilla armor data table at 0x0896E098 and read model IDs
for Rath Soul (102) and Mafumofu (252)."""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

def load_state(slot):
    return zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_{slot}.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

def read_u8(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return data[off]

def read_s16(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<h', data, off)[0]

def read_u16(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<H', data, off)[0]

def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]

def main():
    data = load_state(0)  # Rath Soul equipped

    TABLE_BASE = 0x0896E098
    ENTRY_SIZE = 40

    print("=== Armor Data Table at 0x0896E098 ===\n")

    # Dump entries for equip_ids 0-5 to verify table structure
    print("First 6 entries (verify structure):")
    for eid in range(6):
        addr = TABLE_BASE + eid * ENTRY_SIZE
        model_m = read_s16(data, addr)
        model_f = read_s16(data, addr + 2)
        flags = read_u8(data, addr + 4)
        rarity = read_u8(data, addr + 5)
        sell = read_u32(data, addr + 8)
        defense = read_u8(data, addr + 12)
        fire = read_u8(data, addr + 13)
        water = read_u8(data, addr + 14)
        thunder = read_u8(data, addr + 15)
        dragon = read_u8(data, addr + 16)
        ice = read_u8(data, addr + 17)
        slots = read_u8(data, addr + 18)
        print(f"  [{eid:>3}] model_m={model_m:>4} model_f={model_f:>4} flags=0x{flags:02X} "
              f"rarity={rarity} sell={sell:>6} def={defense:>3} "
              f"fire={fire:+d} water={water:+d} thun={thunder:+d} drag={dragon:+d} ice={ice:+d} "
              f"slots={slots}")

    # Dump entries for Rath Soul (102) and Mafumofu (252)
    print(f"\n=== Rath Soul (eid=102) vs Mafumofu (eid=252) ===\n")
    for eid, name in [(102, "Rath Soul"), (252, "Mafumofu")]:
        addr = TABLE_BASE + eid * ENTRY_SIZE
        print(f"  {name} (eid={eid}) at 0x{addr:08X}:")
        model_m = read_s16(data, addr)
        model_f = read_s16(data, addr + 2)
        flags = read_u8(data, addr + 4)
        rarity = read_u8(data, addr + 5)
        unk1 = read_u16(data, addr + 6)
        sell = read_u32(data, addr + 8)
        defense = read_u8(data, addr + 12)
        fire = read_u8(data, addr + 13)
        water = read_u8(data, addr + 14)
        thunder = read_u8(data, addr + 15)
        dragon = read_u8(data, addr + 16)
        ice = read_u8(data, addr + 17)
        slots = read_u8(data, addr + 18)
        print(f"    modelIdMale={model_m}, modelIdFemale={model_f}")
        print(f"    flags=0x{flags:02X}, rarity={rarity}, unk=0x{unk1:04X}")
        print(f"    sell={sell}, defense={defense}")
        print(f"    fire={fire:+d}, water={water:+d}, thunder={thunder:+d}, dragon={dragon:+d}, ice={ice:+d}")
        print(f"    slots={slots}")

        # Raw hex dump
        print(f"    Raw 40 bytes:")
        for i in range(0, ENTRY_SIZE, 4):
            v = read_u32(data, addr + i)
            print(f"      +{i:2d}: 0x{v:08X}")

    # Cross-reference with FUComplete tables
    print(f"\n=== Cross-reference with FUComplete tables ===\n")
    TABLE_A = 0x089972AC  # file_group
    TABLE_B = 0x08997BA8  # model_index
    TABLE_E = 0x0899851C  # texture
    for eid, name in [(102, "Rath Soul"), (252, "Mafumofu")]:
        a = read_u16(data, TABLE_A + eid * 2)
        b = read_u16(data, TABLE_B + eid * 2)
        e = read_u16(data, TABLE_E + eid * 2)
        addr = TABLE_BASE + eid * ENTRY_SIZE
        model_m = read_s16(data, addr)
        model_f = read_s16(data, addr + 2)
        print(f"  {name} (eid={eid}): FUC_A={a}, FUC_B={b}, FUC_E={e}, "
              f"ArmorData model_m={model_m}, model_f={model_f}")

    # Also verify the table is static (same in both states)
    data2 = load_state(1)  # Mafumofu equipped
    print(f"\n=== Verify table is static (compare both states) ===\n")
    diffs = 0
    for eid in range(300):
        addr = TABLE_BASE + eid * ENTRY_SIZE
        for i in range(0, ENTRY_SIZE, 4):
            v1 = read_u32(data, addr + i)
            off = addr + i - PSP_RAM_START + RAM_BASE_IN_STATE
            if off + 4 <= len(data2):
                v2 = read_u32(data2, addr + i)
                if v1 != v2:
                    diffs += 1
                    print(f"  DIFF: [{eid}]+{i}: 0x{v1:08X} -> 0x{v2:08X}")
    print(f"  Total diffs: {diffs} (should be 0 if static)")

    # Disassemble around 0x0885CFB4 to verify the lhu instruction
    print(f"\n=== Code around 0x0885CFB4 (equip_id read) ===\n")
    import sys
    sys.path.insert(0, '/Users/Exceen/Downloads/mhfu_transmog')
    from disasm_equip_code import disasm
    for i in range(-10, 15):
        addr = 0x0885CFB4 + i * 4
        instr = read_u32(data, addr)
        marker = " <<<" if i == 0 else ""
        print(f"  0x{addr:08X}: [{instr:08X}] {disasm(instr, addr)}{marker}")

    # Disassemble the model ID lookup function at 0x0885DF30
    print(f"\n=== Model ID Lookup at 0x0885DF30 ===\n")
    for i in range(30):
        addr = 0x0885DF30 + i * 4
        instr = read_u32(data, addr)
        print(f"  0x{addr:08X}: [{instr:08X}] {disasm(instr, addr)}")

    # Find unused memory for code cave
    print(f"\n=== Search for zero-filled areas (code cave candidates) ===\n")
    for region_start, region_end, name in [
        (0x0895F000, 0x08960000, "End of EBOOT code"),
        (0x0899A000, 0x089A0000, "End of FUC data"),
        (0x08BF0000, 0x08C00000, "End of General RAM 2"),
    ]:
        for addr in range(region_start, region_end, 64):
            all_zero = True
            for j in range(0, 64, 4):
                if read_u32(data, addr + j) != 0:
                    all_zero = False
                    break
            if all_zero:
                print(f"  64 zero bytes at 0x{addr:08X} ({name})")
                break

if __name__ == '__main__':
    main()

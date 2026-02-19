#!/opt/homebrew/bin/python3
"""Read the HEAD armor table via the pointer at 0x08975974
and dump entries for Rath Soul (102) and Mafumofu (252)."""

import struct
import zstandard
import sys

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

sys.path.insert(0, '/Users/Exceen/Downloads/mhfu_transmog')
from disasm_equip_code import disasm

def load_state(slot):
    return zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_{slot}.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

def read_u8(data, psp):
    return data[psp - PSP_RAM_START + RAM_BASE_IN_STATE]

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
    data = load_state(0)

    PTR_TABLE = 0x08975970
    ENTRY_SIZE = 40

    print("=== Pointer table at 0x08975970 (indexed by type2) ===\n")
    TYPE_NAMES = ["type0", "HEAD", "CHEST", "ARMS", "WAIST", "LEGS", "WEAPON"]
    for i in range(7):
        ptr = read_u32(data, PTR_TABLE + i * 4)
        name = TYPE_NAMES[i] if i < len(TYPE_NAMES) else f"type{i}"
        print(f"  type2={i} ({name:>7s}): table at 0x{ptr:08X}")

    # Read HEAD table
    head_table = read_u32(data, PTR_TABLE + 1 * 4)
    print(f"\n=== HEAD armor table at 0x{head_table:08X} ===\n")

    # Dump first 5 entries to verify structure
    print("First 5 entries:")
    for eid in range(5):
        addr = head_table + eid * ENTRY_SIZE
        # First 4 bytes: modelIdMale (s16), modelIdFemale (s16)
        model_m = read_s16(data, addr)
        model_f = read_s16(data, addr + 2)
        flags = read_u8(data, addr + 4)
        rarity = read_u8(data, addr + 5)
        defense = read_u8(data, addr + 12)
        slots = read_u8(data, addr + 18)
        # Skills at +30 onwards
        skill1_id = read_u8(data, addr + 30)
        skill1_pts = read_u8(data, addr + 31)
        print(f"  [{eid:>3}] model_m={model_m:>4} model_f={model_f:>4} "
              f"flags=0x{flags:02X} rarity={rarity} def={defense:>3} "
              f"slots={slots} skill1={skill1_id}/{skill1_pts}")

    # Dump Rath Soul (102) and Mafumofu (252)
    print(f"\n=== Rath Soul (102) vs Mafumofu (252) ===\n")
    for eid, name in [(102, "Rath Soul"), (252, "Mafumofu")]:
        addr = head_table + eid * ENTRY_SIZE
        print(f"  {name} (eid={eid}) at 0x{addr:08X}:")
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
        print(f"    modelIdMale={model_m}, modelIdFemale={model_f}")
        print(f"    flags=0x{flags:02X}, rarity={rarity}")
        print(f"    defense={defense}, sell={sell}")
        print(f"    fire={fire}, water={water}, thunder={thunder}, dragon={dragon}, ice={ice}")
        print(f"    slots={slots}")
        # Raw hex dump
        print(f"    Raw 40 bytes:")
        for i in range(0, ENTRY_SIZE, 4):
            v = read_u32(data, addr + i)
            print(f"      +{i:2d} (0x{addr+i:08X}): 0x{v:08X}")
        print()

    # Cross-reference: do modelIdMale match FUComplete TABLE_B?
    TABLE_B = 0x08997BA8
    print(f"Cross-reference:")
    for eid, name in [(102, "Rath Soul"), (252, "Mafumofu")]:
        addr = head_table + eid * ENTRY_SIZE
        model_m = read_s16(data, addr)
        fuc_b = read_u16(data, TABLE_B + eid * 2)
        match = "MATCH" if model_m == fuc_b else "MISMATCH"
        print(f"  {name}: ArmorData.modelIdMale={model_m}, FUC_TABLE_B={fuc_b} [{match}]")

    # Check if table is static (identical between save states)
    data2 = load_state(1)
    diffs = 0
    for eid in range(300):
        addr = head_table + eid * ENTRY_SIZE
        for i in range(0, ENTRY_SIZE, 4):
            v1 = read_u32(data, addr + i)
            off = addr + i - PSP_RAM_START + RAM_BASE_IN_STATE
            if off + 4 <= len(data2):
                v2 = read_u32(data2, addr + i)
                if v1 != v2:
                    diffs += 1
    print(f"\n  Table is {'STATIC' if diffs == 0 else 'DYNAMIC'} ({diffs} diffs between states)")

    # Generate CWCheat: overwrite modelIdMale/Female for eid 102 with Mafumofu values
    mafu_addr = head_table + 252 * ENTRY_SIZE
    rath_addr = head_table + 102 * ENTRY_SIZE
    mafu_model_m = read_s16(data, mafu_addr)
    mafu_model_f = read_s16(data, mafu_addr + 2)
    print(f"\n=== CWCheat: Overwrite Rath Soul model IDs with Mafumofu values ===\n")
    # We want to write Mafumofu's modelIdMale and modelIdFemale to Rath Soul's entry
    # Both are adjacent int16, so we can write as one u32
    mafu_models = read_u32(data, mafu_addr)  # first 4 bytes = both model IDs
    offset = rath_addr - 0x08800000
    print(f"  ; Rath Soul entry at 0x{rath_addr:08X}, writing Mafumofu models")
    print(f"  ; Mafumofu modelIdMale={mafu_model_m}, modelIdFemale={mafu_model_f}")
    print(f"  ; As u32: 0x{mafu_models:08X}")
    print(f"  _L 0x2{offset:07X} 0x{mafu_models:08X}")

    # Also disassemble the visual update function at 0x088DB2C4 to find model lookup
    print(f"\n=== Visual Update Function at 0x088DB2C4 ===\n")
    for i in range(80):
        addr = 0x088DB2C4 + i * 4
        instr = read_u32(data, addr)
        print(f"  0x{addr:08X}: [{instr:08X}] {disasm(instr, addr)}")

if __name__ == '__main__':
    main()

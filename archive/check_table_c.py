#!/opt/homebrew/bin/python3
"""Check FUComplete TABLE_C structure and verify identity mapping hypothesis.

TABLE_C base = 0x08997E6C
If TABLE_C[equip_id] = equip_id (identity mapping), it could serve as a
rendering indirection layer - changing TABLE_C[X] = Y would make equip X
render as equip Y.

Also check TABLE_A (file_group) and TABLE_B (model_index) entries for
equip_id 102 (Rath Soul) vs 252 (Mafumofu) to understand the rendering tables.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

TABLE_A = 0x089972AC  # file_group
TABLE_B = 0x08997BA8  # model_index
TABLE_C = 0x08997E6C
TABLE_D = 0x089981D4
TABLE_E = 0x0899851C  # texture


def load_state(slot):
    return zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_{slot}.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)


def read_u8(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return data[off]


def read_u16(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<H', data, off)[0]


def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


def main():
    print("Loading save state (slot 1 = Rath Soul equipped)...")
    data = load_state(0)

    # === 1. Verify TABLE_C identity mapping ===
    print("\n=== TABLE_C identity mapping check (base=0x08997E6C, 2-byte entries) ===")
    print("Checking if TABLE_C[i] == i for equip_ids 0-300...")
    mismatches = 0
    for eid in range(0, 301):
        addr = TABLE_C + eid * 2
        val = read_u16(data, addr)
        if val != eid:
            mismatches += 1
            print(f"  MISMATCH: TABLE_C[{eid}] = {val} (expected {eid}) at 0x{addr:08X}")
    if mismatches == 0:
        print(f"  PERFECT IDENTITY: TABLE_C[i] == i for all i in [0, 300]")
    else:
        print(f"  Total mismatches: {mismatches}")

    # === 2. Check TABLE_C with 1-byte entries (maybe it's u8?) ===
    print("\n=== TABLE_C with 1-byte entries check ===")
    mismatches_u8 = 0
    for eid in range(0, 301):
        addr = TABLE_C + eid
        val = read_u8(data, addr)
        if val != (eid & 0xFF):
            mismatches_u8 += 1
    print(f"  1-byte entry mismatches: {mismatches_u8}/301")

    # === 3. Check TABLE_C with 4-byte entries ===
    print("\n=== TABLE_C with 4-byte entries check ===")
    mismatches_u32 = 0
    for eid in range(0, 200):
        addr = TABLE_C + eid * 4
        val = read_u32(data, addr)
        if val != eid:
            mismatches_u32 += 1
    print(f"  4-byte entry mismatches: {mismatches_u32}/200")

    # === 4. Show TABLE_A/B/C/D/E entries for key equip_ids ===
    print("\n=== Table entries for equip_id 102 (Rath Soul head) ===")
    tables = [
        ("TABLE_A (file_group)", TABLE_A),
        ("TABLE_B (model_index)", TABLE_B),
        ("TABLE_C", TABLE_C),
        ("TABLE_D", TABLE_D),
        ("TABLE_E (texture)", TABLE_E),
    ]
    for name, base in tables:
        for entry_size in [2, 4]:
            addr = base + 102 * entry_size
            if entry_size == 2:
                val = read_u16(data, addr)
                print(f"  {name}[102] ({entry_size}B): {val} (0x{val:04X}) at 0x{addr:08X}")
            else:
                val = read_u32(data, addr)
                print(f"  {name}[102] ({entry_size}B): {val} (0x{val:08X}) at 0x{addr:08X}")

    print("\n=== Table entries for equip_id 252 (Mafumofu Hood) ===")
    for name, base in tables:
        for entry_size in [2, 4]:
            addr = base + 252 * entry_size
            if entry_size == 2:
                val = read_u16(data, addr)
                print(f"  {name}[252] ({entry_size}B): {val} (0x{val:04X}) at 0x{addr:08X}")
            else:
                val = read_u32(data, addr)
                print(f"  {name}[252] ({entry_size}B): {val} (0x{val:08X}) at 0x{addr:08X}")

    # === 5. Determine entry sizes by looking at table structure ===
    # Check TABLE_A: sequential check
    print("\n=== TABLE_A structure analysis (first 20 entries) ===")
    for i in range(20):
        v16 = read_u16(data, TABLE_A + i * 2)
        v32 = read_u32(data, TABLE_A + i * 4)
        print(f"  [{i:3d}] 2B: {v16:>6} (0x{v16:04X})  |  4B: {v32:>10} (0x{v32:08X})")

    print("\n=== TABLE_B structure analysis (first 20 entries) ===")
    for i in range(20):
        v16 = read_u16(data, TABLE_B + i * 2)
        v32 = read_u32(data, TABLE_B + i * 4)
        print(f"  [{i:3d}] 2B: {v16:>6} (0x{v16:04X})  |  4B: {v32:>10} (0x{v32:08X})")

    print("\n=== TABLE_C structure analysis (first 20 entries) ===")
    for i in range(20):
        v16 = read_u16(data, TABLE_C + i * 2)
        v32 = read_u32(data, TABLE_C + i * 4)
        print(f"  [{i:3d}] 2B: {v16:>6} (0x{v16:04X})  |  4B: {v32:>10} (0x{v32:08X})")

    # === 6. Find TABLE_C entry size by looking at the code ===
    # Search for code that uses TABLE_C base address
    print("\n=== Code references to TABLE_C area (lui 0x0899, addiu near 0x7E6C) ===")
    CODE_START = 0x08804000
    CODE_END = 0x08960000
    REG_NAMES = ['zero','at','v0','v1','a0','a1','a2','a3',
                 't0','t1','t2','t3','t4','t5','t6','t7',
                 's0','s1','s2','s3','s4','s5','s6','s7',
                 't8','t9','k0','k1','gp','sp','fp','ra']
    def rn(r):
        return REG_NAMES[r] if r < 32 else f'r{r}'

    # Look for addiu with lower part of TABLE_C address
    # TABLE_C = 0x08997E6C -> lui 0x089A (because 0x7E6C is positive, actually:
    # 0x08997E6C = 0x089A0000 + (-0x8194) ... no
    # 0x08997E6C = 0x08990000 + 0x7E6C
    # lui would be 0x0899 if lower is positive, or 0x089A if using negative offset
    # 0x7E6C is positive (< 0x8000), so: lui $r, 0x0899; addiu $r, $r, 0x7E6C
    target_upper = 0x0899
    target_lower = 0x7E6C

    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        op = (instr >> 26) & 0x3F
        if op == 0x09:  # addiu
            imm = instr & 0xFFFF
            imm_s = imm - 0x10000 if imm >= 0x8000 else imm
            if imm_s == target_lower or imm == target_lower:
                rs = (instr >> 21) & 0x1F
                rt = (instr >> 16) & 0x1F
                # Check if nearby there's a lui with 0x0899
                for d in range(-8, 0):
                    nearby = read_u32(data, psp + d * 4)
                    n_op = (nearby >> 26) & 0x3F
                    if n_op == 0x0F:  # lui
                        n_imm = nearby & 0xFFFF
                        if n_imm == target_upper:
                            n_rt = (nearby >> 16) & 0x1F
                            print(f"\n  TABLE_C reference at 0x{psp:08X}:")
                            print(f"    lui ${rn(n_rt)}, 0x{target_upper:04X} at 0x{psp + d*4:08X}")
                            print(f"    addiu ${rn(rt)}, ${rn(rs)}, 0x{target_lower:04X} at 0x{psp:08X}")
                            # Show context
                            for dd in range(-4, 12):
                                a = psp + dd * 4
                                i = read_u32(data, a)
                                from disasm_equip_code import disasm
                                print(f"      0x{a:08X}: [{i:08X}] {disasm(i, a)}")
                            break

    # === 7. Check if TABLE_C is referenced via the FUComplete lookup function ===
    # Disassemble the FUComplete lookup function at 0x0885143C
    print("\n=== FUComplete lookup function (0x0885143C) ===")
    from disasm_equip_code import disasm
    for i in range(60):
        addr = 0x0885143C + i * 4
        instr = read_u32(data, addr)
        txt = disasm(instr, addr)
        # Mark references to known tables
        note = ""
        if "0899" in txt.lower() or "972" in txt.lower() or "7BA8" in txt.lower() or "7E6C" in txt.lower():
            note = " <<<< TABLE REF?"
        print(f"  0x{addr:08X}: [{instr:08X}] {txt}{note}")
        if "jr $ra" in txt and i > 2:
            break


if __name__ == '__main__':
    main()

#!/opt/homebrew/bin/python3
"""Find the ACTIVE code paths for equip_id processing.

Previous patches at 0x08853D04 and 0x0885DC54 had no effect, meaning those
functions don't run during normal gameplay. We need to find:
1. What writes to entity copy 2 head equip_id (equip change handler)
2. What reads from the third copy area (entity+0x67770)
3. All callers of the FUComplete lookup function (0x0885143C)
4. What's at address 0x089A9AE8
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
CODE_START = 0x08804000
CODE_END = 0x08960000

ENTITY_BASE = 0x099959A0

REG_NAMES = ['zero','at','v0','v1','a0','a1','a2','a3',
             't0','t1','t2','t3','t4','t5','t6','t7',
             's0','s1','s2','s3','s4','s5','s6','s7',
             't8','t9','k0','k1','gp','sp','fp','ra']

def rn(r):
    return REG_NAMES[r] if r < 32 else f'r{r}'


def read_u16(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<H', data, off)[0]


def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


def disasm(instr, addr):
    op = (instr >> 26) & 0x3F
    rs = (instr >> 21) & 0x1F
    rt = (instr >> 16) & 0x1F
    rd = (instr >> 11) & 0x1F
    sa = (instr >> 6) & 0x1F
    func = instr & 0x3F
    imm = instr & 0xFFFF
    imm_s = imm - 0x10000 if imm >= 0x8000 else imm

    if op == 0:
        if func == 0 and rd == 0 and rt == 0 and sa == 0:
            return "nop"
        rtype = {
            0x00: f"sll ${rn(rd)}, ${rn(rt)}, {sa}",
            0x02: f"srl ${rn(rd)}, ${rn(rt)}, {sa}",
            0x03: f"sra ${rn(rd)}, ${rn(rt)}, {sa}",
            0x08: f"jr ${rn(rs)}",
            0x09: f"jalr ${rn(rd)}, ${rn(rs)}",
            0x10: f"mfhi ${rn(rd)}",
            0x12: f"mflo ${rn(rd)}",
            0x18: f"mult ${rn(rs)}, ${rn(rt)}",
            0x21: f"addu ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x23: f"subu ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x24: f"and ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x25: f"or ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x2A: f"slt ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x2B: f"sltu ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
        }
        return rtype.get(func, f"r-type func=0x{func:02X}")

    if op == 0x02:
        return f"j 0x{((instr & 0x03FFFFFF) << 2) | (addr & 0xF0000000):08X}"
    if op == 0x03:
        return f"jal 0x{((instr & 0x03FFFFFF) << 2) | (addr & 0xF0000000):08X}"

    itype = {
        0x04: f"beq ${rn(rs)}, ${rn(rt)}, 0x{(addr + 4 + imm_s * 4) & 0xFFFFFFFF:08X}",
        0x05: f"bne ${rn(rs)}, ${rn(rt)}, 0x{(addr + 4 + imm_s * 4) & 0xFFFFFFFF:08X}",
        0x09: f"addiu ${rn(rt)}, ${rn(rs)}, {imm_s}  (0x{imm:04X})",
        0x0A: f"slti ${rn(rt)}, ${rn(rs)}, {imm_s}",
        0x0B: f"sltiu ${rn(rt)}, ${rn(rs)}, {imm_s}",
        0x0C: f"andi ${rn(rt)}, ${rn(rs)}, 0x{imm:04X}",
        0x0D: f"ori ${rn(rt)}, ${rn(rs)}, 0x{imm:04X}",
        0x0F: f"lui ${rn(rt)}, 0x{imm:04X}",
        0x20: f"lb ${rn(rt)}, {imm_s}(${rn(rs)})",
        0x21: f"lh ${rn(rt)}, {imm_s}(${rn(rs)})",
        0x23: f"lw ${rn(rt)}, {imm_s}(${rn(rs)})",
        0x24: f"lbu ${rn(rt)}, {imm_s}(${rn(rs)})",
        0x25: f"lhu ${rn(rt)}, {imm_s}(${rn(rs)})",
        0x28: f"sb ${rn(rt)}, {imm_s}(${rn(rs)})",
        0x29: f"sh ${rn(rt)}, {imm_s}(${rn(rs)})",
        0x2B: f"sw ${rn(rt)}, {imm_s}(${rn(rs)})",
    }
    return itype.get(op, f"op=0x{op:02X} [{instr:08X}]")


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
    data = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

    # === 0. Check key memory values ===
    print(f"\n{'='*80}")
    print(f"  KEY MEMORY VALUES")
    print(f"{'='*80}")
    print(f"  Entity copy 1 head equip_id (0x09995A1A): {read_u16(data, 0x09995A1A)} (0x{read_u16(data, 0x09995A1A):04X})")
    print(f"  Entity copy 2 head equip_id (0x09995E7A): {read_u16(data, 0x09995E7A)} (0x{read_u16(data, 0x09995E7A):04X})")
    print(f"  Address 0x089A9AE8 (FUComplete call source): {read_u16(data, 0x089A9AE8)} (0x{read_u16(data, 0x089A9AE8):04X})")
    print(f"  Third copy head (0x09FFD110): {read_u16(data, 0x09FFD110)} (0x{read_u16(data, 0x09FFD110):04X})")

    # Also check the third copy area
    print(f"\n  Third copy area (entity+0x6776A to +0x67776):")
    for off in range(0x6776A, 0x67778, 2):
        addr = ENTITY_BASE + off
        val = read_u16(data, addr)
        print(f"    entity+0x{off:05X} (0x{addr:08X}): {val} (0x{val:04X})")

    # Check entity+0x6778C area (destination of 0x088174F0 call)
    print(f"\n  Model data area (entity+0x6778C, 98 bytes):")
    for off in range(0x6778C, 0x6778C + 98, 4):
        addr = ENTITY_BASE + off
        val = read_u32(data, addr)
        print(f"    entity+0x{off:05X} (0x{addr:08X}): 0x{val:08X}")

    # === 1. Search for sh (store halfword) with offset 0x4DA ===
    # This finds code that WRITES to entity copy 2 head equip_id
    print(f"\n{'='*80}")
    print(f"  SEARCH 1: sh with offset 0x04DA (writes to copy 2 head equip_id)")
    print(f"{'='*80}")
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        op = (instr >> 26) & 0x3F
        imm = instr & 0xFFFF
        if op == 0x29 and imm == 0x04DA:  # sh
            rs = (instr >> 21) & 0x1F
            rt = (instr >> 16) & 0x1F
            print(f"  0x{psp:08X}: sh ${rn(rt)}, 0x04DA(${rn(rs)})")
            # Show context
            for d in range(-6, 10):
                a = psp + d * 4
                i = read_u32(data, a)
                arrow = " <<<" if d == 0 else ""
                print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")

    # === 2. Search for lhu/lh with offset 0x7770 ===
    # This finds code that READS from third copy head equip_id
    print(f"\n{'='*80}")
    print(f"  SEARCH 2: lhu/lh with offset 0x7770 (reads from third copy head)")
    print(f"{'='*80}")
    count = 0
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        op = (instr >> 26) & 0x3F
        imm = instr & 0xFFFF
        if op in (0x25, 0x21) and imm == 0x7770:  # lhu or lh
            rs = (instr >> 21) & 0x1F
            rt = (instr >> 16) & 0x1F
            op_name = "lhu" if op == 0x25 else "lh"
            count += 1
            print(f"  0x{psp:08X}: {op_name} ${rn(rt)}, 0x7770(${rn(rs)})")
            for d in range(-6, 10):
                a = psp + d * 4
                i = read_u32(data, a)
                arrow = " <<<" if d == 0 else ""
                print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")
    if count == 0:
        print("  NONE FOUND")
        # Also search for nearby offsets
        print("\n  Searching for offsets 0x776A-0x7776 (all third copy equip slots):")
        for target_off in range(0x776A, 0x7778, 2):
            for psp in range(CODE_START, CODE_END, 4):
                instr = read_u32(data, psp)
                op = (instr >> 26) & 0x3F
                imm = instr & 0xFFFF
                if op in (0x25, 0x21) and imm == target_off:
                    rs = (instr >> 21) & 0x1F
                    rt = (instr >> 16) & 0x1F
                    op_name = "lhu" if op == 0x25 else "lh"
                    print(f"  0x{psp:08X}: {op_name} ${rn(rt)}, 0x{target_off:04X}(${rn(rs)})")

    # === 3. Search for all callers of FUComplete lookup (jal 0x0885143C) ===
    print(f"\n{'='*80}")
    print(f"  SEARCH 3: All callers of FUComplete lookup (jal 0x0885143C)")
    print(f"{'='*80}")
    target = 0x0885143C
    target_encoded = 0x0C000000 | ((target >> 2) & 0x03FFFFFF)
    count = 0
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        if instr == target_encoded:
            count += 1
            print(f"\n  Call site #{count}: 0x{psp:08X}")
            for d in range(-8, 6):
                a = psp + d * 4
                i = read_u32(data, a)
                arrow = " <<<" if d == 0 else ""
                print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")
    print(f"  Total callers: {count}")

    # === 4. Search for sh with offset 0x7770 (writes to third copy head) ===
    print(f"\n{'='*80}")
    print(f"  SEARCH 4: sh with offset 0x7770 (writes to third copy head)")
    print(f"{'='*80}")
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        op = (instr >> 26) & 0x3F
        imm = instr & 0xFFFF
        if op == 0x29 and imm == 0x7770:  # sh
            rs = (instr >> 21) & 0x1F
            rt = (instr >> 16) & 0x1F
            print(f"  0x{psp:08X}: sh ${rn(rt)}, 0x7770(${rn(rs)})")
    # Also check store to 30576 decimal = 0x7770 ✓ (already covered)

    # === 5. Search for code that loads entity+0x7A (copy 1 head) ===
    # If copy 1 is used for anything, we'd see lhu with offset 0x7A
    print(f"\n{'='*80}")
    print(f"  SEARCH 5: lhu/lh with offset 0x007A (reads copy 1 head equip_id)")
    print(f"{'='*80}")
    count = 0
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        op = (instr >> 26) & 0x3F
        imm = instr & 0xFFFF
        if op in (0x25, 0x21) and imm == 0x007A:
            rs = (instr >> 21) & 0x1F
            rt = (instr >> 16) & 0x1F
            op_name = "lhu" if op == 0x25 else "lh"
            count += 1
            if count <= 10:
                print(f"  0x{psp:08X}: {op_name} ${rn(rt)}, 0x007A(${rn(rs)})")
    print(f"  Total: {count}")

    # === 6. Search for all callers of VT1/VT2 stat function ===
    # The function starts at 0x0885DC28. Search for jal to it.
    print(f"\n{'='*80}")
    print(f"  SEARCH 6: All callers of stat lookup function (0x0885DC28)")
    print(f"{'='*80}")
    target = 0x0885DC28
    target_encoded = 0x0C000000 | ((target >> 2) & 0x03FFFFFF)
    count = 0
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        if instr == target_encoded:
            count += 1
            print(f"\n  Call site #{count}: 0x{psp:08X}")
            for d in range(-8, 6):
                a = psp + d * 4
                i = read_u32(data, a)
                arrow = " <<<" if d == 0 else ""
                print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")
    print(f"  Total callers: {count}")

    # === 7. Search in EXTENDED code area (0x08960000-0x09000000) ===
    # FUComplete might have code in data tables area
    print(f"\n{'='*80}")
    print(f"  SEARCH 7: lhu/lh with offset 0x04DA in extended range (0x08960000-0x09400000)")
    print(f"{'='*80}")
    count = 0
    for psp in range(0x08960000, min(0x09400000, PSP_RAM_START + len(data) - RAM_BASE_IN_STATE - 3), 4):
        instr = read_u32(data, psp)
        op = (instr >> 26) & 0x3F
        imm = instr & 0xFFFF
        if op in (0x25, 0x21) and imm == 0x04DA:
            rs = (instr >> 21) & 0x1F
            rt = (instr >> 16) & 0x1F
            op_name = "lhu" if op == 0x25 else "lh"
            count += 1
            if count <= 10:
                print(f"  0x{psp:08X}: {op_name} ${rn(rt)}, 0x04DA(${rn(rs)})")
                for d in range(-4, 8):
                    a = psp + d * 4
                    i = read_u32(data, a)
                    arrow = " <<<" if d == 0 else ""
                    print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")
    print(f"  Total: {count}")

    # === 8. Search for sb/sh/sw with offset 0x04DA in code area ===
    # Find ALL code that writes to entity+0x4DA
    print(f"\n{'='*80}")
    print(f"  SEARCH 8: All stores (sb/sh/sw) with offset 0x04DA in code area")
    print(f"{'='*80}")
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        op = (instr >> 26) & 0x3F
        imm = instr & 0xFFFF
        if op in (0x28, 0x29, 0x2B) and imm == 0x04DA:  # sb, sh, sw
            rs = (instr >> 21) & 0x1F
            rt = (instr >> 16) & 0x1F
            op_names = {0x28: "sb", 0x29: "sh", 0x2B: "sw"}
            print(f"\n  0x{psp:08X}: {op_names[op]} ${rn(rt)}, 0x04DA(${rn(rs)})")
            for d in range(-6, 10):
                a = psp + d * 4
                i = read_u32(data, a)
                arrow = " <<<" if d == 0 else ""
                print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")

    # === 9. Disassemble 0x088174F0 (model loading function?) ===
    disasm_range(data, 0x088174F0, 40,
        "Function 0x088174F0 (called after FUComplete lookup)")

    # === 10. Search for code accessing entity+0x4D8 area via memcpy-like patterns ===
    # Look for code that copies 12 bytes (equip slot size) repeatedly
    print(f"\n{'='*80}")
    print(f"  SEARCH 10: jal 0x088174F0 (all callers of model function)")
    print(f"{'='*80}")
    target = 0x088174F0
    target_encoded = 0x0C000000 | ((target >> 2) & 0x03FFFFFF)
    count = 0
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        if instr == target_encoded:
            count += 1
            print(f"\n  Call site #{count}: 0x{psp:08X}")
            for d in range(-8, 6):
                a = psp + d * 4
                i = read_u32(data, a)
                arrow = " <<<" if d == 0 else ""
                print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")
    print(f"  Total callers: {count}")


if __name__ == '__main__':
    main()

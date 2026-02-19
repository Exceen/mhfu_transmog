#!/opt/homebrew/bin/python3
"""Disassemble game code around equip_id processing sites.

Examines:
1. Code around the two known equip_id read sites
2. Code around VT1/VT2 stat table references
3. Code accessing FUComplete table A (equip_id → file_group for model loading)
4. Code setting up pointers to entity copy 2 equip area
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
CODE_START = 0x08804000
CODE_END = 0x08960000

# Known addresses
EQUIP_SITE_1 = 0x08853D9C
EQUIP_SITE_2 = 0x0885D440
VT1_REF = 0x0885DC58
VT2_REF = 0x0885DC80

# FUComplete tables
TABLE_A = 0x089972AC  # file_group
TABLE_B = 0x08997BA8  # model_index
TABLE_E = 0x0899851C  # texture


def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


REG_NAMES = ['zero','at','v0','v1','a0','a1','a2','a3',
             't0','t1','t2','t3','t4','t5','t6','t7',
             's0','s1','s2','s3','s4','s5','s6','s7',
             't8','t9','k0','k1','gp','sp','fp','ra']

def rn(r):
    return REG_NAMES[r] if r < 32 else f'r{r}'


def disasm(instr, addr):
    op = (instr >> 26) & 0x3F
    rs = (instr >> 21) & 0x1F
    rt = (instr >> 16) & 0x1F
    rd = (instr >> 11) & 0x1F
    sa = (instr >> 6) & 0x1F
    func = instr & 0x3F
    imm = instr & 0xFFFF
    imm_s = imm - 0x10000 if imm >= 0x8000 else imm

    if op == 0:  # R-type
        if func == 0 and rd == 0 and rt == 0 and sa == 0:
            return "nop"
        rtype = {
            0x00: f"sll ${rn(rd)}, ${rn(rt)}, {sa}",
            0x02: f"srl ${rn(rd)}, ${rn(rt)}, {sa}",
            0x03: f"sra ${rn(rd)}, ${rn(rt)}, {sa}",
            0x04: f"sllv ${rn(rd)}, ${rn(rt)}, ${rn(rs)}",
            0x06: f"srlv ${rn(rd)}, ${rn(rt)}, ${rn(rs)}",
            0x08: f"jr ${rn(rs)}",
            0x09: f"jalr ${rn(rd)}, ${rn(rs)}",
            0x10: f"mfhi ${rn(rd)}",
            0x12: f"mflo ${rn(rd)}",
            0x18: f"mult ${rn(rs)}, ${rn(rt)}",
            0x19: f"multu ${rn(rs)}, ${rn(rt)}",
            0x1A: f"div ${rn(rs)}, ${rn(rt)}",
            0x1B: f"divu ${rn(rs)}, ${rn(rt)}",
            0x20: f"add ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x21: f"addu ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x22: f"sub ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x23: f"subu ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x24: f"and ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x25: f"or ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x26: f"xor ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x27: f"nor ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x2A: f"slt ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
            0x2B: f"sltu ${rn(rd)}, ${rn(rs)}, ${rn(rt)}",
        }
        return rtype.get(func, f"r-type func=0x{func:02X} rs={rn(rs)} rt={rn(rt)} rd={rn(rd)} sa={sa}")

    if op == 0x01:  # REGIMM
        regimm = {0: "bltz", 1: "bgez", 16: "bltzal", 17: "bgezal"}
        name = regimm.get(rt, f"regimm_{rt}")
        return f"{name} ${rn(rs)}, 0x{(addr + 4 + imm_s * 4) & 0xFFFFFFFF:08X}"

    if op == 0x02:
        return f"j 0x{((instr & 0x03FFFFFF) << 2) | (addr & 0xF0000000):08X}"
    if op == 0x03:
        return f"jal 0x{((instr & 0x03FFFFFF) << 2) | (addr & 0xF0000000):08X}"

    itype = {
        0x04: f"beq ${rn(rs)}, ${rn(rt)}, 0x{(addr + 4 + imm_s * 4) & 0xFFFFFFFF:08X}",
        0x05: f"bne ${rn(rs)}, ${rn(rt)}, 0x{(addr + 4 + imm_s * 4) & 0xFFFFFFFF:08X}",
        0x06: f"blez ${rn(rs)}, 0x{(addr + 4 + imm_s * 4) & 0xFFFFFFFF:08X}",
        0x07: f"bgtz ${rn(rs)}, 0x{(addr + 4 + imm_s * 4) & 0xFFFFFFFF:08X}",
        0x08: f"addi ${rn(rt)}, ${rn(rs)}, {imm_s}",
        0x09: f"addiu ${rn(rt)}, ${rn(rs)}, {imm_s}  (0x{imm:04X})",
        0x0A: f"slti ${rn(rt)}, ${rn(rs)}, {imm_s}",
        0x0B: f"sltiu ${rn(rt)}, ${rn(rs)}, {imm_s}",
        0x0C: f"andi ${rn(rt)}, ${rn(rs)}, 0x{imm:04X}",
        0x0D: f"ori ${rn(rt)}, ${rn(rs)}, 0x{imm:04X}",
        0x0E: f"xori ${rn(rt)}, ${rn(rs)}, 0x{imm:04X}",
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


MARKERS = {
    EQUIP_SITE_1: "<<< EQUIP SITE 1 (lhu $v1, 0x4DA($a0))",
    EQUIP_SITE_2: "<<< EQUIP SITE 2 (lhu $v1, 0x4DA($v0))",
    VT1_REF: "<<< VT1 REFERENCE",
    VT2_REF: "<<< VT2 REFERENCE",
}


def disasm_range(data, start, count, label=""):
    if label:
        print(f"\n{'='*80}")
        print(f"  {label}")
        print(f"{'='*80}")
    for i in range(count):
        addr = start + i * 4
        instr = read_u32(data, addr)
        marker = MARKERS.get(addr, "")
        if marker:
            marker = f"  {marker}"
        print(f"  0x{addr:08X}: [{instr:08X}] {disasm(instr, addr)}{marker}")


def main():
    print("Loading save state...")
    data = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

    # 1. Disassemble around equip site 1 (0x08853D9C)
    disasm_range(data, EQUIP_SITE_1 - 60*4, 120,
        f"SITE 1: 0x{EQUIP_SITE_1:08X} - lhu $v1, 0x4DA($a0)")

    # 2. Disassemble around equip site 2 (0x0885D440)
    disasm_range(data, EQUIP_SITE_2 - 60*4, 120,
        f"SITE 2: 0x{EQUIP_SITE_2:08X} - lhu $v1, 0x4DA($v0)")

    # 3. Disassemble around VT1/VT2 references (includes stat lookup code)
    disasm_range(data, VT1_REF - 80*4, 160,
        f"VT1/VT2 AREA: 0x{VT1_REF:08X} - 0x{VT2_REF:08X}")

    # 4. Search for FUComplete table A access (lui 0x0899)
    print(f"\n{'='*80}")
    print(f"  SEARCH: lui with 0x0899 (FUComplete table area upper addr)")
    print(f"{'='*80}")
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        op = (instr >> 26) & 0x3F
        if op == 0x0F:  # lui
            imm = instr & 0xFFFF
            if imm == 0x0899:
                rt = (instr >> 16) & 0x1F
                print(f"\n  >>> lui ${rn(rt)}, 0x0899 at 0x{psp:08X}")
                # Show context: 4 before, 10 after
                for d in range(-4, 11):
                    a = psp + d * 4
                    i = read_u32(data, a)
                    arrow = " <<<" if d == 0 else ""
                    print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")

    # 5. Search for addiu with 0x4D8 (pointer to copy 2 equip area base)
    print(f"\n{'='*80}")
    print(f"  SEARCH: addiu with offset 0x4D8 (copy 2 equip area base)")
    print(f"{'='*80}")
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        op = (instr >> 26) & 0x3F
        if op == 0x09:  # addiu
            imm = instr & 0xFFFF
            imm_s = imm - 0x10000 if imm >= 0x8000 else imm
            if imm_s == 0x4D8:
                rs = (instr >> 21) & 0x1F
                rt = (instr >> 16) & 0x1F
                print(f"\n  >>> addiu ${rn(rt)}, ${rn(rs)}, 0x4D8 at 0x{psp:08X}")
                for d in range(-6, 14):
                    a = psp + d * 4
                    i = read_u32(data, a)
                    arrow = " <<<" if d == 0 else ""
                    print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")

    # 6. Search for code that reads with small offsets (0, 2, 4) near copy 2 setup
    # This finds indirect equip_id reads: ptr = entity+0x4D8; lhu rt, 2(ptr)
    print(f"\n{'='*80}")
    print(f"  SEARCH: lhu with offset 2 near addiu 0x4D8 (indirect equip_id read)")
    print(f"{'='*80}")
    count = 0
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        op = (instr >> 26) & 0x3F
        if op == 0x25:  # lhu
            imm = instr & 0xFFFF
            if imm == 0x0002:  # lhu rt, 2(rs) - equip_id offset within a slot
                # Check nearby for addiu with 0x4D8
                for d in range(-20, 1):
                    nearby_addr = psp + d * 4
                    if nearby_addr < CODE_START:
                        continue
                    nearby = read_u32(data, nearby_addr)
                    n_op = (nearby >> 26) & 0x3F
                    if n_op == 0x09:  # addiu
                        n_imm = nearby & 0xFFFF
                        n_imm_s = n_imm - 0x10000 if n_imm >= 0x8000 else n_imm
                        if n_imm_s == 0x4D8:
                            count += 1
                            if count <= 10:
                                rs = (instr >> 21) & 0x1F
                                rt = (instr >> 16) & 0x1F
                                print(f"\n  >>> lhu ${rn(rt)}, 2(${rn(rs)}) at 0x{psp:08X}")
                                print(f"      (addiu +0x4D8 found at 0x{nearby_addr:08X}, delta={d})")
                                for dd in range(-4, 8):
                                    a = psp + dd * 4
                                    i = read_u32(data, a)
                                    arrow = " <<<" if dd == 0 else ""
                                    print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")
                            break
    print(f"  Total indirect equip_id reads found: {count}")

    # 7. Look for all multiply-by-40 patterns with surrounding context
    print(f"\n{'='*80}")
    print(f"  SEARCH: Multiply by 40 patterns (sll 5 + sll 3)")
    print(f"{'='*80}")
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        op = (instr >> 26) & 0x3F
        func = instr & 0x3F
        sa = (instr >> 6) & 0x1F
        if op == 0 and func == 0 and sa == 5:  # sll by 5
            rt_sll = (instr >> 16) & 0x1F
            rd_sll = (instr >> 11) & 0x1F
            for delta in range(-8, 12, 4):
                if delta == 0:
                    continue
                nearby = read_u32(data, psp + delta)
                n_op = (nearby >> 26) & 0x3F
                n_func = nearby & 0x3F
                n_sa = (nearby >> 6) & 0x1F
                n_rt = (nearby >> 16) & 0x1F
                if n_op == 0 and n_func == 0 and n_sa == 3 and n_rt == rt_sll:
                    n_rd = (nearby >> 11) & 0x1F
                    print(f"\n  >>> sll ${rn(rd_sll)}, ${rn(rt_sll)}, 5 at 0x{psp:08X}")
                    print(f"      sll ${rn(n_rd)}, ${rn(rt_sll)}, 3 at 0x{psp+delta:08X}")
                    # Show wide context
                    for d in range(-8, 16):
                        a = psp + d * 4
                        i = read_u32(data, a)
                        arrow = ""
                        if a == psp:
                            arrow = " <<< sll 5"
                        elif a == psp + delta:
                            arrow = " <<< sll 3"
                        print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")
                    break  # Only show once per sll-5


if __name__ == '__main__':
    main()

#!/opt/homebrew/bin/python3
"""Find game code that reads equip_id for stat table lookup.

We want to find MIPS instructions that:
1. Load a halfword from entity+0x4DA (second equip copy head equip_id)
2. Or load from entity+0x4D8 area (second equip copy base)
3. Or reference the stat table bases (VT1=0x08960754, VT2=0x08964B74)
4. Or multiply by 40 (stat table entry size)

If we find the stat calculation code, we can patch it to read from
entity+0x7A (first copy) instead, leaving the model path on copy 2.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

# MIPS opcodes
LHU = 0x25  # load halfword unsigned
LH  = 0x21  # load halfword signed
LW  = 0x23  # load word
LBU = 0x24  # load byte unsigned

# Key offsets
ENTITY_COPY2_HEAD_EQUIP = 0x4DA  # offset from entity base
ENTITY_COPY1_HEAD_EQUIP = 0x7A   # offset from entity base
ENTITY_COPY2_BASE = 0x4D8        # second equip copy base offset
ENTRY_SIZE = 40                    # stat table entry size

# Stat table bases
VT1_BASE = 0x08960754
VT2_BASE = 0x08964B74


def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


def disasm_i_type(instr):
    """Decode MIPS I-type instruction."""
    opcode = (instr >> 26) & 0x3F
    rs = (instr >> 21) & 0x1F
    rt = (instr >> 16) & 0x1F
    imm = instr & 0xFFFF
    # Sign extend
    if imm >= 0x8000:
        imm_signed = imm - 0x10000
    else:
        imm_signed = imm
    return opcode, rs, rt, imm, imm_signed


def reg_name(r):
    names = ['zero','at','v0','v1','a0','a1','a2','a3',
             't0','t1','t2','t3','t4','t5','t6','t7',
             's0','s1','s2','s3','s4','s5','s6','s7',
             't8','t9','k0','k1','gp','sp','fp','ra']
    return names[r] if r < 32 else f'r{r}'


def main():
    print("Loading save state...")
    data = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

    # Game code is in the lower memory area (0x08800000-0x08960000 roughly)
    # EBOOT loads around 0x08804000
    CODE_START = 0x08804000
    CODE_END = 0x08960000

    # === 1. Search for lhu/lh with offset 0x04DA (entity+0x4DA = copy2 head equip_id) ===
    print("=" * 70)
    print("  Search 1: lhu/lh instructions with offset 0x04DA")
    print("=" * 70)
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        opcode, rs, rt, imm, imm_s = disasm_i_type(instr)
        if opcode in (LHU, LH) and imm == 0x04DA:
            op_name = "lhu" if opcode == LHU else "lh"
            print(f"  0x{psp:08X}: {op_name} ${reg_name(rt)}, 0x{imm:04X}(${reg_name(rs)})  [instr=0x{instr:08X}]")

    # === 2. Search for lhu/lh with offset 0x007A (entity+0x7A = copy1 head equip_id) ===
    print("\n" + "=" * 70)
    print("  Search 2: lhu/lh instructions with offset 0x007A")
    print("=" * 70)
    count = 0
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        opcode, rs, rt, imm, imm_s = disasm_i_type(instr)
        if opcode in (LHU, LH) and imm == 0x007A:
            op_name = "lhu" if opcode == LHU else "lh"
            count += 1
            if count <= 20:
                print(f"  0x{psp:08X}: {op_name} ${reg_name(rt)}, 0x{imm:04X}(${reg_name(rs)})  [instr=0x{instr:08X}]")
    print(f"  Total: {count}")

    # === 3. Search for instructions referencing VT1/VT2 base addresses ===
    print("\n" + "=" * 70)
    print("  Search 3: lui instructions loading VT1/VT2 upper address")
    print("=" * 70)
    # VT1 = 0x08960754 → lui would load 0x0896 or 0x0897 (if addiu with negative offset)
    # VT2 = 0x08964B74 → lui would load 0x0896 or 0x0897
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        opcode = (instr >> 26) & 0x3F
        if opcode == 0x0F:  # lui
            rt = (instr >> 16) & 0x1F
            imm = instr & 0xFFFF
            if imm in (0x0896, 0x0897):
                # Check next instruction for addiu with VT1/VT2 lower bits
                next_instr = read_u32(data, psp + 4)
                next_op = (next_instr >> 26) & 0x3F
                next_imm = next_instr & 0xFFFF
                if next_imm >= 0x8000:
                    next_imm_s = next_imm - 0x10000
                else:
                    next_imm_s = next_imm
                computed = (imm << 16) + next_imm_s
                print(f"  0x{psp:08X}: lui ${reg_name(rt)}, 0x{imm:04X}  (next: 0x{next_instr:08X}, computed=0x{computed:08X})")

    # === 4. Search for multiply by 40 patterns ===
    print("\n" + "=" * 70)
    print("  Search 4: Multiply by 40 (sll by 5 + sll by 3 patterns)")
    print("=" * 70)
    # sll rd, rt, 5: opcode=0, func=0, sa=5 → 0x00_rt_rd_05_00 pattern
    # Actually: sll rd, rt, sa → instr = (rt << 16) | (rd << 11) | (sa << 6) | 0
    # sa=5: sa<<6 = 0x140
    # sa=3: sa<<6 = 0xC0
    count = 0
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        opcode = (instr >> 26) & 0x3F
        func = instr & 0x3F
        sa = (instr >> 6) & 0x1F
        if opcode == 0 and func == 0 and sa == 5:  # sll by 5
            rt_sll = (instr >> 16) & 0x1F
            rd_sll = (instr >> 11) & 0x1F
            # Check nearby for sll by 3 with same source
            for delta in range(-8, 12, 4):
                if delta == 0:
                    continue
                nearby = read_u32(data, psp + delta)
                n_op = (nearby >> 26) & 0x3F
                n_func = nearby & 0x3F
                n_sa = (nearby >> 6) & 0x1F
                n_rt = (nearby >> 16) & 0x1F
                if n_op == 0 and n_func == 0 and n_sa == 3 and n_rt == rt_sll:
                    count += 1
                    if count <= 15:
                        n_rd = (nearby >> 11) & 0x1F
                        print(f"  0x{psp:08X}: sll ${reg_name(rd_sll)}, ${reg_name(rt_sll)}, 5  "
                              f"+ sll ${reg_name(n_rd)}, ${reg_name(rt_sll)}, 3 at +{delta}")
    print(f"  Total sll5+sll3 pairs: {count}")

    # === 5. Search for addiu/ori with 40 (0x28) that could be mult operand ===
    print("\n" + "=" * 70)
    print("  Search 5: Instructions loading constant 40 (potential mult by 40)")
    print("=" * 70)
    count = 0
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data, psp)
        opcode = (instr >> 26) & 0x3F
        imm = instr & 0xFFFF
        rs = (instr >> 21) & 0x1F
        rt = (instr >> 16) & 0x1F
        # addiu rt, zero, 40 or ori rt, zero, 40
        if imm == 0x0028 and rs == 0:
            if opcode == 0x09:  # addiu
                # Check nearby for mult/multu
                for delta in range(-16, 20, 4):
                    nearby = read_u32(data, psp + delta)
                    n_func = nearby & 0x3F
                    n_op = (nearby >> 26) & 0x3F
                    if n_op == 0 and n_func in (0x18, 0x19):  # mult/multu
                        count += 1
                        if count <= 15:
                            mult_rs = (nearby >> 21) & 0x1F
                            mult_rt = (nearby >> 16) & 0x1F
                            print(f"  0x{psp:08X}: addiu ${reg_name(rt)}, $zero, 40  "
                                  f"+ mult ${reg_name(mult_rs)}, ${reg_name(mult_rt)} at +{delta}")
    print(f"  Total: {count}")

    # === 6. Search for lhu with offsets near 0x4DA (0x4D8-0x4E0 range, all 5 head equip slots) ===
    print("\n" + "=" * 70)
    print("  Search 6: lhu/lh with offsets 0x04D8-0x050C (all copy2 equip slots)")
    print("=" * 70)
    for off in range(0x4D8, 0x510, 2):
        for psp in range(CODE_START, CODE_END, 4):
            instr = read_u32(data, psp)
            opcode, rs, rt, imm, imm_s = disasm_i_type(instr)
            if opcode in (LHU, LH) and imm == off:
                op_name = "lhu" if opcode == LHU else "lh"
                slot = (off - 0x4D8) // 12
                field = (off - 0x4D8) % 12
                field_names = {0: "type", 2: "equip_id", 4: "deco1", 6: "deco2", 8: "deco3", 10: "extra"}
                fname = field_names.get(field, f"+{field}")
                print(f"  0x{psp:08X}: {op_name} ${reg_name(rt)}, 0x{imm:04X}(${reg_name(rs)}) "
                      f" [slot {slot}, {fname}]  [instr=0x{instr:08X}]")


if __name__ == '__main__':
    main()

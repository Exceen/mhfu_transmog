#!/opt/homebrew/bin/python3
"""Disassemble the key equipment→model mapping functions."""

import struct

EBOOT_PATH = "/Users/Exceen/Downloads/mhfu_transmog/EBOOT.BIN"
EBOOT_LOAD_ADDR = 0x08804000

REG_NAMES = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
             '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
             '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
             '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']


def decode(word):
    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    shamt = (word >> 6) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000
    target = word & 0x3FFFFFF
    R = REG_NAMES
    if opcode == 0x00:
        if funct == 0x00:
            if word == 0: return "nop"
            return f"sll {R[rd]}, {R[rt]}, {shamt}"
        elif funct == 0x02: return f"srl {R[rd]}, {R[rt]}, {shamt}"
        elif funct == 0x03: return f"sra {R[rd]}, {R[rt]}, {shamt}"
        elif funct == 0x08: return f"jr {R[rs]}"
        elif funct == 0x09: return f"jalr {R[rd]}, {R[rs]}"
        elif funct == 0x0A: return f"movz {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x0B: return f"movn {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x10: return f"mfhi {R[rd]}"
        elif funct == 0x12: return f"mflo {R[rd]}"
        elif funct == 0x18: return f"mult {R[rs]}, {R[rt]}"
        elif funct == 0x19: return f"multu {R[rs]}, {R[rt]}"
        elif funct == 0x1A: return f"div {R[rs]}, {R[rt]}"
        elif funct == 0x1B: return f"divu {R[rs]}, {R[rt]}"
        elif funct == 0x20: return f"add {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x21: return f"addu {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x23: return f"subu {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x24: return f"and {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x25: return f"or {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x26: return f"xor {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x27: return f"nor {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x2A: return f"slt {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x2B: return f"sltu {R[rd]}, {R[rs]}, {R[rt]}"
        else: return f"special.{funct:02X} {R[rs]},{R[rt]},{R[rd]}"
    elif opcode == 0x01:
        if rt == 0: return f"bltz {R[rs]}, {simm}"
        elif rt == 1: return f"bgez {R[rs]}, {simm}"
        else: return f"regimm.{rt:02X} {R[rs]}, {simm}"
    elif opcode == 0x02: return f"j 0x{(target << 2) | 0x08000000:08X}"
    elif opcode == 0x03: return f"jal 0x{(target << 2) | 0x08000000:08X}"
    elif opcode == 0x04: return f"beq {R[rs]}, {R[rt]}, {simm}"
    elif opcode == 0x05: return f"bne {R[rs]}, {R[rt]}, {simm}"
    elif opcode == 0x06: return f"blez {R[rs]}, {simm}"
    elif opcode == 0x07: return f"bgtz {R[rs]}, {simm}"
    elif opcode == 0x08: return f"addi {R[rt]}, {R[rs]}, {simm}"
    elif opcode == 0x09: return f"addiu {R[rt]}, {R[rs]}, {simm}"
    elif opcode == 0x0A: return f"slti {R[rt]}, {R[rs]}, {simm}"
    elif opcode == 0x0B: return f"sltiu {R[rt]}, {R[rs]}, {simm}"
    elif opcode == 0x0C: return f"andi {R[rt]}, {R[rs]}, 0x{imm:04X}"
    elif opcode == 0x0D: return f"ori {R[rt]}, {R[rs]}, 0x{imm:04X}"
    elif opcode == 0x0E: return f"xori {R[rt]}, {R[rs]}, 0x{imm:04X}"
    elif opcode == 0x0F: return f"lui {R[rt]}, 0x{imm:04X}"
    elif opcode == 0x14: return f"beql {R[rs]}, {R[rt]}, {simm}"
    elif opcode == 0x15: return f"bnel {R[rs]}, {R[rt]}, {simm}"
    elif opcode == 0x1C:
        if funct == 0x02: return f"mul {R[rd]}, {R[rs]}, {R[rt]}"
        else: return f"special2.{funct:02X}"
    elif opcode == 0x1F:
        if funct == 0x20:
            if shamt == 0x10: return f"seb {R[rd]}, {R[rt]}"
            elif shamt == 0x18: return f"seh {R[rd]}, {R[rt]}"
            else: return f"bshfl.{shamt:02X} {R[rd]}, {R[rt]}"
        elif funct == 0x00: return f"ext {R[rt]}, {R[rs]}, {shamt}, {rd+1}"
        elif funct == 0x04: return f"ins {R[rt]}, {R[rs]}, {shamt}, {rd+1-shamt}"
        else: return f"special3.{funct:02X}"
    elif opcode == 0x20: return f"lb {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x21: return f"lh {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x23: return f"lw {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x24: return f"lbu {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x25: return f"lhu {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x28: return f"sb {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x29: return f"sh {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x2B: return f"sw {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x31: return f"lwc1 $f{rt}, {simm}({R[rs]})"
    elif opcode == 0x39: return f"swc1 $f{rt}, {simm}({R[rs]})"
    else: return f"[{opcode:02X} {R[rs]} {R[rt]} 0x{imm:04X}]"


def disasm(eboot, start, end, label=""):
    if label:
        print(f"\n{'='*70}")
        print(f"  {label}")
        print(f"  PSP 0x{start:08X} - 0x{end:08X}")
        print(f"{'='*70}")
    for psp in range(start, end, 4):
        off = psp - EBOOT_LOAD_ADDR
        if off < 0 or off + 3 >= len(eboot): continue
        word = struct.unpack_from('<I', eboot, off)[0]
        print(f"  0x{psp:08X}: {word:08X}  {decode(word)}")


def main():
    with open(EBOOT_PATH, 'rb') as f:
        eboot = f.read()

    # Function 0x08851448 - called with equip index, returns model info
    # Called from 0x0884AF40: jal 0x08851448
    # With $a1 = equip index (from lhu), $a0 = pointer from 0x089C7508
    disasm(eboot, 0x08851400, 0x08851700,
           "Function 0x08851448 (equip index → model lookup)")

    # Function 0x08850B78 - equipment validation
    disasm(eboot, 0x08850B40, 0x08850E00,
           "Function 0x08850B78 (equipment validation)")

    # Function 0x0882E504 - called from equip iterator with visual params
    disasm(eboot, 0x0882E480, 0x0882E700,
           "Function 0x0882E504 (called from equip rendering)")

    # The SH area at 0x08829514 - stores to offsets 1454, 1452, 1460
    # These could be file ID stores
    disasm(eboot, 0x08829400, 0x08829700,
           "Function with SH to file-ID-like offsets (1452,1454,1460)")

    # Function 0x0882A59C area - another *40 pattern with stores
    disasm(eboot, 0x0882A500, 0x0882A700,
           "Function 0x0882A59C (armor lookup with stores to 740,1054)")

    # Also check what table is at 0x08960754 by dumping from save state
    # Compare structures at 0x08960754 vs 0x089633A8


if __name__ == '__main__':
    main()

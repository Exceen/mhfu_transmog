#!/opt/homebrew/bin/python3
"""Deep disassembly of the equipment change and model assignment functions.

Key targets:
1. The big function at ~0x0884AEB0 that iterates equipment slots with *40 pattern
2. The rendering/update function at 0x088DAB78
3. Functions at 0x08853248 area (armor table access with stores)
4. The function that CALLS 0x08863E68 (model loading)

Also: verify CWCheat address calculations.
"""

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
        elif funct == 0x04: return f"sllv {R[rd]}, {R[rt]}, {R[rs]}"
        elif funct == 0x06: return f"srlv {R[rd]}, {R[rt]}, {R[rs]}"
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
        elif funct == 0x22: return f"sub {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x23: return f"subu {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x24: return f"and {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x25: return f"or {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x26: return f"xor {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x27: return f"nor {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x2A: return f"slt {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x2B: return f"sltu {R[rd]}, {R[rs]}, {R[rt]}"
        else: return f"special.{funct:02X} {R[rs]},{R[rt]},{R[rd]}"
    elif opcode == 0x01:
        if rt == 0x00: return f"bltz {R[rs]}, {simm}"
        elif rt == 0x01: return f"bgez {R[rs]}, {simm}"
        elif rt == 0x10: return f"bltzal {R[rs]}, {simm}"
        elif rt == 0x11: return f"bgezal {R[rs]}, {simm}"
        else: return f"regimm.{rt:02X} {R[rs]}, {simm}"
    elif opcode == 0x02: return f"j 0x{(target << 2) | 0x08000000:08X}"
    elif opcode == 0x03: return f"jal 0x{(target << 2) | 0x08000000:08X}"
    elif opcode == 0x04: return f"beq {R[rs]}, {R[rt]}, {simm}"
    elif opcode == 0x05:
        return f"bne {R[rs]}, {R[rt]}, {simm}"
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
    elif opcode == 0x16: return f"blezl {R[rs]}, {simm}"
    elif opcode == 0x17: return f"bgtzl {R[rs]}, {simm}"
    elif opcode == 0x1C:
        if funct == 0x02: return f"mul {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x00: return f"madd {R[rs]}, {R[rt]}"
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


def disasm(eboot, psp_start, psp_end, label=""):
    if label:
        print(f"\n{'='*70}")
        print(f"  {label}")
        print(f"  PSP 0x{psp_start:08X} - 0x{psp_end:08X}")
        print(f"{'='*70}")
    for psp in range(psp_start, psp_end, 4):
        off = psp - EBOOT_LOAD_ADDR
        if off < 0 or off + 3 >= len(eboot):
            print(f"  0x{psp:08X}: (out of range)")
            continue
        word = struct.unpack_from('<I', eboot, off)[0]
        d = decode(word)
        print(f"  0x{psp:08X}: {word:08X}  {d}")


def main():
    with open(EBOOT_PATH, 'rb') as f:
        eboot = f.read()

    # === CWCheat address verification ===
    print("=" * 70)
    print("CWCheat Address Calculations")
    print("=" * 70)
    print("CWCheat format: _L 0xTAAAAAAA 0xVVVVVVVV")
    print("  T=1: 16-bit write, T=2: 32-bit write")
    print("  Address = 0x08800000 + AAAAAAA")
    print()
    addrs = {
        "Head model index": 0x090AF6BA,
        "Head equip ID (loc1)": 0x090AF682,
        "Head equip ID (loc2)": 0x09995A1A,
        "Head equip ID (loc3)": 0x09995E7A,
        "Head file ID": 0x0912F54C,
        "Armor table entry 102": 0x089633A8 + 102 * 40,
        "Armor table entry 101": 0x089633A8 + 101 * 40,
    }
    for name, psp in addrs.items():
        cw_offset = psp - 0x08800000
        cw16 = 0x10000000 | cw_offset
        cw32 = 0x20000000 | cw_offset
        print(f"  {name}: PSP 0x{psp:08X}")
        print(f"    16-bit: _L 0x{cw16:08X} 0x0000VVVV")
        print(f"    32-bit: _L 0x{cw32:08X} 0xVVVVVVVV")

    # === Disassemble the equipment processing function ===
    # The *40 pattern at 0x0884AEB0 looks like an equipment slot iterator
    disasm(eboot, 0x0884AE60, 0x0884B200,
           "Equipment slot iterator (around *40 at 0x0884AEB0)")

    # === Disassemble the equipment change function at 0x08853248 ===
    # This function has: sh $a0, 16420($a1) then accesses armor table
    # It's computing armor properties from equip IDs
    disasm(eboot, 0x08852F00, 0x08853400,
           "Armor data computation function (0x08853248 region)")

    # === Look at the function that has SH to model index area ===
    # At 0x0891F458: sh $t3, 2($t1) and 0x0891F45C: sh $t2, 0($t1)
    # What are $t1, $t2, $t3 at this point?
    disasm(eboot, 0x0891F300, 0x0891F500,
           "Model index store area (sh at 0x0891F458)")

    # === The function at 0x08863E68 (called from file ID handler) ===
    disasm(eboot, 0x08863E00, 0x08864100,
           "Model loading function 0x08863E68")

    # === Search for functions that do: lhu from armor entry + sh to model area ===
    # A transmog patch would intercept: read armor_id → lookup table → get model
    # Let's search for sh (store halfword) instructions in functions
    # that also have the *40 pattern nearby
    print("\n" + "=" * 70)
    print("  Searching for SH instructions in *40-related functions")
    print("=" * 70)

    # Look for sh instructions within 200 bytes of each *40 pattern location
    mul40_locs = []
    for off in range(0, len(eboot) - 15, 4):
        w1 = struct.unpack_from('<I', eboot, off)[0]
        w2 = struct.unpack_from('<I', eboot, off + 4)[0]
        w3 = struct.unpack_from('<I', eboot, off + 8)[0]
        if (w1 >> 26) != 0 or (w1 & 0x3F) != 0 or ((w1 >> 6) & 0x1F) != 2:
            continue
        rd1 = (w1 >> 11) & 0x1F
        rt1 = (w1 >> 16) & 0x1F
        if (w2 >> 26) != 0 or (w2 & 0x3F) != 0x21:
            continue
        rs2 = (w2 >> 21) & 0x1F
        rt2 = (w2 >> 16) & 0x1F
        rd2 = (w2 >> 11) & 0x1F
        if not ((rs2 == rd1 and rt2 == rt1) or (rs2 == rt1 and rt2 == rd1)):
            continue
        if (w3 >> 26) != 0 or (w3 & 0x3F) != 0 or ((w3 >> 6) & 0x1F) != 3:
            continue
        rt3 = (w3 >> 16) & 0x1F
        if rt3 != rd2:
            continue
        mul40_locs.append(EBOOT_LOAD_ADDR + off)

    for psp in mul40_locs:
        off = psp - EBOOT_LOAD_ADDR
        # Search for sh instructions in range [psp-100, psp+200]
        sh_found = []
        for delta in range(-100, 200, 4):
            check = off + delta
            if check < 0 or check + 3 >= len(eboot):
                continue
            w = struct.unpack_from('<I', eboot, check)[0]
            if (w >> 26) & 0x3F == 0x29:  # sh
                sh_psp = EBOOT_LOAD_ADDR + check
                sh_found.append((sh_psp, w))
        if sh_found:
            print(f"\n  Near *40 at 0x{psp:08X}:")
            for sh_psp, w in sh_found:
                print(f"    SH at 0x{sh_psp:08X}: {w:08X}  {decode(w)}")


if __name__ == '__main__':
    main()

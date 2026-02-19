#!/opt/homebrew/bin/python3
"""Disassemble key functions in EBOOT.BIN related to model loading.

Focus on:
1. The function at PSP 0x0891F2EC (lui 0x090B - model index array ref)
2. The file ID switch at PSP 0x088DAC78 (addiu 406)
3. Functions that write to model index area (sh/sw with computed address)
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

    if opcode == 0x00:  # SPECIAL
        if funct == 0x00:
            if word == 0: return "nop"
            return f"sll {R[rd]}, {R[rt]}, {shamt}"
        elif funct == 0x02: return f"srl {R[rd]}, {R[rt]}, {shamt}"
        elif funct == 0x03: return f"sra {R[rd]}, {R[rt]}, {shamt}"
        elif funct == 0x04: return f"sllv {R[rd]}, {R[rt]}, {R[rs]}"
        elif funct == 0x06: return f"srlv {R[rd]}, {R[rt]}, {R[rs]}"
        elif funct == 0x07: return f"srav {R[rd]}, {R[rt]}, {R[rs]}"
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
        else: return f"special funct=0x{funct:02X} ({R[rs]},{R[rt]},{R[rd]})"
    elif opcode == 0x01:  # REGIMM
        if rt == 0x00: return f"bltz {R[rs]}, {simm}"
        elif rt == 0x01: return f"bgez {R[rs]}, {simm}"
        elif rt == 0x10: return f"bltzal {R[rs]}, {simm}"
        elif rt == 0x11: return f"bgezal {R[rs]}, {simm}"
        else: return f"regimm rt=0x{rt:02X} {R[rs]}, {simm}"
    elif opcode == 0x02:
        return f"j 0x{(target << 2) | 0x08000000:08X}"
    elif opcode == 0x03:
        return f"jal 0x{(target << 2) | 0x08000000:08X}"
    elif opcode == 0x04:
        return f"beq {R[rs]}, {R[rt]}, {simm}"
    elif opcode == 0x05:
        return f"bnez {R[rs]}, {simm}" if rt == 0 else f"bne {R[rs]}, {R[rt]}, {simm}"
    elif opcode == 0x06:
        return f"blez {R[rs]}, {simm}"
    elif opcode == 0x07:
        return f"bgtz {R[rs]}, {simm}"
    elif opcode == 0x08: return f"addi {R[rt]}, {R[rs]}, {simm}"
    elif opcode == 0x09: return f"addiu {R[rt]}, {R[rs]}, {simm}"
    elif opcode == 0x0A: return f"slti {R[rt]}, {R[rs]}, {simm}"
    elif opcode == 0x0B: return f"sltiu {R[rt]}, {R[rs]}, {simm}"
    elif opcode == 0x0C: return f"andi {R[rt]}, {R[rs]}, 0x{imm:04X}"
    elif opcode == 0x0D: return f"ori {R[rt]}, {R[rs]}, 0x{imm:04X}"
    elif opcode == 0x0E: return f"xori {R[rt]}, {R[rs]}, 0x{imm:04X}"
    elif opcode == 0x0F: return f"lui {R[rt]}, 0x{imm:04X}"
    elif opcode == 0x1C:  # SPECIAL2
        if funct == 0x02: return f"mul {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x00: return f"madd {R[rs]}, {R[rt]}"
        else: return f"special2 funct=0x{funct:02X}"
    elif opcode == 0x1F:  # SPECIAL3 / ALLEGREX
        if funct == 0x20:
            if shamt == 0x10: return f"seb {R[rd]}, {R[rt]}"
            elif shamt == 0x18: return f"seh {R[rd]}, {R[rt]}"
            elif shamt == 0x14: return f"bitrev {R[rd]}, {R[rt]}"
            else: return f"bshfl shamt=0x{shamt:02X} {R[rd]}, {R[rt]}"
        elif funct == 0x00:
            return f"ext {R[rt]}, {R[rs]}, {shamt}, {rd+1}"
        elif funct == 0x04:
            return f"ins {R[rt]}, {R[rs]}, {shamt}, {rd+1-shamt}"
        else: return f"special3 funct=0x{funct:02X}"
    elif opcode == 0x20: return f"lb {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x21: return f"lh {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x23: return f"lw {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x24: return f"lbu {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x25: return f"lhu {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x28: return f"sb {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x29: return f"sh {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x2B: return f"sw {R[rt]}, {simm}({R[rs]})"
    # Coprocessor
    elif opcode == 0x31: return f"lwc1 $f{rt}, {simm}({R[rs]})"
    elif opcode == 0x39: return f"swc1 $f{rt}, {simm}({R[rs]})"
    elif opcode == 0x32: return f"lv.s $v{rt}, {simm}({R[rs]})"
    elif opcode == 0x3A: return f"sv.s $v{rt}, {simm}({R[rs]})"
    else:
        return f"[op=0x{opcode:02X} {R[rs]} {R[rt]} imm=0x{imm:04X}]"


def disasm_region(eboot, psp_start, psp_end, label=""):
    """Disassemble a PSP address range."""
    if label:
        print(f"\n{'='*70}")
        print(f"=== {label} ===")
        print(f"=== PSP 0x{psp_start:08X} - 0x{psp_end:08X} ===")
        print(f"{'='*70}")

    for psp in range(psp_start, psp_end, 4):
        off = psp - EBOOT_LOAD_ADDR
        if off < 0 or off + 3 >= len(eboot):
            continue
        word = struct.unpack_from('<I', eboot, off)[0]
        d = decode(word)
        print(f"  0x{psp:08X}: {word:08X}  {d}")


def find_function_bounds(eboot, psp_addr):
    """Try to find function start/end around a PSP address.
    Look for jr $ra (function return) and addiu $sp patterns (function prologue)."""
    off = psp_addr - EBOOT_LOAD_ADDR

    # Search backward for function prologue (addiu $sp, $sp, -N)
    start = off
    for i in range(off, max(off - 2000, 0), -4):
        word = struct.unpack_from('<I', eboot, i)[0]
        # addiu $sp, $sp, -N  (opcode=0x09, rs=29, rt=29, negative imm)
        opcode = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        rt = (word >> 16) & 0x1F
        imm = word & 0xFFFF
        if opcode == 0x09 and rs == 29 and rt == 29 and imm >= 0x8000:
            start = i
            break
        # Also check for jr $ra right before (end of previous function)
        if opcode == 0x00 and (word & 0x3F) == 0x08 and rs == 31:
            start = i + 8  # skip jr $ra and delay slot
            break

    # Search forward for jr $ra + delay slot (function return)
    end = off
    for i in range(off, min(off + 3000, len(eboot) - 4), 4):
        word = struct.unpack_from('<I', eboot, i)[0]
        opcode = (word >> 26) & 0x3F
        rs = (word >> 21) & 0x1F
        funct = word & 0x3F
        if opcode == 0x00 and funct == 0x08 and rs == 31:  # jr $ra
            end = i + 8  # include delay slot
            break

    return EBOOT_LOAD_ADDR + start, EBOOT_LOAD_ADDR + end


def main():
    with open(EBOOT_PATH, 'rb') as f:
        eboot = f.read()

    # === 1. Function containing lui 0x090B (model index array ref) ===
    print("=" * 70)
    print("=== FUNCTION CONTAINING MODEL INDEX ARRAY REFERENCE ===")
    print("=== (lui 0x090B at PSP 0x0891F2EC) ===")
    print("=" * 70)
    fn_start, fn_end = find_function_bounds(eboot, 0x0891F2EC)
    print(f"Estimated function bounds: 0x{fn_start:08X} - 0x{fn_end:08X}")
    # Disassemble a generous range around it
    disasm_region(eboot, max(fn_start - 32, 0x0891F200), min(fn_end + 32, 0x0891F600),
                  "Model index array function")

    # === 2. File ID switch/case ===
    print("\n\n")
    fn_start2, fn_end2 = find_function_bounds(eboot, 0x088DAC78)
    print(f"Estimated file ID function bounds: 0x{fn_start2:08X} - 0x{fn_end2:08X}")
    disasm_region(eboot, max(fn_start2 - 16, 0x088DA000), min(fn_end2 + 16, 0x088DB100),
                  "File ID switch/case function")

    # === 3. Search for SH (store halfword) to model index area ===
    # The model index for head is at 0x090AF6BA
    # With lui 0x090B: base = 0x090B0000
    # Offset = 0x090AF6BA - 0x090B0000 = -0x0946 = 0xF6BA (unsigned)
    # But we already searched for this and found nothing.
    # Try: maybe the base is loaded differently (e.g., from a register/pointer)
    # Let's search for any sh instruction that stores to addresses near model index
    # by looking for patterns like: addu reg, base, offset; sh val, 0(reg)

    # === 4. Search for the function that WRITES to model index array ===
    # The model index for head is at PSP 0x090AF6BA
    # It's a u16. Find sh instructions near the lui 0x090B code.
    print("\n\n")
    print("=" * 70)
    print("=== SEARCH: Store halfword instructions near model index code ===")
    # Look in a broader area around 0x0891F2EC for sh instructions
    for psp in range(0x0891F200, 0x0891F600, 4):
        off = psp - EBOOT_LOAD_ADDR
        if off < 0 or off + 3 >= len(eboot):
            continue
        word = struct.unpack_from('<I', eboot, off)[0]
        opcode = (word >> 26) & 0x3F
        if opcode == 0x29:  # sh
            d = decode(word)
            print(f"  0x{psp:08X}: {word:08X}  {d}")

    # === 5. Look for where file IDs are stored to the array at ~0x0912F54C ===
    # Search for any code writing to 0x0912xxxx range
    print("\n")
    print("=" * 70)
    print("=== SEARCH: lui 0x0913 or lui 0x0912 in full EBOOT ===")
    for off in range(0, len(eboot) - 3, 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        opcode = (word >> 26) & 0x3F
        if opcode == 0x0F:
            imm = word & 0xFFFF
            if imm in (0x0912, 0x0913):
                psp = EBOOT_LOAD_ADDR + off
                d = decode(word)
                print(f"  0x{psp:08X}: {word:08X}  {d}")
                # Show context
                for i in range(1, 6):
                    w = struct.unpack_from('<I', eboot, off + i*4)[0]
                    print(f"    +{i*4}: {decode(w)}")

    # === 6. Search for the equipment-change handler ===
    # When equipment changes, the game must:
    # 1. Read equip ID from slot
    # 2. Look up armor entry (index * 40)
    # 3. Extract model info
    # 4. Store to model index array
    #
    # Search for stores to the known equipment ID address (0x090AF682)
    print("\n")
    print("=" * 70)
    print("=== SEARCH: References to equip struct area 0x090AF6xx ===")
    # The equipment data starts around 0x090AF672 and the head slot equip ID is at 0x090AF682
    # Search for addiu with -0x0946 (= offset from 0x090B0000 to 0x090AF6BA)
    print("  Looking for addiu with -2374 (0xF6BA - head model offset from 0x090B):")
    for off in range(0, len(eboot) - 3, 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        opcode = (word >> 26) & 0x3F
        imm = word & 0xFFFF
        if opcode == 0x09 and imm == 0xF6BA:
            psp = EBOOT_LOAD_ADDR + off
            print(f"    0x{psp:08X}: {decode(word)}")

    print("  Looking for addiu with -2430 (0x090AF682 as 0x090B + -0x097E):")
    for off in range(0, len(eboot) - 3, 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        opcode = (word >> 26) & 0x3F
        imm = word & 0xFFFF
        if opcode == 0x09 and imm == 0xF682:
            psp = EBOOT_LOAD_ADDR + off
            print(f"    0x{psp:08X}: {decode(word)}")

    # === 7. The offset from 0x090B0000 to 0x090AF6BA is -0x0946 ===
    # But the code uses addiu $t1, $t1, -3036
    # -3036 = 0xFFFFF434... wait, -3036 as 16-bit signed = 0xF434
    # So $t1 = 0x090B0000 + 0xFFFFF434 = 0x090AF434
    # That's not 0x090AF6BA. It's 0x090AF434.
    # 0x090AF6BA - 0x090AF434 = 0x286 = 646 bytes
    # This might be a struct base, and the model index is at offset +646
    print("\n")
    print("=" * 70)
    print("=== ANALYSIS: 0x090AF434 struct layout ===")
    print(f"  lui 0x090B + addiu -3036 = 0x090AF434")
    print(f"  Model index (head) at 0x090AF6BA = base + 0x286 = base + {0x286}")
    print(f"  Equip ID (head) at 0x090AF682 = base + 0x24E = base + {0x24E}")
    print(f"  Equip struct at 0x090AF672 = base + 0x23E = base + {0x23E}")
    print(f"  File ID (head) at 0x0912F54C = (different base)")

    # === 8. Search for ALL addiu instructions that compute addresses
    #         near 0x090AF6BA (the head model index) ===
    # The base might be loaded from a pointer, not a lui. Let's search for
    # any instruction that adds an offset that would reach 0x090AF6BA
    # from common bases.
    print("\n")
    print("=" * 70)
    print("=== Large function scan: functions doing armor_id * 40 + table lookup ===")
    # Pattern: sll reg, reg, 2; addu reg, reg, orig; sll reg, reg, 3
    # This computes (x * 4 + x) * 8 = x * 40
    # Search for this 3-instruction pattern
    count = 0
    for off in range(0, len(eboot) - 15, 4):
        w1 = struct.unpack_from('<I', eboot, off)[0]
        w2 = struct.unpack_from('<I', eboot, off + 4)[0]
        w3 = struct.unpack_from('<I', eboot, off + 8)[0]

        # sll rd1, rt1, 2
        if (w1 >> 26) != 0 or (w1 & 0x3F) != 0 or ((w1 >> 6) & 0x1F) != 2:
            continue
        rd1 = (w1 >> 11) & 0x1F
        rt1 = (w1 >> 16) & 0x1F

        # addu rd2, rs2, rt2 where one of rs2/rt2 = rd1 and the other = rt1
        if (w2 >> 26) != 0 or (w2 & 0x3F) != 0x21:
            continue
        rs2 = (w2 >> 21) & 0x1F
        rt2 = (w2 >> 16) & 0x1F
        rd2 = (w2 >> 11) & 0x1F
        if not ((rs2 == rd1 and rt2 == rt1) or (rs2 == rt1 and rt2 == rd1)):
            continue

        # sll rd3, rt3, 3 where rt3 = rd2
        if (w3 >> 26) != 0 or (w3 & 0x3F) != 0 or ((w3 >> 6) & 0x1F) != 3:
            continue
        rt3 = (w3 >> 16) & 0x1F
        if rt3 != rd2:
            continue

        psp = EBOOT_LOAD_ADDR + off
        count += 1
        if count <= 30:
            # Show context: what comes before and after
            before = []
            for i in range(-4, 0):
                w = struct.unpack_from('<I', eboot, off + i*4)[0]
                before.append(decode(w))
            after = []
            for i in range(3, 8):
                if off + i*4 < len(eboot):
                    w = struct.unpack_from('<I', eboot, off + i*4)[0]
                    after.append(decode(w))
            print(f"\n  *40 pattern at 0x{psp:08X}:")
            for i, b in enumerate(before):
                print(f"    -{(4-i)*4}: {b}")
            print(f"    >>> {decode(w1)}")
            print(f"    >>> {decode(w2)}")
            print(f"    >>> {decode(w3)}")
            for i, a in enumerate(after):
                print(f"    +{(i)*4+12}: {a}")

    print(f"\n  Total *40 patterns found: {count}")


if __name__ == '__main__':
    main()

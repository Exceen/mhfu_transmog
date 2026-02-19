#!/opt/homebrew/bin/python3
"""Disassemble the visual lookup function at 0x08860200 area.
This function references ALL 5 visual tables and is likely the key
equip_id → visual model mapping function.

Also disassemble the equipment copy function around 0x08852E08 that
reads validated head slot and copies equipment data.
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
        if off < 0 or off + 3 >= len(eboot): continue
        word = struct.unpack_from('<I', eboot, off)[0]
        print(f"  0x{psp:08X}: {word:08X}  {decode(word)}")


def main():
    with open(EBOOT_PATH, 'rb') as f:
        eboot = f.read()

    # === 1. Visual lookup function at 0x08860200 area ===
    # References ALL 5 visual tables: 0x08960754, 0x08964B74, 0x0896CD4C, 0x08968D14, 0x08970D34
    # Find function start (look for addiu $sp, $sp, -N or similar prologue)
    disasm(eboot, 0x088601A0, 0x08860500,
           "Visual lookup function 0x08860200 area (references ALL visual tables)")

    # === 2. Second visual function at 0x088603C8 area ===
    disasm(eboot, 0x08860380, 0x08860520,
           "Second visual function 0x088603C0 area")

    # === 3. Equipment copy function at 0x08852E08 ===
    # This reads validated head slot and copies equip data to active slots
    disasm(eboot, 0x08852E08, 0x08852FC0,
           "Equipment copy function (reads validated slots, copies equip data)")

    # === 4. The full validation+processing function ===
    # The validation function at 0x08853200+ is not called by jal.
    # It must be part of a larger function. Find the function start.
    # Look backwards from 0x08853200 for a function prologue (addiu $sp, $sp, -N)
    print("\n" + "=" * 70)
    print("  Searching for function start before 0x08853200")
    print("=" * 70)
    for psp in range(0x08853200, 0x088531A0, -4):
        off = psp - EBOOT_LOAD_ADDR
        word = struct.unpack_from('<I', eboot, off)[0]
        opcode = (word >> 26) & 0x3F
        if opcode == 0x09:  # addiu
            rs = (word >> 21) & 0x1F
            rt = (word >> 16) & 0x1F
            simm = (word & 0xFFFF) if (word & 0xFFFF) < 0x8000 else (word & 0xFFFF) - 0x10000
            if rs == 29 and rt == 29 and simm < 0:  # addiu $sp, $sp, -N
                print(f"  Found prologue at 0x{psp:08X}: {decode(word)}")
                break

    # Disassemble from 0x088531FC (lbu right before the validated slot function)
    # to 0x08853400 for the complete validation function
    disasm(eboot, 0x088531FC, 0x088533E0,
           "Validation function (0x088531FC - complete)")

    # === 5. Who calls the equipment copy function? ===
    # The equipment copy function starts around 0x08852E08
    # Search for jal to addresses in 0x08852E00-0x08852E20
    print("\n" + "=" * 70)
    print("  Searching for callers of equipment copy/validation functions")
    print("=" * 70)

    for target_start in range(0x08852E08, 0x08852E20, 4):
        target_field = (target_start >> 2) & 0x3FFFFFF
        jal_word = (0x03 << 26) | target_field
        for off in range(0, len(eboot) - 3, 4):
            word = struct.unpack_from('<I', eboot, off)[0]
            if word == jal_word:
                psp = EBOOT_LOAD_ADDR + off
                print(f"  jal 0x{target_start:08X} from 0x{psp:08X}")

    # Also check for callers to the function that STARTS the validation
    # chain - around 0x08852D70 or wherever the switch starts
    for target_start in [0x08852D70, 0x08852D60, 0x08852D50, 0x08852D40,
                         0x088531FC, 0x08853194, 0x08853190]:
        target_field = (target_start >> 2) & 0x3FFFFFF
        jal_word = (0x03 << 26) | target_field
        for off in range(0, len(eboot) - 3, 4):
            word = struct.unpack_from('<I', eboot, off)[0]
            if word == jal_word:
                psp = EBOOT_LOAD_ADDR + off
                print(f"  jal 0x{target_start:08X} from 0x{psp:08X}")

    # === 6. Search for jalr calls that might call these functions via pointers ===
    # Actually, look for the complete function that contains 0x08852E08
    # It was preceded by: jr $ra; nop at 0x08852E00/E04
    # So 0x08852E08 IS a function start!
    disasm(eboot, 0x08852E08, 0x08852E20,
           "Function prologue at 0x08852E08")

    # Search for jal 0x08852E08
    target_field = (0x08852E08 >> 2) & 0x3FFFFFF
    jal_word = (0x03 << 26) | target_field
    print(f"\n  Searching for jal 0x08852E08 (word=0x{jal_word:08X})...")
    for off in range(0, len(eboot) - 3, 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        if word == jal_word:
            psp = EBOOT_LOAD_ADDR + off
            print(f"    Called from 0x{psp:08X}")

    # === 7. Search for jal 0x088601E0 or nearby (visual lookup) ===
    for target in range(0x088601C0, 0x08860220, 4):
        target_field = (target >> 2) & 0x3FFFFFF
        jal_word = (0x03 << 26) | target_field
        for off in range(0, len(eboot) - 3, 4):
            word = struct.unpack_from('<I', eboot, off)[0]
            if word == jal_word:
                psp = EBOOT_LOAD_ADDR + off
                print(f"  jal 0x{target:08X} from 0x{psp:08X}")

    # === 8. Key question: what reads equip_id and determines which model to load? ===
    # The main armor table at 0x089633A8 has visual_index at entry[18] (offset 36)
    # Search for functions that read from armor_table + offset 36 (u16[18])
    # The visual_index maps equip_id → visual_table_index
    # armor_table[equip_id * 40 + 36] = visual_index
    # Offset 36 = 0x24 from entry start
    # The pattern would be: *40 computation, then lhu $reg, 36($result)
    print("\n" + "=" * 70)
    print("  Search: LHU with offset 36 (0x24) near *40 patterns")
    print("  (Reading visual_index from armor table entries)")
    print("=" * 70)

    # Find *40 patterns
    mul40_locs = []
    for off in range(0, len(eboot) - 11, 4):
        w1 = struct.unpack_from('<I', eboot, off)[0]
        if (w1 >> 26) == 0 and (w1 & 0x3F) == 0 and ((w1 >> 6) & 0x1F) == 2:
            rd1 = (w1 >> 11) & 0x1F
            rt1 = (w1 >> 16) & 0x1F
            w2 = struct.unpack_from('<I', eboot, off + 4)[0]
            if (w2 >> 26) == 0 and (w2 & 0x3F) == 0x21:
                rs2 = (w2 >> 21) & 0x1F
                rt2 = (w2 >> 16) & 0x1F
                rd2 = (w2 >> 11) & 0x1F
                if (rs2 == rd1 and rt2 == rt1) or (rs2 == rt1 and rt2 == rd1):
                    w3 = struct.unpack_from('<I', eboot, off + 8)[0]
                    if (w3 >> 26) == 0 and (w3 & 0x3F) == 0 and ((w3 >> 6) & 0x1F) == 3:
                        rt3 = (w3 >> 16) & 0x1F
                        if rt3 == rd2:
                            mul40_locs.append(EBOOT_LOAD_ADDR + off)

    for mul_psp in mul40_locs:
        mul_off = mul_psp - EBOOT_LOAD_ADDR
        # Search for lhu with offset 0x24 (36) in the next 40 bytes
        for delta in range(12, 40, 4):
            check = mul_off + delta
            if check + 3 >= len(eboot): continue
            w = struct.unpack_from('<I', eboot, check)[0]
            opcode = (w >> 26) & 0x3F
            imm = w & 0xFFFF
            if opcode == 0x25 and imm == 0x0024:  # lhu with offset 36
                psp = EBOOT_LOAD_ADDR + check
                print(f"\n  *40 at 0x{mul_psp:08X}, lhu offset 0x24 at 0x{psp:08X}")
                # Disassemble context
                start = max(EBOOT_LOAD_ADDR, mul_psp - 20)
                end = min(EBOOT_LOAD_ADDR + len(eboot), psp + 40)
                for p in range(start, end, 4):
                    o = p - EBOOT_LOAD_ADDR
                    word = struct.unpack_from('<I', eboot, o)[0]
                    marker = " <--" if p == psp else ""
                    marker2 = " <-- *40" if p == mul_psp else ""
                    print(f"    0x{p:08X}: {word:08X}  {decode(word)}{marker}{marker2}")

    # === 9. Also search for the main armor table base 0x089633A8 ===
    print("\n" + "=" * 70)
    print("  Search: References to main armor table 0x089633A8")
    print("=" * 70)
    # lui 0x0896, addiu 0x33A8
    target_addr = 0x089633A8
    hi = 0x0896
    lo = 0x33A8  # positive, so lui = 0x0896
    found = []
    for off in range(0, len(eboot) - 7, 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        if (word >> 26) == 0x0F:  # lui
            imm = word & 0xFFFF
            if imm == hi:
                rt = (word >> 16) & 0x1F
                for delta in range(4, 40, 4):
                    if off + delta + 3 >= len(eboot): break
                    word2 = struct.unpack_from('<I', eboot, off + delta)[0]
                    if (word2 >> 26) == 0x09:  # addiu
                        rs2 = (word2 >> 21) & 0x1F
                        imm2 = word2 & 0xFFFF
                        imm2_signed = imm2 if imm2 < 0x8000 else imm2 - 0x10000
                        if rs2 == rt and imm2_signed == lo:
                            psp1 = EBOOT_LOAD_ADDR + off
                            psp2 = EBOOT_LOAD_ADDR + off + delta
                            found.append((psp1, psp2))
                            break
    print(f"  Found {len(found)} references to 0x089633A8:")
    for psp1, psp2 in found:
        print(f"    lui at 0x{psp1:08X}, addiu at 0x{psp2:08X}")
        # Disassemble context around the addiu
        start = max(EBOOT_LOAD_ADDR, psp1 - 8)
        end = min(EBOOT_LOAD_ADDR + len(eboot), psp2 + 32)
        for p in range(start, end, 4):
            o = p - EBOOT_LOAD_ADDR
            word = struct.unpack_from('<I', eboot, o)[0]
            print(f"      0x{p:08X}: {word:08X}  {decode(word)}")
        print()


if __name__ == '__main__':
    main()

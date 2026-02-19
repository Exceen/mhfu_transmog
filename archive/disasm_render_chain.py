#!/opt/homebrew/bin/python3
"""Disassemble the rendering/model loading code chain.

Key targets:
1. Function at 0x088DB700 area - reads head equip_id near file ID switch
2. Function at 0x088C5600 area - reads all equip slots (legs/head/body/waist/arm)
3. The file ID switch at 0x088DAB78
4. Find who CALLS these functions

Also check: what uses the model_index value that ends up at 0x090AF6BA
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


def find_callers(eboot, target_addr):
    """Find all jal instructions targeting this address."""
    target_field = (target_addr >> 2) & 0x3FFFFFF
    jal_word = (0x03 << 26) | target_field
    callers = []
    for off in range(0, len(eboot) - 3, 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        if word == jal_word:
            psp = EBOOT_LOAD_ADDR + off
            callers.append(psp)
    return callers


def main():
    with open(EBOOT_PATH, 'rb') as f:
        eboot = f.read()

    # === 1. Function that reads ALL equip slots at 0x088DB700 area ===
    # Has: lhu $v1, 46($s0) at 0x088DB704
    #      lhu $v1, 58($s0) at 0x088DB73C
    #      lhu $v1, 70($s0) at 0x088DB774
    #      lhu $v1, 82($s0) at 0x088DB7AC
    #      lhu $v1, 94($s0) at 0x088DB7E4
    # This reads ALL 5 equipment slot equip_ids from the active slots!
    # Near the file ID switch at 0x088DAB78 - this could be the rendering chain
    disasm(eboot, 0x088DB680, 0x088DB900,
           "Equip slot reader near file ID switch (0x088DB700 area)")

    # === 2. Function at 0x088C5600 area ===
    # Has: lhu $a1, 46($s5) at 0x088C5800
    #      lhu $a1, 58($s5) at 0x088C56C8  (HEAD!)
    #      lhu $a1, 70($s5) at 0x088C5714
    #      lhu $a1, 82($s5) at 0x088C5760
    #      lhu $a1, 94($s5) at 0x088C57AC
    disasm(eboot, 0x088C5600, 0x088C5900,
           "All-slots reader function (0x088C5600 area)")

    # === 3. The file ID switch at 0x088DAB78 - larger context ===
    disasm(eboot, 0x088DAB00, 0x088DAD00,
           "File ID switch function (0x088DAB78)")

    # === 4. Find callers of these functions ===
    print("\n" + "=" * 70)
    print("  Finding callers of key functions")
    print("=" * 70)

    # Find function start for the 0x088DB700 area function
    # Look for prologue before 0x088DB680
    for psp in range(0x088DB680, 0x088DB600, -4):
        off = psp - EBOOT_LOAD_ADDR
        word = struct.unpack_from('<I', eboot, off)[0]
        # Check for jr $ra (end of previous function)
        if word == 0x03E00008:
            func_start = psp + 8  # Skip jr + delay slot
            print(f"  Function at 0x088DB700 area likely starts at 0x{func_start:08X}")
            callers = find_callers(eboot, func_start)
            print(f"    Callers: {[f'0x{c:08X}' for c in callers]}")
            break

    # Find function start for the 0x088C5600 area function
    for psp in range(0x088C5600, 0x088C5500, -4):
        off = psp - EBOOT_LOAD_ADDR
        word = struct.unpack_from('<I', eboot, off)[0]
        if word == 0x03E00008:
            func_start = psp + 8
            print(f"  Function at 0x088C5600 area likely starts at 0x{func_start:08X}")
            callers = find_callers(eboot, func_start)
            print(f"    Callers: {[f'0x{c:08X}' for c in callers]}")
            break

    # === 5. What functions are called from the 0x088DB700 area? ===
    print("\n" + "=" * 70)
    print("  Functions called FROM equip slot reader (0x088DB680-0x088DB900)")
    print("=" * 70)
    for off in range((0x088DB680 - EBOOT_LOAD_ADDR), (0x088DB900 - EBOOT_LOAD_ADDR), 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        if (word >> 26) == 0x03:  # jal
            target = (word & 0x3FFFFFF) << 2 | 0x08000000
            psp = EBOOT_LOAD_ADDR + off
            print(f"    0x{psp:08X}: jal 0x{target:08X}")

    # === 6. What functions are called from 0x088C5600 area? ===
    print("\n" + "=" * 70)
    print("  Functions called FROM all-slots reader (0x088C5600-0x088C5900)")
    print("=" * 70)
    for off in range((0x088C5600 - EBOOT_LOAD_ADDR), (0x088C5900 - EBOOT_LOAD_ADDR), 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        if (word >> 26) == 0x03:  # jal
            target = (word & 0x3FFFFFF) << 2 | 0x08000000
            psp = EBOOT_LOAD_ADDR + off
            print(f"    0x{psp:08X}: jal 0x{target:08X}")

    # === 7. Trace back from the file ID switch ===
    # The file switch at 0x088DAB78 is likely called from a model loading function
    # Find function start
    for psp in range(0x088DAB78, 0x088DAA00, -4):
        off = psp - EBOOT_LOAD_ADDR
        word = struct.unpack_from('<I', eboot, off)[0]
        opcode = (word >> 26) & 0x3F
        if opcode == 0x09:  # addiu
            rs = (word >> 21) & 0x1F
            rt = (word >> 16) & 0x1F
            simm = (word & 0xFFFF) if (word & 0xFFFF) < 0x8000 else (word & 0xFFFF) - 0x10000
            if rs == 29 and rt == 29 and simm < 0:
                print(f"\n  File ID switch function starts at 0x{psp:08X}: {decode(word)}")
                callers = find_callers(eboot, psp)
                print(f"    Callers: {[f'0x{c:08X}' for c in callers]}")
                break

    # === 8. Disassemble the area between equip reader and file ID switch ===
    # 0x088DB700 reads equip IDs, 0x088DAB78 handles file IDs
    # There must be functions in between that do the mapping
    # Let's look at all jal targets called from 0x088DB700 area
    print("\n" + "=" * 70)
    print("  Tracing equip_id → file_id mapping chain")
    print("=" * 70)

    # Specifically look at what happens AFTER reading equip_ids at 0x088DB73C
    disasm(eboot, 0x088DB730, 0x088DB780,
           "After reading head equip_id at 0x088DB73C")

    # === 9. Check for *40 pattern near 0x088DB73C (armor table lookup) ===
    print("\n" + "=" * 70)
    print("  *40 patterns near equip slot reader")
    print("=" * 70)
    for off in range((0x088DB680 - EBOOT_LOAD_ADDR), (0x088DB900 - EBOOT_LOAD_ADDR), 4):
        w = struct.unpack_from('<I', eboot, off)[0]
        if (w >> 26) == 0 and (w & 0x3F) == 0:  # sll
            shamt = (w >> 6) & 0x1F
            if shamt in (2, 3):
                psp = EBOOT_LOAD_ADDR + off
                print(f"    0x{psp:08X}: {w:08X}  {decode(w)}")


if __name__ == '__main__':
    main()

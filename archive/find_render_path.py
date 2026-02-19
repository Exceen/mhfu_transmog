#!/opt/homebrew/bin/python3
"""Find the rendering code path: what reads the validated head slot
and how does the game map equip_id → visual model.

Strategy:
1. Search for load/store instructions with offset 0x4024 (validated head slot)
2. Search for load/store instructions with offset 0x3A (raw head equip_id from equip struct)
3. Search for references to visual table base 0x08960754
4. Search for the *40 multiplication pattern near visual table accesses
5. Disassemble surrounding code for each match
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


def disasm_range(eboot, psp_start, psp_end, label=""):
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

    # === 1. Search for load/store with offset 0x4024 (validated head slot) ===
    # Also search nearby offsets for other slots:
    # Legs=0x4022, Head=0x4024, Body=0x4026, Waist=0x4028, Arm=0x402A
    print("=" * 70)
    print("  Search: Load/Store with validated slot offsets (0x4022-0x402A)")
    print("=" * 70)

    slot_offsets = {
        0x4022: "Legs", 0x4024: "Head", 0x4026: "Body",
        0x4028: "Waist", 0x402A: "Arm"
    }

    for off_val, slot_name in slot_offsets.items():
        found = []
        for off in range(0, len(eboot) - 3, 4):
            word = struct.unpack_from('<I', eboot, off)[0]
            imm = word & 0xFFFF
            opcode = (word >> 26) & 0x3F
            # Check if this is a load or store instruction with our offset
            if imm == off_val and opcode in (0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B):
                psp = EBOOT_LOAD_ADDR + off
                found.append((psp, word))
        if found:
            print(f"\n  Offset 0x{off_val:04X} ({slot_name} validated): {len(found)} matches")
            for psp, word in found:
                print(f"    PSP 0x{psp:08X}: {word:08X}  {decode(word)}")

    # === 2. Search for load/store with offset 0x3A (raw head equip_id) ===
    # And other raw equip offsets: 0x2E (legs), 0x46 (body), 0x52 (waist), 0x5E (arm)
    print("\n" + "=" * 70)
    print("  Search: LHU with raw equip slot offsets (0x2E, 0x3A, 0x46, 0x52, 0x5E)")
    print("=" * 70)

    raw_offsets = {0x2E: "Legs", 0x3A: "Head", 0x46: "Body", 0x52: "Waist", 0x5E: "Arm"}
    # Only search for LHU (0x25) and SH (0x29) since these are u16 equip IDs
    for off_val, slot_name in raw_offsets.items():
        found = []
        for off in range(0, len(eboot) - 3, 4):
            word = struct.unpack_from('<I', eboot, off)[0]
            imm = word & 0xFFFF
            opcode = (word >> 26) & 0x3F
            if imm == off_val and opcode in (0x25, 0x29):  # lhu, sh
                psp = EBOOT_LOAD_ADDR + off
                found.append((psp, word))
        if found:
            print(f"\n  Offset 0x{off_val:04X} ({slot_name} raw equip_id): {len(found)} matches")
            for psp, word in found:
                print(f"    PSP 0x{psp:08X}: {word:08X}  {decode(word)}")
        else:
            print(f"\n  Offset 0x{off_val:04X} ({slot_name} raw equip_id): 0 matches")

    # === 3. Search for references to visual table bases ===
    # Visual tables: 0x08960754, 0x08964B74, 0x0896CD4C, 0x08968D14, 0x08970D34
    print("\n" + "=" * 70)
    print("  Search: Visual table base references")
    print("=" * 70)

    visual_tables = [
        (0x0896, 0x0754, "visual_table_1"),
        (0x0896, 0x4B74, "visual_table_2"),  # Note: 0x4B74 as signed = 0x4B74
        (0x0897, 0x0D34, "visual_table_5"),  # Note: 0x0897 + 0x0D34
        (0x0896, -0x32B4, "visual_table_3_CD4C"),  # 0x0896CD4C = lui 0x0897, addiu -0x32B4
        (0x0897, -0x72EC, "visual_table_4_8D14"),  # 0x08968D14 = lui 0x0897, addiu -0x72EC
    ]

    # Actually let me just search for LUI 0x0896 and LUI 0x0897 followed by addiu/ori
    # that form known visual table addresses
    known_visual_addrs = [0x08960754, 0x08964B74, 0x0896CD4C, 0x08968D14, 0x08970D34]

    for target_addr in known_visual_addrs:
        hi = (target_addr >> 16) & 0xFFFF
        lo = target_addr & 0xFFFF
        lo_signed = lo if lo < 0x8000 else lo - 0x10000
        # If lo is negative (>= 0x8000), lui uses hi+1
        if lo >= 0x8000:
            lui_val = (hi + 1) & 0xFFFF
        else:
            lui_val = hi

        found = []
        for off in range(0, len(eboot) - 7, 4):
            word = struct.unpack_from('<I', eboot, off)[0]
            opcode = (word >> 26) & 0x3F
            if opcode == 0x0F:  # lui
                imm = word & 0xFFFF
                if imm == lui_val:
                    rt = (word >> 16) & 0x1F
                    # Check next few instructions for addiu with lo_signed
                    for delta in range(4, 40, 4):
                        if off + delta + 3 >= len(eboot): break
                        word2 = struct.unpack_from('<I', eboot, off + delta)[0]
                        opcode2 = (word2 >> 26) & 0x3F
                        if opcode2 == 0x09:  # addiu
                            rs2 = (word2 >> 21) & 0x1F
                            imm2 = word2 & 0xFFFF
                            imm2_signed = imm2 if imm2 < 0x8000 else imm2 - 0x10000
                            if rs2 == rt and imm2_signed == lo_signed:
                                psp1 = EBOOT_LOAD_ADDR + off
                                psp2 = EBOOT_LOAD_ADDR + off + delta
                                found.append((psp1, psp2))
                                break
        if found:
            print(f"\n  Visual table 0x{target_addr:08X}: {len(found)} references")
            for psp1, psp2 in found[:15]:
                print(f"    lui at 0x{psp1:08X}, addiu at 0x{psp2:08X}")

    # === 4. Find functions that both read equip_id AND do *40 multiplication ===
    # These are the key equip→visual mapping functions
    print("\n" + "=" * 70)
    print("  Search: Functions with both equip_id load AND *40 pattern")
    print("=" * 70)

    # Find all *40 pattern locations
    mul40_locs = set()
    for off in range(0, len(eboot) - 11, 4):
        w1 = struct.unpack_from('<I', eboot, off)[0]
        # sll $rd, $rt, 2
        if (w1 >> 26) == 0 and (w1 & 0x3F) == 0 and ((w1 >> 6) & 0x1F) == 2:
            rd1 = (w1 >> 11) & 0x1F
            rt1 = (w1 >> 16) & 0x1F
            w2 = struct.unpack_from('<I', eboot, off + 4)[0]
            # addu $rd2, $rd1, $rt1
            if (w2 >> 26) == 0 and (w2 & 0x3F) == 0x21:
                rs2 = (w2 >> 21) & 0x1F
                rt2 = (w2 >> 16) & 0x1F
                rd2 = (w2 >> 11) & 0x1F
                if (rs2 == rd1 and rt2 == rt1) or (rs2 == rt1 and rt2 == rd1):
                    w3 = struct.unpack_from('<I', eboot, off + 8)[0]
                    # sll $rd3, $rd2, 3
                    if (w3 >> 26) == 0 and (w3 & 0x3F) == 0 and ((w3 >> 6) & 0x1F) == 3:
                        rt3 = (w3 >> 16) & 0x1F
                        if rt3 == rd2:
                            psp = EBOOT_LOAD_ADDR + off
                            mul40_locs.add(psp)

    # For each *40 location, check if there's a nearby LHU from validated slot offsets
    # or from raw equip offsets
    interesting_offsets = set(slot_offsets.keys()) | set(raw_offsets.keys())

    print(f"\n  Found {len(mul40_locs)} *40 patterns total")
    for mul_psp in sorted(mul40_locs):
        mul_off = mul_psp - EBOOT_LOAD_ADDR
        # Search in a 500-byte window around the *40 pattern
        nearby_equip_loads = []
        for delta in range(-200, 300, 4):
            check = mul_off + delta
            if check < 0 or check + 3 >= len(eboot): continue
            w = struct.unpack_from('<I', eboot, check)[0]
            opcode = (w >> 26) & 0x3F
            imm = w & 0xFFFF
            if opcode in (0x25, 0x29) and imm in interesting_offsets:  # lhu or sh
                psp = EBOOT_LOAD_ADDR + check
                nearby_equip_loads.append((psp, w))
        if nearby_equip_loads:
            print(f"\n  *40 at 0x{mul_psp:08X} has nearby equip loads:")
            for psp, w in nearby_equip_loads:
                print(f"    0x{psp:08X}: {w:08X}  {decode(w)}")

    # === 5. Disassemble key functions that access validated head slot ===
    # Search for functions with offset 0x4024
    print("\n" + "=" * 70)
    print("  Disassembly of functions accessing validated head slot (offset 0x4024)")
    print("=" * 70)

    for off in range(0, len(eboot) - 3, 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        imm = word & 0xFFFF
        opcode = (word >> 26) & 0x3F
        if imm == 0x4024 and opcode in (0x25, 0x29):  # lhu or sh
            psp = EBOOT_LOAD_ADDR + off
            # Disassemble a window around this instruction
            start = max(EBOOT_LOAD_ADDR, psp - 80)
            end = min(EBOOT_LOAD_ADDR + len(eboot), psp + 80)
            instr_type = "LHU (read)" if opcode == 0x25 else "SH (write)"
            disasm_range(eboot, start, end,
                        f"{instr_type} at PSP 0x{psp:08X} with offset 0x4024 (validated head)")

    # === 6. Search for the function at 0x08853248 - the validation function ===
    # This is the known function that stores to validated slots
    # Let's check what CALLS this function
    print("\n" + "=" * 70)
    print("  Who calls the validation function?")
    print("=" * 70)

    # Search for jal 0x08853248 and nearby function starts
    target = 0x08853248
    target_field = (target >> 2) & 0x3FFFFFF
    jal_word = (0x03 << 26) | target_field
    callers = []
    for off in range(0, len(eboot) - 3, 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        if word == jal_word:
            psp = EBOOT_LOAD_ADDR + off
            callers.append(psp)
    print(f"\n  jal 0x{target:08X} called from {len(callers)} locations:")
    for psp in callers:
        print(f"    0x{psp:08X}")

    # Also search for validation function range (0x08852F00-0x08853400)
    # to find jal to other targets called FROM this function
    print(f"\n  Functions called FROM validation area (0x08852F00-0x08853400):")
    called = set()
    for off in range((0x08852F00 - EBOOT_LOAD_ADDR), (0x08853400 - EBOOT_LOAD_ADDR), 4):
        if off < 0 or off + 3 >= len(eboot): continue
        word = struct.unpack_from('<I', eboot, off)[0]
        if (word >> 26) == 0x03:  # jal
            target = (word & 0x3FFFFFF) << 2 | 0x08000000
            psp = EBOOT_LOAD_ADDR + off
            called.add((psp, target))
    for psp, target in sorted(called):
        print(f"    0x{psp:08X}: jal 0x{target:08X}")

    # === 7. Specifically look for the equip change / model reload trigger ===
    # The equipment change event handler must:
    # 1. Update equip_id in the equipment struct
    # 2. Call the validation function
    # 3. Trigger model loading
    # Search for functions that store halfwords to offset 0x3A (head equip_id in equip struct)
    print("\n" + "=" * 70)
    print("  Functions that WRITE to head equip slot (SH with offset 0x3A)")
    print("=" * 70)

    for off in range(0, len(eboot) - 3, 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        opcode = (word >> 26) & 0x3F
        imm = word & 0xFFFF
        if opcode == 0x29 and imm == 0x003A:  # sh with offset 0x3A
            psp = EBOOT_LOAD_ADDR + off
            start = max(EBOOT_LOAD_ADDR, psp - 60)
            end = min(EBOOT_LOAD_ADDR + len(eboot), psp + 60)
            disasm_range(eboot, start, end,
                        f"SH to offset 0x3A at PSP 0x{psp:08X}")


if __name__ == '__main__':
    main()

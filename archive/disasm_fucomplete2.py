#!/opt/homebrew/bin/python3
"""Disassemble FUComplete's actual rendering code from save state.
Focus on:
1. 0x088C3114 area - where lhu $a1, 58($s5) loads head equip_id
2. 0x08820818 area - where slot-specific dispatch calls are made
3. 0x08851A20 area - another head equip_id load
4. 0x088D9188 area - another head equip_id load
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

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


def disasm_state(data, psp_start, psp_end, label=""):
    if label:
        print(f"\n{'='*70}")
        print(f"  {label}")
        print(f"  PSP 0x{psp_start:08X} - 0x{psp_end:08X}")
        print(f"{'='*70}")
    for psp in range(psp_start, psp_end, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off < 0 or off + 3 >= len(data): continue
        word = struct.unpack_from('<I', data, off)[0]
        d = decode(word)
        # Mark interesting instructions
        mark = ""
        if "lhu" in d and ("58(" in d or "70(" in d or "82(" in d or "46(" in d or "94(" in d):
            mark = "  <== EQUIP_ID LOAD"
        if "jal 0x08851" in d:
            mark = "  <== DISPATCH CALL"
        if "j 0x08851" in d and "jal" not in d:
            mark = "  <== DISPATCH JUMP"
        if "0x088513CC" in d:
            mark = "  <== HANDLER"
        print(f"  0x{psp:08X}: {word:08X}  {d}{mark}")


def main():
    print("Loading save state...")
    data = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)
    print(f"  Decompressed: {len(data)} bytes")

    # === 1. Head equip_id load at 0x088C3114 ===
    disasm_state(data, 0x088C3000, 0x088C3200,
                 "Area around 0x088C3114 (head equip_id load: lhu $a1, 58($s5))")

    # === 2. Slot-specific dispatch calls at 0x08820818 ===
    disasm_state(data, 0x08820780, 0x08820900,
                 "Area around 0x08820818 (dispatch calls for all slots)")

    # === 3. Head equip_id load at 0x08851A20 ===
    disasm_state(data, 0x08851980, 0x08851AC0,
                 "Area around 0x08851A20 (head equip_id load: lhu $a1, 58($v1))")

    # === 4. Head equip_id load at 0x088D9188 ===
    disasm_state(data, 0x088D9100, 0x088D9250,
                 "Area around 0x088D9188 (head equip_id load: lhu $v1, 58($s0))")

    # === 5. Another head load at 0x08850C8C ===
    disasm_state(data, 0x08850C00, 0x08850D40,
                 "Area around 0x08850C8C (head equip_id load: lhu $a3, 58($a1))")

    # === 6. Who calls the function containing 0x088C3114? ===
    # Find function start (look for addiu $sp, $sp, -N)
    print("\n" + "=" * 70)
    print("  Finding function boundaries near 0x088C3114")
    print("=" * 70)
    for psp in range(0x088C3114, 0x088C3000, -4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        word = struct.unpack_from('<I', data, off)[0]
        d = decode(word)
        if "addiu $sp, $sp, -" in d:
            print(f"  Function start: 0x{psp:08X}: {d}")
            # Search for callers of this function
            func_addr = psp
            target_enc = ((func_addr >> 2) & 0x3FFFFFF) | (0x03 << 26)
            print(f"  Searching for jal 0x{func_addr:08X}...")
            for search_psp in range(0x08804000, 0x08A00000, 4):
                s_off = search_psp - PSP_RAM_START + RAM_BASE_IN_STATE
                if s_off + 3 >= len(data): continue
                s_word = struct.unpack_from('<I', data, s_off)[0]
                if s_word == target_enc:
                    print(f"    Called from 0x{search_psp:08X}")
            break

    # === 7. Who calls the function containing 0x08820818? ===
    print("\n" + "=" * 70)
    print("  Finding function boundaries near 0x08820818")
    print("=" * 70)
    for psp in range(0x08820818, 0x08820700, -4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        word = struct.unpack_from('<I', data, off)[0]
        d = decode(word)
        if "addiu $sp, $sp, -" in d:
            print(f"  Function start: 0x{psp:08X}: {d}")
            func_addr = psp
            target_enc = ((func_addr >> 2) & 0x3FFFFFF) | (0x03 << 26)
            print(f"  Searching for jal 0x{func_addr:08X}...")
            for search_psp in range(0x08804000, 0x08A00000, 4):
                s_off = search_psp - PSP_RAM_START + RAM_BASE_IN_STATE
                if s_off + 3 >= len(data): continue
                s_word = struct.unpack_from('<I', data, s_off)[0]
                if s_word == target_enc:
                    print(f"    Called from 0x{search_psp:08X}")
            break


if __name__ == '__main__':
    main()

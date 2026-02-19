#!/opt/homebrew/bin/python3
"""Disassemble FUComplete's ACTUAL running code from the save state.

Key findings so far:
- FUComplete has COMPLETELY rewritten the model lookup functions (0x08851440+),
  the rendering chain (0x088C5600+), and the data copier (0x088DB680+)
- The dispatch table entries at 0x08851440+ all jump to 0x088513CC
- We need to find where FUComplete reads equip_id for rendering

This script:
1. Reads the save state directly (not EBOOT.BIN)
2. Disassembles the dispatch handler at 0x088513CC
3. Searches for lhu instructions with equip_id offsets in code areas
4. Traces the actual rendering path
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


def read_word(data, psp_addr):
    off = psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


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
        print(f"  0x{psp:08X}: {word:08X}  {decode(word)}")


def main():
    print("Loading save state...")
    data = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)
    print(f"  Decompressed: {len(data)} bytes")

    # === 1. Disassemble the dispatch handler at 0x088513CC ===
    # This is where ALL dispatch table entries jump to
    # Start from a bit before to find the function start
    disasm_state(data, 0x08851300, 0x08851440,
                 "FUComplete dispatch handler at 0x088513CC (and surrounding code)")

    # === 2. Disassemble the dispatch table entries ===
    disasm_state(data, 0x08851440, 0x088515B0,
                 "FUComplete dispatch table (0x08851440-0x088515B0)")

    # === 3. Search for lhu instructions in code area that load from equip slot offsets ===
    # Active head equip_id is at offset 0x3A (58) in the equipment struct
    # Other offsets: body=0x46(70), waist=0x52(82), arm=0x2E(46), legs=0x5E(94)
    print("\n" + "=" * 70)
    print("  Searching save state code for lhu with equip_id offsets")
    print("  (looking in FUComplete code area 0x08804000-0x08A00000)")
    print("=" * 70)

    equip_offsets = {
        58: "head (0x3A)", 70: "body (0x46)", 82: "waist (0x52)",
        46: "arm (0x2E)", 94: "legs (0x5E)"
    }

    for psp in range(0x08804000, 0x08A00000, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off < 0 or off + 3 >= len(data): continue
        word = struct.unpack_from('<I', data, off)[0]
        opcode = (word >> 26) & 0x3F
        if opcode == 0x25:  # lhu
            imm = word & 0xFFFF
            simm = imm if imm < 0x8000 else imm - 0x10000
            if simm in equip_offsets:
                rt = (word >> 16) & 0x1F
                rs = (word >> 21) & 0x1F
                print(f"  0x{psp:08X}: {word:08X}  lhu {REG_NAMES[rt]}, {simm}({REG_NAMES[rs]})  [{equip_offsets[simm]}]")

    # === 4. Search for calls to jal 0x088513CC (the dispatch handler) ===
    print("\n" + "=" * 70)
    print("  Calls to dispatch handler 0x088513CC")
    print("=" * 70)
    target_enc = ((0x088513CC >> 2) & 0x3FFFFFF) | (0x03 << 26)
    for psp in range(0x08804000, 0x08A00000, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off < 0 or off + 3 >= len(data): continue
        word = struct.unpack_from('<I', data, off)[0]
        if word == target_enc:
            print(f"  0x{psp:08X}: jal 0x088513CC")

    # === 5. Search for j 0x088513CC (jumps, not calls) ===
    print("\n" + "=" * 70)
    print("  Jumps (j) to dispatch handler 0x088513CC")
    print("=" * 70)
    target_enc_j = ((0x088513CC >> 2) & 0x3FFFFFF) | (0x02 << 26)
    for psp in range(0x08804000, 0x08A00000, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off < 0 or off + 3 >= len(data): continue
        word = struct.unpack_from('<I', data, off)[0]
        if word == target_enc_j:
            print(f"  0x{psp:08X}: j 0x088513CC")

    # === 6. Look for the rendering chain entry point ===
    # The rendering chain was at 0x088C56BC in the save state - it's a new function
    # Let's disassemble a wider area around where the rendering chain was
    disasm_state(data, 0x088C54A0, 0x088C5700,
                 "FUComplete code around old rendering chain area (0x088C54A0-0x088C5700)")

    # === 7. Search for jal 0x0885143C-0x088515B0 range ===
    # Any calls to the dispatch table entries
    print("\n" + "=" * 70)
    print("  Calls (jal) to dispatch table area 0x08851440-0x088515B0")
    print("=" * 70)
    for psp in range(0x08804000, 0x08A00000, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off < 0 or off + 3 >= len(data): continue
        word = struct.unpack_from('<I', data, off)[0]
        if (word >> 26) == 0x03:  # jal
            target = (word & 0x3FFFFFF) << 2 | 0x08000000
            if 0x08851440 <= target <= 0x088515B0:
                print(f"  0x{psp:08X}: jal 0x{target:08X}")

    # === 8. Check for FUComplete code in high memory (0x09xxxxxx) ===
    # FUComplete may have a separate code area
    print("\n" + "=" * 70)
    print("  Searching for jal/j to 0x09xxxxxx (FUComplete code area)")
    print("  (checking 0x08804000-0x08A00000)")
    print("=" * 70)
    fuc_calls = {}
    for psp in range(0x08804000, 0x08A00000, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off < 0 or off + 3 >= len(data): continue
        word = struct.unpack_from('<I', data, off)[0]
        opc = (word >> 26) & 0x3F
        if opc in (0x02, 0x03):  # j or jal
            target = (word & 0x3FFFFFF) << 2 | 0x08000000
            if 0x09000000 <= target < 0x0A000000:
                if target not in fuc_calls:
                    fuc_calls[target] = []
                fuc_calls[target].append(psp)
    for target in sorted(fuc_calls.keys()):
        callers = fuc_calls[target]
        label = "j" if any(True for c in callers
            if (read_word(data, c) >> 26) == 0x02) else "jal"
        print(f"  {label} 0x{target:08X} called from {len(callers)} locations:",
              ", ".join(f"0x{c:08X}" for c in callers[:5]),
              "..." if len(callers) > 5 else "")


if __name__ == '__main__':
    main()

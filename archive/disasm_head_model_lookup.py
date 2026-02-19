#!/opt/homebrew/bin/python3
"""Disassemble the head-specific model lookup function at 0x088514B8.
This is called from the rendering chain with (base_ptr, equip_id).
Understanding this function will tell us why equip_id 252 crashes.

Also disassemble the nearby slot functions:
  Head:  0x088514B8
  Body:  0x088514E4
  Waist: 0x08851510
  Arm:   0x0885153C
  Legs:  0x08851568
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

    # === 1. Head model lookup function at 0x088514B8 ===
    # Called with: $a0 = base pointer (from 0x089C7508), $a1 = equip_id
    # Returns: model data pointer in $v0
    disasm(eboot, 0x08851440, 0x088515A0,
           "All slot model lookup functions (head at 0x088514B8)")

    # === 2. Also disassemble the function these call ===
    # From earlier analysis, 0x08851448 calls a virtual function
    # Let's see the full chain
    disasm(eboot, 0x08851400, 0x08851450,
           "Base equip model function 0x08851448 (called from slot funcs?)")

    # === 3. Check the function that 0x088514B8 calls internally ===
    # By looking at what jal instructions are in the range
    print("\n" + "=" * 70)
    print("  JAL instructions in model lookup functions (0x08851440-0x088515A0)")
    print("=" * 70)
    for off in range((0x08851440 - EBOOT_LOAD_ADDR), (0x088515A0 - EBOOT_LOAD_ADDR), 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        if (word >> 26) == 0x03:  # jal
            target = (word & 0x3FFFFFF) << 2 | 0x08000000
            psp = EBOOT_LOAD_ADDR + off
            print(f"    0x{psp:08X}: jal 0x{target:08X}")

    # === 4. Check what the function at 0x0885143C does ===
    # This is called before EACH slot in the rendering chain
    disasm(eboot, 0x0885143C, 0x088514C0,
           "Function 0x0885143C (called before each slot model lookup)")

    # === 5. Verify what's at 0x088C56C8 in the EBOOT ===
    # Confirm the original instruction
    off = 0x088C56C8 - EBOOT_LOAD_ADDR
    word = struct.unpack_from('<I', eboot, off)[0]
    print(f"\n  Original instruction at 0x088C56C8: {word:08X} = {decode(word)}")

    # === 6. Check if FUComplete might have patched these functions ===
    # Look for any unusual instructions (like jumps to high memory)
    print("\n" + "=" * 70)
    print("  Checking for FUComplete patches in model lookup area")
    print("=" * 70)
    for off in range((0x08851440 - EBOOT_LOAD_ADDR), (0x088515B0 - EBOOT_LOAD_ADDR), 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        psp = EBOOT_LOAD_ADDR + off
        d = decode(word)
        # Check for jumps to unusual addresses (FUComplete hooks)
        if 'j 0x09' in d or 'jal 0x09' in d:
            print(f"  HOOK? 0x{psp:08X}: {word:08X}  {d}")
        # Also check for lui with high addresses
        if (word >> 26) == 0x0F:  # lui
            imm = word & 0xFFFF
            if imm >= 0x0900:
                print(f"  HIGH LUI: 0x{psp:08X}: {word:08X}  {d}")

    # === 7. Read the actual save state to check if the function is patched ===
    import zstandard
    STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
    PSP_RAM_START = 0x08000000
    RAM_BASE_IN_STATE = 0x48

    data = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

    print("\n" + "=" * 70)
    print("  Comparing EBOOT.BIN vs Save State for model lookup functions")
    print("  (differences = FUComplete patches)")
    print("=" * 70)

    for psp in range(0x08851440, 0x088515B0, 4):
        eboot_off = psp - EBOOT_LOAD_ADDR
        state_off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if eboot_off + 3 >= len(eboot) or state_off + 3 >= len(data):
            continue
        eboot_word = struct.unpack_from('<I', eboot, eboot_off)[0]
        state_word = struct.unpack_from('<I', data, state_off)[0]
        if eboot_word != state_word:
            print(f"  PATCHED: 0x{psp:08X}")
            print(f"    EBOOT: {eboot_word:08X}  {decode(eboot_word)}")
            print(f"    STATE: {state_word:08X}  {decode(state_word)}")

    # Also check the rendering chain area
    print("\n  Checking rendering chain (0x088C5600-0x088C5900):")
    for psp in range(0x088C5600, 0x088C5900, 4):
        eboot_off = psp - EBOOT_LOAD_ADDR
        state_off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if eboot_off + 3 >= len(eboot) or state_off + 3 >= len(data):
            continue
        eboot_word = struct.unpack_from('<I', eboot, eboot_off)[0]
        state_word = struct.unpack_from('<I', data, state_off)[0]
        if eboot_word != state_word:
            print(f"  PATCHED: 0x{psp:08X}")
            print(f"    EBOOT: {eboot_word:08X}  {decode(eboot_word)}")
            print(f"    STATE: {state_word:08X}  {decode(state_word)}")

    # Also check the data copier area
    print("\n  Checking data copier (0x088DB680-0x088DB820):")
    for psp in range(0x088DB680, 0x088DB820, 4):
        eboot_off = psp - EBOOT_LOAD_ADDR
        state_off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if eboot_off + 3 >= len(eboot) or state_off + 3 >= len(data):
            continue
        eboot_word = struct.unpack_from('<I', eboot, eboot_off)[0]
        state_word = struct.unpack_from('<I', data, state_off)[0]
        if eboot_word != state_word:
            print(f"  PATCHED: 0x{psp:08X}")
            print(f"    EBOOT: {eboot_word:08X}  {decode(eboot_word)}")
            print(f"    STATE: {state_word:08X}  {decode(state_word)}")


if __name__ == '__main__':
    main()

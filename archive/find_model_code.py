#!/opt/homebrew/bin/python3
"""Find MIPS code in the EBOOT that handles model index / file ID computation.

The attack cheat works by patching CODE (MIPS instructions). We need to find
the code that determines which model to load and patch it similarly.

Search strategy:
1. Find 'lui' instructions loading upper bits of known addresses
   (model array at 0x090BXXXX, file ID array at 0x0913XXXX, armor table at 0x0896XXXX)
2. Find store/load instructions with relevant offsets (0xF6BA, 0xF54C)
3. Cross-reference to find the model loading function
"""

import struct

EBOOT_PATH = "/Users/Exceen/Downloads/mhfu_transmog/EBOOT.BIN"
# EBOOT is loaded at this PSP address (from find_ram_base.py)
EBOOT_LOAD_ADDR = 0x08804000


def decode_instruction(word):
    """Basic MIPS instruction decoder."""
    opcode = (word >> 26) & 0x3F
    rs = (word >> 21) & 0x1F
    rt = (word >> 16) & 0x1F
    rd = (word >> 11) & 0x1F
    shamt = (word >> 6) & 0x1F
    funct = word & 0x3F
    imm = word & 0xFFFF
    simm = imm if imm < 0x8000 else imm - 0x10000
    target = word & 0x3FFFFFF

    reg_names = ['$zero','$at','$v0','$v1','$a0','$a1','$a2','$a3',
                 '$t0','$t1','$t2','$t3','$t4','$t5','$t6','$t7',
                 '$s0','$s1','$s2','$s3','$s4','$s5','$s6','$s7',
                 '$t8','$t9','$k0','$k1','$gp','$sp','$fp','$ra']

    if opcode == 0x0F:  # lui
        return f"lui {reg_names[rt]}, 0x{imm:04X}"
    elif opcode == 0x09:  # addiu
        return f"addiu {reg_names[rt]}, {reg_names[rs]}, {simm}"
    elif opcode == 0x29:  # sh (store halfword)
        return f"sh {reg_names[rt]}, {simm}({reg_names[rs]})"
    elif opcode == 0x25:  # lhu (load halfword unsigned)
        return f"lhu {reg_names[rt]}, {simm}({reg_names[rs]})"
    elif opcode == 0x21:  # lh (load halfword)
        return f"lh {reg_names[rt]}, {simm}({reg_names[rs]})"
    elif opcode == 0x23:  # lw (load word)
        return f"lw {reg_names[rt]}, {simm}({reg_names[rs]})"
    elif opcode == 0x2B:  # sw (store word)
        return f"sw {reg_names[rt]}, {simm}({reg_names[rs]})"
    elif opcode == 0x00:  # SPECIAL
        if funct == 0x00:
            return f"sll {reg_names[rd]}, {reg_names[rt]}, {shamt}"
        elif funct == 0x21:
            return f"addu {reg_names[rd]}, {reg_names[rs]}, {reg_names[rt]}"
        elif funct == 0x08:
            return f"jr {reg_names[rs]}"
        else:
            return f"special funct=0x{funct:02X}"
    elif opcode == 0x03:  # jal
        return f"jal 0x{(target << 2) | (0x08000000):08X}"
    elif opcode == 0x02:  # j
        return f"j 0x{(target << 2) | (0x08000000):08X}"
    else:
        return f"op=0x{opcode:02X} rs={reg_names[rs]} rt={reg_names[rt]} imm=0x{imm:04X}"

    return f"0x{word:08X}"


def main():
    with open(EBOOT_PATH, 'rb') as f:
        eboot = f.read()
    print(f"EBOOT size: {len(eboot)} bytes")

    # Parse ELF to find code sections
    # PSP ELF: entry point and loadable segments
    elf_magic = eboot[:4]
    print(f"Magic: {elf_magic}")

    # For simplicity, search the entire EBOOT binary
    # Instructions are 4-byte aligned

    # === Search 1: lui instructions with relevant upper addresses ===
    targets = {
        0x090B: "model index array (0x090BXXXX -> 0x090AF6XX)",
        0x090A: "model index array alt (0x090AXXXX)",
        0x0913: "file ID array (0x0913XXXX -> 0x0912F5XX)",
        0x0912: "file ID array alt",
        0x0896: "armor data table (0x0896XXXX)",
        0x0897: "armor data table alt",
    }

    print("\n=== LUI instructions with relevant immediates ===")
    for imm_target, desc in targets.items():
        matches = []
        for off in range(0, len(eboot) - 3, 4):
            word = struct.unpack_from('<I', eboot, off)[0]
            opcode = (word >> 26) & 0x3F
            if opcode == 0x0F:  # lui
                imm = word & 0xFFFF
                if imm == imm_target:
                    psp = EBOOT_LOAD_ADDR + off
                    matches.append((off, psp, word))

        print(f"\n  lui 0x{imm_target:04X} ({desc}): {len(matches)} matches")
        for off, psp, word in matches[:30]:
            decoded = decode_instruction(word)
            # Also show the next few instructions for context
            ctx = []
            for i in range(1, 6):
                if off + i*4 < len(eboot):
                    w = struct.unpack_from('<I', eboot, off + i*4)[0]
                    ctx.append(decode_instruction(w))
            print(f"    EBOOT+0x{off:06X} (PSP 0x{psp:08X}): {decoded}")
            for i, c in enumerate(ctx):
                ctx_psp = psp + (i+1)*4
                print(f"      +{(i+1)*4}: {c}")

    # === Search 2: Store halfword with offset 0xF6BA (model index write) ===
    print("\n" + "=" * 70)
    print("=== SH instructions with offset 0xF6BA (model index store) ===")
    # sh rt, -0x0946(rs) where -0x0946 = 0xF6BA as unsigned
    for off in range(0, len(eboot) - 3, 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        opcode = (word >> 26) & 0x3F
        imm = word & 0xFFFF
        if opcode == 0x29 and imm == 0xF6BA:  # sh with offset 0xF6BA
            psp = EBOOT_LOAD_ADDR + off
            decoded = decode_instruction(word)
            print(f"  EBOOT+0x{off:06X} (PSP 0x{psp:08X}): {decoded}")
            # Show context
            for i in range(-4, 8):
                if 0 <= off + i*4 < len(eboot):
                    w = struct.unpack_from('<I', eboot, off + i*4)[0]
                    ctx_psp = psp + i*4
                    marker = " <<<" if i == 0 else ""
                    print(f"    PSP 0x{ctx_psp:08X}: {decode_instruction(w)}{marker}")

    # === Search 3: Load halfword with offset 0xF6BA (model index read) ===
    print("\n=== LH/LHU instructions with offset 0xF6BA (model index load) ===")
    for off in range(0, len(eboot) - 3, 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        opcode = (word >> 26) & 0x3F
        imm = word & 0xFFFF
        if opcode in (0x21, 0x25) and imm == 0xF6BA:
            psp = EBOOT_LOAD_ADDR + off
            decoded = decode_instruction(word)
            print(f"  EBOOT+0x{off:06X} (PSP 0x{psp:08X}): {decoded}")
            for i in range(-4, 8):
                if 0 <= off + i*4 < len(eboot):
                    w = struct.unpack_from('<I', eboot, off + i*4)[0]
                    ctx_psp = psp + i*4
                    marker = " <<<" if i == 0 else ""
                    print(f"    PSP 0x{ctx_psp:08X}: {decode_instruction(w)}{marker}")

    # === Search 4: References to file ID offset 0xF54C ===
    print("\n=== SH/LH with offset 0xF54C (file ID head) ===")
    for off in range(0, len(eboot) - 3, 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        opcode = (word >> 26) & 0x3F
        imm = word & 0xFFFF
        if opcode in (0x21, 0x25, 0x29) and imm == 0xF54C:
            psp = EBOOT_LOAD_ADDR + off
            decoded = decode_instruction(word)
            print(f"  EBOOT+0x{off:06X} (PSP 0x{psp:08X}): {decoded}")

    # === Search 5: References to file ID base 406 (0x196) ===
    # The game might add 406 to model number to get file ID
    print("\n=== ADDIU with immediate 406 (0x196) - file ID base for head ===")
    for off in range(0, len(eboot) - 3, 4):
        word = struct.unpack_from('<I', eboot, off)[0]
        opcode = (word >> 26) & 0x3F
        imm = word & 0xFFFF
        if opcode == 0x09 and imm == 0x0196:  # addiu with 406
            psp = EBOOT_LOAD_ADDR + off
            decoded = decode_instruction(word)
            print(f"  EBOOT+0x{off:06X} (PSP 0x{psp:08X}): {decoded}")
            for i in range(-4, 8):
                if 0 <= off + i*4 < len(eboot):
                    w = struct.unpack_from('<I', eboot, off + i*4)[0]
                    ctx_psp = psp + i*4
                    marker = " <<<" if i == 0 else ""
                    print(f"    PSP 0x{ctx_psp:08X}: {decode_instruction(w)}{marker}")

    # Also search for other file ID bases
    for base_name, base_val in [("body=746", 746), ("arm=1086", 1086), ("waist=1419", 1419), ("leg=62", 62)]:
        count = 0
        for off in range(0, len(eboot) - 3, 4):
            word = struct.unpack_from('<I', eboot, off)[0]
            opcode = (word >> 26) & 0x3F
            imm = word & 0xFFFF
            if opcode == 0x09 and imm == (base_val & 0xFFFF):
                count += 1
        print(f"  addiu with {base_name} (0x{base_val:04X}): {count} matches")


if __name__ == '__main__':
    main()

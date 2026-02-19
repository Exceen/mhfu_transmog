#!/opt/homebrew/bin/python3
"""Verify which rendering path is actually active.

Key question: Is the code at 0x088C3114 (rendering chain with equip_id loads)
the same in EBOOT vs save state? If same = original code, if different = FUComplete patched.

Also find function boundaries and callers, and verify our CWCheat patch target.
"""

import struct
import zstandard

EBOOT_PATH = "/Users/Exceen/Downloads/mhfu_transmog/EBOOT.BIN"
EBOOT_LOAD_ADDR = 0x08804000
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
        elif funct == 0x08: return f"jr {R[rs]}"
        elif funct == 0x09: return f"jalr {R[rd]}, {R[rs]}"
        elif funct == 0x21: return f"addu {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x25: return f"or {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x2B: return f"sltu {R[rd]}, {R[rs]}, {R[rt]}"
        else: return f"R-type funct=0x{funct:02X}"
    elif opcode == 0x02: return f"j 0x{(target << 2) | 0x08000000:08X}"
    elif opcode == 0x03: return f"jal 0x{(target << 2) | 0x08000000:08X}"
    elif opcode == 0x04: return f"beq {R[rs]}, {R[rt]}, {simm}"
    elif opcode == 0x05: return f"bne {R[rs]}, {R[rt]}, {simm}"
    elif opcode == 0x09: return f"addiu {R[rt]}, {R[rs]}, {simm}"
    elif opcode == 0x0B: return f"sltiu {R[rt]}, {R[rs]}, {simm}"
    elif opcode == 0x0F: return f"lui {R[rt]}, 0x{imm:04X}"
    elif opcode == 0x21: return f"lh {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x23: return f"lw {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x24: return f"lbu {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x25: return f"lhu {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x29: return f"sh {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x2B: return f"sw {R[rt]}, {simm}({R[rs]})"
    else: return f"op=0x{opcode:02X} rs={R[rs]} rt={R[rt]} imm=0x{imm:04X}"


def main():
    with open(EBOOT_PATH, 'rb') as f:
        eboot = f.read()

    data = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

    # === 1. Compare EBOOT vs save state at 0x088C3000-0x088C3300 ===
    print("=" * 70)
    print("  EBOOT vs Save State comparison at 0x088C3000-0x088C3300")
    print("  (rendering chain with equip_id loads)")
    print("=" * 70)
    same_count = 0
    diff_count = 0
    for psp in range(0x088C3000, 0x088C3300, 4):
        eboot_off = psp - EBOOT_LOAD_ADDR
        state_off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if eboot_off + 3 >= len(eboot) or state_off + 3 >= len(data):
            continue
        ew = struct.unpack_from('<I', eboot, eboot_off)[0]
        sw = struct.unpack_from('<I', data, state_off)[0]
        if ew != sw:
            diff_count += 1
            if diff_count <= 10:  # Show first 10 diffs
                print(f"  DIFF 0x{psp:08X}: EBOOT={ew:08X} STATE={sw:08X}")
        else:
            same_count += 1
    print(f"\n  SAME: {same_count}, DIFFERENT: {diff_count}")
    if diff_count == 0:
        print("  >>> CODE IS IDENTICAL - this is ORIGINAL EBOOT code, NOT FUComplete")
    else:
        print("  >>> CODE IS DIFFERENT - FUComplete has patched this area")

    # === 2. Verify the specific instruction at 0x088C3114 ===
    print("\n" + "=" * 70)
    print("  Verifying instruction at 0x088C3114")
    print("=" * 70)
    for src_name, src_data, base_off in [
            ("EBOOT", eboot, EBOOT_LOAD_ADDR),
            ("STATE", data, PSP_RAM_START - RAM_BASE_IN_STATE)]:
        off = 0x088C3114 - base_off
        if src_name == "STATE":
            off = 0x088C3114 - PSP_RAM_START + RAM_BASE_IN_STATE
        else:
            off = 0x088C3114 - EBOOT_LOAD_ADDR
        word = struct.unpack_from('<I', src_data, off)[0]
        print(f"  {src_name}: 0x{word:08X} = {decode(word)}")

    # === 3. Find function start by searching backwards for addiu $sp, $sp, -N ===
    print("\n" + "=" * 70)
    print("  Finding function containing 0x088C3114")
    print("=" * 70)
    func_start = None
    for psp in range(0x088C3114, 0x088C2800, -4):
        state_off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        word = struct.unpack_from('<I', data, state_off)[0]
        opcode = (word >> 26) & 0x3F
        rt = (word >> 16) & 0x1F
        rs = (word >> 21) & 0x1F
        simm = (word & 0xFFFF)
        if simm >= 0x8000: simm -= 0x10000
        # addiu $sp, $sp, -N (prologue)
        if opcode == 0x09 and rs == 29 and rt == 29 and simm < 0:
            func_start = psp
            print(f"  Function prologue at 0x{psp:08X}: {decode(word)}")
            break
    if func_start is None:
        print("  No function prologue found (searched to 0x088C2800)")
        # Try searching even further back
        for psp in range(0x088C2800, 0x088C2000, -4):
            state_off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
            word = struct.unpack_from('<I', data, state_off)[0]
            opcode = (word >> 26) & 0x3F
            rt = (word >> 16) & 0x1F
            rs = (word >> 21) & 0x1F
            simm = (word & 0xFFFF)
            if simm >= 0x8000: simm -= 0x10000
            if opcode == 0x09 and rs == 29 and rt == 29 and simm < 0:
                func_start = psp
                print(f"  Function prologue at 0x{psp:08X}: {decode(word)} (searched further)")
                break

    if func_start:
        # Search for callers
        print(f"\n  Searching for callers of 0x{func_start:08X}...")
        target_enc = ((func_start >> 2) & 0x3FFFFFF) | (0x03 << 26)
        caller_count = 0
        for psp in range(0x08804000, 0x08A00000, 4):
            s_off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
            if s_off + 3 >= len(data): continue
            word = struct.unpack_from('<I', data, s_off)[0]
            if word == target_enc:
                caller_count += 1
                # Show context
                prev_off = (psp - 4) - PSP_RAM_START + RAM_BASE_IN_STATE
                prev = struct.unpack_from('<I', data, prev_off)[0]
                next_off = (psp + 4) - PSP_RAM_START + RAM_BASE_IN_STATE
                nxt = struct.unpack_from('<I', data, next_off)[0]
                print(f"    Called from 0x{psp:08X}")
                print(f"      0x{psp-4:08X}: {decode(prev)}")
                print(f"      0x{psp:08X}: jal 0x{func_start:08X}")
                print(f"      0x{psp+4:08X}: {decode(nxt)}")
        if caller_count == 0:
            print("    NO CALLERS FOUND (maybe called via function pointer/vtable)")

    # === 4. Compare at 0x08820780-0x08820900 too ===
    print("\n" + "=" * 70)
    print("  EBOOT vs Save State at 0x08820780-0x08820900 (dispatch call area)")
    print("=" * 70)
    same = 0
    diff = 0
    for psp in range(0x08820780, 0x08820900, 4):
        eboot_off = psp - EBOOT_LOAD_ADDR
        state_off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        ew = struct.unpack_from('<I', eboot, eboot_off)[0]
        sw = struct.unpack_from('<I', data, state_off)[0]
        if ew != sw:
            diff += 1
        else:
            same += 1
    print(f"  SAME: {same}, DIFFERENT: {diff}")
    if diff == 0:
        print("  >>> IDENTICAL - original EBOOT code")
    else:
        print("  >>> DIFFERENT - FUComplete patched")

    # === 5. Try to verify CWCheat is actually writing ===
    # The patch address in CWCheat is 0x200C3114
    # PSP address = 0x08800000 + 0x000C3114 = 0x088C3114 ✓
    print("\n" + "=" * 70)
    print("  CWCheat address verification")
    print("=" * 70)
    cwcheat_addr = 0x200C3114
    psp_addr = 0x08800000 + (cwcheat_addr & 0x0FFFFFFF)
    print(f"  CWCheat code: _L 0x{cwcheat_addr:08X} 0x240500FC")
    print(f"  PSP address:  0x{psp_addr:08X}")
    print(f"  Expected: 0x088C3114 {'✓' if psp_addr == 0x088C3114 else '✗'}")

    # === 6. Check the Attack x8 cheat that WORKS for comparison ===
    print("\n" + "=" * 70)
    print("  Comparing with Attack x8 cheat (which WORKS)")
    print("=" * 70)
    # Attack x8: _L 0x200DBBE0 0x00000000 and _L 0x200DBBE8 0x001080C0
    atk_addr1 = 0x08800000 + 0x000DBBE0  # = 0x088DBBE0
    atk_addr2 = 0x08800000 + 0x000DBBE8  # = 0x088DBBE8
    for addr in [atk_addr1, atk_addr2]:
        eboot_off = addr - EBOOT_LOAD_ADDR
        state_off = addr - PSP_RAM_START + RAM_BASE_IN_STATE
        ew = struct.unpack_from('<I', eboot, eboot_off)[0]
        sw = struct.unpack_from('<I', data, state_off)[0]
        print(f"  0x{addr:08X}: EBOOT={ew:08X} STATE={sw:08X} {'SAME' if ew == sw else 'DIFF'}")
        print(f"    EBOOT: {decode(ew)}")
        print(f"    STATE: {decode(sw)}")

    # === 7. Check if the rendering might go through the 0x08820818 path ===
    # That path loads equip_id from $s3+2, not from $s5+58
    # Find function start for 0x08820818
    print("\n" + "=" * 70)
    print("  Finding function containing 0x08820818 (alternative render path)")
    print("=" * 70)
    for psp in range(0x08820818, 0x08820000, -4):
        state_off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        word = struct.unpack_from('<I', data, state_off)[0]
        opcode = (word >> 26) & 0x3F
        rt = (word >> 16) & 0x1F
        rs = (word >> 21) & 0x1F
        simm = (word & 0xFFFF)
        if simm >= 0x8000: simm -= 0x10000
        if opcode == 0x09 and rs == 29 and rt == 29 and simm < 0:
            func_start2 = psp
            print(f"  Function prologue at 0x{psp:08X}: {decode(word)}")
            # Search for callers
            target_enc = ((psp >> 2) & 0x3FFFFFF) | (0x03 << 26)
            for s in range(0x08804000, 0x08A00000, 4):
                s_off = s - PSP_RAM_START + RAM_BASE_IN_STATE
                if s_off + 3 >= len(data): continue
                w = struct.unpack_from('<I', data, s_off)[0]
                if w == target_enc:
                    print(f"    Called from 0x{s:08X}")
            break

    # === 8. Test: patch with 0xFFFF to make helmet invisible ===
    print("\n" + "=" * 70)
    print("  Suggested test patches")
    print("=" * 70)
    print("  To verify code is actually executing:")
    print("  1. Head=0xFFFF (empty): _L 0x200C3114 0x2405FFFF")
    print("     If helmet disappears → code IS active, equip_id matters")
    print("  2. Head=0 (first helm):  _L 0x200C3114 0x24050000")
    print("     If helmet changes → code IS active")
    print("  3. Head=252 (Mafumofu): _L 0x200C3114 0x240500FC")
    print("     This is our target transmog patch")
    print()
    print("  If NONE of these change the visual → code is NOT the active render path")
    print("  In that case, the rendering goes through 0x08820818 (dispatch table lookups)")


if __name__ == '__main__':
    main()

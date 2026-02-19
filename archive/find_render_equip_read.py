#!/opt/homebrew/bin/python3
"""Find ALL code that reads the head equip_id for rendering.

We know:
- Second entity equip_id at 0x09995E7A triggers model reload when changed (V works)
- Entity base: 0x099959A0, second equip copy at +0x4D8, equip_id at +0x4DA
- Rendering chain at 0x088C3114 uses: lhu $a1, 58($s5) - but patching it did nothing
- We need to find the ACTUAL per-frame rendering code path

Search strategy:
1. Find ALL lhu instructions with offset 58 (known head equip_id offset)
2. Find code that references the entity base 0x099959A0
3. Find code that references the lookup table addresses
4. Find code that references offset 0x4DA or 0x4D8 from any base
5. Look in FUComplete high memory (0x09xxxxxx) too
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
        elif funct == 0x08: return f"jr {R[rs]}"
        elif funct == 0x09: return f"jalr {R[rd]}, {R[rs]}"
        elif funct == 0x0A: return f"movz {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x0B: return f"movn {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x18: return f"mult {R[rs]}, {R[rt]}"
        elif funct == 0x19: return f"multu {R[rs]}, {R[rt]}"
        elif funct == 0x21: return f"addu {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x23: return f"subu {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x24: return f"and {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x25: return f"or {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x2A: return f"slt {R[rd]}, {R[rs]}, {R[rt]}"
        elif funct == 0x2B: return f"sltu {R[rd]}, {R[rs]}, {R[rt]}"
        else: return f"special.{funct:02X} {R[rs]},{R[rt]},{R[rd]}"
    elif opcode == 0x02: return f"j 0x{(target << 2) | 0x08000000:08X}"
    elif opcode == 0x03: return f"jal 0x{(target << 2) | 0x08000000:08X}"
    elif opcode == 0x04: return f"beq {R[rs]}, {R[rt]}, {simm}"
    elif opcode == 0x05: return f"bne {R[rs]}, {R[rt]}, {simm}"
    elif opcode == 0x06: return f"blez {R[rs]}, {simm}"
    elif opcode == 0x07: return f"bgtz {R[rs]}, {simm}"
    elif opcode == 0x09: return f"addiu {R[rt]}, {R[rs]}, {simm}"
    elif opcode == 0x0A: return f"slti {R[rt]}, {R[rs]}, {simm}"
    elif opcode == 0x0B: return f"sltiu {R[rt]}, {R[rs]}, {simm}"
    elif opcode == 0x0C: return f"andi {R[rt]}, {R[rs]}, 0x{imm:04X}"
    elif opcode == 0x0D: return f"ori {R[rt]}, {R[rs]}, 0x{imm:04X}"
    elif opcode == 0x0F: return f"lui {R[rt]}, 0x{imm:04X}"
    elif opcode == 0x20: return f"lb {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x21: return f"lh {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x23: return f"lw {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x24: return f"lbu {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x25: return f"lhu {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x28: return f"sb {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x29: return f"sh {R[rt]}, {simm}({R[rs]})"
    elif opcode == 0x2B: return f"sw {R[rt]}, {simm}({R[rs]})"
    else: return f"[{opcode:02X}.{rs:02X}.{rt:02X} 0x{imm:04X}]"


def read_word(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    if off < 0 or off + 3 >= len(data):
        return None
    return struct.unpack_from('<I', data, off)[0]


def show_context(data, psp, before=4, after=4):
    for addr in range(psp - before*4, psp + (after+1)*4, 4):
        w = read_word(data, addr)
        if w is None: continue
        marker = " >>>" if addr == psp else "    "
        print(f"  {marker} 0x{addr:08X}: {w:08X}  {decode(w)}")


def main():
    print("Loading save state...")
    data = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)
    print(f"  Size: {len(data)} bytes")

    # === 1. Find ALL lhu instructions with offset 58 (head equip_id) ===
    print("\n" + "=" * 70)
    print("  1. ALL 'lhu $reg, 58($reg)' instructions in game code")
    print("     (0x08804000 - 0x08A00000 + 0x09900000 - 0x099F0000)")
    print("=" * 70)

    search_ranges = [
        (0x08804000, 0x08A00000, "EBOOT/FUComplete code area"),
        (0x09900000, 0x099F0000, "FUComplete high memory"),
    ]

    lhu58_hits = []
    for start, end, label in search_ranges:
        for psp in range(start, end, 4):
            w = read_word(data, psp)
            if w is None: continue
            # lhu: opcode 0x25 = 100101, offset 58 = 0x003A
            if (w & 0xFC00FFFF) == 0x9400003A:
                lhu58_hits.append(psp)

    print(f"  Found {len(lhu58_hits)} hits:")
    for hit in lhu58_hits:
        w = read_word(data, hit)
        rt = (w >> 16) & 0x1F
        rs = (w >> 21) & 0x1F
        print(f"\n  --- 0x{hit:08X}: lhu {REG_NAMES[rt]}, 58({REG_NAMES[rs]}) ---")
        show_context(data, hit, before=6, after=6)

    # === 2. Find ALL lhu instructions with offset 70 (body equip_id) ===
    # Just count to verify we're finding the right pattern
    print("\n" + "=" * 70)
    print("  2. ALL 'lhu $reg, 70($reg)' (body equip_id) - just count")
    print("=" * 70)
    count = 0
    for start, end, label in search_ranges:
        for psp in range(start, end, 4):
            w = read_word(data, psp)
            if w is None: continue
            if (w & 0xFC00FFFF) == 0x94000046:  # 70 = 0x46
                count += 1
    print(f"  Found {count} hits")

    # === 3. Find code that loads entity base 0x099959A0 ===
    # lui $reg, 0x0999 followed by ori/addiu $reg, 0x59A0
    print("\n" + "=" * 70)
    print("  3. Code that loads entity base 0x099959A0")
    print("     (lui $reg, 0x0999 or 0x099A)")
    print("=" * 70)

    for start, end, label in search_ranges:
        for psp in range(start, end, 4):
            w = read_word(data, psp)
            if w is None: continue
            # lui: opcode 0x0F
            if (w >> 26) == 0x0F:
                imm = w & 0xFFFF
                if imm in (0x0999, 0x099A):
                    rt = (w >> 16) & 0x1F
                    print(f"\n  0x{psp:08X}: lui {REG_NAMES[rt]}, 0x{imm:04X}")
                    # Check next few instructions for ori/addiu with 0x59A0
                    for i in range(1, 6):
                        w2 = read_word(data, psp + i*4)
                        if w2 is None: continue
                        d = decode(w2)
                        if "59A0" in f"{w2:08X}" or "59A0" in d.lower() or "5E78" in d.lower() or "5E7A" in d.lower():
                            print(f"  0x{psp+i*4:08X}: {w2:08X}  {d}  <<< MATCH")
                        else:
                            print(f"  0x{psp+i*4:08X}: {w2:08X}  {d}")

    # === 4. Find code that references lookup table addresses ===
    # Table B base: 0x08997BA8 → lui 0x0899/0x089A + ori/addiu 0x7BA8
    print("\n" + "=" * 70)
    print("  4. Code referencing lookup Table B (0x08997BA8)")
    print("=" * 70)

    # Search for lui 0x089A (since 0x7BA8 as signed = 0x7BA8, positive, so lui 0x0899 + ori 0x7BA8)
    # Or lui 0x0899 + addiu 0x7BA8
    for start, end, label in search_ranges:
        for psp in range(start, end, 4):
            w = read_word(data, psp)
            if w is None: continue
            if (w >> 26) == 0x0F:  # lui
                imm = w & 0xFFFF
                if imm == 0x0899 or imm == 0x089A:
                    # Check next instructions for table offsets
                    for i in range(1, 8):
                        w2 = read_word(data, psp + i*4)
                        if w2 is None: continue
                        imm2 = w2 & 0xFFFF
                        # Table B: 0x7BA8, Table A: 0x72AC
                        if imm2 in (0x7BA8, 0x72AC, 0x7E6C, 0x81D4, 0x851C):
                            table_names = {0x72AC: "A", 0x7BA8: "B", 0x7E6C: "C", 0x81D4: "D", 0x851C: "E"}
                            tname = table_names.get(imm2, "?")
                            print(f"\n  lui at 0x{psp:08X}: lui ..., 0x{imm:04X}")
                            print(f"  ref at 0x{psp+i*4:08X}: {w2:08X}  {decode(w2)}  <<< Table {tname}")
                            show_context(data, psp, before=2, after=10)
                            break

    # === 5. Find code referencing dispatch pointer table 0x089C7510 ===
    print("\n" + "=" * 70)
    print("  5. Code referencing dispatch table (0x089C7510)")
    print("=" * 70)

    for start, end, label in search_ranges:
        for psp in range(start, end, 4):
            w = read_word(data, psp)
            if w is None: continue
            if (w >> 26) == 0x0F:  # lui
                imm = w & 0xFFFF
                if imm == 0x089D or imm == 0x089C:
                    for i in range(1, 8):
                        w2 = read_word(data, psp + i*4)
                        if w2 is None: continue
                        imm2 = w2 & 0xFFFF
                        if imm2 == 0x7510 or imm2 == 0x7508:
                            ref_name = "dispatch_table" if imm2 == 0x7510 else "base_ptr"
                            print(f"\n  lui at 0x{psp:08X}: lui ..., 0x{imm:04X}")
                            print(f"  ref at 0x{psp+i*4:08X}: {decode(w2)}  <<< {ref_name}")
                            show_context(data, psp, before=2, after=12)
                            break

    # === 6. Search FUComplete high memory for equip_id related code ===
    # Look for lhu with small offsets (2, 14, 26, 38, 50, 58, 70, 82, 94)
    # that could be equip structure reads
    print("\n" + "=" * 70)
    print("  6. FUComplete high memory: lhu with equip offsets (58,70,82,94)")
    print("     Search range: 0x09900000 - 0x099F0000")
    print("=" * 70)

    equip_offsets = [58, 70, 82, 94]  # head, body, waist, legs
    for psp in range(0x09900000, 0x099F0000, 4):
        w = read_word(data, psp)
        if w is None: continue
        opcode = (w >> 26) & 0x3F
        if opcode == 0x25:  # lhu
            imm = w & 0xFFFF
            simm = imm if imm < 0x8000 else imm - 0x10000
            if simm in equip_offsets:
                rt = (w >> 16) & 0x1F
                rs = (w >> 21) & 0x1F
                print(f"\n  0x{psp:08X}: lhu {REG_NAMES[rt]}, {simm}({REG_NAMES[rs]})  [offset={simm}]")
                show_context(data, psp, before=6, after=6)

    # === 7. Find who WRITES to the second entity equip_id ===
    # sh $reg, 0x4DA($base) or sh $reg, 2($ptr_to_second_copy)
    # sh: opcode 0x29
    print("\n" + "=" * 70)
    print("  7. Instructions that WRITE to equip_id offset 58 (sh $reg, 58($reg))")
    print("=" * 70)

    for start, end, label in search_ranges:
        for psp in range(start, end, 4):
            w = read_word(data, psp)
            if w is None: continue
            # sh: opcode 0x29, offset 58
            if (w & 0xFC00FFFF) == 0xA400003A:
                rt = (w >> 16) & 0x1F
                rs = (w >> 21) & 0x1F
                print(f"\n  0x{psp:08X}: sh {REG_NAMES[rt]}, 58({REG_NAMES[rs]})")
                show_context(data, psp, before=6, after=6)

    # === 8. Find the equip change detection code ===
    # The game detects equip_id changes by comparing old vs new values
    # Look for code near the second entity that does comparison
    # Search for lhu from offset 0x4DA or 0x4D8 (second entity equip copy)
    print("\n" + "=" * 70)
    print("  8. Code reading from entity offsets 0x4D8-0x4E4 (second equip copy)")
    print("     (lhu/lh/lw/lbu with offsets 1240-1252)")
    print("=" * 70)

    for start, end, label in search_ranges:
        for psp in range(start, end, 4):
            w = read_word(data, psp)
            if w is None: continue
            opcode = (w >> 26) & 0x3F
            if opcode in (0x20, 0x21, 0x23, 0x24, 0x25):  # lb, lh, lw, lbu, lhu
                imm = w & 0xFFFF
                simm = imm if imm < 0x8000 else imm - 0x10000
                if 0x4D8 <= simm <= 0x4E4:
                    rt = (w >> 16) & 0x1F
                    rs = (w >> 21) & 0x1F
                    load_type = {0x20:"lb", 0x21:"lh", 0x23:"lw", 0x24:"lbu", 0x25:"lhu"}[opcode]
                    print(f"\n  0x{psp:08X}: {load_type} {REG_NAMES[rt]}, {simm}({REG_NAMES[rs]})  [{label}]")
                    show_context(data, psp, before=4, after=4)


if __name__ == '__main__':
    main()

#!/opt/homebrew/bin/python3
"""Dump VT1/VT2 stat table entries for Rath Soul (102) and Mafumofu (252).
Also search FUComplete code area for equip_id reads."""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

VT1_BASE = 0x08960754
VT2_BASE = 0x08964B74
VT_ENTRY_SIZE = 40


def load_state(slot):
    return zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_{slot}.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)


def read_u16(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<H', data, off)[0]


def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


def read_bytes(data, psp, count):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return data[off:off+count]


def main():
    data1 = load_state(0)  # Rath Soul
    data2 = load_state(1)  # Mafumofu

    # === 1. Dump VT1 entries ===
    for eid, name in [(102, "Rath Soul"), (252, "Mafumofu")]:
        vt1_addr = VT1_BASE + eid * VT_ENTRY_SIZE
        vt2_addr = VT2_BASE + eid * VT_ENTRY_SIZE
        print(f"\n{'='*60}")
        print(f"  VT1[{eid}] ({name}) at 0x{vt1_addr:08X}")
        print(f"{'='*60}")
        for i in range(0, VT_ENTRY_SIZE, 2):
            addr = vt1_addr + i
            v1 = read_u16(data1, addr)
            v2 = read_u16(data2, addr)
            diff = "***" if v1 != v2 else ""
            print(f"  +{i:2d} (0x{addr:08X}): {v1:>6} (0x{v1:04X})  Slot2: {v2:>6} {diff}")

        print(f"\n  VT2[{eid}] ({name}) at 0x{vt2_addr:08X}")
        for i in range(0, VT_ENTRY_SIZE, 2):
            addr = vt2_addr + i
            v1 = read_u16(data1, addr)
            v2 = read_u16(data2, addr)
            diff = "***" if v1 != v2 else ""
            print(f"  +{i:2d} (0x{addr:08X}): {v1:>6} (0x{v1:04X})  Slot2: {v2:>6} {diff}")

    # === 2. Generate CWCheat lines ===
    # For VT1[252] and VT2[252], write Rath Soul (102) values
    print(f"\n{'='*60}")
    print(f"  CWCheat: Overwrite VT1/VT2[252] with Rath Soul stats")
    print(f"{'='*60}")
    # VT1[252]
    vt1_src = VT1_BASE + 102 * VT_ENTRY_SIZE  # Rath Soul VT1
    vt1_dst = VT1_BASE + 252 * VT_ENTRY_SIZE  # Mafumofu VT1 (overwrite target)
    print(f"  ; VT1[252] <- VT1[102] (0x{vt1_dst:08X} <- 0x{vt1_src:08X})")
    for i in range(0, VT_ENTRY_SIZE, 4):
        src_val = read_u32(data1, vt1_src + i)
        dst_offset = (vt1_dst + i) - 0x08800000
        print(f"  _L 0x2{dst_offset:07X} 0x{src_val:08X}")

    # VT2[252]
    vt2_src = VT2_BASE + 102 * VT_ENTRY_SIZE
    vt2_dst = VT2_BASE + 252 * VT_ENTRY_SIZE
    print(f"  ; VT2[252] <- VT2[102] (0x{vt2_dst:08X} <- 0x{vt2_src:08X})")
    for i in range(0, VT_ENTRY_SIZE, 4):
        src_val = read_u32(data1, vt2_src + i)
        dst_offset = (vt2_dst + i) - 0x08800000
        print(f"  _L 0x2{dst_offset:07X} 0x{src_val:08X}")

    # === 3. Also check entity+0x044C4 ===
    # This value changed from 55 to 25 between Rath Soul and Mafumofu
    print(f"\n{'='*60}")
    print(f"  entity+0x044C4 defense? restore line")
    print(f"{'='*60}")
    addr = 0x09999E64
    offset = addr - 0x08800000
    v1 = read_u16(data1, addr)
    print(f"  ; entity+0x044C4 = {v1} (Rath Soul value)")
    print(f"  _L 0x1{offset:07X} 0x0000{v1:04X}")

    # === 4. Search FUComplete code area for equip_id reads ===
    print(f"\n{'='*60}")
    print(f"  Search: lhu with offset 2 in FUComplete code (0x0891C000-0x0892E000)")
    print(f"{'='*60}")
    import sys
    sys.path.insert(0, '/Users/Exceen/Downloads/mhfu_transmog')
    from disasm_equip_code import disasm

    count = 0
    for psp in range(0x0891C000, 0x0892E000, 4):
        instr = read_u32(data1, psp)
        op = (instr >> 26) & 0x3F
        imm = instr & 0xFFFF
        if op == 0x25 and imm == 0x0002:  # lhu rt, 2(rs)
            count += 1
            if count <= 20:
                print(f"  0x{psp:08X}: {disasm(instr, psp)}")
                # Show context
                for d in range(-4, 6):
                    a = psp + d * 4
                    i = read_u32(data1, a)
                    arrow = " <<<" if d == 0 else ""
                    print(f"    0x{a:08X}: [{i:08X}] {disasm(i, a)}{arrow}")
    print(f"  Total lhu *, 2(*) in FUComplete area: {count}")

    # Also search for lhu with offset 0x4DA
    print(f"\n  Search: lhu with offset 0x4DA in FUComplete code:")
    for psp in range(0x0891C000, 0x0892E000, 4):
        instr = read_u32(data1, psp)
        op = (instr >> 26) & 0x3F
        imm = instr & 0xFFFF
        if op == 0x25 and imm == 0x04DA:  # lhu rt, 0x4DA(rs)
            print(f"  0x{psp:08X}: {disasm(instr, psp)}")

    # Search for addiu with 0x4D8 in FUComplete code
    print(f"\n  Search: addiu with 0x4D8 in FUComplete code:")
    for psp in range(0x0891C000, 0x0892E000, 4):
        instr = read_u32(data1, psp)
        op = (instr >> 26) & 0x3F
        if op == 0x09:  # addiu
            imm = instr & 0xFFFF
            imm_s = imm - 0x10000 if imm >= 0x8000 else imm
            if imm_s == 0x4D8:
                print(f"  0x{psp:08X}: {disasm(instr, psp)}")


if __name__ == '__main__':
    main()

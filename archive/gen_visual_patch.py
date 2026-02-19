#!/opt/homebrew/bin/python3
"""Generate CWCheat codes for visual table entry swap and table subset tests.

Approach 1: Overwrite visual table entry[102] with entry[252] data
Approach 2: Test subsets of FUComplete lookup tables to find visual-only tables
Approach 3: Fix conditional two-phase with correct E-type format (z=1 for equal)
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
CW_BASE = 0x08800000

def read_bytes(data, psp, n):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return data[off:off+n]

def read_u16(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<H', data, off)[0]

def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]

def cw_addr(psp):
    """Convert PSP address to CWCheat offset."""
    return psp - CW_BASE

def cw_write32(psp, value):
    off = cw_addr(psp)
    return f"_L 0x2{off:07X} 0x{value:08X}"

def cw_write16(psp, value):
    off = cw_addr(psp)
    return f"_L 0x1{off:07X} 0x{value:08X}"


def main():
    print("Loading save state (Rath Soul)...")
    data = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

    # === 1. Visual Table entry swap ===
    VTABLE1 = 0x08960754
    VTABLE2 = 0x08964B74

    print("\n" + "=" * 70)
    print("  Visual Table 1 entries (40 bytes each)")
    print("=" * 70)

    for eid in [102, 252]:
        addr = VTABLE1 + eid * 40
        raw = read_bytes(data, addr, 40)
        print(f"\n  Entry [{eid}] at 0x{addr:08X}:")
        print(f"    Hex: {raw.hex()}")
        u32s = struct.unpack_from('<10I', raw)
        print(f"    As u32[10]: {[f'0x{v:08X}' for v in u32s]}")

    print("\n  CWCheat codes to overwrite VTable1[102] with VTable1[252]:")
    src = VTABLE1 + 252 * 40
    dst = VTABLE1 + 102 * 40
    codes_vtable1 = []
    for i in range(0, 40, 4):
        val = read_u32(data, src + i)
        codes_vtable1.append(cw_write32(dst + i, val))
        print(f"    {codes_vtable1[-1]}  # VT1[102]+{i}: 0x{read_u32(data, dst+i):08X} -> 0x{val:08X}")

    print("\n" + "=" * 70)
    print("  Visual Table 2 entries (40 bytes each)")
    print("=" * 70)

    for eid in [102, 252]:
        addr = VTABLE2 + eid * 40
        raw = read_bytes(data, addr, 40)
        print(f"\n  Entry [{eid}] at 0x{addr:08X}:")
        print(f"    Hex: {raw.hex()}")

    print("\n  CWCheat codes to overwrite VTable2[102] with VTable2[252]:")
    src2 = VTABLE2 + 252 * 40
    dst2 = VTABLE2 + 102 * 40
    codes_vtable2 = []
    for i in range(0, 40, 4):
        val = read_u32(data, src2 + i)
        codes_vtable2.append(cw_write32(dst2 + i, val))
        print(f"    {codes_vtable2[-1]}  # VT2[102]+{i}: 0x{read_u32(data, dst2+i):08X} -> 0x{val:08X}")

    # === 2. Table subset analysis ===
    print("\n" + "=" * 70)
    print("  FUComplete lookup table subsets for equip_id 102")
    print("=" * 70)

    tables = [
        ("A", 0x089972AC, "dispatch slot 4 - file group"),
        ("B", 0x08997BA8, "dispatch slot 6 - model index"),
        ("C", 0x08997E6C, "dispatch slot 8 - identity?"),
        ("D", 0x089981D4, "dispatch slot 10 - stats?"),
        ("E", 0x0899851C, "dispatch slot 12 - texture?"),
    ]

    for name, base, desc in tables:
        addr102 = base + 102 * 2
        addr252 = base + 252 * 2
        v102 = read_u16(data, addr102)
        v252 = read_u16(data, addr252)
        print(f"  Table {name} ({desc}):")
        print(f"    [{name}][102] = {v102} at 0x{addr102:08X}")
        print(f"    [{name}][252] = {v252} at 0x{addr252:08X}")
        print(f"    CWCheat: {cw_write16(addr102, v252)}")

    # === 3. Generate all patches ===
    print("\n" + "=" * 70)
    print("  GENERATED PATCHES")
    print("=" * 70)

    # Patch AE: Visual tables 1+2 swap (no FUComplete table changes)
    print("\n_C0 PATCH AE: Visual tables swap (VT1[102]=VT1[252], VT2[102]=VT2[252])")
    for code in codes_vtable1:
        print(code)
    for code in codes_vtable2:
        print(code)

    # Table redirect lines for individual tables
    table_codes = {}
    for name, base, desc in tables:
        addr102 = base + 102 * 2
        v252 = read_u16(data, base + 252 * 2)
        table_codes[name] = cw_write16(addr102, v252)

    # Patch AF: Tables A+B+E only (suspected model-only)
    print(f"\n_C0 PATCH AF: Tables A+B+E only (model/visual guess)")
    print(table_codes["A"])
    print(table_codes["B"])
    print(table_codes["E"])

    # Patch AG: Tables C+D only (suspected stats-only)
    print(f"\n_C0 PATCH AG: Tables C+D only (stats guess)")
    print(table_codes["C"])
    print(table_codes["D"])

    # Patch AH: Table A only
    print(f"\n_C0 PATCH AH: Table A only (file group)")
    print(table_codes["A"])

    # Patch AI: Two-phase conditional with FIXED format (z=1 for equal)
    print(f"\n_C0 PATCH AI: Two-phase conditional (FIXED equal check z=1)")
    for code in [table_codes[n] for n in "ABCDE"]:
        print(code)
    print("_L 0xE10101F7 0x1031CDA6")  # z=1 (equal), if cache=Rath Soul
    print("_L 0x11195E7A 0x000000FC")  # write 252 to entity
    print("_L 0xE1010080 0x1031CDA6")  # z=1 (equal), if cache=Mafumofu
    print("_L 0x11195E7A 0x00000066")  # write 102 to entity

    # Patch AJ: Visual tables + trigger (change entity equip_id to force reload)
    print(f"\n_C0 PATCH AJ: Visual tables + second entity equip_id->252 (trigger)")
    for code in codes_vtable1:
        print(code)
    for code in codes_vtable2:
        print(code)
    print("_L 0x11195E7A 0x000000FC")  # force equip_id 252 to trigger reload

    # Check if visual table entries differ between equip 102 and 252
    print("\n" + "=" * 70)
    print("  Visual table entry comparison")
    print("=" * 70)
    for tbl_name, tbl_addr in [("VTable1", VTABLE1), ("VTable2", VTABLE2)]:
        e102 = read_bytes(data, tbl_addr + 102*40, 40)
        e252 = read_bytes(data, tbl_addr + 252*40, 40)
        if e102 == e252:
            print(f"  {tbl_name}[102] == {tbl_name}[252] (identical!)")
        else:
            print(f"  {tbl_name}[102] != {tbl_name}[252] (different)")
            for i in range(0, 40, 2):
                v1 = struct.unpack_from('<H', e102, i)[0]
                v2 = struct.unpack_from('<H', e252, i)[0]
                if v1 != v2:
                    print(f"    +{i:2d}: 0x{v1:04X} -> 0x{v2:04X}")


if __name__ == '__main__':
    main()

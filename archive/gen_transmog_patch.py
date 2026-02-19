#!/opt/homebrew/bin/python3
"""Generate the transmog CWCheat patch.

Strategy: Force equip_id 252 (Mafumofu visual) + overwrite stat tables[252]
with Rath Soul data (Rath Soul stats).

The stat tables at 0x08960754 (VT1) and 0x08964B74 (VT2) have 40-byte entries
indexed by equip_id. Overwriting entry[252] with entry[102] data gives
Rath Soul stats when the game looks up equip_id 252.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
CW_BASE = 0x08800000

def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


def main():
    print("Loading save state (Rath Soul)...")
    data = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

    VTABLE1 = 0x08960754
    VTABLE2 = 0x08964B74

    # Source: Rath Soul entry (equip_id 102) — we want THESE stats
    src1_addr = VTABLE1 + 102 * 40  # 0x08961744
    src2_addr = VTABLE2 + 102 * 40  # 0x08965B64

    # Destination: Mafumofu entry (equip_id 252) — overwrite with Rath Soul data
    dst1_addr = VTABLE1 + 252 * 40  # 0x08962EB4
    dst2_addr = VTABLE2 + 252 * 40  # 0x089672D4

    print(f"\n  Stat Table 1 (VT1):")
    print(f"    Rath Soul [102] at 0x{src1_addr:08X}")
    print(f"    Mafumofu  [252] at 0x{dst1_addr:08X}")
    print(f"\n  Stat Table 2 (VT2):")
    print(f"    Rath Soul [102] at 0x{src2_addr:08X}")
    print(f"    Mafumofu  [252] at 0x{dst2_addr:08X}")

    # Generate CWCheat codes
    print("\n" + "=" * 70)
    print("  PATCH AK: Equip_id->252 + stat override (NO FUComplete tables)")
    print("=" * 70)
    print("_C1 PATCH AK: Transmog Rath Soul->Mafumofu (equip+stats)")
    print("_L 0x11195E7A 0x000000FC")
    print("# Stat table 1: overwrite entry[252] with Rath Soul data")
    for i in range(0, 40, 4):
        val = read_u32(data, src1_addr + i)
        off = (dst1_addr + i) - CW_BASE
        print(f"_L 0x2{off:07X} 0x{val:08X}")
    print("# Stat table 2: overwrite entry[252] with Rath Soul data")
    for i in range(0, 40, 4):
        val = read_u32(data, src2_addr + i)
        off = (dst2_addr + i) - CW_BASE
        print(f"_L 0x2{off:07X} 0x{val:08X}")

    print("\n" + "=" * 70)
    print("  PATCH AL: Full transmog (equip+stats+FUComplete tables)")
    print("=" * 70)
    print("_C0 PATCH AL: Transmog full (equip+stats+tables)")
    print("_L 0x11195E7A 0x000000FC")
    print("# FUComplete lookup tables[102] -> Mafumofu values")
    print("_L 0x10197378 0x000000BD")
    print("_L 0x10197C74 0x00000064")
    print("_L 0x10197F38 0x000000FC")
    print("_L 0x101982A0 0x00000032")
    print("_L 0x101985E8 0x00000022")
    print("# Stat table 1: overwrite entry[252] with Rath Soul data")
    for i in range(0, 40, 4):
        val = read_u32(data, src1_addr + i)
        off = (dst1_addr + i) - CW_BASE
        print(f"_L 0x2{off:07X} 0x{val:08X}")
    print("# Stat table 2: overwrite entry[252] with Rath Soul data")
    for i in range(0, 40, 4):
        val = read_u32(data, src2_addr + i)
        off = (dst2_addr + i) - CW_BASE
        print(f"_L 0x2{off:07X} 0x{val:08X}")

    # Verify the addresses
    print("\n" + "=" * 70)
    print("  Address verification")
    print("=" * 70)
    print(f"  Second entity equip_id: 0x09995E7A -> CW offset 0x{0x09995E7A - CW_BASE:07X}")
    print(f"  VT1[252] start: 0x{dst1_addr:08X} -> CW offset 0x{dst1_addr - CW_BASE:07X}")
    print(f"  VT2[252] start: 0x{dst2_addr:08X} -> CW offset 0x{dst2_addr - CW_BASE:07X}")

    # Show what we're overwriting
    print("\n  VT1[252] original (Mafumofu) -> overwrite with (Rath Soul):")
    for i in range(0, 40, 4):
        orig = read_u32(data, dst1_addr + i)
        repl = read_u32(data, src1_addr + i)
        diff = " <<<" if orig != repl else ""
        print(f"    +{i:2d}: 0x{orig:08X} -> 0x{repl:08X}{diff}")

    print("\n  VT2[252] original (Mafumofu) -> overwrite with (Rath Soul):")
    for i in range(0, 40, 4):
        orig = read_u32(data, dst2_addr + i)
        repl = read_u32(data, src2_addr + i)
        diff = " <<<" if orig != repl else ""
        print(f"    +{i:2d}: 0x{orig:08X} -> 0x{repl:08X}{diff}")


if __name__ == '__main__':
    main()

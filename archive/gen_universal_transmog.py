#!/opt/homebrew/bin/python3
"""Generate universal transmog CWCheat patch.

For ANY equipped head armor, shows the target visual while keeping the original
armor's stats. Uses CWCheat type 5 (copy bytes) to dynamically copy stat table
entries at runtime.

Structure per armor:
  _L 0xE105XXXX 0x0AAAAAAA   # if first_entity_copy head equip_id == X (EQUAL)
  _L 0x1BBBBBBB 0x000000FC   # force second entity copy equip_id → target
  _L 0x5SSSSSSS 0x00000028   # copy 40 bytes: VT1[X] → VT1[target]
  _L 0x0DDDDDDD 0x00000000
  _L 0x5SSSSSSS 0x00000028   # copy 40 bytes: VT2[X] → VT2[target]
  _L 0x0DDDDDDD 0x00000000
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48
CW_BASE = 0x08800000

VTABLE1 = 0x08960754
VTABLE2 = 0x08964B74

# Target visual: Mafumofu Hood (equip_id 252)
TARGET_EQUIP_ID = 252

# Entity addresses
ENTITY_BASE = 0x099959A0
FIRST_COPY_HEAD_EQUIP = ENTITY_BASE + 0x7A   # 0x09995A1A
SECOND_COPY_HEAD_EQUIP = ENTITY_BASE + 0x4DA  # 0x09995E7A


def read_bytes(data, psp, n):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return data[off:off+n]


def cw_off(psp):
    return psp - CW_BASE


def main():
    print("Loading save state...")
    data = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

    # Find all valid equip_ids by checking for non-zero VT1 entries
    zero_entry = b'\x00' * 40
    valid_ids = []
    for eid in range(400):
        entry = read_bytes(data, VTABLE1 + eid * 40, 40)
        if entry != zero_entry and eid != TARGET_EQUIP_ID:
            valid_ids.append(eid)

    print(f"Found {len(valid_ids)} valid head armor equip_ids (excluding target {TARGET_EQUIP_ID})")
    print(f"Range: {min(valid_ids)} to {max(valid_ids)}")

    # Destination addresses
    dst_vt1 = VTABLE1 + TARGET_EQUIP_ID * 40
    dst_vt2 = VTABLE2 + TARGET_EQUIP_ID * 40

    # Generate CWCheat codes
    lines = []
    lines.append(f"_C1 Universal Head Transmog -> Mafumofu")

    for eid in valid_ids:
        src_vt1 = VTABLE1 + eid * 40
        src_vt2 = VTABLE2 + eid * 40

        # Conditional: if first entity copy equip_id == eid, apply next 5 lines
        lines.append(f"_L 0xE105{eid:04X} 0x0{cw_off(FIRST_COPY_HEAD_EQUIP):07X}")
        # Force second entity copy → target visual
        lines.append(f"_L 0x1{cw_off(SECOND_COPY_HEAD_EQUIP):07X} 0x{TARGET_EQUIP_ID:08X}")
        # Copy VT1[eid] → VT1[target] (40 bytes)
        lines.append(f"_L 0x5{cw_off(src_vt1):07X} 0x00000028")
        lines.append(f"_L 0x0{cw_off(dst_vt1):07X} 0x00000000")
        # Copy VT2[eid] → VT2[target] (40 bytes)
        lines.append(f"_L 0x5{cw_off(src_vt2):07X} 0x00000028")
        lines.append(f"_L 0x0{cw_off(dst_vt2):07X} 0x00000000")

    total_l_lines = len(valid_ids) * 6
    print(f"Generated {total_l_lines} _L lines for {len(valid_ids)} armors")
    print(f"(6 lines per armor: 1 conditional + 1 equip_id + 4 copy)")

    # Output
    output = "\n".join(lines)
    print("\n" + "=" * 70)
    print(output)

    # Also write to a file for easy copy
    with open("/Users/Exceen/Downloads/mhfu_transmog/universal_transmog.txt", "w") as f:
        f.write(output + "\n")
    print(f"\nSaved to universal_transmog.txt")


if __name__ == '__main__':
    main()

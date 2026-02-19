#!/opt/homebrew/bin/python3
"""Dump all u16 values in the FUComplete rendering data area.

The 297 FUComplete lookup callers load equip_ids from addresses in the
0x089A98xx range. This script dumps those values to find which one
contains 102 (Rath Soul head equip_id) for the rendering path.

It also dumps values from both save states (slot 1 = Rath Soul, slot 2 = Mafumofu)
to help identify which addresses change with equipment.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48


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


def main():
    print("Loading save states...")
    data1 = load_state(0)  # Slot 1: Rath Soul equipped
    data2 = load_state(1)  # Slot 2: Mafumofu equipped

    # Known equip_ids
    # Rath Soul head = 102
    # Mafumofu Hood = 252

    # First, verify the entity copies
    print("\n=== Entity copy verification ===")
    print(f"  Slot 1 copy 1 head: {read_u16(data1, 0x09995A1A)}")
    print(f"  Slot 1 copy 2 head: {read_u16(data1, 0x09995E7A)}")
    print(f"  Slot 2 copy 1 head: {read_u16(data2, 0x09995A1A)}")
    print(f"  Slot 2 copy 2 head: {read_u16(data2, 0x09995E7A)}")

    # Dump the FUComplete rendering data area
    # The callers load from addresses like 0x089A9834, 0x089A9838, etc.
    # Let's dump a wide range: 0x089A9800 - 0x089A9A00
    print("\n=== FUComplete rendering data area (0x089A9800 - 0x089A9A00) ===")
    print(f"  {'Address':>12}  {'Slot1 u16':>10}  {'Slot2 u16':>10}  {'Diff':>5}  Note")
    print(f"  {'-'*12}  {'-'*10}  {'-'*10}  {'-'*5}  ----")

    interesting = []
    for addr in range(0x089A9800, 0x089A9A00, 2):
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        diff = "***" if v1 != v2 else ""
        note = ""
        if v1 == 102:
            note += " [Slot1=Rath Soul head!]"
        if v2 == 252:
            note += " [Slot2=Mafumofu!]"
        if v1 == 252:
            note += " [Slot1=Mafumofu!]"
        if v2 == 102:
            note += " [Slot2=Rath Soul!]"
        if diff or note:
            interesting.append((addr, v1, v2, diff, note))
        print(f"  0x{addr:08X}  {v1:>10}  {v2:>10}  {diff:>5}  {note}")

    print(f"\n=== Addresses with differences or known equip_ids ===")
    for addr, v1, v2, diff, note in interesting:
        print(f"  0x{addr:08X}: Slot1={v1} (0x{v1:04X}), Slot2={v2} (0x{v2:04X})  {diff} {note}")

    # Also search for value 102 anywhere in the 0x089A0000-0x089B0000 range
    print(f"\n=== Searching for value 102 (Rath Soul head) in 0x089A0000-0x089B0000 ===")
    count = 0
    for addr in range(0x089A0000, 0x089B0000, 2):
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        if v1 == 102 and v2 != 102:
            count += 1
            note = ""
            if v2 == 252:
                note = " <<< MATCH: Slot1=102(Rath), Slot2=252(Mafu)!"
            print(f"  0x{addr:08X}: Slot1={v1}, Slot2={v2}{note}")
    print(f"  Total addresses with Slot1=102, Slot2!=102: {count}")

    # Also search for 102 in slot 1 where slot 2 has 252
    print(f"\n=== EXACT MATCH: Slot1=102 AND Slot2=252 in 0x089A0000-0x089B0000 ===")
    for addr in range(0x089A0000, 0x089B0000, 2):
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        if v1 == 102 and v2 == 252:
            print(f"  *** 0x{addr:08X}: Slot1=102 (Rath Soul), Slot2=252 (Mafumofu) ***")

    # Wider search - maybe the rendering data is elsewhere
    print(f"\n=== WIDER: Slot1=102 AND Slot2=252 in 0x08800000-0x09FFFFFF ===")
    max_addr = min(0x0A000000, PSP_RAM_START + len(data1) - RAM_BASE_IN_STATE - 1)
    for addr in range(0x08800000, max_addr, 2):
        v1 = read_u16(data1, addr)
        v2 = read_u16(data2, addr)
        if v1 == 102 and v2 == 252:
            print(f"  *** 0x{addr:08X} ***")


if __name__ == '__main__':
    main()

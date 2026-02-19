#!/opt/homebrew/bin/python3
"""Diff two save states to find all memory addresses that differ.
Slot 1 should have Rath Soul head, Slot 2 should have Mafumofu head.
This will find rendering data, model pointers, and everything else that
changes when head equipment changes.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

ENTITY_BASE = 0x099959A0


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
    data1 = load_state(0)  # Slot 1: Rath Soul head
    data2 = load_state(1)  # Slot 2: Mafumofu head

    # Verify the states have different equipment
    c1_h1 = read_u16(data1, 0x09995A1A)
    c1_h2 = read_u16(data2, 0x09995A1A)
    c2_h1 = read_u16(data1, 0x09995E7A)
    c2_h2 = read_u16(data2, 0x09995E7A)
    print(f"  Slot 1: copy1 head={c1_h1}, copy2 head={c2_h1}")
    print(f"  Slot 2: copy1 head={c1_h2}, copy2 head={c2_h2}")

    if c2_h1 == c2_h2:
        print("\n  WARNING: Both save states have the same head equip_id!")
        print("  Please create two save states:")
        print("    Slot 1: Rath Soul head equipped")
        print("    Slot 2: Mafumofu head equipped")
        print("  Make sure ALL cheats are disabled when creating the states.")
        # Still run the diff to show what's different
        print("\n  Running diff anyway...\n")

    min_len = min(len(data1), len(data2))
    max_psp = PSP_RAM_START + min_len - RAM_BASE_IN_STATE

    # Define memory regions of interest
    regions = [
        ("EBOOT Code", 0x08804000, 0x08960000),
        ("FUComplete Tables", 0x08960000, 0x089C0000),
        ("FUComplete Data", 0x089C0000, 0x08A00000),
        ("General RAM", 0x08A00000, 0x09000000),
        ("Entity Area", 0x09990000, 0x09A00000),
        ("Extended Entity", 0x09A00000, 0x0A000000),
    ]

    for region_name, start, end in regions:
        if start >= max_psp:
            continue
        end = min(end, max_psp)

        diffs = []
        addr = start
        while addr < end:
            off1 = addr - PSP_RAM_START + RAM_BASE_IN_STATE
            off2 = addr - PSP_RAM_START + RAM_BASE_IN_STATE
            if off1 + 2 <= len(data1) and off2 + 2 <= len(data2):
                v1 = struct.unpack_from('<H', data1, off1)[0]
                v2 = struct.unpack_from('<H', data2, off2)[0]
                if v1 != v2:
                    note = ""
                    if v1 == 102 and v2 == 252:
                        note = " <<< EXACT: Rath->Mafu equip_id!"
                    elif v1 == 102:
                        note = f" (Slot1=RathSoul eid)"
                    elif v2 == 252:
                        note = f" (Slot2=Mafumofu eid)"
                    # Check if this is inside entity structure
                    if ENTITY_BASE <= addr < ENTITY_BASE + 0x80000:
                        entity_off = addr - ENTITY_BASE
                        note += f" [entity+0x{entity_off:05X}]"
                    diffs.append((addr, v1, v2, note))
            addr += 2

        if diffs:
            print(f"\n{'='*80}")
            print(f"  {region_name}: {len(diffs)} differences ({start:#010x}-{end:#010x})")
            print(f"{'='*80}")
            # Show first 100 differences
            shown = 0
            for addr, v1, v2, note in diffs:
                if shown < 200 or note:
                    print(f"  0x{addr:08X}: {v1:>6} (0x{v1:04X}) -> {v2:>6} (0x{v2:04X}){note}")
                    shown += 1
            if len(diffs) > shown:
                print(f"  ... and {len(diffs) - shown} more differences")

    # Summary
    print(f"\n{'='*80}")
    print(f"  SUMMARY: Addresses where Slot1=102 AND Slot2=252")
    print(f"{'='*80}")
    addr = 0x08800000
    while addr < max_psp:
        off = addr - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 2 <= min_len:
            v1 = struct.unpack_from('<H', data1, off)[0]
            v2 = struct.unpack_from('<H', data2, off)[0]
            if v1 == 102 and v2 == 252:
                entity_off = ""
                if ENTITY_BASE <= addr < ENTITY_BASE + 0x80000:
                    entity_off = f" [entity+0x{addr - ENTITY_BASE:05X}]"
                print(f"  0x{addr:08X}{entity_off}")
        addr += 2


if __name__ == '__main__':
    main()

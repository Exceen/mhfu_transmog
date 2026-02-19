#!/opt/homebrew/bin/python3
"""Investigate the mystery address 0x090AF682 and entity differences."""

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


def read_u8(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return data[off]


def read_u16(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<H', data, off)[0]


def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


def main():
    print("Loading save states...")
    data1 = load_state(0)  # Rath Soul
    data2 = load_state(1)  # Mafumofu

    # === 1. Investigate 0x090AF682 ===
    addr = 0x090AF682
    print(f"\n{'='*80}")
    print(f"  Mystery address 0x090AF682")
    print(f"{'='*80}")

    # Dump 256 bytes around it
    start = addr - 64
    print(f"\n  Memory dump around 0x{addr:08X} (64 bytes before, 192 bytes after):")
    print(f"  {'Address':>12}  {'Slot1 u16':>10}  {'Slot2 u16':>10}  {'Diff':>5}  Note")
    for a in range(start, start + 256, 2):
        v1 = read_u16(data1, a)
        v2 = read_u16(data2, a)
        diff = "***" if v1 != v2 else ""
        note = ""
        if v1 == 102 and v2 == 252:
            note = " <<< EQUIP_ID!"
        if a == addr:
            note += " <<< TARGET"
        print(f"  0x{a:08X}  {v1:>10}  {v2:>10}  {diff:>5}  {note}")

    # Check if this looks like an equip slot structure
    # Equip slot: [type1:u8][type2:u8][equip_id:u16][deco1:u16][deco2:s16][deco3:s16][extra:s16]
    slot_base = addr - 2  # equip_id is at offset 2 in slot, so base = addr - 2
    print(f"\n  If this is an equip slot (base = 0x{slot_base:08X}):")
    print(f"    type1 (u8):   Slot1={read_u8(data1, slot_base)}, Slot2={read_u8(data2, slot_base)}")
    print(f"    type2 (u8):   Slot1={read_u8(data1, slot_base+1)}, Slot2={read_u8(data2, slot_base+1)}")
    print(f"    equip_id:     Slot1={read_u16(data1, slot_base+2)}, Slot2={read_u16(data2, slot_base+2)}")
    print(f"    deco1:        Slot1={read_u16(data1, slot_base+4)}, Slot2={read_u16(data2, slot_base+4)}")
    print(f"    deco2:        Slot1={read_u16(data1, slot_base+6)}, Slot2={read_u16(data2, slot_base+6)}")
    print(f"    deco3:        Slot1={read_u16(data1, slot_base+8)}, Slot2={read_u16(data2, slot_base+8)}")
    print(f"    extra:        Slot1={read_u16(data1, slot_base+10)}, Slot2={read_u16(data2, slot_base+10)}")

    # Check multiple potential slot bases (try offsets -2, -4, -6... to find structure alignment)
    for test_base in [addr - 2, addr - 4, addr - 6, addr]:
        t1_s1 = read_u8(data1, test_base)
        t2_s1 = read_u8(data1, test_base+1)
        eid_s1 = read_u16(data1, test_base+2)
        t1_s2 = read_u8(data2, test_base)
        t2_s2 = read_u8(data2, test_base+1)
        eid_s2 = read_u16(data2, test_base+2)
        if eid_s1 == 102 and eid_s2 == 252 and t1_s1 == t1_s2 and t1_s1 in range(0, 20):
            print(f"\n  MATCH: Equip slot at 0x{test_base:08X}")
            print(f"    type1={t1_s1}, type2={t2_s1}, equip_id changes 102->252")

    # Look for other equip slots nearby (12-byte stride)
    print(f"\n  Checking for equip slot pattern (12-byte stride) near 0x{slot_base:08X}:")
    for i in range(-5, 6):
        base = slot_base + i * 12
        t1 = read_u8(data1, base)
        t2 = read_u8(data1, base+1)
        eid = read_u16(data1, base+2)
        d1 = read_u16(data1, base+4)
        d2 = read_u16(data1, base+6)
        d3 = read_u16(data1, base+8)
        # Also slot 2
        t1_b = read_u8(data2, base)
        eid_b = read_u16(data2, base+2)
        same = "SAME" if t1 == t1_b and eid == eid_b else "DIFF"
        marker = " <<<" if i == 0 else ""
        print(f"    [{i:+2d}] 0x{base:08X}: type={t1}/{t2} eid={eid:>5} deco={d1},{d2},{d3} [{same}]{marker}")

    # Also try 10-byte stride (in case the slot is smaller)
    print(f"\n  Checking 10-byte stride:")
    for i in range(-5, 6):
        base = slot_base + i * 10
        t1 = read_u8(data1, base)
        t2 = read_u8(data1, base+1)
        eid = read_u16(data1, base+2)
        d1 = read_u16(data1, base+4)
        eid_b = read_u16(data2, base+2)
        same = "SAME" if eid == eid_b else "DIFF"
        marker = " <<<" if i == 0 else ""
        print(f"    [{i:+2d}] 0x{base:08X}: type={t1}/{t2} eid={eid:>5} d1={d1} [{same}]{marker}")

    # === 2. Entity+0x044C4 investigation ===
    print(f"\n{'='*80}")
    print(f"  Entity+0x044C4 (0x09999E64): 55 -> 25")
    print(f"{'='*80}")
    # Dump surroundings
    base = 0x09999E64 - 32
    print(f"  Memory around entity+0x044C4:")
    for a in range(base, base + 128, 2):
        v1 = read_u16(data1, a)
        v2 = read_u16(data2, a)
        diff = "***" if v1 != v2 else ""
        eo = a - ENTITY_BASE
        print(f"    entity+0x{eo:05X} (0x{a:08X}): {v1:>6} -> {v2:>6}  {diff}")

    # === 3. Extended Entity rendering data ===
    print(f"\n{'='*80}")
    print(f"  Extended Entity area - first 50 differences")
    print(f"{'='*80}")
    count = 0
    for a in range(0x09A00000, 0x0A000000, 2):
        off = a - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 2 > len(data1) or off + 2 > len(data2):
            break
        v1 = read_u16(data1, a)
        v2 = read_u16(data2, a)
        if v1 != v2:
            count += 1
            eo = a - ENTITY_BASE
            if count <= 50:
                print(f"    entity+0x{eo:05X} (0x{a:08X}): {v1:>6} (0x{v1:04X}) -> {v2:>6} (0x{v2:04X})")

    # === 4. Search for what code references 0x090AF682 ===
    # The address is 0x090AF682. Check if any code loads from near this address
    # lui would need upper half: 0x090B (since 0xF682 is negative: 0x090A + 0xFFF6682 → 0x090B + (-0x097E))
    # Actually: 0x090AF682 = 0x090B0000 + (-0x097E) = 0x090B0000 + 0xFFFF6682? No.
    # 0x090AF682: upper = 0x090A, lower = 0xF682 (signed = -2430)
    # But since 0xF682 >= 0x8000, lui would use 0x090B and addiu -0x097E
    # 0x090B0000 + (-0x097E) = 0x090B0000 - 0x097E = 0x090AF682 ✓
    print(f"\n{'='*80}")
    print(f"  Search: Code loading from near 0x090AF682")
    print(f"{'='*80}")
    CODE_START = 0x08804000
    CODE_END = 0x08960000

    # Search for lui 0x090B
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data1, psp)
        op = (instr >> 26) & 0x3F
        if op == 0x0F:  # lui
            imm = instr & 0xFFFF
            if imm == 0x090B:
                rt = (instr >> 16) & 0x1F
                REG_NAMES = ['zero','at','v0','v1','a0','a1','a2','a3',
                             't0','t1','t2','t3','t4','t5','t6','t7',
                             's0','s1','s2','s3','s4','s5','s6','s7',
                             't8','t9','k0','k1','gp','sp','fp','ra']
                print(f"  lui ${REG_NAMES[rt]}, 0x090B at 0x{psp:08X}")

    # Also search for lui 0x090A (if the address is loaded with positive offset)
    for psp in range(CODE_START, CODE_END, 4):
        instr = read_u32(data1, psp)
        op = (instr >> 26) & 0x3F
        if op == 0x0F:  # lui
            imm = instr & 0xFFFF
            if imm == 0x090A:
                rt = (instr >> 16) & 0x1F
                REG_NAMES = ['zero','at','v0','v1','a0','a1','a2','a3',
                             't0','t1','t2','t3','t4','t5','t6','t7',
                             's0','s1','s2','s3','s4','s5','s6','s7',
                             't8','t9','k0','k1','gp','sp','fp','ra']
                print(f"  lui ${REG_NAMES[rt]}, 0x090A at 0x{psp:08X}")

    # === 5. Check if 0x090AF682 is a save data mirror or equipment box ===
    # Look for the equip slot pattern: check if nearby addresses also
    # contain equipment data from the save file
    print(f"\n{'='*80}")
    print(f"  Search: Check if 0x090AF682 area contains chest/arms/waist/legs equip_ids")
    print(f"{'='*80}")
    # We know head equip_ids for Rath Soul set:
    # Check entity copy 2 for all 5 slots
    print(f"  Entity copy 2 equipment slots (Slot 1 save state):")
    for slot_idx in range(5):
        slot_names = ["Head", "Chest", "Arms", "Waist", "Legs"]
        base = ENTITY_BASE + 0x4D8 + slot_idx * 12
        t1 = read_u8(data1, base)
        t2 = read_u8(data1, base+1)
        eid = read_u16(data1, base+2)
        d1 = read_u16(data1, base+4)
        d2 = read_u16(data1, base+6)
        d3 = read_u16(data1, base+8)
        print(f"    {slot_names[slot_idx]:>6}: type={t1}/{t2} eid={eid:>5} deco={d1},{d2},{d3}")

    # Now search for these equip_ids near 0x090AF682
    print(f"\n  Searching for other equip_ids from our set near 0x090AF682...")
    chest_eid = read_u16(data1, ENTITY_BASE + 0x4D8 + 1*12 + 2)
    arms_eid = read_u16(data1, ENTITY_BASE + 0x4D8 + 2*12 + 2)
    waist_eid = read_u16(data1, ENTITY_BASE + 0x4D8 + 3*12 + 2)
    legs_eid = read_u16(data1, ENTITY_BASE + 0x4D8 + 4*12 + 2)
    print(f"    Head=102, Chest={chest_eid}, Arms={arms_eid}, Waist={waist_eid}, Legs={legs_eid}")

    target_eids = {102: "Head", chest_eid: "Chest", arms_eid: "Arms",
                   waist_eid: "Waist", legs_eid: "Legs"}

    # Search +/- 256 bytes from 0x090AF682
    search_start = 0x090AF682 - 256
    search_end = 0x090AF682 + 256
    for a in range(search_start, search_end, 2):
        v = read_u16(data1, a)
        if v in target_eids and v != 0:
            offset = a - 0x090AF682
            print(f"    0x{a:08X} (offset {offset:+4d}): {v} ({target_eids[v]})")


if __name__ == '__main__':
    main()

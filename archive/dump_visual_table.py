#!/opt/homebrew/bin/python3
"""Dump visual table entries to understand their structure and create data patches.

Visual tables found in save state:
  Head table 1: 0x08960754
  Head table 2: 0x08964B74
  Other tables: 0x0896CD4C, 0x08968D14, 0x08970D34

Entries are 40 bytes each, indexed by equip_id.

We want to compare equip_id 102 (Rathalos Soul Helm) vs 252 (Mafumofu Hood)
to understand the entry format and create a transmog patch.

Also check the FUComplete lookup tables from the dispatch entries:
  0x089972AC, 0x08997BA8, 0x08997E6C, 0x089981D4, 0x0899851C
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

def read_state_bytes(data, psp_addr, length):
    off = psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE
    return data[off:off+length]

def read_u16(data, psp_addr):
    off = psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<H', data, off)[0]

def read_u32(data, psp_addr):
    off = psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]


def dump_entry(data, table_base, equip_id, label=""):
    addr = table_base + equip_id * 40
    raw = read_state_bytes(data, addr, 40)
    if label:
        print(f"\n  {label} (equip_id={equip_id}, addr=0x{addr:08X}):")
    print(f"    Raw hex: {raw.hex()}")
    # Parse as various formats
    u16s = struct.unpack_from('<20H', raw)
    u8s = raw
    print(f"    As u16[20]: {list(u16s)}")
    print(f"    As u8[40]:  {list(u8s)}")
    # Key fields
    print(f"    Bytes 0-1:  {u16s[0]:04X} ({u16s[0]})  <- likely model_index/file_id?")
    print(f"    Bytes 2-3:  {u16s[1]:04X} ({u16s[1]})")
    print(f"    Bytes 4-5:  {u16s[2]:04X} ({u16s[2]})")
    print(f"    Byte 0:     {u8s[0]:02X} ({u8s[0]})")
    print(f"    Byte 1:     {u8s[1]:02X} ({u8s[1]})")
    return raw


def main():
    print("Loading save state (Rathalos Soul Helm)...")
    data = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

    # Also load Mafumofu save state for comparison
    print("Loading save state (Mafumofu Hood)...")
    data2 = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_1.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

    # === 1. Visual Table 1 (Head) at 0x08960754 ===
    print("\n" + "=" * 70)
    print("  Head Visual Table 1 at 0x08960754 (40-byte entries)")
    print("=" * 70)
    table1 = 0x08960754
    r1a = dump_entry(data, table1, 102, "Rathalos Soul Helm (equip 102)")
    r1b = dump_entry(data, table1, 252, "Mafumofu Hood (equip 252)")
    r1c = dump_entry(data, table1, 0, "Equip ID 0 (reference)")
    r1d = dump_entry(data, table1, 1, "Equip ID 1 (Leather Helm)")

    # Check if table is same between save states
    same = True
    for i in range(40):
        if r1a[i] != read_state_bytes(data2, table1 + 102 * 40, 40)[i]:
            same = False
            break
    print(f"\n    Table entry 102 same in both saves? {same}")

    # === 2. Visual Table 2 (Head) at 0x08964B74 ===
    print("\n" + "=" * 70)
    print("  Head Visual Table 2 at 0x08964B74")
    print("=" * 70)
    table2 = 0x08964B74
    dump_entry(data, table2, 102, "Rathalos Soul Helm (equip 102)")
    dump_entry(data, table2, 252, "Mafumofu Hood (equip 252)")

    # === 3. FUComplete lookup tables ===
    print("\n" + "=" * 70)
    print("  FUComplete Lookup Tables (u16 arrays indexed by equip_id)")
    print("=" * 70)
    fuc_tables = [
        (0x089972AC, "Table A (dispatch slot 4)"),
        (0x08997BA8, "Table B (dispatch slot 6, head?)"),
        (0x08997E6C, "Table C (dispatch slot 8)"),
        (0x089981D4, "Table D (dispatch slot 10)"),
        (0x0899851C, "Table E (dispatch slot 12)"),
    ]
    for tbl_addr, name in fuc_tables:
        print(f"\n  {name} at 0x{tbl_addr:08X}:")
        for eid in [0, 1, 97, 102, 223, 252]:
            addr = tbl_addr + eid * 2
            val = read_u16(data, addr)
            print(f"    [{eid}] = {val} (0x{val:04X}) at 0x{addr:08X}")

    # === 4. Dispatch handler pointer table at 0x089C7510 ===
    print("\n" + "=" * 70)
    print("  Dispatch handler pointer table at 0x089C7510")
    print("  (base pointers for each slot, indexed by slot+2)")
    print("=" * 70)
    ptr_table = 0x089C7510
    for slot in range(14):
        idx = slot + 2
        addr = ptr_table + idx * 4
        offset_val = read_u32(data, addr)
        base = ptr_table + offset_val if offset_val < 0x10000000 else offset_val
        print(f"    Slot {slot:2d}: ptr_table[{idx}] at 0x{addr:08X} = 0x{offset_val:08X} -> base=0x{base:08X}")

    # === 5. For the head slot (slot 7), check what the handler reads for equip_id 102 vs 252 ===
    print("\n" + "=" * 70)
    print("  Handler data for head slot 7")
    print("=" * 70)
    slot7_ptr_addr = ptr_table + (7 + 2) * 4
    slot7_offset = read_u32(data, slot7_ptr_addr)
    slot7_base = ptr_table + slot7_offset
    print(f"  Slot 7 pointer: offset=0x{slot7_offset:08X}, base=0x{slot7_base:08X}")

    for eid in [0, 1, 102, 252]:
        entry_addr = slot7_base + eid * 4
        try:
            val = read_u32(data, entry_addr)
            result = slot7_base + val if val != 0xFFFFFFFF else 0
            print(f"  equip_id {eid:3d}: [{eid}*4] at 0x{entry_addr:08X} = 0x{val:08X} -> model=0x{result:08X}")
        except:
            print(f"  equip_id {eid:3d}: OUT OF BOUNDS at 0x{entry_addr:08X}")

    # === 6. Also check slot 6 (head table lookup) ===
    print("\n" + "=" * 70)
    print("  Handler data for head slot 6 (table lookup path)")
    print("=" * 70)
    slot6_ptr_addr = ptr_table + (6 + 2) * 4
    slot6_offset = read_u32(data, slot6_ptr_addr)
    slot6_base = ptr_table + slot6_offset
    print(f"  Slot 6 pointer: offset=0x{slot6_offset:08X}, base=0x{slot6_base:08X}")

    # For slot 6, the input is the RESULT of the table lookup, not equip_id
    # Table B at 0x08997BA8 maps equip_id -> model_index
    tbl_b = 0x08997BA8
    for eid in [0, 1, 102, 252]:
        model_idx = read_u16(data, tbl_b + eid * 2)
        entry_addr = slot6_base + model_idx * 4
        try:
            val = read_u32(data, entry_addr)
            result = slot6_base + val if val != 0xFFFFFFFF else 0
            print(f"  equip_id {eid:3d}: table_lookup={model_idx} -> [{model_idx}*4] at 0x{entry_addr:08X} = 0x{val:08X} -> model=0x{result:08X}")
        except:
            print(f"  equip_id {eid:3d}: table_lookup={model_idx} -> OUT OF BOUNDS")

    # === 7. Find the currently loaded head model pointer in player entity ===
    # Search for known model pointers in a specific area
    print("\n" + "=" * 70)
    print("  Searching for head model pointer in player entity data")
    print("  (looking for the slot 7 result for equip_id 102)")
    print("=" * 70)

    # Get the model pointer for equip_id 102 via slot 7
    entry_addr_102 = slot7_base + 102 * 4
    val_102 = read_u32(data, entry_addr_102)
    model_ptr_102 = slot7_base + val_102 if val_102 != 0xFFFFFFFF else 0

    if model_ptr_102:
        print(f"  Head model pointer for Rath Soul (102): 0x{model_ptr_102:08X}")
        # Search for this pointer value in save state (player entity area)
        print(f"  Searching for 0x{model_ptr_102:08X} in RAM...")
        found = []
        for psp in range(0x08800000, 0x09A00000, 4):
            off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
            if off + 3 >= len(data): break
            val = struct.unpack_from('<I', data, off)[0]
            if val == model_ptr_102:
                found.append(psp)
        print(f"  Found at {len(found)} locations:")
        for addr in found[:20]:
            print(f"    0x{addr:08X}")

    # === 8. Compare player render state between save states ===
    # Find bytes that differ in a narrow range around the player entity
    # The player entity is likely near 0x089C7508 (base pointer for models)
    print("\n" + "=" * 70)
    print("  Key pointer at 0x089C7508 in both save states")
    print("=" * 70)
    base_ptr_1 = read_u32(data, 0x089C7508)
    base_ptr_2 = read_u32(data2, 0x089C7508)
    print(f"  Save 1 (Rath Soul): 0x{base_ptr_1:08X}")
    print(f"  Save 2 (Mafumofu): 0x{base_ptr_2:08X}")

    if base_ptr_1 == base_ptr_2:
        print("  Same! Searching for diffs near this pointer...")
        for offset in range(0, 0x2000, 4):
            addr = base_ptr_1 + offset
            off1 = addr - PSP_RAM_START + RAM_BASE_IN_STATE
            off2 = addr - PSP_RAM_START + RAM_BASE_IN_STATE
            if off1 + 3 >= len(data) or off2 + 3 >= len(data2): break
            v1 = struct.unpack_from('<I', data, off1)[0]
            v2 = struct.unpack_from('<I', data2, off2)[0]
            if v1 != v2:
                print(f"    0x{addr:08X} (+0x{offset:04X}): {v1:08X} vs {v2:08X}")


if __name__ == '__main__':
    main()

#!/opt/homebrew/bin/python3
"""Compare the different armor data tables found in the EBOOT/RAM.

Known tables:
  0x089633A8 - Main armor table (40-byte entries, 435 entries, found via save state)
  0x08960754 - Visual table 1 (40-byte entries, used by code for gender/flags check)
  0x08964B74 - Visual table 2 (40-byte entries, used for body?)
  0x0895E098 - Another table (28-byte entries based on code)
  0x0899A238 - 24-byte entry table (used by equip iterator for model data)

Also search for FUComplete file loading hooks.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
RAM_BASE_IN_STATE = 0x48
PSP_RAM_START = 0x08000000

def psp_to_state(psp_addr):
    return psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE

def decompress_state(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(data[0xB0:], max_output_size=128 * 1024 * 1024)

def dump_entries(data, table_base, entry_size, indices, label):
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  Base: PSP 0x{table_base:08X}, Entry size: {entry_size}")
    print(f"{'='*70}")
    for idx in indices:
        off = psp_to_state(table_base) + idx * entry_size
        if off < 0 or off + entry_size > len(data):
            print(f"  Entry {idx}: OUT OF RANGE")
            continue
        entry = data[off:off + entry_size]
        u16s = [struct.unpack_from('<H', entry, i)[0] for i in range(0, min(entry_size, 40), 2)]
        print(f"  Entry {idx:4d}: {' '.join(f'{v:5d}' for v in u16s)}")
        # Also hex
        print(f"           hex: {entry[:min(20,entry_size)].hex()}")

def main():
    data = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")
    print(f"Decompressed: {len(data)} bytes")

    # Known armor indices and their visual indices (u16[18] from main table)
    known = [
        (0, "Nothing", 275),
        (1, "Leather Helm", 61),
        (2, "Chainmail Head", 62),
        (101, "Rathalos Soul Cap", 186),
        (102, "Rathalos Soul Helm", 187),
        (251, "Mafumofu Hood v1", 133),
        (252, "Mafumofu Hood v2", 134),
    ]

    armor_ids = [k[0] for k in known]
    visual_ids = [k[2] for k in known]

    # Main armor table at 0x089633A8
    dump_entries(data, 0x089633A8, 40, armor_ids,
                 "Main armor table (0x089633A8, 40-byte entries)")

    # Visual table 1 at 0x08960754 - indexed by visual index (u16[18])
    dump_entries(data, 0x08960754, 40, visual_ids,
                 "Visual table 1 (0x08960754, 40-byte entries) indexed by u16[18]")

    # Visual table 2 at 0x08964B74 - might be same data, different gender
    dump_entries(data, 0x08964B74, 40, visual_ids,
                 "Visual table 2 (0x08964B74, 40-byte entries)")

    # 24-byte table at 0x0899A238 - indexed by equip_index? or visual_index?
    dump_entries(data, 0x0899A238, 24, armor_ids,
                 "24-byte table (0x0899A238) indexed by armor_id")
    dump_entries(data, 0x0899A238, 24, visual_ids,
                 "24-byte table (0x0899A238) indexed by visual_id")

    # What are the values at key visual table entries?
    # Check if visual table entries contain model numbers or file IDs
    print(f"\n{'='*70}")
    print(f"  Checking visual table for model numbers")
    print(f"{'='*70}")

    for armor_id, name, visual_id in known:
        off = psp_to_state(0x08960754) + visual_id * 40
        if off < 0 or off + 40 > len(data): continue
        entry = data[off:off + 40]
        u16s = [struct.unpack_from('<H', entry, i)[0] for i in range(0, 40, 2)]
        u8s = list(entry)

        # Check each field for model number patterns
        # Known: Rathalos Soul Helm = model 97, Mafumofu Hood = model 223
        # File IDs: Rath Helm head = 503, Mafu head = 629
        print(f"\n  [{visual_id:3d}] {name} (armor_id={armor_id}):")
        print(f"    u8:  {u8s}")
        print(f"    u16: {u16s}")

    # Search for file ID base values in the visual tables
    print(f"\n{'='*70}")
    print(f"  Search for file ID 503 (Rath Helm) and 629 (Mafu Hood) in visual tables")
    print(f"{'='*70}")

    for table_name, table_base in [("visual1", 0x08960754), ("visual2", 0x08964B74)]:
        for fid_name, fid, vis_idx in [("Rath503", 503, 187), ("Mafu629", 629, 134)]:
            off = psp_to_state(table_base) + vis_idx * 40
            entry = data[off:off + 40]
            for i in range(0, 40, 2):
                v = struct.unpack_from('<H', entry, i)[0]
                if v == fid:
                    print(f"  FOUND {fid_name} ({fid}) at {table_name}[{vis_idx}]+{i}")

    # Also look for model numbers in visual table
    for vis_idx, name, model in [(187, "Rath Helm", 97), (134, "Mafu Hood", 223)]:
        off = psp_to_state(0x08960754) + vis_idx * 40
        entry = data[off:off + 40]
        for i in range(0, 40, 2):
            v = struct.unpack_from('<H', entry, i)[0]
            if v == model:
                print(f"  FOUND model {model} at visual1[{vis_idx}]+{i} ({name})")

    # Search for strings in EBOOT related to file loading
    print(f"\n{'='*70}")
    print(f"  Searching EBOOT for file/DATA strings")
    print(f"{'='*70}")

    eboot_path = "/Users/Exceen/Downloads/mhfu_transmog/EBOOT.BIN"
    with open(eboot_path, 'rb') as f:
        eboot = f.read()

    # Search for "DATA" and "data" strings
    for pattern in [b'DATA.BIN', b'data.bin', b'nativePSP', b'pac', b'.pac']:
        pos = 0
        count = 0
        while True:
            pos = eboot.find(pattern, pos)
            if pos == -1: break
            psp = 0x08804000 + pos
            # Show surrounding string
            start = max(0, pos - 10)
            end = min(len(eboot), pos + 40)
            ctx = eboot[start:end]
            ctx_str = ctx.replace(b'\x00', b' ').decode('ascii', errors='replace')
            print(f"  '{pattern.decode()}' at EBOOT+0x{pos:06X} (PSP 0x{psp:08X}): ...{ctx_str}...")
            pos += 1
            count += 1
            if count > 10:
                print(f"  ... (more matches)")
                break

    # Check the equip structure in save state for visual indices
    print(f"\n{'='*70}")
    print(f"  Equipment structure dump at PSP 0x090AF672")
    print(f"{'='*70}")
    equip_base = psp_to_state(0x090AF660)
    for i in range(0, 120, 2):
        v = struct.unpack_from('<H', data, equip_base + i)[0]
        psp = 0x090AF660 + i
        marker = ""
        if psp == 0x090AF682: marker = " <-- HEAD EQUIP ID"
        elif psp == 0x090AF672: marker = " <-- HEAD SLOT TYPE"
        elif psp == 0x090AF6BA: marker = " <-- HEAD MODEL INDEX"
        print(f"  PSP 0x{psp:08X} (+{i:3d}): {v:5d} (0x{v:04X}){marker}")


if __name__ == '__main__':
    main()

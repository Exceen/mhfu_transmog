#!/opt/homebrew/bin/python3
"""Find ALL copies of equipment data in RAM.

Search for clusters where the known equipment IDs appear near each other.
Known values from state0 (Rathalos Soul set):
  head=102, body=99, arm=97, waist=97, leg=36

Also search for model clusters and file ID clusters to map all copies.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
RAM_BASE_IN_STATE = 0x48
PSP_RAM_START = 0x08000000


def decompress_state(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(data[0xB0:], max_output_size=128 * 1024 * 1024)


def state_to_psp(off):
    return off - RAM_BASE_IN_STATE + PSP_RAM_START


def search_16bit_value(data, value):
    """Find all offsets where a 16-bit value appears."""
    results = []
    for off in range(0, len(data) - 1, 2):
        v = struct.unpack_from('<H', data, off)[0]
        if v == value:
            results.append(off)
    return results


def main():
    data0 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")
    data1 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_1.ppst")
    print(f"State 0: {len(data0)} bytes, State 1: {len(data1)} bytes")

    # Verify the states differ
    known_model_off = 0x010AF702
    m0 = struct.unpack_from('<H', data0, known_model_off)[0]
    m1 = struct.unpack_from('<H', data1, known_model_off)[0]
    print(f"Head model: {m0} vs {m1}")
    assert m0 != m1, "States must differ!"

    # === Part 1: Find ALL 16-bit diffs that match head armor transition ===
    # Head model: 97 → 223
    # Head file ID: 503 → 629
    # Head equip ID: 102 → 252
    print("\n" + "=" * 70)
    print("=== ALL 16-bit transitions between states ===")

    transitions = {
        '97→223 (model)': (97, 223),
        '503→629 (file_id)': (503, 629),
        '102→252 (equip_id)': (102, 252),
    }

    for label, (v0, v1) in transitions.items():
        matches = []
        for off in range(0, min(len(data0), len(data1)) - 1, 2):
            a = struct.unpack_from('<H', data0, off)[0]
            b = struct.unpack_from('<H', data1, off)[0]
            if a == v0 and b == v1:
                matches.append(off)
        print(f"\n  {label}: {len(matches)} locations")
        for off in matches:
            psp = state_to_psp(off)
            print(f"    PSP 0x{psp:08X} (state 0x{off:08X})")

    # === Part 2: Search for equipment ID clusters ===
    # Look for locations where head=102 appears, then check if body/arm/waist/leg
    # values appear nearby (within 256 bytes)
    print("\n" + "=" * 70)
    print("=== Searching for equipment ID clusters (head=102 near body=99, arm=97, leg=36) ===")

    head_locs = search_16bit_value(data0, 102)
    print(f"Found {len(head_locs)} locations with value 102 in state0")

    for head_off in head_locs:
        # Search within ±128 bytes for other equipment values
        found = {'head': head_off}
        for check_off in range(max(0, head_off - 128), min(len(data0) - 1, head_off + 128), 2):
            v = struct.unpack_from('<H', data0, check_off)[0]
            if v == 99 and 'body' not in found:
                found['body'] = check_off
            elif v == 97 and 'arm' not in found:
                found['arm'] = check_off
            elif v == 36 and 'leg' not in found:
                found['leg'] = check_off

        if len(found) >= 3:  # At least head + 2 others
            psp = state_to_psp(head_off)
            slots_found = ', '.join(f"{k}={found[k]-head_off:+d}" for k in found if k != 'head')
            # Check if this location changes in state1
            v1 = struct.unpack_from('<H', data1, head_off)[0]
            changed = f" → {v1} in state1" if v1 != 102 else " (unchanged in state1)"
            print(f"  PSP 0x{psp:08X}: head=102{changed}, nearby: {slots_found}")

    # === Part 3: Search for model index clusters ===
    print("\n" + "=" * 70)
    print("=== Searching for model index clusters (head=97 near body=90, arm=88, waist=76, leg=66) ===")

    head_model_locs = search_16bit_value(data0, 97)
    print(f"Found {len(head_model_locs)} locations with value 97")

    for head_off in head_model_locs:
        found = {'head': head_off}
        for check_off in range(max(0, head_off - 64), min(len(data0) - 1, head_off + 64), 2):
            v = struct.unpack_from('<H', data0, check_off)[0]
            if v == 90 and 'body' not in found:
                found['body'] = check_off
            elif v == 88 and 'arm' not in found:
                found['arm'] = check_off
            elif v == 76 and 'waist' not in found:
                found['waist'] = check_off
            elif v == 66 and 'leg' not in found:
                found['leg'] = check_off

        if len(found) >= 4:
            psp = state_to_psp(head_off)
            offsets = {k: found[k] - head_off for k in found if k != 'head'}
            v1 = struct.unpack_from('<H', data1, head_off)[0]
            changed = f" → {v1}" if v1 != 97 else " (same)"
            print(f"  PSP 0x{psp:08X}: head=97{changed}, offsets: {offsets}")
            # Dump the full cluster
            min_off = min(found.values())
            max_off = max(found.values())
            for off in range(min_off, max_off + 2, 2):
                v0 = struct.unpack_from('<H', data0, off)[0]
                v1_val = struct.unpack_from('<H', data1, off)[0]
                labels = [k for k, o in found.items() if o == off]
                label = f" [{','.join(labels)}]" if labels else ""
                diff = " DIFF" if v0 != v1_val else ""
                print(f"    0x{state_to_psp(off):08X}: {v0:5d} → {v1_val:5d}{label}{diff}")

    # === Part 4: Search for file ID clusters ===
    print("\n" + "=" * 70)
    print("=== Searching for file ID clusters (head=503 near body=836, arm=1174, waist=1495, leg=128) ===")

    head_fid_locs = search_16bit_value(data0, 503)
    print(f"Found {len(head_fid_locs)} locations with value 503")

    for head_off in head_fid_locs:
        found = {'head': head_off}
        for check_off in range(max(0, head_off - 64), min(len(data0) - 1, head_off + 64), 2):
            v = struct.unpack_from('<H', data0, check_off)[0]
            if v == 836 and 'body' not in found:
                found['body'] = check_off
            elif v == 1174 and 'arm' not in found:
                found['arm'] = check_off
            elif v == 1495 and 'waist' not in found:
                found['waist'] = check_off
            elif v == 128 and 'leg' not in found:
                found['leg'] = check_off

        if len(found) >= 4:
            psp = state_to_psp(head_off)
            offsets = {k: found[k] - head_off for k in found if k != 'head'}
            v1 = struct.unpack_from('<H', data1, head_off)[0]
            changed = f" → {v1}" if v1 != 503 else " (same)"
            print(f"  PSP 0x{psp:08X}: head=503{changed}, offsets: {offsets}")

    # === Part 5: Also search the save file for equipment data ===
    print("\n" + "=" * 70)
    print("=== Searching save file for equipment patterns ===")
    save_path = "/Users/Exceen/Documents/PPSSPP/PSP/SAVEDATA/ULUS10391/MHP2NDG.BIN"
    with open(save_path, 'rb') as f:
        save_data = f.read()
    print(f"Save file: {len(save_data)} bytes")

    # Search for equip IDs in save file
    for label, value in [("head=102", 102), ("body=99", 99), ("leg=36", 36)]:
        locs = []
        for off in range(0, len(save_data) - 1, 2):
            v = struct.unpack_from('<H', save_data, off)[0]
            if v == value:
                locs.append(off)
        print(f"  {label}: {len(locs)} locations in save file")

    # Search for cluster of equip IDs in save file
    print("\n  Searching for equip ID cluster in save file...")
    for head_off in range(0, len(save_data) - 1, 2):
        v = struct.unpack_from('<H', save_data, head_off)[0]
        if v != 102:
            continue
        found = {'head': head_off}
        for check_off in range(max(0, head_off - 128), min(len(save_data) - 1, head_off + 128), 2):
            sv = struct.unpack_from('<H', save_data, check_off)[0]
            if sv == 99 and 'body' not in found:
                found['body'] = check_off
            elif sv == 97 and 'arm' not in found:
                found['arm'] = check_off
            elif sv == 36 and 'leg' not in found:
                found['leg'] = check_off
        if len(found) >= 3:
            offsets = {k: found[k] - head_off for k in found if k != 'head'}
            print(f"    Save offset 0x{head_off:06X}: head=102, nearby: {offsets}")
            # Dump context
            for off in range(max(0, head_off - 16), min(len(save_data) - 1, head_off + 32), 2):
                sv = struct.unpack_from('<H', save_data, off)[0]
                labels = [k for k, o in found.items() if o == off]
                label = f" [{','.join(labels)}]" if labels else ""
                print(f"      0x{off:06X}: {sv:5d} (0x{sv:04X}){label}")

    # === Part 6: Find save data in RAM ===
    print("\n" + "=" * 70)
    print("=== Searching for save file data in RAM ===")
    # Take a chunk from the save file and search for it in RAM
    # Use a distinctive 16-byte chunk from around the middle of the save
    for chunk_offset in [0x1000, 0x10000, 0x50000, 0xA0000]:
        chunk = save_data[chunk_offset:chunk_offset+16]
        if len(chunk) < 16:
            continue
        for ram_off in range(0, len(data0) - 16):
            if data0[ram_off:ram_off+16] == chunk:
                psp = state_to_psp(ram_off)
                delta = ram_off - chunk_offset
                print(f"  Save[0x{chunk_offset:06X}] found at RAM state 0x{ram_off:08X} "
                      f"(PSP 0x{psp:08X}), delta=0x{delta:08X}")
                break


if __name__ == '__main__':
    main()

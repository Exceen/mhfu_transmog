#!/opt/homebrew/bin/python3
"""Find where the equipped armor ID is stored in memory.

We know changing head armor from Rathalos Soul Cap to Mafumofu Hood changes:
  - Model index: 96 → 223 (at state 0x010AF702)
  - File ID: 502 → 629 (at state 0x0112F594)

But writing to those addresses doesn't work because the game recalculates them.
We need to find the SOURCE: the equipped armor ID (101 → 251 for the head).

Strategy:
  1. Dump memory around the model index array to find related fields
  2. Search for ALL 16-bit diffs between states, filtered to plausible armor IDs
  3. Search for 32-bit diffs too
  4. Look for the armor table pointer (0x089633A8 + index * 40)
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


def main():
    # Use the ORIGINAL two states (slot 1 and slot 2 from the previous session)
    data0 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")
    data1 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_1.ppst")

    # First verify these states are actually different
    model_off = 0x010AF702
    m0 = struct.unpack_from('<H', data0, model_off)[0]
    m1 = struct.unpack_from('<H', data1, model_off)[0]
    print(f"Model index at 0x{model_off:08X}: state0={m0}, state1={m1}")
    if m0 == m1:
        print("WARNING: Both states have same model index! States may not be the original pair.")
        print("State 0 head model values around known offset:")
        for i in range(-10, 12, 2):
            off = model_off + i
            v0 = struct.unpack_from('<H', data0, off)[0]
            v1 = struct.unpack_from('<H', data1, off)[0]
            diff = " DIFF" if v0 != v1 else ""
            print(f"  0x{off:08X}: {v0:5d} vs {v1:5d}{diff}")
        print("\nCannot proceed without two different states.")
        print("Please re-save slot 1 with Rathalos Soul Cap and slot 2 with Mafumofu Hood.")
        return

    print(f"Good: states differ (model {m0} vs {m1})")

    # === Part 1: Dump wide area around model index array ===
    print("\n" + "=" * 70)
    print("=== Memory around model index array (state offset 0x010AF6B0-0x010AF720) ===")
    for off in range(0x010AF690, 0x010AF730, 2):
        if off + 1 >= len(data0):
            break
        v0 = struct.unpack_from('<H', data0, off)[0]
        v1 = struct.unpack_from('<H', data1, off)[0]
        diff = " <<< DIFF" if v0 != v1 else ""
        psp = state_to_psp(off)
        label = ""
        if off == 0x010AF6B6: label = " [leg model]"
        elif off == 0x010AF6BA: label = " [head model]"
        elif off == 0x010AF6BC: label = " [body model]"
        elif off == 0x010AF6BE: label = " [arm model]"
        elif off == 0x010AF6C0: label = " [waist model]"
        print(f"  PSP 0x{psp:08X} (state 0x{off:08X}): {v0:5d} vs {v1:5d}{label}{diff}")

    # === Part 2: Dump wide area around file ID array ===
    print("\n" + "=" * 70)
    print("=== Memory around file ID array (state offset 0x0112F580-0x0112F5B0) ===")
    for off in range(0x0112F570, 0x0112F5C0, 2):
        if off + 1 >= len(data0):
            break
        v0 = struct.unpack_from('<H', data0, off)[0]
        v1 = struct.unpack_from('<H', data1, off)[0]
        diff = " <<< DIFF" if v0 != v1 else ""
        psp = state_to_psp(off)
        label = ""
        if off == 0x0112F590: label = " [leg file_id]"
        elif off == 0x0112F594: label = " [head file_id]"
        elif off == 0x0112F596: label = " [body file_id]"
        elif off == 0x0112F598: label = " [arm file_id]"
        elif off == 0x0112F59A: label = " [leg file_id]"
        print(f"  PSP 0x{psp:08X} (state 0x{off:08X}): {v0:5d} vs {v1:5d}{label}{diff}")

    # === Part 3: Search for 16-bit value 101 → 251 transition ===
    print("\n" + "=" * 70)
    print("=== Searching for 16-bit: 101 → 251 (armor table index) ===")
    matches = []
    for off in range(0, min(len(data0), len(data1)) - 1, 2):
        v0 = struct.unpack_from('<H', data0, off)[0]
        v1 = struct.unpack_from('<H', data1, off)[0]
        if v0 == 101 and v1 == 251:
            psp = state_to_psp(off)
            matches.append((off, psp))
    print(f"Found {len(matches)} matches")
    for off, psp in matches[:20]:
        # Show context
        print(f"  PSP 0x{psp:08X} (state 0x{off:08X}):")
        for i in range(-8, 12, 2):
            ctx_off = off + i
            cv0 = struct.unpack_from('<H', data0, ctx_off)[0]
            cv1 = struct.unpack_from('<H', data1, ctx_off)[0]
            marker = " <<<" if i == 0 else ""
            d = " DIFF" if cv0 != cv1 else ""
            print(f"    +{i:+3d}: {cv0:5d} vs {cv1:5d}{d}{marker}")

    # === Part 4: Search byte-aligned 16-bit (not just even offsets) ===
    print("\n" + "=" * 70)
    print("=== Searching for 16-bit (byte-aligned): 101 → 251 ===")
    matches_ba = []
    for off in range(0, min(len(data0), len(data1)) - 1):
        v0 = struct.unpack_from('<H', data0, off)[0]
        v1 = struct.unpack_from('<H', data1, off)[0]
        if v0 == 101 and v1 == 251:
            psp = state_to_psp(off)
            matches_ba.append((off, psp))
    print(f"Found {len(matches_ba)} matches (including odd offsets)")
    for off, psp in matches_ba[:20]:
        print(f"  PSP 0x{psp:08X} (state 0x{off:08X})")

    # === Part 5: Search for 32-bit 101 → 251 ===
    print("\n" + "=" * 70)
    print("=== Searching for 32-bit: 101 → 251 ===")
    matches_32 = []
    for off in range(0, min(len(data0), len(data1)) - 3, 4):
        v0 = struct.unpack_from('<I', data0, off)[0]
        v1 = struct.unpack_from('<I', data1, off)[0]
        if v0 == 101 and v1 == 251:
            psp = state_to_psp(off)
            matches_32.append((off, psp))
    print(f"Found {len(matches_32)} matches")
    for off, psp in matches_32[:20]:
        print(f"  PSP 0x{psp:08X} (state 0x{off:08X})")

    # === Part 6: Search for armor data table pointers ===
    # Rathalos Soul Cap = entry 101: 0x089633A8 + 101*40 = 0x089643C0
    # Mafumofu Hood = entry 251: 0x089633A8 + 251*40 = 0x08966500
    ptr0 = 0x089633A8 + 101 * 40
    ptr1 = 0x089633A8 + 251 * 40
    print(f"\n{'=' * 70}")
    print(f"=== Searching for armor table pointers: 0x{ptr0:08X} → 0x{ptr1:08X} ===")
    matches_ptr = []
    for off in range(0, min(len(data0), len(data1)) - 3, 4):
        v0 = struct.unpack_from('<I', data0, off)[0]
        v1 = struct.unpack_from('<I', data1, off)[0]
        if v0 == ptr0 and v1 == ptr1:
            psp = state_to_psp(off)
            matches_ptr.append((off, psp))
    print(f"Found {len(matches_ptr)} matches")
    for off, psp in matches_ptr[:20]:
        print(f"  PSP 0x{psp:08X} (state 0x{off:08X})")

    # === Part 7: Search for diffs near model index array ===
    # Look for any 16-bit changes within 256 bytes of the model array
    print(f"\n{'=' * 70}")
    print("=== ALL 16-bit diffs within 512 bytes of model index array ===")
    center = 0x010AF702
    for off in range(center - 256, center + 256, 2):
        if off < 0 or off + 1 >= min(len(data0), len(data1)):
            continue
        v0 = struct.unpack_from('<H', data0, off)[0]
        v1 = struct.unpack_from('<H', data1, off)[0]
        if v0 != v1:
            psp = state_to_psp(off)
            dist = off - center
            print(f"  PSP 0x{psp:08X} (state 0x{off:08X}, dist {dist:+4d}): {v0:5d} → {v1:5d}")

    # === Part 8: Search for diffs near file ID array ===
    print(f"\n{'=' * 70}")
    print("=== ALL 16-bit diffs within 512 bytes of file ID array ===")
    center2 = 0x0112F594
    for off in range(center2 - 256, center2 + 256, 2):
        if off < 0 or off + 1 >= min(len(data0), len(data1)):
            continue
        v0 = struct.unpack_from('<H', data0, off)[0]
        v1 = struct.unpack_from('<H', data1, off)[0]
        if v0 != v1:
            psp = state_to_psp(off)
            dist = off - center2
            print(f"  PSP 0x{psp:08X} (state 0x{off:08X}, dist {dist:+4d}): {v0:5d} → {v1:5d}")

    # === Part 9: Wider search - all 16-bit diffs where ONLY head-related values change ===
    # Filter: v0 and v1 are both < 1000 (plausible IDs), and differ
    print(f"\n{'=' * 70}")
    print("=== All 16-bit diffs where both values < 500 (plausible armor IDs) ===")
    print("    (sampling every 2 bytes across full RAM)")
    plausible = []
    for off in range(RAM_BASE_IN_STATE, min(len(data0), len(data1)) - 1, 2):
        v0 = struct.unpack_from('<H', data0, off)[0]
        v1 = struct.unpack_from('<H', data1, off)[0]
        if v0 != v1 and v0 < 500 and v1 < 500 and v0 > 0 and v1 > 0:
            plausible.append((off, v0, v1))

    print(f"Found {len(plausible)} plausible diffs")
    # Filter further: values that could be head armor indices
    # Rathalos Soul Cap = 101, Mafumofu Hood = 251
    head_matches = [(off, v0, v1) for off, v0, v1 in plausible
                    if (v0 == 101 or v1 == 251)]
    print(f"  Of which {len(head_matches)} have v0=101 or v1=251:")
    for off, v0, v1 in head_matches[:30]:
        psp = state_to_psp(off)
        print(f"    PSP 0x{psp:08X}: {v0} → {v1}")

    # Also show model-number matches
    model_matches = [(off, v0, v1) for off, v0, v1 in plausible
                     if (v0 == 96 and v1 == 223)]
    print(f"\n  Diffs with v0=96, v1=223 (model numbers):")
    for off, v0, v1 in model_matches[:30]:
        psp = state_to_psp(off)
        print(f"    PSP 0x{psp:08X}: {v0} → {v1}")

    # File ID matches
    fid_matches = [(off, v0, v1) for off, v0, v1 in plausible
                   if (v0 == 502 or v0 == 453) and (v1 == 629)]
    print(f"\n  Diffs with file ID pattern (502→629):")
    for off, v0, v1 in fid_matches[:30]:
        psp = state_to_psp(off)
        print(f"    PSP 0x{psp:08X}: {v0} → {v1}")


if __name__ == '__main__':
    main()

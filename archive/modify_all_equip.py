#!/opt/homebrew/bin/python3
"""Modify ALL copies of equipment data in the save state.

There are 3 locations where head equip ID (102→252) changes:
  1. PSP 0x090AF682 (near model index array)
  2. PSP 0x09995A1A
  3. PSP 0x09995E7A

Plus model index and file ID arrays.
Modify ALL of them to Mafumofu Hood (252) and see if it works.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
RAM_BASE_IN_STATE = 0x48
PSP_RAM_START = 0x08000000


def psp_to_state(psp_addr):
    return psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE


def state_to_psp(off):
    return off - RAM_BASE_IN_STATE + PSP_RAM_START


def dump_area(data0, data1, psp_center, radius=32):
    """Dump 16-bit values around a PSP address in both states."""
    center = psp_to_state(psp_center)
    for off in range(center - radius, center + radius, 2):
        if off < 0 or off + 1 >= len(data0):
            continue
        v0 = struct.unpack_from('<H', data0, off)[0]
        v1 = struct.unpack_from('<H', data1, off)[0]
        psp = state_to_psp(off)
        diff = " <<< DIFF" if v0 != v1 else ""
        marker = " *** TARGET" if off == center else ""
        print(f"  PSP 0x{psp:08X}: {v0:5d} → {v1:5d}{diff}{marker}")


def main():
    src = f"{STATE_DIR}/ULJM05500_1.01_0.ppst"  # Slot 1 (Rathalos Soul Helm)
    dst = f"{STATE_DIR}/ULJM05500_1.01_2.ppst"  # Slot 3 (output)

    print("Reading both states for comparison...")
    with open(src, 'rb') as f:
        raw0 = f.read()
    with open(f"{STATE_DIR}/ULJM05500_1.01_1.ppst", 'rb') as f:
        raw1 = f.read()

    header = bytearray(raw0[:0xB0])
    dctx = zstandard.ZstdDecompressor()
    data0 = bytearray(dctx.decompress(raw0[0xB0:], max_output_size=128 * 1024 * 1024))
    data1 = dctx.decompress(raw1[0xB0:], max_output_size=128 * 1024 * 1024)

    # Dump areas around all 3 equip ID locations
    equip_locs = [0x090AF682, 0x09995A1A, 0x09995E7A]
    for i, psp in enumerate(equip_locs):
        print(f"\n=== Equip ID location {i+1}: PSP 0x{psp:08X} ===")
        dump_area(data0, data1, psp, radius=40)

    # Now modify ALL locations in data0
    print("\n" + "=" * 70)
    print("=== Modifying ALL equipment data to Mafumofu Hood ===\n")

    # Target values from state1 (Mafumofu Hood):
    # We'll copy the values from state1 at each differing location

    # Find ALL 16-bit diffs between states (in the equipment/model/fileid regions)
    # and patch data0 to match data1 at those locations
    regions_to_patch = [
        # Equip ID region 1 (around 0x090AF682)
        (0x090AF660, 0x090AF6C2),
        # Model index array
        (0x090AF6B6, 0x090AF6C2),
        # File ID regions
        (0x08A35880, 0x08A358A0),
        (0x0912F548, 0x0912F560),
        # Equip ID region 2
        (0x09995A00, 0x09995A40),
        # Equip ID region 3
        (0x09995E60, 0x09995EA0),
    ]

    total_patches = 0
    for psp_start, psp_end in regions_to_patch:
        start = psp_to_state(psp_start)
        end = psp_to_state(psp_end)
        region_patches = 0
        for off in range(start, min(end, len(data0) - 1, len(data1) - 1), 2):
            v0 = struct.unpack_from('<H', data0, off)[0]
            v1 = struct.unpack_from('<H', data1, off)[0]
            if v0 != v1:
                struct.pack_into('<H', data0, off, v1)
                psp = state_to_psp(off)
                print(f"  PSP 0x{psp:08X}: {v0} → {v1}")
                region_patches += 1
        if region_patches > 0:
            print(f"  ({region_patches} patches in region 0x{psp_start:08X}-0x{psp_end:08X})")
        total_patches += region_patches

    print(f"\nTotal patches: {total_patches}")

    # Verify key values
    print("\n=== Verification ===")
    for psp in equip_locs:
        off = psp_to_state(psp)
        v = struct.unpack_from('<H', data0, off)[0]
        print(f"  Equip ID at PSP 0x{psp:08X}: {v}")

    model_off = psp_to_state(0x090AF6BA)
    print(f"  Head model at PSP 0x090AF6BA: {struct.unpack_from('<H', data0, model_off)[0]}")
    fid_off = psp_to_state(0x0912F54C)
    print(f"  Head file ID at PSP 0x0912F54C: {struct.unpack_from('<H', data0, fid_off)[0]}")

    # Recompress and save
    print(f"\nCompressing...")
    cctx = zstandard.ZstdCompressor(level=3)
    compressed = cctx.compress(bytes(data0))

    original_compressed_size = len(raw0) - 0xB0
    for off in range(0, 0xB0 - 3, 4):
        val = struct.unpack_from('<I', header, off)[0]
        if val == original_compressed_size:
            struct.pack_into('<I', header, off, len(compressed))

    output = bytes(header) + compressed
    with open(dst, 'wb') as f:
        f.write(output)
    print(f"Saved to: {dst}")
    print(f"\nLoad slot 3, then trigger model reload (zone change / enter quest).")


if __name__ == '__main__':
    main()

#!/opt/homebrew/bin/python3
"""Modify a PPSSPP save state to change armor model indices.

Diagnostic tool: if loading the modified save state changes the armor
appearance, we know the memory addresses are correct and the CWCheat
issue is a timing/execution problem.

Reads slot 0, modifies armor values to Fatalis Set, writes to slot 2.
This avoids confusion with File Replacer (which replaces Rathalos Soul -> Black).
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
RAM_BASE_IN_STATE = 0x48
PSP_RAM_START = 0x08000000

# PSP addresses for model indices (16-bit)
MODEL_ADDRS = {
    'leg':   0x090AF6B6,
    'head':  0x090AF6BA,
    'body':  0x090AF6BC,
    'arm':   0x090AF6BE,
    'waist': 0x090AF6C0,
}

# PSP addresses for file IDs (16-bit)
FILEID_ADDRS = {
    'leg':   0x0912F548,
    'head':  0x0912F54C,
    'body':  0x0912F54E,
    'arm':   0x0912F550,
    'waist': 0x0912F552,
}

# File ID bases (file_id = base + model_number)
FILE_ID_BASES = {
    'head':  406,
    'body':  746,
    'arm':   1086,
    'waist': 1419,
    'leg':   62,
}

# Fatalis Set model numbers (visually very distinctive - dark dragon armor)
TARGET_SET = {
    'head':  0,    # f_hair000 (Fatalis Helm)
    'body':  61,   # f_body061
    'arm':   59,   # f_arm059
    'waist': 50,   # f_wst050
    'leg':   46,   # f_reg046
}


def psp_to_state(psp_addr):
    return psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE


def main():
    src = f"{STATE_DIR}/ULJM05500_1.01_0.ppst"   # Slot 1 (Rathalos Soul)
    dst = f"{STATE_DIR}/ULJM05500_1.01_2.ppst"   # Slot 3 (output)

    # Read and decompress
    print(f"Reading: {src}")
    with open(src, 'rb') as f:
        raw = f.read()

    header = raw[:0xB0]
    print(f"Header: {len(header)} bytes")
    print(f"Header hex (first 32): {header[:32].hex()}")

    # Check for size fields in header that might need updating
    # Dump some header fields
    for off in [0x00, 0x04, 0x08, 0x0C, 0x10, 0x14, 0x18, 0x1C]:
        val = struct.unpack_from('<I', header, off)[0]
        print(f"  header[0x{off:02X}]: 0x{val:08X} ({val})")

    dctx = zstandard.ZstdDecompressor()
    data = bytearray(dctx.decompress(raw[0xB0:], max_output_size=128 * 1024 * 1024))
    print(f"Decompressed: {len(data)} bytes")

    # Show current values
    print("\n=== Current model indices ===")
    for slot in ['head', 'body', 'arm', 'waist', 'leg']:
        off = psp_to_state(MODEL_ADDRS[slot])
        val = struct.unpack_from('<H', data, off)[0]
        print(f"  {slot:6s}: model {val} (state offset 0x{off:08X})")

    print("\n=== Current file IDs ===")
    for slot in ['head', 'body', 'arm', 'waist', 'leg']:
        off = psp_to_state(FILEID_ADDRS[slot])
        val = struct.unpack_from('<H', data, off)[0]
        print(f"  {slot:6s}: file_id {val} (state offset 0x{off:08X})")

    # Modify to Fatalis Set
    print("\n=== Writing Fatalis Set values ===")
    for slot in ['head', 'body', 'arm', 'waist', 'leg']:
        model_num = TARGET_SET[slot]
        file_id = FILE_ID_BASES[slot] + model_num

        off_model = psp_to_state(MODEL_ADDRS[slot])
        struct.pack_into('<H', data, off_model, model_num)

        off_fid = psp_to_state(FILEID_ADDRS[slot])
        struct.pack_into('<H', data, off_fid, file_id)

        print(f"  {slot:6s}: model={model_num}, file_id={file_id}")

    # Verify writes
    print("\n=== Verify written values ===")
    for slot in ['head', 'body', 'arm', 'waist', 'leg']:
        off_m = psp_to_state(MODEL_ADDRS[slot])
        off_f = psp_to_state(FILEID_ADDRS[slot])
        m = struct.unpack_from('<H', data, off_m)[0]
        f = struct.unpack_from('<H', data, off_f)[0]
        expected_m = TARGET_SET[slot]
        expected_f = FILE_ID_BASES[slot] + expected_m
        ok_m = "OK" if m == expected_m else "FAIL"
        ok_f = "OK" if f == expected_f else "FAIL"
        print(f"  {slot:6s}: model={m} [{ok_m}], file_id={f} [{ok_f}]")

    # Recompress and save
    print(f"\nCompressing...")
    cctx = zstandard.ZstdCompressor(level=3)
    compressed = cctx.compress(bytes(data))

    # Check if header contains the compressed size
    original_compressed_size = len(raw) - 0xB0
    new_compressed_size = len(compressed)
    print(f"Original compressed: {original_compressed_size} bytes")
    print(f"New compressed: {new_compressed_size} bytes")

    # Check if original compressed size appears in header
    for off in range(0, 0xB0 - 3, 4):
        val = struct.unpack_from('<I', header, off)[0]
        if val == original_compressed_size:
            print(f"  Found original compressed size at header offset 0x{off:02X}!")
            print(f"  Updating to {new_compressed_size}")
            header = bytearray(header)
            struct.pack_into('<I', header, off, new_compressed_size)
            header = bytes(header)
        if val == len(data):
            print(f"  Found decompressed size at header offset 0x{off:02X} (unchanged)")

    output = header + compressed
    print(f"\nSaving to: {dst}")
    print(f"Total size: {len(output)} bytes (original: {len(raw)})")
    with open(dst, 'wb') as f:
        f.write(output)

    print(f"\nDone! Load save state slot 2 in PPSSPP to test.")
    print("If armor appearance changes to Fatalis Set -> addresses are correct, CWCheat has a timing issue.")
    print("If still Black armor -> these addresses don't directly control rendering.")


if __name__ == '__main__':
    main()

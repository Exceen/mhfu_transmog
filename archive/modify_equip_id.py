#!/opt/homebrew/bin/python3
"""Modify save state to change the equipped armor ID (not model index).

Test: change head armor ID from 102 (Rathalos Soul Helm) to 252 (Mafumofu Hood).
The game should derive the correct model index and file ID on zone change.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
RAM_BASE_IN_STATE = 0x48
PSP_RAM_START = 0x08000000

# Equipment slot addresses (PSP) - each slot is 12 bytes:
#   [slot_type: u16] [armor_id: u16] [deco1: u16] [deco2: u16] [deco3: u16] [pad: u16]
EQUIP_SLOTS = {
    'leg':   {'type_addr': 0x090AF668, 'id_addr': 0x090AF66A},
    'head':  {'type_addr': 0x090AF680, 'id_addr': 0x090AF682},
    'body':  {'type_addr': 0x090AF68C, 'id_addr': 0x090AF68E},
    'arm':   {'type_addr': 0x090AF698, 'id_addr': 0x090AF69A},
    'waist': {'type_addr': 0x090AF6A4, 'id_addr': 0x090AF6A6},
}


def psp_to_state(psp_addr):
    return psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE


def main():
    src = f"{STATE_DIR}/ULJM05500_1.01_0.ppst"   # Slot 1 (Rathalos Soul)
    dst = f"{STATE_DIR}/ULJM05500_1.01_2.ppst"   # Slot 3 (output)

    print(f"Reading: {src}")
    with open(src, 'rb') as f:
        raw = f.read()

    header = bytearray(raw[:0xB0])
    dctx = zstandard.ZstdDecompressor()
    data = bytearray(dctx.decompress(raw[0xB0:], max_output_size=128 * 1024 * 1024))
    print(f"Decompressed: {len(data)} bytes")

    # Show current equipment IDs
    print("\n=== Current equipment ===")
    for slot in ['leg', 'head', 'body', 'arm', 'waist']:
        off = psp_to_state(EQUIP_SLOTS[slot]['id_addr'])
        val = struct.unpack_from('<H', data, off)[0]
        # Also show decorations (next 3 u16 values)
        deco_off = off + 2
        decos = [struct.unpack_from('<H', data, deco_off + i*2)[0] for i in range(3)]
        print(f"  {slot:6s}: armor_id={val:4d}, decos={decos}")

    # Show current model indices for reference
    model_addrs = {
        'leg':   0x090AF6B6,
        'head':  0x090AF6BA,
        'body':  0x090AF6BC,
        'arm':   0x090AF6BE,
        'waist': 0x090AF6C0,
    }
    print("\n=== Current model indices ===")
    for slot in ['leg', 'head', 'body', 'arm', 'waist']:
        off = psp_to_state(model_addrs[slot])
        val = struct.unpack_from('<H', data, off)[0]
        print(f"  {slot:6s}: model={val}")

    # Modify: change head armor ID from 102 to 252 (Mafumofu Hood)
    # Also clear decorations since Mafumofu Hood may have different slots
    print("\n=== Modifying head armor ID: 102 → 252 (Mafumofu Hood) ===")
    head_id_off = psp_to_state(EQUIP_SLOTS['head']['id_addr'])
    struct.pack_into('<H', data, head_id_off, 252)
    # Clear decoration slots
    for i in range(3):
        struct.pack_into('<H', data, head_id_off + 2 + i*2, 0)

    # Verify
    val = struct.unpack_from('<H', data, head_id_off)[0]
    decos = [struct.unpack_from('<H', data, head_id_off + 2 + i*2)[0] for i in range(3)]
    print(f"  head: armor_id={val}, decos={decos}")

    # Recompress and save
    print(f"\nCompressing...")
    cctx = zstandard.ZstdCompressor(level=3)
    compressed = cctx.compress(bytes(data))

    original_compressed_size = len(raw) - 0xB0
    new_compressed_size = len(compressed)
    for off in range(0, 0xB0 - 3, 4):
        val = struct.unpack_from('<I', header, off)[0]
        if val == original_compressed_size:
            struct.pack_into('<I', header, off, new_compressed_size)

    output = bytes(header) + compressed
    print(f"Saving to: {dst}")
    with open(dst, 'wb') as f:
        f.write(output)

    print(f"\nDone! Load slot 3, then go through a zone change (enter/exit house).")
    print("If head armor changes to Mafumofu Hood → we found the right approach!")


if __name__ == '__main__':
    main()

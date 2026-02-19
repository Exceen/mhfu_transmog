#!/opt/homebrew/bin/python3
"""Dump armor data table entries to find where the model number is stored.

The armor data table is at PSP 0x089633A8, 40 bytes per entry.
We know:
  Index 101 (Rathalos Soul Cap) → model 96
  Index 102 (Rathalos Soul Helm) → model 97
  Index 0 (Nothing) → model 0
  Index 1 (Leather Helm) → model 1 (probably)
  Index 251 (Mafumofu Hood) → model 223
  Index 252 (Mafumofu Hood variant?) → model 223

Search each 40-byte entry for a field that matches the model number.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
RAM_BASE_IN_STATE = 0x48
PSP_RAM_START = 0x08000000

ARMOR_TABLE_PSP = 0x089633A8
ENTRY_SIZE = 40


def psp_to_state(psp_addr):
    return psp_addr - PSP_RAM_START + RAM_BASE_IN_STATE


def decompress_state(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(data[0xB0:], max_output_size=128 * 1024 * 1024)


def dump_entry(data, index, label=""):
    off = psp_to_state(ARMOR_TABLE_PSP) + index * ENTRY_SIZE
    entry = data[off:off + ENTRY_SIZE]
    psp = ARMOR_TABLE_PSP + index * ENTRY_SIZE

    print(f"\n--- Entry {index} ({label}) at PSP 0x{psp:08X} ---")

    # Dump as bytes
    print(f"  Hex: {entry.hex()}")

    # Dump as various formats
    print(f"  u8:  {list(entry)}")

    u16s = [struct.unpack_from('<H', entry, i)[0] for i in range(0, 40, 2)]
    print(f"  u16: {u16s}")

    u32s = [struct.unpack_from('<I', entry, i)[0] for i in range(0, 40, 4)]
    print(f"  u32: {u32s}")

    # Show each field with offset
    print(f"  Field-by-field:")
    for i in range(0, 40, 2):
        u8a, u8b = entry[i], entry[i+1]
        u16 = struct.unpack_from('<H', entry, i)[0]
        s16 = struct.unpack_from('<h', entry, i)[0]
        print(f"    +{i:2d}: u8={u8a:3d},{u8b:3d}  u16={u16:5d}  s16={s16:+6d}  hex={u16:04X}")

    return u16s


def main():
    data = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")
    print(f"Decompressed: {len(data)} bytes")

    # Known armor entries with their model numbers
    known = [
        (0, "Nothing equipped", 0),
        (1, "Leather Helm", 1),
        (2, "Chainmail Head", 2),
        (52, "Red Piercing", None),  # piercing - model unknown
        (53, "Blue Piercing", None),
        (54, "Yellow Piercing", None),
        (55, "Black Piercing", None),
        (101, "Rathalos Soul Cap", 96),
        (102, "Rathalos Soul Helm", 97),
        (233, "White Piercing", None),
        (251, "Mafumofu Hood (v1)", 223),
        (252, "Mafumofu Hood (v2)", 223),
        (381, "Chakra Piercing", None),
    ]

    entries = {}
    for idx, label, model in known:
        u16s = dump_entry(data, idx, label)
        entries[idx] = (label, model, u16s)

    # Now analyze: for entries with known models, which u16 field matches the model?
    print("\n" + "=" * 70)
    print("=== Searching for model number in entry fields ===")
    print("Looking for a consistent field offset where value == model number\n")

    model_entries = [(idx, label, model, u16s) for idx, (label, model, u16s) in entries.items()
                     if model is not None]

    for field_off in range(20):  # 20 u16 fields in 40-byte entry
        values = [(idx, model, u16s[field_off]) for idx, _, model, u16s in model_entries]
        all_match = all(v == m for _, m, v in values)
        if all_match:
            print(f"  *** MATCH at u16 offset {field_off} (byte offset {field_off*2})! ***")
            for idx, model, v in values:
                print(f"      Entry {idx}: field={v}, model={model} ✓")
        else:
            # Check if there's a consistent offset or formula
            diffs = [(v - m) for _, m, v in values]
            if len(set(diffs)) == 1:
                print(f"  Consistent offset at u16[{field_off}]: field = model + {diffs[0]}")
                for idx, model, v in values:
                    print(f"      Entry {idx}: field={v}, model={model}, diff={v-model}")

    # Also try 8-bit fields
    print("\n=== Searching for model in 8-bit fields ===")
    for byte_off in range(40):
        values = []
        for idx, (label, model, u16s) in entries.items():
            if model is None:
                continue
            off = psp_to_state(ARMOR_TABLE_PSP) + idx * ENTRY_SIZE + byte_off
            byte_val = data[off]
            values.append((idx, model, byte_val))

        all_match = all(v == m for _, m, v in values if m < 256)
        if all_match and all(m < 256 for _, m, _ in values):
            print(f"  *** MATCH at byte offset {byte_off}! ***")
            for idx, model, v in values:
                print(f"      Entry {idx}: byte={v}, model={model}")

    # Dump a range of sequential entries to spot patterns
    print("\n" + "=" * 70)
    print("=== Sequential entries 0-10 (field comparison) ===")
    print(f"{'Idx':>4s} ", end="")
    for i in range(20):
        print(f"  u16[{i:2d}]", end="")
    print()

    for idx in range(11):
        off = psp_to_state(ARMOR_TABLE_PSP) + idx * ENTRY_SIZE
        entry = data[off:off + ENTRY_SIZE]
        u16s = [struct.unpack_from('<H', entry, i)[0] for i in range(0, 40, 2)]
        print(f"{idx:4d} ", end="")
        for v in u16s:
            print(f"  {v:7d}", end="")
        print()

    # Also dump entries 96-103 (around Rathalos Soul)
    print(f"\n=== Entries 96-103 ===")
    print(f"{'Idx':>4s} ", end="")
    for i in range(20):
        print(f"  u16[{i:2d}]", end="")
    print()

    for idx in range(96, 104):
        off = psp_to_state(ARMOR_TABLE_PSP) + idx * ENTRY_SIZE
        entry = data[off:off + ENTRY_SIZE]
        u16s = [struct.unpack_from('<H', entry, i)[0] for i in range(0, 40, 2)]
        print(f"{idx:4d} ", end="")
        for v in u16s:
            print(f"  {v:7d}", end="")
        print()

    # Entries 248-255
    print(f"\n=== Entries 248-255 ===")
    print(f"{'Idx':>4s} ", end="")
    for i in range(20):
        print(f"  u16[{i:2d}]", end="")
    print()

    for idx in range(248, 256):
        off = psp_to_state(ARMOR_TABLE_PSP) + idx * ENTRY_SIZE
        entry = data[off:off + ENTRY_SIZE]
        u16s = [struct.unpack_from('<H', entry, i)[0] for i in range(0, 40, 2)]
        print(f"{idx:4d} ", end="")
        for v in u16s:
            print(f"  {v:7d}", end="")
        print()

    # Piercing entries 52-55
    print(f"\n=== Piercing entries 52-55 ===")
    print(f"{'Idx':>4s} ", end="")
    for i in range(20):
        print(f"  u16[{i:2d}]", end="")
    print()

    for idx in [52, 53, 54, 55, 233, 381]:
        off = psp_to_state(ARMOR_TABLE_PSP) + idx * ENTRY_SIZE
        entry = data[off:off + ENTRY_SIZE]
        u16s = [struct.unpack_from('<H', entry, i)[0] for i in range(0, 40, 2)]
        print(f"{idx:4d} ", end="")
        for v in u16s:
            print(f"  {v:7d}", end="")
        print()


if __name__ == '__main__':
    main()

#!/opt/homebrew/bin/python3
"""Find the equip change trigger mechanism.

Search ALL of RAM for u16 locations where:
  State 1 (Rath Soul) = 0x0066 (102)
  State 2 (Mafumofu) = 0x00FC (252)

These could be "last seen equip_id" values that the game compares against
the entity equip_id to detect equipment changes.

Also search for the model cache file_id values and model data pointers
to understand how the renderer resolves models.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

ENTITY_BASE = 0x099959A0
KNOWN_EQUIP_ADDRS = {
    ENTITY_BASE + 0x7A,   # first copy equip_id
    ENTITY_BASE + 0x4DA,  # second copy equip_id
}


def main():
    print("Loading both save states...")
    data1 = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_0.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)
    data2 = zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_1.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

    max_psp = min(
        PSP_RAM_START + len(data1) - RAM_BASE_IN_STATE,
        PSP_RAM_START + len(data2) - RAM_BASE_IN_STATE
    )

    # === 1. Search ALL RAM for u16 = 102 in state1 and 252 in state2 ===
    print("=" * 70)
    print("  Searching ALL RAM for u16 locations: 102 (state1) vs 252 (state2)")
    print(f"  Range: 0x08000000 - 0x{max_psp:08X}")
    print("=" * 70)

    matches = []
    for psp in range(0x08000000, max_psp - 1, 2):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        v1 = struct.unpack_from('<H', data1, off)[0]
        v2 = struct.unpack_from('<H', data2, off)[0]
        if v1 == 0x0066 and v2 == 0x00FC:
            known = " [KNOWN ENTITY COPY]" if psp in KNOWN_EQUIP_ADDRS else ""
            matches.append((psp, known))

    print(f"  Found {len(matches)} locations:")
    for psp, label in matches:
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        # Show context: 4 u16 values before and after
        ctx_before = []
        ctx_after = []
        for i in range(-4, 0):
            cv1 = struct.unpack_from('<H', data1, off + i*2)[0]
            cv2 = struct.unpack_from('<H', data2, off + i*2)[0]
            d = "*" if cv1 != cv2 else ""
            ctx_before.append(f"{cv1:04X}/{cv2:04X}{d}")
        for i in range(1, 5):
            cv1 = struct.unpack_from('<H', data1, off + i*2)[0]
            cv2 = struct.unpack_from('<H', data2, off + i*2)[0]
            d = "*" if cv1 != cv2 else ""
            ctx_after.append(f"{cv1:04X}/{cv2:04X}{d}")
        print(f"  0x{psp:08X}: {' '.join(ctx_before)} [0066/00FC] {' '.join(ctx_after)}{label}")

    # === 2. Search for model cache file_id values ===
    # Rath Soul file_id = 0x01F70000, Mafumofu = 0x00800000
    print("\n" + "=" * 70)
    print("  Searching for model file_id 0x01F7 (Rath Soul head) as u16")
    print("=" * 70)
    count = 0
    for psp in range(0x08800000, 0x09A00000, 2):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 1 >= len(data1): break
        v1 = struct.unpack_from('<H', data1, off)[0]
        v2 = struct.unpack_from('<H', data2, off)[0]
        if v1 == 0x01F7 and v2 != 0x01F7:
            count += 1
            if count <= 20:
                print(f"  0x{psp:08X}: 0x{v1:04X} vs 0x{v2:04X}")
    print(f"  Total: {count}")

    print("\n  Searching for model data ptr 0x091EE8A0 (Rath Soul) as u32")
    count = 0
    for psp in range(0x08800000, 0x09A00000, 4):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 3 >= len(data1): break
        v1 = struct.unpack_from('<I', data1, off)[0]
        v2 = struct.unpack_from('<I', data2, off)[0]
        if v1 == 0x091EE8A0 and v2 != v1:
            count += 1
            if count <= 20:
                v2_str = f"0x{v2:08X}"
                print(f"  0x{psp:08X}: 0x{v1:08X} vs {v2_str}")
    print(f"  Total: {count}")

    # === 3. Check if first and second entity equip copies are EXACT matches ===
    # (to verify one isn't a "previous" copy)
    print("\n" + "=" * 70)
    print("  Comparing first and second entity equip copies within each state")
    print("=" * 70)
    for slot in range(5):  # head, body, arms, waist, legs
        slot_names = ["Head", "Body", "Arms", "Waist", "Legs"]
        first_off = 0x78 + slot * 12
        second_off = 0x4D8 + slot * 12
        first_addr = ENTITY_BASE + first_off
        second_addr = ENTITY_BASE + second_off

        for data, label in [(data1, "State1"), (data2, "State2")]:
            first_bytes = []
            second_bytes = []
            for f in range(0, 12, 2):
                off1 = first_addr + f - PSP_RAM_START + RAM_BASE_IN_STATE
                off2 = second_addr + f - PSP_RAM_START + RAM_BASE_IN_STATE
                v1 = struct.unpack_from('<H', data, off1)[0]
                v2 = struct.unpack_from('<H', data, off2)[0]
                first_bytes.append(f"{v1:04X}")
                second_bytes.append(f"{v2:04X}")
            match = "MATCH" if first_bytes == second_bytes else "DIFFER"
            print(f"  {label} {slot_names[slot]:6s}: 1st=[{' '.join(first_bytes)}] 2nd=[{' '.join(second_bytes)}] {match}")

    # === 4. Check for equip data at OTHER offsets in entity ===
    # Maybe there's a third copy or "rendered equip" state
    print("\n" + "=" * 70)
    print("  Searching entity for equip_id 102 at ANY offset (state 1)")
    print("=" * 70)
    count = 0
    for off in range(0, 0x5000, 2):
        addr = ENTITY_BASE + off
        file_off = addr - PSP_RAM_START + RAM_BASE_IN_STATE
        if file_off + 1 >= len(data1): break
        v = struct.unpack_from('<H', data1, file_off)[0]
        if v == 0x0066:
            # Check if this could be equip_id (context: type bytes before it?)
            ctx_before = struct.unpack_from('<H', data1, file_off - 2)[0]
            ctx_after = struct.unpack_from('<H', data1, file_off + 2)[0]
            count += 1
            if count <= 30:
                print(f"  entity+0x{off:04X} (0x{addr:08X}): 0x0066 [before:{ctx_before:04X} after:{ctx_after:04X}]")
    print(f"  Total occurrences of 0x0066: {count}")

    # === 5. Search for a "rendered equip_id" in model/rendering structures ===
    # The model-related area around 0x08B1CDA4 might have equip_id stored nearby
    print("\n" + "=" * 70)
    print("  Searching model cache area (0x08B00000-0x08C00000) for equip_id 102/252")
    print("=" * 70)
    for psp in range(0x08B00000, 0x08C00000, 2):
        off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 1 >= len(data1) or off + 1 >= len(data2): break
        v1 = struct.unpack_from('<H', data1, off)[0]
        v2 = struct.unpack_from('<H', data2, off)[0]
        if v1 == 0x0066 and v2 == 0x00FC:
            print(f"  0x{psp:08X}: 0x{v1:04X} vs 0x{v2:04X}")

    # === 6. Search area around loaded model data for equip_id ===
    # Models at 0x091EE8A0 (Rath Soul) and 0x0924C0D0 (Mafumofu)
    print("\n" + "=" * 70)
    print("  Searching near model data pointers for equip_id")
    print("=" * 70)
    for model_ptr, label in [
        (0x091EE8A0, "Rath Soul model (state1)"),
        (0x0924C0D0, "Mafumofu model (state2)"),
    ]:
        data = data1 if "state1" in label else data2
        print(f"\n  {label} at 0x{model_ptr:08X}:")
        # Search -0x100 to +0x100 around model data for equip_id
        for moff in range(-0x100, 0x100, 2):
            addr = model_ptr + moff
            file_off = addr - PSP_RAM_START + RAM_BASE_IN_STATE
            if file_off < 0 or file_off + 1 >= len(data): continue
            v = struct.unpack_from('<H', data, file_off)[0]
            target = 0x0066 if "state1" in label else 0x00FC
            if v == target:
                print(f"    model{moff:+05X} (0x{addr:08X}): 0x{v:04X}")

    # === 7. Examine the model cache entry structure in more detail ===
    print("\n" + "=" * 70)
    print("  Model cache entries: full structure dump")
    print("  (32-byte entries starting from ~0x08B1CC44)")
    print("=" * 70)
    # Assume entries start at 0x08B1CC44 (5 entries before our known one)
    # Actually, let's find the start by looking for the pattern
    cache_start = 0x08B1CDA4 - 8 * 0x20  # 8 entries before
    for i in range(16):
        entry_addr = cache_start + i * 0x20
        off = entry_addr - PSP_RAM_START + RAM_BASE_IN_STATE
        if off + 0x20 > len(data1): break
        vals1 = struct.unpack_from('<8I', data1, off)
        vals2 = struct.unpack_from('<8I', data2, off)
        diff = any(a != b for a, b in zip(vals1, vals2))
        marker = " <<<HEAD" if entry_addr == 0x08B1CDA4 else ""
        if diff:
            marker += " DIFF"
        # Check if it looks like a valid entry (has the 01010100 flag at offset 0x18)
        valid = "valid" if vals1[6] == 0x01010100 else "------"
        print(f"  [{i:2d}] 0x{entry_addr:08X}: id={vals1[0]:08X} ptr={vals1[1]:08X} sz={vals1[2]:08X} {valid}{marker}")

    # === 8. Look for "equip change counter" or "dirty" flags ===
    print("\n" + "=" * 70)
    print("  Entity +0x01C analysis (differs: 0x0392 vs 0x034D)")
    print("=" * 70)
    # Check as signed/unsigned interpretations
    val1 = struct.unpack_from('<H', data1, ENTITY_BASE + 0x1C - PSP_RAM_START + RAM_BASE_IN_STATE)[0]
    val2 = struct.unpack_from('<H', data2, ENTITY_BASE + 0x1C - PSP_RAM_START + RAM_BASE_IN_STATE)[0]
    print(f"  State 1: {val1} (0x{val1:04X}) = unsigned {val1}")
    print(f"  State 2: {val2} (0x{val2:04X}) = unsigned {val2}")
    print(f"  Difference: {val1 - val2}")
    # Check context around it
    for off in range(0x18, 0x28, 2):
        addr = ENTITY_BASE + off
        file_off = addr - PSP_RAM_START + RAM_BASE_IN_STATE
        v1 = struct.unpack_from('<H', data1, file_off)[0]
        v2 = struct.unpack_from('<H', data2, file_off)[0]
        diff = " DIFF" if v1 != v2 else ""
        print(f"  +0x{off:03X}: {v1:04X}/{v2:04X}{diff}")


if __name__ == '__main__':
    main()

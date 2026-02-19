#!/opt/homebrew/bin/python3
"""Verify CWCheat addresses by cross-referencing with known working cheats.

The existing HP Max cheat is: 0x108AF464 0x00000096
This writes 150 (0x96) as a 16-bit value.

CWCheat format: 0xTAAAAAAA
  T = type (1 = 16-bit constant write)
  AAAAAAA = address

Question: is AAAAAAA relative to 0x08800000, or is it the raw PSP address?

If relative to 0x08800000:
  HP at 0x08AF464 + 0x08800000 = 0x090AF464
  In state: 0x090AF464 - 0x08000000 + 0x48 = 0x010AF4AC

If raw PSP address:
  HP at 0x008AF464 (or 0x088AF464)
  In state: 0x088AF464 - 0x08000000 + 0x48 = 0x008AF4AC
  OR:       0x008AF464 - 0x08000000 + 0x48 = impossible (negative)

Let's check both interpretations against the save state data.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
RAM_BASE_IN_STATE = 0x48


def decompress_state(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(data[0xB0:], max_output_size=128 * 1024 * 1024)


def main():
    data0 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")
    data1 = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_1.ppst")

    print("=== Verifying HP Max cheat address ===")
    print("Cheat: 0x108AF464 0x00000096 (16-bit write, value 150)")
    print()

    # Interpretation 1: address is offset from 0x08800000
    hp_psp_1 = 0x08800000 + 0x08AF464
    hp_state_1 = hp_psp_1 - 0x08000000 + RAM_BASE_IN_STATE
    print(f"Interpretation 1 (offset from 0x08800000):")
    print(f"  PSP address: 0x{hp_psp_1:08X}")
    print(f"  State offset: 0x{hp_state_1:08X}")
    if hp_state_1 + 1 < len(data0):
        val0 = struct.unpack_from('<H', data0, hp_state_1)[0]
        val1 = struct.unpack_from('<H', data1, hp_state_1)[0]
        print(f"  State 0 value: {val0} (0x{val0:04X})")
        print(f"  State 1 value: {val1} (0x{val1:04X})")
        # Show surrounding values
        print(f"  Context (state 0):")
        for i in range(-8, 12, 2):
            off = hp_state_1 + i
            v = struct.unpack_from('<H', data0, off)[0]
            marker = " <<< HP?" if i == 0 else ""
            print(f"    0x{off:08X}: {v:5d} (0x{v:04X}){marker}")

    # Interpretation 2: address is raw PSP address
    hp_psp_2 = 0x088AF464
    hp_state_2 = hp_psp_2 - 0x08000000 + RAM_BASE_IN_STATE
    print(f"\nInterpretation 2 (raw PSP address 0x088AF464):")
    print(f"  PSP address: 0x{hp_psp_2:08X}")
    print(f"  State offset: 0x{hp_state_2:08X}")
    if hp_state_2 + 1 < len(data0):
        val0 = struct.unpack_from('<H', data0, hp_state_2)[0]
        val1 = struct.unpack_from('<H', data1, hp_state_2)[0]
        print(f"  State 0 value: {val0} (0x{val0:04X})")
        print(f"  State 1 value: {val1} (0x{val1:04X})")
        print(f"  Context (state 0):")
        for i in range(-8, 12, 2):
            off = hp_state_2 + i
            v = struct.unpack_from('<H', data0, off)[0]
            marker = " <<< HP?" if i == 0 else ""
            print(f"    0x{off:08X}: {v:5d} (0x{v:04X}){marker}")

    # Now check our model index address under both interpretations
    print("\n" + "=" * 60)
    print("=== Verifying model index address ===")
    print("Our calculated state offset: 0x010AF702")
    print()

    model_state = 0x010AF702
    val0 = struct.unpack_from('<H', data0, model_state)[0]
    val1 = struct.unpack_from('<H', data1, model_state)[0]
    print(f"State offset 0x{model_state:08X}:")
    print(f"  State 0: {val0} (expected 96 for Rathalos Soul Cap)")
    print(f"  State 1: {val1} (expected 223 for Mafumofu Hood)")

    # If CWCheat uses offset from 0x08800000, then to reach our state offset:
    # state_offset = (0x08800000 + cwcheat_addr) - 0x08000000 + 0x48
    # model_state = 0x08800000 + cwcheat_addr - 0x08000000 + 0x48
    # cwcheat_addr = model_state + 0x08000000 - 0x08800000 - 0x48
    # cwcheat_addr = 0x010AF702 + 0x08000000 - 0x08800000 - 0x48
    cwcheat_addr_1 = model_state + 0x08000000 - 0x08800000 - RAM_BASE_IN_STATE
    psp_addr_1 = 0x08800000 + cwcheat_addr_1
    print(f"\nIf CWCheat = offset from 0x08800000:")
    print(f"  CWCheat address: 0x{cwcheat_addr_1:07X}")
    print(f"  CWCheat line: 0x1{cwcheat_addr_1:07X}")
    print(f"  PSP address: 0x{psp_addr_1:08X}")

    # If CWCheat uses raw PSP address:
    cwcheat_addr_2 = model_state - RAM_BASE_IN_STATE + 0x08000000
    print(f"\nIf CWCheat = raw PSP address:")
    print(f"  CWCheat address: 0x{cwcheat_addr_2 & 0x0FFFFFFF:07X}")
    print(f"  CWCheat line: 0x1{cwcheat_addr_2 & 0x0FFFFFFF:07X}")
    print(f"  PSP address: 0x{cwcheat_addr_2:08X}")

    # Also check: what's at the address we ACTUALLY wrote to?
    # We wrote to CWCheat 0x108AF6BA
    # If this means PSP 0x08800000 + 0x08AF6BA = 0x090AF6BA
    # State offset: 0x090AF6BA - 0x08000000 + 0x48 = 0x010AF702
    # That IS our model index!
    print("\n" + "=" * 60)
    print("=== Cross-check: what does CWCheat 0x108AF6BA point to? ===")
    target_state = 0x090AF6BA - 0x08000000 + RAM_BASE_IN_STATE
    print(f"  CWCheat 0x108AF6BA → PSP 0x090AF6BA → state 0x{target_state:08X}")
    v0 = struct.unpack_from('<H', data0, target_state)[0]
    v1 = struct.unpack_from('<H', data1, target_state)[0]
    print(f"  State 0: {v0}, State 1: {v1}")
    print(f"  Expected: 96 and 223")

    # Check other known cheats from the file
    print("\n" + "=" * 60)
    print("=== Checking other existing cheats ===")
    known_cheats = [
        ("HP Max (1)", 0x108AF464, 0x96),
        ("HP Max (2)", 0x108AF59C, 0x96),
        ("HP Max (3)", 0x108AF59E, 0x96),
        ("Yeriham Max (1)", 0x108B0272, 0x1B5),
        ("Yeriham Max (2)", 0x108AF78C, 0x1B5),
    ]
    for name, cwcheat, expected_val in known_cheats:
        addr_offset = cwcheat & 0x0FFFFFFF
        psp_addr = 0x08800000 + addr_offset
        state_off = psp_addr - 0x08000000 + RAM_BASE_IN_STATE
        if state_off + 1 < len(data0):
            val = struct.unpack_from('<H', data0, state_off)[0]
            match = "✓" if val == expected_val else f"✗ (got {val})"
            print(f"  {name}: CWCheat 0x{cwcheat:08X} → PSP 0x{psp_addr:08X} → "
                  f"state 0x{state_off:08X} = {val} (expected {expected_val}) {match}")
        else:
            print(f"  {name}: state offset 0x{state_off:08X} out of range!")


if __name__ == '__main__':
    main()

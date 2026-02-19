#!/opt/homebrew/bin/python3
"""Find the armor-to-model lookup table in RAM.

We know:
  Head armor entry 101 (Rathalos Soul Cap) -> model 96 (f_hair096)
  Head armor entry 251 (Mafumofu Hood) -> model 223 (f_hair223)
  Head armor entry 1 (Leather Helm) -> model probably 1 (f_hair001)
  Head armor entry 0 (Nothing equipped) -> model 0 (f_hair000)

Search for a contiguous array where these mappings hold.
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
    data = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")

    # Search for array where:
    #   arr[101] == 96  and  arr[251] == 223
    # Try both 8-bit and 16-bit arrays

    # 8-bit array: arr[i] = data[base + i]
    # 16-bit array: arr[i] = u16(data[base + 2*i])

    print("=== Searching for 16-bit lookup table (arr[101]=96, arr[251]=223) ===")
    results_16 = []
    for base in range(0, len(data) - 502, 1):
        if base + 251 * 2 + 1 >= len(data):
            break
        v101 = struct.unpack_from('<H', data, base + 101 * 2)[0]
        v251 = struct.unpack_from('<H', data, base + 251 * 2)[0]
        if v101 == 96 and v251 == 223:
            # Additional checks
            v0 = struct.unpack_from('<H', data, base + 0 * 2)[0]
            v1 = struct.unpack_from('<H', data, base + 1 * 2)[0]
            v52 = struct.unpack_from('<H', data, base + 52 * 2)[0]  # Red Piercing
            v381 = struct.unpack_from('<H', data, base + 381 * 2)[0]  # Chakra Piercing
            psp_addr = base - RAM_BASE_IN_STATE + 0x08000000
            results_16.append((base, psp_addr, v0, v1, v52, v381))

    print(f"Found {len(results_16)} candidates")
    for base, psp, v0, v1, v52, v381 in results_16[:20]:
        print(f"  state 0x{base:08X} (PSP 0x{psp:08X}): "
              f"[0]={v0}, [1]={v1}, [52:RedPiercing]={v52}, [381:Chakra]={v381}")
        # Dump first few values
        vals = [struct.unpack_from('<H', data, base + i * 2)[0] for i in range(10)]
        print(f"    First 10: {vals}")
        # Dump piercing values
        piercing_vals = {
            52: struct.unpack_from('<H', data, base + 52 * 2)[0],
            53: struct.unpack_from('<H', data, base + 53 * 2)[0],
            54: struct.unpack_from('<H', data, base + 54 * 2)[0],
            55: struct.unpack_from('<H', data, base + 55 * 2)[0],
            233: struct.unpack_from('<H', data, base + 233 * 2)[0],
            381: struct.unpack_from('<H', data, base + 381 * 2)[0],
        }
        print(f"    Piercings: {piercing_vals}")

    # 8-bit array
    print("\n=== Searching for 8-bit lookup table (arr[101]=96, arr[251]=223) ===")
    results_8 = []
    for base in range(0, len(data) - 435, 1):
        if data[base + 101] == 96 and data[base + 251] == 223:
            v0 = data[base + 0]
            v1 = data[base + 1]
            v52 = data[base + 52]
            v381 = data[base + 381]
            psp_addr = base - RAM_BASE_IN_STATE + 0x08000000
            results_8.append((base, psp_addr, v0, v1, v52, v381))

    print(f"Found {len(results_8)} candidates")
    for base, psp, v0, v1, v52, v381 in results_8[:20]:
        print(f"  state 0x{base:08X} (PSP 0x{psp:08X}): "
              f"[0]={v0}, [1]={v1}, [52:RedPiercing]={v52}, [381:Chakra]={v381}")
        vals = list(data[base:base + 10])
        print(f"    First 10: {vals}")
        piercing_vals = {
            52: data[base + 52],
            53: data[base + 53],
            54: data[base + 54],
            55: data[base + 55],
            233: data[base + 233],
            381: data[base + 381],
        }
        print(f"    Piercings: {piercing_vals}")

    # Try 32-bit array too
    print("\n=== Searching for 32-bit lookup table ===")
    for base in range(0, len(data) - 252 * 4, 4):
        if base + 251 * 4 + 3 >= len(data):
            break
        v101 = struct.unpack_from('<I', data, base + 101 * 4)[0]
        v251 = struct.unpack_from('<I', data, base + 251 * 4)[0]
        if v101 == 96 and v251 == 223:
            v0 = struct.unpack_from('<I', data, base + 0 * 4)[0]
            v52 = struct.unpack_from('<I', data, base + 52 * 4)[0]
            v381 = struct.unpack_from('<I', data, base + 381 * 4)[0]
            psp_addr = base - RAM_BASE_IN_STATE + 0x08000000
            print(f"  state 0x{base:08X} (PSP 0x{psp_addr:08X}): "
                  f"[0]={v0}, [52]={v52}, [381]={v381}")


if __name__ == '__main__':
    main()

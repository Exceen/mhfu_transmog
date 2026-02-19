#!/usr/bin/env python3
"""
dump_weapon_entries.py
Brute-force search for weapon entries in MHFU PSP RAM dump from PPSSPP save state.
"""

import struct
import zstandard as zstd

# -- Constants -----------------------------------------------------------------
PSP_RAM_START     = 0x08000000
RAM_BASE_IN_STATE = 0x48
MAX_RAM_SIZE      = 128 * 1024 * 1024  # 128 MB

STATE_PATH_0 = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"
STATE_PATH_1 = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_1.ppst"

SKIP_HEADER = 0xB0

# -- Helpers -------------------------------------------------------------------

def load_ram(state_path: str) -> bytes:
    """Load RAM from a PPSSPP zstd-compressed save state."""
    with open(state_path, "rb") as f:
        raw = f.read()

    compressed = raw[SKIP_HEADER:]
    dctx = zstd.ZstdDecompressor()
    decompressed = dctx.decompress(compressed, max_output_size=MAX_RAM_SIZE)

    # RAM starts at RAM_BASE_IN_STATE inside the decompressed blob
    ram = decompressed[RAM_BASE_IN_STATE:]
    print(f"  Loaded {len(decompressed):,} bytes decompressed, RAM portion: {len(ram):,} bytes")
    return ram


def psp_to_offset(psp_addr: int) -> int:
    """Convert a PSP virtual address to an offset into our RAM buffer."""
    return psp_addr - PSP_RAM_START


def read_u16(ram: bytes, psp_addr: int) -> int:
    off = psp_to_offset(psp_addr)
    return struct.unpack_from("<H", ram, off)[0]


def read_u32(ram: bytes, psp_addr: int) -> int:
    off = psp_to_offset(psp_addr)
    return struct.unpack_from("<I", ram, off)[0]


def read_bytes(ram: bytes, psp_addr: int, length: int) -> bytes:
    off = psp_to_offset(psp_addr)
    return ram[off:off + length]


def dump_entry(ram: bytes, addr: int, label: str = ""):
    """Print a single 40-byte weapon entry with decoded fields."""
    raw = read_bytes(ram, addr, 40)
    model_id = struct.unpack_from("<H", raw, 0)[0]
    byte2 = raw[2]
    byte3 = raw[3]
    price_u32 = struct.unpack_from("<I", raw, 6)[0]
    hex_str = raw.hex(" ")
    tag = f"  [{label}]" if label else ""
    print(f"  0x{addr:08X}{tag}: model_id={model_id:5d}  +2=0x{byte2:02X}  +3=0x{byte3:02X}  "
          f"price?={price_u32:>8d}  | {hex_str}")


def brute_search(ram: bytes, target_u16: int, start: int, end: int, max_hits: int = 20):
    """Search every 2-byte aligned address for target_u16, validate as weapon entry."""
    hits = []
    for addr in range(start, end, 2):
        val = read_u16(ram, addr)
        if val != target_u16:
            continue
        # Validation: bytes at +2 and +3 should be small (0-15)
        raw = read_bytes(ram, addr, 40)
        byte2 = raw[2]
        byte3 = raw[3]
        if byte2 > 15 or byte3 > 15:
            continue
        # Validation: u32 at +6 should be a plausible price (0-200000)
        price = struct.unpack_from("<I", raw, 6)[0]
        if price > 200000:
            continue
        # Hit!
        hex_str = raw.hex(" ")
        print(f"  HIT @ 0x{addr:08X}: +2=0x{byte2:02X} +3=0x{byte3:02X} price?={price:>8d} | {hex_str}")
        hits.append(addr)
        if len(hits) >= max_hits:
            print(f"  (stopped after {max_hits} hits)")
            break
    return hits


# -- Main ----------------------------------------------------------------------

def main():
    print("=" * 100)
    print("Loading save state 0 ...")
    ram = load_ram(STATE_PATH_0)
    print()

    # -- TASK 1 ----------------------------------------------------------------
    print("=" * 100)
    print("TASK 1: Brute-force search for u16=21 (0x0015) in 0x0896F000..0x08975000")
    print("-" * 100)
    hits_21 = brute_search(ram, 21, 0x0896F000, 0x08975000)
    print(f"  Total hits: {len(hits_21)}")
    print()

    # -- TASK 2 ----------------------------------------------------------------
    print("=" * 100)
    print("TASK 2: Brute-force search for u16=242 (0x00F2) in 0x0896F000..0x08975000")
    print("-" * 100)
    hits_242 = brute_search(ram, 242, 0x0896F000, 0x08975000)
    print(f"  Total hits: {len(hits_242)}")
    print()

    # -- TASK 3 ----------------------------------------------------------------
    ENTRY_ADDR_21 = 0x089712AA
    ENTRY_SIZE = 40
    print("=" * 100)
    print(f"TASK 3: Dump confirmed entry at 0x{ENTRY_ADDR_21:08X} (model 21) and 5 before/after")
    print("-" * 100)
    for i in range(-5, 6):
        addr = ENTRY_ADDR_21 + i * ENTRY_SIZE
        label = "THIS" if i == 0 else f"{i:+d}"
        dump_entry(ram, addr, label)
    print()

    # -- TASK 4 ----------------------------------------------------------------
    ENTRY_ADDR_242 = 0x08973AFA
    print("=" * 100)
    print(f"TASK 4: Dump confirmed entry at 0x{ENTRY_ADDR_242:08X} (model 242) and 5 before/after")
    print("-" * 100)
    for i in range(-5, 6):
        addr = ENTRY_ADDR_242 + i * ENTRY_SIZE
        label = "THIS" if i == 0 else f"{i:+d}"
        dump_entry(ram, addr, label)
    print()

    # -- TASK 5 ----------------------------------------------------------------
    print("=" * 100)
    print("TASK 5: Compare weapon table between save state 0 and save state 1")
    print("-" * 100)
    print("Loading save state 1 ...")
    ram1 = load_ram(STATE_PATH_1)
    print()

    for tag, addr in [("model 21", ENTRY_ADDR_21), ("model 242", ENTRY_ADDR_242)]:
        data0 = read_bytes(ram, addr, ENTRY_SIZE)
        data1 = read_bytes(ram1, addr, ENTRY_SIZE)
        match = "MATCH (STATIC)" if data0 == data1 else "DIFFER (NOT STATIC)"
        print(f"  0x{addr:08X} ({tag}):")
        print(f"    State 0: {data0.hex(' ')}")
        print(f"    State 1: {data1.hex(' ')}")
        print(f"    Result:  {match}")
        if data0 != data1:
            diffs = [i for i in range(ENTRY_SIZE) if data0[i] != data1[i]]
            print(f"    Differing byte offsets: {diffs}")
        print()

    print("=" * 100)
    print("Done.")


if __name__ == "__main__":
    main()

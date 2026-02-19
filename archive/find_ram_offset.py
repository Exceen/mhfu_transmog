#!/opt/homebrew/bin/python3
"""Find the offset of PSP RAM within a decompressed PPSSPP save state.

Reads the first 64 bytes of EBOOT.BIN (which the PSP loads at 0x08804000),
decompresses the .ppst save state, and searches for those bytes to determine
where the 32MB PSP user RAM (starting at 0x08800000) begins in the state data.

Also searches for known string patterns that might appear in RAM and reports
PPSSPP section markers near the found location.
"""

import struct
import sys
import zstandard

EBOOT_PATH = "/Users/Exceen/Downloads/mhfu_transmog/EBOOT.BIN"
STATE_PATH = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst"

# PSP memory layout
PSP_USER_RAM_START = 0x08800000  # Start of user RAM (32 MB)
PSP_EBOOT_LOAD_ADDR = 0x08804000  # Typical EBOOT load address
PSP_USER_RAM_SIZE = 32 * 1024 * 1024  # 32 MB

# Offset of EBOOT within user RAM
EBOOT_OFFSET_IN_RAM = PSP_EBOOT_LOAD_ADDR - PSP_USER_RAM_START  # 0x4000

# Compressed data starts at this offset in the .ppst file
ZSTD_START_OFFSET = 0xB0


def read_eboot_header(path, size=64):
    """Read the first `size` bytes of EBOOT.BIN."""
    with open(path, 'rb') as f:
        data = f.read(size)
    print(f"Read {len(data)} bytes from EBOOT.BIN")
    print(f"  Hex: {data.hex()}")
    print(f"  ASCII: {data[:16]!r} ...")
    return data


def decompress_state(path):
    """Decompress the PPSSPP save state (.ppst) file.

    The .ppst file has a header, and zstd-compressed data starting at
    offset 0xB0.
    """
    with open(path, 'rb') as f:
        raw = f.read()

    print(f"Save state file size: {len(raw)} bytes ({len(raw) / (1024*1024):.2f} MB)")

    # Verify zstd magic at the expected offset
    zstd_magic = b'\x28\xb5\x2f\xfd'
    if raw[ZSTD_START_OFFSET:ZSTD_START_OFFSET + 4] == zstd_magic:
        print(f"Confirmed zstd magic at offset 0x{ZSTD_START_OFFSET:X}")
    else:
        # Fall back to scanning for the magic
        print(f"No zstd magic at 0x{ZSTD_START_OFFSET:X}, scanning...")
        found = raw.find(zstd_magic)
        if found == -1:
            print("ERROR: No zstd frame found in file!")
            sys.exit(1)
        print(f"Found zstd magic at offset 0x{found:X}")

    compressed = raw[ZSTD_START_OFFSET:]
    dctx = zstandard.ZstdDecompressor()

    try:
        decompressed = dctx.decompress(compressed, max_output_size=128 * 1024 * 1024)
    except Exception as e:
        print(f"Single-shot decompression failed ({e}), trying streaming...")
        reader = dctx.stream_reader(compressed)
        chunks = []
        while True:
            chunk = reader.read(65536)
            if not chunk:
                break
            chunks.append(chunk)
        decompressed = b''.join(chunks)

    print(f"Decompressed size: {len(decompressed)} bytes ({len(decompressed) / (1024*1024):.2f} MB)")
    return decompressed


def find_section_markers(data):
    """Find PPSSPP section headers in the decompressed state data.

    PPSSPP save states use section headers with names like "Memory", "GPU",
    "HLE", "sceCtrl", etc. These are typically length-prefixed or
    null-terminated ASCII strings embedded in the binary data.

    Returns a sorted list of (offset, name) tuples.
    """
    # Known PPSSPP section names
    section_names = [
        b"Memory", b"GPU", b"HLE", b"sceCtrl", b"sceGe", b"sceDisplay",
        b"sceAudio", b"sceDmac", b"sceFont", b"sceKernel", b"sceNet",
        b"sceRtc", b"sceSas", b"sceUmd", b"sceUtility", b"sceIo",
        b"scePower", b"sceImpose", b"CoreTiming", b"sceMpeg",
        b"sceAtrac", b"scePsmf", b"Kernel", b"MemStick",
    ]

    markers = []
    for name in section_names:
        idx = 0
        while True:
            pos = data.find(name, idx)
            if pos == -1:
                break
            # Check that it looks like a real section marker:
            # either preceded by a null byte or a length byte matching the name
            is_marker = False
            if pos > 0:
                preceding = data[pos - 1]
                # Length-prefixed string: preceding byte equals name length
                if preceding == len(name):
                    is_marker = True
                # Null-terminated previous section
                elif preceding == 0:
                    is_marker = True
            else:
                is_marker = True

            if is_marker:
                markers.append((pos, name.decode('ascii')))
            idx = pos + 1

    markers.sort(key=lambda x: x[0])
    return markers


def find_eboot_in_state(data, eboot_header):
    """Search for the EBOOT header bytes within the decompressed state.

    Returns all offsets where the EBOOT header was found.
    """
    matches = []
    idx = 0
    while True:
        pos = data.find(eboot_header, idx)
        if pos == -1:
            break
        matches.append(pos)
        idx = pos + 1
    return matches


def find_string_patterns(data, patterns):
    """Search for ASCII string patterns in the decompressed data.

    Returns a dict mapping each pattern to a list of offsets.
    """
    results = {}
    for pattern in patterns:
        if isinstance(pattern, str):
            pattern_bytes = pattern.encode('ascii')
        else:
            pattern_bytes = pattern
        matches = []
        idx = 0
        while True:
            pos = data.find(pattern_bytes, idx)
            if pos == -1:
                break
            matches.append(pos)
            idx = pos + 1
        results[pattern if isinstance(pattern, str) else pattern.decode('ascii')] = matches
    return results


def print_context(data, offset, window=64, label=""):
    """Print a hex dump of bytes around a given offset."""
    start = max(0, offset - window)
    end = min(len(data), offset + window)
    print(f"  Context around 0x{offset:08X}{' (' + label + ')' if label else ''}:")
    for row_start in range(start, end, 16):
        row_end = min(row_start + 16, end)
        hex_part = ' '.join(f'{data[i]:02X}' for i in range(row_start, row_end))
        ascii_part = ''.join(
            chr(data[i]) if 32 <= data[i] < 127 else '.'
            for i in range(row_start, row_end)
        )
        marker = " <-- MATCH" if row_start <= offset < row_start + 16 else ""
        print(f"    0x{row_start:08X}: {hex_part:<48s} {ascii_part}{marker}")


def main():
    print("=" * 72)
    print("PPSSPP Save State RAM Offset Finder")
    print("=" * 72)

    # Step 1: Read EBOOT header
    print("\n--- Step 1: Reading EBOOT.BIN header ---")
    eboot_header = read_eboot_header(EBOOT_PATH, size=64)

    # Step 2: Decompress save state
    print("\n--- Step 2: Decompressing save state ---")
    state_data = decompress_state(STATE_PATH)

    # Step 3: Find section markers
    print("\n--- Step 3: Finding PPSSPP section markers ---")
    markers = find_section_markers(state_data)
    print(f"Found {len(markers)} section markers:")
    for offset, name in markers:
        print(f"  0x{offset:08X}: {name}")

    # Step 4: Search for EBOOT header in state data
    print("\n--- Step 4: Searching for EBOOT.BIN header in state data ---")
    eboot_matches = find_eboot_in_state(state_data, eboot_header)

    if not eboot_matches:
        print("WARNING: EBOOT header not found! Trying shorter prefix (32 bytes)...")
        eboot_matches = find_eboot_in_state(state_data, eboot_header[:32])
        if not eboot_matches:
            print("WARNING: Still not found with 32 bytes. Trying 16 bytes...")
            eboot_matches = find_eboot_in_state(state_data, eboot_header[:16])

    if eboot_matches:
        print(f"Found EBOOT header at {len(eboot_matches)} location(s):")
        for match_offset in eboot_matches:
            # EBOOT is loaded at PSP_EBOOT_LOAD_ADDR (0x08804000)
            # which is EBOOT_OFFSET_IN_RAM (0x4000) bytes into user RAM.
            # So the start of RAM in the state data is:
            ram_start = match_offset - EBOOT_OFFSET_IN_RAM

            print(f"\n  EBOOT found at state offset:  0x{match_offset:08X}")
            print(f"  EBOOT PSP address:            0x{PSP_EBOOT_LOAD_ADDR:08X}")
            print(f"  Implied RAM start in state:   0x{ram_start:08X}")
            print(f"  RAM end (start + 32MB):       0x{ram_start + PSP_USER_RAM_SIZE:08X}")
            print(f"  State data size:              0x{len(state_data):08X}")

            # Sanity check: RAM region should fit within the state data
            if ram_start >= 0 and ram_start + PSP_USER_RAM_SIZE <= len(state_data):
                print(f"  VALID: 32MB RAM region fits within state data.")
            elif ram_start >= 0:
                available = len(state_data) - ram_start
                print(f"  NOTE: Only {available / (1024*1024):.2f} MB available from RAM start to end of state.")
            else:
                print(f"  WARNING: Calculated RAM start is negative!")

            # Show nearby section markers
            print(f"\n  Section markers near EBOOT (within +/- 0x10000):")
            for sec_offset, sec_name in markers:
                if abs(sec_offset - match_offset) < 0x10000:
                    rel = sec_offset - match_offset
                    print(f"    0x{sec_offset:08X} ({rel:+d}): {sec_name}")

            # Show nearby section markers relative to the implied RAM start
            print(f"\n  Section markers near implied RAM start (within +/- 0x1000):")
            for sec_offset, sec_name in markers:
                if abs(sec_offset - ram_start) < 0x1000:
                    rel = sec_offset - ram_start
                    print(f"    0x{sec_offset:08X} ({rel:+d}): {sec_name}")

            # Print hex context around the EBOOT match
            print_context(state_data, match_offset, window=64, label="EBOOT header")

            # Also show what's just before RAM start (section header?)
            if ram_start > 0:
                print_context(state_data, ram_start, window=64, label="implied RAM start")
    else:
        print("ERROR: Could not find EBOOT header in decompressed state data!")
        print("The EBOOT may be encrypted or the state format differs from expected.")

    # Step 5: Search for string patterns
    print("\n--- Step 5: Searching for known string patterns ---")
    search_strings = ["Nothing", "Rathalos"]
    string_results = find_string_patterns(state_data, search_strings)

    for pattern, offsets in string_results.items():
        print(f"\n  Pattern '{pattern}': found {len(offsets)} occurrence(s)")
        for i, offset in enumerate(offsets):
            if i >= 20:
                print(f"    ... and {len(offsets) - 20} more")
                break
            # If we know the RAM start, calculate PSP address
            psp_addr_str = ""
            if eboot_matches:
                ram_start = eboot_matches[0] - EBOOT_OFFSET_IN_RAM
                if ram_start <= offset < ram_start + PSP_USER_RAM_SIZE:
                    psp_addr = PSP_USER_RAM_START + (offset - ram_start)
                    psp_addr_str = f"  -> PSP addr: 0x{psp_addr:08X}"
            print(f"    0x{offset:08X}{psp_addr_str}")
            print_context(state_data, offset, window=32, label=pattern)

    # Summary
    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    if eboot_matches:
        ram_start = eboot_matches[0] - EBOOT_OFFSET_IN_RAM
        print(f"  PSP RAM (0x{PSP_USER_RAM_START:08X}) starts at state offset: 0x{ram_start:08X}")
        print(f"  EBOOT (0x{PSP_EBOOT_LOAD_ADDR:08X}) found at state offset:   0x{eboot_matches[0]:08X}")
        print(f"  To convert state offset -> PSP address:")
        print(f"    psp_addr = state_offset - 0x{ram_start:X} + 0x{PSP_USER_RAM_START:08X}")
        print(f"  To convert PSP address -> state offset:")
        print(f"    state_offset = psp_addr - 0x{PSP_USER_RAM_START:08X} + 0x{ram_start:X}")
    else:
        print("  Could not determine RAM offset.")


if __name__ == '__main__':
    main()

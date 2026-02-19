#!/opt/homebrew/bin/python3
"""Determine the RAM base offset in the PPSSPP save state.

Strategy: Find a known constant in the decompressed state that we can
map to a known PSP address. The EBOOT's entry point or the armor data
table header are good candidates.
"""

import struct
import zstandard

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
EBOOT_PATH = "/Users/Exceen/Downloads/mhfu_transmog/EBOOT.BIN"


def decompress_state(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    dctx = zstandard.ZstdDecompressor()
    return dctx.decompress(data[0xB0:], max_output_size=128 * 1024 * 1024)


def main():
    print("=== Loading data ===")
    data = decompress_state(f"{STATE_DIR}/ULJM05500_1.01_0.ppst")
    print(f"State size: {len(data)} bytes ({len(data)/1024/1024:.1f} MB)")

    # Read EBOOT
    with open(EBOOT_PATH, 'rb') as f:
        eboot = f.read()
    print(f"EBOOT size: {len(eboot)} bytes")

    # Parse ELF header to find segments
    # ELF header: e_phoff at offset 0x1C (32-bit), e_phentsize at 0x2A, e_phnum at 0x2C
    e_phoff = struct.unpack_from('<I', eboot, 0x1C)[0]
    e_phentsize = struct.unpack_from('<H', eboot, 0x2A)[0]
    e_phnum = struct.unpack_from('<H', eboot, 0x2C)[0]
    e_entry = struct.unpack_from('<I', eboot, 0x18)[0]
    print(f"\nELF: entry=0x{e_entry:08X}, phoff=0x{e_phoff:X}, phnum={e_phnum}, phentsize={e_phentsize}")

    for i in range(e_phnum):
        ph_offset = e_phoff + i * e_phentsize
        p_type = struct.unpack_from('<I', eboot, ph_offset)[0]
        p_offset = struct.unpack_from('<I', eboot, ph_offset + 4)[0]
        p_vaddr = struct.unpack_from('<I', eboot, ph_offset + 8)[0]
        p_paddr = struct.unpack_from('<I', eboot, ph_offset + 12)[0]
        p_filesz = struct.unpack_from('<I', eboot, ph_offset + 16)[0]
        p_memsz = struct.unpack_from('<I', eboot, ph_offset + 20)[0]
        print(f"  Segment {i}: type={p_type}, offset=0x{p_offset:X}, vaddr=0x{p_vaddr:08X}, "
              f"filesz=0x{p_filesz:X}, memsz=0x{p_memsz:X}")

    # The PSP loads the first LOAD segment at its vaddr
    # Take a distinctive chunk from the middle of the EBOOT and search for it
    # Using a 32-byte chunk from offset 0x1000 into the first LOAD segment
    for test_offset in [0x1000, 0x2000, 0x5000, 0x10000, 0x20000]:
        if test_offset + 32 > len(eboot):
            continue
        pattern = eboot[test_offset:test_offset + 32]
        # Skip if pattern is all zeros or all same bytes
        if len(set(pattern)) < 8:
            continue

        pos = data.find(pattern)
        if pos != -1:
            # The pattern from eboot offset test_offset should be at PSP vaddr + test_offset
            # (assuming first segment offset is 0 and loads at its vaddr)
            # Actually, need to account for segment's file offset vs vaddr
            # For PSP, typically the first segment has offset=0 and vaddr=0x08804000
            # So eboot byte at file offset X maps to PSP address vaddr + (X - p_offset)

            # Parse first LOAD segment
            ph0_offset = e_phoff
            p0_offset = struct.unpack_from('<I', eboot, ph0_offset + 4)[0]
            p0_vaddr = struct.unpack_from('<I', eboot, ph0_offset + 8)[0]

            psp_addr = p0_vaddr + (test_offset - p0_offset)
            ram_base_in_state = pos - (psp_addr - 0x08000000)

            print(f"\n  EBOOT offset 0x{test_offset:X} found in state at 0x{pos:08X}")
            print(f"  PSP vaddr of this data: 0x{psp_addr:08X}")
            print(f"  Implied RAM base (0x08000000) in state at offset: 0x{ram_base_in_state:08X}")
            print(f"  Implied user RAM (0x08800000) in state at offset: 0x{ram_base_in_state + 0x800000:08X}")

            # Verify: check the model index array
            model_state_offset = 0x010AF702
            model_psp_addr = 0x08000000 + (model_state_offset - ram_base_in_state)
            print(f"\n  Model index array at state 0x{model_state_offset:08X}")
            print(f"  -> PSP address: 0x{model_psp_addr:08X}")
            print(f"  -> User RAM offset: 0x{model_psp_addr - 0x08800000:08X}")

            fileid_state_offset = 0x0112F594
            fileid_psp_addr = 0x08000000 + (fileid_state_offset - ram_base_in_state)
            print(f"\n  File ID array at state 0x{fileid_state_offset:08X}")
            print(f"  -> PSP address: 0x{fileid_psp_addr:08X}")
            print(f"  -> User RAM offset: 0x{fileid_psp_addr - 0x08800000:08X}")

            break
        else:
            print(f"  Pattern at EBOOT offset 0x{test_offset:X} not found")

    # Alternative approach: look at the "Memory" section header
    # The first "Memory" marker is at 0x28
    print("\n=== Examining Memory section header ===")
    # Show bytes around offset 0x28
    hex_data = ' '.join(f'{b:02X}' for b in data[0x20:0x60])
    print(f"  0x20-0x5F: {hex_data}")

    # PPSSPP CChunkFileReader format:
    # Section header: string title + int version + int size
    # Then data follows
    # "Memory" is at 0x28, preceded by a length byte
    # Let's look at the structure:
    # At 0x28: "Memory" (6 bytes) + null
    # Before 0x28: likely a 4-byte section length or string length

    # Check what's right after "Memory\0"
    mem_section_end = data.find(b'\x00', 0x28) + 1
    print(f"  'Memory' string ends at 0x{mem_section_end:X}")
    post_mem = data[mem_section_end:mem_section_end + 16]
    print(f"  After 'Memory\\0': {' '.join(f'{b:02X}' for b in post_mem)}")
    # Parse as potential version + size
    if mem_section_end + 8 <= len(data):
        version = struct.unpack_from('<I', data, mem_section_end)[0]
        size = struct.unpack_from('<I', data, mem_section_end + 4)[0]
        print(f"  Possible version: {version}, size: {size} (0x{size:X})")
        if 0x01000000 < size < 0x04000000:
            print(f"  Size looks like RAM size: {size / 1024 / 1024:.1f} MB")
            print(f"  RAM data would start at 0x{mem_section_end + 8:X}")
            print(f"  RAM data would end at 0x{mem_section_end + 8 + size:X}")
            ram_start = mem_section_end + 8
            # Verify with known values
            print(f"\n  With RAM base at state offset 0x{ram_start:X}:")
            model_addr = 0x08000000 + (0x010AF702 - ram_start)
            fileid_addr = 0x08000000 + (0x0112F594 - ram_start)
            print(f"  Model array PSP addr: 0x{model_addr:08X} (user offset: 0x{model_addr - 0x08800000:X})")
            print(f"  FileID array PSP addr: 0x{fileid_addr:08X} (user offset: 0x{fileid_addr - 0x08800000:X})")

    # Try another approach: search for the PPSSPP section format
    # Sections typically start with a 4-byte string length, then string, then version, then data size
    print("\n=== Examining start of decompressed data ===")
    for offset in [0, 0x10, 0x20]:
        block = data[offset:offset + 48]
        hex_str = ' '.join(f'{b:02X}' for b in block)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in block)
        print(f"  0x{offset:02X}: {hex_str}")
        print(f"        {ascii_str}")


if __name__ == '__main__':
    main()

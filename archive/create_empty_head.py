#!/usr/bin/env python3
"""Create a minimal empty head armor .pac file with no visible geometry.

Based on the PMO 1.0 format used in MHFU. The idea is to create a valid
PAC container with a PMO model that has zero mesh data, so the game engine
renders nothing for the head slot and the face model's hairstyle shows through.
"""

import struct
import sys
import os


def create_empty_pmo():
    """Create a minimal PMO with no mesh sections."""
    # PMO header is 0x40 bytes (64 bytes)
    header = bytearray(0x40)

    # Magic and version
    header[0x00:0x04] = b'pmo\x00'
    header[0x04:0x08] = b'1.0\x00'

    # Texture/data section offset (points past all data = just the header)
    struct.pack_into('<I', header, 0x08, 0x40)

    # Bounding box (small box at origin)
    struct.pack_into('<f', header, 0x0C, 0.0)  # min X
    struct.pack_into('<f', header, 0x10, 0.0)  # min Y
    struct.pack_into('<f', header, 0x14, 0.0)  # max X
    struct.pack_into('<f', header, 0x18, 0.0)  # max Y

    # Bone count = 0, mesh set count = 0
    struct.pack_into('<H', header, 0x1C, 0)
    struct.pack_into('<H', header, 0x1E, 0)

    # All section offsets point to end of header (no data)
    for off in (0x20, 0x24, 0x28, 0x2C, 0x30, 0x34):
        struct.pack_into('<I', header, off, 0x40)

    # Scale factors
    struct.pack_into('<f', header, 0x40 - 8, 1.0)
    struct.pack_into('<f', header, 0x40 - 4, 1.0)

    return bytes(header)


def create_empty_pac(pmo_data):
    """Wrap PMO data in a PAC container with 1 section."""
    # PAC header: count + offset + padding to 0x20
    header = bytearray(0x20)

    # 1 section
    struct.pack_into('<I', header, 0x00, 1)
    # Section 0 starts at offset 0x20
    struct.pack_into('<I', header, 0x04, 0x20)
    # Section 0 size
    struct.pack_into('<I', header, 0x08, len(pmo_data))

    return bytes(header) + pmo_data


def main():
    output = sys.argv[1] if len(sys.argv) > 1 else 'empty_head.pac'

    pmo = create_empty_pmo()
    pac = create_empty_pac(pmo)

    with open(output, 'wb') as f:
        f.write(pac)

    print(f"Created {output} ({len(pac)} bytes)")
    print(f"  PAC header: 32 bytes")
    print(f"  PMO data: {len(pmo)} bytes (0 bones, 0 meshes)")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Generate NATIVEPSP folder for FUComplete File Replacer.

Reads .pac files from the mods/ folder, maps them to file IDs,
and generates the NATIVEPSP/ folder with FILE.BIN and renamed files.
"""

import os
import struct

# Mapping of filename prefixes to DATA.BIN base file IDs
# prefix -> (female_base_id, male_base_id)
PREFIX_MAP = {
    'f_hair': 406,    # Female head (f_hair000.pac = ID 406)
    'm_hair': 2059,   # Male head   (m_hair000.pac = ID 2059)
    'f_body': 746,    # Female body (f_body000.pac = ID 746)
    'm_body': 2400,   # Male body   (m_body000.pac = ID 2400)
    'f_arm':  1086,   # Female arm  (f_arm000.pac  = ID 1086)
    'm_arm':  2742,   # Male arm    (m_arm000.pac  = ID 2742)
    'f_wst':  1419,   # Female waist(f_wst000.pac  = ID 1419)
    'm_wst':  3080,   # Male waist  (m_wst000.pac  = ID 3080)
    'f_reg':  62,     # Female leg  (f_reg000.pac  = ID 62)
    'm_reg':  1715,   # Male leg    (m_reg000.pac  = ID 1715)
    'we':     3388,   # Weapons     (we000.pac     = ID 3388)
}

def filename_to_id(filename):
    """Map a .pac filename to its DATA.BIN file ID."""
    name = filename.lower()
    if not name.endswith('.pac'):
        return None

    for prefix, base in PREFIX_MAP.items():
        if name.startswith(prefix):
            try:
                num = int(name[len(prefix):-4])
                return base + num
            except ValueError:
                return None

    return None


def generate_filebin(file_ids):
    """Generate the 826-byte FILE.BIN bitmap."""
    data = bytearray(826)
    for fid in file_ids:
        block = fid // 8
        offset = fid % 8
        # Bit ordering is reversed within each byte
        data[block] |= (1 << (7 - offset))
    return bytes(data)


def generate_nativepsp(mods_dir, output_dir):
    """Generate NATIVEPSP folder from mods directory."""
    os.makedirs(output_dir, exist_ok=True)

    entries = []
    for fname in sorted(os.listdir(mods_dir)):
        fpath = os.path.join(mods_dir, fname)
        if not os.path.isfile(fpath):
            continue

        fid = filename_to_id(fname)
        if fid is None:
            print(f"  SKIP: {fname} (unknown filename)")
            continue

        with open(fpath, 'rb') as f:
            file_data = f.read()

        # Prepend 4-byte little-endian size header
        size_header = struct.pack('<I', len(file_data))
        out_path = os.path.join(output_dir, str(fid))
        with open(out_path, 'wb') as f:
            f.write(size_header + file_data)

        entries.append((fname, fid, len(file_data)))
        print(f"  OK: {fname} -> {fid} ({len(file_data)} bytes)")

    # Generate FILE.BIN
    file_ids = [e[1] for e in entries]
    filebin = generate_filebin(file_ids)
    with open(os.path.join(output_dir, 'FILE.BIN'), 'wb') as f:
        f.write(filebin)

    print(f"\nGenerated NATIVEPSP with {len(entries)} file(s) + FILE.BIN")
    return entries


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mods_dir = os.path.join(script_dir, 'mods')
    output_dir = os.path.join(script_dir, 'NATIVEPSP')

    print(f"Mods folder: {mods_dir}")
    print(f"Output:      {output_dir}\n")
    generate_nativepsp(mods_dir, output_dir)

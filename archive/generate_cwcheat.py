#!/opt/homebrew/bin/python3
"""Generate CWCheat codes for MHFU armor transmog.

Writes to the model index and file ID arrays in PSP memory to change
the visual appearance of equipped armor while keeping stats.

Memory layout (PSP addresses, packed 16-bit arrays):
  Model indices:       File IDs:
  0x090AF6B6 = leg     0x0912F548 = leg
  0x090AF6BA = head    0x0912F54C = head
  0x090AF6BC = body    0x0912F54E = body
  0x090AF6BE = arm     0x0912F550 = arm
  0x090AF6C0 = waist   0x0912F552 = waist

CWCheat type 1 = 16-bit constant write
CWCheat address = PSP address - 0x08800000
"""

import sys

# PSP addresses for the currently displayed model indices
MODEL_ADDRS = {
    'leg':   0x090AF6B6,
    'head':  0x090AF6BA,
    'body':  0x090AF6BC,
    'arm':   0x090AF6BE,
    'waist': 0x090AF6C0,
}

# PSP addresses for the currently loaded file IDs
FILEID_ADDRS = {
    'leg':   0x0912F548,
    'head':  0x0912F54C,
    'body':  0x0912F54E,
    'arm':   0x0912F550,
    'waist': 0x0912F552,
}

# Base file IDs for each prefix (file_id = base + model_number)
FILE_ID_BASES = {
    'head':  406,   # f_hair
    'body':  746,   # f_body
    'arm':   1086,  # f_arm
    'waist': 1419,  # f_wst
    'leg':   62,    # f_reg
}

# Prefix names for display
PREFIXES = {
    'head':  'f_hair',
    'body':  'f_body',
    'arm':   'f_arm',
    'waist': 'f_wst',
    'leg':   'f_reg',
}

PSP_BASE = 0x08800000


def cwcheat_addr(psp_addr):
    """Convert PSP address to CWCheat address (type 1 = 16-bit write)."""
    offset = psp_addr - PSP_BASE
    return 0x10000000 | offset


def generate_cwcheat(name, visual_armor):
    """Generate CWCheat code for a transmog.

    visual_armor: dict mapping slot ('head','body','arm','waist','leg')
                  to model number (the ### from f_hair###, f_body### etc.)
    """
    lines = []
    lines.append(f"_C0 Transmog: {name}")

    for slot in ['head', 'body', 'arm', 'waist', 'leg']:
        if slot not in visual_armor:
            continue
        model_num = visual_armor[slot]
        file_id = FILE_ID_BASES[slot] + model_num
        prefix = PREFIXES[slot]

        # Write model index
        addr = cwcheat_addr(MODEL_ADDRS[slot])
        lines.append(f"_L 0x{addr:08X} 0x0000{model_num:04X}")

        # Write file ID
        addr2 = cwcheat_addr(FILEID_ADDRS[slot])
        lines.append(f"_L 0x{addr2:08X} 0x0000{file_id:04X}")

    return '\n'.join(lines)


def main():
    print("=== MHFU Transmog CWCheat Generator ===\n")

    # Game header
    header = "_S ULJM-05500\n_G Monster Hunter Portable 2nd G FUComplete"

    # Example: Black Set transmog (visual) over any equipped armor
    black_set = {
        'head':  47,  # f_hair047
        'body':  47,  # f_body047
        'arm':   46,  # f_arm046
        'waist': 36,  # f_wst036
        'leg':   34,  # f_reg034
    }

    # Example: Fatalis Set
    fatalis_set = {
        'head':  0,   # f_hair000
        'body':  61,  # f_body061
        'arm':   59,  # f_arm059
        'waist': 50,  # f_wst050
        'leg':   46,  # f_reg046
    }

    # Example: Head-only invisible (using model 0 = default appearance)
    invisible_head = {
        'head':  0,   # f_hair000 (default hairstyle - may not match selected hairstyle)
    }

    # Rathalos Soul Cap set (as a reference/test)
    rathalos_soul = {
        'head':  96,  # f_hair096
        'body':  90,  # f_body090
        'arm':   88,  # f_arm088
        'waist': 76,  # f_wst076
        'leg':   66,  # f_reg066
    }

    cheats = [
        ("Black Set", black_set),
        ("Fatalis Set", fatalis_set),
        ("Rathalos Soul Set", rathalos_soul),
        ("Invisible Head (default)", invisible_head),
    ]

    output_lines = [header, ""]

    for name, armor in cheats:
        cheat = generate_cwcheat(name, armor)
        output_lines.append(cheat)
        output_lines.append("")

    cheat_text = '\n'.join(output_lines)
    print(cheat_text)

    # Write to file
    cheat_file = "/Users/Exceen/Downloads/mhfu_transmog/cheat.db"
    with open(cheat_file, 'w') as f:
        f.write(cheat_text + '\n')
    print(f"\nSaved to {cheat_file}")

    # Print address reference
    print("\n=== Address Reference ===")
    print("Model Index Array (16-bit values):")
    for slot in ['head', 'body', 'arm', 'waist', 'leg']:
        addr = MODEL_ADDRS[slot]
        cw = cwcheat_addr(addr)
        print(f"  {slot:6s}: PSP 0x{addr:08X} -> CWCheat 0x{cw:08X}")

    print("\nFile ID Array (16-bit values):")
    for slot in ['head', 'body', 'arm', 'waist', 'leg']:
        addr = FILEID_ADDRS[slot]
        cw = cwcheat_addr(addr)
        print(f"  {slot:6s}: PSP 0x{addr:08X} -> CWCheat 0x{cw:08X}")

    print("\nFile ID calculation: file_id = base + model_number")
    for slot in ['head', 'body', 'arm', 'waist', 'leg']:
        base = FILE_ID_BASES[slot]
        prefix = PREFIXES[slot]
        print(f"  {slot:6s}: {prefix}### -> file_id = {base} + ###")

    print("\n=== How to use ===")
    print("1. Place cheat.db in your PPSSPP cheats folder or CWCheat folder")
    print("   PPSSPP: PSP/Cheats/ULJM05500.ini (copy the cheat lines)")
    print("2. Enable cheats in PPSSPP settings")
    print("3. Equip the armor with stats you want")
    print("4. Enable the transmog cheat to change visuals")
    print("\nNote: Model number = the ### from the filename (e.g., f_hair096 = 96)")
    print("      For piercings/invisible head: needs further testing")


if __name__ == '__main__':
    main()

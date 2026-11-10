#!/usr/bin/env python3
"""Assemble the In-Game Transmog Picker cheat and write ../ingame_codes.json (read by the website)
and transmog_codes.txt (PPSSPP and real PSP format, for copying by hand).

Requires armips (https://github.com/Kingcom/armips) on PATH. Only needed when the assembly
changes; both outputs are committed.

Usage: python3 ingame/build.py
"""
import json
import struct
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "transmog_codes.txt"
JSON_OUTPUT = HERE.parent / "ingame_codes.json"
TITLE = "In-Game Transmog Picker"
VERSION = "3.0"
PSP_MAX_LINES = 30  # real PSP CWCheat: max lines per cheat, title line included
CWCHEAT_BASE = 0x08800000
CAVE = 0x09FF9100
DATA = 0x09FF9800  # run-time data behind the code, not written by the cheat
NRULES = 127  # keep equal to NRULES in transmog.asm
DATA_END = 0x09FFA000  # another community code starts here
# address patched by each word of transmog_hooks.bin, in order
HOOK_ADDRS = [0x08868F5C, 0x0883062C, 0x08830630]


def cw(addr, value):
    return f"_L 0x2{addr - CWCHEAT_BASE:07X} 0x{value:08X}"


def words(path):
    data = path.read_bytes()
    assert len(data) % 4 == 0, path
    return struct.unpack(f"<{len(data) // 4}I", data)


def main():
    (HERE / "bin").mkdir(exist_ok=True)
    subprocess.run(["armips", "transmog.asm"], cwd=HERE, check=True)
    cave = words(HERE / "bin" / "transmog.bin")
    hooks = words(HERE / "bin" / "transmog_hooks.bin")
    assert len(hooks) == len(HOOK_ADDRS)
    assert CAVE + len(cave) * 4 <= DATA, "code runs into its data"
    assert DATA + 12 + NRULES * 16 + 4 <= DATA_END, "data runs into the next code"

    # Hooks go last: when the lines run in order, the code they jump to already exists.
    lines = [cw(CAVE + i * 4, w) for i, w in enumerate(cave)]
    lines += [cw(a, w) for a, w in zip(HOOK_ADDRS, hooks)]
    title = f"{TITLE} v{VERSION}"
    per = PSP_MAX_LINES - 1
    parts = -(-len(lines) // per)
    psp = "\n\n".join(f"_C0 {title} {p + 1}/{parts}\n" + "\n".join(lines[p * per:(p + 1) * per])
                       for p in range(parts))
    OUTPUT.write_text(
        f"{title} (MHFU ULJM05500, FUComplete v1.4.0)\n"
        "Item box -> Arrange Items -> Equipment: pick up the piece whose look you want (Circle), move to\n"
        "the piece that should get it and press Square. Square on the picked-up piece itself resets it.\n"
        "See ingame/README.md.\n\n"
        "## PPSSPP\n\n"
        f"_C0 {title}\n" + "\n".join(lines) + "\n\n"
        f"## Real PSP (CWCheat: max {PSP_MAX_LINES} lines per cheat, enable ALL parts)\n\n"
        + psp + "\n"
    )
    end = DATA_END - 1  # code and its run-time data
    JSON_OUTPUT.write_text(json.dumps({"game": "ULJM05500", "cheat": {
        "title": title,
        "version": VERSION,
        "cave": [f"0x{CAVE:08X}", f"0x{end:08X}"],
        "lines": lines,
    }}, indent=2) + "\n")
    print(f"{title}: cave 0x{CAVE:08X}-0x{CAVE + len(cave) * 4 - 1:08X}, {len(lines)} lines, "
          f"{parts} PSP parts, wrote {OUTPUT.name} and {JSON_OUTPUT.name}")


if __name__ == "__main__":
    main()

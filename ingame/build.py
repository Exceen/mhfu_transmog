#!/usr/bin/env python3
"""Assemble the In-Game Transmog Picker and its Per-Set Transmog add-on, and write
../ingame_codes.json (read by the website) and transmog_codes.txt (PPSSPP and real PSP format,
for copying by hand).

Requires armips (https://github.com/Kingcom/armips) on PATH. Only needed when the assembly
changes; both outputs are committed.

Usage: python3 ingame/build.py
"""
import json
import re
import struct
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIN = HERE / "bin"
OUTPUT = HERE / "transmog_codes.txt"
JSON_OUTPUT = HERE.parent / "ingame_codes.json"
VERSION = "3.2"
PSP_MAX_LINES = 30  # real PSP CWCheat: max lines per cheat, title line included
CWCHEAT_BASE = 0x08800000

PICKER = {
    "id": "picker",
    "title": "In-Game Transmog Picker",
    "src": "transmog.asm",
    "bin": "transmog.bin",
    "hooks_bin": "transmog_hooks.bin",
    "cave": 0x09FF9100,
    "code_end": 0x09FF9800,  # keep the code below this (main thread stack, see transmog.asm)
    "data": 0x09FE2000,      # run-time data, not written by the cheat (sound thread stack)
    "data_end": 0x09FE2C00,  # the Per-Set data starts here
    "hook_addrs": [0x08868F5C, 0x0883062C, 0x08830630],
}
NRULES = 127  # keep equal to NRULES in transmog.asm

SETS = {
    "id": "sets",
    "title": "Per-Set Transmog",
    "src": "sets.asm",
    "bin": "sets.bin",
    "hooks_bin": "sets_hooks.bin",
    "cave": 0x09FF8880,      # the game writes to 0x09FF8878, see sets.asm
    "code_end": 0x09FF8FFF,  # another community code starts here
    "data": 0x09FE2C00,
    "data_end": 0x09FE3400,
    "hook_addrs": [0x0888368C, 0x08883690, 0x088507AC, 0x088507B0],
}
SETS_DATA_SIZE = 0x48 + 20 * 6 * 8  # keep equal to the layout in sets.asm

# Picker labels the add-on calls; build.py passes their addresses to sets.asm.
PICKER_EXPORTS = ["find_rule", "find_word", "entry_addr", "put3", "save_file"]


def cw(addr, value):
    return f"_L 0x2{addr - CWCHEAT_BASE:07X} 0x{value:08X}"


def words(path):
    data = path.read_bytes()
    assert len(data) % 4 == 0, path
    return struct.unpack(f"<{len(data) // 4}I", data)


def assemble(c, sym=None):
    cmd = ["armips", c["src"]] + (["-sym", f"bin/{sym}"] if sym else [])
    subprocess.run(cmd, cwd=HERE, check=True)
    cave = words(BIN / c["bin"])
    hooks = words(BIN / c["hooks_bin"])
    assert len(hooks) == len(c["hook_addrs"]), c["id"]
    assert c["cave"] + len(cave) * 4 <= c["code_end"], f"{c['id']}: code too long for its place"
    # Hooks go last: when the lines run in order, the code they jump to already exists.
    lines = [cw(c["cave"] + i * 4, w) for i, w in enumerate(cave)]
    lines += [cw(a, w) for a, w in zip(c["hook_addrs"], hooks)]
    title = f"{c['title']} v{VERSION}"
    print(f"{title}: code 0x{c['cave']:08X}-0x{c['cave'] + len(cave) * 4 - 1:08X}, "
          f"{len(lines)} lines, {-(-len(lines) // (PSP_MAX_LINES - 1))} PSP parts")
    return {
        "title": title,
        "version": VERSION,
        "cave": [f"0x{c['cave']:08X}", f"0x{c['cave'] + len(cave) * 4 - 1:08X}"],
        "data": [f"0x{c['data']:08X}", f"0x{c['data_end'] - 1:08X}"],
        "lines": lines,
    }


def picker_exports():
    """Write bin/picker_syms.inc from the picker's symbol file and source."""
    syms = {}
    for line in (BIN / "transmog.sym").read_text().splitlines():
        parts = line.split()
        if len(parts) == 2:
            syms[parts[1]] = int(parts[0], 16)
    src = (HERE / "transmog.asm").read_text()
    magic = re.search(r"^RUN_MAGIC\s+equ\s+(0x[0-9A-Fa-f]+)", src, re.M).group(1)
    out = [f"{name:<20} equ 0x{syms[name]:08X}" for name in PICKER_EXPORTS]
    out += [f"{'PICKER_DATA':<20} equ 0x{PICKER['data']:08X}", f"{'PICKER_RUN_MAGIC':<20} equ {magic}"]
    (BIN / "picker_syms.inc").write_text("; written by build.py\n" + "\n".join(out) + "\n")


def psp_parts(cheat):
    per = PSP_MAX_LINES - 1
    lines = cheat["lines"]
    parts = -(-len(lines) // per)
    return "\n\n".join(f"_C0 {cheat['title']} {p + 1}/{parts}\n" + "\n".join(lines[p * per:(p + 1) * per])
                       for p in range(parts))


def main():
    BIN.mkdir(exist_ok=True)
    assert PICKER["data"] + 12 + NRULES * 16 + 4 <= PICKER["data_end"], "picker data runs into the next code"
    assert SETS["data"] + SETS_DATA_SIZE <= SETS["data_end"], "set data runs into the next code"
    picker = assemble(PICKER, sym="transmog.sym")
    picker_exports()
    sets = assemble(SETS)

    JSON_OUTPUT.write_text(json.dumps({"game": "ULJM05500", "cheats": {
        "picker": picker,
        "sets": sets,
    }}, indent=2) + "\n")
    OUTPUT.write_text(
        f"{picker['title']} + {sets['title']} (MHFU ULJM05500, FUComplete v1.4.0)\n"
        "Picker: item box -> Arrange Items -> Equipment: pick up the piece whose look you want (Circle),\n"
        "move to the piece that should get it and press Square. Square on the picked-up piece resets it.\n"
        "Per-Set (optional, needs the picker): every equipment set remembers the looks its pieces had\n"
        "when it was registered and puts them back when you equip it. See ingame/README.md.\n\n"
        "## PPSSPP\n\n"
        f"_C0 {picker['title']}\n" + "\n".join(picker["lines"]) + "\n\n"
        f"_C0 {sets['title']}\n" + "\n".join(sets["lines"]) + "\n\n"
        f"## Real PSP (CWCheat: max {PSP_MAX_LINES} lines per cheat, enable ALL parts)\n\n"
        + psp_parts(picker) + "\n\n" + psp_parts(sets) + "\n"
    )
    print(f"wrote {OUTPUT.name} and {JSON_OUTPUT.name}")


if __name__ == "__main__":
    main()

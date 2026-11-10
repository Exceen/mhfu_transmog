#!/usr/bin/env python3
"""Assemble the bonus Item Sets cheat and write item_sets.txt (PPSSPP and real PSP format).

Not part of the website. Requires armips (https://github.com/Kingcom/armips) on PATH.

Usage: python3 bonus/build.py
"""
import re
import struct
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIN = HERE / "bin"
OUTPUT = HERE / "item_sets.txt"
TITLE = "Item Sets v1.0"
PSP_MAX_LINES = 30  # real PSP CWCheat: max lines per cheat, title line included
CWCHEAT_BASE = 0x08800000
CAVE = 0x09FFA080
DATA_LIMIT = 0x09FFA800  # keep the code and its run-time data below this
HOOK_ADDRS = [0x0881CE38, 0x0881CE3C]


def cw(addr, value):
    return f"_L 0x2{addr - CWCHEAT_BASE:07X} 0x{value:08X}"


def words(path):
    data = path.read_bytes()
    return struct.unpack(f"<{len(data) // 4}I", data)


def main():
    BIN.mkdir(exist_ok=True)
    subprocess.run(["armips", "item_sets.asm", "-sym", "bin/item_sets.sym"], cwd=HERE, check=True)
    cave = words(BIN / "item_sets.bin")
    hooks = words(BIN / "item_sets_hooks.bin")
    assert len(hooks) == len(HOOK_ADDRS)
    data_end = CAVE + len(cave) * 4 + 4 + 2 * 24 * 4
    assert data_end <= DATA_LIMIT, "data runs past the limit"

    lines = [cw(CAVE + i * 4, w) for i, w in enumerate(cave)]
    lines += [cw(a, w) for a, w in zip(HOOK_ADDRS, hooks)]  # hooks last
    per = PSP_MAX_LINES - 1
    parts = -(-len(lines) // per)
    psp = "\n\n".join(f"_C0 {TITLE} {p + 1}/{parts}\n" + "\n".join(lines[p * per:(p + 1) * per])
                      for p in range(parts))
    OUTPUT.write_text(
        f"{TITLE} (MHFU ULJM05500, FUComplete v1.4.0) - port of Kurogami2134's MHP3rd item sets\n"
        "\n"
        "Item box, main menu (Put In Item / Take Out Item / ...):\n"
        "  L / R            load item set 1 / 2: your pouch goes back into the box, then the set's\n"
        "                   items are taken out of the box (as many as the box has)\n"
        "  Select + L / R   save your current pouch as item set 1 / 2\n"
        "Sounds: save = menu open, load = confirm, empty set = error.\n"
        "Nothing is lost: an item that doesn't fit back into a full box stays in the pouch.\n"
        "Sets are saved in PSP/SAVEDATA/MHFU_ITEM_SETS.BIN (shared by all characters).\n"
        f"Memory: 0x{CAVE:08X}-0x{data_end - 1:08X} (code and data). Source: bonus/item_sets.asm\n"
        "\n"
        "## PPSSPP\n\n"
        f"_C0 {TITLE}\n" + "\n".join(lines) + "\n\n"
        f"## Real PSP (CWCheat: max {PSP_MAX_LINES} lines per cheat, enable ALL parts)\n\n"
        + psp + "\n"
    )
    print(f"{TITLE}: 0x{CAVE:08X}-0x{data_end - 1:08X}, {len(lines)} lines, {parts} PSP parts, wrote {OUTPUT.name}")


if __name__ == "__main__":
    main()

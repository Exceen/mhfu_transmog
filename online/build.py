#!/usr/bin/env python3
"""Assemble the online transmog cheats and write ../online_codes.json.

Requires armips (https://github.com/Kingcom/armips) on PATH. Only needed when the
assembly changes; online_codes.json is committed, and the website reads it.

Usage: python3 online/build.py
"""
import json
import struct
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parent / "online_codes.json"
CWCHEAT_BASE = 0x08800000

CHEATS = [
    {
        "id": "armor",
        "title": "Multiplayer Armor Transmog",
        "version": "2.1",
        "src": "armor.asm",
        "bin": "armor.bin",
        "hooks_bin": "armor_hooks.bin",
        "cave": 0x09FF0400,
        # address patched by each word of hooks_bin, in order
        "hook_addrs": [0x08852B44, 0x088517A8, 0x088517AC, 0x08851D64],
    },
    {
        "id": "weapon",
        "title": "Multiplayer Weapon Transmog",
        "version": "2.1",
        "src": "weapon.asm",
        "bin": "weapon.bin",
        "hooks_bin": "weapon_hooks.bin",
        "cave": 0x09FF0600,
        "hook_addrs": [0x08852B3C, 0x08852B40, 0x08851E4C, 0x08851E50],
    },
]


def cw(addr, value):
    return f"_L 0x2{addr - CWCHEAT_BASE:07X} 0x{value:08X}"


def words(path):
    data = path.read_bytes()
    return struct.unpack(f"<{len(data) // 4}I", data)


def build(c):
    subprocess.run(["armips", c["src"]], cwd=HERE, check=True)
    cave = words(HERE / "bin" / c["bin"])
    hooks = words(HERE / "bin" / c["hooks_bin"])
    assert len(hooks) == len(c["hook_addrs"]), c["id"]

    # Hooks go last: when the cheat lines run in order, the code they jump to already exists.
    # The PSP split keeps this order, so the hooks always end up in the last part.
    lines = [cw(c["cave"] + i * 4, w) for i, w in enumerate(cave)]
    lines += [cw(a, w) for a, w in zip(c["hook_addrs"], hooks)]
    end = c["cave"] + len(cave) * 4 - 1
    print(f"{c['title']} v{c['version']}: cave 0x{c['cave']:08X}-0x{end:08X}, {len(lines)} lines")
    return {
        "title": f"{c['title']} v{c['version']}",
        "version": c["version"],
        "cave": [f"0x{c['cave']:08X}", f"0x{end:08X}"],
        "lines": lines,
    }


def main():
    (HERE / "bin").mkdir(exist_ok=True)
    cheats = {c["id"]: build(c) for c in CHEATS}
    spans = sorted((int(v["cave"][0], 16), int(v["cave"][1], 16)) for v in cheats.values())
    for (_, a_end), (b_start, _) in zip(spans, spans[1:]):
        assert a_end < b_start, "code caves overlap"
    OUTPUT.write_text(json.dumps({"game": "ULJM05500", "cheats": cheats}, indent=2) + "\n")
    print(f"wrote {OUTPUT.name}")


if __name__ == "__main__":
    main()

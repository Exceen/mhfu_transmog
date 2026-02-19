#!/usr/bin/env python3
"""
Build transmog_data.json by scraping FUComplete website and reading a PPSSPP save state.

Data sources:
  1. FUComplete website: equipment names (model number -> names)
  2. PPSSPP save state: armor/weapon table entries (equip_id -> model IDs)

Output: transmog_data.json used by transmog.py
"""

import json
import os
import re
import struct
import urllib.request
from html.parser import HTMLParser

# ── Config ──────────────────────────────────────────────────────────────────

STATE_DIR = os.path.expanduser("~/Documents/PPSSPP/PSP/PPSSPP_STATE")
STATE_SLOT = 0
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transmog_data.json")

FUCOMPLETE_BASE = "https://fucomplete.github.io/files_doc/player"
WEAPON_URL = f"{FUCOMPLETE_BASE}/pl_weapons.html"
ARMOR_URLS = {
    "head":  f"{FUCOMPLETE_BASE}/pl_head.html",
    "chest": f"{FUCOMPLETE_BASE}/pl_body.html",
    "arms":  f"{FUCOMPLETE_BASE}/pl_arm.html",
    "waist": f"{FUCOMPLETE_BASE}/pl_wst.html",
    "legs":  f"{FUCOMPLETE_BASE}/pl_leg.html",
}

# PSP memory layout
PSP_RAM_START = 0x08000000
HEADER_SIZE = 0xB0
RAM_OFFSET = 0x48

# Weapon table
WEAPON_TABLE_BASE = 0x089574E8
WEAPON_ENTRY_SIZE = 24
WEAPON_MODEL_OFFSET = 16

# Armor tables (40-byte entries), ordered by address for gap calculation
ARMOR_ENTRY_SIZE = 40
ARMOR_TABLES = {
    "head":  0x08960750,
    "chest": 0x08964B70,
    "arms":  0x08968D10,
    "waist": 0x0896CD48,
    "legs":  0x08970D30,
}

# Max entries per slot (computed from gaps between table addresses)
# HEAD→CHEST: (0x08964B70 - 0x08960750) / 40 = 436
# CHEST→ARMS: (0x08968D10 - 0x08964B70) / 40 = 420
# ARMS→WAIST: (0x0896CD48 - 0x08968D10) / 40 = 411
# WAIST→LEGS: (0x08970D30 - 0x0896CD48) / 40 = 409
# LEGS: detected by all-zero entries (approx 420)
ARMOR_MAX_ENTRIES = {
    "head":  436,
    "chest": 420,
    "arms":  411,
    "waist": 409,
    "legs":  420,
}


# ── HTML Parsing ────────────────────────────────────────────────────────────

class TableParser(HTMLParser):
    """Parse FUComplete HTML tables to extract (filename, file_id, names) rows."""

    def __init__(self):
        super().__init__()
        self.tables = []
        self._in_thead = False
        self._in_tbody = False
        self._in_td = False
        self._current_row = []
        self._current_cell = ""
        self._has_thead = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._has_thead = False
        elif tag == "thead":
            self._has_thead = True
            self._in_thead = True
        elif tag == "tbody":
            if self._has_thead:
                self._in_tbody = True
                self.tables.append([])
        elif tag == "tr" and self._in_tbody:
            self._current_row = []
        elif tag == "td" and self._in_tbody:
            self._in_td = True
            self._current_cell = ""
        elif tag == "br" and self._in_td:
            self._current_cell += "|"

    def handle_endtag(self, tag):
        if tag == "thead":
            self._in_thead = False
        elif tag == "tbody":
            self._in_tbody = False
        elif tag == "td" and self._in_td:
            self._in_td = False
            self._current_row.append(self._current_cell.strip())
        elif tag == "tr" and self._in_tbody and self._current_row:
            self.tables[-1].append(self._current_row)

    def handle_data(self, data):
        if self._in_td:
            self._current_cell += data


def fetch_url(url):
    """Fetch URL content as string."""
    import ssl
    print(f"  Fetching {url}")
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx) as resp:
        return resp.read().decode("utf-8")


def parse_model_number(filename):
    """Extract model number from filename like 'we021.pac' or 'm_hair096.pac'."""
    m = re.search(r"(\d+)\.pac$", filename)
    return int(m.group(1)) if m else None


# ── FUComplete Scraping ─────────────────────────────────────────────────────

def scrape_weapons():
    """Returns {model_num: [names]}."""
    html = fetch_url(WEAPON_URL)
    parser = TableParser()
    parser.feed(html)
    if not parser.tables:
        raise RuntimeError("No tables found on weapons page")

    result = {}
    for row in parser.tables[0]:
        if len(row) < 3:
            continue
        model = parse_model_number(row[0])
        if model is None:
            continue
        names = [n.strip() for n in row[2].split("|") if n.strip()]
        names = [n for n in names if "UNUSED" not in n.upper()]
        if names:
            result[model] = names
    return result


def scrape_armor(slot):
    """Returns (male_names, female_names) dicts: {model_num: [names]}."""
    html = fetch_url(ARMOR_URLS[slot])
    parser = TableParser()
    parser.feed(html)

    if len(parser.tables) < 2:
        raise RuntimeError(f"Expected 2 tables for {slot}, found {len(parser.tables)}")

    def parse_table(rows):
        result = {}
        for row in rows:
            if len(row) < 3:
                continue
            model = parse_model_number(row[0])
            if model is None:
                continue
            names = [n.strip() for n in row[2].split("|") if n.strip()]
            names = [n for n in names if "UNUSED" not in n.upper()]
            if names:
                result[model] = names
        return result

    return parse_table(parser.tables[1]), parse_table(parser.tables[0])  # male, female


# ── Save State Reading ──────────────────────────────────────────────────────

def load_ram():
    """Load PSP RAM from save state."""
    import zstandard
    state_path = os.path.join(STATE_DIR, f"ULJM05500_1.01_{STATE_SLOT}.ppst")
    print(f"  Loading save state: {state_path}")
    with open(state_path, "rb") as f:
        raw = f.read()
    data = zstandard.ZstdDecompressor().decompress(raw[HEADER_SIZE:], max_output_size=256 * 1024 * 1024)
    ram = data[RAM_OFFSET:]
    print(f"  RAM size: {len(ram):,} bytes")
    return ram


def off(psp_addr):
    return psp_addr - PSP_RAM_START


def r_u8(ram, o):
    return ram[o]


def r_s16(ram, o):
    return struct.unpack_from("<h", ram, o)[0]


def r_u16(ram, o):
    return struct.unpack_from("<H", ram, o)[0]


# ── Extraction ──────────────────────────────────────────────────────────────

def extract_weapons(ram):
    """Returns {model_id: [entry_indices]}."""
    base = off(WEAPON_TABLE_BASE)
    by_model = {}
    for i in range(2000):
        o = base + i * WEAPON_ENTRY_SIZE
        if o + WEAPON_ENTRY_SIZE > len(ram):
            break
        model = r_u16(ram, o + WEAPON_MODEL_OFFSET)
        atk = r_u16(ram, o + 2)
        if model > 1000 or atk > 2000 or atk == 0:
            break
        by_model.setdefault(model, []).append(i)
    total = sum(len(v) for v in by_model.values())
    print(f"  Weapon table: {total} entries, {len(by_model)} unique models")
    return by_model


def extract_armor(ram, slot):
    """Returns list of (eid, model_m, model_f, flag) tuples for the given slot."""
    base = off(ARMOR_TABLES[slot])
    max_eid = ARMOR_MAX_ENTRIES[slot]
    entries = []

    for eid in range(max_eid):
        o = base + eid * ARMOR_ENTRY_SIZE
        if o + ARMOR_ENTRY_SIZE > len(ram):
            break
        model_m = r_s16(ram, o)
        model_f = r_s16(ram, o + 2)
        flag = r_u8(ram, o + 4)
        entries.append((eid, model_m, model_f, flag))

    # For LEGS (last table), trim trailing all-zero entries
    if slot == "legs":
        while entries and entries[-1][1] == 0 and entries[-1][2] == 0 and entries[-1][3] == 0:
            entries.pop()

    print(f"  {slot.upper()} table: {len(entries)} entries")
    return entries


# ── Build Armor Sets ────────────────────────────────────────────────────────

def build_armor_sets(entries, male_names, female_names):
    """Group armor entries into sets (paired BM/GN variants).

    Each set = {"names": [...], "variants": [{"model_m": m, "model_f": f, "eids": [...]}]}
    A set has 1 variant (standalone) or 2 variants (BM + GN).
    """
    sets = []
    i = 0
    while i < len(entries):
        eid, model_m, model_f, flag = entries[i]

        # Skip entries with model (0,0) and unknown flags — these are padding
        if model_m == 0 and model_f == 0 and flag not in (0x07, 0x0B, 0x0F):
            i += 1
            continue

        # Try to pair with next entry
        paired = False
        if i + 1 < len(entries):
            next_eid, next_mm, next_mf, next_flag = entries[i + 1]
            if next_eid == eid + 1:
                # BM(0x07) + GN(0x0B) pair
                if flag == 0x07 and next_flag == 0x0B:
                    paired = True
                # Both universal(0x0F) with consecutive male models
                elif flag == 0x0F and next_flag == 0x0F and model_m > 0 and next_mm == model_m + 1:
                    paired = True

        if paired:
            v1 = {"model_m": model_m, "model_f": model_f, "eids": [eid]}
            v2 = {"model_m": next_mm, "model_f": next_mf, "eids": [next_eid]}
            names = _lookup_names(model_m, model_f, male_names, female_names)
            names2 = _lookup_names(next_mm, next_mf, male_names, female_names)
            if names2 and names2 != names:
                names = names + names2
            sets.append({"names": names, "variants": [v1, v2]})
            i += 2
        else:
            # Standalone entry
            v = {"model_m": model_m, "model_f": model_f, "eids": [eid]}
            names = _lookup_names(model_m, model_f, male_names, female_names)
            sets.append({"names": names, "variants": [v]})
            i += 1

    # Merge sets with identical variant models (same armor at different equip_ids)
    merged = {}
    for s in sets:
        key = tuple((v["model_m"], v["model_f"]) for v in s["variants"])
        if key in merged:
            existing = merged[key]
            for j, v in enumerate(s["variants"]):
                existing["variants"][j]["eids"].extend(v["eids"])
        else:
            merged[key] = s

    return list(merged.values())


def _lookup_names(model_m, model_f, male_names, female_names):
    """Look up equipment names from FUComplete data."""
    if model_m == 0 and model_f == 0:
        return ["Nothing Equipped"]
    # Gender-specific: female-only (model_m=0) or male-only (model_f=0)
    if model_m == 0 and model_f > 0:
        return female_names.get(model_f, [f"Female-only (model f:{model_f})"])
    if model_f == 0 and model_m > 0:
        return male_names.get(model_m, [f"Male-only (model m:{model_m})"])
    # Normal: try male first, then female
    names = male_names.get(model_m, [])
    if not names:
        names = female_names.get(model_f, [])
    if not names:
        names = [f"Unknown (model {model_m}/{model_f})"]
    return names


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=== Building transmog data ===\n")

    # Step 1: Scrape FUComplete
    print("[1/3] Scraping FUComplete website...")
    weapon_names = scrape_weapons()
    print(f"  Weapons: {len(weapon_names)} models")

    armor_names = {}
    for slot in ARMOR_URLS:
        male, female = scrape_armor(slot)
        armor_names[slot] = {"male": male, "female": female}
        print(f"  {slot.capitalize()}: {len(male)} male, {len(female)} female")
    print()

    # Step 2: Read save state
    print("[2/3] Reading save state...")
    ram = load_ram()
    weapon_entries = extract_weapons(ram)
    armor_raw = {slot: extract_armor(ram, slot) for slot in ARMOR_TABLES}
    print()

    # Step 3: Build combined data
    print("[3/3] Building combined data...")

    weapons = {}
    for model, indices in weapon_entries.items():
        names = weapon_names.get(model, [f"Unknown Weapon (model {model})"])
        weapons[str(model)] = {"names": names, "entries": sorted(indices)}
    print(f"  Weapons: {len(weapons)} models")

    armor = {}
    for slot in ARMOR_TABLES:
        male = armor_names[slot]["male"]
        female = armor_names[slot]["female"]
        sets = build_armor_sets(armor_raw[slot], male, female)
        armor[slot] = {
            "table_base": f"0x{ARMOR_TABLES[slot]:08X}",
            "sets": sets,
        }
        named = sum(1 for s in sets if s["names"] and "Unknown" not in s["names"][0])
        print(f"  {slot.capitalize()}: {len(sets)} sets ({named} named)")

    data = {
        "weapon_table_base": f"0x{WEAPON_TABLE_BASE:08X}",
        "weapon_entry_size": WEAPON_ENTRY_SIZE,
        "weapon_model_offset": WEAPON_MODEL_OFFSET,
        "armor_entry_size": ARMOR_ENTRY_SIZE,
        "weapons": weapons,
        "armor": armor,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nDone! Wrote {OUTPUT_FILE} ({os.path.getsize(OUTPUT_FILE):,} bytes)")


if __name__ == "__main__":
    main()

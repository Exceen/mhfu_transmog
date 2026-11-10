#!/usr/bin/env python3
"""
MHFU Transmog Tool — Generate CWCheat codes for equipment visual overrides.

Reads transmog_data.json (built by build_data.py) and interactively guides
the user through selecting source/target equipment to generate CWCheat codes.
The Multiplayer menu prints the multiplayer codes from online_codes.json (built by online/build.py).

Usage: python transmog.py
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "transmog_data.json")
ONLINE_FILE = os.path.join(SCRIPT_DIR, "online_codes.json")
CHEAT_FILE = os.path.expanduser("~/Documents/PPSSPP/PSP/Cheats/ULJM05500.ini")
CWCHEAT_BASE = 0x08800000
PSP_MAX_LINES = 30  # real PSP CWCheat: max lines per cheat, title line included

SLOT_NAMES = ["head", "chest", "arms", "waist", "legs"]
SLOT_LABELS = {"head": "Head", "chest": "Chest", "arms": "Arms", "waist": "Waist", "legs": "Legs"}
PAGE_SIZE = 20


# ── ANSI Formatting ───────────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"


def key(s):
    """Format a key/shortcut like [1] or [s]."""
    return f"{YELLOW}{BOLD}{s}{RESET}"


def header(s):
    """Format a section header."""
    return f"{CYAN}{BOLD}{s}{RESET}"


def success(s):
    """Format a success message."""
    return f"{GREEN}{s}{RESET}"


def error(s):
    """Format an error/warning message."""
    return f"{RED}{s}{RESET}"


def dim(s):
    """Format dimmed/secondary text."""
    return f"{DIM}{s}{RESET}"


def bold(s):
    """Format bold text."""
    return f"{BOLD}{s}{RESET}"


# ── Data Loading ────────────────────────────────────────────────────────────

def load_data():
    """Load transmog_data.json."""
    if not os.path.exists(DATA_FILE):
        print(error(f"Error: {DATA_FILE} not found. Run build_data.py first."))
        sys.exit(1)
    with open(DATA_FILE) as f:
        return json.load(f)


def load_online():
    """Load online_codes.json, or None if it's missing."""
    if not os.path.exists(ONLINE_FILE):
        return None
    with open(ONLINE_FILE) as f:
        return json.load(f)


# ── Display Helpers ─────────────────────────────────────────────────────────

def display_name(names):
    """Get the display name from a list of names (last = highest tier)."""
    return names[-1] if names else "???"


def short_name(names):
    """Get a shorter display name (first name, typically the base form)."""
    return names[0] if names else "???"


def format_item(item, idx):
    """Format an item for display in a numbered list."""
    names = item["names"]
    return f"{key(f'[{idx}]')} {' / '.join(names)}"


# ── Selection UI ────────────────────────────────────────────────────────────

def select_equipment(items, prompt, allow_invisible=False, preset_search=None):
    """Interactive equipment selection with search and pagination.

    Args:
        items: list of dicts with "names" key
        prompt: display prompt
        allow_invisible: if True, show invisible option as [0]
        preset_search: pre-filled search term (for full set mode)

    Returns:
        Selected item dict, or None for invisible.
    """
    # Sort items alphabetically by first name
    sorted_items = sorted(items, key=lambda x: x["names"][0].lower() if x["names"] else "")
    # Remove "Nothing Equipped" from normal list (it's the invisible option)
    sorted_items = [i for i in sorted_items if i["names"] != ["Nothing Equipped"]]

    search_term = preset_search
    filtered = None
    page = 0

    while True:
        print(f"\n{header(prompt)}")

        if search_term is not None and filtered is None:
            # Apply search filter
            term_lower = search_term.lower()
            filtered = [i for i in sorted_items if any(term_lower in n.lower() for n in i["names"])]
            page = 0

        if filtered is not None:
            # Show search results
            if not filtered:
                print(f'No results for "{search_term}"')
                search_term = None
                filtered = None
                continue

            if allow_invisible:
                print(f"{key('[0]')} {MAGENTA}** Invisible **{RESET}")
            for idx, item in enumerate(filtered, 1):
                print(format_item(item, idx))

            print(f'\n{dim(f"Showing {len(filtered)} results for")} "{bold(search_term)}"')
            print(f"{key('[s]')} New search  {key('[b]')} Browse all  {key('[q]')} Cancel")
            choice = input(f"\n{bold('Select:')} ").strip()

            if choice.lower() == "s":
                search_term = None
                filtered = None
                continue
            elif choice.lower() == "b":
                search_term = None
                filtered = None
                continue
            elif choice.lower() == "q":
                return "cancel"
            elif choice == "0" and allow_invisible:
                return None  # Invisible
            elif choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(filtered):
                    return filtered[idx - 1]
        else:
            # Show paginated browse
            total_pages = (len(sorted_items) + PAGE_SIZE - 1) // PAGE_SIZE
            start = page * PAGE_SIZE
            end = min(start + PAGE_SIZE, len(sorted_items))
            page_items = sorted_items[start:end]

            if allow_invisible:
                print(f"{key('[0]')} {MAGENTA}** Invisible **{RESET}")
            for idx, item in enumerate(page_items, start + 1):
                print(format_item(item, idx))

            print(f"\n{dim(f'Page {page + 1}/{total_pages} ({len(sorted_items)} items)')}")
            nav = []
            if page > 0:
                nav.append(f"{key('[p]')} Prev")
            if page < total_pages - 1:
                nav.append(f"{key('[n]')} Next")
            nav.extend([f"{key('[s]')} Search", f"{key('[q]')} Cancel"])
            print(f"{' | '.join(nav)}")
            choice = input(f"\n{bold('Select:')} ").strip()

            if choice.lower() == "n" and page < total_pages - 1:
                page += 1
                continue
            elif choice.lower() == "p" and page > 0:
                page -= 1
                continue
            elif choice.lower() == "s":
                term = input(f"{bold('Search:')} ").strip()
                if term:
                    search_term = term
                    filtered = None
                continue
            elif choice.lower() == "q":
                return "cancel"
            elif choice == "0" and allow_invisible:
                return None
            elif choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(sorted_items):
                    return sorted_items[idx - 1]

        print(error("Invalid choice, try again."))


def prompt_search_or_enter(prompt_text):
    """Ask user for search term or Enter to browse."""
    term = input(f"\n{prompt_text} {dim('(search or Enter to browse)')}: ").strip()
    return term if term else None


def _variant_label(variant, index, set_names=None):
    """Get a display label for a variant, with fallback for old data."""
    names = variant.get("names")
    if names:
        return names[-1] if len(names) > 1 else names[0]
    # Fallback: use set-level names (first name for variant 0, last for variant 1)
    if set_names and len(set_names) >= 2:
        return set_names[0] if index == 0 else set_names[-1]
    return f"Variant {index + 1}"


def select_variant(target_set):
    """Prompt the user to pick a variant when the target has 2+ variants.

    Returns None (match by armor type, default behavior) or a variant index (0 or 1).
    """
    variants = target_set["variants"]
    if len(variants) < 2:
        return None

    set_names = target_set.get("names", [])
    label1 = _variant_label(variants[0], 0, set_names)
    label2 = _variant_label(variants[1], 1, set_names)

    print(f"\n{header('Variant:')}")
    print(f"{key('[1]')} Match armor type {dim(f'({label1}→{label1}, {label2}→{label2})')}")
    print(f"{key('[2]')} {label1} {dim('(all pieces)')}")
    print(f"{key('[3]')} {label2} {dim('(all pieces)')}")

    while True:
        choice = input(f"\n{bold('Select:')} ").strip()
        if choice == "1":
            return None
        elif choice == "2":
            return 0
        elif choice == "3":
            return 1
        print(error("Invalid choice, try again."))


def select_gender(target_set):
    """Prompt the user to swap gender models.

    Only shown when the target has different male/female model IDs.
    Returns True for swap, False for default.
    """
    if target_set is None:
        return False
    if not any(v["model_m"] != v["model_f"] for v in target_set["variants"]):
        return False

    print(f"\n{header('Gender:')}")
    print(f"{key('[1]')} Default")
    print(f"{key('[2]')} Opposite gender model")

    while True:
        choice = input(f"\n{bold('Select:')} ").strip()
        if choice == "1":
            return False
        elif choice == "2":
            return True
        print(error("Invalid choice, try again."))


# ── CWCheat Generation ─────────────────────────────────────────────────────

def gen_universal_invisible_codes(data, slot):
    """Generate CWCheat lines to make ALL armor in a slot invisible.

    Writes model (0, 0) to every entry with a non-zero model.
    Returns list of (comment, code) tuples.
    """
    table_base = int(data["armor"][slot]["table_base"], 16)
    entry_size = data["armor_entry_size"]
    lines = []

    for armor_set in data["armor"][slot]["sets"]:
        for variant in armor_set["variants"]:
            if variant["model_m"] == 0 and variant["model_f"] == 0:
                continue
            for eid in variant["eids"]:
                entry_addr = table_base + eid * entry_size
                offset = entry_addr - CWCHEAT_BASE
                code = f"_L 0x2{offset:07X} 0x00000000"
                lines.append(("", code))

    return lines


def gen_armor_codes(data, slot, source_set, target_set, force_variant=None, swap_gender=False):
    """Generate CWCheat lines for armor transmog.

    Returns (model_lines, pigment_on, pigment_off) — lists of (comment, code) tuples.
    model_lines: the model ID overwrites.
    pigment_on / pigment_off: byte +19 writes that enable (2) / disable (0) pigment
    support on the source entries. Use armor_lines() to combine them.
    """
    table_base = int(data["armor"][slot]["table_base"], 16)
    entry_size = data["armor_entry_size"]
    model_lines = []
    pigment_on = []
    pigment_off = []

    src_variants = source_set["variants"]
    if target_set is None:
        tgt_variants = [{"model_m": 0, "model_f": 0}] * len(src_variants)
    else:
        tgt_variants = target_set["variants"]

    for vi, src_v in enumerate(src_variants):
        if force_variant is not None:
            tgt_v = tgt_variants[force_variant]
        else:
            tgt_v = tgt_variants[vi] if vi < len(tgt_variants) else tgt_variants[0]
        target_m = tgt_v["model_m"]
        target_f = tgt_v["model_f"]
        if swap_gender:
            value = (target_m & 0xFFFF) << 16 | (target_f & 0xFFFF)
        else:
            value = (target_f & 0xFFFF) << 16 | (target_m & 0xFFFF)

        for eid in src_v["eids"]:
            entry_addr = table_base + eid * entry_size
            offset = entry_addr - CWCHEAT_BASE
            if swap_gender:
                comment = f"; {SLOT_LABELS[slot]} eid {eid} -> model({target_f},{target_m}) [swapped]"
            else:
                comment = f"; {SLOT_LABELS[slot]} eid {eid} -> model({target_m},{target_f})"
            code = f"_L 0x2{offset:07X} 0x{value:08X}"
            model_lines.append((comment, code))
            pig_flag_offset = (entry_addr + 19) - CWCHEAT_BASE
            pigment_on.append(("", f"_L 0x0{pig_flag_offset:07X} 0x00000002"))
            pigment_off.append(("", f"_L 0x0{pig_flag_offset:07X} 0x00000000"))

    return model_lines, pigment_on, pigment_off


def armor_lines(model_lines, pigment_on, pigment_off, pigment):
    """Combine model lines with the chosen pigment lines ("keep", "enable" or "disable")."""
    if pigment == "enable":
        return model_lines + pigment_on
    if pigment == "disable":
        return model_lines + pigment_off
    return model_lines


def ask_pigment():
    """Ask how the transmog should handle pigment color. Returns "keep", "enable" or "disable"."""
    print(f"\n{header('Pigment color:')}")
    print(f"{key('[1]')} Unchanged {dim('(the equipped armor decides)')}")
    print(f"{key('[2]')} Enable {dim('(also on armor that normally cannot be dyed; best on S-series looks)')}")
    print(f"{key('[3]')} Disable {dim('(never apply pigment color)')}")
    while True:
        choice = input(f"\n{bold('Select:')} ").strip() or "1"
        if choice in ("1", "2", "3"):
            return {"1": "keep", "2": "enable", "3": "disable"}[choice]
        print(error("Invalid choice, try again."))


def gen_weapon_codes(data, source_weapon, target_weapon):
    """Generate CWCheat lines for weapon transmog.

    Returns list of (comment, code) tuples.
    """
    weapon_base = int(data["weapon_table_base"], 16)
    entry_size = data["weapon_entry_size"]
    model_offset = data["weapon_model_offset"]
    target_model = int(target_weapon["model"])
    lines = []

    for entry_idx in source_weapon["entries"]:
        model_addr = weapon_base + entry_idx * entry_size + model_offset
        offset = model_addr - CWCHEAT_BASE
        comment = f"; Weapon entry {entry_idx} -> model {target_model}"
        code = f"_L 0x1{offset:07X} 0x0000{target_model:04X}"
        lines.append((comment, code))

    return lines


# ── Cheat Output ────────────────────────────────────────────────────────────

def format_blocks(blocks, psp=False, enabled=False):
    """Format (title, lines) blocks as CWCheat text.

    lines are (comment, code) tuples. With psp=True, blocks longer than PSP_MAX_LINES
    (title included) are split into numbered parts; the line order is kept.
    """
    prefix = "_C1" if enabled else "_C0"
    out = []
    for title, lines in blocks:
        codes = [code for _, code in lines]
        per = PSP_MAX_LINES - 1
        if not psp or len(codes) <= per:
            out.append("\n".join([f"{prefix} {title}"] + codes))
            continue
        parts = (len(codes) + per - 1) // per
        for n in range(parts):
            chunk = codes[n * per:(n + 1) * per]
            out.append("\n".join([f"{prefix} {title} {n + 1}/{parts}"] + chunk))
    return "\n\n".join(out)


def ask_format(blocks):
    """Ask for PPSSPP or real-PSP format if any block is too long for a PSP cheat."""
    if all(len(lines) <= PSP_MAX_LINES - 1 for _, lines in blocks):
        return False
    print(f"\n{bold('Code format:')}")
    print(f"{key('[1]')} PPSSPP {dim('(one cheat per code)')}")
    print(f"{key('[2]')} Real PSP {dim(f'(split into cheats of at most {PSP_MAX_LINES} lines; enable all parts)')}")
    return input(f"\n{bold('Choice:')} ").strip() == "2"


def output_codes(blocks):
    """Display and optionally save generated codes. blocks: list of (title, lines)."""
    psp = ask_format(blocks)
    full_output = format_blocks(blocks, psp=psp)

    print(f"\n{header('Generated CWCheat Codes')}")
    print(f"{'─' * 50}")
    print()
    for line in full_output.splitlines():
        if line.startswith("_C"):
            print(f"{BOLD}{line}{RESET}")
        else:
            print(f"{DIM}{line}{RESET}")
    print()

    # Offer to save
    print(f"{bold('Save options:')}")
    print(f"{key('[1]')} Append to PPSSPP cheat file {dim(f'({CHEAT_FILE})')}")
    print(f"{key('[2]')} Save to custom file")
    dont_save = dim("(don't save)")
    print(f"{key('[3]')} Done {dont_save}")
    choice = input(f"\n{bold('Choice:')} ").strip()

    if choice == "1":
        with open(CHEAT_FILE, "a") as f:
            f.write("\n\n" + full_output + "\n")
        print(success(f"Appended to {CHEAT_FILE}"))
    elif choice == "2":
        path = input(f"{bold('File path:')} ").strip()
        if path:
            with open(path, "w") as f:
                f.write(full_output + "\n")
            print(success(f"Saved to {path}"))
    else:
        print(dim("Codes not saved."))


# ── Flows ───────────────────────────────────────────────────────────────────

def weapon_flow(data, preset_source_search=None, preset_search=None):
    """Weapon transmog selection flow. Returns ((title, lines), source_name, target_name) or None."""
    weapons = data["weapons"]

    # Build items list with model info
    items = []
    for model_str, wdata in weapons.items():
        items.append({
            "names": wdata["names"],
            "entries": wdata["entries"],
            "model": model_str,
        })

    os.system("cls" if os.name == "nt" else "clear")
    print(f"\n{header('Weapon Transmog')}")

    # Select source
    search = preset_source_search if preset_source_search else prompt_search_or_enter("Source weapon (equipped)")
    source = select_equipment(items, "Select SOURCE weapon", preset_search=search)
    if source == "cancel" or source is None:
        return None
    src_name = display_name(source["names"])
    print(success(f"Source: {src_name}"))

    # Select target
    search = preset_search if preset_search else prompt_search_or_enter("Target weapon (visual)")
    target = select_equipment(items, "Select TARGET weapon visual", preset_search=search)
    if target == "cancel" or target is None:
        return None
    tgt_name = display_name(target["names"])
    print(success(f"Target: {tgt_name}"))

    # Generate codes
    lines = gen_weapon_codes(data, source, target)
    title = f"Weapon Transmog: {src_name} -> {tgt_name}"
    return (title, lines), src_name, tgt_name


def armor_slot_flow(data, slot, preset_source_search=None, preset_search=None):
    """Single armor slot selection flow. Returns (lines, source_name, target_name, is_invisible) or None."""
    sets = data["armor"][slot]["sets"]
    label = SLOT_LABELS[slot]

    # Build items list (exclude Nothing Equipped for source)
    items = []
    for s in sets:
        if s["names"] != ["Nothing Equipped"]:
            items.append(s)

    os.system("cls" if os.name == "nt" else "clear")
    print(f"\n{header(f'{label} Armor Transmog')}")

    # Select source
    search = preset_source_search if preset_source_search else prompt_search_or_enter(f"Source {label.lower()} armor (equipped)")
    source = select_equipment(items, f"Select SOURCE {label.lower()} armor", preset_search=search)
    if source == "cancel":
        return None
    if source is None:
        print(error("Source cannot be invisible. Try again."))
        return None
    src_name = display_name(source["names"])
    print(success(f"Source: {src_name}"))

    # Select target (with invisible option)
    search = preset_search if preset_search else prompt_search_or_enter(f"Target {label.lower()} visual")
    target_items = list(sets)  # All sets including Nothing Equipped for target
    target = select_equipment(target_items, f"Select TARGET {label.lower()} visual", allow_invisible=True, preset_search=search)
    if target == "cancel":
        return None

    is_invisible = target is None
    force_variant = None
    swap_gender = False
    if is_invisible:
        tgt_name = "Invisible"
        print(f"Target: {MAGENTA}** Invisible **{RESET}")
    else:
        tgt_name = display_name(target["names"])
        print(success(f"Target: {tgt_name}"))
        # Offer variant selection if target has multiple variants
        if len(target["variants"]) > 1:
            force_variant = select_variant(target)
        # Offer gender swap
        swap_gender = select_gender(target)

    model_lines, pigment_on, pigment_off = gen_armor_codes(data, slot, source, target, force_variant=force_variant, swap_gender=swap_gender)
    return model_lines, pigment_on, pigment_off, src_name, tgt_name, is_invisible


def armor_flow(data):
    """Single armor slot selection flow with output."""
    os.system("cls" if os.name == "nt" else "clear")
    print(f"\n{bold('Select armor slot:')}")
    for i, slot in enumerate(SLOT_NAMES, 1):
        print(f"{key(f'[{i}]')} {SLOT_LABELS[slot]}")

    choice = input(f"\n{bold('Slot:')} ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= 5):
        print(error("Invalid choice."))
        return

    slot = SLOT_NAMES[int(choice) - 1]
    result = armor_slot_flow(data, slot)
    if result is None:
        return

    model_lines, pigment_on, pigment_off, src_name, tgt_name, is_invisible = result
    lines = armor_lines(model_lines, pigment_on, pigment_off, ask_pigment())
    suffix = f" (invisible {SLOT_LABELS[slot].lower()})" if is_invisible else ""
    title = f"Armor Transmog: {src_name} -> {tgt_name}{suffix}"
    output_codes([(title, lines)])


def armor_set_flow(data):
    """Armor set transmog flow (all 5 armor slots)."""
    print(f"\n{header('Armor Set Transmog')}")
    print("You'll select all 5 armor pieces.")
    print(f"{dim('Persistent search filters can be used across selections.')}\n")

    persistent_source_search = input(f"Source search filter {dim('(Enter to skip)')}: ").strip()
    if not persistent_source_search:
        persistent_source_search = None

    persistent_search = input(f"Target search filter {dim('(Enter to skip)')}: ").strip()
    if not persistent_search:
        persistent_search = None

    pigment = ask_pigment()

    all_armor_lines = []
    armor_summaries = []

    for slot in SLOT_NAMES:
        result = armor_slot_flow(data, slot, preset_source_search=persistent_source_search, preset_search=persistent_search)
        if result is None:
            print(dim(f"Skipping {SLOT_LABELS[slot]}."))
            continue
        model_lines, pigment_on, pigment_off, src_name, tgt_name, is_invisible = result
        lines = armor_lines(model_lines, pigment_on, pigment_off, pigment)
        all_armor_lines.extend(lines)
        armor_summaries.append((slot, src_name, tgt_name, is_invisible))

    # Build armor block
    if not all_armor_lines:
        print(dim("\nNo codes generated."))
        return None

    target_names = set()
    for _, _, tgt, inv in armor_summaries:
        if not inv:
            target_names.add(tgt)
    invisible_slots = [SLOT_LABELS[s].lower() for s, _, _, inv in armor_summaries if inv]

    if len(target_names) == 1:
        tgt_display = target_names.pop()
    elif len(target_names) == 0:
        tgt_display = "Invisible"
    else:
        tgt_display = "Custom"

    source_names = set(src for _, src, _, _ in armor_summaries)
    src_display = source_names.pop() if len(source_names) == 1 else "Mixed"

    title = f"Armor Transmog: {src_display} -> {tgt_display}"
    if invisible_slots:
        title += f" (invisible {', '.join(invisible_slots)})"
    output_codes([(title, all_armor_lines)])


def universal_invisible_flow(data):
    """Universal invisible slot flow."""
    os.system("cls" if os.name == "nt" else "clear")
    print(f"\n{header('Universal Invisible Slot')}")
    print(f"{dim('Makes ALL armor in a slot invisible (writes model 0,0 to every entry).')}\n")

    print(f"{bold('Select slot:')}")
    for i, slot in enumerate(SLOT_NAMES, 1):
        print(f"{key(f'[{i}]')} {SLOT_LABELS[slot]}")

    choice = input(f"\n{bold('Slot:')} ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= 5):
        print(error("Invalid choice."))
        return

    slot = SLOT_NAMES[int(choice) - 1]
    lines = gen_universal_invisible_codes(data, slot)
    if not lines:
        print(dim("No entries to patch."))
        return

    title = f"Universal Invisible {SLOT_LABELS[slot]} ({len(lines)} entries)"
    output_codes([(title, lines)])


def online_flow():
    """Print the online transmog codes (armor and/or weapon)."""
    online = load_online()
    os.system("cls" if os.name == "nt" else "clear")
    print(f"\n{header('Multiplayer')}")
    if online is None:
        print(error(f"{ONLINE_FILE} not found. Run online/build.py first."))
        return
    print("Lets other players with these codes see your transmog, and you theirs.")
    print("Players without them see your real equipment. Keep your normal transmog codes")
    print("enabled; these send what they set. Everyone should use the same game version.")
    print(dim("After changing your transmog: re-equip, then change area or rejoin."))

    cheats = online["cheats"]
    armor, weapon = cheats["armor"], cheats["weapon"]
    print(f"\n{bold('Which codes?')}")
    print(f"{key('[1]')} Both")
    print(f"{key('[2]')} {armor['title']} {dim('(armor models + pigment)')}")
    print(f"{key('[3]')} {weapon['title']} {dim('(weapon model)')}")
    choice = input(f"\n{bold('Choice:')} ").strip() or "1"
    picked = {"1": [armor, weapon], "2": [armor], "3": [weapon]}.get(choice)
    if not picked:
        print(error("Invalid choice."))
        return
    output_codes([(c["title"], [("", line) for line in c["lines"]]) for c in picked])


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    data = load_data()

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(f"{CYAN}{BOLD}{'─' * 34}{RESET}")
        print(f"{CYAN}{BOLD}MHFU Transmog Tool{RESET}")
        print(f"{CYAN}{BOLD}{'─' * 34}{RESET}")
        print()
        print(f"{key('[1]')} Weapon Transmog")
        print(f"{key('[2]')} Armor Transmog {dim('(single slot)')}")
        print(f"{key('[3]')} Armor Transmog {dim('(set)')}")
        print(f"{key('[4]')} Universal Invisible Slot")
        print(f"{key('[5]')} Multiplayer {dim('(let other players see your transmog)')}")
        print()
        print(f"{key('[q]')} Quit")

        choice = input(f"\n{bold('Choice:')} ").strip().lower()

        if choice == "1":
            result = weapon_flow(data)
            if result:
                output_codes([result[0]])
        elif choice == "2":
            armor_flow(data)
        elif choice == "3":
            armor_set_flow(data)
        elif choice == "4":
            universal_invisible_flow(data)
        elif choice == "5":
            online_flow()
        elif choice == "q":
            break
        else:
            print(error("Invalid choice."))

        if choice in ("1", "2", "3", "4", "5"):
            input(f"\n{dim('Press Enter to return to menu...')}")


if __name__ == "__main__":
    main()

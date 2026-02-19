#!/usr/bin/env python3
"""
MHFU Transmog Tool — Generate CWCheat codes for equipment visual overrides.

Reads transmog_data.json (built by build_data.py) and interactively guides
the user through selecting source/target equipment to generate CWCheat codes.

Usage: python transmog.py
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, "transmog_data.json")
CHEAT_FILE = os.path.expanduser("~/Documents/PPSSPP/PSP/Cheats/ULJM05500.ini")
CWCHEAT_BASE = 0x08800000

SLOT_NAMES = ["head", "chest", "arms", "waist", "legs"]
SLOT_LABELS = {"head": "Head", "chest": "Chest", "arms": "Arms", "waist": "Waist", "legs": "Legs"}
PAGE_SIZE = 20


# ── Data Loading ────────────────────────────────────────────────────────────

def load_data():
    """Load transmog_data.json."""
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found. Run build_data.py first.")
        sys.exit(1)
    with open(DATA_FILE) as f:
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
    return f"  [{idx}] {' / '.join(names)}"


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
        print(f"\n--- {prompt} ---")

        if search_term is not None and filtered is None:
            # Apply search filter
            term_lower = search_term.lower()
            filtered = [i for i in sorted_items if any(term_lower in n.lower() for n in i["names"])]
            page = 0

        if filtered is not None:
            # Show search results
            if not filtered:
                print(f'  No results for "{search_term}"')
                search_term = None
                filtered = None
                continue

            if allow_invisible:
                print("  [0] ** Invisible **")
            for idx, item in enumerate(filtered, 1):
                print(format_item(item, idx))

            print(f'\n  Showing {len(filtered)} results for "{search_term}"')
            print("  [s] New search  [b] Browse all  [q] Cancel")
            choice = input("\n  Select: ").strip()

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
                print("  [0] ** Invisible **")
            for idx, item in enumerate(page_items, start + 1):
                print(format_item(item, idx))

            print(f"\n  Page {page + 1}/{total_pages} ({len(sorted_items)} items)")
            nav = []
            if page > 0:
                nav.append("[p] Prev")
            if page < total_pages - 1:
                nav.append("[n] Next")
            nav.extend(["[s] Search", "[q] Cancel"])
            print(f"  {' | '.join(nav)}")
            choice = input("\n  Select: ").strip()

            if choice.lower() == "n" and page < total_pages - 1:
                page += 1
                continue
            elif choice.lower() == "p" and page > 0:
                page -= 1
                continue
            elif choice.lower() == "s":
                term = input("  Search: ").strip()
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

        print("  Invalid choice, try again.")


def prompt_search_or_enter(prompt_text):
    """Ask user for search term or Enter to browse."""
    term = input(f"\n  {prompt_text} (search or Enter to browse): ").strip()
    return term if term else None


# ── CWCheat Generation ─────────────────────────────────────────────────────

def gen_armor_codes(data, slot, source_set, target_set):
    """Generate CWCheat lines for armor transmog.

    Returns list of (comment, code) tuples.
    """
    table_base = int(data["armor"][slot]["table_base"], 16)
    entry_size = data["armor_entry_size"]
    lines = []

    # Pair source and target variants by index
    src_variants = source_set["variants"]
    if target_set is None:
        # Invisible: use model (0,0) for all variants
        tgt_variants = [{"model_m": 0, "model_f": 0}] * len(src_variants)
    else:
        tgt_variants = target_set["variants"]

    for vi, src_v in enumerate(src_variants):
        # Get target model (pair by variant index, fall back to first)
        tgt_v = tgt_variants[vi] if vi < len(tgt_variants) else tgt_variants[0]
        target_m = tgt_v["model_m"]
        target_f = tgt_v["model_f"]
        value = (target_f & 0xFFFF) << 16 | (target_m & 0xFFFF)

        for eid in src_v["eids"]:
            entry_addr = table_base + eid * entry_size
            offset = entry_addr - CWCHEAT_BASE
            comment = f"; {SLOT_LABELS[slot]} eid {eid} -> model({target_m},{target_f})"
            code = f"_L 0x2{offset:07X} 0x{value:08X}"
            lines.append((comment, code))

    return lines


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

def format_cheat_block(title, lines, enabled=True):
    """Format a CWCheat code block."""
    prefix = "_C1" if enabled else "_C0"
    result = [f"{prefix} {title}"]
    for comment, code in lines:
        result.append(code)
    return "\n".join(result)


def output_codes(armor_block, weapon_block):
    """Display and optionally save generated codes."""
    print("\n" + "=" * 60)
    print("  GENERATED CWCHEAT CODES")
    print("=" * 60)

    blocks = []
    if armor_block:
        blocks.append(armor_block)
    if weapon_block:
        blocks.append(weapon_block)

    full_output = "\n\n".join(blocks)
    print()
    print(full_output)
    print()

    # Offer to save
    print("Options:")
    print(f"  [1] Append to PPSSPP cheat file ({CHEAT_FILE})")
    print("  [2] Save to custom file")
    print("  [3] Done (don't save)")
    choice = input("\n  Choice: ").strip()

    if choice == "1":
        with open(CHEAT_FILE, "a") as f:
            f.write("\n\n" + full_output + "\n")
        print(f"  Appended to {CHEAT_FILE}")
    elif choice == "2":
        path = input("  File path: ").strip()
        if path:
            with open(path, "w") as f:
                f.write(full_output + "\n")
            print(f"  Saved to {path}")
    else:
        print("  Codes not saved.")


# ── Flows ───────────────────────────────────────────────────────────────────

def weapon_flow(data, preset_search=None):
    """Weapon transmog selection flow. Returns (weapon_block_str, source_name, target_name) or None."""
    weapons = data["weapons"]

    # Build items list with model info
    items = []
    for model_str, wdata in weapons.items():
        items.append({
            "names": wdata["names"],
            "entries": wdata["entries"],
            "model": model_str,
        })

    print("\n=== Weapon Transmog ===")

    # Select source
    search = prompt_search_or_enter("Source weapon (equipped)")
    source = select_equipment(items, "Select SOURCE weapon", preset_search=search)
    if source == "cancel" or source is None:
        return None
    src_name = display_name(source["names"])
    print(f"  Selected source: {src_name}")

    # Select target
    search = preset_search if preset_search else prompt_search_or_enter("Target weapon (visual)")
    target = select_equipment(items, "Select TARGET weapon visual", preset_search=search)
    if target == "cancel" or target is None:
        return None
    tgt_name = display_name(target["names"])
    print(f"  Selected target: {tgt_name}")

    # Generate codes
    lines = gen_weapon_codes(data, source, target)
    title = f"Weapon Transmog: {src_name} -> {tgt_name}"
    block = format_cheat_block(title, lines)
    return block, src_name, tgt_name


def armor_slot_flow(data, slot, preset_search=None):
    """Single armor slot selection flow. Returns (lines, source_name, target_name, is_invisible) or None."""
    sets = data["armor"][slot]["sets"]
    label = SLOT_LABELS[slot]

    # Build items list (exclude Nothing Equipped for source)
    items = []
    for s in sets:
        if s["names"] != ["Nothing Equipped"]:
            items.append(s)

    print(f"\n=== {label} Armor Transmog ===")

    # Select source
    search = prompt_search_or_enter(f"Source {label.lower()} armor (equipped)")
    source = select_equipment(items, f"Select SOURCE {label.lower()} armor", preset_search=search)
    if source == "cancel":
        return None
    if source is None:
        print("  Source cannot be invisible. Try again.")
        return None
    src_name = display_name(source["names"])
    print(f"  Selected source: {src_name}")

    # Select target (with invisible option)
    search = preset_search if preset_search else prompt_search_or_enter(f"Target {label.lower()} visual")
    target_items = list(sets)  # All sets including Nothing Equipped for target
    target = select_equipment(target_items, f"Select TARGET {label.lower()} visual", allow_invisible=True, preset_search=search)
    if target == "cancel":
        return None

    is_invisible = target is None
    if is_invisible:
        tgt_name = "Invisible"
        print(f"  Selected target: ** Invisible **")
    else:
        tgt_name = display_name(target["names"])
        print(f"  Selected target: {tgt_name}")

    lines = gen_armor_codes(data, slot, source, target)
    return lines, src_name, tgt_name, is_invisible


def armor_flow(data):
    """Full armor slot selection flow. Returns (armor_block_str, summary) or None."""
    print("\nSelect armor slot:")
    for i, slot in enumerate(SLOT_NAMES, 1):
        print(f"  [{i}] {SLOT_LABELS[slot]}")

    choice = input("\n  Slot: ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= 5):
        print("  Invalid choice.")
        return None

    slot = SLOT_NAMES[int(choice) - 1]
    result = armor_slot_flow(data, slot)
    if result is None:
        return None

    lines, src_name, tgt_name, is_invisible = result
    suffix = f" (invisible {SLOT_LABELS[slot].lower()})" if is_invisible else ""
    title = f"Armor Transmog: {src_name} -> {tgt_name}{suffix}"
    block = format_cheat_block(title, lines)
    return block, title


def full_set_flow(data):
    """Full set transmog flow (weapon + all 5 armor slots)."""
    print("\n=== Full Set Transmog ===")
    print("You'll select one weapon and all 5 armor pieces.")
    print("A persistent search filter can be used across target selections.\n")

    persistent_search = input("  Target search filter (reused across selections, Enter to skip): ").strip()
    if not persistent_search:
        persistent_search = None

    # Weapon
    weapon_result = weapon_flow(data, preset_search=persistent_search)

    # Armor (all 5 slots)
    all_armor_lines = []
    armor_summaries = []
    has_invisible = False

    for slot in SLOT_NAMES:
        result = armor_slot_flow(data, slot, preset_search=persistent_search)
        if result is None:
            print(f"  Skipping {SLOT_LABELS[slot]}.")
            continue
        lines, src_name, tgt_name, is_invisible = result
        all_armor_lines.extend(lines)
        armor_summaries.append((slot, src_name, tgt_name, is_invisible))
        if is_invisible:
            has_invisible = True

    # Build armor block
    armor_block = None
    if all_armor_lines:
        # Build title: if all targets are the same, use that name
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

        # Source: use first armor source name or "Mixed"
        source_names = set(src for _, src, _, _ in armor_summaries)
        src_display = source_names.pop() if len(source_names) == 1 else "Mixed"

        title = f"Armor Transmog: {src_display} -> {tgt_display}"
        if invisible_slots:
            title += f" (invisible {', '.join(invisible_slots)})"
        armor_block = format_cheat_block(title, all_armor_lines)

    # Build weapon block
    weapon_block = None
    if weapon_result:
        weapon_block = weapon_result[0]

    if armor_block or weapon_block:
        output_codes(armor_block, weapon_block)
    else:
        print("\n  No codes generated.")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    data = load_data()

    while True:
        print("\n" + "=" * 40)
        print("  MHFU Transmog Tool")
        print("=" * 40)
        print("  [1] Weapon Transmog")
        print("  [2] Armor Transmog (single slot)")
        print("  [3] Full Set Transmog")
        print("  [q] Quit")

        choice = input("\n  Choice: ").strip().lower()

        if choice == "1":
            result = weapon_flow(data)
            if result:
                output_codes(None, result[0])
        elif choice == "2":
            result = armor_flow(data)
            if result:
                output_codes(result[0], None)
        elif choice == "3":
            full_set_flow(data)
        elif choice == "q":
            print("  Bye!")
            break
        else:
            print("  Invalid choice.")


if __name__ == "__main__":
    main()

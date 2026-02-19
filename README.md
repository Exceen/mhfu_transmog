# MHFU Transmog

Change the visual appearance of weapons and armor in Monster Hunter Freedom Unite (with [FUComplete](https://github.com/FUComplete/FUComplete) mod) without affecting stats.

Works on PPSSPP and real PSP hardware via CWCheat codes.

## How It Works

The game stores equipment data in static memory tables. Each armor/weapon entry contains a model ID that determines its 3D appearance. CWCheat codes overwrite these model IDs at runtime, making one piece of equipment look like another while keeping the original stats.

## Requirements

- Python 3.6+
- MHFU with FUComplete mod (game ID: ULJM05500)
- PPSSPP save state (for building the data file)
- Game files: `DATA.BIN`, `EBOOT.BIN`, `FILE.BIN` placed in the `data/` folder (not included — extract from your own copy of the game)

## Setup

```bash
pip install -r requirements.txt
python build_data.py
```

`build_data.py` scrapes equipment names from the [FUComplete docs](https://fucomplete.github.io/files_doc/player/player_asset.html) and reads the armor/weapon tables from a PPSSPP save state to generate `transmog_data.json`.

By default it reads save slot 0 from `~/Documents/PPSSPP/PSP/PPSSPP_STATE/`. Edit the constants at the top of the script if your paths differ.

## Usage

```bash
python transmog.py
```

The tool offers three modes:

- **Weapon Transmog** — change a weapon's appearance
- **Armor Transmog** — change a single armor slot's appearance
- **Full Set Transmog** — guided flow for weapon + all 5 armor slots, with a persistent search filter across selections

For each selection you can search by name or browse an alphabetical list with pagination. Armor targets include an "Invisible" option (shows hair for head, hides the piece for other slots).

Generated codes are printed to the terminal and can optionally be appended to the PPSSPP cheat file at `~/Documents/PPSSPP/PSP/Cheats/ULJM05500.ini`.

### Example Output

```ini
_C1 Armor Transmog: Rathalos Soul Cap U -> Black Face (invisible head)
_L 0x20161718 0x00000000
_L 0x20161740 0x00000000
_L 0x20165AE8 0x002F002F
_L 0x20165B10 0x00300030
...

_C1 Weapon Transmog: Sieglinde G -> Black Fatalis Blade
_L 0x10157810 0x000000F2
_L 0x10157828 0x000000F2
_L 0x1015B6B0 0x000000F2
```

After enabling the cheat in PPSSPP, unequip and re-equip the armor/weapon to trigger a model reload.

## Technical Details

See [FINDINGS.md](FINDINGS.md) for the full reverse-engineering documentation, including memory table layouts, address calculations, and known pitfalls.

## TODO

- [ ] include a script to auto-extract the required game files
- [ ] improve usability of the transmog script
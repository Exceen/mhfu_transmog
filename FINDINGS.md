# MHFU Transmog via CWCheat — Complete Technical Findings

Game: Monster Hunter Freedom Unite (MHP2G) with FUComplete mod
Platform: PPSSPP (PSP emulator)
Game ID: ULJM05500
Cheat file: `PPSSPP/PSP/Cheats/ULJM05500.ini`

---

## 1. PPSSPP Save State Format

Save states are `.ppst` files located in `PPSSPP/PSP/PPSSPP_STATE/`.
Filename pattern: `ULJM05500_1.01_{slot}.ppst`

### Structure
| Offset | Size | Content |
|--------|------|---------|
| 0x00   | 0xB0 | PPSSPP header (skip) |
| 0xB0   | ...  | Zstandard-compressed PSP memory snapshot |

### Decompression
```python
import zstandard
raw = open(state_path, 'rb').read()
compressed = raw[0xB0:]
data = zstandard.ZstdDecompressor().decompress(compressed, max_output_size=128*1024*1024)
```
Decompressed size: ~38.7 MB.

### PSP RAM layout within decompressed data
- RAM data starts at offset **0x48** in the decompressed data
- PSP RAM starts at address **0x08000000**

### Address conversion formula
```
state_offset = (psp_address - 0x08000000) + 0x48
```

Or, if you strip the 0x48 header first:
```
ram_offset = psp_address - 0x08000000
```

---

## 2. CWCheat Format

CWCheat codes are written in the cheat `.ini` file.

### Header
```
_S ULJM-05500
_G Monster Hunter Freedom Unite
```

### Code block
```
_C0 Cheat Name Here          # _C0 = disabled, _C1 = enabled
_L 0xTAAAAAAA 0xVVVVVVVV     # T = type, A = address offset, V = value
```

### Address calculation
CWCheat addresses use an offset from base **0x08800000**:
```
cwcheat_offset = psp_address - 0x08800000
```

### Write types
| Type | Code prefix | Size | Value format |
|------|-------------|------|--------------|
| 0    | `_L 0x0`    | 8-bit (1 byte) | `0x000000VV` |
| 1    | `_L 0x1`    | 16-bit (2 bytes) | `0x0000VVVV` |
| 2    | `_L 0x2`    | 32-bit (4 bytes) | `0xVVVVVVVV` |

### Example
To write 32-bit value `0x002F002F` at PSP address `0x08965AE8`:
```
offset = 0x08965AE8 - 0x08800000 = 0x00165AE8
_L 0x20165AE8 0x002F002F
     ^              ^
     type=2          value
```

### PPSSPP limitations
- CWCheat type 5 (copy bytes) does **NOT** work on PPSSPP
- CWCheat type 8 (multi-write) does **NOT** work on PPSSPP
- Only types 0, 1, 2 (byte/halfword/word writes) are reliable

---

## 3. Armor Data Tables

### Overview
Armor data is stored in 5 static tables in PSP memory, one per equipment slot. Each table is an array of fixed-size entries indexed by **equip_id** (equipment ID).

### Pointer table
A pointer table at **0x08975970** stores the base address of each armor table, indexed by `type2`:

| type2 | Slot  | Table base address |
|-------|-------|--------------------|
| 0     | LEGS  | 0x08970D30         |
| 1     | HEAD  | 0x08960750         |
| 2     | CHEST | 0x08964B70         |
| 3     | ARMS  | 0x08968D10         |
| 4     | WAIST | 0x0896CD48         |
| 5     | (flags, not a pointer) | 0x02030007 |
| 6     | (flags, not a pointer) | 0x04030002 |

**Important**: LEGS is at index 0 (not 5). Indices 5 and 6 contain flag values, not valid pointers.

### Entry structure (40 bytes)
| Offset | Type | Field | Description |
|--------|------|-------|-------------|
| +0     | s16  | modelIdMale | Male character 3D model ID |
| +2     | s16  | modelIdFemale | Female character 3D model ID |
| +4     | u8   | flag | Variant flag (see below) |
| +5     | u8   | rarity | Item rarity (0-9) |
| +6     | ...  | (padding/unknown) | |
| +8     | u32  | sellPrice | Sell price in zenny |
| +12    | u8   | defense | Base defense |
| +13    | u8   | fireRes | Fire resistance |
| +14    | u8   | waterRes | Water resistance |
| +15    | u8   | thunderRes | Thunder resistance |
| +16    | u8   | dragonRes | Dragon resistance |
| +17    | u8   | iceRes | Ice resistance |
| +18    | u8   | slots | Decoration slots (0-3) |
| +19    | u8   | pigmentFlag | Pigment support: 0=none, 1/2/3=enabled (tier) |
| +20-29 | ...  | (unknown) | |
| +30    | u8   | skill1Id | First skill ID |
| +31    | u8   | skill1Pts | First skill points |
| +32-39 | ...  | (more skills) | |

### Flag byte values
| Flag | Meaning |
|------|---------|
| 0x07 | Blademaster (both male and female models present) |
| 0x0B | Gunner (both male and female models present) |
| 0x0F | Gender-neutral / universal (used for HEAD pieces like Chakra) |

### Entry address calculation
```
entry_address = table_base + equip_id * 40
```

### Model file naming convention
Armor models are stored as `.pac` files with slot-specific prefixes:

| Slot  | Male prefix | Female prefix | Example (model 96) |
|-------|-------------|---------------|---------------------|
| HEAD  | m_hair      | f_hair        | m_hair096.pac, f_hair096.pac |
| CHEST | m_body      | f_body        | m_body092.pac, f_body092.pac |
| ARMS  | m_arm       | f_arm         | m_arm089.pac, f_arm089.pac |
| WAIST | m_wst       | f_wst         | m_wst076.pac, f_wst076.pac |
| LEGS  | m_reg       | f_reg         | m_reg067.pac, f_reg067.pac |

**Special values**:
- Model `(0, 0)` = "Nothing Equipped" → loads `m_hair000.pac`/`f_hair000.pac` → shows invisible armor with hair visible (useful for HEAD slot)
- Model `(-1, -1)` = hides everything including hair (not recommended for HEAD)

### BM/GN pairing
Armor entries come in consecutive pairs:
- Even equip_id (or first in pair) = Blademaster variant
- Odd equip_id (or second in pair) = Gunner variant

Both must be patched to cover all equipment variants.

### Tables are STATIC
The armor data tables are identical across different save states. They are loaded from the game's ROM/EBOOT data and never modified at runtime. This means CWCheat constant-write codes work reliably.

---

## 4. Weapon Data Table

### Overview
All weapons (across all weapon types) share a single data table in PSP memory.

### Table location
| Property | Value |
|----------|-------|
| Base address | **0x089574E8** |
| Entry size | **24 bytes** |
| Total entries | ~1,149 |
| Total size | ~27,576 bytes (0x6BB8) |
| End address | ~0x0895E0A0 |

### Entry structure (24 bytes)
| Offset | Type | Field | Description |
|--------|------|-------|-------------|
| +0     | u8   | byte0 | Unknown (possibly weapon category/flags, values 0-7) |
| +1     | u8   | byte1 | Unknown (possibly upgrade tier, values 0-5) |
| +2     | u16  | attack | Base attack value (true raw before multiplier) |
| +4     | u16  | field4 | Unknown (possibly affinity or element modifier) |
| +6     | u16  | field6 | Unknown (possibly element type + value) |
| +8     | u16  | field8 | Unknown |
| +10    | u16  | field10 | Unknown (possibly decoration slots) |
| +12    | u16  | field12 | Unknown (possibly sharpness index) |
| +14    | u16  | field14 | Unknown (usually 0) |
| **+16** | **u16** | **modelId** | **Weapon model ID** (`weXXX.pac`) |
| +18    | u16  | rarity | Item rarity (0-9) |
| +20    | u32  | price | Buy price in zenny |

### Entry address calculation
```
entry_address = 0x089574E8 + entry_index * 24
model_id_address = entry_address + 16
```

### Multiple entries per weapon model
The same weapon model ID appears in multiple entries representing different **upgrade tiers** of the same weapon. All entries sharing a model ID use the same 3D model visually.

Example — Sieglinde (model 21):
| Entry index | Address | Attack | Rarity | Price |
|-------------|---------|--------|--------|-------|
| 33          | 0x08957800 | 110 | 2 | 6,200z |
| 34          | 0x08957818 | 130 | 4 | 16,000z |
| 701         | 0x0895B6A0 | 270 | 9 | 200,000z |

Example — Black Fatalis Blade (model 242):
| Entry index | Address | Attack | Rarity | Price |
|-------------|---------|--------|--------|-------|
| 376         | 0x08959828 | 130 | 4 | 30,000z |
| 419         | 0x08959C30 | 170 | 7 | 200,000z |
| 651         | 0x0895B1F0 | 210 | 9 | 300,000z |

### Weapon model file naming
Weapon models are stored as `weXXX.pac` files:
```
we000.pac, we001.pac, ..., we021.pac (Sieglinde), ..., we242.pac (BFB), ...
```

File ID formula (for reference): `file_id = 3388 + model_number`
- Sieglinde: 3388 + 21 = 3409
- BFB: 3388 + 242 = 3630

### Table is STATIC
Like armor tables, the weapon data table is static across save states.

### How the game code indexes it
Game code addresses the same table as `0x089574C8 + eid * 24` with the **model as u16 at +0**,
where `eid` is the weapon's equipment ID (as stored in the player's equipment entry). This is the
same memory: `0x089574E8 + i*24 + 16 = 0x089574C8 + (i+2)*24`, so `eid = entry_index + 2`.

### Gunner weapons (bowguns, bows)
Bowguns and bows have their own table right after the blademaster table: `0x0895E098 + eid * 28`,
model as u16 at `+0`, eids 1–353 (eid 0 unused). `getNetWeaponModel` (`0x08851E4C`) uses it when the
weapon entry's type byte (`+1`) is not 5. Light/Heavy Bowguns and Bows are mixed in this table.

### Weapon class per model
`0x08975984 + model` is one byte per weapon model (`weXXX.pac`) with the weapon class, in the usual
order: 0 Great Sword, 1 Heavy Bowgun, 2 Hammer, 3 Lance, 4 Sword & Shield, 5 Light Bowgun,
6 Dual Blades, 7 Long Sword, 8 Hunting Horn, 9 Gunlance, 10 Bow. Neither weapon table stores a class.
`build_data.py` reads the types from here (earlier hand-made lists had 74 wrong types).

---

## 5. Armor Transmog — How to Generate CWCheat Codes

### Goal
Change the visual appearance of armor piece A to look like armor piece B, without affecting stats.

### What to patch
Overwrite the first 4 bytes (modelIdMale + modelIdFemale) of the **source** armor's entry with the **target** armor's model IDs.

### Step-by-step process

1. **Identify the source armor's equip_id and slot** (e.g., Rath Soul Helm S = HEAD eid 101)
2. **Identify the target armor's model IDs** (e.g., Black Head model_m=50, model_f=50)
3. **Calculate the source entry's PSP address**:
   ```
   entry_addr = table_base[slot] + equip_id * 40
   ```
4. **Pack the target model IDs into a 32-bit value**:
   ```
   value = (model_f & 0xFFFF) << 16 | (model_m & 0xFFFF)
   ```
5. **Calculate the CWCheat offset**:
   ```
   offset = entry_addr - 0x08800000
   ```
6. **Write the CWCheat line**:
   ```
   _L 0x2{offset:07X} 0x{value:08X}
   ```

### Patch both BM and GN variants
Each armor set has Blademaster and Gunner variants at consecutive equip_ids. You need to patch **both** to ensure the transmog works regardless of which variant is equipped.

### Example: Making HEAD invisible
```
entry_addr = 0x08960750 + eid * 40
value = 0x00000000                    # model (0,0) = invisible with hair
offset = entry_addr - 0x08800000
_L 0x2{offset:07X} 0x00000000
```

---

## 6. Weapon Transmog — How to Generate CWCheat Codes

### Goal
Change the visual appearance of weapon A to look like weapon B, without affecting stats.

### What to patch
Overwrite the **model ID** field (u16 at offset +16) of ALL entries that share the source weapon's model ID.

### Step-by-step process

1. **Identify the source weapon's model ID** (e.g., Sieglinde = model 21)
2. **Identify the target weapon's model ID** (e.g., BFB = model 242 = 0x00F2)
3. **Find all entries in the weapon table with the source model ID**:
   ```python
   for i in range(1149):
       entry_addr = 0x089574E8 + i * 24
       if read_u16(data, entry_addr + 16) == source_model:
           # This entry needs patching
   ```
4. **For each matching entry, calculate the CWCheat line**:
   ```
   model_addr = entry_addr + 16
   offset = model_addr - 0x08800000
   _L 0x1{offset:07X} 0x0000{target_model:04X}
   ```

### Note: Patch ALL matching entries
A weapon model appears in multiple table entries (different upgrade tiers). You must patch all of them because you might have any upgrade tier equipped.

### Example: Sieglinde → BFB
```
Entry 33:  model at 0x08957810 → _L 0x10157810 0x000000F2
Entry 34:  model at 0x08957828 → _L 0x10157828 0x000000F2
Entry 701: model at 0x0895B6B0 → _L 0x1015B6B0 0x000000F2
```

---

## 7. How to Find Equip IDs and Model IDs

### From the FUComplete website
The FUComplete mod documentation lists all equipment with their model file names. The model number is extracted from the filename:
- `m_hair096.pac` → HEAD model 96
- `we021.pac` → weapon model 21

### From the save state (searching by model ID)
To find all equip_ids that use a specific model, scan the relevant table:

```python
# For armor (e.g., HEAD):
table_base = 0x08960750
for eid in range(400):
    addr = table_base + eid * 40
    model_m = read_s16(data, addr)
    model_f = read_s16(data, addr + 2)
    if model_m == target_model:
        print(f"Found at eid={eid}")

# For weapons:
for i in range(1149):
    addr = 0x089574E8 + i * 24
    model = read_u16(data, addr + 16)
    if model == target_model:
        print(f"Found at index={i}")
```

---

## 8. Working Transmog Examples

### Armor: Rath Soul → Black (with invisible head)
```ini
_C0 Armor Transmog: Rath Soul -> Black (invisible head)
_L 0x20161718 0x00000000    ; HEAD eid 101 (BM) -> invisible
_L 0x20161740 0x00000000    ; HEAD eid 102 (GN) -> invisible
_L 0x20165AE8 0x002F002F    ; CHEST eid 99 (BM) -> Black model 47/47
_L 0x20165B10 0x00300030    ; CHEST eid 100 (GN) -> Black model 48/48
_L 0x20169C38 0x002E002E    ; ARMS eid 97 (BM) -> Black model 46/46
_L 0x20169C60 0x002F002F    ; ARMS eid 98 (GN) -> Black model 47/47
_L 0x2016DC70 0x00240023    ; WAIST eid 97 (BM) -> Black model 35/36
_L 0x2016DC98 0x00220024    ; WAIST eid 98 (GN) -> Black model 34/36
_L 0x20171BE0 0x00220022    ; LEGS eid 94 (BM) -> Black model 34/34
_L 0x20171C08 0x00230023    ; LEGS eid 95 (GN) -> Black model 35/35
```

### Weapon: Sieglinde → Black Fatalis Blade
```ini
_C0 Weapon Transmog: Sieglinde -> Black Fatalis Blade
_L 0x10157810 0x000000F2    ; Entry 33 model 21 -> 242
_L 0x10157828 0x000000F2    ; Entry 34 model 21 -> 242
_L 0x1015B6B0 0x000000F2    ; Entry 701 model 21 -> 242
```

---

## 9. Other Tables Found (Reference)

### Model file lookup table (DO NOT MODIFY)
- Address: **0x0893E7F0**
- Entry size: 8 bytes, indexed by model number
- This maps model IDs to file loading parameters
- **WARNING**: Modifying this table affects ALL equipment using that model number (e.g., changing model 21 here broke head armor)

### FUComplete lookup tables (NOT used for model loading)
| Table | Address | Entry size | Notes |
|-------|---------|------------|-------|
| TABLE_A | 0x089972AC | u16 array | Not used at model-load time |
| TABLE_B | 0x08997BA8 | u16 array | Matches modelIdMale but not used for rendering |
| TABLE_E | 0x0899851C | u16 array | Not used at model-load time |

### Crafting/Upgrade table
- Address: **0x08938D1A**
- Entry size: 26 bytes
- Field +18 = weapon ID, links to materials

### Weapon index table
- Address: **0x089A1878**
- Entry size: 10 bytes
- 87 entries with sequential IDs (0-86)

---

## 10. Armor Pigment Color

### Overview
MHFU allows players to change the pigment (color) of their armor. The pigment is stored as a **color index** (0–10) per armor slot in the player's character data.

### Color palette
| Index | Color |
|-------|-------|
| 0 | White |
| 1 | Black |
| 2 | Red |
| 3 | Pink |
| 4 | Orange |
| 5 | Yellow |
| 6 | Green |
| 7 | Jade Green |
| 8 | Deep Blue |
| 9 | Blue |
| 10 | Purple |

### Memory layout
Five consecutive 4-byte slots store the pigment index for each armor slot:

| Address | Slot |
|---------|------|
| **0x090B0250** | Slot 1 |
| **0x090B0254** | Slot 2 |
| **0x090B0258** | Slot 3 |
| **0x090B025C** | Slot 4 |
| **0x090B0260** | Slot 5 |

Each slot stores the color index as a single byte at offset +0, with bytes +1 through +3 set to `0xFF`.

### Nearby data
| Address | Content |
|---------|---------|
| 0x090B02D0 | `FF FF FF FF 7F 7F 7F 00` — base white/gray reference |
| 0x090B02E0 | RGB bytes of the active pigment color (derived from index) |
| 0x090B02E4 | Duplicate of 0x090B02E0 |

### Pigment support flag (byte +19 of armor entry)
The game checks byte +19 of the **equipped** armor's entry to determine if pigment is supported:
- **0** = pigment not supported (low-rank / base armor)
- **1** = pigment supported (special elder dragon S armor)
- **2** = pigment supported (high-rank S armor)
- **3** = pigment supported (G-rank X/Z armor)

To enable pigment on armor that doesn't normally support it (e.g., when transmogging to a pigment-supporting target), write `0x02` to byte +19 of the source armor's table entry:
```
pigment_flag_addr = entry_addr + 19
offset = pigment_flag_addr - 0x08800000
_L 0x0{offset:07X} 0x00000002
```

### CWCheat format
Use type 0 (8-bit write) to set the pigment color:
```
offset = pigment_address - 0x08800000
_L 0x0{offset:07X} 0x000000{color_index:02X}
```

### Example: Set all armor to Black pigment
```ini
_C1 Pigment Color: Black
_L 0x008B0250 0x00000001
_L 0x008B0254 0x00000001
_L 0x008B0258 0x00000001
_L 0x008B025C 0x00000001
_L 0x008B0260 0x00000001
```

---

## 11. Known Pitfalls

1. **LEGS table is at pointer index 0**, not index 5. Index 5 contains `0x02030007` (a flag value, not a pointer).

2. **Do NOT modify the model file lookup table** at `0x0893E7F0`. It is shared across equipment types and changing an entry there affects ALL equipment using that model number.

3. **Runtime addresses are unreliable**. Addresses like `0x08A35890` (current head model file_id) or `0x0912F54C` change depending on which equipment is loaded. They cannot be used for static CWCheat codes.

4. **Entity model data is overwritten each frame**. Patching the entity structure directly (e.g., at `0x099959A0 + offset`) does not persist.

5. **CWCheat type 5 and type 8 don't work on PPSSPP**. Only byte (type 0), halfword (type 1), and word (type 2) constant writes are reliable.

6. **Armor transmog requires re-equipping**. After enabling the cheat, unequip and re-equip the armor piece to trigger a model reload.

7. **Multiple weapon entries share the same model**. When creating weapon transmog, you must patch ALL entries with the source model ID, not just one.

8. **Only real fields of the network record are transmitted** (see section 13). Padding bytes such as record `+0x2A` arrive as zero on the other side.

9. **The model getters' slot parameter is not type2.** `0x088517A8` / `0x08851994` use 0 legs, 1 hair, 2 head, 3 chest, 4 arms, 5 waist, while equipment entries and armor tables use type2 (0 legs, 1 head, 2 chest, 3 arms, 4 waist).

10. **Don't call `0x088515D0` (getArmorModel) from a hook for the head**: its head case depends on a flag in `$t0`. Read the armor table directly instead.

11. **Real PSP CWCheat: at most 30 lines per cheat.** Longer codes must be split into several cheats (in order).

---

## 12. Scripts

These research scripts are in [`archive/`](archive/):

| Script | Purpose |
|--------|---------|
| `find_weapon_data.py` | Discovered the weapon data table structure at 0x089574E8 |
| `precise_lookup.py` | Reads specific armor entries and computes CWCheat lines |
| `gen_full_transmog.py` | Generates full armor transmog codes (searches by model ID) |
| `find_all_transmog.py` | Comprehensive armor table search |
| `find_black_armor.py` | Finds Black armor entries across all tables |
| `read_head_table.py` | Reads HEAD armor table, dumps entry structure |
| `read_jump_table.py` | Reads the equipment type dispatch jump table |
| `verify_weapon_table2.py` | Verified the (wrong) model file table at 0x0893E7F0 |
| `disasm_equip_code.py` | MIPS disassembler helper for analyzing game code |

---

## 13. Multiplayer Transmog

Transmog codes only patch your own tables. Other players draw your hunter from the equipment IDs
they receive, looked up in their own tables. The online codes (`online/armor.asm`, `online/weapon.asm`,
built into `online_codes.json`) send the models your patched tables produce, in spare bits of data
the game already sends, and make the receiver use them. Unmodified games ignore those bits
(tested). Inspired by Kurogami2134's MHP3rd transmog, which stores a model override in an unused
equipment byte.

### Player data

| Address | Content |
|---------|---------|
| `0x099959A0` | player base (also at `*0x089C7508`) |
| `0x09995E40` | your equipped gear (base + 0x4A0): weapon entry `+0x20`, armor entries `+0x2C + type2*12`, gender `+0x13` |
| `0x099959D0 + p*0x8C` | network records, `p` = player index, `p = 0` is you |

Equipment entry (12 bytes, same layout everywhere):

| Offset | Type | Content |
|--------|------|---------|
| +0 | u8 | 1 |
| +1 | u8 | type2 (0 legs, 1 head, 2 chest, 3 arms, 4 waist, 5 blademaster weapon, 6 gunner weapon) |
| +2 | u16 | equipment ID (eid) |
| +4 | u8 | armor: level. weapon: 0 |
| +5 | u8 | unused (0) |
| +6..+B | 3×u16 | decorations |

Network record (`0x8C` bytes): `+0x10` gender, `+0x15 + type2*4` pigment color index,
`+0x2C` hair color, `+0x30` weapon entry, `+0x3C + type2*12` armor entries.

`0x0885298C(base)` copies your gear into your record (whole halfword at entry +4, so +5 too). It is
called from the area/menu code (5 call sites in the `0x09A6xxxx` overlay), so an update reaches
others after re-equipping plus an area change or rejoin. The packet is serialized per field, not as
a raw copy of the record: the padding bytes at `+0x29..+0x2B` do **not** arrive. The record's size
(`0x8C`) is passed at `0x09AC6218`.

The code around `0x088D0CD0` initializes another player's hunter entity from a record (copies all
fields, then calls the model getters below).

### Model getters

| Address | Function |
|---------|----------|
| `0x088517A8` | getNetArmorModel(base, player, p): reads the record (gender `+0x10`, eid `+0x3E + type2*12`) |
| `0x08851994` | getLocalArmorModel(base, p): reads your equipped gear |
| `0x088515D0` | getArmorModel(_, gender, p, eid) |
| `0x08851CE8` | getNetPigmentFlag(base, player, p): armor table byte +19 of the record's eid (`lbu v0, 0x13(v0)` at `0x08851D64`) |
| `0x08851E4C` | getNetWeaponModel(base, player): type byte `+0x31` 5 → `0x089574C8 + eid*24`, otherwise gunner table `0x0895E098 + eid*28` |
| `0x0885CB60` | getArmorEntry(_, type2, eid) |
| `0x08856C3C` | p → type2 |

Their slot parameter `p` is 0 legs, 1 hair, 2 head, 3 chest, 4 arms, 5 waist (type2 = p - 1, legs 0).

### Encoding

All in your own network record only; your equipped gear (and the save file) is never touched.

| Bits | Location | Content |
|------|----------|---------|
| armor model, 9 bits per slot | bits 0-7: armor entry `+5`; bit 8: weapon entry `+4` bit `type2` | 0 = nothing sent, `0x1FF` = model -1, else model + 1 |
| pigment on/off per slot | weapon entry `+4` bit `5 + type2` | 1 = armor table byte +19 is non-zero |
| pigment info present | weapon entry `+4` bit 10 | set by every online armor sender |
| weapon model, 10 bits | bits 0-4: weapon entry `+4` bits 11-15; bits 5-9: bit 7 of each armor entry's level byte (`+4`, slot = bit - 5) | 0 = nothing sent, else model + 1 |

Receiver pigment: off → 0; on → the receiver's own flag if non-zero, else 2 (what the pigment
enable codes write). Armor models are at most ~341 and weapon models at most 552 in FUComplete v1.4.0.
The weapon code (since v2.1) sends blademaster (type 5) and gunner (type 6) weapons; v2.0 only type 5.

### Compatibility rules

Many players may run different versions of these codes, so every version must work with every other:

- Never change the meaning of an existing bit; only use free bits for new features.
- Receivers read only the bits they know, so newer senders never break older receivers.
- 0 always means "nothing sent": the receiver then falls back to the game's own lookup, so an older
  sender that lacks a feature simply shows the real gear.
- The armor and weapon codes keep each other's bits (armor: weapon `+4` bits 0-10; weapon: bits 11-15
  and the level bytes' bit 7), so any mix of versions of the two codes works.
- Probably still free: bits 4-6 of each armor entry's level byte (levels seen so far: 4-8; check the
  maximum before using them), 15 bits in total. Weapon `+4` and the armor `+5` bytes are fully used.

### Hooks and code caves

| Code | Cave | Hook | Replaces |
|------|------|------|----------|
| armor sender | `0x09FF0400` | `0x08852B44` | `j 0x0880CD4C` (memcpy tail call at the end of `0x0885298C`; `$v1` = your record) |
| armor receiver | | `0x088517A8` | first 2 instructions of getNetArmorModel |
| pigment receiver | | `0x08851D64` | `lbu v0, 0x13(v0)` (`$s0` = record, `$a1` = type2) |
| weapon sender | `0x09FF0600` | `0x08852B3C` | `addiu a0, v1, 0x81; addiu a2, zero, 8` (runs before the armor sender, then continues into it) |
| weapon receiver | | `0x08851E4C` | first 2 instructions of getNetWeaponModel |

The caves are in the `0xFF`-filled region `0x09FF0000-0x09FFFFFF` (free on PPSSPP and real PSP).
The hook lines come last in each code, so the cave is complete before anything jumps into it.

### Multiplayer Marker (optional)

`online/marker.asm` (output `online/marker_codes.txt`, not on the website) marks other players in the
gathering hall who send the bits above with a `°` in front of their name.

- Hook: text function `0x08890D7C(a0 ctx, a1 x, a2 y, a3 UTF-16 string)`, replaces its first 2
  instructions. Cave `0x09FF0800`, buffers `0x09FF09A0-0x09FF09CB`.
- Hall player list: `A = *0x09A07284`, entry `i` at `A + 0x57C + i*0xC8` (`i` 0-7, 4-7 repeat 0-3),
  player count `A + 0xEE3`. Entry `+0x00`: 6-byte MAC (the game finds players by it, `0x0883B514`),
  `+0x08`: name (UTF-16), `+0x40`: weapon entry, `+0x4C + type2*12`: armor entries. Name tags
  (`0x088358A4`, `0x088359E8`) and the player list (`0x0883B8AC`) draw the names straight from it;
  your own name tag uses your save name (`0x09995E40`) instead.
- Detection: weapon `+4` bits 10-15 or bit 7 of any armor level byte (sent by either code; always 0 from
  an unmodified game).
- Self check: entry MAC == own MAC from `sceNetGetLocalEtherAddr` (import stub `0x0890BFF8`, fetched
  once). `*0x089C7508 + 0x28` is **not** your hall index (0 on host and guest). If the MAC can't be
  fetched, the self check is skipped (rather mark yourself than miss another player).
- Font: Shift-JIS symbols are full width; Latin-1/ASCII are half width. Names are UTF-16.
- Quest displays use other copies of the names, so the marker only appears in the hall.

### Debugging online

Save states are disabled while ad-hoc is active. PPSSPP's remote debugger (Settings → Tools →
Developer tools → *Allow remote debugger*) exposes a WebSocket at `ws://127.0.0.1:<port>/debugger`
(find the port with `lsof -nP -iTCP -sTCP:LISTEN -c PPSSPP`); `{"event": "memory.read", "address": ..., "size": ...}`
returns base64 memory, so the records of all players can be read live: `online/read_records.py`
does that and decodes what each player sends (`pip install websocket-client`). A second PPSSPP instance needs
its own MAC address (`[SystemParam] MacAddress` in `ppsspp.ini`), or the ad-hoc server merges both players.


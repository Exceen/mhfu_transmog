#!/usr/bin/env python3
"""
MHFU Equipment Write & Model Loading Analysis
=============================================
Searches EBOOT and FUComplete code for sh (store halfword) instructions
that write to equipment slot offsets, and traces the model loading flow.

Run with: python3.14 find_equip_write.py
"""

import struct
import zstandard

# ── Load save state ──────────────────────────────────────────────────────────
print("Loading save state...")
with open("/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE/ULJM05500_1.01_0.ppst", 'rb') as f:
    raw = f.read()

data = zstandard.ZstdDecompressor().decompress(raw[0xB0:], max_output_size=128 * 1024 * 1024)
print(f"Decompressed state size: {len(data)} bytes (0x{len(data):X})")

RAM_OFFSET = 0x48
PSP_RAM_BASE = 0x08000000

def psp_to_file(psp_addr):
    return psp_addr - PSP_RAM_BASE + RAM_OFFSET

def read_u32(psp_addr):
    return struct.unpack_from('<I', data, psp_to_file(psp_addr))[0]

def read_u16(psp_addr):
    return struct.unpack_from('<H', data, psp_to_file(psp_addr))[0]

def read_s16(psp_addr):
    return struct.unpack_from('<h', data, psp_to_file(psp_addr))[0]

def sign_extend_16(val):
    return val - 0x10000 if val & 0x8000 else val

REG = ['zero','at','v0','v1','a0','a1','a2','a3',
       't0','t1','t2','t3','t4','t5','t6','t7',
       's0','s1','s2','s3','s4','s5','s6','s7',
       't8','t9','k0','k1','gp','sp','fp','ra']

def disasm(addr, instr):
    op = (instr >> 26) & 0x3F
    rs = (instr >> 21) & 0x1F; rt = (instr >> 16) & 0x1F
    rd = (instr >> 11) & 0x1F; shamt = (instr >> 6) & 0x1F
    funct = instr & 0x3F
    imm = instr & 0xFFFF; simm = sign_extend_16(imm)
    t26 = instr & 0x03FFFFFF
    if instr == 0: return 'nop'
    if op == 0:
        if funct == 0x08: return f'jr ${REG[rs]}'
        if funct == 0x09: return f'jalr ${REG[rd]}, ${REG[rs]}'
        if funct in (0,2,3):
            nm = {0:'sll',2:'srl',3:'sra'}[funct]
            return f'{nm} ${REG[rd]}, ${REG[rt]}, {shamt}'
        if funct == 0x21: return f'addu ${REG[rd]}, ${REG[rs]}, ${REG[rt]}'
        if funct == 0x23: return f'subu ${REG[rd]}, ${REG[rs]}, ${REG[rt]}'
        if funct == 0x24: return f'and ${REG[rd]}, ${REG[rs]}, ${REG[rt]}'
        if funct == 0x25: return f'or ${REG[rd]}, ${REG[rs]}, ${REG[rt]}'
        if funct == 0x2A: return f'slt ${REG[rd]}, ${REG[rs]}, ${REG[rt]}'
        if funct == 0x2B: return f'sltu ${REG[rd]}, ${REG[rs]}, ${REG[rt]}'
        return f'R(0x{funct:02x}) ${REG[rd]},${REG[rs]},${REG[rt]}'
    tgt = (addr & 0xF0000000) | (t26 << 2)
    btgt = (addr + 4 + (simm << 2)) & 0xFFFFFFFF
    m = {
        0x02:f'j 0x{tgt:08X}', 0x03:f'jal 0x{tgt:08X}',
        0x04:f'beq ${REG[rs]},${REG[rt]},0x{btgt:08X}',
        0x05:f'bne ${REG[rs]},${REG[rt]},0x{btgt:08X}',
        0x09:f'addiu ${REG[rt]},${REG[rs]},{simm}',
        0x0C:f'andi ${REG[rt]},${REG[rs]},0x{imm:04X}',
        0x0D:f'ori ${REG[rt]},${REG[rs]},0x{imm:04X}',
        0x0F:f'lui ${REG[rt]},0x{imm:04X}',
        0x23:f'lw ${REG[rt]},{simm}(${REG[rs]})',
        0x24:f'lbu ${REG[rt]},{simm}(${REG[rs]})',
        0x25:f'lhu ${REG[rt]},{simm}(${REG[rs]})',
        0x28:f'sb ${REG[rt]},{simm}(${REG[rs]})',
        0x29:f'sh ${REG[rt]},{simm}(${REG[rs]})',
        0x2B:f'sw ${REG[rt]},{simm}(${REG[rs]})',
        0x15:f'bnel ${REG[rs]},${REG[rt]},0x{btgt:08X}',
    }
    return m.get(op, f'op=0x{op:02X} raw=0x{instr:08X}')

def dump(start, count, highlight=None):
    for i in range(count):
        a = start + i*4
        inst = read_u32(a)
        mark = '>>>' if a == highlight else '   '
        print(f'  {mark} 0x{a:08X}: {inst:08X}  {disasm(a, inst)}')


# ══════════════════════════════════════════════════════════════════════════════
# PART 1: Equipment Slot Array Structure
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 90)
print("PART 1: EQUIPMENT SLOT ARRAY")
print("=" * 90)

game_state = read_u32(0x089C7508)
print(f"\ngame_state pointer: 0x{game_state:08X} (loaded from 0x089C7508)")

# Slot address calculator at 0x088567AC:
# result = game_state + slot_index * 4 + 0x6AEA6
# Each slot: [equip_id:u16][signed_value:i16] = 4 bytes
# 24 slots total (0-23)

base = game_state + 0x6AEA6
print(f"Equipment array base: game_state + 0x6AEA6 = 0x{base:08X}")
print(f"Format: [equip_id:u16][value:i16] per slot, 4 bytes each, 24 slots")
print()

for i in range(24):
    addr = base + i * 4
    eid = read_u16(addr)
    val = read_s16(addr + 2)
    if eid != 0:
        print(f"  Slot {i:2d}: equip_id={eid:5d} (0x{eid:04X}), value={val:6d}  @ 0x{addr:08X}")


# ══════════════════════════════════════════════════════════════════════════════
# PART 2: sh Instructions Writing to Equipment Offsets
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 90)
print("PART 2: sh (STORE HALFWORD) TO EQUIPMENT AREA OFFSETS")
print("=" * 90)

# Equipment slot destinations in the character struct (from bulk copy function 0x088D903C):
# Slot layout: type1:u8, type2:u8, equip_id:u16, count:u16, deco1:i16, deco2:i16, deco3:i16
# = 12 bytes per slot
# Weapon:  s1+0x4E8
# Head:    s1+0x4F4
# Body:    s1+0x500
# Arms:    s1+0x50C
# Waist:   s1+0x518
# Legs:    s1+0x524

SLOT_INFO = {
    0x4EA: "Weapon equip_id", 0x4F6: "Head equip_id",
    0x502: "Body equip_id", 0x50E: "Arms equip_id",
    0x51A: "Waist equip_id", 0x526: "Legs equip_id",
    0x4E8: "Weapon type", 0x4F4: "Head type",
    0x500: "Body type", 0x50C: "Arms type",
    0x518: "Waist type", 0x524: "Legs type",
}

EQUIP_AREA_MIN = 0x4D0
EQUIP_AREA_MAX = 0x5CF

SEARCH_RANGES = [
    ("EBOOT", 0x08800000, 0x08960000),
    ("FUC",   0x0891C000, 0x0892E000),
]

for region_name, region_start, region_end in SEARCH_RANGES:
    print(f"\n--- {region_name} (0x{region_start:08X}-0x{region_end:08X}) ---")
    found = 0
    for addr in range(region_start, region_end, 4):
        try: instr = read_u32(addr)
        except: continue
        if (instr >> 26) & 0x3F != 0x29: continue
        offset = sign_extend_16(instr & 0xFFFF)
        rs = (instr >> 21) & 0x1F
        rt = (instr >> 16) & 0x1F
        if EQUIP_AREA_MIN <= offset <= EQUIP_AREA_MAX:
            found += 1
            label = SLOT_INFO.get(offset, "")
            if label:
                label = f" ** {label} **"
            print(f"  0x{addr:08X}: sh ${REG[rt]}, {offset}(${REG[rs]})  [0x{offset:04X}]{label}")
    print(f"  Total: {found} sh instructions with offset in [0x{EQUIP_AREA_MIN:X}-0x{EQUIP_AREA_MAX:X}]")


# ══════════════════════════════════════════════════════════════════════════════
# PART 3: The Bulk Equipment Copy Function (0x088D903C)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 90)
print("PART 3: BULK EQUIPMENT COPY FUNCTION (0x088D903C)")
print("=" * 90)
print("""
This function copies all 6 equipment slots from the inventory/game data
to the character's equipped-item struct. It is a FUComplete-modified
function (no callers found in EBOOT - likely called via function pointer
or from FUComplete hooks).

Source: s0 = game_state + 0x4A0 (equipment data table)
Dest:   s1 = character's equipment struct (passed as a0)

Key operations:
  - Copies slot data for weapon(+0x4E8), head(+0x4F4), body(+0x500),
    arms(+0x50C), waist(+0x518), legs(+0x524)
  - Each slot: sb type1, sb type2, sh equip_id, sh count, sh deco1-3
  - Calls 0x0885DF30 to look up model/icon ID from equip_id
  - Stores model_id at s1+0x534
  - Calls 0x0885CDF8/0x0885CE14/0x0885CDB0 for equipment property lookups
""")
dump(0x088D903C, 30)
print("  ... (continues with per-slot copies) ...")


# ══════════════════════════════════════════════════════════════════════════════
# PART 4: Equipment Change Handler (0x08829948)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 90)
print("PART 4: EQUIPMENT CHANGE HANDLER (0x08829948)")
print("=" * 90)
print("""
Callers:
  0x0881D7A8: jal 0x08829948  (equip menu handler, button type 0)
  0x0881E7D4: jal 0x08829948  (equip menu handler, other types)
  0x0881EA38: jal 0x08829948  (equip menu handler)

Parameters: a0=entity, a1=slot_type, stack=equip_ids

Flow:
  1. Resolves slot addresses via 0x088567AC
  2. Calls 0x08829C5C(entity, equip_struct) to do the actual swap
  3. Calls 0x088DA420(equip_struct, ...) to update derived properties
  4. Calls 0x088DA948(equip_struct) to update visual indices
  5. Searches equipment array to find new slot positions
  6. Stores results at s5+0x648 (table index), s5+0x686 (secondary index)
  7. If conditions met, calls 0x088DB284(equip_struct) to sync equip array

Key sh writes in this function:
  0x08829A28: sh v0, 0x686(s5) - store equipment index
  0x08829B78: sh a1, 0x648(s5) - store slot reference
  0x08829BB8: sh v1, 0x686(s5) - store equipment index
""")
dump(0x08829948, 20)
print("  ...")


# ══════════════════════════════════════════════════════════════════════════════
# PART 5: Model/Visual Update Functions
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 90)
print("PART 5: MODEL/VISUAL UPDATE FUNCTIONS")
print("=" * 90)

print("""
0x088DB2C4 - MAIN VISUAL UPDATE FUNCTION (11 callers)
  Called from: 0x0882224C, 0x08822310, 0x088223AC, 0x08828058,
              0x08834DD0, 0x08834DE8, 0x08834E2C, 0x0883A674,
              0x0883A7A4, 0x088D0E38, 0x088DCB70
  
  This function:
  - Clears visual property fields at offsets 0x634-0x67B (9 bytes * 6 slots)
  - Iterates through equipment config table at 0x089B2D00
  - For each config entry, calls 0x088DB6EC to set visual properties
  - Then processes 6 body part slots: priority, model blend, etc.

0x088DB73C - PER-SLOT VISUAL CALCULATOR
  Called from 0x088DB2C4
  Processes each armor slot for visual contribution:
    jal 0x0885CF94 with s1+0x500 (body)
    jal 0x0885CF94 with s1+0x518 (waist)
    jal 0x0885CF94 with s1+0x524 (legs)
    jal 0x0885CF94 with s1+0x4F4 (head)
    jal 0x0885CF94 with s1+0x4E8 (weapon)
    jal 0x0885D1CC for combined weapon calc

0x0885CF94 - EQUIPMENT PROPERTY CALCULATOR
  Reads equip_id at: lhu a0, 2(a1)  <-- offset +2 from slot base
  Uses equip_id to index into armor data tables at 0x0897xxxx area
  Returns stat/visual contribution values

0x0885DF30 - MODEL ID LOOKUP
  Takes equipment slot pointer in a1
  Reads slot type at a1+1, equip_id at a1+2
  Returns model/icon ID from game data tables:
    - Type 5 (weapon): table at 0x089574C8, stride=0x18
    - Type 6 (armor):  table at 0x0896E098, stride=0x1C

0x0885DF98 - MODEL DATA LOADER
  Large function for loading full model/render data
  Branches by equipment type (0=head, 1=body, 2=arms)
  Calls 0x0885AEC8 (equip_id -> equipment array index)
  Calls 0x0885C334 (model data accumulator)
""")


# ══════════════════════════════════════════════════════════════════════════════
# PART 6: Key Data Tables
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 90)
print("PART 6: KEY DATA TABLES")
print("=" * 90)
print(f"""
  game_state pointer:      0x089C7508 -> 0x{game_state:08X}
  Equipment array:         game_state + 0x6AEA6 (24 slots * 4 bytes)
  Equipment slot calc:     0x088567AC (a0=game_state, a1=index) -> address
  
  Weapon data table:       0x089574C8 (stride 0x18 = 24 bytes per entry)
  Armor data table:        0x0896E098 (stride 0x1C = 28 bytes per entry)
  
  Armor stat table:        0x089AA238 (stride 0x18 = 24 bytes, indexed by equip_id)
  Equipment config table:  0x089B2D00 (7 bytes per entry, used by visual update)
  
  Character equip struct offsets (relative to character entity):
    +0x4E8: weapon slot  (12 bytes: type1,type2,equip_id,count,d1,d2,d3)
    +0x4F4: head slot
    +0x500: body slot
    +0x50C: arms slot
    +0x518: waist slot
    +0x524: legs slot
    +0x530: pointer to ???
    +0x534: model_id (written by bulk copy)
    +0x5F3: equipment property 1
    +0x5F4: equipment property 2
    +0x5F5: equipment property 3
    +0x5F6: equipment property 4
    +0x634: visual body part 0 (model index)
    +0x63A: visual body part 0 (model param)
    +0x648: equipment table index
    +0x676: visual body part flags (6 bytes)
    +0x686: secondary equipment index
""")


# ══════════════════════════════════════════════════════════════════════════════
# PART 7: Suggested Transmog Hook Points
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 90)
print("PART 7: SUGGESTED TRANSMOG HOOK POINTS")
print("=" * 90)
print("""
APPROACH A: Hook the Visual Update Function (0x088DB2C4)
  - 11 callers, all visual-related
  - Before this function runs, swap equip_ids in the character's slot data
    with the transmog visual equip_ids
  - After it returns, restore original equip_ids
  - This ensures stats come from real equipment, visuals from transmog
  - Hook point: Replace first instruction at 0x088DB2C4 with jal to custom code

APPROACH B: Hook the Per-Slot Visual Calculator (0x088DB73C)  
  - Called from 0x088DB2C4 with the character struct
  - Before calling 0x0885CF94 for each slot, temporarily replace equip_id
  - Slot pointers: s1+0x4E8, s1+0x4F4, s1+0x500, s1+0x518, s1+0x524
  - Read equip_id at slot+2, replace with transmog_id, call, restore

APPROACH C: Hook the Model ID Lookup (0x0885DF30)
  - Called 3 times total, used in bulk equipment copy
  - Reads type at a1+1 and equip_id at a1+2
  - Could intercept and return model_id for transmog equipment instead
  - But this changes model_id which may affect other systems

APPROACH D: Hook the Equipment Array Reader (0x088567AC)
  - Central function called 94 times - too broad, would affect stats too
  - NOT recommended for transmog

RECOMMENDED: Approach A or B
  - Approach A is simplest: one hook, swap all 5 armor equip_ids before visual calc
  - Store transmog IDs in unused memory (e.g., after equipment config area)
  - In hook: save real equip_ids, write transmog IDs, call original, restore
""")

print("\nDone.")

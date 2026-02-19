#!/opt/homebrew/bin/python3
"""Read the jump table at 0x0892EC18 and disassemble each handler.
This jump table dispatches based on equipment type2 (1=head, 2=chest, etc.)"""

import struct
import zstandard
import sys

STATE_DIR = "/Users/Exceen/Documents/PPSSPP/PSP/PPSSPP_STATE"
PSP_RAM_START = 0x08000000
RAM_BASE_IN_STATE = 0x48

sys.path.insert(0, '/Users/Exceen/Downloads/mhfu_transmog')
from disasm_equip_code import disasm

def load_state(slot):
    return zstandard.ZstdDecompressor().decompress(
        open(f"{STATE_DIR}/ULJM05500_1.01_{slot}.ppst", 'rb').read()[0xB0:],
        max_output_size=128*1024*1024)

def read_u8(data, psp):
    return data[psp - PSP_RAM_START + RAM_BASE_IN_STATE]

def read_u16(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<H', data, off)[0]

def read_u32(data, psp):
    off = psp - PSP_RAM_START + RAM_BASE_IN_STATE
    return struct.unpack_from('<I', data, off)[0]

def main():
    data = load_state(0)

    JUMP_TABLE = 0x0892EC18
    TYPE_NAMES = ["type0", "HEAD", "CHEST", "ARMS", "WAIST", "LEGS", "WEAPON?"]

    print("=== Jump table at 0x0892EC18 ===\n")
    handlers = []
    for i in range(7):
        addr = read_u32(data, JUMP_TABLE + i * 4)
        name = TYPE_NAMES[i] if i < len(TYPE_NAMES) else f"type{i}"
        print(f"  type2={i} ({name:>8s}): handler at 0x{addr:08X}")
        handlers.append((i, name, addr))

    # Disassemble each handler
    for type2, name, handler_addr in handlers:
        print(f"\n{'='*80}")
        print(f"  Handler for type2={type2} ({name}) at 0x{handler_addr:08X}")
        print(f"{'='*80}")
        for j in range(40):
            addr = handler_addr + j * 4
            instr = read_u32(data, addr)
            print(f"  0x{addr:08X}: [{instr:08X}] {disasm(instr, addr)}")
            # Stop at jr $ra (return) if it's the main return
            if instr == 0x03E00008 and j > 2:  # jr $ra
                # Print one more (delay slot)
                addr2 = addr + 4
                instr2 = read_u32(data, addr2)
                print(f"  0x{addr2:08X}: [{instr2:08X}] {disasm(instr2, addr2)}")
                break

    # Also check what table the HEAD handler reads from
    # Look for lui instructions that could load table base addresses
    print(f"\n{'='*80}")
    print(f"  Search HEAD handler for table references (lui instructions)")
    print(f"{'='*80}")
    head_handler = handlers[1][2]  # type2=1 handler
    for j in range(60):
        addr = head_handler + j * 4
        instr = read_u32(data, addr)
        op = (instr >> 26) & 0x3F
        if op == 0x0F:  # lui
            rt = (instr >> 16) & 0x1F
            imm = instr & 0xFFFF
            REG_NAMES = ['zero','at','v0','v1','a0','a1','a2','a3',
                         't0','t1','t2','t3','t4','t5','t6','t7',
                         's0','s1','s2','s3','s4','s5','s6','s7',
                         't8','t9','k0','k1','gp','sp','fp','ra']
            print(f"  0x{addr:08X}: lui ${REG_NAMES[rt]}, 0x{imm:04X}")
            # Check next instruction for addiu to get full address
            next_instr = read_u32(data, addr + 4)
            next_op = (next_instr >> 26) & 0x3F
            if next_op == 0x09:  # addiu
                next_imm = next_instr & 0xFFFF
                # Sign extend
                if next_imm >= 0x8000:
                    next_imm_s = next_imm - 0x10000
                else:
                    next_imm_s = next_imm
                full_addr = (imm << 16) + next_imm_s
                print(f"           -> full address: 0x{full_addr:08X}")

    # Read what the HEAD handler's table looks like
    print(f"\n{'='*80}")
    print(f"  Analyze HEAD handler table entries for eid 102 and 252")
    print(f"{'='*80}")
    # We'll look for the table address in the head handler disassembly
    # and then read entries from it

if __name__ == '__main__':
    main()

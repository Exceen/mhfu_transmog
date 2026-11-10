; MHFU (ULJM05500, FUComplete) online ARMOR transmog, v1.0
;
; Works together with the offline transmog cheats, which rewrite the model fields of the
; armor tables. The sender looks up the model its (patched) table gives for each equipped
; piece and puts it into spare bits of its network record. The receiver uses those models
; for other players instead of looking the eids up in its own table.
;
; Equipment entry, 12 bytes: +0 u8 1, +1 u8 type2, +2 u16 eid, +4 u16 (armor: low byte level,
; high byte unused), +6..+B decorations. type2: 0 legs, 1 head, 2 chest, 3 arms, 4 waist.
;
; Network record (0x099959D0 + player*0x8C; player 0 = you):
;   +0x10 gender, +0x30 weapon entry, +0x3C armor entries (type2 * 12)
;
; Sent value per armor slot, 9 bits: 0 = nothing sent, 0x1FF = model -1, else model + 1.
;   bits 0-7: armor entry +5
;   bit 8:    weapon entry +4, bit type2
;
; Pigment on/off (armor entry +19 != 0, patched by the offline "Pigment Enable/Disable" cheats):
;   weapon entry +4, bit 5+type2; bit 10 = pigment info present. Bits 11-15 stay free.
;   (Record padding like +0x2A is NOT transmitted; only real fields are.)
;   Receiver: off -> 0; on -> its own table's flag if non-zero, else 2 (what the enable cheats write).
;
; Hooks:
;   0x08852B44  tail of 0x0885298C (copies your gear into your network record) -> cave_send
;   0x088517A8  getNetArmorModel(base, player, p) -> cave_recv
;               p: 0 legs, 1 hair (untouched), 2 head, 3 chest, 4 arms, 5 waist; type2 = p ? p-1 : 0
;   0x08851D64  getNetPigmentFlag: "lbu v0, 0x13(v0)" (s0 = record, a1 = type2) -> cave_pig

.psp

ARMOR_TABLES        equ 0x08975970      ; u32[5] table pointers, indexed by type2
MEMCPY              equ 0x0880CD4C
SEND_HOOK           equ 0x08852B44
NET_HOOK            equ 0x088517A8
PIG_HOOK            equ 0x08851D64

.create "bin/armor.bin", 0x09FF0400
.org 0x09FF0400

; ---------------------------------------------------------------------------
; Sender. Reached in place of "j MEMCPY" (its delay slot already ran).
; v1 = your network record; a0/a1/a2 = memcpy args and ra = caller, all preserved.
cave_send:
    lbu     t7, 0x10(v1)            ; gender
    lhu     t6, 0x34(v1)            ; weapon +4
    andi    t6, t6, 0xF800          ; clear our bits 0-10, keep 11-15
    ori     t6, t6, 0x0400          ; bit 10: pigment info present
    move    t0, zero                ; type2
    addiu   t9, v1, 0x3C            ; armor entry
    lui     t5, hi(ARMOR_TABLES)
@@loop:
    sll     t1, t0, 2
    addu    t1, t5, t1
    lw      t1, lo(ARMOR_TABLES)(t1)    ; table for this slot
    lhu     t2, 2(t9)               ; eid
    sll     t3, t2, 2
    addu    t3, t3, t2
    sll     t3, t3, 3               ; eid * 40
    addu    t1, t1, t3              ; armor table entry
    lbu     t4, 0x13(t1)            ; pigment flag
    sltu    t4, zero, t4            ; on/off
    addiu   t3, t0, 5
    sllv    t4, t4, t3
    or      t6, t6, t4              ; bit 5+type2
    beql    t7, zero, @@have_model
    lh      t2, 0(t1)               ; male model
    lh      t2, 2(t1)               ; female model
@@have_model:
    addiu   t2, t2, 1               ; value = model + 1
    bne     t2, zero, @@range
    nop
    b       @@store
    addiu   t2, zero, 0x1FF         ; model -1
@@range:
    sltiu   at, t2, 0x1FF
    beql    at, zero, @@store
    move    t2, zero                ; out of range: send nothing
@@store:
    sb      t2, 5(t9)               ; bits 0-7
    srl     t3, t2, 8
    andi    t3, t3, 1
    sllv    t3, t3, t0
    or      t6, t6, t3              ; bit 8 -> weapon +4 bit type2
    addiu   t9, t9, 12
    addiu   t0, t0, 1
    sltiu   at, t0, 5
    bne     at, zero, @@loop
    nop
    sh      t6, 0x34(v1)
    j       MEMCPY
    nop

; ---------------------------------------------------------------------------
; Receiver. a0 = base (0x099959A0), a1 = player, a2 = p.
cave_recv:
    sltiu   at, a2, 6
    beq     at, zero, @@orig
    addiu   t0, a2, -1              ; type2 = p - 1
    beq     a2, zero, @@legs
    addiu   at, zero, 1
    beq     a2, at, @@orig          ; hair
    nop
    b       @@have_type
    nop
@@legs:
    move    t0, zero
@@have_type:
    sll     v1, a1, 3
    subu    v1, v1, a1              ; 7 * player
    sll     t1, v1, 2
    addu    v1, v1, t1              ; 35 * player
    sll     v1, v1, 2               ; player * 0x8C
    addu    v1, a0, v1
    addiu   v1, v1, 0x30            ; network record
    sll     t1, t0, 1
    addu    t1, t1, t0
    sll     t1, t1, 2               ; type2 * 12
    addu    t1, v1, t1
    lbu     t2, 0x41(t1)            ; armor entry (+0x3C) + 5
    lhu     t3, 0x34(v1)            ; weapon +4
    srlv    t3, t3, t0
    andi    t3, t3, 1
    sll     t3, t3, 8
    or      t2, t2, t3
    beq     t2, zero, @@orig        ; nothing sent: normal lookup
    addiu   at, zero, 0x1FF
    beql    t2, at, @@ret
    ori     v0, zero, 0xFFFF        ; model -1 (the game returns it as u16)
    addiu   v0, t2, -1              ; model
@@ret:
    jr      ra
    nop
@@orig:
    sll     v1, a1, 3               ; the 2 replaced instructions
    j       NET_HOOK + 8
    subu    a1, v1, a1

; ---------------------------------------------------------------------------
; Pigment flag of another player's armor piece. Replaces "lbu v0, 0x13(v0)" at PIG_HOOK;
; its delay slot (lw ra, 0xC(sp) at PIG_HOOK+4) already ran and is harmless to repeat.
; v0 = armor table entry (receiver's table), a1 = type2, s0 = network record.
cave_pig:
    lhu     t0, 0x34(s0)            ; weapon entry (+0x30) + 4
    andi    t1, t0, 0x0400
    beq     t1, zero, @@orig        ; sender didn't send pigment info
    andi    t2, a1, 0xFF
    sltiu   at, t2, 5
    beq     at, zero, @@orig
    addiu   t2, t2, 5
    srlv    t0, t0, t2
    andi    t0, t0, 1
    beql    t0, zero, @@ret
    move    v0, zero                ; pigment off
    lbu     v0, 0x13(v0)            ; on: own flag if it has one...
    beql    v0, zero, @@ret
    addiu   v0, zero, 2             ; ...else 2
@@ret:
    j       PIG_HOOK + 4
    nop
@@orig:
    j       PIG_HOOK + 4
    lbu     v0, 0x13(v0)
cave_end:

.close

; Hook words, emitted by build.py
.create "bin/armor_hooks.bin", 0
.word 0x08000000 | ((cave_send >> 2) & 0x03FFFFFF)     ; at SEND_HOOK (delay slot kept)
.word 0x08000000 | ((cave_recv >> 2) & 0x03FFFFFF)     ; at NET_HOOK
.word 0                                                 ; at NET_HOOK + 4
.word 0x08000000 | ((cave_pig >> 2) & 0x03FFFFFF)      ; at PIG_HOOK (delay slot kept)
.close

; MHFU (ULJM05500, FUComplete) online WEAPON transmog, v2.1 - separate from the armor cheat
;
; Works together with the offline weapon transmog cheats, which rewrite weapon model fields.
; Weapon entry type (+1): 5 = blademaster weapon, 6 = gunner weapon (bowguns, bows).
; Blademaster table as the code indexes it: 0x089574C8 + eid*24, model = u16 at +0.
; Gunner table: 0x0895E098 + eid*28, model = u16 at +0. (v2.0 only handled type 5.)
;
; Sent value, 10 bits: 0 = nothing sent, else model + 1 (models go up to 550).
;   bits 0-4: weapon entry +4, bits 11-15 (bits 0-10 belong to the armor cheat)
;   bits 5-9: bit 7 of each armor entry's level byte (+4), armor entry type2 = bit - 5
;
; Network record (0x099959D0 + player*0x8C): +0x30 weapon entry (+0x31 type 5, +0x32 eid,
; +0x34 u16), +0x3C armor entries (12 bytes each).
;
; Hooks:
;   0x08852B3C  in 0x0885298C after all fields are copied, just before the armor cheat's
;               hook at 0x08852B44 (so both cheats work alone or together) -> cave_wsend
;   0x08851E4C  getNetWeaponModel(base, player) -> cave_wrecv

.psp

WEAPON_TABLE        equ 0x089574C8
GUNNER_TABLE        equ 0x0895E098
WSEND_HOOK          equ 0x08852B3C
WRECV_HOOK          equ 0x08851E4C

.create "bin/weapon.bin", 0x09FF0600
.org 0x09FF0600

; ---------------------------------------------------------------------------
; Sender. Replaces "addiu a0, v1, 0x81 ; addiu a2, zero, 8". v1 = your network record.
cave_wsend:
    lbu     t0, 0x31(v1)            ; entry type
    addiu   at, zero, 5
    beq     t0, at, @@blade
    lhu     t1, 0x32(v1)            ; eid
    addiu   at, zero, 6
    bne     t0, at, @@done          ; neither weapon type
    sll     t2, t1, 3
    subu    t2, t2, t1
    sll     t2, t2, 2               ; eid * 28
    lui     t3, hi(GUNNER_TABLE)
    addu    t3, t3, t2
    b       @@model
    lhu     t2, lo(GUNNER_TABLE)(t3)    ; model (from your patched table)
@@blade:
    sll     t2, t1, 1
    addu    t2, t2, t1
    sll     t2, t2, 3               ; eid * 24
    lui     t3, hi(WEAPON_TABLE)
    addu    t3, t3, t2
    lhu     t2, lo(WEAPON_TABLE)(t3)    ; model (from your patched table)
@@model:
    addiu   t2, t2, 1               ; value = model + 1
    sltiu   at, t2, 0x400
    beql    at, zero, @@have
    move    t2, zero                ; out of range: send nothing
@@have:
    lhu     t3, 0x34(v1)            ; weapon +4
    andi    t3, t3, 0x07FF          ; keep the armor cheat's bits
    andi    t4, t2, 0x1F
    sll     t4, t4, 11
    or      t3, t3, t4
    sh      t3, 0x34(v1)
    srl     t2, t2, 5               ; bits 5-9
    addiu   t5, v1, 0x40            ; armor entry 0 (+0x3C) level byte (+4)
    addiu   t0, zero, 5
@@loop:
    lbu     t3, 0(t5)
    andi    t3, t3, 0x7F
    andi    t4, t2, 1
    sll     t4, t4, 7
    or      t3, t3, t4
    sb      t3, 0(t5)
    srl     t2, t2, 1
    addiu   t0, t0, -1
    bne     t0, zero, @@loop
    addiu   t5, t5, 12
@@done:
    addiu   a0, v1, 0x81            ; the 2 replaced instructions
    j       WSEND_HOOK + 8
    addiu   a2, zero, 8

; ---------------------------------------------------------------------------
; Receiver. a0 = base (0x099959A0), a1 = player.
cave_wrecv:
    sll     v1, a1, 3
    subu    v1, v1, a1              ; 7 * player
    sll     t1, v1, 2
    addu    v1, v1, t1              ; 35 * player
    sll     v1, v1, 2               ; player * 0x8C
    addu    v1, a0, v1
    addiu   v1, v1, 0x30            ; network record
    lbu     t0, 0x31(v1)            ; entry type
    addiu   t0, t0, -5
    sltiu   at, t0, 2               ; 5 (blademaster) or 6 (gunner)
    beq     at, zero, @@orig
    lhu     t1, 0x34(v1)
    srl     t1, t1, 11              ; bits 0-4
    addiu   t5, v1, 0x40            ; armor level bytes
    addiu   t2, zero, 5             ; bit position
@@loop:
    lbu     t3, 0(t5)
    srl     t3, t3, 7
    sllv    t3, t3, t2
    or      t1, t1, t3
    addiu   t2, t2, 1
    sltiu   at, t2, 10
    bne     at, zero, @@loop
    addiu   t5, t5, 12
    beq     t1, zero, @@orig        ; nothing sent: normal lookup
    nop
    jr      ra
    addiu   v0, t1, -1              ; model
@@orig:
    sll     v0, a1, 3               ; the 2 replaced instructions
    j       WRECV_HOOK + 8
    subu    v1, v0, a1
weapon_end:

.close

.create "bin/weapon_hooks.bin", 0
.word 0x08000000 | ((cave_wsend >> 2) & 0x03FFFFFF), 0     ; at WSEND_HOOK, +4
.word 0x08000000 | ((cave_wrecv >> 2) & 0x03FFFFFF), 0     ; at WRECV_HOOK, +4
.close

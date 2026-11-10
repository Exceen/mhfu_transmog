; MHFU (ULJM05500, FUComplete) Multiplayer Marker v2.1 - optional, not on the website
;
; Gathering hall: marks OTHER players who run the Multiplayer transmog codes with "°"
; ("°Name") in the name tags and the player list. Nothing stored is changed: the
; name is copied into BUF with the symbol added, and only the string pointer passed to
; the text function is swapped.
;
; Hall player array: A = *0x09A07284, entry i at A + 0x57C + i*0xC8 (i = 0..7, 4-7 repeat):
;   +0x00 6 bytes MAC address (the game matches players by it, see 0x0883B514)
;   +0x08 name, UTF-16
;   name+0x3C u16  weapon entry +4   (bit 10: armor code marker, bits 11-15: weapon code)
;   name+0x48 + slot*12 u8  armor level (bit 7: weapon code)
; Self check: entry MAC == own MAC from sceNetGetLocalEtherAddr (stub 0x0890BFF8),
; fetched once and cached in MACBUF (FLAG = 0 once valid). If the MAC can't be fetched,
; the self check is skipped: better to mark yourself than to miss another player.
; Text function 0x08890D7C(a0 ctx, a1 x, a2 y, a3 utf16 string).

.psp

TEXT_HOOK  equ 0x08890D7C
HALL_PTR   equ 0x09A07284
GET_MAC    equ 0x0890BFF8       ; import stub sceNetGetLocalEtherAddr(u8 *mac)
BUF        equ 0x09FF09A0       ; marked name, 0x18 bytes
MACBUF     equ 0x09FF09C0       ; own MAC, 8 bytes
FLAG       equ 0x09FF09C8       ; 0 = MACBUF valid (region starts as 0xFF)

.create "bin/marker.bin", 0x09FF0800
.org 0x09FF0800

cave_text:
    lui     v0, HALL_PTR >> 16
    lw      v0, (HALL_PTR & 0xFFFF)(v0)
    beq     v0, zero, @@orig
    nop
    addiu   v0, v0, 0x584           ; name of entry 0
    move    t8, zero
    li      t9, 8
@@find:
    beq     a3, v0, @@found
    nop
    addiu   v0, v0, 0xC8
    addiu   t8, t8, 1
    bne     t8, t9, @@find
    nop
    b       @@orig
    nop
@@found:                            ; v0 = name
    lui     t9, 0x09FF
    lw      t8, (FLAG & 0xFFFF)(t9)
    beq     t8, zero, @@have
    nop
    addiu   sp, sp, -0x20           ; fetch own MAC once
    sw      ra, 0x00(sp)
    sw      a0, 0x04(sp)
    sw      a1, 0x08(sp)
    sw      a2, 0x0C(sp)
    sw      a3, 0x10(sp)
    sw      v0, 0x14(sp)
    sw      t0, 0x18(sp)
    lui     a0, MACBUF >> 16
    jal     GET_MAC
    addiu   a0, a0, MACBUF & 0xFFFF
    lui     t9, 0x09FF
    sw      v0, (FLAG & 0xFFFF)(t9)
    lw      ra, 0x00(sp)
    lw      a0, 0x04(sp)
    lw      a1, 0x08(sp)
    lw      a2, 0x0C(sp)
    lw      a3, 0x10(sp)
    lw      v0, 0x14(sp)
    lw      t0, 0x18(sp)
    addiu   sp, sp, 0x20
    lw      t8, (FLAG & 0xFFFF)(t9)
    bne     t8, zero, @@other       ; no MAC: skip the self check
    nop
@@have:                             ; t9 = 0x09FF0000
    lw      t8, -8(v0)              ; entry MAC bytes 0-3
    lw      v1, (MACBUF & 0xFFFF)(t9)
    bne     t8, v1, @@other
    nop
    lhu     t8, -4(v0)              ; MAC bytes 4-5
    lhu     v1, (MACBUF & 0xFFFF) + 4(t9)
    beq     t8, v1, @@orig          ; it's you: never mark
    nop
@@other:
    lhu     t8, 0x3C(v0)
    andi    t8, t8, 0xFC00          ; armor marker or weapon bits
    bne     t8, zero, @@mark
    nop
    lbu     t8, 0x48(v0)
    lbu     t9, 0x54(v0)
    or      t8, t8, t9
    lbu     t9, 0x60(v0)
    or      t8, t8, t9
    lbu     t9, 0x6C(v0)
    or      t8, t8, t9
    lbu     t9, 0x78(v0)
    or      t8, t8, t9
    andi    t8, t8, 0x80            ; weapon bits in the level bytes
    beq     t8, zero, @@orig
    nop
@@mark:
    lui     v1, BUF >> 16
    addiu   v1, v1, BUF & 0xFFFF
    li      t8, 0x00B0              ; °
    sh      t8, 0(v1)
    addiu   t9, v1, 0x12            ; copy at most 9 halfwords
@@copy:
    lhu     t8, 0(v0)
    sh      t8, 2(v1)
    addiu   v0, v0, 2
    beq     t8, zero, @@use
    addiu   v1, v1, 2
    bne     v1, t9, @@copy
    nop
    sh      zero, 2(v1)             ; unterminated name: cut it off
@@use:
    lui     a3, BUF >> 16
    addiu   a3, a3, BUF & 0xFFFF
@@orig:
    addiu   sp, sp, -0x10           ; the 2 replaced instructions
    j       TEXT_HOOK + 8
    sw      ra, 0xC(sp)
marker_end:

.close

.create "bin/marker_hooks.bin", 0
.word 0x08000000 | ((cave_text >> 2) & 0x03FFFFFF), 0     ; at TEXT_HOOK, +4
.close

; MHFU (ULJM05500, FUComplete) Multiplayer transmog: keep the sent bits out of the live hunters.
; Part of BOTH the armor and the weapon cheat since v3.3 (identical lines in both, so they work
; alone or together).
;
; The sent values sit in the halfword at entry +4 of the weapon and of each armor piece of the
; network records (see armor.asm / weapon.asm). Two functions build a hunter object from a record
; and copy those halfwords as they are (object +0x4EC weapon, +0x4F8 + type2*12 armor):
;   0x088D0BE0  village / gathering hall, on every area change
;   0x088DF914  quest start
; The game then uses them as the armor level (16 bit: "Lv 13318", defense) and, for gunner
; weapons, as attachment flags (bits 4-7, e.g. the zoom scope). So the copies are cleaned:
;   armor:  low byte without bit 7 = the real level (bit 7 and +5 are transmog bits)
;   weapon: your own hunter (object +0x1E6 = player 0): the value of your equipped gear
;           (base + 0x4C4; here the record address is the base).
;           Other players: bit 10 set (an armor sender overwrote bits 0-10) -> 0,
;           else bits 0-9 (their real value; bits 11-15 belong to the weapon cheat).
;
; Each hook is "jal" at the address of the original "lhu" with that "lhu" as its delay slot
; (it replaces the "sh" that followed). Both functions save ra in their prologue.

.psp

.create "bin/clean.bin", 0x09FF0780
.org 0x09FF0780

; 0x088D0D34. a3 = base + player*0x8C, s1 = hunter object, a0 = weapon +4
clean_wb:
    lhu     at, 0x1E6(s1)           ; player index
    beql    at, zero, @@store
    lhu     a0, 0x4C4(a3)           ; you: equipped weapon +4
    andi    at, a0, 0x0400
    andi    a0, a0, 0x03FF
    movn    a0, zero, at
@@store:
    jr      ra
    sh      a0, 0x4EC(s1)

; 0x088DFA34. t0 = base + player*0x8C, s0 = hunter object, a1 = weapon +4
clean_wa:
    lhu     at, 0x1E6(s0)
    beql    at, zero, @@store
    lhu     a1, 0x4C4(t0)
    andi    at, a1, 0x0400
    andi    a1, a1, 0x03FF
    movn    a1, zero, at
@@store:
    jr      ra
    sh      a1, 0x4EC(s0)

; 0x088D0D74. a1 = armor +4, t0 = hunter object + type2*12
clean_ab:
    andi    a1, a1, 0x7F
    jr      ra
    sh      a1, 0x4F8(t0)

; 0x088DFA74. a2 = armor +4, t1 = hunter object + type2*12
clean_aa:
    andi    a2, a2, 0x7F
    jr      ra
    sh      a2, 0x4F8(t1)
clean_end:

.close

; Hook words, emitted by build.py
.create "bin/clean_hooks.bin", 0
.word 0x0C000000 | ((clean_wb >> 2) & 0x03FFFFFF)      ; at 0x088D0D34
.word 0x94E40064                                         ; at 0x088D0D38: lhu a0, 0x64(a3)
.word 0x0C000000 | ((clean_ab >> 2) & 0x03FFFFFF)      ; at 0x088D0D74
.word 0x94450040                                         ; at 0x088D0D78: lhu a1, 0x40(v0)
.word 0x0C000000 | ((clean_wa >> 2) & 0x03FFFFFF)      ; at 0x088DFA34
.word 0x95050064                                         ; at 0x088DFA38: lhu a1, 0x64(t0)
.word 0x0C000000 | ((clean_aa >> 2) & 0x03FFFFFF)      ; at 0x088DFA74
.word 0x94660040                                         ; at 0x088DFA78: lhu a2, 0x40(v1)
.close

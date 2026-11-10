; MHFU (ULJM05500, FUComplete v1.4.0) PER-SET TRANSMOG, an add-on for the In-Game Transmog Picker
;
; Every equipment set (item box -> Change Equipment -> Equipment Set, 20 per character) remembers
; the looks of its pieces:
;   - "Reg Curr Equip" and "EditEquipmentSet -> Register" store, for each piece of the set, the look
;     the picker currently gives it (or "its own look").
;   - "Equipment Set" puts exactly these looks back on the pieces while the set is equipped.
; So the same piece can look different in different sets. Looks picked in the Arrange menu work as
; before; they become part of a set the next time that set is registered.
;
; Needs the In-Game Transmog Picker of the same version: it calls the picker's rule functions
; (addresses from bin/picker_syms.inc, written by build.py) and does nothing while the picker's
; rules aren't loaded.
;
; Storage: one file per character, ms0:/PSP/SAVEDATA/MHFU_TRANSMOG_SETS_<hash>.BIN, <hash> = 8 hex
; digits computed from the character name (save data +0, 8 UTF-16 chars). The save data is never
; touched. File = magic "TMS1" + 20 sets x 6 slots x 8 bytes.
; Slot record, 8 bytes: +0 u16 0x8000 | type << 12 | eid of the piece (0 = nothing stored),
;   +2 s16 look model male (weapons: model), +4 s16 female, +6 u8 pigment flag,
;   +7 u8 1 = has a look, 0 = shows its own look.
; Slots in set order: weapon, legs, head, chest, arms, waist (= equipment type 0-4 for armor).
;
; Hooks (both in the EBOOT, the menus themselves are in the village overlay):
;   0x0888368C  play menu sound; two of its callers are the "register" confirmations:
;               ra = 0x09ADC570  Reg Curr Equip      (s4 = menu state S, set index S+0x7F,
;                                                     pieces = equipped box indexes, save +0x4020)
;               ra = 0x09ADB3F0  EditEquipmentSet    (s1 = S, set index S+0x7F,
;                                                     pieces = edited set at S+0xA2)
;   0x088507AC  equip the box piece a1 (a0 = player base); called once per slot by the set equip
;               function 0x09AE6FF0:
;               ra = 0x09AE702C  weapon              (s3 = the set's 32-byte entry)
;               ra = 0x09AE7064  armor, s1 = 12 * i  (s3 = set entry + 2 * i)

.psp
.include "bin/picker_syms.inc"      ; find_rule, find_word, entry_addr, put3, save_file,
                                    ; PICKER_DATA, PICKER_RUN_MAGIC

CAVE            equ 0x09FF84E0
DATA            equ 0x09FF8B20
; DATA + 0 cache magic, + 4 name hash of the cached sets, + 8 path (60 bytes),
; + 0x44 file: magic + sets
CACHE_MAGIC     equ 0x31534D43          ; "CMS1"
FILE_MAGIC      equ 0x31534D54          ; "TMS1"
NSETS           equ 20
SET_SIZE        equ 6 * 8
FILE_SIZE       equ 4 + NSETS * SET_SIZE
PATH            equ DATA + 8
FILEBUF         equ DATA + 0x44
SETS            equ DATA + 0x48

PLAYER_PTR      equ 0x089C7508          ; *: player base, save data at +0x4A0
SOUND_HOOK      equ 0x0888368C
EQUIP_HOOK      equ 0x088507AC
IO_OPEN         equ 0x0890B938
IO_READ         equ 0x0890B908
IO_WRITE        equ 0x0890B8F8
IO_CLOSE        equ 0x0890B918

.create "bin/sets.bin", CAVE
.org CAVE

; ---------------------------------------------------------------------------
; In place of the first 2 instructions of the sound function (a0-a3, t0-t3 and 0(sp) are its
; arguments and must survive).
cave_snd:
    li      t9, 0x09ADC570
    beq     ra, t9, @@reg
    move    t8, s4                      ; S
    li      t9, 0x09ADB3F0
    bne     ra, t9, @@orig
    move    t8, s1                      ; S
@@reg:
    addiu   sp, sp, -0x30
    sw      ra, 0x00(sp)
    sw      a0, 0x04(sp)
    sw      a1, 0x08(sp)
    sw      a2, 0x0C(sp)
    sw      a3, 0x10(sp)
    sw      t0, 0x14(sp)
    sw      t1, 0x18(sp)
    sw      t2, 0x1C(sp)
    sw      t3, 0x20(sp)
    lbu     a0, 0x7F(t8)                ; set index
    li      t9, 0x09ADC570
    beq     ra, t9, @@equipped
    addiu   a1, t8, 0xA2                ; edited set
    b       @@go
    nop
@@equipped:
    lui     a1, hi(PLAYER_PTR)
    lw      a1, lo(PLAYER_PTR)(a1)
    addiu   a1, a1, 0x44C0              ; save data + 0x4020: equipped box indexes
@@go:
    jal     snapshot
    nop
    lw      ra, 0x00(sp)
    lw      a0, 0x04(sp)
    lw      a1, 0x08(sp)
    lw      a2, 0x0C(sp)
    lw      a3, 0x10(sp)
    lw      t0, 0x14(sp)
    lw      t1, 0x18(sp)
    lw      t2, 0x1C(sp)
    lw      t3, 0x20(sp)
    addiu   sp, sp, 0x30
@@orig:
    addiu   sp, sp, -0x40               ; the 2 replaced instructions
    j       SOUND_HOOK + 8
    sw      ra, 0x3C(sp)

; ---------------------------------------------------------------------------
; In place of the first 2 instructions of the equip function (a0 = player base, a1 = box index).
cave_eq:
    li      t9, 0x09AE702C
    beq     ra, t9, @@slot
    move    t8, zero                    ; slot 0 = weapon
    li      t9, 0x09AE7064
    bne     ra, t9, @@orig
    addiu   t9, zero, 12
    divu    s1, t9
    mflo    t8                          ; armor i
    addiu   t8, t8, 1                   ; slot
@@slot:
    addiu   sp, sp, -0x20
    sw      ra, 0x00(sp)
    sw      a0, 0x04(sp)
    sw      a1, 0x08(sp)
    sll     t9, t8, 1
    addiu   t9, t9, -2
    bltzl   t9, @@have_set              ; weapon: s3 = set entry
    move    t9, zero
@@have_set:
    subu    a2, s3, t9                  ; armor: s3 - 2 * i
    addiu   t9, a0, 0x47D4              ; first set entry (save data + 0x4334)
    subu    a2, a2, t9
    srl     a0, a2, 5                   ; set index
    move    a2, a1                      ; box index
    jal     apply_slot
    move    a1, t8                      ; slot
    lw      ra, 0x00(sp)
    lw      a0, 0x04(sp)
    lw      a1, 0x08(sp)
    addiu   sp, sp, 0x20
@@orig:
    addiu   a2, a0, 0x4A0               ; the 2 replaced instructions
    j       EQUIP_HOOK + 8
    andi    a0, a1, 0xFFFF

; ---------------------------------------------------------------------------
; v0 = 1 if the picker is running (its rules are loaded).
picker_ok:
    li      v0, PICKER_DATA
    lw      v0, 0(v0)
    li      t0, PICKER_RUN_MAGIC
    xor     v0, v0, t0
    jr      ra
    sltiu   v0, v0, 1

; a0 = box index -> v0 = key (type << 16 | eid) of that box piece, or -1 if empty;
; v1 = its record id (0x8000 | type << 12 | eid).
box_key:
    li      v0, -1
    li      t0, 0xFFFF
    beq     a0, t0, @@done
    lui     t0, hi(PLAYER_PTR)
    lw      t0, lo(PLAYER_PTR)(t0)
    sll     t1, a0, 1
    addu    t1, t1, a0
    sll     t1, t1, 2
    addu    t0, t0, t1
    lbu     t1, 0x548(t0)               ; save data + 0xA8 + index * 12: +0 used
    beq     t1, zero, @@done
    lbu     t1, 0x549(t0)               ; type
    lhu     t2, 0x54A(t0)               ; eid
    sll     v0, t1, 16
    or      v0, v0, t2
    sll     v1, t1, 12
    or      v1, v1, t2
    ori     v1, v1, 0x8000
@@done:
    jr      ra
    nop

; a0 = set index (0-19), a1 = slot (0-5) -> v0 = slot record (in SETS), or 0 if out of range.
record:
    sltiu   t0, a0, NSETS
    beq     t0, zero, @@bad
    sltiu   t0, a1, 6
    beq     t0, zero, @@bad
    addiu   t0, zero, SET_SIZE
    multu   a0, t0
    mflo    t0
    sll     t1, a1, 3                   ; slot * 8
    addu    t0, t0, t1
    li      v0, SETS
    jr      ra
    addu    v0, v0, t0
@@bad:
    jr      ra
    move    v0, zero

; ---------------------------------------------------------------------------
; a0 = set index, a1 = u16[6] box indexes of its pieces: store the pieces' current looks.
snapshot:
    addiu   sp, sp, -0x20
    sw      ra, 0x00(sp)
    sw      s0, 0x04(sp)
    sw      s1, 0x08(sp)
    sw      s2, 0x0C(sp)
    sw      s3, 0x10(sp)
    move    s0, a0
    jal     picker_ok
    move    s1, a1
    beq     v0, zero, @@done
    nop
    jal     load_sets
    move    s2, zero                    ; slot
@@loop:
    move    a0, s0
    jal     record
    move    a1, s2
    beq     v0, zero, @@done
    move    s3, v0
    sll     t0, s2, 1
    addu    t0, s1, t0
    jal     box_key
    lhu     a0, 0(t0)
    sw      zero, 0(s3)
    bltz    v0, @@next                  ; empty slot
    sw      zero, 4(s3)
    sh      v1, 0(s3)
    jal     find_rule
    move    a0, v0
    beq     v0, zero, @@next            ; no look: "own look" (all zero)
    nop
    lh      t0, 4(v0)
    sh      t0, 2(s3)
    lh      t0, 6(v0)
    sh      t0, 4(s3)
    lbu     t0, 12(v0)
    sb      t0, 6(s3)
    addiu   t0, zero, 1
    sb      t0, 7(s3)
@@next:
    addiu   s2, s2, 1
    sltiu   t0, s2, 6
    bne     t0, zero, @@loop
    nop
    jal     save_sets
    nop
@@done:
    lw      ra, 0x00(sp)
    lw      s0, 0x04(sp)
    lw      s1, 0x08(sp)
    lw      s2, 0x0C(sp)
    lw      s3, 0x10(sp)
    jr      ra
    addiu   sp, sp, 0x20

; a0 = set index, a1 = slot, a2 = box index being equipped: give that piece the stored look.
apply_slot:
    addiu   sp, sp, -0x20
    sw      ra, 0x00(sp)
    sw      s0, 0x04(sp)
    sw      s1, 0x08(sp)
    sw      s2, 0x0C(sp)
    sw      s3, 0x10(sp)
    move    s0, a0
    move    s1, a1
    jal     picker_ok
    move    s2, a2
    beq     v0, zero, @@done
    nop
    jal     box_key
    move    a0, s2
    bltz    v0, @@done
    move    s2, v0                      ; key of the piece
    jal     load_sets
    sw      v1, 0x14(sp)                ; its record id
    move    a0, s0
    jal     record
    move    a1, s1
    beq     v0, zero, @@done
    move    s3, v0
    lhu     t0, 0(s3)
    lw      t1, 0x14(sp)
    bne     t0, t1, @@done              ; nothing stored for this piece
    nop
    jal     find_rule                   ; s1 = its rule (or 0)
    move    a0, s2
    move    s1, v0
    lbu     t0, 7(s3)
    bne     t0, zero, @@look
    nop
    beq     s1, zero, @@done            ; own look, and it has no rule: nothing to do
    nop
    lh      a1, 8(s1)                   ; remove the rule, as the picker's reset does
    lh      a2, 10(s1)
    lbu     a3, 13(s1)
    jal     put3
    move    a0, s2
    b       @@save
    sw      zero, 0(s1)
@@look:
    bne     s1, zero, @@have
    nop
    jal     find_word                   ; a free rule
    move    t2, zero
    beq     v0, zero, @@done            ; all rules in use
    move    s1, v0
    sw      zero, 8(s1)
    sw      zero, 12(s1)
    jal     entry_addr                  ; remember the original look
    move    a0, s2
    lh      t0, 0(v0)
    sh      t0, 8(s1)
    sltiu   t1, v1, 5
    beq     t1, zero, @@new
    nop
    lh      t0, 2(v0)
    sh      t0, 10(s1)
    lbu     t0, 19(v0)
    sb      t0, 13(s1)
@@new:
    lui     t0, 0x8000
    or      t0, t0, s2
    b       @@set
    sw      t0, 0(s1)
@@have:
    lh      t0, 4(s1)                   ; same look already: nothing to do
    lh      t1, 2(s3)
    bne     t0, t1, @@set
    lh      t0, 6(s1)
    lh      t1, 4(s3)
    bne     t0, t1, @@set
    lbu     t0, 12(s1)
    lbu     t1, 6(s3)
    beq     t0, t1, @@done
    nop
@@set:
    lh      a1, 2(s3)
    lh      a2, 4(s3)
    lbu     a3, 6(s3)
    sh      a1, 4(s1)
    sh      a2, 6(s1)
    sb      a3, 12(s1)
    jal     put3
    move    a0, s2
@@save:
    jal     save_file                   ; the picker's file
    nop
@@done:
    lw      ra, 0x00(sp)
    lw      s0, 0x04(sp)
    lw      s1, 0x08(sp)
    lw      s2, 0x0C(sp)
    lw      s3, 0x10(sp)
    jr      ra
    addiu   sp, sp, 0x20

; ---------------------------------------------------------------------------
; Make SETS hold the current character's sets (read the file if another character's are cached).
load_sets:
    addiu   sp, sp, -0x10
    sw      ra, 0x00(sp)
    sw      s0, 0x04(sp)
    lui     t0, hi(PLAYER_PTR)          ; hash of the name, 8 UTF-16 chars at save data +0
    lw      t0, lo(PLAYER_PTR)(t0)
    addiu   t0, t0, 0x4A0
    addiu   t1, t0, 16
    li      v0, 5381
@@hash:
    lhu     t2, 0(t0)
    sll     t3, v0, 5
    addu    v0, v0, t3
    addu    v0, v0, t2
    addiu   t0, t0, 2
    bne     t0, t1, @@hash
    nop
    li      s0, DATA
    lw      t0, 0(s0)
    li      t1, CACHE_MAGIC
    bne     t0, t1, @@load
    lw      t0, 4(s0)
    beq     t0, v0, @@done              ; already cached
    nop
@@load:
    sw      zero, 0(s0)
    sw      v0, 4(s0)
    li      t0, path_prefix             ; path = prefix + 8 hex digits + ".BIN"
    addiu   t1, s0, 8
@@copy:
    lbu     t2, 0(t0)
    addiu   t0, t0, 1
    beq     t2, zero, @@hex
    addiu   t1, t1, 1
    b       @@copy
    sb      t2, -1(t1)
@@hex:
    addiu   t1, t1, -1
    addiu   t3, zero, 28
@@digit:
    srlv    t2, v0, t3
    andi    t2, t2, 0xF
    sltiu   t0, t2, 10
    bnel    t0, zero, @@put
    addiu   t2, t2, 0x30                ; '0'
    addiu   t2, t2, 0x37                ; 'A' - 10
@@put:
    sb      t2, 0(t1)
    addiu   t1, t1, 1
    bne     t3, zero, @@digit
    addiu   t3, t3, -4
    li      t0, path_suffix
@@copy2:
    lbu     t2, 0(t0)
    sb      t2, 0(t1)
    addiu   t0, t0, 1
    bne     t2, zero, @@copy2
    addiu   t1, t1, 1
    addiu   t0, s0, 0x44                ; clear the sets
    addiu   t1, s0, 0x44 + FILE_SIZE
@@clear:
    sw      zero, 0(t0)
    addiu   t0, t0, 4
    bne     t0, t1, @@clear
    nop
    addiu   a0, s0, 8
    addiu   a1, zero, 1                 ; PSP_O_RDONLY
    jal     IO_OPEN
    move    a2, zero
    bltz    v0, @@ok                    ; no file yet: no sets stored
    nop
    sw      v0, 0x08(sp)
    move    a0, v0
    addiu   a1, s0, 0x44
    jal     IO_READ
    addiu   a2, zero, FILE_SIZE
    sw      v0, 0x0C(sp)
    jal     IO_CLOSE
    lw      a0, 0x08(sp)
    lw      v0, 0x0C(sp)
    addiu   t0, zero, FILE_SIZE
    bne     v0, t0, @@bad
    lw      t1, 0x44(s0)
    li      t0, FILE_MAGIC
    beq     t1, t0, @@ok
    nop
@@bad:
    addiu   t0, s0, 0x44                ; damaged file: start empty
    addiu   t1, s0, 0x44 + FILE_SIZE
@@clear2:
    sw      zero, 0(t0)
    addiu   t0, t0, 4
    bne     t0, t1, @@clear2
    nop
@@ok:
    li      t0, CACHE_MAGIC
    sw      t0, 0(s0)
@@done:
    lw      ra, 0x00(sp)
    lw      s0, 0x04(sp)
    jr      ra
    addiu   sp, sp, 0x10

save_sets:
    addiu   sp, sp, -0x10
    sw      ra, 0x00(sp)
    sw      s0, 0x04(sp)
    li      t0, FILE_MAGIC
    li      t1, FILEBUF
    sw      t0, 0(t1)
    li      a0, PATH
    addiu   a1, zero, 0x602             ; PSP_O_WRONLY | PSP_O_CREAT | PSP_O_TRUNC
    jal     IO_OPEN
    addiu   a2, zero, 0x1FF
    bltz    v0, @@done
    move    s0, v0
    move    a0, s0
    li      a1, FILEBUF
    jal     IO_WRITE
    addiu   a2, zero, FILE_SIZE
    jal     IO_CLOSE
    move    a0, s0
@@done:
    lw      ra, 0x00(sp)
    lw      s0, 0x04(sp)
    jr      ra
    addiu   sp, sp, 0x10

path_prefix:
    .asciiz "ms0:/PSP/SAVEDATA/MHFU_TRANSMOG_SETS_"
path_suffix:
    .asciiz ".BIN"
    .align 4
cave_end:

.close

; Hook words, emitted by build.py
.create "bin/sets_hooks.bin", 0
.word 0x08000000 | ((cave_snd >> 2) & 0x03FFFFFF), 0    ; at SOUND_HOOK, +4
.word 0x08000000 | ((cave_eq >> 2) & 0x03FFFFFF), 0     ; at EQUIP_HOOK, +4
.close

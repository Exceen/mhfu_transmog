; MHFU (ULJM05500, FUComplete v1.4.0) ITEM SETS - port of Kurogami2134's p3rd_item_sets
;
; Item box, main menu (Put In Item / Take Out Item / ...):
;   L / R            load item set 1 / 2: the pouch goes back into the box, then the set's items
;                    are taken out of the box into the pouch (as many as the box has)
;   Select + L / R   save the current pouch as item set 1 / 2
; Sounds: save = "open", load = "confirm", empty set = "error".
;
; Nothing is ever lost: a pouch item that doesn't fit into the box stays in its pouch slot (and
; that slot is then left out of the set). Box stacks hold at most 99, as in the game.
; Sets are stored in ms0:/PSP/SAVEDATA/MHFU_ITEM_SETS.BIN (2 sets x 24 x (u16 id, u16 count)),
; shared by all characters; the save data only changes the way the game's own menus change it.
;
; Save data (*0x089C7508 + 0x4A0): item box +0x2F88 (1000 x (u16 id, u16 count)),
; pouch +0x3F28 (24 x (u16 id, u16 count)); a working copy of the pouch is at player base +0x6AEA6.
;
; Hook: 0x0881CE38 (EBOOT menu cursor function), acting only when called from the item box main
; menu (return address 0x09AD7CAC, a2 = pressed buttons).

.psp

CAVE            equ 0x09FFA080
LOADED_MAGIC    equ 0x31534C49          ; "ILS1"

PLAYER_PTR      equ 0x089C7508
PAD_HELD        equ 0x08A5DD38          ; u32 buttons currently held
CUR_HOOK        equ 0x0881CE38
CUR_CALLER      equ 0x09AD7CAC
PLAY_SOUND      equ 0x0888368C
IO_OPEN         equ 0x0890B938
IO_READ         equ 0x0890B908
IO_WRITE        equ 0x0890B8F8
IO_CLOSE        equ 0x0890B918

BOX             equ 0x2F88 + 0x4A0      ; from the player base
BOX_SLOTS       equ 1000
POUCH           equ 0x3F28 + 0x4A0
POUCH_SHOWN     equ 0x6AEA6             ; the game's working copy of the pouch (what the menus show,
                                        ; 0x088567AC); the game keeps both copies in sync
POUCH_SLOTS     equ 24
MAX_STACK       equ 99
SET_SIZE        equ POUCH_SLOTS * 4

SND_SAVE        equ 0x11
SND_LOAD        equ 0x13
SND_ERROR       equ 0x15

.create "bin/item_sets.bin", CAVE
.org CAVE

; ---------------------------------------------------------------------------
; In place of the first 2 instructions of the cursor function (a0-a3 are its arguments).
cave_cur:
    li      t9, CUR_CALLER
    bne     ra, t9, @@orig
    andi    t8, a2, 0x0300              ; L or R pressed
    beq     t8, zero, @@orig
    nop
    addiu   sp, sp, -0x20
    sw      ra, 0x00(sp)
    sw      a0, 0x04(sp)
    sw      a1, 0x08(sp)
    sw      a2, 0x0C(sp)
    sw      a3, 0x10(sp)
    andi    a0, a2, 0x0100
    sltiu   a0, a0, 1                   ; L: set 0, R: set 1
    lui     a1, hi(PAD_HELD)
    lw      a1, lo(PAD_HELD)(a1)
    jal     action
    andi    a1, a1, 0x0001              ; Select held: save
    lw      ra, 0x00(sp)
    lw      a0, 0x04(sp)
    lw      a1, 0x08(sp)
    lw      a2, 0x0C(sp)
    lw      a3, 0x10(sp)
    addiu   sp, sp, 0x20
@@orig:
    addiu   sp, sp, -0x20               ; the 2 replaced instructions
    j       CUR_HOOK + 8
    sw      ra, 0x1C(sp)

; ---------------------------------------------------------------------------
; a0 = set (0/1), a1 = 1: save the pouch into it, 0: load it.
action:
    addiu   sp, sp, -0x30
    sw      ra, 0x10(sp)
    sw      s0, 0x14(sp)
    sw      s1, 0x18(sp)
    sw      s2, 0x1C(sp)
    sw      s3, 0x20(sp)
    sw      s4, 0x24(sp)
    move    s0, a0
    jal     load_file
    move    s1, a1
    li      s2, sets
    sll     t0, s0, 5
    sll     t1, s0, 6
    addu    t0, t0, t1                  ; set * 96
    addu    s2, s2, t0                  ; the set
    lui     s3, hi(PLAYER_PTR)
    lw      s3, lo(PLAYER_PTR)(s3)
    addiu   s3, s3, POUCH               ; the pouch
    beq     s1, zero, @@load
    nop

    move    t0, s3                      ; save: copy the pouch
    move    t1, s2
    addiu   t2, s3, SET_SIZE
@@copy:
    lw      t3, 0(t0)
    sw      t3, 0(t1)
    addiu   t0, t0, 4
    bne     t0, t2, @@copy
    addiu   t1, t1, 4
    jal     save_file
    nop
    b       @@sound
    addiu   a2, zero, SND_SAVE

@@load:
    move    t0, s2                      ; empty set: nothing to do
    addiu   t2, s2, SET_SIZE
@@check:
    lhu     t3, 0(t0)
    bne     t3, zero, @@go
    addiu   t0, t0, 4
    bne     t0, t2, @@check
    nop
    b       @@sound
    addiu   a2, zero, SND_ERROR
@@go:
    move    s4, zero                    ; 1. pouch -> box
@@put:
    sll     t0, s4, 2
    addu    t0, s3, t0
    lhu     a0, 0(t0)
    lhu     a1, 2(t0)
    beq     a0, zero, @@put_next
    nop
    beq     a1, zero, @@put_clear
    nop
    jal     box_add
    nop
    sll     t0, s4, 2
    addu    t0, s3, t0
    bne     v0, zero, @@put_next        ; didn't fit: v0 stays in the pouch
    sh      v0, 2(t0)
@@put_clear:
    sw      zero, 0(t0)
@@put_next:
    addiu   s4, s4, 1
    sltiu   t0, s4, POUCH_SLOTS
    bne     t0, zero, @@put
    nop

    move    s4, zero                    ; 2. box -> pouch, slot by slot
@@take:
    sll     t0, s4, 2
    addu    t1, s3, t0                  ; pouch slot
    lhu     t2, 0(t1)
    bne     t2, zero, @@take_next       ; still occupied (box was full)
    addu    t0, s2, t0                  ; set slot
    lhu     a0, 0(t0)
    beq     a0, zero, @@take_next
    nop
    jal     box_take
    lhu     a1, 2(t0)
    beq     v0, zero, @@take_next       ; none in the box
    sll     t0, s4, 2
    addu    t1, s3, t0
    sll     t2, s4, 2
    addu    t2, s2, t2
    lhu     t3, 0(t2)
    sh      t3, 0(t1)
    sh      v0, 2(t1)
@@take_next:
    addiu   s4, s4, 1
    sltiu   t0, s4, POUCH_SLOTS
    bne     t0, zero, @@take
    nop
    lui     t0, hi(PLAYER_PTR)          ; 3. copy the pouch to the one the menus show
    lw      t0, lo(PLAYER_PTR)(t0)
    li      t1, POUCH_SHOWN
    addu    t0, t0, t1
    move    t1, s3
    addiu   t2, s3, SET_SIZE
@@show:
    lhu     t3, 0(t1)
    sh      t3, 0(t0)
    addiu   t1, t1, 2
    bne     t1, t2, @@show
    addiu   t0, t0, 2
    addiu   a2, zero, SND_LOAD

@@sound:
    lui     a0, 0x08A6
    lw      a0, -0x21A4(a0)             ; *0x08A5DE5C, sound context
    move    a1, zero
    move    a3, zero
    move    t0, zero
    move    t1, zero
    move    t2, zero
    move    t3, zero
    jal     PLAY_SOUND
    sw      zero, 0(sp)
    lw      ra, 0x10(sp)
    lw      s0, 0x14(sp)
    lw      s1, 0x18(sp)
    lw      s2, 0x1C(sp)
    lw      s3, 0x20(sp)
    lw      s4, 0x24(sp)
    jr      ra
    addiu   sp, sp, 0x30

; ---------------------------------------------------------------------------
; a0 = item id, a1 = count -> put it into the box; v0 = count that didn't fit. Uses t0-t5.
box_add:
    lui     t0, hi(PLAYER_PTR)
    lw      t0, lo(PLAYER_PTR)(t0)
    addiu   t0, t0, BOX
    addiu   t1, t0, BOX_SLOTS * 4
    move    t4, t0
@@stack:                                ; first top up stacks of the same item
    lhu     t2, 0(t4)
    bne     t2, a0, @@stack_next
    lhu     t3, 2(t4)
    sltiu   t5, t3, MAX_STACK
    beq     t5, zero, @@stack_next
    addiu   t5, zero, MAX_STACK
    subu    t5, t5, t3                  ; room
    sltu    t2, a1, t5
    bnel    t2, zero, @@stack_put
    move    t5, a1
@@stack_put:
    addu    t3, t3, t5
    sh      t3, 2(t4)
    subu    a1, a1, t5
    beq     a1, zero, @@done
    nop
@@stack_next:
    addiu   t4, t4, 4
    bne     t4, t1, @@stack
    nop
    move    t4, t0
@@empty:                                ; then empty slots
    lhu     t2, 0(t4)
    beq     t2, zero, @@empty_put
    lhu     t3, 2(t4)
    bne     t3, zero, @@empty_next
    nop
@@empty_put:
    sltiu   t2, a1, MAX_STACK + 1
    addiu   t5, zero, MAX_STACK
    bnel    t2, zero, @@empty_store
    move    t5, a1
@@empty_store:
    sh      a0, 0(t4)
    sh      t5, 2(t4)
    subu    a1, a1, t5
    beq     a1, zero, @@done
    nop
@@empty_next:
    addiu   t4, t4, 4
    bne     t4, t1, @@empty
    nop
@@done:
    jr      ra
    move    v0, a1

; a0 = item id, a1 = wanted count -> take up to that many out of the box; v0 = count taken.
box_take:
    lui     t0, hi(PLAYER_PTR)
    lw      t0, lo(PLAYER_PTR)(t0)
    addiu   t0, t0, BOX
    addiu   t1, t0, BOX_SLOTS * 4
    move    v0, zero
@@loop:
    beq     a1, zero, @@done
    lhu     t2, 0(t0)
    bne     t2, a0, @@next
    lhu     t3, 2(t0)
    beq     t3, zero, @@next
    sltu    t5, a1, t3
    bnel    t5, zero, @@take
    move    t3, a1                      ; t3 = taken from this slot
@@take:
    lhu     t2, 2(t0)
    subu    t2, t2, t3
    sh      t2, 2(t0)
    beql    t2, zero, @@taken
    sh      zero, 0(t0)                 ; slot empty now
@@taken:
    addu    v0, v0, t3
    subu    a1, a1, t3
@@next:
    addiu   t0, t0, 4
    bne     t0, t1, @@loop
    nop
@@done:
    jr      ra
    nop

; ---------------------------------------------------------------------------
; Read the sets once (they are kept in memory after that).
load_file:
    li      t0, loaded
    lw      t1, 0(t0)
    li      t2, LOADED_MAGIC
    beq     t1, t2, @@ret
    nop
    addiu   sp, sp, -0x10
    sw      ra, 0x00(sp)
    sw      s0, 0x04(sp)
    sw      t2, 0(t0)
    li      t0, sets                    ; start empty
    addiu   t1, t0, SET_SIZE * 2
@@clear:
    sw      zero, 0(t0)
    addiu   t0, t0, 4
    bne     t0, t1, @@clear
    nop
    li      a0, path
    addiu   a1, zero, 1                 ; PSP_O_RDONLY
    jal     IO_OPEN
    move    a2, zero
    bltz    v0, @@done
    move    s0, v0
    move    a0, s0
    li      a1, sets
    jal     IO_READ
    addiu   a2, zero, SET_SIZE * 2
    jal     IO_CLOSE
    move    a0, s0
@@done:
    lw      ra, 0x00(sp)
    lw      s0, 0x04(sp)
    addiu   sp, sp, 0x10
@@ret:
    jr      ra
    nop

save_file:
    addiu   sp, sp, -0x10
    sw      ra, 0x00(sp)
    sw      s0, 0x04(sp)
    li      a0, path
    addiu   a1, zero, 0x602             ; PSP_O_WRONLY | PSP_O_CREAT | PSP_O_TRUNC
    jal     IO_OPEN
    addiu   a2, zero, 0x1FF
    bltz    v0, @@done
    move    s0, v0
    move    a0, s0
    li      a1, sets
    jal     IO_WRITE
    addiu   a2, zero, SET_SIZE * 2
    jal     IO_CLOSE
    move    a0, s0
@@done:
    lw      ra, 0x00(sp)
    lw      s0, 0x04(sp)
    jr      ra
    addiu   sp, sp, 0x10

path:
    .asciiz "ms0:/PSP/SAVEDATA/MHFU_ITEM_SETS.BIN"
    .align 4
code_end:

; Run-time data behind the code, not written by the cheat (no bytes are emitted for it).
loaded:                                 ; LOADED_MAGIC once the sets are in memory
.definelabel sets, loaded + 4           ; 2 x 24 x (u16 id, u16 count)

.close

.create "bin/item_sets_hooks.bin", 0
.word 0x08000000 | ((cave_cur >> 2) & 0x03FFFFFF), 0    ; at CUR_HOOK, +4
.close

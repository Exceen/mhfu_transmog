; MHFU (ULJM05500, FUComplete v1.4.0) IN-GAME TRANSMOG PICKER, v3.3
;
; Pick looks in the game instead of generating table-patch cheats on the website.
;
; Use (item box -> Arrange Items -> Equipment):
;   pick up the piece whose LOOK you want (Circle), move to the piece that should get that look
;   and press Square instead of Circle. Square on the picked-up piece itself resets that piece.
; Both pieces must be the same slot (weapons: the same weapon class). An equipped piece changes at
; once, others when you equip them.
;
; How it works: a rule says "equipment (type, eid) looks like models X". Applying a rule writes the
; model fields (and the armor pigment flag) of that eid's table entry, exactly what the website's
; cheats do, so everything that works with those (incl. the Multiplayer codes) works unchanged.
; Rules live in RULES (127 x 16 bytes) and in a file on the memory stick (PATH); the save data is
; never touched. The file is read once after boot and written after every change.
;
; Rule, 16 bytes: +0 u32 0x80000000 | type << 16 | eid (0 = free)
;                 +4 s16 look model male (weapons: model)   +6 s16 look model female
;                 +8 s16 original male                      +10 s16 original female
;                 +12 u8 look pigment flag                  +13 u8 original pigment flag
; type: 0 legs, 1 head, 2 chest, 3 arms, 4 waist, 5 blademaster weapon, 6 gunner weapon.
;
; Memory: the code lives at CAVE, in the low part of the main thread's 32 KB stack, which exists
; before the first cheat write (cave_frame runs from the first frame on). The data lives in the
; unused low part of a sound thread's stack (like the Multiplayer codes): the game writes now and
; then to scattered addresses low in the main thread's stack (e.g. 0x09FF99FC at boot, where v3.0
; kept its rules), but never there. That stack is created and 0xFF-filled about a second after boot;
; this only clears the run magic, so cave_frame simply loads the rules again.
;
; Hooks (both in the EBOOT, nothing is written into overlays):
;   0x08868F5C  jal sceCtrlReadBufferPositive (once per frame) -> cave_frame: load the file once,
;               finish a model reload started from the Arrange menu
;   0x0883062C  equipment compare function -> cave_ui, which acts on one caller:
;               ra = 0x09AE3410  Arrange Equipment, Square pressed on a non-empty slot
;                                (s1 = menu state, a1 = box entry under the cursor)

.psp

CAVE            equ 0x09FF9100
DATA            equ 0x09FE2000          ; run-time data, see the note on memory below
RUN_MAGIC       equ 0x324D4F47          ; "GOM2", set once the rules are loaded (new value whenever
                                        ; the data layout changes, so old save states reload)
FILE_MAGIC      equ 0x31474D54          ; "TMG1"
NRULES          equ 127                 ; keep the file format of v3.0 (2036 bytes)
RULES_SIZE      equ NRULES * 16
FILE_SIZE       equ 4 + RULES_SIZE
; DATA + 0 run magic, + 4 unused, + 8 file magic,
; + 12 rules, + PENDING: 1 while a model reload started from the Arrange menu is running
PENDING         equ 12 + RULES_SIZE

ARMOR_TABLES    equ 0x08975970          ; u32[5] table pointers by type, 40-byte entries
WEAPON_TABLE    equ 0x089574C8          ; + eid * 24, model u16 at +0
GUNNER_TABLE    equ 0x0895E098          ; + eid * 28, model u16 at +0
WEAPON_CLASS    equ 0x08975984          ; u8 per weapon model
SOUND_CTX       equ 0x08A5DE5C
PLAY_SOUND      equ 0x0888368C
CTRL_READ       equ 0x0890BBF8          ; sceCtrlReadBufferPositive
IO_OPEN         equ 0x0890B938
IO_READ         equ 0x0890B908
IO_WRITE        equ 0x0890B8F8
IO_CLOSE        equ 0x0890B918
FRAME_HOOK      equ 0x08868F5C
UI_HOOK         equ 0x0883062C
ARR_CALLER      equ 0x09AE3410          ; return address of the Arrange Equipment "Info" call
ARR_RETURN      equ 0x09AE3470          ; in that function: "return 0" (no button pressed)
; Village overlay, only called while that menu is open (or was a moment ago):
RELOAD_MODELS   equ 0x09A9C3D0          ; start reloading the hunter's models (a0 = *RELOAD_CTX)
RELOAD_FINISH   equ 0x09A9C580          ; show them (a0 = *RELOAD_CTX), once *RELOAD_BUSY is 0
RELOAD_CTX      equ 0x09B1E310
RELOAD_BUSY     equ 0x09B1E308          ; pointer to a byte that is non-zero while loading

SND_APPLY       equ 0x13
SND_RESET       equ 0x14
SND_ERROR       equ 0x15

.create "bin/transmog.bin", CAVE
.org CAVE

; ---------------------------------------------------------------------------
; Once per frame, in place of "jal sceCtrlReadBufferPositive" (a0, a1 = its arguments).
cave_frame:
    li      t0, DATA
    lw      t1, 0(t0)
    li      t2, RUN_MAGIC
    bne     t1, t2, @@init
    lw      t1, PENDING(t0)
    beq     t1, zero, @@go
    lui     t1, 0x09AA
    lw      t1, -0x3A80(t1)             ; first instruction of RELOAD_FINISH
    li      t2, 0x27BDFFF0
    bnel    t1, t2, @@go                ; the village overlay is gone: forget it
    sw      zero, PENDING(t0)
    lui     t1, 0x09B2
    lw      t1, -0x1CF8(t1)             ; *RELOAD_BUSY
    lbu     t1, 0(t1)
    bne     t1, zero, @@go              ; still loading
    nop
    sw      zero, PENDING(t0)
    addiu   sp, sp, -0x10
    sw      ra, 0(sp)
    sw      a0, 4(sp)
    sw      a1, 8(sp)
    lui     a0, 0x09B2
    jal     RELOAD_FINISH
    lw      a0, -0x1CF0(a0)             ; *RELOAD_CTX
    b       @@restore
    nop
@@init:
    addiu   sp, sp, -0x10
    sw      ra, 0(sp)
    sw      a0, 4(sp)
    jal     do_init
    sw      a1, 8(sp)
@@restore:
    lw      ra, 0(sp)
    lw      a0, 4(sp)
    lw      a1, 8(sp)
    addiu   sp, sp, 0x10
@@go:
    j       CTRL_READ
    nop

; ---------------------------------------------------------------------------
; In place of the first 2 instructions of UI_HOOK.
cave_ui:
    li      t0, ARR_CALLER
    bne     ra, t0, @@orig
    nop

    ; Arrange Equipment: Square on a piece. The game has just set "Info shown" (0x5D).
    lbu     t0, 0x3A(s1)
    addiu   t1, zero, 1
    bne     t0, t1, @@orig              ; no piece picked up: the normal Info window
    lhu     t0, 0x44(s1)                ; box index of the picked-up piece
    lhu     t1, 0x42(s1)                ; cursor
    subu    t0, t0, t1
    sll     t1, t0, 1
    addu    t1, t1, t0
    sll     t1, t1, 2
    addu    t1, a1, t1                  ; box entry of the picked-up piece
    lbu     t2, 1(t1)
    lhu     t3, 2(t1)
    sll     t2, t2, 16
    or      t2, t2, t3
    lui     t3, 0x8000
    move    a0, a1                      ; target = piece under the cursor
    jal     action
    or      a1, t2, t3                  ; look source = picked-up piece
    sb      zero, 0x5D(s1)              ; no Info window
    andi    t0, v0, 2
    bne     t0, zero, @@done            ; not possible: keep the piece picked up
    andi    t0, v0, 1
    sb      zero, 0x3A(s1)              ; put the piece down
    beq     t0, zero, @@done            ; no look changed
    lui     t1, 0x089C
    lw      t1, 0x7508(t1)
    lhu     t0, 0x42(s1)
    addiu   t1, t1, 0x44C0              ; save data + 0x4020: u16[6] box indexes of the
    addiu   t2, t1, 12                  ; equipped pieces
@@equipped:
    lhu     t3, 0(t1)
    beq     t3, t0, @@reload
    addiu   t1, t1, 2
    bne     t1, t2, @@equipped
    nop
    b       @@done
    nop
@@reload:
    lui     a0, 0x09B2
    jal     RELOAD_MODELS
    lw      a0, -0x1CF0(a0)             ; *RELOAD_CTX
    li      t0, DATA
    addiu   t1, zero, 1
    sw      t1, PENDING(t0)             ; cave_frame finishes the reload
@@done:
    li      ra, ARR_RETURN              ; skip the compare function
    jr      ra
    nop
@@orig:
    addiu   sp, sp, -0x20               ; the 2 replaced instructions
    j       UI_HOOK + 8
    sw      ra, 0x1C(sp)

; ---------------------------------------------------------------------------
; a0 = target box entry (+1 type, +2 eid), a1 = look source (0x80000000 | key).
; Returns v0: bit 0 = a look changed, bit 1 = error.
action:
    addiu   sp, sp, -0x30
    sw      zero, 4(sp)
    sw      ra, 0x10(sp)
    sw      s0, 0x14(sp)
    sw      s1, 0x18(sp)
    sw      s2, 0x1C(sp)
    sw      s3, 0x20(sp)
    li      s0, DATA
    move    s2, a1
    lbu     t0, 1(a0)
    lhu     t1, 2(a0)
    sll     t0, t0, 16
    or      s1, t0, t1                  ; target key = type << 16 | eid
    lui     t3, 0x8000
    or      t3, t3, s1
    beq     s2, t3, @@reset             ; source = target
    xor     t4, s2, t3
    srl     t4, t4, 16
    bne     t4, zero, @@error           ; another slot
    srl     t0, s1, 16
    sltiu   t0, t0, 5
    bne     t0, zero, @@apply           ; armor
    nop
    jal     get3                        ; weapons: both must be the same class
    move    a0, s1
    li      t0, WEAPON_CLASS
    addu    t0, t0, a1
    lbu     s3, 0(t0)
    jal     get3
    move    a0, s2
    li      t0, WEAPON_CLASS
    addu    t0, t0, a1
    lbu     t0, 0(t0)
    bne     t0, s3, @@error
    nop
@@apply:
    jal     get3                        ; a1, a2, a3 = real look of the source
    move    a0, s2
    jal     find_rule
    move    a0, s1
    bne     v0, zero, @@have
    move    s3, v0
    jal     find_word                   ; a free rule
    move    t2, zero
    beq     v0, zero, @@error           ; all rules in use
    move    s3, v0
    sw      zero, 8(s3)
    sw      zero, 12(s3)
    jal     entry_addr                  ; remember the original look
    move    a0, s1
    lh      t0, 0(v0)
    sh      t0, 8(s3)
    sltiu   t1, v1, 5
    beq     t1, zero, @@new
    nop
    lh      t0, 2(v0)
    sh      t0, 10(s3)
    lbu     t0, 19(v0)
    sb      t0, 13(s3)
@@new:
    lui     t0, 0x8000
    or      t0, t0, s1
    sw      t0, 0(s3)
@@have:
    sh      a1, 4(s3)
    sh      a2, 6(s3)
    sb      a3, 12(s3)
    jal     put3
    move    a0, s1
    jal     save_file
    nop
    addiu   t0, zero, 1
    sw      t0, 4(sp)
    b       @@sound
    addiu   a2, zero, SND_APPLY
@@reset:
    jal     find_rule
    move    a0, s1
    beq     v0, zero, @@sound           ; it has no look: nothing to do
    addiu   a2, zero, SND_RESET
    move    s3, v0
    lh      a1, 8(s3)
    lh      a2, 10(s3)
    lbu     a3, 13(s3)
    jal     put3
    move    a0, s1
    jal     save_file
    sw      zero, 0(s3)
    addiu   t0, zero, 1
    sw      t0, 4(sp)
    b       @@sound
    addiu   a2, zero, SND_RESET
@@error:
    addiu   t0, zero, 2
    sw      t0, 4(sp)
    addiu   a2, zero, SND_ERROR
@@sound:
    lui     a0, 0x08A6
    lw      a0, -0x21A4(a0)             ; *SOUND_CTX
    move    a1, zero
    move    a3, zero
    move    t0, zero
    move    t1, zero
    move    t2, zero
    move    t3, zero
    jal     PLAY_SOUND
    sw      zero, 0(sp)
    lw      v0, 4(sp)
    lw      ra, 0x10(sp)
    lw      s0, 0x14(sp)
    lw      s1, 0x18(sp)
    lw      s2, 0x1C(sp)
    lw      s3, 0x20(sp)
    jr      ra
    addiu   sp, sp, 0x30

; ---------------------------------------------------------------------------
; a0 = key -> v0 = its rule or 0. find_word: t2 = first word to look for. Uses t0-t2.
find_rule:
    lui     t2, 0x8000
    or      t2, t2, a0
find_word:
    li      t0, DATA + 12
    addiu   t1, t0, RULES_SIZE
@@loop:
    lw      v0, 0(t0)
    beq     v0, t2, @@hit
    nop
    addiu   t0, t0, 16
    bne     t0, t1, @@loop
    nop
    jr      ra
    move    v0, zero
@@hit:
    jr      ra
    move    v0, t0

; a0 = key -> v0 = table entry, v1 = type. Uses t0, t1.
entry_addr:
    srl     v1, a0, 16
    andi    v1, v1, 7
    andi    t0, a0, 0xFFFF              ; eid
    sltiu   t1, v1, 5
    beq     t1, zero, @@weapon
    sll     t1, t0, 2
    addu    t1, t1, t0
    sll     t1, t1, 3                   ; eid * 40
    sll     v0, v1, 2
    lui     t0, 0x0897
    addu    t0, t0, v0
    lw      v0, 0x5970(t0)              ; ARMOR_TABLES[type]
    jr      ra
    addu    v0, v0, t1
@@weapon:
    addiu   t1, zero, 5
    bne     v1, t1, @@gunner
    sll     t1, t0, 3
    sll     v0, t0, 4
    addu    t1, t1, v0                  ; eid * 24
    li      v0, WEAPON_TABLE
    jr      ra
    addu    v0, v0, t1
@@gunner:
    sll     v0, t0, 5
    sll     t1, t0, 2
    subu    t1, v0, t1                  ; eid * 28
    li      v0, GUNNER_TABLE
    jr      ra
    addu    v0, v0, t1

; a0 = key, a1 = male model (weapons: model), a2 = female model, a3 = pigment flag: write the table.
put3:
    move    t7, ra
    jal     entry_addr
    nop
    sltiu   t0, v1, 5
    beq     t0, zero, @@done
    sh      a1, 0(v0)
    sh      a2, 2(v0)
    sb      a3, 19(v0)
@@done:
    jr      t7
    nop

; a0 = key -> a1, a2, a3 = its real look (the original one if it has a rule).
get3:
    move    t7, ra
    jal     find_rule
    nop
    beq     v0, zero, @@table
    nop
    lh      a1, 8(v0)
    lh      a2, 10(v0)
    jr      t7
    lbu     a3, 13(v0)
@@table:
    jal     entry_addr
    nop
    lh      a1, 0(v0)
    move    a2, a1
    sltiu   t0, v1, 5
    beq     t0, zero, @@done
    move    a3, zero
    lh      a2, 2(v0)
    lbu     a3, 19(v0)
@@done:
    jr      t7
    nop

; ---------------------------------------------------------------------------
clear_rules:
    li      t0, DATA + 8
    addiu   t1, t0, FILE_SIZE
@@loop:
    sw      zero, 0(t0)
    addiu   t0, t0, 4
    bne     t0, t1, @@loop
    nop
    jr      ra
    nop

; Read the file (if any), apply all rules, mark as loaded.
do_init:
    addiu   sp, sp, -0x10
    sw      ra, 0(sp)
    sw      s0, 4(sp)
    sw      s1, 8(sp)
    jal     clear_rules
    nop
    li      s0, DATA
    li      a0, path
    addiu   a1, zero, 1                 ; PSP_O_RDONLY
    jal     IO_OPEN
    move    a2, zero
    bltz    v0, @@apply
    move    s1, v0
    move    a0, s1
    addiu   a1, s0, 8
    jal     IO_READ
    addiu   a2, zero, FILE_SIZE
    sw      v0, 12(sp)
    jal     IO_CLOSE
    move    a0, s1
    lw      v0, 12(sp)                  ; bytes read: magic + whole rules (a file written by
    addiu   t0, v0, -4                  ; a version with fewer rules is shorter)
    andi    t0, t0, 15
    bne     t0, zero, @@bad
    lw      t1, 8(s0)
    li      t0, FILE_MAGIC
    beq     t1, t0, @@apply
    nop
@@bad:
    jal     clear_rules
    nop
@@apply:
    addiu   s1, s0, 12
@@loop:
    lw      a0, 0(s1)
    bgez    a0, @@next                  ; free
    nop
    lh      a1, 4(s1)
    lh      a2, 6(s1)
    jal     put3
    lbu     a3, 12(s1)
@@next:
    addiu   s1, s1, 16
    addiu   t0, s0, 12 + RULES_SIZE
    bne     s1, t0, @@loop
    nop
    li      t0, FILE_MAGIC
    sw      t0, 8(s0)
    sw      zero, PENDING(s0)
    li      t0, RUN_MAGIC
    sw      t0, 0(s0)
    lw      ra, 0(sp)
    lw      s0, 4(sp)
    lw      s1, 8(sp)
    jr      ra
    addiu   sp, sp, 0x10

save_file:
    addiu   sp, sp, -0x10
    sw      ra, 0(sp)
    sw      s1, 4(sp)
    li      a0, path
    addiu   a1, zero, 0x602             ; PSP_O_WRONLY | PSP_O_CREAT | PSP_O_TRUNC
    jal     IO_OPEN
    addiu   a2, zero, 0x1FF
    bltz    v0, @@done
    move    s1, v0
    li      a1, DATA + 8
    move    a0, s1
    jal     IO_WRITE
    addiu   a2, zero, FILE_SIZE
    jal     IO_CLOSE
    move    a0, s1
@@done:
    lw      ra, 0(sp)
    lw      s1, 4(sp)
    jr      ra
    addiu   sp, sp, 0x10

path:
    .asciiz "ms0:/PSP/SAVEDATA/MHFU_TRANSMOG.BIN"
    .align 4
cave_end:

.close

; Hook words, emitted by build.py
.create "bin/transmog_hooks.bin", 0
.word 0x0C000000 | ((cave_frame >> 2) & 0x03FFFFFF)     ; at FRAME_HOOK (jal, delay slot kept)
.word 0x08000000 | ((cave_ui >> 2) & 0x03FFFFFF), 0     ; at UI_HOOK, +4
.close

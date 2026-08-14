/*
 * BK3635 SlimBlade adaptation, created 2026-08-14.
 *
 * This new file follows the structure of the Apache-2.0 BK3633
 * SDK/src/system/startup_boot.S.  Constants and instruction order were
 * independently recovered from the Kensington SlimBlade Pro v4.49 image.
 * It contains no Kensington binary data beyond the represented instructions.
 */

    .syntax unified
    .cpu arm968e-s
    .arm
    .section .startup, "ax", %progbits
    .balign 4

    .global stock_vectors
    .type stock_vectors, %function
stock_vectors:
    ldr     pc, [pc, #0x18]       /* reset */
    ldr     pc, [pc, #0x18]       /* undefined instruction */
    ldr     pc, [pc, #0x18]       /* software interrupt */
    ldr     pc, [pc, #0x18]       /* prefetch abort */
    ldr     pc, [pc, #0x18]       /* data abort */
    mov     r0, r0                /* reserved vector */
    ldr     pc, [pc, #0x18]       /* IRQ */
    ldr     pc, [pc, #0x18]       /* FIQ */

    .word   reset_handler
    .word   exception_hang
    .word   exception_hang
    .word   exception_hang
    .word   exception_hang
    .word   0
    .word   0x00002320            /* stock FIQ wrapper */
    .word   0x00002300            /* stock IRQ wrapper */

exception_hang:
    b       exception_hang

reset_handler:
    mov     r0, #0
    mov     r1, #0
    mov     r2, #0
    mov     r3, #0
    mov     r4, #0
    mov     r5, #0
    mov     r6, #0
    mov     r7, #0
    mov     r8, #0
    mov     r9, #0
    mov     r10, #0
    mov     r11, #0
    mov     r12, #0
    bl      initialize_stacks
    bl      zero_bss
    bl      copy_data
    ldr     pc, [pc, #0xc4]       /* enter Thumb application at 0x19879 */
    ldr     pc, [pc, #0xc4]       /* retained stock runtime entry */
    ldr     pc, [pc, #0xc4]       /* retained stock null entry */
    b       .

initialize_stacks:
    ldr     r0, [pc, #0xc0]       /* 0xdeadbeef */
    ldr     r1, [pc, #0xc0]       /* guard address */
    str     r0, [r1]

    mov     r0, #0xd2             /* IRQ, interrupts masked */
    msr     cpsr_c, r0
    ldr     sp, [pc, #0xb4]
    ldr     r0, [pc, #0xa8]
    str     r0, [sp]

    mov     r0, #0xd1             /* FIQ, interrupts masked */
    msr     cpsr_c, r0
    ldr     sp, [pc, #0xa4]
    ldr     r0, [pc, #0x94]
    str     r0, [sp]

    mov     r0, #0xdf             /* System, interrupts masked */
    msr     cpsr_c, r0
    ldr     sp, [pc, #0x94]
    ldr     r0, [pc, #0x80]
    str     r0, [sp]

    mov     r0, #0xd3             /* Supervisor, interrupts masked */
    msr     cpsr_c, r0
    ldr     sp, [pc, #0x84]
    ldr     r0, [pc, #0x6c]
    str     r0, [sp]
    bx      lr

copy_data:
    ldr     r0, [pc, #0x78]       /* flash source */
    ldr     r1, [pc, #0x78]       /* RAM destination */
    mov     r2, r1
    ldr     r4, [pc, #0x74]       /* byte count */
    add     r2, r2, r4
1:
    cmp     r1, r2
    ldrlo   r3, [r0], #4
    strlo   r3, [r1], #4
    blo     1b
    bx      lr

stock_return_one:
    mov     r0, #1                /* alternate stock entry point */
zero_bss:
    ldr     r2, [pc, #0x58]       /* byte count */
    ldr     r0, [pc, #0x58]       /* RAM start */
    mov     r1, r0
    add     r1, r1, r2
    mov     r2, #0
2:
    cmp     r0, r1
    strlo   r2, [r0], #4
    blo     2b
    bx      lr

stock_heap_base:
    ldr     r0, [pc, #0x3c]
    bx      lr

    b       .

    /* Literal pool at the exact stock addresses 0x2170--0x21ab. */
    .word   0x00019879
    .word   0x00002020
    .word   0x00000000
    .word   0xdeadbeef
    .word   0x004073bc
    .word   0x00407efc
    .word   0x00407dbc
    .word   0x004073b0
    .word   0x00407abc
    .word   0x0001ed60
    .word   0x00400020
    .word   0x000006f4
    .word   0x00003940
    .word   0x00400714
    .word   0x00403f54

    .size stock_vectors, . - stock_vectors

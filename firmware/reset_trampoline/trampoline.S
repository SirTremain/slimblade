    .syntax unified
    .cpu arm968e-s
    .section .text, "ax", %progbits
    .arm

/*
 * The stock reset handler begins at 0x2064 with `mov r0, #0`. Execution is
 * redirected here, that exact displaced instruction is replayed, and stock
 * startup resumes at its next instruction, 0x2068.
 */
    .global reset_trampoline
    .type reset_trampoline, %function
reset_trampoline:
    mov r0, #0
    /* ARM B from 0x22b8 to absolute address 0x2068. */
    .word 0xeaffff6a
    .size reset_trampoline, . - reset_trampoline

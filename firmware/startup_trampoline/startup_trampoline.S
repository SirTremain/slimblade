    .syntax unified
    .cpu arm968e-s
    .section .text, "ax", %progbits
    .arm

/*
 * Exercise the standalone stub's CPU-mode, stack, and ARM/Thumb entry path,
 * then restore the incoming reset state and resume the stock handler.
 */
    .global startup_trampoline
    .type startup_trampoline, %function
startup_trampoline:
    mrs r10, cpsr
    mov r11, sp
    mov r0, #0xd3
    msr cpsr_c, r0
    ldr sp, .Lstack_top
    ldr r0, .Lthumb_entry_address
    bx r0

    .arm
.Larm_resume:
    msr cpsr_c, r10
    mov sp, r11
    mov r0, #0
    /* ARM B from 0x22dc to absolute stock continuation 0x2068. */
    .word 0xeaffff61

.Lstack_top:
    .word 0x00407f00
.Lthumb_entry_address:
    .word .Lthumb_entry + 1

    .thumb
.Lthumb_entry:
    ldr r0, .Larm_resume_address
    bx r0
    .align 2
.Larm_resume_address:
    .word .Larm_resume
    .size startup_trampoline, . - startup_trampoline

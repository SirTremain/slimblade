/*
 * BK3635 SlimBlade adaptation, created 2026-08-14.
 *
 * This new file follows the structure of the Apache-2.0 BK3633
 * SDK/src/system/startup_boot.S IRQ/FIQ entries. Constants and exact exception
 * return behavior were independently recovered from SlimBlade Pro v4.49.
 */

    .syntax unified
    .cpu arm968e-s
    .arm

    .section .irq_wrapper, "ax", %progbits
    .balign 4
    .global stock_irq_wrapper
    .type stock_irq_wrapper, %function
stock_irq_wrapper:
    push    {r0-r3, r12, lr}
    .word   0xfa0006db             /* blx 0x3e78 (Thumb IRQ dispatcher) */
    pop     {r0-r3, r12, lr}
    subs    pc, lr, #4
    .size stock_irq_wrapper, . - stock_irq_wrapper

    .section .fiq_wrapper, "ax", %progbits
    .balign 4
    .global stock_fiq_wrapper
    .type stock_fiq_wrapper, %function
stock_fiq_wrapper:
    push    {r0-r3, r12, lr}
    .word   0xfa000f6d             /* blx 0x60e0 (Thumb FIQ dispatcher) */
    pop     {r0-r3, r12, lr}
    subs    pc, lr, #4
    .size stock_fiq_wrapper, . - stock_fiq_wrapper

    .syntax unified
    .cpu arm968e-s
    .section .vectors, "ax", %progbits
    .arm
    .global _vector_start
    .type _vector_start, %function

_vector_start:
    ldr pc, reset_vector
    ldr pc, undefined_vector
    ldr pc, software_interrupt_vector
    ldr pc, prefetch_abort_vector
    ldr pc, data_abort_vector
    nop
    ldr pc, irq_vector
    ldr pc, fiq_vector

reset_vector:              .word reset_handler
undefined_vector:          .word hang
software_interrupt_vector: .word hang
prefetch_abort_vector:     .word hang
data_abort_vector:         .word hang
reserved_vector:           .word 0
irq_vector:                .word hang
fiq_vector:                .word hang

hang:
    b hang

reset_handler:
    mov r0, #0xd3
    msr cpsr_c, r0
    ldr sp, =0x00407f00
    ldr r0, =stub_main
    bx r0

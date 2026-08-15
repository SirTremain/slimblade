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
    ldr sp, .Lstack_top
    ldr r0, .Lthumb_entry
    bx r0
.Lstack_top:  .word 0x00407f00
.Lthumb_entry: .word stub_main

    .section .text.guard_prefix, "ax", %progbits
    .thumb
    .thumb_func
    .global stub_main
    .type stub_main, %function
stub_main:
    bl bk3635_enter_resident_loader

    .thumb_func
    .type bk3635_enter_resident_loader, %function
bk3635_enter_resident_loader:
    ldr r0, .Lsystem_interrupt_control
    movs r1, #1
    str r1, [r0]
    movs r0, #0x2d
    lsls r0, r0, #17
    ldr r1, .Lwatchdog_control
    str r0, [r1]
    movs r0, #0xa5
    lsls r0, r0, #16
    str r0, [r1]
    bl eeprom_erase
    ldr r4, .Lmarker_address
    ldr r1, .Lmarker_first_word
    movs r0, r4
    bl eeprom_write_word
    adds r0, r4, #1
    ldr r1, .Lmarker_second_word
    bl eeprom_write_word
    movs r0, #200
    movs r1, #0
    bl bk3635_stock_delay
    bl rust_experiment
    nop
.Lsystem_interrupt_control: .word 0x0080001c
.Lwatchdog_control:         .word 0x00806000
.Lmarker_address:           .word 0x0000807c
.Lmarker_first_word:        .word 0x78563412
.Lmarker_second_word:       .word 0x19d2bc9a

    .thumb_func
    .type eeprom_erase, %function
eeprom_erase:
    push {r7, lr}
    movs r0, #1
    lsls r0, r0, #15
    ldr r1, .Lstorage_address_erase
    str r0, [r1]
    movs r0, #0x28
    bl storage_operation
    pop {r7, pc}
    nop
.Lstorage_address_erase: .word 0x00803008

    .thumb_func
    .type eeprom_write_word, %function
eeprom_write_word:
    push {r7, lr}
    ldr r2, .Lstorage_address_write
    str r0, [r2]
    str r1, [r2, #4]
    movs r0, #0x24
    bl storage_operation
    pop {r7, pc}
.Lstorage_address_write: .word 0x00803008

    .thumb_func
    .type watchdog_reset, %function
watchdog_reset:
    ldr r1, .Lreset_interrupt_control
    movs r0, #1
    str r0, [r1]
    movs r0, #0x2d
    lsls r2, r0, #17
    ldr r0, .Lreset_watchdog_control
    str r2, [r0]
    movs r3, #0xa5
    lsls r3, r3, #16
    str r3, [r0]
    ldr r4, .Lreset_request
    ldr r5, .Lreset_key
    str r5, [r4]
    movs r4, #0
    str r4, [r1]
    movs r1, #0x50
    str r1, [r0]
    adds r2, #0x50
    str r2, [r0]
    adds r3, #0x50
    str r3, [r0]
.Lwatchdog_hang:
    b .Lwatchdog_hang
.Lreset_interrupt_control: .word 0x0080001c
.Lreset_watchdog_control:  .word 0x00806000
.Lreset_request:           .word 0x008000c0
.Lreset_key:               .word 0x00aa5aaa

    .thumb_func
    .type storage_operation, %function
storage_operation:
    ldr r1, .Lstorage_base
    ldr r2, .Lstorage_unlock_a
    str r2, [r1]
    ldr r2, .Lstorage_unlock_b
    str r2, [r1]
    movs r2, #0xa5
    str r2, [r1, #0x10]
    movs r2, #0xc3
    str r2, [r1, #0x14]
    ldr r2, [r1, #4]
    movs r3, #0x7c
    bics r2, r3
    orrs r2, r0
    str r2, [r1, #4]
    movs r0, #1
    orrs r0, r2
    str r0, [r1, #4]
.Lstorage_wait:
    ldr r0, [r1, #4]
    lsls r0, r0, #31
    bne .Lstorage_wait
    movs r0, #0
    str r0, [r1]
    str r0, [r1]
    str r0, [r1, #0x10]
    str r0, [r1, #0x14]
    bx lr
.Lstorage_base:     .word 0x00803000
.Lstorage_unlock_a: .word 0x000058a9
.Lstorage_unlock_b: .word 0x0000a958

    .section .text.stock_delay, "ax", %progbits
    .thumb
    .thumb_func
    .global bk3635_stock_delay
    .type bk3635_stock_delay, %function
bk3635_stock_delay:
    push {r4, r5, r6, lr}
    movs r5, r1
    movs r4, r0
    b .Louter_test
.Louter_body:
    movs r2, #106
.Lmiddle_body:
    movs r0, #1
    bl .Linner_delay
    movs r0, r2
    subs r2, r2, #1
    lsls r2, r2, #24
    lsrs r2, r2, #24
    cmp r0, #0
    bne .Lmiddle_body
    cmp r5, #0
    beq .Louter_test
    nop
.Louter_test:
    movs r0, r4
    subs r4, r4, #1
    lsls r4, r4, #16
    lsrs r4, r4, #16
    cmp r0, #0
    bne .Louter_body
    pop {r4, r5, r6, pc}
.Linner_delay:
    b .Linner_test
.Linner_body:
    movs r1, #0
.Linner_loop:
    adds r1, r1, #1
    lsls r1, r1, #24
    lsrs r1, r1, #24
    cmp r1, #17
    blo .Linner_loop
.Linner_test:
    movs r1, r0
    subs r0, r0, #1
    lsls r0, r0, #24
    lsrs r0, r0, #24
    cmp r1, #0
    bne .Linner_body
    bx lr

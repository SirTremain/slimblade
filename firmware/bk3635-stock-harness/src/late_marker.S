    .syntax unified
    .cpu arm968e-s

    .equ SYSTEM_INTERRUPT_CONTROL, 0x0080001c
    .equ SYSTEM_RESET_REQUEST,     0x008000c0
    .equ WATCHDOG_CONTROL,         0x00806000
    .equ STORAGE_BASE,             0x00803000
    .equ MARKER_ADDRESS,           0x0000807c
    .equ STOCK_RECOVERY_COMMAND,   0x0001895d
    .equ STOCK_DELAY,              0x000178eb

    .section .text.carrier, "ax", %progbits
    .thumb

/* Command 0x0e writes the marker only after stock startup, then returns. */
    .thumb_func
    .global carrier_dispatch
    .type carrier_dispatch, %function
carrier_dispatch:
    cmp r0, #0x0d
    beq .Lstock_recovery
    cmp r0, #0x0e
    beq carrier_late_marker
    cmp r0, #0x0f
    beq carrier_reset_probe
    b carrier_full_recovery
.Lstock_recovery:
    ldr r3, =STOCK_RECOVERY_COMMAND
    bx r3
    .size carrier_dispatch, . - carrier_dispatch

    .thumb_func
    .global carrier_late_marker
    .type carrier_late_marker, %function
carrier_late_marker:
    push {r4, lr}
    bl marker_set
    pop {r4, pc}
    .size carrier_late_marker, . - carrier_late_marker

    .thumb_func
    .type carrier_reset_probe, %function
carrier_reset_probe:
    b watchdog_reset
    .size carrier_reset_probe, . - carrier_reset_probe

    .thumb_func
    .type carrier_full_recovery, %function
carrier_full_recovery:
    bl marker_set
    b watchdog_reset
    .size carrier_full_recovery, . - carrier_full_recovery

/* Called only from Thumb code; restore interrupt control before returning. */
    .thumb_func
    .global marker_set
    .type marker_set, %function
marker_set:
    push {lr}
    bl watchdog_disable

    movs r0, #1
    lsls r0, r0, #15
    ldr r1, =STORAGE_BASE
    str r0, [r1, #8]
    movs r0, #0x28
    bl storage_operation

    ldr r0, =MARKER_ADDRESS
    ldr r1, =STORAGE_BASE
    str r0, [r1, #8]
    ldr r0, =0x78563412
    str r0, [r1, #12]
    movs r0, #0x24
    bl storage_operation

    ldr r0, =MARKER_ADDRESS + 1
    ldr r1, =STORAGE_BASE
    str r0, [r1, #8]
    ldr r0, =0x19d2bc9a
    str r0, [r1, #12]
    movs r0, #0x24
    bl storage_operation

    movs r0, #200
    movs r1, #0
    ldr r3, =STOCK_DELAY
    blx r3
    ldr r0, =SYSTEM_INTERRUPT_CONTROL
    movs r1, #0
    str r1, [r0]
    pop {pc}
    .size marker_set, . - marker_set

/* Reset startup performs only the already-proven Thumb-to-ARM return. */
    .thumb_func
    .global stock_resume
    .type stock_resume, %function
stock_resume:
    ldr r0, =startup_arm_resume
    bx r0
    .size stock_resume, . - stock_resume

    .thumb_func
    .type watchdog_disable, %function
watchdog_disable:
    ldr r0, =SYSTEM_INTERRUPT_CONTROL
    movs r1, #1
    str r1, [r0]
    movs r0, #0x2d
    lsls r0, r0, #17
    ldr r1, =WATCHDOG_CONTROL
    str r0, [r1]
    movs r0, #0xa5
    lsls r0, r0, #16
    str r0, [r1]
    bx lr
    .size watchdog_disable, . - watchdog_disable

    .thumb_func
    .type watchdog_reset, %function
watchdog_reset:
    bl watchdog_disable
    ldr r0, =SYSTEM_RESET_REQUEST
    ldr r1, =0x00aa5aaa
    str r1, [r0]
    ldr r0, =SYSTEM_INTERRUPT_CONTROL
    movs r1, #0
    str r1, [r0]
    ldr r0, =WATCHDOG_CONTROL
    movs r1, #0x50
    str r1, [r0]
    ldr r1, =0x005a0050
    str r1, [r0]
    ldr r1, =0x00a50050
    str r1, [r0]
.Lreset_wait:
    b .Lreset_wait
    .size watchdog_reset, . - watchdog_reset

    .thumb_func
    .type storage_operation, %function
storage_operation:
    ldr r1, =STORAGE_BASE
    ldr r2, =0x000058a9
    str r2, [r1]
    ldr r2, =0x0000a958
    str r2, [r1]
    movs r2, #0xa5
    str r2, [r1, #16]
    movs r2, #0xc3
    str r2, [r1, #20]
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
    str r0, [r1, #16]
    str r0, [r1, #20]
    bx lr
    .size storage_operation, . - storage_operation

    .ltorg

    .section .text.trampoline, "ax", %progbits
    .arm
    .balign 4
    .global startup_trampoline
    .type startup_trampoline, %function
startup_trampoline:
    mrs r10, cpsr
    mov r11, sp
    mov r0, #0xd3
    msr cpsr_c, r0
    ldr sp, .Lstack_top
    ldr r0, .Lstock_resume_address
    bx r0

    .global startup_arm_resume
startup_arm_resume:
    msr cpsr_c, r10
    mov sp, r11
    mov r0, #0
    /* ARM B from 0x22f4 to the absolute stock continuation at 0x2068. */
    .word 0xeaffff5b

.Lstack_top:
    .word 0x00407f00
.Lstock_resume_address:
    /* The Thumb function symbol already carries bit zero in this relocation. */
    .word stock_resume
    .size startup_trampoline, . - startup_trampoline

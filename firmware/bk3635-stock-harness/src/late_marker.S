    .syntax unified
    .cpu arm968e-s

    .equ SYSTEM_INTERRUPT_CONTROL, 0x0080001c
    .equ SYSTEM_RESET_REQUEST,     0x008000c0
    .equ WATCHDOG_CONTROL,         0x00806000
    .equ STORAGE_BASE,             0x00803000
    .equ MARKER_ADDRESS,           0x0000807c
    .equ STOCK_RECOVERY_COMMAND,   0x0001895d
    .equ STOCK_DELAY,              0x000178eb
    .ifdef POST_INIT_STEADY_LOOP_HOOK_PROBE
    .equ STOCK_MODE_ADDRESS,       0x00400264
    .equ STOCK_STEADY_SERVICE,     0x00015d35
    .else
    .ifdef POST_INIT_ACTIVE_LOOP_HOOK_PROBE
    .equ STOCK_MODE_ADDRESS,       0x00400264
    .equ STOCK_WIRED_POINTER,      0x004002b8
    .else
    .ifdef POST_INIT_LOOP_HOOK_PROBE
    .equ STOCK_MODE_ADDRESS,       0x00400264
    .equ STOCK_MAIN_LOOP,          0x00019b4b
    .else
    .equ STOCK_MODE_ADDRESS,       0x00400282
    .equ STOCK_MAIN_LOOP,          0x00019bf3
    .endif
    .endif
    .endif

    .section .text.carrier, "ax", %progbits
    .thumb

/* Command 0x0e writes the marker only after stock startup, then returns. */
    .thumb_func
    .global carrier_dispatch
    .type carrier_dispatch, %function
carrier_dispatch:
    .ifdef POST_INIT_HOOK_PROBE
    cmp r0, #0x0d
    beq .Lstock_recovery
    cmp r0, #0x0e
    beq carrier_late_marker
    cmp r0, #0x0f
    beq carrier_hook_state
    bx lr
.Lstock_recovery:
    ldr r3, =STOCK_RECOVERY_COMMAND
    bx r3
    .else
    .ifdef RUST_RESPONSE_PROBE
    cmp r0, #0x0d
    beq .Lstock_recovery
    cmp r0, #0x0e
    beq carrier_late_marker
    bx lr
    nop
.Lstock_recovery:
    ldr r3, =STOCK_RECOVERY_COMMAND
    bx r3
    nop
    .else
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
    .endif
    .endif
    .size carrier_dispatch, . - carrier_dispatch

    .thumb_func
    .global carrier_late_marker
    .type carrier_late_marker, %function
carrier_late_marker:
    push {r4, lr}
    bl marker_set
    .ifdef POST_INIT_HOOK_PROBE
    ldr r0, =STOCK_MODE_ADDRESS
    .ifdef POST_INIT_STEADY_LOOP_HOOK_PROBE
    movs r1, #5
    .else
    .ifdef POST_INIT_ACTIVE_LOOP_HOOK_PROBE
    movs r1, #5
    .else
    .ifdef POST_INIT_LOOP_HOOK_PROBE
    movs r1, #5
    .else
    movs r1, #3
    .endif
    .endif
    .endif
    strb r1, [r0]
    .ifdef POST_INIT_STEADY_LOOP_HOOK_PROBE
    movs r0, #0xa7
    .else
    .ifdef POST_INIT_ACTIVE_LOOP_HOOK_PROBE
    movs r0, #0xa6
    .else
    .ifdef POST_INIT_LOOP_HOOK_PROBE
    movs r0, #0xa5
    .else
    movs r0, #0xa3
    .endif
    .endif
    .endif
    strb r0, [r4, #3]
    pop {r4, pc}
    .else
    .ifdef EXPERIMENT_ENTRY_HANG
.Lexperiment_hang:
    b .Lexperiment_hang
    .else
    .ifdef RUST_RESPONSE_PROBE
    b rust_response_shim
    .else
    pop {r4, pc}
    .endif
    .endif
    .endif
    .size carrier_late_marker, . - carrier_late_marker

    .ifdef POST_INIT_HOOK_PROBE
    .thumb_func
    .global carrier_hook_state
    .type carrier_hook_state, %function
carrier_hook_state:
    ldr r0, =STOCK_MODE_ADDRESS
    ldrb r0, [r0]
    strb r0, [r4, #3]
    bx lr
    .size carrier_hook_state, . - carrier_hook_state
    .else
    .ifdef RUST_RESPONSE_PROBE
    .thumb_func
    .global rust_response_shim
    .type rust_response_shim, %function
rust_response_shim:
    bl rust_probe_value
    strb r0, [r4, #3]
    pop {r4, pc}
    .size rust_response_shim, . - rust_response_shim
    .else
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
    .endif
    .endif

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

    .ifndef POST_INIT_HOOK_PROBE
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
    .endif

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

    .ifdef POST_INIT_ACTIVE_LOOP_HOOK_PROBE
/* Replays the two displaced stock instructions, then consumes armed state 5. */
    .thumb_func
    .global active_loop_hook_impl
    .type active_loop_hook_impl, %function
active_loop_hook_impl:
    ldr r7, =STOCK_WIRED_POINTER
    ldr r0, [r7]
    ldr r1, =STOCK_MODE_ADDRESS
    ldrb r2, [r1]
    cmp r2, #5
    bne .Lactive_loop_return
    movs r2, #0
    strb r2, [r1]
.Lactive_loop_return:
    bx lr
    .size active_loop_hook_impl, . - active_loop_hook_impl
    .ltorg
    .endif

    .ifdef POST_INIT_STEADY_LOOP_HOOK_PROBE
/* Calls the displaced stock service first, then consumes armed state 5. */
    .thumb_func
    .global steady_loop_hook_impl
    .type steady_loop_hook_impl, %function
steady_loop_hook_impl:
    push {lr}
    ldr r3, =STOCK_STEADY_SERVICE
    blx r3
    ldr r1, =STOCK_MODE_ADDRESS
    ldrb r2, [r1]
    cmp r2, #5
    bne .Lsteady_loop_return
    movs r2, #0
    strb r2, [r1]
.Lsteady_loop_return:
    pop {pc}
    .size steady_loop_hook_impl, . - steady_loop_hook_impl
    .ltorg
    .endif

    .ifdef POST_INIT_HOOK_PROBE
    .section .text.rust_probe, "ax", %progbits
    .thumb
    .thumb_func
    .global post_init_hook
    .type post_init_hook, %function
post_init_hook:
    .ifdef POST_INIT_STEADY_LOOP_HOOK_PROBE
    b steady_loop_hook_impl
    .else
    .ifdef POST_INIT_ACTIVE_LOOP_HOOK_PROBE
    b active_loop_hook_impl
    .else
    .ifdef POST_INIT_LOOP_HOOK_PROBE
    movs r0, #0
    strb r0, [r7]
    .else
    movs r0, #2
    strb r0, [r4]
    .endif
    ldr r0, .Lstock_main_loop
    bx r0
.Lstock_main_loop:
    .word STOCK_MAIN_LOOP
    .endif
    .endif
    .size post_init_hook, . - post_init_hook
    .endif

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

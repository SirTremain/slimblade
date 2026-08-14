    .syntax unified
    .cpu arm968e-s
    .section .text.bk3635_stock_delay, "ax", %progbits
    .thumb
    .thumb_func
    .global bk3635_stock_delay
    .type bk3635_stock_delay, %function

/*
 * Cycle-path reconstruction of stock v4.49 functions 0x178ce and 0x178ea.
 * The recovery path calls this as (200, 0), so its dormant watchdog-feed call
 * is intentionally absent. The taken path and counter widths match stock.
 */
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

    .size bk3635_stock_delay, . - bk3635_stock_delay

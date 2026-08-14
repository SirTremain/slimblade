
    #define MODE_USR        0x10
    #define MODE_FIQ        0x11
    #define MODE_IRQ        0x12
    #define MODE_SVC        0x13
    #define MODE_ABT        0x17
    #define MODE_UND        0x1B
    #define MODE_SYS        0x1F // available on ARM Arch 4 and later
    #define I_BIT           0x80 // when I bit is set, IRQ is disabled
    #define F_BIT           0x40 // when F bit is set, FIQ is disabled

    #define STACK_SIZE_USR  0x00000000
    #define STACK_SIZE_FIQ  0x00000500
    #define STACK_SIZE_IRQ  0x00000500
    #define STACK_SIZE_SVC  0x00000500
    #define STACK_SIZE_ABT  0x00000000
    #define STACK_SIZE_UND  0x00000200
    #define STACK_SIZE_SYS  0x00000000
    #define STACK_TOP_ADDR  0x0040C000

    //.equ SYSirq_FIQ_Handler,0x00024F00  //for define CFG_DBG	
    //.equ SYSirq_IRQ_Handler,0x00024F20 //for define CFG_DBG
    .equ SYSirq_FIQ_Handler,0x25e00
    .equ SYSirq_IRQ_Handler,0x25e20


    
    .extern Irq_Exception

    .globl  _reset_handler
    .globl  _undefined_handler
    .globl  _swi_handler
    .globl  _pabort_handler
    .globl  _dabort_handler
    .globl  _reserved_handler
    .globl  __irq_handler
    .globl  __fiq_handler
    .globl  __enable_irq
    .globl  __disable_irq

    .macro ARM_MODE_SET, mode, stack, size, color
        MRS R0, CPSR
        BIC R0, R0, #0x1F
        ORR R0, R0, #\mode
        MSR CPSR_c, R0
        LDR R0, \size
        LDR R1, \stack
        LDR R2, =\color
        MOV SP, R1
        SUB R0, R1, R0
100:    CMP R0, R1
        STRLT R2, [r0]
        ADDLT R0, R0, #4
        BLT   100b
    .endm








_reset_handler:
    //Disable IRQ and FIQ before starting anything
    MRS   R0, CPSR
    ORR   R0, R0, #0xC0
    MSR   CPSR_c, R0

    //Setup all stacks, Abt and Usr mode are not used
    ARM_MODE_SET  MODE_SYS  _STACK_ADDR_UND  _STACK_SIZE_UND  0xAAAAAAAA
    ARM_MODE_SET  MODE_ABT  _STACK_ADDR_UND  _STACK_SIZE_UND  0xAAAAAAAA
    ARM_MODE_SET  MODE_UND  _STACK_ADDR_UND  _STACK_SIZE_UND  0xAAAAAAAA
    ARM_MODE_SET  MODE_IRQ  _STACK_ADDR_IRQ  _STACK_SIZE_IRQ  0xBBBBBBBB
    ARM_MODE_SET  MODE_FIQ  _STACK_ADDR_FIQ  _STACK_SIZE_FIQ  0xCCCCCCCC

    //Clear FIQ banked registers while in FIQ mode
    MOV R8,  #0
    MOV R9,  #0
    MOV R10, #0
    MOV R11, #0
    MOV R12, #0

    ARM_MODE_SET  MODE_SVC  _STACK_ADDR_SVC  _STACK_SIZE_SVC  0xDDDDDDDD

    //Copy data from binary to ram
    BL _data_init

    //Init the BSS section
    BL _zi_init

    MOV R0,  #0
    MOV R1,  #0
    MOV R2,  #0
    MOV R3,  #0
    MOV R4,  #0
    MOV R5,  #0
    MOV R6,  #0
    MOV R7,  #0
    MOV R8,  #0
    MOV R9,  #0
    MOV R10, #0
    MOV R11, #0
    MOV R12, #0

    B   bim_main

_data_init:
    LDR R0, =_data_load_begin
    LDR R1, =_data_addr_begin
    LDR R2, =_data_addr_end

1:  CMP R1, R2
    LDRLO   R4, [R0], #4
    STRLO   R4, [R1], #4
    BLO     1b
    BX      LR

_zi_init:
    LDR     R0, =_bss_start
    LDR     R1, =_bss_end

    MOV R3, R1
    MOV R4, R0
    MOV R2, #0
2:  CMP R4, R3
    STRLO   R2, [R4], #4
    BLO 2b
    BX  LR



__irq_handler:
    STMFD SP!, {R0-R12,LR}
    LDR   R0, =0x00400000
    LDR   R1, [R0]
    CMP   R1, #0x01
    BLEQ  Irq_Exception
    BL    SYSirq_IRQ_Handler
    LDMFD SP!, {R0-R12,LR}
    SUBS  PC,  LR, #4

__fiq_handler:
    STMFD SP!, {R0-R12,LR}
    BL    SYSirq_FIQ_Handler
    LDMFD SP!, {R0-R12,LR}
    SUBS  PC,  LR, #4

    //void __enable_irq(void);
    .globl __enable_irq
    .type  __enable_irq, %function
__enable_irq:
    MRS     R0, APSR //formerly CPSR
    BIC     R0, R0, #0x80
    MSR     CPSR_c, R0
    BX      LR

    //int  __disable_irq(void);
    .globl __disable_irq
    .type  __disable_irq, %function
__disable_irq:
    MRS     R0, APSR //formerly CPSR
    ORR     R1, R0, #0x80
    MSR     CPSR_c, R1
    AND     R0, R0, #0x80
    BX      LR

    //void __enable_fiq(void);
    .globl __enable_fiq
    .type  __enable_fiq, %function
__enable_fiq:
    MRS     R0, APSR //formerly CPSR
    BIC     R0, R0, #0x40
    MSR     CPSR_c, R0
    BX      LR

    //int  __disable_fiq(void);
    .globl __disable_fiq
    .type  __disable_fiq, %function
__disable_fiq:
    MRS     R0, APSR //formerly CPSR
    ORR     R1, R0, #0x40
    MSR     CPSR_c, R1
    AND     R0, R0, #0x40
    BX      LR

_STACK_ADDR_FIQ: .word STACK_TOP_ADDR
_STACK_SIZE_FIQ: .word STACK_SIZE_FIQ
_STACK_ADDR_IRQ: .word STACK_TOP_ADDR-STACK_SIZE_FIQ
_STACK_SIZE_IRQ: .word STACK_SIZE_IRQ
_STACK_ADDR_SVC: .word STACK_TOP_ADDR-STACK_SIZE_FIQ-STACK_SIZE_IRQ
_STACK_SIZE_SVC: .word STACK_SIZE_SVC
_STACK_ADDR_UND: .word STACK_TOP_ADDR-STACK_SIZE_FIQ-STACK_SIZE_IRQ-STACK_SIZE_SVC
_STACK_SIZE_UND: .word STACK_SIZE_UND

    .balignl 16, 0xdeadbeef
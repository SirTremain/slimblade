
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
    #define STACK_SIZE_FIQ  0x00000800
    #define STACK_SIZE_IRQ  0x00000800
    #define STACK_SIZE_SVC  0x00001600
    #define STACK_SIZE_ABT  0x00000000
    #define STACK_SIZE_UND  0x00000600
    #define STACK_SIZE_SYS  0x00000000
    #define STACK_TOP_ADDR  0x0040FFFC

    //.equ SYSirq_FIQ_Handler,0x00024F00  //for define CFG_DBG	
    //.equ SYSirq_IRQ_Handler,0x00024F20 //for define CFG_DBG
    //.equ SYSirq_FIQ_Handler,0x25e00
    //.equ SYSirq_IRQ_Handler,0x25e20


    
    .extern Irq_Exception

	.globl boot_stack_base_UNUSED
	.globl boot_stack_len_UNUSED
	.globl boot_stack_base_SVC
	.globl boot_stack_len_SVC
	.globl boot_stack_base_IRQ
	.globl boot_stack_len_IRQ
	.globl boot_stack_base_FIQ
	.globl boot_stack_len_FIQ	


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
		ADD R1,#4
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
    ARM_MODE_SET  MODE_SYS  boot_stack_base_UNUSED  boot_stack_len_UNUSED  0xAAAAAAAA
    ARM_MODE_SET  MODE_ABT  boot_stack_base_UNUSED  boot_stack_len_UNUSED  0xAAAAAAAA
    ARM_MODE_SET  MODE_UND  boot_stack_base_UNUSED  boot_stack_len_UNUSED  0xAAAAAAAA
    ARM_MODE_SET  MODE_IRQ  boot_stack_base_IRQ  boot_stack_len_IRQ  0xCCCCCCCC
    ARM_MODE_SET  MODE_FIQ  boot_stack_base_FIQ  boot_stack_len_FIQ  0xDDDDDDDD

    //Clear FIQ banked registers while in FIQ mode
    MOV R8,  #0
    MOV R9,  #0
    MOV R10, #0
    MOV R11, #0
    MOV R12, #0

    ARM_MODE_SET  MODE_SVC  boot_stack_base_SVC  boot_stack_len_SVC  0xBBBBBBBB

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

    B   main

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

boot_stack_base_FIQ: .word STACK_TOP_ADDR
boot_stack_len_FIQ: .word STACK_SIZE_FIQ
boot_stack_base_IRQ: .word STACK_TOP_ADDR-STACK_SIZE_FIQ
boot_stack_len_IRQ: .word STACK_SIZE_IRQ
boot_stack_base_SVC: .word STACK_TOP_ADDR-STACK_SIZE_FIQ-STACK_SIZE_IRQ
boot_stack_len_SVC: .word STACK_SIZE_SVC
boot_stack_base_UNUSED: .word STACK_TOP_ADDR-STACK_SIZE_FIQ-STACK_SIZE_IRQ-STACK_SIZE_SVC
boot_stack_len_UNUSED: .word STACK_SIZE_UND

    .balignl 16, 0xdeadbeef

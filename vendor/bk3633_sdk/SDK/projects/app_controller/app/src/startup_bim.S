	#define STACK_SIZE_USR  0x00000000
    #define STACK_SIZE_FIQ  0x000001f0
    #define STACK_SIZE_IRQ  0x000003f0
    #define STACK_SIZE_SVC  0x00000500
    #define STACK_SIZE_ABT  0x00000000
    #define STACK_SIZE_UND  0x00000100
    #define STACK_SIZE_SYS  0x00000000
    #define STACK_TOP_ADDR  0x0040FFF0

	.extern _reset_handler
	.extern Undefined_Exception
    .extern SoftwareInterrupt_Exception
    .extern PrefetchAbort_Exception
    .extern DataAbort_Exception
    .extern Reserved_Exception
	.extern __irq_handler
    .extern __fiq_handler
	
    .section .stack
    .space STACK_SIZE_UND+STACK_SIZE_FIQ+STACK_SIZE_IRQ+STACK_SIZE_SVC

    .section ".vectors", "ax"
_vector_start:
    B       _reset_handler
    ldr pc, _undefined_handler
    ldr pc, _swi_handler
    ldr pc, _pabort_handler
    ldr pc, _dabort_handler
    ldr pc, _reserved_handler
    ldr pc, _irq_handler
    ldr pc, _fiq_handler

_undefined_handler : .word Undefined_Exception
_swi_handler       : .word SoftwareInterrupt_Exception
_pabort_handler    : .word PrefetchAbort_Exception
_dabort_handler    : .word DataAbort_Exception
_reserved_handler  : .word Reserved_Exception
_irq_handler       : .word __irq_handler
_fiq_handler       : .word __fiq_handler

    .balignl 16, 0xdeadbeef

/**
 ****************************************************************************************
 *
 * @file intc.c
 *
 * @brief Definition of the Interrupt Controller (INTCTRL) API.
 *
 * Copyright (C) RivieraWaves 2009-2015
 *
 *
 ****************************************************************************************
 */

/**
 ****************************************************************************************
 * @addtogroup INTC
 * @{
 ****************************************************************************************
 */

/*
 * INCLUDE FILES
 ****************************************************************************************
 */
#if defined(CFG_BT) || defined(CFG_BLE)
#include "rwip_config.h"
#endif// defined(CFG_BT) || defined(CFG_BLE)
#include "compiler.h"        // for inline functions
#include "arch.h"            // arch definition
#include "co_math.h"         // math library definition

#if defined(CFG_BT)
#include "rwip_config.h"     // stack configuration
#include "rwbt.h"            // rwbt core
#endif //CFG_BT

#if defined(CFG_BLE)
#if (BLE_EMB_PRESENT)
#include "rwble.h"           // rwble core
#endif // (BLE_EMB_PRESENT)
#endif //CFG_BLE

#if defined(CFG_BT) && defined(CFG_BLE)
#include "rwip.h"            // rw IP core driver
#endif // #if defined(CFG_BT) && defined(CFG_BLE)

#include "intc.h"            // interrupt controller
#include "reg_intc.h"        // intc registers
#if PLF_UART
#include "uart.h"            // uart definitions
#endif //PLF_UART



#include "BK3633_RegList.h"
#include "gpio.h"  
#include "spi.h"
#include "intc.h"
#include "icu.h"
#include "dma.h"
#if(ADC_DRIVER)
#include "adc.h"
#endif
#if(UART_DRIVER)
#include "uart.h"
#endif
#if(UART2_DRIVER)
#include "uart2.h"
#endif
#if(AON_RTC_DRIVER)
#include "aon_rtc.h"
#endif
#if (USB_DRIVER)
#include "driver_usb.h"
#endif
/*
 * DEFINES
 ****************************************************************************************
 */

#define RWBT_INT      CO_BIT(INTC_BT)
#define RWBTDM_INT    CO_BIT(INTC_BTDM)
#define UART_INT      CO_BIT(INTC_UART)
#define UART_2_INT    CO_BIT(INTC_UART_2)

#define RWBLE_INT     CO_BIT(INTC_BLE)
#define RWCOMMON_INT  CO_BIT(INTC_COMMON)
#define TIMER_INT     CO_BIT(INTC_TIMER)


// enable the supported interrupts
#define PLF_INT     (UART_INT | UART_2_INT | TIMER_INT)

#if defined(CFG_BT)
#define BT_INT      (RWBT_INT)
#else
#define BT_INT       0
#endif // #if defined(CFG_BT)

#if defined(CFG_BLE)
#if (BLE_EMB_PRESENT)
#define BLE_INT     (RWBLE_INT)
#else
#define BLE_INT      0
#endif // (BLE_EMB_PRESENT)
#else
#define BLE_INT      0
#endif // #if defined(CFG_BLE)

#if defined(CFG_BT) && defined(CFG_BLE)
#define BTDM_INT    (RWBTDM_INT)
#else
#define BTDM_INT    0
#endif // #if defined(CFG_BT) && defined(CFG_BLE)




/*
 * FUNCTION DEFINITIONS
 ****************************************************************************************
 */
void intc_spurious(void)
{
    // force error
    //ASSERT_ERR(0);
}

void intc_init(void)
{
    addSYS_Reg0x10 = 0; // int enable 0:disable 1::enable
    addSYS_Reg0x11 = 0; // priority; 0: irq  1:fiq

    //setf_SYS_Reg0x10_int_uart0_en; //enable uart_int irq
    //setf_SYS_Reg0x10_int_timer0_en; //enable timer_int irq

    setf_SYS_Reg0x10_int_rwble_en; //enable int rwble
    setf_SYS_Reg0x10_int_rwdm_en; //enable int rwdm
    setf_SYS_Reg0x10_int_rwbt_en; //enable  rwbt
    setf_SYS_Reg0x11_int_rwble_pri; // 1:fiq
    setf_SYS_Reg0x11_int_rwdm_pri; // 1:fiq
    setf_SYS_Reg0x11_int_rwbt_pri; // 1:fiq

}



/*__IRQ */void intc_irq(void)
{

    uint32_t IntStat;
	uint32_t irq_status = 0;

	IntStat = intc_status_get();

 
    // call the function handler
	if(IntStat & INT_STATUS_UART0_bit)
	{
		irq_status |= INT_STATUS_UART0_bit;
        uart_isr();
	}
    if(IntStat & INT_STATUS_UART2_bit)
	{
		irq_status |= INT_STATUS_UART2_bit;
        uart2_isr();
	}
#if (ADC_DRIVER)
    if(IntStat & INT_STATUS_ADC_bit)
    {
        irq_status |= INT_STATUS_ADC_bit;
        adc_isr();
    }
#endif
#if (AON_RTC_DRIVER)
	if(IntStat & INT_STATUS_AON_RTC_bit)
	{
		irq_status |= INT_STATUS_AON_RTC_bit;
		aon_rtc_isr();
	}
#endif


#if (GPIO_DRIVER)
	if(IntStat & INT_STATUS_AON_GPIO_bit)
	{
		irq_status |= INT_STATUS_AON_GPIO_bit;
		gpio_isr();
	}
#endif
#if (SPI_DRIVER)
    if(IntStat & INT_STATUS_SPI0_bit)
    {
        irq_status |= INT_STATUS_SPI0_bit;
        spi_isr();
    }
#endif
#if (I2C_DRIVER)	
    if(IntStat & INT_STATUS_I2C0_bit)
    {
        irq_status |= INT_STATUS_I2C0_bit;
        i2c_isr();
    }
#endif     
#if (PWM_DRIVER)
    if(IntStat & INT_STATUS_PWM1_bit)
    {
        irq_status |= INT_STATUS_PWM1_bit;
        pwm_isr();
    }
    if(IntStat & INT_STATUS_PWM2_bit)
    {
        irq_status |= INT_STATUS_PWM2_bit;
        pwm_isr();
    }
    if(IntStat & INT_STATUS_PWM3_bit)
    {
        irq_status |= INT_STATUS_PWM3_bit;
        pwm_isr();
    }
    if(IntStat & INT_STATUS_PWM4_bit)
    {
        irq_status |= INT_STATUS_PWM4_bit;
        pwm_isr();
    }

    if(IntStat &INT_STATUS_PWM5_bit)
    {
        irq_status |= INT_STATUS_PWM5_bit;
        pwm6_irq_done();
    }
#endif

#if(USB_DRIVER)  
    if(IntStat & INT_STATUS_USB_bit)
    {
    	irq_status |= INT_STATUS_USB_bit;
    	USB_InterruptHandler();
    }
#endif

	intc_status_clear(irq_status);
}

/*__FIQ */void intc_fiq(void)
{
    uint32_t IntStat;
	uint32_t fiq_status=0;
    //cpu_wakeup();
	IntStat = intc_status_get();

    //uart_printf("FIQ IntStat:%x\r\n",IntStat);
    if(IntStat & INT_STATUS_RWDM_bit)
	{
		fiq_status |= INT_STATUS_RWDM_bit;
        rwip_isr();
	}
    #if (BT_DUAL_MODE || BLE_STD_MODE)
    if(IntStat & INT_STATUS_RWBLE_bit)
	{
		fiq_status |= INT_STATUS_RWBLE_bit;
		rwble_isr();
	}
    #endif //(BT_DUAL_MODE || BLE_STD_MODE) 
    #if (BT_DUAL_MODE || BT_STD_MODE) 
	if(IntStat & INT_STATUS_RWBT_bit)
	{
		fiq_status |= INT_STATUS_RWBT_bit;
        rwbt_isr();
	} 
    #endif //(BT_DUAL_MODE || BT_STD_MODE)


	if(IntStat & INT_STATUS_DMA_bit)
	{
		fiq_status |= INT_STATUS_DMA_bit;
        dma_isr();
	}
	intc_status_clear(fiq_status);
}


void Undefined_Exception(void)
{

}
void SoftwareInterrupt_Exception(void)
{


}
void PrefetchAbort_Exception(void)
{


}
void DataAbort_Exception(void)
{


}
	
void Reserved_Exception(void)
{

}

#if defined(__CC_ARM)

#pragma ARM//不要修改以下两个文件
__IRQ FAST_IRQ_ENTRY void SYSirq_IRQ_Handler(void)
{
    intc_irq();		
}

__FIQ FAST_FIQ_ENTRY void SYSirq_FIQ_Handler(void)
{
    intc_fiq();	 
}

const  unsigned int BK36 __attribute__((at(0x100)))={0x36334B42};
const  unsigned int BK33 __attribute__((at(0x104)))={0x00103333};
/// @} INTC
#else

 void SYSirq_IRQ_Handler(void)
{
    intc_irq();		
}

 void SYSirq_FIQ_Handler(void)
{
    intc_fiq();	 
}


//#pragma GCC target ("arm")
//__attribute__((__interrupt__("IRQ"))) 
void Irq_Exception(void)
{


}


 
volatile  unsigned int BK36[] __attribute__((section(".section_bk")))=
{
    0x36334B42,0x00103333,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,
    0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000
};

#endif

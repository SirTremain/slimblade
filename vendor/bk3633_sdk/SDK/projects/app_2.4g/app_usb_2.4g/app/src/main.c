/**
 ****************************************************************************************
 *
 * @file arch_main.c
 *
 * @brief Main loop of the application.
 *
 * Copyright (C) RivieraWaves 2009-2015
 *
 *
 ****************************************************************************************
 */
#include <stdlib.h>    // standard lib functions
#include <stddef.h>    // standard definitions
#include <stdint.h>    // standard integer definition
#include <stdbool.h>   // boolean definition
#include <string.h>   // boolean definition
#include "intc.h"      // Interrupt initialization
#include "uart.h"      // UART initialization
#include "uart2.h"      // UART2 initialization
#include "flash.h"     // Flash initialization
#include "app.h"       // application functions
#include "reg_access.h"
#include "boot.h"
#include "dbg.h"
#include "icu.h"
#include "user_config.h"
#include "gpio.h"
#include "icu.h"
#include "wdt.h"
#include "spi.h"
#include "adc.h"
#include "uart2.h"
#include "aon_rtc.h"
#include "rf.h"
#if(USB_DRIVER)
#include "driver_usb.h"
#endif
#include "Application_mode.h"
extern void  xvr_reg_initial_24(void);
uint8_t uart_rx_en;

static void stack_integrity_check(void)
{
	if ((REG_PL_RD(STACK_BASE_UNUSED)!= BOOT_PATTERN_UNUSED))
	{
		while(1)
		{
			uart_printf("Stack_Integrity_Check STACK_BASE_UNUSED fail!\r\n");
		}
	}

	if ((REG_PL_RD(STACK_BASE_SVC)!= BOOT_PATTERN_SVC))
	{
		while(1)
		{
			uart_printf("Stack_Integrity_Check STACK_BASE_SVC fail!\r\n");
		}
	}

	if ((REG_PL_RD(STACK_BASE_FIQ)!= BOOT_PATTERN_FIQ))
	{
		while(1)
		{
			uart_printf("Stack_Integrity_Check STACK_BASE_FIQ fail!\r\n");
		}
	}

	if ((REG_PL_RD(STACK_BASE_IRQ)!= BOOT_PATTERN_IRQ))
	{
		while(1)
		{
			uart_printf("Stack_Integrity_Check STACK_BASE_IRQ fail!\r\n");
		}
	}

}







void platform_reset(uint32_t error)
{

    uart_printf("reset error = %x\r\n", error);
    // Disable interrupts
    GLOBAL_INT_STOP();

    cpu_reset();

}



int main(void)
{
    icu_init();

  //  wdt_disable();
    intc_init();
    
#if(UART_PRINTF_ENABLE)
    #if(!USB_DRIVER)
    uart_init(115200);
    #endif
    uart2_init(1000000);//
#endif


    gpio_init();
    flash_init();
  //  xvr_reg_initial_24();
  //  gpio_set_neg(0x04);

    xvr_reg_initial();

    mcu_clk_switch(MCU_CLK_16M);
    
#if(AON_RTC_DRIVER)
    aon_rtc_init();
#endif
#if(SPI_DRIVER)
    spi_init(0,0,0);
#endif


#if(ADC_DRIVER)
    adc_init(1,1);
#endif
#if(USB_DRIVER)
    usb_init(1);
#endif
	

    gpio_cb_register(app_gpio_sleep);
    GLOBAL_INT_START();
 //   gpio_set_neg(0x04);

    uart_printf("main start~~~~~\r\n");
    fn24main();
    while(1)
    {

        stack_integrity_check();


    }
}







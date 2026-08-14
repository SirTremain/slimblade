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
#include "rwip_config.h" // RW SW configuration
#include "arch.h"      // architectural platform definitions
#include <stdlib.h>    // standard lib functions
#include <stddef.h>    // standard definitions
#include <stdint.h>    // standard integer definition
#include <stdbool.h>   // boolean definition
#include <string.h>   // boolean definition
#include "rwip.h"      // RW SW initialization
#include "prf.h"      // RW SW initialization
#include "rwble.h"

#include "intc.h"      // Interrupt initialization
#if PLF_UART
#include "uart.h"      // UART initialization
#if PLF_UART2
#include "uart2.h"      // UART2 initialization
#endif // PLF_UART2
#endif //PLF_UART
#include "flash.h"     // Flash initialization
#include "led.h"       // Led initialization
#if (BLE_EMB_PRESENT || BT_EMB_PRESENT)
//#include "rf.h"        // RF initialization
#endif // BLE_EMB_PRESENT || BT_EMB_PRESENT

#if (BLE_APP_PRESENT)
#include "app.h"       // application functions
#endif

#if (NVDS_SUPPORT)
#include "nvds.h"         // NVDS definitions
#endif
#include "reg_access.h"
#include "boot.h"
#include "dbg.h"
#include "icu.h"
#include "user_config.h"
#include "co_utils.h" 
#include "gpio.h"
#include "icu.h"
#include "wdt.h"
#include "spi.h"
#include "adc.h"
#include "uart2.h"
#include "aon_rtc.h"
#include "lcd360g.h"
#include "oads.h"
#include "rf.h"


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

static void rom_env_init(struct rom_env_tag *api)
{
	memset(&rom_env,0,sizeof(struct rom_env_tag));
	rom_env.prf_get_id_from_task = prf_get_id_from_task;
	rom_env.prf_get_task_from_id = prf_get_task_from_id;
	rom_env.prf_init = prf_init;
	rom_env.prf_create = prf_create;
	rom_env.prf_cleanup = prf_cleanup;
	rom_env.prf_add_profile = prf_add_profile;

	rom_env.rwip_reset = rwip_reset;
	rom_env.platform_reset = platform_reset;
	rom_env.rwble_sleep_wakeup_end = rwble_sleep_wakeup_end;
	rom_env.stack_printf=uart2_printf;
	//rom_env.assert_err = assert_err;
	//rom_env.assert_param = assert_param;
	//rom_env.Read_Uart_Buf = Read_Uart_Buf;
	//rom_env.uart_clear_rxfifo = uart_clear_rxfifo;

}

/*
 * GLOBAL VARIABLE DEFINITIONS
 ****************************************************************************************
 */
#if PLF_UART		////Added
// Creation of uart external interface api
const struct rwip_eif_api uart_api =
{
    uart_read,
    uart_write,
    uart_flow_on,
    uart_flow_off,
};
#endif




void bdaddr_env_init(void)
{
	struct bd_addr co_bdaddr;
	flash_read_data(&co_bdaddr.addr[0],0x7E000,6);
	if(co_bdaddr.addr[0]!=0xff ||co_bdaddr.addr[1]!=0xff||
	        co_bdaddr.addr[2]!=0xff||co_bdaddr.addr[3]!=0xff||
	        co_bdaddr.addr[4]!=0xff||co_bdaddr.addr[5]!=0xff )
	{
		memcpy(&co_default_bdaddr,&co_bdaddr,6);
	}        
}



#if (PLF_DEBUG)
void assert_err(const char *condition, const char * file, int line)
{
	uart_printf("%s,condition %s,file %s,line = %d\r\n",__func__,condition,file,line);
}

void assert_param(int param0, int param1, const char * file, int line)
{
	uart_printf("%s,param0 = %d,param1 = %d,file = %s,line = %d\r\n",__func__,param0,param1,file,line);
}

void assert_warn(int param0, int param1, const char * file, int line)
{
	uart_printf("%s,param0 = %d,param1 = %d,file = %s,line = %d\r\n",__func__,param0,param1,file,line);
}

void dump_data(uint8_t* data, uint16_t length)
{
	uart_printf("%s,data = %d,length = %d,file = %s,line = %d\r\n",__func__,data,length);
}

#endif //PLF_DEBUG



void platform_reset(uint32_t error)
{   
    uart_printf("reset error = %x\r\n", error);
    // Disable interrupts
    GLOBAL_INT_STOP();
    
    // Restart FW
    cpu_reset();    
}

uint8_t system_mode;
void sys_mode_init(uint8_t mode)
{
	system_mode = mode;
}
uint8_t get_sys_mode(void)
{
	return system_mode;
}
void enter_dut_fcc_mode(void)
{
	while(1)
	{
		// schedule all pending events
		rwip_schedule();
        #if (VIRTUAL_UART_H4TL == 1)
		uart_h4tl_data_switch();
	    #endif
	}
}

void enter_normal_app_mode(void)
{
	while(1)
	{
        // schedule all pending events
        rwip_schedule();

        //adc_get_value(1);
		oad_updating_user_section_pro();
        // Checks for sleep have to be done with interrupt disabled
        GLOBAL_INT_DISABLE();
        // Check if the processor clock can be gated
 #if 0  
        if( NO_SLEEP!=icu_get_sleep_mode() )
        {
            switch(rwip_sleep())
            {
                case RWIP_DEEP_SLEEP:        
                {    
                    // add here platform specific deep sleep code  
                    if(MCU_REDUCE_VO_SLEEP==icu_get_sleep_mode())
                    {
                        cpu_reduce_voltage_sleep();         
                        cpu_wakeup();
                    }
                    else if(MCU_IDLE_SLEEP==icu_get_sleep_mode())
                    {
                        cpu_idle_sleep();
                    }
                    else if(MCU_DEEP_SLEEP==icu_get_sleep_mode())
                    {
                        ////before deepsleep use (deep_sleep_wakeup_set)  config gpio wakeup mcu
                        ////deep_sleep_wakeup_set(0X10);
                        deep_sleep();
                    }
                }
                break;
                case RWIP_CPU_SLEEP:
                {   
                    // Wait for interrupt
                    cpu_idle_sleep(); 
                }
                break;
                case RWIP_ACTIVE:
                default:
                {
                    // nothing to do.
                } break;
            }
        }
#endif        
        // Checks for sleep have to be done with interrupt disabled
        GLOBAL_INT_RESTORE();
        stack_integrity_check();
	}
}


int main(void)
{
    icu_init();
    
    wdt_disable();

    intc_init();

    sys_mode_init(NORMAL_MODE);
    
    gpio_config(0x00,INPUT,PULL_HIGH); 
    Delay_ms(1);
    if(0==gpio_get_input(0x00))
    {
        Delay_ms(10);
        if(0==gpio_get_input(0x00))
            sys_mode_init(DUT_FCC_MODE);
    }
    
    uart_init(115200);
    uart2_init(1000000);

    gpio_init(); 

    //timer_init();
    
    flash_init();

    bdaddr_env_init();

    srand(co_default_bdaddr.addr[0]+co_default_bdaddr.addr[5]);
    
#if (NVDS_SUPPORT)
    nvds_init();
#endif 
    rom_env_init(&rom_env);
    // Initialize RW SW stack
    rwip_init(0);

    uart_printf("rw_main  start!!!=%x \r\n",EM_BLE_END);

    if((system_mode & DUT_FCC_MODE) == DUT_FCC_MODE) //dut mode
	{
        uart_printf("enter_dut_fcc_mode \r\n");
        GLOBAL_INT_START();
		mcu_clk_switch(MCU_CLK_80M);
		enter_dut_fcc_mode();
	}
	else //normal mode
	{
        uart_printf("enter_normal_app_mode \r\n");
        
        mcu_clk_switch(MCU_CLK_80M);
        
        #if(AON_RTC_DRIVER)   
        aon_rtc_init();
        #endif
        #if(SPI_DRIVER)    
        spi_init(0,1,0);
        #endif

        #if(ADC_DRIVER) 
        adc_init(1,1);
        #endif
        
        GLOBAL_INT_START();
        
		enter_normal_app_mode();
	}
    
}


const struct rwip_eif_api* rwip_eif_get(uint8_t idx)
{
    const struct rwip_eif_api* ret = NULL;
    switch(idx)
    {
		#if PLF_UART		////
        case 0:
        {
            ret = &uart_api;
        }
        break;
		#endif
        default:
        {
            ASSERT_INFO(0, idx, 0);
        }
        break;
    }
    return ret;
}





/**
 ****************************************************************************************
 *
 * @file bim_intc.c
 *
 * @brief Definition of the Interrupt Controller (INTCTRL) API.
 *
 * Copyright (C) RivieraWaves 2009-2015
 *
 *
 ****************************************************************************************
 */
#include "bim_intc.h"
#include <string.h>
#include "bim_uart2.h"
#include "bim_wdt.h"
#include "bim_icu.h"
#include "driver_usb.h"

typedef void (*FUNCPTR_T)(void);

void Undefined_Exception(void)
{
    wdt_enable(0X10);
    while(1)
    {
        //uart_putchar("Undefined_Exception\r\n");
    }
}
void SoftwareInterrupt_Exception(void)
{
    wdt_enable(0X10);
    while(1)
    {
        //uart_putchar("SoftwareInterrupt_Exception\r\n");
    }
}
void PrefetchAbort_Exception(void)
{
    wdt_enable(0X10);
    while(1)
    {
        //uart_putchar("PrefetchAbort_Exception\r\n");
    }
}
void DataAbort_Exception(void)
{
    wdt_enable(0X10);
    while(1)
    {
        //uart_putchar("DataAbort_Exception\r\n");
    }
}

void Reserved_Exception(void)
{
    wdt_enable(0X10);
    while(1)
    {
        //uart_putchar("Reserved_Exception\r\n");
    }
}


__IRQ void Irq_Exception(void)
{
    uint32_t IntStat=SYS_REG0X12;
    
    if(IntStat & (1<<POS_SYS_REG0X12_INT_USB_STA))
    	USB_InterruptHandler();
  
    SYS_REG0X12=IntStat;

}

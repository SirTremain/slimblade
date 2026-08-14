/*************************************************************
 * @file        driver_usb.c
 * @brief       code of USB driver of BK3435_v2
 * @author      GuWenFu
 * @version     V1.0
 * @date        2016-09-29
 * @par
 * @attention
 *
 * @history     2016-09-29 gwf    create this file
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "driver_icu.h"
#include "driver_usb.h"
#include "mu_impl.h"

#include "bk3633_reglist.h"

void DelayNops(volatile unsigned int nops)
{
    while (nops --)
    {
    }
}



extern int usb_sw_init(void);
extern void MGC_AfsUdsIsr(uint16_t wIntrTxValue,uint16_t wIntrRxValue,uint8_t bIntrUsbValue);

void usb_init(uint8_t usb_mode)
{
    //uart_printf("usb_sw_init OK\r\n");
    unsigned char ucUSBIntStatus;
 
    setf_SYS_Reg0x3_usb_pwd;
    DelayNops(500);
   
    clrf_SYS_Reg0x3_usb_pwd;

    REG_USB_INTRRX1E = 0x0;
    REG_USB_INTRTX1E = 0x0;
    REG_USB_INTRUSBE = 0x0;
    REG_AHB2_USB_VTH &= ~(1<<7);

    if (usb_mode == USB_HOST_MODE)
    {
        REG_AHB2_USB_OTG_CFG = 0x50;        // host
        REG_AHB2_USB_DEV_CFG = 0x00;
    }
    else
    {
        REG_USB_INTRRX1E = 0x07;
        REG_USB_INTRTX1E = 0x07;
        REG_USB_INTRUSBE = 0x3F;
        REG_AHB2_USB_OTG_CFG = 0x08;        // device
        REG_AHB2_USB_DEV_CFG = 0xF4;
        REG_AHB2_USB_OTG_CFG |= 0x01;
    }

    ucUSBIntStatus = REG_AHB2_USB_INT;
    DelayNops(500);
    REG_AHB2_USB_INT = ucUSBIntStatus;
    DelayNops(500);

    REG_AHB2_USB_GEN = (0x7<<4) | (0x7<<0);   //  DP_EN DN_EN

    if(usb_sw_init() == 0)
    {
        ICU_INT_ENABLE_SET(ICU_INT_ENABLE_IRQ_USB_MASK);
        bim_printf("usb_sw_init OK\r\n");
    }
    else
    {
        bim_printf("usb_sw_init failed!\r\n");
    }
    REG_AHB2_USB_RESET |= 0x01;
}

void usb_deinit(void)
{
    REG_USB_INTRRX1E = 0x0;
    REG_USB_INTRTX1E = 0x0;
    REG_USB_INTRUSBE = 0x0;
    ICU_INT_ENABLE_CLEAR(ICU_INT_ENABLE_IRQ_USB_MASK);

    REG_AHB2_USB_GEN = 0;
    REG_AHB2_USB_OTG_CFG = 0;

    ICU_USB_PWD_SET();
}

void USB_InterruptHandler(void)
{
	//uint8 ucUSBIntStatus = REG_AHB2_USB_INT;
	uint8 bIntrUsbValue = REG_USB_INTRUSB;
	uint16 wIntrTxValue = REG_USB_INTRTX1 | (REG_USB_INTRTX2 << 8);
	uint16 wIntrRxValue = REG_USB_INTRRX1 | (REG_USB_INTRRX2 << 8);

	//os_printf("------------------- USB_InterruptHandler in  ---------------------\r\n");

	bIntrUsbValue &= ~(0xc0);
	MGC_AfsUdsIsr(wIntrTxValue,wIntrRxValue,bIntrUsbValue);
	//os_printf("------------------- USB_InterruptHandler out ---------------------\r\n");
}

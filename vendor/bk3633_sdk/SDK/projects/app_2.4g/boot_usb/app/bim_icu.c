/**
****************************************************************************************
*
* @file icu.c
*
* @brief icu initialization and specific functions
*
* Copyright (C) Beken 2009-2016
*
* $Rev: $
*
****************************************************************************************
*/
#include <stddef.h>     // standard definition
#include "bim_icu.h"      // timer definition
#include "bim_uart2.h"
void icu_init(void)
{
    SYS_REG0X0 &= ~(1<<POS_SYS_REG0X0_JTAG_MODE);///close JTAG
    SYS_REG0X2 =0;
    SYS_REG0X2 = (1<< POS_SYS_REG0X2_CORE_SEL);///16M CLK
    SYS_REG0X17 &= ~0x2;
    SYS_REG0X0D |= 0x40;

}

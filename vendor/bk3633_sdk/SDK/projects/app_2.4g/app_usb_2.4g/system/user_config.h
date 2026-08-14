/**
 ****************************************************************************************
 *
 * @file user_config.h
 *
 * @brief Configuration of the BT function
 *
 * Copyright (C) Beken 2019
 *
 ****************************************************************************************
 */
#ifndef USER_CONFIG_H_
#define USER_CONFIG_H_
#include "uart2.h"
#include "uart.h"

/// Use RC 32Kif INTER_RC32K set to 1
#define INTER_RC32K            1
#define UART_PRINTF_ENABLE     1
#define DEBUG_HW               0
#define GPIO_DBG_MSG           0
#define MALLCO_DEFINE          1


//DRIVER CONFIG
#define UART0_DRIVER			1
#define UART2_DRIVER			1
#define GPIO_DRIVER				1
#define AUDIO_DRIVER			0
#define RTC_DRIVER				0
#define ADC_DRIVER				1
#define I2C_DRIVER				0
#define PWM_DRIVER				0
#define USB_DRIVER              1
#define SPI_DRIVER              0
#define AON_RTC_DRIVER          0



#define uart_printf              uart2_printf


#ifndef NULL
#define NULL (void*)0
#endif


#define LDO_MODE 1


#endif // USER_CONFIG_H_



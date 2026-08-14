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

#define VIRTUAL_UART_H4TL	       1
#define UART_PRINTF_ENABLE         1
#define DEBUG_HW                   0
#define DEBUG_HW_DIGITAL           0
#define GPIO_DBG_MSG               0
#define DEBUG_RF_REG               0
#define LDO_MODE                   0
#define LDO_MODE_IN_SLEEP          1



//DRIVER CONFIG
#define UART0_DRIVER				1
#define UART2_DRIVER				1

#define GPIO_DRIVER					0
#define ADC_DRIVER					0
#define I2C_DRIVER					0
#define PWM_DRIVER					0
#define USB_DRIVER                  0 
#define SPI_DRIVER                  0 
#define AON_RTC_DRIVER              1


#define uart_printf              uart2_printf




/// Default Device Name
#define APP_DFLT_DEVICE_NAME            ("BK3633_BLE")
#define APP_DFLT_DEVICE_NAME_LEN        (sizeof(APP_DFLT_DEVICE_NAME))

#define APP_SCNRSP_DATA         "\x09\xFF\x00\x60\x42\x4B\x2D\x42\x4C\x45"
#define APP_SCNRSP_DATA_LEN     (10)



/// Advertising channel map - 37, 38, 39
#define APP_ADV_CHMAP           (0x07)
/// Advertising minimum interval - 40ms (64*0.625ms)
#define APP_ADV_INT_MIN         (160 )
/// Advertising maximum interval - 40ms (64*0.625ms)
#define APP_ADV_INT_MAX         (160)
/// Fast advertising interval
#define APP_ADV_FAST_INT        (32)

/// Advertising channel map - 37, 38, 39
#define APP_MESH_ADV_CHMAP           (0x07)
/// Advertising minimum interval - 40ms (64*0.625ms)
#define APP_MESH_ADV_INT_MIN         (80 )
/// Advertising maximum interval - 40ms (64*0.625ms)
#define APP_MESH_ADV_INT_MAX         (80)
/// Fast advertising interval
#define APP_MESH_ADV_FAST_INT        (32)



//最小连接间隔
#define BLE_UAPDATA_MIN_INTVALUE		20
//最大连接间隔 
#define BLE_UAPDATA_MAX_INTVALUE		40
//连接Latency
#define BLE_UAPDATA_LATENCY				0
//连接超时
#define BLE_UAPDATA_TIMEOUT				600






#endif // USER_CONFIG_H_



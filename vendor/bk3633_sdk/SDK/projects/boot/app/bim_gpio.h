/**
 ****************************************************************************************
 *
 * @file gpio.h
 *
 * @brief gpio Driver for gpio operation.
 *
 * Copyright (C) Beken 2009-2015
 *
 *
 ****************************************************************************************
 */
#ifndef _GPIO_H_
#define _GPIO_H_
#include <stdbool.h>          // standard boolean definitions
#include <stdint.h>           // standard integer functions
#define BASEADDR_GPIO                                           0x00800A00
#define GPIO_INPUT_VA   0
#define GPIO_OUTPUT_VA  1
#define GPIO_INPUT_EN   2
#define GPIO_OUTPUT_EN  3
#define GPIO_PULL_MODE  4
#define GPIO_PULL_EN    5
#define GPIO_2FUN_EN    6
typedef enum
{
    INPUT,
    OUTPUT,
    FLOAT,
    SC_FUN,
} Dir_Type;
typedef enum
{
    PULL_HIGH,
    PULL_LOW,
    PULL_NONE
} Pull_Type;

typedef void (*GPIO_INT_CALLBACK_T)(void);
void gpio_cb_register(GPIO_INT_CALLBACK_T cb);
void gpio_init(void);
void gpio_config(uint8_t gpio, Dir_Type dir, Pull_Type pull);
uint8_t gpio_get_input(uint8_t gpio);
void gpio_set(uint8_t gpio, uint8_t val);
void gpio_target(uint8_t gpio);
void gpio_isr(void);
void gpio_sleep(void);
void gpio_wakeup(void);
void gpio_triger(uint8_t gpio);
void DEBUG_MSG(uint8_t x);

#endif

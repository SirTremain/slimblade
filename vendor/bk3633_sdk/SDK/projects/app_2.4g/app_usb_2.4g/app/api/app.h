#ifndef _APP_H__
#define _APP_H__

#include "define_system.h"
#include "uart2.h"
#include "uart.h"


extern void Delay_ms(int num);
extern void Delay_us(int num);

typedef uint8_t boolean;
typedef struct
{
    uint8_t   key;
    int16_t  sensor_x;
    int16_t  sensor_y;
    uint8_t   sensor_cpi;
    uint8_t   wheel;
    uint8_t   pair_key;
}APP_MOUSE_T ;

typedef enum
{
    PAIR_KEY_IDLE=0,
    PAIR_KEY_PAIR ,
    PAIR_KEY_MODE_CHANGE ,
    PAIR_KEY_24_TO_BT ,
} pair_key;

typedef enum
{
    APP_VOLTAGE_1V5=0Xba,
    APP_VOLTAGE_1V4=0Xac,
    APP_VOLTAGE_1V3=0Xa1,
    APP_VOLTAGE_1V2=0X96,
    APP_VOLTAGE_1V1=0X8b,
    APP_VOLTAGE_1V0=0X80,
    APP_VOLTAGE_0V9=0x73,	// 0X70,
    APP_VOLTAGE_0V8=0X60,
    APP_VOLTAGE_0V7=0X50,
    APP_VOLTAGE_0V6=0X40,
} bat_voltage;

#define SENSOR_TEST         1


#define TEST_PIN1           0X14
#define TEST_PIN2           0x15
#define TEST_PIN3           0x20
#define TEST_PIN4           0x21

#define PCBA_SCLK           0x04
#define PCBA_SDIO           0x32
#define PCBA_SACK           0x31

#define WHEEL_B             0x32
#define WHEEL_A             0x31

#define KEY_RIGHT           0X11
#define KEY_LEFT            0x12
#define KEY_MIDDLE          0x13
#define KEY_PAIR            0x10

#define PAW3205_SDIO_PIN    0x03
#define PAW3205_SCLK_PIN    0x04
#define PAW3205_MOTSWK_PIN  0x05	// note:must check the IO need (pull down & up)wakeup

#define LED_24              0x06

#define	SHORT_CNT			                            2
#define	LONG_CNT			                            250
#define	LONG_REPEAT_CNT		                            300

#define MOUSE_STANDARD_KEY_LEFT                 0x01
#define MOUSE_STANDARD_KEY_RIGHT                0x02
#define MOUSE_STANDARD_KEY_MIDDLE               0x04
#define MOUSE_STANDARD_KEY_BACK                 0x08
#define MOUSE_STANDARD_KEY_FORAWARD             0x10
#define MOUSE_STANDARD_KEY_DPI                  0x20
#define MOUSE_STANDARD_KEY_SWING_LEFT           0x40
#define MOUSE_STANDARD_KEY_SWING_RIGHT          0x80
#define	cLowBatCNT           3
#define cBatADCFilt         3
#define ADC_CHANNEL         6


#define B_0100_0000         0x40
#define B_1000_0000         0x80
#define B_1100_0000         0xc0
#define B_1000_0001         0x81
#define B_0000_0000         0x00
#define B_1000_0010         0x82
#define B_1000_0011         0x83
#define B_0111_1111         0x7f

//RF_flag bit set
#define flag_rf_paged               0x00000001
#define flag_dongle_lost            0x00000002
#define flag_rf_send                0x00000004
#define flag_tick_8ms_loop          0x00000008
#define flag_key_released           0x00000010
#define flag_key_pressed            0x00000020
#define flag_key_short              0x00000040
#define flag_key_long               0x00000080
#define flag_status_idle            0x00000100
#define flag_status_sleep           0x00000200
#define flag_rf_send_end            0x00000400
#define flag_rf_last_state          0x00000800
#define flag_rf_need_clear_maxRT    0x00001000
#define flag_rf_hop_16ch            0x00002000
#define flag_wake_up_by_timer       0x00004000
#define flag_power_up               0x00008000
#define flag_low_batt               0x00010000
#define flag_rf_receive_page        0x00020000 // 0 allow to page with dongle when power up
#define flag_rf_send_success        0x00040000
#define	flag_system_powerdown		0x00080000	// dongle unused.



void app_gpio_sleep(void);
void app_mouse_wheel_scan(void);
void app_mouse_key_scan(void);
void app_mouse_key_check(void);
void app_timer0_1_int_cb(void);
void app_timer1_2_int_cb(void);
void driver_delay_set_with_base_tick(TIMER *timer, uint32_t timeout);
uint8_t driver_delay_with_base_tick_expire_check(TIMER *timer);
void driver_timer0_reset(void);
#endif

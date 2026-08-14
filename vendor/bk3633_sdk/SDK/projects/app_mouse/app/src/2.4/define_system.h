#ifndef	_DEFINE_SYSTEM_H
	#define	_DEFINE_SYSTEM_H
#include "BK_system.h"

#define SENSOR_POWER_OFF
// System  mode
typedef enum _APPLICATION_MODE
{
    SYSTEM_NORMAL = 0x00,
    SYSTEM_PAGE,
    SYSTEM_CONFIGURE,
    SYSTEM_DEBUG,
    SYSTEM_TEST,
    SYSTEM_PCBA,
    SYSTEM_MODE_MAX
} SYSTEM_MODE;
// timer struct definition
typedef struct _TIME_STRUCT
{
//12B
    uint32_t tick_system;        // system timer tick, 8ms
    uint8_t  tick_2ms;                    // 2ms, 2*4=8ms
    uint16_t tick_sleep_check;      // 2ms, 2*5000=10s
    uint16_t tick_lbd_check;          // 2ms, 1250**4*2=10s
    uint16_t tick_rf_send_fail;      // 8ms, 60*8=480ms
    uint16_t tick_test_power_up;  // 8ms, 7500*8=60s
} TIME_STRUCT;
// system timer struct
typedef struct _TIMER
{
// 4B
    uint32_t value_expired;           //time out value
} TIMER;
typedef struct _SYS_Led
{
    uint8_t freq;                // the count of flicker
    uint8_t time;                // ms
    TIMER led_timer;
} SYS_Led;
//#########System Struct Definiton Mouse Part Start###################
// sensor cpi
typedef enum _DIRVER_SENSOR_DIRECTION
{
    DIRECTION_0 = 0x00,
    DIRECTION_90,
    DIRECTION_180,
    DIRECTION_270,
    DIRECTION_MAX
} SENSOR_DIRECTION;
// sensor type
typedef enum _DIRVER_SENSOR_TYPE
{
    SENSOR_NONE,
    SENSOR_3205,
    SENSOR_3065,
} SENSOR_TYPE;
// sensor value
typedef struct _DIRVER_SENSOR_VALUE
{
    uint8_t dpi_index;
    uint8_t dpi_value[3];
    SENSOR_DIRECTION direction;
    SENSOR_TYPE type;
    int16_t x;
    int16_t y;
    uint8_t   sensor_up;
	uint8_t bDisplayBTMode;
    uint16_t sensor_up_count;
} SENSOR_VALUE;
//#########System Struct Definiton Shard Part Start####################
// system state defined in data region
typedef struct _APPLICATION_STRUCT_DATA
{
//35B
    uint8_t system_mode;
    TIME_STRUCT time;                              //12B
//    uint8_t led_flick_count;
//    uint16_t led_period_count;
    uint8_t key_current;
    uint8_t key_valid;
    SENSOR_VALUE sensor_val;                 // 9B
    int8_t wheel;
	uint8_t rf_array;
    uint8_t rf_channel;
    uint8_t rf_send_length;
    uint8_t rf_connect;
    uint8_t lbd_count;
	uint8_t bled_flag;
    SYS_Led led;                                        // 6B
#ifdef SENSOR_POWER_OFF
    uint8_t dongle_lost_count;
    uint16_t dongle_search_count;
#endif
	uint16_t idle_time;
#if MOUSE_SWING
	int8_t swing;
#endif
} SYSTEM_STRUCT_DATA;
//#########System Definiton Mouse & Keyboard Part Start##########
//   send information
#define SYSTEM_SYNCHRONIZE      0x02
#define SYSTEM_END              0x04
#define SYSTEM_NEXT_CH          0x08
#define SYSTEM_SLEEP            0x8a
#define PAGE_WAIT_TIME          5000      // keyboard 4ms*5000=20s, mouse 8ms*5000=40s
//#########System Definiton Mouse & Keyboard Part End###########
// data type
typedef enum _DATATYPE
{
    DATATYPE_NULL = 0x80,
    DATATYPE_MOUSE = 0x01,	// 0x00,
    DATATYPE_KEYBOARD = 0x10,	// 0x01,
    DATATYPE_PAGE_START = 0xA5,
    DATATYPE_PAGE_END_MOUSE = 0x34,
    DATATYPE_PAGE_END_KEYBOARD = 0x36,
    DATATYPE_MOUSE_SEARCH_DONGLE = 0x50,
    DATATYPE_MOUSE_SLEEP = 0x28,
    KEYBOARD_LED_STATUS=0x41,//add  keyboard led status
    #if	0
    DATATYPE_CMD = 0x02,
    DATATYPE_M_CMD = 0x90,
    DATATYPE_TXID_CMD = 0xc0,
    #endif
    DATATYPE_MAX
} DATATYPE;
// time * 8
#define LBD_CHECK_TIME_MOUSE                            1250*4    // 2*1250=10s
#define SYSTEM_SEND_FAIL_TIME_MOUSE                     150      // 8*150=1200ms
#define POWER_UP_TEST_CHECK_TIME_MOUSE                  7500    // 7500*8=60s
// 2ms
#define SYSTEM_SLEEP_TIME_MOUSE                         5000    // 5000*2=10s
#define DONGLE_SEARCH_TIME_MOUSE                        1000    // 2*1000=2S
#define SLEEP_DELAY_TIME                                5000
#define ID2 0x01
#define ID3 0x02
#define ID0 0x03
#define ID1 0x04
#define ID4 0x05

#endif

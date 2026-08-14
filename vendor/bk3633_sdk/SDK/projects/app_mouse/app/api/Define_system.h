#ifndef	_DEFINE_SYSTEM_H
	#define	_DEFINE_SYSTEM_H
#include <stdint.h>    // standard integer definition
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
//    uint16 led_period_count;
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
	uint8_t swing;
#endif
}SYSTEM_STRUCT_DATA;


typedef struct
{
    uint8_t   key;
    int16_t   sensor_x;
    int16_t   sensor_y;
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

#define BUF_CNT  1
#define BUF_SIZE  10


typedef struct
{
    uint8_t     buf[BUF_CNT][BUF_SIZE];
    uint8_t     class_bt_len[BUF_CNT];
    uint8_t     write_index;
    uint8_t     read_index;
    uint8_t     data_cnt;
    uint8_t     read_start_time;
    uint8_t	    powered_bind;
    uint32_t	power_on_cnt;
}APP_VAL_T ;

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


#define	SHORT_CNT			                            2
#define	LONG_CNT			                            250
#define	LONG_REPEAT_CNT		                            300

#define PAIR_KEY_PRESS_TIME                     800///0.25S
#define KEY_PRESS_SHORT_TIME                   100///1S
#define KEY_PRESS_LONG_TIME                     200///2S
#define KEY_PRESS_CANCEL                           5///50ms

#endif

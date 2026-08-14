#ifndef	_APPLICATION_MODE_H
	#define	_APPLICATION_MODE_H

#include "app.h"
#include "application_rf.h"
#include "driver_rf.h"

typedef struct
{
    uint8_t bPwrOnModeCK;
}APP_BT_T ;

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

//   send information
#define SYSTEM_SYNCHRONIZE      0x02
#define SYSTEM_END              0x04
#define SYSTEM_NEXT_CH          0x08
//#define SYSTEM_SLEEP            0x8a
#define PAGE_WAIT_TIME          5000      // keyboard 4ms*5000=20s, mouse 8ms*5000=40s

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


#define	cRFPWR		0x0e	// 0x0b

#define POWER_VALUE_5DBM                        15
#define POWER_VALUE_0DBM                        11
#define POWER_VALUE_MINUS_5DBM                  7
#define POWER_VALUE_MINUS_10DBM                 5
#define POWER_VALUE_MINUS_15DBM                 4
#define POWER_VALUE_MINUS_20DBM                 0
#define PAGE_RX_COUNT_MAX     20
#define PAGE_COUNT_CHECK_DONGLE_LOW     20    // 20/100
#define PAGE_COUNT_CHECK_DONGLE_MIDDLE  15
#define PAGE_COUNT_CHECK_DONGLE_HIGH    15
#define RF_ADDRESS_LEN                          5
#define RF_ADDRESS_FIRST_BYTE                   0x23	// 0xBC


#define	cPWROnEnPageTimer		3750		// 30s
#define	cPageTimer				3750

// wSysFlagfn24 bit set
#define	flag_led_lbd		0x00000001

#define	cLEDOn		0
#define	cLEDOff		1

void application_initial(void);
//void fCheckPage(void);
void f24GetFreqConfigValue(void);
void fn24main(void);
void application_normal_mode_initial(void);
void application_mouse_status_check(void);
void application_mouse_rf_send_check(void);
void application_mouse_sleep_check(void);
void application_mouse_idle_oscxmhz(void);
void application_mouse_wake_up_from_32khz(void);
//void application_mouse_idle_rc32khz_with_2ms_timer(void);
void application_mouse_idle_rc32khz(void);
void application_page_key_check(void);
void application_normal_mode(void);
void application_mouse_channel_search(void);
void general_dongle_search(void);
void application_page_mode(void);
void driver_lbd_process(void);
void LED_Ctrl(uint8_t bLED);
void LED_Toggle(void);
void application_mouse_led_start(uint8_t time, uint8_t freq);
void application_mouse_led_process(void);

#endif

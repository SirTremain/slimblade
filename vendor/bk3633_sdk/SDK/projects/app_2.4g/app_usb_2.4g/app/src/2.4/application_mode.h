#ifndef	_APPLICATION_MODE_H
	#define	_APPLICATION_MODE_H

#include "app.h"
#include "application_rf.h"
#include "driver_rf.h"

typedef struct
{
    uint8_t bPwrOnModeCK;
}APP_BT_T ;


typedef struct
{
    uint8_t	powered_bind;
    uint32_t	power_on_cnt;
}APP_VAL_T ;

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

#ifndef _APP_KEY_H__
#define _APP_KEY_H__

#define POWER_KEY 0X10 ///GPIO07

#define PRESS_TIME 10  ///10*100ms


void app_key_init(void);
uint8_t app_key_scan(void);
void app_key_sleep(void);
void app_key_wakeup(void);
void power_down_satus_set(uint8_t status);
uint8_t power_down_satus_get(void);
#endif


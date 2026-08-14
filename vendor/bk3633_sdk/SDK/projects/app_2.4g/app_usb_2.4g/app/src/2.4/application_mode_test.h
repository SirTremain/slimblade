#ifndef	_APPLICATION_MODE_TEST_H
	#define	_APPLICATION_MODE_TEST_H

#define RF_MODE_SINGLE                          0
#define RF_MODE_NORMAL                          1

typedef enum _SYTEM_TEST_MODE
{
	TEST_SINGLE_WAVE = 0,
	TEST_CD,
	TEST_RF_DATA,
	TEST_MAX
}SYTEM_TEST_MODE;


void driver_rf_mode_single_wave(uint8_t freq);
void driver_rf_mode_normal(void);
void application_test_mode(void);

#endif

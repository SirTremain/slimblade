#include "app.h"
#include "app_key.h"

#include "BK3633_RegList.h"
#include "icu.h"
#include "driver_timer.h"
#include "application_mode.h"
#include "application_mode_test.h"
#include "application_mode_PCBA.h"
#include <string.h>


#include "gpio.h"

#include <string.h>

SYSTEM_STRUCT_DATA system_data;

extern uint32_t P0_Address[5] ;
extern uint32_t RF_flag;
extern uint8_t local_addr[6];
extern APP_VAL_T     app_val;
extern void  xvr_reg_initial_24(void);

APP_BT_T  app_bt;

#define UART_PRINTF	uart_printf
int uart_printf(const char *fmt,...);
extern uint8_t flash_read(uint8_t flash_space, uint32_t address, uint32_t len, uint8_t *buffer, void (*callback)(void));

void f24Init(void)
{
 //   rf24_xvr_init();
    Rf_Init();
//  while(1);
    SetDataRate(1);  // data rate:1M
}
void f24GetFreqConfigValue(void)
{
	system_data.rf_array = 0x0;
	system_data.rf_channel = (uint8_t)(P0_Address[1]);			// P0_Address[1]:ID3(low byte).
	system_data.rf_channel += (uint8_t)(P0_Address[2] >> 3);
	system_data.rf_channel += (uint8_t)(P0_Address[3] >> 4);
	system_data.rf_channel += (uint8_t)(P0_Address[4] >> 6);
	system_data.rf_channel ^= (uint8_t)(P0_Address[1] >> 3);
}
void fReadRFAddr(void)
{
    uint8_t temp[14];
//    system_data.system_mode = SYSTEM_NORMAL;
    flash_read(0,0x7d210, 14,temp, (void*)0);//the addr is the word,so the addr +20
//    uart_printf(" msg=%x,%x,%x,%x,%x\r\n",temp[0],temp[1],temp[2],temp[3],temp[4]);
// 0-7: dongle addr; 8-13 local adddr
    if((temp[0] == (temp[4] ^ 0xff)) && (temp[1] == (temp[5] ^ 0xff)) && (temp[2] == (temp[6] ^ 0xff)) && (temp[3] == (temp[7] ^ 0xff)))
    {
        P0_Address[1] = temp[0];
        P0_Address[2] = temp[1];
        P0_Address[3] = temp[2];
        P0_Address[4] = temp[3];
		P0_Address[0] = RF_ADDRESS_FIRST_BYTE;

		f24GetFreqConfigValue();
    }
    temp[8] = 0xa1;
    temp[9] = 0xa2;
    temp[10] = 0xa3;
    temp[11] = 0xa4;
    temp[12] = 0xa5;
    temp[13] = 0x66;
    memcpy(local_addr,&temp[8],6);
	uart_printf(" msg=%x,%x,%x,%x,%x\r\n",temp[0],temp[1],temp[2],temp[3],system_data.rf_channel);
}

void application_initial(void)
{
	SENSOR_TYPE eType;
	eType = system_data.sensor_val.type;
	memset(&system_data, 0, sizeof(SYSTEM_STRUCT_DATA));
	system_data.sensor_val.type = eType;
    fReadRFAddr();
    f24Init();

    Timer_Initial(0,1,15); // T0,1M
    Timer_Initial(1,0,0); // T1,32k
    Timer0_Start(1,2000000); // 2ms
    //注册IO回调
	timer_cb_register(0,1,app_timer0_1_int_cb);

    gpio_config(TEST_PIN1,OUTPUT, PULL_NONE);
    gpio_config(TEST_PIN2,OUTPUT, PULL_NONE);
    gpio_config(TEST_PIN3,OUTPUT, PULL_NONE);
    gpio_config(TEST_PIN4,OUTPUT, PULL_NONE);

    gpio_config(KEY_RIGHT,INPUT, PULL_HIGH);
    gpio_config(KEY_LEFT,INPUT, PULL_HIGH);
    gpio_config(KEY_MIDDLE,INPUT, PULL_HIGH);
    gpio_config(KEY_PAIR,INPUT, PULL_HIGH);

    gpio_config(LED_24,OUTPUT, PULL_NONE);

    gpio_set(TEST_PIN1,0);
    gpio_set(TEST_PIN2,0);
    gpio_set(TEST_PIN3,0);
    gpio_set(TEST_PIN4,0);
    #if(!SENSOR_TEST)
    app_sensor_init();      //清buff数据，免得对码成功瞬间光标会移动
    #endif
  //  LED_Ctrl(cLEDOff);


    //  WHEEL_WAKEUP_EX_INTERRUPT_FALLING_EDGE;
    SYS_REG0X10_INT_EN |= POS_SYS_REG0X10_INT_EN_TIMER0 |POS_SYS_REG0X10_INT_EN_GPIO;
}
#if	0
void fCheckPage(void)
{
    if(system_data.system_mode == SYSTEM_PAGE)
    {
        return;
    }
    if((!gpio_get_input(KEY_LEFT))&&(!gpio_get_input(KEY_RIGHT)))
        //page
    {
        system_data.system_mode = SYSTEM_PAGE;
    }
    else
    {
        system_data.system_mode = SYSTEM_NORMAL;
        driver_rf_ouput_power_value_set(cRFPWR);
    }
}
#endif

void app_set_24page_timer(void)
{

	app_bt.bPwrOnModeCK = 0x0;
	app_val.power_on_cnt = 0x0;

    if((!gpio_get_input(KEY_RIGHT)) && (!gpio_get_input(KEY_MIDDLE)))
    {

        uart_printf("in 24 \r\n");
    	app_bt.bPwrOnModeCK = 0x01;
    }
    app_val.powered_bind = 0x01;

}

void fWorkModeInit(void)
{

    channel_search = 0;
	flag_test = 0;
	RF_flag = 0x0;

    RF_POWER_UP;
    RF_CMD_FLUSH_TX;
    RF_CMD_FLUSH_RX;
    SwitchToTxMode();
    if(app_bt.bPwrOnModeCK)
    {
        app_bt.bPwrOnModeCK = 0x0;
        if((!gpio_get_input(KEY_LEFT)) && (!gpio_get_input(KEY_RIGHT)) && (!gpio_get_input(KEY_MIDDLE)))
        {
            system_data.system_mode = SYSTEM_TEST;
        }
        else if((!gpio_get_input(KEY_RIGHT)) && (!gpio_get_input(KEY_MIDDLE)))
        {
            system_data.system_mode = SYSTEM_PCBA;
        }
        else
        {
            system_data.system_mode = SYSTEM_NORMAL;
        }
    }
    else
    {
        system_data.system_mode = SYSTEM_NORMAL;
    }

    if(system_data.system_mode == SYSTEM_NORMAL)
    {
        driver_rf_ouput_power_value_set(cRFPWR);
        general_dongle_search();
    }
}


void fn24main(void)
{
 //   uint8 bTest = 0x0;
    uart_printf("in 2.4 mode\r\n");
    gpio_set(LED_24,0);
    xvr_reg_initial_24();

    application_initial();

    app_set_24page_timer();

    fWorkModeInit();
   // rw_sleep();

    while(1)
    {
        if(system_data.system_mode==SYSTEM_NORMAL)
        {
            application_normal_mode();
        }
        else if(system_data.system_mode == SYSTEM_PAGE)
        {
            application_page_mode();
        }
        else if(system_data.system_mode == SYSTEM_TEST)
        {
            application_test_mode();
        }
        else if(system_data.system_mode == SYSTEM_PCBA)
        {
            application_PCBA_mode();
        }
    }
}

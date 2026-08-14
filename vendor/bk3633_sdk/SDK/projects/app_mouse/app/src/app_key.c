/** **************************************************************************************
 *
 * @file app_key.c
 *
 * @brief ffe0 Application Module entry point
 *
 * @auth  alen
 *
 * @date  2017.03.30
 *
 * Copyright (C) Beken 2009-2016
 *
 *
 ****************************************************************************************
 */

#include "rwip_config.h"     // SW configuration

/*
 * INCLUDE FILES
 ****************************************************************************************
 */
#include <string.h>
#include "app.h"                     // Application Definitions
#include "app_task.h"                // application task definitions
#include "app_key.h"               	 // health thermometer functions
#include "co_bt.h"
#include "prf_types.h"               // Profile common types definition
#include "arch.h"                    // Platform Definitions
#include "prf.h"
#include "rf.h"
#include "prf_utils.h"
#include "ke_timer.h"
#include "uart.h"
#include "gpio.h"
#include "app_hid.h"
#include "app_sec.h"
#include "app_hid.h"
#include "icu.h"
#include "BK3633_RegList.h"
//#include "lld_evt.h"
//#include "DEFINE_SYSTEM.h"
#include "driver_timer.h"
extern void deep_sleep_wakeup_set(uint8_t gpio);
extern SYSTEM_STRUCT_DATA system_data;

uint8_t bt_tx_buff[SEND_BUFFER_CNT][SEND_BUFFER_SIZE];
uint8_t tx_buff_len[SEND_BUFFER_CNT];
uint8_t tx_buff_head = 0;
uint8_t tx_buff_tail = 0;
uint8_t tx_buff_count = 0;
uint8_t key_press_flag,key_rel_flag;
uint8_t stan_key_len,old_key_len;
uint8_t cow[KEYBOARD_MAX_COL_SIZE];
uint8_t row[KEYBOARD_MAX_ROW_SIZE];
uint8_t key_flag[KEYBOARD_MAX_ROW_SIZE][KEYBOARD_MAX_COL_SIZE];
uint8_t stan_key[8],old_key[8];
uint8_t real_key_value[KEYBOARD_MAX_COL_SIZE];
uint8_t key_err_time,key_status;
uint8_t m_key,s_key,c_key,p_key,key_null;
uint8_t sys_media_key[4],sys_power_key[1],sys_standard_key[8];
uint8_t data_upload_status;
uint8_t f1_f12[14] = {0,1,4,45,46,11,12,13,14,9,10,8,6,24};
uint8_t axis_x,axis_y;
uint8_t detect_key_start=0;

volatile uint8_t uRF_TXTime;
#if	(KEYBOARD)
volatile eRC_TIMER_DUTY eTimerDuty;
volatile uint8_t uTimer2msCnt;
#endif
extern SYSTEM_STRUCT_DATA system_data;
extern uint32_t RF_flag;

const uint8_t media_key[47][2] =
{
    {0x24,0x02},    //WWW back  0
    {0x25,0x02},    //WWW forward 1
    {0x26,0x02},    //WWW Stop  2
    {0x27,0x02},    //WWW Refresh 3
    {0x21,0x02},    //WWW Search 4
    {0x2A,0x02},    //WWW Favorites  5
    {0x23,0x02},    //WWW Home 6
    {0x8A,0x01},    //Mail  7
    {0xE2,0x00},    //Mute 8
    {0xEA,0x00},    //Volume-  9
    {0xE9,0x00},    //Volume+   10
    {0xCD,0x00},    //Play/Pause  11
    {0xB7,0x00},    //Stop  12
    {0xB6,0x00},    //Prev Track 13
    {0xB5,0x00},    //Next Track  14
    {0x83,0x01},    //Media Select  15
    {0x94,0x01},    //My Computer   16
    {0x92,0x01},    //Calculator   17
    {0x09,0x02},    //More Info  18
    {0xB2,0x00},    //Record     19
    {0xB3,0x00},    //Forward     20
    {0xB4,0x00},    //Rewind      21
    {0x8D,0x00},    //Guide        22
    {0x04,0x00},    //<Reserved>   23
    {0x30,0x00},    //Eject(Mac)   24
    {0x07,0x03},    //H7    25
    {0x0A,0x03},    //H10   26lightness+
    {0x0B,0x03},    //H11   27lightness-
    {0xb1,0x01},    //photo 28
    {0xb8,0x00},    //touchkey 29
    {0x14,0x03},    //H20   30
    {0x01,0x03},    //H1   31
    {0x02,0x03},    //H2   32
    {0x03,0x03},    //H3    33
    {0x04,0x03},    //H4    34
    {0x05,0x03},    //H5    35
    {0x06,0x03},    //H6    36
    {0x08,0x03},    //H8    37
    {0x09,0x03},    //H9    38
    {0x0C,0x03},    //H12   39
    {0x0D,0x03},    //H13   40
    {0x0E,0x03},    //H14   41
    {0x0F,0x03},    //H15   42
    {0x10,0x03},    //H16   43
    {0x11,0x03},    //H17   44
    {0x12,0x03},    //H18   45
    {0x13,0x03},    //H19   46
};

uint8_t power_key[3] =
{
    0x01,   //ACPI:Power
    0x02,   //ACPI:Sleep
    0x04,   //ACPI:Wake up
};



//按键配置
#ifndef __MOUSE__
uint8_t stand_key_map[KEYBOARD_MAX_ROW_SIZE][KEYBOARD_MAX_COL_SIZE]=
{
    {KEY_POWER,			KEY_UP_ARROW,	KEY_NULL},		//KR0
    {KEY_RIGHT_ARROW,	KEY_ENTER,		KEY_LEFT_ARROW},//KR1
    {KEY_NULL,			KEY_DOWN_ARROW,	KEY_NULL},		//KR2
    {KEY_VOLUME_ADD,	KEY_WWW_BACK, 	KEY_VOLUME_SUB},//KR3
    {KEY_SET,			KEY_VOICE, 		KEY_HOME}, 		//KR4
};

uint8_t gpio_buff_c[KEYBOARD_MAX_COL_SIZE]= {0x30,0x31,0x32}; //p3.0,p3.1,p3.2
uint8_t gpio_buff_r[KEYBOARD_MAX_ROW_SIZE]= {0x33,0x34,0x35,0x36,0x37}; //P1.1,p1.4,p1.5,p1.6,p1.7

#endif
volatile uint32_t sys_flag = 0;
app_key_type app_key_state = ALL_KEY_FREE_DELAY;

//语音按键状态，0x0表示释放状态
//static unsigned char voice_key_press_status = 0x0;
//static unsigned char old_voice_key_press_status;
//static uint32_t power_key_delay = 0;
static unsigned char app_clear_bond_flag = 0;
unsigned char restart_adv_after_stop=0;
//声明应用层GPIO中断回调函数
static void app_gpio_int_cb(void);


/*******************************************************************************
    //for 48M clock
    //100=12.5us
    //16=2us
    //8=1us
    //for 32.768 clock
    //8=1.6ms
    //16M clock
    //100=120us
*******************************************************************************/
void delay_us(uint32_t num)
{

    uint32_t i,j;
    for(i=0; i<num; i++)
        for(j=0; j<3; j++)
        {
            ;
        }
}
uint8_t key_sleep_en=0;
extern uint8_t rf_mode;// 0:2.4,1:BLE

static void app_gpio_int_cb(void)
{
	uart_printf("gpio int1\r\n");
	//uart_printf("reg35=%x\r\n",addAON_GPIO_Reg0x35);
    key_sleep_en = 1;

	key_wakeup_set();
	//uart_printf("reg33=%x\r\n",addAON_GPIO_Reg0x33);
	//uart_printf("reg31=%x\r\n",addAON_GPIO_Reg0x31);
	//uart_printf("reg35=%x\r\n",addAON_GPIO_Reg0x35);
	//uart_printf("reg03=%x\r\n",addPMU_Reg0x3);
	//uart_printf("reg04=%x\r\n",addPMU_Reg0x4);
	//restart adv
	//ke_msg_send_basic(APP_ADV_ENABLE_TIMER,TASK_APP,TASK_APP);
    if(rf_mode == RF_BLE_MODE)
    {
        if((app_env.adv_state == APP_ADV_STATE_CREATED)&&
        	(ke_state_get(TASK_APP) == APPM_READY))
        {
            appm_start_advertising();
        }
        #if 0
        detect_key_start = 1;
    	#else
    	if(!ke_timer_active(APP_PERIOD_TIMER, TASK_APP))
    	{
    			uart_printf("start_key_timer=%d,%d\r\n",APP_PERIOD_TIMER,ke_state_get(TASK_APP));
    			//ke_msg_send_basic(APP_PERIOD_TIMER,TASK_APP,TASK_APP);
    			ke_timer_set(APP_PERIOD_TIMER,TASK_APP,APP_KEYSCAN_DURATION);
    	}
    	#endif
    }
}
void app_timer0_1_int_cb(void)
{
    #if (!KEYBOARD)
    uRF_TXTime++;
    system_data.time.tick_2ms++;
    system_data.time.tick_lbd_check++;
    if(system_data.time.tick_2ms >= 4) // 8ms
    {
        system_data.time.tick_2ms = 0;
        system_data.time.tick_system++;
        if(system_data.time.tick_system == 120)
        {
            gpio_set(LED_24,1);

        }
        RF_flag |= flag_tick_8ms_loop ;
    }
    #endif
    RF_flag |= flag_wake_up_by_timer;

}

void app_timer1_2_int_cb(void)
{
    #if (KEYBOARD)
    //  LED_Toggle();
    if(eTimerDuty == cRC_TIMER_2ms)
    {
        uTimer2msCnt++;
        if(uTimer2msCnt > 1)
        {
            uTimer2msCnt -= 2;
            bTimerInc = 1;
        }
    }
    else
    {
        bTimerInc = 1;
        if(eTimerDuty == cRC_TIMER_8ms)
        {
            uRF_TXTime++;
            system_data.time.u32KeyPressTime++;
            system_data.time.tick_4ms++;
            system_data.time.systemBindTick++;
            system_data.time.tick_lbd_check++;
        }
    }

    if(bTimerInc)
    {
        uRF_TXTime++;
        system_data.time.u32KeyPressTime++;
        system_data.time.tick_4ms++;
        system_data.time.systemBindTick++;
        system_data.time.tick_lbd_check++;
        if(system_data.time.tick_4ms > 1) // 8ms
        {
            system_data.time.tick_4ms -= 2;
            system_data.time.tick_system++;

            app_val.power_on_cnt++;
            RF_flag |= flag_tick_8ms_loop;
        }
        if(RF_flag & flag_release_delay)
        {
            system_data.time.releaseTick++;
            if(system_data.time.releaseTick > 10)
            {
                RF_flag &= ~flag_release_delay;
                RF_flag |= flag_release_send;
            }
        }
        RF_flag |= flag_power_on_timer ;
    }
    eTimerDuty = cRC_TIMER_4ms;
    #endif

}

void start_key_timer(void)
{
	if(detect_key_start>=2)
	{
		if(!ke_timer_active(APP_PERIOD_TIMER, TASK_APP))
		{
			uart_printf("start_key_timer=%d,%d\r\n",APP_PERIOD_TIMER,detect_key_start);
			ke_msg_send_basic(APP_PERIOD_TIMER,TASK_APP,TASK_APP);
            //ke_timer_set(APP_PERIOD_TIMER,TASK_APP,APP_KEYSCAN_DURATION);
		}
		detect_key_start=0;
	}else if(detect_key_start != 0)
	{
		detect_key_start++;
	}
}

#ifdef __MOUSE__

void app_enable_deep_sleep_wakeup(void)
{
    deep_sleep_wakeup_set(KEY_LEFT);
    deep_sleep_wakeup_set(KEY_RIGHT);
    deep_sleep_wakeup_set(KEY_MIDDLE);
    deep_sleep_wakeup_set(KEY_PAIR);
    deep_sleep_wakeup_set(SENSOR_MOTSWK_PIN);
    deep_sleep_wakeup_set(WHEEL_A);
    deep_sleep_wakeup_set(WHEEL_B);
}



void key_init(void)  // As GPIO Output
{
	//注册IO回调
	gpio_cb_register(app_gpio_int_cb);

    gpio_config(KEY_LEFT, INPUT, PULL_HIGH);
    gpio_config(KEY_RIGHT, INPUT, PULL_HIGH);
    gpio_config(KEY_MIDDLE, INPUT, PULL_HIGH);
    gpio_config(KEY_PAIR, INPUT, PULL_HIGH);

    gpio_config(WHEEL_A,INPUT,PULL_HIGH/*!!!!!!!PULL_NONE*/); // no pukll high & no pull low
    gpio_config(WHEEL_B,INPUT,PULL_HIGH/*!!!!!!!PULL_NONE*/);// no pukll high & no pull low

    gpio_config(LED_24,OUTPUT,PULL_NONE);   // 2.4G LED (04)
    gpio_config(LED_BT,OUTPUT,PULL_NONE);   //BT1 LED  (05)
    gpio_set(LED_24,1);
    gpio_set(LED_BT,1);

    gpio_config(TEST_PIN1, OUTPUT, PULL_NONE);
    gpio_config(TEST_PIN2, OUTPUT, PULL_NONE);
    gpio_config(TEST_PIN3, OUTPUT, PULL_NONE);
    gpio_config(TEST_PIN4, OUTPUT, PULL_NONE);
    key_wakeup_config();
    app_enable_deep_sleep_wakeup();
}

#else
/* 按键初始化 */
void key_init(void)
{
    uint8_t i;

	//初始化LED
	gpio_config(BlueLedPort, OUTPUT, PULL_NONE);
	gpio_set(BlueLedPort, 0);

	//注册IO回调
	gpio_cb_register(app_gpio_int_cb);

    for (i = 0; i < KEYBOARD_MAX_ROW_SIZE; i++)
    {
		gpio_config(gpio_buff_r[i], OUTPUT, PULL_NONE);
		gpio_set(gpio_buff_r[i], 0);
    }
    for (i = 0; i < KEYBOARD_MAX_COL_SIZE; i++)
    {
		gpio_config(gpio_buff_c[i], INPUT, PULL_HIGH);
    }

	for(i=0; i<KEYBOARD_MAX_COL_SIZE; i++)
    {
    	addPMU_Reg0x3 |= 1<<(8*(gpio_buff_c[i]>>4)+(gpio_buff_c[i]&0x0f));//允许唤醒
		addAON_GPIO_Reg0x33 |= 1<<(8*(gpio_buff_c[i]>>4)+(gpio_buff_c[i]&0x0f));//允许产生中断

		for (i = 0; i < KEYBOARD_MAX_COL_SIZE; i++)
        {
    		if((8*(gpio_buff_c[i]>>4)+(gpio_buff_c[i]&0x0f))>=16)
                addAON_GPIO_Reg0x31 |= 3<<(((8*(gpio_buff_c[i]>>4)+(gpio_buff_c[i]&0x0f))-16)*2);//下降沿触发中断
            else
                addAON_GPIO_Reg0x30 |= 3<<( (8*(gpio_buff_c[i]>>4)+(gpio_buff_c[i]&0x0f))*2 );//下降沿触发中断

        }

    	addAON_GPIO_Reg0x35 |= 1<<(8*(gpio_buff_c[i]>>4)+(gpio_buff_c[i]&0x0f));//中断状态清0

    }
	addPMU_Reg0x4 |= 1<<8;//允许timer唤醒
	uart_printf("reg33=%x\r\n",addAON_GPIO_Reg0x33);
	uart_printf("reg31=%x\r\n",addAON_GPIO_Reg0x31);
	uart_printf("reg35=%x\r\n",addAON_GPIO_Reg0x35);
	uart_printf("reg03=%x\r\n",addPMU_Reg0x3);
	uart_printf("reg04=%x\r\n",addPMU_Reg0x4);
	setf_SYS_Reg0x10_int_aon_gpio_en;

	//This flag is setted to allow system into sleep mode when power on.
	app_key_state = ALL_KEY_FREE_DELAY;

	uart_printf("%s,(%d) \r\n",__func__,__LINE__);
}
#endif
#ifdef __MOUSE__

APP_MOUSE_T mouse_val;
extern uint32_t RF_flag;
extern APP_VAL_T   app_val;
extern void ble_addr_add1(void);
extern uint8_t rf_mode;// 0:2.4,1:BLE

void app_check_pair_and_mode_change(void)
{
    static uint8_t key_press_timer_cnt = 0;

    if(0==gpio_get_input(KEY_PAIR))
    {
        if(key_press_timer_cnt<0xff)
            key_press_timer_cnt++;
        if(key_press_timer_cnt==KEY_PRESS_LONG_TIME)///长按2s进入配对
        {
            uart_printf("long_press\r\n");
            app_clear_bond_flag = 0x01;
        }
     //   app_sys_status_check(0);
    }
    else
    {
        if(key_press_timer_cnt>KEY_PRESS_CANCEL && key_press_timer_cnt<KEY_PRESS_SHORT_TIME)///短按时间在1S内的切换模式
        {
            uart_printf("short_press\r\n");

       //     app_set_bt_idle();  // 在这里加蓝牙断线程序 //  !!!!!!!!!!!!!aileen
       //  !!!!!!!!!!!!!aileen
            mouse_val.pair_key=PAIR_KEY_MODE_CHANGE;
            if(ke_state_get(TASK_APP) == APPM_CONNECTED)
    		{
    			appm_disconnect();
    		}

        }
        else if(mouse_val.pair_key==PAIR_KEY_24_TO_BT)
        {
            mouse_val.pair_key=PAIR_KEY_MODE_CHANGE;
        }
        key_press_timer_cnt=0;

    }

/*   if((app_bt.bt_status==APP_BT_IDLE) && (mouse_val.pair_key==PAIR_KEY_PAIR))
    {
        mouse_val.pair_key=PAIR_KEY_IDLE;
		system_data.sensor_val.bDisplayBTMode = 0x0;
        app_enter_pair();  //在这里加配对程序  //  !!!!!!!!!!!!!aileen
  //      app_led_show(1,0,0,1);

    }*/
    if(app_clear_bond_flag ) //power key to clear bond info
	{
	    if(rf_mode == RF_24_MODE)
        {
            mouse_val.pair_key=PAIR_KEY_MODE_CHANGE;
            key_press_timer_cnt=0;
        }
        else
        {
		uart_printf("User clear adv mode\r\n");
		app_clear_bond_flag = 0;
        sys_flag |= FLAG_KEY_PAIRED;
		if(ke_state_get(TASK_APP) == APPM_CONNECTED)
		{
			appm_disconnect();
		}
        else
		{
		    uart_printf("adv st=%xr\n",app_env.adv_state);
          //  if((sys_flag & FLAG_KEY_PAIRED)&&(sys_flag & FLAG_PAIR_RW_INIT_EN))
            {
                sys_flag &= ~FLAG_PAIR_RW_INIT_EN;
                sys_flag &= ~FLAG_PEER_PUBLIC_ADDR;
             //   sys_flag &= ~FLAG_KEY_PAIRED;
                ble_addr_add1();
                appm_init();
                ke_timer_set(APP_PERIOD_TIMER,TASK_APP,APP_KEYSCAN_DURATION);
                app_env.adv_state = APP_ADV_STATE_IDLE;
                appm_create_advertising();
            //    return;
           //     rwble_init(1);
            }
		/*	if(app_env.adv_state == APP_ADV_STATE_CREATED)
			{
			    appm_delete_advertising();
			}else
			{
				appm_adv_fsm_next();
				restart_adv_after_stop = 1;
			}*/
    		}
		}

	}

    if( mouse_val.pair_key==PAIR_KEY_MODE_CHANGE)
    {
        if((ke_state_get(TASK_APP) == APPM_READY)||(rf_mode == RF_24_MODE))
    {
        uart_printf("change 24\r\n");
        mouse_val.pair_key = PAIR_KEY_IDLE;
        mouse_val.pair_key=PAIR_KEY_IDLE;
		system_data.sensor_val.bDisplayBTMode = 0x0;
        appm_change_device_mode();   // 在这里加却换2.4的程序   //  !!!!!!!!!!!!!aileen
    //    app_led_show(0,0,0,1);
        }
    }
}
#define WHEEL_EN 0
void app_mouse_wheel_scan(void)
{
 #if WHEEL_EN  
	static uint8_t old_pinLevel = 0;
    static uint8_t wheel_tog = 0 ;
    uint8_t pinLevel = 0;

    if(gpio_get_input(WHEEL_B))
        pinLevel |= B_0100_0000;
    if(gpio_get_input(WHEEL_A))
        pinLevel |= B_1000_0000;

    if(pinLevel == B_0100_0000)
    {
        if(old_pinLevel == B_1100_0000)
            wheel_tog = B_1000_0001 ;                 // 2
        else if(old_pinLevel == B_0000_0000)
            wheel_tog = B_1000_0010 ;                 // 4
    }
    else if(pinLevel == B_1000_0000)
    {
        if(old_pinLevel == B_1100_0000)
            wheel_tog = B_1000_0011;                // 3
        else if(old_pinLevel == B_0000_0000)
            wheel_tog = B_1000_0000 ;               // 1
    }
    else
    {
        if(wheel_tog & B_1000_0000)
        {
            wheel_tog &= B_0111_1111;

            if(((wheel_tog == 0x00) && (pinLevel==B_1100_0000))||((wheel_tog == 0x01) && (pinLevel==B_0000_0000)))
                system_data.wheel++;
            else if(((wheel_tog == 0x02) && (pinLevel==B_1100_0000))||((wheel_tog == 0x03) && (pinLevel==B_0000_0000)))
                system_data.wheel--;
        }
    }
    old_pinLevel = pinLevel;
#endif
}


void app_mouse_key_scan(void)
{
    static uint8_t old_key_shake = 0;
    static uint16_t key_count_shake = 0;

    //scan and save into key_current
    system_data.key_current = 0;

    if(!gpio_get_input(KEY_LEFT))
        system_data.key_current |= MOUSE_STANDARD_KEY_LEFT;
    if(!gpio_get_input(KEY_RIGHT))
        system_data.key_current |= MOUSE_STANDARD_KEY_RIGHT;
    if(!gpio_get_input(KEY_MIDDLE))
        system_data.key_current |= MOUSE_STANDARD_KEY_MIDDLE;

    if( (mouse_val.pair_key==PAIR_KEY_MODE_CHANGE) ||
         (mouse_val.pair_key==PAIR_KEY_PAIR) ||(!gpio_get_input(KEY_PAIR) ) )
    {
        system_data.key_current = 0;
     }

    //remove shake and save into key_valid
    system_data.key_valid = 0x00;
    if(old_key_shake != system_data.key_current)
    {
        RF_flag |= flag_key_released ;
        if(old_key_shake)
        {
            if(key_count_shake >= SHORT_CNT)
            {
                RF_flag &= ~flag_key_pressed ;
                RF_flag |= flag_key_short ;
                RF_flag &= ~flag_key_long ;
                system_data.key_valid = old_key_shake;
            }
        }
        key_count_shake = 0;
        old_key_shake = system_data.key_current;
    }
    else
    {
        if(system_data.key_current)
        {
            if(key_count_shake <= LONG_REPEAT_CNT)
                key_count_shake++;
            if(key_count_shake >= LONG_CNT)
            {
                RF_flag |= flag_key_long ;
                system_data.key_valid = old_key_shake;
            }
            if(key_count_shake == SHORT_CNT)
            {
                RF_flag |= flag_key_pressed ;
                RF_flag &= ~flag_key_released ;
                system_data.key_valid = old_key_shake;
            }
        }
    }
}

void app_mouse_key_check(void)
{
    if(RF_flag & flag_key_short)
    {
        RF_flag &= ~flag_key_short ;
        // 现在sensor的部分不加
        // if((system_data.key_valid & MOUSE_STANDARD_KEY_DPI) && !flag_dongle_lost)                                                //cpi switch
        //driver_sensor_dpi_switch();
    }
}

bool app_sensor_check(void)
{
#if(SENSOR_TEST)
    static int16_t deltaX,deltaY;

    static uint8_t dcount = 100;
    delay_us(350);
    dcount++;
    if(dcount>=100)
    {
        dcount = 0;

        if ((deltaX == 0) && (deltaY == 4))
        {
            deltaX=4;
            deltaY = 0;
        }
        else if ((deltaX == 4) && (deltaY == 0))
        {
            deltaX = 0;
            deltaY = -4;
        }
        else if ((deltaX == 0) && (deltaY== -4))
        {
            deltaX = -4;
            deltaY = 0;
        }
        else if((deltaX == -4) && (deltaY == 0))
        {
            deltaX = 0;
            deltaY = 4;
        }
        else
        {
            deltaX = 4;
            deltaY = 0;
        }
    }
    system_data.sensor_val.x = deltaX;
    system_data.sensor_val.y = deltaY;
    return 1;
#else
		uint8_t buf[3];
    uint16_t deltaX_l, deltaY_l, deltaX_h, deltaY_h;
    uint8_t count = 0;
		
    deltaX_h = 0;
    deltaY_h = 0;
    system_data.sensor_val.x = 0;
    system_data.sensor_val.y = 0;

    do
    {
        driver_sensor_paw3204_read_data(0x00, buf, 1);

//        bprintf("sensor= %x\r\n",buf[0]);
        count++;
        if ((buf[0] != 0x30)&&(buf[0] != 0x31))
        {
            resync1();
        }
        else
        {
            break;
        }
        if(count >= 17)
        {
            switch(system_data.sensor_val.type)
            {
                case SENSOR_3065:
                    app_sensor_paw3065_inital();
                    break;
                case SENSOR_3205:
                    app_sensor_paw3205_inital();
                    break;
                default:
                    break;
            }
            return FALSE;
        }
    } while(1);

    if(driver_sensor_check_up())
        system_data.sensor_val.sensor_up =1;
    else
        system_data.sensor_val.sensor_up =0;

    if(gpio_get_input(PAW3205_MOTSWK_PIN))
    {
        driver_sensor_paw3204_send_data(0x09 , 0x00);

        return TRUE;
    }

    driver_sensor_paw3204_read_data(0x02, buf , 3);
    deltaX_l = buf[1];
    deltaY_l =buf[2];

    if(deltaX_l & 0x0080)
    deltaX_h = 0xff00;
    if(deltaY_l & 0x0080)
    deltaY_h = 0xff00;
#if(USER1_DEFINE)


    system_data.sensor_val.x = deltaX_h | deltaX_l;
    system_data.sensor_val.y = deltaY_h | deltaY_l;
    system_data.sensor_val.x =  (~system_data.sensor_val.x)+1;
#else
    system_data.sensor_val.x = deltaY_h | deltaY_l;
    system_data.sensor_val.y = deltaX_h | deltaX_l;
#endif

    driver_sensor_paw3204_send_data(0x09 , 0x00);
    return TRUE;
#endif
}

#else
/* 按键扫描*/
void key_scan(void)
{
    unsigned char i,j,rw,cw;
    stan_key_len = 0;
    sys_flag &= ~FLAG_KEY_ACTIVE;
    for(i=0; i<8; i++)
    {
        stan_key[i] = 0;
    }
    for(i=0; i<KEYBOARD_MAX_COL_SIZE; i++)
    {
        cow[i] = 0;
    }
    for(i=0; i<KEYBOARD_MAX_ROW_SIZE; i++)
    {
        row[i] = 0;
    }
    for(i=0; i<KEYBOARD_MAX_ROW_SIZE; i++)
    {
        for(j=0; j<KEYBOARD_MAX_COL_SIZE; j++)
        {
            key_flag[i][j] <<= 1;
        }
    }
    for(rw = 0; rw < KEYBOARD_MAX_ROW_SIZE; rw++)
    {
        gpio_config(gpio_buff_r[rw], OUTPUT, PULL_NONE);
		gpio_set(gpio_buff_r[rw], 0);
        delay_us(50);
        for(cw = 0; cw < KEYBOARD_MAX_COL_SIZE; cw++)
        {
			if(0 == gpio_get_input(gpio_buff_c[cw]))
            {
                sys_flag |= FLAG_KEY_ACTIVE;
                key_flag[rw][cw] |=1;
                if((key_flag[rw][cw]&SCAN_COUT)==SCAN_COUT )
                {
                    real_key_value[cw] |= (1<<rw);
					if((rw == 4) && (cw == 1))
					{
						voice_key_press_status = 0x1;
					}else if((rw == 0)&& (cw == 0))
					{
						if(++power_key_delay > 120)
						{
							power_key_delay = 0;
							app_clear_bond_flag = 0x01;
						}
					}
                }
            }
            else
            {
            	if( (key_flag[rw][cw]&SCAN_COUT) == 0x00)
            	{
            		real_key_value[cw] &= ~(1<<rw);
	                if((rw == 4) && (cw == 1))
					{
						voice_key_press_status = 0x0;
					}else if((rw == 0)&&(cw == 0))
					{
						power_key_delay = 0;
						app_clear_bond_flag = 0;
					}
				}
            }
            if( real_key_value[cw]&(1<<rw))
            {
                stan_key[stan_key_len]=stand_key_map[rw][cw];
                row[rw]++;
                cow[cw]++;
                if(stan_key_len<8)
                {
                    stan_key_len++;
                }
            }
        }
        gpio_set(gpio_buff_r[rw],  1);
		gpio_config(gpio_buff_r[rw], FLOAT, PULL_NONE);


    }
}

void key_judge_error(void)
{
    uint8_t  i;
    key_status &= ~KEY_STATUS_CHANGE;
    if(stan_key_len != old_key_len) //按键长度变化
    {
        key_status  |= KEY_STATUS_CHANGE;
    }
    else
    {
        for(i = 0; i < stan_key_len; i++)  //按键值不一样
        {
            if(old_key[i] != stan_key[i])
            {
                key_status  |= KEY_STATUS_CHANGE;
                break;
            }
        }
    }
    if(key_status&KEY_STATUS_CHANGE)
    {
        key_status &= ~KEY_STATUS_ERROR;
        key_err_time=0;
        old_key_len = stan_key_len;
        for(i = 0; i < stan_key_len; i++)
        {
            old_key[i] = stan_key[i];
        }
    }
    if((!(key_status & KEY_STATUS_CHANGE)) && stan_key_len) //如果相同按键按下
    {
        key_err_time++;
        if(key_err_time >= KEY_ERROR_TIMEOUT)
        {
            key_status |= KEY_STATUS_ERROR;
        }
    }
}


void key_ghost_scan(void)
{
    uint8_t i,r;
    key_status &= ~KEY_STATUS_GHOST ;
    if(stan_key_len > 2)
    {
        for(r = 0; r<KEYBOARD_MAX_COL_SIZE; r++)
        {
        	//如果当前列存在两个以上按键按下
            if(cow[r] >= 2)
            {
                for(i = 0; i<KEYBOARD_MAX_ROW_SIZE; i++)
                {
                	//判断行中当前列是否存在按键按下
                    if(real_key_value[i]&(1<<r))
                    {
                    	//如果在行中存在两个以上案件按下
                        if(row[i] >= 2)
                        {
                            key_status |= KEY_STATUS_GHOST ;;
                            return;
                        }
                    }
                }
            }
        }
    }
}

void key_data_analysis(void)
{
    uint8_t i = 0,j = 2;
    uint8_t numlock_sta;
    key_status &= ~KEY_STATUS_FN;
    for(i = 0; i < stan_key_len; i++)  //FN 键检测
    {
        if(KEY_FN == stan_key[i])
        {
            key_status |= KEY_STATUS_FN;
        }
    }
    //其他键检测
    for(i = 0; i < stan_key_len; i++)
    {
        m_key = 0xff;
        s_key = 0xff;
        c_key = 0xff;
        p_key = 0xff;
        key_null = 0xff;
        switch(stan_key[i])
        {
            //sepcal key
        case KEY_POWER: //POWER
            p_key = 0;
            break;
        case KEY_SLEEP: //SLEEP
            p_key = 1;
            break;
        case KEY_WAKE_UP: //WAKE UP
            p_key = 2;
            break;
        case KEY_VOLUME_SUB: //volume-
            m_key = 9;
            break;
        case KEY_PLAY_PAUSE: //play/pause
            m_key = 11;
            break;
        case KEY_VOLUME_ADD: //volume+
            m_key = 10;
            break;
        case KEY_NEXT_TRACK: //next track
            m_key = 14;
            break;
        case KEY_PREV_TRACK: //prev track
            m_key = 13;
            break;
        case KEY_MUTE: //mute
            m_key = 8;
            break;
        case KEY_FN: //FN
            break;
	   case KEY_H7:  //H7
	   		m_key = 31;
			break;
	   case KEY_MAIL:  //mail
	   		m_key = 7;
			break;
	       case KEY_H8: //H8
		   	m_key = 32;
			break;
	   case KEY_H2: //H2
	   		m_key = 26;
			break;
	   case KEY_WWW_FAVORITE: //www favorite
	   		m_key = 5;
			break;
	       case KEY_H9:  //H9
		   	m_key = 33;
			break;
	   //case KEY_PAIR: //bind
	   //	break;
	   case KEY_WWW_FORWARD: //www forward
	   		m_key = 1;
		break;
	       case KEY_H10: //H10
		   	m_key = 34;
			break;
	   case KEY_H1: //H1
	   		m_key = 25;
		break;
	       case KEY_WWW_STOP: //www stop
		   	m_key = 2;
			break;
	   case KEY_MY_COMPUTER: //my computer
	   		m_key = 16;
		break;
	   case KEY_H11: //H11
		   	m_key = 35;
			break;
	   case KEY_H3: //H3
	   		m_key = 27;
			break;
	    case KEY_WWW_BACK: //www back
		   	m_key = 0;
			break;
	    case KEY_STOP:  //stop
		   	m_key = 12;
			break;
	    case KEY_H12: //H12
		   	m_key = 36;
			break;
	    case KEY_WWW_REFRESH: //www refresh
		   	m_key = 3;
			break;
	    case KEY_CALCULATOR://calculator
		   	m_key = 17;
			break;
	    case KEY_H13: //H13
		   	m_key = 37;
			break;
	    case KEY_H4: //H4
		   	m_key = 28;
			break;
	    case KEY_WEB_HOME: //web home
		   	m_key = 6;
			break;
	    case KEY_H14: //H14
		   	m_key = 38;
			break;
	    case KEY_H5:  //H5
	   		m_key = 29;
			break;
	       case KEY_H6: //H6
		   	m_key = 30;
			break;
	       case KEY_MEDIA: //media
		   	m_key = 15;
			break;
	    case KEY_WWW_SEARCH: //www search
	   		m_key = 4;
			break;
	    case KEY_BACKLIGHT:  //BACKLIGHT
		   	break;
        // ctrl key
        case KEY_LCTRL :
        case KEY_LALT  :
        case KEY_LSHFIT:
        case KEY_LWIN  :
        case KEY_RCTRL :
        case KEY_RALT  :
        case KEY_RSHIFT:
        case KEY_RWIN  :
            c_key = (1<<(stan_key[i]-0XE0));
            break;
        case END_NULL  :
            key_null = 0x00;
            break;
        default :
            if(key_status & KEY_STATUS_FN)     //fn 键按下
            {
                switch(stan_key[i])
                {
                case KEY_INS:
                    s_key = KEY_INS;
                    break;
                case KEY_UP_ARROW:
                    s_key = KEY_UP_ARROW;
                    break;
                case KEY_DOWN_ARROW:
                    s_key = KEY_DOWN_ARROW;
                    break;
                case KEY_LEFT_ARROW:
                    s_key = KEY_LEFT_ARROW;
                    break;
                case KEY_RIGHT_ARROW:
                    s_key = KEY_RIGHT_ARROW;
                    break;
                default:
                    if(1)//system.keyboard_config.fn_num)  //带FN小键盘功能
                    {
                        numlock_sta=key_status&KEY_STATUS_NUMLOCK;
                        switch(stan_key[i])
                        {
                        case KEY_7 :
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_7;
                            break;
                        case KEY_8 :
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_8;
                            break;
                        case KEY_9 :
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_9;
                            break;
                        case KEY_0 :
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_DIV;
                            break;
                        case KEY_U :
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_4;
                            break;
                        case KEY_I :
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_5;
                            break;
                        case KEY_O :
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_6;
                            break;
                        case KEY_P :
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_MUL;
                            break;
                        case KEY_J :
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_1;
                            break;
                        case KEY_K :
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_2;
                            break;
                        case KEY_L :
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_3;
                            break;
                        case KEY_SEMICOLON:
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_SUB;
                            break;
                        case KEY_M :
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_0;
                            break;
                        case KEY_DOT:
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_DOT;
                            break;
                        case KEY_QUESTION :
                            s_key = numlock_sta ? stan_key[i] : KEY_PAD_ADD;
                            break;
                        default:
                            s_key = stan_key[i];
                            break;
                        }
                    } //不带FN小键盘功能
                    else
                    {
                        s_key = stan_key[i];
                    }
                    break;
                }
            }
            else    // fn 键没按下
            {
                if(1)//system.keyboard_config.fn_num)  //带FN小键盘功能
                {
                    numlock_sta=key_status&KEY_STATUS_NUMLOCK;
                    switch(stan_key[i])
                    {
                    //case KEY_F1 : m_key = f1_f12[0]; break;
                    //case KEY_F2 : m_key = f1_f12[1]; break;
                    case KEY_F3 :
                        m_key = f1_f12[2];
                        break;
                    case KEY_F4 :
                        m_key = f1_f12[3];
                        break;
                    //case KEY_F5 :         //alen
                    //    m_key = f1_f12[4];
                    //    break;
                    //case KEY_F6 : m_key = f1_f12[6]; break;
                    case KEY_F7 :
                        m_key = f1_f12[8];
                        break;
                    case KEY_F8 :
                        m_key = f1_f12[5];
                        break;
                    case KEY_F9 :
                        m_key = f1_f12[7];
                        break;
                    case KEY_F10 :
                        m_key = f1_f12[11];
                        break;
                    case KEY_F11 :
                        m_key = f1_f12[9];
                        break;
                    case KEY_F12 :
                        m_key = f1_f12[10];
                        break;
                    //case KEY_ESC :               //alen
                    //    m_key = f1_f12[12];
                    //    break;
                    case KEY_DEL :
                        m_key = f1_f12[13];
                        break;
                    case KEY_7 :
                        s_key = numlock_sta ? KEY_PAD_7: stan_key[i];
                        break;
                    case KEY_8 :
                        s_key = numlock_sta ? KEY_PAD_8: stan_key[i];
                        break;
                    case KEY_9 :
                        s_key = numlock_sta ? KEY_PAD_9: stan_key[i];
                        break;
                    case KEY_0 :
                        s_key = numlock_sta ? KEY_PAD_DIV: stan_key[i];
                        break;
                    case KEY_U :
                        s_key = numlock_sta ? KEY_PAD_4: stan_key[i];
                        break;
                    case KEY_I :
                        s_key = numlock_sta ? KEY_PAD_5: stan_key[i];
                        break;
                    case KEY_O :
                        s_key = numlock_sta ? KEY_PAD_6: stan_key[i];
                        break;
                    case KEY_P :
                        s_key = numlock_sta ? KEY_PAD_MUL: stan_key[i];
                        break;
                    case KEY_J :
                        s_key = numlock_sta ? KEY_PAD_1: stan_key[i];
                        break;
                    case KEY_K :
                        s_key = numlock_sta ? KEY_PAD_2: stan_key[i];
                        break;
                    case KEY_L :
                        s_key = numlock_sta ? KEY_PAD_3: stan_key[i];
                        break;
                    case KEY_SEMICOLON:
                        s_key = numlock_sta ? KEY_PAD_SUB: stan_key[i];
                        break;
                    case KEY_M :
                        s_key = numlock_sta ? KEY_PAD_0: stan_key[i];
                        break;
                    case KEY_DOT:
                        s_key = numlock_sta ? KEY_PAD_DOT: stan_key[i];
                        break;
                    case KEY_QUESTION:
                        s_key = numlock_sta ? KEY_PAD_ADD: stan_key[i];
                        break;
                    default:
                        s_key = stan_key[i];
                        break;
                    }
                } //不带FN小键盘功能
                else
                {
                    s_key = stan_key[i];
                }
            }
            break;
        }
        if(m_key != 0xff) //多媒体
        {
            sys_media_key[0] = media_key[m_key][0];
            sys_media_key[1] = media_key[m_key][1];
            data_upload_status |= MEDIA_KEY_UPLOAD;
            data_upload_status |= MEDIA_KEY_SEND;
        }
        if(p_key != 0xff) //电源控制
        {
            sys_power_key[0] = power_key[p_key];
            data_upload_status |= POWER_KEY_UPLOAD;
            data_upload_status |= POWER_KEY_SEND;
        }
        if(s_key != 0xff) //普通按键
        {
            if(j < 8)
            {
                sys_standard_key[j] = s_key;
                j++;
            }
            data_upload_status |= STANDARD_KEY_UPLOAD;
            data_upload_status |= STANDARD_KEY_SEND;
        }
        if(c_key != 0xff)  //控制按键
        {
            sys_standard_key[0] |= c_key;
            data_upload_status |= STANDARD_KEY_UPLOAD;
            data_upload_status |= STANDARD_KEY_SEND;
        }
    }
    if(stan_key_len == 0x00)
    {
        if(data_upload_status & STANDARD_KEY_UPLOAD)  //普通按键释放
        {
            memset(sys_standard_key,0,8);
            data_upload_status &= ~STANDARD_KEY_UPLOAD;
            data_upload_status |= STANDARD_KEY_SEND;
        }
        if(data_upload_status & MEDIA_KEY_UPLOAD)  //多媒体按键释放
        {
            data_upload_status &= ~MEDIA_KEY_UPLOAD;
            data_upload_status |= MEDIA_KEY_SEND;
            sys_media_key[0] = 0;
            sys_media_key[1] = 0;
            sys_media_key[2] = 0;
            sys_media_key[3] = 0;
        }
        if(data_upload_status & POWER_KEY_UPLOAD)  //电源控制按键释放
        {
            data_upload_status &= ~POWER_KEY_UPLOAD;
            data_upload_status |= POWER_KEY_SEND;
            sys_power_key[0] = 0x00;
        }
    }
    if((!(data_upload_status & STANDARD_KEY_SEND)) && (data_upload_status & STANDARD_KEY_UPLOAD))  //普通按键释放
    {
        memset(sys_standard_key,0,8);
        data_upload_status &= ~STANDARD_KEY_UPLOAD;
        data_upload_status |= STANDARD_KEY_SEND;
    }
    if((!(data_upload_status & MEDIA_KEY_SEND)) && (data_upload_status & MEDIA_KEY_UPLOAD))  //多媒体按键释放
    {
        data_upload_status &= ~MEDIA_KEY_UPLOAD;
        data_upload_status |= MEDIA_KEY_SEND;
        sys_media_key[0] = 0;
        sys_media_key[1] = 0;
        sys_media_key[2] = 0;
        sys_media_key[3] = 0;
    }
    if((!(data_upload_status & POWER_KEY_SEND)) && (data_upload_status & POWER_KEY_UPLOAD))  //电源控制按键释放
    {
        data_upload_status &= ~POWER_KEY_UPLOAD;
        data_upload_status |= POWER_KEY_SEND;
        sys_power_key[0] = 0x00;
    }
}
unsigned char key_press_detect(void)
{
	static uint8_t keypress=0;
	static uint32_t keypresstime=0;
	uint8_t ret=0;
	extern uint8_t  rmac_find;
	extern uint8_t  lmac_find;
#define GPIO_KEY 0x32

	if(keypress == 0)
	{
		if(gpio_get_input(GPIO_KEY)==0)
		{
			uart_printf("key press1\r\n");
			keypress=1;
			keypresstime=0;
		}
	}
    else
	{
        if(gpio_get_input(GPIO_KEY)==0)
        {
            keypresstime++;
            //uart_printf("key press2\r\n");
        }
        else
        {
            if((keypresstime > 2))
            {
                keypresstime = 0;
                keypress=0;
                ret = 1; //short press
                uart_printf("key press3\r\n");
            }
        }
	}
	return ret;
}
uint8_t xyz_axis_process(uint8_t joystick_xyz)
{
    if(joystick_xyz>0x78&& joystick_xyz<0x88)
    {
        joystick_xyz=0x80;
    }
    else if(joystick_xyz<0x10)
    {
        joystick_xyz=0;
    }
    else if(joystick_xyz<=0x78)
    {
        joystick_xyz=(0x80*(joystick_xyz-0x10))/(float)0x68;
    }
    else if(joystick_xyz>=0xf0)
    {
        joystick_xyz=0xff;
    }
    else
    {
        joystick_xyz=0xff-(0x80*(0xf0-joystick_xyz))/(float)0x68;
    }
    return joystick_xyz;
}
#endif
void key_state_reset(void)
{
	tx_buff_count = 0;
	tx_buff_tail = 0;
	tx_buff_head = 0;
}


void key_process(void)
{
    static uint8_t temp_cnt=0;

#ifdef __MOUSE__
    app_mouse_key_scan();
     if(!gpio_get_input(KEY_LEFT))
        {
	//uart_printf("sensor\r\n");
        app_sensor_check();
        }
    else
    {
       system_data.sensor_val.x=0;
       system_data.sensor_val.y=0;
    }
    if(app_val.read_start_time<0x10)
    {
        app_val.read_start_time++;
        if(app_val.read_start_time<0x0B)///连上后前8次的数据丢弃
        {
            app_val.write_index=0;
            app_val.data_cnt=0;
            return;
        }
    }

    sys_flag &= ~FLAG_KEY_ACTIVE;
    #if MOUSE_SWING
    if( (system_data.key_current==0) && (system_data.sensor_val.x==0)
       &&(system_data.sensor_val.y==0) && (system_data.wheel==0) && (system_data.swing==0))
    #else
    if( (system_data.key_current==0) && (system_data.sensor_val.x==0)
       &&(system_data.sensor_val.y==0) && (system_data.wheel==0) )
    #endif
    {
        if(temp_cnt<0xff)
            temp_cnt++;
        if(temp_cnt>3)
            return;
    }
    else
        temp_cnt=0;
    sys_flag |= FLAG_KEY_ACTIVE;

    if(tx_buff_count>=SEND_BUFFER_CNT)
        return;
    if(1)//((sys_flag & FLAG_CLASS_PROTOCOL)||(APP_BLE_CONNECTED ==  app_get_bt_status()))
    {
        bt_tx_buff[tx_buff_head][0] = system_data.key_current;
        bt_tx_buff[tx_buff_head][1] = system_data.sensor_val.x;
        bt_tx_buff[tx_buff_head][2] = ((system_data.sensor_val.y<<4)&0xf0)|((system_data.sensor_val.x>>8)&0x0f);
        bt_tx_buff[tx_buff_head][3] = system_data.sensor_val.y>>4;
        bt_tx_buff[tx_buff_head][4] = system_data.wheel;
        #if MOUSE_SWING
        bt_tx_buff[tx_buff_head][5] = system_data.swing;
        tx_buff_len[tx_buff_head]=6;
        #else
        tx_buff_len[tx_buff_head]=5;
        #endif
    }
    else
    {

        bt_tx_buff[tx_buff_head][0] = system_data.key_current;
        bt_tx_buff[tx_buff_head][1] = system_data.sensor_val.x;
        bt_tx_buff[tx_buff_head][2] = system_data.sensor_val.y>>4;
        bt_tx_buff[tx_buff_head][3] = system_data.wheel;
        tx_buff_len[tx_buff_head]=4;

    }

    tx_buff_head++;
    tx_buff_count++;
    tx_buff_head=tx_buff_head%SEND_BUFFER_CNT;
    system_data.wheel = 0;
    #if MOUSE_SWING
    system_data.swing = 0x0;
    #endif

#else
    key_scan();
    key_judge_error();
    key_ghost_scan();

    if( (key_status&KEY_STATUS_CHANGE)&&(!(key_status&(KEY_STATUS_ERROR|KEY_STATUS_GHOST)))
            &&(tx_buff_count<SEND_BUFFER_CNT))
    {
        key_data_analysis();
        if(data_upload_status & STANDARD_KEY_SEND)
        {
            memcpy(&(bt_tx_buff[tx_buff_head][0]),sys_standard_key,8);
            memset(sys_standard_key,0,8);
            tx_buff_len[tx_buff_head]=8;
            tx_buff_head++;
            tx_buff_count++;
            tx_buff_head=tx_buff_head%SEND_BUFFER_CNT;
            data_upload_status &= ~STANDARD_KEY_SEND;
        }
        if(data_upload_status & MEDIA_KEY_SEND)
        {
            bt_tx_buff[tx_buff_head][0]=sys_media_key[0];
            bt_tx_buff[tx_buff_head][1]=sys_media_key[1];
            tx_buff_len[tx_buff_head]=2;
            tx_buff_head++;
            tx_buff_count++;
            sys_media_key[0]=0;
            sys_media_key[1]=0;
            sys_media_key[2]=0;
            sys_media_key[3]=0;
            tx_buff_head=tx_buff_head%SEND_BUFFER_CNT;
            data_upload_status &= ~MEDIA_KEY_SEND;
        }
        if(data_upload_status & POWER_KEY_SEND)
        {
            bt_tx_buff[tx_buff_head][0]=sys_power_key[0];
            sys_power_key[0]=0;
            tx_buff_len[tx_buff_head]=1;
            tx_buff_head++;
            tx_buff_count++;
            tx_buff_head=tx_buff_head%SEND_BUFFER_CNT;
            data_upload_status &= ~POWER_KEY_SEND;
        }
    }
#endif
}

void key_wakeup_set(void)
{

#ifdef __MOUSE__

    addAON_GPIO_Reg0x33 = 0;
    addPMU_Reg0x3=0;
    addAON_GPIO_Reg0x35 = 0xffffffff ;
	clrf_SYS_Reg0x10_int_aon_gpio_en;

#else

    uint8_t i;
    for(i=0; i<KEYBOARD_MAX_ROW_SIZE; i++)
    {
        gpio_set(gpio_buff_r[i], 1);
		gpio_config(gpio_buff_r[i], SC_FUN, PULL_NONE);
    }
	addAON_GPIO_Reg0x35 = 0xffffffff;
    addPMU_Reg0x3=0;
	clrf_SYS_Reg0x10_int_aon_gpio_en;
#endif
}
void gpio_sleep(void)
{

    gpio_set_int_mode(KEY_LEFT,3);
    gpio_set_int_mode(KEY_RIGHT,3);
    gpio_set_int_mode(KEY_MIDDLE,3);
    gpio_set_int_mode(KEY_PAIR,3);
    gpio_set_int_mode(SENSOR_MOTSWK_PIN,3);

    if(gpio_get_input(WHEEL_B))
        gpio_set_int_mode(WHEEL_B,3);
    else
        gpio_set_int_mode(WHEEL_B,2);
    if(gpio_get_input(WHEEL_A))
        gpio_set_int_mode(WHEEL_A,3);
    else
        gpio_set_int_mode(WHEEL_A,2);
    #if 0
    REG_APB5_GPIO_WUATOD_TYPE = ((1<<( (KEY_LEFT>>4)*8)+(KEY_LEFT&0x0f)))
                                |((1<<((KEY_RIGHT>>4)*8)+(KEY_RIGHT&0x0f)))
                                |((1<<( (KEY_MIDDLE>>4)*8)+(KEY_MIDDLE&0x0f)))
                                |((1<<( (KEY_PAIR>>4)*8)+(KEY_PAIR&0x0f)))
                                |((1<<( (WHEEL_B>>4)*8)+(WHEEL_B&0x0f)))
                                |((1<<( (WHEEL_A>>4)*8)+(WHEEL_A&0x0f)))
                                |((1<<( (PAW3205_MOTSWK_PIN>>4)*8)+(PAW3205_MOTSWK_PIN&0x0f)));
    #endif
    REG_GPIO_WUATOD_STATUS = 0xffffffff ;

    addPMU_Reg0x3=addAON_GPIO_Reg0x33;
    SYS_REG0X10_INT_FLAG |=(0x01 << POS_SYS_REG0X10_INT_EN_GPIO);
    SYS_REG0X10_INT_EN |= (0x01 << POS_SYS_REG0X10_INT_EN_GPIO);

}


/*配置按键中断及休眠*/
void key_wakeup_config(void)
{
#ifdef __MOUSE__
    uint64_t u32WakeType = (3<<((((KEY_LEFT>>4)*8)+(KEY_LEFT&0x0f))<<1))
                            |(3<<((((KEY_RIGHT>>4)*8)+(KEY_RIGHT&0x0f))<<1))
                            |(3<<((((KEY_MIDDLE>>4)*8)+(KEY_MIDDLE&0x0f))<<1))
                            |(3<<((((KEY_PAIR>>4)*8)+(KEY_PAIR&0x0f))<<1))
                            |(3<<((((SENSOR_MOTSWK_PIN>>4)*8)+(SENSOR_MOTSWK_PIN&0x0f))<<1));



    if(gpio_get_input(WHEEL_B))
        u32WakeType |= (3<<((((WHEEL_B>>4)*8)+(WHEEL_B&0x0f))<<1));
    else
        u32WakeType |= (2<<((((WHEEL_B>>4)*8)+(WHEEL_B&0x0f))<<1));
    if(gpio_get_input(WHEEL_A))
        u32WakeType |= (3<<((((WHEEL_A>>4)*8)+(WHEEL_A&0x0f))<<1));
    else
        u32WakeType |= (2<<((((WHEEL_A>>4)*8)+(WHEEL_A&0x0f))<<1));
    
    addAON_GPIO_Reg0x30 = u32WakeType&0xffffffff;
    addAON_GPIO_Reg0x31 = (u32WakeType>>32)&0xffffffff;
    addAON_GPIO_Reg0x33 = ((1<<( (KEY_LEFT>>4)*8)+(KEY_LEFT&0x0f)))
                                |((1<<((KEY_RIGHT>>4)*8)+(KEY_RIGHT&0x0f)))
                                |((1<<( (KEY_MIDDLE>>4)*8)+(KEY_MIDDLE&0x0f)))
                                |((1<<( (KEY_PAIR>>4)*8)+(KEY_PAIR&0x0f)))
                                |((1<<( (WHEEL_B>>4)*8)+(WHEEL_B&0x0f)))
                                |((1<<( (WHEEL_A>>4)*8)+(WHEEL_A&0x0f)))
                                |((1<<( (SENSOR_MOTSWK_PIN>>4)*8)+(SENSOR_MOTSWK_PIN&0x0f)));
    addPMU_Reg0x3=addAON_GPIO_Reg0x33;
    addAON_GPIO_Reg0x35 = 0xffffffff ;
	setf_SYS_Reg0x10_int_aon_gpio_en;
  //  uart_printf("IO_int=%x,%x,%x,%x\r\n",addPMU_Reg0x3,addAON_GPIO_Reg0x30,addAON_GPIO_Reg0x31,addAON_GPIO_Reg0x33,addSYS_Reg0x10);

#else


    uint8_t i;

    for(i=0; i<KEYBOARD_MAX_ROW_SIZE; i++)
    {
        gpio_config(gpio_buff_r[i],OUTPUT,PULL_NONE);
        gpio_set(gpio_buff_r[i],0);
    }
	for(i=0; i<KEYBOARD_MAX_COL_SIZE; i++)
    {
		gpio_config(gpio_buff_c[i], INPUT, PULL_HIGH);
    }

	//Clear period timer
	ke_timer_clear(APP_PERIOD_TIMER, TASK_APP);
	for(i=0; i<KEYBOARD_MAX_COL_SIZE; i++)
    {


    	addPMU_Reg0x3 |= 1<<(8*(gpio_buff_c[i]>>4)+(gpio_buff_c[i]&0x0f));//允许唤醒
		addAON_GPIO_Reg0x33 |= 1<<(8*(gpio_buff_c[i]>>4)+(gpio_buff_c[i]&0x0f));//允许产生中断
		addAON_GPIO_Reg0x31 |= 3<<16;//下降沿触发中断
		addAON_GPIO_Reg0x31 |= 3<<18;//下降沿触发中断
		addAON_GPIO_Reg0x31 |= 3<<20;//下降沿触发中断
		addAON_GPIO_Reg0x35 |= 1<<(8*(gpio_buff_c[i]>>4)+(gpio_buff_c[i]&0x0f));
    }

	setf_SYS_Reg0x10_int_aon_gpio_en;
#endif
}


#if (SYSTEM_SLEEP)
/*检测按键的状态，返回0表示语音按键按下，返回1表示普通按键或者没有按键按下*/
app_key_type key_status_check(void)
{

#ifdef __MOUSE__

    if((0==gpio_get_input(KEY_PAIR))||(sys_flag & FLAG_KEY_ACTIVE))
    {
        return (GENERAL_KEY_DOWN);
    }
    else
    {
        return (ALL_KEY_FREE);
    }
#else
    static uint8_t key_down_status=0;

		if((stan_key_len == 0)&&(sys_flag & FLAG_KEY_ACTIVE))
		{
		    if(key_down_status==1)
            {
			    key_down_status=0;
                uart_printf("key FREE\r\n");
            }

			return (ALL_KEY_FREE);
		}
		else
		{
            key_down_status=1;
            uart_printf("key DOWN\r\n");
			return (GENERAL_KEY_DOWN);

	}
#endif
}

#endif

extern  struct app_hid_env_tag app_hid_env;

/*发送按键键值*/
void hid_send_keycode( void )
{
#ifdef __MOUSE__
  /*  struct hogpd_enable_req * req = KE_MSG_ALLOC(HOGPD_ENABLE_REQ,
                                                    prf_get_task_from_id(TASK_ID_HOGPD),
                                                    TASK_APP,
                                                    hogpd_enable_req);
     app_env.conidx = KE_IDX_GET(src_id);*/


    if((tx_buff_count)&&(ke_state_get(TASK_APP) == APPM_CONNECTED)&& (app_hid_env.state  == APP_HID_READY))
    {

        app_hid_send_report(&bt_tx_buff[tx_buff_tail][0],tx_buff_len[tx_buff_tail]);

        tx_buff_tail++;
        tx_buff_tail %= SEND_BUFFER_CNT;
        tx_buff_count--;
    }

#else
    if((tx_buff_count)&&(ke_state_get(TASK_APP) == APPM_CONNECTED)&&(sys_flag &FLAG_CONNECT))
    {
		if(voice_key_press_status && (bt_tx_buff[tx_buff_tail][2] == KEY_VOICE)
									&& ke_state_get(TASK_APP)== APPM_CONNECTED)
		{
			old_voice_key_press_status = voice_key_press_status;
			uart_printf("voice key down\r\n");
		}
		else if(old_voice_key_press_status && (!voice_key_press_status))
		{
			old_voice_key_press_status = 0x0;
			voice_key_press_status = 0x0;

			uart_printf("voice key up\r\n");
		}
		else
		{
			for(uint8_t i=0; i<tx_buff_len[tx_buff_tail]; i++)
			{
				uart_printf("0x%x ", bt_tx_buff[tx_buff_tail][i]);
			}
			uart_printf("\r\n");

			if((tx_buff_len[tx_buff_tail] != 0x1) && (!voice_key_press_status)) //not power key
			{
				app_hid_send_report(&bt_tx_buff[tx_buff_tail][0],tx_buff_len[tx_buff_tail]);
			}
		}

        tx_buff_tail++;
        tx_buff_tail %= SEND_BUFFER_CNT;
        tx_buff_count--;
    }

	if(app_clear_bond_flag ) //power key to clear bond info
	{
		uart_printf("User clear adv mode\r\n");
		app_clear_bond_flag = 0;
		app_sec_remove_bond();

		if(ke_state_get(TASK_APP) == APPM_CONNECTED)
		{
			appm_disconnect();
		}else
		{
			if(app_env.adv_state == APP_ADV_STATE_CREATED)
			{
				appm_update_adv_state(true);
			}else
			{
				appm_adv_fsm_next();
				restart_adv_after_stop = 1;
			}
		}

	}
#endif
}

/*! \fn void driver_timer0_reset(void)
    \brief Reset timer0 for system basic tick.

    \param void
    \return void
*/
void driver_timer0_reset(void)
{
	#if	(!KEYBOARD)
	Timer0_Stop(1);				// must used.
	Timer0_1m5_Start(1,1500000); // 1.5ms
    system_data.time.tick_2ms = 0;
    RF_flag &= ~flag_tick_8ms_loop;
	#endif

}

void driver_timer1_reset(void)
{
	#if	(KEYBOARD)
	Timer1_Stop(1);				// must used.
	Delay_us(50); 				// must used. 10 err, 50 ok, 100 ok,150 ok, 1500=880us.
	eTimerDuty = cRC_TIMER_2ms;
	Timer1_ReStart(1, 2000); 	// 2ms
	system_data.time.tick_4ms = 0;
    RF_flag &= ~flag_tick_8ms_loop;
	#endif
}

/*! \fn void driver_delay_set_with_base_tick(TIMER *timer, UINT8 timeout)
    \brief Set a delay \a timeout*system_tick ms with \a timer.

    \param timer - the timer used for delay
    \param timeout - delay timeout*system_tick ms
    \return void
*/
void driver_delay_set_with_base_tick(TIMER *timer, uint32_t timeout)
{
//    ET0 = 0;
    timer->value_expired = system_data.time.tick_system + timeout;
//    ET0 = 1;
}

/*! \fn BOOL driver_delay_with_base_tick_expire_check(TIMER *timer)
    \brief Check the delay set by \a driver_delay_set_with_base_tick is whether expired.

    \param timer - the timer used for delay
    \return TRUE - expired, FALSE - otherwise
*/
uint8_t driver_delay_with_base_tick_expire_check(TIMER *timer)
{
    uint8_t flag_expired;

 //   ET0 = 0;
    flag_expired = system_data.time.tick_system >= timer->value_expired;
 //   ET0 = 1;

    return flag_expired;
}
/*
	ms*8ms
*/
void Wait_Xms(uint32_t ms)
{
	TIMER Delay;
	driver_delay_set_with_base_tick(&Delay, ms);
	while (!driver_delay_with_base_tick_expire_check(&Delay));
}



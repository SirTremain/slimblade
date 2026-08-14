#include "app.h"
#include "app_key.h"

//#include "driver_sensor.h"
#include "application_mode.h"
#include "wdt.h"
#include "adc.h"
#include "driver_timer.h"
#include "icu.h"
#include "gpio.h"

#include <string.h>
#define UART_PRINTF	uart_printf
int uart_printf(const char *fmt,...);

uint32_t RF_flag=0;
uint8_t status_idle_cnt=0 ;
uint8_t rf_lost_cnt = 0;
uint8_t lbd_sleep_onetime;

static uint8_t bLEDState;

uint32_t wSysFlagfn24;
uint32_t lbd_sleep_count;

TIMER BLED_Timer;

APP_VAL_T     app_val;

extern SYSTEM_STRUCT_DATA system_data;
extern uint8_t rf_fifo_data[MAX_PACKET_LEN];             //rf fifo
extern uint8_t sync_count;


/*! \fn void application_normal_mode_initial(void)
    \brief  Initialize the system before entering normal mode.
    \param void
    \return void
*/
void application_normal_mode_initial(void)
{
    uart_printf("ID=%x,%x,%x,%x,%x\r\n",P0_Address[0],P0_Address[1],P0_Address[2],P0_Address[3],P0_Address[4]);

	//wdt_enable(0x1000);		// 0x1000*250us=1s
    status_idle_cnt = 0;
    sync_count = 0;
    driver_rf_ouput_power_value_set(0x0a);

    RF_POWER_UP;
    RF_CMD_FLUSH_TX;
    RF_CMD_FLUSH_RX;
    SwitchToTxMode();

    memset(rf_fifo_data, 0, 10);
    application_mouse_channel_search();
    sync_count = 0x0;
    system_data.rf_connect = SYSTEM_SYNCHRONIZE;
	if(app_val.powered_bind)
		system_data.time.tick_rf_send_fail = cPWROnEnPageTimer+2;
	else
    	system_data.time.tick_rf_send_fail = SYSTEM_SEND_FAIL_TIME_MOUSE;
	RF_flag &= ~flag_system_powerdown;

    wSysFlagfn24 = 0x0;
    lbd_sleep_onetime = 0x0;
    lbd_sleep_count = 0x0;

  //  adc_init(ADC_CHANNEL,2);			// low bat detect.
}
/*! \fn void application_mouse_status_check(void)
    \brief Check and set the rf send status if there are some data needed
tobe sent to dongle.
    Mouse:
            If the key pressed, sensor moving and wheel rolling events happend
, mouse need send them to dongle.\n
            If the key pressed and release events happened, keyboard needsend
them to dongle.\n
            If battery detection of power up by adc module is over, mouseneed
send them to dongle.
    \param void
    \return void
*/
uint8_t wheel_old_cnt=0;
void application_mouse_status_check(void)
{
    RF_flag &= ~(flag_status_idle | flag_status_sleep) ;
	#if MOUSE_SWING
	if((!(RF_flag & flag_rf_last_state)) && (system_data.wheel != 0x0) && (system_data.swing != 0x0))
	#else
    if((!(RF_flag & flag_rf_last_state)) && (system_data.wheel != 0x0))
	#endif
    {
        wheel_old_cnt++;
        if(wheel_old_cnt > 100)
        {
            system_data.wheel = 0; // when dongle lost,wheel = 0
            #if MOUSE_SWING
            system_data.swing = 0x0;
			#endif
        }
		if(system_data.rf_connect == SYSTEM_END)
			system_data.rf_connect = 0x0;
    }
	#if MOUSE_SWING
	if((RF_flag & (flag_key_pressed | flag_key_released)) || \
		(system_data.wheel != 0x0) || (system_data.swing != 0x0) || (system_data.sensor_val.x != 0x0 ) || (system_data.sensor_val.y != 0x0))
	#else
    if((RF_flag & (flag_key_pressed | flag_key_released)) || \
		(system_data.wheel != 0x0) || (system_data.sensor_val.x != 0x0 ) || (system_data.sensor_val.y != 0x0))
	#endif
    {
        RF_flag &= ~flag_key_released;
        RF_flag |= flag_rf_send ;
        RF_flag |= flag_rf_send_end ;
		system_data.idle_time = 400;
		if(system_data.rf_connect == SYSTEM_END)
			system_data.rf_connect = 0x0;
    }
    else if((RF_flag & flag_rf_send_end) && (RF_flag & flag_rf_last_state))
    {
        wheel_old_cnt = 0;
        RF_flag |= flag_rf_send;
        RF_flag &= ~flag_rf_send_end ;
        system_data.rf_connect = SYSTEM_END;
		system_data.idle_time = 400;
    }
    else
    {
        if(system_data.time.tick_rf_send_fail)
        {
            system_data.time.tick_rf_send_fail--;
            if(system_data.time.tick_rf_send_fail == 0)
            {
                wheel_old_cnt = 0;
                RF_flag |= flag_status_idle ;
                status_idle_cnt =0;
                RF_flag |= flag_dongle_lost ;
            }
        }
        else
        {
        	if(system_data.idle_time)
        		system_data.idle_time--;
			if(system_data.idle_time == 0)
			{
//	            if(RF_flag & flag_rf_last_state)//||(!flag_rf_paged))
	            {
	                wheel_old_cnt = 0;
	                RF_flag |= flag_status_idle ;
	                status_idle_cnt =0;
	            }
			}
        }
    }
}
/*! \fn void application_mouse_rf_send_check(void)
    \brief The rf sending function that executes the real data sending.
    If it is first sending, it will call \a application_mouse_rf_send to
fillrf fifo data buffer and send them.\n
    If the last sending failed, it will call \
aapplication_mouse_rf_send_with_insistent_hop_in_8ms to search quickly or call
        \a application_mouse_rf_send_with_once_hop to search slowly.
    \param void
    \return void
*/
void application_mouse_rf_send_check(void)
{
    if(RF_flag & flag_rf_send )
    {
        RF_flag &= ~flag_rf_send;
		RF_flag &= ~flag_rf_hop_16ch;
		system_data.time.tick_rf_send_fail = SYSTEM_SEND_FAIL_TIME_MOUSE;
//		uart_printf("f=%x,sNO=%x\n",(RF_flag & flag_rf_last_state),sync_count);
        application_mouse_rf_send();

		#if	0
		if(system_data.rf_send_length && sync_count && (system_data.time.tick_rf_send_fail == 0x0))
		{
			// TX fail,
		}
		else
		{
			RF_flag &= ~flag_rf_send;
		}

		if(RF_flag & flag_rf_last_state)
		{
//			uart_printf("tok.\n");
//			uart_printf("ok:l=%x,cnt=%x,scnt=%x\n",system_data.rf_send_length,system_data.time.tick_rf_send_fail,sync_count);
		}
		else
		{
//			uart_printf("tER.\n");
//			uart_printf("er:fNO=%x,sNO=%x\n",system_data.time.tick_rf_send_fail,sync_count);
		}
		#endif
    }
    else if((!(RF_flag & flag_rf_last_state )) && system_data.rf_send_length && system_data.time.tick_rf_send_fail)
    {
    //	uart_printf("rtx=%x\n",system_data.time.tick_rf_send_fail);
        RF_CHIP_ENABLE;
        application_mouse_rf_send_with_insistent_hop_16ch();
        RF_CHIP_DISABLE;
		if(RF_flag & flag_rf_last_state)
		{
			sync_count = 0;
            system_data.rf_connect = 0x00;
			system_data.time.tick_rf_send_fail = 0x0;
		}
    }
    else if((RF_flag & flag_rf_need_clear_maxRT)&&(system_data.time.tick_rf_send_fail==0))
    {
    //	uart_printf("rtx fail\n");
        driver_rf_maxRT_clear();
        RF_flag &= ~flag_rf_need_clear_maxRT ;
        RF_flag &= ~flag_rf_hop_16ch ;
    }
    if(RF_flag & flag_rf_last_state)
    {
    //	uart_printf("tok\n");
#ifdef SENSOR_POWER_OFF
        if(RF_flag & flag_dongle_lost)//&&flag_rf_paged)//公共地址
        {
            RF_flag &= ~flag_dongle_lost;
            //   driver_sensor_power_up();
        }
#endif
    }

}
/*! \fn void application_mouse_sleep_check(void)
    \brief Check mouse  need to enter into sleep state. If the key ischanging
or last rf send fail, it will NOT.
    \param void
    \return void
*/
void application_mouse_sleep_check(void)
{
    if((RF_flag & flag_status_idle)/* && (!(RF_flag & flag_rf_last_state))*/)
    {

        RF_flag &= ~flag_status_idle;
        RF_flag |= flag_status_sleep;
		if(system_data.led.freq)
			RF_flag &= ~flag_status_sleep;

    }

	if((wSysFlagfn24 & flag_led_lbd) && (!lbd_sleep_onetime))
	{
		if(RF_flag & flag_status_sleep)
		{
			RF_flag &= ~flag_status_sleep;
			lbd_sleep_onetime = 1;
			lbd_sleep_count = 700;
		}
	}

	if(lbd_sleep_count)
	{
		RF_flag &= ~flag_status_sleep;
		lbd_sleep_count--;
	}


	if((RF_flag & flag_status_sleep) == 0x0)            //低电压LED处理,在鼠标动作时
    {
        if((wSysFlagfn24 & flag_led_lbd) && (!system_data.led.freq) && (!system_data.bled_flag))
        {
        	uart_printf("low bat\n");
           // if(driver_delay_with_base_tick_expire_check(&system_data.led.led_timer))
            {
                application_mouse_led_start(24, 2);		// 3
                driver_delay_set_with_base_tick(&BLED_Timer,500);
                system_data.bled_flag = 1;
            }
        }
    }


    //在低电提示时间内
	if(system_data.bled_flag)
	{
		if(driver_delay_with_base_tick_expire_check(&BLED_Timer))
	    {
			system_data.bled_flag = 0;
	    }
		RF_flag &= ~flag_status_sleep;
	}
}
/*! \fn void application_mouse_idle_oscxmhz(void)
    \brief The first level sleep of mouse, idle in osc8mhz.
    Mouse enter into idle state in osc8mhz clock with timer running, and itneeds the wake-up by timer expired or key/wheel/sensor events.\n
    RF module also powers on, so it can send rf data continously.
    \param void
    \return void
*/
void application_mouse_idle_oscxmhz(void)
{
//	uart_printf("fg=%xr\n",RF_flag);
    if((!(RF_flag & flag_tick_8ms_loop)) && (RF_flag & flag_rf_last_state) && (!(RF_flag & flag_status_idle)) && (!(RF_flag & flag_status_sleep)))
    {
        cpu_idle_sleep();
        //  WHEEL_SLEEP;
//        uart_printf("idle osc\n");
        //  WHEEL_WORKING;
    }
}
/*! \fn void application_mouse_idle_oscxmhz(void)
    \brief The first level sleep of mouse, idle in osc8mhz.
    Mouse enter into idle state in osc8mhz clock with timer running, and
itneeds the wake-up by timer expired or key/wheel/sensor events.\n
    RF module also powers on, so it can send rf data continously.
    \param void
    \return void
*/
void application_mouse_wake_up_from_32khz(void)
{
    //  WHEEL_WORKING;
//   driver_gpio_initial();
    system_data.time.tick_2ms = 0;
    //system_data.time.tick_system = 0;
    RF_POWER_UP;
    //flag_tick_8ms_loop = 1;
    system_data.rf_connect = SYSTEM_SYNCHRONIZE;
    system_data.time.tick_rf_send_fail = SYSTEM_SEND_FAIL_TIME_MOUSE;

	//wdt_enable(0x1000); 	// 0x1000*250us=1s
}
#if	0
/*! \fn void application_mouse_idle_rc32khz_with_2ms_timer(void)
    \brief The second level sleep of mouse, idle in rc32khz with 2ms timerrunning.
    Mouse enter into idle state in rc32khz clock with 2ms timer running, andit needs the wake-up by timer expired or key/wheel/sensor events.\nRF module powers off.
    \param void
    \return void
*/
void application_mouse_idle_rc32khz_with_2ms_timer(void)
{
    //  uint8 pin_timer=0;
    //  pin_timer=0;
    if(RF_flag & flag_status_idle)
    {
        RF_flag &= ~flag_status_sleep ;
        system_data.time.tick_rf_send_fail = SYSTEM_SEND_FAIL_TIME_MOUSE;
	#ifdef SENSOR_POWER_OFF
        if(RF_flag & flag_dongle_lost) //power off sensor
        {
            /*
            if(flag_sensor_state)
            {
                driver_sensor_power_down();
            }
            */
        }
	#endif
        RF_CHIP_DISABLE;			//避免滚轮丢码，不power down RF
        app_gpio_sleep();
        //    WHEEL_SLEEP;
        RF_flag &= ~flag_wake_up_by_timer ;
        system_data.time.tick_sleep_check = 0;
        system_data.wheel = 0x00;
        while(!(RF_flag & flag_status_sleep))
        {
//            memset(rf_fifo_data, 0, 10);
            cpu_idle_sleep();
			wdt_enable(0x1000); 	// 0x1000*250us=1s
			uart_printf("idle\n");
            if(RF_flag & flag_wake_up_by_timer)
            {
                //  driver_mouse_wheel_scan();
                if(system_data.wheel)
                    //wheel change
                {
                	uart_printf("w\n");
                    break;
                }
                if((!gpio_get_input(KEY_LEFT)) || (!gpio_get_input(KEY_RIGHT) )|| (!gpio_get_input(KEY_MIDDLE))|| (!gpio_get_input(PAW3205_MOTSWK_PIN)))//|| !key_row_forward || !key_row_backward || !key_row_dpi || !SENSOR_MOTION_PIN)
                {
                    break;
                }
                if(RF_flag & flag_tick_8ms_loop)
                {
                    RF_flag &= ~flag_tick_8ms_loop ;
                }
				#if	0
                if(!(RF_flag & flag_dongle_lost))
                {

                    //   driver_sensor_check();
                    if(system_data.sensor_val.x || system_data.sensor_val.y)
                    {
                    	uart_printf("x\n");
                        break;
                    }
                }
                else
                {
                	memset(rf_fifo_data, 0, 10);
                    driver_rf_data_send_noACK(5);//为了耗电
                    driver_rf_maxRT_clear();
                }
				#endif
                RF_flag &= ~flag_wake_up_by_timer ;
                app_gpio_sleep();
                system_data.time.tick_sleep_check++;
#ifdef SENSOR_TYPE_AN5030
                if(flag_sensor_an5030)
                {
                    if((system_data.time.tick_sleep_check >=SYSTEM_SLEEP_TIME_MOUSE*3)||(rf_lost_cnt>0x20))
                    {
                        status_sleep =  1;
                        break;
                    }
                }
                else
#endif
                    if(RF_flag & flag_dongle_lost)
                    {
                        status_idle_cnt++;
                        if(status_idle_cnt >= 0x20)
                        {
                            status_idle_cnt =0;
                            RF_flag |= flag_status_sleep ;
                            break;
                        }
                    }
                if((system_data.time.tick_sleep_check >=SYSTEM_SLEEP_TIME_MOUSE)/*||(rf_lost_cnt>0x20)*/)
                {
                	uart_printf(" to sleep\r\n");
                    RF_flag |= flag_status_sleep ;
                    break;
                }
            }
            else
            {
                if(!gpio_get_input(KEY_PAIR)) // for mode key is change very fast
                {
                    uart_printf(" to BT2\r\n");
                    app_set_device_index(DEVICE_OTHER);
                }
                break;                     //key or sensor wakeup
            }
        }
        // 1 - wheel pin, p1^0 p1^1, low interrupt, wakeup
        // 2 - 2ms expire, and then detect wheel has changed
        // 3 - other gpio wakeup if set, now is key_r3-0, so key press detect
        if(!(RF_flag & flag_status_sleep))
        {
            application_mouse_wake_up_from_32khz();
            RF_CHIP_ENABLE;
            system_data.time.tick_sleep_check = 0;
            RF_flag &= ~flag_status_idle ;
        }
        else
        {
        }
        RF_flag &= ~flag_power_up;
    }
}
#endif
/*! \fn void application_mouse_idle_rc32khz(void)
    \brief The third level sleep of mouse, idle in rc32khz without
timerrunning.
    Mouse enter into idle state in rc32khz clock without timer running, andit
needs the wake-up by key/wheel/sensor events.\n
    RF module powers off.
    \param void
    \return void
*/
void application_mouse_idle_rc32khz(void)
{
    uint8_t uWLLastState, uWLCurState;
	uWLLastState = 0x0;
	uWLCurState = 0x0;

    gpio_set_neg(TEST_PIN3);
    if(RF_flag & (flag_status_sleep/* | flag_system_powerdown*/))
    {

    gpio_set_neg(TEST_PIN3);
    	if((!gpio_get_input(KEY_PAIR))||(!gpio_get_input(KEY_LEFT))||(!gpio_get_input(KEY_RIGHT))
                ||(!gpio_get_input(KEY_MIDDLE))||(!gpio_get_input(SENSOR_MOTSWK_PIN)))
        {
            return;
        }

        gpio_set_neg(TEST_PIN3);
        uart_printf("in sleep\n");
//        uart_printf("swp=%2x,w=%2x\r\n", uWheelTest, system_data.wheel);
        RF_POWER_DOWN;
        RF_CHIP_DISABLE;

        //WHEEL_SLEEP;
        RF_flag &= ~flag_power_up ;
        rf_lost_cnt =0;
        status_idle_cnt = 0;
        adc_deinit(ADC_CHANNEL);

        #if(USB_DRIVER)
        usb_deinit();
        #endif
//        delay_ms(1);
//        DEBUG_MSG1(0xf1);
        wdt_disable();

        Timer0_Stop(1);
		#if	0
		if(RF_flag & flag_system_powerdown)
		{
			app_sensor_powerdown();
		}
		#endif
        Delay_ms(1);
//        DEBUG_MSG1(0xf2);
        SYS_REG0X10_INT_EN |= POS_SYS_REG0X10_INT_EN_GPIO;

        if((gpio_get_input(KEY_PAIR)) && (gpio_get_input(KEY_LEFT)) && (gpio_get_input(KEY_RIGHT)) \
        && (gpio_get_input(KEY_MIDDLE)) && (gpio_get_input(SENSOR_MOTSWK_PIN)))
        {
            if(gpio_get_input(WHEEL_B))
                uWLLastState |= B_0100_0000;
            if(gpio_get_input(WHEEL_A))
                uWLLastState |= B_1000_0000;
            key_wakeup_config();//gpio_sleep();
            cpu_24_reduce_voltage_sleep();
        }
 //      LED_Ctrl(1);
//        DEBUG_MSG1(0xf3);
        Timer0_Start(1,2000000); // 2ms
        //注册IO回调
        timer_cb_register(0,1,app_timer0_1_int_cb);

        SYS_REG0X10_INT_EN |= POS_SYS_REG0X10_INT_EN_TIMER0|POS_SYS_REG0X10_INT_EN_GPIO;
        application_mouse_wake_up_from_32khz();
//        delay_us(200);		// 200: about 160us.
		if(gpio_get_input(WHEEL_B))
	        uWLCurState |= B_0100_0000;
	    if(gpio_get_input(WHEEL_A))
	        uWLCurState |= B_1000_0000;
		if((uWLLastState != uWLCurState) && (gpio_get_input(KEY_PAIR)) && (gpio_get_input(KEY_LEFT)) && (gpio_get_input(KEY_RIGHT)) \
			&& (gpio_get_input(KEY_MIDDLE)) && (gpio_get_input(SENSOR_MOTSWK_PIN)))
		{
			Delay_ms(10);		// 1: about 1.4ms
			uart_printf("w wakeup\n");
		}
		else
		{
			Delay_ms(1);		// 1: about 1.4ms
			uart_printf("o wakeup\n");
		}
		#if	0
		if(RF_flag & flag_system_powerdown)
		{
			RF_flag &= ~flag_system_powerdown;
			app_sensor_wakeup();
		}
		#endif
//RC32K_BREAK:
	//	adc_init(ADC_CHANNEL,2);

        #if(USB_DRIVER)
        usb_init();
        #endif

        //flag_rf_last_state=1;
        system_data.time.tick_system = 0;
		lbd_sleep_onetime = 0x0;
        RF_flag &= ~flag_status_sleep ;
        system_data.wheel = 0x00;
		#if MOUSE_SWING
		system_data.swing = 0x0;
		#endif
//		LED_Ctrl(0);
    }
}

void application_page_key_check(void)
{
    if(app_val.powered_bind)
    {
        app_val.power_on_cnt++;
        if(app_val.power_on_cnt <= cPWROnEnPageTimer)
        {
            if((system_data.key_current & 0x07) == 0x07)
            {
                system_data.system_mode = SYSTEM_PAGE;
            }
        }
        else
        {
            app_val.powered_bind = 0x0;
			uart_printf("dispage\n");
        }
    }
}

extern uint8_t rf_mode;// 0:2.4,1:BLE

void application_normal_mode(void)
{
    uart_printf("in normal\n");

    application_normal_mode_initial();
	uart_printf("in normal mode, B=%x, T=%x\r\n", app_val.powered_bind, app_val.power_on_cnt);
    while((system_data.system_mode == SYSTEM_NORMAL))
    {
//滚轴的检测后面放在中断中去做，所以这边先不处理

		app_mouse_wheel_scan();

        if(RF_flag & flag_tick_8ms_loop)
        {
            gpio_set_neg(TEST_PIN1);
       //     wdt_enable(0x1000);       //enable wdt and clear it

            RF_flag &= ~flag_tick_8ms_loop;
            app_check_pair_and_mode_change();
       //     pair_key_check();
            if(rf_mode == RF_BLE_MODE)
            {
                break;
            }
            app_mouse_key_scan();
            app_mouse_key_check();
            application_page_key_check();
            if(system_data.system_mode != SYSTEM_NORMAL)
            {
                break;
            }
			#if(!SENSOR_TEST)
			if(bSensorCheck == 1)
            {
                app_sensor_check();
                rf_lost_cnt = 0;
            }
            #else
            if(!gpio_get_input(KEY_LEFT))
            {
                app_sensor_check();
                rf_lost_cnt = 0;
            }
            else
            {
            system_data.sensor_val.x = 0;
            system_data.sensor_val.y = 0;
            }

			#endif
            application_mouse_status_check();

            application_mouse_rf_send_check();

			driver_lbd_process();
            application_mouse_led_process();
            application_mouse_sleep_check();
        }
        application_mouse_idle_oscxmhz();
       //     if((Bled_time>=750)||flag_dongle_lost)
        {
//            application_mouse_idle_rc32khz_with_2ms_timer();
            application_mouse_idle_rc32khz();
        }
    }
}

void application_mouse_channel_search(void)
{
	uint8_t i,j;
//	uint8 uTmp;
	if(!flag_test && !channel_search)
	{
//		system_data.rf_array = 0;
//		system_data.rf_channel = 0;
		system_data.rf_array = 0x03;
		for(j = 0; j < 16; j++)
		{
    //        wdt_enable(0x1000);       //enable wdt and clear it
//			driver_set_rf_channel(system_data.rf_array, system_data.rf_channel);
			driver_rf_channel_switch();
			RF_CHIP_ENABLE;
			for(i = 0; i < 3; i++)
			{
				Delay_us(50);
				if(driver_rf_data_send(3))
				{
					channel_search = 1;
					uart_printf("con dongle\r\n");
					break;
				}
			}
			RF_CHIP_DISABLE;
			if(channel_search)
				break;

			#if	0
			system_data.rf_channel++;
			if(system_data.rf_channel > 3)
			{
				system_data.rf_channel = 0;
				system_data.rf_array++;
				if(system_data.rf_array > 3)
					system_data.rf_array = 0;
			}
			#endif
		}
	}
}

/*
	search test dongle.
*/
void general_dongle_search(void)
{
	uint8_t i;
	if(system_data.system_mode == SYSTEM_NORMAL)
	{
		RF_flag &= ~flag_rf_send_success;
		flag_test = 0;
		TRX_SETUP_RETR = 0x03;
		TRX_RF_CH = 0x80+90;				// 2490MHZ
		driver_rf_ouput_power_value_set(POWER_VALUE_MINUS_10DBM);

		memcpy_2461(&TRX_RX_ADDR_P0_0, rf_address_tx_pub, RF_ADDRESS_LEN);
		memcpy_2461(&TRX_TX_ADDR_0, rf_address_tx_pub, RF_ADDRESS_LEN);
		rf_fifo_data[0] = 0x0;

		for(i=0;i<3;i++)
		{
			Delay_us(150*10); 				// 1500=880us.
			driver_rf_data_send(1);

			if(RF_flag & flag_rf_send_success)
				break;
		}

		if(RF_flag & flag_rf_send_success)
		{
			uart_printf("con test dongle\r\n");
			flag_test = 1;
			for(i=0;i<5;i++)
				P0_Address[i] = rf_address_tx_pub[i];
		}
		else
		{
			driver_rf_ouput_power_value_set(cRFPWR);

			memcpy_2461(&TRX_RX_ADDR_P0_0, P0_Address, RF_ADDRESS_LEN);
			memcpy_2461(&TRX_TX_ADDR_0, P0_Address, RF_ADDRESS_LEN);
			#if	0
			system_data.rf_array = 0x0;
			system_data.rf_channel = 0x0;
			driver_set_rf_channel(system_data.rf_array, system_data.rf_channel);
			#endif
			system_data.rf_array = 0x03;
			driver_rf_channel_switch();
		}
	}

}
#define LBD_EN 0
void driver_lbd_process(void)
{
	#if LBD_EN
	uint16_t wADC;
   
    if(system_data.time.tick_lbd_check >= LBD_CHECK_TIME_MOUSE)
    {
        system_data.time.tick_lbd_check = 0;
//		adc_init(ADC_CHANNEL,1);
//		wADC = adc_get_value_(0x01,1);
		wADC = adc_get_value(ADC_CHANNEL,2);
		if(wADC == 0xffff)
		{
			wADC = 0x0;
//			uart_printf("adc err\n");
		}
//		else
			uart_printf("adc:=%x\n",wADC);
		if(wADC <= APP_VOLTAGE_1V0)		// single battery, 1.0V
		{
			system_data.lbd_count++;
		}
		else
			system_data.lbd_count = 0;

        if(system_data.lbd_count >= 3)
        {
        	wSysFlagfn24 |= flag_led_lbd; 					//低电压
        }
        else
        {
            wSysFlagfn24 &= ~flag_led_lbd;                 //非低电压
            //system_data.lbd_count = 0;
        }
    }
		#endif
}

void LED_Ctrl(uint8_t bLED)
{
	bLEDState = bLED;
	gpio_set(LED_24,bLEDState);
}

void LED_Toggle(void)
{
	bLEDState ^= 0xff;
	gpio_set(LED_24,(bLEDState&0x01));
}

/*! \fn void application_mouse_led_start(UINT8 time, UINT8 freq)
    \brief Start the led flicker frequency and time.

    The led will flicker in \a time delay, and continue for \a freq times.
    \param time: xms, based on the system tick, mouse 8ms, keyboard 4ms.
    \param freq: the flicker times
    \return void
*/
void application_mouse_led_start(uint8_t time, uint8_t freq)
{
    system_data.led.time = time;
    system_data.led.freq = freq * 2;
    LED_Ctrl(cLEDOn);
    driver_delay_set_with_base_tick(&system_data.led.led_timer, system_data.led.time);
    system_data.led.freq--;
}

/*! \fn void application_mouse_led_process(void)
    \brief If the flicker delay is expired, led will turn on or off and decrease the frequency. If the frequency is 0, led flicker will end.
    \param void
    \return void
*/
void application_mouse_led_process(void)
{
    if(system_data.led.freq)
    {
        if(driver_delay_with_base_tick_expire_check(&system_data.led.led_timer))
        {
            driver_delay_set_with_base_tick(&system_data.led.led_timer, system_data.led.time);
            LED_Toggle();
            system_data.led.freq--;
        }
    }
}


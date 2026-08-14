#include "app.h"
#include "icu.h"
#include "gpio.h"
#include "wdt.h"
#include "driver_timer.h"
extern SYSTEM_STRUCT_DATA system_data;
extern uint32 RF_flag;

APP_MOUSE_T mouse_val;
volatile uint8_t uRF_TXTime;
#if	(KEYBOARD)
volatile eRC_TIMER_DUTY eTimerDuty;
volatile uint8_t uTimer2msCnt;
#endif

void app_mouse_wheel_scan(void)
{
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

void app_gpio_sleep(void)
{

    gpio_set_int_mode(KEY_LEFT,3);
    gpio_set_int_mode(KEY_RIGHT,3);
    gpio_set_int_mode(KEY_MIDDLE,3);
    gpio_set_int_mode(KEY_PAIR,3);
    gpio_set_int_mode(PAW3205_MOTSWK_PIN,3);

	if(gpio_get_input(WHEEL_B))
        gpio_set_int_mode(WHEEL_B,3);
    else
        gpio_set_int_mode(WHEEL_B,2);
	if(gpio_get_input(WHEEL_A))
		gpio_set_int_mode(WHEEL_A,3);
    else
        gpio_set_int_mode(WHEEL_A,2);
	#if	0
    REG_APB5_GPIO_WUATOD_TYPE = ((1<<( (KEY_LEFT>>4)*8)+(KEY_LEFT&0x0f)))
                                |((1<<((KEY_RIGHT>>4)*8)+(KEY_RIGHT&0x0f)))
                                |((1<<( (KEY_MIDDLE>>4)*8)+(KEY_MIDDLE&0x0f)))
                                |((1<<( (KEY_PAIR>>4)*8)+(KEY_PAIR&0x0f)))
                                |((1<<( (WHEEL_B>>4)*8)+(WHEEL_B&0x0f)))
                                |((1<<( (WHEEL_A>>4)*8)+(WHEEL_A&0x0f)))
                                |((1<<( (PAW3205_MOTSWK_PIN>>4)*8)+(PAW3205_MOTSWK_PIN&0x0f)));
	#endif
    REG_GPIO_WUATOD_STATUS = 0xffffffff ;
    SYS_REG0X10_INT_EN |= (0x01 << POS_SYS_REG0X10_INT_EN_GPIO);

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

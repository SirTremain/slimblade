#include <string.h>
#include "BK3633_RegList.h"
#include "app.h"                     // Application Definitions
#include "app_task.h"                // application task definitions
#include "app_key.h"    
#include "gpio.h" 
#include "ke_timer.h"
#include "icu.h"

uint8_t power_down_satus=0;
static void app_key_int_cb(void)
{	
    uart_printf("%s \r\n",__func__);
	app_key_wakeup();

	if(!ke_timer_active(APP_PERIOD_TIMER, TASK_APP))
	    ke_msg_send_basic(APP_PERIOD_TIMER,TASK_APP,TASK_APP);
 
}
void app_key_init(void)
{
    gpio_config(POWER_KEY,INPUT,PULL_HIGH);

    gpio_cb_register(app_key_int_cb);
}

void power_down_satus_set(uint8_t status)
{
    power_down_satus=status;
}
uint8_t power_down_satus_get(void)
{
    return power_down_satus;
}
uint8_t app_key_scan(void)
{
    uart_printf("%s \r\n",__func__);
    static uint8_t cnt=0;
    uint8_t state=0;
    if(0==gpio_get_input(POWER_KEY))
    {
        if(cnt<100)
            cnt++;  
        if(cnt==PRESS_TIME)
        {
            if(APPM_CONNECTED==ke_state_get(TASK_APP))
            {
                appm_disconnect();
                power_down_satus_set(1);
            }
            else
            {
                appm_start_advertising();
            }
            state = 1;
        }        
    }
    else
    {
        cnt=0;
        state = 0;        
    }
    return state;
}

void app_key_sleep(void)
{
    uart_printf("%s \r\n",__func__);

    gpio_wakeup_config(POWER_KEY);
    
    SYS_REG0X10_INT_EN |= (1<<POS_SYS_REG0X10_INT_EN_GPIO);

}

void app_key_wakeup(void)
{
    uart_printf("%s \r\n",__func__);
    gpio_wakeup(POWER_KEY);
    SYS_REG0X10_INT_EN &= ~(1<<POS_SYS_REG0X10_INT_EN_GPIO);
}




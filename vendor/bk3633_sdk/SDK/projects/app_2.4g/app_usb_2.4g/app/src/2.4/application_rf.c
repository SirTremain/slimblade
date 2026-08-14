#include "app.h"
#include "gpio.h"

#include <string.h>
#include "application_mode.h"

#define UART_PRINTF	uart_printf
int uart_printf(const char *fmt,...);

uint8 sync_count=0;
//uint8 uLastCH;

extern SYSTEM_STRUCT_DATA system_data;
extern uint8_t rf_fifo_data[20];             //rf fifo
extern uint32_t RF_flag;
/*! \fn void application_mouse_rf_synchronize(void)
    \brief Mouse  sends rf synchoronize packet.
    \param void
    \return void
*/
void application_mouse_rf_synchronize(void)
{
    if(system_data.rf_connect != SYSTEM_END)
    {
        system_data.rf_connect = SYSTEM_SYNCHRONIZE;
        rf_fifo_data[0] |= SYSTEM_SYNCHRONIZE;
    }
}
void application_mouse_rf_send_with_insistent_hop_16ch(void)
{
    //UINT8 count = 16;
    if(!(RF_flag &flag_rf_hop_16ch))
    {
        application_mouse_rf_synchronize();
        driver_rf_channel_switch();
        TRX_SETUP_RETR = 0x03;	// 0x02;//250us,retranslate 2times
        if(driver_rf_data_send(system_data.rf_send_length))
        {
            //return result;
            RF_flag &= ~flag_rf_hop_16ch ;
            system_data.rf_connect = 0x00;
        }
        else
        {
        //	uart_printf("IH1ER,c=%d\n",RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel]);
            RF_flag |= flag_rf_hop_16ch ;
//            system_data.time.tick_rf_send_fail = SYSTEM_SEND_FAIL_TIME_MOUSE;
        }
    }
    if(RF_flag & flag_rf_hop_16ch)
    {
        while(!(RF_flag & flag_tick_8ms_loop))
        {
            //count--;
            driver_rf_channel_switch();
            if(driver_rf_data_retrans())
            {
                RF_flag &= ~flag_rf_hop_16ch;
                RF_flag &= ~flag_rf_need_clear_maxRT ;
                system_data.rf_connect = 0x00;
                break;
            }
            else
            {
                //system_data.time.tick_rf_send_fail = SYSTEM_SEND_FAIL_TIME_MOUSE;
                RF_flag |= flag_rf_need_clear_maxRT ;
		//		uart_printf("IH2ER,c=%d\n",RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel]);
            }

        }
    }
    //driver_rf_maxRT_clear();
}
/*! \fn void application_mouse_rf_send(void)
    \brief Mouse  sends events or adc data to dongle through rf module.
    Mouse:\n
            key pressed     - including left/right/middle key pressed, long pressed and released events for standard mouse\n
            wheel scrolling - direction, that's clockwise and anticlockwise; step\n
            sensor moving - relative x and y coordinate\n
            battery voltage when power up - just used in dongle part, not sent to PC\n
    \param void
    \return void
*/
void application_mouse_rf_send(void)
{
//    uint8 i;
	memset(rf_fifo_data, 0, 10);

	application_mouse_channel_search();
	if((!flag_test && !channel_search) || (!gpio_get_input(KEY_PAIR)))
	{
		system_data.wheel = 0x0;
		#if MOUSE_SWING
		system_data.swing = 0x0;
		#endif
		return;
	}

    RF_CHIP_ENABLE;
    {
        rf_fifo_data[0] = DATATYPE_MOUSE;
        rf_fifo_data[0] |= system_data.rf_connect;
        rf_fifo_data[1] = system_data.key_current;
        rf_fifo_data[2] = system_data.wheel;
        rf_fifo_data[3] = (uint8_t)(system_data.sensor_val.x);
        rf_fifo_data[4] = (uint8_t)(system_data.sensor_val.x >> 8);
        rf_fifo_data[5] = (uint8_t)(system_data.sensor_val.y);
        rf_fifo_data[6] = (uint8_t)(system_data.sensor_val.y >> 8);
		#if MOUSE_SWING
		rf_fifo_data[7] = system_data.swing;
		system_data.rf_send_length = 8;
		#else
        system_data.rf_send_length = 7;
		#endif
        #if(!SENSOR_TEST)

        system_data.sensor_val.x = 0;
        system_data.sensor_val.y =0;
        #endif
        //  system_data.wheel = 0;
    }
//    RF_CMD_CLEAR_STATUS_ALL;
    if((RF_flag & flag_rf_last_state ) && (sync_count==0))    //如果跳频包发送成功了， flag_rf_last_state会置位，但是sync_count==2
    {
        if(application_mouse_rf_send_start())//正常发送及发送跳频包
        {
            sync_count = 0;
			system_data.time.tick_rf_send_fail = 0x0;
//			uLastCH = RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel];
        }
        else
        {
        	if(RF_flag & flag_rf_last_state )
        	{
        		// hop pacekt tx ok.
		    	// retx mouse data.
				driver_rf_channel_switch();
				application_mouse_rf_synchronize();
				if(!application_mouse_rf_send_start())
				{
					// SYNC flag +user data pacekt tx fail.
					if(RF_flag & flag_rf_last_state )
		        	{
		        		// hop flag pacekt tx ok.
		            	sync_count = SYNC_TIMES;
		            	system_data.rf_connect = 0x00;
//						system_data.time.tick_rf_send_fail = SYSTEM_SEND_FAIL_TIME_MOUSE;	// next duty no new data, then retx mouse data.
//							uart_printf("hop2OK L=%d,c=%d\n",uLastCH,RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel]);
//							uLastCH = RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel];
		            }
		            else
		            {
		            	sync_count = 0x0;
		            	system_data.rf_connect = 0x00;
//						system_data.time.tick_rf_send_fail = SYSTEM_SEND_FAIL_TIME_MOUSE;
		            	RF_flag &= ~flag_rf_hop_16ch;
		            }
				}
				else
				{
					// SYNC flag + mouse data pacekt tx ok.
					sync_count = 0;
					system_data.rf_connect = 0x00;
					system_data.time.tick_rf_send_fail = 0x0;
//						uart_printf("hopMOK L=%d,c=%d\n",uLastCH,RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel]);
//						uLastCH = RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel];
				}
            }
            else
            {
            	// hop pacekt tx fail, 8ms over time.
            	sync_count = SYNC_TIMES;
			    system_data.rf_connect = 0x00;
	//			system_data.time.tick_rf_send_fail = SYSTEM_SEND_FAIL_TIME_MOUSE;
			    RF_flag &= ~flag_rf_hop_16ch;
		//		uart_printf("hopEr,c=%d\n",RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel]);
            }
        }
    }
    else if(sync_count)
    {
        sync_count--;
        driver_rf_channel_switch();
        application_mouse_rf_synchronize();
        if(!application_mouse_rf_send_start())
        {
        	if(RF_flag & flag_rf_last_state )
        	{
        		// hop pacekt tx ok.
        		// retx mouse data.
				driver_rf_channel_switch();
				application_mouse_rf_synchronize();
				Delay_us(300);
				if(!application_mouse_rf_send_start())
				{
					// SYNC flag +user data pacekt tx fail.
					if(RF_flag & flag_rf_last_state )
		        	{
		        		// hop flag pacekt tx ok.
		            	sync_count = SYNC_TIMES;
		            	system_data.rf_connect = 0x00;
//						system_data.time.tick_rf_send_fail = SYSTEM_SEND_FAIL_TIME_MOUSE;	// next duty no new data, then retx mouse data.
//							uart_printf("SHop2OK, L=%d,c=%d\n",uLastCH,RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel]);
//							uLastCH = RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel];
		            }
		            else
		            {
		            	sync_count = 0x0;
		            	system_data.rf_connect = 0x00;
//							system_data.time.tick_rf_send_fail = SYSTEM_SEND_FAIL_TIME_MOUSE;
		            	RF_flag &= ~flag_rf_hop_16ch;
		            }
				}
				else
				{
					// SYNC flag + mouse data pacekt tx ok.
					sync_count = 0;
					system_data.rf_connect = 0x00;
					system_data.time.tick_rf_send_fail = 0x0;
//						uart_printf("ShopMOK, L=%d,c=%d\n",uLastCH,RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel]);
//						uLastCH = RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel];
				}
            }
            else
			{
//            	system_data.time.tick_rf_send_fail = SYSTEM_SEND_FAIL_TIME_MOUSE;
            	RF_flag &= ~flag_rf_hop_16ch;
				uart_printf("ShopE,c=%d\n",RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel]);
            }
        }
        else
        {
            sync_count = 0;
            system_data.rf_connect = 0x00;
			system_data.time.tick_rf_send_fail = 0x0;
//			uart_printf("Sok, L=%d,c=%d\n",uLastCH,RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel]);
//			uLastCH = RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel];
        }
    }
    else
    {
        application_mouse_rf_send_with_insistent_hop_16ch();
		if(RF_flag & flag_rf_last_state )
		{
			RF_flag &= ~flag_rf_hop_16ch;
			sync_count = 0;
            system_data.rf_connect = 0x00;
			system_data.time.tick_rf_send_fail = 0x0;
//			uart_printf("IHok, L=%d,c=%d\n",uLastCH,RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel]);
//			uLastCH = RF_CHANNEL_TABLE[system_data.rf_array][system_data.rf_channel];
		}
		#if	0
		else
		{
			uart_printf("IHE\n");
		}
		#endif
    }
}
/*! \fn BOOL application_mouse_rf_send_start(void)
    \brief Mouse sends rf data to dongle when last sending succeeded.
    \param void
    \return TRUE - succeed to send, FALSE - otherwise
*/
uint8_t application_mouse_rf_send_start(void)
{
    TRX_SETUP_RETR = 0x08;	// 0x08;//250us,redo 8times

    if(driver_rf_data_send(system_data.rf_send_length))
    {

        return 1;
    }
    else
    {

        driver_rf_maxRT_clear();
    }

    //////////////////////////开始发送跳频包
    rf_fifo_data[0] &= ~SYSTEM_SYNCHRONIZE;
    system_data.rf_connect = SYSTEM_NEXT_CH;
    rf_fifo_data[0] |= system_data.rf_connect;
    TRX_SETUP_RETR = 0x01;//250us,retranslate 1 times

    if(driver_rf_data_send(system_data.rf_send_length))
    {

        return 0;
    }
    else
    {

        while(!(RF_flag & flag_tick_8ms_loop))
        {

            if(driver_rf_data_retrans())
            {

                break;
            }
        }
    }

	if((RF_flag & flag_rf_last_state) == 0x0)
    	driver_rf_maxRT_clear();

    rf_fifo_data[0] &= ~SYSTEM_NEXT_CH;
    system_data.rf_connect = 0;
    return 0;
}

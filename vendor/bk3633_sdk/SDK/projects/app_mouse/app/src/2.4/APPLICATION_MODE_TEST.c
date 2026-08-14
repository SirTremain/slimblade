#include "app.h"
#include "app_key.h"
#include "wdt.h"
#include "application_mode.h"
#include "application_mode_test.h"

#define UART_PRINTF	uart_printf
int uart_printf(const char *fmt,...);

uint8_t RF_TEST_CHANNEL[3] = {2, 46, 79};	// {8, 35, 77};
uint8_t RF_TEST_ADDRESS[RF_ADDRESS_LEN] = {0x15, 0x59, 0x23, 0x00, 0x00};
uint32_t XVR_REG24_BAK;

extern SYSTEM_STRUCT_DATA system_data;
extern uint32_t RF_flag;
extern uint8_t rf_fifo_data[MAX_PACKET_LEN];

extern volatile uint32_t XVR_ANALOG_REG_BAK[32];

//配置单载波发射
//freq:频点设置，双频点(2-80)
//power:功率等级(0x1-0xf)
void driver_rf_mode_single_wave(uint8_t freq)
{
	uint32_t val = 0;
/*
	bit0~6: channel, select by auto_chn; bit7~10[cur_cfg_pwr]: PA output;
	bit17: auto_chn, 0: config by XVR_REG24, 1:by baseband;
	bit20: auto_txpwr, 0: control by cur_cfg_pwr
	bit31: 0:1M, 1:2M;
*/
    XVR_ANALOG_REG_BAK[4] |=1<<29;
    addXVR_Reg0x4 = XVR_ANALOG_REG_BAK[4];

	XVR_REG24_BAK = addXVR_Reg0x24;
	val |= freq;
	val |= ((0x0f << 7) & XVR_REG24_BAK);		// PA output.
	addXVR_Reg0x24 = val;
	addXVR_Reg0x25 |= (0x1<<12) |(0x1<<13);

//	while(1);
}
/*
	该函数从PN9模式切换到正常模式切不过来
*/
void driver_rf_mode_normal(void)
{
	addXVR_Reg0x24 = XVR_REG24_BAK;
	addXVR_Reg0x25 &= ~(0x1<<12) |(0x1<<13);
}

void application_test_mode(void)
{
    uint8_t send_count;
    uint8_t single_channel_index = 1;
    uint8_t data_channel_index = 1;
    uint8_t status,flag_test_power_up_single_wave;
    uint8_t flag_revice=0;

	wdt_disable();   		//close when in test mode

    flag_test_power_up_single_wave = TEST_SINGLE_WAVE;
    TRX_SETUP_RETR = 0x03;
	driver_rf_ouput_power_value_set(cRFPWR);	// POWER_VALUE_MINUS_5DBM

    RF_POWER_DOWN;
    RF_POWER_UP;
    //RF_CHIP_DISABLE;
    //RF_CHIP_ENABLE;
	SwitchToTxMode();
	driver_rf_mode_single_wave(RF_TEST_CHANNEL[single_channel_index]);
//	TRX_RF_CH = 0x80 + RF_TEST_CHANNEL[single_channel_index];


	application_mouse_led_start(20,15);
    while(1)
    {
        if(RF_flag & flag_tick_8ms_loop)
        {
			RF_flag &= ~flag_tick_8ms_loop;

            if(flag_test_power_up_single_wave == TEST_RF_DATA)
            {
                rf_fifo_data[0] = DATATYPE_MOUSE;	// 0;
                rf_fifo_data[1] = 1;
                rf_fifo_data[2] = 2;
                rf_fifo_data[3] = 3;
                rf_fifo_data[4] = 4;
                send_count = 5;
                while(send_count--)
                {
                    driver_rf_data_send_noACK(5);
                    Delay_us(150*10); 				// 1500=880us.
                }
            }
			else if(flag_test_power_up_single_wave == TEST_CD)
			{
				rf_fifo_data[0] = 0xcc;
                rf_fifo_data[1] = 0xcc;
                rf_fifo_data[2] = 0xcc;
                rf_fifo_data[3] = 0xcc;
                rf_fifo_data[4] = 0xcc;
				rf_fifo_data[5] = 0xcc;
                rf_fifo_data[6] = 0xcc;
                rf_fifo_data[7] = 0xcc;
                rf_fifo_data[8] = 0xcc;
                rf_fifo_data[9] = 0xcc;
				rf_fifo_data[10] = 0xcc;
                rf_fifo_data[11] = 0xcc;
                rf_fifo_data[12] = 0xcc;
                rf_fifo_data[13] = 0xcc;
                rf_fifo_data[14] = 0xcc;
				rf_fifo_data[15] = 0xcc;
                rf_fifo_data[16] = 0xcc;
                rf_fifo_data[17] = 0xcc;
                rf_fifo_data[18] = 0xcc;
                rf_fifo_data[19] = 0xcc;
				rf_fifo_data[20] = 0xcc;
                rf_fifo_data[21] = 0xcc;
                rf_fifo_data[22] = 0xcc;
                rf_fifo_data[23] = 0xcc;
                rf_fifo_data[24] = 0xcc;
                send_count = 5;
                while(send_count--)
                {
					driver_rf_data_send_noACK(25);
                    Delay_us(150*10); 				// 1500=880us.
                }
			}

			if(flag_revice)
            {
                status = TRX_IRQ_STATUS;
			    if(status & STATUS_RX_DR)
			    {
			       RF_CMD_FLUSH_RX;
			       //RF_CMD_FLUSH_TX;
			      TRX_IRQ_STATUS = status;;
			    }
            }

            app_mouse_key_scan();

            //key process
            if(RF_flag & flag_key_short)
            {
                RF_flag &= ~flag_key_short;

                // left key: low middle high channel switch
                if(system_data.key_valid & MOUSE_STANDARD_KEY_MIDDLE)
                {
                    flag_revice=0;
					Rf_Init();
					SetDataRate(1);  		// data rate:1M
					RF_POWER_UP;
				    RF_CMD_FLUSH_TX;
				    RF_CMD_FLUSH_RX;
					TRX_SETUP_RETR = 0x03;
					driver_rf_ouput_power_value_set(cRFPWR);
					if(flag_test_power_up_single_wave == TEST_SINGLE_WAVE)
					{
						application_mouse_led_start(80,15);
						flag_test_power_up_single_wave = TEST_RF_DATA;
						TRX_RF_CH = 0x80 + RF_TEST_CHANNEL[data_channel_index];
						SwitchToTxMode();
 //                   	driver_rf_mode_normal();

						uart_printf("TEST_RF_DATA:=%x\n",XVR_REG24_BAK);
					}
					else if(flag_test_power_up_single_wave == TEST_RF_DATA)
					{
						application_mouse_led_start(50,15);
						flag_test_power_up_single_wave = TEST_CD;
						TRX_RF_CH = 0x80 + RF_TEST_CHANNEL[data_channel_index];
						SwitchToTxMode();
//                    	driver_rf_mode_normal();
						uart_printf("TEST_CD\n");
					}
					else if(flag_test_power_up_single_wave == TEST_CD || flag_test_power_up_single_wave == TEST_MAX)
					{
						application_mouse_led_start(20,15);
						flag_test_power_up_single_wave = TEST_SINGLE_WAVE;
//						SwitchToTxMode();
//						TEST_LED = 0;
						driver_rf_mode_single_wave(RF_TEST_CHANNEL[data_channel_index]);
						uart_printf("TEST_SINGLE_WAVE:=%x\n",XVR_REG24_BAK);
					}
                }
                else if(system_data.key_valid & MOUSE_STANDARD_KEY_LEFT)
                {
//                	TEST_LED = 0;
                    flag_revice = 0;
                    data_channel_index++;
                    if(data_channel_index > 2)
                        data_channel_index = 0;

					Rf_Init();
					SetDataRate(1);  		// data rate:1M
					RF_POWER_UP;
				    RF_CMD_FLUSH_TX;
				    RF_CMD_FLUSH_RX;
					TRX_SETUP_RETR = 0x03;
					driver_rf_ouput_power_value_set(cRFPWR);

					SwitchToTxMode();

					if(flag_test_power_up_single_wave == TEST_SINGLE_WAVE)
					{
						driver_rf_mode_single_wave(RF_TEST_CHANNEL[data_channel_index]);
					}
					else
						TRX_RF_CH = 0x80 + RF_TEST_CHANNEL[data_channel_index];
					uart_printf("switch ch==%d, mode=%x\n",RF_TEST_CHANNEL[data_channel_index], flag_test_power_up_single_wave);
                }
			  	else if(system_data.key_valid & MOUSE_STANDARD_KEY_RIGHT)
			  	{
//			  		TEST_LED = 0;
			       	flag_revice = 1;
					flag_test_power_up_single_wave = TEST_MAX;

					Rf_Init();
					SetDataRate(1);  		// data rate:1M
					RF_POWER_UP;
				    RF_CMD_FLUSH_TX;
				    RF_CMD_FLUSH_RX;
					TRX_SETUP_RETR = 0x03;
					TRX_RF_CH = 0x80 + RF_TEST_CHANNEL[data_channel_index];
					driver_rf_ouput_power_value_set(cRFPWR);

					SwitchToRxMode();
	                TRX_RF_CH = 0x80 + RF_TEST_CHANNEL[data_channel_index];
//	                driver_rf_mode_normal();
				}

		    }
//			else
//		  		TEST_LED = 1;
        }
		application_mouse_led_process();
    }
}

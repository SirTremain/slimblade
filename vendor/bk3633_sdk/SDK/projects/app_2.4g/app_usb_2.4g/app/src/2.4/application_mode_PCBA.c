#include "app.h"
#include "icu.h"
#include "adc.h"
#include "driver_timer.h"
#include "Driver_rf.h"
#include "gpio.h"
#include "wdt.h"
#include "application_mode.h"

#include "driver_bk24.h"
#include "driver_sensor.h"

unsigned char result_data,send_chl,send_time;

extern uint32_t RF_flag;
extern uint8_t rf_fifo_data[MAX_PACKET_LEN];
extern void driver_rf_mode_single_wave(uint8_t freq);

unsigned char  REC_OneByte(void)
{
	uint8_t i,test_tran_channel;
	uint16_t  j;
	test_tran_channel = 0;
	i = 0;
	j = 0;
	test_tran_channel = 0;

	while(gpio_get_input(PCBA_SCLK));
	for(i = 0; i < 8; i++)
	{
		while(gpio_get_input(PCBA_SCLK));
		{
			j++;
			if(j > 10000)
			{

				break;
			}
		}
		j = 0;
		while((gpio_get_input(PCBA_SCLK) == 0x0));
		{
			j++;
			if(j > 10000)
			{
				break;
			}
		}

		test_tran_channel = test_tran_channel<< 1;

		if(gpio_get_input(PCBA_SDIO))
		{
			test_tran_channel |= 0x01;
		}

	}

	return test_tran_channel;

}

void pcba_test_init()
{
	uint32_t rf_address_tx_test[RF_ADDRESS_LEN];

	gpio_config(PCBA_SCLK,INPUT, PULL_HIGH);
	gpio_config(PCBA_SDIO,INPUT, PULL_HIGH);	// input  SDIO

	gpio_set(PCBA_SACK,1);						// output  SACK
	gpio_config(PCBA_SACK,OUTPUT, PULL_NONE);

	rf_address_tx_test[0] = 0x15;
	rf_address_tx_test[1] = 0x59;
	rf_address_tx_test[2] = 0x23;
	rf_address_tx_test[3] = 0xC6;
	rf_address_tx_test[4] = 0x00;

	memcpy_2461(&TRX_RX_ADDR_P0_0, rf_address_tx_test, RF_ADDRESS_LEN);
	memcpy_2461(&TRX_TX_ADDR_0, rf_address_tx_test, RF_ADDRESS_LEN);
	SwitchToTxMode();

	Timer0_Stop(1);					// must used.
	Timer0_Start(1,3000000); 	// 3ms
	send_chl = 0;
	send_time = 1;
}

void send_bind_result()
{
	unsigned char i;

	app_sensor_init();

	for(i = 0;i < 100; i++)
	{
		result_data = 0xaa;
		if(!bSensorCheck)
		{
			result_data = 0x55;
		}

		while((RF_flag & flag_wake_up_by_timer) == 0x0);	// 3ms
		RF_flag &=  ~flag_wake_up_by_timer;

		RF_CMD_FLUSH_TX;
		RF_CMD_FLUSH_RX;

		RF_CHIP_ENABLE;

		rf_fifo_data[0] = result_data;
		rf_fifo_data[1] = send_chl;			//rf_power;
		rf_fifo_data[2] = send_time;
		rf_fifo_data[3] = 0x0;		// *******P0;
		rf_fifo_data[4] = 0x0;		// *******P1;
		rf_fifo_data[5] = 0x0;		// *******P2;
		driver_rf_data_send(6);

		RF_CHIP_DISABLE;

	}

	for(i = 0;i < 42; i++)
	{
		while((RF_flag & flag_wake_up_by_timer) == 0x0);	// 3ms
		RF_flag &=  ~flag_wake_up_by_timer;
	}

}

void application_PCBA_mode(void)
{
	unsigned char cmd_temp,retran_cnt,j,i;

	wdt_disable();   		//close when in test mode

//	REG_AHB0_ICU_IRQ_ENABLE = 0x0;

	pcba_test_init();

	TRX_SETUP_AW = 0x01;
	TRX_SETUP_RETR = 0x05;
	TRX_RF_CH = 0x80 + 0x0A;
	TRX_RF_SETUP = 0x03;
	RF_POWER_UP;
//	REG_AHB0_ICU_IRQ_ENABLE = 0x3;

	gpio_set(PCBA_SACK,0);
	Delay_ms(1);   			// 1, 1ms; wait for  1.2ms
	gpio_set(PCBA_SACK,1);
	Delay_ms(1);   			//wait for  1.2ms
	gpio_set(PCBA_SACK,0);
	Delay_ms(1);   			//wait for  1.2ms
	gpio_set(PCBA_SACK,1);
	Delay_ms(1);   			//wait for  1.2ms
	gpio_set(PCBA_SACK,0);
	Delay_ms(1);   			//wait for  1.2ms
	gpio_set(PCBA_SACK,1);

	retran_cnt = 0;

	while(1)
	{
		cmd_temp = REC_OneByte();
		if(cmd_temp == 0xa5)
		{

			send_chl = REC_OneByte();
			send_time = REC_OneByte();

			TRX_RF_CH = 0x80 + send_chl;

			Delay_us(50*10); 				// 1500=880us.

			gpio_set(PCBA_SACK,0);
			break;
		}
		else
		{
			retran_cnt++;
			if(retran_cnt >= 20)
				break;
		}
	}


/////////////////
	RF_flag &=  ~flag_wake_up_by_timer;
	for(j = 0; j < 68; j++)
	{
		while((RF_flag & flag_wake_up_by_timer) == 0x0);  // 3ms
		RF_flag &=  ~flag_wake_up_by_timer;
	}
////////////////

	if(send_time == 0xff)
	{
		while(1)
		{
			send_bind_result();
		}
	}
	else
	{
		send_bind_result();
		driver_rf_mode_single_wave(send_chl);
		for(j = 0;j < (send_time-1);j++)
		{
			for(i = 0; i < 150; i++)
			{
				while((RF_flag & flag_wake_up_by_timer) == 0x0);  //3ms
				RF_flag &=  ~flag_wake_up_by_timer;
			}
		}
		Rf_Init();
		SetDataRate(1);  		// data rate:1M
		RF_POWER_UP;
	    RF_CMD_FLUSH_TX;
	    RF_CMD_FLUSH_RX;
		TRX_SETUP_AW = 0x01;
		TRX_SETUP_RETR = 0x05;
		TRX_RF_CH = 0x80 + send_chl;
		TRX_RF_SETUP = 0x03;
		SwitchToTxMode();
//		driver_rf_mode_normal();
	}

	Delay_us(150*10); 				// 1500=880us.

	app_sensor_powerdown();
	RF_POWER_DOWN;
	Timer0_Stop(1);
	//WHEEL_SLEEP;
	adc_deinit(ADC_CHANNEL);
	app_gpio_sleep();

	while(1)
	{
		SYS_REG0X10_INT_EN = 0x0;
//		TEST_LED = 0;
		cpu_reduce_voltage_sleep();
	}

}


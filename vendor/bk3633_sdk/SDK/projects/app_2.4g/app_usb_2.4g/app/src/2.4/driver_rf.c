#include <stdio.h>
#include "app.h"

#include "driver_rf.h"
#include "driver_bk24.h"
#include "gpio.h"
#include "driver_timer.h"
#include "application_mode.h"
#include "bk3633_reglist.h"

#define UART_PRINTF	uart_printf
int uart_printf(const char *fmt,...);

extern SYSTEM_STRUCT_DATA system_data;
extern uint32_t RF_flag;
extern volatile uint8_t uRF_TXTime;

uint32_t Cfg_0c_Val[4] = {0x1F, 0x1B, 0x73, 0x00};
uint32_t Cfg_0d_Val[4] = {0x36, 0xB4, 0x80, 0x28};
uint32_t P0_Address[5] = {0x10, 0x11, 0x36, 0x0, 0x0};	// {0x03, 0x01, 0xe7, 0xa5, 0xbc};
uint32_t rf_address_tx_pub[5] = {0x50,0x25, 0x34, 0x18, 0x24};	// {0x50,0x00, 0x00, 0x00, 0x00};

uint32_t P1_Address[5] = {0x10, 0x56, 0x24, 0xCD, 0x78};
uint8_t rf_fifo_data[MAX_PACKET_LEN];             //rf fifo
//uint8 RF_CHANNEL_TABLE[16] = {8, 37, 68, 21, 40, 77, 7, 35, 67, 10, 42, 55, 14, 28, 49, 41};//{3, 28, 53, 8, 33, 58, 13, 38, 63, 18, 43, 68, 23, 48, 73, 78};
uint8_t RF_CHANNEL_TABLE[4][4] = {{7, 8, 10, 14}, {21, 28, 35, 37}, {40, 41, 42, 49}, {55, 67, 68, 77}};	// { {8,37,68,21},{40, 77, 7, 35},{67, 10, 42, 55},{14, 28, 49, 41} };

uint8_t uRXDataLens;
uint8_t flag_test;
uint8_t channel_search;

/*! \fn void driver_rf_spi_write_register(UINT8 reg,  UINT8 value)
    \brief Write the value of register address \reg.
    \param reg - register address
    \param value - data
    \return void
*/
void PowerUp_Rf(void)
{
    TRX_CONFIG |= 0x02;
}
void PowerDown_Rf(void)
{
    TRX_CONFIG &= 0xFD;
}
void SwitchToRxMode(void)
{
    PowerUp_Rf();
    FLUSH_RX;
    TRX_CE = 0;
    TRX_CONFIG |= 0x01;
    TRX_CE = 1;
}
void SwitchToTxMode(void)
{
    PowerUp_Rf();
    FLUSH_TX;
    TRX_CE = 0;
    TRX_CONFIG &= 0xFE;
    TRX_CE = 1;
}
void ChangeTxPipe(uint8_t pipe)
{
    uint32_t tmp_address[5];
    switch(pipe)
    {
    case 0:
        memcpy_2461(&TRX_RX_ADDR_P0_0, P0_Address, RF_ADDRESS_LEN);
        memcpy_2461(&TRX_TX_ADDR_0, P0_Address, RF_ADDRESS_LEN);
        memcpy_2461(&TRX_RX_ADDR_P1_0, P1_Address, RF_ADDRESS_LEN);
        break;
    case 1:
    case 2:
    case 3:
    case 4:
    case 5:
        memcpy_2461(tmp_address, P1_Address, RF_ADDRESS_LEN);
        if(pipe == 2)                              // For P1, need not change LSB
        {
            tmp_address[0] = TRX_RX_ADDR_P2;
        }
        else if(pipe == 3)
        {
            tmp_address[0] = TRX_RX_ADDR_P3;
        }
        else if(pipe == 4)
        {
            tmp_address[0] = TRX_RX_ADDR_P4;
        }
        else if(pipe == 5)
        {
            tmp_address[0] = TRX_RX_ADDR_P5;
        }
        memcpy_2461(&TRX_RX_ADDR_P0_0, tmp_address, RF_ADDRESS_LEN);
        memcpy_2461(&TRX_TX_ADDR_0, tmp_address, RF_ADDRESS_LEN);
        memcpy_2461(tmp_address, P1_Address, RF_ADDRESS_LEN);
        tmp_address[2] = 0x37;                          // avoid for 2 same address for R1, R2, ... R5
        memcpy_2461(&TRX_RX_ADDR_P1_0, tmp_address, RF_ADDRESS_LEN);
        break;
    default:
        break;
    }
}
void R_RX_PAYLOAD(uint8_t *pBuf, uint8_t bytes)
{
    uint8_t i;
    TRX_CMD = 0x40;                   // command
    for(i=0; i<bytes; i++)
    {
        pBuf[i] = TRX_FIFO;    // data
    }
    TRX_CMD = 0x00;                   // end: nop command
}
void W_TX_PAYLOAD(uint8_t *pBuf, uint8_t bytes)
{
    uint8_t i;
    TRX_CMD = 0x60;
    for(i=0; i<bytes; i++)
    {
        TRX_FIFO = pBuf[i];
    }
    TRX_CMD = 0x00;
}
void W_TX_PAYLOAD_NOACK(uint8_t *pBuf, uint8_t bytes)
{
    uint8_t i;
    TRX_CMD = 0x68;//0xB0;
    for(i=0; i<bytes; i++)
    {
        TRX_FIFO = pBuf[i];
    }
    TRX_CMD = 0x00;
}
void W_ACK_PAYLOAD(uint8_t *pBuf, uint8_t bytes, uint8_t pipe)
{
    uint8_t i;
    TRX_CMD = 0x68 + pipe;
    for(i=0; i<bytes; i++)
    {
        TRX_FIFO = pBuf[i];
    }
    TRX_CMD = 0x00;
}
void Rf_Init(void)
{
    clrf_SYS_Reg0x3_bk24_pwd;
  //   set_SYS_Reg0x2_core_div(1);
	//  set_SYS_Reg0x2_core_sel(3);

//    set_SYS_Reg0x1e_ahb_clk_gate_disable(9);
//    uint8 i;
//    // 初始化模拟寄存器
//    for(i=0; i<8; i++)
//        Write_Reg_Ana(i, Ana_Init_Val[i]);
//    // 设置功率
//    TRX_GPA0 = 0x05;
//    TRX_GPA1 = 0xF8;
//    // 关闭模式选择电路
//    TRX_ANAPWD_CTRL0 |= 0x11;
    // 初始化cfg_0C, cfg_0D
    memcpy_2461(&TRX_CFG_0C_0, Cfg_0c_Val, 4);
    memcpy_2461(&TRX_CFG_0D_0, Cfg_0d_Val, 4);
//    memcpy_2461(&TRX_RAMP_TABLE_0, Ramp_Table_Val, 11);
    TRX_CONFIG     = 0x0C;    // default PTX
    TRX_EN_AA      = 0x3F;
    TRX_EN_RXADDR  = 0X3F;
    TRX_SETUP_AW   = 0x03;
    TRX_SETUP_RETR = 0x33;
    TRX_RF_CH      = 0x5;
    TRX_RF_SETUP   = 0x0f;
    memcpy_2461(&TRX_RX_ADDR_P0_0, P0_Address, RF_ADDRESS_LEN);
    memcpy_2461(&TRX_RX_ADDR_P1_0, P1_Address, RF_ADDRESS_LEN);
    TRX_RX_ADDR_P2 = 0x11;
    TRX_RX_ADDR_P3 = 0x12;
    TRX_RX_ADDR_P4 = 0x13;
    TRX_RX_ADDR_P5 = 0x14;
    memcpy_2461(&TRX_TX_ADDR_0, P0_Address, RF_ADDRESS_LEN);
    TRX_RX_PW_P0 = 0x20;
    TRX_RX_PW_P1 = 0x20;
    TRX_RX_PW_P2 = 0x20;
    TRX_RX_PW_P3 = 0x20;
    TRX_RX_PW_P4 = 0x20;
    TRX_RX_PW_P5 = 0x20;
    TRX_DYNPD    = 0x3F;
    TRX_FEATURE  = 0x07;
//    TRX_PLL_SDM &= 0xEF;    // open_loop_en=0
    PowerDown_Rf();
    addXVR_Reg0x24 = 0x000e0782;
    addXVR_Reg0x3b = 0x36340048;

}
void memcpy_2461(volatile uint32_t *p, uint32_t *val, uint8_t len)
{
    uint8_t i = 0;
    for ( i = 0; i < len ; i++ )
    {
        p[i] = val[i];
    }
}
void SetDataRate(int data_rate)
{
    switch ( data_rate )
    {
        case 0 :  // 250kbps
            addXVR_Reg0x2e &= 0xfffffe00 ;
            addXVR_Reg0x2e |= 0x64 ;
            addXVR_Reg0x26 &= 0xe000ffff;
            addXVR_Reg0x26 |= 0x04080000;
            addXVR_Reg0x30 &= ~(0x1ff<<8);
            addXVR_Reg0x30 |= 0x28<<8;
            TRX_RF_SETUP = 0x27;
            break;
        case 1 : // 1Mbps
            addXVR_Reg0x2e &= 0xfffffe00 ;
            addXVR_Reg0x2e |= 0x100 ;
            addXVR_Reg0x26 &= 0xe000ffff;
            addXVR_Reg0x26 |= 0x10200000;
            TRX_RF_SETUP = 0x07;
            break;
        case 2 : // 2Mbps
            addXVR_Reg0x2e &= 0xfffffe00 ;
            addXVR_Reg0x2e |= 0x100 ;
            addXVR_Reg0x26 &= 0xe000ffff;
            addXVR_Reg0x26 |= 0x10200000;
            TRX_RF_SETUP = 0x0F;
            break;
        default:
            break;
    }
}

void driver_rf_channel_switch(void)
{
	uint8_t uTmp;
	#if	0
	system_data.rf_channel++;
    if(system_data.rf_channel > 3)
		system_data.rf_channel = 0;
	#endif
	system_data.rf_array++;
    if(system_data.rf_array > 3)
		system_data.rf_array = 0;
	uTmp = system_data.rf_channel;
	if(system_data.rf_array == 0x1)
		uTmp = uTmp >> 2;
	else if(system_data.rf_array == 0x02)
		uTmp = uTmp >> 4;
	else if(system_data.rf_array == 0x03)
		uTmp = uTmp >> 6;
	uTmp &= 0x03;
    if(!flag_test)
    {
    	TRX_RF_CH = 0x80+RF_CHANNEL_TABLE[system_data.rf_array][uTmp];
        TRX_CE = 0;
        TRX_CE = 1;
    }
}

void driver_set_rf_channel(uint8_t uArray, uint8_t uIndx)
{
    TRX_CE = 0;
	TRX_RF_CH = 0x80+RF_CHANNEL_TABLE[uArray][uIndx];
    TRX_CE = 1;
}

uint32_t driver_rf_data_send(uint8_t len)
{
    uint8_t status;
	uint8_t fifo_status_rx;
	uint8_t rx_len;
	uint8_t bTXOvTime;

    RF_CMD_FLUSH_TX;
    RF_CMD_FLUSH_RX;
    RF_CMD_CLEAR_STATUS_ALL;
    RF_flag &= ~flag_rf_last_state;
    W_TX_PAYLOAD(rf_fifo_data,len);

	bTXOvTime = 0x0;
	uRF_TXTime = 0x0;
    do
    {
        status=TRX_IRQ_STATUS;
        Delay_us(5);
		if(uRF_TXTime > 5)
		{
			bTXOvTime = 1;
			break;
		}
    }
    while((status & (STATUS_TX | STATUS_RX_DR)) == 0x00);

    if(status & STATUS_TX_DS)
    {

        RF_flag |= flag_rf_last_state ;
		RF_flag |= flag_rf_send_success;
		if(system_data.rf_connect != SYSTEM_NEXT_CH)
		{
        	system_data.rf_send_length = 0;
			system_data.wheel = 0;
			#if MOUSE_SWING
			system_data.swing = 0x0;
			#endif
		}
        //  driver_rf_receive_MSG_package();
        if(system_data.rf_connect == SYSTEM_SYNCHRONIZE)
        {
            driver_timer0_reset();
        }
        else if(TRX_OBSERVE_TX & 0x0F)
        {
            if(system_data.rf_connect != SYSTEM_NEXT_CH)
            {
 //               driver_timer0_reset();
            }
        }
        RF_CMD_FLUSH_TX;
        RF_CMD_CLEAR_STATUS_TX;
    }
    else
    {

    }

	if(status & STATUS_RX_DR)
	{

		do
        {
            rx_len = TRX_RX_RPL_WIDTH;
            if(rx_len <= MAX_PACKET_LEN)
            {
                //memset(rf_fifo_data, 0, 32);
                R_RX_PAYLOAD(rf_fifo_data,len);			// read receive payload from RX_FIFO buffer
                if((rf_fifo_data[0] == DATATYPE_MOUSE) && (rf_fifo_data[1] == DATATYPE_MOUSE_SLEEP))
                {
                    RF_flag |= flag_system_powerdown;
                }
            }

            fifo_status_rx = TRX_IRQ_STATUS;	            // read register FIFO_STATUS's value
        }while((fifo_status_rx & STATUS_RX_EMPTY) == 0);    // while not empty

		uart_printf("rx\n");
		RF_CMD_FLUSH_RX;
		RF_CMD_CLEAR_STATUS_RX;
	}

	if(bTXOvTime)
	{
		RF_CMD_FLUSH_RX;
		RF_CMD_FLUSH_TX;
		PowerDown_Rf();
		PowerUp_Rf();
        RF_CMD_CLEAR_STATUS_MAX;
	}
//因为max后需要重传，只要清max就可以启动
//rf_send_exit:
    //if(status & STATUS_MAX_RT)
    //{
    //RF_CMD_FLUSH_TX;
    //RF_CMD_FLUSH_RX;
    //RF_CMD_CLEAR_STATUS_ALL;
    //}
    return (RF_flag&flag_rf_last_state);
}
uint32_t driver_rf_data_retrans(void)
{
    uint8_t status;
	uint8_t bTXOvTime;

    RF_CMD_CLEAR_STATUS_MAX;
//	delay_us(20);
	bTXOvTime = 0x0;
	uRF_TXTime = 0x0;
    do
    {
        status = TRX_IRQ_STATUS;
		Delay_us(5);
		if(uRF_TXTime > 5)
		{
			bTXOvTime = 1;
			break;
		}
        #if	0
        if(RF_flag & flag_tick_8ms_loop)
        {
            break;
        }

        if(!gpio_get_input(KEY_PAIR))
        {
		    app_set_device_index(DEVICE_OTHER);
            break;
        }
        #endif
    }
    while((status & STATUS_TX) == 0x00);

    if(status & STATUS_TX_DS)
    {
        RF_flag |= flag_rf_last_state ;
		if(system_data.rf_connect != SYSTEM_NEXT_CH)
		{
        	system_data.rf_send_length = 0;
			system_data.wheel = 0;
			#if MOUSE_SWING
			system_data.swing = 0x0;
			#endif
		}
        if((system_data.rf_connect == SYSTEM_SYNCHRONIZE))
        {
            driver_timer0_reset();
        }
        else if(TRX_OBSERVE_TX&0x0F)
        {
            if(system_data.rf_connect != SYSTEM_NEXT_CH)
            {
//                driver_timer0_reset();
            }
//			uart_printf("re=%d\n",TRX_OBSERVE_TX&0x0F);
        }
		RF_CMD_FLUSH_TX;
        RF_CMD_CLEAR_STATUS_TX;
    }
    if(status & STATUS_MAX_RT)
    {
        RF_flag &= ~flag_rf_last_state ;
    }

	if(bTXOvTime)
	{
		RF_CMD_FLUSH_RX;
		RF_CMD_FLUSH_TX;
		PowerDown_Rf();
		PowerUp_Rf();
        RF_CMD_CLEAR_STATUS_MAX;

		RF_flag &= ~flag_rf_last_state ;
		RF_flag &= ~flag_rf_hop_16ch;			// 重新填fifo, 避免空fifo调用driver_rf_data_retrans函数
	}
    return (RF_flag & flag_rf_last_state);
}
void driver_rf_maxRT_clear(void)
{
    //RF_CMD_FLUSH_TX;
    //RF_CMD_FLUSH_RX;
    //RF_CMD_CLEAR_STATUS_ALL;
    RF_CMD_FLUSH_TX;
    RF_CMD_FLUSH_RX;
    RF_CMD_CLEAR_STATUS_ALL;
}
uint8_t driver_rf_data_send_noACK(uint8_t len)
{
    uint8_t status;
    RF_CMD_FLUSH_RX;
    RF_CMD_FLUSH_TX;
    RF_CHIP_ENABLE;
    W_TX_PAYLOAD_NOACK(rf_fifo_data,len);
    //sleep and wake up by rf interrupt
    //ENABLE_RF_WAKEUP;
    //driver_idle_osc8mhz();
    //DISABLE_RF_WAKEUP;
    do
    {
        status = TRX_IRQ_STATUS;
    }
    while((status & STATUS_TX) == 0x00);
    if(status & STATUS_TX_DS)
    {
        //RF_CMD_FLUSH_TX;
        RF_CMD_CLEAR_STATUS_TX;
    }
	else
	{
	}
    RF_CHIP_DISABLE;
    return 1;
}

uint8_t driver_rf_data_send_ACK(uint8_t len)
{
    uint8_t status, uRes = 0x0;
	uint8_t bTXOvTime;
    RF_CMD_FLUSH_RX;
    RF_CMD_FLUSH_TX;
	RF_CMD_CLEAR_STATUS_ALL;
    RF_CHIP_ENABLE;
    W_TX_PAYLOAD(rf_fifo_data,len);
    //sleep and wake up by rf interrupt
    //ENABLE_RF_WAKEUP;
    //driver_idle_osc8mhz();
    //DISABLE_RF_WAKEUP;
    bTXOvTime = 0x0;
	uRF_TXTime = 0x0;
    do
    {
        status = TRX_IRQ_STATUS;
		if(uRF_TXTime > 5)
		{
			bTXOvTime = 1;
			break;
		}
    }
    while((status & STATUS_TX) == 0x00);

	if(status & STATUS_RX_DR)
    {
        RF_CMD_FLUSH_RX;
        RF_CMD_CLEAR_STATUS_RX;
		uRes = 2;
    }

    if(status & STATUS_TX_DS)
    {
        RF_CMD_FLUSH_TX;
        RF_CMD_CLEAR_STATUS_TX;
		uRes = 1;
    }

	if((status & STATUS_MAX_RT) || bTXOvTime)
    {
    	RF_CMD_FLUSH_RX;
		RF_CMD_FLUSH_TX;
		PowerDown_Rf();
		PowerUp_Rf();
        RF_CMD_CLEAR_STATUS_MAX;
    }

    RF_CHIP_DISABLE;
    return uRes;
}

/*! \fn void driver_rf_receive_package(void)
    \brief Receive the RF package to fifo buffer.
    \param void
    \return void
*/
void driver_rf_receive_package(void)
{
    uint8_t status;
    uint8_t fifo_status;
    uint8_t len;
    status=TRX_IRQ_STATUS;

 //   uart_printf("s=%x\r\n",status);
// read register STATUS's value
    if(status & STATUS_RX_DR)            // if receive data ready (RX_DR) interrupt
    {
        do
        {
            len = TRX_RX_RPL_WIDTH;
            if(len <= MAX_PACKET_LEN)
            {
                R_RX_PAYLOAD(rf_fifo_data,len);			// read receive payload from RX_FIFO buffer
                if(!(RF_flag&flag_rf_receive_page) && ((rf_fifo_data[0] == DATATYPE_PAGE_START) || (rf_fifo_data[0] == DATATYPE_PAGE_END_MOUSE)))
                {
//                    if(rf_fifo_data[3] & 0x01)
                    {
                        RF_flag |= flag_rf_receive_page;
						uRXDataLens = len;
                    }
                }
            }
            else
            {
                RF_CMD_FLUSH_RX;
                break;
            }
            fifo_status = TRX_IRQ_STATUS;               // read register FIFO_STATUS's value
        }
        while((fifo_status & STATUS_RX_EMPTY) != STATUS_RX_EMPTY);  // check the rx fifo is empty         // while not empty
      TRX_IRQ_STATUS = fifo_status;
      }

}
extern uint32_t XVR_REG24_BAK;
extern volatile uint32_t XVR_ANALOG_REG_BAK[32];

void driver_rf_ouput_power_value_set(uint8_t power_level)
{
    uint32_t regv_0x24;
    XVR_ANALOG_REG_BAK[4] |=1<<29;
    addXVR_Reg0x4 = XVR_ANALOG_REG_BAK[4];
    regv_0x24=addXVR_Reg0x24&0xFFFFF87F;
    /*    switch(power_level)
        {
          case 0x0:
            power_level=0;
            break;
          case 0x1:
            power_level=1;
            break;
          default:
            power_level=6;
            break;
        }*/
    regv_0x24=regv_0x24|(power_level<<7);
    addXVR_Reg0x24 = regv_0x24;
	XVR_REG24_BAK = addXVR_Reg0x24;

 //   XVR_ANALOG_REG_BAK[4] &= ~1<<29;
 //   addXVR_Reg0x4 = XVR_ANALOG_REG_BAK[4];

//  uart_printf("24= %2x\r\n",XVR_REG24);
}

uint8_t get_rf_rssi(void)
/*
注意
1 读rssi最好把agc关闭，    addXVR_Reg0x3c |=0x01<<31;
2 把中频的rx gain降到最低：
   		 XVR_ANALOG_REG_BAK[8] &= ~(0x7f<<20);
    		addXVR_Reg0x8 = XVR_ANALOG_REG_BAK[8]  ;

tx功率设定为0，天线靠近，得到的值为0x5e；十公分大概0x58；二十公分大概0x51；50
公分大概0x52-0x49不稳定
以上测试值与天线和方向有关

记得用完要切回正常值

*/
{
    uint8_t rssi_data = 0;
    rssi_data = get_XVR_Reg0x13_rssi_ind_o;
    return(rssi_data);
}


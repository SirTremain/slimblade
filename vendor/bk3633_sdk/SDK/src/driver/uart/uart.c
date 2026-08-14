/**
 ****************************************************************************************
 *
 * @file uart.c
 *
 * @brief UART driver
 *
 * Copyright (C) RivieraWaves 2009-2015
 *
 *
 ****************************************************************************************
 */
#include <stddef.h>     // standard definition
#include <stdarg.h>
#include <stdint.h>        // standard integer definition
#include <string.h>        // string manipulation
#include <stdio.h>
#include "icu.h"
#include "uart.h"       // uart definition
#include "rwip.h" 
#include "gpio.h"
#include "user_config.h"
#include "icu.h"
#include "BK3633_RegList.h"


const uint8_t reset_cmd[9]={0x01, 0xe0, 0xfc, 0x05,  0xfe, 0x95, 0x27, 0x95,  0x27 };

extern volatile uint32_t XVR_ANALOG_REG_BAK[32];
volatile static uint8_t  uart_rx_done = 0;
volatile static uint32_t uart_rx_index = 0;
volatile static struct uart_env_tag uart_env;
uint8_t uart_rx_buf[UART_FIFO_MAX_COUNT];
uint8_t uart_tx_buf[UART_FIFO_MAX_COUNT];

void uart_init(uint32_t baudrate)
{

    uint32_t uart_clk_div;
    
    SET_UART_POWER_UP ;   //open periph
    uart_clk_div = 16000000/baudrate -1;
    
    gpio_config(0x00,SC_FUN,PULL_HIGH);
    gpio_config(0x01,SC_FUN,PULL_HIGH);
    
    UART_REG0X0 = (uart_clk_div << POS_UART_REG0X0_CLK_DIVID) |
                    (0x0          << POS_UART_REG0X0_STOP_LEN ) |
                    (0x0          << POS_UART_REG0X0_PAR_MODE ) |
                    (0x0          << POS_UART_REG0X0_PAR_EN   ) |
                    (0x3          << POS_UART_REG0X0_LEN      ) |
                    (0x0          << POS_UART_REG0X0_IRDA     ) |
                    (0x1          << POS_UART_REG0X0_RX_ENABLE) |
                    (0x1          << POS_UART_REG0X0_TX_ENABLE) ;
    
    UART_REG0X1 = 0x00004010;
    UART_REG0X4 = 0x42;
    UART_REG0X6 = 0x0;
    UART_REG0X7 = 0x0;

    SYS_REG0X10_INT_EN |= (0x01 << POS_SYS_REG0X10_INT_EN_UART);

    uart_rx_done = 0;
    uart_rx_index = 0;

    //// Initialize RX and TX transfer callbacks
    uart_env.rx.callback = NULL;
    uart_env.tx.callback = NULL;
    uart_env.uart_tx_buf = NULL;
    uart_env.uart_rx_buf = NULL;
    uart_env.uart_tx_length = 0;
    uart_env.uart_rx_length = 0;
    uart_env.uart_tx_enable = 0;
    uart_env.uart_rx_enable = 0;
    
#if (VIRTUAL_UART_H4TL == 1)
    #if (BLE_APP_PRESENT)
    if( get_sys_mode()==DUT_FCC_MODE )
    #endif
    {
        hci_data_init((HCI_DATA_TYPE_CMD | HCI_DATA_TYPE_EVENT));
        host_get_event_cbReg(uart_send);
    }
#endif
}

static void uart_send_byte(uint8_t data)
{
    while( 0==(UART_REG0X2&(1<<POS_UART_REG0X2_FIFO_WR_READY)) );
    
    UART_REG0X3 = data;
}

void uart_send(void *buff, uint16_t len)
{
    uint8_t *tmpbuf = (uint8_t *)buff;
    while (len--)
        uart_send_byte(*tmpbuf++);
}

int uart0_printf(const char *fmt,...)
{
    va_list ap;
    int n;
    char send_buf[128];
    va_start(ap, fmt);
    n=vsprintf(send_buf, fmt, ap);
    va_end(ap);
    uart_send(send_buf, n);
    return n;
}

void uart_flow_on(void)
{

}
bool uart_flow_off(void)
{
    return true;
}

void uart_read(uint8_t *bufptr, uint32_t size, void (*callback) (void*, uint8_t), void* dummy)
{	
    ASSERT_ERR(bufptr != NULL);
    ASSERT_ERR(size != 0);
    ASSERT_ERR(callback != NULL);
    uart_env.rx.callback = callback;
    uart_env.rx.dummy    = dummy;

    uart_env.uart_rx_buf = bufptr;	////	uart_rx_ptr_setf((uint32_t) bufptr);
    uart_env.uart_rx_length = size; ////	uart_rx_size_setf(size);
    uart_env.uart_rx_enable = 1;	////	uart_rx_start_setf(1);
}

void uart_write(uint8_t *bufptr, uint32_t size, void (*callback) (void*, uint8_t), void* dummy)
{
	// Sanity check
    ASSERT_ERR(bufptr != NULL);
    ASSERT_ERR(size != 0);
    ASSERT_ERR(callback != NULL);
    uart_env.tx.callback = callback;
    uart_env.tx.dummy    = dummy;
        
    uart_env.uart_tx_buf = bufptr;
    uart_env.uart_tx_length = size;
    uart_env.uart_tx_enable = 1;
}

static void uart_rx_data(uint8_t *buf, uint8_t len)
{
#if 0    
    for(uint8_t i=0; i<len; i++)
    {
        uart_printf("0x%x ", buf[i]);
    }
    uart_printf("\r\n");
#else
    return ;
#endif    
} 
extern uint8_t uart_rx_en;
void  uart_isr(void)
{
    uint32_t uart_int_status;	
    uart_int_status = UART_REG0X5;
    if ( uart_int_status & ( (1<<POS_UART_REG0X5_RX_FIFO_NEED_READ)|(1<<POS_UART_REG0X5_UART_RX_STOP_END ) ) )
    {    
        uart_rx_en = 1;
        while(UART_REG0X2 & (1<<POS_UART_REG0X2_FIFO_RD_READY))
        {
            uart_rx_buf[uart_rx_index] = (UART_REG0X3>>8);
            uart_rx_handler(uart_rx_buf[uart_rx_index]);
            uart_rx_index++;
            if (uart_rx_index == UART_FIFO_MAX_COUNT)
            {
                uart_rx_index = 0;
            }       
        }
        if ( uart_int_status & (1<<POS_UART_REG0X5_UART_RX_STOP_END ) )
        {   
            #if (VIRTUAL_UART_H4TL == 1)
            #if (BLE_APP_PRESENT)
            if( get_sys_mode()==DUT_FCC_MODE )
            #endif
            {
                if((uart_rx_buf[0] == 0x01) && ((uart_rx_buf[3] + 4) == uart_rx_index))
                {
                    host_send_cmd(uart_rx_buf,uart_rx_index);
                }
            }
            #endif
            
            uart_rx_data(uart_rx_buf,uart_rx_index); 
            uart_rx_index=0;
            uart_rx_done = 1;             
        }
    }
    UART_REG0X5 = uart_int_status;
}
void uart_rx_cmd_respone(uint8_t *buff,uint8_t len )
{
    uint8_t respone_buff[32];
    
    respone_buff[0]=0x04;
    respone_buff[1]=0x0e;
    respone_buff[2]=4+len;
    respone_buff[3]=0x01;
    respone_buff[4]=0xe0;
    respone_buff[5]=0xfc;
    respone_buff[6]=len;
    
    memcpy(&respone_buff[7],buff,len);

    uart_send(respone_buff,7+len);


}
void uart_rx_cmd_handler(uint8_t *buff,uint8_t len )
{      
    uint32_t rx_command;
    uint8_t length;
    static uint8_t rx_cmd_count=0;
    length=len;
    switch(buff[0])
    {
        case UART_LINK_CHECK:
        {
            if(length==1)
            {   
                if(rx_cmd_count++>2)
                    icu_set_sleep_mode(NO_SLEEP);   
                buff[1]=0;
            }
        }            
        break;
        case CMD_SYS_RESET:
        {    
            if(length==5)
            {
                rx_command = (buff[1]<<24|buff[2]<<16|buff[3]<<8|buff[4]);
                if(rx_command==0x95279527)
                {
                    cpu_reset();
                    
                }
            }
            length -=1;
        }
        break;
        #if(DEBUG_RF_REG)          
        case REG_WRITE_CMD:
        {
            uint32_t reg_index;
            uint32_t reg_addr;
            uint32_t reg_value; 

            reg_addr=buff[1]+(buff[2]<<8)+(buff[3]<<16)+(buff[4]<<24); 
            reg_value=buff[5]+(buff[6]<<8)+(buff[7]<<16)+(buff[8]<<24);
            reg_index = (reg_addr-BASEADDR_XVR)/4;

            *(volatile uint32_t *)reg_addr = reg_value;
            
            if(reg_index<=0x1f)
            {
                XVR_ANALOG_REG_BAK[reg_index] = reg_value;
            }
            
        }       
        break;
        case REG_READ_CMD:
        {
            uint32_t reg_index;
            uint32_t reg_addr;
            uint32_t reg_value; 

            reg_addr=buff[1]+(buff[2]<<8)+(buff[3]<<16)+(buff[4]<<24);  
            
            reg_index = (reg_addr-BASEADDR_XVR)/4;

            if (reg_index<=0x0f)
            {
                reg_value  = XVR_ANALOG_REG_BAK[reg_index];    
            }
            else if( (reg_index>0x1b) && (reg_index<=0x1f) )
            {
                reg_value  = XVR_ANALOG_REG_BAK[reg_index];    
            }
            else
            {
                reg_value  = *(volatile uint32_t *)reg_addr;              
            }
            
            memcpy(&buff[5],&reg_value,4);
            length += 3;
            
        }
        break;
        #endif        
    }
  
    #if(DEBUG_RF_REG)       
    uart_rx_cmd_respone(&buff[1],length);
    #endif

}

void uart_rx_handler(uint8_t value )
{

    static uint8_t cmd_status=0;
    static uint16_t index=0;
    static uint16_t length;
    static uint8_t uart_cmd[32];

                      
    switch(cmd_status)
    {        
        case UART_CMD_STATE_HEAD:
        {
            if(value==0x01)
            {
                cmd_status=UART_CMD_STATE_OPCODE_ONE;              
            }
            else
                cmd_status=UART_CMD_STATE_HEAD;
        }
        break;
        case UART_CMD_STATE_OPCODE_ONE:
        {
            if( value==0xe0 )                    
                cmd_status=UART_CMD_STATE_OPCODE_TWO;
            else
                cmd_status=UART_CMD_STATE_HEAD;     
        }
        break;
        case UART_CMD_STATE_OPCODE_TWO:
        {
            if( value==0xfc )                    
                cmd_status=UART_CMD_STATE_LENGTH;
            else
                cmd_status=UART_CMD_STATE_HEAD;      
        }
        break;
        case UART_CMD_STATE_LENGTH:
        {
            length=value;           
            if( length>0 )                    
            {
                cmd_status=UART_CMD_STATE_CMD;
                index=0;   
            }
            else
                cmd_status=UART_CMD_STATE_HEAD;                         
        }
        break;       
        case UART_CMD_STATE_CMD:
        {
            uart_cmd[index++]=value;           
            if(index==length)
            {              
                uart_rx_cmd_handler(uart_cmd,length);
                cmd_status=UART_CMD_STATE_HEAD;
            }        
        }
        break;           
    }         
}




#if (VIRTUAL_UART_H4TL == 1)

volatile struct hci_cmd_event_data host_cmd_data;
volatile struct hci_cmd_event_data host_event_data;
void hci_data_init(uint8_t type)
{	////type: 0x01-Clear host cmd data; 0x02-Clear host event data
    
    if(type & HCI_DATA_TYPE_CMD)
    {
        host_cmd_data.callback = NULL;
        memset((void *)&host_cmd_data.data_buf[0], 0, HCI_DATA_BUF_SIZE);
        host_cmd_data.data_len = 0;
    }
    if(type & HCI_DATA_TYPE_EVENT)
    {
    ////	host_event_data.callback = NULL;		////Will clear callback func
        memset((void *)&host_event_data.data_buf[0], 0, HCI_DATA_BUF_SIZE);
        host_event_data.data_len = 0;
    }
}

void host_send_cmd(uint8_t *bufptr, uint16_t length)
{
	//uint16_t tmpCnt = 0;
	ASSERT_ERR(length >= HCI_DATA_BUF_SIZE);
	host_cmd_data.callback = NULL;		////Test Only
	memcpy((void *)&host_cmd_data.data_buf[0], bufptr, length);
	host_cmd_data.data_len = length;

}

////void host_get_event(uint8 *bufptr, uint8 length)
void host_get_event(void)
{

	if(host_event_data.callback != NULL)
	{
		host_event_data.callback((void *)host_event_data.data_buf, host_event_data.data_len);
	}
	hci_data_init(HCI_DATA_TYPE_EVENT);
}

void host_get_event_cbReg(void (*callback) (void*, uint16_t))
{
	host_event_data.callback = callback;
}

void uart_h4tl_data_switch(void)
{   
    void (*callback) (void*, uint8_t) = NULL;
    void* data =NULL;
    uint16_t data_len = 0;

    while(uart_env.uart_tx_enable == 1)
    {
        //uart_printf("uart_h4tl_data_switch tx_enable\r\n");
        // Retrieve callback pointer
        callback = uart_env.tx.callback;
        data     = uart_env.tx.dummy;

        uart_env.uart_tx_enable = 0;
        memcpy((void *)&host_event_data.data_buf[data_len], uart_env.uart_tx_buf, uart_env.uart_tx_length);
        data_len += uart_env.uart_tx_length;
        host_event_data.data_len += uart_env.uart_tx_length;
        if(callback != NULL)
        {
            // Clear callback pointer
            uart_env.tx.callback = NULL;
            uart_env.tx.dummy    = NULL;

            // Call handler
            callback(data, RWIP_EIF_STATUS_OK);
        }
        else
        {
            ASSERT_ERR(0);
        }
    }
    
    if(host_event_data.data_len != 0)
    {	////New Event
        host_get_event();           
    }

    data_len = 0;

    if(host_cmd_data.data_len > 0)
    {	
        while(uart_env.uart_rx_enable == 1)
        {
            // Retrieve callback pointer
            callback = uart_env.rx.callback;
            data     = uart_env.rx.dummy;
            uart_env.uart_rx_enable = 0;

            memcpy((void *)uart_env.uart_rx_buf, (void *)&host_cmd_data.data_buf[data_len], uart_env.uart_rx_length);

            data_len += uart_env.uart_rx_length;
            if(callback != NULL)
            {
                // Clear callback pointer
                uart_env.rx.callback = NULL;
                uart_env.rx.dummy    = NULL;

                // Call handler
                callback(data, RWIP_EIF_STATUS_OK);
            }
            else
            {
                ASSERT_ERR(0);
            }
            if(data_len >= host_cmd_data.data_len)
                break;
        }////while(uart_env.uart_rx_enable == 1)
     
      	////Clear HCI Cmd data
       hci_data_init(HCI_DATA_TYPE_CMD);        
    }
}


#endif




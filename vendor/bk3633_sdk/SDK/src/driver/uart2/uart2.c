#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "uart2.h"
#include "user_config.h"
#include "gpio.h"
#include "icu.h"


volatile uint8_t  uart2_rx_done = 0;
volatile uint32_t uart2_rx_index = 0;

uint8_t uart2_rx_buf[UART2_FIFO_MAX_COUNT];
uint8_t uart2_tx_buf[UART2_FIFO_MAX_COUNT];


//==============================UART_INITIAL===================

void uart2_init(uint32_t baudrate)
{
    uint32_t    uart_clk_div;
    
    SET_UART2_POWER_UP ;   //open periph
    uart_clk_div = 16000000/baudrate -1 ;
    
    gpio_config(0x16,SC_FUN,PULL_HIGH);
    gpio_config(0x17,SC_FUN,PULL_HIGH);
    
    UART2_REG0X0 = (uart_clk_div << POS_UART2_REG0X0_CLK_DIVID) |
                                (0x0          << POS_UART2_REG0X0_STOP_LEN ) |
                                (0x0          << POS_UART2_REG0X0_PAR_MODE ) |
                                (0x0          << POS_UART2_REG0X0_PAR_EN   ) |
                                (0x3          << POS_UART2_REG0X0_LEN      ) |
                                (0x0          << POS_UART2_REG0X0_IRDA     ) |
                                (0x1          << POS_UART2_REG0X0_RX_ENABLE) |
                                (0x1          << POS_UART2_REG0X0_TX_ENABLE) ;
    
    UART2_REG0X1 = 0x00004010;
    UART2_REG0X4 = 0x42;
    UART2_REG0X6 = 0x0;
    UART2_REG0X7 = 0x0;

    SYS_REG0X10_INT_EN |= (0x01 << POS_SYS_REG0X10_INT_EN_UART2);

    uart2_rx_done = 0;
    uart2_rx_index = 0;

}




static void uart2_send_byte(unsigned char data)
{
    while( 0==(UART2_REG0X2&(1<<POS_UART2_REG0X2_FIFO_WR_READY)) );
    UART2_REG0X3 = data;
}

void uart2_send(void *buff, int len)
{
    uint8_t *tmpbuf = (uint8_t *)buff;
    while (len--)
        uart2_send_byte(*tmpbuf++);
}


void clear_uart2_buffer(void)
{
    uart2_rx_index = 0;
    uart2_rx_done = 0;
    memset(uart2_rx_buf, 0, sizeof(uart2_rx_buf)); /**< Clear the RX buffer */
    memset(uart2_tx_buf, 0, sizeof(uart2_tx_buf)); /**< Clear the TX buffer */
}


int uart2_printf(const char *fmt,...)
{
#if (UART_PRINTF_ENABLE)    
    va_list ap;
    int n;
    char send_buf[128];
    va_start(ap, fmt);
    n=vsprintf(send_buf, fmt, ap);
    va_end(ap);
    uart2_send(send_buf, n);
    return n;
#else
    return 0;
#endif
}


//==========================UART_INTERRUPT==========================

void uart2_isr(void)
{
    unsigned long uart_int_status;
    unsigned char uart_fifo_rdata;	
    uart_int_status = UART2_REG0X5;
    if ( uart_int_status & ( (1<<POS_UART2_REG0X5_RX_FIFO_NEED_READ)|(1<<POS_UART2_REG0X5_UART_RX_STOP_END ) ) )
    {    
        while(UART2_REG0X2 & (1<<POS_UART2_REG0X2_FIFO_RD_READY)
)
        {
            uart_fifo_rdata = (UART2_REG0X3>>8);

            uart2_rx_buf[uart2_rx_index++] = uart_fifo_rdata;
            if (uart2_rx_index == UART2_FIFO_MAX_COUNT)
            {
                uart2_rx_index = 0;
            }
        }

        if ( uart_int_status & (1<<POS_UART2_REG0X5_UART_RX_STOP_END ) )
        uart2_rx_done = 1;    // 此处应该先判断是否满足RX STOP
    }

    UART2_REG0X5 = uart_int_status;
}






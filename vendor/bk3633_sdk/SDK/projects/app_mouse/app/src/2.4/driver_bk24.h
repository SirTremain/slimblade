/*************************************************************
 * @file        driver_bk24.h
 * @brief       Header file of driver_bk24.c
 * @author      lvjinxia
 * @version     V1.0
 * @date        2018-09-06
 * @par
 * @attention
 */
#ifndef __DRIVER_BK24_H__
#define __DRIVER_BK24_H__
#ifdef __cplusplus
extern "C" {
#endif  /* __cplusplus */
//#include "BK_System.h"
#define APB_BK24_BASE            0x00805000
#define  XBYTE      ((volatile uint32_t *)APB_BK24_BASE)
#define  ADDR_BASE_TRX          0x00
#define  ADDR_BASE_XRAM         0x00
#define  TRX_CONFIG             XBYTE[0x00]
#define  TRX_EN_AA              XBYTE[0x01]
#define  TRX_EN_RXADDR          XBYTE[0x02]
#define  TRX_SETUP_AW           XBYTE[0x03]
#define  TRX_SETUP_RETR         XBYTE[0x04]
#define  TRX_RF_CH              XBYTE[0x05]
#define  TRX_RF_SETUP           XBYTE[0x06]
#define  TRX_RX_ADDR_P0_0       XBYTE[0x07]
#define  TRX_RX_ADDR_P0_1       XBYTE[0x08]
#define  TRX_RX_ADDR_P0_2       XBYTE[0x09]
#define  TRX_RX_ADDR_P0_3       XBYTE[0x0a]
#define  TRX_RX_ADDR_P0_4       XBYTE[0x0b]
#define  TRX_RX_ADDR_P1_0       XBYTE[0x0c]
#define  TRX_RX_ADDR_P1_1       XBYTE[0x0d]
#define  TRX_RX_ADDR_P1_2       XBYTE[0x0e]
#define  TRX_RX_ADDR_P1_3       XBYTE[0x0f]
#define  TRX_RX_ADDR_P1_4       XBYTE[0x10]
#define  TRX_RX_ADDR_P2         XBYTE[0x11]
#define  TRX_RX_ADDR_P3         XBYTE[0x12]
#define  TRX_RX_ADDR_P4         XBYTE[0x13]
#define  TRX_RX_ADDR_P5         XBYTE[0x14]
#define  TRX_TX_ADDR_0          XBYTE[0x15]
#define  TRX_TX_ADDR_1          XBYTE[0x16]
#define  TRX_TX_ADDR_2          XBYTE[0x17]
#define  TRX_TX_ADDR_3          XBYTE[0x18]
#define  TRX_TX_ADDR_4          XBYTE[0x19]
#define  TRX_RX_PW_P0           XBYTE[0x1a]
#define  TRX_RX_PW_P1           XBYTE[0x1b]
#define  TRX_RX_PW_P2           XBYTE[0x1c]
#define  TRX_RX_PW_P3           XBYTE[0x1d]
#define  TRX_RX_PW_P4           XBYTE[0x1e]
#define  TRX_RX_PW_P5           XBYTE[0x1f]
#define  TRX_DYNPD              XBYTE[0x20]
#define  TRX_FEATURE            XBYTE[0x21]
#define  TRX_CFG_0C_0           XBYTE[0x22]
#define  TRX_CFG_0C_1           XBYTE[0x23]
#define  TRX_CFG_0C_2           XBYTE[0x24]
#define  TRX_CFG_0C_3           XBYTE[0x25]
#define  TRX_CFG_0D_0           XBYTE[0x26]
#define  TRX_CFG_0D_1           XBYTE[0x27]
#define  TRX_CFG_0D_2           XBYTE[0x28]
#define  TRX_CFG_0D_3           XBYTE[0x29]
#define  TRX_RAMP_TABLE_0       XBYTE[0x2a]
#define  TRX_RAMP_TABLE_1       XBYTE[0x2b]
#define  TRX_RAMP_TABLE_2       XBYTE[0x2c]
#define  TRX_RAMP_TABLE_3       XBYTE[0x2d]
#define  TRX_RAMP_TABLE_4       XBYTE[0x2e]
#define  TRX_RAMP_TABLE_5       XBYTE[0x2f]
#define  TRX_RAMP_TABLE_6       XBYTE[0x30]
#define  TRX_RAMP_TABLE_7       XBYTE[0x31]
#define  TRX_RAMP_TABLE_8       XBYTE[0x32]
#define  TRX_RAMP_TABLE_9       XBYTE[0x33]
#define  TRX_RAMP_TABLE_A       XBYTE[0x34]
#define  TRX_CE                 XBYTE[0x35]
#define  TRX_CMD                XBYTE[0x36]
#define  TRX_FIFO               XBYTE[0x37]
#define  TRX_IRQ_STATUS         XBYTE[0x40]
//interrupt status bit
#define  B_IRQ_RX_DR            0x40
#define  B_IRQ_TX_DS            0x20
#define  B_IRQ_MAX_RT           0x10
#define  B_IRQ_TX_FULL          0x01
#define  TRX_OBSERVE_TX         XBYTE[0x41]
#define  TRX_RSSI_IND           XBYTE[0x42]
#define  TRX_FIFO_STATUS        XBYTE[0x43]
//FIFO status bit
#define  B_FIFO_TX_REUSE        0x40
#define  B_FIFO_TX_FULL         0x20
#define  B_FIFO_TX_EMPTY        0x10
#define  B_FIFO_RX_FULL         0x02
#define  B_FIFO_RX_EMPTY        0x01
#define  TRX_RX_RPL_WIDTH       XBYTE[0x44]
#define  TRX_MBIST_STATUS       XBYTE[0x45]
// command
#define  FLUSH_TX               { TRX_CMD = 0xA0; }
#define  FLUSH_RX               { TRX_CMD = 0x80; }
#define  REUSE_TX_PL            { TRX_CMD = 0x10; }
#define  TIMES_FOR_LOOP_PIPES   20
#define  MAX_PIPE_NUMBER        6
#define  RX_PLOAD_MAX_WIDTH     0x20
#endif

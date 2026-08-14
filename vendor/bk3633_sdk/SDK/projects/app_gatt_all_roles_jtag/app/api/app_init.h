/**
 ****************************************************************************************
 *
 * @file master_app.h
 *
 * @brief Application entry point
 *
 * Copyright (C) Beken 2009-2016
 *
 *
 ****************************************************************************************
 */
#ifndef APP_INIT_H_
#define APP_INIT_H_
#include "rwip_config.h"     // SW configuration
#if (BLE_APP_PRESENT)
#include <stdint.h>          // Standard Integer Definition
#include <co_bt.h>           // Common BT Definitions
#include "arch.h"            // Platform Definitions
#include "gap.h"
#include "gapc.h"            // GAPC Definitions
#include "gattc_task.h"
#include <stdbool.h>
#include "ke_task.h"
#include "co_error.h"
#include "attm.h"
#include "gattc_task.h"
#include "prf_utils.h"
#include "ke_mem.h"
#include "sdp_service.h"
#if (BLE_CENTRAL)

/// Initing state machine
enum app_init_state
{
    /// Iint activity does not exists
    APP_INIT_STATE_IDLE = 0,
    /// Creating Iint activity
    APP_INIT_STATE_CREATING,
   /// Iint activity created
    APP_INIT_STATE_CREATED,
    /// Starting Iint activity
    APP_INIT_STATE_CONECTTING,
    /// Iint activity conected
    APP_INIT_STATE_CONECTED,
    /// Stopping Iint activity
    APP_INIT_STATE_STOPPING,

};

extern struct gap_bdaddr  con_bdaddr;
uint8_t appm_start_connecting(struct gap_bdaddr bdaddr);
uint8_t appm_stop_connencting(void);
void appm_set_connect_dev_addr(struct gap_bdaddr bdaddr);

struct gap_bdaddr appm_get_connect_dev_addr(void);

void appm_recover_connencting(struct gap_bdaddr bdaddr);
void appm_creat_connenct(void);
uint8_t appc_write_service_data_req(uint8_t conidx,uint16_t handle,uint16_t data_len,uint8_t *data);
uint8_t appc_write_service_ntf_cfg_req(uint8_t conidx,uint16_t handle,uint16_t ntf_cfg,uint16_t seq_num);
uint8_t appm_read_service_data_by_uuid_req(uint8_t conidx,uint8_t uuid_len,uint8_t* uuid);
uint8_t appm_read_service_data_by_handle_req(uint8_t conidx,uint16_t handle);
uint8_t appm_read_service_ntf_ind_cfg_by_handle_req(uint8_t conidx,uint16_t handle);
uint8_t appm_read_service_userDesc_by_handle_req(uint8_t conidx,uint16_t handle);

void uart_data_pro(void);

void appm_init_fsm_next(void);
void appm_update_init_state(bool start);
void appm_read_info_req(uint8_t conidx,uint16_t handle);
/**
 ****************************************************************************************
 * @brief Send a disconnection request
 ****************************************************************************************
 */
//uint8_t appm_disconnect(uint8_t condix);


#endif //#if (BLE_CENTRAL)
#endif
#endif

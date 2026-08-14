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
#ifndef APP_SCAN_H_
#define APP_SCAN_H_
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
#include "app_task.h"
#if (BLE_CENTRAL || BLE_OBSERVER)

/// Scaning state machine
enum app_scan_state
{
    /// Scaning activity does not exists
    APP_SCAN_STATE_IDLE = 0,
    /// Creating Scaning activity
    APP_SCAN_STATE_CREATING,
    /// Scaning activity created
    APP_SCAN_STATE_CREATED,
    /// Starting Scaning activity
    APP_SCAN_STATE_STARTING,
    /// Scaning activity started
    APP_SCAN_STATE_STARTED,
    /// Stopping Scaning activity
    APP_SCAN_STATE_STOPPING,

};



void appm_start_scanning(void);
void appm_stop_scanning(void);
uint8_t appm_adv_data_decode(uint8_t len,const uint8_t *data,uint8_t *find_str,uint8_t str_len);
uint8_t appm_adv_data_decode_name(uint8_t len,const uint8_t *data,uint8_t *name_str);


void uart_data_pro(void);


void appm_scan_fsm_next(void);
void appm_update_scan_state(bool start);

/**
 ****************************************************************************************
 * @brief Send a disconnection request
 ****************************************************************************************
 */
//uint8_t appm_disconnect(uint8_t condix);

#endif //#if (BLE_CENTRAL || BLE_OBSERVER)
#endif
#endif

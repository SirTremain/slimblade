/**
 ****************************************************************************************
 *
 * @file app_adv.h
 *
 * @brief Application entry point
 *
 * Copyright (C) Beken 2009-2016
 *
 *
 ****************************************************************************************
 */
 
#ifndef APP_ADV_H_
#define APP_ADV_H_

#include "rwip_config.h"     // SW configuration
#include <stdint.h>          // Standard Integer Definition
#include <co_bt.h>           // Common BT Definitions
#include "arch.h"            // Platform Definitions
#include "gapc_task.h"       // GAPC Definitions

#if (BLE_APP_PRESENT) 
/// Default Device Name


/// Advertising state machine
enum app_adv_state
{
    /// Advertising activity does not exists
    APP_ADV_STATE_IDLE = 0,
    /// Creating advertising activity
    APP_ADV_STATE_CREATING,
    /// Setting advertising data
    APP_ADV_STATE_SETTING_ADV_DATA,
    /// Setting scan response data
    APP_ADV_STATE_SETTING_SCAN_RSP_DATA,
     /// Updata adv data
    APP_ADV_STATE_UPDATA_ADV_DATA,
    /// Advertising activity created
    APP_ADV_STATE_CREATED,
    /// Starting advertising activity
    APP_ADV_STATE_STARTING,
    /// Advertising activity started
    APP_ADV_STATE_STARTED,
    /// Stopping advertising activity
    APP_ADV_STATE_STOPPING,
    APP_ADV_STATE_DELETE,

};
/**
 ****************************************************************************************
 * @brief
 ****************************************************************************************
 */
void appm_adv_fsm_next(void);

/**
 ****************************************************************************************
 * @brief Send to request to update the adv data parameters
 ****************************************************************************************
 */
uint8_t appm_updata_adv_data(uint16_t length, uint8_t *p_data);


/**
 ****************************************************************************************
 * @brief delete advertising
 *
 * @param[in] none
 ****************************************************************************************
 */

void appm_delete_advertising(void);
bool app_gapm_adv_check_data_sanity(uint16_t length, uint8_t *p_data);
 
#endif //

#endif //


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
 
#ifndef APP_MESH_ADV_H_
#define APP_MESH_ADV_H_

#include "rwip_config.h"     // SW configuration
#include <stdint.h>          // Standard Integer Definition
#include <co_bt.h>           // Common BT Definitions
#include "arch.h"            // Platform Definitions
#include "gapc_task.h"       // GAPC Definitions

#if (BLE_APP_PRESENT) 
/// Default Device Name

/// Advertising state machine
enum app_mesh_adv_state
{
    /// Advertising activity does not exists
    APP_MESH_ADV_STATE_IDLE = 0,
    /// Creating advertising activity
    APP_MESH_ADV_STATE_CREATING,
    /// Setting advertising data
    APP_MESH_ADV_STATE_SETTING_ADV_DATA,
     /// Updata adv data
    APP_MESH_ADV_STATE_UPDATA_ADV_DATA,
    /// Advertising activity created
    APP_MESH_ADV_STATE_CREATED,
    /// Starting advertising activity
    APP_MESH_ADV_STATE_STARTING,
    /// Advertising activity started
    APP_MESH_ADV_STATE_STARTED,
    /// Stopping advertising activity
    APP_MESH_ADV_STATE_STOPPING,
    APP_MESH_ADV_STATE_DELETE,

};
/**
 ****************************************************************************************
 * @brief
 ****************************************************************************************
 */
void appm_mesh_adv_fsm_next(void);

/**
 ****************************************************************************************
 * @brief Send to request to update the adv data parameters
 ****************************************************************************************
 */
uint8_t appm_mesh_updata_adv_data(uint16_t length, uint8_t *p_data);

/**
 ****************************************************************************************
 * @brief Start/stop advertising
 *
 * @param[in] start     True if advertising has to be started, else false
 ****************************************************************************************
 */
void appm_mesh_update_adv_state(bool start);

/**
 ****************************************************************************************
 * @brief delete advertising
 *
 * @param[in] none
 ****************************************************************************************
 */

void appm_mesh_delete_advertising(void);
bool app_mesh_gapm_adv_check_data_sanity(uint16_t length, uint8_t *p_data);
void appm_mesh_adv_fsm_next(void);
 
#endif //

#endif //


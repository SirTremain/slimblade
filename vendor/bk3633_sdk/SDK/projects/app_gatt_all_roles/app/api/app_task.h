/**
 ****************************************************************************************
 *
 * @file app_task.h
 *
 * @brief Header file - APPTASK.
 *
 * Copyright (C) RivieraWaves 2009-2015
 *
 *
 ****************************************************************************************
 */

#ifndef APP_TASK_H_
#define APP_TASK_H_

/**
 ****************************************************************************************
 * @addtogroup APPTASK Task
 * @ingroup APP
 * @brief Routes ALL messages to/from APP block.
 *
 * The APPTASK is the block responsible for bridging the final application with the
 * RWBLE software host stack. It communicates with the different modules of the BLE host,
 * i.e. @ref SMP, @ref GAP and @ref GATT.
 *
 * @{
 ****************************************************************************************
 */

/*
 * INCLUDE FILES
 ****************************************************************************************
 */

#include "rwip_config.h"             // SW configuration

#if (BLE_APP_PRESENT)

#include <stdint.h>         // Standard Integer
#include "rwip_task.h"      // Task definitions
#include "ke_task.h"        // Kernel Task

/*
 * DEFINES
 ****************************************************************************************
 */

/// Number of APP Task Instances
#define APP_IDX_MAX                 (BLE_CONNECTION_MAX)

/*
 * ENUMERATIONS
 ****************************************************************************************
 */
enum appc_state
{
    APPC_LINK_IDLE,
    
    APPC_CREATE_DB = 1, // 1
    
    APPC_LINK_CONNECTED,

    APPC_SDP_DISCOVERING, 

    APPC_SERVICE_CONNECTED,
    /// Number of defined states.
    APPC_STATE_MAX
    
};
/// States of APP task
enum appm_state
{

       /// Initialization state
    APPM_INIT = 0, // 0
    /// Database create state
    APPM_CREATE_DB = 1, // 1

};

/// APP Task messages
/*@TRACE*/
enum app_msg_id
{
    APPM_DUMMY_MSG = TASK_FIRST_MSG(TASK_ID_APP),

    #if (BLE_APP_HT)
    /// Timer used to refresh the temperature measurement value
    APP_HT_MEAS_INTV_TIMER,
    #endif //(BLE_APP_HT)

    #if (BLE_APP_HID)
    /// Timer used to disconnect the moue if no activity is detecter
    APP_HID_MOUSE_TIMEOUT_TIMER,
    #endif //(BLE_APP_HID)
	
	APP_PARAM_UPDATE_REQ_IND,

	APP_SEND_SECURITY_REQ,
	
	APP_ANCS_REQ_IND,
	
	APP_PERIOD_TIMER,	
	
	APP_GATTC_EXC_MTU_CMD,

	APP_GATTC_SDP_TIMER,
	
	APP_START_SMP_REQ_TIMER,
	
	APP_START_ENCRYPT_TIMER,
	
	APP_START_SCAN_TIMER,
};


/*
 * GLOBAL VARIABLE DECLARATIONS
 ****************************************************************************************
 */

/// @} APPTASK

#endif //(BLE_APP_PRESENT)

#endif // APP_TASK_H_

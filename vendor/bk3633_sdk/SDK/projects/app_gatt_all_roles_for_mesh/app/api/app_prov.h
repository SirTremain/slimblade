/**
 ****************************************************************************************
 *
 * @file app_oads.h
 *
 * @brief OAD Application Module entry point
 *
 * @auth  gang.cheng
 *
 * @date  2016.10.13
 *
 * Copyright (C) Beken 2009-2016
 *
 *
 ****************************************************************************************
 */
#ifndef APP_PROV_H_
#define APP_PROV_H_
/**
 ****************************************************************************************
 * @addtogroup APP
 * @ingroup BEKEN
 *
 * @brief OADS Application Module entry point
 *
 * @{
 ****************************************************************************************
 */
/*
 * INCLUDE FILES
 ****************************************************************************************
 */

#include "rwip_config.h"     // SW configuration


#include <stdint.h>          // Standard Integer Definition
#include "ke_task.h"         // Kernel Task Definition
#include "prov.h"
/*
 * STRUCTURES DEFINITION
 ****************************************************************************************
 */
 

/// bracess Application Module Environment Structure
struct app_prov_env_tag
{
    /// Connection handle
    uint8_t conidx;
	
};
/*
 * GLOBAL VARIABLES DECLARATIONS
 ****************************************************************************************
 */

/// fff0s Application environment
extern struct app_prov_env_tag app_prov_env;

/// Table of message handlers
extern const struct app_subtask_handlers app_prov_handler;
/*
 * FUNCTIONS DECLARATION
 ****************************************************************************************
 */

/**
 ****************************************************************************************
 *
 * braces Application Functions
 *
 ****************************************************************************************
 */

/**
 ****************************************************************************************
 * @brief Initialize braces Application Module
 ****************************************************************************************
 */
void app_prov_init(void);
/**
 ****************************************************************************************
 * @brief Add a oad Service instance in the DB
 ****************************************************************************************
 */
void app_prov_add_prov(void);

/**
 ****************************************************************************************
 * @brief Enable the oad Service
 ****************************************************************************************
 */
void app_prov_enable_prf(uint8_t conidx);
/**
 ****************************************************************************************
 * @brief Send a step_info
 ****************************************************************************************
 */
 
 /*********************************************************************
 * LOCAL FUNCTIONS
 */



#endif // APP_OADS_H_

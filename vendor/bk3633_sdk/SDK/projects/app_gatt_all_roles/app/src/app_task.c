/**
 ****************************************************************************************
 *
 * @file appm_task.c
 *
 * @brief RW APP Task implementation
 *
 * Copyright (C) RivieraWaves 2009-2015
 *
 *
 ****************************************************************************************
 */

/**
 ****************************************************************************************
 * @addtogroup APPTASK
 * @{
 ****************************************************************************************
 */

/*
 * INCLUDE FILES
 ****************************************************************************************
 */

#include "rwip_config.h"          // SW configuration


#if (BLE_APP_PRESENT)

#include "rwapp_config.h"
#include "app_task.h"             // Application Manager Task API
#include "app.h"                  // Application Manager Definition
#include "gapc_task.h"            // GAP Controller Task API
#include "gapm_task.h"            // GAP Manager Task API
#include "arch.h"                 // Platform Definitions
#include <string.h>
#include "co_utils.h"
#include "ke_timer.h"             // Kernel timer
#include "app.h"  
#include "app_scan.h"  
#include "app_adv.h"
#include "app_sec.h"
#include "app_mesh_adv.h"
#include "app_init.h"
#include "gap.h"
#if (BLE_APP_FEE0S)
#include "app_fee0.h"              //  Module Definition
#endif //(BLE_APP_FEE0S)

#if (BLE_APP_FCC0S)
#include "app_fcc0.h"              //  Module Definition
#endif //(BLE_APP_FCC0S)

#if (BLE_APP_OADS)
#include "app_oads.h"             
#include "oads_task.h"   
#endif 

#if (BLE_APP_ANCS)
#include "app_ancsc.h"
#include "ancsc_task.h"
#endif 

#if (BLE_APP_SEC)
#include "app_sec.h"              // Security Module Definition
#endif //(BLE_APP_SEC)

#if (BLE_APP_HT)
#include "app_ht.h"               // Health Thermometer Module Definition
#include "htpt_task.h"
#endif //(BLE_APP_HT)

#if (BLE_APP_DIS)
#include "app_dis.h"              // Device Information Module Definition
#include "diss_task.h"
#endif //(BLE_APP_DIS)

#if (BLE_APP_BATT)
#include "app_batt.h"             // Battery Module Definition
#include "bass_task.h"
#endif //(BLE_APP_BATT)

#if (BLE_APP_HID)
#include "app_hid.h"              // HID Module Definition
#include "hogpd_task.h"
#endif //(BLE_APP_HID)

#if (BLE_APP_AM0)
#include "app_am0.h"             // Audio Mode 0 Application
#endif //(BLE_APP_AM0)

#if (DISPLAY_SUPPORT)
#include "app_display.h"          // Application Display Definition
#endif //(DISPLAY_SUPPORT)
#include "user_config.h" 
#include "mesh_sec.h" 
/*
 * LOCAL FUNCTION DEFINITIONS
 ****************************************************************************************
 */

static uint8_t app_get_handler(const struct app_subtask_handlers *handler_list_desc,
                               ke_msg_id_t msgid,
                               void *param,
                               ke_task_id_t src_id)
{
    // Counter
    uint8_t counter;

    // Get the message handler function by parsing the message table
    for (counter = handler_list_desc->msg_cnt; 0 < counter; counter--)
    {
        struct ke_msg_handler handler
                = (struct ke_msg_handler)(*(handler_list_desc->p_msg_handler_tab + counter - 1));

        if ((handler.id == msgid) ||
            (handler.id == KE_MSG_DEFAULT_HANDLER))
        {
            // If handler is NULL, message should not have been received in this state
            ASSERT_ERR(handler.func);

            return (uint8_t)(handler.func(msgid, param, TASK_APP, src_id));
        }
    }

    // If we are here no handler has been found, drop the message
    return (KE_MSG_CONSUMED);
}

/*
 * MESSAGE HANDLERS
 ****************************************************************************************
 */

/**
 ****************************************************************************************
 * @brief Handles GAPM_ACTIVITY_CREATED_IND event
 *
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance.
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gapm_activity_created_ind_handler(ke_msg_id_t const msgid,
                                             struct gapm_activity_created_ind const *p_param,
                                             ke_task_id_t const dest_id,
                                             ke_task_id_t const src_id)
{
    uart_printf("%s, p_param->actv_type=%x,p_param->actv_idx=%x\r\n",__func__,p_param->actv_type,p_param->actv_idx);
    if ((app_env.adv_state == APP_ADV_STATE_CREATING) && (p_param->actv_type == GAPM_ACTV_TYPE_ADV) && (p_param->actv_idx==0) )
    {
        // Store the advertising activity index
        app_env.adv_actv_idx = p_param->actv_idx;
        
    }

    if ((app_env.mesh_adv_state == APP_MESH_ADV_STATE_CREATING) && (p_param->actv_type == GAPM_ACTV_TYPE_ADV) && (p_param->actv_idx!=0) )
    {
        // Store the advertising activity index
        app_env.mesh_adv_actv_idx = p_param->actv_idx;
        
    }

    if((app_env.scan_state == APP_SCAN_STATE_CREATING) && (p_param->actv_type == GAPM_ACTV_TYPE_SCAN))
    {
        // Store the scaning activity index
        app_env.scan_actv_idx = p_param->actv_idx;
        app_env.scan_state = APP_SCAN_STATE_CREATED;
    }   
    else if((app_env.init_state == APP_INIT_STATE_CREATING) && (p_param->actv_type == GAPM_ACTV_TYPE_INIT))
    {
        // Store the scaning activity index
        app_env.init_actv_idx = p_param->actv_idx;
        app_env.init_state = APP_INIT_STATE_CREATED;
        
    }

    return (KE_MSG_CONSUMED);
}

/**
 ****************************************************************************************
 * @brief Handles GAPM_ACTIVITY_STOPPED_IND event.
 *
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance.
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gapm_activity_stopped_ind_handler(ke_msg_id_t const msgid,
                                             struct gapm_activity_stopped_ind const *p_param,
                                             ke_task_id_t const dest_id,
                                             ke_task_id_t const src_id)
{
    uart_printf("%s,reason:%x,actv_idx=%x\r\n",__func__,p_param->reason,p_param->actv_idx);
   
    if ((app_env.adv_state == APP_ADV_STATE_STARTED) &&(app_env.adv_actv_idx==p_param->actv_idx))
    {
        // Act as if activity had been stopped by the application
        // Perform next operation
        // Go created state
        app_env.adv_state = APP_ADV_STATE_CREATED;        
        

    }
    else if ((app_env.mesh_adv_state == APP_MESH_ADV_STATE_STARTED)&&(app_env.mesh_adv_actv_idx==p_param->actv_idx))
    {
        uint8_t mesh_adv_data[21]={0x14,0x2B,0x00,0xA8,0x01,0x71,0x33,0x02,0x00,0x00,0x1B,0xD7,0xBC,0x07,0xDA,0x78,0x00,0x00,0x00,0x00,0x00};
        static uint8_t mesh_adv_data_cnt=0;
        mesh_adv_data[18]=mesh_adv_data_cnt++;
        // Act as if activity had been stopped by the application
        app_env.mesh_adv_state = APP_MESH_ADV_STATE_STOPPING;

        // Perform next operation
        appm_mesh_adv_fsm_next();

        appm_mesh_updata_adv_data(21,mesh_adv_data);

    }
    else if((app_env.scan_state == APP_SCAN_STATE_STARTED) && (p_param->actv_type == GAPM_ACTV_TYPE_SCAN))
    {        
        // Act as if activity had been stopped by the application
        app_env.scan_state = APP_SCAN_STATE_STOPPING;
        // Perform next operation
        appm_scan_fsm_next();        
    }
    else if((app_env.init_state == APP_INIT_STATE_CONECTED) && (p_param->actv_type == GAPM_ACTV_TYPE_INIT))
    {     
        {
            // Act as if activity had been stopped by the application
            app_env.init_state = APP_INIT_STATE_STOPPING;

            // Perform next operation
            appm_init_fsm_next();
        }      
    }

    return (KE_MSG_CONSUMED);
}

/**
 ****************************************************************************************
 * @brief Handles GAPM_PROFILE_ADDED_IND event
 *
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance.
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gapm_profile_added_ind_handler(ke_msg_id_t const msgid,
                                          struct gapm_profile_added_ind *param,
                                          ke_task_id_t const dest_id,
                                          ke_task_id_t const src_id)
{ 
    // Current State
    ke_state_t state = ke_state_get(dest_id);
    uart_printf("%s prf_task_id:%d,prf_task_nb:%d,start_hdl:%d\r\n",__func__,param->prf_task_id, param->prf_task_nb,param->start_hdl);
    if (state == APPM_CREATE_DB)
    {
        switch (param->prf_task_id)
        {
            #if (BLE_APP_AM0)
            case (TASK_ID_AM0_HAS):
            {
                app_am0_set_prf_task(param->prf_task_nb);
            } break;
            #endif //(BLE_APP_AM0)

            default: /* Nothing to do */ break;
        }
    }
    else
    {
        ASSERT_INFO(0, state, src_id);
    }

    return KE_MSG_CONSUMED;
}

/**
 ****************************************************************************************
 * @brief Handles GAP manager command complete events.
 *
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance (TASK_GAP).
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gapm_cmp_evt_handler(ke_msg_id_t const msgid,
                                struct gapm_cmp_evt const *param,
                                ke_task_id_t const dest_id,
                                ke_task_id_t const src_id)
{
    #if (NVDS_SUPPORT)
    uint8_t key_len = KEY_LEN;
    #endif //(NVDS_SUPPORT)
    uart_printf("%s operation:%x,status:%x\r\n",__func__,param->operation,param->status);
    uart_printf("app_env.adv_state=%x,app_env.mesh_adv_state=%x\n",app_env.adv_state,app_env.mesh_adv_state);
    switch(param->operation)
    {
        // Reset completed
        case (GAPM_RESET)://0
        {

            if(param->status == GAP_ERR_NO_ERROR)
            {
                #if (NVDS_SUPPORT)
                nvds_tag_len_t len;
                #endif //(NVDS_SUPPORT)
                #if (BLE_APP_HID)
                app_hid_start_mouse();
                #endif //(BLE_APP_HID)

                // Set Device configuration
                struct gapm_set_dev_config_cmd* cmd = KE_MSG_ALLOC(GAPM_SET_DEV_CONFIG_CMD,
                                                                   TASK_GAPM, TASK_APP,
                                                                   gapm_set_dev_config_cmd);
                // Set the operation
                cmd->operation = GAPM_SET_DEV_CONFIG;
                // Set the device role - Peripheral / central
                cmd->role      = GAP_ROLE_ALL;//GAP_ROLE_PERIPHERAL;
                
                #if (BLE_APP_SEC_CON)
                // The Max MTU is increased to support the Public Key exchange
                // HOWEVER, with secure connections enabled you cannot sniff the 
                // LEAP and LEAS protocols
                cmd->max_mtu = 160;
                cmd->pairing_mode = GAPM_PAIRING_SEC_CON | GAPM_PAIRING_LEGACY;
                #else // !(BLE_APP_SEC_CON)
                // Do not support secure connections
                cmd->pairing_mode = GAPM_PAIRING_LEGACY;
                #endif //(BLE_APP_SEC_CON)
                
                // Set Data length parameters
                cmd->sugg_max_tx_octets = LE_MAX_OCTETS;//LE_MIN_OCTETS;//LE_MAX_OCTETS;
                cmd->sugg_max_tx_time   = LE_MAX_TIME;//LE_MIN_TIME;//LE_MAX_TIME;
                
                cmd->max_mtu = 527;//ATT_DEFAULT_MTU;
               
                #if (BLE_APP_HID)
                // Enable Slave Preferred Connection Parameters present 
                cmd->att_cfg = GAPM_MASK_ATT_SLV_PREF_CON_PAR_EN;
                #endif //(BLE_APP_HID)

                // Host privacy enabled by default
                cmd->privacy_cfg = 0;
                

                #if (NVDS_SUPPORT)
                if (nvds_get(NVDS_TAG_BD_ADDRESS, &len, &cmd->addr.addr[0]) == NVDS_OK)
                {
                    // Check if address is a static random address
                    if (cmd->addr.addr[5] & 0xC0)
                    {
                        // Host privacy enabled by default
                        cmd->privacy_cfg |= GAPM_PRIV_CFG_PRIV_ADDR_BIT;
                    }
                }
                else
                {
                    memcpy(&cmd->addr.addr[0],&co_default_bdaddr.addr[0],BD_ADDR_LEN);
                    if (cmd->addr.addr[5] & 0xC0)
                    {
                        // Host privacy enabled by default
                        cmd->privacy_cfg |= GAPM_PRIV_CFG_PRIV_ADDR_BIT;
                    }
                }
                #endif //(NVDS_SUPPORT)

                #if (BLE_APP_AM0)
                cmd->audio_cfg   = GAPM_MASK_AUDIO_AM0_SUP;
                #endif //(BLE_APP_AM0)


                #if (NVDS_SUPPORT)
                if ((app_sec_get_bond_status()==true) &&
                    (nvds_get(NVDS_TAG_LOC_IRK, &key_len, app_env.loc_irk) == NVDS_OK))
                {
                    memcpy(cmd->irk.key, app_env.loc_irk, 16);
                }
                else
                #endif //(NVDS_SUPPORT)
                {
                    memset((void *)&cmd->irk.key[0], 0x00, KEY_LEN);
                }
                // Send message
                ke_msg_send(cmd);
            }
            else
            {
                ASSERT_ERR(0);
            }
            
        }
        break;

        case (GAPM_PROFILE_TASK_ADD)://0x1b
        {          
            // Add the next requested service
            if (!appm_add_svc())
            {
                // Go to the ready state
                //ke_state_set(KE_BUILD_ID(TASK_APP,conidx), APPM_READY);
                #if (BLE_PERIPHERAL) 
                // No more service to add, create advertising                
                if(app_env.adv_state==APP_ADV_STATE_IDLE)
                {
                    // appm_adv_fsm_next();
                    appm_create_advertising();
                }
                #endif
                
                #if (BLE_OBSERVER || BLE_CENTRAL)
                // No more service to add, start scaning
               // appm_update_scan_state(true);
                #endif
                
                #if (BLE_CENTRAL)
              //  appm_update_init_state(true);
                #endif

                //ke_timer_set(APP_PERIOD_TIMER,TASK_APP,50); 
            }
            
        }
        break;

        case (GAPM_GEN_RAND_NB) ://0x1a
        {
            if (app_env.rand_cnt == 1)
            {
                // Generate a second random number
                app_env.rand_cnt++;
                struct gapm_gen_rand_nb_cmd *cmd = KE_MSG_ALLOC(GAPM_GEN_RAND_NB_CMD,
                                                                TASK_GAPM, TASK_APP,
                                                                gapm_gen_rand_nb_cmd);
                cmd->operation = GAPM_GEN_RAND_NB;
                ke_msg_send(cmd);
            }
            else
            {
                struct gapm_set_irk_cmd *cmd = KE_MSG_ALLOC(GAPM_SET_IRK_CMD,
                                                        TASK_GAPM, TASK_APP,
                                                        gapm_set_irk_cmd);
                app_env.rand_cnt=0;
                ///  - GAPM_SET_IRK
                cmd->operation = GAPM_SET_IRK;
                memcpy(&cmd->irk.key[0], &app_env.loc_irk[0], KEY_LEN);
                ke_msg_send(cmd);
            }
        }
        break;

        case (GAPM_SET_IRK):
        {
            // ASSERT_INFO(param->status == GAP_ERR_NO_ERROR, param->operation, param->status);

            #if (BLE_APP_SEC)
            // If not Bonded already store the generated value in NVDS
            if (app_sec_get_bond_status()==false)
            {
                if (nvds_get(NVDS_TAG_LOC_IRK, &key_len, app_env.loc_irk) != NVDS_OK)
                {               
                    if (nvds_put(NVDS_TAG_LOC_IRK, KEY_LEN, (uint8_t *)&app_env.loc_irk) != NVDS_OK)
                    {
                        ASSERT_INFO(0, 0, 0);
                    }
                }
            }
            #endif //(BLE_APP_SEC)
            app_env.rand_cnt = 0;
             
            // Go to the create db state
            ke_state_set(TASK_APP, APPC_CREATE_DB);

            // Add the first required service in the database
            // and wait for the PROFILE_ADDED_IND
            appm_add_svc();
                   
        }
        break;

        // Device Configuration updated
        case (GAPM_SET_DEV_CONFIG):
        {
            ASSERT_INFO(param->status == GAP_ERR_NO_ERROR, param->operation, param->status);

            #if (BLE_APP_SEC)
            if (app_sec_get_bond_status()==true) 
            {
                #if (NVDS_SUPPORT)
                // If Bonded retrieve the local IRK from NVDS
                if (nvds_get(NVDS_TAG_LOC_IRK, &key_len, app_env.loc_irk) == NVDS_OK)
                {
                    // Set the IRK in the GAP
                    struct gapm_set_irk_cmd *cmd = KE_MSG_ALLOC(GAPM_SET_IRK_CMD,
                                                                TASK_GAPM, TASK_APP,
                                                                gapm_set_irk_cmd);
                    ///  - GAPM_SET_IRK: 
                    cmd->operation = GAPM_SET_IRK;
                    memcpy(&cmd->irk.key[0], &app_env.loc_irk[0], KEY_LEN);
                    ke_msg_send(cmd);
                }
                else
                #endif //(NVDS_SUPPORT)
               
                {
                     // If cannot read IRK from NVDS ASSERT
                     ASSERT_ERR(0);
                }
            }
            else // Need to start the generation of new IRK
            #endif //(BLE_APP_SEC)
            {
                struct gapm_gen_rand_nb_cmd *cmd = KE_MSG_ALLOC(GAPM_GEN_RAND_NB_CMD,
                                                                TASK_GAPM, TASK_APP,
                                                                gapm_gen_rand_nb_cmd);
                cmd->operation   = GAPM_GEN_RAND_NB;
                app_env.rand_cnt = 1;
                ke_msg_send(cmd);
            }
           
        }
        break;
    #if (BLE_OBSERVER || BLE_CENTRAL)
        case (GAPM_CREATE_SCAN_ACTIVITY)://0xA1           
        {
            #if (BLE_OBSERVER || BLE_CENTRAL)
             if(param->status == GAP_ERR_NO_ERROR)
             {
                 appm_scan_fsm_next();
             }           
            #endif
        }break;
    #endif
        
    #if (BLE_CENTRAL )
        case (GAPM_CREATE_INIT_ACTIVITY)://0xA2
        {
            if(param->status == GAP_ERR_NO_ERROR)
            {
                 //appm_init_fsm_next();
            }
        }break;
    #endif
     
        case (GAPM_CREATE_ADV_ACTIVITY)://0xA0  
        {
            if(param->status == GAP_ERR_NO_ERROR)
            {
                if(app_env.adv_state == APP_ADV_STATE_CREATING)
                {
                    // appm_adv_fsm_next(); 
                     appm_set_adv_data();                    
                }
                   
                else if(app_env.mesh_adv_state == APP_ADV_STATE_CREATING)
                    appm_mesh_adv_fsm_next();  
            }
        }break;
        case (GAPM_SET_ADV_DATA)://0xA9
        {
            if(param->status == GAP_ERR_NO_ERROR)
            {
                if(app_env.adv_state == APP_ADV_STATE_SETTING_ADV_DATA)
                {
           
                    appm_set_scan_rsp_data();
                }
                    
                else if(app_env.mesh_adv_state == APP_MESH_ADV_STATE_SETTING_ADV_DATA)
                    appm_mesh_adv_fsm_next();
                else if(app_env.mesh_adv_state == APP_MESH_ADV_STATE_UPDATA_ADV_DATA)
                { 
                    app_env.mesh_adv_state = APP_MESH_ADV_STATE_CREATED;
                    appm_mesh_adv_fsm_next();     
                }   
                
            }
        }break;
        case (GAPM_SET_SCAN_RSP_DATA)://0xAA
        {
            // Sanity checks
            ASSERT_INFO(app_env.adv_op == param->operation, app_env.adv_op, param->operation);
            ASSERT_INFO(param->status == GAP_ERR_NO_ERROR, param->status, app_env.adv_op);
            // Perform next operation
            if(param->status == GAP_ERR_NO_ERROR)
            {
                if(app_env.adv_state == APP_ADV_STATE_SETTING_SCAN_RSP_DATA)
                {
                
                    // Start advertising activity
                    appm_start_advertising();
                }
            }  
  
        } break;
       
        case (GAPM_START_ACTIVITY)://0xA4
        {
            if(param->status == GAP_ERR_NO_ERROR)
            {
                if(app_env.adv_state == APP_ADV_STATE_STARTING)
                {
           
                    // Go to started state
                    app_env.adv_state = APP_ADV_STATE_STARTED;
                   
                }
                if(app_env.mesh_adv_state == APP_MESH_ADV_STATE_STARTING)
                {
                    appm_mesh_adv_fsm_next(); 
                }
                #if (BLE_OBSERVER || BLE_CENTRAL)
                if(app_env.scan_state == APP_SCAN_STATE_STARTING)
                {
                    appm_scan_fsm_next(); 
                }
                if(app_env.init_state == APP_INIT_STATE_CONECTTING)
                {
                    appm_init_fsm_next(); 
                }
                #endif   
            }
            
        }break;
        case (GAPM_STOP_ACTIVITY)://0xA5
        {
            if(param->status == GAP_ERR_NO_ERROR)
            {
                if(app_env.adv_state == APP_ADV_STATE_STOPPING)
                {
       
                    // Go created state
                    app_env.adv_state = APP_ADV_STATE_CREATED;
                }
                if(app_env.mesh_adv_state == APP_MESH_ADV_STATE_STOPPING)
                {
                    appm_mesh_adv_fsm_next(); 
                }
                #if (BLE_OBSERVER || BLE_CENTRAL)
                if(app_env.scan_state == APP_SCAN_STATE_STOPPING)
                {
                    appm_scan_fsm_next(); 
                    app_env.init_state = APP_INIT_STATE_CREATED;
                    appm_init_fsm_next();
                }
                #endif
            }
        }break;
        case (GAPM_DELETE_ACTIVITY)://0xA7
        {
            if(app_env.adv_state == APP_ADV_STATE_DELETE)
            {
                app_env.adv_state = APP_ADV_STATE_IDLE;
            }
            else if(app_env.mesh_adv_state == APP_MESH_ADV_STATE_DELETE)
            {
                app_env.mesh_adv_state = APP_MESH_ADV_STATE_IDLE;
            }
                
        }break;
        

        case (GAPM_DELETE_ALL_ACTIVITIES) :
        {
            // Re-Invoke activty
            app_env.adv_state = APP_ADV_STATE_IDLE;
            app_env.mesh_adv_state = APP_MESH_ADV_STATE_IDLE;
            #if (BLE_OBSERVER || BLE_CENTRAL )
            app_env.scan_state = APP_SCAN_STATE_IDLE;
            #endif
            
            #if (BLE_CENTRAL)
            app_env.init_state = APP_INIT_STATE_IDLE;
            #endif            

        } break;


        default:
        {
            // Drop the message
        }
        break;
    }
    
    return (KE_MSG_CONSUMED);
}

static int gapc_get_dev_info_req_ind_handler(ke_msg_id_t const msgid,
        struct gapc_get_dev_info_req_ind const *param,
        ke_task_id_t const dest_id,
        ke_task_id_t const src_id)
{
    switch(param->req)
    {
        case GAPC_DEV_NAME:
        {
            struct gapc_get_dev_info_cfm * cfm = KE_MSG_ALLOC_DYN(GAPC_GET_DEV_INFO_CFM,
                                                    src_id, dest_id,
                                                    gapc_get_dev_info_cfm, APP_DEVICE_NAME_MAX_LEN);
            cfm->req = param->req;
            cfm->info.name.length = appm_get_dev_name(cfm->info.name.value);

            // Send message
            ke_msg_send(cfm);
        } break;

        case GAPC_DEV_APPEARANCE:
        {
            // Allocate message
            struct gapc_get_dev_info_cfm *cfm = KE_MSG_ALLOC(GAPC_GET_DEV_INFO_CFM,
                                                             src_id, dest_id,
                                                             gapc_get_dev_info_cfm);
            cfm->req = param->req;
            // Set the device appearance
            #if (BLE_APP_HT)
            // Generic Thermometer - TODO: Use a flag
            cfm->info.appearance = 728;
            #elif (BLE_APP_HID)
            // HID Mouse
            cfm->info.appearance = 962;
            #else
            // No appearance
            cfm->info.appearance = 0;
            #endif

            // Send message
            ke_msg_send(cfm);
        } break;

        case GAPC_DEV_SLV_PREF_PARAMS:
        {
            // Allocate message
            struct gapc_get_dev_info_cfm *cfm = KE_MSG_ALLOC(GAPC_GET_DEV_INFO_CFM,
                    src_id, dest_id,
                                                            gapc_get_dev_info_cfm);
            cfm->req = param->req;
            // Slave preferred Connection interval Min
            cfm->info.slv_pref_params.con_intv_min = BLE_UAPDATA_MIN_INTVALUE;
            // Slave preferred Connection interval Max
            cfm->info.slv_pref_params.con_intv_max = BLE_UAPDATA_MAX_INTVALUE;
            // Slave preferred Connection latency
            cfm->info.slv_pref_params.slave_latency  = BLE_UAPDATA_LATENCY;
            // Slave preferred Link supervision timeout
            cfm->info.slv_pref_params.conn_timeout    = BLE_UAPDATA_TIMEOUT;  // 2s (500*10ms)

            // Send message
            ke_msg_send(cfm);
        } break;

        default: /* Do Nothing */ break;
    }


    return (KE_MSG_CONSUMED);
}
/**
 ****************************************************************************************
 * @brief Handles GAPC_SET_DEV_INFO_REQ_IND message.
 *
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance (TASK_GAP).
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gapc_set_dev_info_req_ind_handler(ke_msg_id_t const msgid,
        struct gapc_set_dev_info_req_ind const *param,
        ke_task_id_t const dest_id,
        ke_task_id_t const src_id)
{
    // Set Device configuration
    struct gapc_set_dev_info_cfm* cfm = KE_MSG_ALLOC(GAPC_SET_DEV_INFO_CFM, src_id, dest_id,
                                                     gapc_set_dev_info_cfm);
    // Reject to change parameters
    cfm->status = GAP_ERR_REJECTED;
    cfm->req = param->req;
    // Send message
    ke_msg_send(cfm);

    return (KE_MSG_CONSUMED);
}

/**
 ****************************************************************************************
 * @brief Handles connection complete event from the GAP. Enable all required profiles
 *
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance (TASK_GAP).
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gapc_connection_req_ind_handler(ke_msg_id_t const msgid,
                                           struct gapc_connection_req_ind const *param,
                                           ke_task_id_t const dest_id,
                                           ke_task_id_t const src_id)
{
    app_env.conidx = KE_IDX_GET(src_id);
    uart_printf("%s \r\n",__func__);
    
    // Check if the received Connection Handle was valid
    if (app_env.conidx != GAP_INVALID_CONIDX)
    {
        // Retrieve the connection info from the parameters
        app_env.conhdl = param->conhdl;
        
        /// Connection handle
        uart_printf("conhdl:%d \r\n",param->conhdl);
        uart_printf("con_interval:%d \r\n",param->con_interval);
        uart_printf("con_latency:%d \r\n",param->con_latency );
        uart_printf("sup_to:%d \r\n",param->sup_to  );
        uart_printf("peer_addr_type:%d \r\n",param->peer_addr_type);
        {
            uart_printf("peer_addr:0x");
            for(uint8_t i = 0;i < GAP_BD_ADDR_LEN;i++)
            {
                uart_printf("%02x",param->peer_addr.addr[i]);
            }uart_printf("\r\n");
        }
        uart_printf("role:%s \r\n",param->role ? "Slave" : "Master");
        
        // Send connection confirmation
        struct gapc_connection_cfm *cfm = KE_MSG_ALLOC(GAPC_CONNECTION_CFM,
                KE_BUILD_ID(TASK_GAPC, app_env.conidx), KE_BUILD_ID(TASK_APP,app_env.conidx),
                gapc_connection_cfm);

        #if(BLE_APP_SEC)
        cfm->auth      = app_sec_get_bond_status() ? GAP_AUTH_REQ_NO_MITM_BOND : GAP_AUTH_REQ_NO_MITM_NO_BOND; 
        #else 
        cfm->auth      = GAP_AUTH_REQ_NO_MITM_NO_BOND;
        #endif 
        // Send the message
        ke_msg_send(cfm);

        // We are now in connected State
        ke_state_set(KE_BUILD_ID(TASK_APP,app_env.conidx), APPC_LINK_CONNECTED);
        
        /*--------------------------------------------------------------
         * ENABLE REQUIRED PROFILES
         *--------------------------------------------------------------*/
        if(param->role==ROLE_SLAVE)
        {
            #if (BLE_APP_BATT)
            // Enable Battery Service
            app_batt_enable_prf(app_env.conidx);
            #endif //(BLE_APP_BATT)

            #if (BLE_APP_HID)
            // Enable HID Service
            app_hid_enable_prf(app_env.conhdl);
            #endif //(BLE_APP_HID)
            ke_timer_set(APP_PARAM_UPDATE_REQ_IND,TASK_APP,250);
            app_sec_env.bonded = false;
    		app_sec_env.peer_pairing = false;
    		app_sec_env.peer_encrypt = false;
        }

        app_env.role[app_env.conidx]=param->role;
		
        ke_timer_set(APP_GATTC_EXC_MTU_CMD,TASK_APP,20);
		ke_timer_set(APP_GATTC_SDP_TIMER,TASK_APP,30);
        
       // ke_timer_set(APP_START_SCAN_TIMER,TASK_APP,500);
    }
    else
    {
        // No connection has been established, restart advertising
        //appm_update_adv_state(true);
        
        
    }

    return (KE_MSG_CONSUMED);
}

/**
 ****************************************************************************************
 * @brief Handles connection complete event from the GAP. Enable all required profiles
 *
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance (TASK_GAP).
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gapc_param_update_req_ind_handler(ke_msg_id_t const msgid,
                                           struct gapc_param_update_req_ind const *param,
                                           ke_task_id_t const dest_id,
                                           ke_task_id_t const src_id)
{
    app_env.conidx = KE_IDX_GET(src_id);
    uart_printf("gapc_param_update_req_ind_handler\n");

    // Check if the received Connection Handle was valid
    if (app_env.conidx != GAP_INVALID_CONIDX)
    {

        // Send connection confirmation
        struct gapc_param_update_cfm *cfm = KE_MSG_ALLOC(GAPC_PARAM_UPDATE_CFM,
                KE_BUILD_ID(TASK_GAPC, app_env.conidx), TASK_APP,
                gapc_param_update_cfm);

        cfm->accept = true;
        cfm->ce_len_min = 2;
        cfm->ce_len_max = 4;

        // Send message
        ke_msg_send(cfm);

    }
    else
    {
        // No connection has been established, restart advertising
        appm_start_advertising();
    }

    return (KE_MSG_CONSUMED);
}

static int gattc_cmp_evt_handler(ke_msg_id_t const msgid,  struct gattc_cmp_evt const *param,
                                 ke_task_id_t const dest_id, ke_task_id_t const src_id)
{
    uart_printf("appc %s ,dest_id:%x,src_id:%x,operation = 0x%x,status = 0x%x,param->seq_num = 0x%x\r\n",__func__,dest_id,src_id,param->operation,param->status,param->seq_num);

    uint8_t find;  
    uint8_t conidx = KE_IDX_GET(src_id);
    switch(param->operation)
    {
        case GATTC_MTU_EXCH:
        {      
            uart_printf("GATTC_MTU_EXCH\r\n");
                       
        }
        break;
        
        case GATTC_WRITE:
        {
    		uart_printf("GATTC_WRITE stu:0x%x\r\n",param->status);
            if(param->seq_num == 0xaa)
            {      
        		find = sdp_enable_all_server_ntf_ind(app_env.conidx,0);
        		
        	    ke_state_set(KE_BUILD_ID(TASK_APP,app_env.conidx), APPC_SERVICE_CONNECTED);
        		
        		uart_printf("find2= %d\r\n",find);
        		
            }            
        }
        break;
        
        case GATTC_SDP_DISC_SVC:
        {
            if(param->status == ATT_ERR_NO_ERROR)
            {        
                uart_printf("GATTC_SDP_DISC_SVC !!!role %d \r\n",gapc_get_role(conidx));
                
                ke_state_set(KE_BUILD_ID(TASK_APP,app_env.conidx), APPC_SERVICE_CONNECTED);
    					          
            }
        }
        break;
    	case GATTC_SDP_DISC_SVC_ALL:
        {
            if(param->status == ATT_ERR_NO_ERROR)
            {
    			ke_state_set(KE_BUILD_ID(TASK_APP,app_env.conidx), APPC_SERVICE_CONNECTED);
                
                find =sdp_enable_all_server_ntf_ind(app_env.conidx,1);
                
    			uart_printf("all service discovered !!!=%x\r\n",find);
            }

        }
        break;
        case GATTC_REGISTER:
        {
            uart_printf("GATTC_REGISTER !!!\r\n");
            if(gapc_get_role(conidx) == ROLE_SLAVE)
            {
                
            }
            else
            {
                ke_state_set(KE_BUILD_ID(TASK_APP,app_env.conidx), APPC_SERVICE_CONNECTED); 
                ke_timer_set(APP_PERIOD_TIMER,TASK_APP,2000);
            }				
        }
        break;
        
        case GATTC_UNREGISTER:
        {
            uart_printf("GATTC_UNREGISTER !!!\r\n");
                   
        }
        break;
        case GATTC_WRITE_NO_RESPONSE:
        {

            
        }
        break;
    }
    return (KE_MSG_CONSUMED);
}



/**
 ****************************************************************************************
 * @brief Handles GAP controller command complete events.
 *
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance (TASK_GAP).
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gapc_cmp_evt_handler(ke_msg_id_t const msgid,
                                struct gapc_cmp_evt const *param,
                                ke_task_id_t const dest_id,
                                ke_task_id_t const src_id)
{
   
	uart_printf("gapc_cmp_evt_handler operation = %x\r\n",param->operation);
//	uint8_t conidx = KE_IDX_GET(dest_id);
	switch(param->operation)
	{
    	case (GAPC_UPDATE_PARAMS):  //0x09
    	{
			if (param->status != GAP_ERR_NO_ERROR)
        	{
            	uart_printf("gapc update params fail !\r\n");
			}
			else
			{
				uart_printf("gapc update params ok !\r\n");
			}
			
    	} break;
		case (GAPC_DISCONNECT): //0x01
		{
			if(param->status == GAP_ERR_NO_ERROR)
			{
				uart_printf("pairing_fail = 0x%x\r\n",app_sec_env.pairing_fail);
				//bonding info lost and pairing fail
				if(app_sec_env.pairing_fail)
				{
					app_sec_env.pairing_fail = false;
					
					uart_printf("restart advertising\r\n");
					
					//ke_state_set(TASK_APP, APPM_READY);
					//restart advertising
					//appm_start_advertising();
				}
			}
		}break;
		case (GAPC_SECURITY_REQ): //0x0c
		{
			if (param->status != GAP_ERR_NO_ERROR)
	        {
	            uart_printf("gapc security req fail !\r\n");
	        }
	        else
	        {
	            uart_printf("gapc security req ok !\r\n");
	        }
		}break;
		
        case (GAPC_BOND):
    	{
    		if (param->status != GAP_ERR_NO_ERROR)
    		{
    			uart_printf("gapc bond fail\r\n");
    		}
    		else
    		{
    			uart_printf("gapc bond ok\r\n");
                ke_state_set(KE_BUILD_ID(TASK_APP,app_env.conidx), APPC_SDP_DISCOVERING);
              	sdp_discover_all_service(app_env.conidx); 
              	
    		}
    	}
    	break;

    	case (GAPC_ENCRYPT):
    	{
    		if (param->status != GAP_ERR_NO_ERROR)
    		{
    			uart_printf("gapc encrypt fail\r\n");
    		}
    		else
    		{
    			uart_printf("gapc encrypt ok,app_env.conidx=%x,%x\r\n",app_env.conidx,sdp_env_init.used_status[0]);
                
                if(sdp_env_init.used_status[0] == FREE_STATUS)
                {
                    ke_state_set(KE_BUILD_ID(TASK_APP,app_env.conidx), APPC_SDP_DISCOVERING);
                    sdp_discover_all_service(app_env.conidx);
                }
                else
                {
                    sdp_prf_register_all_atthdl2gatt(app_env.conidx);
                    
                }
                
                
    		}
    	}
    	break;
    		

        	default:
        	  break;
    }

    return (KE_MSG_CONSUMED);
}

/**
 ****************************************************************************************
 * @brief Handles disconnection complete event from the GAP.
 *
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance (TASK_GAP).
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gapc_disconnect_ind_handler(ke_msg_id_t const msgid,
                                      struct gapc_disconnect_ind const *param,
                                      ke_task_id_t const dest_id,
                                      ke_task_id_t const src_id)
{
    
    uint8_t conidx = KE_IDX_GET(dest_id);
    uart_printf("gapc_disconnect_ind_handler,reason=%x\n",param->reason);
    // Go to the ready state
    ke_state_set(KE_BUILD_ID(TASK_APP, conidx), APPC_LINK_IDLE);

    #if (BLE_APP_HT)
    // Stop interval timer
    app_stop_timer();
    #endif //(BLE_APP_HT)

    #if (DISPLAY_SUPPORT)
    // Update Connection State screen
    app_display_set_con(false);
    #endif //(DISPLAY_SUPPORT)

    #if (BLE_ISO_MODE_0_PROTOCOL)
    app_env.adv_state = APP_ADV_STATE_CREATING;
    #endif //(BLE_ISO_MODE_0_PROTOCOL)

    #if (!BLE_APP_HID)
    // Restart Advertising
    appm_start_advertising();
    #endif //(!BLE_APP_HID)

    // Go to the ready state
	if( app_env.scan_state == APP_SCAN_STATE_CREATED ) 
    {   
        ke_timer_set(APP_START_SCAN_TIMER,TASK_APP,20);
    }
    
    if(app_env.role[conidx]==ROLE_MASTER)
        app_env.init_state = APP_INIT_STATE_CREATED;

    return (KE_MSG_CONSUMED);
}

/**
 ****************************************************************************************
 * @brief Handles reception of all messages sent from the lower layers to the application
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int appm_msg_handler(ke_msg_id_t const msgid,
                            void *param,
                            ke_task_id_t const dest_id,
                            ke_task_id_t const src_id)
{
    // Retrieve identifier of the task from received message
    ke_task_id_t src_task_id = MSG_T(msgid);
    // Message policy
    uint8_t msg_pol = KE_MSG_CONSUMED;

    switch (src_task_id)
    {
        case (TASK_ID_GAPC):
        {
            #if (BLE_APP_SEC)
            if ((msgid >= GAPC_BOND_CMD) &&
                (msgid <= GAPC_SECURITY_IND))
            {
                // Call the Security Module
                msg_pol = app_get_handler(&app_sec_handlers, msgid, param, src_id);
            }
            #endif //(BLE_APP_SEC)
            // else drop the message
        } break;

        case (TASK_ID_GATTC):
        {
            // Service Changed - Drop
        } break;

        #if (BLE_APP_FEE0S)
        case (TASK_ID_FEE0S):
        {
            // Call the app fee0s Module
            msg_pol = app_get_handler(&app_fee0_handler, msgid, param, src_id);
        } break;
        #endif //(BLE_APP_FEE0S)
        
        #if (BLE_APP_FCC0S)
        case (TASK_ID_FCC0S):
        {
            // Call the app fee0s Module
            msg_pol = app_get_handler(&app_fcc0_handler, msgid, param, src_id);
        } break;
        #endif //(BLE_APP_FCC0S)
        
        #if (BLE_APP_HT)
        case (TASK_ID_HTPT):
        {
            // Call the Health Thermometer Module
            msg_pol = app_get_handler(&app_ht_handlers, msgid, param, src_id);
        } break;
        #endif //(BLE_APP_HT)

        #if (BLE_APP_DIS)
        case (TASK_ID_DISS):
        {
            // Call the Device Information Module
            msg_pol = app_get_handler(&app_dis_handlers, msgid, param, src_id);
        } break;
        #endif //(BLE_APP_DIS)

        #if (BLE_APP_HID)
        case (TASK_ID_HOGPD):
        {
            // Call the HID Module
            msg_pol = app_get_handler(&app_hid_handlers, msgid, param, src_id);
        } break;
        #endif //(BLE_APP_HID)

        #if (BLE_APP_BATT)
        case (TASK_ID_BASS):
        {
            // Call the Battery Module
            msg_pol = app_get_handler(&app_batt_handlers, msgid, param, src_id);
        } break;
        #endif //(BLE_APP_BATT)

        #if (BLE_APP_AM0)
        case (TASK_ID_AM0):
        {
            // Call the Audio Mode 0 Module
            msg_pol = app_get_handler(&app_am0_handlers, msgid, param, src_id);
        } break;

        case (TASK_ID_AM0_HAS):
        {
            // Call the Audio Mode 0 Module
            msg_pol = app_get_handler(&app_am0_has_handlers, msgid, param, src_id);
        } break;
        #endif //(BLE_APP_AM0)
        #if(BLE_APP_ANCS)
        case (TASK_ID_ANCSC):
        {
            // Call the Health Thermometer Module
            msg_pol = app_get_handler(&app_ancsc_handler, msgid, param, src_id);
        } break;
        #endif
        #if(BLE_APP_OADS)
        case (TASK_ID_OADS):
        {
            // Call the Health Thermometer Module
            msg_pol = app_get_handler(&app_oads_handler, msgid, param, src_id);
        } break;
        #endif
        default:
        {
            #if (BLE_APP_HT)
            if (msgid == APP_HT_MEAS_INTV_TIMER)
            {
                msg_pol = app_get_handler(&app_ht_handlers, msgid, param, src_id);
            }
            #endif //(BLE_APP_HT)

            #if (BLE_APP_HID)
            if (msgid == APP_HID_MOUSE_TIMEOUT_TIMER)
            {
                msg_pol = app_get_handler(&app_hid_handlers, msgid, param, src_id);
            }
            #endif //(BLE_APP_HID)
        } break;
    }

    return (msg_pol);
}

/**
 ****************************************************************************************
 * @brief Handles reception of random number generated message
 *
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gapm_gen_rand_nb_ind_handler(ke_msg_id_t const msgid, struct gapm_gen_rand_nb_ind *param,
                                        ke_task_id_t const dest_id, ke_task_id_t const src_id)
{
    if (app_env.rand_cnt==1)      // First part of IRK
    {
        memcpy(&app_env.loc_irk[0], &param->randnb.nb[0], 8);
    }
    else if (app_env.rand_cnt==2) // Second part of IRK
    {
        memcpy(&app_env.loc_irk[8], &param->randnb.nb[0], 8);
    }

    return KE_MSG_CONSUMED;
}

/**
 ****************************************************************************************
 * @brief  GAPC_PARAM_UPDATED_IND
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gapc_param_updated_ind_handler (ke_msg_id_t const msgid, 
										const struct gapc_param_updated_ind  *param,
                 						ke_task_id_t const dest_id, 
                 						ke_task_id_t const src_id)
{
    uart_printf("%s \r\n", __func__);
	uart_printf("con_interval = %d\r\n",param->con_interval);
	uart_printf("con_latency = %d\r\n",param->con_latency);
	uart_printf("sup_to = %d\r\n",param->sup_to);
	
	return KE_MSG_CONSUMED;
}

#if (BLE_OBSERVER || BLE_CENTRAL )

static int gapm_ext_adv_report_ind_handler(ke_msg_id_t const msgid, struct gapm_ext_adv_report_ind *param,
                                        ke_task_id_t const dest_id, ke_task_id_t const src_id)
{
    uint8_t con_dev_str_name1[] ="Surface Mobile Mouse";
    //uint8_t con_dev_str_name2[] ="BK3435RC";
    uint8_t con_dev_str_name2[] ="RAPOO BT4.0 Mouse";
    //uint8_t con_dev_str_name2[] ="Surface Mobile Mouse";		//Microsoft Bluetooth Mouse
    uint8_t find1 = 0 ;
	uint8_t find2 = 0;
    uint8_t length = NVDS_LEN_LTK2;
    
/*
    uart_printf("%s\r\n",__func__);
    uart_printf("actv_idx:%x\r\n",param->actv_idx);
    uart_printf("info:%x\r\n",param->info);
    uart_printf("ch:%d\r\n",param->channel_idx);
    uart_printf("rssi:%d\r\n",param->rssi);
    uart_printf("addr_type:%x\r\n",param->trans_addr.addr_type);
    uart_printf("addr");
    for(int i = 0;i < 6;i++)
    {
        uart_printf(":%02x",param->trans_addr.addr.addr[i]);
    }uart_printf("\r\n");
    
    uart_printf("data len:%d\r\n",param->length);
    
    uart_printf("data");
    for(int i = 0;i < param->length;i++)
    {
        uart_printf(":%02x",param->data[i]);
    }uart_printf("\r\n");
*/            
    if(app_env.scan_state != APP_SCAN_STATE_STARTED)
        return 0;
    
    app_sec_env.bond_state=0;
    for(uint8_t index=0;index<BLE_CONNECTION_MAX;index++)
    {
        if (nvds_get(NVDS_TAG_LTK2+index, &length,app_sec_env.ltk_buff) == NVDS_OK)  
    	{
            struct gap_bdaddr  bond_addr;
    	    memcpy(bond_addr.addr.addr,app_sec_env.ltk_buff,6);
            
    		if(memcmp(bond_addr.addr.addr,param->trans_addr.addr.addr,6) == 0)
        	{
    	    	memcpy(&con_bdaddr,&param->trans_addr,sizeof(struct gap_bdaddr));
                appm_set_connect_dev_addr(param->trans_addr);
                appm_scan_fsm_next();
                
        		
                app_sec_env.bond_state=1;
    			uart_printf("!!~ltk_buff=%x,%x,%x,%x,%x,%x\r\n",app_sec_env.ltk_buff[0],app_sec_env.ltk_buff[1],app_sec_env.ltk_buff[2],app_sec_env.ltk_buff[3],app_sec_env.ltk_buff[4],app_sec_env.ltk_buff[5]);
                return KE_MSG_CONSUMED;
        	}          
    	}       
    }        
    find1 = appm_adv_data_decode(param->length, param->data,con_dev_str_name1,sizeof(con_dev_str_name1)-1,param->trans_addr);
    find2 = appm_adv_data_decode(param->length, param->data,con_dev_str_name2,sizeof(con_dev_str_name2)-1,param->trans_addr);
    
    if(find1 == 1 || find2 == 1)
	{
        uart_printf("app_sec_env.bond_device=%x\n",app_sec_env.bond_device);
	    
	    memcpy(&con_bdaddr,&param->trans_addr,sizeof(struct gap_bdaddr));
        appm_set_connect_dev_addr(param->trans_addr);
        appm_scan_fsm_next();
        


	}   
    return KE_MSG_CONSUMED;
}
#endif
#if (BLE_SDP_CLIENT)
uint16_t user_uuid = 0xfee0;
static int gattc_sdp_svc_ind_handler(ke_msg_id_t const msgid,
                                     struct gattc_sdp_svc_ind const *ind,
                                     ke_task_id_t const dest_id,
                                     ke_task_id_t const src_id)
{
    uint8_t conidx = KE_IDX_GET(src_id);
    uart_printf("appc %s msgid:0x%x,dest_id:0x%x,src_id:0x%x\r\n",__func__,msgid,dest_id,src_id);
   // struct prf_sdp_db_env *prf_db_env = NULL;
     
    uart_printf("ind uuid len:%d,uuid:",ind->uuid_len);
    for(int i = 0;i < ind->uuid_len;i++)
    {
        uart_printf("%02x ",ind->uuid[ind->uuid_len - i - 1]);
    }
    uart_printf(" \r\n");

    //app_add_sdp_fee0_srv(conidx,2,ind);
    sdp_extract_svc_info(conidx,ind);
   
   
    return (KE_MSG_CONSUMED);
}
static int app_gattc_event_ind_handler(ke_msg_id_t const msgid,
                                   struct gattc_event_ind const *param,
                                   ke_task_id_t const dest_id,
                                   ke_task_id_t const src_id)
{
    uint8_t state = ke_state_get(dest_id);
    uint8_t conidx = KE_IDX_GET(src_id);
    uart_printf("gattc_event_ind conidx:%d\r\n",conidx);
    uart_printf("NOTIF RECIVE length:%d,value = \r\n",param->length);
    for(int i = 0; i< param->length; i++)
    {
        uart_printf("%02x ",param->value[i]);
    }uart_printf("\r\n");

   return (KE_MSG_CONSUMED);  
}

static int app_gattc_event_req_ind_handler(ke_msg_id_t const msgid,
                                       struct gattc_event_ind const *param,
                                       ke_task_id_t const dest_id,
                                       ke_task_id_t const src_id)
{
    uint8_t state = ke_state_get(dest_id);

    uart_printf("RECIVE value =  \r\n");
    for(int i = 0; i< param->length; i++)
    {
        uart_printf("%02x ",param->value[i]);
    }
    uart_printf("\r\n");
   return (KE_MSG_CONSUMED);  
}
#endif

/**
 ****************************************************************************************
 * @brief  GATTC_MTU_CHANGED_IND
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gattc_mtu_changed_ind_handler(ke_msg_id_t const msgid,
                                     struct gattc_mtu_changed_ind const *ind,
                                     ke_task_id_t const dest_id,
                                     ke_task_id_t const src_id)
{
	uart_printf("%s \r\n",__func__);
	uart_printf("ind->mtu = %d,seq = %d\r\n",ind->mtu,ind->seq_num);
	ke_timer_clear(APP_GATTC_EXC_MTU_CMD,TASK_APP);
 	return (KE_MSG_CONSUMED);
}
static int gapm_scan_request_ind_handler(ke_msg_id_t const msgid,
                                 struct gapm_scan_request_ind const *p_ind,
                                 ke_task_id_t const dest_id,
                                 ke_task_id_t const src_id)
{
    uart_printf("%s\r\n",__func__);
    uart_printf("actv_idx:%d,addr_type:%d\r\n",p_ind->actv_idx,p_ind->trans_addr.addr_type);
    uart_printf("addr ");
    for(int i = 0;i < 6;i++)
    {
        uart_printf(":%02x ",p_ind->trans_addr.addr.addr[i]);
    }uart_printf("\r\n");
    return (KE_MSG_CONSUMED);  
}


/*******************************************************************************
 * Function: gapc_update_conn_param_req_ind_handler
 * Description: Update request command processing from slaver connection parameters
 * Input: msgid   -Id of the message received.
 *		  param   -Pointer to the parameters of the message.
 *		  dest_id -ID of the receiving task instance
 *		  src_id  -ID of the sending task instance.
 * Return: If the message was consumed or not.
 * Others: void
*******************************************************************************/
static int app_update_conn_param_req_ind_handler (ke_msg_id_t const msgid, 
									const struct gapc_param_update_req_ind  *param,
                 					ke_task_id_t const dest_id, 
                 					ke_task_id_t const src_id)
{

	uart_printf("slave send param_update_req\r\n");
	struct gapc_conn_param  up_param;
	
	up_param.intv_min   = BLE_UAPDATA_MIN_INTVALUE;
	up_param.intv_max   = BLE_UAPDATA_MAX_INTVALUE; 
	up_param.latency    = BLE_UAPDATA_LATENCY;  
	up_param.time_out   = BLE_UAPDATA_TIMEOUT; 
	
	appm_update_param(&up_param);
	
	return KE_MSG_CONSUMED;
}

/**
 ****************************************************************************************
 * @brief  APP_SEND_SECURITY_REQ
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int app_send_security_req_handler(ke_msg_id_t const msgid, 
										void const *param,
        								ke_task_id_t const dest_id, 
        								ke_task_id_t const src_id)
{   
	app_sec_send_security_req(app_env.conidx);
    
    return KE_MSG_CONSUMED;
}

static int app_ancs_req_handler(ke_msg_id_t const msgid, void const *param,
        ke_task_id_t const dest_id, ke_task_id_t const src_id)
{
    #if (BLE_APP_ANCS)
    app_ancsc_enable_prf(app_env.conhdl);
    #endif
    return KE_MSG_CONSUMED;
}
/*******************************************************************************
 * Function: app_period_timer_handler
 * Description: app period timer process
 * Input: msgid -Id of the message received.
 *		  param -Pointer to the parameters of the message.
 *		  dest_id -ID of the receiving task instance (TASK_GAP).
 *		  ID of the sending task instance.
 * Return: If the message was consumed or not.
 * Others: void
*******************************************************************************/
static int app_period_timer_handler(ke_msg_id_t const msgid,
                                          void *param,
                                          ke_task_id_t const dest_id,
                                          ke_task_id_t const src_id)
{
#if 0
    static uint8_t cnt=0;
    cnt++;
  
    if(cnt%2==0)
        mesh_ccm_cipher_test();
    else
        mesh_ccm_decipher_test();

    ke_timer_set(APP_PERIOD_TIMER,TASK_APP,200);         
//#else
    gapc_mesh_send_get_pub_key_cmd(0);        
#endif

    return KE_MSG_CONSUMED;
}

/** 
*******************************************************************************

 * @brief  GATTC_EXC_MTU_CMD
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 
*******************************************************************************
**/
static int app_mtu_exchange_req_handler(ke_msg_id_t const msgid,
                                        struct gattc_exc_mtu_cmd const *req,
                                        ke_task_id_t const dest_id,
                                        ke_task_id_t const src_id)
{
	uart_printf("%s \r\n", __func__);
	struct gattc_exc_mtu_cmd *cmd = KE_MSG_ALLOC(GATTC_EXC_MTU_CMD,
	                                KE_BUILD_ID(TASK_GATTC, app_env.conidx),
	                                TASK_APP,gattc_exc_mtu_cmd);
	cmd->operation = GATTC_MTU_EXCH;
	cmd->seq_num = 0;
	ke_msg_send(cmd);

	return (KE_MSG_CONSUMED);
}

static int app_gattc_sdp_timer_handler(ke_msg_id_t const msgid,
                                        struct gattc_exc_mtu_cmd const *req,
                                        ke_task_id_t const dest_id,
                                        ke_task_id_t const src_id)
{
			uart_printf("%s \r\n", __func__);
			
	     //  ke_timer_set(APP_PERIOD_TIMER,TASK_APP,2000);
					
		//	return (KE_MSG_CONSUMED);
			
 			if(app_env.role[app_env.conidx]==ROLE_MASTER)
            {  
                if( app_sec_env.bond_device || app_sec_env.bond_state ) 
                {
                    
                    if(app_sec_env.bond_state==0)
                    {
                        sdp_service_status_reset();
                        ke_timer_set(APP_START_SMP_REQ_TIMER, TASK_APP,5);			
                    }
                    else
                    {	
                        ke_timer_set(APP_START_ENCRYPT_TIMER,TASK_APP,5);
                    }
                }
                else 
                {
                    sdp_service_status_reset();
                    ke_state_set(KE_BUILD_ID(TASK_APP,app_env.conidx), APPC_SDP_DISCOVERING);
                    sdp_discover_all_service(app_env.conidx);
                } 
            }
			return (KE_MSG_CONSUMED);
}


/**
 ****************************************************************************************
 * @brief Handles GAPM_PUB_KEY_IND message received from HL.
 *
 * @param[in] msg_id    Id of the message received.
 * @param[in] p_param   Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance.
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gapm_mesh_pub_key_ind_handler(ke_msg_id_t const msg_id, struct gapm_pub_key_ind *p_param,
                             ke_task_id_t const dest_id, ke_task_id_t const src_id)
{
    uart_printf("pub_key_x: ");
    for(uint8_t i=0;i<32;i++)
        uart_printf("0x%02x,",p_param->pub_key_x[i]);
    uart_printf("\n");

    
    uart_printf("pub_key_y: ");
    for(uint8_t i=0;i<32;i++)
        uart_printf("0x%02x,",p_param->pub_key_y[i]);
    uart_printf("\n");

    gapc_mesh_send_gen_dh_key_cmd(0,p_param->pub_key_x,p_param->pub_key_y);

    return (KE_MSG_CONSUMED);
}

/**
 ****************************************************************************************
 * @brief Handles GAPM_GEN_DH_KEY_IND message received from HL.
 *
 * @param[in] msg_id    Id of the message received.
 * @param[in] p_param   Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance.
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int gapm_mesh_gen_dh_key_ind_handler(ke_msg_id_t const msg_id, struct gapm_gen_dh_key_ind *p_param,
                                ke_task_id_t const dest_id, ke_task_id_t const src_id)

{

    uart_printf("result: ");
    for(uint8_t i=0;i<32;i++)
        uart_printf("0x%02x,",p_param->result[i]);
    uart_printf("\n");
    return (KE_MSG_CONSUMED);
}


static int app_start_smpc_handler(ke_msg_id_t const msgid,void *param,
                                    ke_task_id_t const dest_id,ke_task_id_t const src_id)

{
	uart_printf("%s\r\n", __func__);
	
	app_sec_bond_cmd_req();
	
	return KE_MSG_CONSUMED;	
}


static int app_start_encrypt_handler(ke_msg_id_t const msgid,struct gapm_profile_added_ind *param,
                                    ke_task_id_t const dest_id,ke_task_id_t const src_id)
{
	uart_printf("%s\r\n", __func__);

	app_sec_encry_cmd_req();

		
	return (KE_MSG_CONSUMED);
}
static int app_start_scan_handler(ke_msg_id_t const msgid,struct gapm_profile_added_ind *param,
                                    ke_task_id_t const dest_id,ke_task_id_t const src_id)
{
	uart_printf("%s\r\n", __func__);

    if( app_env.scan_state == APP_SCAN_STATE_CREATED )
	    appm_scan_fsm_next();

	return (KE_MSG_CONSUMED);
}

/*
 * GLOBAL VARIABLES DEFINITION
 ****************************************************************************************
 */

/* Default State handlers definition. */
KE_MSG_HANDLER_TAB(appm)
{
    // Note: first message is latest message checked by kernel so default is put on top.
    {KE_MSG_DEFAULT_HANDLER,    (ke_msg_func_t)appm_msg_handler},

    // GAPM messages
    {GAPM_PROFILE_ADDED_IND,    (ke_msg_func_t)gapm_profile_added_ind_handler},
    {GAPM_ACTIVITY_CREATED_IND, (ke_msg_func_t)gapm_activity_created_ind_handler},
    {GAPM_ACTIVITY_STOPPED_IND, (ke_msg_func_t)gapm_activity_stopped_ind_handler},
    {GAPM_CMP_EVT,              (ke_msg_func_t)gapm_cmp_evt_handler},
    {GAPM_GEN_RAND_NB_IND,      (ke_msg_func_t)gapm_gen_rand_nb_ind_handler},
    #if (BLE_BROADCASTER)    
    {GAPM_SCAN_REQUEST_IND,      (ke_msg_func_t)gapm_scan_request_ind_handler},
    #endif
    
    #if (BLE_OBSERVER || BLE_CENTRAL )
    {GAPM_EXT_ADV_REPORT_IND,   (ke_msg_func_t)gapm_ext_adv_report_ind_handler},
    #endif 
    #if(BLE_MESH)
    {GAPM_MESH_PUB_KEY_IND,     (ke_msg_func_t)gapm_mesh_pub_key_ind_handler},
    {GAPM_MESH_GEN_DH_KEY_IND,  (ke_msg_func_t)gapm_mesh_gen_dh_key_ind_handler},
    #endif

    // GAPC messages
    {GAPC_GET_DEV_INFO_REQ_IND, (ke_msg_func_t)gapc_get_dev_info_req_ind_handler},
    {GAPC_SET_DEV_INFO_REQ_IND, (ke_msg_func_t)gapc_set_dev_info_req_ind_handler},
    {GAPC_CONNECTION_REQ_IND,   (ke_msg_func_t)gapc_connection_req_ind_handler},
    {GAPC_PARAM_UPDATE_REQ_IND, (ke_msg_func_t)gapc_param_update_req_ind_handler},
    {GAPC_CMP_EVT,              (ke_msg_func_t)gapc_cmp_evt_handler},
    {GAPC_DISCONNECT_IND,       (ke_msg_func_t)gapc_disconnect_ind_handler},
    {GAPC_PARAM_UPDATED_IND,	(ke_msg_func_t)gapc_param_updated_ind_handler}, 
    
    {GATTC_MTU_CHANGED_IND,		(ke_msg_func_t)gattc_mtu_changed_ind_handler},

     // GATTC messages
    #if (BLE_SDP_CLIENT)
    {GATTC_SDP_SVC_IND,         (ke_msg_func_t)gattc_sdp_svc_ind_handler},
    {GATTC_EVENT_IND,           (ke_msg_func_t)app_gattc_event_ind_handler},
    {GATTC_EVENT_REQ_IND,       (ke_msg_func_t)app_gattc_event_req_ind_handler},
    {GATTC_CMP_EVT,             (ke_msg_func_t)gattc_cmp_evt_handler},
    #endif
    
    {APP_PARAM_UPDATE_REQ_IND, 	(ke_msg_func_t)app_update_conn_param_req_ind_handler},
    {APP_SEND_SECURITY_REQ,     (ke_msg_func_t)app_send_security_req_handler},
    {APP_ANCS_REQ_IND,			(ke_msg_func_t)app_ancs_req_handler},
    {APP_PERIOD_TIMER,			(ke_msg_func_t)app_period_timer_handler},
    {APP_GATTC_EXC_MTU_CMD,		(ke_msg_func_t)app_mtu_exchange_req_handler},
    {APP_GATTC_SDP_TIMER,       (ke_msg_func_t)app_gattc_sdp_timer_handler},
    {APP_START_SMP_REQ_TIMER,   (ke_msg_func_t)app_start_smpc_handler},
    {APP_START_ENCRYPT_TIMER,   (ke_msg_func_t)app_start_encrypt_handler},
    {APP_START_SCAN_TIMER,      (ke_msg_func_t)app_start_scan_handler},    

    
};

/* Defines the place holder for the states of all the task instances. */
ke_state_t appm_state[APP_IDX_MAX];

// Application task descriptor
const struct ke_task_desc TASK_DESC_APP = {appm_msg_handler_tab, appm_state, APP_IDX_MAX, ARRAY_LEN(appm_msg_handler_tab)};

#endif //(BLE_APP_PRESENT)

/// @} APPTASK

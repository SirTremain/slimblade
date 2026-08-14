#include "rwip_config.h"             // SW configuration
#if (BLE_APP_PRESENT)
#include "ke_timer.h"
#include "app.h"
#include "app_task.h"                // Application task Definition
#include "app_init.h"                     // Application Definition
#include "gap.h"                     // GAP Definition
#include "gapm_task.h"               // GAP Manager Task API
#include "gapc_task.h"               // GAP Controller Task API
#include "gattc_task.h"
#include "co_bt.h"                   // Common BT Definition
#include "co_math.h"                 // Common Maths Definition
#include "sdp_service_task.h"
#include "sdp_service.h"
#include "prf_utils.h"
#include "uart.h"
#include "gpio.h"


/// Application Environment Structure
//struct useapp_env_tag useapp_env;
#if (BLE_CENTRAL)

/// Scan interval 
#define APP_CONN_SCAN_INTV         (10)
/// Scan window 
#define APP_CONN_SCAN_WD         (6)
/// Conn interval 
#define APP_CONN_INTV         (24) // 1.25MS
/// Conn window 
#define APP_CONN_LATENCY         (0)
#define APP_CONN_SUP_TO        (300) // 10MS

struct gap_bdaddr  con_bdaddr;
static struct gap_bdaddr g_bdaddr;

static void appm_create_init(void)
{
    uart_printf("func %s,init_state:%d\r\n",__func__,app_env.init_state);
    if (app_env.init_state == APP_INIT_STATE_IDLE)
    {
        // Prepare the GAPM_ACTIVITY_CREATE_CMD message
        struct gapm_activity_create_cmd *p_cmd = KE_MSG_ALLOC(GAPM_ACTIVITY_CREATE_CMD,
                                                                  TASK_GAPM, TASK_APP,
                                                                  gapm_activity_create_cmd);

        // Set operation code
        p_cmd->operation = GAPM_CREATE_INIT_ACTIVITY;

        // Fill the allocated kernel message
        p_cmd->own_addr_type = GAPM_STATIC_ADDR;
         
        // Send the message
        ke_msg_send(p_cmd);

        // Keep the current operation
        app_env.init_state = APP_INIT_STATE_CREATING;
        // And the next expected operation code for the command completed event
        app_env.init_op = GAPM_CREATE_INIT_ACTIVITY;
        app_env.conn_intv = APP_CONN_INTV;
        app_env.conn_latency = APP_CONN_LATENCY;
        app_env.conn_super_to = APP_CONN_SUP_TO;
        app_env.scan_intv = APP_CONN_SCAN_INTV;
        app_env.scan_wd = APP_CONN_SCAN_WD;
    }
}


void appm_set_connect_dev_addr(struct gap_bdaddr bdaddr)
{
    memcpy(&g_bdaddr,&bdaddr,sizeof(struct gap_bdaddr));
}

struct gap_bdaddr appm_get_connect_dev_addr(void)
{
    return g_bdaddr;
}

uint8_t appm_start_connecting(struct gap_bdaddr bdaddr)
{
    uart_printf("func %s,init_state:%d\r\n",__func__,app_env.init_state);
     
    uint8_t ret = APPM_ERROR_NO_ERROR;
    if (app_env.init_state == APP_INIT_STATE_CREATED)
    {
        // Prepare the GAPM_ACTIVITY_START_CMD message
        struct gapm_activity_start_cmd *p_cmd = KE_MSG_ALLOC(GAPM_ACTIVITY_START_CMD,
                                                             TASK_GAPM, TASK_APP,
                                                             gapm_activity_start_cmd);

        p_cmd->operation = GAPM_START_ACTIVITY;
        p_cmd->actv_idx = app_env.init_actv_idx;
        
        p_cmd->u_param.init_param.type = GAPM_INIT_TYPE_DIRECT_CONN_EST;        
        
        p_cmd->u_param.init_param.prop = GAPM_INIT_PROP_1M_BIT;
      
        p_cmd->u_param.init_param.conn_param_1m.ce_len_min = 2;
        p_cmd->u_param.init_param.conn_param_1m.ce_len_max = 4;  
       
        p_cmd->u_param.init_param.conn_param_1m.conn_intv_min = APP_CONN_INTV;
        p_cmd->u_param.init_param.conn_param_1m.conn_intv_max = APP_CONN_INTV;       
        p_cmd->u_param.init_param.conn_param_1m.conn_latency = APP_CONN_LATENCY;
        p_cmd->u_param.init_param.conn_param_1m.supervision_to = APP_CONN_SUP_TO;
        
        p_cmd->u_param.init_param.conn_to = 1000;
        
        p_cmd->u_param.init_param.peer_addr.addr_type = bdaddr.addr_type;
     
        memcpy(p_cmd->u_param.init_param.peer_addr.addr.addr,bdaddr.addr.addr,6);
        
        p_cmd->u_param.init_param.scan_param_1m.scan_intv = APP_CONN_SCAN_INTV;
        p_cmd->u_param.init_param.scan_param_1m.scan_wd = APP_CONN_SCAN_WD;
        // Send the message
        ke_msg_send(p_cmd);

        // Keep the current operation
        app_env.init_state = APP_INIT_STATE_CONECTTING;
        // And the next expected operation code for the command completed event
        app_env.init_op = GAPM_START_ACTIVITY;
    }
    return ret;
}

uint8_t appm_stop_connencting(void)
{
    uart_printf("func %s\r\n",__func__);
    uint8_t ret = APPM_ERROR_NO_ERROR;
    if (app_env.init_state == APP_INIT_STATE_CONECTTING)
    {
        // Prepare the GAPM_ACTIVITY_STOP_CMD message
        struct gapm_activity_stop_cmd *cmd = KE_MSG_ALLOC(GAPM_ACTIVITY_STOP_CMD,
                                                          TASK_GAPM, TASK_APP,
                                                          gapm_activity_stop_cmd);

        // Fill the allocated kernel message
        cmd->operation = GAPM_STOP_ACTIVITY;
        cmd->actv_idx = app_env.init_actv_idx;

        // Send the message
        ke_msg_send(cmd);

        // Update advertising state
        app_env.init_state = APP_INIT_STATE_STOPPING;       
        // And the next expected operation code for the command completed event
        app_env.adv_op = GAPM_STOP_ACTIVITY;
        //
    }else
    {
        ret = APPM_ERROR_STATE;
    }
    
    return ret;
}




//     bdaddr.addr.addr[0] = 0x0f;
//     bdaddr.addr.addr[1] = 0x43;
//     bdaddr.addr.addr[2] = 0x45;
//     bdaddr.addr.addr[3] = 0x67;
//     bdaddr.addr.addr[4] = 0x89;
//      bdaddr.addr.addr[5] = 0xAB;
void appm_init_fsm_next(void)
{
    
 //   return;
    uart_printf("%s init_state:%x\r\n",__func__,app_env.init_state);
    switch (app_env.init_state)
    {
        case (APP_INIT_STATE_IDLE):
        {
            // Create init
            appm_create_init();
        } break;

        case (APP_INIT_STATE_CREATING):
        {
            app_env.init_state = APP_INIT_STATE_CREATED;
        }break;
        case (APP_INIT_STATE_CREATED):       
        {   
            // Start init activity
            appm_start_connecting(g_bdaddr);
        } break;

        case (APP_INIT_STATE_CONECTTING):
        {
            // Go to started state
            app_env.init_state = APP_INIT_STATE_CONECTED;
        } break;

        case (APP_INIT_STATE_CONECTED):
        {
            // Stop connencting activity         
        } break;

        case (APP_INIT_STATE_STOPPING):
        {
            
            // Go created state
            app_env.init_state = APP_INIT_STATE_CREATED;
        } break;

        default:
        {
            ASSERT_ERR(0);
        } break;
    }
    uart_printf("end init_state:%x\r\n",app_env.init_state);
}


void appm_update_init_state(bool start)
{
    // TODO [LT] - Check current advertising state
    // Start or stop advertising
    if(app_env.init_state == APP_INIT_STATE_IDLE)
        appm_init_fsm_next();
}


uint8_t appc_write_service_data_req(uint8_t conidx,uint16_t handle,uint16_t data_len,uint8_t *data)
{
    uart_printf("func %s,state = %x,",__func__,ke_state_get(KE_BUILD_ID(TASK_APP,conidx)));
    uart_printf("conidx:%d,handle = 0x%04x\r\n",conidx,handle);
    uint8_t ret = APPM_ERROR_NO_ERROR;
    if((ke_state_get(KE_BUILD_ID(TASK_APP,conidx)) == APPC_SERVICE_CONNECTED))
    {   
        struct sdp_write_info_req *req = KE_MSG_ALLOC_DYN(SDP_WRITE_VALUE_INFO_REQ,
                                         prf_get_task_from_id(KE_BUILD_ID(TASK_ID_SDP,conidx)), KE_BUILD_ID(TASK_APP,conidx),
                                         sdp_write_info_req, data_len);
        // Fill in the parameter structure
        req->conidx = conidx;
        req->handle = handle;
        req->length = data_len;
        memcpy(req->data,data,data_len);
        uart_printf("dest = 0x%04x\r\n",prf_get_task_from_id(KE_BUILD_ID(TASK_ID_SDP,conidx)));
        uart_printf("data len:%d,",data_len);
        for(int i = 0;i<data_len;i++)
        {
            uart_printf("%02x ",data[i]);
        } uart_printf("\r\n");
        // Send the message
        ke_msg_send(req);
    }
    else
    {
        ret = APPM_ERROR_STATE;
        uart_printf("ke_state_get(TASK_APP) = %x\r\n",ke_state_get(KE_BUILD_ID(TASK_APP,conidx)));
    }
    
    return ret;
  
}

uint8_t appc_write_service_ntf_cfg_req(uint8_t conidx,uint16_t handle,uint16_t ntf_cfg,uint16_t seq_num)
{
    uart_printf("func %s\r\n,state = %x,",__func__,ke_state_get(KE_BUILD_ID(TASK_APP,conidx)));
    uart_printf("conidx:%d,handle = 0x%04x,ntf_cfg = 0x%x\r\n",conidx,handle,ntf_cfg);
    
    uint8_t ret = APPM_ERROR_NO_ERROR;
    if((ke_state_get(KE_BUILD_ID(TASK_APP,conidx)) != APPC_LINK_IDLE))
    {
        struct sdp_write_ntf_cfg_req *req = KE_MSG_ALLOC(SDP_WRITE_NTF_CFG_REQ,
                                        prf_get_task_from_id(KE_BUILD_ID(TASK_ID_SDP,conidx)), KE_BUILD_ID(TASK_APP,conidx),
                                        sdp_write_ntf_cfg_req);
        uart_printf("dest = 0x%04x\r\n",prf_get_task_from_id(KE_BUILD_ID(TASK_ID_SDP,conidx)));
        // Fill in the parameter structure
        req->conidx = conidx;
        req->handle = handle;
        req->ntf_cfg = ntf_cfg;
        req->seq_num = seq_num;
        // Send the message
        ke_msg_send(req);
    }
    else
    {
        ret = APPM_ERROR_STATE;
        uart_printf("ke_state_get(TASK_APPC) = %x\r\n",ke_state_get(KE_BUILD_ID(TASK_APP,conidx)));
    }
    
    return ret;
  
}
void appm_read_info_req(uint8_t conidx,uint16_t handle)
{
    uart_printf("%s\r\n",__func__);
    
    struct sdp_read_info_req *req = KE_MSG_ALLOC(SDP_READ_INFO_REQ,
                                    prf_get_task_from_id(KE_BUILD_ID(TASK_ID_SDP,conidx)), KE_BUILD_ID(TASK_APP,conidx),
                                    sdp_read_info_req);
    
    // Fill in the parameter structure
    req->conidx = conidx;
    req->handle = handle;
    req->type= 0;
    // Send the message
    ke_msg_send(req);

    
  
}
uint8_t appm_read_service_data_by_uuid_req(uint8_t conidx,uint8_t uuid_len,uint8_t* uuid)
{
    uart_printf("func %s\r\n",__func__);
    
    uint8_t ret = APPM_ERROR_NO_ERROR;
    if((ke_state_get(KE_BUILD_ID(TASK_APP,conidx)) == APPC_SERVICE_CONNECTED))
    {
        struct sdp_read_info_req *req = KE_MSG_ALLOC(SDP_READ_INFO_REQ,
                                        prf_get_task_from_id(TASK_ID_SDP), TASK_APP,
                                        sdp_read_info_req);
        // Fill in the parameter structure
        req->uuid_len = uuid_len;
        memcpy(req->uuid,uuid,uuid_len);
        
        req->info = SDPC_CHAR_VAL;       
        req->type = SDPC_OPERATE_UUID;
        // Send the message
        ke_msg_send(req);
    }
    else
    {
        ret = APPM_ERROR_STATE;
        uart_printf("ke_state_get(TASK_APP) = %x\r\n",ke_state_get(TASK_APP));
    }
    
    return ret;
 
}

uint8_t appm_read_service_data_by_handle_req(uint8_t conidx,uint16_t handle)
{
    uart_printf("func %s\r\n",__func__);
    
    uint8_t ret = APPM_ERROR_NO_ERROR;
    if((ke_state_get(KE_BUILD_ID(TASK_APP,conidx)) == APPC_SERVICE_CONNECTED))
    {
        struct sdp_read_info_req *req = KE_MSG_ALLOC(SDP_READ_INFO_REQ,
                                        prf_get_task_from_id(TASK_ID_SDP), TASK_APP,
                                        sdp_read_info_req);
        // Fill in the parameter structure
        req->handle = handle;       
        req->info = SDPC_CHAR_VAL;       
        req->type = SDPC_OPERATE_HANDLE;
        // Send the message
        ke_msg_send(req);
    }
    else
    {
        ret = APPM_ERROR_STATE;
        uart_printf("ke_state_get(TASK_APP) = %x\r\n",ke_state_get(TASK_APP));
    }    
    return ret;

}

uint8_t appm_read_service_ntf_ind_cfg_by_handle_req(uint8_t conidx,uint16_t handle)
{
    uart_printf("func %s\r\n",__func__);
    
    uint8_t ret = APPM_ERROR_NO_ERROR;
    if((ke_state_get(KE_BUILD_ID(TASK_APP,conidx)) == APPC_SERVICE_CONNECTED))
    {
        struct sdp_read_info_req *req = KE_MSG_ALLOC(SDP_READ_INFO_REQ,
                                        prf_get_task_from_id(TASK_ID_SDP), TASK_APP,
                                        sdp_read_info_req);
        // Fill in the parameter structure
        req->handle = handle; 
        req->info = SDPC_CHAR_NTF_CFG;
        req->type = SDPC_OPERATE_HANDLE;
        // Send the message
        ke_msg_send(req);
    }
    else
    {
        ret = APPM_ERROR_STATE;
        uart_printf("ke_state_get(TASK_APP) = %x\r\n",ke_state_get(TASK_APP));
    }
    return ret;

}

uint8_t appm_read_service_userDesc_by_handle_req(uint8_t conidx,uint16_t handle)
{
    uart_printf("func %s\r\n",__func__);
   
    uint8_t ret = APPM_ERROR_NO_ERROR;
    if((ke_state_get(KE_BUILD_ID(TASK_APP,conidx)) == APPC_SERVICE_CONNECTED))
    {
        struct sdp_read_info_req *req = KE_MSG_ALLOC(SDP_READ_INFO_REQ,
                                        prf_get_task_from_id(TASK_ID_SDP), TASK_APP,
                                        sdp_read_info_req);
        // Fill in the parameter structure
        req->handle = handle; 
        req->info = SDPC_CHAR_USER_DESC_VAL;
        req->type = SDPC_OPERATE_HANDLE;
        // Send the message
        ke_msg_send(req);
    }
    else
    {
        ret = APPM_ERROR_STATE;
        uart_printf("ke_state_get(TASK_APP) = %x\r\n",ke_state_get(TASK_APP));
    }    
    return ret;

}

#endif // (#if (BLE_CENTRAL || BLE_OBSERVER))
#endif  //#if (BLE_APP_PRESENT)


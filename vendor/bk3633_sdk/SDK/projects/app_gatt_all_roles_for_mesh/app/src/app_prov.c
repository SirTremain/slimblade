
/**
 ****************************************************************************************
 * @addtogroup APP
 * @{
 ****************************************************************************************
 */

#include "rwip_config.h"     // SW configuration


/*
 * INCLUDE FILES
 ****************************************************************************************
 */
#include <string.h>
#include "app_prov.h"                // Bracese Application Module Definitions
#include "app.h"                     // Application Definitions
#include "app_task.h"                // application task definitions
#include "prov.h"
#include "prov_task.h"               // health thermometer functions
#include "co_bt.h"
#include "co_utils.h"
#include "prf_types.h"               // Profile common types definition
#include "arch.h"                    // Platform Definitions
#include "prf.h"
#include "uart.h"


		
/*
 * LOCATION FUN DEFINES
 ****************************************************************************************
 */



/*
 * GLOBAL VARIABLE DEFINITIONS
 ****************************************************************************************
 */

/// braces Application Module Environment Structure
struct app_prov_env_tag app_prov_env;



/*
 * GLOBAL FUNCTION DEFINITIONS
 ****************************************************************************************
 */

void app_prov_init(void)
{

    // Reset the environment
    memset(&app_prov_env, 0, sizeof(struct app_prov_env_tag));
		
 
}

void app_prov_add_prov(void)
{

	uart_printf("app_oad_add_prov\r\n");
	struct prov_db_cfg *db_cfg;

	struct gapm_profile_task_add_cmd *req = KE_MSG_ALLOC_DYN(GAPM_PROFILE_TASK_ADD_CMD,
                                                  TASK_GAPM, TASK_APP,
                                                  gapm_profile_task_add_cmd, sizeof(struct prov_db_cfg));
    // Fill message
    req->operation = GAPM_PROFILE_TASK_ADD;
    req->sec_lvl = 0;//PERM(SVC_AUTH, ENABLE);
    req->prf_task_id = TASK_ID_PROV;
    req->app_task = TASK_APP;
    req->start_hdl = 0; //req->start_hdl = 0; dynamically allocated

	 
	  // Set parameters
    db_cfg = (struct prov_db_cfg* ) req->param;
	 
    // Sending of notifications is supported
    db_cfg->features = PROV_NTF_SUP;
		uart_printf("app_oad_add_prov d = %x,s = %x\r\n",TASK_GAPM,TASK_APP);
    // Send the message
    ke_msg_send(req);
}








/**
 ****************************************************************************************
 * @brief
 *
 * @param[in] msgid     Id of the message received.
 * @param[in] param     Pointer to the parameters of the message.
 * @param[in] dest_id   ID of the receiving task instance (TASK_GAP).
 * @param[in] src_id    ID of the sending task instance.
 *
 * @return If the message was consumed or not.
 ****************************************************************************************
 */
static int app_prov_msg_dflt_handler(ke_msg_id_t const msgid,
                                     void const *param,
                                     ke_task_id_t const dest_id,
                                     ke_task_id_t const src_id)
{
    // Drop the message
		uart_printf("%s\r\n",__func__);
		uart_printf("msgid = 0x%04x,destid = 0x%x,srcid = 0x%x\r\n",msgid,dest_id,src_id);
    return (KE_MSG_CONSUMED);
}


/*
 * LOCAL VARIABLE DEFINITIONS
 ****************************************************************************************
 */

/// Default State handlers definition
const struct ke_msg_handler app_prov_msg_handler_list[] =
{
	// Note: first message is latest message checked by kernel so default is put on top.
	{KE_MSG_DEFAULT_HANDLER,          (ke_msg_func_t)app_prov_msg_dflt_handler},


};

const struct app_subtask_handlers app_prov_handler = APP_HANDLERS(app_prov);    


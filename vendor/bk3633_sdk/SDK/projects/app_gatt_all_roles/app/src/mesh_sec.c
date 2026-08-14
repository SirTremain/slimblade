/**
 ****************************************************************************************
 *
 * @file mal_sec.c
 *
 * @brief Mesh Abstraction Layer Security Module
 *
 * Copyright (C) RivieraWaves 2017-2019
 *
 *
 ****************************************************************************************
 */

/**
 ****************************************************************************************
 * @addtogroup MAL_SEC
 * @{
 ****************************************************************************************
 */

/*
 * INCLUDE FILES
 ****************************************************************************************
 */
#include <string.h>
#include "ke_msg.h"        // Mesh Abstraction Layer Internal Definitions
#include "aes.h"        // AES Functions Definitions
#include "mesh_sec.h" 
#include "gapm_task.h"
#include "prf.h"

void mesh_sec_init(bool reset)
{
    aes_init(reset);
}
void mesh_sec_aes(const uint8_t *p_key, const uint8_t *p_val, mal_sec_aes_res_cb res_cb)
{
    uint32_t src_info=AES_INFO_ENCRYPT;
    // use AES encrypt function
    aes_encrypt(p_key, p_val, 0,(aes_func_result_cb) res_cb,src_info);
}

void mesh_sec_rand(mal_sec_aes_res_cb res_cb)
{
    uint32_t src_info=AES_INFO_RAND;
    // use AES rand function
    aes_rand((aes_func_result_cb) res_cb,src_info);
}

void mesh_sec_aes_cmac(const uint8_t *p_key, const uint8_t *p_message, uint16_t message_len, mal_sec_aes_res_cb res_cb)
{
    uint32_t src_info=AES_INFO_CMAC;
    // use AES CMAC function
    aes_cmac(p_key, p_message, message_len, (aes_func_result_cb) res_cb,src_info);
}

void mesh_sec_aes_s1(const uint8_t *p_message, uint8_t message_len, mal_sec_aes_res_cb res_cb)
{
    uint32_t src_info=AES_INFO_S1;
    // use AES S1 function
    aes_s1(p_message, message_len, (aes_func_result_cb) res_cb,src_info);
}

void mesh_sec_aes_k1(const uint8_t *p_salt, const uint8_t *p_n, uint8_t n_len, const uint8_t *p_p, uint8_t p_len,mal_sec_aes_res_cb res_cb)
{
    uint32_t src_info=AES_INFO_K1;
    // use AES K1 function
    aes_k1(p_salt, p_n, n_len, p_p, p_len, (aes_func_result_cb) res_cb,src_info);
}

void mesh_sec_aes_k2(const uint8_t *p_n, const uint8_t *p_p, uint8_t p_len, mal_sec_aes_res_cb res_cb)
{
    uint32_t src_info=AES_INFO_K2;
    // use AES K2 function
    aes_k2(p_n, p_p, p_len, (aes_func_result_cb) res_cb,src_info);
}

void mesh_sec_aes_k3(const uint8_t *p_n, mal_sec_aes_res_cb res_cb)
{
    uint32_t src_info=AES_INFO_K3;
    // use AES K3 function
    aes_k3(p_n, (aes_func_result_cb) res_cb,src_info);
}

void mesh_sec_aes_k4(const uint8_t *p_n, mal_sec_aes_res_cb res_cb)
{
    uint32_t src_info=AES_INFO_K4;
    // use AES K4 function
    aes_k4(p_n, (aes_func_result_cb) res_cb,src_info);
}

void mesh_sec_aes_ccm(const uint8_t *p_key, const uint8_t *p_nonce, const uint8_t *p_in_message,
                     uint8_t *p_out_message, uint16_t message_len, uint8_t mic_len, bool cipher,
                     const uint8_t *p_add_auth_data, uint8_t add_auth_data_len, mal_sec_aes_ccm_cb res_cb)
{
    uint32_t src_info;

    if(cipher)
    {
        src_info=AES_INFO_CCM_CIPHER;
    }
    else 
    {
        src_info=AES_INFO_CCM_DECIPHER;
    }
    // use AES CCM function
    aes_ccm(p_key, p_nonce, p_in_message, p_out_message, message_len, mic_len, cipher,
            p_add_auth_data, add_auth_data_len, (aes_ccm_func_result_cb) res_cb,src_info);
}

void mesh_sec_aes_cb(uint8_t status, uint8_t* result, uint32_t src_info)
{
    uart_printf("result: ");
    for(uint8_t i=0;i<16;i++)
        uart_printf("%x",result[i]);
    uart_printf("\n");
    
    switch(src_info)
    {
        case AES_INFO_ENCRYPT:
            break;
    	case AES_INFO_RAND:
            break;
    	case AES_INFO_CMAC:
            break;
    	case AES_INFO_S1:
            break;
    	case AES_INFO_K1:
            break;
    	case AES_INFO_K2:
            break;
    	case AES_INFO_K3:
            break;
    	case AES_INFO_K4:
            break;
    }
}


uint8_t key[16]={0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f,0x11};
uint8_t nonce[13]={0x11,0x12,0x13,0x14,0x15,0x16,0x17,0x18,0x19,0x1a,0x1b,0x1c,0x1d};
uint8_t in_message[20]={0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f,0x10,0x11,0x12,0x13,0x14};
uint8_t in_message_d[24]={0x7a,0x67,0xe1,0xd8,0xf6,0xce,0xcd,0xad,0x6b,0xa2,0x83,0x1e,0x8a,0x7d,0x42,0xdc,0x9a,0x50,0xbc,0xa1,0x2a,0x8f,0x28,0x87};///×îºó4BYTESÎªMIC
uint8_t out_message[24];
    
void mesh_sec_aes_ccm_cb (bool mic_error,uint32_t src_info)
{
    uart_printf("mic_error:%x \n",mic_error);
    
    uart_printf("out_message: ");
    
    for(uint8_t i=0;i<24;i++)
        uart_printf("0x%02x,",out_message[i]);
    
     uart_printf("\n");
}
void mesh_ccm_cipher_test(void)
{   
    uart_printf("cipher_test\n ");
    
    mesh_sec_aes_ccm(key,nonce,in_message,out_message,20,4,1,0,0,mesh_sec_aes_ccm_cb);

}
void mesh_ccm_decipher_test(void)
{
    uart_printf("decipher_test\n ");
    
    mesh_sec_aes_ccm(key,nonce,in_message_d,out_message,20,4,0,0,0,mesh_sec_aes_ccm_cb);
}



void gapc_mesh_send_get_pub_key_cmd(uint8_t conidx)
{
    uart_printf("gapc_mesh_send_get_pub_key_cmd\n ");
    struct gapm_get_pub_key_cmd *p_cmd = KE_MSG_ALLOC(GAPM_GET_PUB_KEY_CMD,
                                                   TASK_GAPM, KE_BUILD_ID(TASK_GAPC, conidx),
                                                   gapm_get_pub_key_cmd);
    p_cmd->operation = GAPM_GET_PUB_KEY;

    ke_msg_send(p_cmd);
    
}

/**
 ****************************************************************************************
 * @brief Send a GAPM_GEN_DH_KEY_CMD message to the SMPM. Shall be use when we need to
 *        generate a DH KEy
 *
 * @param[in] conidx      Connection Index
 * @param[in] operand_1   X co-ordinate
 * @param[in] operand_2   Y co-ordinate
 ****************************************************************************************
 */
void gapc_mesh_send_gen_dh_key_cmd(uint8_t conidx, uint8_t *operand_1, uint8_t *operand_2)
{
    struct gapm_gen_dh_key_cmd *cmd = KE_MSG_ALLOC(GAPM_GEN_DH_KEY_CMD,
                                                   TASK_GAPM, KE_BUILD_ID(TASK_GAPC, conidx),
                                                   gapm_gen_dh_key_cmd);
    cmd->operation = GAPM_GEN_DH_KEY;
    // Set operand_1 value
    memcpy(&cmd->operand_1[0], operand_1, GAP_P256_KEY_LEN);
    // Set operand_2 value
    memcpy(&cmd->operand_2[0], operand_2, GAP_P256_KEY_LEN);

    ke_msg_send(cmd);
}

/// @} MAL_SEC

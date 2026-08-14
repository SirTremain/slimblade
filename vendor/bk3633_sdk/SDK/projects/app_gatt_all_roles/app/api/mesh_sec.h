/**
 ****************************************************************************************
 *
 * @file mesh_tb_sec.h
 *
 * @brief Header file for Mesh Security Manager
 *
 * Copyright (C) RivieraWaves 2017-2019
 *
 ****************************************************************************************
 */

#ifndef _MESH_SEC_
#define _MESH_SEC_

/**
 ****************************************************************************************
 * @defgroup MESH_TB_SEC Mesh Security Manager
 * @ingroup MESH
 * @brief Mesh Security Manager
 * @{
 ****************************************************************************************
 */

/*
 * INCLUDE FILES
 ****************************************************************************************
 */





/// List of security token that can be used
enum aes_info_id
{
    AES_INFO_NONE=0,
	AES_INFO_ENCRYPT,
	AES_INFO_RAND,
	AES_INFO_CMAC,
	AES_INFO_S1,
	AES_INFO_K1,
	AES_INFO_K2,
	AES_INFO_K3,
	AES_INFO_K4,
	AES_INFO_CCM_CIPHER,
    AES_INFO_CCM_DECIPHER,
};

typedef void (*mal_sec_aes_res_cb) ( uint8_t status, const uint8_t *p_aes_res,uint32_t info );
typedef void (*mal_sec_aes_ccm_cb) (bool mic_error,uint32_t info );



void mesh_sec_init(bool reset);
void mesh_sec_aes(const uint8_t *p_key, const uint8_t *p_val, mal_sec_aes_res_cb res_cb);

void mesh_sec_rand(mal_sec_aes_res_cb res_cb);

void mesh_sec_aes_cmac(const uint8_t *p_key, const uint8_t *p_message, uint16_t message_len, mal_sec_aes_res_cb res_cb);

void mesh_sec_aes_s1(const uint8_t *p_message, uint8_t message_len, mal_sec_aes_res_cb res_cb);
void mesh_sec_aes_k1(const uint8_t *p_salt, const uint8_t *p_n, uint8_t n_len, const uint8_t *p_p, uint8_t p_len,mal_sec_aes_res_cb res_cb);
void mesh_sec_aes_k2(const uint8_t *p_n, const uint8_t *p_p, uint8_t p_len, mal_sec_aes_res_cb res_cb);
void mesh_sec_aes_k3(const uint8_t *p_n, mal_sec_aes_res_cb res_cb);

void mesh_sec_aes_k4(const uint8_t *p_n, mal_sec_aes_res_cb res_cb);

void mesh_sec_aes_ccm(const uint8_t *p_key, const uint8_t *p_nonce, const uint8_t *p_in_message,
                     uint8_t *p_out_message, uint16_t message_len, uint8_t mic_len, bool cipher,
                     const uint8_t *p_add_auth_data, uint8_t add_auth_data_len, mal_sec_aes_ccm_cb res_cb);

void mesh_sec_aes_cb(uint8_t status, uint8_t* result, uint32_t src_info);

    
void mesh_sec_aes_ccm_cb (bool mic_error,uint32_t src_info);
void mesh_ccm_cipher_test(void);
void mesh_ccm_decipher_test(void);

void gapc_mesh_send_get_pub_key_cmd(uint8_t conidx);
void gapc_mesh_send_gen_dh_key_cmd(uint8_t conidx, uint8_t *operand_1, uint8_t *operand_2);

#endif /* MESH_TB_SEC_ */

#include <stdint.h>

#define BOOT_MAX_SIZE                            (0x2000)
#define FLASH_SEC_SIZE                           (0X1000)
#define FLASH_ONE_BLOCK_SIZE                     (0X10000)
#define SEC_MAX_FSIZE_APP_BLOCK                  (0x2A00)
#define SEC_MAX_FSIZE_STACK_BLOCK                (0x3E00)

#define SEC_IMAGE_RUN_STACK_CADDR                (0x1F00)///==(BOOT_MAX_SIZE/272+1)*256
#define SEC_IMAGE_RUN_STACK_FADDR                (0x20F0) /////==(BOOT_MAX_SIZE/272+1)*272
#define SEC_IMAGE_OAD_HEADER_STACK_FADDR         (0x20E0) /////==(BOOT_MAX_SIZE/272+1)*272-0x10

#define SEC_IMAGE_RUN_APP_FADDR                  (0x280B0)
#define SEC_IMAGE_OAD_HEADER_APP_FADDR           (0x280A0)

#define SEC_IMAGE_ALLOC_START_STACK_FADDR        (0x2000)  //(8KB)
#define SEC_ALL_IMAGE_ALLOC_END_FADDR            (0x40000) //(256KB)
#define SEC_ALL_BACKUP_OAD_HEADER_FADDR          (0x40000) //256kb * 1024
#define SEC_ALL_BACKUP_OAD_IMAGE_FADDR           (0x40010) //256kb * 1024 + 0X10
#define SEC_PART_IMAGE_ALLOC_END_FADDR           (0x52000) 
#define SEC_PART_BACKUP_OAD_HEADER_FADDR         (0x52000) 
#define SEC_PART_BACKUP_OAD_IMAGE_FADDR          (0x52010) 
#define OAD_APP_PART_UID                         (0x42424242)
#define OAD_APP_STACK_UID                        (0x53535353)
/*********************************************************************
 * TYPEDEFS
 */
// The Image Header will not be encrypted, but it will be included in a Signature.
typedef struct
{
    // Secure OAD uses the Signature for image validation instead of calculating a CRC, but the use
    // of CRC==CRC-Shadow for quick boot-up determination of a validated image is still used.
    uint32_t crc;       // CRC must not be 0x0000 or 0xFFFF.
    // User-defined Image Version Number - default logic uses simple a '!=' comparison to start an OAD.
    uint16_t ver;

    uint16_t len;        // Image length in 4-byte blocks (i.e. HAL_FLASH_WORD_SIZE blocks).

    uint32_t  uid;       // User-defined Image Identification bytes.
    uint8_t  crc_status;     // cur image crc status
    uint8_t  sec_status;     // cur image sec status
    uint16_t  rom_ver;     // Rom ver.
} img_hdr_t;
#define BLOCK_SIZE          0X10
#define READ_BLOCK_SIZE     0X20
#define CRC_UNCHECK         0xFF
#define CRC_CHECK_OK        0xAA
#define CRC_CHECK_FAIL      0x55
#define SECT_UNKNOW         0xFF
#define SECT_NORMAL         0xAA
#define SECT_ABNORMAL       0x55
enum
{
    SSTATUS_SECT_NORMAL = 0,
    SSTATUS_SECT_ERASED,
    SSTATUS_SECT_ABNORMAL,
    SSTATUS_SECT_UNKOWN ,
    SSTATUS_SECT_DIFF_ROM_VER ,
};
void bim_erase_image_sec(void);
void bim_erase_backup_sec(void);
void bim_updata_backup_to_image_sec(void);
void bim_updata_image_to_backup_sec(void);
void bim_test_crc(void);
void bim_test_erase_time(void);
uint8_t bim_select_sec(void);
int make_crc32_table(void);
uint32_t make_crc32(uint32_t crc,unsigned char *string,uint32_t size);

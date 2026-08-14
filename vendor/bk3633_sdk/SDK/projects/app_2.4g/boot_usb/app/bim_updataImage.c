#include "bim_updataImage.h"
#include "bim_icu.h"
#include "bim_uart2.h"
#include "bim_flash.h"
#include "bim_wdt.h"
#include <string.h>

img_hdr_t hdr_img;
img_hdr_t hdr_back;
img_hdr_t hdr_back_part;
uint32_t bim_get_psec_image_header(void)
{
    uint32_t sec_image_oad_header_fddr;
    if(hdr_back.uid == OAD_APP_PART_UID)
    {
        sec_image_oad_header_fddr = SEC_IMAGE_OAD_HEADER_APP_FADDR;
    }
    else if(hdr_back.uid == OAD_APP_STACK_UID)
    {
        sec_image_oad_header_fddr = SEC_IMAGE_OAD_HEADER_STACK_FADDR;
    }
    sec_image_oad_header_fddr = SEC_OAD_RUN_APP_FADDR;

    bim_printf("ad= %x\n",sec_image_oad_header_fddr);
    flash_read((uint8_t *)&hdr_img,sec_image_oad_header_fddr,sizeof(img_hdr_t));
#if 1
    bim_printf("hdr_img.crc = %x\n",hdr_img.crc);
    bim_printf("hdr_img.crc_status = %x\n",hdr_img.crc_status);
    bim_printf("hdr_img.len =%x\n ",hdr_img.len);
    bim_printf("hdr_img.rom_ver = %x\n",hdr_img.rom_ver);
    bim_printf("hdr_img.sec_status = %x\n",hdr_img.sec_status);
    bim_printf("hdr_img.ver = %x\n",hdr_img.ver);
    bim_printf("hdr_img.uid = %x\n",hdr_img.uid);
#endif
    return 0;
}

uint32_t bim_get_psec_backup_header(void)
{
    flash_read((uint8_t *)&hdr_back_part,SEC_PART_BACKUP_OAD_HEADER_FADDR,sizeof(img_hdr_t));
    if(hdr_back_part.uid!=OAD_APP_PART_UID)
    {
        flash_read((uint8_t *)&hdr_back,SEC_ALL_BACKUP_OAD_HEADER_FADDR,sizeof(img_hdr_t));
    }
    else
    {
        hdr_back.uid=hdr_back_part.uid;
        hdr_back.crc=hdr_back_part.crc;
        hdr_back.ver=hdr_back_part.ver;
        hdr_back.len=hdr_back_part.len;
        hdr_back.crc_status=hdr_back_part.crc_status;
        hdr_back.sec_status=hdr_back_part.sec_status;
        hdr_back.rom_ver=hdr_back_part.rom_ver;
    }
    bim_printf("hdr_back.crc = %x\n",hdr_back.crc);
    bim_printf("hdr_back.crc_status = %x\n",hdr_back.crc_status);
    bim_printf("hdr_back.len =%x\n ",hdr_back.len);
    bim_printf("hdr_back.rom_ver = %x\n",hdr_back.rom_ver);
    bim_printf("hdr_back.sec_status = %x\n",hdr_back.sec_status);
    bim_printf("hdr_back.ver = %x\n",hdr_back.ver);
    bim_printf("hdr_back.uid = %x\n",hdr_back.uid);
    return 0;
}
int make_crc32_table(void);
uint32_t make_crc32(uint32_t crc,unsigned char *string,uint32_t size);
uint32_t calc_image_sec_crc(void)
{
    uint8_t data[BLOCK_SIZE];
    //uint8_t tmp_data[BLOCK_SIZE];
    uint32_t block_total;
    uint32_t read_addr;
    uint32_t calcuCrc = 0xffffffff;
    make_crc32_table();
    block_total =  hdr_img.len / 4 - 1;// not clac HDR
    if(hdr_img.uid == OAD_APP_PART_UID)
    {
        read_addr = SEC_IMAGE_RUN_APP_FADDR;
    }
    else if(hdr_img.uid == OAD_APP_STACK_UID)
    {
        read_addr = SEC_IMAGE_RUN_STACK_FADDR;
    }
    bim_printf("read start addr = %x\n",read_addr);
    for(uint32_t i = 0; i < block_total; i++)
    {
        flash_read(data,read_addr,BLOCK_SIZE);
        //flash_read(tmp_data,read_addr,BLOCK_SIZE);
        calcuCrc = make_crc32(calcuCrc,data,BLOCK_SIZE);
#if 0
        if(memcmp(data,tmp_data,BLOCK_SIZE) != 0)
        {
            bim_printf("read_addr error = 0x08%x\r\n",read_addr);
            for(int a=0; a<BLOCK_SIZE; a++)
            {
                bim_printf("tmp_data = %02x,data = %02x \r\n",tmp_data[a],data[a]);
            }
        }
#endif
        read_addr+= BLOCK_SIZE;
    }
    bim_printf("read end addr = %x\n",read_addr);
    return calcuCrc;
}
uint32_t calc_backup_sec_crc(uint32_t addr)
{

    uint8_t data[BLOCK_SIZE];

    uint16_t block_total;
    uint32_t read_addr;
    uint32_t calcuCrc = 0xffffffff;
    make_crc32_table();
    block_total = hdr_back.len / 4 - 1;
    read_addr = addr;

    for(uint32_t i = 0; i < block_total; i++)
    {
        flash_read(data,read_addr,BLOCK_SIZE);

        calcuCrc = make_crc32(calcuCrc,data,BLOCK_SIZE);
        read_addr+= BLOCK_SIZE;

    }

    return calcuCrc;
}
//const uint32_t ROM_VER = 0x0005;
uint8_t bim_check_image_sec_status(void)
{
    bim_get_psec_image_header();
    if(hdr_img.uid == OAD_APP_PART_UID)
    {
        if(CRC_UNCHECK == hdr_img.crc_status) // image not crc check and image is exist ,do crc calc
        {
            if(hdr_img.len != 0xffff && (hdr_img.len / 4)<= SEC_MAX_FSIZE_APP_BLOCK)
            {
                if(hdr_img.crc == calc_image_sec_crc()) // crc ok
                {
                    bim_printf("check crc OK!!!\r\n");
                    hdr_img.crc_status = CRC_CHECK_OK;
                    hdr_img.sec_status = SECT_NORMAL;
                    flash_write((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_APP_FADDR,sizeof(img_hdr_t));
                    flash_read((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_APP_FADDR,sizeof(img_hdr_t));
                    bim_get_psec_image_header();
                    return SSTATUS_SECT_NORMAL;
                }
                else
                {
                    bim_printf("check crc fail!!!\r\n");
                    hdr_img.crc_status = CRC_CHECK_FAIL;
                    hdr_img.sec_status = SECT_ABNORMAL;
                    flash_write((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_APP_FADDR,sizeof(img_hdr_t));
                    flash_read((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_APP_FADDR,sizeof(img_hdr_t));
                    return SSTATUS_SECT_ABNORMAL;
                }
            }
            else if(hdr_img.rom_ver == 0xffff)
            {
                return SSTATUS_SECT_ERASED;
            }
            else
            {
                hdr_img.crc_status = CRC_CHECK_FAIL;
                hdr_img.sec_status = SECT_ABNORMAL;
                flash_write((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_APP_FADDR,sizeof(img_hdr_t));
                flash_read((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_APP_FADDR,sizeof(img_hdr_t));
                return SSTATUS_SECT_ABNORMAL;
            }
        }
        else if(CRC_CHECK_FAIL == hdr_img.crc_status)
        {
            hdr_img.crc_status = CRC_CHECK_FAIL;
            hdr_img.sec_status = SECT_ABNORMAL;
            flash_write((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_APP_FADDR,sizeof(img_hdr_t));
            flash_read((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_APP_FADDR,sizeof(img_hdr_t));
            return SSTATUS_SECT_ABNORMAL;
        }
        else if(CRC_CHECK_OK == hdr_img.crc_status)
        {
            hdr_img.crc_status = CRC_CHECK_OK;
            hdr_img.sec_status = SECT_NORMAL;
            flash_write((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_APP_FADDR,sizeof(img_hdr_t));
            flash_read((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_APP_FADDR,sizeof(img_hdr_t));
            return SSTATUS_SECT_NORMAL;
        }
        else
        {
            hdr_img.crc_status = CRC_CHECK_FAIL;
            hdr_img.sec_status = SECT_ABNORMAL;
            flash_write((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_APP_FADDR,sizeof(img_hdr_t));
            flash_read((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_APP_FADDR,sizeof(img_hdr_t));
            return SSTATUS_SECT_ABNORMAL;
        }
    }
    else if(hdr_img.uid == OAD_APP_STACK_UID)
    {
        if(CRC_UNCHECK == hdr_img.crc_status) // image not crc check and image is exist ,do crc calc
        {
            if(hdr_img.len != 0xffff && (hdr_img.len / 4)<= SEC_MAX_FSIZE_STACK_BLOCK)
            {
                if(hdr_img.crc == calc_image_sec_crc()) // crc ok
                {
                    bim_printf("check crc OK!!!\r\n");
                    hdr_img.crc_status = CRC_CHECK_OK;
                    hdr_img.sec_status = SECT_NORMAL;
                    flash_write((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_STACK_FADDR,sizeof(img_hdr_t));
                    flash_read((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_STACK_FADDR,sizeof(img_hdr_t));
                    bim_get_psec_image_header();
                    return SSTATUS_SECT_NORMAL;
                }
                else
                {
                    bim_printf("check crc fail!!!\r\n");
                    hdr_img.crc_status = CRC_CHECK_FAIL;
                    hdr_img.sec_status = SECT_ABNORMAL;
                    flash_write((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_STACK_FADDR,sizeof(img_hdr_t));
                    flash_read((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_STACK_FADDR,sizeof(img_hdr_t));
                    return SSTATUS_SECT_ABNORMAL;
                }
            }
            else if(hdr_img.ver == 0xffff)
            {
                return SSTATUS_SECT_ERASED;
            }
            else
            {
                hdr_img.crc_status = CRC_CHECK_FAIL;
                hdr_img.sec_status = SECT_ABNORMAL;
                flash_write((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_STACK_FADDR,sizeof(img_hdr_t));
                flash_read((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_STACK_FADDR,sizeof(img_hdr_t));
                return SSTATUS_SECT_ABNORMAL;
            }
        }
        else if(CRC_CHECK_FAIL == hdr_img.crc_status)
        {
            hdr_img.crc_status = CRC_CHECK_FAIL;
            hdr_img.sec_status = SECT_ABNORMAL;
            flash_write((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_STACK_FADDR,sizeof(img_hdr_t));
            flash_read((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_STACK_FADDR,sizeof(img_hdr_t));
            return SSTATUS_SECT_ABNORMAL;
        }
        else if(CRC_CHECK_OK == hdr_img.crc_status)
        {
            hdr_img.crc_status = CRC_CHECK_OK;
            hdr_img.sec_status = SECT_NORMAL;
            flash_write((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_STACK_FADDR,sizeof(img_hdr_t));
            flash_read((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_STACK_FADDR,sizeof(img_hdr_t));
            return SSTATUS_SECT_NORMAL;
        }
        else
        {
            hdr_img.crc_status = CRC_CHECK_FAIL;
            hdr_img.sec_status = SECT_ABNORMAL;
            flash_write((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_STACK_FADDR,sizeof(img_hdr_t));
            flash_read((uint8_t *)&hdr_img,SEC_IMAGE_OAD_HEADER_STACK_FADDR,sizeof(img_hdr_t));
            return SSTATUS_SECT_ABNORMAL;
        }
    }
    else
    {
        bim_printf("bim_check_image_sec_status: ERROR, UNKNOWN UID\r\n");
        return SSTATUS_SECT_UNKOWN;
    }
}

uint8_t bim_check_backup_sec_status(void)//NOT WRITE INFO TO FLASH
{
    bim_get_psec_backup_header();
    if((hdr_back.rom_ver == 0xffff) || (hdr_back.ver == 0xffff)  )
    {
        return SSTATUS_SECT_ERASED;
    }
    if(hdr_back.uid == OAD_APP_PART_UID)
    {
        if(CRC_UNCHECK == hdr_back.crc_status) // image not crc check and image is exist ,do crc calc
        {

            if(hdr_back.len != 0xffff && (hdr_back.len / 4) <= SEC_MAX_FSIZE_APP_BLOCK)
            {
                if(hdr_back.crc == calc_backup_sec_crc(SEC_PART_BACKUP_OAD_IMAGE_FADDR)) // crc ok
                {
                    bim_printf("crc ok\r\n");
                    hdr_back.crc_status = CRC_CHECK_OK;
                    hdr_back.sec_status = SECT_NORMAL;
                    return SSTATUS_SECT_NORMAL;
                }
                else
                {
                    bim_printf("crc error\r\n");
                    hdr_back.crc_status = CRC_CHECK_FAIL;
                    hdr_back.sec_status = SECT_ABNORMAL;
                    return SSTATUS_SECT_ABNORMAL;
                }
            }
            else
            {
                hdr_back.crc_status = CRC_CHECK_FAIL;
                hdr_back.sec_status = SECT_ABNORMAL;
                return SSTATUS_SECT_ABNORMAL;
            }
        }
        else if(CRC_CHECK_FAIL == hdr_back.crc_status)
        {
            hdr_back.crc_status = CRC_CHECK_FAIL;
            hdr_back.sec_status = SECT_ABNORMAL;
            return SSTATUS_SECT_ABNORMAL;
        }
        else if(CRC_CHECK_OK == hdr_back.crc_status)
        {
            hdr_back.crc_status = CRC_CHECK_OK;
            hdr_back.sec_status = SECT_NORMAL;
            return SSTATUS_SECT_NORMAL;
        }
        else
        {
            hdr_back.crc_status = CRC_CHECK_FAIL;
            hdr_back.sec_status = SECT_ABNORMAL;
            return SSTATUS_SECT_ABNORMAL;
        }
    }
    else if(hdr_back.uid == OAD_APP_STACK_UID)
    {
        if(CRC_UNCHECK == hdr_back.crc_status) // image not crc check and image is exist ,do crc calc
        {
            if(hdr_back.len != 0xffff && (hdr_back.len / 4) <= SEC_MAX_FSIZE_STACK_BLOCK)
            {
                if(hdr_back.crc == calc_backup_sec_crc(SEC_ALL_BACKUP_OAD_IMAGE_FADDR)) // crc ok
                {
                    bim_printf("crc ok\r\n");
                    hdr_back.crc_status = CRC_CHECK_OK;
                    hdr_back.sec_status = SECT_NORMAL;
                    return SSTATUS_SECT_NORMAL;
                }
                else
                {
                    bim_printf("crc error\r\n");
                    hdr_back.crc_status = CRC_CHECK_FAIL;
                    hdr_back.sec_status = SECT_ABNORMAL;
                    return SSTATUS_SECT_ABNORMAL;
                }
            }
            else
            {
                hdr_back.crc_status = CRC_CHECK_FAIL;
                hdr_back.sec_status = SECT_ABNORMAL;
                return SSTATUS_SECT_ABNORMAL;
            }
        }
        else if(CRC_CHECK_FAIL == hdr_back.crc_status)
        {
            hdr_back.crc_status = CRC_CHECK_FAIL;
            hdr_back.sec_status = SECT_ABNORMAL;
            return SSTATUS_SECT_ABNORMAL;
        }
        else if(CRC_CHECK_OK == hdr_back.crc_status)
        {
            hdr_back.crc_status = CRC_CHECK_OK;
            hdr_back.sec_status = SECT_NORMAL;
            return SSTATUS_SECT_NORMAL;
        }
        else
        {
            hdr_back.crc_status = CRC_CHECK_FAIL;
            hdr_back.sec_status = SECT_ABNORMAL;
            return SSTATUS_SECT_ABNORMAL;
        }
    }
    else
    {
        return SSTATUS_SECT_UNKOWN;
    }
}
void bim_erase_image_sec(void)
{
    //uint8_t sector_cnt;
    bim_printf("erase_image start \n");
    if(hdr_back.uid == OAD_APP_PART_UID)  //128k
    {
        ///erase 160k~328k
        flash_erase(0x28000,0X8000);
        flash_erase_one_block(0X30000);
        flash_erase_one_block(0X40000);
        flash_erase(0x50000,0X2000);
    }
    else if(hdr_back.uid == OAD_APP_STACK_UID) //248k
    {
        uint32_t addr = SEC_ALL_IMAGE_ALLOC_END_FADDR - FLASH_ONE_BLOCK_SIZE ;

        flash_erase_one_block(addr);
        addr -= FLASH_ONE_BLOCK_SIZE;

        flash_erase_one_block(addr);
        addr -= FLASH_ONE_BLOCK_SIZE;

        flash_erase_one_block(addr);

        flash_erase(SEC_IMAGE_ALLOC_START_STACK_FADDR,(0x10000-SEC_IMAGE_ALLOC_START_STACK_FADDR));
    }
    else
    {
        bim_printf("bim_erase_image_sec: ERROR, UNKNOWN UID\r\n");
    }

    bim_printf("erase_image end \n");
}
void bim_erase_backup_sec(void)
{
    if(hdr_back.uid==OAD_APP_STACK_UID)
    {
        flash_erase_one_block(SEC_ALL_BACKUP_OAD_HEADER_FADDR);
        flash_erase_one_block(SEC_ALL_BACKUP_OAD_HEADER_FADDR+0x10000);
        flash_erase_one_block(SEC_ALL_BACKUP_OAD_HEADER_FADDR+0x20000);
        flash_erase((SEC_ALL_BACKUP_OAD_HEADER_FADDR+0x30000),48*1024);

        bim_printf("erase all backup addr \r\n");
    }
    else if(hdr_back.uid==OAD_APP_PART_UID)
    {
        flash_erase(SEC_PART_BACKUP_OAD_HEADER_FADDR,56*1024);
        flash_erase_one_block(0x60000);
        flash_erase(0x70000,48*1024);

        bim_printf("erase part backup addr\r\n");
    }
}
void bim_updata_backup_to_image_sec(void)
{
    uint8_t data[READ_BLOCK_SIZE];
    uint32_t backup_size = hdr_back.len * 4;
    uint32_t read_end_addr ;
    uint32_t read_addr;
    uint32_t write_addr;
    bim_printf("backup_size =%x\n",backup_size);
    if(hdr_back.uid == OAD_APP_PART_UID) // only app part
    {
        write_addr = SEC_IMAGE_OAD_HEADER_APP_FADDR;
        read_end_addr = SEC_PART_BACKUP_OAD_HEADER_FADDR + backup_size;
        read_addr = SEC_PART_BACKUP_OAD_HEADER_FADDR;

    }
    else if(hdr_back.uid == OAD_APP_STACK_UID) //app and stack
    {
        write_addr = SEC_IMAGE_OAD_HEADER_STACK_FADDR;
        read_end_addr = SEC_ALL_BACKUP_OAD_HEADER_FADDR + backup_size;
        read_addr = SEC_ALL_BACKUP_OAD_HEADER_FADDR;
    }
    bim_printf("write_addr = %x\r\n",write_addr);
    bim_printf("read_end_addr = %x\r\n",read_end_addr);

    while(read_addr < read_end_addr)
    {
        flash_read(data,read_addr,READ_BLOCK_SIZE);
        flash_write(data,write_addr,READ_BLOCK_SIZE);
        write_addr += READ_BLOCK_SIZE;
        read_addr += READ_BLOCK_SIZE;
    }
    bim_printf("udi_updata_backup_to_image_sec end\r\n");
}

uint8_t bim_select_sec(void)
{
    uint8_t bsec_status;
    uint8_t status = 0;

    bsec_status = bim_check_backup_sec_status();
    bim_printf("bsec_status= %x\n",bsec_status);

    switch(bsec_status)
    {
        case SSTATUS_SECT_NORMAL: // 1:I NORMAL ,B NORMAL,updata B -> I,RUN I
        {
            if(hdr_back.uid == OAD_APP_PART_UID)
            {
                flash_wp_128k();
            }
            else if(hdr_back.uid == OAD_APP_STACK_UID)
            {
                flash_wp_8k();
            }
            bim_erase_image_sec();
            bim_updata_backup_to_image_sec();
            if(SSTATUS_SECT_NORMAL == bim_check_image_sec_status())
            {
                bim_printf("1234\n");
                flash_wp_256k();
                bim_erase_backup_sec();
                status = 1;
                flash_wp_ALL();
            }
            else
            {
                flash_wp_ALL();
                wdt_enable(100);//reset
            }
        }
        break;
        case SSTATUS_SECT_ERASED://://3:I NORMAL,B ERASED,RUN I
        {

            bim_printf("earse\n");
            status = 1;
            flash_wp_ALL();
        }
        break;
        case SSTATUS_SECT_ABNORMAL:
        case SSTATUS_SECT_DIFF_ROM_VER:////4:I DIFF_ROM,B ERASED,NOT HAPPEN
        default:
        {
            flash_wp_256k();
            status = 1;
            bim_erase_backup_sec();
            flash_wp_ALL();
        }
        break;
    }
    return status ;
}
uint32_t crc32_table[256];
int make_crc32_table(void)
{
    uint32_t c;
    int i = 0;
    int bit = 0;
    for(i = 0; i < 256; i++)
    {
        c = (uint32_t)i;
        for(bit = 0; bit < 8; bit++)
        {
            if(c&1)
            {
                c = (c>>1)^(0xEDB88320);
            }
            else
            {
                c = c >> 1;
            }
        }
        crc32_table[i] = c;
    }
    return 0;
}
uint32_t make_crc32(uint32_t crc,unsigned char *string,uint32_t size)
{
    while(size--)
    {
        crc = (crc >> 8)^(crc32_table[(crc^*string++)&0xff]);
    }
    return crc;
}

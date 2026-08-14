
#include <stdint.h>        // standard integer definition
#include <string.h>        // string manipulation
#include "flash.h"         // flash definition
#include "co_error.h"      // error definition
#include "uart.h"
#include "rwip.h"
#include "ll.h"





#define MAX(x, y)                  (((x) > (y)) ? (x) : (y))
#define MIN(x, y)                  (((x) < (y)) ? (x) : (y))
#define max(x, y)                  (((x) > (y)) ? (x) : (y))
#define min(x, y)                  (((x) < (y)) ? (x) : (y))

/// Flash environment structure
struct flash_env_tag
{
    /// base address
    uint32_t    base_addr;
    /// length
    uint32_t    length;
    /// type
    uint32_t    space_type;
};


/// Flash environment structure variable
struct flash_env_tag flash_env;


extern uint8_t system_mode;

uint8_t flash_enable_write_flag1;
uint8_t flash_enable_write_flag2;
uint8_t flash_enable_write_flag3;
uint8_t flash_enable_write_flag4;
uint8_t flash_enable_erase_flag1;
uint8_t flash_enable_erase_flag2;



uint32_t flash_mid = 0;
void set_flash_clk(unsigned char clk_conf) 
{
	//note :>16M don't use la for flash debug
    unsigned int temp0;
    temp0 = REG_FLASH_CONF;
    REG_FLASH_CONF = (  (clk_conf << BIT_FLASH_CLK_CONF)
                      | (temp0    &  SET_MODE_SEL)
                      | (temp0    &  SET_FWREN_FLASH_CPU)
                      | (temp0    &  SET_WRSR_DATA)
                      | (temp0    &  SET_CRC_EN));
	while(REG_FLASH_OPERATE_SW & 0x80000000){;}
}

uint32_t get_flash_ID(void)
{
    unsigned int temp0;

	while(REG_FLASH_OPERATE_SW & 0x80000000);
	
	REG_FLASH_OPERATE_SW = (       FLASH_ADDR_FIX
								| (FLASH_OPCODE_RDID << BIT_OP_TYPE_SW)
								| (0x1				 << BIT_OP_SW));
	while(REG_FLASH_OPERATE_SW & 0x80000000);

    for (temp0=0; temp0<8; temp0++)
            REG_FLASH_DATA_SW_FLASH = 0xffffffff;

	return REG_FLASH_RDID_DATA_FLASH ;
}


uint32_t flash_read_sr( )
{
	uint16_t temp;
	

/*
	while(REG_FLASH_OPERATE_SW & 0x80000000);
	temp0 = REG_FLASH_OPERATE_SW;
	REG_FLASH_OPERATE_SW = (  (temp0             &  SET_ADDRESS_SW)
	                        | (FLASH_OPCODE_RDSR2 << BIT_OP_TYPE_SW)
	                        | (0x1               << BIT_OP_SW)
	                        | (temp0             &  SET_WP_VALUE));
	while(REG_FLASH_OPERATE_SW & 0x80000000);

	temp=(REG_FLASH_SR_DATA_CRC_CNT&0xff)<<8;

*/	
	 while(REG_FLASH_OPERATE_SW & 0x80000000);
	 
	 REG_FLASH_OPERATE_SW = (  FLASH_ADDR_FIX
							 | (FLASH_OPCODE_RDSR << BIT_OP_TYPE_SW)
							 | (0x1 			  << BIT_OP_SW));

    
	while(REG_FLASH_OPERATE_SW & 0x80000000);
    temp = (REG_FLASH_SR_DATA_CRC_CNT&0xff);
    
	return temp ;
}



void flash_write_sr( uint8_t bytes,  uint16_t val )
{
	if(flash_mid != get_flash_ID())
		return;
	switch(flash_mid)
	{
		case MX_FLASH_4M:
		case MX_FLASH_1:			   //MG xx
			REG_FLASH_CONF &= 0xffdf0fff;
		break;     
		
		case GD_FLASH_1:			  //QD xx ,
		case BY25Q80:
		case PN25f04:
			REG_FLASH_CONF &= 0xfefe0fff;
		break;
        case XTX_FLASH_1:			   //XTX xx
		case GD_MD25D40:
        case GD_GD25WD40:
        default:
			REG_FLASH_CONF &= 0xffff0fff;
		break;
	}

    if(bytes==0||bytes>2)	
        return;
    REG_FLASH_CONF |= (val << BIT_WRSR_DATA)|SET_FWREN_FLASH_CPU;
    while(REG_FLASH_OPERATE_SW & 0x80000000);
	if(flash_mid != get_flash_ID())
		return;
    if( bytes == 1 ) 
    {
        REG_FLASH_OPERATE_SW = (FLASH_ADDR_FIX|(FLASH_OPCODE_WRSR << BIT_OP_TYPE_SW)
	                           | (0x1<< BIT_OP_SW)
	                           | (0x1<< BIT_WP_VALUE));
        
    }
    else if(bytes == 2 )
    {
        REG_FLASH_OPERATE_SW = (FLASH_ADDR_FIX|(FLASH_OPCODE_WRSR2 << BIT_OP_TYPE_SW)
	                           | (0x1<< BIT_OP_SW)
	                           | (0x1<< BIT_WP_VALUE));       
    }
        
    while(REG_FLASH_OPERATE_SW & 0x80000000);


    REG_FLASH_OPERATE_SW = FLASH_ADDR_FIX; 

    while(REG_FLASH_OPERATE_SW & 0x80000000);
}

void flash_wp_256k( void)
{
    switch(flash_mid)
    {
        case MX_FLASH_4M:
        case MX_FLASH_1:			   //MG xx
            flash_write_sr( 2, 0x088C );
            break;
        case XTX_FLASH_1:			   //XTX xx
            flash_write_sr( 1, 0xAC );
            break;   

        case GD_FLASH_1:			  //QD xx ,
        case BY25Q80:
        case PN25f04:
            flash_write_sr( 2, 0x00ac );
            break;
        case GD_MD25D40:
        case GD_GD25WD40:    
        default:
            flash_write_sr( 1, 0x98 );
            break;    
    }
}

void flash_wp_ALL( void )
{
    switch(flash_mid)
    {
        case MX_FLASH_4M:
        case MX_FLASH_1:			   //MG xx
            flash_write_sr( 2, 0x00bc );
            break;
        case XTX_FLASH_1:			   //XTX xx
            flash_write_sr( 1, 0xBC );
            break;  
        case GD_FLASH_1:			  //QD xx ,
        case BY25Q80:
        case PN25f04:
            flash_write_sr( 2, 0x0094 );
            break;
        case GD_MD25D40:
        case GD_GD25WD40:    
        default:
            flash_write_sr( 1, 0x9c );
            break;    
    }
}

void flash_advance_init(void)
{
    uint32_t flash_sr;

    flash_mid = get_flash_ID();
    
    flash_sr=flash_read_sr( );

    switch(flash_mid)
    {
        case MX_FLASH_4M:
        case MX_FLASH_1:			   //MG xx
            if(flash_sr!=0x00bc)
                flash_write_sr( 2, 0x00bc );
            break;
        case XTX_FLASH_1:			   //XTX xx
            if(flash_sr!=0xbc)
                flash_write_sr( 1, 0xBC );
            break;  
        case GD_FLASH_1:			  //QD xx ,
        case BY25Q80:
        case PN25f04:
            if(flash_sr!=0x0094)
                flash_write_sr( 2, 0x0094 );
            break;
        case GD_MD25D40:
        case GD_GD25WD40:    
        default:
            if(flash_sr!=0x9c)
                flash_write_sr( 1, 0x9c );
            break;    
    }
    uart_printf("flash_mid=%x\n",flash_mid);   
}


void flash_init(void)
{   
    flash_advance_init();
    flash_set_dual_mode();       
    set_flash_clk(0x08);    
}


void flash_erase_sector(uint32_t address)
{
    GLOBAL_INT_DISABLE();
    flash_set_line_mode(1);
    if(flash_enable_erase_flag1==FLASH_ERASE_ENABLE1&&flash_enable_erase_flag2==FLASH_ERASE_ENABLE2)    
    {
        flash_wp_256k();
        
        while(REG_FLASH_OPERATE_SW & 0x80000000);

        REG_FLASH_OPERATE_SW = (  (address << BIT_ADDRESS_SW)
                                                   | (FLASH_OPCODE_SE<< BIT_OP_TYPE_SW)
                                                   | (0x1             << BIT_OP_SW));

        while(REG_FLASH_OPERATE_SW & 0x80000000);
        flash_set_line_mode(4);
        flash_wp_ALL();
    }
    GLOBAL_INT_RESTORE();
}



void flash_read_data (uint8_t *buffer, uint32_t address, uint32_t len)
{	
    uint32_t i, j,k;
    uint32_t addr = address;
    uint32_t buf[8];
    k=0;  
    if (len == 0)
        return;

    GLOBAL_INT_DISABLE();
    while(REG_FLASH_OPERATE_SW & 0x80000000);

    for(j=0;j<((len-1)/32+1);j++)
    {
        REG_FLASH_OPERATE_SW = (  (addr << BIT_ADDRESS_SW)
                                | (FLASH_OPCODE_READ << BIT_OP_TYPE_SW)
                                | (0x1 << BIT_OP_SW));
        while(REG_FLASH_OPERATE_SW & 0x80000000);
        addr+=32;
        for (i=0; i<8; i++)
        {
            buf[i] = REG_FLASH_DATA_FLASH_SW;
        }

        if(len>32*(j+1))
            memcpy(&buffer[k],buf,32);
        else
        {
            memcpy(&buffer[k],buf,len-k);
        }
        k += 32;        
    }
    REG_FLASH_OPERATE_SW=FLASH_ADDR_FIX ;
    for (i=0; i<8; i++)
        REG_FLASH_DATA_SW_FLASH = 0xffffffff;
    GLOBAL_INT_RESTORE();
}




void flash_write_data (uint8_t *buffer, uint32_t address, uint32_t len)
{
    uint32_t i, j,k;
    uint32_t addr = address;
    uint32_t buf[8];
    k=0;
    if (len == 0)
        return;
    if (address<0x40000)
        return;
    GLOBAL_INT_DISABLE();
	flash_set_line_mode(1);

    while(REG_FLASH_OPERATE_SW & 0x80000000);
    
    flash_enable_write_flag3=FLASH_WRITE_ENABLE3; 
    flash_wp_256k();
    for(j=0;j<((len-1)/32+1);j++)
    {
        if(len>32*(j+1))
            memcpy(buf,&buffer[k],32);
        else
        {
         	for(i=0;i<8;i++)
                buf[i]=0xffffffff;
            memcpy(buf,&buffer[k],len-k);
        }
        k += 32;
        flash_enable_write_flag4=FLASH_WRITE_ENABLE4; 
        for (i=0; i<8; i++)
            REG_FLASH_DATA_SW_FLASH = buf[i];


        if(flash_enable_write_flag1==FLASH_WRITE_ENABLE1 && flash_enable_write_flag2==FLASH_WRITE_ENABLE2 )
        {
            while(REG_FLASH_OPERATE_SW & 0x80000000);
            
            if(flash_enable_write_flag3==FLASH_WRITE_ENABLE3 && flash_enable_write_flag4==FLASH_WRITE_ENABLE4)
            {
                if(addr<0x40000)
                    return;
                REG_FLASH_OPERATE_SW = (  (addr << BIT_ADDRESS_SW)
                                    | (FLASH_OPCODE_PP << BIT_OP_TYPE_SW)
                                    | (0x1 << BIT_OP_SW));
            }
            while(REG_FLASH_OPERATE_SW & 0x80000000);
        }
        addr+=32;
    }
    flash_wp_ALL();
    REG_FLASH_OPERATE_SW=FLASH_ADDR_FIX ;
    flash_enable_write_flag3=0;
    flash_enable_write_flag4=0;
    for (i=0; i<8; i++)
        REG_FLASH_DATA_SW_FLASH = 0xffffffff;
	flash_set_line_mode(4);
	GLOBAL_INT_RESTORE();
}



void flash_set_qe(void)
{
	uint32_t temp0;
	while(REG_FLASH_OPERATE_SW & 0x80000000){;}
//XTX_FLASH_1 没有QE,不需要,靠 EQPI(38h) CMD 来处理
//这个仅对MX_FLASH_1 、MX_FLASH_4M、XTX_FLASH_1有效。

	temp0 = REG_FLASH_CONF; //配置WRSR Status data

	if(flash_mid == XTX_FLASH_1)  // wanghong
		return;
	if((flash_mid == MX_FLASH_1)||(flash_mid == MX_FLASH_4M))  // wanghong
	{
		//WRSR QE=1
		REG_FLASH_CONF = ((temp0 &  SET_FLASH_CLK_CONF)
						| (temp0 &  SET_MODE_SEL)
						| (temp0 &  SET_FWREN_FLASH_CPU)
						| (temp0 & SET_WRSR_DATA)
						| (0x1 << 16) // SET QE=1,quad enable
						| (temp0 &  SET_CRC_EN));

		//Start WRSR
		
		REG_FLASH_OPERATE_SW = (  FLASH_ADDR_FIX
						     | (FLASH_OPCODE_WRSR2 << BIT_OP_TYPE_SW)
						     | (0x1				  << BIT_OP_SW)); 
	}
	else
	{
		REG_FLASH_CONF = (	(temp0 &  SET_FLASH_CLK_CONF)
						  | (temp0 &  SET_MODE_SEL)
						  | (temp0 &  SET_FWREN_FLASH_CPU)
						  |	(temp0 & SET_WRSR_DATA)
						  |	(0x01 << 19)
						  | (temp0 &  SET_CRC_EN));

		//Start WRSR
		
		REG_FLASH_OPERATE_SW = (  FLASH_ADDR_FIX
						        | (FLASH_OPCODE_WRSR2 << BIT_OP_TYPE_SW)
						        | (0x1				  << BIT_OP_SW)); 
	}
	while(REG_FLASH_OPERATE_SW & 0x80000000);
}



void clr_flash_qwfr(void)
{
    uint32_t temp0,mod_sel;	
	
    temp0 = REG_FLASH_CONF;
    while(REG_FLASH_OPERATE_SW & 0x80000000){;}
    mod_sel = temp0 & (0xC << BIT_MODE_SEL); //??3ymode_sel?D
    mod_sel |= (0x1 << BIT_MODE_SEL);
    REG_FLASH_CONF = (  (temp0 &  SET_FLASH_CLK_CONF)
                        | mod_sel
                        | (temp0 &  SET_FWREN_FLASH_CPU)
                        | (temp0 &  SET_WRSR_DATA)
                        | (temp0 &  SET_CRC_EN));
    //reset flash
    
    if(flash_mid == XTX_FLASH_1)
    {
        REG_FLASH_OPERATE_SW = (  (FLASH_ADDR_FIX<< BIT_ADDRESS_SW)
                                | (FLASH_OPCODE_CRMR << BIT_OP_TYPE_SW)
                                | (0x1               << BIT_OP_SW));
    }
    else
    {
        REG_FLASH_OPERATE_SW = (  (FLASH_ADDR_FIX<< BIT_ADDRESS_SW)
                                | (FLASH_OPCODE_CRMR2 << BIT_OP_TYPE_SW)
                                | (0x1               << BIT_OP_SW));
    }

    while(REG_FLASH_OPERATE_SW & 0x80000000);
}


void flash_set_dual_mode(void)
{
    clr_flash_qwfr();
    REG_FLASH_CONF &= (~(7<<BIT_MODE_SEL));
    REG_FLASH_CONF |= (1<<BIT_MODE_SEL);
    while(REG_FLASH_OPERATE_SW & 0x80000000);
}

void flash_set_line_mode(uint8_t mode)
{

}


uint8_t flash_read(uint8_t flash_space, uint32_t address, uint32_t len, uint8_t *buffer, void (*callback)(void))
{
    uint32_t pre_address;
    uint32_t post_address;
    uint32_t pre_len;
    uint32_t post_len;
    uint32_t page0;
    uint32_t page1;
    page0 = address &(~FLASH_PAGE_MASK);
    page1 = (address + len) &(~FLASH_PAGE_MASK);
    if(page0 != page1)
    {
        pre_address = address;
        pre_len = page1 - address;
        flash_read_data(buffer, pre_address, pre_len);
        post_address = page1;
        post_len = address + len - page1;
        flash_read_data((buffer + pre_len), post_address, post_len);
    }
    else
    {
        flash_read_data(buffer, address, len);
    }
		
    return CO_ERROR_NO_ERROR;
}



uint8_t flash_write(uint8_t flash_space, uint32_t address, uint32_t len, uint8_t *buffer, void (*callback)(void))
{
    uint32_t pre_address;
    uint32_t post_address;
    uint32_t pre_len;
    uint32_t post_len;
    uint32_t page0;
    uint32_t page1;
    
    if(flash_mid != get_flash_ID())
    {
        uart_printf("flash = 0x%x\r\n", get_flash_ID());
        return CO_ERROR_UNDEFINED;
    }

    flash_enable_write_flag1=FLASH_WRITE_ENABLE1; 
    
    page0 = address &(~FLASH_PAGE_MASK);
    page1 = (address + len) &(~FLASH_PAGE_MASK);
     
    if(page0 != page1)
    {
        pre_address = address;
        pre_len = page1 - address;
        flash_enable_write_flag2=FLASH_WRITE_ENABLE2;
        flash_write_data(buffer, pre_address, pre_len);
        
        post_address = page1;
        post_len = address + len - page1;
        flash_write_data((buffer + pre_len), post_address, post_len);

    }
    else
    {
        flash_enable_write_flag2=FLASH_WRITE_ENABLE2;
        flash_write_data(buffer, address, len);

    }
    flash_enable_write_flag1=0; 
    flash_enable_write_flag2=0;	
    
    return CO_ERROR_NO_ERROR;
}





////擦除函数，地址和长度都要4K的整数倍
uint8_t flash_erase(uint8_t flash_type, uint32_t address, uint32_t len, void (*callback)(void))
{
    /* assume: the worst span is four sectors*/
    int erase_addr;
    int erase_len;


    flash_enable_erase_flag1=FLASH_ERASE_ENABLE1;
    
    if(flash_mid != get_flash_ID())
    {
        return CO_ERROR_UNDEFINED;
    }
    
    
    {
        erase_addr = address & (~FLASH_ERASE_SECTOR_SIZE_MASK);
        erase_len = len;
    }
    do
    {
        int i;
        int erase_whole_sector_cnt;
        //erase_whole_sector_cnt = erase_len >> FLASH_ERASE_SECTOR_SIZE_RSL_BIT_CNT;
        erase_whole_sector_cnt = erase_len/FLASH_ERASE_SECTOR_SIZE + (erase_len%FLASH_ERASE_SECTOR_SIZE>0? 1:0);//不要求长度是4k整数倍
        flash_enable_erase_flag2=FLASH_ERASE_ENABLE2;
        for(i = 0; i < erase_whole_sector_cnt; i ++)
        {
            flash_erase_sector(erase_addr);
            erase_addr += FLASH_ERASE_SECTOR_SIZE;
            //erase_len -= FLASH_ERASE_SECTOR_SIZE;
        }
    }
    while(0);
    
    flash_enable_erase_flag1=0;
    flash_enable_erase_flag2=0;
    return CO_ERROR_NO_ERROR;
}


void flash_write_some_data(uint8_t *buffer, uint32_t address, uint32_t len)
    // 仅保存当前地址下的完整1K数据
{
    unsigned char flash_temp[1024];
    flash_wp_256k(); // 有 bug 1、 保护空间不对，2、写完没有恢复保护
    flash_read(0,address&0xfffffc00, 1024,flash_temp, (void*)0);//the addr is the word,so the addr +20
    memcpy(&flash_temp[address&0x3ff],buffer,len);
    flash_erase(0,address,0x1000,0);
    flash_write(0,address&0xfffffc00,1024,flash_temp,(void*)0);
    flash_wp_ALL();

}

#define  TEST_FLASH_ADDRESS  0x7FF00
#define  TEST_LEN 0xff
void flash_test(void)
{
	unsigned char w_temp[TEST_LEN];
	unsigned char r_temp[TEST_LEN];
	int i;

    flash_wp_256k();

	uart_printf("flash_test\n ");
    flash_read(0,TEST_FLASH_ADDRESS ,TEST_LEN,r_temp,NULL);

    uart_printf("r_temp1: ");
    for (i=0; i<TEST_LEN; i++)
	{
	    uart_printf("%x,",r_temp[i]);
	}
    uart_printf("\n ");
    
	for (i=0; i<TEST_LEN; i++)
	{
	    w_temp[i] = i;
	}
    
	flash_write(0,TEST_FLASH_ADDRESS ,TEST_LEN,w_temp,NULL);
    
    flash_read(0,TEST_FLASH_ADDRESS ,TEST_LEN,r_temp,NULL);

    uart_printf("r_temp1: ");
    for (i=0; i<TEST_LEN; i++)
	{
	    uart_printf("%x,",r_temp[i]);
	}
    uart_printf("\n ");
    
    flash_erase(0,TEST_FLASH_ADDRESS ,0x1000,NULL);
    
    flash_read(0,TEST_FLASH_ADDRESS ,TEST_LEN,r_temp,NULL);

    uart_printf("r_temp1: ");
    for (i=0; i<TEST_LEN; i++)
	{
	    uart_printf("%x,",r_temp[i]);
	}
    uart_printf("\n ");
}




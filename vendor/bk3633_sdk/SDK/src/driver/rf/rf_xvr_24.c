
#include <string.h>             // for memcpy
#include <stdint.h> 
#include "rf.h"                 // RF interface		
#include "uart2.h"		
#include "bk3633_reglist.h"
#include "user_config.h"


void CLK32K_AutoCali_init(void);
volatile uint32_t XVR_ANALOG_REG_BAK[32] = {0};

void  xvr_reg_initial(void) {
           
    addXVR_Reg0x0 = 0xC4B0323F  ;
    XVR_ANALOG_REG_BAK[0] = 0xC4B0323F;
    addXVR_Reg0x1 = 0x8295C200  ;
    XVR_ANALOG_REG_BAK[1] = 0x8295C200;
    addXVR_Reg0x2 = 0x2742E000  ;
    XVR_ANALOG_REG_BAK[2] = 0x2742E000;
    addXVR_Reg0x3 = 0x60035C62  ;
    XVR_ANALOG_REG_BAK[3] = 0x60035C62;
    addXVR_Reg0x4 = 0xFF76AACF  ;
    XVR_ANALOG_REG_BAK[4] = 0xFF76AACF;//0xFFD6BBCC
    addXVR_Reg0x5 = 0x4620501F  ;
    XVR_ANALOG_REG_BAK[5] = 0x4620501F; //0x4620501F 03.31 // 0x4420501F 04.01
    #if(LDO_MODE)
        addXVR_Reg0x6 = 0x8487CC00;//0x80B7CE20  ;
        XVR_ANALOG_REG_BAK[6] = 0x8487CC00;//0x80B7CE20;
    #else
        addXVR_Reg0x6 = 0x84A7CC00;//0x8097CE20  ;
        XVR_ANALOG_REG_BAK[6] = 0x84A7CC00;//0x8097CE20;
    #endif
    addXVR_Reg0x7 = 0xAA0A3FC0  ;
    XVR_ANALOG_REG_BAK[7] = 0xAA0A3FC0;
    addXVR_Reg0x8 = 0x0FB0C02F  ;
    XVR_ANALOG_REG_BAK[8] = 0x0FB0C02F;

    addXVR_Reg0x9 = 0x7493220C  ;
    XVR_ANALOG_REG_BAK[9] = 0x7493220C;

    #if(LDO_MODE)
        addXVR_Reg0xa = 0x9C07785B;//0x9C27785B  ;
        XVR_ANALOG_REG_BAK[0xa] = 0x9C07785B;//0x9C27785B;
    #else
        addXVR_Reg0xa = 0x9C03785F;//0x9C27785B  ;
        XVR_ANALOG_REG_BAK[0xa] = 0x9C03785F;//0x9C27785B;
    #endif
    addXVR_Reg0xb = 0x0FD93F23  ;
    XVR_ANALOG_REG_BAK[0xb] = 0x0FD93F23;
    addXVR_Reg0xc = 0x80001008  ;
    XVR_ANALOG_REG_BAK[0xc] = 0x80001008;
    addXVR_Reg0xd = 0xCC42BF23  ;
    XVR_ANALOG_REG_BAK[0xd] = 0xCC42BF23;
    addXVR_Reg0xe = 0x00309350  ;
    XVR_ANALOG_REG_BAK[0xe] = 0x00309350;
    addXVR_Reg0xf = 0x3126E978  ;
    XVR_ANALOG_REG_BAK[0xf] = 0x3126E978;
 

    addXVR_Reg0x1c = 0x999CDDC5  ;XVR_ANALOG_REG_BAK[0x1c] = 0x999CDDC5;
    addXVR_Reg0x1d = 0xEA8501C0  ;XVR_ANALOG_REG_BAK[0x1d] = 0xEA8501C0;

    addXVR_Reg0x1e = 0x00010180  ;XVR_ANALOG_REG_BAK[0x1e] = 0x00010180; //xtal 32k

    addXVR_Reg0x1f = 0x00000000  ;XVR_ANALOG_REG_BAK[0x1f] = 0x00000000;
  
    addXVR_Reg0x20 = 0x8E89BED6;// REG_20
    addXVR_Reg0x21 = 0x96000000;//0x96000000;// REG_21
    addXVR_Reg0x22 = 0x78000000;// REG_22
    addXVR_Reg0x23 = 0xA0000000;// REG_23
    addXVR_Reg0x24 = 0x000a0202;//0x000A0782;// REG_24
    addXVR_Reg0x25 = 0X00200000;// REG_25
    addXVR_Reg0x26 = 0x10200502;// REG_26 0x10200502 0x14a40505
    addXVR_Reg0x27 = 0x0008C900;// REG_27
    addXVR_Reg0x28 = 0x01011010;// REG_28
    addXVR_Reg0x29 = 0x3C104E00;// REG_29
    addXVR_Reg0x2a = 0x0e103830;//0x0e10404d;//0x0e103D68;// REG_2A
    addXVR_Reg0x2b = 0x00000408;// REG_2B
    //addXVR_Reg0x2c = 0x006A404d;// REG_2C   //0x006a404d
    addXVR_Reg0x2d = 0x082CC446;// REG_2D 0x082CC444
    addXVR_Reg0x2e = 0x00000100;//0x00000000;// REG_2E
    addXVR_Reg0x2f = 0X00000000;// REG_2F

    addXVR_Reg0x30 = 0x10010001;// REG_30
    addXVR_Reg0x31 = 0X00000000;// REG_31
    addXVR_Reg0x32 = 0X00000000;// REG_32
    addXVR_Reg0x33 = 0X00000000;// REG_33
    addXVR_Reg0x34 = 0X00000000;// REG_34
    addXVR_Reg0x35 = 0X00000000;// REG_35
    addXVR_Reg0x36 = 0X00000000;// REG_36
    addXVR_Reg0x37 = 0X00000000;// REG_37
    addXVR_Reg0x38 = 0X00000000;// REG_38
    addXVR_Reg0x39 = 0X00000000;// REG_39
    addXVR_Reg0x3a = 0x00128000;// REG_3A
    addXVR_Reg0x3b = 0x36341048;// REG_3B 0x22341048
    addXVR_Reg0x3c = 0x01FF1c80;// REG_3C
    addXVR_Reg0x3d = 0x00000000;// REG_3D
    addXVR_Reg0x3e = 0X0000D940;// REG_3E
    addXVR_Reg0x3f = 0X00000000;// REG_3F

    addXVR_Reg0x40 = 0x01000000;// REG_40
    addXVR_Reg0x41 = 0x07050402;// REG_41
    addXVR_Reg0x42 = 0x120F0C0A;// REG_42
    addXVR_Reg0x43 = 0x221E1A16;// REG_43
    addXVR_Reg0x44 = 0x35302B26;// REG_44
    addXVR_Reg0x45 = 0x4B45403A;// REG_45
    addXVR_Reg0x46 = 0x635D5751;// REG_46
    addXVR_Reg0x47 = 0x7C767069;// REG_47
    addXVR_Reg0x48 = 0x968F8983;// REG_48
    addXVR_Reg0x49 = 0xAEA8A29C;// REG_49
    addXVR_Reg0x4a = 0xC5BFBAB4;// REG_4A
    addXVR_Reg0x4b = 0xD9D4CFCA;// REG_4B
    addXVR_Reg0x4c = 0xE9E5E1DD;// REG_4C
    addXVR_Reg0x4d = 0xF5F3F0ED;// REG_4D
    addXVR_Reg0x4e = 0xFDFBFAF8;// REG_4E
    addXVR_Reg0x4f = 0xFFFFFFFE;// REG_4F
    
    
    
    
    
        
    addPMU_Reg0x10 |= (0X1 << 8);
    addPMU_Reg0x12 &= ~(0X1 << 8);
    
    addPMU_Reg0x13 = 0XFFFFFF80;
    
    kmod_calibration();
    
    
#if (INTER_RC32K)
    XVR_ANALOG_REG_BAK[9] &= ~(0x01 << 26);
    addXVR_Reg0x9 = XVR_ANALOG_REG_BAK[9];

    XVR_ANALOG_REG_BAK[0x1e]  |= 0x80000000;
    addXVR_Reg0x1e = XVR_ANALOG_REG_BAK[0x1e];
    CLK32K_AutoCali_init();
    Delay_ms(50);
#endif
      
     

    //addXVR_Reg0x6 = 0x84a7cc00;XVR_ANALOG_REG_BAK[0x6] = 0x84a7cc00;
    addXVR_Reg0x7 = 0xeA023FC0;XVR_ANALOG_REG_BAK[0x7] = 0xeA023FC0;  
    //addXVR_Reg0xa = 0x9C03785f;XVR_ANALOG_REG_BAK[0xa] = 0x9C03785f;
    addXVR_Reg0x1c = 0x999CDDC5;XVR_ANALOG_REG_BAK[0x1c] = 0x999CDDC5;

}

void  xvr_reg_initial_24(void)
{

   addXVR_Reg0x2c = 0x0a6a5c71;//0x006A404d;// REG_2C   //0x006a404d
   addXVR_Reg0x2d = 0x082ac441;//0x082CC446;// REG_2D 0x082CC444

}


void Delay_us(int num)
{
    int x, y;
    for(y = 0; y < num; y ++ )
    {
        for(x = 0; x < 10; x++);
    }
}

void Delay(int num)
{
    int x, y;
    for(y = 0; y < num; y ++ )
    {
        for(x = 0; x < 50; x++);
    }
}

void Delay_ms(int num) //sync from svn revision 18
{
    int x, y;
    for(y = 0; y < num; y ++ )
    {
        for(x = 0; x < 3260; x++);
    }

}



void kmod_calibration(void) 
{

/* 1、在初始化0X26的 [16:28] = 0x1084 
			2、在0X30的BT 设置成 BT = 1去校准
	
		3、校准完成后将在0X30的BT 设置成 BT = 0.5
	
	
	*/

    uint32_t value;
    uint32_t value_kcal_result;


    addXVR_Reg0x24 &= ~(0x1 << 17);
    Delay_ms(10);
    addXVR_Reg0x24 &= ~(0x7f);
    Delay_ms(10);
    addXVR_Reg0x25 |= (1<<12);
    Delay_ms(10);
    addXVR_Reg0x25 |= (1<<13);
    Delay_ms(10);
    addXVR_Reg0x25 |= (1<<11);
    Delay_ms(10);
    XVR_ANALOG_REG_BAK[3] &= ~(0x1 << 6);
    addXVR_Reg0x3 = XVR_ANALOG_REG_BAK[3];
    Delay_ms(10);
    XVR_ANALOG_REG_BAK[3] |= (0x1 << 7);
    addXVR_Reg0x3 = XVR_ANALOG_REG_BAK[3];
    Delay_ms(10);
    addXVR_Reg0x25 |= (1<<16);
    Delay_ms(50);
    value = addXVR_Reg0x12;

    value = ((value >> 16) & 0x1fff);

    value_kcal_result =  ((256*250/value)&0x1ff) ; 
    addXVR_Reg0x30 &= (~(0x1ff<<8));
    addXVR_Reg0x30 |= (value_kcal_result<<8);
    Delay_ms(50);

    addXVR_Reg0x25 &= ~(1<<16);
    XVR_ANALOG_REG_BAK[3] &= ~(0x1 << 7);
    addXVR_Reg0x3 = XVR_ANALOG_REG_BAK[3];
    Delay_ms(10);

    XVR_ANALOG_REG_BAK[3] |= (0x1 << 6);
    addXVR_Reg0x3 = XVR_ANALOG_REG_BAK[3];
    addXVR_Reg0x25 &= ~(1<<11);

    addXVR_Reg0x25 &= ~(1<<13);
    addXVR_Reg0x25 &= ~(1<<12); 
    addXVR_Reg0x24 |= (0x1 << 17);
    
    
}


void CLK32K_AutoCali_init(void)
{
    XVR_ANALOG_REG_BAK[0xc] &= ~(0x01 << 15);
    addXVR_Reg0xc = XVR_ANALOG_REG_BAK[0xc]; 

    XVR_ANALOG_REG_BAK[0xc] |= (0x01 << 15);
    addXVR_Reg0xc = XVR_ANALOG_REG_BAK[0xc];

    XVR_ANALOG_REG_BAK[0xc] |= (0x1388 << 16);
    XVR_ANALOG_REG_BAK[0xc] |= (0x1 << 14);    
    addXVR_Reg0xc = XVR_ANALOG_REG_BAK[0xc]; 
    addXVR_Reg0xc = 0x13881004; 
    Delay_ms(10);
    XVR_ANALOG_REG_BAK[0xc] = 0x1388d004;
    addXVR_Reg0xc = 0x1388d004;
}


//配置单载波发射
//freq:频点设置，双频点(2-80)
//power:功率等级(0x1-0xf)
void singleWaveCfg(uint8_t freq, uint8_t power_level)
{
	uint32_t val = 0;
    uint32_t reg = XVR_ANALOG_REG_BAK[0x04];
	
	addXVR_Reg0x4 = reg | (0x1 << 29);
    
	val |= freq;
	val |= (power_level<< 7);
	addXVR_Reg0x24 = val;
	addXVR_Reg0x25 |= (0x1<<12) |(0x1<<13);

	while(1);
}


//修改发射功率
//power_level:功率等级(0x0-0xf)
void set_power(uint8_t power_level)
{
	uint32_t val = 0;
	uint32_t reg = XVR_ANALOG_REG_BAK[0x04];

	addXVR_Reg0x24 &= ~(0x1 << 20);
	addXVR_Reg0x4 = reg | (0x1 << 29);
	val |= (power_level << 7);
	addXVR_Reg0x24 &= ~(0xf << 7);
	addXVR_Reg0x24 |= val;
}

///晶体频偏调整
///cal_data默认为0x35,最大为0x7f
void xtal_cal_set(uint8_t cal_data)
{
    if(cal_data>0x7f)
        cal_data=0x7f;
    XVR_ANALOG_REG_BAK[3] = 0x60000C62|(cal_data<<12);
    addXVR_Reg0x3 = XVR_ANALOG_REG_BAK[3] ;
}








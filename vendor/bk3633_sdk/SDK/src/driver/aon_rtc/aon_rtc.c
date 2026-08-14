/**
****************************************************************************************
* @addtogroup RTC
* @ingroup beken corp
* @brief RTC
* @author Alen
*
* This is the driver block for RTC
* @{
****************************************************************************************
*/


#include <stdint.h>        // standard integer definition
#include <string.h>        // string manipulation
#include <stddef.h>        // standard definition
#include "aon_rtc.h"
#include "user_config.h"
#include "BK3633_RegList.h"
#include "uart2.h"


#if(AON_RTC_DRIVER)

void aon_rtc_init(void)
{
    setf_rtc_aon_Reg0x0_rtc_clk_en ;  //enable rtc clk
    
    addrtc_aon_Reg0x1 = AON_RTC_1000MS;//AON_RTC_UP_VALUE;// set up_val
    addrtc_aon_Reg0x2 = AON_RTC_1000MS;//set  tick_val
    
    setf_rtc_aon_Reg0x0_rtc_aon_int  ;  // clear aon int
    setf_rtc_aon_Reg0x0_rtc_tick_int ;  //clear tick int
    setf_rtc_aon_Reg0x0_rtc_tick_int_en  ;       //rtc tick_int_enable
    setf_rtc_aon_Reg0x0_rtc_aon_int_en	 ;		   // rtc aon_int_enable

    setf_SYS_Reg0x10_int_aon_rtc_en  ;   // rtc int enable

}

static unsigned int rtc_cnt=0;

void aon_rtc_isr(void)
{   
    setf_rtc_aon_Reg0x0_rtc_tick_int ;     

    uart_printf("rtc_cnt=%d\n",rtc_cnt++); 
    //uart_printf("rtc_cnt=%d\n",ip_slotclk_sclk_getf());
    //ip_slotclk_sclk_setf(0x10000);   
    //uart_printf("rtc_cnt=%d\n",ip_slotclk_sclk_getf());
    
}



#endif




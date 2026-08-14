#include "bim_updataImage.h"
#include "bim_app.h"
#include "bim_uart2.h"
#include "bim_flash.h"
#include "bim_icu.h"
#include "bim_wdt.h"


#if defined(__CC_ARM)
const  unsigned int BK36[] __attribute__((at(0x100)))= 
{
    0x36334B42,0x00103333,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,
    0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000
};
#else
volatile  unsigned int BK36[] __attribute__((section(".section_bk")))=
{
    0x36334B42,0x00103333,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,
    0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000,0x00000000
};

#endif

typedef void (*FUNCPTR)(void);


void bim_main(void)
{
    icu_init();
    wdt_disable();
    uart2_init(1000000);
    flash_advance_init();
    bim_printf("boot_start\r\n");
    

    if( 1 == bim_select_sec() )
    {
        (*(FUNCPTR)SEC_IMAGE_RUN_STACK_CADDR)();
    }
    else
    {
        while(1)
        {
            bim_printf("error_start\r\n");
        }
    }
    
}






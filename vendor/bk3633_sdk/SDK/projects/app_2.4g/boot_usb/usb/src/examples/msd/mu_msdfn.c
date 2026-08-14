/*************************************************************
 * @file        Mu_msdfn.c
 * @brief       code of USB multifunctional composite peripheral of BK3435_v2
 * @author      GuWenFu
 * @version     V1.0
 * @date        2016-09-29
 * @par
 * @attention
 *
 * @history     2016-09-29 gwf    create this file
 */

/*
 * multifunctional composite peripheral
 */

#include "mu_arch.h"
#include "mu_cdi.h"
#include "mu_diag.h"
#include "mu_mem.h"


/******************************************************************
Defines
******************************************************************/
#define STATIC
//#define STATIC static


#define INTERFACE_NUM           1

#define HIDS_KB_REPORT_ID       1
#define HIDS_MOUSE_REPORT_ID    5
#define RMC_VENDOR_REPORT_ID_1  0xfd
#define RMC_VENDOR_REPORT_ID_2   0x1e
#define HIDS_MM_KB_REPORT_ID     3
#define RMC_SENSORS_DATA_REPORT_ID  0x32 
#define OUTPUT_REPORT   	0xBA

#define HIDS_PWR_KB_REPORT_ID   4


/******************************************************************
Forwards
******************************************************************/
STATIC uint8_t MGC_McpDeviceRequest(void* hClient, MUSB_BusHandle hBus, 
				    uint32_t dwSequenceNumber, 
				    const uint8_t* pSetup, 
				    uint16_t wRequestLength);
STATIC uint8_t MGC_McpDeviceConfigSelected(void* hClient, 
					   MUSB_BusHandle hBus, 
					   uint8_t bConfigurationValue, 
					   MUSB_Pipe* ahPipe);
STATIC void MGC_McpNewUsbState(void* hClient, MUSB_BusHandle hBus, 
			       MUSB_State State);

/******************************************************************
Globals
******************************************************************/

STATIC uint8_t MGC_bMcpSelfPowered = FALSE;
STATIC MUSB_State MGC_eMcpUsbState = MUSB_POWER_OFF;

STATIC uint8_t MGC_aControlData[256];


const uint8_t gHidReportDescriptor[] =
{
/*
06 a0 ff 09  01 
a1 01 09  02 a1 
00 09  03 09 04 
15 00 26 ff 00  
35 00 45 ff  75 
08 95 40  81 02 
09 05 09 06 15 
00  26 ff 00 35  
00 45 ff 75  08 
95 40 91 02 c0 c0              
*/
0x06, 0xa0, 0xff, 
0x09, 0x01 , 
0xa1 , 0x01 , 
0x09, 0x02 , 
0xa1 , 0x00 , 
0x09  , 0x03 , 
0x09 , 0x04 , 
0x15, 0x00 , 
0x26, 0xff , 0x00  , 
0x35 , 0x00 , 
0x45, 0xff  ,
0x75 , 0x08, 
0x95 , 0x40, 
0x81 , 0x02 , 
0x09 , 0x05, 
0x09 , 0x06 , 
0x15 ,0x00  , 
0x26 , 0xff , 0x00 , 
0x35  ,0x00 , 
0x45 , 0xff , 
0x75  , 0x08 , 
0x95 , 0x40 , 
0x91, 0x02 , 
0xc0 , 0xc0                                     
};

unsigned long ulgHidReportDescriptorLen = sizeof(gHidReportDescriptor);


STATIC CONST uint8_t MGC_aDescriptorData[] = 
{
    /* Device Descriptor */
    0x12,                      /* bLength              */
    MUSB_DT_DEVICE,            /* DEVICE               */
    0x00,0x01,                 /* USB 1.0              */
    0x00,                      /* CLASS                */
    0x00,                      /* Subclass             */
    0x00,                      /* Protocol             */
    0x40,                      /* bMaxPktSize0         */
    
	//0x56,0x02,                 /* idVendor             */
	// 0x34,0x20,                 /* idProduct            */

	0x45,0xA7,                 /* idVendor             */
	0x33,0x00,                 /* idProduct            */
   
    0x00,0x00,                 /* bcdDevice            */
    0x00,                      /* iManufacturer        */
    0x00,                      /* iProduct             */
    0x00,                      /* iSerial Number       */
    0x01,                      /* One configuration    */

    /* strings */
    2+2,
    MUSB_DT_STRING,
    0x09, 0x04,			/* English (U.S.) */

    /* TODO: make tool to generate strings and eventually whole descriptor! */
    /* English (U.S.) strings */
    2+18,			/* Manufacturer: Mentor Graphics */
    MUSB_DT_STRING,
    'b', 0, 'e', 0, 'k', 0, 'e', 0, 'n', 0, ' ', 0,
    'g', 0, 'w', 0, 'f', 0, 

    2+8,			/* Product ID: Demo */
    MUSB_DT_STRING,
    'D', 0, 'e', 0, 'm', 0, 'o', 0,

    2+24,			/* Serial #: 123412341234 */
    MUSB_DT_STRING,
    '1', 0, '2', 0, '3', 0, '4', 0,
    '5', 0, '6', 0, '7', 0, '8', 0,
    '9', 0, 'a', 0, 'b', 0, 'c', 0,

    /* configuration */
    0x09,                                   /* bLength              */
    0x02,                                   /* CONFIGURATION        */
    (uint8_t)9+(9+7*2+9)*INTERFACE_NUM, 0x00,          /* length               */
    (uint8_t)INTERFACE_NUM,                 /* bNumInterfaces       */
    0x01,                                   /* bConfigurationValue  */
    0x00,                                   /* iConfiguration       */
    0x80,                                   /* bmAttributes (required + self-powered) */
    0x0f,                                   /* power                */

    /*
    // interface    mouse
    0x09,                                   // bLength            
    0x04,                                   // INTERFACE        
    0x00,                                   //bInterfaceNumber     
    0x00,                                   //bAlternateSetting    
    0x01,                                   //bNumEndpoints        
    0xff,                                   // bInterfaceClass      
    0xff,                                   //bInterfaceSubClass (1=RBC, 6=SCSI)
    0xff,                                   //bInterfaceProtocol (BOT)
    0x00,                                   // iInterface          
    */
    
   
   // ------ Mouse ---------------------
    0x09,                                   //bLength              
    0x04,                                   //INTERFACE           
    0x00,                                   //bInterfaceNumber    
    0x00,                                   // bAlternateSetting 
    0x02,//NumEndpoints
    0x03,//HID
    0x00,//
    0x00,//
    0x00,//

    //add 180720
    0x09,//
    0x21,//
    0x00,0x01,                          // bcdHID
    0x00,//
    0x01,//
    0x22,// Report Descriptor
    sizeof(gHidReportDescriptor),0x00,//  0x39,bDescriptorLength

    //Endpoint Descriptor  : In
    0x07,
    0x05,
    0x81, //Endpoint 2, IN direction
    0x03,       //Interrupt
    0x40,0x00,  //wMaxPacketSize
    0x03,  
     
    //Endpoint Descriptor  : Out 
    0x07,                                  	// bLength              
    0x05,                                   //ENDPOINT             
    0x02,                                  	// bEndpointAddress      
    0x03,                                  	// bmAttributes
    0x40, 0x00,                         	// wMaxPacketSize  
    0x03                                   	// bInterval          
    
};


unsigned long ulMGC_aDescriptorDataLen = sizeof(MGC_aDescriptorData);
const uint8_t *pMGC_aDescriptorData = MGC_aDescriptorData;

STATIC uint8_t MGC_bMcpInterface = 0;

STATIC MUSB_Irp MGC_McpUsbRxDataIrp = 
{
    NULL,
    NULL,
    0,
    0,
    0,
    NULL,
    NULL,
    FALSE,	/* bAllowShortTransfer */
    TRUE,	/* bIsrCallback */
    FALSE	/* bAllowDma */
};

STATIC MUSB_Irp MGC_McpUsbTxDataIrp = 
{
    NULL,
    NULL,
    0,
    0,
    0,
    NULL,
    NULL,
    FALSE,	/* bAllowShortTransfer */
    TRUE,	/* bIsrCallback */
    FALSE	/* bAllowDma */
};

// by gwf   STATIC uint8_t MGC_aJunk[1];//[512];
uint8_t MGC_RX_Buffer[64];
uint8_t MGC_TX_Buffer[64];

/*
* registration
*/
MUSB_FunctionClient MGC_McpFunctionClient =
{
    NULL,	/* no instance data; we are singleton */
    MGC_aDescriptorData,
    sizeof(MGC_aDescriptorData),
    3,		/* strings per language */
    NULL,
    0,
    sizeof(MGC_aControlData),
    MGC_aControlData,
    &MGC_bMcpSelfPowered,
    MGC_McpDeviceRequest,
    MGC_McpDeviceConfigSelected,
    NULL,
    MGC_McpNewUsbState
};

//STATIC uint8_t MGC_aMcpData[4*1024+64];//[1024+512];


#define JTAG_GET_IDCODE_CMD         0xA0
#define JTAG_MID_READ_CMD           0xA1
#define JTAG_MID_WRITE_CMD          0xA2
#define JTAG_STALL_CMD              0xA3
#define JTAG_UNSTALL_CMD            0xA4
#define JTAG_CHIP_ERASE_CMD         0xA5
#define JTAG_READ_ALL_CMD           0xA6
#define JTAG_SPR_READ_CMD           0xA7
#define JTAG_SPR_WRITE_CMD          0xA8
#define JTAG_FLASH_WRITE_START      0xA9
#define JTAG_FLASH_WRITE_DATA       0xAA
#define JTAG_FLASH_WRITE_END        0xAB
#define JTAG_FLASH_READ_START       0xAC
#define JTAG_FLASH_READ_DATA        0xAD
#define JTAG_SECTOR_ERASE_CMD       0xB0



////////////// for user ///////////////////////
STATIC volatile uint8_t b_isConnected = FALSE;
volatile uint8_t b_isTRxing = FALSE;
volatile uint8_t b_isDataing = FALSE;

void USBD_StartRx()
{	
	while(b_isTRxing == TRUE)
	{
	    //bim1_uart_printf("tran rx\r\n");
	}
	//bim1_uart_printf("tran 9\r\n");
//	DEBUG_MSG(0X79);
	///b_isTRxing = TRUE;
	MGC_McpUsbRxDataIrp.dwActualLength = 0;
	MUSB_StartTransfer(&MGC_McpUsbRxDataIrp);
}

void USBD_StartTx(unsigned char *pBuf, unsigned long ulLen)
{
    unsigned char *pBufTemp = pBuf;
	unsigned long ulLenTemp;    
	b_isTRxing = FALSE;
	do
	{
		//bim1_uart_printf("index 33\r\n");
		if (b_isTRxing == TRUE)
		{
			//bim1_uart_printf("index 35\r\n");
			//continue;
		}
		ulLenTemp = MIN(ulLen, 64);
		//b_isTRxing = TRUE;
		MGC_McpUsbTxDataIrp.pBuffer = pBufTemp;
		MGC_McpUsbTxDataIrp.dwLength = ulLenTemp;
		MGC_McpUsbTxDataIrp.dwActualLength = 0;
		MUSB_StartTransfer(&MGC_McpUsbTxDataIrp);
		//bim1_uart_printf("index 34\r\n");
		//bim1_uart_printf("ulLenTemp = %x\r\n",ulLenTemp);
		ulLen -= ulLenTemp;
		pBufTemp += ulLenTemp;
	} while (ulLen);
	b_isTRxing = TRUE;

}

STATIC uint32_t USBD_RxDataCallback(void* pCompleteParam, MUSB_Irp* pIrp)
{
    b_isTRxing = FALSE;
    b_isDataing = TRUE;
//    bim1_uart_printf("USBD_RxData Complete\r\n");
    return 0;
}

STATIC uint32_t USBD_TxDataCallback(void* pCompleteParam, MUSB_Irp* pIrp)
{
    b_isTRxing = FALSE;
    //bim1_uart_printf("USBD_TxData Complete\r\n");
    return 0;
}

void test_usb_device(void)
{
    if (b_isConnected == FALSE)
    {
        return ;
    }
    //bim1_uart_printf("call 2\r\n");
    USBD_StartRx();
}
////////////// for user ///////////////////////


/******************************************************************
CDI callbacks
******************************************************************/
STATIC void MGC_McpNewUsbState(void* hClient, MUSB_BusHandle hBus,
			       MUSB_State State)
{
//    MUSB_DPRINTF("MGC_McpNewUsbState: state = %x\r\n",State);
    MGC_eMcpUsbState = State;

    /* TODO: anything? */

    if (State == MUSB_CONFIGURED)
    {
        b_isConnected = TRUE;
    }
    else
    {
        b_isConnected = FALSE;
    }
}

STATIC uint8_t MGC_McpDeviceRequest(void* hClient, MUSB_BusHandle hBus,
				    uint32_t dwSequence, const uint8_t* pSetup,
				    uint16_t wLength)
{
	MUSB_DPRINTF("MGC_McpDeviceRequest\r\n");
       return TRUE;
}

STATIC uint8_t MGC_McpDeviceConfigSelected(void* hClient, MUSB_BusHandle hBus,
					   uint8_t bConfigurationValue,
					   MUSB_Pipe* ahPipe)
{
    MGC_McpUsbRxDataIrp.hPipe = ahPipe[1];
    MGC_McpUsbTxDataIrp.hPipe = ahPipe[0];

    MGC_McpUsbRxDataIrp.pBuffer = (uint8_t*)MGC_RX_Buffer;
    MGC_McpUsbRxDataIrp.dwLength = sizeof(MGC_RX_Buffer);

    MGC_McpUsbTxDataIrp.pBuffer = (uint8_t*)MGC_TX_Buffer;
    MGC_McpUsbTxDataIrp.dwLength = sizeof(MGC_TX_Buffer);

    b_isConnected = TRUE;
    MGC_McpUsbRxDataIrp.pfIrpComplete = USBD_RxDataCallback;
    MGC_McpUsbTxDataIrp.pfIrpComplete = USBD_TxDataCallback;
    test_usb_device();
	
    return TRUE;
}

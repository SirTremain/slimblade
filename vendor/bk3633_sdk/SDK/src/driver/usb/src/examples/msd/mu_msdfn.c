/*************************************************************
 * @file        Mu_mcp.c
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
#include "sdp_service_task.h"
#include "reg_blecore.h"
#include "user_config.h"
#include "app.h"
#include "flash.h"

int uart_printf(const char *fmt,...);
/******************************************************************
Defines
******************************************************************/
#define STATIC
//#define STATIC static
#define __ISOC_16K__


#define MUSIC_48KHZ_2CH_16BIT
//#define MUSIC_24KHZ_2CH_16BIT

#if USB_APP_CONFIG
#define INTERFACE_NUM           3
#else
#define INTERFACE_NUM           1
#endif

#define HIDS_KB_REPORT_ID       1
#define HIDS_MOUSE_REPORT_ID    5
#define RMC_VENDOR_REPORT_ID_1  0xFD
#define RMC_VENDOR_REPORT_ID_2  0x1E
#define ISOC_VENDOR_REPORT_ID_1 0x5A
#define ISOC_VENDOR_REPORT_ID_2 0x6B
#define HIDS_MM_KB_REPORT_ID     3
#define HIDS_PWR_KB_REPORT_ID   4

#define RMC_SENSORS_DATA_REPORT_ID  0x32
#define OUTPUT_REPORT   	0xBA


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

/* UCDI variables */
STATIC uint8_t MGC_bMcpSelfPowered = FALSE;
STATIC MUSB_State MGC_eMcpUsbState = MUSB_POWER_OFF;

STATIC uint8_t MGC_aControlData[256];

const uint8_t gHidKeyboardReportDescriptor[] =
{
#if 1
	// MicoSoft Keyboard
	0x05, 0x01, 
	0x09, 0x06, 
	0xA1, 0x01, 
	0x85, HIDS_KB_REPORT_ID,	//0x02, 
	0x15, 0x00, 
	0x25, 0x01, 
	0x05, 0x07, 
	0x1A, 0xE0, 0x00,
	0x2A, 0xE7, 0x00, 
	0x75, 0x01, 
	0x95, 0x08, 
	0x81, 0x02, 
	0x05, 0x07, 
	0x19, 0x00, 
	0x2A, 0x91, 0x00, 
	0x16, 0x00, 0x00, 
	0x26, 0xFF, 0x00, 
	0x75, 0x08, 
	0x95, 0x0A, 
	0x81, 0x00, 
	0xC0,

#else
    0x05, 0x01,        // Usage Page (Generic Desktop),
    0x09, 0x06,        // Usage (Keyboard),
    0xA1, 0x01,        // Collection (Application),
    0x85, HIDS_KB_REPORT_ID,	 // HIDS_KB_REPORT_ID,
    0x05, 0x07,        // Usage Page (Key Codes);
    0x19, 0xE0,        // Usage Minimum (224),
    0x29, 0xE7,        // Usage Maximum (231),
    0x15, 0x00,        // Logical Minimum (0),
    0x25, 0x01,        // Logical Maximum (1),
    0x75, 0x01,        // Report Size (1),
    0x95, 0x08,        // Report Count (8),
    0x81, 0x02,        // Input (Data, Variable, Absolute), ;Modifier byte
    0x95, 0x01,        // Report Count (1),
    0x75, 0x08,        // Report Size (8),
    0x81, 0x01,        // Input (Constant), ;Reserved byte
    0x95, 0x05,        // Report Count (5),
    0x75, 0x01,        // Report Size (1),
    0x05, 0x08,        // Usage Page (Page# for LEDs),
    0x19, 0x01,        // Usage Minimum (1),
    0x29, 0x05,        // Usage Maximum (5),
    0x91, 0x02,        // Output (Data, Variable, Absolute), ;Led report
    0x95, 0x01,        // Report Count (1),
    0x75, 0x03,        // Report Size (3),
    0x91, 0x01,        // Output (Constant), ;Led report padding
    0x95, 0x06,        // Report Count (6),
    0x75, 0x08,        // Report Size (8),
    0x15, 0x00,        // Logical Minimum (0),
    0x25, 0xff,        // Logical Maximum(101),
    0x05, 0x07,        // Usage Page (Key Codes),
    0x19, 0x00,        // Usage Minimum (0),
    0x29, 0xff,        // Usage Maximum (101),
    0x81, 0x00,        // Input (Data, Array), ;Key arrays (6 bytes)
    0xC0,                  // End Collection
#endif
#if 1    
    // MicoSoft Mouse 
	0x05, 0x01, 
	0x09, 0x02, 
	0xA1, 0x01, 
	0x05, 0x01, 
	0x09, 0x02, 
	0xA1, 0x02, 
	0x85, HIDS_MOUSE_REPORT_ID, 
	0x09, 0x01, 
	0xA1, 0x00, 
	0x05, 0x09, 
	0x19, 0x01, 
	0x29, 0x05, 
	0x15, 0x00, 
	0x25, 0x01, 
	0x95, 0x05, 
	0x75, 0x01, 
	0x81, 0x02, 
	0x95, 0x01, 
	0x75, 0x03, 
	0x81, 0x01, 
	0x05, 0x01, 
	0x09, 0x30, 
	0x09, 0x31, 
	0x95, 0x02, 
	0x75, 0x10, 
	0x16, 0x01, 0x80, 
	0x26, 0xFF, 0x7F, 
	0x81, 0x06, 
	0xA1, 0x02, 
	0x85, HIDS_MOUSE_REPORT_ID, 
	0x09, 0x38, 
	0x35, 0x00, 
	0x45, 0x00, 
	0x95, 0x01, 
	0x75, 0x10, 
	0x16, 0x01, 0x80, 
	0x26, 0xFF, 0x7F, 
	0x81, 0x06, 
	0x85, HIDS_MOUSE_REPORT_ID,
	0x05, 0x0C, 
	0x95, 0x01, 
	0x75, 0x10, 
	0x16, 0x01, 0x80, 
	0x26, 0xFF, 0x7F, 
	0x0A, 0x38, 0x02, 
	0x81, 0x06, 
	0xC0, 
	0xC0, 
	0xC0, 
	0xC0, 
#else
	0x05, 0x01, 		// Usage Page (Generic Desktop)
	0x09, 0x02, 		// Usage (Mouse)
	0xA1, 0x01, 		// Collection (Application)
	0x85, HIDS_MOUSE_REPORT_ID,//0x01, 		// Report Id (1)	
	0x09, 0x01, 		// Usage (Pointer)	
	0xA1, 0x00, 		// Collection (Physical)
	0x05, 0x09, 		// Usage Page (Button)
	0x19, 0x01, 		// Usage Minimum (Button 1)	
	0x29, 0x05, 		// Usage Maximum (Button 5)
	0x15, 0x00, 		// Logical minimum (0)
	0x25, 0x01, 		// Logical maximum (1)
	0x95, 0x05, 		// Report Count (5)
	0x75, 0x01, 		// Report Size (1)
	0x81, 0x02, 		// Input (Data,Value,Absolute,Bit Field)
	0x95, 0x01, 		// Report Count (1)		
	0x75, 0x03, 		// Report Size (3)	
	0x81, 0x01, 		// Input (Constant,Array,Absolute,Bit Field)
	0x05, 0x01, 		// Usage Page (Generic Desktop)
	0x09, 0x30, 		// Usage (X)	
	0x09, 0x31, 		// Usage (Y)	
	0x16, 0x01, 0xF8, 	// Logical minimum (-2'047)		
	0x26, 0xFF, 0x07, 	// Logical maximum (2'047)	
	0x75, 0x0C, 		// Report Size (12)	
	0x95, 0x02, 		// Report Count (2	
	0x81, 0x06, 		// Input (Data,Value,Relative,Bit Field)
	0x09, 0x38, 		// Usage (Wheel)
	0x15, 0x81, 		// Logical minimum (-127)	
	0x25, 0x7F, 		// Logical maximum (127)	
	0x75, 0x08, 		// Report Size (8)	
	0x95, 0x01, 		// Report Count (1)
	0x81, 0x06, 		// Input (Data,Value,Relative,Bit Field)
	0xC0, 				// End Collection
	0xC0,				// End Collection

#endif
    // MULTIMEDIA_KEYBOARD
	 0x05, 0x0c,		   // USAGE_PAGE (Consumer Devices)
	 0x09, 0x01,		   // USAGE (Consumer Control)
	 0xa1, 0x01,		   // COLLECTION (Application)
	 0x85, HIDS_MM_KB_REPORT_ID,  // REPORT_ID (1)
	 0x19, 0x00,		  //USAGE_MINIMUM (0)
	 0x2A, 0x9c, 0x02,	  //USAGE_MAXIMUM (29c)
	 0x15, 0x00,		  //LOGICAL_MINIMUM (0)
	 0x26, 0x9c, 0x02,	  //LOGICAL_MAXIMUM (29c)
	 0x95, 0x01,		  //REPORT_COUNT (1)
	 0x75, 0x10,		  //REPORT_SIZE (16)
	 0x81, 0x00,		  //INPUT (Data,Ary,Abs)
	 0xc0,
};
unsigned long ulgHidKeyboardReportDescriptorLen = sizeof(gHidKeyboardReportDescriptor);


const uint8_t gHidMouseReportDescriptor[] =
{
// mouse
   /* 0x05, 0x01,
    0x09, 0x02,
    0xa1, 0x01,
    0x85, HIDS_MOUSE_REPORT_ID,	 // HIDS_MOUSE_REPORT_ID,
    0x09, 0x01,
    0xa1, 0x00,
    0x05, 0x09,
    0x19, 0x01,
    0x29, 0x03,
    0x15, 0x00,
    0x25, 0x01,
    0x95, 0x03,
    0x75, 0x01,
    0x81, 0x02,
    0x95, 0x01,
    0x75, 0x05,
    0x81, 0x01,
    0x05, 0x01,
    0x09, 0x30,
    0x09, 0x31,
    0x09, 0x38,
    0x15, 0x81,
    0x25, 0x7f,
    0x75, 0x08,
    0x95, 0x03,
    0x81, 0x06,
    0xc0,
    0xc0,*/
  /*  0x06, 0x00, 0xff,              // USAGE_PAGE (Vendor Defined Page 1)
    0x09, 0x0e,                    // USAGE (Vendor Usage 1)
    0xa1, 0x01,                    // COLLECTION (Application)
    0x85, OUTPUT_REPORT,      // Report ID
    0x95, 0x40,  //   REPORT_COUNT ( )
    0x75, 0x08,                    //   REPORT_SIZE (8)
    0x26, 0xff, 0x00,              //   LOGICAL_MAXIMUM (255)
    0x15, 0x00,                    //   LOGICAL_MINIMUM (0)
    0x09, 0x01,                    //   USAGE (Vendor Usage 1)
    0x91, 0x02,

    0x85, INPUT_REPORT,         //   Report ID
    0x95, 0x40,         //   REPORT_COUNT ( )
    0x75, 0x08,         //   REPORT_SIZE (8)
    0x26, 0xff, 0x00,//   LOGICAL_MAXIMUM (255)
    0x15, 0x00,         //   LOGICAL_MINIMUM (0)
    0x09, 0x01,         //   USAGE (Vendor Usage 1)
    0x81, 0x02,         //   INPUT (Data,Var,Abs)
    0xC0,                //   end Application Collection};*/
 /*   0x06, 0xa0, 0xff, 
0x09, 0x01 , 
0xa1 , 0x01 , 
0x09, 0x02 , 
0xa1 , 0x00 , 
0x09  , 0x03 , 
0x09 , 0x04 , 
0x15, 0x00 , 
0x26, 0xff , 0x00  , 
0x35 , 0x00 , 
0x45 , 0xff  , 0x75 , 
0x08 , 0x95 , 
0x40  , 0x81 , 0x02 , 
0x09 , 0x05, 
0x09 , 0x06 , 
0x15 ,0x00  , 
0x26 , 0xff , 0x00 , 
0x35  ,0x00 , 
0x45 , 0xff , 
0x75  , 0x08 , 
0x95 , 0x40 , 
0x91, 0x02 , 
0xc0 , 0xc0      */    
    /*0x06, 0xa0, 0xff, 
    0x09, 0x01 , 
    0xa1 , 0x01 , 
    0x09, 0x02 , 
    0xa1 , 0x00 , 
    0x09  , 0x03 , 
    0x09 , 0x04 , 
    0x15, 0x00 , 
    0x26, 0xff , 0x00  , 
    0x35 , 0x00 , 
    0x45 , 0xff  , 0x75 , 
    0x08 , 0x95 , 
    0x40  , 0x81 , 0x02 , 
    
    0x09 , 0x05, 
    0x09 , 0x06 , 
    0x15 ,0x00  , 
    0x26 , 0xff , 0x00 , 
    0x35  ,0x00 , 
    0x45 , 0xff , 
    0x75  , 0x08 , 
    0x95 , 0x40 , 
    0x91, 0x02 , 
    0xc0 , 0xc0   */
    /*0x06 ,0x00 ,0xFF ,0x09 ,0x00 ,0xA1 ,0x01 ,0x15 ,0x00 ,0x25
    ,0xFF ,0x19 ,0x01 ,0x29 ,0x08 ,0x95 ,0x40 ,0x75 ,0x08 ,0x81
    ,0x02 ,0x19 ,0x01 ,0x29 ,0x08 ,0x91 ,0x02 ,0xC0*/
    
    0x06 ,0x00 ,0xFF ,
    0x09 ,0x00 ,
    0xA1 ,0x01 ,
    0x15 ,0x00 ,
    0x25 ,0xFF,
    0x19 ,0x01 ,
    0x29 ,0x08 ,
    0x75 ,0x08 ,
    0x95 ,0x40 ,
    0x81 ,0x02 ,
    0x19,0x01 ,
    0x29 ,0x08 ,
    0x91 ,0x02 ,
    0xC0,   

};
unsigned long ulgHidMouseReportDescriptorLen = sizeof(gHidMouseReportDescriptor);

const uint8_t gHidISOCVoiceReportDescriptor[] =
{
    0x05, 0x0c,            //Usage Page
    0x09, 0x01,            //Usage
    0xa1, 0x01,            //Collection

    0x09, 0xea,            //Usage vol dec
    0x09, 0xe9,            //Usage vol inc
    0x09, 0xe2,            //Usage audio mute
    0x09, 0xb7,            //Usage stop
    0x09, 0xcc,            //Usage stop/enject
    0x09, 0xcd,            //Usage play/pause
    0x09, 0xb6,            //Usage prev
    0x09, 0xb5,            //Usage next

    0x0a, 0x01, 0xa3,
    0x0a, 0x01, 0x51,
    0x0a, 0x01, 0x52,      //base increment
    0x0a, 0x01, 0x53,
    0x0a, 0x01, 0x54,
    0x0a, 0x01, 0x55,

    0x15, 0x00,            //Logical Minimum
    0x25, 0x01,            //Logical Maxmum

    0x95, 0x0E,            //Report Count
    0x75, 0x01,            //Report Size
    0x81, 0x42,            //Input

    0x95, 0x01,            //Report Count
    0x75, 0x02,            //Report Size
    0x81, 0x01,            //Input
    0xc0
};

unsigned long ulgHidISOCVoiceReportDescriptorLen = sizeof(gHidISOCVoiceReportDescriptor);

const uint8_t gIsocCurrentDescriptor[] =
{
    0x01, 0x00, 0x01, 0x01,
    0x15, 0x16, 0x05, 0x00,
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x60,
    0x09, 0x00, 0x20, 0x03,
    0x00, 0x00
};

unsigned long ulgIsocCurrentDescriptorLen = sizeof(gIsocCurrentDescriptor);


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
    
    0x61,0x8F,                 /* idVendor             */
    0x25,0xF8,                 /* idProduct            */
        //0xc4,0x10,                 /* idVendor             */
   	 //0x33,0x00,                 /* idProduct            */
       
// by gwf    0x00,0x02,                 /* bcdDevice            */
    0x10,0x01,                 /* bcdDevice            */
    0x01,                      /* iManufacturer        */
    0x02,                      /* iProduct             */
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

    2+12,			/* Product ID: By gwf */
    MUSB_DT_STRING,
    'B', 0, 'y', 0, ' ', 0, 'g', 0, 'w', 0, 'f', 0,


    0x09,                               // Length
    0x02,                               // Type
    //LEN_USB_CONFIGURATION_DESCRIPTOR&0xff, // Totallength = 9+(9+9+7)*3+214+25
    //LEN_USB_CONFIGURATION_DESCRIPTOR>>8,
    0xA6+0x07,0x00,//    0x11,0x01,//0xF8,0x00
    0x04,                               // NumInterfaces
    0x01,                               // bConfigurationValue
    0x00,                               // iConfiguration
    0xa0,                               // bmAttributes
    0x32,                               // MaxPower (in 2mA units)

    0x09, //Size of this descriptor
    0x04, //INTERFACE descriptor
    0x00, //Index of this interface
    0x00, //Index of this setting
    0x00, //only uses Endpoint 0
    0x01, //AUDIO
    0x01, //AUDIO_CONTROL
    0x00, //not vendor or class specific
    0x00, //null string

    0x09, // 0x0A, //
    0x24, //
    0x01, //HEADER subtype
    0x00,0x01,//Revision of  class specification - 1.00
    0x2E,0x00,//Total size of class-specific Audio Control (includes this descriptor)
    0x01, //The number of streaming interfaces
    0x01, //Streaming interface number 1 belongs to this audio control interface. IN Interface
//    0x02, //Streaming interface number 2 belongs to this audio control interface. OUT Interface

    0x0C,
    0x24,
    0x02, //INPUT_TERMINAL subtype
    0x02, //ID of this terminal
    0x01,0x02,//Terminal is Microphone
    0x00, //Associated with Output Terminal  is 0x04
    0x02, //Two channel
    0x03,0x00,// Left/Right Front
    0x00, //
    0x00, //

    0x09,//
    0x24,//CS_INTERFACE
    0x03,// OUTPUT_TERMINAL subtype
    0x12,// ID of this terminal
    0x01,0x01,// Terminal is USB streaming
    0x02,// Associate with Input Terminal
    0x07,// From Feature Unit  (ID5)
    0x00,//



    0x07, //
    0x24, //
    0x05, //Selector_UNIT descriptor subtype
    0x07, //ID of this feature Unit
    0x01, //Inputs Pins
    0x05, //From Input Terminal
    0x00,

    0x09,//
    0x24,//
    0x06,//FEATURE_UNIT descriptor subtype
    0x05,//ID of this feature Unit
    0x02,//From  Input Terminal (Microphone)
    0x01,//One byte Control Array
    0x03,//D0(Mute) D1(Volume) supported
    0x00,//
    0x00,//



    //---------------------------------
    0x09,//
    0x04,//INTERFACE descriptor
    0x01,// bInterfaceNumber ,Index of this interface, mic
    0x00,// Index of this setting
    0x00,// 0 Endpoint
    0x01,// AUDIO
    0x02,// AUDIO_STREAMING
    0x00,//
    0x00,//

    0x09,//
    0x04,//bDescriptorType
    0x01,// bInterfaceNumber
    0x01,// bAlternateSetting
    0x01,// bNumEndpoints
    0x01,// bInterfaceClass
    0x02,// bInterfaceSubclass
    0x00,// bInterfaceProtocol
    0x00,// iInterface

    0x07,//
    0x24,// CS_INTERFACE descriptor
    0x01,// AS_GENERAL
    0x12,// Unit ID of terminal(Output Terminal ID)
    0x00,// Interface delay
    0x01,0x00,//PCM

    0x0b,//
    0x24,//
    0x02,// FORMAT_TYPE
    0x01,// FORMAT_TYPE_I
    0x01,// One channel
    0x02,// Two bytes per slot
    0x10,// 16 bits
    0x01,// bSamFreqType
 #ifdef __ISOC_16K__
 	0x80,0x3E,0x00,// 16000Hz =3e80
 #else
        0x40,0x1F,0x00,// 8000Hz =1f40
 #endif

    0x09,//
    0x05,//
    0x81,//Endpoint 1, IN direction
    0x05,//Isochronous, asynchronous
 #ifdef __ISOC_16K__
 	0x20,0x00,// 2byte*16k sample*1ch=32 byte/frame
 #else
        0x10,0x00,// 2byte*8k sample*1ch=32 byte/frame
 #endif
    0x01, //One packet every frame (Must be set to 1)
    0x00, //
    0x00, //

    0x07,
    0x25,
    0x01,//EP GENERAL
    0x00, //sample rate control
    0x00,
    0x00,0x00,



   

    // ------ Keyboard ---------------------
    0x09,                                   /* bLength              */
    0x04,                                   /* INTERFACE            */
    0x02,                                   /* bInterfaceNumber     */
    0x00,                                   /* bAlternateSetting    */
    0x01,                                   /* bNumEndpoints        */
    0x03,                                   /* bInterfaceClass      */
    0x01,                                   /* bInterfaceSubClass (1=RBC, 6=SCSI) */
    0x01,                               // bInterfaceProcotol // keyboard:mouse = 1:2
    0x00,                                   /* iInterface           */

    0x09,                      // the size of this descriptor
    0x21,                      // hid descriptor type
    0x01,0x01,                          // bcdHID
    0x00,                      // the country code
    0x01,                      // the number of class descriptor
    0x22,                      // report descriptor
    sizeof(gHidKeyboardReportDescriptor),//0x26,
    0x00,  //HID_MEDIA_REPORT_DESCRIPTOR_SIZE>>8

    /* Endpoint Descriptor  : In */
    0x07,                                   /* bLength              */
    0x05,                                   /* ENDPOINT             */
    0x82,                                   /* bEndpointAddress     */
    0x03,                                   /* bmAttributes         */
    0x40,                               // MaxPacketSize (LITTLE ENDIAN)
    0x00,
    0x01,                                  // bInterval
    
     // ------ Mouse ---------------------
    0x09,                                   /* bLength              */
    0x04,                                   /* INTERFACE            */
    0x03,                                   /* bInterfaceNumber     */
    0x00,                                   /* bAlternateSetting    */
    0x02,//NumEndpoints
    0x03,//HID
    0x00,//
    0x01,//
    0x00,//

    0x09,//
    0x21,//
    0x11,0x01,                          // bcdHID
    0x00,//
    0x01,//
    0x22,// Report Descriptor
    sizeof(gHidMouseReportDescriptor),0x00,//  0x39,bDescriptorLength

    0x07,
    0x05,
    0x83,//0x82, //Endpoint 2, IN direction
    0x03,       //Interrupt
    0x40,0x00,  //wMaxPacketSize
    0x01,//10,       //wInterval
     

    0x07,
    0x05,
    0x04, //Endpoint 2, out direction
    0x03,       //Interrupt
    0x40,0x00,  //wMaxPacketSize
    1,//10,       //wInterval
    
};

unsigned long ulMGC_aDescriptorDataLen = sizeof(MGC_aDescriptorData);
const uint8_t *pMGC_aDescriptorData = MGC_aDescriptorData;

STATIC CONST uint8_t MGC_aHighSpeedDescriptorData[] =
{
    /* device qualifier */
    0x0a,                      /* bLength              */
    MUSB_DT_DEVICE_QUALIFIER,  /* DEVICE Qualifier     */
    0x00,0x01,                 /* USB 2.0              */
    0,                         /* CLASS                */
    0,                         /* Subclass             */
    0x00,                      /* Protocol             */
    0x40,                      /* bMaxPacketSize0      */
    0x01,                      /* One configuration    */
    0x00,                      /* bReserved            */

    0x09,                               // Length
    MUSB_DT_OTHER_SPEED,                // Type
    //LEN_USB_CONFIGURATION_DESCRIPTOR&0xff, // Totallength = 9+(9+9+7)*3+214+25
    //LEN_USB_CONFIGURATION_DESCRIPTOR>>8,
    0xA6+0x07,0x00,//    0x11,0x01,//0xF8,0x00
    0x04,                               // NumInterfaces
    0x01,                               // bConfigurationValue
    0x00,                               // iConfiguration
    0xa0,                               // bmAttributes
    0x32,                               // MaxPower (in 2mA units)

    0x09, //Size of this descriptor
    0x04, //INTERFACE descriptor
    0x00, //Index of this interface
    0x00, //Index of this setting
    0x00, //only uses Endpoint 0
    0x01, //AUDIO
    0x01, //AUDIO_CONTROL
    0x00, //not vendor or class specific
    0x00, //null string

    0x09, // 0x0A, //
    0x24, //
    0x01, //HEADER subtype
    0x00,0x01,//Revision of  class specification - 1.00
    0x2E,0x00,//Total size of class-specific Audio Control (includes this descriptor)
    0x01, //The number of streaming interfaces
    0x01, //Streaming interface number 1 belongs to this audio control interface. IN Interface
//    0x02, //Streaming interface number 2 belongs to this audio control interface. OUT Interface

    0x0C,
    0x24,
    0x02, //INPUT_TERMINAL subtype
    0x02, //ID of this terminal
    0x01,0x02,//Terminal is Microphone
    0x00, //Associated with Output Terminal  is 0x04
    0x02, //Two channel
    0x03,0x00,// Left/Right Front
    0x00, //
    0x00, //

    0x09,//
    0x24,//CS_INTERFACE
    0x03,// OUTPUT_TERMINAL subtype
    0x12,// ID of this terminal
    0x01,0x01,// Terminal is USB streaming
    0x02,// Associate with Input Terminal
    0x07,// From Feature Unit  (ID5)
    0x00,//

//    0x09,
//    0x24,
//    0x03, //OUTPUT_TERMINAL subtype
//    0x04, //ID of this terminal
//    0x01,0x03,//Terminal is Speaker
//    0x03, //Associate with Input Terminal  0x03
//    0x08, //From Feature Unit  (ID8)
//    0x00,

//    0x0C, //
//    0x24, //
//    0x02, //INPUT_TERMINAL subtype
//    0x01, //ID of this terminal
//    0x01,0x02,//Terminal is Microphone
//    0x00, // 0x02, //Associated with Output Terminal  0x02
//    0x01, //One channel
//    0x00,0x00,//Mono sets no position bit
//    0x00, //
//    0x00, //

//    0x09,//
//    0x24,//CS_INTERFACE
//    0x03,// OUTPUT_TERMINAL subtype
//    0x02,// ID of this terminal
//    0x01,0x01,// Terminal is USB streaming
//    0x01,// Associate with Input Terminal is 0x01
//    0x05,// From Feature Unit  (ID5)
//    0x00,//

//    0x08,//
//    0x24,//
//    0x06,// FEATURE_UNIT descriptor subtype
//    0x05,// ID of this feature Unit
//    0x07,// From  Selector Unit
//    0x01,// One byte Control Array
//    0x03,// D0(Mute), D1(Volume) supported
//    0x00,//

    0x07, //
    0x24, //
    0x05, //Selector_UNIT descriptor subtype
    0x07, //ID of this feature Unit
    0x01, //Inputs Pins
    0x05, //From Input Terminal
    0x00,

    0x09,//
    0x24,//
    0x06,//FEATURE_UNIT descriptor subtype
    0x05,//ID of this feature Unit
    0x02,//From  Input Terminal (Microphone)
    0x01,//One byte Control Array
    0x03,//D0(Mute) D1(Volume) supported
    0x00,//
    0x00,//

//    0x0D,// Size of this descriptor
//    0x24,// CS_INTERFACE
//    0x06,// FEATURE_UNIT descriptor subtype
//    0x08,// ID of this feature Unit
//    0x09,// From Mixer Unit(ID9)
//    0x02,// Two byte Control Array
//    0x01,0x01,// D0(Mute) , D8(Bass Boost)is enable for channel0
//    0x02,0x00,// D1(Volume) control is enable for channel 1
//    0x02,0x00,// D1(Volume) control is enable for channel 2
//    0x00,//

//    0x0D,//
//    0x24,//
//    0x04,//MIXER_UNIT subtype
//    0x09,//ID of this terminal
//    0x02,//Number of Input Pin
//    0x06,// From Feature Unit 2(ID6)
//    0x03,// From IT(ID3)
//    0x02,// Number of  logical output channels in the Mixer's output audio channel cluster
//    0x03,0x00,//describes the spatial  location  L/R front
//    0x00,// Index of String descriptor
//    0x00,//
//    0x00,//

    //---------------------------------
    0x09,//
    0x04,//INTERFACE descriptor
    0x01,// bInterfaceNumber ,Index of this interface, mic
    0x00,// Index of this setting
    0x00,// 0 Endpoint
    0x01,// AUDIO
    0x02,// AUDIO_STREAMING
    0x00,//
    0x00,//

    0x09,//
    0x04,//bDescriptorType
    0x01,// bInterfaceNumber
    0x01,// bAlternateSetting
    0x01,// bNumEndpoints
    0x01,// bInterfaceClass
    0x02,// bInterfaceSubclass
    0x00,// bInterfaceProtocol
    0x00,// iInterface

    0x07,//
    0x24,// CS_INTERFACE descriptor
    0x01,// AS_GENERAL
    0x12,// Unit ID of terminal(Output Terminal ID)
    0x00,// Interface delay
    0x01,0x00,//PCM

    0x0b,//
    0x24,//
    0x02,// FORMAT_TYPE
    0x01,// FORMAT_TYPE_I
    0x01,// One channel
    0x02,// Two bytes per slot
    0x10,// 16 bits
    0x01,// bSamFreqType
 #ifdef __ISOC_16K__
 	0x80,0x3E,0x00,// 16000Hz =3e80
 #else
    0x40,0x1F,0x00,// 8000Hz =1f40
 #endif

    0x09,//
    0x05,//
    0x81,//Endpoint 1, IN direction
    0x05,//Isochronous, asynchronous
 #ifdef __ISOC_16K__
 	0x20,0x00,// 2byte*16k sample*1ch=32 byte/frame
 #else
    0x10,0x00,// 2byte*8k sample*1ch=32 byte/frame
 #endif
    0x01, //One packet every frame (Must be set to 1)
    0x00, //
    0x00, //

    0x07,
    0x25,
    0x01,//EP GENERAL
    0x00, //sample rate control
    0x00,
    0x00,0x00,


//    // ------ ISOC Rx ---------------------
//    0x09, // bLength
//    0x04, // bDescriptorType
//    0x02, // bInterfaceNumber, player
//    0x00, // bAlternateSetting
//    0x00, // bNumEndpoints
//    0x01, // bInterfaceClass
//    0x02, // bInterfaceSubclass
//    0x00, // bInterfaceProtocol
//    0x00, // iInterface

//    0x09,//
//    0x04,//
//    0x02,//
//    0x01,//
//    0x01,//
//    0x01,//
//    0x02,//
//    0x00,//
//    0x00,//

//    0x07,//
//    0x24,//
//    0x01,// AS_GENERAL
//    0x03,// Unit ID of  Terminal(Input Terminal
//    0x00,//
//    0x01,0x00,//PCM

//    0x0b,//
//    0x24,//
//    0x02,//
//    0x01,//
//    0x02,// Two channels
//    0x02,// Two bytes per slot ,????????
//    0x10,// 16  bits
//    0x01,//
//#if defined(MUSIC_48KHZ_2CH_16BIT)
//    0x80, 0xBB, 0x00, //48kHZ,???????
//#elif defined(MUSIC_24KHZ_2CH_16BIT)
//    0xc0, 0x5d, 0x00, //24kHZ,???????
//#endif

//    0x09,
//    0x05,//ENDPOINT descriptor
//    0x02,// Endpoint 2, OUT direction
//    0x09,// Adaptive  Isochronous
//#if defined(MUSIC_48KHZ_2CH_16BIT)
//    0x40,0x00,// 2byte*(48+2)sample*2ch=200 byte/frame
//#elif defined(MUSIC_24KHZ_2CH_16BIT)
//    0x64,0x00,
//#endif
//    0x01,//
//    0x00,
//    0x00,

//    0x07,
//    0x25,
//    0x01, // EP_GENERAL
//    0x00, // Sample rate control
//    0x00,
//    0x00,0x00,


  
    // ------ Keyboard ---------------------
    0x09,                               // bLength
    0x04,                               // bDescriptorType
    0x02,                               // bInterfaceNumber
    0x00,                               // bAlternateSetting
    0x01,                               // bNumEndpoints
    0x03,                               // bInterfaceClass (3 = HID)
    0x01,                               // bInterfaceSubClass
    0x01,                               // bInterfaceProcotol // keyboard:mouse = 1:2
    0x00,                               // iInterface

    0x09,                               // bLength
    0x21,                               // bDescriptorType
    0x01,0x01,                          // bcdHID
    0x00,                               // bCountryCode
    0x01,                               // bNumDescriptors
    0x22,                               // bDescriptorType
    sizeof(gHidKeyboardReportDescriptor),//0x26,
    0x00,  //HID_MEDIA_REPORT_DESCRIPTOR_SIZE>>8

    // IN endpoint (mandatory for HID)
    0x07,                               // bLength
    0x05,                               // bDescriptorType
    0x82,                               // bEndpointAddress
    0x03,                               // bmAttributes
    0x40,                               // MaxPacketSize (LITTLE ENDIAN)
    0x00,
    0x01,                                  // bInterval
      // ------ Mouse ---------------------
    0x09,//
    0x04,//
    0x03,//Index of this interface
    0x00,//
    0x02,//NumEndpoints
    0x03,//HID
    0x00,//
    0x01,//0x02,//
    0x00,//0x00,//

    0x09,//
    0x21,//
    0x11,0x01,                          // bcdHID
    0x00,//
    0x01,//
    0x22,// Report Descriptor
    sizeof(gHidMouseReportDescriptor),0x00,//  0x39,bDescriptorLength

    0x07,
    0x05,
    0x83,//0x82,
    0x03,       //Interrupt
    0x40,0x00,  //wMaxPacketSize
    0x01,//10,       //wInterval

    0x07,
    0x05,
    0x04, //Endpoint 2, IN direction
    0x03,       //Interrupt
    0x40,0x00,  //wMaxPacketSize
    1,//10,       //wInterval
};

unsigned long ulMGC_aHighSpeedDescriptorDataLen = sizeof(MGC_aHighSpeedDescriptorData);
const uint8_t *pMGC_aHighSpeedDescriptorData = MGC_aHighSpeedDescriptorData;


STATIC uint8_t MGC_bMcpInterface = 0;

// by gwf   STATIC uint8_t MGC_aJunk[1];//[512];
STATIC uint8_t MGC_aJunk[64];
uint8_t MGC_RX_Buffer[64];
uint8_t MGC_TX_Buffer[64];


/** IRP for tx isoc data transmission */
STATIC MUSB_IsochIrp MGC_McpIsocTxDataIrp =
{
    NULL,   /* hPipe */
    NULL,   /* pBuffer */
    0,   /* adwLength */
    0,   /* adwStatus */
    0,   /* adwActualLength */
    NULL,   /* pfIrpComplete */
    NULL,   /* pCompleteParam */
    0,      /* wFrameCount */
    0,      /* wCurrentFrame */
    0,      /* wCallbackInterval */
    TRUE,	/* bIsrCallback */
    FALSE	/* bAllowDma */
};

///** IRP for rx isoc data transmission */
//STATIC MUSB_IsochIrp MGC_McpIsocRxDataIrp =
//{
//    NULL,   /* hPipe */
//    NULL,   /* pBuffer */
//    NULL,   /* adwLength */
//    NULL,   /* adwStatus */
//    NULL,   /* adwActualLength */
//    NULL,   /* pfIrpComplete */
//    NULL,   /* pCompleteParam */
//    0,      /* wFrameCount */
//    0,      /* wCurrentFrame */
//    0,      /* wCallbackInterval */
//    TRUE,	/* bIsrCallback */
//    FALSE	/* bAllowDma */
//};
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

/** IRP for mouse data transmission */
STATIC MUSB_Irp MGC_McpMouseTxDataIrp =
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

/** IRP for keyboard data transmission */
STATIC MUSB_Irp MGC_McpKeyboardTxDataIrp =
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


/*
* registration
*/
#if 1
MUSB_FunctionClient MGC_McpFunctionClient =
{
    NULL,	/* no instance data; we are singleton */
    MGC_aDescriptorData,
    sizeof(MGC_aDescriptorData),
    3,		/* strings per language */
    MGC_aHighSpeedDescriptorData,//
    sizeof(MGC_aHighSpeedDescriptorData),
    sizeof(MGC_aControlData),
    MGC_aControlData,
    &MGC_bMcpSelfPowered,
    MGC_McpDeviceRequest,
    MGC_McpDeviceConfigSelected,
    NULL,
    MGC_McpNewUsbState
};
#else 
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
#endif


////////////// for user ///////////////////////
STATIC volatile uint8_t b_isConnected = FALSE;
STATIC volatile uint8_t b_isTRxing = FALSE;

void test_usb_device(void);
STATIC void USBD_IsocTxDataComplete(void* pCompleteParam, MUSB_IsochIrp* pIrp)
{
	b_isTRxing = FALSE;
	
	test_usb_device();
	os_printf("USBD_IsocTxDataComplete\r\n");
}
//STATIC void USBD_IsocRxDataComplete(void* pCompleteParam, MUSB_IsochIrp* pIrp)
//{
//	b_isTRxing = FALSE;
//	os_printf("USBD_IsocRxDataComplete\r\n");
//}
STATIC uint32_t USBD_MouseTxDataComplete(void* pCompleteParam, MUSB_Irp* pIrp)
{
	b_isTRxing = FALSE;
	os_printf("USBD_MouseTxDataComplete\r\n");
    test_usb_device();  ///190404
	return 0;
}
STATIC uint32_t USBD_KeyboardTxDataComplete(void* pCompleteParam, MUSB_Irp* pIrp)
{
	b_isTRxing = FALSE;
	os_printf("USBD_KeyboardTxDataComplete\r\n");
    test_usb_device();  ///190404
    //UART_PRINTF("USBD_KeyboardTxDataComplete \r\n");
	return 0;
}

void USBD_IsocStartTx(unsigned char *pBuf, unsigned long ulLen)
{
	unsigned char *pBufTemp = pBuf;
	unsigned long ulLenTemp;
	os_printf("USBD_IsocStartTx ---1\r\n");
	do
	{
		if (b_isTRxing == TRUE)
		{
			return;
		}
        os_printf("USBD_IsocStartTx ---2\r\n");
		ulLenTemp = MIN(ulLen, 64);
		b_isTRxing = TRUE;
		MGC_McpIsocTxDataIrp.pBuffer = pBufTemp;
		MGC_McpIsocTxDataIrp.adwLength = ulLenTemp;
		//MGC_McpIsocTxDataIrp.adwLength[1] = ulLenTemp;
		//MGC_McpIsocTxDataIrp.adwLength[2] = ulLenTemp;
		MGC_McpIsocTxDataIrp.adwActualLength = 0;
		//MGC_McpIsocTxDataIrp.adwActualLength[1] = 0;
		//MGC_McpIsocTxDataIrp.adwActualLength[2] = 0;
		MGC_McpIsocTxDataIrp.pfIrpComplete = USBD_IsocTxDataComplete;
		MUSB_ScheduleIsochTransfer(0, &MGC_McpIsocTxDataIrp);
		ulLen -= ulLenTemp;
		pBufTemp += ulLenTemp;
	} while (ulLen);
	os_printf("USBD_IsocStartTx ---3\r\n");
}

//void USBD_IsocStartRx(unsigned char *pBuf, unsigned long ulLen)
//{
//	unsigned char *pBufTemp = pBuf;
//	unsigned long ulLenTemp;
//	os_printf("USBD_IsocStartRx ---1\r\n");
//	do
//	{
//		if (b_isTRxing == TRUE)
//		{
//			return;
//		}
//        os_printf("USBD_IsocStartRx ---2\r\n");
//		ulLenTemp = MIN(ulLen, 64);
//		b_isTRxing = TRUE;
//		MGC_McpIsocRxDataIrp.pBuffer = pBufTemp;
//		MGC_McpIsocRxDataIrp.adwLength[0] = ulLenTemp;
//		MGC_McpIsocRxDataIrp.adwLength[1] = ulLenTemp;
//		MGC_McpIsocRxDataIrp.adwLength[2] = ulLenTemp;
//		MGC_McpIsocRxDataIrp.adwActualLength[0] = 0;
//		MGC_McpIsocRxDataIrp.adwActualLength[1] = 0;
//		MGC_McpIsocRxDataIrp.adwActualLength[2] = 0;
//		MGC_McpIsocRxDataIrp.pfIrpComplete = USBD_IsocRxDataComplete;
//		MUSB_ScheduleIsochTransfer(0, &MGC_McpIsocRxDataIrp);
//		ulLen -= ulLenTemp;
//		pBufTemp += ulLenTemp;
//	} while (ulLen);
//	os_printf("USBD_IsocStartRx ---3\r\n");
//}

void USBD_MouseStartTx(unsigned char *pBuf, unsigned long ulLen)
{
	unsigned char *pBufTemp = pBuf;
	unsigned long ulLenTemp;

//	UART_PRINTF("USBD_MouseStartTx ---1\r\n");
	do
	{
		if (b_isTRxing == TRUE)
		{
			return;
		}
//	UART_PRINTF("USBD_MouseStartTx ---2\r\n");
		ulLenTemp = MIN(ulLen, 64);
		b_isTRxing = TRUE;
#if 0
		memcpy(MGC_aJunk, pBufTemp, ulLenTemp);
		MGC_McpMouseTxDataIrp.pBuffer = MGC_aJunk;
#else
		MGC_McpMouseTxDataIrp.pBuffer = pBufTemp;
#endif
		MGC_McpMouseTxDataIrp.dwLength = ulLenTemp;
		MGC_McpMouseTxDataIrp.dwActualLength = 0;
		MGC_McpMouseTxDataIrp.pfIrpComplete = USBD_MouseTxDataComplete;
		MUSB_StartTransfer(&MGC_McpMouseTxDataIrp);
		ulLen -= ulLenTemp;
		pBufTemp += ulLenTemp;
	} while (ulLen);
//	UART_PRINTF("USBD_MouseStartTx ---3\r\n");
}

void USBD_KeyboardStartTx(unsigned char *pBuf, unsigned long ulLen)
{
	unsigned char *pBufTemp = pBuf;
	unsigned long ulLenTemp;

//	UART_PRINTF("USBD_KeyboardStartTx ---1\r\n");
	do
	{
		//UART_PRINTF("LEN=%X,IS_TX=%X\r\n",ulLen,b_isTRxing);
		if (b_isTRxing == TRUE)
		{
			return;
		}
//	UART_PRINTF("USBD_KeyboardStartTx ---2\r\n");
		ulLenTemp = MIN(ulLen, 64);
		b_isTRxing = TRUE;
		MGC_McpKeyboardTxDataIrp.pBuffer = pBufTemp;
		MGC_McpKeyboardTxDataIrp.dwLength = ulLenTemp;
		MGC_McpKeyboardTxDataIrp.dwActualLength = 0;
		MGC_McpKeyboardTxDataIrp.pfIrpComplete = USBD_KeyboardTxDataComplete;
		MUSB_StartTransfer(&MGC_McpKeyboardTxDataIrp);
		ulLen -= ulLenTemp;
		pBufTemp += ulLenTemp;
	} while (ulLen);
//	UART_PRINTF("USBD_KeyboardStartTx ---3\r\n");
}

unsigned char tISOCTable[]=
						{
							0x3c,0x37,
							0x0e,0x27,
							0x01,0x00,
							0xf1,0xd8,
							0xc5,0xc8,
							0xf2,0xd8,
							0x01,0x00,
							0x0f,0x27
						};

extern unsigned char ucAudioRecordOnOff;
extern	uint8_t check_b_isTRxing(void);
extern uint8_t  read_decode_data(uint8_t *buf);
uint8_t notify_voice_data[64];
				
#include "gpio.h"
void test_usb_device(void)
{
	extern struct rev_ntf_data notify_data;

    if (b_isConnected == FALSE)
    {
        UART_PRINTF("sk 12\r\n");
        return;
    }
		
    if (b_isTRxing == TRUE)
    {
        UART_PRINTF("sk 13\r\n");
        return;
    }
       
   
#if (USB_DRIVER)	
    if(notify_data.notify_mouse_status==1)
    {
        notify_data.notify_mouse_status=0;
        notify_data.notify_mouse[0]=HIDS_MOUSE_REPORT_ID;
		USBD_KeyboardStartTx(notify_data.notify_mouse, 10);
	//	USBD_MouseStartTx(notify_data.notify_mouse,10);
    }
	
    else if(notify_data.notify_media_key_status==1)
    {
	 	UART_PRINTF("MK\r\n");			
        notify_data.notify_media_key_status=0;
        notify_data.notify_media_key[0]=HIDS_MM_KB_REPORT_ID;
        USBD_KeyboardStartTx(notify_data.notify_media_key, 3);
    }

    
    else if(notify_data.notify_power_key_status==1)
    {
        notify_data.notify_power_key_status=0;
        notify_data.notify_power_key[0]=HIDS_PWR_KB_REPORT_ID;
        USBD_KeyboardStartTx(notify_data.notify_power_key, 2);
    }
     
   else if(notify_data.notify_sensor_status==1)
    {
        notify_data.notify_sensor_status=0;
        notify_data.notify_sensor[0]=RMC_SENSORS_DATA_REPORT_ID;
        USBD_KeyboardStartTx(notify_data.notify_sensor, 19);
    }

   else if(notify_data.notify_standard_key_status==1)
    {
        notify_data.notify_standard_key_status=0;
        notify_data.notify_standard_key[0]=HIDS_KB_REPORT_ID;
        USBD_KeyboardStartTx(notify_data.notify_standard_key, 12);
    }
    else if (ucAudioRecordOnOff == 0x81 )//|| (ucAudioRecordOnOff == 0x01))
    {
        /*
        if(1 == read_decode_data(notify_voice_data))
        {
        	USBD_IsocStartTx(notify_voice_data, 32);
        }	
        else
        {
            memset(notify_voice_data,0x00,32);
            USBD_IsocStartTx(notify_voice_data, 32);
        }
        */
    }
#endif

    
}
////////////// for user ///////////////////////

/******************************************************************
CDI callbacks
******************************************************************/
STATIC void MGC_McpNewUsbState(void* hClient, MUSB_BusHandle hBus,
			       MUSB_State State)
{
	//uart_printf("MGC_McpNewUsbState: state = %x\r\n",State);
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
    MUSB_DeviceRequest* pRequest = (MUSB_DeviceRequest*)pSetup;
    uint8_t bOk = FALSE;

    os_printf("MGC_McpDeviceRequest\r\n");
    if (MUSB_TYPE_STANDARD == (pRequest->bmRequestType & MUSB_TYPE_MASK))
    {
        switch(pRequest->bRequest)
        {
        case MUSB_REQ_GET_INTERFACE:
            MUSB_DeviceResponse(hBus, dwSequence, &MGC_bMcpInterface, 1, FALSE);
            bOk = TRUE;
            break;
        case MUSB_REQ_SET_INTERFACE:
            MUSB_DeviceResponse(hBus, dwSequence, NULL, 0, FALSE);
            bOk = TRUE;
            break;
        }
    }
    else if ((pRequest->bmRequestType & MUSB_TYPE_CLASS)
         && (pRequest->bmRequestType & MUSB_RECIP_INTERFACE))
    {
        switch(pRequest->bRequest)
        {
        	default:
            break;
        }
    }
    return bOk;
}

void USBD_StartRx()
{	
	while(b_isTRxing == TRUE)
	{
	    UART_PRINTF("tran rx\r\n");
	}
    MGC_McpUsbRxDataIrp.dwActualLength = 0;
	MUSB_StartTransfer(&MGC_McpUsbRxDataIrp);
}


volatile uint8_t b_isDataing = FALSE;
uint8_t user_flash_data1[16] = {0x12,0x34,0xaa,0x00,0x00,0x20,0x00,0x00,
                                0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,};
STATIC uint32_t USBD_RxDataCallback(void* pCompleteParam, MUSB_Irp* pIrp)
{
        //b_isTRxing = FALSE;
        //b_isDataing = TRUE;
        UART_PRINTF("USBD_RxData Complete\r\n");
        UART_PRINTF("dwLength: %d  dwActualLength: %d\r\n",MGC_McpUsbRxDataIrp.dwLength,MGC_McpUsbRxDataIrp.dwActualLength);
         //01 E0 FC 02 0E A5
         if((MGC_McpUsbRxDataIrp.pBuffer[0] == 0x01) && 
              (MGC_McpUsbRxDataIrp.pBuffer[4] == 0x0e) 
              &&(MGC_McpUsbRxDataIrp.pBuffer[5] == 0xa5) 
              &&(MGC_McpUsbRxDataIrp.pBuffer[1] == 0xe0)
              &&(MGC_McpUsbRxDataIrp.pBuffer[2] == 0xfc)
              &&(MGC_McpUsbRxDataIrp.pBuffer[3] == 0x02) 
              )
         {
                
                ///flash_erase(0,0x7ff00,16,NULL);
                flash_write(0,0x7ff00,16,user_flash_data1,NULL);
                                      
                platform_reset(0x1515);
         }
        return 0;
}

STATIC uint8_t MGC_McpDeviceConfigSelected(void* hClient, MUSB_BusHandle hBus,
					   uint8_t bConfigurationValue,
					   MUSB_Pipe* ahPipe)
{
//	uart_printf("MGC_McpDeviceConfigSelected\r\n");

    MGC_McpIsocTxDataIrp.hPipe  = ahPipe[0];
    MGC_McpIsocTxDataIrp.pBuffer = (uint8_t*)MGC_aJunk;
    MGC_McpIsocTxDataIrp.adwLength = sizeof(MGC_aJunk);
    //MGC_McpIsocTxDataIrp.adwLength[1] = sizeof(MGC_aJunk);
    //MGC_McpIsocTxDataIrp.adwLength[2] = sizeof(MGC_aJunk);
    MGC_McpIsocTxDataIrp.adwActualLength = 0;
    //MGC_McpIsocTxDataIrp.adwActualLength[1] = 0;
    //MGC_McpIsocTxDataIrp.adwActualLength[2] = 0;
    MGC_McpIsocTxDataIrp.pfIrpComplete = USBD_IsocTxDataComplete;

//    MGC_McpIsocRxDataIrp.hPipe  = ahPipe[1];
//    MGC_McpIsocRxDataIrp.pBuffer = (uint8_t*)MGC_aJunk;
//    MGC_McpIsocRxDataIrp.adwLength[0] = sizeof(MGC_aJunk);
//    MGC_McpIsocRxDataIrp.adwLength[1] = sizeof(MGC_aJunk);
//    MGC_McpIsocRxDataIrp.adwLength[2] = sizeof(MGC_aJunk);
//    MGC_McpIsocRxDataIrp.adwActualLength[0] = 0;
//    MGC_McpIsocRxDataIrp.adwActualLength[1] = 0;
//    MGC_McpIsocRxDataIrp.adwActualLength[2] = 0;
//    MGC_McpIsocRxDataIrp.pfIrpComplete = USBD_IsocRxDataComplete;
    MGC_McpUsbRxDataIrp.hPipe = ahPipe[3]; 
    MGC_McpUsbRxDataIrp.pBuffer = (uint8_t*)MGC_RX_Buffer;
    MGC_McpUsbRxDataIrp.dwLength = sizeof(MGC_RX_Buffer);
    MGC_McpUsbRxDataIrp.pfIrpComplete = USBD_RxDataCallback;
    
	

	MGC_McpKeyboardTxDataIrp.hPipe = ahPipe[1];
	MGC_McpKeyboardTxDataIrp.pBuffer = (uint8_t*)MGC_aJunk;
	MGC_McpKeyboardTxDataIrp.dwLength = sizeof(MGC_aJunk);
	MGC_McpKeyboardTxDataIrp.pfIrpComplete = USBD_KeyboardTxDataComplete;

    MGC_McpMouseTxDataIrp.hPipe = ahPipe[2];
	MGC_McpMouseTxDataIrp.pBuffer = (uint8_t*)MGC_TX_Buffer;
	MGC_McpMouseTxDataIrp.dwLength = sizeof(MGC_TX_Buffer);
	MGC_McpMouseTxDataIrp.pfIrpComplete = USBD_MouseTxDataComplete;
    
    /*if (b_isConnected == FALSE)
    {
        return TRUE;
    }
    //bim1_uart_printf("call 2\r\n");*/
    USBD_StartRx();
	return TRUE;
}


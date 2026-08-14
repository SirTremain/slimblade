/*************************************************************
 * @file        BK_System.h
 * @brief       Header file of BK_System.c
 * @author      GuWenFu
 * @version     V1.0
 * @date        2016-09-29
 * @par         
 * @attention   
 *
 * @history     2016-09-29 gwf    create this file
 */

#ifndef  __BK_SYSTEM_H__
#define  __BK_SYSTEM_H__


#ifdef __cplusplus
extern "C" {
#endif  /* __cplusplus */



#define MAX(a,b)    (((a) > (b)) ? (a) : (b))
#define MIN(a,b)    (((a) < (b)) ? (a) : (b))
#define NUMBER_ROUND_UP(a,b)        ((a) / (b) + (((a) % (b)) ? 1 : 0))
#define NUMBER_ROUND_DOWN(a,b)      ((a) / (b))


typedef unsigned char       BYTE;
typedef signed   char       int8;       // 有符号8位整型变量
typedef signed   short      int16;      // 有符号16位整型变量
typedef signed   int        int32;      // 有符号32位整型变量
typedef unsigned int        uint32; 
typedef unsigned char       uint8;      // 无符号8位整型变量
typedef unsigned short      uint16; 



typedef signed   char       int8_t;     // 有符号8位整型变量
typedef signed   short      int16_t;    // 有符号16位整型变量
//typedef signed   int       int32_t;    // 有符号32位整型变量
typedef unsigned char       uint8_t;    // 无符号8位整型变量
typedef unsigned short      uint16_t;   // 无符号16位整型变量
#if defined(__CC_ARM)
typedef signed   int       int32_t;    // 有符号32位整型变量
typedef unsigned int       uint32_t;   // 无符号32位整型变量

#endif


#ifdef __cplusplus
}
#endif  /* __cplusplus */


#endif      /* __BK_SYSTEM_H__ */

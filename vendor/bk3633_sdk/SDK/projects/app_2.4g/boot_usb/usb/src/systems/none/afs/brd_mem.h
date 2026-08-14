/******************************************************************
 *                                                                *
 *        Copyright Mentor Graphics Corporation 2004              *
 *                                                                *
 *                All Rights Reserved.                            *
 *                                                                *
 *    THIS WORK CONTAINS TRADE SECRET AND PROPRIETARY INFORMATION *
 *  WHICH IS THE PROPERTY OF MENTOR GRAPHICS CORPORATION OR ITS   *
 *  LICENSORS AND IS SUBJECT TO LICENSE TERMS.                    *
 *                                                                *
 ******************************************************************/

#ifndef __MUSB_NONE_AFS_MEMORY_H__
#define __MUSB_NONE_AFS_MEMORY_H__

/*
 * AFS-specific memory abstraction
 * $Revision: 1.4 $
 */

//#include "uhal.h"
#include <stdlib.h>
#include <string.h>
#include "BK_system.h"

extern void* MGC_AfsMemRealloc(void* pBuffer, uint32_t iSize);
extern void *print_jmalloc(uint32_t isize);
extern void print_jfree(void *addr);

#define MUSB_MemAlloc(a) malloc(a)
#define MUSB_MemRealloc realloc
#define MUSB_MemFree free
#define MUSB_MemCopy(_pDest, _pSrc, _iSize) \
    memcpy((void*)_pDest, (void*)_pSrc, _iSize)
#define MUSB_MemSet(_pDest, _iData, _iSize) \
    memset((void*)_pDest, _iData, _iSize)

#endif	/* multiple inclusion protection */

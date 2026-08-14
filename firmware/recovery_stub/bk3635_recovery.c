#include <stdint.h>

/*
 * Register-level reconstruction of the stock v4.49 command-0x0d path.
 *
 * This is intentionally isolated from the related BK3633 SDK: BK3635 uses a
 * different nonvolatile-memory controller at 0x00803000. The constants and
 * ordering below come from the SlimBlade v4.49 application disassembly.
 */

#define MMIO32(address) (*(volatile uint32_t *)(address))

#define SYSTEM_INTERRUPT_CONTROL MMIO32(0x0080001cu)
#define SYSTEM_RESET_REQUEST MMIO32(0x008000c0u)
#define WATCHDOG_CONTROL MMIO32(0x00806000u)

#define STORAGE_BASE 0x00803000u
#define STORAGE_UNLOCK MMIO32(STORAGE_BASE + 0x00u)
#define STORAGE_COMMAND MMIO32(STORAGE_BASE + 0x04u)
#define STORAGE_ADDRESS MMIO32(STORAGE_BASE + 0x08u)
#define STORAGE_WRITE_DATA MMIO32(STORAGE_BASE + 0x0cu)
#define STORAGE_KEY_A MMIO32(STORAGE_BASE + 0x10u)
#define STORAGE_KEY_B MMIO32(STORAGE_BASE + 0x14u)

#define STORAGE_COMMAND_FIELDS 0x0000007cu
#define STORAGE_COMMAND_START 0x00000001u
#define EEPROM_ERASE_COMMAND ((1u << 5) | 8u)
#define EEPROM_WRITE_COMMAND ((1u << 5) | 4u)

#define EEPROM_ERASE_ADDRESS 0x00008000u
#define LOADER_MARKER_WORD_ADDRESS 0x0000807cu

static void watchdog_disable(void)
{
    SYSTEM_INTERRUPT_CONTROL = 1u;
    WATCHDOG_CONTROL = 0x005a0000u;
    WATCHDOG_CONTROL = 0x00a50000u;
}

static void storage_finish(void)
{
    STORAGE_UNLOCK = 0u;
    STORAGE_UNLOCK = 0u;
    STORAGE_KEY_A = 0u;
    STORAGE_KEY_B = 0u;
}

static void storage_operation(uint32_t command)
{
    uint32_t value;

    /* Stock v4.49 function 0x177d8 writes these in this exact order. */
    STORAGE_UNLOCK = 0x000058a9u;
    STORAGE_UNLOCK = 0x0000a958u;
    STORAGE_KEY_A = 0x000000a5u;
    STORAGE_KEY_B = 0x000000c3u;

    value = STORAGE_COMMAND;
    value &= ~STORAGE_COMMAND_FIELDS;
    value |= command;
    STORAGE_COMMAND = value;
    STORAGE_COMMAND = value | STORAGE_COMMAND_START;
    while ((STORAGE_COMMAND & STORAGE_COMMAND_START) != 0u) {
    }

    storage_finish();
}

static void eeprom_erase(void)
{
    STORAGE_ADDRESS = EEPROM_ERASE_ADDRESS;
    storage_operation(EEPROM_ERASE_COMMAND);
}

static void eeprom_write_word(uint32_t word_address, uint32_t value)
{
    STORAGE_ADDRESS = word_address;
    STORAGE_WRITE_DATA = value;
    storage_operation(EEPROM_WRITE_COMMAND);
}

void bk3635_stock_delay(uint32_t outer, uint32_t feed_watchdog);

__attribute__((noreturn)) static void watchdog_reset(void)
{
    watchdog_disable();
    SYSTEM_RESET_REQUEST = 0x00aa5aaau;
    SYSTEM_INTERRUPT_CONTROL = 0u;
    WATCHDOG_CONTROL = 0x00000050u;
    WATCHDOG_CONTROL = 0x005a0050u;
    WATCHDOG_CONTROL = 0x00a50050u;

    for (;;) {
    }
}

__attribute__((noreturn)) void bk3635_enter_resident_loader(void)
{
    /* Bytes: 12 34 56 78 9a bc d2 19. The last byte is (0x55-sum)&0xff. */
    watchdog_disable();
    eeprom_erase();
    eeprom_write_word(LOADER_MARKER_WORD_ADDRESS, 0x78563412u);
    eeprom_write_word(LOADER_MARKER_WORD_ADDRESS + 1u, 0x19d2bc9au);
    bk3635_stock_delay(200u, 0u);
    watchdog_reset();
}

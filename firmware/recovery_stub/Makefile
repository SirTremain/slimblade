ROOT := ../..
BUILD := build
TARGET := $(BUILD)/DO_NOT_FLASH-recovery-stub
CLANG ?= clang
OBJCOPY ?= llvm-objcopy

ARCH := --target=arm-none-eabi -mcpu=arm968e-s -march=armv5te
CFLAGS := $(ARCH) -mthumb -Os -ffreestanding -fno-builtin -ffunction-sections -fdata-sections -Wall -Wextra -Werror
ASFLAGS := $(ARCH) -x assembler-with-cpp
LDFLAGS := $(ARCH) -nostdlib -fuse-ld=lld -Wl,-T,recovery_stub.ld -Wl,--gc-sections -Wl,-Map,$(TARGET).map

.PHONY: all clean inspect preflight

all: $(TARGET).container.bin inspect

$(BUILD):
	mkdir -p $@

$(BUILD)/startup.o: startup.S | $(BUILD)
	$(CLANG) $(ASFLAGS) -c $< -o $@

$(BUILD)/stock_delay.o: stock_delay.S | $(BUILD)
	$(CLANG) $(ASFLAGS) -c $< -o $@

$(BUILD)/main.o: main.c | $(BUILD)
	$(CLANG) $(CFLAGS) -c $< -o $@

$(BUILD)/bk3635_recovery.o: bk3635_recovery.c | $(BUILD)
	$(CLANG) $(CFLAGS) -c $< -o $@

$(TARGET).elf: $(BUILD)/startup.o $(BUILD)/main.o $(BUILD)/bk3635_recovery.o $(BUILD)/stock_delay.o recovery_stub.ld
	$(CLANG) $(LDFLAGS) $(BUILD)/startup.o $(BUILD)/main.o $(BUILD)/bk3635_recovery.o $(BUILD)/stock_delay.o -o $@

$(TARGET).code.bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

$(TARGET).container.bin: $(TARGET).code.bin
	python3 $(ROOT)/tools/firmware_image.py pack-application $< $@ --end-offset 0x1f470

inspect: $(TARGET).container.bin
	python3 $(ROOT)/tools/firmware_image.py inspect $<
	llvm-readelf -h -S $(TARGET).elf

preflight: all
	python3 $(ROOT)/tools/verify_recovery_stub.py /tmp/slimblade-v449.bin $(TARGET).container.bin $(TARGET).code.bin $(TARGET).elf
	python3 -m unittest discover -s $(ROOT)/tests -p 'test_*.py'

clean:
	rm -r $(BUILD)

ROOT := ../..
BUILD := build
TARGET := $(BUILD)/DO_NOT_FLASH-stock-reset-trampoline
BASE ?= ../recovery_carrier/build/DO_NOT_FLASH-stock-recovery-carrier.container.bin
CLANG ?= clang
OBJCOPY ?= llvm-objcopy

ARCH := --target=arm-none-eabi -mcpu=arm968e-s -march=armv5te
ASFLAGS := $(ARCH) -x assembler-with-cpp
LDFLAGS := $(ARCH) -nostdlib -fuse-ld=lld -Wl,-T,reset_trampoline.ld -Wl,--gc-sections -Wl,-Map,$(TARGET).map

.PHONY: all inspect preflight clean

all: $(TARGET).container.bin inspect

$(BUILD):
	mkdir -p $@

$(BASE):
	$(MAKE) -C ../recovery_carrier all

$(BUILD)/trampoline.o: trampoline.S | $(BUILD)
	$(CLANG) $(ASFLAGS) -c $< -o $@

$(TARGET).elf: $(BUILD)/trampoline.o reset_trampoline.ld
	$(CLANG) $(LDFLAGS) $< -o $@

$(TARGET).code.bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

$(TARGET).container.bin: $(TARGET).code.bin $(BASE)
	python3 $(ROOT)/tools/make_reset_trampoline.py $(BASE) $< $@

inspect: $(TARGET).container.bin
	python3 $(ROOT)/tools/firmware_image.py inspect $<
	llvm-readelf -h -S $(TARGET).elf

preflight: all
	python3 $(ROOT)/tools/verify_reset_trampoline.py $(BASE) $(TARGET).container.bin $(TARGET).code.bin $(TARGET).elf
	python3 -m unittest discover -s $(ROOT)/tests -p 'test_*.py'

clean:
	rm -r $(BUILD)

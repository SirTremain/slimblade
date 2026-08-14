ROOT := ../..
BUILD := build
TARGET := $(BUILD)/DO_NOT_FLASH-stock-recovery-carrier
STOCK ?= /tmp/slimblade-v449.bin
CLANG ?= clang
OBJCOPY ?= llvm-objcopy

ARCH := --target=arm-none-eabi -mcpu=arm968e-s -march=armv5te
ASFLAGS := $(ARCH) -x assembler-with-cpp
LDFLAGS := $(ARCH) -nostdlib -fuse-ld=lld -Wl,-T,carrier.ld -Wl,--gc-sections -Wl,-Map,$(TARGET).map

.PHONY: all inspect preflight clean

all: $(TARGET).container.bin inspect

$(BUILD):
	mkdir -p $@

$(BUILD)/carrier.o: carrier.S | $(BUILD)
	$(CLANG) $(ASFLAGS) -c $< -o $@

$(TARGET).elf: $(BUILD)/carrier.o carrier.ld
	$(CLANG) $(LDFLAGS) $< -o $@

$(TARGET).code.bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

$(TARGET).container.bin: $(TARGET).code.bin $(STOCK)
	python3 $(ROOT)/tools/make_recovery_carrier.py $(STOCK) $< $@

inspect: $(TARGET).container.bin
	python3 $(ROOT)/tools/firmware_image.py inspect $<
	llvm-readelf -h -S $(TARGET).elf

preflight: all
	python3 $(ROOT)/tools/verify_recovery_carrier.py $(STOCK) $(TARGET).container.bin $(TARGET).code.bin $(TARGET).elf
	python3 -m unittest discover -s $(ROOT)/tests -p 'test_*.py'

clean:
	rm -r $(BUILD)

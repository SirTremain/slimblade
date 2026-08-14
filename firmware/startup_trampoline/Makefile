ROOT := ../..
BUILD := build
TARGET := $(BUILD)/DO_NOT_FLASH-stock-startup-trampoline
BASE ?= ../reset_trampoline/build/DO_NOT_FLASH-stock-reset-trampoline.container.bin
STUB ?= ../recovery_stub/build/DO_NOT_FLASH-recovery-stub.container.bin
CLANG ?= clang
OBJCOPY ?= llvm-objcopy

ARCH := --target=arm-none-eabi -mcpu=arm968e-s -march=armv5te
ASFLAGS := $(ARCH) -x assembler-with-cpp
LDFLAGS := $(ARCH) -nostdlib -fuse-ld=lld -Wl,-T,startup_trampoline.ld -Wl,--gc-sections -Wl,-Map,$(TARGET).map

.PHONY: all inspect preflight clean

all: $(TARGET).container.bin inspect

$(BUILD):
	mkdir -p $@

$(BASE):
	$(MAKE) -C ../reset_trampoline all

$(STUB):
	$(MAKE) -C ../recovery_stub all

$(BUILD)/startup_trampoline.o: startup_trampoline.S | $(BUILD)
	$(CLANG) $(ASFLAGS) -c $< -o $@

$(TARGET).elf: $(BUILD)/startup_trampoline.o startup_trampoline.ld
	$(CLANG) $(LDFLAGS) $< -o $@

$(TARGET).code.bin: $(TARGET).elf
	$(OBJCOPY) -O binary $< $@

$(TARGET).container.bin: $(TARGET).code.bin $(BASE)
	python3 $(ROOT)/tools/make_startup_trampoline.py $(BASE) $< $@

inspect: $(TARGET).container.bin
	python3 $(ROOT)/tools/firmware_image.py inspect $<
	llvm-readelf -h -S $(TARGET).elf

preflight: all $(STUB)
	python3 $(ROOT)/tools/verify_startup_trampoline.py $(BASE) $(TARGET).container.bin $(TARGET).code.bin $(TARGET).elf $(STUB)
	python3 -m unittest discover -s $(ROOT)/tests -p 'test_*.py'

clean:
	rm -r $(BUILD)

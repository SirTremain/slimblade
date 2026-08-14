REPO_ROOT := ../../../../..
BUILD := build
TARGET := $(BUILD)/stock-startup-reference
STOCK ?= /tmp/slimblade-v449.bin
CLANG ?= clang
OBJCOPY ?= llvm-objcopy

ARCH := --target=arm-none-eabi -mcpu=arm968e-s -march=armv5te
ASFLAGS := $(ARCH) -x assembler-with-cpp
LDFLAGS := $(ARCH) -nostdlib -fuse-ld=lld -Wl,-T,startup_reference.ld -Wl,-Map,$(TARGET).map

.PHONY: all clean inspect preflight

all: $(TARGET).bin $(TARGET).interrupt-wrappers.bin

$(BUILD):
	mkdir -p $@

$(BUILD)/startup_stock_reference.o: startup_stock_reference.S | $(BUILD)
	$(CLANG) $(ASFLAGS) -c $< -o $@

$(BUILD)/interrupt_wrappers_stock_reference.o: interrupt_wrappers_stock_reference.S | $(BUILD)
	$(CLANG) $(ASFLAGS) -c $< -o $@

$(TARGET).elf: $(BUILD)/startup_stock_reference.o $(BUILD)/interrupt_wrappers_stock_reference.o startup_reference.ld
	$(CLANG) $(LDFLAGS) $(BUILD)/startup_stock_reference.o $(BUILD)/interrupt_wrappers_stock_reference.o -o $@

$(TARGET).bin: $(TARGET).elf
	$(OBJCOPY) -O binary --only-section=.startup $< $@

$(TARGET).interrupt-wrappers.bin: $(TARGET).elf
	$(OBJCOPY) -O binary --gap-fill=0 --only-section=.irq_wrapper --only-section=.fiq_wrapper $< $@

inspect: $(TARGET).bin
	llvm-readelf -h -S $(TARGET).elf
	llvm-objdump -d $(TARGET).elf

preflight: $(TARGET).bin $(TARGET).interrupt-wrappers.bin
	python3 $(REPO_ROOT)/tools/verify_sdk_startup.py $(STOCK) $(TARGET).bin $(TARGET).interrupt-wrappers.bin $(TARGET).elf

clean:
	rm -r $(BUILD)

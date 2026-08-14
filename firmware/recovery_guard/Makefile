ROOT := ../..
BUILD := build
TARGET := $(BUILD)/DO_NOT_FLASH-marker-first-guard-hang-probe
STUB ?= ../recovery_stub/build/DO_NOT_FLASH-recovery-stub.container.bin

.PHONY: all inspect preflight clean

all: $(TARGET).container.bin inspect

$(BUILD):
	mkdir -p $@

$(STUB):
	$(MAKE) -C ../recovery_stub all

$(TARGET).container.bin: $(STUB) $(ROOT)/tools/make_recovery_guard.py | $(BUILD)
	python3 $(ROOT)/tools/make_recovery_guard.py $(STUB) $@ $(TARGET).code.bin

$(TARGET).code.bin: $(TARGET).container.bin
	test -f $@

inspect: $(TARGET).container.bin
	python3 $(ROOT)/tools/firmware_image.py inspect $<

preflight: all
	python3 $(ROOT)/tools/verify_recovery_guard.py $(STUB) $(TARGET).container.bin $(TARGET).code.bin
	python3 -m unittest discover -s $(ROOT)/tests -p 'test_*.py'

clean:
	rm -r $(BUILD)


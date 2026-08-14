
BUILD_DIR = build
TARGET    = BK3633_BIM_ALLROLES

AR = arm-none-eabi-gcc-ar
CC = arm-none-eabi-gcc

CCFLAGS  = -Os -mcpu=arm968e-s -march=armv5te -mthumb -mthumb-interwork -ffunction-sections -fdata-sections
CCFLAGS += -flto -fno-strict-aliasing -fgnu89-inline -ffast-math -fmessage-length=0
CCFLAGS += -Wall

LKFLAGS  = -Os -mcpu=arm968e-s -mthumb -mthumb-interwork -flto -ffunction-sections -fdata-sections
LKFLAGS += -nostartfiles

CCFLAGS += -I./config \
      -I./app \
      
LKFLAGS += $(LIB_INCS)
LKFLAGS += -T./lnk/link_bim.lds
LKLIBS  += 

ASMS = app/startup_bim.S \
	   app/handler_bim.S
	   
SRCS = app/bim_app.c \
       app/bim_icu.c \
       app/bim_intc.c \
	   app/bim_flash.c \
	   app/bim_gpio.c \
       app/bim_wdt.c \
       app/bim_updataImage.c \
	   app/bim_uart2.c

OBJS := $(SRCS:%.c=$(BUILD_DIR)/%.o)
OBJS += $(SRC1:%.c=$(BUILD_DIR)/dd1/%.o)
OBJS += $(SRC2:%.c=$(BUILD_DIR)/dd2/%.o)
OBJS += $(ASMS:%.S=$(BUILD_DIR)/%.o)
DEPS := $(OBJS:.o=.d)

target: $(BUILD_DIR)/$(TARGET).elf $(BUILD_DIR)/$(TARGET).bin

$(BUILD_DIR)/$(TARGET).elf : $(OBJS)
	@echo Build target: $@
	@$(CC) $(LKFLAGS) -o $@ $(OBJS) $(LKLIBS)
	@echo 'Finished building target: $@'
	@echo ' '

%.bin : %.elf
	@echo Build target: $@
	@arm-none-eabi-objcopy -O binary $< $@
	@arm-none-eabi-objdump -date     $<    > $(<:%.elf=%.dmp)
	@arm-none-eabi-nm                $<    > $(<:%.elf=%.map)
ifeq ($(OS),Windows_NT)
	@arm-none-eabi-readelf.exe       $< -a > $(<:%.elf=%.txt)
	@encrc -bc -o $(@:%.bin=%_crc.bin) $@
else
	@arm-none-eabi-readelf           $< -a > $(<:%.elf=%.txt)
	@./BinConvert -crc $@
	@cp -R ./build/BK3633_BIM_ALLROLES.bin ./output
	@cp -R ./build/BK3633_BIM_ALLROLES_crc.bin ./output
endif
	@cp -R ./build/BK3633_BIM_ALLROLES.bin ../app_gatt_all_roles/output/boot
	@cp -R ./build/BK3633_BIM_ALLROLES.bin ../app_gatt_all_roles_for_mesh/output/boot
	@cp -R ./build/BK3633_BIM_ALLROLES.elf ../../src/project_files
	@echo 'Finished building target: $@'
	@echo ' '

clean:
	@echo Clean project: $(TARGET)
	@-rm -rf $(OBJS) $(DEPS) $(BUILD_DIR)/$(TARGET).elf $(BUILD_DIR)/$(TARGET).bin
	-@echo ' '

prev-build:
	-@echo 'Pre-building'
	-@rm -rf $(BUILD_DIR)/$(TARGET)*.*
	-@echo ' '

post-build:
	-@echo 'Post-building'
	-@echo ' '

$(BUILD_DIR)/%.o : %.c
	@echo Compiling $<
	@mkdir -p $(dir $@)
	@$(CC) -c $(CCFLAGS) -MMD -MP -MF$(@:%.o=%.d) -MT$(@) $< -o $@

$(BUILD_DIR)/dd1/%.o : ../%.c
	@echo Compiling $<
	@mkdir -p $(dir $@)
	@$(CC) -c $(CCFLAGS) -MMD -MP -MF$(@:%.o=%.d) -MT$(@) $< -o $@

$(BUILD_DIR)/dd2/%.o : ../../%.c
	@echo Compiling $<
	@mkdir -p $(dir $@)
	@$(CC) -c $(CCFLAGS) -MMD -MP -MF$(@:%.o=%.d) -MT$(@) $< -o $@

$(BUILD_DIR)/%.o : %.S
	@echo Compiling $<
	@mkdir -p $(dir $@)
	@$(CC) -c $(CCFLAGS) -MMD -MP -MF$(@:%.o=%.d) -MT$(@) $< -o $@

ifneq ($(MAKECMDGOALS),clean)
ifneq ($(strip $(DEPS)),)
-include $(DEPS)
endif
endif

.PHONY : all clean pre-build post-build

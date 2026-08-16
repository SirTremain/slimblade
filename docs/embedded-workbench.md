# Embedded development workbench

Last checked: 2026-08-16

This list covers the SlimBlade recovery and likely future firmware, protocol,
and board-level projects. It is ordered by expected usefulness, not price.

## Buy or locate now

- Genuine Adafruit FT232H breakout (`ADA2264`) and a USB-C data cable.
- Digital multimeter with DC voltage and audible continuity. A Brymen BM235 is
  a good long-term meter; a basic functioning meter is sufficient for the
  immediate low-voltage checks.
- 10 or 20 cm jumper ribbons in female/female, male/female, and male/male.
- 30 AWG Kynar wire in at least two colours, fine heat-shrink, and spare
  2.54 mm breakaway headers.
- 0.5--0.7 mm electronics solder, no-clean flux pen, 1--2 mm desolder braid,
  isopropyl alcohol, lint-free swabs, and polyimide tape.
- Fine tweezers, flush cutters, a 20--30 AWG wire stripper, precision screwdrivers,
  and a non-metallic spudger.
- Stable PCB holder or helping hands, bright lighting, and magnification.
- ESD mat and wrist strap, eye protection, and solder-fume extraction.
- A small sacrificial PCB on which to practise soldering and removing fine wire
  before touching another irreplaceable board.

If the existing iron lacks temperature control or a fine replaceable tip, a
genuine Hakko FX-888DX with a 0.8--1.2 mm chisel tip is a durable general-purpose
replacement. A tiny needle tip is not automatically better because it transfers
heat poorly.

## High-value project instruments

- Yepkit YKUSH switchable USB hub. Its documented host command switches VBUS
  per port, allowing scripted, repeatable cold boots without manual unplugging.
- Saleae Logic 8. Eight digital channels are enough for the four-wire Beken SPI
  interface plus reset and auxiliary signals, and its protocol decoders will be
  valuable when tracing the sensor buses.
- Sensepeek PCBite kit with four SQ10 or SP10 probes. It provides a stable PCB
  base and hands-free needle contacts for a multimeter or logic analyser. It
  does not replace soldered wiring when six contacts must remain reliable for a
  full flash dump.
- A 0--30 V bench supply with adjustable current limiting, output enable, and
  readable low-current resolution. Current limiting is more important here
  than a large maximum current rating.
- A four-channel oscilloscope. A Rigol DHO804-class 12-bit, 70 MHz scope is ample
  for ordinary MCU power, clock, reset, UART, SPI, I2C, and sensor work.
- A 7--20x stereo optical microscope with a boom stand and ring light. It is
  generally more comfortable for live soldering than a low-cost USB microscope.

## Useful protocol and debug adapters

- Bus Pirate 5 for interactive SPI, I2C, UART, 1-Wire, and simple logic work.
  It complements rather than replaces the FT232H: the FT232H remains preferable
  for a locked-down Rust recovery tool.
- A genuine USB-to-UART adapter with selectable or clearly specified 1.8/3.3 V
  logic, plus mini-grabber leads. Never assume that a `3.3 V` power pin implies
  3.3 V signal levels.
- A full-size genuine SEGGER J-Link model with explicit legacy ARM9 support if
  that JTAG path becomes important. Confirm the exact model before ordering.
  The inexpensive J-Link EDU Mini supports JTAG electrically but not legacy
  ARM9 cores, so it is not the correct purchase for the BK3635 target. It
  remains a useful future probe for mainstream Cortex-M projects.
- A full-speed USB isolator for experiments involving unknown ground paths. Its
  isolated output-current limit and USB speed must be checked before use; do
  not insert it into a recovery setup merely by default.
- USB 2.0 A/B/C breakout boards and known-good short data cables for measuring
  VBUS and accessing D+/D-. Linux `usbmon` and Wireshark remain sufficient for
  ordinary USB protocol capture, so a dedicated USB protocol analyser is not a
  priority.

## Broader board-repair equipment

- Temperature-controlled hot-air rework station, heat-resistant mat, solder
  paste, and low-melt removal alloy.
- Universal flash programmer such as an XGecu T48/T56 with genuine SOIC clips
  and adapters. This is useful for discrete SPI/I2C memories but is not a
  substitute for the BK3635 programming interface.
- Digital calipers for connector pitch and mechanical measurements.
- Assorted breadboards, perfboard, resistor/capacitor kits, LEDs, switches,
  pin headers, JST leads, and small component organisers.
- A few mainstream development boards, such as Raspberry Pi Pico/Pico 2,
  STM32 Nucleo, and ESP32-S3, for testing host protocols and firmware ideas on
  documented hardware.

## Wait for measurements before buying

- Logic-level translators: choose them only after measuring the SlimBlade
  `VCC` and determining signal direction and speed.
- FFC/FPC breakout boards: first measure connector pitch and contact count.
- A Beken production programmer: no currently identified listing proves
  BK3635 support or safe readback behavior.
- A dedicated USB protocol analyser: useful only if software capture and a
  normal oscilloscope cannot answer a concrete USB question.

## Example sources

- [Adafruit FT232H at Core Electronics](https://core-electronics.com.au/adafruit-ft232h-breakout-general-purpose-usb-to-gpio-spi-i2c.html)
- [Brymen BM235 manufacturer page](https://www.brymen.com/PD02BM230_235.html)
- [Hakko FX-888DX and ESD-mat bundle](https://mektronics.com.au/products/hakko-fx888dx-soldering-station-silver-90-watt-genuine-esd-mat-300-x-500mm)
- [Yepkit YKUSH](https://www.yepkit.com/products/ykush)
- [Saleae Logic 8](https://store.saleae.com/products/logic-8)
- [Sensepeek PCBite SQ10 kit](https://kandaelectronics.com.au/products/pcbite-kit-with-4x-sq10-probes-and-test-wires)
- [Rigol DHO804 at Core Electronics](https://core-electronics.com.au/rigol-dho-804-oscilloscope.html)
- [SEGGER J-Link BASE model support](https://kb.segger.com/J-Link_BASE)
- [SEGGER J-Link EDU Mini limitations](https://kb.segger.com/J-Link_EDU)
- [Adafruit full-speed USB isolator](https://www.adafruit.com/product/2107)

# Embedded development workbench

Last checked: 2026-08-16

This list covers the SlimBlade recovery and likely future firmware, protocol,
and board-level projects. It is ordered by expected usefulness, not price.

## Desk-scale AUD 250 configuration

This project does not require a dedicated bench. A clear section of the
standing desk, a stable board holder, bright light, and a lidded container for
tools and contaminated consumables are sufficient.

The computer is an ASUS TUF GAMING B650-PLUS WIFI Rev 1.xx with AMD 600-series
and Raphael xHCI controllers. Its root hubs were tested on 2026-08-16 with
`uhubctl` 2.6.0 and libusb 1.0.30. It reported `No compatible devices
detected!`, so they do not advertise a usable per-port power-switching
interface. ASUS documents BIOS control of USB standby power when the entire PC
is in S4/S5, not live per-port VBUS control. A dedicated switch is required for
reliable scripted cold boots while the development host remains running.

### Current two-store shopping list

Prices and availability were checked on 2026-08-16. Store stock remains
location-dependent.

Core Electronics order:

- Adafruit FT232H breakout (`ADA2264`): AUD 27.80.
- 20 cm female/female 30 AWG jumper ribbon (`CE05098`): AUD 3.95. Cut one end
  from the required leads and solder those ends to the target pads.
- SparkFun USB-C extension cable with VBUS switch (`CAB-25579`): AUD 17.45.
  It keeps USB 2.0 D+/D- connected while switching VBUS, so it replaces manual
  unplugging but is not software controlled. Only one local unit was listed.

Core subtotal: AUD 49.20. Also check that a known-good USB-C data cable is
already available. The FT232H includes loose male headers, which still need to
be soldered.

Jaycar order:

- PCB holder with LED magnifier and iron stand (`TH1987`): AUD 24.95.
- Duratech 48 W temperature-controlled soldering station (`TS1620`):
  AUD 61.95. It includes a 1 mm conical tip, a lightweight low-voltage pencil,
  a stand and sponge, and a mains-earth socket for static-sensitive work.
- 0.71 mm 60/40 resin-core solder (`NS3008`): AUD 2.95 sale price.
- No-clean flux pen (`NS3036`): AUD 17.50.
- 1.5 mm Goot desolder braid (`NS3026`): AUD 10.25.
- 16 mm polyimide tape (`NM2892`): AUD 12.95.
- Anti-magnetic precision tweezers (`TH1754`): AUD 3.95 sale price.
- 99.8% IPA spray (`NA1066`): AUD 13.95.
- Autoranging multimeter with audible continuity (`QM1528`): AUD 26.95,
  **only if the existing meter cannot be found and verified**.

The Jaycar subtotal is AUD 148.45 without the meter or AUD 175.40 with it.
The combined product total is therefore AUD 197.65 or AUD 224.60, before the
two stores' delivery charges.

Useful additions that are not part of that total:

- Core dual USB power switch (`TPH-105499`), AUD 8.95. An FT232H GPIO can drive
  its `EN` input, but it is power-only and requires a custom adapter that routes
  USB D+/D- around it. It is not a drop-in programmable USB hub.
- Core 8-channel 24 MHz sigrok analyser (`TOL-18627`), AUD 49.30. Defer until
  recovery works unless the extra spend is comfortable.
- Jaycar 30 AWG Kynar wire (`WW4346`), AUD 17.95; useful for later permanent
  fly-wires, but the jumper ribbon covers the immediate connection.
- Jaycar benchtop mat (`HM8100`), AUD 9.50 sale price.
- Jaycar small prototyping board (`HP9570`), AUD 6.95, if no scrap board is
  available for practising fine-wire attachment and removal first.
- Jaycar 0.5 mm conical tip for the station (`TS1622`), AUD 12.50. Do not buy
  it initially: the included 1 mm tip transfers heat better and is already
  fine enough for the known pads.

Do not order an iron tip by appearance. Identify the iron model and tip family
first, then choose a compatible roughly 0.8--1.2 mm chisel or conical tip.

No desktop fume extractor is included. Arrange the existing large fan and open
window so the entire plume travels away from the face and outside. Stop if the
airflow does not reliably do that. A true ducted extractor remains a later
upgrade.

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

- A proven `uhubctl`-compatible hub remains a future convenience, but the
  YKUSH XS is outside the current value threshold. Exact hardware revisions of
  cheaper hubs must be verified before purchase.
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
- [Core female/female jumper ribbon](https://core-electronics.com.au/prototyping/prototyping-wire/female-female.html)
- [Core USB-C data cable with VBUS switch](https://core-electronics.com.au/usb-c-extension-cable-with-power-switch-1m.html)
- [Core GPIO-controlled dual USB power switch](https://core-electronics.com.au/usb-power-switch-dual.html)
- [Core 24 MHz sigrok logic analyser](https://core-electronics.com.au/usb-logic-analyzer-24mhz-8-channel.html)
- [Jaycar PCB holder and magnifier](https://www.jaycar.com.au/holder-pcb-with-led-magnifier-and-soldering-iron-stand/p/TH1987)
- [Jaycar Duratech 48 W soldering station](https://www.jaycar.com.au/duratech-48w-temperature-controlled-soldering-station/p/TS1620)
- [Jaycar 0.5 mm tip for the TS1620](https://www.jaycar.com.au/conical-0-5mm-soldering-iron-tip/p/TS1622)
- [Jaycar soldering supplies](https://www.jaycar.com.au/soldering)
- [Brymen BM235 manufacturer page](https://www.brymen.com/PD02BM230_235.html)
- [Hakko FX-888DX and ESD-mat bundle](https://mektronics.com.au/products/hakko-fx888dx-soldering-station-silver-90-watt-genuine-esd-mat-300-x-500mm)
- [Yepkit YKUSH](https://www.yepkit.com/products/ykush)
- [Yepkit YKUSH XS](https://www.yepkit.com/product/300115/YKUSHXS)
- [Saleae Logic 8](https://store.saleae.com/products/logic-8)
- [Local 24 MHz sigrok logic analyser](https://www.phippselectronics.com/product/usb-8-channel-24mhz-logic-analyser/)
- [Sensepeek PCBite SQ10 kit](https://kandaelectronics.com.au/products/pcbite-kit-with-4x-sq10-probes-and-test-wires)
- [Rigol DHO804 at Core Electronics](https://core-electronics.com.au/rigol-dho-804-oscilloscope.html)
- [SEGGER J-Link BASE model support](https://kb.segger.com/J-Link_BASE)
- [SEGGER J-Link EDU Mini limitations](https://kb.segger.com/J-Link_EDU)
- [Adafruit full-speed USB isolator](https://www.adafruit.com/product/2107)
- [HSE solder-fume guidance](https://www.hse.gov.uk/lung-disease/electronics-soldering.htm)
- [ASUS TUF GAMING B650-PLUS WIFI specifications](https://www.asus.com/uk/motherboards-components/motherboards/tuf-gaming/tuf-gaming-b650-plus-wifi/techspec/)

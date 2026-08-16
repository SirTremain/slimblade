# Board observations

Last checked: 2026-08-16

User-supplied board photographs are stored in [`images/`](../images/). They show the component side in four overlapping regions.

## Identified parts

- Controller: `BK3635UQN56A`, secondary marking `AU334KX`.
- PCB marking: `JP32088B`, with secondary marking `2544`.
- `SW2`: three-position 2.4 GHz / wired / Bluetooth mode selector; nearby silkscreen includes `2.4`, `W1`, and `B1`.
- With `SW2` at `W1`, the device resumed normal wired USB operation after USB was disconnected and reconnected. The status LED remained solid red while the battery was charging, so red can obscure the normal wired-status indication.
- `DPI`: ordinary external DPI/pairing momentary button.
- The four large black parts are the main mechanical mouse-button switches. Their silkscreen is partly obscured; visible/reported labels include `SWM`, `SML`/`SWL`, `SMR`/`SWR`, and `SWB`/`BB`. The holes and colored actuator visible in each housing are mechanical features, not reset access.
- `J2` and `J3`: flat-flex connectors leading to the sensor/button assemblies.

None of the component-side controls is marked boot or reset. [`back.jpg`](../images/back.jpg) directly confirms a reverse-side factory pad cluster labeled `RSTN`, `P04`, `P05`, `P06`, `P07`, `VCC`, and `GND`. The four GPIO traces run together toward the controller, consistent with the BK3635 programming/debug interface.

The official BK3633 datasheet provides a stronger related-chip mapping than
the production document below: in JTAG mode, `P04=TDI`, `P05=TDO`, `P06=TCK`,
and `P07=TMS`; in programming mode, the same pins are SPI MOSI, MISO, SCK, and
CS. It assigns `P03=JTAG_NTRST`, but the photographed cluster has no `P03` pad.
These assignments remain a BK3635 hypothesis until a read-only scan succeeds.
See [Hardware-assisted loader entry](hardware-loader-entry.md).

A Tuya production-programming document for the closely related BK3632 maps the
same four labels as `P07=SPI_CS`, `P05=SPI_MISO`, `P04=SPI_MOSI`, and
`P06=SPI_SCK`, alongside `RSTN`, supply, and ground. The physical match is
strong evidence for the purpose of this board's cluster, but it is not a
BK3635 pinout or proof that a generic SPI adapter implements the required flash
protocol. Do not connect a programmer until signal voltage and BK3635 tool
compatibility are established.

## Boot-mode indicator

The official updater recognizes generic boot-device VID/PIDs `25A7:FABE`, `3554:F600`, and `3554:F800`, distinct from the normal Kensington application VID/PID `047D:80D7`. USB enumeration under one of those generic IDs would confirm bootloader mode without writing flash.

## Sources

- [Beken BK3635 product page](https://www.bekencorp.com/en/goods/detail/cid/46.html), retrieved 2026-08-16: JTAG debugging, SPI flash download, `1.8–3.6 V` battery supply, and `4.75–5.25 V` USB supply.
- [BK3633 Datasheet V0.5](https://gitee.com/beken-corp/bk3633_ble_sdk/raw/master/BK3633%20Datasheet_V0.5.pdf), retrieved 2026-08-16: related-chip programming/JTAG GPIO mapping; 600,626 bytes; SHA-256 `2772e7ca7f9c253c478d9c8547100fce34cc99db0f86e8fd48f920fded9a4da5`.
- [BK3633 quick-start guide V1.0](https://gitee.com/beken-corp/bk3633_ble_sdk/raw/master/Tools/BK3633%E4%BD%BF%E7%94%A8%E5%BF%AB%E9%80%9F%E5%85%A5%E9%97%A8.pdf), retrieved 2026-08-16: Beken HID SPI-programmer wiring and read/download tooling; 828,711 bytes; SHA-256 `347e019c5701dbc6b8e9b2b2249efc346dc3dad42a29bea0b7dbaa26024736cb`.
- [Tuya production-programming document](https://images.tuyacn.com/goat/pdf/01JJ5YK07MZ71F4M4JEV737R4H/%E8%8A%AF%E7%89%87%E7%83%A7%E5%BD%95_%E6%B6%82%E9%B8%A6%E5%BC%80%E5%8F%91%E8%80%85%E5%B9%B3%E5%8F%B0_%E6%B6%82%E9%B8%A6%E5%BC%80%E5%8F%91%E8%80%85%E5%B9%B3%E5%8F%B0.pdf), version 2025-01-22, retrieved 2026-08-16: closely related BK3632 factory SPI-pad mapping.

# Board observations

Last checked: 2026-08-14

User-supplied board photographs are stored in [`images/`](../images/). They show the component side in four overlapping regions.

## Identified parts

- Controller: `BK3635UQN56A`, secondary marking `AU334KX`.
- PCB marking: `JP32088B`, with secondary marking `2544`.
- `SW2`: three-position 2.4 GHz / wired / Bluetooth mode selector; nearby silkscreen includes `2.4`, `W1`, and `B1`.
- With `SW2` at `W1`, the device resumed normal wired USB operation after USB was disconnected and reconnected. The status LED remained solid red while the battery was charging, so red can obscure the normal wired-status indication.
- `DPI`: ordinary external DPI/pairing momentary button.
- The four large black parts are the main mechanical mouse-button switches. Their silkscreen is partly obscured; visible/reported labels include `SWM`, `SML`/`SWL`, `SMR`/`SWR`, and `SWB`/`BB`. The holes and colored actuator visible in each housing are mechanical features, not reset access.
- `J2` and `J3`: flat-flex connectors leading to the sensor/button assemblies.

None of the component-side controls is marked boot or reset. [`back.jpg`](../images/back.jpg) directly confirms a reverse-side factory pad cluster labeled `RSTN`, `P04`, `P05`, `P06`, `P07`, `VCC`, and `GND`. The four GPIO traces run together toward the controller, consistent with the BK3635 programming/debug interface. Exact signal assignments remain unverified.

## Boot-mode indicator

The official updater recognizes generic boot-device VID/PIDs `25A7:FABE`, `3554:F600`, and `3554:F800`, distinct from the normal Kensington application VID/PID `047D:80D7`. USB enumeration under one of those generic IDs would confirm bootloader mode without writing flash.

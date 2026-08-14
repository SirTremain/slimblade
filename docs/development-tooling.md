# Development tooling

Last checked: 2026-08-14

## Stable device paths

[`udev/70-slimblade-research.rules`](../udev/70-slimblade-research.rules) now defines stable symlinks instead of requiring changing `hidrawN` numbers. The rule passes `udevadm verify` and is installed system-wide.

- `/dev/slimblade-vendor`: `047d:80d7`, USB interface `01`; verified as the 170-byte vendor/updater report-descriptor interface.
- `/dev/slimblade-loader`: any recorded loader identity (`25a7:fabe`, `3554:f600`, or `3554:f800`).

Live application validation passed on 2026-08-14: `/dev/slimblade-vendor` resolved to the current `/dev/hidraw4`, udev reported USB interface `01` and revision `0452`, and the utility read the expected 170-byte vendor descriptor. `/dev/slimblade-loader` is absent in normal application mode as intended; its rule awaits validation during the next loader transition.

The USB utility now defaults application commands to `/dev/slimblade-vendor`. Loader commands should name `/dev/slimblade-loader`; application flashing also scans that link and current `hidraw` nodes during its pre-erase retry window.

The normal mouse-report interface is USB interface `00` and should not receive updater commands. Current udev properties expose `ID_USB_INTERFACE_NUM=00` and `01`, so the application symlink distinguishes them without depending on enumeration order. An initial rule incorrectly combined USB-device and USB-interface `ATTRS` matches and did not create the link; the corrected rule uses the verified `ID_USB_INTERFACE_NUM=01` property.

A stable symlink does not by itself remove the resident loader's periodic disconnect/re-enumeration race. The flashing utility now searches the preferred path, `/dev/slimblade-loader`, and current `hidraw` nodes until it opens a recognized loader and receives `B2 → d2`. This retry is bounded and exists only before command `B0`. Once `B0` is attempted, any error stops without a blind retry because erase or partial transfer may already have started.

# Development tooling

Last checked: 2026-08-14

## Stable device paths

TODO after reset-trampoline validation: extend the repository udev rules to create stable symlinks instead of referring to changing `hidrawN` numbers.

- `/dev/slimblade-vendor`: `047d:80d7`, USB interface `01`; verified as the 170-byte vendor/updater report-descriptor interface.
- `/dev/slimblade-loader`: any recorded loader identity (`25a7:fabe`, `3554:f600`, or `3554:f800`).

The normal mouse-report interface is USB interface `00` and should not receive updater commands. Current udev properties expose `ID_USB_INTERFACE_NUM=00` and `01`, so the application symlink can distinguish them without depending on enumeration order.

A stable symlink does not by itself remove the resident loader's periodic disconnect/re-enumeration race. The flashing utility should also wait for and reopen the loader when identity/open fails before command `B0`. It must not blindly retry after `B0`, because erase or partial transfer may already have started.

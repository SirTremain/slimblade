Plan is basically to create custom firmware for the Slimblade Kensington pro and expose the raw Z-zxis rotation to the OS, along with the raw X and Y axis rotation. Then, I guess it would need a small custom driver and some sort of plugin initially for Blender (it is open source so should be the easiest to develop a plugin for).

The idea would be that it is a software only solution. There are some potential problems/things to figure out:

- the slimblade uses 2 sensors, so mayb it's better to send the raw sensor data and just handle the 3-axis rotation part on the software side.
- the firmware must be able to be flashed onto the slimblade
- the original firmware must not be so complicated it can't be decompiled and at least semi figured out OR the sensors must be obvious enough inputs to whatever microcontroller it uses so I can write a firmware from scratch
- the board in it must be able to be fixed if I ever fully break it by flashing a broken firmware. i.e I ahve to be able to flash the actual software on there as a recovery. I don't want to brick my one slimblade pro
- The firmware must be able to actually be flashed onto the device, this means it can't have things like authenticity checks etc. built into it (it might require the firmware be signed with specific private keys I don't have for instance)
- preferably no readout protection so I can just read out the existing bootloader and then reuse it for the custom firmware.
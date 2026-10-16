# SlimBlade pogo fixture

Retained historical fixture design, not an active fabrication or device-access
assignment. The [project plan](../../docs/project-plan.md) defines current
hardware gates. Preserve the existing fabrication lock; revalidate the design
and target compatibility before any separately requested fixture work.

This fixture provides repeatable access to `RSTN`, `P04`--`P07`, `VCC`, and
`GND` without soldering to the SlimBlade PCB. The damaged controller is the
mechanical prototype; the replacement controller must not be the first board
used to check fit or probe travel.

## Design

Keep the controller attached to its factory plastic frame with its original
screws. A printed cradle locates that frame from several exterior edges and
non-delicate moulded features. A separate probe plate travels vertically on
two guide shafts and carries seven pogo probes. Clamp force reacts through the
factory frame rather than through a programming pad or a single PCB screw.

The one accessible PCB screw hole and a long frame/PCB edge are sufficient
measurement datums. The screw remains a factory fastener; it is not a jig
clamp point.

Use P75 probes in R75 receptacles if practical. Receptacles make probe height
more repeatable and let a bent probe be replaced without rewiring the fixture.
Raw P75 probes can instead be friction-fitted into the printed probe plate and
fixed only after their height and travel have been checked against the old
board, but that is the less serviceable construction.

Only the fixture is soldered. The target controller remains unmodified.

## Files

- [`measurements.json`](measurements.json) is the single source of board and
  fixture dimensions. Its incomplete values intentionally block generation.
- [`MEASURING.md`](MEASURING.md) defines the coordinate system and required
  measurements.
- [`generate_fixture.py`](generate_fixture.py) validates the measurements and
  creates editable FreeCAD, STEP, and STL models.
- [`SHOPPING.md`](SHOPPING.md) lists the fixture parts and Australian sources.
- `generated/` is ignored because its files are reproducible.

The present generator is the validated earlier two-hole carrier prototype. It
remains fabrication-locked and will be revised to the chassis-cradle design
after the frame geometry is measured. Do not set
`confirmed_for_fabrication=true` in the present measurement file.

Generate after every required value has been measured and
`confirmed_for_fabrication` has deliberately been changed to `true`:

```sh
freecadcmd hardware/pogo_fixture/generate_fixture.py --pass --measurements hardware/pogo_fixture/measurements.json --output hardware/pogo_fixture/generated
```

The legacy output contains a carrier and a printer-specific bore calibration
coupon. The revised generator will instead produce a cradle and probe plate.
The `.FCStd` document retains named objects and custom properties for normal
editing in FreeCAD.

## Mechanical gates

Do these in order, using the old board:

1. Print the bore coupon. Update `pogo_bore_diameter_mm` to the hole that gives
   a straight, close sliding fit for the chosen receptacle or raw probe.
2. Print the cradle and empty probe plate without installing electrically
   connected probes. Check that the factory frame seats against all intended
   cradle contacts and cannot translate or rotate.
3. Insert blunt rods or unconnected probes. Put removable marker ink on their
   tips, clamp once, then inspect the witness marks under magnification. Every
   mark must be centred on its intended pad.
4. Fit all probes and measure their compression. No probe may bottom out, and
   the factory frame must remain fully seated without visible PCB flex.
5. Repeat the clamp cycle at least ten times. Pad centring must remain stable.

Failure at any gate means adjust the dimensions and reprint. Do not make the
replacement board compensate for a tight cradle or a misaligned probe.

## Electrical gates

The fixture terminates at a keyed connector; it must not expose FT232H `3V` or
`5V`. `VCC` is a voltage reference for target-native pull-ups, never a target
power feed.

A 2x5 keyed 2.54 mm IDC header is the default fixture boundary:

| IDC pin | Signal | IDC pin | Signal |
| ---: | --- | ---: | --- |
| 1 | `GND` | 2 | `VCC_REF` |
| 3 | `RSTN` | 4 | `P04` |
| 5 | `P05` | 6 | `P06` |
| 7 | `P07` | 8 | not connected |
| 9 | not connected | 10 | not connected |

The shroud and cable key must be fitted; an unkeyed loose header defeats this
interface boundary.

| Contact | Fixture output | FT232H path |
| --- | --- | --- |
| `GND` | ground | `GND` |
| `VCC` | target reference | pull-ups only |
| `RSTN` | reset | `D4` through 470 ohm |
| `P04` | MOSI candidate | `D1` through 470 ohm |
| `P05` | MISO candidate | `D2` through 1 kohm |
| `P06` | SCK candidate | `D0` through 470 ohm |
| `P07` | CS candidate | `D3` through 470 ohm |

Before target power is connected:

1. Check for shorts between every adjacent fixture contact and between each
   signal and both rails.
2. Check continuity from each probe tip to the labelled connector pin.
3. Start the FT232H in high-impedance drive-zero mode.
4. Connect the fixture to the unpowered controller, then power the controller
   from its normal USB cable.
5. Run only identification and bounded read commands. Erase, write, unlock,
   and protection commands remain out of scope until two identical full dumps
   have been verified offline.

## Print and assembly starting points

- Print the first cradle and probe plate in PETG at 0.20 mm layers, four walls,
  and at least 30% infill. PLA is adequate for disposable fit checks.
- A 0.4 mm nozzle is suitable. Bore diameter must be selected from the printed
  coupon because printer compensation matters more than the nominal nozzle.
- Use heat-set inserts and fixture-side M3 fasteners for the moving mechanism.
  Do not replace, load, or clamp through the original PCB screw.
- Add strain relief to the fixture cable so it cannot load the pogo plate.

## Open decisions

- Whether raw P75 probes already on hand are adequate or R75 receptacles should
  be ordered.
- Which exterior frame edges or moulded features provide three non-collinear,
  repeatable cradle contacts without touching delicate components.
- Whether the final electronics should remain on a breadboard or move to a
  small keyed interface PCB attached to the printed cradle.

## References

- [Adafruit P75-B1 dimensions](https://www.adafruit.com/product/2430), checked
  2026-08-18: 1.0 mm body, 0.7 mm needle head, and 16--13 mm free/compressed
  length.
- [Adafruit pogo-pin fixture guide](https://learn.adafruit.com/how-to-make-a-pogo-pin-test-jig?view=all),
  checked 2026-08-18: a practical two-plate fixture construction reference.

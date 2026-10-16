# Pogo-clamp shopping list

Archived procurement notes, not a current shopping instruction. These parts are
not prerequisites for offline decompilation. See the [fixture status](README.md)
and [project plan](../../docs/project-plan.md) before planning new hardware work.

Checked: 2026-08-19. Prices are AUD including GST where the seller states it.
Stock and freight can change.

## Construction being supplied

The SlimBlade controller stays screwed to its original plastic frame. A
printed cradle locates the frame, while a printed probe plate moves vertically
on two 6 mm shafts. Four linear bearings prevent lateral drift. Springs lift
the plate; two hand-adjusted stops initially limit downward travel. A toggle
clamp is an optional later convenience and must never be the travel stop.

## Historical purchase list

### Core Electronics

| Qty | Item | Price checked | Purpose |
| ---: | --- | ---: | --- |
| 2 packs | [Adafruit P75-B1 needle pogo pins, 10/pack](https://core-electronics.com.au/pogo-pins-needle-head-10-pack-p75-b1.html) | $9.30/pack | Seven fitted probes and thirteen spares |
| 1 | [M2--M6 heat-set insert kit](https://core-electronics.com.au/heat-set-insert-nut-for-3d-prints-m2-m3-m4-m5-m6-kit-300pcs.html) | $26.40 | Durable removable joints in the printed cradle and probe plate |
| 1 | [Half-size Perma-Proto PCB](https://core-electronics.com.au/catalog/product/view/sku/ADA1609) | $9.45 | Permanent fixture-side pull-ups, series resistors, and connector |
| 5 | [2x5 2.54 mm keyed box header](https://core-electronics.com.au/box-idc-header-2x5.html) | $0.23 each | Two fitted, one test adapter, two spares |
| 1, optional | [1% passives pack](https://core-electronics.com.au/passives-pack-resistors-and-diodes.html) | $9.80 | Large reserve of 470 ohm, 1 kohm, and 10 kohm parts |

Core subtotal: **$55.60**, or **$65.40** with the redundant resistor pack.
The loose resistors already on hand are sufficient, so the passives pack is
not a project blocker.

### Maker Store

| Qty | Item | Price checked | Purpose |
| ---: | --- | ---: | --- |
| 3 | [6 mm smooth rod, 150 mm](https://www.makerstore.com.au/product/hard-rod-6/) | from $2.71 each | Two vertical guides and one spare |
| 6 | [LM6UU 6 mm linear bearing](https://www.makerstore.com.au/product/bear-lm6uu/) | $1.88 each | Four in the moving plate and two spares |

Expected subtotal using the listed starting rod price: about **$19.41**. The
150 mm rods can remain full length; cutting hardened shaft is unnecessary.

### Tempero Systems

| Qty | Item | Price checked | Purpose |
| ---: | --- | ---: | --- |
| 3 | [10-pin 2x5 socket-to-socket IDC cable](https://temperosystems.com.au/products/10-pin-socket-socket-idc-ribbon-cable/) | from $3.95 each | Fixture cable, bench cable, and spare |

Select the **2.54 mm/0.100 inch** version, not the smaller 1.27 mm SWD cable.
The expected subtotal for the shortest listed version is **$11.85**.

### Jaycar

| Qty | Item | Price checked | Purpose |
| ---: | --- | ---: | --- |
| 1 | [200-piece compression/tension spring assortment, HP0638](https://www.jaycar.com.au/200-piece-spring-assortment/p/HP0638) | $19.95 | Select matched light return springs for the moving plate |
| 1 pack | [M3 x 25 mm nylon screws, HP0142](https://www.jaycar.com.au/m3-x-25mm-nylon-screws-pack-of-10/p/HP0142) | $3.50 | Nonconductive adjustable hard stops |
| 1 pack | [M3 nylon nuts/washers, HP0150](https://www.jaycar.com.au/3mm-nylon-nuts-and-washer-pack-of-25/p/HP0150) | $6.50 | Lock the hard-stop adjustment |
| 1 pack | [M3 nylon washers, HP0148](https://www.jaycar.com.au/tools-test-equipment/tools/screws-fasteners/c/7FJ?p=3) | $2.50 | Spares and non-marring contact surfaces |
| 1 pack | [11 mm screw-fixed rubber feet, HP0800](https://www.jaycar.com.au/11mm-screw-fixing-rubber-feet-pack-of-8/p/HP0800) | $4.50 | Stable desk base; screw-fixed is preferable to adhesive |
| 1 | [Two-part epoxy, NA1510](https://www.jaycar.com.au/epoxy-bond-glue-34ml/p/NA1510) | $13.25 | Retain pogo barrels only after travel has been proved |
| 1 | [1.5--10 mm heat-shrink assortment, WH5525](https://www.jaycar.com.au/assorted-heatshrink-pack-1-5-10mm/p/WH5525) | $9.25 | Probe-tail insulation and cable strain relief |
| 1, if absent | [30 AWG Kynar wire, WW4346](https://www.jaycar.com.au/blue-wire-wrap-wire-on-spool/p/WW4346) | $17.95 | Short fixed wiring between probes and fixture PCB |

Jaycar subtotal: **$59.45**, or **$77.40** if another Kynar spool is needed.

### Local fastener shop or Bunnings

Buy one small pack each of M3 x 10, 20, 35, and 50 mm steel machine screws,
plus M3 flat washers and nuts. These fasten only printed fixture parts and
heat-set inserts; none touches the SlimBlade PCB. Typical small-pack pricing is
roughly $2--$4 per length. The original Kensington PCB screws remain in the
mouse and need no replacement.

Also ensure at least 250 g of dry PETG is available. A full 1 kg spool is worth
buying only if no suitable filament is already on hand.

## Optional after the screw-driven clamp works

- One [Good Hand GH-101A vertical toggle clamp](https://www.carbatec.com.au/products/clamp-toggle-gh-101a),
  checked at $15. Its 50 kg holding rating is vastly above what the PCB needs.
  Fit it only after the printed hard stops independently prevent excessive
  probe travel.
- One [10-pin IDC rainbow breakout cable](https://littlebirdelectronics.com.au/products/10-pin-idc-socket-rainbow-breakout-cable),
  checked at $8.60, if individual female leads are more convenient at the
  FT232H end than a second small adapter PCB.
- TPU filament or thin closed-cell rubber for replaceable cradle pads. Do not
  use soft foam to establish probe height because it compresses unpredictably.
- A phone desk arm or tripod for orthogonal measurement photographs. Manual
  calipers remain the dimensional reference; the phone image records geometry
  and helps locate the damaged pad centres.

## Already reported on hand

Check these before ordering duplicates:

- Adafruit FT232H and USB data cable;
- multimeter with continuity mode;
- soldering equipment, flux, braid, IPA, tweezers, and magnification;
- breadboard and jumper leads;
- 470 ohm, 1 kohm, and 10 kohm resistors;
- manual calipers and a capable 0.4 mm-nozzle 3D printer;
- original SlimBlade plastic frame and PCB mounting screws.

## Expected spend

The core fixture purchases are approximately **$146.31** before freight when
the redundant resistor pack is omitted:

- Core without redundant resistors: $55.60;
- Maker Store motion hardware: about $19.41;
- Tempero IDC cables: from $11.85;
- Jaycar without another Kynar spool: $59.45;
- add $9.80 if the redundant resistor pack is wanted;
- add roughly $10--$20 for local M3 fasteners.

Including the local M3 fasteners gives a likely **$156.31--$166.31 before
freight**. Adding the resistor pack, Kynar wire, and toggle clamp brings that
to about **$199.06--$209.06 before freight**. The screw-driven, hard-stopped
version is safer for first contact.

# Measuring the controller

Historical fixture instructions. No measurement, disassembly or probe work is
part of the current offline reconstruction task. See the
[fixture status](README.md) and [project plan](../../docs/project-plan.md)
before using this procedure in a separately requested hardware session.

Do not infer fabrication dimensions directly from `images/back.jpg`; it has
perspective distortion. Use the damaged controller for mounting geometry and
the earlier photograph for the original pad locations. If damaged holes no
longer have clear centres, register the old photograph against a new flat scan
using several undamaged vias and frame features around the pad cluster.

The replacement controller should receive only a non-contact optical check:
confirm the seven centres against a flat scan or orthogonal photograph before
installing probes. It must not be used to discover whether a printed boss fits.

## Coordinate system

- Use the accessible screw hole nearest the pad cluster as datum `L1`.
- Set the centre of `L1` to `(0, 0)`.
- Choose a long straight PCB or plastic-frame edge as the rotational datum.
- Define `+X` parallel to that edge in the direction documented in the setup
  photograph; `+Y` is 90 degrees counter-clockwise when viewing the
  factory-pad side.
- Record all centres in millimetres to two decimal places. Record raw readings
  as well; do not silently average inconsistent measurements.

The revised generator will rotate nothing: coordinates entered in the revised
measurement schema will appear directly in FreeCAD. The present JSON and
generator still describe the rejected two-hole prototype and remain
fabrication-locked; do not enter final measurements into them yet.

## Preferred method

A flatbed scan at 600--1200 DPI is the easiest accurate source:

1. Put the bare PCB pad-side down with a steel rule or calibration square in
   the same plane.
2. Keep the board flat without loading components on the opposite side.
3. Save the original scan without resizing or perspective correction.
4. Calibrate pixels per millimetre from the rule in both axes.
5. Measure each feature centre relative to `L1`, then independently verify its
   perpendicular offset from the selected straight edge with calipers.

For the damaged `P04`, `P06`, and `P07` area, align the original undamaged
photograph to the scan with at least six shared points surrounding the pad
cluster. Use a perspective transform, not simple scaling. Reject the result if
the transformed check points differ from the scan by more than 0.15 mm.

If no scanner is available, use a camera on a rigid support directly above the
board, zoom in rather than using a wide lens, and include a rule in the PCB
plane. Camera-derived coordinates are provisional until the printed witness
test passes.

## Required measurements

Record these for the forthcoming revision of
[`measurements.json`](measurements.json):

- PCB thickness.
- `L1` hole diameter and the location of the selected straight-edge datum.
- At least three exterior frame contact features for the printed cradle.
- For every contact: centre `x`, centre `y`, and remaining copper diameter.
- Circular or rectangular bottom-side keep-outs for component leads, solder
  joints, or other features that must not touch the printed cradle or probe
  plate.
- The dimensions and heights of the selected frame contacts that will seat in
  the cradle without loading the PCB.
- The actual receptacle or probe body diameter measured with calipers.

Measure centre-to-centre spans over several features where possible. For
example, measure from the left edge of `P04` to the right edge of `P07`, then
subtract the radii; this reduces the relative error of measuring tiny centres
one at a time.

## Data quality gates

- Repeat each `L1`--contact measurement and independently check it from the
  selected straight edge.
- Coordinates derived by the two routes must agree within 0.15 mm.
- The revised generator will require one point datum, one rotational edge,
  three cradle contacts, and exactly seven uniquely named contacts.
- Keep-out geometry must be measured before fabrication is confirmed.
- Change `confirmed_for_fabrication` to `true` only after the JSON has been
  reviewed against the bare board and the original undamaged photograph.

The printed ink-witness test is the final geometry measurement. It takes
precedence over apparently precise camera coordinates.

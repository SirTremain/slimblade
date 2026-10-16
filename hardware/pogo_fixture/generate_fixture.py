#!/usr/bin/env python3
"""Generate the measured SlimBlade pogo carrier with FreeCAD.

This script is intentionally strict: incomplete, unconfirmed, or geometrically
unsafe measurement files do not produce fabrication artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import FreeCAD as App
import Mesh
import Part


CONTACT_NAMES = {"RSTN", "P04", "P05", "P06", "P07", "VCC", "GND"}


class MeasurementError(ValueError):
    """Raised when fixture measurements are incomplete or unsafe."""


def number(value: Any, path: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MeasurementError(f"{path} must be a number, got {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise MeasurementError(f"{path} must be finite")
    if positive and result <= 0:
        raise MeasurementError(f"{path} must be greater than zero")
    return result


def named_items(data: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    items = data.get(key)
    if not isinstance(items, list):
        raise MeasurementError(f"{key} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise MeasurementError(f"{key}[{index}] must be an object")
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise MeasurementError(f"{key}[{index}].name must be non-empty")
        if name in result:
            raise MeasurementError(f"duplicate {key} name {name!r}")
        result[name] = item
    return result


def validate(data: dict[str, Any]) -> None:
    if data.get("schema_version") != 1:
        raise MeasurementError("schema_version must be 1")
    if data.get("units") != "mm":
        raise MeasurementError("units must be 'mm'")
    if data.get("confirmed_for_fabrication") is not True:
        raise MeasurementError(
            "confirmed_for_fabrication is not true; review every measurement first"
        )

    board = data.get("board")
    fixture = data.get("fixture")
    if not isinstance(board, dict) or not isinstance(fixture, dict):
        raise MeasurementError("board and fixture must be objects")
    number(board.get("thickness_mm"), "board.thickness_mm", positive=True)

    locators = named_items(data, "locators")
    if set(locators) != {"L1", "L2"}:
        raise MeasurementError("locators must contain exactly L1 and L2")
    for name, item in locators.items():
        number(item.get("x_mm"), f"locators.{name}.x_mm")
        number(item.get("y_mm"), f"locators.{name}.y_mm")
        number(
            item.get("hole_diameter_mm"),
            f"locators.{name}.hole_diameter_mm",
            positive=True,
        )
        number(
            item.get("support_diameter_mm"),
            f"locators.{name}.support_diameter_mm",
            positive=True,
        )

    if abs(number(locators["L1"]["x_mm"], "L1.x")) > 1e-6 or abs(
        number(locators["L1"]["y_mm"], "L1.y")
    ) > 1e-6:
        raise MeasurementError("L1 must be at (0, 0)")
    if abs(number(locators["L2"]["y_mm"], "L2.y")) > 0.05:
        raise MeasurementError("rotate measurements so L2 lies on the +X axis")
    if number(locators["L2"]["x_mm"], "L2.x") <= 0:
        raise MeasurementError("L2 must lie in the +X direction from L1")

    contacts = named_items(data, "contacts")
    if set(contacts) != CONTACT_NAMES:
        missing = sorted(CONTACT_NAMES - set(contacts))
        extra = sorted(set(contacts) - CONTACT_NAMES)
        raise MeasurementError(
            f"contacts must be exactly {sorted(CONTACT_NAMES)}; "
            f"missing={missing}, extra={extra}"
        )
    for name, item in contacts.items():
        number(item.get("x_mm"), f"contacts.{name}.x_mm")
        number(item.get("y_mm"), f"contacts.{name}.y_mm")
        number(
            item.get("pad_diameter_mm"),
            f"contacts.{name}.pad_diameter_mm",
            positive=True,
        )

    positive_fields = (
        "plate_thickness_mm",
        "board_gap_mm",
        "edge_margin_mm",
        "pogo_bore_diameter_mm",
        "locator_fit_clearance_mm",
        "locator_protrusion_mm",
        "fastener_bore_diameter_mm",
        "minimum_wall_mm",
    )
    values = {
        field: number(fixture.get(field), f"fixture.{field}", positive=True)
        for field in positive_fields
    }

    for name, item in locators.items():
        hole = number(item["hole_diameter_mm"], f"{name}.hole", positive=True)
        support = number(
            item["support_diameter_mm"], f"{name}.support", positive=True
        )
        boss = hole - values["locator_fit_clearance_mm"]
        if boss <= values["fastener_bore_diameter_mm"] + 2 * values["minimum_wall_mm"]:
            raise MeasurementError(
                f"{name} locator boss has insufficient wall around its fastener bore"
            )
        if support <= hole + 2 * values["minimum_wall_mm"]:
            raise MeasurementError(f"{name} support shoulder is too narrow")

    bore = values["pogo_bore_diameter_mm"]
    minimum_spacing = bore + values["minimum_wall_mm"]
    contact_list = list(contacts.values())
    for index, left in enumerate(contact_list):
        for right in contact_list[index + 1 :]:
            distance = math.hypot(
                number(left["x_mm"], "contact.x")
                - number(right["x_mm"], "contact.x"),
                number(left["y_mm"], "contact.y")
                - number(right["y_mm"], "contact.y"),
            )
            if distance < minimum_spacing:
                raise MeasurementError(
                    f"contacts {left['name']} and {right['name']} leave less than "
                    f"{values['minimum_wall_mm']:.2f} mm of printed wall"
                )

    keepouts = data.get("keepouts")
    if not isinstance(keepouts, list):
        raise MeasurementError("keepouts must be a list")
    for index, keepout in enumerate(keepouts):
        if not isinstance(keepout, dict):
            raise MeasurementError(f"keepouts[{index}] must be an object")
        kind = keepout.get("kind")
        number(keepout.get("x_mm"), f"keepouts[{index}].x_mm")
        number(keepout.get("y_mm"), f"keepouts[{index}].y_mm")
        if kind == "circle":
            number(
                keepout.get("diameter_mm"),
                f"keepouts[{index}].diameter_mm",
                positive=True,
            )
        elif kind == "rectangle":
            number(
                keepout.get("width_mm"),
                f"keepouts[{index}].width_mm",
                positive=True,
            )
            number(
                keepout.get("height_mm"),
                f"keepouts[{index}].height_mm",
                positive=True,
            )
        else:
            raise MeasurementError(
                f"keepouts[{index}].kind must be 'circle' or 'rectangle'"
            )


def bounds(data: dict[str, Any]) -> tuple[float, float, float, float]:
    fixture = data["fixture"]
    margin = float(fixture["edge_margin_mm"])
    extents: list[tuple[float, float, float]] = []
    for locator in data["locators"]:
        extents.append(
            (
                float(locator["x_mm"]),
                float(locator["y_mm"]),
                float(locator["support_diameter_mm"]) / 2,
            )
        )
    for contact in data["contacts"]:
        extents.append(
            (
                float(contact["x_mm"]),
                float(contact["y_mm"]),
                float(fixture["pogo_bore_diameter_mm"]) / 2,
            )
        )
    return (
        min(x - radius for x, _, radius in extents) - margin,
        max(x + radius for x, _, radius in extents) + margin,
        min(y - radius for _, y, radius in extents) - margin,
        max(y + radius for _, y, radius in extents) + margin,
    )


def build_carrier(data: dict[str, Any]) -> Part.Shape:
    fixture = data["fixture"]
    plate = float(fixture["plate_thickness_mm"])
    gap = float(fixture["board_gap_mm"])
    board = float(data["board"]["thickness_mm"])
    protrusion = float(fixture["locator_protrusion_mm"])
    clearance = float(fixture["locator_fit_clearance_mm"])
    fastener_bore = float(fixture["fastener_bore_diameter_mm"])
    min_x, max_x, min_y, max_y = bounds(data)

    shape = Part.makeBox(
        max_x - min_x,
        max_y - min_y,
        plate,
        App.Vector(min_x, min_y, 0),
    )

    for locator in data["locators"]:
        x = float(locator["x_mm"])
        y = float(locator["y_mm"])
        support_radius = float(locator["support_diameter_mm"]) / 2
        boss_radius = (float(locator["hole_diameter_mm"]) - clearance) / 2
        shoulder = Part.makeCylinder(
            support_radius, gap, App.Vector(x, y, plate)
        )
        boss = Part.makeCylinder(
            boss_radius,
            gap + board + protrusion,
            App.Vector(x, y, plate),
        )
        shape = shape.fuse(shoulder).fuse(boss)
        fastener = Part.makeCylinder(
            fastener_bore / 2,
            plate + gap + board + protrusion + 2,
            App.Vector(x, y, -1),
        )
        shape = shape.cut(fastener)

    pogo_bore = float(fixture["pogo_bore_diameter_mm"])
    for contact in data["contacts"]:
        hole = Part.makeCylinder(
            pogo_bore / 2,
            plate + 2,
            App.Vector(float(contact["x_mm"]), float(contact["y_mm"]), -1),
        )
        shape = shape.cut(hole)

    for keepout in data["keepouts"]:
        x = float(keepout["x_mm"])
        y = float(keepout["y_mm"])
        height = plate + gap + board + protrusion + 2
        if keepout["kind"] == "circle":
            cutter = Part.makeCylinder(
                float(keepout["diameter_mm"]) / 2,
                height,
                App.Vector(x, y, -1),
            )
        else:
            width = float(keepout["width_mm"])
            depth = float(keepout["height_mm"])
            cutter = Part.makeBox(
                width,
                depth,
                height,
                App.Vector(x - width / 2, y - depth / 2, -1),
            )
        shape = shape.cut(cutter)

    shape = shape.removeSplitter()
    if shape.isNull() or not shape.isValid():
        raise MeasurementError("generated carrier is not a valid solid")
    return shape


def build_coupon(data: dict[str, Any]) -> tuple[Part.Shape, list[float]]:
    nominal = float(data["fixture"]["pogo_bore_diameter_mm"])
    thickness = float(data["fixture"]["plate_thickness_mm"])
    diameters = [round(nominal + offset, 3) for offset in (-0.10, 0, 0.10, 0.20, 0.30)]
    pitch = 5.0
    width = pitch * (len(diameters) + 1)
    depth = 10.0
    shape = Part.makeBox(width, depth, thickness)
    for index, diameter in enumerate(diameters, start=1):
        if diameter <= 0:
            raise MeasurementError("coupon bore diameter is not positive")
        hole = Part.makeCylinder(
            diameter / 2,
            thickness + 2,
            App.Vector(index * pitch, depth / 2, -1),
        )
        shape = shape.cut(hole)
    return shape.removeSplitter(), diameters


def add_metadata(obj: App.DocumentObject, data: dict[str, Any], digest: str) -> None:
    obj.addProperty("App::PropertyString", "MeasurementSHA256", "Fixture")
    obj.MeasurementSHA256 = digest
    obj.addProperty("App::PropertyString", "CoordinateSystem", "Fixture")
    obj.CoordinateSystem = data["coordinate_system"]
    for contact in data["contacts"]:
        prop = f"Contact_{contact['name']}"
        obj.addProperty("App::PropertyVector", prop, "Measured contacts")
        setattr(
            obj,
            prop,
            App.Vector(float(contact["x_mm"]), float(contact["y_mm"]), 0),
        )


def file_identity(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def export(data: dict[str, Any], source: Path, output: Path) -> None:
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    carrier = build_carrier(data)
    coupon, coupon_diameters = build_coupon(data)

    output.mkdir(parents=True, exist_ok=True)
    document = App.newDocument("SlimBladePogoFixture")
    carrier_object = document.addObject("PartDesign::Feature", "Carrier")
    carrier_object.Label = "Measured pogo carrier"
    carrier_object.Shape = carrier
    add_metadata(carrier_object, data, digest)

    document.recompute()
    output_names = (
        "slimblade_pogo_fixture.FCStd",
        "carrier.step",
        "carrier.stl",
        "bore_coupon.stl",
    )
    document.saveAs(str(output / output_names[0]))
    Part.export([carrier_object], str(output / output_names[1]))
    Mesh.export([carrier_object], str(output / output_names[2]))

    coupon_document = App.newDocument("SlimBladePogoBoreCoupon")
    coupon_object = coupon_document.addObject("PartDesign::Feature", "BoreCoupon")
    coupon_object.Label = "Printer bore calibration coupon"
    coupon_object.Shape = coupon
    coupon_object.addProperty("App::PropertyString", "BoreDiametersMM", "Fixture")
    coupon_object.BoreDiametersMM = ", ".join(
        f"{value:.2f}" for value in coupon_diameters
    )
    coupon_document.recompute()
    Mesh.export([coupon_object], str(output / output_names[3]))

    manifest = {
        "measurement_sha256": digest,
        "fixture_name": data["fixture_name"],
        "artifacts": {
            name: file_identity(output / name) for name in output_names
        },
        "coupon_bore_diameters_mm": coupon_diameters,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    App.closeDocument(coupon_document.Name)
    App.closeDocument(document.Name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurements", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args, freecad_args = parser.parse_known_args()
    unexpected = [
        value
        for value in freecad_args
        if value != "--pass" and not value.endswith("generate_fixture.py")
    ]
    if unexpected:
        parser.error(f"unrecognized arguments: {' '.join(unexpected)}")
    return args


def main() -> int:
    args = parse_args()
    try:
        data = json.loads(args.measurements.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise MeasurementError("measurement root must be an object")
        validate(data)
        export(data, args.measurements, args.output)
    except (OSError, json.JSONDecodeError, MeasurementError) as error:
        print(f"fixture generation refused: {error}", file=sys.stderr)
        return 2
    print(f"generated fixture artifacts in {args.output}", flush=True)
    return 0


raise SystemExit(main())

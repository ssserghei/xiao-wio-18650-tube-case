"""Read-only checks of the finished v2 model. Pass = FINAL_CHECK= line appears."""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import hashlib
import json
import math
import os
from pathlib import Path

import FreeCAD as App
import Part

source = Path(os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd")))
original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
doc = App.openDocument(str(source))


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


def lift(obj, top=20.0):
    """Volume swept by obj moving straight up (+Y); cylinders start at the axis."""
    b = obj.Shape.BoundBox
    start = b.Center.y if obj.TypeId == "Part::Cylinder" else b.YMin
    return Part.makeBox(b.XLength, top - start, b.ZLength, App.Vector(b.XMin, start, b.ZMin))


def overlap(a, b):
    return a.common(b).Volume


sheet = labeled("Parameters")
chassis = labeled("ChassisFinal")
sleeve = labeled("SleeveFinal")
clamp = labeled("BoardClamp")
shutter = labeled("Shutter")
battery = labeled("Battery")
electronics = labeled("Electronics")
dummies = [battery, electronics, labeled("NegativeContact"), labeled("PositiveContact"), labeled("SpringEnvelope")]
printed = [chassis, sleeve, clamp, shutter]


def value(alias):
    return float(sheet.get(alias).Value) if hasattr(sheet.get(alias), "Value") else float(sheet.get(alias))


def plug_box():
    w, h = value("USBPlugWidth"), value("USBPlugHeight")
    length = value("SleeveLength")
    z = electronics.Shape.BoundBox.ZMax
    plug = Part.makeBox(w, h, length + 15 - z, App.Vector(-w / 2, value("USBCenterY") - h / 2, z))
    sides = [e for e in plug.Edges if e.BoundBox.XLength < 1e-6 and e.BoundBox.YLength < 1e-6]
    return plug.makeFillet(1.0, sides)  # moulded plug bodies have rounded corners


def check():
    for obj in printed:
        assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1, (obj.Label, len(obj.Shape.Solids))
    for i, first in enumerate(printed):
        for second in printed[i + 1:]:
            assert overlap(first.Shape, second.Shape) < 1e-6, (first.Label, second.Label)
    for part in printed:
        for dummy in dummies:
            assert overlap(part.Shape, dummy.Shape) < 1e-6, (part.Label, dummy.Label)
    for dummy in dummies:
        assert overlap(chassis.Shape, lift(dummy)) < 1e-6, "blocked insertion: " + dummy.Label
    for piece in ("ClampBody", "ClampTongue"):  # the clamp is L-shaped: sweep each block
        assert overlap(chassis.Shape, lift(labeled(piece))) < 1e-6, "clamp blocked: " + piece
    plug = plug_box()
    for part in printed:
        assert overlap(part.Shape, plug) < 1e-6, "plug blocked by " + part.Label
    # Shutter turned 180 degrees closes the port completely.
    closed = shutter.Shape.copy()
    closed.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 180)
    assert overlap(closed, sleeve.Shape) < 1e-6, "closed shutter hits the sleeve"
    length = value("SleeveLength")
    plate = closed.common(Part.makeBox(40, 40, 1, App.Vector(-20, -20, length + 1)))
    bb = plug.BoundBox
    port = Part.makeBox(bb.XLength, bb.YLength, 1, App.Vector(bb.XMin, bb.YMin, length + 1))
    assert abs(plate.common(port).Volume - port.Volume) < 1e-6, "closed shutter leaves the port open"
    # Wire path: channel reaches riser, riser reaches the board pocket.
    channel = labeled("WireChannelTool").Shape
    riser = labeled("WireRiserTool").Shape
    assert overlap(channel, riser) > 1
    assert overlap(riser, labeled("BoardPocketTool").Shape) > 0
    assert overlap(labeled("AntennaHoleTool").Shape, channel) > 1, "antenna hole must open into the channel"
    # Bore stays intact where the O-ring seals.
    bore = Part.makeCylinder(16.2, 2.7, App.Vector(0, 0, value("ORingGrooveStartZ")))
    assert overlap(sleeve.Shape, bore) > 0
    assert abs(overlap(sleeve.Shape, Part.makeCylinder(16.0, 2.7, App.Vector(0, 0, value("ORingGrooveStartZ"))))) < 1e-6


check()


def check_rear():
    """Rear lug: open hole, free antenna and socket paths, flange still round."""
    y, f = value("AntennaCenterY"), value("FlangeThickness")
    socket = Part.makeCylinder(value("AntennaNutRecessDiameter") / 2 - 0.05, 40, App.Vector(0, y, -f - 40 + f - value("AntennaNutRecessDepth")))
    assert overlap(chassis.Shape, socket) < 1e-6, "socket path blocked"
    antenna = Part.makeCylinder(6.5, 40, App.Vector(0, y, -f - 40.01))
    assert overlap(chassis.Shape, antenna) < 1e-6, "antenna base hits the lug"
    tip_r = value("LugTipDiameter") / 2
    zc = -f - value("LugReach") + tip_r + value("LugHoleOffset")
    bore = Part.makeCylinder(value("LugHoleDiameter") / 2 - 0.01, 40, App.Vector(0, value("LugCenterY") - 20, zc), App.Vector(0, 1, 0))
    assert overlap(chassis.Shape, bore) < 1e-6, "lug hole blocked"
    wall = chassis.Shape.distToShape(Part.Vertex(App.Vector(0, value("LugCenterY"), -f - value("LugReach") + 0.01)))[0]
    assert wall < 0.2, "lug tip is not where expected"
    ring = Part.makeCylinder(17.4, 1.5, App.Vector(0, 0, -1.5)).cut(Part.makeCylinder(16.6, 1.5, App.Vector(0, 0, -1.5)))
    assert abs(overlap(chassis.Shape, ring) - ring.Volume) < 1e-3, "flange is not round where it meets the sleeve"


check_rear()


def check_bayonet():
    """Lugs enter straight, then follow the helix for the whole turn without touching the slots."""
    z_axis = App.Vector(0, 0, 1)
    origin = App.Vector(0, 0, 0)
    turn = value("BayonetTurn")
    lead = value("BayonetLead")
    for angle in (30, 150, 270):
        lug = labeled("BayonetLugShape%d" % angle).Shape
        assert lug.isValid() and overlap(sleeve.Shape, lug) < 1e-6, "lug hits its seat"
        for step in range(0, 11):
            moved = lug.copy()
            fraction = step / 10.0
            moved.rotate(origin, z_axis, -turn * fraction)
            moved.translate(App.Vector(0, 0, -lead * fraction))
            assert overlap(sleeve.Shape, moved) < 1e-6, "lug blocked on the helix"
        for step in range(1, 9):
            out = lug.copy()
            out.rotate(origin, z_axis, -turn)
            out.translate(App.Vector(0, 0, -lead - 0.5 * step))
            assert overlap(sleeve.Shape, out) < 1e-6, "lug blocked in the entry slot"


check_bayonet()


def check_contacts():
    """Nothing between each plate and the battery; tab wells run through to the channel."""
    w = value("ContactPlateWidth")
    y = value("BatteryCenterY")
    neg_h, pos_h = value("NegativePlateHeight"), value("PositivePlateHeight")
    neg_z, pos_z = value("NegativeContactZ"), value("PositiveContactZ")
    battery_rear = battery.Shape.BoundBox.ZMin
    battery_front = battery.Shape.BoundBox.ZMax
    assert abs(neg_z - (battery_rear - 2.0)) < 1e-6, "spring gap must be 2 mm"
    rear_gap = Part.makeBox(w, neg_h, battery_rear - neg_z, App.Vector(-w / 2, y - neg_h / 2, neg_z))
    assert overlap(chassis.Shape, rear_gap) < 1e-6, "wall left in front of the minus plate"
    front_gap = Part.makeBox(w, pos_h, pos_z - battery_front, App.Vector(-w / 2, y - pos_h / 2, battery_front))
    assert overlap(chassis.Shape, front_gap) < 1e-6, "wall left in front of the plus plate"
    for plate, z_back in ((labeled("NegativeContact"), neg_z - value("NegativePocketDepth") - 0.11), (labeled("PositiveContact"), pos_z + value("PositivePocketDepth") + 0.01)):
        b = plate.Shape.BoundBox
        behind = Part.makeBox(b.XLength, b.YLength, 0.1, App.Vector(b.XMin, b.YMin, z_back))
        assert abs(overlap(chassis.Shape, behind) - behind.Volume) < 1e-3, "no flat wall behind " + plate.Label
    channel = labeled("WireChannelTool").Shape
    for tool in ("NegativeTabPassTool", "PositiveTabPassTool"):
        well = labeled(tool).Shape
        assert overlap(well, channel) > 1, tool
        assert overlap(chassis.Shape, well) < 1e-6, tool + " is blocked"
    assert abs(value("WireChannelStartZ") - 4.9) < 1e-6, "antenna wall must not follow the contact"


check_contacts()


def check_cable():
    """Real board stack and coax against the printed parts; report the tightest bend."""
    stack = labeled("BoardStackModel").Shape
    closed = []
    for solid in stack.Solids:
        if solid.isValid():
            closed.append(solid)
        else:  # mesh-derived PCBs can be invalid; their bounding box is the stricter test
            b = solid.BoundBox
            closed.append(Part.makeBox(b.XLength, b.YLength, b.ZLength, App.Vector(b.XMin, b.YMin, b.ZMin)))
    assert len(closed) >= 30, len(closed)
    for part in printed:
        for piece in closed:
            assert overlap(part.Shape, piece) < 1e-5, ("board stack hits " + part.Label, piece.BoundBox)
    cable = labeled("AntennaCable").Shape
    for part in printed + [battery]:
        assert overlap(part.Shape, cable) < 1e-5, "coax hits " + part.Label
    gap = battery.Shape.distToShape(cable)[0]
    assert gap >= 0.5, gap  # the slot is open into the battery pocket
    return round(gap, 2)


cable_to_battery = check_cable()


cable_bend = value("AntennaCableMinBend")
assert cable_bend >= 30.0, cable_bend  # the coax must stay practically straight


def check_real_pins():
    """The kit model pins are 0.35 mm short, so test the measured length as well."""
    top = value("WioBottomY")
    tip = value("PinTipY")
    start = value("BoardPocketStart") + 3.0
    for x in (-value("PinRowOffsetX"), value("PinRowOffsetX")):
        pins = Part.makeBox(0.6, top - tip, 16.0, App.Vector(x - 0.3, tip, start))
        assert overlap(chassis.Shape, pins) < 1e-6, "pin slot too small"
        assert overlap(sleeve.Shape, pins) < 1e-6, "pins hit the sleeve"
        assert math.hypot(abs(x) + 0.3, tip) < value("ChassisDiameter") / 2, "pin tips leave the chassis diameter"


check_real_pins()


def min_wall(a_shape, b_shape):
    return round(a_shape.distToShape(b_shape)[0], 3)


tools = {
    "antenna_hole_to_oring": min_wall(labeled("AntennaHoleTool").Shape, labeled("ORingGrooveTool").Shape),
    "battery_to_channel": min_wall(labeled("BatteryPocketTool").Shape, labeled("WireChannelTool").Shape),
    "riser_to_plus_pocket": min_wall(labeled("WireRiserTool").Shape, labeled("PositivePocketTool").Shape),
}
nut_height = 2.0
antenna_wall = value("FlangeThickness") - value("AntennaNutRecessDepth") + value("WireChannelStartZ")
free_thread = value("AntennaThreadLength") - antenna_wall - nut_height
assert free_thread >= 3.5, free_thread
assert value("AntennaNutRecessDepth") < value("FlangeThickness"), "recess must not cut through the flange"
report = {
    "antenna_wall": round(antenna_wall, 2),
    "antenna_free_thread": round(free_thread, 2),
    "cable_to_battery": cable_to_battery,
    "cable_min_bend_radius": cable_bend,
    "lug_tip_z": round(chassis.Shape.optimalBoundingBox(True, True).ZMin, 2),
    "sleeve_length": value("SleeveLength"),
    "overall_length": round(shutter.Shape.optimalBoundingBox(True, True).ZMax - chassis.Shape.optimalBoundingBox(True, True).ZMin, 2),
    "overall_diameter": round(sleeve.Shape.optimalBoundingBox(True, True).XLength, 2),
    "battery_top_gap": round(15.7 - battery.Shape.BoundBox.YMax, 3),
    "volumes_cm3": {o.Label: round(o.Shape.Volume / 1000, 2) for o in printed},
    "walls_mm": tools,
}
sheet.set("B47", "0.5 mm")
sheet.set("B7", "20 mm")
doc.recompute()
check()
sheet.set("B47", "0.25 mm")
sheet.set("B7", "21 mm")
doc.recompute()
check()
report["parameter_change_restore"] = "passed"
App.closeDocument(doc.Name)
assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
print("FINAL_CHECK=" + json.dumps(report))

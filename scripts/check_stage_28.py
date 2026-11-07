"""Read-only checks of the saved v2 model. Pass = STAGE_28_CHECK= line appears."""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import hashlib
import json
from pathlib import Path

import FreeCAD as App
import Part

source = Path(_os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
doc = App.openDocument(str(source))


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


def lift(obj, top=20.0):
    """Volume swept by obj moving straight up (+Y) out of the chassis.

    A cylinder's lower bbox corners lie outside the cylinder, so its sweep
    starts at the axis: the half below the axis is already covered by its
    own zero-intersection check.
    """
    b = obj.Shape.BoundBox
    start = b.Center.y if obj.TypeId == "Part::Cylinder" else b.YMin
    return Part.makeBox(b.XLength, top - start, b.ZLength, App.Vector(b.XMin, start, b.ZMin))


sheet = labeled("Parameters")
tip = labeled("ChassisWireChannel")
battery = labeled("Battery")
negative = labeled("NegativeContact")
positive = labeled("PositiveContact")
spring = labeled("SpringEnvelope")
electronics = labeled("Electronics")
sleeve = labeled("Sleeve")
chain = ["ChassisUSBSlot", "ChassisSpringEntry", "ChassisButtonSlot", "ChassisNegativeTab", "ChassisPositiveTab", "ChassisWireChannel"]


def check():
    for label in chain:
        shape = labeled(label).Shape
        assert shape.isValid() and len(shape.Solids) == 1, label
    for obj in (battery, negative, positive, spring, electronics, sleeve):
        assert tip.Shape.common(obj.Shape).Volume < 1e-6, obj.Label
    for obj in (battery, negative, positive, spring, electronics):
        assert tip.Shape.common(lift(obj)).Volume < 1e-6, "blocked insertion: " + obj.Label
    channel = labeled("WireChannelTool").Shape
    assert channel.common(labeled("BoardPocketTool").Shape).Volume > 1, "channel must reach the board pocket"
    for tool in ("NegativeTabPassTool", "PositiveTabPassTool"):
        assert labeled(tool).Shape.common(channel).Volume > 1, tool + " must reach the channel"
    assert labeled("NegativeTabPassTool").Shape.common(labeled("NegativePocketTool").Shape).Volume > 0
    assert labeled("PositiveTabPassTool").Shape.common(labeled("PositivePocketTool").Shape).Volume > 0


check()
b = battery.Shape.BoundBox
c = labeled("ChassisCore").Shape.BoundBox
w = labeled("WireChannelTool").Shape.BoundBox
button = Part.makeCylinder(2.75, 0.73, App.Vector(0, b.Center.y, 79.3))
report = {
    "battery_y": [round(b.YMin, 3), round(b.YMax, 3)],
    "battery_top_gap": round(c.YMax - b.YMax, 3),
    "under_battery": round(b.YMin - c.YMin, 3),
    "channel_x": [w.XMin, w.XMax],
    "channel_top_y": round(w.YMax, 3),
    "channel_z": [round(w.ZMin, 3), round(w.ZMax, 3)],
    "button_clear": tip.Shape.common(button).Volume < 1e-6,
    "chassis_volume_cm3": round(tip.Shape.Volume / 1000, 2),
}
assert report["button_clear"]
assert abs(report["battery_top_gap"] - 0.25) < 1e-6
sheet.set("B47", "0.5 mm")
sheet.set("B49", "8 mm")
doc.recompute()
check()
sheet.set("B47", "0.25 mm")
sheet.set("B49", "10 mm")
doc.recompute()
check()
report["parameter_change_restore"] = "passed"
App.closeDocument(doc.Name)
assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
print("STAGE_28_CHECK=" + json.dumps(report))

"""Lower the board stack so the coax stays nearly straight; the Wio rests on a floor with pin slots.

Measured on the real stack: pins 4.35 mm below the Wio, coax centre 4.5 mm above its underside.
Run with freecadcmd after apply_board_model.py, then set_view_in_gui.py.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import math
import os

import FreeCAD as App
import Part

TARGET = os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
P = "<<Parameters>>."

doc = App.openDocument(TARGET)
assert not doc.getObjectsByLabel("ChassisPinSlots"), "the lowered stack is already applied"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


sheet = labeled("Parameters")
rows = [
    (91, "Длина штырей под платой Wio", "4.35 mm", "PinLength"),
    (92, "Центр кабеля над низом Wio", "4.5 mm", "CableHeight"),
    (93, "Кончики штырей, Y", "=-13.5 mm", "PinTipY"),
    (94, "Нижняя сторона Wio, Y", "=PinTipY + PinLength", "WioBottomY"),
    (95, "Верх блока плат, Y", "=WioBottomY + BoardThickness - PinLength", "StackTopY"),
    (96, "Ширина прорези штырей", "1.6 mm", "PinSlotWidth"),
    (97, "Ряды штырей от оси, X", "7.62 mm", "PinRowOffsetX"),
]
for row, text, value, alias in rows:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
sheet.set("B9", "8 mm")     # the coax no longer has to drop 3.6 mm, only about 0.7 mm
sheet.set("B85", "=-2 mm")
sheet.set("B68", "=StackTopY - 1.65 mm")
doc.recompute()

to_outside = P + "ChassisDiameter / 2 + 1 mm"
for label, expressions in {
    "Electronics": {
        "Placement.Base.y": P + "WioBottomY",
        "Width": P + "BoardThickness - " + P + "PinLength",
    },
    "BoardPocketTool": {
        "Placement.Base.y": P + "WioBottomY - 0.05 mm",
        "Width": to_outside + " - " + P + "WioBottomY + 0.05 mm",
    },
    "USBWindowTool": {"Placement.Base.y": P + "StackTopY - 3.8 mm"},
    "USBEntryTool": {
        "Placement.Base.y": P + "StackTopY",
        "Width": to_outside + " - " + P + "StackTopY",
    },
    "WireRiserTool": {"Width": P + "StackTopY - " + P + "WireChannelTopY + 1 mm"},
    "ClampBody": {
        "Placement.Base.y": P + "StackTopY + 0.1 mm",
        "Width": to_outside + " - " + P + "StackTopY - 0.1 mm",
    },
    "BoardStackModel": {"Placement.Base.y": P + "WioBottomY - 5.6 mm"},  # Wio underside is z=5.6 in the model
}.items():
    for field, expression in expressions.items():
        labeled(label).setExpression(field, expression)


def pin_slot(name, x):
    tool = doc.addObject("Part::Box", name)
    tool.Label = name
    for field, expression in {
        "Length": P + "PinSlotWidth",
        "Width": P + "WioBottomY + " + to_outside,
        "Height": "17.3 mm",
        "Placement.Base.x": x,
        "Placement.Base.y": "-(" + to_outside + ")",
        "Placement.Base.z": P + "BoardPocketStart + 2.3 mm",
    }.items():
        tool.setExpression(field, expression)
    tool.Visibility = False
    return tool


half = P + "PinSlotWidth / 2"
slots = doc.addObject("Part::MultiFuse", "PinSlotTools")
slots.Label = "PinSlotTools"
slots.Shapes = [
    pin_slot("PinSlotRight", P + "PinRowOffsetX - " + half),
    pin_slot("PinSlotLeft", "-" + P + "PinRowOffsetX - " + half),
]
slots.Visibility = False
cut = doc.addObject("Part::Cut", "ChassisPinSlots")
cut.Label = "ChassisPinSlots"
cut.Base = labeled("ChassisKeyed")
cut.Tool = slots
cut.Visibility = False
labeled("ChassisFinal").Base = cut
doc.recompute()

# Coax centre line, redrawn for the lowered U.FL (static, re-run if the route moves).
V = App.Vector
pocket = float(sheet.get("BoardPocketStart").Value)
x = -float(sheet.get("UFLOffsetX").Value)
start_y = float(sheet.get("WioBottomY").Value) + float(sheet.get("CableHeight").Value)
radius = float(sheet.get("AntennaCableDiameter").Value) / 2
points = [
    V(x, start_y, pocket - 1.85),
    V(x, -5.3, 81.0),
    V(x, -7.6, 62.0),
    V(x * 0.6, -8.5, 35.0),
    V(0, -10.0, 13.0),
]
spline = Part.BSplineCurve()
spline.interpolate(Points=points, InitialTangent=V(0, 0, -1), FinalTangent=V(0, 0, -1))
steps = 4000
span = spline.LastParameter - spline.FirstParameter
worst = max(spline.curvature(spline.FirstParameter + span * i / steps) for i in range(steps + 1))
sheet.set("B90", "%.2f mm" % (1 / worst))
path = Part.Wire([spline.toShape()])
profile = Part.Wire([Part.makeCircle(radius, points[0], V(0, 0, -1))])
labeled("AntennaCable").Shape = path.makePipeShell([profile], True, True)
doc.recompute()

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
tip = labeled("ChassisFinal")
assert tip.Shape.isValid() and len(tip.Shape.Solids) == 1
assert math.isfinite(worst)
doc.save()
App.closeDocument(doc.Name)
print("APPLY_LOWER_CHECK=saved")

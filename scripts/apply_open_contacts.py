"""Replace the contact slots with open faces: plates are glued on flat walls, tabs go down wells.

The printer cannot make the thin retaining slots, so everything between each plate and the
battery is cut away. The negative plate moves 2 mm towards the battery, which leaves the
spring 2 mm of working height. Run after apply_flush_body.py, then set_view_in_gui.py.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import os

import FreeCAD as App

TARGET = os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
P = "<<Parameters>>."

doc = App.openDocument(TARGET)
assert not doc.getObjectsByLabel("ChassisNegativeFace"), "the open contacts are already applied"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


sheet = labeled("Parameters")
sheet.set("B40", "2 mm")    # NegativeContactZ follows: the plate moves 2 mm towards the battery
sheet.set("B52", "4.9 mm")  # the channel must not follow it: the antenna thread needs this wall
sheet.set("B46", "=PositivePlateThickness + 0.05 mm")  # flat wall right behind the plus plate
doc.recompute()

to_top = P + "ChassisDiameter / 2 + 1 mm - " + P + "BatteryCenterY"
clear = P + "ContactPocketClearance"
pocket_end = P + "RearSpace + " + P + "BatteryLength + " + P + "BatteryEndClearance"


def face_tool(name, plate_height, start_z, height):
    tool = doc.addObject("Part::Box", name)
    tool.Label = name
    for field, expression in {
        "Length": P + "ContactPlateWidth + 2 * " + clear,
        "Width": to_top + " + " + P + plate_height + " / 2 + " + clear,
        "Height": height,
        "Placement.Base.x": "-(" + P + "ContactPlateWidth / 2 + " + clear + ")",
        "Placement.Base.y": P + "BatteryCenterY - (" + P + plate_height + " / 2 + " + clear + ")",
        "Placement.Base.z": start_z,
    }.items():
        tool.setExpression(field, expression)
    tool.Visibility = False
    return tool


negative = face_tool(
    "NegativeFaceTool", "NegativePlateHeight",
    P + "NegativeContactZ - 0.1 mm",
    P + "RearSpace - " + P + "BatteryEndClearance - " + P + "NegativeContactZ + 0.2 mm",
)
positive = face_tool(
    "PositiveFaceTool", "PositivePlateHeight",
    pocket_end + " - 0.1 mm",
    P + "PositiveContactZ - (" + pocket_end + ") + 0.2 mm",
)


def cut(name, base, tool):
    result = doc.addObject("Part::Cut", name)
    result.Label = name
    result.Base = base
    result.Tool = tool
    base.Visibility = False
    result.Visibility = False
    return result


tip = cut("ChassisNegativeFace", labeled("ChassisPinSlots"), negative)
tip = cut("ChassisPositiveFace", tip, positive)
labeled("ChassisFinal").Base = tip
doc.recompute()

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
final = labeled("ChassisFinal")
assert final.Shape.isValid() and len(final.Shape.Solids) == 1
doc.save()
App.closeDocument(doc.Name)
print("APPLY_CONTACTS_CHECK=saved")

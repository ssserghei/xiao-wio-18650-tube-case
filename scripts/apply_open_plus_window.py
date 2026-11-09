"""Open window in front of the plus plate again; the pocket wall around it is the guard.

The guard ring of apply_guard_marks.py left a 0.4 mm slot between the ring and the back
wall, too narrow to print. The plate is glued anyway, so the whole plate-sized area in front
of it is open again, as in apply_open_contacts.py. A battery end (Ø18.6) is wider than the
plate (13 mm): a reversed cell rests its flat end on the wall beside and below the window,
0.5 mm (PlusContactRecess) short of the plate's bump; a button-top plus end reaches it.
Run with freecadcmd, then set_view_in_gui.py.
"""
import os as _os
import sys as _sys
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
_sys.path.insert(0, _os.path.join(_REPO, "scripts"))

import FreeCAD as App

import rebuild_static

TARGET = _os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
P = "<<Parameters>>."

doc = App.openDocument(TARGET)
assert doc.getObjectsByLabel("PlusGuardTool"), "expects the guard ring of apply_guard_marks.py"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


clear = P + "ContactPocketClearance"
pocket_end = P + "RearSpace + " + P + "BatteryLength + " + P + "BatteryEndClearance"
window = doc.addObject("Part::Box", "PositiveFaceTool")
window.Label = "PositiveFaceTool"
for field, expression in {
    "Length": P + "ContactPlateWidth + 2 * " + clear,
    "Width": P + "ChassisDiameter / 2 + 1 mm - " + P + "BatteryCenterY + " + P + "PositivePlateHeight / 2 + " + clear,
    "Height": P + "PositiveContactZ - (" + pocket_end + ") + 0.2 mm",
    "Placement.Base.x": "-(" + P + "ContactPlateWidth / 2 + " + clear + ")",
    "Placement.Base.y": P + "BatteryCenterY - (" + P + "PositivePlateHeight / 2 + " + clear + ")",
    "Placement.Base.z": pocket_end + " - 0.1 mm",
}.items():
    window.setExpression(field, expression)
window.Visibility = False
labeled("ChassisPositiveFace").Tool = window
doc.recompute()
for label in ("PlusGuardTool", "PlusGuardHoleTool", "PlusBumpChannelTool"):
    doc.removeObject(labeled(label).Name)
sheet = labeled("Parameters")
for row in (128, 133):  # PlusGuardHoleDiameter, PlusBumpChannelWidth
    sheet.clear("A%d" % row)
    sheet.clear("B%d" % row)
sheet.set("A127", "Утопление кнопки плюса за упором (стенкой отсека)")
doc.recompute()

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
for label in ("ChassisFinal", "SleeveFinal", "Shutter", "BoardClamp"):
    part = labeled(label).Shape
    assert part.isValid() and len(part.Solids) == 1, (label, part.isValid(), len(part.Solids))
rebuild_static.save(doc)
App.closeDocument(doc.Name)
print("APPLY_OPEN_PLUS_CHECK=saved")

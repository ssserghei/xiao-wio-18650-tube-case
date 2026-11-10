"""Front wall moves 1.5 mm onto the boards; only the USB-C connector passes through it.

The board stack (BoardStackModel) ends 1.5 mm before the USB-C connector tip. The front
wall used to stand in front of the connector, leaving 1.5 mm of empty pocket beside it.
- USBOverhang = 1.5 mm. The board pocket now ends 0.15 mm past the PCBs, the 1.5 mm wall
  stands right there, and the connector sits in the USB window inside the wall.
- FrontSpace 1.8 -> 0.3 mm: case 1.5 mm shorter, the plug reaches 1.5 mm deeper.
- USB window and entry slot start at the pocket end, the clamp body stops before the wall.
- Electronics envelope ends at the PCBs; new dummy USBConnector carries the plug path.
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
labeled = lambda label: doc.getObjectsByLabel(label)[0]
assert not doc.getObjectsByLabel("USBConnector"), "already applied"
sheet = labeled("Parameters")

sheet.set("A139", "Выступ USB-C за платы")
sheet.set("B139", "1.5 mm")
sheet.setAlias("B139", "USBOverhang")
sheet.set("B24", "=BoardLength - USBOverhang + 2 * BoardClearance")  # BoardPocketLength
sheet.set("B10", "0.3 mm")  # FrontSpace: the wall now stands beside the connector, not in front of it
doc.recompute()

pocket_end = P + "BoardPocketStart + " + P + "BoardPocketLength"
for name in ("USBWindowTool", "USBEntryTool"):
    labeled(name).setExpression("Placement.Base.z", pocket_end + " - 0.1 mm")
labeled("ClampBody").setExpression("Height", P + "BoardPocketLength - " + P + "BoardClearance - " + P + "BoardClampGap - 0.1 mm")
labeled("Electronics").setExpression("Height", P + "BoardLength - " + P + "USBOverhang")

connector = doc.addObject("Part::Box", "USBConnector")  # dummy, never printed
connector.Label = "USBConnector"
for field, expression in {
    "Length": "9 mm",
    "Width": "3.3 mm",
    "Height": P + "USBOverhang",
    "Placement.Base.x": "-4.5 mm",
    "Placement.Base.y": P + "USBCenterY - 1.65 mm",
    "Placement.Base.z": P + "RearSpace + " + P + "BatteryLength + " + P + "BoardGap + " + P + "BoardLength - " + P + "USBOverhang",
}.items():
    connector.setExpression(field, expression)
connector.Visibility = False
doc.recompute()

rebuild_static.rebuild_all(doc)  # sleeve length changed: lattice, cable, marks, fillets

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
for label in ("ChassisFinal", "SleeveFinal", "Shutter", "BoardClamp"):
    part = labeled(label).Shape
    assert part.isValid() and len(part.Solids) == 1, (label, part.isValid(), len(part.Solids))
rebuild_static.save(doc)
App.closeDocument(doc.Name)
print("APPLY_TRIM_FRONT_CHECK=saved")

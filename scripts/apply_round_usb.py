"""Round the corners of the USB-C windows: all four in the disc, the two lower ones in the chassis.

The upper chassis corners are formed by the clamp tongue and stay square.
Run after apply_open_contacts.py, then set_view_in_gui.py.
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
RADIUS = 2.0

doc = App.openDocument(TARGET)
assert not doc.getObjectsByLabel("DiscWindowRounded"), "the rounded windows are already applied"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


def rounded(name, tool, wanted):
    edges = [i for i, e in enumerate(tool.Shape.Edges, 1)
             if e.BoundBox.XLength < 1e-6 and e.BoundBox.YLength < 1e-6 and wanted(e)]
    result = doc.addObject("Part::Fillet", name)
    result.Label = name
    result.Base = tool
    result.Edges = [(i, RADIUS, RADIUS) for i in edges]
    tool.Visibility = False
    result.Visibility = False
    return result


disc_tool = labeled("DiscWindowTool")
labeled("DiscWindow").Tool = rounded("DiscWindowRounded", disc_tool, lambda e: True)

chassis_tool = labeled("USBPlugWindowTool")
low_y = chassis_tool.Shape.BoundBox.YMin
labeled("ChassisFinal").Tool = rounded("USBPlugWindowRounded", chassis_tool, lambda e: abs(e.BoundBox.YMin - low_y) < 1e-6)
doc.recompute()

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
for label in ("ChassisFinal", "Shutter"):
    shape = labeled(label).Shape
    assert shape.isValid() and len(shape.Solids) == 1, label
doc.save()
App.closeDocument(doc.Name)
print("APPLY_ROUND_USB_CHECK=saved")

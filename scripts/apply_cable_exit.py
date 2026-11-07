"""Open a full-width exit for the antenna coax behind the boards and add a cable dummy.

The U.FL sits on the top side of the Wio board, at the end away from USB-C, offset
3.44 mm from the board axis (from the Seeed STEP). The coax leaves towards the battery.
Run with freecadcmd after apply_rear_lug.py, then set_view_in_gui.py.
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
assert not doc.getObjectsByLabel("ChassisCableExit"), "the cable exit is already applied"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


sheet = labeled("Parameters")
rows = [
    (83, "Диаметр антенного кабеля", "2 mm", "AntennaCableDiameter"),
    (84, "Смещение U.FL от оси платы, X", "3.44 mm", "UFLOffsetX"),
    (85, "Верх выхода кабеля из отсека плат, Y", "=-1 mm", "CableExitTopY"),
    (86, "Начало выхода кабеля, Z", "=PositiveContactZ + 0.7 mm", "CableExitStartZ"),
]
for row, text, value, alias in rows:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
doc.recompute()

# Long enough for the coax to ease down from the U.FL to the channel, not to kink.
start_z = P + "CableExitStartZ"
tool = doc.addObject("Part::Box", "CableExitTool")
tool.Label = "CableExitTool"
for field, expression in {
    "Length": P + "WireChannelWidth",
    "Width": P + "CableExitTopY - " + P + "WireChannelTopY + 1 mm",
    "Height": P + "BoardPocketStart - (" + start_z + ") + 0.1 mm",
    "Placement.Base.x": "-" + P + "WireChannelWidth / 2",
    "Placement.Base.y": P + "WireChannelTopY - 1 mm",
    "Placement.Base.z": start_z,
}.items():
    tool.setExpression(field, expression)
tool.Visibility = False

riser = labeled("ChassisRiser")
exit_cut = doc.addObject("Part::Cut", "ChassisCableExit")
exit_cut.Label = "ChassisCableExit"
exit_cut.Base = riser
exit_cut.Tool = tool
exit_cut.Visibility = False
labeled("ChassisAntennaHole").Base = exit_cut

cable = doc.addObject("Part::Cylinder", "AntennaCableEnvelope")  # dummy, never printed
cable.Label = "AntennaCableEnvelope"
for field, expression in {
    "Radius": P + "AntennaCableDiameter / 2",
    "Height": P + "BoardPocketStart + " + P + "BoardClearance - " + P + "WireChannelStartZ - 3 mm",
    "Placement.Base.x": "-" + P + "UFLOffsetX",
    "Placement.Base.y": P + "WireChannelTopY - " + P + "AntennaCableDiameter / 2 - 0.05 mm",
    "Placement.Base.z": P + "WireChannelStartZ + 3 mm",
}.items():
    cable.setExpression(field, expression)

doc.recompute()
bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
tip = labeled("ChassisFinal")
assert tip.Shape.isValid() and len(tip.Shape.Solids) == 1
doc.save()
App.closeDocument(doc.Name)
print("APPLY_CABLE_CHECK=saved")

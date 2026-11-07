"""Add the real board stack and route the antenna coax along a checked path.

Board stack: "XIAO nRF52840 & Wio-SX1262 Kit 3D model" by zuberio (Printables), used
as a reference dummy only; it is never printed or exported.
Run with freecadcmd after apply_cable_exit.py, then set_view_in_gui.py.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import os

import FreeCAD as App
import Mesh
import Part

TARGET = os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
KIT = _os.path.join(_REPO, "reference", "xiao-nrf52840-and-wio-sx1262.stl")
P = "<<Parameters>>."

# Model axes: x across, y from the U.FL end to USB-C, z from the pins up to the XIAO.
KIT_CENTRE_X = 185.73
KIT_REAR_Y = 72.72   # rear edge of the Wio board
KIT_TOP_Z = 22.1     # top of USB-C

doc = App.openDocument(TARGET)
assert not doc.getObjectsByLabel("BoardStackModel"), "the board model is already applied"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


sheet = labeled("Parameters")
sheet.set("B9", "10 mm")      # room for the coax to bend down behind the boards
sheet.set("B84", "3.6 mm")    # U.FL offset measured on the kit model
sheet.set("B85", "=-0.5 mm")  # the coax leaves the U.FL at about Y=-2
for row, text, value, alias in [
    (87, "Верх желобка кабеля, Y", "=-4.1 mm", "CableSlotTopY"),
    (88, "Ширина желобка кабеля", "3.6 mm", "CableSlotWidth"),
    (89, "Длина желобка кабеля", "15 mm", "CableSlotLength"),
]:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
doc.recompute()

# A shallow groove in the channel ceiling, on the U.FL side only.
slot = doc.addObject("Part::Box", "CableSlotTool")
slot.Label = "CableSlotTool"
for field, expression in {
    "Length": P + "CableSlotWidth",
    "Width": P + "CableSlotTopY - " + P + "WireChannelTopY + 1 mm",
    "Height": P + "CableSlotLength + 0.1 mm",
    "Placement.Base.x": "-" + P + "UFLOffsetX - " + P + "CableSlotWidth / 2",
    "Placement.Base.y": P + "WireChannelTopY - 1 mm",
    "Placement.Base.z": P + "CableExitStartZ - " + P + "CableSlotLength",
}.items():
    slot.setExpression(field, expression)
slot.Visibility = False
slot_cut = doc.addObject("Part::Cut", "ChassisCableSlot")
slot_cut.Label = "ChassisCableSlot"
slot_cut.Base = labeled("ChassisCableExit")
slot_cut.Tool = slot
slot_cut.Visibility = False
labeled("ChassisAntennaHole").Base = slot_cut
doc.removeObject(labeled("AntennaCableEnvelope").Name)
doc.recompute()

# Board stack: mesh components become solids so the checks can intersect them.
solids, open_parts = [], 0
for component in Mesh.Mesh(KIT).getSeparateComponents():
    shape = Part.Shape()
    shape.makeShapeFromMesh(component.Topology, 0.01)
    try:
        solid = Part.Solid(Part.Shell(shape.Faces))
        solids.append(solid if solid.Volume > 0 else solid.reversed())
    except Exception:
        open_parts += 1
        solids.append(shape)
stack = doc.addObject("Part::Feature", "BoardStackModel")
stack.Label = "BoardStackModel"
stack.Shape = Part.makeCompound(solids)
matrix = App.Matrix(-1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1)  # x -> -X, y -> Z, z -> Y
stack.Placement = App.Placement(matrix)
base_y = P + "BoardThickness / 2 - %s mm" % KIT_TOP_Z
base_z = P + "BoardPocketStart + 0.05 mm - %s mm" % KIT_REAR_Y
stack.setExpression("Placement.Base.x", "%s mm" % KIT_CENTRE_X)
stack.setExpression("Placement.Base.y", base_y)
stack.setExpression("Placement.Base.z", base_z)
doc.recompute()

# Coax centre line from the U.FL crimp to the antenna connector (static, re-run if moved).
pocket = float(sheet.get("BoardPocketStart").Value)
x = -float(sheet.get("UFLOffsetX").Value)
exit_z = float(sheet.get("CableExitStartZ").Value)
slot_z = exit_z - float(sheet.get("CableSlotLength").Value)
radius = float(sheet.get("AntennaCableDiameter").Value) / 2
V = App.Vector
# Few points on purpose: extra ones make the spline wiggle. The bend starts where the
# rigid U.FL crimp ends, 1.9 mm behind the board edge.
points = [
    V(x, -1.9, pocket - 1.85),
    V(x, -5.6, exit_z + 0.27),
    V(x, -7.6, slot_z - 7.7),
    V(x * 0.6, -8.5, 35.0),
    V(0, -10.0, 13.0),
]
spline = Part.BSplineCurve()
spline.interpolate(Points=points, InitialTangent=V(0, 0, -1), FinalTangent=V(0, 0, -1))
steps = 4000
span = spline.LastParameter - spline.FirstParameter
worst = max(spline.curvature(spline.FirstParameter + span * i / steps) for i in range(steps + 1))
sheet.set("A90", "Минимальный радиус изгиба кабеля (расчёт)")
sheet.set("B90", "%.2f mm" % (1 / worst))
sheet.setAlias("B90", "AntennaCableMinBend")
path = Part.Wire([spline.toShape()])
profile = Part.Wire([Part.makeCircle(radius, points[0], V(0, 0, -1))])
cable = doc.addObject("Part::Feature", "AntennaCable")  # dummy, never printed
cable.Label = "AntennaCable"
cable.Shape = path.makePipeShell([profile], True, True)
doc.recompute()

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
tip = labeled("ChassisFinal")
assert tip.Shape.isValid() and len(tip.Shape.Solids) == 1
doc.save()
App.closeDocument(doc.Name)
print("APPLY_BOARD_CHECK=saved solids=%d open=%d" % (len(solids), open_parts))

"""Open the cable slot into the battery pocket: the coax stays straight and the case gets shorter.

The floor under the battery end is not structural, so it is cut away along the coax.
Run with freecadcmd after apply_lower_boards.py, then set_view_in_gui.py.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import os

import FreeCAD as App
import Part

TARGET = os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))

doc = App.openDocument(TARGET)


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


sheet = labeled("Parameters")
assert float(sheet.get("BoardGap").Value) != 6.0, "the open slot is already applied"
sheet.set("B87", "=-2 mm")  # above the battery pocket floor, so the slot opens into it
sheet.set("B9", "6 mm")     # no bend left to make room for
doc.recompute()

V = App.Vector
pocket = float(sheet.get("BoardPocketStart").Value)
x = -float(sheet.get("UFLOffsetX").Value)
start_y = float(sheet.get("WioBottomY").Value) + float(sheet.get("CableHeight").Value)
radius = float(sheet.get("AntennaCableDiameter").Value) / 2
points = [
    V(x, start_y, pocket - 1.85),
    V(x, -5.6, 72.0),
    V(x, -7.6, 60.0),
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
doc.save()
App.closeDocument(doc.Name)
print("APPLY_OPEN_SLOT_CHECK=saved")

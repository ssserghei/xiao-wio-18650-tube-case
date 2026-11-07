"""Round the outer rim of the sleeve front end. Run after apply_round_usb.py, then set_view_in_gui.py."""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import math
import os

import FreeCAD as App

TARGET = os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
RADIUS = 1.5

doc = App.openDocument(TARGET)
assert not doc.getObjectsByLabel("SleeveNotched"), "the front rim is already rounded"

base = doc.getObjectsByLabel("SleeveFinal")[0]
base.Label = "SleeveNotched"
shape = base.Shape
outer = float(doc.getObjectsByLabel("Parameters")[0].get("SleeveOuterDiameter").Value) / 2
top = max(v.Z for v in shape.Vertexes)
edges = [
    i for i, e in enumerate(shape.Edges, 1)
    if abs(e.BoundBox.ZMin - top) < 1e-6 and abs(e.BoundBox.ZMax - top) < 1e-6
    and abs(math.hypot(e.valueAt(e.FirstParameter).x, e.valueAt(e.FirstParameter).y) - outer) < 1e-6
]
assert edges, "outer front edge not found"
rim = doc.addObject("Part::Fillet", "SleeveRim")
rim.Label = "SleeveFinal"
rim.Base = base
rim.Edges = [(i, RADIUS, RADIUS) for i in edges]
base.Visibility = False
rim.Visibility = True
doc.recompute()
assert rim.Shape.isValid() and len(rim.Shape.Solids) == 1
assert rim.Shape.Volume < base.Shape.Volume, "fillet removed nothing"
doc.save()
App.closeDocument(doc.Name)
print("APPLY_RIM_CHECK=saved")

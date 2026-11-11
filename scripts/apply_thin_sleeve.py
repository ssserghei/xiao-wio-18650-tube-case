"""Thinner sleeve: 0.9 mm in the cells instead of 1.5 mm.

The printed sleeve of print 3 was far stiffer than needed. The wall under the rib lattice
drops to two perimeters (SleeveOuterDiameter 35 -> 33.8); the ribs stay 0.8 mm, so the case
is Ø35.4 over the ribs instead of 36.6, and the flange follows. Bayonet slots and shutter
notches lie in the solid end bands, which keep about 1 mm over them. The rib shell now
overlaps the wall by 0.1 mm only, so it no longer refills those grooves.
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

doc = App.openDocument(TARGET)
labeled = lambda label: doc.getObjectsByLabel(label)[0]
sheet = labeled("Parameters")
assert abs(float(sheet.get("SleeveOuterDiameter").Value) - 35.0) < 1e-6, "already applied"
sheet.set("B11", "33.8 mm")
doc.recompute()

rebuild_static.rebuild_all(doc, rear_fillets=True)  # lattice, marks, front fillet; the flange shrank

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
for label in ("ChassisFinal", "SleeveFinal", "Shutter", "BoardClamp"):
    part = labeled(label).Shape
    assert part.isValid() and len(part.Solids) == 1, (label, part.isValid(), len(part.Solids))
rebuild_static.save(doc)
App.closeDocument(doc.Name)
print("APPLY_THIN_SLEEVE_CHECK=saved")

"""Shutter detents big enough for a 0.4 mm nozzle.

On the first print the sleeve notches (0.25 mm deep) came out as stringing and were cut off.
- Sleeve notches: 0.75 mm deep (DiscNotchRadius 16.75), 3 mm wide (DiscNotchWidth).
- Disc ribs: 0.35 mm proud of the sleeve bore (DiscRibRadius 16.35), was 0.15.
- Spring slot behind each rib: 0.6 mm wide, was 0.4, so the slicer keeps it open.
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
sheet = labeled("Parameters")
assert abs(float(sheet.get("DiscNotchRadius").Value) - 16.25) < 1e-6, "detents already enlarged"

sheet.set("B110", "16.35 mm")  # DiscRibRadius
sheet.set("B111", "16.75 mm")  # DiscNotchRadius
sheet.set("A134", "Ширина паза фиксатора в гильзе")
sheet.set("B134", "3 mm")
sheet.setAlias("B134", "DiscNotchWidth")
sheet.set("A135", "Внутренний радиус пружинящей прорези диска")
sheet.set("B135", "14.4 mm")
sheet.setAlias("B135", "DiscArcInnerRadius")
doc.recompute()

for name in ("DiscNotchRight", "DiscNotchLeft"):
    notch = labeled(name)
    notch.setExpression("Width", P + "DiscNotchWidth")
    notch.setExpression("Placement.Base.y", "-" + P + "DiscNotchWidth / 2")
for name in ("DiscArcInnerRight", "DiscArcInnerLeft"):
    labeled(name).setExpression("Radius", P + "DiscArcInnerRadius")
doc.recompute()
rebuild_static.rebuild_front_fillet(doc)  # the notches renumber the sleeve edges

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
for label in ("ChassisFinal", "SleeveFinal", "Shutter", "BoardClamp"):
    part = labeled(label).Shape
    assert part.isValid() and len(part.Solids) == 1, (label, part.isValid(), len(part.Solids))
rebuild_static.save(doc)
App.closeDocument(doc.Name)
print("APPLY_DETENTS_CHECK=saved")

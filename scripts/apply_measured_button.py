"""Plus contact recess from the measured battery: button 1.32 mm, plate bump 1.02 mm deep.

The cell's plus button stands 1.32 mm above its shoulder (measured: full length minus
length without the button). With a 0.5 mm recess the button would reach the plate long
before the shoulder reaches the stop, the cell would sit 0.8 mm further forward and the
minus spring would relax to about 3.3 mm.
- The battery pocket ends at the shoulder (+0.3 mm clearance), not at the button tip.
- The plate bump sits where the button tip arrives: PlusContactRecess = button - clearance
  = 1.02 mm behind the pocket end, so a reversed cell stops 1.02 mm short of the plate.
- The spring keeps its 2.5 mm working height. BoardGap goes back to 6 mm: the plate is
  0.8 mm closer to the battery again, so the wire riser keeps its original 2.37 mm.
- Battery dummy: body only; new dummy BatteryButton (Ø8 x 1.32).
Run with freecadcmd, then set_view_in_gui.py.
"""
import os as _os
import re
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
assert not doc.getObjectsByLabel("BatteryButton"), "already applied"
sheet = labeled("Parameters")

for row, text, value, alias in [
    (136, "Высота выступа плюса батареи (измерено)", "1.32 mm", "BatteryButtonHeight"),
    (137, "Диаметр выступа плюса батареи", "8 mm", "BatteryButtonDiameter"),
    (138, "Торец батарейного отсека у плюса, Z", "=RearSpace - BatteryEndClearance + BatteryPocketLength", "BatteryPocketEndZ"),
]:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
sheet.set("B21", "=BatteryLength - BatteryButtonHeight + 2 * BatteryEndClearance")
sheet.set("B127", "=BatteryButtonHeight - BatteryEndClearance")
sheet.set("A127", "Утопление кнопки плюса за торцом отсека")
sheet.set("B43", "=BatteryPocketEndZ + PlusContactRecess + PositiveButtonHeight")
sheet.set("B9", "6 mm")
doc.recompute()

# Every tool that started at the old pocket end now refers to BatteryPocketEndZ.
spaced = r"<<Parameters>>\.RearSpace\s*\+\s*<<Parameters>>\.BatteryLength\s*\+\s*<<Parameters>>\.BatteryEndClearance"
negated = r"-\s*<<Parameters>>\.RearSpace\s*-\s*<<Parameters>>\.BatteryLength\s*-\s*<<Parameters>>\.BatteryEndClearance"
changed = []
for obj in doc.Objects:
    for prop, expr in list(obj.ExpressionEngine):
        new = re.sub(negated, "- " + P + "BatteryPocketEndZ", re.sub(spaced, P + "BatteryPocketEndZ", expr))
        if new != expr:
            obj.setExpression(prop, new)
            changed.append("%s.%s" % (obj.Label, prop))
assert len(changed) == 5, changed

battery = labeled("Battery")
battery.setExpression("Height", P + "BatteryLength - " + P + "BatteryButtonHeight")
button = doc.addObject("Part::Cylinder", "BatteryButton")  # dummy, never printed
button.Label = "BatteryButton"
for field, expression in {
    "Radius": P + "BatteryButtonDiameter / 2",
    "Height": P + "BatteryButtonHeight",
    "Placement.Base.y": P + "BatteryCenterY",
    "Placement.Base.z": P + "RearSpace + " + P + "BatteryLength - " + P + "BatteryButtonHeight",
}.items():
    button.setExpression(field, expression)
doc.recompute()

rebuild_static.rebuild_all(doc)  # sleeve length, cable start and the plus sign moved

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
for label in ("ChassisFinal", "SleeveFinal", "Shutter", "BoardClamp"):
    part = labeled(label).Shape
    assert part.isValid() and len(part.Solids) == 1, (label, part.isValid(), len(part.Solids))
rebuild_static.save(doc)
App.closeDocument(doc.Name)
print("APPLY_BUTTON_CHECK=saved " + ",".join(changed))

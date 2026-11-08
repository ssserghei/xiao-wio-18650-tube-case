"""Widen the pin slots under the Wio to 2.75 mm so Dupont housings fit on the pins.

A row of seven 2.54 mm housings is about 17.8 mm long, so the slots also grow to 18.8 mm.
Run with freecadcmd, then set_view_in_gui.py.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)

import time

import FreeCAD as App

TARGET = _os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
P = "<<Parameters>>."

doc = App.openDocument(TARGET)
sheet = doc.getObjectsByLabel("Parameters")[0]
sheet.set("B96", "2.75 mm")
for row, text, value, alias in [
    (122, "Длина прорези штырей", "18.8 mm", "PinSlotLength"),
    (123, "Начало прорези штырей от отсека плат, Z", "1.6 mm", "PinSlotStart"),
]:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
doc.recompute()
for label in ("PinSlotRight", "PinSlotLeft"):
    slot = doc.getObjectsByLabel(label)[0]
    slot.setExpression("Height", P + "PinSlotLength")
    slot.setExpression("Placement.Base.z", P + "BoardPocketStart + " + P + "PinSlotStart")
doc.recompute()

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
final = doc.getObjectsByLabel("ChassisFinal")[0]
assert final.Shape.isValid() and len(final.Shape.Solids) == 1
for attempt in range(6):  # Windows sometimes still holds the file
    try:
        doc.save()
        break
    except OSError:
        if attempt == 5:
            raise
        time.sleep(2)
App.closeDocument(doc.Name)
print("APPLY_DUPONT_CHECK=saved")

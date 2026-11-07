"""Record the measured antenna thread and deepen the nut recess for more free thread.

Run with freecadcmd after apply_stage_29_32.py, then run set_view_in_gui.py.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import FreeCAD as App

TARGET = _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd")

doc = App.openDocument(TARGET)
sheet = doc.getObjectsByLabel("Parameters")[0]
sheet.set("B61", "3.5 mm")
sheet.set("A79", "Длина резьбы антенного разъёма")
sheet.set("B79", "11 mm")
sheet.setAlias("B79", "AntennaThreadLength")
doc.recompute()
bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
doc.save()
App.closeDocument(doc.Name)
print("APPLY_ANTENNA_CHECK=saved")

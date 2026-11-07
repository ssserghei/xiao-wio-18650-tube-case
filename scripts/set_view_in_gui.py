"""Run with freecad.exe (GUI): set colours and visibility, save with view data, quit.

A GUI save keeps GuiDocument.xml, which a freecadcmd save drops.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import os
import traceback

import FreeCAD as App
import FreeCADGui as Gui

TARGET = _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd")
LOG = _os.path.join(_REPO, "gui_save.log")

STYLE = {
    "ChassisFinal": ((0.85, 0.20, 0.15), 0),
    "SleeveFinal": ((0.75, 0.82, 0.90), 75),
    "BoardClamp": ((0.95, 0.60, 0.15), 0),
    "Shutter": ((0.30, 0.45, 0.85), 40),
    "Battery": ((0.30, 0.70, 0.35), 0),
    "BoardStackModel": ((0.15, 0.45, 0.30), 0),
    "NegativeContact": ((0.75, 0.75, 0.75), 0),
    "PositiveContact": ((0.75, 0.75, 0.75), 0),
    "SpringEnvelope": ((0.60, 0.35, 0.70), 0),
    "AntennaCable": ((0.10, 0.10, 0.10), 0),
}

with open(LOG, "w", encoding="utf-8") as log:
    try:
        doc = App.openDocument(TARGET)
        log.write("opened, objects: %d\n" % len(doc.Objects))
        for obj in doc.Objects:
            view = getattr(obj, "ViewObject", None)
            if view is None or obj.TypeId == "Spreadsheet::Sheet":
                continue
            style = STYLE.get(obj.Label)
            view.Visibility = style is not None
            if style:
                view.ShapeColor = style[0]
                view.Transparency = style[1]
        bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
        log.write("errors: %s\n" % bad)
        doc.save()
        log.write("GUI_SAVE=ok\n")
    except BaseException:
        log.write("GUI_SAVE=fail\n" + traceback.format_exc())
os._exit(0)

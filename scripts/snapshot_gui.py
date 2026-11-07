"""Run with freecad.exe: save shaded views of the chassis rear end, then quit. Does not save the document.

XIAO_TARGET selects the file, XIAO_SNAP_PREFIX the output path prefix.
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
import Part

ROOT = _REPO
TARGET = os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
PREFIX = os.environ.get("XIAO_SNAP_PREFIX", _os.path.join(ROOT, "renders", "rear"))
VIEWS = {
    "_rear": (0.0, 0.0, 1.0),
    "_side": (1.0, 0.0, 0.0),
    "_iso_top": (0.6, -0.6, 0.55),
    "_iso_bottom": (-0.6, 0.6, 0.55),
}

with open(PREFIX + ".log", "w", encoding="utf-8") as log:
    try:
        doc = App.openDocument(TARGET)
        for obj in doc.Objects:
            view = getattr(obj, "ViewObject", None)
            if view is not None and obj.TypeId != "Spreadsheet::Sheet":
                view.Visibility = False
        chassis = doc.getObjectsByLabel("ChassisFinal")[0].Shape
        rear = chassis.common(Part.makeBox(60, 60, 34, App.Vector(-30, -30, -26)))
        tip = doc.addObject("Part::Feature", "SnapRear")  # exists only for the pictures
        tip.Shape = rear
        tip.ViewObject.ShapeColor = (0.95, 0.62, 0.12)
        tip.ViewObject.DisplayMode = "Shaded"
        # Second picture set: the boards and coax in the open chassis.
        extras = []
        for label, colour in (("BoardStackModel", (0.15, 0.45, 0.30)), ("AntennaCable", (0.08, 0.08, 0.08)), ("BoardClamp", (0.95, 0.75, 0.25))):
            extra = doc.getObjectsByLabel(label)[0]
            extra.ViewObject.ShapeColor = colour
            extra.ViewObject.DisplayMode = "Shaded"
            extras.append(extra)
        active = Gui.activeDocument().activeView()
        active.setCameraType("Perspective")
        Gui.updateGui()
        for suffix, direction in VIEWS.items():
            active.setViewDirection(direction)
            active.fitAll()
            Gui.updateGui()
            active.saveImage(PREFIX + suffix + ".png", 1100, 800, "White")
        tip.ViewObject.Visibility = False
        full = doc.addObject("Part::Feature", "SnapFront")  # exists only for the pictures
        full.Shape = chassis.common(Part.makeBox(60, 60, 56, App.Vector(-30, -30, 66)))
        full.ViewObject.ShapeColor = (0.95, 0.62, 0.12)
        full.ViewObject.DisplayMode = "Shaded"
        extras[0].ViewObject.Visibility = True
        extras[1].ViewObject.Visibility = False
        coax = doc.addObject("Part::Feature", "SnapCoax")  # exists only for the pictures
        coax.Shape = extras[1].Shape.common(Part.makeBox(60, 60, 56, App.Vector(-30, -30, 66)))
        coax.ViewObject.ShapeColor = (0.08, 0.08, 0.08)
        coax.ViewObject.DisplayMode = "Shaded"
        for suffix, direction in (("_boards", (0.3, -0.85, 0.45)), ("_boards_under", (0.3, 0.85, 0.45))):
            active.setViewDirection(direction)
            active.fitAll()
            Gui.updateGui()
            active.saveImage(PREFIX + suffix + ".png", 1100, 800, "White")
        # Third set: the closed case as it will look.
        for obj in doc.Objects:
            view = getattr(obj, "ViewObject", None)
            if view is not None and obj.TypeId != "Spreadsheet::Sheet":
                view.Visibility = obj.Label in ("ChassisFinal", "SleeveFinal", "Shutter")
        for label in ("ChassisFinal", "SleeveFinal", "Shutter"):
            part = doc.getObjectsByLabel(label)[0].ViewObject
            part.ShapeColor = (0.95, 0.62, 0.12)
            part.Transparency = 0
            part.DisplayMode = "Shaded"
        for suffix, direction in (("_case_front", (0.5, -0.45, -0.75)), ("_case_rear", (0.55, 0.45, 0.7))):
            active.setViewDirection(direction)
            active.fitAll()
            Gui.updateGui()
            active.saveImage(PREFIX + suffix + ".png", 1100, 800, "White")
        log.write("SNAP=ok\n")
    except BaseException:
        log.write("SNAP=fail\n" + traceback.format_exc())
os._exit(0)

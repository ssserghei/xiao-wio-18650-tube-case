"""Diamond knurl bands on the sleeve: 10 mm at each end, about 4.5 mm diamonds.

Two sets of 24 helical V-grooves (left- and right-handed, 45 degrees) are swept and cut.
The rear band starts behind the bayonet slots, where the wall is only 0.85 mm; the front
band stops before the disc detent notches. The grooves are a static shape (`KnurlTool`).
Run with freecadcmd, then set_view_in_gui.py.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)

import math
import time

import FreeCAD as App
import Part

TARGET = _os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
STARTS = 24          # diamonds around the circumference: 110 mm / 24 = 4.6 mm
DEPTH = 0.5          # groove depth, mm
TOP_FLAT = 0.6       # flat left on each diamond top, measured around the circumference
BAND = 10.0
REAR_START = 6.0

doc = App.openDocument(TARGET)
assert not doc.getObjectsByLabel("KnurlTool"), "the knurl is already applied"
sheet = doc.getObjectsByLabel("Parameters")[0]


def number(alias):
    item = sheet.get(alias)
    return float(item.Value) if hasattr(item, "Value") else float(item)


radius = number("SleeveOuterDiameter") / 2
length = number("SleeveLength")
for row, text, value, alias in [
    (124, "Рифление: ромбов по окружности", str(STARTS), "KnurlStarts"),
    (125, "Рифление: глубина", "%s mm" % DEPTH, "KnurlDepth"),
    (126, "Рифление: ширина пояса", "%s mm" % BAND, "KnurlBand"),
]:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)

circumference = 2 * math.pi * radius
lead = circumference          # 45 degree helix: one turn per circumference of height
groove_width = circumference / STARTS - TOP_FLAT   # around the circumference
axial_half = groove_width / 2  # at 45 degrees the axial width equals the circumferential one


def groove(z0, height, left):
    helix = Part.makeHelix(lead, height, radius, 0, left)
    helix.translate(App.Vector(0, 0, z0))
    start = helix.Edges[0].valueAt(helix.Edges[0].FirstParameter)
    profile = Part.makePolygon([
        App.Vector(start.x + 0.6, 0, start.z - axial_half - 0.4),
        App.Vector(start.x - DEPTH, 0, start.z),
        App.Vector(start.x + 0.6, 0, start.z + axial_half + 0.4),
        App.Vector(start.x + 0.6, 0, start.z - axial_half - 0.4),
    ])
    return Part.Wire(helix.Edges).makePipeShell([profile], True, True)


bands = [(REAR_START, BAND), (length - BAND, BAND)]
tools = []
for z0, height in bands:
    clip = Part.makeCylinder(radius + 2, height, App.Vector(0, 0, z0)).cut(Part.makeCylinder(radius - DEPTH - 0.2, height, App.Vector(0, 0, z0)))
    for left in (False, True):
        base = groove(z0 - 3, height + 6, left)
        for i in range(STARTS):
            piece = base.copy()
            piece.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 360.0 * i / STARTS)
            tools.append(piece.common(clip))
knurl = doc.addObject("Part::Feature", "KnurlTool")
knurl.Label = "KnurlTool"
knurl.Shape = Part.makeCompound([s for t in tools for s in t.Solids])
knurl.Visibility = False

rim = doc.getObjectsByLabel("SleeveFinal")[0]
rim.Label = "SleeveRim"
cut = doc.addObject("Part::Cut", "SleeveKnurled")
cut.Label = "SleeveFinal"
cut.Base = rim
cut.Tool = knurl
rim.Visibility = False
cut.Visibility = True
doc.recompute()

shape = cut.Shape
assert shape.isValid() and len(shape.Solids) == 1, (shape.isValid(), len(shape.Solids))
assert shape.Volume < rim.Shape.Volume - 50, "knurl removed almost nothing"
for attempt in range(6):  # Windows sometimes still holds the file
    try:
        doc.save()
        break
    except OSError:
        if attempt == 5:
            raise
        time.sleep(2)
removed = rim.Shape.Volume - shape.Volume
App.closeDocument(doc.Name)
print("APPLY_KNURL_CHECK=saved removed_mm3=%.1f grooves=%d" % (removed, len(tools)))

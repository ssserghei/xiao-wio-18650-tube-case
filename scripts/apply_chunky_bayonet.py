"""Drop the O-ring, rebuild the bayonet chunkier, give the wire niche side walls.

- The O-ring sealed nothing: printed PETG is porous. Its groove goes, and the rear wall it
  occupied (Z 0-4.9 mm) now carries much thicker bayonet lugs.
- Bayonet: lugs 2.4 mm thick (was 1.0) and 45 degrees wide (was 40), lead 0.5 mm over a
  40 degree turn, 0.2 mm axial and 0.25 mm radial clearance for a coarse printer. The sleeve
  keeps 0.85 mm of wall over the slots.
- Wire niche: a 1.5 mm outer wall follows the chassis surface on both sides, so wires do not
  fall out while the sleeve is pushed on. The original channel still opens the bottom.
Lugs and slots are static helical lofts. Run with freecadcmd, then set_view_in_gui.py.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)

import math

import FreeCAD as App
import Part

TARGET = _os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
P = "<<Parameters>>."
LUG_ANGLES = (30, 150, 270)

doc = App.openDocument(TARGET)
assert doc.getObjectsByLabel("ChassisORing"), "the O-ring groove is already gone"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


def remove(*labels):
    for label in labels:
        for obj in doc.getObjectsByLabel(label):
            doc.removeObject(obj.Name)


sheet = labeled("Parameters")
rows = [
    (98, "Низ выступа байонета в центре, Z", "1.6 mm", "BayonetLugStartZ"),
    (99, "Толщина выступа байонета", "2.4 mm", "BayonetLugThickness"),
    (100, "Радиус выступа байонета", "16.4 mm", "BayonetLugRadius"),
    (101, "Радиус паза байонета", "16.65 mm", "BayonetGrooveRadius"),
    (112, "Ширина выступа байонета, градусы", "45", "BayonetLugAngle"),
    (113, "Поворот байонета, градусы", "40", "BayonetTurn"),
    (114, "Подъём байонета за поворот", "0.5 mm", "BayonetLead"),
    (120, "Осевой зазор байонета", "0.2 mm", "BayonetAxialClearance"),
    (121, "Стенка ниши проводов", "1.5 mm", "WireNicheWall"),
]
for row, text, value, alias in rows:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
sheet.clear("A102")
sheet.clear("B102")  # the click ridge is gone: the helix holds by friction
doc.recompute()


def number(alias):
    item = sheet.get(alias)
    return float(item.Value) if hasattr(item, "Value") else float(item)


# --- O-ring groove out of the chassis chain.
o_ring = labeled("ChassisORing")
before = o_ring.Base
bayonet = labeled("ChassisBayonet")

# --- New helical lugs and slots.
width = number("BayonetLugAngle")
turn = number("BayonetTurn")
lead = number("BayonetLead")
low = number("BayonetLugStartZ")
thick = number("BayonetLugThickness")
lug_r = number("BayonetLugRadius")
groove_r = number("BayonetGrooveRadius")
gap = number("BayonetAxialClearance")
slope = lead / turn


def section(r0, r1, z0, z1, angle):
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    points = [App.Vector(r * c, r * s, z) for r, z in ((r0, z0), (r1, z0), (r1, z1), (r0, z1), (r0, z0))]
    return Part.makePolygon(points)


def helical(r0, r1, a0, a1, z0, z1):
    steps = max(2, int(math.ceil((a1 - a0) / 4.0)))
    angles = [a0 + (a1 - a0) * i / steps for i in range(steps + 1)]
    return Part.makeLoft([section(r0, r1, z0(a), z1(a), a) for a in angles], True, True)


lugs, slots = [], []
for phi in LUG_ANGLES:
    lug_low = lambda a, phi=phi: low + slope * (a - phi)
    lug_high = lambda a, phi=phi: low + slope * (a - phi) + thick
    shape = helical(15.0, lug_r, phi - width / 2, phi + width / 2, lug_low, lug_high)
    old = labeled("BayonetLugShape%d" % phi)
    old.Shape = shape  # same object, so the fuse keeps its link
    lugs.append(old)
    far = phi + width / 2 + 2
    near = phi - turn - width / 2 - 2
    ramp = helical(15.5, groove_r, near, far, lambda a, f=lug_low: f(a) - gap, lambda a, f=lug_high: f(a) + gap)
    entry = helical(15.5, groove_r, near, phi - turn + width / 2 + 2, lambda a: -1.0, lambda a, f=lug_high: f(a) + gap)
    # Fusing the two lofts silently drops one of them, so the cut gets both as separate solids.
    for piece in (ramp, entry):
        assert piece.isValid() and len(piece.Solids) == 1, ("slot", phi)
        slots.append(piece)
bayonet.Shapes = [before] + lugs
labeled("BayonetSlotShapes").Shape = Part.makeCompound(slots)
# A new Shape on a Part::Feature does not mark its users: touch them so they recompute.
for label in ("SleeveBayonet", "ChassisBayonet"):
    labeled(label).touch()
doc.recompute()
remove("ChassisORing", "ORingGrooveTool")
for row in (62, 63, 64):
    sheet.clear("A%d" % row)
    sheet.clear("B%d" % row)
doc.recompute()

# --- Niche with side walls: the full-width box now stops 1.5 mm inside the chassis surface.
niche_box = labeled("WireNicheTool")
core = doc.addObject("Part::Cylinder", "WireNicheCore")
core.Label = "WireNicheCore"
for field, expression in {
    "Radius": P + "ChassisDiameter / 2 - " + P + "WireNicheWall",
    "Height": P + "BoardPocketStart - " + P + "WireChannelStartZ + 2 mm",
    "Placement.Base.z": P + "WireChannelStartZ - 1 mm",
}.items():
    core.setExpression(field, expression)
core.Visibility = False
inner = doc.addObject("Part::MultiCommon", "WireNicheInner")
inner.Label = "WireNicheInner"
inner.Shapes = [niche_box, core]
inner.Visibility = False
labeled("ChassisWireNiche").Tool = inner
doc.recompute()

# --- The sleeve rim fillet stores an edge number, and the slots changed the numbering.
notched = labeled("SleeveNotched")
rim = labeled("SleeveFinal")
shape = notched.Shape
outer = number("SleeveOuterDiameter") / 2
top = max(v.Z for v in shape.Vertexes)
edges = [
    i for i, e in enumerate(shape.Edges, 1)
    if abs(e.BoundBox.ZMin - top) < 1e-6 and abs(e.BoundBox.ZMax - top) < 1e-6
    and abs(math.hypot(e.valueAt(e.FirstParameter).x, e.valueAt(e.FirstParameter).y) - outer) < 1e-6
]
assert edges, "outer front edge not found"
rim.Edges = [(i, 1.5, 1.5) for i in edges]
doc.recompute()

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
for label in ("ChassisFinal", "SleeveFinal", "Shutter", "BoardClamp"):
    part = labeled(label).Shape
    assert part.isValid() and len(part.Solids) == 1, (label, part.isValid(), len(part.Solids))
assert rim.Shape.Volume < notched.Shape.Volume, "rim fillet removed nothing"
# Saving sometimes fails with "Permission denied" while Windows still holds the file: retry.
import time

for attempt in range(6):
    try:
        doc.save()
        break
    except OSError:
        if attempt == 5:
            raise
        time.sleep(2)
App.closeDocument(doc.Name)
print("APPLY_CHUNKY_CHECK=saved")

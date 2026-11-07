"""Helical bayonet, wider tab wells, thinner USB wall, lug hole moved away from the tip.

The bayonet becomes a short three-start thread: wide lugs on a 0.4 mm lead over a 40 degree
turn, so the last part of the turn pulls the flange tight. Lugs and slots are static shapes:
re-run this logic if their parameters change. Run after apply_round_front.py, then set_view_in_gui.py.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import math
import os

import FreeCAD as App
import Part

TARGET = os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
P = "<<Parameters>>."
EDGE_RADIUS = 1.5
HOLE_EDGE_RADIUS = 0.8
LUG_ANGLES = (30, 150, 270)

doc = App.openDocument(TARGET)
assert not doc.getObjectsByLabel("BayonetLugShape30"), "the helical bayonet is already applied"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


def remove(*labels):
    for label in labels:
        for obj in doc.getObjectsByLabel(label):
            doc.removeObject(obj.Name)


sheet = labeled("Parameters")
sheet.set("B10", "1.8 mm")   # USB wall = FrontSpace - BoardClearance = 1.5 mm
sheet.set("B55", "2.6 mm")   # tab wells take a Dupont connector
sheet.set("B64", "2.4 mm")   # O-ring moves clear of the helical slots
sheet.set("B98", "1 mm")     # lug low face at its centre
sheet.set("B99", "1 mm")     # lug thickness
rows = [
    (112, "Ширина выступа байонета, градусы", "40", "BayonetLugAngle"),
    (113, "Поворот байонета, градусы", "40", "BayonetTurn"),
    (114, "Подъём байонета за поворот", "0.4 mm", "BayonetLead"),
    (115, "Смещение отверстия проушины от конца", "0.5 mm", "LugHoleOffset"),
]
for row, text, value, alias in rows:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
doc.recompute()


def number(alias):
    item = sheet.get(alias)
    return float(item.Value) if hasattr(item, "Value") else float(item)


width = number("BayonetLugAngle")
turn = number("BayonetTurn")
lead = number("BayonetLead")
low = number("BayonetLugStartZ")
thick = number("BayonetLugThickness")
lug_r = number("BayonetLugRadius")
groove_r = number("BayonetGrooveRadius")
slope = lead / turn


def section(r0, r1, z0, z1, angle):
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    points = [App.Vector(r * c, r * s, z) for r, z in ((r0, z0), (r1, z0), (r1, z1), (r0, z1), (r0, z0))]
    return Part.makePolygon(points)


def helical(r0, r1, a0, a1, z0, z1):
    """Solid between two radii, swept from a0 to a1 with z limits given as functions of angle."""
    steps = max(2, int(math.ceil((a1 - a0) / 4.0)))
    angles = [a0 + (a1 - a0) * i / steps for i in range(steps + 1)]
    return Part.makeLoft([section(r0, r1, z0(a), z1(a), a) for a in angles], True, True)


def feature(label, shape):
    obj = doc.addObject("Part::Feature", label)
    obj.Label = label
    obj.Shape = shape
    obj.Visibility = False
    return obj


lugs, slots = [], []
for phi in LUG_ANGLES:
    lug_low = lambda a, phi=phi: low + slope * (a - phi)
    lug_high = lambda a, phi=phi: low + slope * (a - phi) + thick
    lugs.append(feature("BayonetLugShape%d" % phi, helical(15.0, lug_r, phi - width / 2, phi + width / 2, lug_low, lug_high)))
    far = phi + width / 2 + 2
    near = phi - turn - width / 2 - 2
    ramp = helical(15.5, groove_r, near, far, lambda a, f=lug_low: f(a) - 0.05, lambda a, f=lug_high: f(a) + 0.1)
    entry = helical(15.5, groove_r, near, phi - turn + width / 2 + 2, lambda a: -1.0, lambda a, f=lug_high: f(a) + 0.1)
    slots.append(ramp.fuse(entry).removeSplitter())

# --- Swap the old lugs and slots for the new shapes.
bayonet = labeled("ChassisBayonet")
bayonet.Shapes = [labeled("ChassisORing")] + lugs
sleeve_cut = labeled("SleeveBayonet")
sleeve_cut.Tool = feature("BayonetSlotShapes", Part.makeCompound(slots))
doc.recompute()
remove("BayonetSlotTools")
for phi in LUG_ANGLES:
    remove("BayonetSeat%d" % phi, "BayonetRidge%d" % phi, "BayonetEntry%d" % phi,
           "BayonetLug%d" % phi, "BayonetSector%d" % phi, "BayonetCore%d" % phi)

# --- Wider wells. The minus one starts further back to keep a wall to the battery pocket.
labeled("NegativeTabPassTool").setExpression("Placement.Base.z", P + "NegativeContactZ - 1.6 mm")

# --- Lug hole, then the rear fillets again: the hole edges changed.
hole = labeled("LugHoleTool")
hole.setExpression("Placement.Base.z", "-" + P + "FlangeThickness - " + P + "LugReach + " + P + "LugTipDiameter / 2 + " + P + "LugHoleOffset")
chassis_blank = labeled("ChassisBlank")
drilled = labeled("RearDrilled")
chassis_blank.Shapes = [labeled("ChassisCore"), drilled]
remove("RearBody", "RearRounded")
doc.recompute()


def normal_at(face, point):
    u, v = face.Surface.parameter(point)
    return face.normalAt(u, v)


def is_sharp(shape, edge):
    middle = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2)
    faces = shape.ancestorsOfType(edge, Part.Face)
    if len(faces) < 2 or faces[0].isSame(faces[1]):
        return False
    angle = normal_at(faces[0], middle).getAngle(normal_at(faces[1], middle))
    return angle > math.radians(4) and abs(angle - math.pi) > math.radians(4)


def round_pass(base, name, radius, skip_hole):
    """Round every sharp edge the kernel accepts; one bad edge must not lose the rest."""
    shape = base.Shape
    hole_r = hole.Radius.Value
    hole_z = hole.Placement.Base.z
    kept, left = [], []
    for index, edge in sorted(enumerate(shape.Edges, 1), key=lambda item: item[1].BoundBox.ZMin):
        if edge.BoundBox.ZMin > -0.01 or not is_sharp(shape, edge):
            continue
        middle = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2)
        if skip_hole and abs(math.hypot(middle.x, middle.z - hole_z) - hole_r) < 1e-4:
            continue
        try:
            trial = shape.makeFillet(radius, [shape.Edges[i - 1] for i in kept + [index]])
            good = trial.isValid() and len(trial.Solids) == 1
        except Exception:
            good = False
        if good:
            kept.append(index)
        else:
            left.append((round(middle.x, 1), round(middle.y, 1), round(middle.z, 1)))
    result = doc.addObject("Part::Fillet", name)
    result.Label = name
    result.Base = base
    result.Edges = [(i, radius, radius) for i in kept]
    base.Visibility = False
    result.Visibility = False
    doc.recompute()
    assert result.Shape.isValid() and len(result.Shape.Solids) == 1, name
    print("edges", name, "rounded:", len(kept), "left sharp:", left)
    return result


body = round_pass(drilled, "RearRounded", EDGE_RADIUS, True)
body = round_pass(body, "RearBody", HOLE_EDGE_RADIUS, False)
chassis_blank.Shapes = [labeled("ChassisCore"), body]
doc.recompute()

# --- The sleeve rim fillet holds an edge number, and the slots changed the numbering.
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
doc.save()
App.closeDocument(doc.Name)
print("APPLY_BAYONET_CHECK=saved")

"""Raised diamond lattice instead of cut knurl: the sleeve gets stiffer instead of thinner.

- The knurl grooves are removed.
- A 0.8 mm outer shell covers the sleeve. Diamond windows are cut into it between a solid
  band over the bayonet slots (Z 0-6 mm, where the wall was only 0.85 mm) and a solid band
  at the front end. What stays between the windows is a lattice of 45 degree ribs, about
  10 mm diamonds, 11 around the circumference.
- Windows are simple prisms that never touch each other. Sweeping crossing helical ribs
  instead took 16 minutes and still produced an invalid solid.
- The flange grows to the shell diameter so the seam stays flush; the rear-body fillets are
  re-picked because the flange edges changed.
The shell is a static shape (`RibCage`). Run with freecadcmd, then set_view_in_gui.py.
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
STARTS = 11          # diamonds around the circumference
HEIGHT = 0.8         # rib height above the sleeve wall
RIB = 2.4            # rib width, normal to the rib
REAR_BAND = 6.0
FRONT_BAND = 5.2     # 2 mm before the chassis end plus the 3.2 mm sleeve extension
EDGE_RADIUS = 1.5
HOLE_EDGE_RADIUS = 0.8

doc = App.openDocument(TARGET)
assert doc.getObjectsByLabel("KnurlTool"), "expects the knurled sleeve"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


def remove(*labels):
    for label in labels:
        for obj in doc.getObjectsByLabel(label):
            doc.removeObject(obj.Name)


sheet = labeled("Parameters")


def number(alias):
    item = sheet.get(alias)
    return float(item.Value) if hasattr(item, "Value") else float(item)


# --- Knurl out.
knurled = labeled("SleeveFinal")
rim = labeled("SleeveRim")
doc.removeObject(knurled.Name)
remove("KnurlTool")
for row in (124, 125, 126):
    sheet.clear("A%d" % row)
    sheet.clear("B%d" % row)
for row, text, value, alias in [
    (124, "Рёбра: ромбов по окружности", str(STARTS), "RibStarts"),
    (125, "Рёбра: высота", "%s mm" % HEIGHT, "RibHeight"),
    (126, "Рёбра: ширина", "%s mm" % RIB, "RibWidth"),
]:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
sheet.set("B17", "=SleeveOuterDiameter + 2 * RibHeight")  # flange flush with the shell
doc.recompute()

# --- Shell with diamond windows.
radius = number("SleeveOuterDiameter") / 2
length = number("SleeveLength")
end = length + number("SleeveFrontExtra")
crest = radius + HEIGHT
period = 2 * math.pi * radius / STARTS              # diamond pitch around and along, mm
half = (period / 2 * math.sin(math.radians(45)) - RIB / 2) / math.sin(math.radians(45))  # window half-diagonal
z_low, z_high = REAR_BAND, end - FRONT_BAND


def clip(points, w_min, w_max):
    """Sutherland-Hodgman against w_min <= w <= w_max, points as (u, w)."""
    for limit, keep in ((w_min, lambda w: w >= w_min), (w_max, lambda w: w <= w_max)):
        out = []
        for i, current in enumerate(points):
            previous = points[i - 1]
            if keep(current[1]):
                if not keep(previous[1]):
                    t = (limit - previous[1]) / (current[1] - previous[1])
                    out.append((previous[0] + t * (current[0] - previous[0]), limit))
                out.append(current)
            elif keep(previous[1]):
                t = (limit - previous[1]) / (current[1] - previous[1])
                out.append((previous[0] + t * (current[0] - previous[0]), limit))
        points = out
        if len(points) < 3:
            return []
    return points


windows = []
row = 0
zc = z_low - period / 2
while zc - half < z_high:
    offset = 0.5 if row % 2 else 0.0
    for k in range(STARTS):
        theta = 2 * math.pi * (k + offset) / STARTS
        diamond = [(half, 0), (0, half), (-half, 0), (0, -half)]
        poly = clip(diamond, z_low - zc, z_high - zc)
        if len(poly) < 3 or max(p[1] for p in poly) - min(p[1] for p in poly) < 0.6:
            continue
        normal = App.Vector(math.cos(theta), math.sin(theta), 0)
        tangent = App.Vector(-math.sin(theta), math.cos(theta), 0)
        centre = normal * (crest + 0.6) + App.Vector(0, 0, zc)
        pts = [centre + tangent * u + App.Vector(0, 0, w) for u, w in poly]
        face = Part.Face(Part.makePolygon(pts + [pts[0]]))
        windows.append(face.extrude(normal * -(HEIGHT + 1.0)))
    row += 1
    zc += period / 2

shell = Part.makeCylinder(crest, end, App.Vector(0, 0, 0)).cut(Part.makeCylinder(radius - 0.3, end, App.Vector(0, 0, 0)))
cage = shell.cut(Part.makeCompound(windows)).removeSplitter()
assert cage.isValid() and len(cage.Solids) == 1, ("rib cage", cage.isValid(), len(cage.Solids))
cage_obj = doc.addObject("Part::Feature", "RibCage")
cage_obj.Label = "RibCage"
cage_obj.Shape = cage
cage_obj.Visibility = False

ribbed = doc.addObject("Part::MultiFuse", "SleeveRibbed")
ribbed.Label = "SleeveRibbed"
# The shell goes on the sleeve before its old rim fillet: over the fillet it would leave a
# ring-shaped dip in the front face. The new fillet rounds the shell crest instead.
notched = rim.Base
ribbed.Shapes = [notched, cage_obj]
notched.Visibility = False
ribbed.Visibility = False
doc.recompute()
doc.removeObject(rim.Name)
doc.recompute()
assert ribbed.Shape.isValid() and len(ribbed.Shape.Solids) == 1

shape = ribbed.Shape
top = max(v.Z for v in shape.Vertexes)
edges = [
    i for i, e in enumerate(shape.Edges, 1)
    if abs(e.BoundBox.ZMin - top) < 1e-6 and abs(e.BoundBox.ZMax - top) < 1e-6
    and abs(math.hypot(e.valueAt(e.FirstParameter).x, e.valueAt(e.FirstParameter).y) - crest) < 1e-4
]
assert edges, "front crest edge not found"
final = doc.addObject("Part::Fillet", "SleeveRibRim")
final.Label = "SleeveFinal"
final.Base = ribbed
final.Edges = [(i, 1.5, 1.5) for i in edges]
final.Visibility = True
doc.recompute()
assert final.Shape.isValid() and len(final.Shape.Solids) == 1

# --- The flange grew: rebuild the rear-body fillets.
hole = labeled("LugHoleTool")
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


def round_pass(base, name, radius_, skip_hole):
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
            trial = shape.makeFillet(radius_, [shape.Edges[i - 1] for i in kept + [index]])
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
    result.Edges = [(i, radius_, radius_) for i in kept]
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

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
for label in ("ChassisFinal", "SleeveFinal", "Shutter", "BoardClamp"):
    part = labeled(label).Shape
    assert part.isValid() and len(part.Solids) == 1, (label, part.isValid(), len(part.Solids))
for attempt in range(6):  # Windows sometimes still holds the file
    try:
        doc.save()
        break
    except OSError:
        if attempt == 5:
            raise
        time.sleep(2)
App.closeDocument(doc.Name)
print("APPLY_RIBS_CHECK=saved windows=%d half_diagonal=%.2f" % (len(windows), half))

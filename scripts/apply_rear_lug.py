"""Replace the flange and ring loop with one rounded rear body that grows into a flat lug.

Run with freecadcmd, then set_view_in_gui.py. Set XIAO_TARGET to try it on another file.
Edges of the fillet are picked here, so re-run this script if the topology changes.
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
import Sketcher

TARGET = os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
P = "<<Parameters>>."
EDGE_RADIUS = 1.5
HOLE_EDGE_RADIUS = 0.8

doc = App.openDocument(TARGET)
assert not doc.getObjectsByLabel("RearBody"), "the rear lug is already applied"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


sheet = labeled("Parameters")

# The ring loop goes first: its expressions use the aliases reused below.
spring = labeled("ChassisSpring")
pockets = labeled("ChassisPockets")
old_fuse = labeled("ChassisLanyard")
old_loop = labeled("LanyardLoop")
spring.Base = pockets
doc.removeObject(old_fuse.Name)
doc.removeObject(old_loop.Name)
doc.recompute()

rows = [
    (26, "Диаметр конца проушины", "13 mm", "LugTipDiameter"),
    (27, "Диаметр отверстия проушины", "6 mm", "LugHoleDiameter"),
    (28, "Толщина проушины", "6 mm", "LugThickness"),
    (29, "Вылет проушины за задний торец", "16 mm", "LugReach"),
    (30, "Центр проушины, Y", "8 mm", "LugCenterY"),
    (80, "Радиус перехода к проушине снизу", "5 mm", "LugNeckRadiusLow"),
    (81, "Радиус перехода к проушине сверху", "8 mm", "LugNeckRadiusTop"),
    (82, "Полуширина контура у торца", "16 mm", "LugShoulderHalfWidth"),
]
for row, text, value, alias in rows:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
doc.recompute()

F = P + "FlangeThickness"
tip_r = P + "LugTipDiameter / 2"
top = P + "LugCenterY + " + P + "LugThickness / 2"
low = P + "LugCenterY - " + P + "LugThickness / 2"
far_z = "-" + F + " - " + P + "LugReach - 2 mm"

# Side profile (sketch x = model Y, sketch y = model Z), extruded across X.
# A flat lug grows out of the rear face through two concave arcs.
side = doc.addObject("Sketcher::SketchObject", "LugSideSketch")
side.Label = "LugSideSketch"
side.Placement = App.Placement(App.Vector(-22, 0, 0), App.Rotation(App.Vector(1, 1, 1), 120))
V = App.Vector
RU, RL, YT, YL, ZF = 8.0, 5.0, 11.0, 5.0, -22.0
side.addGeometry(Part.LineSegment(V(-22, 2, 0), V(22, 2, 0)), False)                 # 0
side.addGeometry(Part.LineSegment(V(22, 2, 0), V(22, -4, 0)), False)                 # 1
side.addGeometry(Part.LineSegment(V(22, -4, 0), V(YT + RU, -4, 0)), False)           # 2
upper = Part.Circle(V(YT + RU, -4 - RU, 0), V(0, 0, 1), RU)
side.addGeometry(Part.ArcOfCircle(upper, math.pi / 2, math.pi), False)               # 3
side.addGeometry(Part.LineSegment(V(YT, -4 - RU, 0), V(YT, ZF, 0)), False)           # 4
side.addGeometry(Part.LineSegment(V(YT, ZF, 0), V(YL, ZF, 0)), False)                # 5
side.addGeometry(Part.LineSegment(V(YL, ZF, 0), V(YL, -4 - RL, 0)), False)           # 6
lower = Part.Circle(V(YL - RL, -4 - RL, 0), V(0, 0, 1), RL)
side.addGeometry(Part.ArcOfCircle(lower, 0, math.pi / 2), False)                     # 7
side.addGeometry(Part.LineSegment(V(YL - RL, -4, 0), V(-22, -4, 0)), False)          # 8
side.addGeometry(Part.LineSegment(V(-22, -4, 0), V(-22, 2, 0)), False)               # 9
C = Sketcher.Constraint
for constraint in (
    C("Coincident", 0, 2, 1, 1), C("Coincident", 1, 2, 2, 1),
    C("Tangent", 2, 2, 3, 1), C("Tangent", 3, 2, 4, 1),
    C("Coincident", 4, 2, 5, 1), C("Coincident", 5, 2, 6, 1),
    C("Tangent", 6, 2, 7, 1), C("Tangent", 7, 2, 8, 1),
    C("Coincident", 8, 2, 9, 1), C("Coincident", 9, 2, 0, 1),
    C("Horizontal", 0), C("Horizontal", 2), C("Horizontal", 5), C("Horizontal", 8),
    C("Vertical", 1), C("Vertical", 4), C("Vertical", 6), C("Vertical", 9),
):
    side.addConstraint(constraint)


def side_datum(constraint, name, expression):
    side.renameConstraint(side.addConstraint(constraint), name)
    side.setExpression("Constraints." + name, expression)


side_datum(C("DistanceX", 0, 1, -22.0), "LeftY", "-22 mm")
side_datum(C("DistanceY", 0, 1, 2.0), "TopZ", "2 mm")
side_datum(C("DistanceX", 1, 1, 22.0), "RightY", "22 mm")
side_datum(C("DistanceY", 2, 1, -4.0), "RearZ", "-" + F)
side_datum(C("DistanceY", 8, 2, -4.0), "RearZLow", "-" + F)
side_datum(C("DistanceX", 4, 1, YT), "LugTopY", top)
side_datum(C("DistanceX", 6, 1, YL), "LugLowY", low)
side_datum(C("DistanceY", 5, 1, ZF), "FarZ", far_z)
side_datum(C("Radius", 3, RU), "NeckTop", P + "LugNeckRadiusTop")
side_datum(C("Radius", 7, RL), "NeckLow", P + "LugNeckRadiusLow")

# Plan outline (sketch x = model X, sketch y = model Z), extruded along Y.
plan = doc.addObject("Sketcher::SketchObject", "LugPlanSketch")
plan.Label = "LugPlanSketch"
plan.Placement = App.Placement(App.Vector(0, 22, 0), App.Rotation(App.Vector(1, 0, 0), 90))
# The outline narrows only behind the rear face, so the flange stays fully round.
W, rear, r, zc = 16.0, -4.0, 6.5, -13.5
h = rear - zc
d = math.hypot(W, h)
t = math.atan2(h, W) - math.acos(r / d)
tx, tz = r * math.cos(t), zc + r * math.sin(t)
plan.addGeometry(Part.LineSegment(V(-22, 2, 0), V(22, 2, 0)), False)        # 0
plan.addGeometry(Part.LineSegment(V(22, 2, 0), V(22, rear, 0)), False)      # 1
plan.addGeometry(Part.LineSegment(V(22, rear, 0), V(W, rear, 0)), False)    # 2
plan.addGeometry(Part.LineSegment(V(W, rear, 0), V(tx, tz, 0)), False)      # 3
circle = Part.Circle(V(0, zc, 0), V(0, 0, 1), r)
plan.addGeometry(Part.ArcOfCircle(circle, math.pi - t, 2 * math.pi + t), False)  # 4
plan.addGeometry(Part.LineSegment(V(-tx, tz, 0), V(-W, rear, 0)), False)    # 5
plan.addGeometry(Part.LineSegment(V(-W, rear, 0), V(-22, rear, 0)), False)  # 6
plan.addGeometry(Part.LineSegment(V(-22, rear, 0), V(-22, 2, 0)), False)    # 7
for constraint in (
    C("Coincident", 0, 2, 1, 1), C("Coincident", 1, 2, 2, 1), C("Coincident", 2, 2, 3, 1),
    C("Tangent", 3, 2, 4, 2), C("Tangent", 4, 1, 5, 1),
    C("Coincident", 5, 2, 6, 1), C("Coincident", 6, 2, 7, 1), C("Coincident", 7, 2, 0, 1),
    C("Horizontal", 0), C("Horizontal", 2), C("Horizontal", 6),
    C("Vertical", 1), C("Vertical", 7),
    C("PointOnObject", 4, 3, -2),
):
    plan.addConstraint(constraint)


def named(constraint, name, expression):
    plan.renameConstraint(plan.addConstraint(constraint), name)
    plan.setExpression("Constraints." + name, expression)


tip_center_z = "-" + F + " - " + P + "LugReach + " + tip_r
named(C("Radius", 4, r), "TipRadius", tip_r)
named(C("DistanceY", 4, 3, zc), "TipCenterZ", tip_center_z)
named(C("DistanceX", 0, 2, 22.0), "OuterRight", "22 mm")
named(C("DistanceX", 0, 1, -22.0), "OuterLeft", "-22 mm")
named(C("DistanceY", 0, 2, 2.0), "TopZ", "2 mm")
named(C("DistanceY", 2, 1, rear), "RearZ", "-" + F)
named(C("DistanceY", 6, 1, rear), "RearZLeft", "-" + F)
named(C("DistanceX", 2, 2, W), "HalfWidth", P + "LugShoulderHalfWidth")
named(C("DistanceX", 6, 1, -W), "HalfWidthLeft", "-" + P + "LugShoulderHalfWidth")
doc.recompute()
assert side.solve() == 0 and plan.solve() == 0, (side.solve(), plan.solve())
assert side.FullyConstrained and plan.FullyConstrained, (side.FullyConstrained, plan.FullyConstrained)


def extrude(name, sketch):
    result = doc.addObject("Part::Extrusion", name)
    result.Label = name
    result.Base = sketch
    result.DirMode = "Normal"
    result.LengthFwd = 44
    result.Solid = True
    sketch.Visibility = False
    result.Visibility = False
    return result


core = doc.addObject("Part::Cylinder", "RearBodyCore")
core.Label = "RearBodyCore"
core.setExpression("Radius", P + "FlangeDiameter / 2")
core.setExpression("Height", F + " + " + P + "LugReach + 1 mm")
core.setExpression("Placement.Base.z", "-(" + F + " + " + P + "LugReach + 1 mm)")
core.Visibility = False
blank = doc.addObject("Part::MultiCommon", "RearBlank")
blank.Label = "RearBlank"
blank.Shapes = [core, extrude("LugSide", side), extrude("LugPlan", plan)]
blank.Visibility = False

hole = doc.addObject("Part::Cylinder", "LugHoleTool")
hole.Label = "LugHoleTool"
hole.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation(App.Vector(1, 0, 0), -90))
hole.Height = 30
hole.setExpression("Radius", P + "LugHoleDiameter / 2")
hole.setExpression("Placement.Base.y", P + "LugCenterY - 15 mm")
hole.setExpression("Placement.Base.z", tip_center_z)
hole.Visibility = False
drilled = doc.addObject("Part::Cut", "RearDrilled")
drilled.Label = "RearDrilled"
drilled.Base = blank
drilled.Tool = hole
drilled.Visibility = False
doc.recompute()
assert drilled.Shape.isValid() and len(drilled.Shape.Solids) == 1


def normal_at(face, point):
    u, v = face.Surface.parameter(point)
    return face.normalAt(u, v)


def is_sharp(shape, edge):
    middle = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2)
    faces = shape.ancestorsOfType(edge, Part.Face)
    if len(faces) < 2 or faces[0].isSame(faces[1]):
        return False
    return normal_at(faces[0], middle).getAngle(normal_at(faces[1], middle)) > math.radians(4) and \
        abs(normal_at(faces[0], middle).getAngle(normal_at(faces[1], middle)) - math.pi) > math.radians(4)


def round_pass(base, name, radius, skip_hole):
    """Round every sharp edge the kernel accepts; one bad edge must not lose the rest."""
    shape = base.Shape
    hole_r = hole.Radius.Value
    hole_z = hole.Placement.Base.z
    kept = []
    left = []
    # Lug tip first: its tangent chains are the hardest, so they get the first try.
    ordered = sorted(enumerate(shape.Edges, 1), key=lambda item: item[1].BoundBox.ZMin)
    for index, edge in ordered:
        if edge.BoundBox.ZMin > -0.01 or not is_sharp(shape, edge):
            continue  # the z=0 end joins the chassis core
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

chassis_blank = labeled("ChassisBlank")
flange = labeled("RearFlange")
chassis_blank.Shapes = [labeled("ChassisCore"), body]
doc.recompute()
doc.removeObject(flange.Name)
doc.recompute()
bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
tip = labeled("ChassisFinal")
assert tip.Shape.isValid() and len(tip.Shape.Solids) == 1
doc.save()
App.closeDocument(doc.Name)
print("APPLY_LUG_CHECK=saved")

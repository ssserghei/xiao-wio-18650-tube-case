"""Flush cylinder: flange at sleeve diameter, bayonet at the rear, recessed disc at the USB end.

Replaces the key, the snap-on cap and the sleeve ridge. The O-ring becomes 1.5 mm section
so the bayonet lugs fit between it and the flange without lengthening the rear wall,
which keeps the antenna thread usable. Run after apply_open_cable_slot.py, then set_view_in_gui.py.
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
from BasicShapes import Shapes

TARGET = os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
P = "<<Parameters>>."
EDGE_RADIUS = 1.5
HOLE_EDGE_RADIUS = 0.8
LUG_ANGLES = (30, 150, 270)  # lug centres on the chassis, degrees
LUG_WIDTH = 22
SLOT_WIDTH = 25
TURN = 30                    # bayonet rotation
RIDGE_WIDTH = TURN - SLOT_WIDTH + 0  # shallow click ridge between entry and seat

doc = App.openDocument(TARGET)
assert not doc.getObjectsByLabel("ChassisBayonet"), "the flush body is already applied"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


def remove(*labels):
    for label in labels:
        for obj in doc.getObjectsByLabel(label):
            doc.removeObject(obj.Name)


sheet = labeled("Parameters")

# --- Old cap, ridge and key go first: their expressions use the rows cleared below.
remove("Shutter", "ShutterWindow", "ShutterSlits", "ShutterRibPlus", "ShutterRibMinus", "ShutterWindowTool",
       "ShutterSlitTools", "ShutterSlit30", "ShutterSlit90", "ShutterSlit150", "ShutterBlank", "ShutterBore",
       "ShutterBoreMain", "ShutterBoreLip", "ShutterBoreRamp", "ShutterOuter")
remove("SleeveFinal", "ShutterDetentTools", "DetentXPlus", "DetentXMinus", "DetentYPlus", "DetentYMinus",
       "SleeveRidged", "SnapRidge", "SnapRidgeSolid", "SnapRidgeBase", "SnapRidgeRamp", "SnapRidgeCore")
labeled("SleeveEntry").Base = labeled("Sleeve")
remove("SleeveKeyed", "KeyNotchTool")
pin_cut = labeled("ChassisPinSlots")
pin_cut.Base = labeled("ChassisORing")
remove("ChassisKeyed", "KeyTab")
doc.recompute()
for row in (65, 66, 67, 73, 74, 75, 76, 77, 78):
    sheet.clear("A%d" % row)
    sheet.clear("B%d" % row)

sheet.set("B17", "=SleeveOuterDiameter")
sheet.set("B62", "29.6 mm")
sheet.set("B63", "2 mm")
sheet.set("B64", "2.2 mm")
sheet.set("B82", "15 mm")
rows = [
    (98, "Начало выступа байонета, Z", "0.8 mm", "BayonetLugStartZ"),
    (99, "Толщина выступа байонета", "1.2 mm", "BayonetLugThickness"),
    (100, "Радиус выступа байонета", "16.6 mm", "BayonetLugRadius"),
    (101, "Радиус паза байонета", "16.7 mm", "BayonetGrooveRadius"),
    (102, "Радиус щелчка байонета", "16.45 mm", "BayonetRidgeRadius"),
    (103, "Удлинение гильзы за шасси", "3.2 mm", "SleeveFrontExtra"),
    (104, "Внутренний радиус бортика гильзы", "14.4 mm", "SleeveLipRadius"),
    (105, "Толщина бортика гильзы", "1.6 mm", "SleeveLipThickness"),
    (106, "Радиус фланца диска", "15.8 mm", "DiscFlangeRadius"),
    (107, "Радиус лицевой части диска", "14.2 mm", "DiscBossRadius"),
    (108, "Торцевой зазор диска", "0.2 mm", "DiscEndGap"),
    (109, "Толщина фланца диска", "1.3 mm", "DiscFlangeThickness"),
    (110, "Радиус фиксатора диска", "16.15 mm", "DiscRibRadius"),
    (111, "Радиус паза фиксатора в гильзе", "16.25 mm", "DiscNotchRadius"),
]
for row, text, value, alias in rows:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
doc.recompute()


def hide(obj):
    obj.Visibility = False
    return obj


def box(name, expressions):
    tool = doc.addObject("Part::Box", name)
    tool.Label = name
    for field, expression in expressions.items():
        tool.setExpression(field, expression)
    return hide(tool)


def cylinder(name, expressions, start=None, sweep=None):
    tool = doc.addObject("Part::Cylinder", name)
    tool.Label = name
    if sweep is not None:
        tool.Angle = sweep
        tool.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation(App.Vector(0, 0, 1), start))
    for field, expression in expressions.items():
        tool.setExpression(field, expression)
    return hide(tool)


def cut(name, base, tool):
    result = doc.addObject("Part::Cut", name)
    result.Label = name
    result.Base = base
    result.Tool = tool
    hide(base)
    return hide(result)


def fuse(name, shapes):
    result = doc.addObject("Part::MultiFuse", name)
    result.Label = name
    result.Shapes = shapes
    for shape in shapes:
        hide(shape)
    return hide(result)


# --- Rear body is rebuilt: the flange is smaller, so the fillet edges change.
chassis_blank = labeled("ChassisBlank")
drilled = labeled("RearDrilled")
chassis_blank.Shapes = [labeled("ChassisCore"), drilled]
remove("RearBody", "RearRounded")
doc.recompute()
hole = labeled("LugHoleTool")


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
    hide(base)
    hide(result)
    doc.recompute()
    assert result.Shape.isValid() and len(result.Shape.Solids) == 1, name
    print("edges", name, "rounded:", len(kept), "left sharp:", left)
    return result


body = round_pass(drilled, "RearRounded", EDGE_RADIUS, True)
body = round_pass(body, "RearBody", HOLE_EDGE_RADIUS, False)
chassis_blank.Shapes = [labeled("ChassisCore"), body]
doc.recompute()

# --- Bayonet lugs on the chassis, between the flange and the O-ring.
lugs = []
for angle in LUG_ANGLES:
    sector = cylinder("BayonetSector%d" % angle, {
        "Radius": P + "BayonetLugRadius",
        "Height": P + "BayonetLugThickness",
        "Placement.Base.z": P + "BayonetLugStartZ",
    }, angle - LUG_WIDTH / 2, LUG_WIDTH)
    core = cylinder("BayonetCore%d" % angle, {
        "Radius": "15 mm",
        "Height": P + "BayonetLugThickness + 1 mm",
        "Placement.Base.z": P + "BayonetLugStartZ - 0.5 mm",
    })
    lugs.append(cut("BayonetLug%d" % angle, sector, core))
bayonet = fuse("ChassisBayonet", [labeled("ChassisORing")] + lugs)
pin_cut.Base = bayonet

# --- Sleeve: longer, inner lip at the front, bayonet slots at the rear.
L = P + "SleeveLength"
labeled("Sleeve").setExpression("Height", L + " + " + P + "SleeveFrontExtra")
lip = Shapes.addTube(doc, "SleeveLip")
lip.Label = "SleeveLip"
for field, expression in {
    "OuterRadius": P + "SleeveInnerDiameter / 2 + 0.5 mm",
    "InnerRadius": P + "SleeveLipRadius",
    "Height": P + "SleeveLipThickness",
    "Placement.Base.z": L + " + " + P + "SleeveFrontExtra - " + P + "SleeveLipThickness",
}.items():
    lip.setExpression(field, expression)
hide(lip)
sleeve = fuse("SleeveLipped", [labeled("SleeveEntry"), lip])

slot_top = P + "BayonetLugStartZ + " + P + "BayonetLugThickness + 0.1 mm"
tools = []
for angle in LUG_ANGLES:
    tools.append(cylinder("BayonetSeat%d" % angle, {
        "Radius": P + "BayonetGrooveRadius",
        "Height": P + "BayonetLugThickness + 0.2 mm",
        "Placement.Base.z": P + "BayonetLugStartZ - 0.1 mm",
    }, angle - SLOT_WIDTH / 2, SLOT_WIDTH))
    tools.append(cylinder("BayonetRidge%d" % angle, {
        "Radius": P + "BayonetRidgeRadius",
        "Height": P + "BayonetLugThickness + 0.2 mm",
        "Placement.Base.z": P + "BayonetLugStartZ - 0.1 mm",
    }, angle - SLOT_WIDTH / 2 - RIDGE_WIDTH - 0.5, RIDGE_WIDTH + 1))
    tools.append(cylinder("BayonetEntry%d" % angle, {
        "Radius": P + "BayonetGrooveRadius",
        "Height": slot_top + " + 1 mm",
        "Placement.Base.z": "-1 mm",
    }, angle - TURN - SLOT_WIDTH / 2, SLOT_WIDTH))
sleeve = cut("SleeveBayonet", sleeve, fuse("BayonetSlotTools", tools))


def disc_z(extra="0 mm"):
    return L + " + " + P + "DiscEndGap + " + extra


notches = fuse("DiscNotchTools", [
    box("DiscNotchRight", {
        "Length": P + "DiscNotchRadius - 15 mm",
        "Width": "2.4 mm",
        "Height": P + "DiscFlangeThickness",
        "Placement.Base.x": "15 mm",
        "Placement.Base.y": "-1.2 mm",
        "Placement.Base.z": disc_z(),
    }),
    box("DiscNotchLeft", {
        "Length": P + "DiscNotchRadius - 15 mm",
        "Width": "2.4 mm",
        "Height": P + "DiscFlangeThickness",
        "Placement.Base.x": "-" + P + "DiscNotchRadius",
        "Placement.Base.y": "-1.2 mm",
        "Placement.Base.z": disc_z(),
    }),
])
final_sleeve = cut("SleeveFinal", sleeve, notches)
final_sleeve.Visibility = True

# --- Disc: trapped between the lip and the chassis, flush with the sleeve end.
flange = cylinder("DiscFlange", {
    "Radius": P + "DiscFlangeRadius",
    "Height": P + "DiscFlangeThickness",
    "Placement.Base.z": disc_z(),
})
boss = cylinder("DiscBoss", {
    "Radius": P + "DiscBossRadius",
    "Height": P + "SleeveFrontExtra - " + P + "DiscEndGap",
    "Placement.Base.z": disc_z(),
})
disc = fuse("DiscBlank", [flange, boss])

# Spring arcs: a curved slot behind each rib lets the rim flex into the sleeve notch.
slots = []
for name, centre in (("Right", 0), ("Left", 180)):
    outer = cylinder("DiscArcOuter" + name, {
        "Radius": "15 mm",
        "Height": P + "DiscFlangeThickness + 1 mm",
        "Placement.Base.z": disc_z("-0.5 mm"),
    }, centre - 30, 60)
    inner = cylinder("DiscArcInner" + name, {
        "Radius": "14.6 mm",
        "Height": P + "DiscFlangeThickness + 2 mm",
        "Placement.Base.z": disc_z("-1 mm"),
    })
    slots.append(cut("DiscArc" + name, outer, inner))
disc = cut("DiscSprung", disc, fuse("DiscArcTools", slots))

half_w = "(" + P + "USBPlugWidth / 2 + " + P + "USBPlugClearance)"
half_h = "(" + P + "USBPlugHeight / 2 + " + P + "USBPlugClearance)"
window = box("DiscWindowTool", {
    "Length": "2 * " + half_w,
    "Width": "2 * " + half_h,
    "Height": P + "SleeveFrontExtra + 2 mm",
    "Placement.Base.x": "-" + half_w,
    "Placement.Base.y": P + "USBCenterY - " + half_h,
    "Placement.Base.z": L + " - 1 mm",
})
disc = cut("DiscWindow", disc, window)
grip = box("DiscGripTool", {
    "Length": "2.6 mm",
    "Width": "10.5 mm",
    "Height": "2.2 mm",
    "Placement.Base.x": "-1.3 mm",
    "Placement.Base.y": "-13 mm",
    "Placement.Base.z": L + " + " + P + "SleeveFrontExtra - 1.2 mm",
})
disc = cut("DiscGrip", disc, grip)


def rib(name, x):
    return box(name, {
        "Length": P + "DiscRibRadius - 15.5 mm",
        "Width": "1.4 mm",
        "Height": P + "DiscFlangeThickness - 0.4 mm",
        "Placement.Base.x": x,
        "Placement.Base.y": "-0.7 mm",
        "Placement.Base.z": disc_z("0.2 mm"),
    })


shutter = fuse("Shutter", [disc, rib("DiscRibRight", "15.5 mm"), rib("DiscRibLeft", "-" + P + "DiscRibRadius")])
shutter.Visibility = True

doc.recompute()
bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
for label in ("ChassisFinal", "SleeveFinal", "Shutter", "BoardClamp"):
    shape = labeled(label).Shape
    assert shape.isValid() and len(shape.Solids) == 1, (label, shape.isValid(), len(shape.Solids))
doc.save()
App.closeDocument(doc.Name)
print("APPLY_FLUSH_CHECK=saved")

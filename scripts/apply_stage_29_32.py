"""Stages 29-32: wire riser, antenna, O-ring, key, USB plug window, sleeve, clamp, shutter.

Run with freecadcmd or inside FreeCAD. Edits and saves only xiao_wio_18650_tube_case.FCStd.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import FreeCAD as App
from BasicShapes import Shapes

TARGET = _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd")
P = "<<Parameters>>."

doc = App.openDocument(TARGET)
assert doc.getObjectsByLabel("ChassisWireChannel"), "stage 28 is missing"
assert not doc.getObjectsByLabel("ChassisFinal"), "stages 29-32 are already applied"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


sheet = labeled("Parameters")
sheet.set("B9", "6 mm")    # room behind the boards for wires and the coax
sheet.set("B49", "13 mm")  # wires must pass beside the antenna connector
rows = [
    (57, "Ширина подъёма проводов к платам", "8 mm", "WireRiserWidth"),
    (58, "Ось антенного разъёма, Y", "=-10 mm", "AntennaCenterY"),
    (59, "Отверстие антенного разъёма", "6.6 mm", "AntennaHoleDiameter"),
    (60, "Диаметр выемки под гайку антенны", "12 mm", "AntennaNutRecessDiameter"),
    (61, "Глубина выемки под гайку антенны", "3 mm", "AntennaNutRecessDepth"),
    (62, "Диаметр дна канавки кольца", "28.8 mm", "ORingGrooveDiameter"),
    (63, "Ширина канавки кольца", "2.7 mm", "ORingGrooveWidth"),
    (64, "Начало канавки кольца, Z", "1.2 mm", "ORingGrooveStartZ"),
    (65, "Ширина ключа шасси — гильза", "5 mm", "KeyWidth"),
    (66, "Длина ключа шасси — гильза", "4 mm", "KeyLength"),
    (67, "Зазор ключа", "0.2 mm", "KeyClearance"),
    (68, "Центр USB-C, Y", "=BoardThickness / 2 - 1.65 mm", "USBCenterY"),
    (69, "Ширина штекера USB-C", "12.5 mm", "USBPlugWidth"),
    (70, "Высота штекера USB-C", "6.5 mm", "USBPlugHeight"),
    (71, "Зазор вокруг штекера, на сторону", "0.4 mm", "USBPlugClearance"),
    (72, "Зазор прижимной вставки", "0.15 mm", "BoardClampGap"),
    (73, "Радиальный зазор шторки", "0.2 mm", "ShutterClearance"),
    (74, "Торцевой зазор шторки", "0.2 mm", "ShutterEndGap"),
    (75, "Толщина диска шторки", "2.5 mm", "ShutterPlateThickness"),
    (76, "Толщина юбки шторки", "1 mm", "ShutterSkirtThickness"),
    (77, "Высота защёлки шторки", "0.4 mm", "ShutterSnapHeight"),
    (78, "Глубина фиксатора шторки", "0.35 mm", "ShutterDetentDepth"),
]
for row, text, value, alias in rows:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
doc.recompute()


def configure(obj, name, expressions):
    obj.Label = name
    for field, expression in expressions.items():
        obj.setExpression(field, expression)
    obj.Visibility = False
    return obj


def box(name, expressions):
    return configure(doc.addObject("Part::Box", name), name, expressions)


def cylinder(name, expressions):
    return configure(doc.addObject("Part::Cylinder", name), name, expressions)


def cone(name, expressions):
    return configure(doc.addObject("Part::Cone", name), name, expressions)


def cut(name, base, tool):
    result = doc.addObject("Part::Cut", name)
    result.Label = name
    result.Base = base
    result.Tool = tool
    base.Visibility = False
    result.Visibility = False
    return result


def merge(kind, name, shapes):
    result = doc.addObject(kind, name)
    result.Label = name
    result.Shapes = shapes
    for shape in shapes:
        shape.Visibility = False
    result.Visibility = False
    return result


def fuse(name, shapes):
    return merge("Part::MultiFuse", name, shapes)


L = P + "SleeveLength"
SO = P + "SleeveOuterDiameter / 2"
half_plug_w = "(" + P + "USBPlugWidth / 2 + " + P + "USBPlugClearance)"
half_plug_h = "(" + P + "USBPlugHeight / 2 + " + P + "USBPlugClearance)"
pocket_end = "(" + P + "BoardPocketStart + " + P + "BoardPocketLength)"
above = P + "ChassisDiameter / 2 + 1 mm"

# --- Chassis ---------------------------------------------------------------
riser_start = P + "PositiveContactZ + " + P + "ContactTabPassThickness"
riser = box("WireRiserTool", {
    "Length": P + "WireRiserWidth",
    "Width": P + "BoardThickness / 2 - " + P + "WireChannelTopY + 1 mm",
    "Height": P + "BoardPocketStart - (" + riser_start + ") + 0.1 mm",
    "Placement.Base.x": "-" + P + "WireRiserWidth / 2",
    "Placement.Base.y": P + "WireChannelTopY - 1 mm",
    "Placement.Base.z": riser_start,
})
antenna_hole = cylinder("AntennaHoleTool", {
    "Radius": P + "AntennaHoleDiameter / 2",
    "Height": P + "FlangeThickness + " + P + "WireChannelStartZ + 1.5 mm",
    "Placement.Base.y": P + "AntennaCenterY",
    "Placement.Base.z": "-" + P + "FlangeThickness - 1 mm",
})
antenna_nut = cylinder("AntennaNutTool", {
    "Radius": P + "AntennaNutRecessDiameter / 2",
    "Height": P + "AntennaNutRecessDepth + 1 mm",
    "Placement.Base.y": P + "AntennaCenterY",
    "Placement.Base.z": "-" + P + "FlangeThickness - 1 mm",
})
groove = Shapes.addTube(doc, "ORingGrooveTool")
configure(groove, "ORingGrooveTool", {
    "OuterRadius": P + "ChassisDiameter / 2 + 1 mm",
    "InnerRadius": P + "ORingGrooveDiameter / 2",
    "Height": P + "ORingGrooveWidth",
    "Placement.Base.z": P + "ORingGrooveStartZ",
})
key = box("KeyTab", {
    "Length": "1.3 mm",
    "Width": P + "KeyWidth",
    "Height": P + "KeyLength + 1 mm",
    "Placement.Base.x": "-(" + P + "FlangeDiameter / 2 - 0.3 mm)",
    "Placement.Base.y": "-" + P + "KeyWidth / 2",
    "Placement.Base.z": "-1 mm",
})
plug_window = box("USBPlugWindowTool", {
    "Length": "2 * " + half_plug_w,
    "Width": above + " - " + P + "USBCenterY + " + half_plug_h,
    "Height": L + " - " + pocket_end + " + 1.1 mm",
    "Placement.Base.x": "-" + half_plug_w,
    "Placement.Base.y": P + "USBCenterY - " + half_plug_h,
    "Placement.Base.z": pocket_end + " - 0.1 mm",
})
tip = cut("ChassisRiser", labeled("ChassisWireChannel"), riser)
tip = cut("ChassisAntennaHole", tip, antenna_hole)
tip = cut("ChassisAntennaNut", tip, antenna_nut)
tip = cut("ChassisORing", tip, groove)
tip = fuse("ChassisKeyed", [tip, key])
tip = cut("ChassisFinal", tip, plug_window)
tip.Visibility = True

# --- Sleeve ----------------------------------------------------------------
snap_z = L + " - 5 mm"
key_notch = box("KeyNotchTool", {
    "Length": P + "FlangeDiameter / 2 + 1 mm - 16.7 mm",
    "Width": P + "KeyWidth + 2 * " + P + "KeyClearance",
    "Height": P + "KeyLength + " + P + "KeyClearance + 1 mm",
    "Placement.Base.x": "-(" + P + "FlangeDiameter / 2 + 1 mm)",
    "Placement.Base.y": "-(" + P + "KeyWidth / 2 + " + P + "KeyClearance)",
    "Placement.Base.z": "-1 mm",
})
entry = cone("SleeveEntryTool", {
    "Radius1": P + "SleeveInnerDiameter / 2 + 0.5 mm",
    "Radius2": P + "SleeveInnerDiameter / 2",
    "Height": "0.5 mm",
})
ridge_bottom = cylinder("SnapRidgeBase", {
    "Radius": SO + " + " + P + "ShutterSnapHeight",
    "Height": "1 mm",
    "Placement.Base.z": snap_z,
})
ridge_ramp = cone("SnapRidgeRamp", {
    "Radius1": SO + " + " + P + "ShutterSnapHeight",
    "Radius2": SO,
    "Height": "1 mm",
    "Placement.Base.z": snap_z + " + 1 mm",
})
ridge_core = cylinder("SnapRidgeCore", {
    "Radius": SO + " - 0.5 mm",
    "Height": "3 mm",
    "Placement.Base.z": snap_z + " - 0.5 mm",
})
ridge = cut("SnapRidge", fuse("SnapRidgeSolid", [ridge_bottom, ridge_ramp]), ridge_core)


def detent(name, x, y, length, width):
    return box(name, {
        "Length": length,
        "Width": width,
        "Height": "4 mm",
        "Placement.Base.x": x,
        "Placement.Base.y": y,
        "Placement.Base.z": L + " - 3 mm",
    })


inner_r = SO + " - " + P + "ShutterDetentDepth"
depth = P + "ShutterDetentDepth + 1 mm"
detents = fuse("ShutterDetentTools", [
    detent("DetentXPlus", inner_r, "-1.1 mm", depth, "2.2 mm"),
    detent("DetentXMinus", "-(" + SO + " + 1 mm)", "-1.1 mm", depth, "2.2 mm"),
])  # two stops, 180 degrees apart: at 90 degrees a window corner still overlaps the port
sleeve = cut("SleeveKeyed", labeled("Sleeve"), key_notch)
sleeve = cut("SleeveEntry", sleeve, entry)
sleeve = fuse("SleeveRidged", [sleeve, ridge])
sleeve = cut("SleeveFinal", sleeve, detents)
sleeve.Visibility = True

# --- Board clamp -----------------------------------------------------------
g = P + "BoardClampGap"
body_y = P + "BoardThickness / 2 + 0.1 mm"
clamp_body = box("ClampBody", {
    "Length": P + "BoardPocketWidth - 2 * " + g,
    "Width": above + " - (" + body_y + ")",
    # Stops short of the USB mouth so the plug body can seat against the connector.
    "Height": P + "BoardLength + " + P + "BoardClearance - " + g + " - 0.1 mm",
    "Placement.Base.x": "-(" + P + "BoardPocketWidth / 2 - " + g + ")",
    "Placement.Base.y": body_y,
    "Placement.Base.z": P + "BoardPocketStart + " + g,
})
tongue_y = P + "USBCenterY + " + half_plug_h + " + " + g
clamp_tongue = box("ClampTongue", {
    "Length": "2 * " + half_plug_w + " - 2 * " + g,
    "Width": above + " - (" + tongue_y + ")",
    "Height": L + " - " + pocket_end + " + 1 mm + " + g,
    "Placement.Base.x": "-(" + half_plug_w + " - " + g + ")",
    "Placement.Base.y": tongue_y,
    "Placement.Base.z": pocket_end + " - 1 mm - " + g,
})
clamp_core = cylinder("ClampCore", {
    "Radius": P + "ChassisDiameter / 2",
    "Height": L,
})
clamp = merge("Part::MultiCommon", "BoardClamp", [fuse("ClampBlank", [clamp_body, clamp_tongue]), clamp_core])
clamp.Visibility = True

# --- Shutter ---------------------------------------------------------------
c = P + "ShutterClearance"
snap = P + "ShutterSnapHeight"
skirt_inner = SO + " + " + snap + " + " + c  # the skirt has to clear the sleeve ridge
lip_inner = SO + " + " + c + " / 2"          # the lip hooks behind that ridge
outer = cylinder("ShutterOuter", {
    "Radius": skirt_inner + " + " + P + "ShutterSkirtThickness",
    "Height": "7 mm + " + P + "ShutterEndGap + " + P + "ShutterPlateThickness",
    "Placement.Base.z": L + " - 7 mm",
})
bore_main = cylinder("ShutterBoreMain", {
    "Radius": skirt_inner,
    "Height": "5.1 mm + " + P + "ShutterEndGap",
    "Placement.Base.z": L + " - 5.1 mm",
})
bore_lip = cylinder("ShutterBoreLip", {
    "Radius": lip_inner,
    "Height": "1.1 mm",
    "Placement.Base.z": L + " - 6.1 mm",
})
bore_ramp = cone("ShutterBoreRamp", {
    "Radius1": skirt_inner,
    "Radius2": lip_inner,
    "Height": "1 mm",
    "Placement.Base.z": L + " - 7.05 mm",
})
blank = cut("ShutterBlank", outer, fuse("ShutterBore", [bore_main, bore_lip, bore_ramp]))

slits = []
for angle in (30, 90, 150):
    slit = doc.addObject("Part::Box", "ShutterSlit%d" % angle)
    slit.Label = "ShutterSlit%d" % angle
    slit.Length = 44
    slit.Width = 1
    rotation = App.Rotation(App.Vector(0, 0, 1), angle)
    slit.Placement = App.Placement(rotation.multVec(App.Vector(-22, -0.5, 0)), rotation)
    slit.setExpression("Height", "7 mm")
    slit.setExpression("Placement.Base.z", L + " - 8 mm")
    slit.Visibility = False
    slits.append(slit)
window = box("ShutterWindowTool", {
    "Length": "2 * " + half_plug_w,
    "Width": "2 * " + half_plug_h,
    "Height": P + "ShutterPlateThickness + " + P + "ShutterEndGap + 2 mm",
    "Placement.Base.x": "-" + half_plug_w,
    "Placement.Base.y": P + "USBCenterY - " + half_plug_h,
    "Placement.Base.z": L + " - 1 mm",
})


rib_length = "(" + P + "ShutterDetentDepth + " + snap + " + " + c + " + 0.3 mm)"


def rib(name, x):
    return box(name, {
        "Length": rib_length,
        "Width": "1.4 mm",
        "Height": "1.3 mm",
        "Placement.Base.x": x,
        "Placement.Base.y": "-0.7 mm",
        "Placement.Base.z": L + " - 2.8 mm",
    })


rib_inner = SO + " - " + P + "ShutterDetentDepth + 0.1 mm"
rib_plus = rib("ShutterRibPlus", rib_inner)
rib_minus = rib("ShutterRibMinus", "-(" + rib_inner + " + " + rib_length + ")")
shutter = cut("ShutterSlits", blank, fuse("ShutterSlitTools", slits))
shutter = cut("ShutterWindow", shutter, window)
shutter = fuse("Shutter", [shutter, rib_plus, rib_minus])
shutter.Visibility = True

doc.recompute()
bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
doc.save()
App.closeDocument(doc.Name)
print("APPLY_STAGE_29_32_CHECK=saved")

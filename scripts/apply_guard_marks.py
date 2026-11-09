"""Reverse-battery guard, roomier spring, finger notch, polarity and lock marks, standing print.

- Battery compartment moves 0.5 mm away from the minus plate: spring gap 2.5 mm.
- A guard ring with a Ø10 hole stands in front of the plus plate. The plate's button sits
  0.5 mm behind the ring face, so a battery inserted backwards rests its flat minus end on
  the ring and cannot touch the plate; a button-top plus end reaches it through the hole.
- BoardGap grows to 6.5 mm so the wire riser behind the moved plate keeps its length.
- Rib lattice: 6 diamonds around instead of 11, rounded corners, 30 degree walls, whole
  cells only, so dirt does not pack into sharp corners.
- A finger scoop at the plus end of the battery window.
- Engraved "+" and "-" by the contacts, a lock dot and an insert dash on the flange and a
  line on the sleeve.
- The flange's sleeve face becomes a 45 degree cone and the sleeve end matches it, so the
  chassis prints standing on its USB end without supports under the flange.
Run with freecadcmd, then set_view_in_gui.py.
"""
import os as _os
import sys as _sys
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
_sys.path.insert(0, _os.path.join(_REPO, "scripts"))

import FreeCAD as App

import rebuild_static

TARGET = _os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
P = "<<Parameters>>."

doc = App.openDocument(TARGET)
assert not doc.getObjectsByLabel("PlusGuardHoleTool"), "this change is already applied"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


def hide(obj):
    obj.Visibility = False
    return obj


def cut(name, base, tool):
    result = doc.addObject("Part::Cut", name)
    result.Label = name
    result.Base = base
    result.Tool = tool
    return hide(result)


sheet = labeled("Parameters")
for row in (124, 125, 126):
    sheet.clear("A%d" % row)
    sheet.clear("B%d" % row)
for row, text, value, alias in [
    (124, "Рёбра: ромбов по окружности", "6", "RibStarts"),
    (125, "Рёбра: высота", "0.8 mm", "RibHeight"),
    (126, "Рёбра: ширина у основания", "3 mm", "RibWidth"),
    (127, "Утопление кнопки плюса за упором", "0.5 mm", "PlusContactRecess"),
    (128, "Отверстие упора плюса", "10 mm", "PlusGuardHoleDiameter"),
    (129, "Радиус выемки под палец", "7 mm", "FingerNotchRadius"),
    (130, "Глубина конуса шва грибок — гильза", "1.9 mm", "SeamConeDepth"),
    (131, "Рёбра: уклон стенок ячейки, градусы", "30", "RibDraft"),
    (132, "Рёбра: радиус углов ячейки", "2.5 mm", "RibCornerRadius"),
    (133, "Канал кнопки плюсовой пластины, ширина", "7 mm", "PlusBumpChannelWidth"),
]:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
sheet.set("B5", "10.5 mm")    # RearSpace: the compartment moves 0.5 mm away from the minus plate
sheet.set("B40", "2.5 mm")    # SpringWorkingHeight keeps the minus plate where it is
sheet.set("B9", "6.5 mm")     # BoardGap: keeps the wire riser about as long as before
sheet.set("B43", "=RearSpace + BatteryLength + BatteryEndClearance + PlusContactRecess + PositiveButtonHeight")
doc.recompute()

# --- Plus contact: the battery pocket end is the guard ring. Behind it, a Ø10 hole for the
# battery's button and a channel for the plate's own bump, which slides down from the top.
pocket_end = P + "RearSpace + " + P + "BatteryLength + " + P + "BatteryEndClearance"
hole = doc.addObject("Part::Cylinder", "PlusGuardHoleTool")
hole.Label = "PlusGuardHoleTool"
for field, expression in {
    "Radius": P + "PlusGuardHoleDiameter / 2",
    "Height": P + "PositiveContactZ - (" + pocket_end + ") + 0.25 mm",
    "Placement.Base.y": P + "BatteryCenterY",
    "Placement.Base.z": pocket_end + " - 0.2 mm",
}.items():
    hole.setExpression(field, expression)
hide(hole)
channel = doc.addObject("Part::Box", "PlusBumpChannelTool")
channel.Label = "PlusBumpChannelTool"
for field, expression in {
    "Length": P + "PlusBumpChannelWidth",
    "Width": P + "ChassisDiameter / 2 + 1 mm - " + P + "BatteryCenterY",
    "Height": P + "PositiveButtonHeight + 0.1 mm",
    "Placement.Base.x": "-" + P + "PlusBumpChannelWidth / 2",
    "Placement.Base.y": P + "BatteryCenterY",
    "Placement.Base.z": P + "PositiveContactZ - " + P + "PositiveButtonHeight - 0.05 mm",
}.items():
    channel.setExpression(field, expression)
hide(channel)
guard = doc.addObject("Part::MultiFuse", "PlusGuardTool")
guard.Label = "PlusGuardTool"
guard.Shapes = [hole, channel]
hide(guard)
face_cut = labeled("ChassisPositiveFace")
old_face = face_cut.Tool
face_cut.Tool = guard
doc.recompute()
if old_face.InList == []:
    doc.removeObject(old_face.Name)

# --- Finger scoop at the plus end of the battery window (cylinder across X), down to the axis.
scoop = doc.addObject("Part::Cylinder", "FingerNotchTool")
scoop.Label = "FingerNotchTool"
scoop.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation(App.Vector(0, 1, 0), 90))
scoop.Height = 40
for field, expression in {
    "Radius": P + "FingerNotchRadius",
    "Placement.Base.x": "-20 mm",
    "Placement.Base.y": P + "BatteryCenterY + " + P + "FingerNotchRadius",
    "Placement.Base.z": pocket_end + " - " + P + "FingerNotchRadius",
}.items():
    scoop.setExpression(field, expression)
hide(scoop)

rebuild_static.rebuild_marks(doc)  # creates ChassisMarkTool and SleeveMarkTool
final = labeled("ChassisFinal")
tip = cut("ChassisFingerNotch", final.Base, scoop)
tip = cut("ChassisMarks", tip, doc.getObject("ChassisMarkTool"))
final.Base = tip

# --- 45 degree seam cone on the flange, matching cone on the sleeve end.
outer = doc.addObject("Part::Cylinder", "SeamConeOuter")
outer.Label = "SeamConeOuter"
outer.setExpression("Radius", P + "FlangeDiameter / 2 + 1 mm")
outer.setExpression("Height", P + "SeamConeDepth")
outer.setExpression("Placement.Base.z", "-" + P + "SeamConeDepth")
cone = doc.addObject("Part::Cone", "SeamConeKeep")
cone.Label = "SeamConeKeep"
cone.setExpression("Radius1", P + "ChassisDiameter / 2 + " + P + "SeamConeDepth")
cone.setExpression("Radius2", P + "ChassisDiameter / 2")
cone.setExpression("Height", P + "SeamConeDepth")
cone.setExpression("Placement.Base.z", "-" + P + "SeamConeDepth")
seam_tool = cut("SeamConeTool", hide(outer), hide(cone))
bore = labeled("ChassisBore")
flange_cut = cut("ChassisSeamCone", bore.Base, seam_tool)
bore.Base = flange_cut

ring_outer = doc.addObject("Part::Cylinder", "SleeveConeOuter")
ring_outer.Label = "SleeveConeOuter"
ring_outer.setExpression("Radius", P + "FlangeDiameter / 2")
ring_outer.setExpression("Height", P + "SeamConeDepth")
ring_outer.setExpression("Placement.Base.z", "-" + P + "SeamConeDepth")
ring_inner = doc.addObject("Part::Cone", "SleeveConeInner")
ring_inner.Label = "SleeveConeInner"
ring_inner.setExpression("Radius1", P + "ChassisDiameter / 2 + 0.1 mm + " + P + "SeamConeDepth")
ring_inner.setExpression("Radius2", P + "ChassisDiameter / 2 + 0.1 mm")
ring_inner.setExpression("Height", P + "SeamConeDepth")
ring_inner.setExpression("Placement.Base.z", "-" + P + "SeamConeDepth")
ring = cut("SleeveConeRing", hide(ring_outer), hide(ring_inner))
lipped = labeled("SleeveLipped")
lipped.Shapes = list(lipped.Shapes) + [ring]

# --- Sleeve lock line after the crest fillet.
rim = doc.getObject("SleeveRibRim")
rim.Label = "SleeveRibRim"
marked = doc.addObject("Part::Cut", "SleeveMarked")
marked.Base = rim
marked.Tool = doc.getObject("SleeveMarkTool")
marked.Label = "SleeveFinal"
rim.Visibility = False
marked.Visibility = True
doc.recompute()

# --- Everything static follows the new sheet.
rebuild_static.rebuild_all(doc, rear_fillets=False)

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
for label in ("ChassisFinal", "SleeveFinal", "Shutter", "BoardClamp"):
    part = labeled(label).Shape
    assert part.isValid() and len(part.Solids) == 1, (label, part.isValid(), len(part.Solids))
rebuild_static.save(doc)
App.closeDocument(doc.Name)
print("APPLY_GUARD_CHECK=saved")

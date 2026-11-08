"""After the first prototype: thin antenna wall, snug antenna seat, hex pocket, full-width wire niche.

- The wall clamped between the jack's hex flange and its nut becomes 2 mm, so the antenna
  screws all the way down.
- The outer recess is sized for the antenna base (Ø9.56 mm measured) to sit slightly tight.
- The jack's hex flange sits 1 mm deep in a hex pocket, so it cannot turn while the nut is tightened.
- Below the channel ceiling the chassis is opened across its full width for easy wiring.
Run with freecadcmd, then set_view_in_gui.py.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)

import FreeCAD as App

TARGET = _os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
P = "<<Parameters>>."

doc = App.openDocument(TARGET)
assert not doc.getObjectsByLabel("ChassisWireNiche"), "this change is already applied"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


sheet = labeled("Parameters")
rows = [
    (116, "Стенка под гайкой антенного разъёма", "2 mm", "AntennaWallThickness"),
    (117, "Глубина шестигранника фланца разъёма", "1 mm", "AntennaHexDepth"),
    (118, "Шестигранник фланца, под ключ, с зазором", "8.2 mm", "AntennaHexAcrossFlats"),
    (119, "Диаметр основания антенны (замер)", "9.56 mm", "AntennaBaseDiameter"),
]
for row, text, value, alias in rows:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
# Printed holes come out about 0.1-0.15 mm small: +0.15 mm gives a slightly tight fit.
sheet.set("B60", "=AntennaBaseDiameter + 0.15 mm")
sheet.set("B61", "=FlangeThickness + WireChannelStartZ - AntennaHexDepth - AntennaWallThickness")
doc.recompute()


def hide(obj):
    obj.Visibility = False
    return obj


def cut(name, base, tool):
    result = doc.addObject("Part::Cut", name)
    result.Label = name
    result.Base = base
    result.Tool = tool
    hide(base)
    return hide(result)


# Hex pocket on the inner face. Flats point up and down: a corner at the bottom would
# almost reach the O-ring groove.
hex_tool = doc.addObject("Part::Prism", "AntennaHexTool")
hex_tool.Label = "AntennaHexTool"
hex_tool.Polygon = 6
for field, expression in {
    "Circumradius": P + "AntennaHexAcrossFlats / sqrt(3)",
    "Height": P + "AntennaHexDepth + 0.5 mm",
    "Placement.Base.y": P + "AntennaCenterY",
    "Placement.Base.z": P + "WireChannelStartZ - " + P + "AntennaHexDepth",
}.items():
    hex_tool.setExpression(field, expression)
hide(hex_tool)

niche_tool = doc.addObject("Part::Box", "WireNicheTool")
niche_tool.Label = "WireNicheTool"
outside = P + "ChassisDiameter / 2 + 1 mm"
for field, expression in {
    "Length": "2 * (" + outside + ")",
    "Width": P + "WireChannelTopY + " + outside,
    "Height": P + "BoardPocketStart - " + P + "WireChannelStartZ",
    "Placement.Base.x": "-(" + outside + ")",
    "Placement.Base.y": "-(" + outside + ")",
    "Placement.Base.z": P + "WireChannelStartZ",
}.items():
    niche_tool.setExpression(field, expression)
hide(niche_tool)

final = labeled("ChassisFinal")
tip = cut("ChassisAntennaHex", final.Base, hex_tool)
tip = cut("ChassisWireNiche", tip, niche_tool)
final.Base = tip
doc.recompute()

bad = [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
assert not bad, bad
assert final.Shape.isValid() and len(final.Shape.Solids) == 1
doc.save()
App.closeDocument(doc.Name)
print("APPLY_NICHE_CHECK=saved")

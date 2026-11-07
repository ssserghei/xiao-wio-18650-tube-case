"""Stage 28: raise the battery, open contact insertion paths, cut the wire channel.

Run with freecadcmd. Edits and saves only cad/xiao_wio_18650_tube_case.FCStd.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import FreeCAD as App

TARGET = _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd")
P = "<<Parameters>>."

doc = App.openDocument(TARGET)
assert not doc.getObjectsByLabel("ChassisWireChannel"), "stage 28 is already applied"
doc.Label = "xiao_wio_case_v2"


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


sheet = labeled("Parameters")
rows = [
    (47, "Зазор батарея — верх шасси", "0.25 mm", "BatteryTopGap"),
    (48, "Смещение оси батареи вверх, Y", "=ChassisDiameter / 2 - BatteryTopGap - BatteryDiameter / 2", "BatteryCenterY"),
    (49, "Ширина паза проводов, X", "10 mm", "WireChannelWidth"),
    (50, "Перемычка над пазом проводов", "2 mm", "WireChannelFloor"),
    (51, "Верх паза проводов, Y", "=BatteryCenterY - BatteryPocketDiameter / 2 - WireChannelFloor", "WireChannelTopY"),
    (52, "Начало паза проводов, Z", "=NegativeContactZ - NegativePocketDepth", "WireChannelStartZ"),
    (53, "Конец паза проводов, Z", "=BoardPocketStart + 1 mm", "WireChannelEndZ"),
    (54, "Ширина прохода ушка контакта", "4.5 mm", "ContactTabPassWidth"),
    (55, "Толщина прохода ушка контакта", "2.2 mm", "ContactTabPassThickness"),
    (56, "Ширина прорези кнопки плюса", "8 mm", "ButtonSlotWidth"),
]
for row, text, value, alias in rows:
    sheet.set("A%d" % row, text)
    sheet.set("B%d" % row, value)
    sheet.setAlias("B%d" % row, alias)
doc.recompute()

# Everything centred on the battery axis follows BatteryCenterY.
to_top = P + "ChassisDiameter / 2 + 1 mm - " + P + "BatteryCenterY"
labeled("Battery").setExpression("Placement.Base.y", P + "BatteryCenterY")
labeled("BatteryPocketTool").setExpression("Placement.Base.y", P + "BatteryCenterY")
window = labeled("BatteryWindowTool")
window.setExpression("Placement.Base.y", P + "BatteryCenterY")
window.setExpression("Width", to_top)
labeled("SpringEnvelope").setExpression("Placement.Base.y", P + "BatteryCenterY")
labeled("SpringPocketTool").setExpression("Placement.Base.y", P + "BatteryCenterY")
for dummy, tool, height in (
    ("NegativeContact", "NegativePocketTool", "NegativePlateHeight"),
    ("PositiveContact", "PositivePocketTool", "PositivePlateHeight"),
):
    labeled(dummy).setExpression("Placement.Base.y", P + "BatteryCenterY - " + P + height + " / 2")
    pocket = labeled(tool)
    pocket.setExpression("Placement.Base.y", P + "BatteryCenterY - (" + P + height + " / 2 + " + P + "ContactPocketClearance)")
    pocket.setExpression("Width", to_top + " + " + P + height + " / 2 + " + P + "ContactPocketClearance")


def box(name, expressions):
    tool = doc.addObject("Part::Box", name)
    tool.Label = name
    for field, expression in expressions.items():
        tool.setExpression(field, expression)
    tool.Visibility = False
    return tool


def cut(name, base, tool):
    result = doc.addObject("Part::Cut", name)
    result.Label = name
    result.Base = base
    result.Tool = tool
    base.Visibility = False
    result.Visibility = False
    return result


spring_width = P + "SpringDiameter + 2 * " + P + "SpringClearance"
spring_entry = box("SpringEntryTool", {
    "Length": spring_width,
    "Width": to_top,
    "Height": P + "SpringWorkingHeight",
    "Placement.Base.x": "-(" + spring_width + ") / 2",
    "Placement.Base.y": P + "BatteryCenterY",
    "Placement.Base.z": P + "NegativeContactZ",
})
button_slot = box("ButtonSlotTool", {
    "Length": P + "ButtonSlotWidth",
    "Width": to_top + " + " + P + "ButtonSlotWidth / 2",
    "Height": P + "PositiveContactZ - " + P + "RearSpace - " + P + "BatteryLength - " + P + "BatteryEndClearance + 0.2 mm",
    "Placement.Base.x": "-" + P + "ButtonSlotWidth / 2",
    "Placement.Base.y": P + "BatteryCenterY - " + P + "ButtonSlotWidth / 2",
    "Placement.Base.z": P + "RearSpace + " + P + "BatteryLength + " + P + "BatteryEndClearance - 0.1 mm",
})


def tab_pass(name, plate_height, start_z):
    pocket_bottom = P + "BatteryCenterY - " + P + plate_height + " / 2 - " + P + "ContactPocketClearance"
    return box(name, {
        "Length": P + "ContactTabPassWidth",
        "Width": pocket_bottom + " - " + P + "WireChannelTopY + 1.1 mm",
        "Height": P + "ContactTabPassThickness",
        "Placement.Base.x": "-" + P + "ContactTabPassWidth / 2",
        "Placement.Base.y": P + "WireChannelTopY - 1 mm",
        "Placement.Base.z": start_z,
    })


negative_pass = tab_pass("NegativeTabPassTool", "NegativePlateHeight", P + "NegativeContactZ - " + P + "NegativePocketDepth")
positive_pass = tab_pass("PositiveTabPassTool", "PositivePlateHeight", P + "PositiveContactZ")
channel = box("WireChannelTool", {
    "Length": P + "WireChannelWidth",
    "Width": P + "WireChannelTopY + " + P + "ChassisDiameter / 2 + 1 mm",
    "Height": P + "WireChannelEndZ - " + P + "WireChannelStartZ",
    "Placement.Base.x": "-" + P + "WireChannelWidth / 2",
    "Placement.Base.y": "-" + P + "ChassisDiameter / 2 - 1 mm",
    "Placement.Base.z": P + "WireChannelStartZ",
})

tip = labeled("ChassisUSBSlot")
for name, tool in (
    ("ChassisSpringEntry", spring_entry),
    ("ChassisButtonSlot", button_slot),
    ("ChassisNegativeTab", negative_pass),
    ("ChassisPositiveTab", positive_pass),
    ("ChassisWireChannel", channel),
):
    tip = cut(name, tip, tool)
tip.Visibility = True
doc.recompute()
assert not [o.Label for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
doc.save()
App.closeDocument(doc.Name)
print("APPLY_STAGE_28_CHECK=saved")

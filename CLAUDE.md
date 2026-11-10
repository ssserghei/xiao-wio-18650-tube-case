# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

A parametric FreeCAD 1.1.3 enclosure, not a software project. There is no build or test framework. The model is edited by Python scripts run with `freecadcmd`; the user also opens it in the FreeCAD GUI.

## Rules

- **Only `cad/xiao_wio_18650_tube_case.FCStd` is saved by scripts.** Check that FreeCAD is not showing this file before saving, or the GUI copy and the file diverge.
- **A `freecadcmd` save drops the GUI data** (colours, visibility). Afterwards run `freecad scripts/set_view_in_gui.py` from the repository root, with FreeCAD otherwise closed. Add new visible parts to its `STYLE` table.
- **Do not export STL or slice until the user says the model is finished.** `stl/` is stale after any model change until then.
- **Each change is a new `scripts/apply_*.py`** that edits and saves the document, followed by `scripts/check_stage_29_32.py`, `scripts/render_sections.py`, and a note in `docs/design-log-ru.md` (Russian, compact style).
- **Write to the user in Russian;** keep code, file names and README in English.

## Checks

```bash
freecadcmd scripts/check_stage_29_32.py
```

The exit code is always 0. A script passed only if its `<NAME>_CHECK=` line appears; a failure prints `Exception while processing file`. The marker can come before FreeCAD's banner, so don't `tail` the output.

- **Geometry only:** checks compare parts with envelope dummies, so never report them as a physical fit.
- **False failures:** bounding-box sweeps fail on cylinders and L-shaped parts, so `lift()` starts cylinders at the axis and the clamp is swept block by block. `BoundBox` overestimates filleted shapes; use `optimalBoundingBox(True, True)`.
- **Scratch copies first:** try risky edits on a copy by setting `XIAO_TARGET` to it.

## Model

- **Axes:** Z from the antenna end (negative Z: flange and lug) to the USB end. +Y is up, where the battery and boards go in. The battery axis is at `BatteryCenterY`; the board stack is placed by `WioBottomY` and `StackTopY`.
- **Parameters:** the `Parameters` spreadsheet, aliases on column B. Add new dimensions there, not as literals.
- **Printed parts:** `ChassisFinal`, `SleeveFinal`, `BoardClamp`, `Shutter`.
- **Dummies:** `Battery`, `Electronics`, `BoardStackModel` (CC0 model by zuberio; two PCB solids are invalid, test them by bounding box), `AntennaCable` (static spline), `BatteryButton` (measured plus button), `USBConnector` (the USB-C beyond the PCBs; the plug path starts at its tip), `NegativeContact`, `PositiveContact`, `SpringEnvelope`.
- **Chassis:** a linear chain of Part booleans ending in `ChassisFinal`; `ChassisBlank` fuses `ChassisCore` with the filleted `RearBody`.
- **Static shapes:** bayonet lugs and slots, `RibCage`, `AntennaCable`, `ChassisMarkTool` and `SleeveMarkTool` are computed, and the rear-body and front-crest fillets store edge numbers. `scripts/rebuild_static.py` rebuilds all of them from the sheet; other scripts import it (`rebuild_all`, `rebuild_rib_cage`, ...). Run it after any parameter change that touches them.
- **Finding objects:** internal names are generic; look objects up with `doc.getObjectsByLabel("...")[0]`.
- **Sleeve chain end:** `SleeveLipped` also fuses `SleeveConeRing`, the skirt over the flange cone. `SleeveNotched` → `SleeveRibbed` (fuse with `RibCage`) → `SleeveRibRim` (front crest fillet, by edge number) → object `SleeveMarked`, labelled `SleeveFinal` (lock line).
- **Chassis additions:** `ChassisSeamCone` sits between `ChassisBlank` and `ChassisBore`; `ChassisFingerNotch` and `ChassisMarks` sit right before `ChassisFinal`. `ChassisPositiveFace` cuts `PositiveFaceTool`, the open plate-sized window: no slot narrower than the printer can make, the plates are glued.
- **Lattice method:** cut disjoint windows from one shell; each window is a ruled loft between two rounded rhombi, wider outside (draft) and scaled with the radius. Sweeping crossing helical ribs took 16 minutes and gave an invalid solid.
- **Slow checks:** `check_stage_29_32.py` takes about 7 minutes, `rebuild_static.py` about 4, `apply_guard_marks.py` about 5; run them in the background.
- **History:** `scripts/apply_*.py` record the build in order and cannot be replayed on the finished file.

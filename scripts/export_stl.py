"""Export printable parts in print orientation and check each mesh (read-only for FCStd).

Settings: LinearDeflection 0.02 mm, AngularDeflection 10 degrees, millimetres.
"""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import json
import math

import FreeCAD as App
import Mesh
import MeshPart

ROOT = _REPO
doc = App.openDocument(_os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))

X = App.Vector(1, 0, 0)
ORIGIN = App.Vector(0, 0, 0)
# label -> (file suffix, rotation about X in degrees)
PARTS = {
    "ChassisFinal": ("chassis", 90),   # window up: contact slots stay vertical walls
    "SleeveFinal": ("sleeve", 180),    # standing, lip on the bed: no overhang, round bore
    "BoardClamp": ("board_clamp", 90), # flat pressing face on the bed
    "Shutter": ("shutter", 0),         # flange on the bed: face down leaves the flange unsupported
}


def is_clean(mesh):
    return mesh.isSolid() and not mesh.hasNonManifolds() and not mesh.hasSelfIntersections()


def repair(mesh):
    """Fillet corners can tessellate with tiny defects: fix them, report how many rounds it took."""
    rounds = 0
    while not is_clean(mesh) and rounds < 8:
        rounds += 1
        mesh.removeDuplicatedPoints()
        mesh.removeDuplicatedFacets()
        mesh.removeNonManifolds()
        mesh.removeNonManifoldPoints()
        mesh.fixSelfIntersections()
        mesh.fixDegenerations(0.0001)
        mesh.fillupHoles(400)
        mesh.harmonizeNormals()
    return rounds


report = {}
for label, (suffix, angle) in PARTS.items():
    shape = doc.getObjectsByLabel(label)[0].Shape.copy()
    if angle:
        shape.rotate(ORIGIN, X, angle)
    shape.translate(App.Vector(0, 0, -shape.BoundBox.ZMin))
    # Fillet corners tessellate differently at each setting: take the finest one that comes out clean.
    for linear, angular in ((0.02, 10), (0.03, 10), (0.05, 12), (0.015, 8), (0.08, 15)):
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=linear, AngularDeflection=math.radians(angular), Relative=False)
        rounds = repair(mesh)
        if is_clean(mesh):
            break
        print("MESH_TRY", label, linear, angular, mesh.isSolid(), mesh.hasNonManifolds(), mesh.hasSelfIntersections())
    assert is_clean(mesh), (label, mesh.isSolid(), mesh.hasNonManifolds(), mesh.hasSelfIntersections())
    error = abs(mesh.Volume - shape.Volume) / shape.Volume
    assert error < 0.005, (label, error)
    mesh.write(_os.path.join(ROOT, "stl", "xiao_wio_18650_tube_case_%s.stl" % suffix))
    b = mesh.BoundBox
    report[suffix] = {"facets": mesh.CountFacets, "size": [round(b.XLength, 2), round(b.YLength, 2), round(b.ZLength, 2)], "volume_error_pct": round(error * 100, 3), "repair_rounds": rounds, "deflection": linear}
App.closeDocument(doc.Name)
print("EXPORT_CHECK=" + json.dumps(report))

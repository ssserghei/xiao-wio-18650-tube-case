"""Rebuild every static shape from the Parameters sheet.

FreeCAD cannot keep these parametric on its own: helical lugs and slots, the rib lattice
and the antenna cable are computed shapes, and Part fillets store edge numbers. After
changing a parameter, run this script; it regenerates all of them and saves.

    freecadcmd scripts/rebuild_static.py          (whole model)

Other scripts import it and call rebuild_all(doc) or a single rebuild_* function.
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

LUG_ANGLES = (30, 150, 270)
REAR_BAND = 6.0
FRONT_BAND = 5.2
EDGE_RADIUS = 1.5
HOLE_EDGE_RADIUS = 0.8
V = App.Vector


def _labeled(doc, label):
    return doc.getObjectsByLabel(label)[0]


def _num(doc, alias):
    item = _labeled(doc, "Parameters").get(alias)
    return float(item.Value) if hasattr(item, "Value") else float(item)


def _feature(doc, name, shape):
    found = doc.getObject(name)
    if found is None:
        found = doc.addObject("Part::Feature", name)
        found.Label = name
        found.Visibility = False
    found.Shape = shape
    return found


# --- Bayonet -----------------------------------------------------------------
def _section(r0, r1, z0, z1, angle):
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    pts = [V(r * c, r * s, z) for r, z in ((r0, z0), (r1, z0), (r1, z1), (r0, z1), (r0, z0))]
    return Part.makePolygon(pts)


def _helical(r0, r1, a0, a1, z0, z1):
    steps = max(2, int(math.ceil((a1 - a0) / 4.0)))
    angles = [a0 + (a1 - a0) * i / steps for i in range(steps + 1)]
    return Part.makeLoft([_section(r0, r1, z0(a), z1(a), a) for a in angles], True, True)


def rebuild_bayonet(doc):
    width, turn, lead = _num(doc, "BayonetLugAngle"), _num(doc, "BayonetTurn"), _num(doc, "BayonetLead")
    low, thick = _num(doc, "BayonetLugStartZ"), _num(doc, "BayonetLugThickness")
    lug_r, groove_r, gap = _num(doc, "BayonetLugRadius"), _num(doc, "BayonetGrooveRadius"), _num(doc, "BayonetAxialClearance")
    slope = lead / turn
    slots = []
    for phi in LUG_ANGLES:
        lug_low = lambda a, phi=phi: low + slope * (a - phi)
        lug_high = lambda a, phi=phi: low + slope * (a - phi) + thick
        _labeled(doc, "BayonetLugShape%d" % phi).Shape = _helical(15.0, lug_r, phi - width / 2, phi + width / 2, lug_low, lug_high)
        far, near = phi + width / 2 + 2, phi - turn - width / 2 - 2
        ramp = _helical(15.5, groove_r, near, far, lambda a, f=lug_low: f(a) - gap, lambda a, f=lug_high: f(a) + gap)
        entry = _helical(15.5, groove_r, near, phi - turn + width / 2 + 2, lambda a: -1.0, lambda a, f=lug_high: f(a) + gap)
        slots += [ramp, entry]  # fusing the two lofts silently drops one of them
    _labeled(doc, "BayonetSlotShapes").Shape = Part.makeCompound(slots)
    for label in ("SleeveBayonet", "ChassisBayonet"):
        _labeled(doc, label).touch()  # a new Part::Feature shape does not mark its users
    doc.recompute()


# --- Rear-body fillets -------------------------------------------------------
def _normal_at(face, point):
    u, v = face.Surface.parameter(point)
    return face.normalAt(u, v)


def _is_sharp(shape, edge):
    middle = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2)
    faces = shape.ancestorsOfType(edge, Part.Face)
    if len(faces) < 2 or faces[0].isSame(faces[1]):
        return False
    angle = _normal_at(faces[0], middle).getAngle(_normal_at(faces[1], middle))
    return angle > math.radians(4) and abs(angle - math.pi) > math.radians(4)


def _round_edges(doc, base, fillet, radius, skip_hole):
    """Pick every sharp edge of the rear body the kernel can round; set them on `fillet`."""
    hole = _labeled(doc, "LugHoleTool")
    shape = base.Shape
    kept = []
    for index, edge in sorted(enumerate(shape.Edges, 1), key=lambda item: item[1].BoundBox.ZMin):
        if edge.BoundBox.ZMin > -0.01 or not _is_sharp(shape, edge):
            continue  # the z=0 end joins the chassis core
        middle = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2)
        if skip_hole and abs(math.hypot(middle.x, middle.z - hole.Placement.Base.z) - hole.Radius.Value) < 1e-4:
            continue
        try:
            trial = shape.makeFillet(radius, [shape.Edges[i - 1] for i in kept + [index]])
            if trial.isValid() and len(trial.Solids) == 1:
                kept.append(index)
        except Exception:
            pass
    fillet.Edges = [(i, radius, radius) for i in kept]
    doc.recompute()
    assert fillet.Shape.isValid() and len(fillet.Shape.Solids) == 1, fillet.Label


def rebuild_rear_fillets(doc):
    rounded, body = _labeled(doc, "RearRounded"), _labeled(doc, "RearBody")
    doc.recompute()
    _round_edges(doc, rounded.Base, rounded, EDGE_RADIUS, True)
    _round_edges(doc, rounded, body, HOLE_EDGE_RADIUS, False)


# --- Rib lattice on the sleeve -------------------------------------------------
def _rounded_rhombus(au, aw, rc):
    """Edges of a rhombus with half-diagonals au, aw and corner radius rc, as (u, w) points."""
    verts = [(au, 0.0), (0.0, aw), (-au, 0.0), (0.0, -aw)]
    corners = []
    for i, v in enumerate(verts):
        p, n = verts[i - 1], verts[(i + 1) % 4]
        d1 = (p[0] - v[0], p[1] - v[1])
        d2 = (n[0] - v[0], n[1] - v[1])
        l1, l2 = math.hypot(*d1), math.hypot(*d2)
        d1, d2 = (d1[0] / l1, d1[1] / l1), (d2[0] / l2, d2[1] / l2)
        half = math.acos(max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1]))) / 2
        bis = (d1[0] + d2[0], d1[1] + d2[1])
        lb = math.hypot(*bis)
        bis = (bis[0] / lb, bis[1] / lb)
        t = rc / math.tan(half)
        c = rc / math.sin(half)
        t_in = (v[0] + d1[0] * t, v[1] + d1[1] * t)
        t_out = (v[0] + d2[0] * t, v[1] + d2[1] * t)
        mid = (v[0] + bis[0] * (c - rc), v[1] + bis[1] * (c - rc))
        corners.append((t_in, mid, t_out))
    return corners


def _window_wire(corners, normal, tangent, depth, zc):
    to3d = lambda q: normal * depth + tangent * q[0] + V(0, 0, zc + q[1])
    edges = []
    for i, (t_in, mid, t_out) in enumerate(corners):
        edges.append(Part.Arc(to3d(t_in), to3d(mid), to3d(t_out)).toShape())
        edges.append(Part.LineSegment(to3d(t_out), to3d(corners[(i + 1) % 4][0])).toShape())
    return Part.Wire(edges)


def rebuild_rib_cage(doc):
    """Raised lattice: a shell with rounded, drafted diamond windows; whole windows only."""
    starts = int(round(_num(doc, "RibStarts")))
    height, rib = _num(doc, "RibHeight"), _num(doc, "RibWidth")
    draft, corner = _num(doc, "RibDraft"), _num(doc, "RibCornerRadius")
    radius = _num(doc, "SleeveOuterDiameter") / 2
    end = _num(doc, "SleeveLength") + _num(doc, "SleeveFrontExtra")
    crest = radius + height
    period = 2 * math.pi * radius / starts
    h0 = period / 2 - rib / 2 / math.sin(math.radians(45))       # half-diagonal at the floor
    grow = math.tan(math.radians(draft)) / math.sin(math.radians(45))
    d_out, d_in = crest + 0.5, radius - 2.0

    def sizes(d):  # u follows the radius (tangential walls stay drafted to the surface), w only drafts
        return h0 * d / radius + (d - radius) * grow, h0 + (d - radius) * grow

    au_o, aw_o = sizes(d_out)
    au_i, aw_i = sizes(d_in)
    rc_i = corner * min(au_i / au_o, aw_i / aw_o)
    outer, inner = _rounded_rhombus(au_o, aw_o, corner), _rounded_rhombus(au_i, aw_i, rc_i)
    reach = sizes(crest)[1]
    z_low, z_high = REAR_BAND, end - FRONT_BAND
    rows = int((z_high - z_low - 2 * reach) // (period / 2)) + 1
    first = (z_low + z_high) / 2 - (rows - 1) * period / 4
    windows = []
    for row in range(rows):
        zc = first + row * period / 2
        for k in range(starts):
            theta = 2 * math.pi * (k + (0.5 if row % 2 else 0.0)) / starts
            normal, tangent = V(math.cos(theta), math.sin(theta), 0), V(-math.sin(theta), math.cos(theta), 0)
            windows.append(Part.makeLoft([_window_wire(outer, normal, tangent, d_out, zc),
                                          _window_wire(inner, normal, tangent, d_in, zc)], True, True))
    # The shell overlaps the sleeve wall by 0.1 mm only: deeper, it would refill the bayonet
    # grooves (BayonetGrooveRadius) and shutter notches (DiscNotchRadius) cut before it.
    shell = Part.makeCylinder(crest, end).cut(Part.makeCylinder(radius - 0.1, end))
    cage = shell.cut(Part.makeCompound(windows)).removeSplitter()
    assert cage.isValid() and len(cage.Solids) == 1, "rib cage"
    _labeled(doc, "RibCage").Shape = cage
    _labeled(doc, "SleeveRibbed").touch()
    doc.recompute()
    rebuild_front_fillet(doc)


def rebuild_front_fillet(doc):
    """Front crest fillet: its edge number changes whenever the sleeve topology does."""
    crest = _num(doc, "SleeveOuterDiameter") / 2 + _num(doc, "RibHeight")
    doc.recompute()
    rim = doc.getObject("SleeveRibRim")
    shape = rim.Base.Shape
    top = max(v.Z for v in shape.Vertexes)
    edges = [i for i, e in enumerate(shape.Edges, 1)
             if abs(e.BoundBox.ZMin - top) < 1e-6 and abs(e.BoundBox.ZMax - top) < 1e-6
             and abs(math.hypot(e.valueAt(e.FirstParameter).x, e.valueAt(e.FirstParameter).y) - crest) < 1e-4]
    assert edges, "front crest edge not found"
    rim.Edges = [(i, 1.5, 1.5) for i in edges]
    doc.recompute()


# --- Antenna cable dummy ---------------------------------------------------------
def rebuild_cable(doc):
    pocket = _num(doc, "BoardPocketStart")
    x = -_num(doc, "UFLOffsetX")
    start_y = _num(doc, "WioBottomY") + _num(doc, "CableHeight")
    radius = _num(doc, "AntennaCableDiameter") / 2
    points = [V(x, start_y, pocket - 1.85), V(x, -5.6, 72.0), V(x, -7.6, 60.0), V(x * 0.6, -8.5, 35.0), V(0, -10.0, 13.0)]
    spline = Part.BSplineCurve()
    spline.interpolate(Points=points, InitialTangent=V(0, 0, -1), FinalTangent=V(0, 0, -1))
    span = spline.LastParameter - spline.FirstParameter
    worst = max(spline.curvature(spline.FirstParameter + span * i / 4000) for i in range(4001))
    _labeled(doc, "Parameters").set("B90", "%.2f mm" % (1 / worst))
    profile = Part.Wire([Part.makeCircle(radius, points[0], V(0, 0, -1))])
    _labeled(doc, "AntennaCable").Shape = Part.Wire([spline.toShape()]).makePipeShell([profile], True, True)
    doc.recompute()


# --- Marks ---------------------------------------------------------------------
def _box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def rebuild_marks(doc):
    """Polarity signs on both sides of the chassis, lock and insert marks on flange and sleeve."""
    r = _num(doc, "ChassisDiameter") / 2
    depth = 0.5
    z_plus = _num(doc, "PositiveContactZ") - 6.0
    z_minus = _num(doc, "NegativeContactZ") + 6.0
    signs = []
    for side in (-1, 1):
        x0, x1 = (-r - 1, -r + depth) if side < 0 else (r - depth, r + 1)
        signs.append(_box(x0, x1, -2.5, 2.5, z_minus - 0.6, z_minus + 0.6))           # minus
        signs.append(_box(x0, x1, -2.5, 2.5, z_plus - 0.6, z_plus + 0.6))             # plus, across
        signs.append(_box(x0, x1, -0.6, 0.6, z_plus - 2.5, z_plus + 2.5))             # plus, along
    # Flange: grooves across the rim, seen from the side and from behind.
    # One groove = locked position, two grooves = where the sleeve line goes on insertion.
    flange_r = _num(doc, "FlangeDiameter") / 2
    z0, z1 = -_num(doc, "FlangeThickness") - 1, -_num(doc, "SeamConeDepth") - 0.3
    grooves = [_box(-0.6, 0.6, flange_r - 0.6, flange_r + 2, z0, z1)]
    for offset in (-1.0, 1.0):
        dash = _box(offset - 0.4, offset + 0.4, flange_r - 0.6, flange_r + 2, z0, z1)
        dash.rotate(V(0, 0, 0), V(0, 0, 1), _num(doc, "BayonetTurn"))
        grooves.append(dash)
    _feature(doc, "ChassisMarkTool", Part.makeCompound(signs + grooves))
    crest = _num(doc, "SleeveOuterDiameter") / 2 + _num(doc, "RibHeight")
    _feature(doc, "SleeveMarkTool", _box(-0.6, 0.6, crest - depth, crest + 1, -0.8, REAR_BAND - 1.4))  # line
    for name in ("ChassisMarks", "SleeveMarked"):
        if doc.getObject(name) is not None:
            doc.getObject(name).touch()
    doc.recompute()


def rebuild_all(doc, rear_fillets=False):
    rebuild_bayonet(doc)
    if rear_fillets:
        rebuild_rear_fillets(doc)
    rebuild_rib_cage(doc)
    rebuild_cable(doc)
    rebuild_marks(doc)


def save(doc):
    for attempt in range(6):  # Windows sometimes still holds the file
        try:
            doc.save()
            return
        except OSError:
            if attempt == 5:
                raise
            time.sleep(2)


if __name__ == "__main__":
    target = _os.environ.get("XIAO_TARGET", _os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))
    document = App.openDocument(target)
    rebuild_all(document, rear_fillets=True)
    bad = [o.Label for o in document.Objects if "Invalid" in o.State or "Error" in o.State]
    assert not bad, bad
    save(document)
    App.closeDocument(document.Name)
    print("REBUILD_STATIC_CHECK=saved")

"""Draw section views of the saved v2 model into renders/sections.png (read-only)."""
import os as _os
try:
    _REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
except NameError:  # freecad.exe runs GUI scripts without __file__: start it from the repo root
    _REPO = _os.getcwd()
_REPO = _os.environ.get("XIAO_REPO", _REPO)
import FreeCAD as App
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath

ROOT = _REPO
doc = App.openDocument(_os.path.join(_REPO, "cad", "xiao_wio_18650_tube_case.FCStd"))


def labeled(label):
    return doc.getObjectsByLabel(label)[0]


def section_path(shape, normal, offset, axes):
    verts, codes = [], []
    for wire in shape.slice(normal, offset):
        points = wire.discretize(Deflection=0.02)
        verts += [(getattr(p, axes[0]), getattr(p, axes[1])) for p in points] + [(0, 0)]
        codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(points) - 1) + [MplPath.CLOSEPOLY]
    return MplPath(verts, codes) if verts else None


PARTS = (
    ("ChassisFinal", "#8a8f98", "#30343a", 1.0),
    ("SleeveFinal", "#b9c7d8", "#55657a", 1.0),
    ("BoardClamp", "#f09a30", "#8a5510", 1.0),
    ("Shutter", "#5a78d8", "#26408f", 1.0),
    ("Battery", "#6fb36f", "#2f6b2f", 0.55),
    ("BatteryButton", "#6fb36f", "#2f6b2f", 0.55),
    ("BoardStackModel", "#2f8f60", "#14523a", 0.9),
    ("NegativeContact", "#d04040", "#d04040", 1.0),
    ("PositiveContact", "#d04040", "#d04040", 1.0),
    ("SpringEnvelope", "#b060c0", "#703080", 0.7),
    ("AntennaCable", "#101010", "#101010", 1.0),
)


def draw(ax, normal, offset, axes, title, xlim, ylim):
    for label, face, edge, alpha in PARTS:
        path = section_path(labeled(label).Shape, normal, offset, axes)
        if path is not None:
            ax.add_patch(PathPatch(path, facecolor=face, edgecolor=edge, lw=0.5, alpha=alpha))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=9)
    ax.grid(True, lw=0.3, alpha=0.5)
    ax.tick_params(labelsize=7)


zn = App.Vector(0, 0, 1)
xn = App.Vector(1, 0, 0)
L = labeled("SleeveFinal").Shape.BoundBox.ZMax
figure = plt.figure(figsize=(14, 10), dpi=120)
grid = figure.add_gridspec(2, 5, height_ratios=[1.0, 1.25])
square = ((-20, 20), (-20, 20))
draw(figure.add_subplot(grid[0, 0]), zn, 1.4, "xy", "Z=1.4: bayonet lugs and slots", *square)
draw(figure.add_subplot(grid[0, 1]), zn, 45.0, "xy", "Z=45: battery + wire channel", *square)
draw(figure.add_subplot(grid[0, 2]), zn, 84.5, "xy", "Z=84.5: riser + antenna cable exit", *square)
draw(figure.add_subplot(grid[0, 3]), zn, 100.0, "xy", "Z=100: boards + clamp", *square)
draw(figure.add_subplot(grid[0, 4]), zn, L - 2.4, "xy", "Disc flange, spring arcs, USB window", *square)
draw(figure.add_subplot(grid[1, :]), xn, -3.6, "zy", "X=-3.6, through the coax: antenna end left, USB end right", (-22, 122), (-20, 20))
figure.tight_layout()
figure.savefig(_os.path.join(ROOT, "renders", "sections.png"))
plt.close(figure)

App.closeDocument(doc.Name)
print("RENDER_CHECK=ok")

"""Shared chart style so every figure in the repo looks like one system."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

# Categorical slots in fixed order (validated reference palette).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]

# Menu-engineering classes always use the same slot + marker (identity never colour-only).
CLASS_STYLE = {
    "STAR": {"color": SERIES[0], "marker": "*", "size": 140, "label": "Star"},
    "PLOWHORSE": {"color": SERIES[1], "marker": "o", "size": 60, "label": "Plowhorse"},
    "PUZZLE": {"color": SERIES[2], "marker": "D", "size": 55, "label": "Puzzle"},
    "DOG": {"color": SERIES[3], "marker": "s", "size": 55, "label": "Dog"},
}


def apply():
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "axes.titleweight": "bold",
        "axes.titlesize": 13,
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "text.color": INK,
        "font.size": 10,
        "legend.frameon": False,
        "figure.dpi": 110,
    })

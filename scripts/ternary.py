"""Discover computed phases or render a sourced ternary composition inventory."""

import argparse
from collections import defaultdict
from itertools import combinations
import json
from math import dist, isfinite, sqrt
import os
from pathlib import Path
import re

from pymatgen.core import Composition, Element

H = sqrt(3) / 2
BASES = {
    "atomic_ratio", "atomic_fraction", "atomic_percent",
    "mass_g", "mass_fraction", "mass_percent",
}
PHASE_STYLES = {
    "reported": ("s", "#235789", "Reported phase"),
    "computed": ("D", "#777777", "Computed candidate"),
    "user": ("s", "#555555", "User phase"),
}
POINT_STYLES = {
    "input": ("o", "#a74116", "Nominal input"),
    "output": ("^", "#007c83", "Measured output"),
    "sample": ("o", "#a74116", "Sample composition"),
}


def elements_for(symbols):
    elements = tuple(Element(symbol) for symbol in symbols)
    if len(elements) != 3 or len(set(elements)) != 3:
        raise ValueError("Provide three distinct elements")
    return elements


def fractions(record, elements, axis_basis):
    has_formula = "formula" in record
    if has_formula == ("values" in record):
        raise ValueError(f"{record['id']}: provide exactly one of formula or values")
    values = (Composition(record["formula"]).get_el_amt_dict()
              if has_formula else record["values"])
    basis = "atomic_ratio" if has_formula else record["basis"]
    outside = set(values) - {e.symbol for e in elements}
    if outside or basis not in BASES:
        raise ValueError(f"{record['id']}: unsupported basis or outside elements {sorted(outside)}")
    amounts = [float(values.get(e.symbol, 0)) for e in elements]
    if any(not isfinite(a) or a < 0 for a in amounts) or sum(amounts) <= 0:
        raise ValueError(f"{record['id']}: composition must be finite, nonnegative and nonzero")
    if axis_basis == "atomic" and basis.startswith("mass_"):
        amounts = [a / float(e.atomic_mass) for a, e in zip(amounts, elements)]
    if axis_basis == "mass" and basis.startswith("atomic_"):
        amounts = [a * float(e.atomic_mass) for a, e in zip(amounts, elements)]
    total = sum(amounts)
    if not isfinite(total) or total <= 0:
        raise ValueError(f"{record['id']}: invalid composition total")
    return tuple(a / total for a in amounts)


def xy(fractions):
    _, b, c = fractions
    return b + c / 2, H * c


def formula_label(formula):
    return re.sub(r"([0-9]+(?:\.[0-9]+)?)", lambda m: r"$_{" + m[1] + r"}$", formula)


def draw_grid(ax, elements, axis_basis):
    ax.plot([0, 1, .5, 0], [0, 0, H, 0], color="black", lw=1.2, zorder=1)
    unit = "at.%" if axis_basis == "atomic" else "wt.%"
    for pct in range(10, 100, 10):
        f = pct / 100
        segments = [
            ((f, 1-f, 0), (f, 0, 1-f)),
            ((1-f, f, 0), (0, f, 1-f)),
            ((1-f, 0, f), (0, 1-f, f)),
        ]
        for p, q in segments:
            x1, y1 = xy(p)
            x2, y2 = xy(q)
            ax.plot([x1, x2], [y1, y2], color="#dddddd", lw=.55, zorder=0)
        for comp, off, alignment in [
            ((f, 1-f, 0), (0, -8), "center"),
            ((0, f, 1-f), (7, 0), "left"),
            ((1-f, 0, f), (-7, 0), "right"),
        ]:
            ax.annotate(str(pct), xy(comp), xytext=off, textcoords="offset points",
                        ha=alignment, va="center", fontsize=8)
    for e, x, y, rotation in zip(elements, (.5, .80, .20), (-.074, .47, .47), (0, -60, 60)):
        ax.text(x, y, f"{e.symbol} ({unit})", rotation=rotation, ha="center", va="center")
    for e, x, y in zip(elements, (-.025, 1.025, .5), (-.025, -.025, H+.025)):
        ax.text(x, y, e.symbol, ha="center", fontsize=12)
    ax.set(xlim=(-.13, 1.13), ylim=(-.11, H+.09), aspect="equal")
    ax.set_axis_off()


def place_labels(fig, ax, labels, obstacles):
    from matplotlib.text import Text
    from matplotlib.transforms import Bbox

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    occupied = [item if isinstance(item, Bbox) else item.get_window_extent(renderer)
                for item in [*ax.texts, *obstacles]]
    for (position, preferred), names in labels.items():
        text = "\n".join(name[0] if isinstance(name, tuple) else name for name in names)
        alpha = max(name[1] if isinstance(name, tuple) else 1 for name in names)
        annotation = ax.annotate(text, position, xytext=preferred, alpha=alpha,
                                 textcoords="offset points", fontsize=7.5, zorder=6,
                                 arrowprops={"arrowstyle": "-", "color": "0.45", "lw": .55})
        candidates = [preferred]
        for distance in (7, 13, 22, 34, 50, 72, 100):
            candidates.extend((distance * dx, distance * dy) for dx, dy in
                              ((1, 1), (-1, 1), (1, -1), (-1, -1),
                               (1, 0), (-1, 0), (0, 1), (0, -1)))
        for offset in candidates:
            annotation.set_position(offset)
            annotation.set_ha("right" if offset[0] < 0 else "left")
            annotation.update_positions(renderer)
            bounds = Text.get_window_extent(annotation, renderer).padded(2)
            if (all(fig.bbox.contains(*corner) for corner in bounds.get_points())
                    and not any(bounds.overlaps(other) for other in occupied)):
                occupied.append(bounds)
                break
        else:
            annotation.remove()
            raise ValueError(f"Could not place label {text!r}. Adjust label_offset.")


def plot(data, output, *, include_theoretical=False):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch
    from matplotlib.transforms import Bbox

    if output.suffix.lower() != ".png":
        raise ValueError("Output must be a PNG")
    elements = elements_for(data["elements"])
    axis_basis = data.get("axis_basis", "atomic")
    if axis_basis not in ("atomic", "mass"):
        raise ValueError("axis_basis must be atomic or mass")
    phase_records = data.get("phases", [])
    excluded = {
        r["id"] for r in phase_records
        if r["kind"] == "computed" and r.get("theoretical") is not False
        and not (include_theoretical and r.get("theoretical") is True)
    }
    phases = {r["id"] for r in phase_records}
    records = {}
    for record in data.get("phases", []) + data.get("points", []):
        key = record["id"]
        if key in records:
            raise ValueError(f"Duplicate ID: {key}")
        records[key] = (record, xy(fractions(record, elements, axis_basis)))

    records = {key: value for key, value in records.items() if key not in excluded}

    fonts = {font.name for font in matplotlib.font_manager.fontManager.ttflist}
    if "Arial" in fonts:
        plt.rcParams.update({"font.family": "Arial", "mathtext.fontset": "custom",
                             "mathtext.rm": "Arial", "mathtext.it": "Arial:italic",
                             "mathtext.bf": "Arial:bold"})
    fig, ax = plt.subplots(figsize=(8, 8))
    draw_grid(ax, elements, axis_basis)
    for line in data.get("lines", []):
        kind = line.get("kind", "guide")
        if kind not in ("guide", "alkemade"):
            raise ValueError(f"Unknown line kind: {kind}")
        a, b = line["from"], line["to"]
        if kind == "alkemade" and (
            a not in phases or b not in phases or not line.get("source") or not line.get("conditions")
        ):
            raise ValueError("An Alkemade line requires two phase IDs, source and conditions")
        if a in excluded or b in excluded:
            continue
        x1, y1 = records[a][1]
        x2, y2 = records[b][1]
        if (x1, y1) == (x2, y2):
            raise ValueError("Line endpoints must have distinct compositions")
        ax.plot([x1, x2], [y1, y2], "--" if kind == "alkemade" else ":",
                color=line.get("color", "#555555"), lw=1.3, zorder=2,
                label=line.get("label", "Alkemade line" if kind == "alkemade" else "Composition guide"))
    fig.canvas.draw()
    styles = {}
    for key, (record, _) in records.items():
        marker, color, legend = (PHASE_STYLES[record["kind"]] if key in phases
                                 else POINT_STYLES[record.get("role", "sample")])
        color = record.get("color", color)
        alpha = 1
        if key in phases and record["kind"] == "computed":
            if record.get("theoretical") is True:
                alpha, legend = .2, "MP candidate without experimental match"
            elif record.get("theoretical") is False:
                legend = "MP candidate with experimental match"
            else:
                legend = "Computed candidate (provenance unknown)"
        styles[key] = (marker, color, legend, alpha)
    insets = []
    for arrow in data.get("arrows", []):
        if arrow["from"] in excluded or arrow["to"] in excluded:
            continue
        start, end = (records[arrow[key]][1] for key in ("from", "to"))
        if start == end:
            raise ValueError("Arrow endpoints coincide. Use a shared point label.")
        patch = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13,
                                shrinkA=4, shrinkB=4, linewidth=1.6, zorder=4,
                                color=arrow.get("color", "#333333"),
                                label=arrow.get("label", "Input → output"))
        pixel_distance = dist(*ax.transData.transform([start, end]))
        if pixel_distance * 72 / fig.dpi < 19 and len(insets) < 2:
            insets.append((arrow["from"], arrow["to"], patch.get_edgecolor(), patch.get_label()))
            continue
        if pixel_distance * 72 / fig.dpi < 19:
            patch.shrinkA = patch.shrinkB = 0
            patch.set_connectionstyle("arc3,rad=.65")
        ax.add_patch(patch)

    labels = defaultdict(list)
    for key, (record, position) in records.items():
        phase = key in phases
        if phase:
            if not record.get("source"):
                raise ValueError(f"{key}: record a phase source")
            label = record.get("label") or formula_label(record.get("formula", key))
        else:
            label = record.get("label", key)
        marker, color, legend, alpha = styles[key]
        ax.scatter(*position, marker=marker, color=color, s=26, zorder=5, label=legend, alpha=alpha,
                   facecolors="none" if legend == "Nominal input" else color)
        offset = tuple(record.get("label_offset", (5, 5)))
        if alpha < 1:
            label = (label, alpha)
        if label not in labels[position, offset]:
            labels[position, offset].append(label)
    ax.set_title(data.get("title", "–".join(e.symbol for e in elements) + " compositions"))
    handles, names = ax.get_legend_handles_labels()
    unique = dict(zip(names, handles))
    obstacles = [ax.title]
    if unique:
        obstacles.append(ax.legend(unique.values(), unique.keys(), loc="upper left",
                                   framealpha=1, facecolor="white", edgecolor="black",
                                   fancybox=False, fontsize=8))
    for index, (start_id, end_id, color, label) in enumerate(insets):
        start, end = records[start_id][1], records[end_id][1]
        height = .15
        inset = ax.inset_axes([.80, .99 - (index + 1) * height, .19, height - .023])
        x, y = [(a + b) / 2 for a, b in zip(start, end)]
        radius = dist(start, end) * .86
        inset.set(xlim=(x - radius, x + radius), ylim=(y - radius, y + radius),
                  xticks=[], yticks=[], title=f"{label} (detail)")
        inset.title.set_fontsize(7)
        inset.set_aspect("equal", adjustable="box")
        for key in (start_id, end_id):
            marker, marker_color, legend, alpha = styles[key]
            inset.scatter(*records[key][1], marker=marker, edgecolors=marker_color, zorder=3, alpha=alpha,
                          facecolors="none" if legend == "Nominal input" else marker_color)
        inset.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=11,
                                        shrinkA=4, shrinkB=4, color=color))
        obstacles.extend([inset, inset.title])
    fig.canvas.draw()
    marker_radius = 4 * fig.dpi / 72
    for _, position in records.values():
        x, y = ax.transData.transform(position)
        obstacles.append(Bbox.from_bounds(x - marker_radius, y - marker_radius,
                                          2 * marker_radius, 2 * marker_radius))
    place_labels(fig, ax, labels, obstacles)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, facecolor="white")
    plt.close(fig)


def discover(symbols, output):
    setup = "See references.md and https://docs.materialsproject.org/downloading-data/using-the-api/getting-started"
    try:
        from mp_api.client import MPRester
    except ImportError as exc:
        raise ValueError(f"Install the Materials Project client with python -m pip install mp-api. {setup}") from exc
    api_key = os.getenv("MP_API_KEY")
    if not api_key:
        raise ValueError(f"Set MP_API_KEY using the API key from your Materials Project dashboard. {setup}")

    original_order = [e.symbol for e in elements_for(symbols)]
    symbols = sorted(original_order)
    systems = ["-".join(pair) for pair in combinations(symbols, 2)] + ["-".join(symbols)]
    phases, counts = {}, {}
    with MPRester(api_key) as client:
        version = client.get_database_version()
        for system in systems:
            docs = client.materials.summary.search(
                chemsys=system, deprecated=False,
                fields=["material_id", "formula_pretty", "chemsys", "theoretical"],
            )
            found = set()
            for doc in docs:
                if doc.chemsys != system:
                    continue
                mid = str(doc.material_id)
                found.add(mid)
                phases[mid] = {
                    "id": mid, "formula": doc.formula_pretty,
                    "kind": "computed", "source": f"https://materialsproject.org/materials/{mid}",
                    "theoretical": doc.theoretical,
                }
            counts[system] = len(found)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "elements": original_order,
        "discovery": {"database": "Materials Project", "version": str(version), "record_counts": counts},
        "phases": list(phases.values()),
    }, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    render = commands.add_parser("plot")
    render.add_argument("input", type=Path)
    render.add_argument("output", type=Path)
    render.add_argument("--include-theoretical", action="store_true",
                        help="Include Materials Project candidates without an experimental match at 20%% opacity")
    survey = commands.add_parser("discover")
    survey.add_argument("elements", nargs=3)
    survey.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "plot":
            plot(json.loads(args.input.read_text(encoding="utf-8")), args.output,
                 include_theoretical=args.include_theoretical)
        else:
            discover(args.elements, args.output)
    except (ValueError, KeyError, ImportError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()

---
name: ternary-plotting-skill
description: Discover and plot reported or computed phases in a three-element chemical system, with optional sample points, Alkemade lines, and arrows from input to output compositions.
---

# Ternary plotting skill

1. Take three distinct element symbols in the requested order (left, right, top). Default to atomic percent. Set `axis_basis` to `mass` for weight percent. Default to ambient pressure (about 0.1 MPa) for discovered phases unless the user specifies otherwise. See the [pressure and phase selection criteria](references.md#select-phases-for-the-ternary).
2. Unless the user supplies the phase inventory or requests plotting only, search all three binary subsystems and the ternary system. The pure elements are already vertices. Add a sourced elemental phase record if a vertex needs a specific phase identity or an overlay endpoint. Start with [the assessed phase shortlist](references.md#select-phases-for-the-ternary), then use ICSD as the first database for targeted verification. Use Materials Project as a secondary database to cross-check coverage or find requested computed candidates. Report sources and gaps.
3. Save the plotted inventory and overlays in a JSON file. Use stable IDs and cite sources. Follow the [runnable example](example.json).
4. Run `python <skill-dir>/scripts/ternary.py plot INPUT.json OUTPUT.png` (Python 3.10+, Matplotlib and pymatgen). For an installed virtual environment, use `.venv/Scripts/python.exe` on Windows or `.venv/bin/python` on macOS/Linux. Deliver the PNG and input JSON. State which sources and subsystems were searched and any coverage gaps. Follow the user's image inspection preferences.

For Materials Project results, plot only compositions with an experimental structure match by default. Tell the user that theoretical entries are available at 20% opacity with `plot --include-theoretical`. Preserve all discovery records in the inventory.

If Materials Project discovery is unavailable, provide the [API setup steps](references.md#connect-materials-project) and offer to help verify the user's installation and connection.

## Compositions and overlays

- A phase or point takes a `formula` or a `values` dictionary and `basis`. Omitted elements have zero content. Bases are `atomic_ratio`, `atomic_fraction`, `atomic_percent`, `mass_g`, `mass_fraction`, and `mass_percent`. For compound precursor masses, convert to moles of formula units and sum their atomic contributions before plotting. Projection of outside elements requires the user's chosen projection rule.
- Add `lines` on request. For an Alkemade line, use two phase IDs plus `kind: alkemade`, a liquidus `source`, and `conditions`. Confirm the phases have adjacent primary crystallization fields in that source. If adjacency is unavailable, use `kind: guide` and tell the user what evidence is missing. A convex hull edge does not establish liquidus adjacency.
- For a reaction composition shift, mark the starting point with `role: input` and the characterized composition with `role: output`. Record the characterization method and whether it describes the bulk sample or a specific product phase when known. Use the point IDs as `from` and `to` to show the shift. Keep the measured coordinates and use a magnified detail when the endpoints are close. For identical endpoints use a shared point label.
- Label 10 through 90 in 10-point increments on each side. The pure-element vertices mark the endpoints. Use distinct markers for phases and sample points. A phase marker represents a composition. Plot homogeneity ranges, tie lines, or phase boundaries only with supporting data. Keep distinct polymorph IDs even when they share coordinates. The plotter tries `label_offset` first, then looks for a clear position. Use shorter labels or a numbered key if the plot is too dense.

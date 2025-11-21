# Disk Method Visualizer

Interactive cmu_graphics visualizer for the disk method: explore solids of revolution, adjust domains and slice counts, and see midpoint Riemann-sum volume approximations in real time.

This repository currently ships the trimmed **prelim** build. It keeps the MVC architecture and the educational core (Preset functions, disk volumes, animation), but purposefully omits the archived stretch features such as custom parsing, adaptive Simpson’s rule, and 3D previews. Everything described below reflects exactly what the code in this folder provides today.

## How to Run

1. Create a fresh virtual environment (optional but recommended).
2. Install the minimal dependency set:
   ```
   pip install -r requirements.txt
   ```
3. Launch the MVP application:
   ```
   python main.py
   ```

### Controls (current build)

- `← / →` or `A / D`: switch between the three preset functions.
- `[` and `]`: nudge the start or end of the integration domain.
- `{` and `}`: larger domain adjustments for quick framing.
- `+` / `-`: increase or decrease the number of slices.
- `Space`: toggle the rotation highlight animation.
- `R`: reset to the suggested domain and slice count for the active function.
- Mouse click inside the plot: focus the highlight on the nearest slice (and pause the animation).
- Mouse click outside the plot: toggle animation on/off.

That is the complete control surface for the prelim submission—there is intentionally no custom-expression entry, no tolerance controls, and no 3D toggle in this branch.

---

## Current Feature Set

- **Preset function library:** quadratic, sine bump, and circular arc selections, each with built-in recommended domains.
- **Disk-method volume estimate:** midpoint Riemann-sum approximation of \( \pi r^2 \Delta x \) across the active domain.
- **Slice visualization:** semi-transparent bars showing radius and width, derived directly from the numerical integration step.
- **Sidebar summary:** read-only display of the expression, domain, slice count, current volume estimate, animation status, and the latest status message.
- **Lightweight animation:** optional rotation indicator controlled purely through the model’s `is_animating` flag (no video playback or shell mode in this build).

## Architecture Snapshot (MVC)

- **`main.py`** – Registers the cmu_graphics callbacks and forwards every event to the controller. It holds no additional logic.
- **`mvp/controller.py`**
  - Initializes shared layout rectangles, color palette, and `AppState`.
  - Converts the supported keyboard/mouse events into model calls.
  - Keeps drag/release hooks as no-ops solely to satisfy cmu_graphics.
- **`mvp/model.py`**
  - Stores the compact `AppState` (function list, domain, slice count, animation flag, rotation angle, volume, status message).
  - Provides helpers to cycle functions, tweak domains/slice counts, toggle animation, and recompute the midpoint Riemann volume.
  - Supplies utilities for the view (curve samples, slice samples, projection-friendly data).
- **`mvp/view.py`**
  - Draws the background, ribbon, plot region, slices, curve, and sidebar using only cmu_graphics primitives.
  - Reads from `app.state` but never mutates it, preserving MVC separation.

## Numerical Approach

Only the **midpoint disk method** is implemented in this code drop:

1. Divide the current domain `[x_min, x_max]` into `n` uniform slices.
2. Evaluate the active function at each midpoint to obtain the slice radius.
3. Accumulate \( \pi r^2 \Delta x \) for the displayed volume estimate.
4. Reuse the same slice data for drawing the translucent bars in the view.

Future integrations (adaptive Simpson, relative-error comparisons, smart slice placement, etc.) live in the archived branch and will return after the prelim checkpoint.

## Near-Term Roadmap

| Phase | Focus |
| --- | --- |
| Prelim (current) | Minimal, mentor-reviewable build: preset functions, disk method, clean MVC separation, ~400 total LOC. |
| Post-prelim | Restore custom expression parser, advanced integration routines, convergence overlays, and 3D preview from the archive snapshot. |
| Final polish | UX cleanup, expanded documentation, and educator-facing scaffolding informed by feedback. |

## Module List

- `cmu_graphics==1.1.44`
- Python standard library: `math`, `dataclasses`, `typing`

No other dependencies are used in the running code at this time.

## Preliminary Code Status

- Total lines across `main.py` and `mvp/` are ~380, keeping the submission lightweight for the mentor review.
- Features implemented today: preset carousel, domain tuning, slice-count tuning, midpoint disk integration, clickable slice focus, sidebar summaries, and animation toggle.
- Features deliberately **not** present in this branch: custom functions, adaptive Simpson’s rule, error analysis, smart slices, shell mode, and 3D rendering (all preserved in `archive/` for later reintroduction).

---

## TP1 Proposal

### Project Description
**Name:** Equation-to-Motion — Solids of Revolution Lab  
**Goal:** deliver a teaching aid where students manipulate solids of revolution inside cmu_graphics. The prelim build showcases the foundation (preset curves, domain control, disk volumes), while the archived branch contains the expanded toolkit (custom expressions, adaptive methods, 3D preview) ready to return after mentor approval.

Key experiences across phases:
- **Prelim (current repo):** rotate among curated functions, adjust domains and slices, observe the midpoint disk approximation, and monitor a concise status sidebar.
- **Post-prelim (archived code):** add safe expression parsing, adaptive Simpson comparison, smart slice distributions, convergence plots, and pseudo-isometric previews—all already implemented but temporarily parked.

### Competitive Analysis
1. **Desmos / GeoGebra:** rich plotting but no per-slice disk animation or instantaneous volume readouts.
2. **3Blue1Brown / Khan Academy videos:** intuitive explanations yet non-interactive.
3. **Legacy Manim scripts:** good visuals yet slow iteration and not permitted before MVP.

This project blends Desmos-style sliders with 3B1B clarity inside a course-compliant cmu_graphics MVC app, letting students iterate quickly without leaving Python.

### Structural Plan (MVC Overview)
- **Entry point (`main.py`):** registers cmu_graphics callbacks and forwards them to the controller—no extra logic.
- **Controller (`mvp/controller.py`):**
  - Initializes layout, colors, and `AppState` during `app_started`.
  - Routes keyboard/mouse input to model helpers (cycle functions, adjust domain, adjust slices, toggle/reset animation).
  - Retains drag/release no-ops solely for API completeness.
- **Model (`mvp/model.py`):**
  - Defines `AppState` with compact fields (function list, domain, slices, animation flag, angle, volume, status).
  - Implements all mutations and recomputes the midpoint Riemann sum.
  - Supplies samples for the view to draw curves and slices.
- **View (`mvp/view.py`):**
  - Renders the background, ribbon, axes, slices, curve, and sidebar using cmu_graphics primitives.
  - Centralizes coordinate transforms so the UI updates smoothly as domains change.
  - Remains purely read-only with respect to `app.state`.

### Algorithmic Plan
1. **Midpoint Riemann Core** – complete and powering the current submission.
2. **Custom Function Parsing** – implemented in the archived branch via `ast` validation; to be reactivated once the prelim review concludes.
3. **Adaptive Simpson + Convergence Analysis** – likewise archived; produces tolerance-driven recommendations and comparison tables.
4. **3D Mesh + Smart Slices** – pseudo-isometric mesh with shading plus derivative-weighted slice distribution (both archived).

### Timeline Plan
| Date | Milestone |
| --- | --- |
| **Week 10 (Nov 8–14)** | Confirm scope, build MVC skeleton, seed preset functions, midpoint integration. |
| **Week 11 (Nov 15–21)** | Deliver trimmed prelim build (current repo state) and align documentation. |
| **Week 12 (Nov 22–28)** | Restore custom parser, adaptive Simpson workflow, and sidebar controls from archive. |
| **Week 13 (Nov 29–Dec 5)** | Re-enable 3D preview, smart slice heuristics, convergence overlays, shell mode. |
| **Week 14 (Dec 6–10)** | Polish UX, gather mentor feedback, finalize TP1+TP2 documentation. |

### Module List
- `cmu_graphics==1.1.44`
- Python standard library modules: `math`, `dataclasses`, `typing`
- Archived branch also relies on `ast`, `itertools`, and `functools` for the advanced planner; they will return with the fuller feature set.

### Preliminary Code Status (Expanded)
- Current repo holds ~380 LOC to satisfy the prelim requirement.
- Archived snapshot (see `archive/full-20251121/`) contains the ~1,800 LOC full build with custom parsing, adaptive integration, shell mode, and 3D previews.
- After mentor sign-off, the plan is to merge the archived modules back in, run targeted tests, and refresh this README again.

---

## Citations & Acknowledgements

- 3Blue1Brown for clear explanations of solids of revolution.
- cmu_graphics course notes for API references.

# Disk Method Visualizer

interactive cmu_graphics visualizer for the disk method: explore solids of revolution, adjust domains and slice counts, and see riemann-sum volume approximations in real time.

This repository now hosts an **interactive solids of revolution visualizer** that is fully compliant with the 15-112 term project pre-MVP rules:

- Built entirely with **cmu_graphics** and standard Python libraries
- Structured using the **Model–View–Controller (MVC)** pattern
- Runs locally with no external APIs, hardware, or disallowed frameworks

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

Controls inside the app:

- `← / →` (or `A / D`): switch between supported functions
- `[` and `]`: adjust the integration bounds
- `+ / -` or `↑ / ↓`: tune the number of slices in the Riemann sum
- `Space`: toggle the rotation highlight animation
- `V`: play a single 360° “video” rotation
- `R`: reset the current function to its suggested domain
- `Click` inside the plot: focus the rotation on a particular slice
- `N`: start typing your own function (`sin`, `cos`, `exp`, `sqrt`, …)
- `3`: toggle the 3D surface preview
- `Esc`: cancel custom-function entry
- `S`: toggle between disk and shell (y-axis) methods

---

## TP1 Proposal

### Project Description
**Name:** Equation-to-Motion — Solids of Revolution Lab  
**Goal:** Deliver a teaching aid where students *manipulate* solids of revolution inside cmu_graphics. The app highlights how changing a function, domain, or slice density alters the resulting volume, so learners can experiment before attempting formal proofs or hand calculations.

Key experiences:
- Library of starter functions (quadratic, trig, exponential) with suggested bounds.
- Custom-expression entry that compiles safely and immediately joins the function carousel.
- Visual feedback (2D slices + optional 3D mesh) tied to live numerical summaries.

### Competitive Analysis
1. **Desmos / GeoGebra:** both offer rich graphing and sliders, yet neither shows Riemann slices for volumes of revolution nor simulates slice-by-slice animation. Users must compute integrals separately.
2. **YouTube/3Blue1Brown / Khan Academy:** provide excellent conceptual visuals but remain passive. Students cannot tweak inputs or observe convergence interactively.
3. **Manim scripts (legacy project):** create cinematic renders, but authoring and re-rendering is slow, code-heavy, and violates the course’s “cmu_graphics only before MVP” rule.

This project combines the immediacy of Desmos sliders, the clarity of 3B1B visuals, and the step-by-step perspective of classroom demos—all within an MVC app that runs offline and encourages experimentation.

### Structural Plan (MVC Overview)
- **Entry point (`main.py`):** registers cmu_graphics callbacks (start, redraw, input). Holds no logic besides delegating to the controller.
- **Controller (`mvp/controller.py`):**
  - Initializes shared layout/colour constants at `app_started`.
  - Converts keyboard and mouse events into model function calls.
  - Maintains a cache of clickable button bounds for the sidebar.
- **Model (`mvp/model.py`):**
  - Stores `AppState` (functions, domain, slice count, animation flags, adaptive data).
  - Parses custom expressions via `ast`, compiles safe callables, and tracks recommended domains.
  - Implements numerical routines: midpoint Riemann sum, trapezoidal, Simpson, adaptive Simpson, convergence analysis, smart slice distribution, and shell/disk toggles.
- **View (`mvp/view.py`):**
  - Draws the background, axes, slices, 3D mesh, overlays, and sidebar widgets.
  - Uses helper functions for coordinate transforms, shading, and annotation.
  - Reads only from `app.state`; all mutations happen in the model.

### Algorithmic Plan
1. **Midpoint Riemann Core**
   - Divide `[a, b]` into `n` slices.
   - Evaluate `f` at each midpoint, accumulate \( \pi f(x)^2 \Delta x \).
   - Cache slice geometry for the animation/highlight logic.
2. **Custom Function Parsing**
   - Use `ast.parse` in `eval` mode, recursively validate nodes against a white-list (`+`, `-`, `*`, `/`, `**`, `sin`, `exp`, etc.).
   - Replace `^` with `**`, forbid `math.` prefix, reject keywords/imports.
   - Compile to a callable that executes in a sandboxed dictionary.
3. **Adaptive Simpson’s Rule**
   - Recursive helper returns `(approximation, error)` for an interval.
   - Terminate when error < tolerance or recursion limit reached.
   - Record subinterval depth for visual overlays and slice recommendations.
4. **Comparison + Recommendations**
   - Compute midpoint, trapezoid, Simpson, and adaptive results in the model.
   - Estimate relative error vs. adaptive result; derive a “suggested slice count” by back-solving from the Simpson error model.
5. **3D Mesh + Smart Slices**
   - Generate a coarse grid of theta rotations (≤18 steps) and axial samples (≤200) to avoid the cmu_graphics shape limit.
   - Derivative-based heuristic weights slices toward areas where |f'(x)| is large.

### Timeline Plan
| Date | Milestone |
| --- | --- |
| **Week 10 (Nov 8–14)** | Confirm final project scope with mentor, stub MVC files, seed function library, basic Riemann computation. |
| **Week 11 (Nov 15–21)** | Implement custom function flow, sidebar controls, animation loop, and documentation (TP1 deliverable). |
| **Week 12 (Nov 22–28)** | Add adaptive Simpson’s rule, error indicators, and polish (TP2 MVP). |
| **Week 13 (Nov 29–Dec 5)** | Stress-test custom expressions, capture demo footage, refine README/controls. |
| **Week 14 (Dec 6–10)** | Buffer for mentor feedback, bug fixes, and TP3 final touches. |

### Module List
- `cmu_graphics==1.1.44` (required by the syllabus; no other graphics modules).
- Python standard library modules: `math`, `dataclasses`, `typing`, `ast`, `itertools`.
- **No external APIs, AI services, or additional libraries** before MVP; will revisit only after TP2 with mentor approval.

### Preliminary Code Status
- Current repository already contains ~1,800 lines of MVC code:
  - `main.py` (event wiring), `mvp/controller.py`, `mvp/model.py`, `mvp/view.py`.
- Features implemented so far: curated function set, Riemann animation with video playback, safe custom function entry, adaptive Simpson’s rule, 3D preview, and polished UI elements.
- Further commits between TP1 and TP2 will focus on stability, documentation, and additional educator-facing overlays.

---

## Citations & Acknowledgements
- 3Blue1Brown content for conceptual inspiration on visualising calculus topics.
- cmu_graphics documentation from course notes.
- Prior personal experiments with Manim (for historical context; not part of the MVP submission).

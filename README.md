# Disk Method Visualizer (MVP-Ready for 15-112)

interactive cmu_graphics visualizer for the disk method: explore solids of revolution, adjust domains and slice counts, and see riemann-sum volume approximations in real time.

This repository now hosts an **interactive solids of revolution visualizer** that is fully compliant with the 15-112 term project pre-MVP rules:

- Built entirely with **cmu_graphics** and standard Python libraries
- Structured using the **Model–View–Controller (MVC)** pattern
- Runs locally with no external APIs, hardware, or disallowed frameworks

This codebase only contains the MVP deliverable plus the TP1 design documentation. All post-MVP experiments and external-module pipelines have been removed for now and can be restored later as needed.

---

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
- `R`: reset the current function to its suggested domain
- `Click` inside the plot: focus the rotation on a particular slice

---

## TP1 Proposal

### Project Description
**Name:** Manimify Math – Interactive Disk Method MVP  
**Goal:** Provide calculus learners with an intuitive, interactive way to explore volumes of revolution before introducing automation powered by external services. Users can switch between curated functions, adjust integration bounds, and see both the Riemann slices and the resulting volume approximation update in real time.

### Competitive Analysis
- **Desmos** offers excellent static graphing with sliders but does not emphasise the disk method or provide automated volume estimates.
- **3Blue1Brown** videos explain the concept beautifully yet are non-interactive and passive.
- **Manim** scripts (including the legacy version of this project) create stunning animations, but authoring them requires advanced tooling and is non-interactive.

This MVP bridges the gap by combining the immediacy of Desmos with the conceptual clarity of 3B1B, all within a single educational experience that runs locally and remains hands-on.

### Structural Plan (MVC Overview)
- **Model (`mvp/model.py`)**: encapsulates application state, selectable functions, integration bounds, slice counts, and disk-method computations.
- **View (`mvp/view.py`)**: renders axes, function graphs, slice approximations, and explanatory panels using cmu_graphics drawing primitives.
- **Controller (`mvp/controller.py`)**: translates keyboard/mouse input and timer events into model updates, ensuring the view redraws cleanly.
- **Entry Point (`main.py`)**: wires cmu_graphics callbacks to the controller and launches the event loop.

### Algorithmic Plan
The main algorithmic component is a **midpoint Riemann sum** that approximates \( V = \int_a^b \pi [f(x)]^2 dx \) for solids of revolution about the x-axis.  
Implementation details:
- Sample the function at slice midpoints, guaranteeing stability for non-negative functions.
- Recompute the volume whenever the user changes the function, domain, or slice count.
- Maintain a lightweight animation index derived from a rotation angle; this connects the numerical approximation to the highlighted slice for conceptual reinforcement.

### Timeline Plan
- **Week 10:** Finalize function library, MVC scaffolding, and data flow (DONE).
- **Week 11:** Polish UI/UX details, add instructions, verify algorithm correctness (IN PROGRESS).
- **Week 12:** Stretch goals (symbol input, saving sessions) if time permits; otherwise, perform robustness testing and documentation.

### Module List
- **Currently used:** `cmu_graphics`, `math`, `dataclasses`, standard library helpers.

---

## TP2 Update
Pending — will document structural refinements or design changes once TP1 feedback is received and processed.

---

## Citations & Acknowledgements
- 3Blue1Brown content for conceptual inspiration on visualising calculus topics.
- cmu_graphics documentation from course notes.
- Prior personal experiments with Manim (for historical context; not part of the MVP submission).

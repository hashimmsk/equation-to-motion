"""
View layer for the cmu_graphics MVP.

All drawing logic and coordinate transforms live in this module.
The controller calls `redraw_all` from the main `redrawAll` handler.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple
import math

from cmu_graphics import (  # type: ignore[attr-defined]
    drawLine,
    drawLabel,
    drawPolygon,
    drawRect,
    drawOval,
)

from . import model


def redraw_all(app) -> None:
    """Entry point used by the controller."""

    required_attrs = ("colors", "layout", "cache", "state")
    for attr in required_attrs:
        if not hasattr(app, attr):
            return

    if not isinstance(app.colors, dict) or "background" not in app.colors:
        return

    app.cache["buttons"] = {}

    draw_background(app)
    draw_plot(app)
    draw_ribbon(app)
    draw_sidebar(app)
    draw_status_bar(app)

    if app.state.input_stage != "idle":
        draw_input_overlay(app)


# ---------------------------------------------------------------------------
# Core panels
# ---------------------------------------------------------------------------


def draw_background(app) -> None:
    drawRect(0, 0, app.width, app.height, fill=app.colors["background"])

    graph_left, graph_top, graph_width, graph_height = app.layout["graph"]
    drawRect(
        graph_left - 12,
        graph_top - 12,
        graph_width + 24,
        graph_height + 24,
        fill=app.colors["panel"],
        border=app.colors["panelBorder"],
    )

    sidebar_left, sidebar_top, sidebar_width, sidebar_height = app.layout["sidebar"]
    drawRect(
        sidebar_left - 6,
        sidebar_top - 12,
        sidebar_width + 12,
        sidebar_height + 24,
        fill=app.colors["panel"],
        border=app.colors["panelBorder"],
    )


def draw_plot(app) -> None:
    state = app.state
    points, radius_max = model.curve_points_and_radius(state)
    y_min, y_max = compute_vertical_bounds(points, radius_max)
    app.cache["yRange"] = (y_min, y_max)
    app.cache["radiusMax"] = radius_max

    graph_left, graph_top, graph_width, graph_height = app.layout["graph"]

    drawRect(
        graph_left,
        graph_top,
        graph_width,
        graph_height,
        fill=app.colors["canvas"],
        border=app.colors["canvasBorder"],
        borderWidth=1,
    )

    draw_axes(app, y_min, y_max)

    if len(points) > 1:
        for pt_a, pt_b in zip(points[:-1], points[1:]):
            drawLine(
                *to_screen(app, pt_a),
                *to_screen(app, pt_b),
                fill=app.colors["curve"],
                lineWidth=2,
            )

    if state.show_3d and radius_max > 0:
        try:
            draw_surface_mesh(app, points, radius_max)
        except Exception as exc:  # noqa: BLE001
            state.show_3d = False
            state.message = f"3D preview unavailable: {exc}"
            draw_slices(app)
    else:
        draw_slices(app)
        if state.adaptive_intervals:
            draw_adaptive_intervals(app)

    if state.show_3d and state.adaptive_intervals:
        # Also overlay adaptive intervals in 3D mode for reference
        draw_adaptive_intervals(app, overlay_only=True)


def draw_axes(app, y_min: float, y_max: float) -> None:
    state = app.state

    if y_min <= 0 <= y_max:
        x0, y0 = to_screen(app, (state.domain_start, 0))
        x1, y1 = to_screen(app, (state.domain_end, 0))
        drawLine(x0, y0, x1, y1, fill=app.colors["axis"], lineWidth=1)

    if state.domain_start <= 0 <= state.domain_end:
        y0 = to_screen(app, (0, y_min))[1]
        y1 = to_screen(app, (0, y_max))[1]
        x = to_screen(app, (0, 0))[0]
        drawLine(x, y0, x, y1, fill=app.colors["axis"], lineWidth=1)

    for i in range(5):
        t = i / 4
        x = state.domain_start + t * (state.domain_end - state.domain_start)
        sx, sy0 = to_screen(app, (x, y_min))
        _, sy1 = to_screen(app, (x, y_max))
        drawLine(sx, sy0, sx, sy0 + 6, fill=app.colors["axis"])
        drawLabel(f"{x:.2f}", sx, sy0 + 16, size=10, fill=app.colors["axisSubtle"])

        y = y_min + t * (y_max - y_min)
        sx0, sy = to_screen(app, (state.domain_start, y))
        sx1, _ = to_screen(app, (state.domain_end, y))
        drawLine(sx0 - 6, sy, sx0, sy, fill=app.colors["axis"])
        drawLabel(f"{y:.2f}", sx0 - 28, sy + 2, size=10, fill=app.colors["axisSubtle"])


def draw_slices(app) -> None:
    state = app.state
    slices = model.slice_samples(state)
    if not slices:
        return
    dx = (state.domain_end - state.domain_start) / state.slice_count
    highlight_index = model.compute_highlight_index(state)

    for index, (x_mid, radius) in enumerate(slices):
        x_left = x_mid - 0.5 * dx
        x_right = x_mid + 0.5 * dx
        sx0, sy0 = to_screen(app, (x_left, 0))
        sx1, _ = to_screen(app, (x_right, 0))
        sx2, sy2 = to_screen(app, (x_right, radius))
        sx3, sy3 = to_screen(app, (x_left, radius))

        fill = app.colors["sliceHighlight"] if index == highlight_index else app.colors["slice"]
        border = app.colors["sliceBorder"]
        opacity = 55 if index == highlight_index else 28

        drawPolygon(
            sx0,
            sy0,
            sx1,
            sy0,
            sx2,
            sy2,
            sx3,
            sy3,
            fill=fill,
            border=border,
            opacity=opacity,
        )

        ellipse_width = abs(sx1 - sx0)
        ellipse_height = max(4, ellipse_width * 0.25)
        cx = (sx0 + sx1) / 2
        cy = sy3 - ellipse_height / 2
        drawOval(
            cx,
            cy,
            ellipse_width,
            ellipse_height,
            fill=fill,
            border=border,
            opacity=65 if index == highlight_index else 40,
        )


def draw_surface_mesh(app, points: List[Tuple[float, float]], radius_max: float) -> None:
    state = app.state
    if len(points) < 2 or radius_max <= 0:
        return

    step = max(1, len(points) // 80)
    sampled = points[::step]
    if sampled[-1] != points[-1]:
        sampled.append(points[-1])

    theta_steps = 18
    highlight_index = model.compute_highlight_index(state)
    domain_span = state.domain_end - state.domain_start or 1
    graph_left, graph_top, graph_width, graph_height = app.layout["graph"]
    y_min, y_max = app.cache["yRange"]
    y_span = y_max - y_min or 1
    depth_x = graph_width / domain_span * 0.05
    depth_y = graph_height / y_span * 0.04

    polygons = []

    for seg_index in range(len(sampled) - 1):
        x0, y0 = sampled[seg_index]
        x1, y1 = sampled[seg_index + 1]
        r0 = max(0.0, abs(y0))
        r1 = max(0.0, abs(y1))

        for j in range(theta_steps):
            theta0 = j / theta_steps * math.pi
            theta1 = (j + 1) / theta_steps * math.pi
            sin0, cos0 = math.sin(theta0), math.cos(theta0)
            sin1, cos1 = math.sin(theta1), math.cos(theta1)

            p0 = _project_point(app, x0, r0 * cos0, r0 * sin0, depth_x, depth_y)
            p1 = _project_point(app, x1, r1 * cos0, r1 * sin0, depth_x, depth_y)
            p2 = _project_point(app, x1, r1 * cos1, r1 * sin1, depth_x, depth_y)
            p3 = _project_point(app, x0, r0 * cos1, r0 * sin1, depth_x, depth_y)

            avg_depth = (sin0 + sin1) / 2
            slice_index = min(
                state.slice_count - 1,
                max(
                    0,
                    int((x0 - state.domain_start) / domain_span * state.slice_count),
                ),
            )
            polygons.append(
                (
                    avg_depth,
                    slice_index == highlight_index,
                    (p0, p1, p2, p3),
                    j,
                )
            )

    polygons.sort(key=lambda item: item[0])

    for depth, is_highlight, corners, theta_index in polygons:
        color = app.colors["sliceHighlight"] if is_highlight else app.colors["slice"]
        border = app.colors["sliceBorder"]
        opacity = 60 if is_highlight else int(25 + 30 * (1 - theta_index / theta_steps))
        drawPolygon(
            corners[0][0],
            corners[0][1],
            corners[1][0],
            corners[1][1],
            corners[2][0],
            corners[2][1],
            corners[3][0],
            corners[3][1],
            fill=color,
            border=border,
            opacity=opacity,
        )

    # Re-draw the axis on top for clarity
    draw_axes(app, y_min, y_max)


def draw_ribbon(app) -> None:
    ribbon_left, ribbon_top, ribbon_width, ribbon_height = app.layout["ribbon"]
    drawRect(ribbon_left, ribbon_top, ribbon_width, ribbon_height, fill=app.colors["ribbon"])
    drawLabel(
        "Interactive Disk Method Visualizer",
        ribbon_left + 16,
        ribbon_top + ribbon_height / 2,
        align="left",
        size=22,
        fill=app.colors["ribbonText"],
        bold=True,
    )
    drawLabel(
        "←/→ switch · [ ] domain · +/- slices · Space loop · V video · N new function · 3 toggle 3D · A adaptive · G apply slices · T tolerance",
        ribbon_left + ribbon_width - 16,
        ribbon_top + ribbon_height / 2,
        align="right",
        size=12,
        fill=app.colors["ribbonText"],
    )


def draw_sidebar(app) -> None:
    state = app.state
    sidebar_left, sidebar_top, sidebar_width, sidebar_height = app.layout["sidebar"]

    drawLabel(
        "Control Panel",
        sidebar_left + sidebar_width / 2,
        sidebar_top + 28,
        size=18,
        fill=app.colors["sidebarHeading"],
        bold=True,
    )

    # Buttons
    button_width = sidebar_width - 48
    button_height = 34
    button_y = sidebar_top + 60
    spacing = 12
    button_specs = [
        ("play", "Play video (V)"),
        ("toggle3d", f"3D preview: {'On' if state.show_3d else 'Off'} (3)"),
        ("addFunction", "Add custom function (N)"),
        ("adaptive", "Adaptive refine (A)"),
        ("applySlices", "Apply suggested slices (G)"),
        ("tolerance", f"Tolerance: ±{state.adaptive_tolerance:g} (T)"),
    ]

    for index, (name, label) in enumerate(button_specs):
        y = button_y + index * (button_height + spacing)
        draw_button(
            app,
            name,
            label,
            sidebar_left + 24,
            y,
            button_width,
            button_height,
        )

    active_fn = model.active_function(state)
    info_top = button_y + len(button_specs) * (button_height + spacing) + 20
    info_lines = [
        ("Function", active_fn.name),
        ("Expression", active_fn.expression),
        ("Domain", f"[{state.domain_start:.2f}, {state.domain_end:.2f}]"),
        ("Slices", f"{state.slice_count}"),
        ("Volume (approx)", f"{state.approx_volume:.4f} units³"),
        (
            "Playback",
            "Video" if state.play_mode == "video" else ("Looping" if state.is_animating else "Paused"),
        ),
        (
            "Adaptive volume",
            "—" if state.adaptive_volume is None else f"{state.adaptive_volume:.5f} units³",
        ),
        (
            "Adaptive error",
            "—" if state.adaptive_error is None else f"{state.adaptive_error:.5g}",
        ),
        (
            "Suggested slices",
            "—" if state.adaptive_recommended_slices is None else f"{state.adaptive_recommended_slices}",
        ),
        ("Input stage", state.input_stage),
    ]

    for i, (label, value) in enumerate(info_lines):
        y = info_top + i * 46
        drawLabel(label, sidebar_left + 24, y, align="left", size=14, fill=app.colors["sidebarLabel"], bold=True)
        drawLabel(value, sidebar_left + 24, y + 20, align="left", size=14, fill=app.colors["sidebarValue"])

    footer_top = sidebar_top + sidebar_height - 110
    drawLabel(
        "MVC Reminder",
        sidebar_left + sidebar_width / 2,
        footer_top,
        size=16,
        fill=app.colors["sidebarHeading"],
        bold=True,
    )
    drawLabel(
        "Model: state + math\nView: drawing routines\nController: events",
        sidebar_left + sidebar_width / 2,
        footer_top + 52,
        size=12,
        fill=app.colors["sidebarValue"],
        align="center",
    )


def draw_status_bar(app) -> None:
    state = app.state
    bar_height = 36
    drawRect(
        0,
        app.height - bar_height,
        app.width,
        bar_height,
        fill=app.colors["panel"],
        border=app.colors["panelBorder"],
    )
    drawLabel(
        state.message,
        18,
        app.height - bar_height / 2,
        align="left",
        size=14,
        fill=app.colors["sidebarValue"],
    )


def draw_input_overlay(app) -> None:
    state = app.state
    stage = state.input_stage
    prompts = {
        "function": "Enter f(x) using sin, cos, exp, sqrt... No 'math.' prefix. Press Enter when done.",
        "domain_start": "Enter the domain start (a number). Press Enter to continue.",
        "domain_end": "Enter the domain end (greater than start). Press Enter to finish.",
    }
    prompt = prompts.get(stage, "")

    drawRect(0, 0, app.width, app.height, fill="black", opacity=45)
    box_width = app.width * 0.7
    box_height = 160
    box_left = (app.width - box_width) / 2
    box_top = app.height * 0.28

    drawRect(box_left, box_top, box_width, box_height, fill=app.colors["canvas"], border=app.colors["panelBorder"])
    drawLabel(
        prompt,
        app.width / 2,
        box_top + 34,
        size=16,
        align="center",
        fill=app.colors["sidebarValue"],
    )

    caret = "_" if (state.input_stage != "idle" and (len(state.input_buffer) // 2) % 2 == 0) else " "
    drawLabel(
        f"> {state.input_buffer}{caret}",
        app.width / 2,
        box_top + 92,
        size=20,
        align="center",
        fill=app.colors["sidebarHeading"],
        bold=True,
    )
    drawLabel(
        "Press Esc to cancel",
        app.width / 2,
        box_top + 126,
        size=12,
        align="center",
        fill=app.colors["axisSubtle"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def draw_button(app, name: str, label: str, x: float, y: float, width: float, height: float) -> None:
    drawRect(x, y, width, height, fill=app.colors["canvas"], border=app.colors["panelBorder"])
    drawLabel(label, x + width / 2, y + height / 2, align="center", size=13, fill=app.colors["sidebarHeading"])
    app.cache["buttons"][name] = (x, y, width, height)


def compute_vertical_bounds(points: Iterable[Tuple[float, float]], radius_padding: float) -> Tuple[float, float]:
    """Expands the raw min/max slightly to keep the graph readable."""

    values = list(y for (_, y) in points)
    values.extend([0.0, radius_padding, -radius_padding])

    if not values or max(values) == min(values):
        return (-1.0, 1.0)

    y_min = min(values)
    y_max = max(values)
    if math.isclose(y_min, y_max, abs_tol=1e-6):
        padding = abs(y_min) * 0.1 if y_min != 0 else 0.5
        return (y_min - padding, y_max + padding)
    padding = 0.12 * (y_max - y_min)
    return (y_min - padding, y_max + padding)


def to_screen(app, point: Tuple[float, float]) -> Tuple[float, float]:
    """Transforms (x, y) coordinates into screen-space pixels."""

    x, y = point
    state = app.state
    graph_left, graph_top, graph_width, graph_height = app.layout["graph"]
    y_min, y_max = app.cache["yRange"]

    x_span = state.domain_end - state.domain_start or 1
    y_span = y_max - y_min or 1

    sx_fraction = (x - state.domain_start) / x_span
    sy_fraction = (y - y_min) / y_span

    sx = graph_left + sx_fraction * graph_width
    sy = graph_top + graph_height - sy_fraction * graph_height
    return (sx, sy)


def _project_point(app, x: float, y: float, z: float, depth_x: float, depth_y: float) -> Tuple[float, float]:
    """Simple isometric-style projection for the surface preview."""

    sx, sy = to_screen(app, (x, y))
    px = sx + z * depth_x
    py = sy - z * depth_y
    if not (math.isfinite(px) and math.isfinite(py)):
        raise ValueError("Projected point became non-finite.")
    max_pad_x = app.width * 4
    max_pad_y = app.height * 4
    if abs(px) > max_pad_x or abs(py) > max_pad_y:
        raise ValueError("Projected point escaped the drawable area.")
    return (px, py)


def draw_adaptive_intervals(app, overlay_only: bool = False) -> None:
    """Visualise the adaptive Simpson intervals as vertical markers."""

    state = app.state
    if not state.adaptive_intervals:
        return

    y_min, y_max = app.cache["yRange"]
    bottom = to_screen(app, (state.domain_start, y_min))[1]
    top = to_screen(app, (state.domain_start, y_max))[1]
    max_depth = max((depth for _, _, depth in state.adaptive_intervals), default=1)
    max_depth = max(1, max_depth)

    for interval_start, interval_end, depth in state.adaptive_intervals:
        color = app.colors["sliceHighlight"] if depth == max_depth else app.colors["sliceBorder"]
        alpha = 45 if depth == max_depth else 22
        sx_start = to_screen(app, (interval_start, y_min))[0]
        sx_end = to_screen(app, (interval_end, y_min))[0]
        drawRect(
            min(sx_start, sx_end),
            min(top, bottom),
            abs(sx_end - sx_start),
            abs(bottom - top),
            fill=color,
            opacity=alpha if not overlay_only else max(12, alpha // 2),
            border=None,
        )
        drawLine(
            sx_start,
            top,
            sx_start,
            bottom,
            fill=color,
            lineWidth=1,
        )
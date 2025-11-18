"""
View layer for the cmu_graphics MVP.

All drawing logic and coordinate transforms live in this module.
The controller calls `redraw_all` from the main `redrawAll` handler.
"""

from __future__ import annotations

from typing import Iterable, Tuple
import math

from cmu_graphics import (  # type: ignore[attr-defined]
    drawLine,
    drawLabel,
    drawPolygon,
    drawRect,
    drawOval,
)

from . import model

Color = Tuple[int, int, int]


def redraw_all(app) -> None:
    """Entry point used by the controller."""

    required_attrs = ("colors", "layout", "cache", "state")
    for attr in required_attrs:
        if not hasattr(app, attr):
            return

    if not isinstance(app.colors, dict) or "background" not in app.colors:
        return

    draw_background(app)
    draw_plot(app)
    draw_ribbon(app)
    draw_sidebar(app)


def draw_background(app) -> None:
    drawRect(0, 0, app.width, app.height, fill=app.colors["background"])

    # backdrop panels
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
    points = model.curve_points(state)
    y_min, y_max = compute_vertical_bounds(points)
    app.cache["yRange"] = (y_min, y_max)

    graph_left, graph_top, graph_width, graph_height = app.layout["graph"]

    # axes
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

    # function curve
    if len(points) > 1:
        for pt_a, pt_b in zip(points[:-1], points[1:]):
            drawLine(*to_screen(app, pt_a), *to_screen(app, pt_b), fill=app.colors["curve"], lineWidth=2)

    draw_slices(app, y_min, y_max)


def draw_axes(app, y_min: float, y_max: float) -> None:
    state = app.state
    graph_left, graph_top, graph_width, graph_height = app.layout["graph"]

    # x-axis
    if y_min <= 0 <= y_max:
        x0, y0 = to_screen(app, (state.domain_start, 0))
        x1, y1 = to_screen(app, (state.domain_end, 0))
        drawLine(x0, y0, x1, y1, fill=app.colors["axis"], lineWidth=1)

    # y-axis
    if state.domain_start <= 0 <= state.domain_end:
        y0 = to_screen(app, (0, y_min))[1]
        y1 = to_screen(app, (0, y_max))[1]
        x = to_screen(app, (0, 0))[0]
        drawLine(x, y0, x, y1, fill=app.colors["axis"], lineWidth=1)

    # tick marks (4 along each axis)
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


def draw_slices(app, y_min: float, y_max: float) -> None:
    state = app.state
    slices = model.slice_samples(state)
    dx = (state.domain_end - state.domain_start) / state.slice_count
    highlight_index = compute_highlight_index(state)

    for index, (x_mid, radius) in enumerate(slices):
        x_left = x_mid - 0.5 * dx
        x_right = x_mid + 0.5 * dx
        sx0, sy0 = to_screen(app, (x_left, 0))
        sx1, _ = to_screen(app, (x_right, 0))
        sx2, sy2 = to_screen(app, (x_right, radius))
        sx3, sy3 = to_screen(app, (x_left, radius))

        fill = app.colors["sliceHighlight"] if index == highlight_index else app.colors["slice"]
        border = app.colors["sliceBorder"]

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
            opacity=45 if index == highlight_index else 30,
        )

        # pseudo-3D disk preview at the top of each slice
        ellipse_width = abs(sx1 - sx0)
        ellipse_height = max(4, (ellipse_width) * 0.25)
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


def draw_ribbon(app) -> None:
    state = app.state
    ribbon_left, ribbon_top, ribbon_width, ribbon_height = app.layout["ribbon"]
    drawRect(ribbon_left, ribbon_top, ribbon_width, ribbon_height, fill=app.colors["ribbon"])
    drawLabel(
        "Interactive Disk Method Visualizer (MVP)",
        ribbon_left + 16,
        ribbon_top + ribbon_height / 2,
        align="left",
        size=22,
        fill=app.colors["ribbonText"],
        bold=True,
    )
    drawLabel(
        "Use ←/→ to change functions · [ and ] to adjust domain · +/- slices · space to animate",
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
        "MVP Control Panel",
        sidebar_left + sidebar_width / 2,
        sidebar_top + 24,
        size=18,
        fill=app.colors["sidebarHeading"],
        bold=True,
    )

    active_fn = model.active_function(state)
    paragraph_top = sidebar_top + 70
    info_lines = [
        ("Function", active_fn.name),
        ("Expression", active_fn.expression),
        ("Domain", f"[{state.domain_start:.2f}, {state.domain_end:.2f}]"),
        ("Slices", f"{state.slice_count}"),
        ("Approx Volume", f"{state.approx_volume:.4f} units³"),
        ("Animating", "Yes" if state.is_animating else "No"),
    ]
    spacing = 48
    for i, (label, value) in enumerate(info_lines):
        y = paragraph_top + i * spacing
        drawLabel(label, sidebar_left + 24, y, align="left", size=14, fill=app.colors["sidebarLabel"], bold=True)
        drawLabel(value, sidebar_left + 24, y + 20, align="left", size=14, fill=app.colors["sidebarValue"])

    footer_top = sidebar_top + sidebar_height - 110
    drawLabel(
        "MVC Structure",
        sidebar_left + sidebar_width / 2,
        footer_top,
        size=16,
        fill=app.colors["sidebarHeading"],
        bold=True,
    )
    drawLabel(
        "Model: State + math\nView: Drawing routines\nController: Events",
        sidebar_left + sidebar_width / 2,
        footer_top + 50,
        size=12,
        fill=app.colors["sidebarValue"],
        align="center",
    )


def compute_vertical_bounds(points: Iterable[Tuple[float, float]]) -> Tuple[float, float]:
    """Expands the raw min/max slightly to keep the graph readable."""

    y_values = [y for (_, y) in points]
    if not y_values:
        return (-1, 1)
    y_min = min(y_values + [0])
    y_max = max(y_values + [0])
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

    sx_fraction = (x - state.domain_start) / (state.domain_end - state.domain_start)
    sx = graph_left + sx_fraction * graph_width

    sy_fraction = (y - y_min) / (y_max - y_min)
    sy = graph_top + graph_height - sy_fraction * graph_height
    return (sx, sy)


def compute_highlight_index(state: model.AppState) -> int:
    """Maps the rotation angle to a slice index for highlighting."""

    if not state.is_animating:
        return -1
    normalized = (state.rotation_angle % 360) / 360
    index = int(normalized * state.slice_count)
    return min(state.slice_count - 1, index)



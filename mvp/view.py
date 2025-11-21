"""
View layer for the cmu_graphics MVP.
All drawing logic and coordinate transforms live in this module.
The controller calls `redraw_all` from the main `redrawAll` handler.

"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from cmu_graphics import drawLabel, drawLine, drawPolygon, drawRect

from . import model


def redraw_all(app) -> None:
    if not _ready(app):
        return
    draw_background(app)
    draw_ribbon(app)
    draw_graph(app)
    draw_sidebar(app)


def draw_background(app) -> None:
    drawRect(0, 0, app.width, app.height, fill=app.colors["background"])


def draw_ribbon(app) -> None:
    x, y, w, h = app.layout["ribbon"]
    drawRect(x, y, w, h, fill=app.colors["ribbon"])
    drawLabel(
        "Disk method visualizer",
        x + 20,
        y + h / 2,
        align="left",
        size=22,
        fill=app.colors["ribbonText"],
    )
    drawLabel(
        f"{model.active_function(app.state).name}",
        x + w - 20,
        y + h / 2,
        align="right",
        size=18,
        fill=app.colors["ribbonText"],
    )


def draw_graph(app) -> None:
    bounds = app.layout["graph"]
    drawRect(*bounds, fill=app.colors["canvas"], border=app.colors["canvasBorder"], borderWidth=2)
    samples = model.sample_curve(app.state, steps=160)
    if not samples:
        return
    y_min, y_max = _curve_window(samples)
    _draw_axes(app, bounds, y_min, y_max)
    _draw_slices(app, bounds, y_min, y_max)
    _draw_curve(app, bounds, y_min, y_max, samples)


def draw_sidebar(app) -> None:
    x, y, w, h = app.layout["sidebar"]
    drawRect(x, y, w, h, fill=app.colors["sidebar"], border=app.colors["canvasBorder"])
    inset = 24
    line = y + inset
    spacing = 28
    info = [
        ("Function", model.active_function(app.state).expression),
        ("Domain", f"[{app.state.x_min:.2f}, {app.state.x_max:.2f}]"),
        ("Slices", str(app.state.slice_count)),
        ("Volume", f"{app.state.approx_volume:.3f} units³"),
        ("Animation", "running" if app.state.is_animating else "paused"),
        ("Status", app.state.status_message),
    ]
    for label, value in info:
        drawLabel(label, x + inset, line, align="left", size=14, fill=app.colors["sidebarText"])
        drawLabel(value, x + inset, line + 16, align="left", size=18, fill=app.colors["accent"])
        line += spacing
    drawLabel(
        f"Angle {app.state.rotation_angle:05.1f}°",
        x + inset,
        y + h - inset,
        align="left",
        size=16,
        fill=app.colors["sidebarText"],
    )


def _draw_axes(app, bounds, y_min, y_max) -> None:
    left, top, width, height = bounds
    axis_color = app.colors["axis"]
    drawLine(left, top, left, top + height, fill=axis_color)
    drawLine(left, top + height, left + width, top + height, fill=axis_color)
    if y_min <= 0 <= y_max:
        _, zero_y = _project(app, bounds, app.state.x_min, 0, y_min, y_max)
        drawLine(left, zero_y, left + width, zero_y, fill=axis_color)


def _draw_slices(app, bounds, y_min, y_max) -> None:
    state = app.state
    for x0, width, radius in model.slice_samples(state):
        x1 = x0 + width
        base1 = _project(app, bounds, x0, 0, y_min, y_max)
        base2 = _project(app, bounds, x1, 0, y_min, y_max)
        top1 = _project(app, bounds, x0, radius, y_min, y_max)
        top2 = _project(app, bounds, x1, radius, y_min, y_max)
        coords = [
            base1[0],
            base1[1],
            top1[0],
            top1[1],
            top2[0],
            top2[1],
            base2[0],
            base2[1],
        ]
        drawPolygon(
            *coords,
            fill=app.colors["slice"],
            opacity=40,
            border=app.colors["curve"],
            borderWidth=1,
        )


def _draw_curve(app, bounds, y_min, y_max, samples: Sequence[Tuple[float, float]]) -> None:
    for a, b in zip(samples, samples[1:]):
        ax, ay = _project(app, bounds, a[0], a[1], y_min, y_max)
        bx, by = _project(app, bounds, b[0], b[1], y_min, y_max)
        drawLine(ax, ay, bx, by, fill=app.colors["curve"], lineWidth=2)


def _curve_window(samples: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    ys = [y for _, y in samples]
    y_min = min(ys)
    y_max = max(ys)
    if abs(y_max - y_min) < 1e-3:
        padding = 0.5
        return y_min - padding, y_max + padding
    padding = 0.15 * (y_max - y_min)
    return y_min - padding, y_max + padding


def _ready(app) -> bool:
    return all(hasattr(app, attr) for attr in ("colors", "layout", "state"))


def _project(app, bounds, x, y, y_min, y_max) -> Tuple[float, float]:
    left, top, width, height = bounds
    span_x = app.state.x_max - app.state.x_min
    span_y = y_max - y_min or 1.0
    rel_x = 0.0 if span_x == 0 else (x - app.state.x_min) / span_x
    rel_y = (y - y_min) / span_y
    px = left + rel_x * width
    py = top + height - rel_y * height
    return px, py


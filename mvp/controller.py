"""
Controller layer for the cmu_graphics MVP.
Translates user input events from cmu_graphics into calls on the model,
and coordinates the redraw cycle.

"""

from __future__ import annotations

from cmu_graphics import rgb

from . import model


def app_started(app) -> None:
    app.state = model.create_initial_state()
    app.cache = {}
    app.layout = {
        "graph": (70, 120, int(app.width * 0.6), int(app.height * 0.65)),
        "sidebar": (int(app.width * 0.72), 120, int(app.width * 0.24), int(app.height * 0.65)),
        "ribbon": (0, 40, app.width, 60),
    }
    app.colors = {
        "background": rgb(246, 247, 251),
        "canvas": rgb(255, 255, 255),
        "canvasBorder": rgb(214, 222, 238),
        "axis": rgb(140, 150, 170),
        "curve": rgb(60, 90, 230),
        "slice": rgb(120, 160, 255),
        "sidebar": rgb(234, 238, 247),
        "sidebarText": rgb(40, 50, 80),
        "accent": rgb(247, 103, 131),
        "ribbon": rgb(32, 44, 78),
        "ribbonText": rgb(248, 250, 255),
    }
    app.stepsPerSecond = 15


def key_pressed(app, event) -> None:
    state = app.state
    key = event.key
    if key in ("left", "a"):
        model.cycle_function(state, -1)
        return
    if key in ("right", "d"):
        model.cycle_function(state, 1)
        return
    if key == "[":
        model.adjust_domain(state, -0.2, 0)
        return
    if key == "]":
        model.adjust_domain(state, 0, 0.2)
        return
    if key in ("{",):
        model.adjust_domain(state, -0.5, 0)
        return
    if key in ("}",):
        model.adjust_domain(state, 0, 0.5)
        return
    if key in ("+", "="):
        model.adjust_slice_count(state, 1)
        return
    if key in ("-", "_"):
        model.adjust_slice_count(state, -1)
        return
    if key == "space":
        model.toggle_animation(state)
        model.set_status(state, "Animation toggled")
        return
    if key.lower() == "r":
        model.reset_state(state)


def mouse_pressed(app, event) -> None:
    bounds = app.layout["graph"]
    if not _within(bounds, event.x, event.y):
        model.toggle_animation(app.state)
        return
    left, _, width, _ = bounds
    span = app.state.x_max - app.state.x_min
    if width <= 0 or span <= 0:
        return
    relative = max(0.0, min(1.0, (event.x - left) / width))
    app.state.rotation_angle = relative * 360
    app.state.is_animating = False
    model.set_status(app.state, f"Slice focus {relative:.2f}")


def on_mouse_drag(app, mouseX, mouseY) -> None:
    _ = (app, mouseX, mouseY)


def on_mouse_release(app, event) -> None:
    _ = (app, event)


def timer_fired(app) -> None:
    model.tick_animation(app.state, degrees_per_tick=4.0)


def redraw_all(app) -> None:
    from . import view

    view.redraw_all(app)


def _within(bounds, x, y) -> bool:
    left, top, width, height = bounds
    return left <= x <= left + width and top <= y <= top + height


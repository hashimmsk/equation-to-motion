"""
Controller layer for the cmu_graphics MVP.

Translates user input events from cmu_graphics into calls on the model,
and coordinates the redraw cycle.
"""

from __future__ import annotations

from typing import Optional

from cmu_graphics import rgb  # type: ignore[attr-defined]

from . import model


def app_started(app) -> None:
    """Initialises global app data and shared layout constants."""
    app.state = model.create_initial_state()
    app.cache = {"buttons": {}}

    app.layout = {
        "graph": (80, 120, int(app.width * 0.6), int(app.height * 0.72)),
        "sidebar": (int(app.width * 0.72), 120, int(app.width * 0.24), int(app.height * 0.72)),
        "ribbon": (0, 40, app.width, 60),
    }
    app.colors = {
        "background": rgb(245, 246, 250),
        "panel": rgb(230, 235, 245),
        "panelBorder": rgb(202, 210, 226),
        "canvas": rgb(255, 255, 255),
        "canvasBorder": rgb(214, 220, 235),
        "axis": rgb(120, 132, 148),
        "axisSubtle": rgb(151, 163, 178),
        "curve": rgb(58, 87, 232),
        "slice": rgb(58, 87, 232),
        "sliceHighlight": rgb(245, 94, 138),
        "sliceBorder": rgb(41, 57, 125),
        "ribbon": rgb(33, 46, 82),
        "ribbonText": rgb(248, 250, 255),
        "sidebarHeading": rgb(33, 46, 82),
        "sidebarLabel": rgb(80, 92, 110),
        "sidebarValue": rgb(25, 35, 58),
    }

    app.stepsPerSecond = 15


def key_pressed(app, event) -> None:
    """Delegates key events to the model."""

    key = event.key
    state = app.state

    if state.input_stage != "idle":
        if key == "enter":
            model.submit_input(state)
        elif key == "backspace":
            model.backspace_input(state)
        elif key == "escape":
            model.cancel_input(state)
        else:
            char = _key_to_char(key)
            if char:
                model.append_input_character(state, char)
        return

    if key in ("left", "a"):
        model.cycle_function(state, -1)
    elif key in ("right", "d"):
        model.cycle_function(state, +1)
    elif key == "[":
        model.adjust_domain(state, -0.1, 0)
    elif key == "]":
        model.adjust_domain(state, 0, 0.1)
    elif key in ("{",):
        model.adjust_domain(state, -0.25, 0)
    elif key in ("}",):
        model.adjust_domain(state, 0, 0.25)
    elif key in ("+", "="):
        model.adjust_slice_count(state, +1)
    elif key in ("-", "_"):
        model.adjust_slice_count(state, -1)
    elif key in ("up",):
        model.adjust_slice_count(state, +2)
    elif key in ("down",):
        model.adjust_slice_count(state, -2)
    elif key == "space":
        model.toggle_animation(state)
    elif key.lower() == "n":
        model.begin_custom_function_entry(state)
    elif key.lower() == "v":
        model.start_video_playback(state)
    elif key.lower() == "a":
        model.run_adaptive_refinement(state)
    elif key.lower() == "g":
        model.apply_adaptive_slice_recommendation(state)
    elif key.lower() == "t":
        model.cycle_adaptive_tolerance(state)
    elif key == "3":
        model.toggle_display_mode(state)
    elif key == "r":
        model.reset_state(state)
    elif key == "p":
        # quick snapshot of the current approximation for debugging
        print(f"Current approximate volume: {state.approx_volume:.4f} units^3")


def mouse_pressed(app, event) -> None:
    """
    Clicking inside the graph toggles animation focusing on the nearest slice.
    Clicking elsewhere simply toggles animation.
    """

    graph_left, graph_top, graph_width, graph_height = app.layout["graph"]
    state = app.state

    if state.input_stage != "idle":
        return

    button_hit = _button_hit(app, event.x, event.y)
    if button_hit == "play":
        model.start_video_playback(state)
        return
    if button_hit == "toggle3d":
        model.toggle_display_mode(state)
        return
    if button_hit == "addFunction":
        model.begin_custom_function_entry(state)
        return
    if button_hit == "adaptive":
        model.run_adaptive_refinement(state)
        return
    if button_hit == "tolerance":
        model.cycle_adaptive_tolerance(state)
        return
    if button_hit == "applySlices":
        model.apply_adaptive_slice_recommendation(state)
        return

    if (
        graph_left <= event.x <= graph_left + graph_width
        and graph_top <= event.y <= graph_top + graph_height
    ):
        focus_index = _index_for_x(app, event.x)
        if focus_index is not None:
            # jump rotation directly to the clicked slice
            step_fraction = focus_index / max(1, state.slice_count)
            state.rotation_angle = step_fraction * 360
            state.is_animating = True
    else:
        model.toggle_animation(state)


def on_mouse_drag(app, mouseX: float, mouseY: float) -> None:
    """Currently a no-op placeholder to satisfy cmu_graphics' drag hook."""

    # Drag-based domain adjustments were removed for TP2 polish, but the main
    # module still wires up onMouseDrag. Having this stub prevents attribute
    # errors when cmu_graphics emits drag events.
    _ = (app, mouseX, mouseY)


def on_mouse_release(app, event) -> None:
    """No-op placeholder to keep the release hook balanced with on_mouse_drag."""

    _ = (app, event)


def timer_fired(app) -> None:
    """Keeps the animation advancing smoothly."""

    state = app.state
    speed = 5.0 if state.play_mode == "video" else 4.0
    model.tick_animation(state, degrees_per_tick=speed)


def redraw_all(app) -> None:
    """Redirects the view call; defined for symmetry."""

    from . import view

    app.cache.setdefault("buttons", {})
    view.redraw_all(app)


def _index_for_x(app, x_pixel: float):
    """Converts a screen x-position into a slice index."""

    state = app.state
    graph_left, _, graph_width, _ = app.layout["graph"]

    relative = (x_pixel - graph_left) / graph_width
    if not 0 <= relative <= 1:
        return None
    return min(state.slice_count - 1, max(0, int(relative * state.slice_count)))


def _key_to_char(key: str) -> Optional[str]:
    """Map cmu_graphics key strings to the characters we allow in text input."""

    if len(key) == 1:
        return key
    mapping = {
        "space": " ",
        "minus": "-",
        "equal": "=",
        "slash": "/",
        "period": ".",
        "comma": ",",
        "apostrophe": "'",
        "semicolon": ";",
        "leftBracket": "[",
        "rightBracket": "]",
        "backslash": "\\",
    }
    return mapping.get(key)


def _button_hit(app, x: float, y: float) -> Optional[str]:
    """Return the identifier of the button under the cursor, if any."""

    buttons = app.cache.get("buttons", {})
    for name, (bx, by, bw, bh) in buttons.items():
        if bx <= x <= bx + bw and by <= y <= by + bh:
            return name
    return None
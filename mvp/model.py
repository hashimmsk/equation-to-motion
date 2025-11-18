"""
Model layer for the cmu_graphics MVP.

Encapsulates the application state and pure functions that update
the state in response to controller actions. No drawing or UI logic
appears here so that we can adhere to the MVC structure required by
15-112.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Tuple
import math


@dataclass
class FunctionDefinition:
    """Metadata describing a selectable function."""

    name: str
    expression: str
    evaluator: Callable[[float], float]
    suggested_domain: Tuple[float, float]


@dataclass
class AppState:
    """
    Stores the mutable state for the application. The controller
    mutates this state strictly through helper functions provided
    in this module.
    """

    functions: List[FunctionDefinition]
    current_index: int = 0
    domain_start: float = 0.0
    domain_end: float = 2.0
    slice_count: int = 12
    is_animating: bool = False
    rotation_angle: float = 0.0
    approx_volume: float = 0.0


def _build_default_functions() -> List[FunctionDefinition]:
    """
    Defines the starter set of functions that the MVP supports.
    These functions are carefully chosen so that f(x) >= 0 on the
    suggested domains, keeping the solids-of-revolution intuition
    straightforward for students.
    """

    return [
        FunctionDefinition(
            name="Quadratic Bowl",
            expression="f(x) = (x - 1)^2 + 0.5",
            evaluator=lambda x: (x - 1) ** 2 + 0.5,
            suggested_domain=(0.0, 2.0),
        ),
        FunctionDefinition(
            name="Shifted Sine",
            expression="f(x) = sin(x) + 1.25",
            evaluator=lambda x: math.sin(x) + 1.25,
            suggested_domain=(0.0, math.pi),
        ),
        FunctionDefinition(
            name="Exponential Arc",
            expression="f(x) = 0.6·e^(0.5x)",
            evaluator=lambda x: 0.6 * math.exp(0.5 * x),
            suggested_domain=(0.0, 2.0),
        ),
    ]


def create_initial_state() -> AppState:
    """Factory used by the controller during app start-up."""

    functions = _build_default_functions()
    start, end = functions[0].suggested_domain
    state = AppState(
        functions=functions,
        current_index=0,
        domain_start=start,
        domain_end=end,
        slice_count=12,
        is_animating=False,
        rotation_angle=0.0,
        approx_volume=0.0,
    )
    recompute_volume(state)
    return state


def active_function(state: AppState) -> FunctionDefinition:
    """Returns the function currently selected by the learner."""

    return state.functions[state.current_index]


def cycle_function(state: AppState, step: int) -> None:
    """
    Moves forward/backward through the available functions. The
    domain resets to the suggested range of the newly-selected
    function to keep the visualization meaningful.
    """

    state.current_index = (state.current_index + step) % len(state.functions)
    start, end = active_function(state).suggested_domain
    state.domain_start = start
    state.domain_end = end
    recompute_volume(state)


def adjust_domain(state: AppState, delta_start: float, delta_end: float) -> None:
    """
    Adjusts the integration bounds. The domain is clamped to remain
    valid (start < end) and within a reasonable range so the view
    can render the graph cleanly.
    """

    raw_start = state.domain_start + delta_start
    raw_end = state.domain_end + delta_end
    min_gap = 0.2

    # ensure ordering
    if raw_end - raw_start < min_gap:
        raw_end = raw_start + min_gap

    state.domain_start = max(-2.0, min(4.0, raw_start))
    state.domain_end = max(-1.8, min(4.5, raw_end))
    recompute_volume(state)


def set_domain(state: AppState, start: float, end: float) -> None:
    """Sets new integration bounds with validation."""

    if start >= end:
        raise ValueError("Domain start must be strictly less than domain end.")
    state.domain_start = start
    state.domain_end = end
    recompute_volume(state)


def adjust_slice_count(state: AppState, delta: int) -> None:
    """Increases or decreases the number of slices used for the Riemann sum."""

    state.slice_count = max(4, min(120, state.slice_count + delta))
    recompute_volume(state)


def toggle_animation(state: AppState) -> None:
    """Toggles whether the visualization rotates through the slices."""

    state.is_animating = not state.is_animating


def reset_state(state: AppState) -> None:
    """Restores defaults for the current function."""

    start, end = active_function(state).suggested_domain
    state.domain_start = start
    state.domain_end = end
    state.slice_count = 12
    state.is_animating = False
    state.rotation_angle = 0.0
    recompute_volume(state)


def tick_animation(state: AppState, degrees_per_tick: float = 4.0) -> None:
    """Advances the rotation angle used by the view."""

    if state.is_animating:
        state.rotation_angle = (state.rotation_angle + degrees_per_tick) % 360


def _sample_curve_points(
    evaluator: Callable[[float], float], start: float, end: float, resolution: int = 180
) -> List[Tuple[float, float]]:
    """
    Samples the underlying function to support plotting. Sampling occurs
    in the model so that the view can remain relatively thin.
    """

    if resolution <= 0:
        raise ValueError("Resolution must be positive.")

    step = (end - start) / resolution
    return [(x, evaluator(x)) for x in _frange(start, end, step)]


def curve_points(state: AppState, resolution: int = 180) -> List[Tuple[float, float]]:
    """Public wrapper to fetch sampled (x, f(x)) pairs."""

    func = active_function(state).evaluator
    return _sample_curve_points(func, state.domain_start, state.domain_end, resolution)


def slice_samples(state: AppState) -> List[Tuple[float, float]]:
    """
    Returns representative sample points for the Riemann slices.
    Each tuple holds (x_midpoint, radius) for a slice.
    """

    func = active_function(state).evaluator
    start, end = state.domain_start, state.domain_end
    dx = (end - start) / state.slice_count
    slices = []
    for i in range(state.slice_count):
        x_mid = start + (i + 0.5) * dx
        radius = max(0.0, func(x_mid))
        slices.append((x_mid, radius))
    return slices


def recompute_volume(state: AppState) -> None:
    """
    Recomputes the approximated volume using the disk method via a
    midpoint Riemann sum. This function must be called whenever the
    function, domain, or slice count changes.
    """

    func = active_function(state).evaluator
    start, end = state.domain_start, state.domain_end
    dx = (end - start) / state.slice_count
    volume = 0.0
    for i in range(state.slice_count):
        x_mid = start + (i + 0.5) * dx
        radius = max(0.0, func(x_mid))
        volume += math.pi * (radius**2) * dx
    state.approx_volume = volume


def _frange(start: float, end: float, step: float):
    """Floating-point range generator that is robust to rounding error."""

    if step <= 0:
        raise ValueError("Step must be positive.")

    i = 0
    current = start
    # guard with a small epsilon to ensure the endpoint is included
    epsilon = step / 2
    while current <= end + epsilon:
        yield current if i == 0 else min(current, end)
        current = start + (i := i + 1) * step



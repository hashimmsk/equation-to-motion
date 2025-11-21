"""
Model layer for the cmu_graphics MVP.
Encapsulates the application state and pure functions that update
the state in response to controller actions. No drawing or UI logic
appears here so that we can adhere to the MVC structure required by
15-112.

"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi, sin
from typing import Callable, List, Tuple


@dataclass
class FunctionDefinition:
    name: str
    expression: str
    evaluator: Callable[[float], float]
    suggested_domain: Tuple[float, float]


@dataclass
class AppState:
    functions: List[FunctionDefinition]
    current_index: int
    x_min: float
    x_max: float
    slice_count: int
    is_animating: bool
    rotation_angle: float
    approx_volume: float
    status_message: str


def create_initial_state() -> AppState:
    functions = _build_functions()
    first = functions[0]
    state = AppState(
        functions=functions,
        current_index=0,
        x_min=first.suggested_domain[0],
        x_max=first.suggested_domain[1],
        slice_count=12,
        is_animating=False,
        rotation_angle=0.0,
        approx_volume=0.0,
        status_message="Use arrows to cycle functions",
    )
    _update_volume(state)
    return state


def active_function(state: AppState) -> FunctionDefinition:
    return state.functions[state.current_index]


def cycle_function(state: AppState, direction: int) -> None:
    count = len(state.functions)
    state.current_index = (state.current_index + direction) % count
    func = active_function(state)
    state.x_min, state.x_max = func.suggested_domain
    state.rotation_angle = 0.0
    state.is_animating = False
    _update_volume(state)
    set_status(state, f"Now viewing {func.name}")


def adjust_domain(state: AppState, delta_min: float, delta_max: float) -> None:
    new_min = state.x_min + delta_min
    new_max = state.x_max + delta_max
    if new_max - new_min < 0.4:
        return
    span_limit = 8.0
    state.x_min = max(-span_limit, new_min)
    state.x_max = min(span_limit, new_max)
    _update_volume(state)


def adjust_slice_count(state: AppState, delta: int) -> None:
    new_count = min(60, max(2, state.slice_count + delta))
    if new_count == state.slice_count:
        return
    state.slice_count = new_count
    _update_volume(state)


def toggle_animation(state: AppState) -> None:
    state.is_animating = not state.is_animating


def reset_state(state: AppState) -> None:
    func = active_function(state)
    state.x_min, state.x_max = func.suggested_domain
    state.slice_count = 12
    state.rotation_angle = 0.0
    state.is_animating = False
    _update_volume(state)
    set_status(state, "Reset to defaults")


def tick_animation(state: AppState, degrees_per_tick: float = 4.0) -> None:
    if not state.is_animating:
        return
    state.rotation_angle = (state.rotation_angle + degrees_per_tick) % 360


def sample_curve(state: AppState, steps: int = 120) -> List[Tuple[float, float]]:
    span = state.x_max - state.x_min
    if span <= 0 or steps < 2:
        return []
    dx = span / (steps - 1)
    x = state.x_min
    samples: List[Tuple[float, float]] = []
    for _ in range(steps):
        samples.append((x, evaluate_curve(state, x)))
        x += dx
    return samples


def slice_samples(state: AppState) -> List[Tuple[float, float, float]]:
    span = state.x_max - state.x_min
    if span <= 0 or state.slice_count <= 0:
        return []
    width = span / state.slice_count
    x = state.x_min
    data: List[Tuple[float, float, float]] = []
    for _ in range(state.slice_count):
        radius = abs(evaluate_curve(state, x + width / 2))
        data.append((x, width, radius))
        x += width
    return data


def evaluate_curve(state: AppState, x: float) -> float:
    return active_function(state).evaluator(x)


def set_status(state: AppState, message: str) -> None:
    state.status_message = message


def _update_volume(state: AppState) -> None:
    volume = 0.0
    for x, width, radius in slice_samples(state):
        volume += pi * radius * radius * width
    state.approx_volume = volume


def _build_functions() -> List[FunctionDefinition]:
    return [
        FunctionDefinition(
            name="Parabola",
            expression="y = 0.3x^2 + 0.5",
            evaluator=lambda x: 0.3 * x * x + 0.5,
            suggested_domain=(0.0, 3.0),
        ),
        FunctionDefinition(
            name="Sine bump",
            expression="y = sin(x) + 1.2",
            evaluator=lambda x: sin(x) + 1.2,
            suggested_domain=(0.0, 6.0),
        ),
        FunctionDefinition(
            name="Circular arc",
            expression="y = sqrt(4 - x^2)",
            evaluator=lambda x: max(0.0, 4 - x * x) ** 0.5,
            suggested_domain=(-2.0, 2.0),
        ),
    ]


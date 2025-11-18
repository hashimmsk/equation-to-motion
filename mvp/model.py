"""
Model layer for the cmu_graphics MVP.

Encapsulates the application state and pure functions that update
the state in response to controller actions. No drawing or UI logic
appears here so that we can adhere to the MVC structure required by
15-112.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
import ast
import math


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


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
    show_3d: bool = False
    message: str = "Use ←/→ to switch functions. Press N to add your own."
    input_stage: str = "idle"  # idle/function/domain_start/domain_end
    input_buffer: str = ""
    pending_expression: Optional[str] = None
    pending_evaluator: Optional[Callable[[float], float]] = None
    pending_domain_start: Optional[float] = None
    custom_count: int = 0
    play_mode: str = "loop"  # loop or video
    last_evaluation_error: Optional[str] = None
    adaptive_tolerance: float = 0.005
    adaptive_volume: Optional[float] = None
    adaptive_intervals: List[Tuple[float, float, int]] = field(default_factory=list)
    adaptive_error: Optional[float] = None
    adaptive_recommended_slices: Optional[int] = None


# ---------------------------------------------------------------------------
# Expression parsing helpers
# ---------------------------------------------------------------------------


_ALLOWED_FUNCTIONS: Dict[str, Callable[[float], float]] = {
    name: getattr(math, name)
    for name in (
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "exp",
        "log",
        "log10",
        "sqrt",
        "sinh",
        "cosh",
        "tanh",
    )
}
_ALLOWED_FUNCTIONS.update({"abs": abs})

_ALLOWED_CONSTANTS: Dict[str, float] = {"pi": math.pi, "e": math.e}
_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod)
_ALLOWED_UNARY = (ast.UAdd, ast.USub)


def _validate_node(node: ast.AST) -> None:
    """Recursively ensure that the AST uses only safe operations."""

    if isinstance(node, ast.Expression):
        _validate_node(node.body)
    elif isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)) and node.value is not None:
            raise ValueError("Only numeric constants are allowed.")
    elif isinstance(node, ast.Name):
        if node.id not in _ALLOWED_FUNCTIONS and node.id not in _ALLOWED_CONSTANTS and node.id != "x":
            raise ValueError(f"Unknown name '{node.id}'. Use common math functions without 'math.'.")
    elif isinstance(node, ast.BinOp):
        if not isinstance(node.op, _ALLOWED_BINOPS):
            raise ValueError("Unsupported binary operation.")
        _validate_node(node.left)
        _validate_node(node.right)
    elif isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, _ALLOWED_UNARY):
            raise ValueError("Unsupported unary operation.")
        _validate_node(node.operand)
    elif isinstance(node, ast.Call):
        if node.keywords:
            raise ValueError("Keyword arguments are not supported in expressions.")
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls like sin(x) are allowed.")
        if node.func.id not in _ALLOWED_FUNCTIONS:
            raise ValueError(f"Function '{node.func.id}' is not supported.")
        for arg in node.args:
            _validate_node(arg)
    else:
        raise ValueError("Unsupported expression component.")


def _compile_expression(expr: str) -> Callable[[float], float]:
    """Compile a user-provided expression into a callable."""

    cleaned = expr.strip()
    if not cleaned:
        raise ValueError("Expression cannot be empty.")

    cleaned = cleaned.replace("^", "**")
    tree = ast.parse(cleaned, mode="eval")
    _validate_node(tree)
    code = compile(tree, "<user-function>", "eval")

    def evaluator(x: float) -> float:
        local_scope = {**_ALLOWED_FUNCTIONS, **_ALLOWED_CONSTANTS, "x": x}
        result = eval(code, {"__builtins__": {}}, local_scope)  # noqa: S307 - controlled eval
        if isinstance(result, complex):
            raise ValueError("Expression produced complex values; only real numbers are supported.")
        if not isinstance(result, (int, float)):
            raise ValueError("Expression must evaluate to a real number.")
        if not math.isfinite(result):
            raise ValueError("Expression produced a non-finite value.")
        return float(result)

    return evaluator


# ---------------------------------------------------------------------------
# State factories and selectors
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# State mutation helpers
# ---------------------------------------------------------------------------


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
    state.is_animating = False
    state.rotation_angle = 0.0
    state.play_mode = "loop"
    state.message = f"Now viewing: {active_function(state).name}"
    _clear_adaptive_cache(state, keep_message=True)
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

    if raw_end - raw_start < min_gap:
        raw_end = raw_start + min_gap

    state.domain_start = max(-10.0, min(10.0, raw_start))
    state.domain_end = max(-9.8, min(10.0, raw_end))
    state.message = f"Domain set to [{state.domain_start:.2f}, {state.domain_end:.2f}]"
    _clear_adaptive_cache(state, keep_message=True)
    recompute_volume(state)


def set_domain(state: AppState, start: float, end: float) -> None:
    """Sets new integration bounds with validation."""

    if start >= end:
        raise ValueError("Domain start must be strictly less than domain end.")
    state.domain_start = start
    state.domain_end = end
    state.message = f"Domain set to [{start:.2f}, {end:.2f}]"
    _clear_adaptive_cache(state, keep_message=True)
    recompute_volume(state)


def adjust_slice_count(state: AppState, delta: int) -> None:
    """Increases or decreases the number of slices used for the Riemann sum."""

    state.slice_count = max(4, min(240, state.slice_count + delta))
    state.message = f"Using {state.slice_count} slices for approximation."
    _clear_adaptive_cache(state, keep_message=True)
    recompute_volume(state)


def toggle_animation(state: AppState) -> None:
    """Toggles whether the visualization rotates through the slices."""

    state.play_mode = "loop"
    state.is_animating = not state.is_animating
    state.message = "Looping rotation." if state.is_animating else "Rotation paused."


def start_video_playback(state: AppState) -> None:
    """Runs a single 360° rotation as a 'video' playback."""

    state.play_mode = "video"
    state.is_animating = True
    state.rotation_angle = 0.0
    state.message = "Playing full revolution…"


def toggle_display_mode(state: AppState) -> None:
    """Switch between pure 2D and hybrid 3D visualisation."""

    state.show_3d = not state.show_3d
    state.message = "3D surface preview on." if state.show_3d else "3D surface preview off."


def reset_state(state: AppState) -> None:
    """Restores defaults for the current function."""

    start, end = active_function(state).suggested_domain
    state.domain_start = start
    state.domain_end = end
    state.slice_count = 12
    state.is_animating = False
    state.rotation_angle = 0.0
    state.play_mode = "loop"
    state.message = f"Reset to defaults for {active_function(state).name}."
    _clear_adaptive_cache(state, keep_message=True)
    recompute_volume(state)


def tick_animation(state: AppState, degrees_per_tick: float = 4.0) -> None:
    """Advances the rotation angle used by the view."""

    if not state.is_animating:
        return

    next_angle = state.rotation_angle + degrees_per_tick
    if state.play_mode == "video":
        if next_angle >= 360.0:
            state.rotation_angle = 360.0
            state.is_animating = False
            state.play_mode = "loop"
            state.message = "Video playback complete."
        else:
            state.rotation_angle = next_angle
    else:
        state.rotation_angle = next_angle % 360.0


# ---------------------------------------------------------------------------
# Sampling utilities
# ---------------------------------------------------------------------------


def _sample_curve_points(
    state: AppState,
    evaluator: Callable[[float], float],
    start: float,
    end: float,
    resolution: int = 180,
) -> List[Tuple[float, float]]:
    """
    Samples the underlying function to support plotting. Sampling occurs
    in the model so that the view can remain relatively thin.
    """

    if resolution <= 0:
        raise ValueError("Resolution must be positive.")

    points: List[Tuple[float, float]] = []
    step = (end - start) / resolution
    last_error: Optional[str] = None

    for x in _frange(start, end, step):
        try:
            value = evaluator(x)
        except Exception as exc:  # noqa: BLE001
            last_error = f"Evaluation error near x={x:.3f}: {exc}"
            points.clear()
            break

        if not isinstance(value, (int, float)):
            last_error = "Function must return real numbers."
            points.clear()
            break

        if not math.isfinite(value):
            last_error = "Function produced a non-finite value."
            points.clear()
            break

        points.append((x, float(value)))

    state.last_evaluation_error = last_error
    if last_error:
        state.message = last_error
    return points


def curve_points(state: AppState, resolution: int = 180) -> List[Tuple[float, float]]:
    """Public wrapper to fetch sampled (x, f(x)) pairs."""

    func = active_function(state).evaluator
    return _sample_curve_points(
        state=state,
        evaluator=func,
        start=state.domain_start,
        end=state.domain_end,
        resolution=resolution,
    )


def slice_samples(state: AppState) -> List[Tuple[float, float]]:
    """
    Returns representative sample points for the Riemann slices.
    Each tuple holds (x_midpoint, radius) for a slice.
    """

    func = active_function(state).evaluator
    start, end = state.domain_start, state.domain_end
    dx = (end - start) / state.slice_count
    slices: List[Tuple[float, float]] = []

    for i in range(state.slice_count):
        x_mid = start + (i + 0.5) * dx
        try:
            radius = func(x_mid)
        except Exception:  # noqa: BLE001
            state.message = "Failed to evaluate function while computing slices."
            return []

        radius = float(radius)
        if not math.isfinite(radius):
            state.message = "Function produced non-finite values within the domain."
            return []
        slices.append((x_mid, max(0.0, abs(radius))))
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
        try:
            radius = func(x_mid)
        except Exception:  # noqa: BLE001
            state.message = "Failed to evaluate function inside volume integral."
            state.approx_volume = float("nan")
            return

        radius = float(radius)
        if not math.isfinite(radius):
            state.message = "Function produced non-finite values inside volume integral."
            state.approx_volume = float("nan")
            return

        radius = abs(radius)
        volume += math.pi * (radius**2) * dx

    state.approx_volume = volume


# ---------------------------------------------------------------------------
# Custom function workflow
# ---------------------------------------------------------------------------


def begin_custom_function_entry(state: AppState) -> None:
    """Start the workflow for defining a custom function."""

    if state.input_stage != "idle":
        return

    state.input_stage = "function"
    state.input_buffer = ""
    state.pending_expression = None
    state.pending_evaluator = None
    state.pending_domain_start = None
    state.message = "Enter f(x) using sin, cos, exp... then press Enter."


def cancel_input(state: AppState) -> None:
    """Abort the custom-function workflow."""

    state.input_stage = "idle"
    state.input_buffer = ""
    state.pending_expression = None
    state.pending_evaluator = None
    state.pending_domain_start = None
    state.message = "Custom function entry cancelled."


def append_input_character(state: AppState, char: str) -> None:
    """Append a character to the active input buffer."""

    if state.input_stage == "idle":
        return

    if state.input_stage == "function":
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+-*/^().,_ "
    else:
        allowed = "0123456789eE+-."

    if char in allowed and len(state.input_buffer) < 120:
        state.input_buffer += char


def backspace_input(state: AppState) -> None:
    """Remove the most recent character from the input buffer."""

    if state.input_stage != "idle" and state.input_buffer:
        state.input_buffer = state.input_buffer[:-1]


def submit_input(state: AppState) -> None:
    """Handle Enter presses during the custom workflow."""

    if state.input_stage == "function":
        _handle_function_expression(state)
    elif state.input_stage == "domain_start":
        _handle_domain_start(state)
    elif state.input_stage == "domain_end":
        _handle_domain_end(state)


def _handle_function_expression(state: AppState) -> None:
    """Validate and store the typed function expression."""

    expr = state.input_buffer.strip()
    try:
        evaluator = _compile_expression(expr)
        # quick sanity check at a midpoint
        evaluator((state.domain_start + state.domain_end) / 2)
    except Exception as exc:  # noqa: BLE001
        state.message = f"Cannot parse expression: {exc}"
        state.input_buffer = ""
        return

    state.pending_expression = expr
    state.pending_evaluator = evaluator
    state.input_buffer = ""
    state.input_stage = "domain_start"
    state.message = "Enter domain start (float) and press Enter."


def _handle_domain_start(state: AppState) -> None:
    """Capture the custom domain start."""

    try:
        state.pending_domain_start = float(state.input_buffer.strip())
    except ValueError:
        state.message = "Domain start must be a number."
        state.input_buffer = ""
        return

    state.input_buffer = ""
    state.input_stage = "domain_end"
    state.message = "Enter domain end (greater than start) and press Enter."


def _handle_domain_end(state: AppState) -> None:
    """Capture the domain end and finalise the custom function."""

    assert state.pending_domain_start is not None
    try:
        domain_end = float(state.input_buffer.strip())
    except ValueError:
        state.message = "Domain end must be numeric."
        state.input_buffer = ""
        return

    domain_start = state.pending_domain_start
    if domain_end <= domain_start:
        state.message = "Domain end must be greater than start."
        state.input_buffer = ""
        return

    evaluator = state.pending_evaluator
    expr = state.pending_expression
    if evaluator is None or expr is None:
        state.message = "Unexpected error finalising custom function."
        cancel_input(state)
        return

    try:
        min_val, max_val = _sample_for_validation(evaluator, domain_start, domain_end)
    except Exception as exc:  # noqa: BLE001
        state.message = f"Could not evaluate function on domain: {exc}"
        cancel_input(state)
        return

    state.custom_count += 1
    name = f"Custom {state.custom_count}"
    new_function = FunctionDefinition(
        name=name,
        expression=f"f(x) = {expr}",
        evaluator=evaluator,
        suggested_domain=(domain_start, domain_end),
    )
    state.functions.append(new_function)
    state.current_index = len(state.functions) - 1
    state.domain_start = domain_start
    state.domain_end = domain_end
    state.input_stage = "idle"
    state.input_buffer = ""
    state.pending_evaluator = None
    state.pending_expression = None
    state.pending_domain_start = None
    state.play_mode = "loop"
    state.is_animating = False
    _clear_adaptive_cache(state, keep_message=True)

    if min_val < 0:
        state.message = (
            f"Added {name}. Warning: function dips below the axis; discs use |f(x)|."
        )
    else:
        state.message = f"Added {name}! Press space to animate or V to play once."

    recompute_volume(state)


def _sample_for_validation(
    evaluator: Callable[[float], float], start: float, end: float, samples: int = 90
) -> Tuple[float, float]:
    """Check that the function is numerically well-behaved on the domain."""

    if end <= start:
        raise ValueError("Domain must have positive length.")

    min_val = float("inf")
    max_val = float("-inf")
    step = (end - start) / samples

    for x in _frange(start, end, step):
        value = evaluator(x)
        if not isinstance(value, (int, float)):
            raise ValueError("Function returned a non-numeric value.")
        if not math.isfinite(value):
            raise ValueError("Function produced non-finite values.")
        min_val = min(min_val, value)
        max_val = max(max_val, value)

    return min_val, max_val


# ---------------------------------------------------------------------------
# Misc utilities
# ---------------------------------------------------------------------------


def _frange(start: float, end: float, step: float):
    """Floating-point range generator that is robust to rounding error."""

    if step <= 0:
        raise ValueError("Step must be positive.")

    i = 0
    current = start
    epsilon = step / 2
    while current <= end + epsilon:
        yield current if i == 0 else min(current, end)
        current = start + (i := i + 1) * step


def curve_points_and_radius(state: AppState) -> Tuple[List[Tuple[float, float]], float]:
    """
    Convenience helper returning the sample points and the maximum radius.
    The max radius is useful for 3D rendering and warnings.
    """

    points = curve_points(state)
    if not points:
        return [], 0.0
    radius_max = max(abs(y) for _, y in points)
    return points, radius_max


def compute_highlight_index(state: AppState) -> int:
    """Maps the rotation angle to a slice index for highlighting."""

    if not state.is_animating and state.play_mode != "video":
        return -1
    normalized = (state.rotation_angle % 360.0) / 360.0
    index = int(normalized * state.slice_count)
    return min(state.slice_count - 1, index)


# ---------------------------------------------------------------------------
# Adaptive integration (algorithmic enrichment)
# ---------------------------------------------------------------------------


_TOLERANCE_CYCLE = [0.05, 0.02, 0.01, 0.005, 0.001, 0.0005]


def cycle_adaptive_tolerance(state: AppState) -> None:
    """Cycle through preset tolerances for the adaptive Simpson integrator."""

    try:
        current_index = _TOLERANCE_CYCLE.index(state.adaptive_tolerance)
    except ValueError:
        current_index = 0
    next_index = (current_index + 1) % len(_TOLERANCE_CYCLE)
    state.adaptive_tolerance = _TOLERANCE_CYCLE[next_index]
    state.message = f"Adaptive tolerance set to ±{state.adaptive_tolerance:g}"
    _clear_adaptive_cache(state, keep_message=True)


def run_adaptive_refinement(state: AppState) -> None:
    """Use adaptive Simpson's rule to estimate the volume and highlight intervals."""

    func = active_function(state).evaluator

    def integrand(x: float) -> float:
        value = func(x)
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("Function produced non-finite values during integration.")
        value = abs(value)
        return math.pi * (value**2)

    try:
        volume, intervals = _adaptive_simpson_integrate(
            integrand,
            state.domain_start,
            state.domain_end,
            state.adaptive_tolerance,
        )
    except Exception as exc:  # noqa: BLE001
        state.message = f"Adaptive refinement failed: {exc}"
        state.adaptive_volume = None
        state.adaptive_intervals.clear()
        state.adaptive_error = None
        state.adaptive_recommended_slices = None
        return

    state.adaptive_volume = volume
    state.adaptive_intervals = intervals
    state.adaptive_error = abs(volume - state.approx_volume)
    state.adaptive_recommended_slices = max(12, len(intervals) * 2)
    state.message = (
        f"Adaptive volume ≈ {volume:.5f}; "
        f"manual error ≈ {state.adaptive_error:.5g}. "
        f"Suggested slices: {state.adaptive_recommended_slices}."
    )


def apply_adaptive_slice_recommendation(state: AppState) -> None:
    """Adopt the slice count suggested by the adaptive integrator."""

    if not state.adaptive_recommended_slices:
        state.message = "No adaptive recommendation yet. Press A to analyse first."
        return

    state.slice_count = max(4, min(240, state.adaptive_recommended_slices))
    state.message = f"Applied adaptive slice count: {state.slice_count}"
    recompute_volume(state)


def _adaptive_simpson_integrate(
    f: Callable[[float], float],
    a: float,
    b: float,
    tol: float,
    max_depth: int = 12,
) -> Tuple[float, List[Tuple[float, float, int]]]:
    """Return integral estimate and the terminal intervals used."""

    intervals: List[Tuple[float, float, int]] = []
    fa = f(a)
    fb = f(b)
    fm = f((a + b) / 2)
    S = _simpson_basic(a, b, fa, fb, fm)
    result = _adaptive_simpson_recursive(
        f,
        a,
        b,
        tol,
        max_depth,
        0,
        fa,
        fb,
        fm,
        S,
        intervals,
    )
    return result, intervals


def _adaptive_simpson_recursive(
    f: Callable[[float], float],
    a: float,
    b: float,
    tol: float,
    max_depth: int,
    depth: int,
    fa: float,
    fb: float,
    fm: float,
    S: float,
    intervals: List[Tuple[float, float, int]],
) -> float:
    c = (a + b) / 2
    fd = f((a + c) / 2)
    fe = f((c + b) / 2)

    S_left = _simpson_basic(a, c, fa, fm, fd)
    S_right = _simpson_basic(c, b, fm, fb, fe)
    S2 = S_left + S_right

    if depth >= max_depth or abs(S2 - S) <= 15 * tol:
        intervals.append((a, b, depth))
        # Richardson extrapolation improves accuracy
        return S2 + (S2 - S) / 15

    left = _adaptive_simpson_recursive(
        f,
        a,
        c,
        tol / 2,
        max_depth,
        depth + 1,
        fa,
        fm,
        fd,
        S_left,
        intervals,
    )
    right = _adaptive_simpson_recursive(
        f,
        c,
        b,
        tol / 2,
        max_depth,
        depth + 1,
        fm,
        fb,
        fe,
        S_right,
        intervals,
    )
    return left + right


def _simpson_basic(a: float, b: float, fa: float, fb: float, fm: float) -> float:
    return (b - a) / 6 * (fa + 4 * fm + fb)


def _clear_adaptive_cache(state: AppState, keep_message: bool = False) -> None:
    """Reset cached adaptive results after structural changes."""

    state.adaptive_volume = None
    state.adaptive_intervals.clear()
    state.adaptive_error = None
    state.adaptive_recommended_slices = None
    if not keep_message:
        state.message = "Adaptive cache cleared."



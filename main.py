"""
Entry point for the cmu_graphics-based MVP implementation.

Running this file launches the interactive disk method visualizer that
complies with the 15-112 term project pre-MVP restrictions.
"""

from types import SimpleNamespace

from cmu_graphics import app, runApp  # type: ignore[attr-defined]

from mvp import controller


def onAppStart(app):
    controller.app_started(app)


def onKeyPress(app, key):
    event = SimpleNamespace(key=key)
    controller.key_pressed(app, event)


def onMousePress(app, mouseX, mouseY):
    event = SimpleNamespace(x=mouseX, y=mouseY)
    controller.mouse_pressed(app, event)


def onStep(app):
    controller.timer_fired(app)


def redrawAll(app):
    controller.redraw_all(app)


if __name__ == "__main__":
    runApp(width=1180, height=720)


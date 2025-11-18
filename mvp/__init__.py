"""
Core package for the cmu_graphics-based MVP implementation.

This package exposes the model, view, and controller modules that
compose the refactored 15-112 term project prototype.
"""

from . import model, view, controller  # re-export for convenience

__all__ = ["model", "view", "controller"]


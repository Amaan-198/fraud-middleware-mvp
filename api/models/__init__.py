"""
Fraud detection model engines.

This package exposes the core detection engines (rules, ML, policy), but we
delay importing their heavy dependencies (numpy, lightgbm, onnxruntime, etc.)
until the attributes are actually accessed. This allows lightweight modules
such as `api.models.institute_security` to be imported in isolation for unit
tests without forcing the full ML stack to be installed.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = ["RulesEngine", "MLEngine", "PolicyEngine"]


def __getattr__(name: str) -> Any:
    """Lazy-load heavy engine modules on first access."""
    if name not in __all__:
        raise AttributeError(f"module 'api.models' has no attribute '{name}'")

    module_map = {
        "RulesEngine": ("api.models.rules", "RulesEngine"),
        "MLEngine": ("api.models.ml_engine", "MLEngine"),
        "PolicyEngine": ("api.models.policy", "PolicyEngine"),
    }

    module_name, attr = module_map[name]
    module = import_module(module_name)
    value = getattr(module, attr)
    globals()[name] = value
    return value


if TYPE_CHECKING:
    from api.models.rules import RulesEngine
    from api.models.ml_engine import MLEngine
    from api.models.policy import PolicyEngine

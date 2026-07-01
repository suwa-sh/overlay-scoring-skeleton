"""Canonical overlay engine for readiness / scoring definitions."""

from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("overlay-scoring-skeleton")
except PackageNotFoundError:  # not installed (e.g. running from a source checkout)
    __version__ = "0.0.0.dev0"

from .overlay import (
    MergeResult,
    MergeViolation,
    apply_overlay,
    apply_overlays,
    group_items,
    group_of,
    is_leaf,
    load_yaml,
    separator_of,
    validate_definition,
)

__all__ = [
    "__version__",
    "MergeResult",
    "MergeViolation",
    "apply_overlay",
    "apply_overlays",
    "group_items",
    "group_of",
    "is_leaf",
    "load_yaml",
    "separator_of",
    "validate_definition",
]

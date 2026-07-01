"""Canonical overlay engine for readiness / scoring definitions."""

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

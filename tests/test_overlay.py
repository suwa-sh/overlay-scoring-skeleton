"""Tests for the canonical overlay engine.

Covers add / strengthen (leaf + group, group-scoped), every boundary condition,
source-order preservation, opaque-payload preservation, and a round-trip against
two real migrated definitions (aidr four-layer + siir dpa-clauses).
"""

from copy import deepcopy
from pathlib import Path

from overlay_scoring import (
    apply_overlay,
    apply_overlays,
    group_items,
    load_yaml,
    validate_definition,
)

DEFS = Path(__file__).resolve().parents[1] / "definitions"
OVERLAYS = Path(__file__).resolve().parents[1] / "examples" / "overlays"


def four_layer() -> dict:
    return load_yaml(DEFS / "example-four-layer.yaml")


def dpa() -> dict:
    return load_yaml(DEFS / "example-dpa-clauses.yaml")


def _ids(defn: dict) -> list[str]:
    return [it["id"] for it in defn["items"]]


# --- base integrity ---------------------------------------------------------

def test_base_definitions_validate():
    assert validate_definition(four_layer()) == []
    assert validate_definition(dpa()) == []


def test_definition_with_orphan_leaf_is_rejected():
    defn = {"version": 1, "name": "x", "items": [{"id": "A.child"}]}
    kinds = {v.kind for v in validate_definition(defn)}
    assert "unknown_group" in kinds


def test_definition_with_duplicate_id_is_rejected():
    defn = {"version": 1, "name": "x", "items": [{"id": "A"}, {"id": "A"}]}
    kinds = {v.kind for v in validate_definition(defn)}
    assert "id_collision" in kinds


# --- add --------------------------------------------------------------------

def test_add_leaf_to_existing_group():
    ov = {"extends": "four-layer-delegation-readiness",
          "add": [{"id": "L1.Q5", "text": "extra", "weight": 1.0}]}
    r = apply_overlay(four_layer(), ov)
    assert r.ok, r.violations
    assert "L1.Q5" in _ids(r.merged)


def test_add_leaf_with_unknown_group_is_rejected():
    ov = {"extends": "four-layer-delegation-readiness",
          "add": [{"id": "LZ.Q1", "text": "x", "weight": 1.0}]}
    r = apply_overlay(four_layer(), ov)
    # LZ matches selector "L*" but there is no LZ header
    assert not r.ok
    assert {v.kind for v in r.violations} == {"unknown_group"}


def test_add_to_ungoverned_group_is_rejected():
    ov = {"extends": "four-layer-delegation-readiness",
          "add": [{"id": "XYZ.q", "text": "x"}]}
    r = apply_overlay(four_layer(), ov)
    assert {v.kind for v in r.violations} == {"unsupported_op"}


def test_add_id_collision_with_base_is_rejected():
    ov = {"extends": "four-layer-delegation-readiness",
          "add": [{"id": "L1.Q1", "text": "dup", "weight": 1.0}]}
    r = apply_overlay(four_layer(), ov)
    assert {v.kind for v in r.violations} == {"id_collision"}


def test_add_id_collision_within_same_overlay_is_rejected():
    ov = {"extends": "four-layer-delegation-readiness",
          "add": [{"id": "L1.NEW", "text": "a", "weight": 1.0},
                  {"id": "L1.NEW", "text": "b", "weight": 1.0}]}
    r = apply_overlay(four_layer(), ov)
    assert {v.kind for v in r.violations} == {"id_collision"}


def test_add_new_group_header_then_leaf_in_same_overlay():
    ov = {"extends": "four-layer-delegation-readiness",
          "add": [{"id": "L5", "name": "extra_layer", "pass": 1.0, "revise": 0.7},
                  {"id": "L5.Q1", "text": "q", "weight": 1.0}]}
    r = apply_overlay(four_layer(), ov)
    assert r.ok, r.violations
    assert "L5" in _ids(r.merged) and "L5.Q1" in _ids(r.merged)


def test_add_id_with_two_separators_is_rejected():
    ov = {"extends": "four-layer-delegation-readiness",
          "add": [{"id": "L1.Q1.deep", "text": "x", "weight": 1.0}]}
    r = apply_overlay(four_layer(), ov)
    assert {v.kind for v in r.violations} == {"invalid_overlay"}


def test_add_item_without_id_is_rejected():
    ov = {"extends": "four-layer-delegation-readiness", "add": [{"text": "no id"}]}
    r = apply_overlay(four_layer(), ov)
    assert {v.kind for v in r.violations} == {"invalid_overlay"}


# --- strengthen -------------------------------------------------------------

def test_strengthen_group_field_higher_is_accepted():
    ov = {"extends": "four-layer-delegation-readiness",
          "strengthen": {"L4": {"revise": 0.8}}}
    r = apply_overlay(four_layer(), ov)
    assert r.ok, r.violations
    l4 = next(i for i in r.merged["items"] if i["id"] == "L4")
    assert l4["revise"] == 0.8


def test_strengthen_group_field_equal_is_accepted():
    ov = {"extends": "four-layer-delegation-readiness",
          "strengthen": {"L4": {"revise": 0.6}}}  # base is 0.6
    r = apply_overlay(four_layer(), ov)
    assert r.ok, r.violations


def test_strengthen_group_field_weakening_is_rejected():
    ov = {"extends": "four-layer-delegation-readiness",
          "strengthen": {"L4": {"revise": 0.4}}}  # 0.6 -> 0.4 is weaker
    r = apply_overlay(four_layer(), ov)
    assert {v.kind for v in r.violations} == {"weakening_rejected"}


def test_strengthen_leaf_field_lower_is_accepted():
    ov = {"extends": "shared-infra-dpa-clauses",
          "strengthen": {"clauses.DPA03": {"sla_confirmed_hours": 48}}}
    r = apply_overlay(dpa(), ov)
    assert r.ok, r.violations
    c = next(i for i in r.merged["items"] if i["id"] == "clauses.DPA03")
    assert c["sla_confirmed_hours"] == 48


def test_strengthen_leaf_field_weakening_is_rejected():
    ov = {"extends": "shared-infra-dpa-clauses",
          "strengthen": {"clauses.DPA03": {"sla_hours": 48}}}  # 24 -> 48 is weaker (lower is stricter)
    r = apply_overlay(dpa(), ov)
    assert {v.kind for v in r.violations} == {"weakening_rejected"}


def test_strengthen_non_numeric_is_rejected():
    ov = {"extends": "shared-infra-dpa-clauses",
          "strengthen": {"clauses.DPA03": {"sla_hours": "soon"}}}
    r = apply_overlay(dpa(), ov)
    assert {v.kind for v in r.violations} == {"invalid_overlay"}


def test_strengthen_undeclared_field_is_rejected():
    # weight is a leaf field but not declared strengthen-able in four-layer
    ov = {"extends": "four-layer-delegation-readiness",
          "strengthen": {"L1.Q1": {"weight": 2.0}}}
    r = apply_overlay(four_layer(), ov)
    assert {v.kind for v in r.violations} == {"unsupported_op"}


def test_strengthen_unknown_id_is_rejected():
    ov = {"extends": "four-layer-delegation-readiness",
          "strengthen": {"L9": {"revise": 0.9}}}
    r = apply_overlay(four_layer(), ov)
    assert {v.kind for v in r.violations} == {"unknown_id"}


# --- top-level / extends ----------------------------------------------------

def test_extends_mismatch_is_rejected():
    ov = {"extends": "wrong-name", "add": []}
    r = apply_overlay(four_layer(), ov)
    assert {v.kind for v in r.violations} == {"extends_mismatch"}


def test_unsupported_top_level_key_is_rejected():
    ov = {"extends": "four-layer-delegation-readiness", "delete": ["L1"]}
    r = apply_overlay(four_layer(), ov)
    assert {v.kind for v in r.violations} == {"unsupported_op"}


# --- multi-overlay ----------------------------------------------------------

def test_apply_overlays_stops_at_first_bad(tmp_path):
    good = tmp_path / "good.yaml"
    bad = tmp_path / "bad.yaml"
    after = tmp_path / "after.yaml"
    good.write_text("extends: four-layer-delegation-readiness\nadd:\n  - {id: 'L1.G1', text: g, weight: 1.0}\n")
    bad.write_text("extends: four-layer-delegation-readiness\nstrengthen:\n  L4: {revise: 0.1}\n")
    after.write_text("extends: four-layer-delegation-readiness\nadd:\n  - {id: 'L1.G2', text: g, weight: 1.0}\n")
    r = apply_overlays(four_layer(), [good, bad, after])
    assert not r.ok
    assert r.applied == [str(good)]           # good applied, stopped before 'after'
    assert "L1.G1" in _ids(r.merged)
    assert "L1.G2" not in _ids(r.merged)


# --- structural guarantees --------------------------------------------------

def test_source_order_and_opaque_payload_preserved():
    base = four_layer()
    ov = load_yaml(OVERLAYS / "sample-four-layer.yaml")
    r = apply_overlay(base, ov)
    assert r.ok, r.violations
    groups = group_items(r.merged)
    # group order preserved
    assert list(groups.keys()) == ["L1", "L2", "L3", "L4", "efficacy"]
    # added leaves appended to their group, base leaves kept in order
    l1_leaves = [i["id"] for i in groups["L1"]["leaves"]]
    assert l1_leaves == ["L1.Q1", "L1.Q2", "L1.Q3", "L1.Q4", "L1.ACME_Q5"]
    # opaque payload on the header survives untouched
    assert groups["L1"]["header"]["case_evidence"][0]["confidence"] == "observed_fact"


def test_engine_never_mutates_base():
    base = four_layer()
    snapshot = deepcopy(base)
    apply_overlay(base, {"extends": "four-layer-delegation-readiness",
                         "add": [{"id": "L1.Z", "text": "z", "weight": 1.0}]})
    assert base == snapshot


# --- round-trip against both real migrated definitions -----------------------

def test_roundtrip_four_layer_sample_overlay():
    r = apply_overlay(four_layer(), load_yaml(OVERLAYS / "sample-four-layer.yaml"))
    assert r.ok, r.violations
    ids = _ids(r.merged)
    assert "L1.ACME_Q5" in ids and "L4.ACME_Q6" in ids
    l4 = next(i for i in r.merged["items"] if i["id"] == "L4")
    assert l4["revise"] == 0.8


def test_roundtrip_dpa_sample_overlay():
    r = apply_overlay(dpa(), load_yaml(OVERLAYS / "sample-dpa-clauses.yaml"))
    assert r.ok, r.violations
    ids = _ids(r.merged)
    assert "clauses.ACME01" in ids
    dpa03 = next(i for i in r.merged["items"] if i["id"] == "clauses.DPA03")
    assert dpa03["sla_confirmed_hours"] == 48
    assert dpa03["sla_hours"] == 24                 # untouched
    assert dpa03["title"] == "委託先→委託元 漏えい通知SLA"   # opaque payload preserved

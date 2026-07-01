# Migration map: aidr / siir → canonical model

The canonical model is a single flat `items` list with `.`-separated ids
(`<group>` header, `<group>.<leaf>` leaf; one level only). This table is the
authoritative old→new mapping the aidr / siir migrations follow.

Rules that apply everywhere:
- Every leaf id is `<group>.<leaf>`; every group header id is `<group>` (no dot).
- Group-level numerics (thresholds, SLAs on a header) → header fields, `level: group`.
- Leaf numerics (weight, sla_hours, …) → leaf fields, `level: leaf`.
- Non-numeric / structural data (`when`, `cells`, `recommended`, `injects`,
  `action`, `case_evidence`, …) → **opaque payload** on the item; the engine never
  touches it, so consumers keep reading it as before.
- `extension_points` become structured (`group` selector + `allow` + for strengthen
  `level`/`field`/`direction`), replacing the old `path:` strings.

## aidr — ai-delegation-readiness

### four-layer.yaml  (done — see `definitions/example-four-layer.yaml`)
| old | new |
|---|---|
| `layers[]` (L1..L4) | header `L1`..`L4` (name/name_ja/purpose + `case_evidence` opaque) |
| `layers[].questions[]` | leaf `L1.Q1` … (`text`, `weight`) |
| `layers[].verdict_thresholds.{pass,revise}` | header fields `pass`/`revise` (`level: group`, `direction: higher`) |
| `efficacy_axis` | header `efficacy` (+ `pass`/`revise`) |
| `efficacy_axis.questions[]` | leaf `efficacy.E1` … |
| ext `layers[].questions` add | `{group: "L*", allow: add}` |
| ext `layers[].verdict_thresholds` strengthen | `{group: "L*", level: group, field: pass|revise, direction: higher}` |
| ext `efficacy_axis.*` | same with `group: "efficacy"` |

### delegation-matrix.yaml
| old | new |
|---|---|
| `axes[]` (verifiability, answer_definability) | header `verifiability`, `answer_definability` (name/name_ja/purpose + `threshold`) |
| `axes[].questions[]` (V1.., A1..) | leaf `verifiability.V1` …, `answer_definability.A1` … (`text`) |
| `axes[].threshold` | header field `threshold` (`level: group`, `direction: higher`) |
| `regions[]` (green/yellow/red) | header `regions` + leaf `regions.green`/`regions.yellow`/`regions.red` with opaque `when: [...]` + `action` |
| `examples[]` (**no id today**) | leaf `examples.<slug>` — synthesise a stable slug from `judgment` (e.g. `examples.receipt_mandatory_items_check`); keep `judgment`/`case`/`verifiability_yes`/`answer_definability_yes`/`region`/`rationale`/`confidence` as opaque payload |
| ext `axes[].questions` add | `{group: "verifiability", allow: add}` + `{group: "answer_definability", allow: add}` |
| ext `axes[].threshold` strengthen | `{group: "verifiability"|"answer_definability", level: group, field: threshold, direction: higher}` |
| ext `examples` add | `{group: "examples", allow: add}` |

> `regions` is a fixed lookup, not really extension-scored; keep it as data (add is optional). `score_delegation._resolve_region()` must keep reading each region's `when` list in source order.

## siir — shared-infra-incident-readiness

### dpa-clauses.yaml  (done — see `definitions/example-dpa-clauses.yaml`)
| old | new |
|---|---|
| `clauses[]` | header `clauses` + leaf `clauses.DPA01` … (`title`/`requirement`/`required` opaque) |
| `clauses[].sla_hours` | leaf field (`level: leaf`, `direction: lower`) |
| `clauses[].sla_confirmed_hours` (DPA03) | leaf field (`level: leaf`, `direction: lower`) — **do not drop** |
| ext `clauses` add / `clauses[].sla_hours` strengthen | `{group: "clauses", allow: add}` / `{group: "clauses", level: leaf, field: sla_hours|sla_confirmed_hours, direction: lower}` |

### notification-obligations.yaml
| old | new |
|---|---|
| `obligations[]` | header `obligations` + leaf `obligations.OB01` … (deadline_anchor/duration_text/recipient/… opaque) |
| `obligations[].duration_hours` | leaf field (`level: leaf`, `direction: lower`) |

### responsibility-matrix.yaml
| old | new |
|---|---|
| `roles[]` | header `roles` + leaf `roles.<id>` (`name` opaque) |
| `items[]` (responsibility items) | header `resp` + leaf `resp.<id>` (`cells` map + `recommended` opaque) |
| `legend` | keep as a top-level definition field (not an item) |
| ext `roles` add / `items` add | `{group: "roles", allow: add}` / `{group: "resp", allow: add}` |

### incident-raci.yaml
| old | new |
|---|---|
| `roles[]` | header `raci_roles` + leaf `raci_roles.<id>` |
| `activities[]` | header `raci_act` + leaf `raci_act.AC01` … (`text`/`cells`/`obligation_ref`/`clause_ref` opaque) |
| ext `roles`/`activities` add | `{group: "raci_roles", allow: add}` / `{group: "raci_act", allow: add}` |

### scenarios.yaml
| old | new |
|---|---|
| `scenarios[]` | header `scenarios` + leaf `scenarios.<id>` (`title`/`trigger`/`injects`/`facilitation_questions`/`focus_items`/`affected_brands`/`duration_minutes` opaque) |
| ext `scenarios` add | `{group: "scenarios", allow: add}` |

## Consumer projection

All consumers stop reading nested keys (`defn["layers"]`, `defn["clauses"]`, …) and
instead call `group_items(defn)` (in `overlay_scoring.overlay`) which returns an
ordered `{group: {"header": ..., "leaves": [...]}}` map preserving source order.
Group the flat items by id prefix; read header numerics from `header`, leaf data
from `leaves`. Order matters for: aidr layer sequence / region evaluation, siir
runbook activity order and SLA lookup by `obligation_ref`/`clause_ref`.

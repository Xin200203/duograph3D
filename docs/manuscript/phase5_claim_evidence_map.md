# Phase 5 Claim-to-Evidence Map

日期：2026-04-23  
状态：Phase 5 drafting in progress

---

## Purpose
Map each frozen claim row to the specific current artifacts that support it, so Phase 5 writing stays evidence-grounded.

---

## Claim 1 — Two-layer necessity

### Claim
Separating current-evidence repair from current-to-memory association is operationally useful.

### Current evidence
- code structure:
  - `src/duograph3d/layer1.py`
  - `src/duograph3d/layer2.py`
- structural rival evidence:
  - `single_layer_rival`
- analysis artifacts:
  - `docs/baselines/generated/phase4_broad_analysis/phase4_main_table_candidate.md`
  - `docs/baselines/generated/phase4_broad_analysis/phase4_failure_casebook.md`
  - `docs/manuscript/phase5_reviewer_defense.md`

### Current strength
- medium to medium-high

### Main risk
- reviewer may still say “this is decomposition style, not necessity” unless results discussion ties directly to the structural rival gap.

---

## Claim 2 — Memory-authority necessity

### Claim
Graph memory should be decision-bearing state rather than post-hoc export.

### Current evidence
- code structure:
  - `src/duograph3d/memory.py`
  - `src/duograph3d/layer2.py`
- graph activation:
  - relation edges
  - relation density
  - relation-edge counts
- analysis artifacts:
  - `docs/baselines/generated/phase4_broad_analysis/phase4_main_table_candidate.md`
  - `docs/manuscript/phase5_reviewer_defense.md`

### Current strength
- medium-high

### Main risk
- current package has weak memory-authority event activation under the broad real-observation suite, so the final paper should emphasize graph-memory decision structure carefully and avoid overselling memory-authority event counts as the only proof.

---

## Claim 3 — Temporal necessity

### Claim
Temporal continuity must affect 3D object decisions rather than only polishing intermediate masks.

### Current evidence
- code structure:
  - `src/duograph3d/evidence.py`
  - `src/duograph3d/layer2.py`
- temporal family:
  - none / naive / DEVA-style
- historical proxy package:
  - G2/G3 summaries
- current writing assets:
  - `docs/manuscript/phase5_reviewer_defense.md`

### Current strength
- medium

### Main risk
- broad Phase 4 package downgraded legacy proxy gates to historical reference, so the final paper needs to explain this transition carefully and not rely on old proxy-only temporal rows as if they were the final evidence surface.

---

## Claim 4 — Dual-consistency necessity

### Claim
Temporal continuity and geometry consistency should jointly constrain identity updates.

### Current evidence
- code structure:
  - geometry-profile consistency in layer-1 and layer-2
  - dual-consistency gate in layer-2
- regression tests:
  - continuity-without-geometry failure is blocked
- candidate package:
  - geometry-support-based analysis surfaces

### Current strength
- medium

### Main risk
- the geometry side is still weaker than reviewer-familiar map-quality / segmentation-quality metrics, so the final draft must present this as the current strongest implementation-backed form rather than a fully saturated geometry story.

---

## External comparison claim support

### Current artifacts
- `docs/story_aligned_experiment_setup.md`
- `docs/baselines/generated/external_baseline_matrix.md`
- `docs/phase3_external_baseline_inventory.md`
- DEVA summary artifacts
- ESAM summary artifacts (auxiliary-only)

### Role in paper
- justify that the work is not evaluated in isolation
- support grouped nearest-neighbor discussion by innovation row
- preserve provenance honesty
- remind the draft that ESAM-family assets are auxiliary compatibility references rather than the defining direct baseline

---

## Immediate writing rule

Every major claim in the Phase 5 manuscript should point to at least one of:
- a code-level grounding artifact
- a current candidate table
- a casebook / failure analysis artifact
- an external baseline family artifact

If a claim cannot be mapped, it should be weakened or removed.

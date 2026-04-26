# Phase 5 Figure Specs

日期：2026-04-23  
状态：Phase 5 figure-spec asset complete

---

## Figure 1 — Overall pipeline

### Purpose
Show the complete DuoGraph3D flow:
- observation input
- evidence builder
- layer-1 repair
- layer-2 association
- graph memory update
- output / analysis surfaces

### Source materials
- `docs/manuscript/phase5_paper_draft.md`
- `src/duograph3d/pipeline.py`
- `src/duograph3d/evidence.py`
- `src/duograph3d/layer1.py`
- `src/duograph3d/layer2.py`
- `src/duograph3d/memory.py`

### Caption draft
> Overview of DuoGraph3D. Real observations are converted into evidence items, repaired in a current-evidence graph, associated against graph memory under dual temporal/geometric consistency, and committed into a decision-bearing object graph memory.

---

## Figure 2 — Layer-1 evidence graph

### Purpose
Show compatibility graph construction and connected-component repair.

### Source materials
- `src/duograph3d/layer1.py`

### Caption draft
> Layer-1 current-evidence repair. Evidence items are connected by continuity, appearance, and geometry-profile compatibility before being collapsed into repaired current object hypotheses.

---

## Figure 3 — Layer-2 association + graph-memory update

### Purpose
Show:
- temporal cues
- geometry-profile consistency
- relation-edge bonus
- dual-consistency gate

### Source materials
- `src/duograph3d/layer2.py`
- `src/duograph3d/memory.py`

### Caption draft
> Layer-2 current-to-memory association. Temporal identity cues and geometry-profile consistency jointly constrain identity updates, while graph-memory relation edges provide historical interaction bias.

---

## Figure 4 — Graph memory / relation edge view

### Purpose
Demonstrate that graph memory is not post-hoc only.

### Source materials
- `src/duograph3d/contracts.py`
- `src/duograph3d/memory.py`
- `docs/baselines/generated/phase4_broad_analysis/phase4_casebook.md`

### Caption draft
> Object graph memory stores node state, lifecycle status, and explicit relation edges. These relations are updated online and can influence future association decisions.

---

## Figure 5 — Representative DEVA / Replica case

### Purpose
Show a strong real-observation success case.

### Source materials
- `docs/baselines/generated/phase4_broad_analysis/phase4_casebook.md`
- `docs/phase1_real_observation_cases.md`

### Target scene
- `replica/office0` or `replica/office3`

### Caption draft
> Representative Replica case under DEVA-derived observations, showing stable current-to-memory identity maintenance across repeated observations.

---

## Figure 6 — Worst fragmentation ScanNet case

### Purpose
Show the hardest current failure mode.

### Source materials
- `docs/baselines/generated/phase4_broad_analysis/phase4_failure_casebook.md`

### Target scene
- `scannet/scene0222_00`

### Caption draft
> Failure case from the broad ScanNet real-observation package. The scene exhibits high fragmentation under dense object turnover, defining the current stress frontier for DuoGraph3D.

---

## Table 1 — Internal regime main table

### Source
- `docs/baselines/generated/phase4_broad_analysis/phase4_main_table_candidate.md`

### Role
Main internal result table across real-observation regimes.

---

## Table 2 — Internal ablation table

### Source
- `docs/baselines/generated/phase4_broad_analysis/phase4_ablation_table_candidate.md`

### Role
Delta-to-baseline ablation table.

---

## Table 3 — External baseline family table

### Source
- `docs/phase4_paper_candidate_tables.md`
- `docs/baselines/generated/external_baseline_matrix.md`

### Role
Parallel external-family comparison table with provenance-preserving metric surfaces.

---

## Table 4 — Phase 4 readiness / package summary (internal)

### Source
- `docs/baselines/generated/phase4_broad_readiness/phase4_readiness.md`

### Role
Internal coordination table; likely supplementary rather than main-paper table.

---

## Immediate next figure work
- [x] convert the above specs into actual rendered figures
- [x] assign scene screenshots / panel assets
- [x] finalize captions
- [x] choose which tables stay in main paper vs supplementary

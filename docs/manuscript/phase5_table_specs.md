# Phase 5 Table Specs

日期：2026-04-23  
状态：Phase 5 table-spec asset complete

---

## Table 1 — Internal regime main table

### Purpose
Provide the main internal Phase 4 real-observation results across the four regimes:
- baseline
- burst
- random
- stress

### Source artifacts
- `docs/baselines/generated/phase4_broad_analysis/phase4_main_table_candidate.md`
- `docs/baselines/generated/phase4_broad_observation_metrics_summary.json`

### Required columns
- regime
- coverage
- identity fragmentation
- track consistency
- real-observation frame rate
- geometry support mean

### Main takeaway
The baseline regime yields the highest observation coverage but also the highest fragmentation, showing that more observation throughput does not automatically produce better identity stability.

### Caption draft
> Internal real-observation regime comparison. Baseline maximizes observation coverage but also exhibits the strongest fragmentation, while burst/random/stress regimes expose different stability-versus-coverage trade-offs.

---

## Table 2 — Internal ablation table

### Purpose
Show deltas relative to the baseline regime.

### Source artifacts
- `docs/baselines/generated/phase4_broad_analysis/phase4_ablation_table_candidate.md`

### Required columns
- regime
- delta fragmentation
- delta track consistency
- delta observation frame rate
- delta geometry support

### Main takeaway
Every non-baseline regime improves fragmentation relative to baseline, but does so while lowering observation frame rate.

### Caption draft
> Internal ablation deltas relative to the baseline regime. Lower fragmentation and higher consistency are accompanied by reduced observation-frame coverage, highlighting the current operating frontier.

---

## Table 3 — Story-aligned comparison table

### Purpose
Summarize external comparisons by **role in the paper story** rather than by one convenience-driven benchmark family.

### Source artifacts
- `docs/story_aligned_experiment_setup.md`
- `docs/submission_lock.md`
- `docs/manuscript/phase5_reviewer_defense.md`

### Required columns
- comparison group
- representative baseline(s)
- dataset family
- metric family
- which claim row it tests
- status / provenance

### Main takeaway
External baselines should be grouped into direct-task, temporal, graph/memory, dense-mapping, and auxiliary-compatibility roles. ESAM belongs only to the last category unless a later protocol justifies a stronger role.

### Caption draft
> Story-aligned comparison protocol. Baselines are grouped by the specific claim they test: direct zero-shot online 3D comparison, temporal carry-over, graph/object-memory alternatives, dense mapping alternatives, and auxiliary benchmark-compatibility reference.

---

## Table 4 — Worst/best scene table

### Purpose
Compactly summarize the strongest and weakest scenes for the major internal metrics.

### Source artifacts
- `docs/baselines/generated/phase4_broad_analysis/phase4_worst_best_analysis.md`

### Required columns
- metric
- best scene / value
- worst scene / value

### Main takeaway
Replica scenes dominate the strongest identity-stability rows, while several ScanNet scenes define the current fragmentation frontier.

### Caption draft
> Worst/best scene summary for the current observation-grounded metrics. The table exposes the current stability frontier and supplies direct figure targets.

---

## Table 5 — Robustness table (supplementary)

### Purpose
Summarize regime-level pass status and row stability for supplementary reporting.

### Source artifacts
- `docs/manuscript/phase5_robustness_table.md`
- `docs/baselines/generated/phase4_broad_robustness_summary.json`

### Placement
- supplementary / appendix

### Caption draft
> Robustness summary across the broadened real-observation regimes. This table is retained as supplementary context rather than a main-paper result surface.

---

## Table placement recommendation

### Main paper
- Table 1 — internal regime main table
- Table 2 — internal ablation table
- Table 3 — story-aligned comparison table

### Supplementary / appendix candidate
- Table 4 — worst/best scene table
- readiness table (if retained at all)

---

## Immediate table work
- [x] choose final metric formatting and rounding
- [x] confirm which tables stay in the main paper
- [x] add explicit claim references for each table
- [x] ensure all captions stay inside the frozen claim boundary

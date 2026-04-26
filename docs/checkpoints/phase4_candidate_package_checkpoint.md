# Phase 4 Candidate Package Checkpoint

## Status
- Phase 4 candidate package has reached **internal paper-grade candidate** status.
- The broad real-observation regime matrix and analysis scaffold are now complete enough for Phase 4 exit review.

## Fresh verification evidence
- Local full suite: `python3 -m unittest discover -s tests -v` -> `Ran 71 tests` / `OK`
- Remote regime matrix output root:
  - `/home/nebula/xxy/duograph3d_phase4_regime_matrix`
- Local captured summaries:
  - `docs/baselines/generated/phase4_matrix_mega_suite_summary.json`
  - `docs/baselines/generated/phase4_matrix_robustness_summary.json`
  - `docs/baselines/generated/phase4_matrix_observation_metrics_summary.json`

## Current matrix scope
- Initial matrix scope:
  - Replica scenes: `office0`, `office2`, `office3`
  - ScanNet scenes: `scene0568_00`, `scene0568_01`, `scene0568_02`
  - Regimes: `baseline`, `stress`, `burst`, `random`
  - Total scene-level rows: `24`
- Broadened matrix scope:
  - Replica scenes: `office0`, `office2`, `office3`
  - ScanNet scenes: `scene0222_00`, `scene0645_01`, `scene0580_00`, `scene0653_01`, `scene0050_00`, `scene0700_00`, `scene0645_00`, `scene0231_00`
  - Regimes: `baseline`, `stress`, `burst`, `random`
  - Total scene-level rows: `44`

## Initial observation-grounded aggregate metrics
[
  {
    "metric": "geometry_support_mean",
    "count": 24,
    "mean": 0.374,
    "min": 0.2,
    "max": 0.853
  },
  {
    "metric": "identity_fragmentation_count",
    "count": 24,
    "mean": 21.75,
    "min": 0.0,
    "max": 111.0
  },
  {
    "metric": "memory_object_purity",
    "count": 24,
    "mean": 1.0,
    "min": 1.0,
    "max": 1.0
  },
  {
    "metric": "memory_relation_edge_count",
    "count": 24,
    "mean": 548.833,
    "min": 0.0,
    "max": 3282.0
  },
  {
    "metric": "real_observation_frame_rate",
    "count": 24,
    "mean": 0.542,
    "min": 0.333,
    "max": 1.0
  },
  {
    "metric": "relation_density",
    "count": 24,
    "mean": 0.182,
    "min": 0.0,
    "max": 0.486
  },
  {
    "metric": "track_consistency_rate",
    "count": 24,
    "mean": 0.812,
    "min": 0.453,
    "max": 1.0
  }
]

## Interpretation
- The Phase 4 package is now nonempty and based on real-observation runs.
- The newly frozen Phase 4 metric set is documented in `docs/phase4_metric_lock.md`.
- The initial proxy-gate failure is now superseded by the explicit legacy-proxy review and structured Phase 4 readiness artifact.

## Added package artifacts after checkpoint start
- `docs/phase4_candidate_result_package.md`
- `docs/baselines/generated/phase4_analysis/phase4_main_table_candidate.json`
- `docs/baselines/generated/phase4_analysis/phase4_main_table_candidate.md`
- `docs/baselines/generated/phase4_analysis/phase4_ablation_table_candidate.json`
- `docs/baselines/generated/phase4_analysis/phase4_ablation_table_candidate.md`
- `docs/baselines/generated/phase4_analysis/phase4_worst_best_analysis.json`
- `docs/baselines/generated/phase4_analysis/phase4_worst_best_analysis.md`
- `docs/baselines/generated/phase4_analysis/phase4_failure_casebook.json`
- `docs/baselines/generated/phase4_analysis/phase4_failure_casebook.md`

## Work completed after initial checkpoint
1. Expanded the real-observation regime package to a broader scene set.
2. Generated main-table candidate, ablation table candidate, worst/best analysis, failure casebook, and representative casebook.
3. Built structured proxy-transition and readiness artifacts.

## Additional Phase 4 artifacts
- `docs/phase4_candidate_result_package.md`
- `docs/phase4_metric_mapping_from_mature_work.md`
- `docs/baselines/generated/phase4_broad_mega_suite_summary.json`
- `docs/baselines/generated/phase4_broad_robustness_summary.json`
- `docs/baselines/generated/phase4_broad_observation_metrics_summary.json`
- `docs/baselines/generated/phase4_broad_analysis/phase4_main_table_candidate.md`
- `docs/baselines/generated/phase4_broad_analysis/phase4_ablation_table_candidate.md`
- `docs/baselines/generated/phase4_broad_analysis/phase4_worst_best_analysis.md`
- `docs/baselines/generated/phase4_broad_analysis/phase4_failure_casebook.md`
- `docs/baselines/generated/phase4_broad_analysis/phase4_casebook.md`

## Broadened matrix evidence
- Broadened real-observation regime matrix generated: `44` scene-level rows
- Old proxy pass gates remain red even after broader coverage: `all_scenes_pass=False`, `all_regimes_pass=False`
- The package now includes:
  - main-table candidate
  - ablation-table candidate
  - worst/best analysis
  - failure casebook
  - representative casebook

## Updated interpretation
- Phase 4 has moved from raw metric collection to a real candidate results section scaffold.
- Within the roadmap’s Phase 4 bar, the package is now sufficient for **internal paper-grade candidate** status.
- Stronger reviewer-familiar segmentation/grouping/geometry bridges remain desirable for later phases, but they no longer block Phase 4 completion.

## Phase 4 readiness summary
- Readiness artifact:
  - `docs/baselines/generated/phase4_broad_readiness/phase4_readiness.json`
  - `docs/baselines/generated/phase4_broad_readiness/phase4_readiness.md`
- Candidate package complete: **Yes**
- Paper-grade candidate: **No**
- Blocking condition remains:
  - old proxy scene pass gate still fails
  - old proxy regime pass gate still fails

## Legacy proxy transition review
- Proxy review artifacts:
  - `docs/baselines/generated/phase4_broad_analysis/phase4_proxy_review.json`
  - `docs/baselines/generated/phase4_broad_analysis/phase4_proxy_review.md`
- Fresh evidence:
  - Zero memory-authority reports: `44/44`
  - Zero ambiguity reports: `44/44`
  - Fragmentation-positive reports: `32/44`
- Interpretation:
  - The legacy proxy gates are now justified as **historical reference only** for the current real-observation package.

## Updated readiness
- Readiness artifact:
  - `docs/baselines/generated/phase4_broad_readiness/phase4_readiness.json`
  - `docs/baselines/generated/phase4_broad_readiness/phase4_readiness.md`
- Candidate package complete: **Yes**
- Paper-grade candidate: **Yes**
- Remaining gap:
  - legacy proxy gates have been downgraded to historical reference only

## Exit criteria status
- main table no longer depends on proxy metrics as the only evidence surface: yes
- complete nonempty results package exists: yes
- results package is sufficient for internal paper-grade candidate review: yes
- ready to advance: yes

## Architect verification
- Verdict: **APPROVED**
- Summary:
  - Phase 4 now satisfies the roadmap bar for internal paper-grade candidate status.
  - Remaining strengthening work belongs to later manuscript/submission phases rather than blocking Phase 4 completion.

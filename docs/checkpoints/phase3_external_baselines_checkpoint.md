# Phase 3 Checkpoint Report — External Baseline System Build-out

## Phase goal
Build a reviewer-credible external baseline system with at least two external baseline families documented by official provenance, execution paths, and formal result artifacts.

## Deliverables produced
- `src/duograph3d/external_baselines.py`
  - added `esam_official_target(...)`
- `src/duograph3d/esam_results.py`
  - ESAM result summarizer, lane normalizer, and markdown renderer
- `examples/render_esam_output_summary.py`
- `tests/test_esam_results.py`
- updated `tests/test_external_baselines.py`
- local captured raw artifacts:
  - `docs/baselines/raw/deva_jsonfiles/*.json`
  - `docs/baselines/raw/esam/metric.json`
  - `docs/baselines/raw/esam/online_monitor_summary.json`
- generated baseline summaries:
  - `docs/baselines/generated/deva_output_summary.json`
  - `docs/baselines/generated/deva_output_summary.md`
  - `docs/baselines/generated/deva_lanes.json`
  - `docs/baselines/generated/esam_output_summary.json`
  - `docs/baselines/generated/esam_output_summary.md`
  - `docs/baselines/generated/esam_lane.json`
- `docs/phase3_external_baseline_inventory.md`
- `docs/baselines/generated/external_baseline_matrix.json`
- `docs/baselines/generated/external_baseline_matrix.md`

## Validation results
- Targeted external-baseline tests: **PASS**
  - `python3 -m unittest tests.test_external_baselines tests.test_esam_results -v`
  - Result: `Ran 3 tests` / `OK`
- Full local suite: **PASS**
  - `python3 -m unittest discover -s tests -v`
  - Result: `Ran 62 tests` / `OK`
- External provenance verification: **PASS**
  - ESAM official repo available on remote machine at commit `188fc6de44f7577fecec2d69b75c7adbd9992251`
  - ConceptGraphs official repo available on remote machine at commit `72f5962822b5e8678a446f367a06df1a977d2a4d`
- Formal result artifacts available for two external families: **PASS**
  - DEVA official offline family
  - ESAM / EmbodiedSAM official-family ScanNet-MV lane
- Unified baseline matrix generated: **PASS**
  - `docs/baselines/generated/external_baseline_matrix.json`
  - `docs/baselines/generated/external_baseline_matrix.md`
- Official ESAM rerun attempt from the official checkout: **ATTEMPTED / BLOCKED BY ENV DRIFT**
  - Command launched from `/home/nebula/xxy/ESAM` with official config
  - Blocker observed: missing `ultralytics.yolo` import inside the official environment during `oneformer3d` import

## Exit criteria status
- DEVA official lane formalized: yes
- second external nearest-neighbor family formalized: yes
- both families have documented provenance and local normalized result artifacts: yes
- ready to advance: yes

## Architect verification
- Verdict: **APPROVED**
- Summary:
  - Two external baseline families are now formalized with normalized artifacts.
  - The ESAM provenance caveat is explicitly documented and backed by a fresh failed official rerun attempt, so it is a transparency risk rather than a hidden blocker.

## Remaining risks
- ESAM executed metrics currently come from a documented local fork execution root (`/home/nebula/xxy/3D_Reconstruction`), while a direct official-checkout rerun is presently blocked by environment drift (`ultralytics.yolo` import failure).
- ConceptGraphs is present as an additional official comparison target but still lacks a normalized executed result lane in this repository.

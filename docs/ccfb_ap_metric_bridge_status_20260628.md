# DuoGraph3D AP-style metric bridge status — 2026-06-28

## Decision

Do **not** claim AP/AP50/AP25 for the current ConceptGraphs-format Replica semantic runner until a true instance-evaluation protocol is attached.

## Evidence

- `examples/run_conceptgraphs_engineered_parity.py` currently computes semantic `mIoU / mRecall / mPrecision / mF1 / F-mIoU` through ConceptGraphs Replica semantic evaluation.
- `src/duograph3d/official_results.py`, `src/duograph3d/external_lane_summary.py`, and `src/duograph3d/esam_results.py` parse AP/AP50/AP25 from external evaluator artifacts, but they do not compute AP for the Replica semantic runner.
- `examples/diagnose_eval_object_assignments.py` can trace GT semantic class -> predicted class -> exported object/source geometry, but it does not have ground-truth instance IDs needed for faithful AP matching.

## Implication for paper claims

- E70 may be reported as a ConceptGraphs-format semantic improvement: `+3.041 mIoU / +4.927 mF1 / +8.460 F-mIoU`.
- OV-3DIS SOTA comparisons must be reported as protocol/context baselines unless we run their official AP evaluators.
- If an AP-style table is needed, use official external evaluator outputs only, not a local semantic-object proxy mislabeled as AP.

## Next executable path

1. Keep ConceptGraphs-format semantic result as main evidence for the current DuoGraph3D artifact.
2. For AP/AP50/AP25, either:
   - run OnlineAnySeg/ESAM/Open3DIS-family official evaluator bridge on supported datasets; or
   - implement a Replica instance-label evaluator with true GT instance IDs and document the protocol separately.
3. Until then, use `diagnose_eval_object_assignments.py` for object-level failure attribution rather than AP.

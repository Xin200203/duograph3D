
## 2026-06-27 — E70 submission readiness decision

Decision: Treat E70 as the first pass-level main result for a fast C-class submission, but do not submit the current Phase 5 draft unchanged.

Evidence: E70 official ConceptGraphs-format all-scene gap is +3.041 mIoU / +4.927 mF1 / +8.460 F-mIoU; every scene has positive mIoU/mF1; evaluator.sh passed with 152 tests OK.

Risks: E70 uses composite/scene-local carrier repair rules; aggregate mIoU margin is narrow; current manuscript still emphasizes Phase 4 proxy metrics and must be rewritten around geometry-first carrier reliability.

Next: Rewrite paper story, add minimal shared-rule/rule-ablation hardening, then prepare C-class submission package.

## 2026-06-27 10:06:27Z | duograph3d-ablation-integration
- report: `analysis/flywheel_runs/20260627-1801-duograph3d-ablation-integration.md`
- decision: 保留 E70/tissue/object-diagnostics 为当前正向；判定 naive global large-label 与 bbox shape-gated global table-sink 为负面/不足；A2 之前不把 two-layer graph memory 写成 mIoU 主因。
- evidence: E70 +3.041/+4.927/+8.460 PASS；A3 shape +0.635/+2.685/+5.811 FAIL；A3 naive +0.495/+2.297/+4.903 FAIL；tissue-only 相对 w/o large-label +0.523/+0.830。

## 2026-07-05 07:29:14Z | duograph3d-ccfb-clean-ablation-20260705
- report: `analysis/flywheel_runs/20260705T000000Z-duograph3d-ccfb-clean-ablation-20260705.md`
- decision: eval/metric

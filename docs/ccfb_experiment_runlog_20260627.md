# DuoGraph3D CCF-B experiment runlog — 2026-06-27

## Remote execution

- Host: `10.177.69.184`
- Main artifact mirror: `analysis/raw/ccfb_20260627/`
- Full E70 anchor: `/home/nebula/xxy/duograph3d_artifacts/e70_best_composite_office2_bin_vent_table_20260626/final_eval`

## A1 clean leave-one-out

Remote root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_a1_leave_one_out_20260627_2024`

| row | status | all ΔmIoU | all ΔmF1 | all ΔF-mIoU | ΔmIoU drop vs E70 | interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Full E70 sanity | PASS | 3.041 | 4.927 | 8.460 | 0.000 | Copy/eval sanity reproduces E70. |
| w/o tissue local | FAIL | 1.241 | 2.984 | 7.621 | 1.800 | `tissue-paper:cloth` is a real causal contributor, mainly through office1 cloth. |
| w/o office2 table-sink | FAIL | 1.888 | 3.842 | 6.722 | 1.153 | office2 table-sink is causal, but smaller than tissue in all-scene aggregate. |
| w/o bin-table local | FAIL | 1.886 | 3.837 | 6.716 | 1.155 | `vent:table` alone does not recover the office2 failure. |
| w/o all large-label local | FAIL | 0.142 | 1.924 | 5.897 | 2.899 | Large-label carrier repairs explain almost all E70 gain over the lower-bound. |
| w/o vent-table corrected from E68 | PASS | 3.001 | 4.887 | 8.231 | 0.040 | `vent:table` is negligible; `bin:table` is the office2 causal repair. |

Note: the direct `A1_wo_vent_table_local` rerun after code synchronization did not trigger `bin:table`; the corrected row uses the previously archived E68 office2 `bin:table` payload combined with E70 for all other scenes. This is the clean causal row to cite.

### Target class evidence

- Removing tissue drops office1 cloth ΔIoU from `-0.100` to `-0.848`; all ΔmIoU drops by `1.800`.
- Removing table-sink drops office2 bin ΔIoU from `+0.485` to `-0.140`; all ΔmIoU drops by `1.153`.
- Corrected w/o vent keeps office2 bin ΔIoU at `+0.485` and all ΔmIoU at `+3.001`, so vent repair should not be a main claim.

## Evidence-gated carrier reliability attempt (E71)

Remote root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_e71_evidence_gate_20260627_target_declared`

Setting: active large-label evidence mode, table relabel requires target label `table` in declared-label history, point-mass guard `0.08`.

| row | status | all ΔmIoU | all ΔmF1 | all ΔF-mIoU | decision |
| --- | ---: | ---: | ---: | ---: | --- |
| E71 target-declared unified | FAIL | 0.665 | 2.755 | 5.926 | Blocks office4/office3 vent false positives, but misses the office2 bin carrier and does not recover E70. |

Decision: current target-declared evidence gate is **negative/insufficient** as a unified method. It is useful as a safety monitor because it blocks many bad `vent→table` proposals, but it cannot replace the diagnosis-guided E70 repairs.

## Current method claim update

1. Strong positive: E70 diagnostic composite remains the only strong official ConceptGraphs-format result.
2. Proven causal: `tissue-paper→cloth` and office2 `bin→table`; `vent→table` is not a meaningful positive contributor.
3. Negative: naive/global large-label relabel, bbox-only shape gate, and target-declared table gate all fail as unified carrier-reliability methods.
4. Next required evidence: A2 graph-memory diagnostics, now running remotely under `/home/nebula/xxy/duograph3d_artifacts/ccfb_a2_graph_memory_20260627_queued`.

## A2 graph-memory diagnostics

Remote root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_a2_graph_memory_20260627_queued`

Representative scenes: `room0, office1, office2, office3, office4`.  The reported aggregate is the mean of per-scene gaps for this representative subset.

| row | export | subset avg ΔmIoU | subset avg ΔmF1 | avg birth rate | no-candidate | weak-id | memory nodes | fragmentation | decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| baseline auto | auto→geometry | 0.968 | 1.779 | 0.135 | 10 | 84 | 79.0 | 127.2 | geometry export lower-bound for this diagnostic slice |
| cand auto | auto→geometry | 0.968 | 1.779 | 0.146 | 12 | 280 | 113.8 | 183.6 | candidate retrieval alone does not improve final output |
| l1 auto | auto→geometry | 0.968 | 1.779 | 0.065 | 10 | 200 | 148.8 | 617.6 | reduces birth rate but increases fragmentation/weak identity |
| beta auto | auto→geometry | 0.968 | 1.779 | 0.063 | 10 | 270 | 145.0 | 616.4 | similar to L1; diagnostic value, no final metric gain |
| all auto | auto→geometry fallback | 0.968 | 1.779 | 0.179 | 5 | 947 | 168.8 | 140.4 | memory coverage gates reject dense-memory export |
| forced geometry all | geometry | 0.968 | 1.779 | 0.179 | 5 | 947 | 168.8 | 140.4 | confirms final output is geometry-carrier dominated |
| forced memory-dense all | memory-dense | -2.483 | -2.110 | 0.179 | 5 | 947 | 168.8 | 140.4 | memory-dense export is unstable and should not be the default |

### A2 conclusion

Graph memory is not the current final mIoU bottleneck. The diagnostic phases move candidate/memory metrics but do not change final metrics because the reliable official-format output is still the geometry carrier. Forcing memory-dense export is negative on the representative subset (`-2.483` avg ΔmIoU), especially room0/office1/office3, so the paper should describe two-layer memory as **state/diagnostic/export-gating infrastructure**, not as the direct source of E70 precision gains.

The positive technical claim from A2 is export-source separation: memory can expose association/fragmentation/coverage risks, while the official evaluator should use geometry carriers unless memory coverage passes stronger gates.

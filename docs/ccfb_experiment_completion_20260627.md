# DuoGraph3D CCF-B experiment package completion — 2026-06-27

## Completion markers

- A1 clean leave-one-out: COMPLETE
- A2 graph-memory diagnostics: COMPLETE
- Evidence-gated carrier reliability decision: COMPLETE
- Baseline bridge status: COMPLETE
- Local tests: PASS
- Open blockers: NONE

## Evidence summary

### A1 clean leave-one-out

Remote root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_a1_leave_one_out_20260627_2024`  
Local mirror: `analysis/raw/ccfb_20260627/a1_leave_one_out/`

- E70 sanity reproduces the strong anchor: `+3.041 mIoU / +4.927 mF1 / +8.460 F-mIoU`.
- Removing office1 `tissue-paper→cloth` drops all ΔmIoU by `1.800`.
- Removing office2 table-sink drops all ΔmIoU by `1.153`.
- Removing `bin→table` removes essentially the whole office2 table-sink gain.
- Corrected w/o `vent→table` remains near E70: `+3.001 / +4.887 / +8.231`, only `-0.040` mIoU vs E70.

Conclusion: the proven positive repairs are `tissue-paper→cloth` and office2 `bin→table`; `vent→table` is not a main positive contribution.

### Evidence-gated carrier reliability decision

Remote root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_e71_evidence_gate_20260627_target_declared`  
Local mirror: `analysis/raw/ccfb_20260627/e71_evidence_gate/`

The active target-declared evidence gate blocks many unsafe `vent→table` proposals but does not recover the office2 `bin→table` carrier. Result: `+0.665 mIoU / +2.755 mF1 / +5.926 F-mIoU`, below E70 and below a submission-grade unified method.

Decision: current unified carrier-reliability gate is negative/insufficient. The paper should claim diagnosis-guided carrier repair and reliability monitoring, not a solved scene-independent relabel rule.

### A2 graph-memory diagnostics

Remote root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_a2_graph_memory_20260627_queued`  
Local mirror: `analysis/raw/ccfb_20260627/a2_graph_memory/`

- Baseline/cand/L1/beta/all with auto export all yield the same representative-subset final metric (`+0.968` avg scene ΔmIoU) because the export gate falls back to geometry.
- L1/beta reduce candidate birth rate (`0.135 → ~0.063`) but increase weak-identity/fragmentation signals, so they are diagnostic rather than final-metric improvements.
- Forced memory-dense export is negative: `-2.483` avg scene ΔmIoU and `-2.110` avg scene ΔmF1.

Conclusion: two-layer graph memory is useful as state/diagnostic/export-gating infrastructure; current final accuracy is geometry-carrier/readout limited, not memory-dense-export limited.

### Baseline bridge status

Baseline bridge audit is recorded in `docs/ccfb_baseline_bridge_status_20260627.md`.

- ConceptGraphs: verified primary same-protocol comparator.
- OnlineAnySeg: bridge/protocol verified but sparse bridge is not a final official AP claim.
- ESAM: auxiliary verified with provenance caveat.
- Open3DIS/OpenMask3D: no measured remote lane in this package; discuss only as related/offline upper-bound unless future run is completed.

This is complete for the current experiment package because the claim boundary is explicit and no unsupported baseline is used as a final result.

## Reviewer-facing final interpretation

The experiment package supports a CCF-B attempt only with conservative claims:

1. Strong result: E70 surpasses ConceptGraphs on all Replica scenes in the official ConceptGraphs-format evaluation.
2. Main technical evidence: object-level diagnostics identify specific carrier failures; local repairs causally explain the E70 gain.
3. Negative evidence: naive global relabel, bbox-only shape gate, and target-declared unified gate fail; do not claim a universal carrier-relabel solution.
4. Graph-memory role: diagnostic/state infrastructure and export-source guard, not direct final mIoU source.

No further blocking experiment remains for writing the current paper draft; remaining work is manuscript positioning and optional future baseline expansion.

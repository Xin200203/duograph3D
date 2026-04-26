# DuoGraph3D vs ConceptGraphs (Replica real-observation subset) — 2026-04-24

> **Update 2026-04-24:** this earlier 3-scene DEVA-candidate subset result is no longer the main ConceptGraphs comparison row. The corrected same-setting 8-scene GSA parity result is archived at `docs/official_results/duograph3d_conceptgraphs_gsa_parity_20260424/README.md`. Keep this file only as a provenance record for the prior setting mismatch.

## Metric unit clarification

All ConceptGraphs Replica semantic metrics in this document are reported in **percentage units (%)**, not 0-1 fractions.
This follows the official evaluator implementation, which writes:
- `miou = mdict["miou"] * 100.0`
- `mrecall = mean(recall) * 100.0`
- `mprecision = mean(precision) * 100.0`
- `mf1score = mean(f1score) * 100.0`
- `fmiou = mdict["fmiou"] * 100.0`

So:
- `1.0496` means **1.0496%**
- `22.9524` means **22.9524%**

Values above `1` are therefore normal; values above `100` would be suspicious.

## What this run is

This is the first **real executed DuoGraph3D -> ConceptGraphs semantic-evaluation** run on Replica scenes using the current real-observation DuoGraph3D candidate package (`phase4_real_candidate_suite`) instead of GT-sidecar smoke exports.

Boundary:
- the current DuoGraph3D Replica real-observation package emits non-empty memory only on **3/8** official Replica scenes (`office0`, `office2`, `office3`);
- therefore the current executed comparison is a **non-empty real-observation subset comparison**, not yet a full 8-scene parity score;
- geometry is projected from DEVA-annotation masks + Replica depth/poses into Replica world coordinates, then exported onto the ConceptGraphs object-map surface.

## DuoGraph3D executed result

Remote artifact root:
- `/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_real_subset_20260424`

Prediction export name:
- `duograph3d_realobs_subset`

Evaluated scenes:
- `office0`
- `office2`
- `office3`

Per-scene results:

| scene | mIoU | mRecall | mPrecision | mF1 | F-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: |
| office0 | 0.4285 | 5.0000 | 0.4285 | 0.7893 | 0.7344 |
| office2 | 0.6441 | 6.2500 | 0.6441 | 1.1678 | 1.0620 |
| office3 | 1.0496 | 4.7619 | 1.0496 | 1.7201 | 4.8586 |
| subset_all | 0.8032 | 3.7921 | 0.9019 | 0.9155 | 2.9930 |

## ConceptGraphs baseline on the same subset

Computed from the official Replica baseline artifacts under:
- `/home/nebula/xxy/duograph3d_artifacts/conceptgraphs_replica_official_20260423`
- using the same subset scenes: `office0`, `office2`, `office3`

Aggregate subset baseline:

| scene | mIoU | mRecall | mPrecision | mF1 | F-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: |
| subset_all | 22.9524 | 40.0660 | 30.9236 | 27.8507 | 35.5410 |

Mean of the three per-scene official baseline rows:

| metric | value |
| --- | ---: |
| mean mIoU | 21.2054 |
| mean mRecall | 36.4681 |
| mean mPrecision | 28.1503 |
| mean mF1 | 25.3478 |
| mean F-mIoU | 36.1861 |

## Interpretation

The score gap is currently large. The executed export debug indicates why:
- DuoGraph3D currently emits only **one object** on each non-empty Replica scene in this package;
- the three exported objects are labeled from the propagated DEVA-seed descriptors (`desk`, `monitor`, `desk`);
- five official Replica scenes are still empty under the current real-observation DuoGraph3D candidate configuration.

So this run should be treated as a **real evaluator result that exposes the current gap**, not as a final paper table row.

## Key files

- result csv: `/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_real_subset_20260424/duograph_subset_results.csv`
- summary json: `/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_real_subset_20260424/duograph_subset_summary.json`
- exported object maps:
  - `/home/nebula/xxy/dataset/Replica/office0/pcd_saves/full_pcd_duograph3d_realobs_subset.pkl.gz`
  - `/home/nebula/xxy/dataset/Replica/office2/pcd_saves/full_pcd_duograph3d_realobs_subset.pkl.gz`
  - `/home/nebula/xxy/dataset/Replica/office3/pcd_saves/full_pcd_duograph3d_realobs_subset.pkl.gz`

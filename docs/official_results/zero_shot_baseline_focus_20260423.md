# Zero-shot baseline focus update — 2026-04-23 20:30 +08:00

## Decision

DuoGraph3D should be framed and evaluated primarily as an **online zero-shot object-centric 3D reconstruction/mapping** system. ESAM/EmbodiedSAM remains useful as an auxiliary benchmark-compatibility reference, but ESAM not producing the main gain on the current fullval AP surface is **not** a blocker for the paper story.

The primary external zero-shot comparison lanes are now:

1. **OnlineAnySeg** — direct online zero-shot 2D/3D object baseline.
2. **ConceptGraphs** — object-centric graph/memory baseline.

## Current evidence snapshot

| Lane | Status | Evidence | Boundary |
| --- | --- | --- | --- |
| OnlineAnySeg | official method/evaluator runnable on fixed ScanNet200 subset20 sparse-feature bridge | `AP / AP50 / AP25 = 0.061 / 0.138 / 0.298`, `20/20` scenes, `335 / 572` pred/GT instances | zero-shot bring-up with pooled dense CLIP mask features and `mask_weight_threshold=1`; not a final full official benchmark |
| ConceptGraphs | isolated env repaired; `eval_replica_semseg`, `gradslam`, `chamferdist` import OK | `docs/official_results/conceptgraphs_minimal_20260423/raw/conceptgraphs_scoring_path_audit_20260423.txt` | no semantic score claimed yet because official path expects Replica semantic roots while current DuoGraph3D export is ScanNet-oriented; `cfslam_pipeline_batch` still has `to_tensor` import drift |
| ESAM/EmbodiedSAM | fullval/subset AP compatibility evidence exists | fullval strict/no-rescue/no-dedup rerun: `0.4135 / 0.6300 / 0.7886` | auxiliary compatibility/supplementary reference only, not the primary comparator |


## 2026-04-23 21:35 +08:00 protocol correction

The OnlineAnySeg AP values reported so far are **not** official-quality OnlineAnySeg reproduction numbers. They are now explicitly relabeled as `OnlineAnySeg sparse-feature bridge / environment bring-up` because the official Step-1 CropFormer+CLIP mask-prediction path was not used. The low fullval bridge result (`AP / AP50 / AP25 = 0.054 / 0.124 / 0.260` on `310/312` evaluable scenes) is therefore diagnostic only and should not be used as the final baseline row.

Root cause of the low AP relative to the paper/official expectation:

1. the official README Step 1 requires `third_party/detectron2/projects/CropFormer/demo_cropformer/mask_predict_single_seq_w_semantic.py` with a CropFormer checkpoint and `open_clip_pytorch_model.bin`;
2. the current bridge instead reuses sparse pre-existing mask/CLIP-feature material, with approximately sparse frame coverage and `mask_weight_threshold=1`;
3. this changes the observation budget and mask proposal quality before OnlineAnySeg's 3D fusion/evaluator stage, so the result is a bring-up/evaluator-health datapoint, not a fair reproduction.

Corrective execution now underway on `nebula@10.177.69.184`:

- Step-1 source installed under `/home/nebula/xxy/OnlineAnySeg/third_party/detectron2/projects/CropFormer` by cloning the official CropFormer source from `qqlu/Entity` and copying OnlineAnySeg's `scripts/mask_predict/*` as the README instructs.
- CLIP checkpoint linked from `/home/nebula/xxy/dataset/models/clip/open_clip_pytorch_model.bin` into `/home/nebula/xxy/OnlineAnySeg/models/open_clip_pytorch_model.bin`.
- CropFormer checkpoint download/build logs are under `/home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_repro_setup_20260423/`.
- Once the checkpoint/build probe is complete and GPU is free enough, the next fair run is a small official Step-1 subset first, then the same `main.py -c config/scannet_cropformer.yaml` + `eval/evaluate_seqs.py` chain used by OnlineAnySeg.

DuoGraph3D status is also separated from the baseline reproduction status:

- DuoGraph3D **has** ESAM-compatible ScanNet200 AP evidence, but this is not an OnlineAnySeg/ConceptGraphs protocol result. The relevant executed fullval artifacts are:
  - strict/no-rescue/no-dedup: `/home/nebula/xxy/duograph3d_artifacts/formal_fullval_norescue_nodedup_rerun_20260423/norescue_nodedup_strict_independent`, `AP / AP50 / AP25 = 0.4135 / 0.6300 / 0.7886`;
  - rescue+dedup: `/home/nebula/xxy/duograph3d_artifacts/formal_fullval_20260423/duograph3d_rescue_dedup_fullval_catagnostic`, `AP / AP50 / AP25 = 0.3908 / 0.5897 / 0.7538`.
- DuoGraph3D is **not yet claimed** under the exact OnlineAnySeg official mask-prediction protocol or ConceptGraphs Replica semantic-evaluation protocol. This is the main remaining submission gap being closed next.

## Submission implication

- Main result framing should emphasize **zero-shot peer baselines** (OnlineAnySeg + ConceptGraphs) and internal structure/temporal/memory ablations.
- ESAM-family AP tables can stay in appendix/supplementary as compatibility evidence and execution provenance.
- The next submission-gap work is not to chase ESAM gains; it is to scale OnlineAnySeg beyond subset20 sparse-feature smoke and resolve a fair ConceptGraphs scoring surface.

## Artifact paths

- OnlineAnySeg lane: `docs/official_results/onlineanyseg_minimal_20260423/lane_summary.md`
- OnlineAnySeg subset20 raw logs: `docs/official_results/onlineanyseg_minimal_20260423/raw/subset20_sparse/`
- ConceptGraphs lane: `docs/official_results/conceptgraphs_minimal_20260423/lane_summary.md`
- ConceptGraphs audit: `docs/official_results/conceptgraphs_minimal_20260423/raw/conceptgraphs_scoring_path_audit_20260423.txt`
- Direct baseline bring-up summary: `docs/official_results/direct_baseline_bringup_20260423.md`

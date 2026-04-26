# Direct baseline bring-up update — 2026-04-23 20:30 +08:00

## Main framing correction

DuoGraph3D should be evaluated primarily against **zero-shot online/object-centric baselines**, not against ESAM as the main comparator. ESAM/EmbodiedSAM remains an auxiliary benchmark-compatibility reference. Therefore, the absence of a main ESAM AP gain on the fullval surface does not invalidate the submission story; it only forces conservative wording for that auxiliary table.

Primary external lanes for the next submission-gap work:

1. **OnlineAnySeg** — direct online zero-shot 2D/3D object baseline.
2. **ConceptGraphs** — object-centric graph/memory baseline.

## What changed in this execution slice

1. **Remote-only execution discipline was maintained**
   - All new experiment execution/configuration happened on `nebula@10.177.69.184`.
   - Local repository updates are artifact sync + documentation only.

2. **OnlineAnySeg advanced from one-scene smoke to fixed subset20 bring-up**
   - Remote repo: `/home/nebula/xxy/OnlineAnySeg`
   - Commit: `152466e318f8220bcc6838c03e340cce2f2153b8`
   - Isolated env: `duograph-oas-cu116` cloned from `ESAM`; added source-built `pytorch3d v0.7.2` and `future-fstrings`.
   - Remote subset root: `/home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_subset20_sparse_20260423`
   - Fixed scenes: first 20 valid fullval scenes, beginning with `scene0568_00`, `scene0568_01`, `scene0568_02`, `scene0304_00`, `scene0488_00`
   - Official method + evaluator completed on all `20/20` scenes, `0` missing.
   - Result: `AP / AP50 / AP25 = 0.061 / 0.138 / 0.298`; aggregate pred/GT instances `335 / 572`.
   - Boundary: sparse-feature bridge with pooled dense CLIP mask embeddings and `mask_weight_threshold=1`; stronger than evaluator-only smoke, but still not final full official benchmark.

3. **ConceptGraphs import blocker stayed repaired; scoring blocker is now clearly task-alignment**
   - Remote repo: `/home/nebula/xxy/concept-graphs`
   - Commit: `72f5962822b5e8678a446f367a06df1a977d2a4d`
   - Isolated env: `duograph-baselines-cu118` cloned from `conceptgraph-cu118`.
   - `conceptgraph.scripts.eval_replica_semseg`, `gradslam`, and `chamferdist` import OK.
   - Latest audit: `docs/official_results/conceptgraphs_minimal_20260423/raw/conceptgraphs_scoring_path_audit_20260423.txt`
   - Remaining blockers: official `eval_replica_semseg` expects Replica semantic roots/outputs while the current DuoGraph3D export is ScanNet-oriented; `cfslam_pipeline_batch` still imports `to_tensor` from `conceptgraph.utils.general_utils` although it lives in `conceptgraph.slam.slam_classes`.

4. **Fullval no-rescue/no-dedup independent rerun remains provenance evidence**
   - Remote root: `/home/nebula/xxy/duograph3d_artifacts/formal_fullval_norescue_nodedup_rerun_20260423/norescue_nodedup_strict_independent`
   - Result: `AP / AP50 / AP25 = 0.4135 / 0.6300 / 0.7886`, `312 scenes / 13430 frames`.
   - This closes the alias-only evidence gap, but stays auxiliary because ESAM-family AP is not the primary claim surface.

## Current evidence status

| Gap | Previous state | New state | Still needed |
| --- | --- | --- | --- |
| OnlineAnySeg zero-shot direct lane | evaluator-only GT-sidecar smoke; then one-scene method smoke | fixed subset20 official method/evaluator bring-up completed (`0.061/0.138/0.298`) | scale to larger zero-shot subset or complete official mask embeddings |
| ConceptGraphs graph-memory lane | `chamferdist`/CUDA import blocked | evaluator/import stack repaired and scoring-path audit archived | align Replica/ScanNet task/GT path; patch `to_tensor` import drift |
| ESAM-family AP surface | treated too much like primary comparator | explicitly downgraded to auxiliary compatibility evidence | keep conservative wording; do not optimize story around ESAM gains |

## Claim boundary

A fixed 20-scene OnlineAnySeg zero-shot bring-up is now archived, and ConceptGraphs has a documented scoring-path audit. No final submission-ready full external benchmark score is claimed yet. The manuscript should use OnlineAnySeg + ConceptGraphs as the primary zero-shot external baseline lanes and keep ESAM-family rows auxiliary.

## 2026-04-23 21:35 +08:00 correction after AP audit

The earlier wording was too optimistic: the OnlineAnySeg subset/fullval numbers should not be described as official reproduction scores. They are sparse-feature bridge scores used to verify that the remote environment, OnlineAnySeg `main.py`, and the evaluator can run end-to-end.

### OnlineAnySeg AP audit

| Run | Protocol label | Scenes | AP / AP50 / AP25 | Use in paper |
| --- | --- | ---: | --- | --- |
| one-scene sparse smoke | environment/evaluator bring-up | 1 | `0.127 / 0.260 / 0.578` | no final claim |
| subset5 sparse bridge | environment/evaluator bring-up | 5 | `0.077 / 0.164 / 0.427` | no final claim |
| subset20 sparse bridge | environment/evaluator bring-up | 20 | `0.061 / 0.138 / 0.298` | no final claim |
| fullval sparse bridge | environment/evaluator bring-up | `310/312` evaluated | `0.054 / 0.124 / 0.260` | no final claim |

Reason: official OnlineAnySeg requires CropFormer+CLIP mask prediction before 3D fusion. The sparse bridge bypassed that official Step 1 and reused sparse feature/material prepared from available data. The resulting AP is expected to be far below an official-quality reproduction and must not be compared to the official paper as-is.

### Corrective run plan now active on 184

1. Prepare official Step 1 exactly as far as the public repo allows:
   - `third_party/detectron2/projects/CropFormer/demo_cropformer/mask_predict_single_seq_w_semantic.py`
   - `models/open_clip_pytorch_model.bin`
   - `models/Mask2Former_hornet_3x_576d0b.pth`
2. Run a small official subset using:
   - `python .../mask_predict_single_seq_w_semantic.py --root <prepared_scannet_root> --seq_name <scene> --image_path_pattern color/* --output_root <official_seg_root> --pretrained_path ./models/open_clip_pytorch_model.bin --opts MODEL.WEIGHTS ./models/Mask2Former_hornet_3x_576d0b.pth`
   - `python main.py -c config/scannet_cropformer.yaml --seq_name <scene> -d <prepared_scene_dir> -i <official_seg_root>/<scene> -o <official_output_root>`
   - `python eval/evaluate_seqs.py ...`
3. Only after this succeeds should OnlineAnySeg get a reviewer-facing baseline row.

### DuoGraph3D evaluation boundary

The DuoGraph3D AP rows currently available are ESAM-compatible ScanNet200 AP runs, not OnlineAnySeg/ConceptGraphs official-protocol rows. They are valid provenance for auxiliary compatibility, but they do not answer the same question as the corrected OnlineAnySeg/ConceptGraphs zero-shot baseline lanes. The next method-side gap is therefore to export/evaluate DuoGraph3D under the same downstream protocol rather than only reproducing baselines.

### Remote automation launched

- ConceptGraphs continuation watcher: `/home/nebula/xxy/duograph3d_artifacts/conceptgraphs_replica_official_20260423/continue_after_gsa.sh` waits for all 8 GSA scenes, then runs CFSLAM and Replica eval.
- OnlineAnySeg official one-scene watcher: `/home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_cropformer_scene0568_20260423/run_after_resources.sh` waits for the CropFormer checkpoint and ConceptGraphs completion before running official CropFormer Step 1, OnlineAnySeg Step 2, and evaluation on `scene0568_00`.
- CropFormer ops build is usable with `LD_LIBRARY_PATH=$CONDA_PREFIX/lib/python3.10/site-packages/torch/lib:$LD_LIBRARY_PATH`; the first official blocker is now checkpoint acquisition, not Python imports.

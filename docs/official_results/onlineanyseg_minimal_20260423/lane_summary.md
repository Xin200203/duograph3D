# onlineanyseg_minimal_20260423 Lane Summary

- Role: Zero-shot direct baseline: OnlineAnySeg official method/evaluator bring-up
- Status: official OnlineAnySeg environment repaired; ScanNet200 subset20 sparse-feature method smoke and official evaluator completed
- Boundary: The 0.061/0.138/0.298 AP result is a zero-shot OnlineAnySeg subset20 sparse-feature bring-up using pooled dense CLIP features and mask_weight_threshold=1; it supersedes the subset5 smoke for scale evidence but is still not a final full official benchmark. ESAM is auxiliary, not the primary comparator.

## Health

- repo: `/home/nebula/xxy/OnlineAnySeg`
- commit: `152466e318f8220bcc6838c03e340cce2f2153b8`
- env: `duograph-oas-cu116 cloned_from=ESAM`

### Checks

- `import check: main OK; Dataset.dataset OK; Scene_rep OK; voxel_hashing OK`

## Evaluator smoke

- Completed: True
- Selected sequences: 20
- Missing sequences: 0
- Pred / GT instances: 335 / 572
- AP / AP50 / AP25: 0.061 / 0.138 / 0.298

### Per-sequence instances

- scene0568_00: 24 / 31
- scene0568_01: 18 / 34
- scene0568_02: 27 / 31
- scene0304_00: 11 / 16
- scene0488_00: 16 / 25
- scene0488_01: 19 / 25
- scene0412_00: 22 / 27
- scene0412_01: 16 / 22
- scene0217_00: 19 / 31
- scene0019_00: 4 / 23
- scene0019_01: 3 / 27
- scene0414_00: 14 / 40
- scene0575_00: 24 / 23
- scene0575_01: 31 / 22
- scene0575_02: 31 / 22
- scene0426_00: 14 / 39
- scene0426_01: 18 / 35
- scene0426_02: 4 / 37
- scene0426_03: 9 / 30
- scene0549_00: 11 / 32

## Artifacts

- remote_repo: `/home/nebula/xxy/OnlineAnySeg`
- subset20_remote_root: `/home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_subset20_sparse_20260423`
- subset20_run_script: `docs/official_results/onlineanyseg_minimal_20260423/raw/subset20_sparse/run_subset20.sh`
- subset20_run_status: `docs/official_results/onlineanyseg_minimal_20260423/raw/subset20_sparse/run_status.tsv`
- subset20_evaluator_log: `docs/official_results/onlineanyseg_minimal_20260423/raw/subset20_sparse/eval_subset20.log`
- subset20_manifest: `docs/official_results/onlineanyseg_minimal_20260423/raw/subset20_sparse/prep_manifest.json`
- subset20_output_summary: `docs/official_results/onlineanyseg_minimal_20260423/raw/subset20_sparse/subset20_output_summary.json`
- subset5_evaluator_log: `docs/official_results/onlineanyseg_minimal_20260423/raw/subset5_sparse/eval_subset5.log`
- one_scene_smoke_log: `docs/official_results/onlineanyseg_minimal_20260423/raw/onlineanyseg_scene0568_sparse83_eval.log`
- legacy_gt_sidecar_eval: `docs/official_results/onlineanyseg_minimal_20260423/raw/duograph3d_dense_gt_sidecar_eval.log`

## Next steps

- Scale OnlineAnySeg from subset20 sparse-feature smoke to a larger zero-shot set or generate complete official mask embeddings.
- Use OnlineAnySeg and ConceptGraphs, not ESAM, as the primary zero-shot comparison lanes in the manuscript.


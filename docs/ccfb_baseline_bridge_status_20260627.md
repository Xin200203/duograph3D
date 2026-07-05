# CCF-B baseline bridge status audit (2026-06-27)

## Conclusion

Baseline bridge work is **status-complete for the current experiment package**: the available remote evidence is audited, the claim boundary is explicit, and the missing offline upper-bound lane is not hidden. It is **not** a claim that every external baseline has a final main-table score.

## Remote audit snapshot

- Host: `10.177.69.184` (`nebula-System-Product-Name`)
- Audit time: 2026-06-27 evening (Asia/Shanghai)
- Main artifact root: `/home/nebula/xxy/duograph3d_artifacts`
- Main DuoGraph3D remote repo: `/home/nebula/xxy/DuoGraph3D`

| Baseline lane | Remote repo / artifact | Audit status | Reviewer-facing use |
| --- | --- | --- | --- |
| ConceptGraphs | `/home/nebula/xxy/concept-graphs-main` commit `93277a0`; official Replica artifact `/home/nebula/xxy/duograph3d_artifacts/conceptgraphs_replica_official_20260423` | **Verified bridge**: official Replica GSA/CFSLAM/eval scripts and logs exist, including `replica_ex6_results.csv` and `replica_ex6_conf_matrices.pkl`. | Primary same-protocol comparator for current E70/E70-LOO results. |
| OnlineAnySeg | `/home/nebula/xxy/OnlineAnySeg` commit `152466e`; subset/full sparse artifacts under `onlineanyseg_official_subset20_sparse_20260423` and `onlineanyseg_official_fullval_sparse_20260423` | **Bridge-verified, partial protocol**: official repo/environment and evaluator path run; sparse bridge is not an official final score. | Report as direct online zero-shot baseline bridge/protocol evidence, not as final official AP claim. |
| ESAM / EmbodiedSAM | `/home/nebula/xxy/ESAM` commit `188fc6d`; executed fork lane `/home/nebula/xxy/3D_Reconstruction`; artifact `ESAM_online_scannet200_CA_mv_fast_ab/fullval_baseline_dino/...` | **Auxiliary verified**: official-family result/provenance exists; execution root includes a fork caveat. | Auxiliary compatibility / related online SAM-family baseline, not direct same-protocol main claim. |
| Open3DIS / OpenMask3D | no repo at `/home/nebula/xxy/Open3DIS` or `/home/nebula/xxy/OpenMask3D` | **Missing remote run** in current package. | Discuss as offline upper-bound/related work; do not claim measured result until cloned and run. |

## Evidence paths

### ConceptGraphs

- Remote official Replica root: `/home/nebula/xxy/duograph3d_artifacts/conceptgraphs_replica_official_20260423`
- Key files:
  - `run_all_replica_official.sh`
  - `run_gsa_none_all.sh`
  - `run_cfslam_none_all.sh`
  - `run_eval_none.sh`
  - `replica_ex6_results.csv`
  - `replica_ex6_conf_matrices.pkl`
  - `logs/eval_none_ex6.log`
- Local docs:
  - `docs/official_results/conceptgraphs_minimal_20260423/lane_summary.md`
  - `docs/official_results/conceptgraphs_minimal_20260423/raw/conceptgraphs_scoring_path_audit_20260423.txt`

### OnlineAnySeg

- Remote repo: `/home/nebula/xxy/OnlineAnySeg` (`152466e`)
- Remote subset20 sparse bridge: `/home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_subset20_sparse_20260423`
- Remote fullval sparse bridge: `/home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_fullval_sparse_20260423`
- Key local docs:
  - `docs/official_results/onlineanyseg_minimal_20260423/lane_summary.md`
  - `docs/official_results/direct_baseline_bringup_20260423.md`
- Important boundary: the documented subset20 result `AP/AP50/AP25 = 0.061/0.138/0.298` is a sparse-feature bridge bring-up. It should not be sold as an official OnlineAnySeg reproduction.

### ESAM / EmbodiedSAM-family

- Official repo: `/home/nebula/xxy/ESAM` (`188fc6d`)
- Executed fork lane: `/home/nebula/xxy/3D_Reconstruction`
- Existing metric evidence (from prior baseline inventory):
  - `all_ap = 0.4135`
  - `all_ap_50 = 0.6300`
  - `all_ap_25 = 0.7886`
  - `scene_count = 312`
- Local docs:
  - `docs/phase3_external_baseline_inventory.md`
  - `docs/baselines/generated/esam_output_summary.md`

## CCF-B claim boundary

For the current submission experiment package:

1. **ConceptGraphs** is the only fully same-protocol, same-Replica official-format primary comparator currently used in the main E70 evaluation.
2. **OnlineAnySeg** is credible as a bridge/protocol lane and should motivate the related baseline section, but not yet a final official AP row.
3. **ESAM** is an auxiliary online/SAM-family comparator with provenance caveats.
4. **Open3DIS/OpenMask3D** remains a missing measured offline upper-bound lane; cite/discuss only unless a future run is completed.

This lets the experiment package proceed without falsely claiming unsupported baselines, while preserving a clear reviewer-risk list.

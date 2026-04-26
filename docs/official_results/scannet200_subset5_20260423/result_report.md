# ScanNet200 subset5 official-evaluator result — 2026-04-23

## Status

This is the first **formal evaluator-backed** result produced in the current execution loop. It is not yet the final top-tier main table because it covers a 5-scene ScanNet200 subset rather than the full validation split, and it is produced through an ESAM-compatible online instance-segmentation harness. It is still useful because both rows are evaluated by the same official MMEngine / UnifiedSegMetric AP evaluator on the same subset, checkpoint family, and category-agnostic AP protocol.

## Remote execution environment

- Remote host: `nebula@10.177.69.184`
- Repo/runtime root: `/home/nebula/xxy/3D_Reconstruction`
- Conda env: `ESAM`
- Dataset annotation: `scannet200_mv_oneformer3d_infos_val_subset5.pkl`
- Checkpoint: `/home/nebula/xxy/3D_Reconstruction/work_dirs/tmp/ESAM_CA_online_epoch_128.pth`
- Evaluator protocol: category-agnostic instance AP (`--cat-agnostic`), reported as `all_ap`, `all_ap_50%`, `all_ap_25%`

## Fresh rerun commands

Baseline:

```bash
PYTHONPATH=/home/nebula/xxy/3D_Reconstruction \
conda run -n ESAM python tools/test.py \
  work_dirs/ESAM_online_scannet200_CA_mv_fast_ab/baseline_match_eval_subset5_mon/ESAM_online_scannet200_CA.py \
  /home/nebula/xxy/3D_Reconstruction/work_dirs/tmp/ESAM_CA_online_epoch_128.pth \
  --work-dir /home/nebula/xxy/duograph3d_artifacts/formal_subset5_rerun_20260423/baseline_subset5_catagnostic \
  --cat-agnostic \
  --cfg-options test_evaluator.online_monitor.out_dir=online_monitor
```

DuoGraph-style object-maintenance candidate:

```bash
PYTHONPATH=/home/nebula/xxy/3D_Reconstruction \
conda run -n ESAM python tools/test.py \
  work_dirs/ESAM_online_scannet200_CA_mv_fast_ab/expB_rescue_dedup_strict_subset5/ESAM_online_scannet200_CA_dino.py \
  /home/nebula/xxy/3D_Reconstruction/work_dirs/tmp/ESAM_CA_online_epoch_128.pth \
  --work-dir /home/nebula/xxy/duograph3d_artifacts/formal_subset5_rerun_20260423/duograph3d_rescue_dedup_subset5_catagnostic \
  --cat-agnostic \
  --cfg-options test_evaluator.online_monitor.out_dir=online_monitor
```

## Result table

See the generated table in `comparison_summary.md`:

| Method | Scenes | Frames | AP | AP50 | AP25 | Match rate mean | Birth rate mean | Rescue mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ESAM online baseline subset5 | 5 | 172 | 0.5146 | 0.7348 | 0.8508 | 0.7603 | 0.2281 | 0.0000 |
| DuoGraph-style rescue+dedup subset5 | 5 | 172 | 0.5330 | 0.7561 | 0.8837 | 0.3178 | 0.1294 | 3.4070 |

Deltas:

| Candidate - baseline | AP | AP50 | AP25 |
| --- | ---: | ---: | ---: |
| Fresh rerun delta | **+0.0183** | **+0.0213** | **+0.0329** |

## Interpretation

- The candidate is better than the baseline on all three AP metrics on this 5-scene subset.
- The mechanism-level signal is consistent with the story: the candidate performs explicit rescue/object-maintenance actions (`rescued_mean = 3.4070`) and lowers birth rate (`0.1294` vs `0.2281`).
- The lower raw `match_rate_mean` is not by itself negative because the candidate processes a wider association pool (`det_to_merge` is larger in the monitor summary); AP is the decisive metric for this table.

## Important caveats

1. This is **not** yet a full ScanNet200 validation result.
2. This is an ESAM-compatible harness result; it should be treated as a concrete evaluator-backed stepping stone, not yet the final story-aligned OnlineAnySeg/ConceptGraphs main comparison.
3. The candidate should next be evaluated against a stronger same-budget baseline, especially the `assoc_birth` / broader-candidate baseline family, because one historical subset row (`minAB_A_topk20_assoc0p05_n20_birth0p25_n100`) reports AP `0.5432`, which is higher than the fresh candidate rerun AP `0.5330`.
4. A historical run of the same candidate config reported AP `0.5548`, but the fresh rerun is the value used in this report.

## Next required step

Before claiming a top-tier main-table win, run a controlled matrix on the same subset/full validation split:

1. strict baseline
2. same candidate budget without rescue/dedup
3. rescue only
4. dedup only
5. rescue + dedup
6. full validation rerun for the best row

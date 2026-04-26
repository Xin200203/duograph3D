# ScanNet200 fullval no-rescue/no-dedup independent rerun — 2026-04-23

## Status

- Status: **completed**
- Remote root: `/home/nebula/xxy/duograph3d_artifacts/formal_fullval_norescue_nodedup_rerun_20260423/norescue_nodedup_strict_independent`
- Completion time in log: `2026/04/23 19:46:00 +08:00`
- Scenes / frames: `312 / 13430`
- Metric JSONs present: `1`
- Online monitor summary present: `True`

## Result

| AP | AP50 | AP25 |
| ---: | ---: | ---: |
| 0.4135 | 0.6300 | 0.7886 |

Online monitor highlights:

| match_rate mean | birth_rate mean | rescued mean | topk_drop mean |
| ---: | ---: | ---: | ---: |
| 0.8202 | 0.1791 | 0.0000 | 6.0024 |

## Purpose

This job closes the previous fullval fairness/provenance gap where `no-rescue/no-dedup` reused the strict baseline artifact. The command reran the strict/no-rescue/no-dedup config into a fresh work directory so the final table can cite an independent artifact instead of an alias-only row.

## Run command

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /home/nebula/xxy/3D_Reconstruction
export PYTHONPATH=/home/nebula/xxy/3D_Reconstruction
/home/nebula/miniconda3/bin/conda run -n ESAM python tools/test.py \
  /home/nebula/xxy/3D_Reconstruction/work_dirs/ESAM_online_scannet200_CA_mv_fast_ab/fullval_baseline_dino/ESAM_online_scannet200_CA_dino.py \
  /home/nebula/xxy/3D_Reconstruction/work_dirs/tmp/ESAM_CA_online_epoch_128.pth \
  --work-dir /home/nebula/xxy/duograph3d_artifacts/formal_fullval_norescue_nodedup_rerun_20260423/norescue_nodedup_strict_independent \
  --cat-agnostic \
  --cfg-options test_evaluator.online_monitor.out_dir=online_monitor
```

## Local raw artifacts

- `raw/20260423_192234.json`
- `raw/20260423_192234.log`
- `raw/online_monitor_summary.json`
- `raw/online_monitor.json`
- `raw/run_command.sh`

## Boundary

The independent rerun closes the artifact-provenance gap. It does **not** change the quantitative fullval conclusion: the no-rescue/no-dedup result is numerically aligned with strict baseline, and rescue/dedup fullval variants still need cautious claim framing.

# ScanNet200 Fullval Comparison Summary — 2026-04-23

## Main rows

| Method | Scenes | Frames | AP | AP50 | AP25 | Match rate | Birth rate | Rescued | Status | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| ESAM online baseline (strict) | 312 | 13430 | 0.4135 | 0.6300 | 0.7886 | 0.8202 | 0.1791 | 0.0000 | done | ESAM strict fullval baseline retained as reference; no-rescue/no-dedup now also has an independent same-config rerun artifact. |
| DuoGraph-style no-rescue/no-dedup | 312 | 13430 | 0.4135 | 0.6300 | 0.7886 | 0.8202 | 0.1791 | 0.0000 | done_independent_rerun | Independent rerun completed on 2026-04-23 in a fresh work directory; same strict/no-rescue/no-dedup config, no longer an alias-only artifact. |
| DuoGraph-style rescue-only (retry2) | 312 | 13430 | 0.4133 | 0.6286 | 0.7897 | 0.7999 | 0.1636 | 2.1584 | done | Primary runnable rescue-only fullval artifact; earlier 1st rescue-only attempt was incomplete. |
| DuoGraph-style dedup-only | 312 | 13430 | 0.4133 | 0.6244 | 0.7797 | 0.8104 | 0.1888 | 0.0000 | done | dedup enabled, rescue disabled. |
| DuoGraph-style rescue+dedup | 312 | 13430 | 0.4051 | 0.6139 | 0.7708 | 0.7861 | 0.1723 | 2.3946 | done | dedup+rescue baseline-comparable ablation. |

## Delta vs strict reference

| Delta | AP | AP50 | AP25 | Match rate | Birth rate | Rescued |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DuoGraph-style no-rescue/no-dedup - ESAM online baseline (strict) | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| DuoGraph-style rescue-only (retry2) - ESAM online baseline (strict) | -0.0002 | -0.0014 | +0.0011 | -0.0202 | -0.0155 | +2.1584 |
| DuoGraph-style dedup-only - ESAM online baseline (strict) | -0.0002 | -0.0056 | -0.0088 | -0.0097 | +0.0097 | +0.0000 |
| DuoGraph-style rescue+dedup - ESAM online baseline (strict) | -0.0084 | -0.0161 | -0.0178 | -0.0341 | -0.0068 | +2.3946 |

## Auxiliary rows

| Method | AP | AP50 | AP25 | Status | Notes |
| --- | ---: | ---: | ---: | --- | --- |
| ESAM-style dedup+rescue (aux) | 0.3985 | 0.6024 | 0.7624 | done | Additional fullval control-family variant observed from remote, kept for diagnostics. |

## Plan status

- Status: `fullval_norescue_nodedup_independent_rerun_completed`
- Independent no-rescue/no-dedup rerun completed on 2026-04-23 under /home/nebula/xxy/duograph3d_artifacts/formal_fullval_norescue_nodedup_rerun_20260423/norescue_nodedup_strict_independent.
- Metrics are numerically aligned with the strict baseline as expected for the same config; the previous alias-only evidence gap is closed by a separate command and work directory.
- DuoGraph rescue/dedup fullval variants still underperform the strict baseline on AP; subset gains remain a scoped observation rather than the fullval main claim.

## Boundary

- The independent no-rescue/no-dedup rerun closes the artifact-provenance gap, not the fullval performance gap.
- Fullval still shows rescue/dedup variants below strict AP; claims should emphasize where graph repair helps (subset/diagnostic/story-aligned lanes) unless later fullval variants improve.

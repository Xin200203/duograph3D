# Carrier-v2 subset diagnostic analysis — 2026-06-28

## Artifacts

- Remote carrier-v2 root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_carrier_v2_subset_20260628_carrier_v2_subset`
- Local mirror: `analysis/raw/ccfb_20260628/carrier_v2_subset_20260628_carrier_v2_subset/`
- Remote no-vent root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_carrier_v2_novent_subset_20260628_carrier_v2_novent`
- Local mirror: `analysis/raw/ccfb_20260628/carrier_v2_novent_subset_20260628_carrier_v2_novent/`

Subset scenes: `room0, office1, office2, office3, office4`.  The reported summary is the **per-scene average gap** versus ConceptGraphs; do not use the subset evaluator's synthetic `all` row as full-Replica evidence.

## Result table

| variant | ΔmIoU avg | ΔmF1 avg | ΔF-mIoU avg | decision |
| --- | ---: | ---: | ---: | --- |
| `Control_E71_active_target_declared` | +2.657056 | +3.243100 | +3.499455 | strong subset control; target-declared blocks unsafe `vent→table` |
| `CarrierV2_table_z025_rate016` | +1.369853 | +2.166050 | +3.280345 | negative vs control; geometry override lets `vent→table` damage office4 |
| `CarrierV2_table_z035_rate016` | +1.350332 | +2.162919 | +3.275993 | negative vs control; looser z does not solve the failure |
| `CarrierV2_bin_table_no_vent_z025_rate016` | **+2.791550** | **+3.315545** | **+3.517940** | best subset variant; remove unsafe `vent→table`, keep tissue/bin carrier gate |

## Per-scene readout for best variant

| scene | ΔmIoU | ΔmF1 | ΔF-mIoU | main repair evidence |
| --- | ---: | ---: | ---: | --- |
| room0 | +6.531666 | +8.393501 | +7.469402 | `large_tissue-paper_to_cloth: 1` |
| office1 | +3.436970 | +6.237720 | +0.273630 | `large_tissue-paper_to_cloth: 1` |
| office2 | -0.136518 | -1.093404 | +10.861230 | no large-label relabel; office2 bin/table gain still not recovered |
| office3 | +2.371705 | +1.977585 | -0.769891 | `vent_to_sofa: 5`, `large_tissue-paper_to_cloth: 2`, `large_bin_to_table: 1` |
| office4 | +1.753928 | +1.062322 | -0.244670 | no large-label relabel; avoids z025/z035 `vent→table` damage |

## Interpretation

- The initial carrier-v2 hypothesis was too broad: **geometry authorization alone is unsafe for `vent→table`**.  Many office4 vent-like carriers are geometrically table-like enough under bbox constraints, but semantically they are not tables.
- The positive part is narrower and clearer: **`tissue-paper→cloth` is stable**, and **a constrained `bin→table` can help when it fires** without carrying the `vent→table` false-positive risk.
- This supports a new claim boundary: `vent→table` is a negative innovation candidate / rejected rule, while `no-vent carrier-v2` is the current best scene-independent small-slice candidate.

## Next action

Run full Replica with `CarrierV2_bin_table_no_vent_z025_rate016`; launched in tmux `ccfb_carrier_v2_novent_full_20260628` with remote root `/home/nebula/xxy/duograph3d_artifacts/ccfb_carrier_v2_novent_full_20260628_carrier_v2_novent_full`.

## Full-run follow-up result

`CarrierV2_bin_table_no_vent_full_z025_rate016` was launched after the subset passed.  It failed the full official target:

| metric | full all gap |
| --- | ---: |
| ΔmIoU | +0.668524 |
| ΔmF1 | +2.758818 |
| ΔF-mIoU | +5.924266 |

Failure interpretation:

1. The subset average was optimistic because it averaged scene rows; the official full `all` row is class/point-confusion based and remains the publication gate.
2. This full run used office1 `phase gamma`, while E70's strong office1 row used `phase beta`; that alone loses the E70 office1 gain.
3. The z-thickness `bin→table` rule did not fire in office2; E70's office2 gain came from one `large_bin_to_table` plus additional `vent→table` relabels.  Therefore the z025 shape rule is too strict for the actual office2 table-carrier failure.

Immediate correction now running:

- `ccfb_active_novent_full_20260628`: active target-declared evidence, rules `tissue-paper→cloth,bin→table`, no `vent→table`, office1 restored to `phase beta`.
- Hypothesis: target-declared `bin→table` should recover the safe part of office2 without reopening the office4 `vent→table` failure.

## Corrected active/no-vent result

`ActiveNoVent_target_declared_full` restored office1 to `phase beta` and used active target-declared evidence with rules `tissue-paper→cloth,bin→table` while still excluding `vent→table`. It also failed:

| metric | full all gap |
| --- | ---: |
| ΔmIoU | +0.239238 |
| ΔmF1 | +1.940370 |
| ΔF-mIoU | +6.674002 |

Diagnostics:

- office2 remains negative (`-0.1365 mIoU`, `-1.0934 mF1`), because `bin→table` did not trigger under the current combined active rule.
- office1 no longer reproduces the E70 office1 jump; the current run reports `+2.7865 mIoU` vs E70's `+8.1715 mIoU`.
- Therefore the current unification problem is not just “remove `vent→table`”; it is that the reliable E70 rules are entangled with run-policy/code-path details. The next diagnostic should compare E70 exact archived manifests vs current runner output before another broad gate attempt.

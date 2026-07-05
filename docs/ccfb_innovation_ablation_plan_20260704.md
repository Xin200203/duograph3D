# DuoGraph3D innovation + ablation plan — 2026-07-04

## Current evidence boundary

- Strong anchor: E70 full Replica ConceptGraphs-format result, all `+3.040857 mIoU / +4.926709 mF1 / +8.459598 F-mIoU`.
- Proven negatives: naive/shared `vent→table`, bbox/shape-only carrier-v2, and target-declared shared gate do **not** replace E70.
- Current publishable direction: **auditable geometry-carrier authority** — object-level diagnostics identify when semantic readout overwrites a reliable carrier; graph memory supports monitoring/export-source separation, not direct dense final prediction.

## Ablation

### P0-A — E70 exact-reproduction probe on target scenes

### Target hypothesis
E70's positive result is not a broad parameter improvement; it depends on two concrete carrier-authority failures: office1 `tissue-paper→cloth` and office2 `bin→table`.  Before writing a unified method claim, the current runner must reproduce these two target-scene mechanisms under isolated exact settings.

### Expected signal
- `office1_beta_tissue_off` should recover the E70-level office1 gain direction; `office1_beta_no_large` should drop in cloth/overall metrics.
- `office2_gamma_bin_only_off` should recover most of office2 gain if A1's corrected no-vent conclusion is reproducible in current code.
- `office2_gamma_bin_vent_off` should reproduce the unsafe E70 office2 upper-bound, while `office2_gamma_bin_active` tests whether target-declared evidence blocks the needed carrier.

### Stop condition
If exact isolated probes fail to reproduce office1/office2, stop broad full runs and audit current-runner vs archived E70 manifest/code path. If they reproduce, promote the reproducible target mechanisms into the next shared-gate ablation.

## Ablation

### P0-B — scene-independent safe carrier gate after exact probes

### Target hypothesis
A paper-worthy innovation requires a scene-independent gate that keeps the safe `tissue→cloth`/`bin→table` mechanisms but rejects the proven unsafe `vent→table` family.

### Expected signal
- Full Replica all ΔmIoU > `+2.0` (minimum), ideally close to E70 `+3.0`.
- No target-scene collapse: office1 and office2 must be positive; office4 must not become negative from vent/table overreach.
- Relabel diagnostics should show few, high-evidence carrier corrections, not broad label forcing.

### Stop condition
If full all ΔmIoU remains around `+0.2~+0.7` or office2 stays negative, do not claim unified carrier repair. Write E70 as diagnostic composite and make the innovation the auditable failure-attribution/export-gating framework.

## Ablation

### P1 — graph-memory source-separation table

### Target hypothesis
Two-layer memory is valuable as state/diagnostic/export-gating infrastructure, not as the final dense source.

### Expected signal
- Candidate/no-candidate/weak-id/fragmentation metrics change across memory variants.
- Forced memory-dense export remains unstable versus geometry fallback.
- Auto export safely chooses geometry unless coverage gates pass.

### Stop condition
If memory-dense does not consistently beat geometry fallback, keep graph memory out of the primary accuracy claim and use it for diagnostics/observability claims only.

## Immediate execution

Launch a remote 184 target-scene probe (`ccfb_e70_repro_probe_20260704`) with these variants:

1. `office1_beta_tissue_off`
2. `office1_beta_no_large`
3. `office2_gamma_bin_vent_off`
4. `office2_gamma_bin_only_off`
5. `office2_gamma_bin_active`
6. `office2_gamma_bin_carrier_noz`

Primary readout: per-scene `gap_miou/gap_mf1score/gap_fmiou`, relabel counts, blocked relabel counts, export object counts.

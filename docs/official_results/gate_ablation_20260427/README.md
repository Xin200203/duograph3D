# Gate ablation 2026-04-27

Scenes: room0 + office0. Baseline row is from the full 8-scene history-object greedy run, sliced to these two scenes.

## Ablation plan

1. **spatial065_margin010_spatial055**
   - Target hypothesis: many false merges come from weak shared-history candidates, so requiring stronger spatial evidence should reduce false merge.
   - Expected signal: lower Layer1 false merge with modest duplicate increase.
   - Stop condition: Layer2 accuracy drops or duplicate birth rises without clear false-merge reduction.
2. **boost025_merge105_spatial045**
   - Target hypothesis: the history boost itself is too strong, so lowering boost and raising Layer1 threshold should make merges safer.
   - Expected signal: lower false merge while keeping Layer2 accuracy near baseline.
   - Stop condition: duplicate p50 rises sharply or accuracy does not improve.
3. **semantic055_assoc170**
   - Target hypothesis: history should only help Layer1 when semantic support is also stable, and Layer2 needs a stricter greedy threshold.
   - Expected signal: much lower false merge and ID-switch/error rate, accepting some under-merge.
   - Stop condition: duplicate birth becomes the dominant failure again.

## Decision

Selected **semantic055_assoc170** as the current safety/default gate because it reduced Layer1 false merge from `0.341` to `0.049`, improved Layer2 accuracy from `0.802` to `0.873`, and reduced ID-switch rate from `0.445` to `0.341` on the two-scene debug slice. The tradeoff is clear: duplicate birth rose from `0.663` to `0.930`, so the next pass should recover recall/merge coverage without relaxing false merges too far.

| variant | L1 false merge | room0 L1 dup p50 | office0 L1 dup p50 | L2 acc | dup birth | id switch | note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| baseline_default | 0.341 | 0.000 | 0.000 | 0.802 | 0.663 | 0.445 | default gates before tuning |
| spatial065_margin010_spatial055 | 0.275 | 0.083 | 0.000 | 0.779 | 0.761 | 0.455 | raises history affinity/margin and requires spatial>=0.55 |
| boost025_merge105_spatial045 | 0.218 | 0.083 | 0.143 | 0.799 | 0.798 | 0.453 | lower history boost and higher Layer1 threshold |
| semantic055_assoc170 | 0.049 | 0.150 | 0.222 | 0.873 | 0.930 | 0.341 | adds semantic gate and stricter Layer2 threshold |


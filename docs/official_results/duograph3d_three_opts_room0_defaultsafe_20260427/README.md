# DuoGraph3D three optimizations local slice (room0)

This is a bounded GT-aware validation slice for the three code optimizations:

1. object-level point-overlap scoring is recorded on history candidates and can be enabled as a guarded affinity bonus;
2. Layer2 residual absorption is implemented but left disabled by default after GT checks showed it can create false same-frame absorptions unless tuned per scene/profile;
3. duplicate-birth decomposition is now emitted in the GT layer monitor.

Command (remote):

```bash
cd /home/nebula/xxy/DuoGraph3D
/home/nebula/miniconda3/envs/duograph-baselines-cu118/bin/python \
  examples/run_conceptgraphs_gt_layer_monitor.py \
  --root /home/nebula/xxy/duograph3d_artifacts/duograph3d_three_opts_room0_defaultsafe_20260427 \
  --scenes room0 \
  --duograph-pred-exp-name duograph3d_three_opts_room0_defaultsafe_20260427
```

Key GT monitor values from `gt_layer_monitor_summary.json`:

- Layer1 eval hypotheses: 8607
- Layer1 false-merge rate: 0.154990
- Layer1 per-frame duplicate p50: 0.208333
- Layer2 decision accuracy: 0.793308
- Layer2 duplicate-birth rate: 0.952869
- Layer2 duplicate-birth families: semantic_gate_low=412, spatial_overlap_gate_low=52, association_score_below_threshold=1
- Layer2 residual absorption count: 0 (disabled by default)
- DuoGraph3D object duplicate rate: 0.717391
- ConceptGraphs object duplicate rate: 0.086957

Interpretation: the new monitor confirms the biggest remaining gap is not missing code instrumentation but semantic/object-level aggregation quality: most duplicate births are blocked by semantic instability, and ConceptGraphs still has far stronger object-level consolidation on this room0 slice. Residual absorption exists as an opt-in path, but the GT trial showed it needs additional safeguards before becoming a default optimization.

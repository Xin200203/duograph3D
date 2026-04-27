# GT-aware layer monitor

GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.

## Implementation notes

- This run uses history-aware Layer1 shared-object boosting, CG-style Layer2 greedy thresholding (`association_threshold=1.55`) without per-frame one-to-one exclusion, and online object-memory export (`object_source=online_memory_node`).
- The Layer1 duplicate p50 drops to 0.0 on 7/8 scenes, but the GT-proxy false-merge rate is high (~0.30-0.39), so the next tuning target is reducing over-merge while preserving the duplicate reduction.
- Object-level duplication is now close to ConceptGraphs at rollup level (Duo 0.237 vs CG 0.210), but scene-level semantic accuracy remains unstable in office scenes.

## Rollup

- valid eval observations: 43369
- Layer1 eval hypotheses: 19330
- Layer2 decision accuracy: 0.789602
- Layer2 duplicate birth rate: 0.788732
- Layer2 ID switch events: 8511
- DuoGraph3D object monitor: {'available_scene_count': 8, 'object_count': 384, 'valid_eval_object_count': 152, 'semantic_accuracy_weighted': 0.322368, 'semantic_cell_duplicate_count': 36, 'semantic_cell_duplicate_rate_micro': 0.236842}
- ConceptGraphs object monitor: {'available_scene_count': 8, 'object_count': 620, 'valid_eval_object_count': 338, 'semantic_accuracy_weighted': 0.263313, 'semantic_cell_duplicate_count': 71, 'semantic_cell_duplicate_rate_micro': 0.210059}

## Per scene

| scene | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | Duo obj count | Duo obj acc | Duo obj dup | CG obj count | CG obj acc | CG obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 0.192 | 0.000 | 0.351 | 0.813 | 0.689 | 0.440 | 38 | 0.292 | 0.333 | 76 | 0.326 | 0.087 |
| room1 | 0.222 | 0.000 | 0.394 | 0.790 | 0.795 | 0.380 | 46 | 0.500 | 0.056 | 67 | 0.432 | 0.189 |
| room2 | 0.214 | 0.000 | 0.306 | 0.781 | 0.883 | 0.457 | 44 | 0.565 | 0.435 | 81 | 0.212 | 0.231 |
| office0 | 0.275 | 0.000 | 0.325 | 0.782 | 0.644 | 0.453 | 46 | 0.083 | 0.083 | 82 | 0.326 | 0.186 |
| office1 | 0.200 | 0.000 | 0.361 | 0.815 | 0.833 | 0.418 | 35 | 0.214 | 0.286 | 55 | 0.417 | 0.167 |
| office2 | 0.304 | 0.000 | 0.381 | 0.786 | 0.769 | 0.479 | 52 | 0.067 | 0.200 | 82 | 0.178 | 0.244 |
| office3 | 0.310 | 0.111 | 0.334 | 0.769 | 0.808 | 0.513 | 50 | 0.455 | 0.273 | 96 | 0.193 | 0.298 |
| office4 | 0.261 | 0.000 | 0.302 | 0.771 | 0.889 | 0.475 | 73 | 0.333 | 0.167 | 81 | 0.118 | 0.235 |

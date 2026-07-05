# GT-aware layer monitor

GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.

## Rollup

- valid eval observations: 4831
- Layer1 eval hypotheses: 3738
- Layer2 decision accuracy: 0.873997
- Stage target coverage (micro): init 85 -> L1 82 (0.964706) -> L2 82 (0.964706)
- Layer2 duplicate birth rate: 0.802083
- Layer2 duplicate birth failure families: {'association_score_below_threshold': 50, 'spatial_overlap_gate_low': 50, 'weak_identity': 53, 'semantic_gate_low': 1}
- Layer2 residual absorption: 0 (accuracy 0.0)
- Layer2 ID switch events: 1148
- DuoGraph3D object monitor: {'available_scene_count': 1, 'object_count': 188, 'valid_eval_object_count': 75, 'semantic_accuracy_weighted': 0.346667, 'semantic_cell_duplicate_count': 35, 'semantic_cell_duplicate_rate_micro': 0.466667}
- ConceptGraphs object monitor: {'available_scene_count': 1, 'object_count': 104, 'valid_eval_object_count': 58, 'semantic_accuracy_weighted': 0.362069, 'semantic_cell_duplicate_count': 20, 'semantic_cell_duplicate_rate_micro': 0.344828}

## Per scene

| scene | init targets | L1 cov | L2 cov | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | Duo obj count | Duo obj acc | Duo obj dup | CG obj count | CG obj acc | CG obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room1 | 85 | 0.965 | 0.965 | 0.250 | 0.167 | 0.130 | 0.874 | 0.802 | 0.314 | 188 | 0.347 | 0.467 | 104 | 0.362 | 0.345 |

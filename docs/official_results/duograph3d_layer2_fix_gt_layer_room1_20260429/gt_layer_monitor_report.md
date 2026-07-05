# GT-aware layer monitor

GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.

## Rollup

- valid eval observations: 4831
- Layer1 eval hypotheses: 3838
- Layer2 decision accuracy: 0.859823
- Stage target coverage (micro): init 85 -> L1 83 (0.976471) -> L2 83 (0.976471)
- Layer2 duplicate birth rate: 0.830769
- Layer2 duplicate birth failure families: {'association_score_below_threshold': 59, 'spatial_overlap_gate_low': 66, 'weak_identity': 36, 'semantic_gate_low': 1}
- Layer2 residual absorption: 19 (accuracy 0.526316)
- Layer2 ID switch events: 1178
- DuoGraph3D object monitor: {'available_scene_count': 1, 'object_count': 176, 'valid_eval_object_count': 82, 'semantic_accuracy_weighted': 0.341463, 'semantic_cell_duplicate_count': 41, 'semantic_cell_duplicate_rate_micro': 0.5}
- ConceptGraphs object monitor: {'available_scene_count': 1, 'object_count': 67, 'valid_eval_object_count': 37, 'semantic_accuracy_weighted': 0.432432, 'semantic_cell_duplicate_count': 7, 'semantic_cell_duplicate_rate_micro': 0.189189}

## Per scene

| scene | init targets | L1 cov | L2 cov | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | Duo obj count | Duo obj acc | Duo obj dup | CG obj count | CG obj acc | CG obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room1 | 85 | 0.976 | 0.976 | 0.250 | 0.176 | 0.117 | 0.860 | 0.831 | 0.314 | 176 | 0.341 | 0.500 | 67 | 0.432 | 0.189 |

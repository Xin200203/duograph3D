# GT-aware layer monitor

GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.

## Rollup

- valid eval observations: 13381
- Layer1 eval hypotheses: 10341
- Layer2 decision accuracy: 0.8006
- Stage target coverage (micro): init 210 -> L1 204 (0.971429) -> L2 204 (0.971429)
- Layer2 duplicate birth rate: 0.919365
- Layer2 duplicate birth failure families: {'spatial_overlap_gate_low': 32, 'semantic_gate_low': 1030, 'weak_identity': 326, 'association_score_below_threshold': 3}
- Layer2 residual absorption: 0 (accuracy 0.0)
- Layer2 ID switch events: 4448
- DuoGraph3D object monitor: {'available_scene_count': 2, 'object_count': 471, 'valid_eval_object_count': 192, 'semantic_accuracy_weighted': 0.25, 'semantic_cell_duplicate_count': 79, 'semantic_cell_duplicate_rate_micro': 0.411458}
- ConceptGraphs object monitor: {'available_scene_count': 2, 'object_count': 143, 'valid_eval_object_count': 83, 'semantic_accuracy_weighted': 0.373494, 'semantic_cell_duplicate_count': 11, 'semantic_cell_duplicate_rate_micro': 0.13253}

## Per scene

| scene | init targets | L1 cov | L2 cov | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | Duo obj count | Duo obj acc | Duo obj dup | CG obj count | CG obj acc | CG obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 128 | 0.961 | 0.961 | 0.192 | 0.133 | 0.129 | 0.792 | 0.927 | 0.435 | 285 | 0.250 | 0.455 | 76 | 0.326 | 0.087 |
| room1 | 82 | 0.988 | 0.988 | 0.222 | 0.188 | 0.113 | 0.817 | 0.901 | 0.446 | 186 | 0.250 | 0.317 | 67 | 0.432 | 0.189 |

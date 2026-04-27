# GT-aware layer monitor

GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.

## Rollup

- valid eval observations: 11990
- Layer1 eval hypotheses: 8607
- Layer2 decision accuracy: 0.793308
- Layer2 duplicate birth rate: 0.952869
- Layer2 duplicate birth failure families: {'semantic_gate_low': 412, 'spatial_overlap_gate_low': 52, 'association_score_below_threshold': 1}
- Layer2 residual absorption: 0 (accuracy 0.0)
- Layer2 ID switch events: 4583
- DuoGraph3D object monitor: {'available_scene_count': 1, 'object_count': 383, 'valid_eval_object_count': 276, 'semantic_accuracy_weighted': 0.199275, 'semantic_cell_duplicate_count': 198, 'semantic_cell_duplicate_rate_micro': 0.717391}
- ConceptGraphs object monitor: {'available_scene_count': 1, 'object_count': 76, 'valid_eval_object_count': 46, 'semantic_accuracy_weighted': 0.326087, 'semantic_cell_duplicate_count': 4, 'semantic_cell_duplicate_rate_micro': 0.086957}

## Per scene

| scene | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | Duo obj count | Duo obj acc | Duo obj dup | CG obj count | CG obj acc | CG obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 0.333 | 0.208 | 0.155 | 0.793 | 0.953 | 0.540 | 383 | 0.199 | 0.717 | 76 | 0.326 | 0.087 |

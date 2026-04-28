# GT-aware layer monitor

GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.

## Rollup

- valid eval observations: 8741
- Layer1 eval hypotheses: 8401
- Layer2 decision accuracy: 0.960481
- Layer2 duplicate birth rate: 0.285714
- Layer2 duplicate birth failure families: {'semantic_gate_low': 4}
- Layer2 residual absorption: 0 (accuracy 0.0)
- Layer2 ID switch events: 2182
- DuoGraph3D object monitor: {'available_scene_count': 1, 'object_count': 9, 'valid_eval_object_count': 5, 'semantic_accuracy_weighted': 0.2, 'semantic_cell_duplicate_count': 0, 'semantic_cell_duplicate_rate_micro': 0.0}
- ConceptGraphs object monitor: {'available_scene_count': 1, 'object_count': 76, 'valid_eval_object_count': 46, 'semantic_accuracy_weighted': 0.326087, 'semantic_cell_duplicate_count': 4, 'semantic_cell_duplicate_rate_micro': 0.086957}

## Per scene

| scene | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | Duo obj count | Duo obj acc | Duo obj dup | CG obj count | CG obj acc | CG obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 0.192 | 0.160 | 0.012 | 0.960 | 0.286 | 0.264 | 9 | 0.200 | 0.000 | 76 | 0.326 | 0.087 |

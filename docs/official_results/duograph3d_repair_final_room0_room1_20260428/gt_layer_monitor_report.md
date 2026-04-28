# GT-aware layer monitor

GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.

## Rollup

- valid eval observations: 13381
- Layer1 eval hypotheses: 12452
- Layer2 decision accuracy: 0.944828
- Layer2 duplicate birth rate: 0.64
- Layer2 duplicate birth failure families: {'spatial_overlap_gate_low': 3, 'semantic_gate_low': 29}
- Layer2 residual absorption: 0 (accuracy 0.0)
- Layer2 ID switch events: 3133
- DuoGraph3D object monitor: {'available_scene_count': 2, 'object_count': 40, 'valid_eval_object_count': 18, 'semantic_accuracy_weighted': 0.444444, 'semantic_cell_duplicate_count': 2, 'semantic_cell_duplicate_rate_micro': 0.111111}
- ConceptGraphs object monitor: {'available_scene_count': 2, 'object_count': 143, 'valid_eval_object_count': 83, 'semantic_accuracy_weighted': 0.373494, 'semantic_cell_duplicate_count': 11, 'semantic_cell_duplicate_rate_micro': 0.13253}

## Per scene

| scene | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | Duo obj count | Duo obj acc | Duo obj dup | CG obj count | CG obj acc | CG obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 0.192 | 0.161 | 0.023 | 0.953 | 0.417 | 0.283 | 15 | 0.300 | 0.200 | 76 | 0.326 | 0.087 |
| room1 | 0.222 | 0.185 | 0.039 | 0.930 | 0.846 | 0.203 | 25 | 0.625 | 0.000 | 67 | 0.432 | 0.189 |

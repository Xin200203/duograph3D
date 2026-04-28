# GT-aware layer monitor

GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.

## Rollup

- valid eval observations: 4640
- Layer1 eval hypotheses: 4435
- Layer2 decision accuracy: 0.954228
- Layer2 duplicate birth rate: 0.4
- Layer2 duplicate birth failure families: {'semantic_gate_low': 2}
- Layer2 residual absorption: 0 (accuracy 0.0)
- Layer2 ID switch events: 401
- DuoGraph3D object monitor: {'available_scene_count': 1, 'object_count': 11, 'valid_eval_object_count': 4, 'semantic_accuracy_weighted': 0.5, 'semantic_cell_duplicate_count': 0, 'semantic_cell_duplicate_rate_micro': 0.0}
- ConceptGraphs object monitor: {'available_scene_count': 1, 'object_count': 67, 'valid_eval_object_count': 37, 'semantic_accuracy_weighted': 0.432432, 'semantic_cell_duplicate_count': 7, 'semantic_cell_duplicate_rate_micro': 0.189189}

## Per scene

| scene | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | Duo obj count | Duo obj acc | Duo obj dup | CG obj count | CG obj acc | CG obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room1 | 0.222 | 0.200 | 0.014 | 0.954 | 0.400 | 0.092 | 11 | 0.500 | 0.000 | 67 | 0.432 | 0.189 |

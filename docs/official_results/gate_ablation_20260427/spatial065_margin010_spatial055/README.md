# GT-aware layer monitor

GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.

## Rollup

- valid eval observations: 14021
- Layer1 eval hypotheses: 7059
- Layer2 decision accuracy: 0.778722
- Layer2 duplicate birth rate: 0.760563
- Layer2 ID switch events: 3122
- DuoGraph3D object monitor: {'available_scene_count': 2, 'object_count': 84, 'valid_eval_object_count': 48, 'semantic_accuracy_weighted': 0.1875, 'semantic_cell_duplicate_count': 10, 'semantic_cell_duplicate_rate_micro': 0.208333}
- ConceptGraphs object monitor: {'available_scene_count': 2, 'object_count': 158, 'valid_eval_object_count': 89, 'semantic_accuracy_weighted': 0.325843, 'semantic_cell_duplicate_count': 12, 'semantic_cell_duplicate_rate_micro': 0.134831}

## Per scene

| scene | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | Duo obj count | Duo obj acc | Duo obj dup | CG obj count | CG obj acc | CG obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 0.192 | 0.083 | 0.271 | 0.775 | 0.802 | 0.452 | 38 | 0.292 | 0.333 | 76 | 0.326 | 0.087 |
| office0 | 0.275 | 0.000 | 0.283 | 0.785 | 0.705 | 0.461 | 46 | 0.083 | 0.083 | 82 | 0.326 | 0.186 |

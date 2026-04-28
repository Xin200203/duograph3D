# GT-aware layer monitor

GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.

## Rollup

- valid eval observations: 13381
- Layer1 eval hypotheses: 5955
- Layer2 decision accuracy: 0.694207
- Layer2 duplicate birth rate: 0.863469
- Layer2 duplicate birth failure families: {'spatial_overlap_gate_low': 7, 'semantic_gate_low': 438, 'association_score_below_threshold': 23}
- Layer2 residual absorption: 0 (accuracy 0.0)
- Layer2 ID switch events: 2790
- DuoGraph3D object monitor: {'available_scene_count': 2, 'object_count': 490, 'valid_eval_object_count': 266, 'semantic_accuracy_weighted': 0.304511, 'semantic_cell_duplicate_count': 136, 'semantic_cell_duplicate_rate_micro': 0.511278}
- ConceptGraphs object monitor: {'available_scene_count': 2, 'object_count': 143, 'valid_eval_object_count': 83, 'semantic_accuracy_weighted': 0.373494, 'semantic_cell_duplicate_count': 11, 'semantic_cell_duplicate_rate_micro': 0.13253}

## Per scene

| scene | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | Duo obj count | Duo obj acc | Duo obj dup | CG obj count | CG obj acc | CG obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 0.192 | 0.000 | 0.205 | 0.659 | 0.889 | 0.496 | 250 | 0.244 | 0.525 | 76 | 0.326 | 0.087 |
| room1 | 0.222 | 0.000 | 0.192 | 0.744 | 0.826 | 0.469 | 240 | 0.396 | 0.491 | 67 | 0.432 | 0.189 |

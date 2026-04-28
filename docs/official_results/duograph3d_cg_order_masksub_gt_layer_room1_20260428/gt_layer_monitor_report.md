# GT-aware layer monitor

GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.

## Rollup

- valid eval observations: 4831
- Layer1 eval hypotheses: 3778
- Layer2 decision accuracy: 0.788777
- Stage target coverage (micro): init 85 -> L1 84 (0.988235) -> L2 84 (0.988235)
- Layer2 duplicate birth rate: 0.908738
- Layer2 duplicate birth failure families: {'semantic_gate_low': 342, 'spatial_overlap_gate_low': 10, 'weak_identity': 115, 'association_score_below_threshold': 1}
- Layer2 residual absorption: 0 (accuracy 0.0)
- Layer2 ID switch events: 1787
- DuoGraph3D object monitor: {'available_scene_count': 1, 'object_count': 190, 'valid_eval_object_count': 61, 'semantic_accuracy_weighted': 0.344262, 'semantic_cell_duplicate_count': 17, 'semantic_cell_duplicate_rate_micro': 0.278689}
- ConceptGraphs object monitor: {'available_scene_count': 1, 'object_count': 67, 'valid_eval_object_count': 37, 'semantic_accuracy_weighted': 0.432432, 'semantic_cell_duplicate_count': 7, 'semantic_cell_duplicate_rate_micro': 0.189189}

## Per scene

| scene | init targets | L1 cov | L2 cov | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | Duo obj count | Duo obj acc | Duo obj dup | CG obj count | CG obj acc | CG obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room1 | 85 | 0.988 | 0.988 | 0.250 | 0.176 | 0.120 | 0.789 | 0.909 | 0.484 | 190 | 0.344 | 0.279 | 67 | 0.432 | 0.189 |

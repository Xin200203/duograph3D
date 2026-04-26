# GT-aware layer monitor

GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.

## Rollup

- valid eval observations: 43369
- Layer1 eval hypotheses: 41990
- Layer2 decision accuracy: 0.11648
- Layer2 duplicate birth rate: 0.982458
- Layer2 ID switch events: 38335
- DuoGraph3D object monitor: {'available_scene_count': 8, 'object_count': 2308, 'valid_eval_object_count': 751, 'semantic_accuracy_weighted': 0.250333, 'semantic_cell_duplicate_count': 342, 'semantic_cell_duplicate_rate_micro': 0.455393}
- ConceptGraphs object monitor: {'available_scene_count': 8, 'object_count': 620, 'valid_eval_object_count': 338, 'semantic_accuracy_weighted': 0.263313, 'semantic_cell_duplicate_count': 71, 'semantic_cell_duplicate_rate_micro': 0.210059}

## Per scene

| scene | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | Duo obj count | Duo obj acc | Duo obj dup | CG obj count | CG obj acc | CG obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 0.192 | 0.182 | 0.002 | 0.095 | 0.984 | 0.931 | 306 | 0.358 | 0.446 | 76 | 0.326 | 0.087 |
| room1 | 0.222 | 0.200 | 0.003 | 0.152 | 0.979 | 0.899 | 208 | 0.342 | 0.329 | 67 | 0.432 | 0.189 |
| room2 | 0.214 | 0.167 | 0.006 | 0.114 | 0.980 | 0.933 | 256 | 0.264 | 0.429 | 81 | 0.212 | 0.231 |
| office0 | 0.275 | 0.257 | 0.001 | 0.108 | 0.981 | 0.943 | 267 | 0.205 | 0.509 | 82 | 0.326 | 0.186 |
| office1 | 0.200 | 0.200 | 0.004 | 0.204 | 0.986 | 0.849 | 154 | 0.273 | 0.485 | 55 | 0.417 | 0.167 |
| office2 | 0.304 | 0.282 | 0.003 | 0.096 | 0.985 | 0.951 | 328 | 0.155 | 0.578 | 82 | 0.178 | 0.244 |
| office3 | 0.310 | 0.294 | 0.003 | 0.095 | 0.984 | 0.951 | 403 | 0.211 | 0.421 | 96 | 0.193 | 0.298 |
| office4 | 0.261 | 0.167 | 0.002 | 0.125 | 0.977 | 0.925 | 386 | 0.114 | 0.341 | 81 | 0.118 | 0.235 |

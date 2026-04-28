# Supervised ConceptGraphs parity diagnosis

This report combines: (1) official Replica semantic confusion matrices, (2) GT-aware stage supervision for init/Layer1/Layer2, and (3) memory-dense ambiguous assignment samples enriched by geometry-key GT summaries.

## Stage supervision

| scene | init targets | L1 coverage | L1 dup | L1 pair precision | L2 coverage | L2 acc | L2 acc after merge | L2 duplicate birth | L2 id-switch |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room1 | 85 | 0.988 | 0.978 | 0.235 | 0.988 | 0.789 | 0.840 | 0.909 | 0.484 |

## Room-level diagnosis

- **room1**: ΔIoU=-0.027, ΔRecall=0.028, ΔPrecision=-0.053; precision_gap_dominant. room差距更像是语义误投/对象混合带来的false positive，而不是单纯没有覆盖到GT点。
- **all**: ΔIoU=0.036, ΔRecall=0.010, ΔPrecision=-0.018; mixed_recall_precision_gap. recall与precision都在损失，需要同时看语义误投和对象拆合。

## room1 worst per-class gaps

| class | GT pts | ΔIoU | Duo R | CG R | ΔR | Duo P | CG P | ΔP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pillow | 403988 | -0.464 | 0.042 | 0.511 | -0.469 | 1.000 | 0.983 | 0.017 |
| lamp | 364655 | -0.094 | 0.000 | 0.094 | -0.094 | 0.000 | 0.956 | -0.956 |
| picture | 344866 | -0.051 | 1.000 | 1.000 | 0.000 | 0.948 | 0.999 | -0.051 |
| nightstand | 85960 | -0.031 | 0.922 | 0.929 | -0.006 | 0.224 | 0.256 | -0.032 |
| comforter | 470985 | -0.020 | 1.000 | 1.000 | 0.000 | 0.257 | 0.276 | -0.020 |
| vent | 34810 | -0.017 | 0.999 | 0.999 | -0.000 | 0.117 | 0.134 | -0.017 |
| basket | 14029 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| bed | 315698 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| blanket | 459141 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cabinet | 85694 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## room1 DuoGraph3D top GT→pred confusions

| GT | predicted | points | GT error share |
| --- | --- | ---: | ---: |
| blanket | comforter | 458735 | 0.999 |
| pillow | comforter | 386976 | 0.958 |
| bed | comforter | 313660 | 0.994 |
| rug | comforter | 188189 | 0.673 |
| lamp | nightstand | 177515 | 0.487 |
| lamp | vent | 173583 | 0.476 |
| rug | vent | 79284 | 0.284 |
| cabinet | nightstand | 79078 | 0.923 |
| lamp | picture | 12436 | 0.034 |
| rug | nightstand | 11957 | 0.043 |

## room1 ambiguous memory assignment examples with GT

| key | selected share | roots | pred label | GT class | semantic acc | eval obs | unique GT targets |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: |
| `room1:gsa:item:-10:3:-3` | 0.333 | 3 | comforter | pillow | 0.333 | 3 | 1 |
| `room1:gsa:item:-10:3:-4` | 0.375 | 6 | comforter | bed | 0.000 | 16 | 2 |
| `room1:gsa:item:-10:7:-2` | 0.400 | 3 | comforter | bed | 0.200 | 10 | 1 |
| `room1:gsa:item:-10:7:-4` | 0.500 | 2 | pillow | pillow | 0.500 | 2 | 2 |
| `room1:gsa:item:-11:-11:1` | 0.571 | 2 | blinds | blinds | 1.000 | 7 | 1 |
| `room1:gsa:item:-10:2:-4` | 0.583 | 3 | pillow | bed | 0.000 | 14 | 2 |
| `room1:gsa:item:-10:4:-4` | 0.600 | 3 | vent | bed | 0.000 | 13 | 2 |
| `room1:gsa:item:-10:6:-4` | 0.667 | 2 | comforter | pillow | 0.000 | 3 | 3 |

## Interpretation

Recall low means: among all GT points of a class, many points were finally assigned to another predicted class. In the ConceptGraphs evaluator, predictions are resampled onto the SLAM cloud, so this is usually a label/assignment problem rather than simply no point existing. If recall is worse but precision is okay, the class is missed or absorbed by other labels. If precision is much worse, the predicted class has swallowed many wrong GT points, usually from semantic confusion or cross-object merge/assignment noise.

For room1, compare the ΔRecall and ΔPrecision columns plus the ambiguous samples above. If ΔPrecision is the larger loss and ambiguous keys show low selected-root share or wrong dominant GT class, the gap is mainly semantic/object assignment pollution; if ΔRecall is the larger loss and few ambiguous samples touch that class, the gap is mainly missed coverage/filtering.

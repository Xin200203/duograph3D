# Supervised ConceptGraphs parity diagnosis

This report combines: (1) official Replica semantic confusion matrices, (2) GT-aware stage supervision for init/Layer1/Layer2, and (3) memory-dense ambiguous assignment samples enriched by geometry-key GT summaries.

## Stage supervision

| scene | init targets | L1 coverage | L1 dup | L1 pair precision | L2 coverage | L2 acc | L2 acc after merge | L2 duplicate birth | L2 id-switch |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 128 | 0.961 | 0.982 | 0.151 | 0.961 | 0.792 | 0.830 | 0.927 | 0.435 |
| room1 | 82 | 0.988 | 0.978 | 0.189 | 0.988 | 0.817 | 0.861 | 0.901 | 0.446 |

## Room-level diagnosis

- **room0**: ΔIoU=0.024, ΔRecall=-0.015, ΔPrecision=0.118; recall_gap_dominant. room差距更像是目标类别覆盖不足或被过滤/漏检。
- **room1**: ΔIoU=-0.029, ΔRecall=0.023, ΔPrecision=-0.102; precision_gap_dominant. room差距更像是语义误投/对象混合带来的false positive，而不是单纯没有覆盖到GT点。
- **all**: ΔIoU=-0.037, ΔRecall=-0.020, ΔPrecision=-0.015; mixed_recall_precision_gap. recall与precision都在损失，需要同时看语义误投和对象拆合。

## room1 worst per-class gaps

| class | GT pts | ΔIoU | Duo R | CG R | ΔR | Duo P | CG P | ΔP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pillow | 403988 | -0.507 | 0.000 | 0.511 | -0.511 | 0.000 | 0.983 | -0.983 |
| lamp | 364655 | -0.094 | 0.000 | 0.094 | -0.094 | 0.000 | 0.956 | -0.956 |
| nightstand | 85960 | -0.043 | 0.917 | 0.929 | -0.012 | 0.213 | 0.256 | -0.044 |
| vent | 34810 | -0.024 | 0.999 | 0.999 | 0.000 | 0.110 | 0.134 | -0.024 |
| picture | 344866 | -0.017 | 1.000 | 1.000 | 0.000 | 0.981 | 0.999 | -0.017 |
| comforter | 470985 | -0.010 | 1.000 | 1.000 | -0.000 | 0.266 | 0.276 | -0.010 |
| blinds | 872892 | -0.009 | 0.989 | 0.999 | -0.010 | 0.998 | 0.997 | 0.001 |
| basket | 14029 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| bed | 315698 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| blanket | 459141 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## room1 DuoGraph3D top GT→pred confusions

| GT | predicted | points | GT error share |
| --- | --- | ---: | ---: |
| blanket | comforter | 458735 | 0.999 |
| pillow | comforter | 403714 | 0.999 |
| bed | comforter | 295664 | 0.937 |
| lamp | vent | 194142 | 0.532 |
| lamp | nightstand | 168938 | 0.463 |
| rug | comforter | 124500 | 0.445 |
| cabinet | nightstand | 79135 | 0.923 |
| rug | vent | 77710 | 0.278 |
| rug | pillow | 59772 | 0.214 |
| bed | nightstand | 19809 | 0.063 |

## room1 ambiguous memory assignment examples with GT

| key | selected share | roots | pred label | GT class | semantic acc | eval obs | unique GT targets |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: |
| `room1:gsa:item:-10:6:-4` | 0.333 | 3 | comforter | pillow | 0.000 | 3 | 3 |
| `room1:gsa:item:-10:7:-3` | 0.417 | 5 | comforter | pillow | 0.083 | 12 | 1 |
| `room1:gsa:item:-10:4:-4` | 0.500 | 5 | vent | bed | 0.000 | 13 | 2 |
| `room1:gsa:item:-10:-5:6` | 0.500 | 2 | clock |  | 0.000 | 0 | 0 |
| `room1:gsa:item:-11:-11:1` | 0.571 | 2 | blinds | blinds | 1.000 | 7 | 1 |
| `room1:gsa:item:-10:2:-4` | 0.636 | 2 | pillow | bed | 0.000 | 13 | 2 |
| `room1:gsa:item:-10:7:-4` | 0.667 | 2 | comforter | pillow | 0.333 | 6 | 2 |
| `room1:gsa:item:-10:-10:-4` | 0.667 | 2 | blinds |  | 0.000 | 0 | 0 |

## Interpretation

Recall low means: among all GT points of a class, many points were finally assigned to another predicted class. In the ConceptGraphs evaluator, predictions are resampled onto the SLAM cloud, so this is usually a label/assignment problem rather than simply no point existing. If recall is worse but precision is okay, the class is missed or absorbed by other labels. If precision is much worse, the predicted class has swallowed many wrong GT points, usually from semantic confusion or cross-object merge/assignment noise.

For room1, compare the ΔRecall and ΔPrecision columns plus the ambiguous samples above. If ΔPrecision is the larger loss and ambiguous keys show low selected-root share or wrong dominant GT class, the gap is mainly semantic/object assignment pollution; if ΔRecall is the larger loss and few ambiguous samples touch that class, the gap is mainly missed coverage/filtering.

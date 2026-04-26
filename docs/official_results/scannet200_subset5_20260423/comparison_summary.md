# Official Evaluator Comparison

| Method | Scenes | Frames | AP | AP50 | AP25 | Match rate mean | Birth rate mean | Rescue mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ESAM online baseline subset5 | 5 | 172 | 0.5146 | 0.7348 | 0.8508 | 0.7603 | 0.2281 | 0.0000 |
| DuoGraph-style rescue+dedup subset5 | 5 | 172 | 0.5330 | 0.7561 | 0.8837 | 0.3178 | 0.1294 | 3.4070 |

| Delta | AP | AP50 | AP25 | Match rate mean | Birth rate mean | Rescue mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Candidate - baseline | +0.0183 | +0.0213 | +0.0329 | -0.4424 | -0.0987 | +3.4070 |

Candidate beats baseline on AP/AP50/AP25: **True**

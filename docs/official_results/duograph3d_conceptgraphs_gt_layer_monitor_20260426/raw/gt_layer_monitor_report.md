# GT-aware layer monitor

GT target = semantic class + 1m GT cell proxy. It separates SAM/init duplication, Layer1 post-repair duplication, and Layer2 ID behavior; it is not a true instance-ID metric because the available Replica semantic map is semantic-label based.

## Rollup

- valid eval observations: 57191
- Layer1 eval hypotheses: 46522
- Layer2 decision accuracy: 0.102274
- Layer2 duplicate birth rate: 0.983734
- Layer2 ID switch events: 43268

## Per scene

| scene | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | baseline obj acc | baseline obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 0.333 | 0.227 | 0.113 | 0.087 | 0.986 | 0.942 | 0.326 | 0.087 |
| room1 | 0.368 | 0.250 | 0.094 | 0.149 | 0.980 | 0.904 | 0.432 | 0.189 |
| room2 | 0.348 | 0.250 | 0.066 | 0.100 | 0.982 | 0.948 | 0.212 | 0.231 |
| office0 | 0.385 | 0.300 | 0.063 | 0.095 | 0.984 | 0.962 | 0.326 | 0.186 |
| office1 | 0.385 | 0.273 | 0.109 | 0.178 | 0.986 | 0.881 | 0.417 | 0.167 |
| office2 | 0.421 | 0.339 | 0.084 | 0.081 | 0.986 | 0.965 | 0.178 | 0.244 |
| office3 | 0.429 | 0.341 | 0.060 | 0.079 | 0.983 | 0.971 | 0.193 | 0.298 |
| office4 | 0.333 | 0.250 | 0.017 | 0.095 | 0.977 | 0.953 | 0.118 | 0.235 |

# DuoGraph3D 魔鬼审稿人投稿级别判断（2026-06-27）

## 0. 一句话结论

以当前证据包判断：**不支持 CCF-A / 顶会 / 顶刊；未硬化前也不稳支持 CCF-B regular；最现实目标是 CCF-C regular 或中等/应用型期刊。** 如果完成 clean leave-one-out、A2 graph-memory diagnostic、并把 scene-local E70 抽象成更可信的 shared reliability gate，才有机会冲击 CCF-B 边缘会议/期刊。

## 1. 当前最强证据

- E70 full composite 在 Replica full scenes 上超过 ConceptGraphs：all `+3.041 mIoU / +4.927 mF1 / +8.460 F-mIoU`，evaluator PASS，152 tests OK。
- 每个场景 mIoU/mF1 都为正，但部分场景 F-mIoU 为负或余量小：office0 `-0.984 F-mIoU`，office3 `-0.862`，office4 `-0.245`，room2 mIoU 仅 `+0.598`。
- object-level diagnostics 能解释 office2 bin/table failure，并导向 E66/E69/E70。
- 当前 A3 naive/global 与 bbox shape-gated shared rule 都失败，说明 E70 还没有被统一方法完整复现。

## 2. 魔鬼审稿人会怎么攻击

### 2.1 Contribution risk

当前论文最容易被认为是：

> A diagnostic-heavy system with scene-local heuristic repairs, not a general new method.

如果主贡献写成 two-layer graph memory，审稿人会问：为什么最终提升主要来自 tissue/bin/vent relabel？A2 之前不能直接回答。

### 2.2 Experimental risk

- 主强结果只在 Replica full scenes + ConceptGraphs baseline 上成立。
- 目前缺 clean leave-one-out：E70 的每条 local repair 贡献还没有在同一 deployment policy 下严格量化。
- 统一化尝试失败：A3 shape only `+0.635/+2.685/+5.811`，远低于 E70。
- 一些消融仍比 ConceptGraphs 高，但这只说明 baseline path 有一定正收益，不等于支持 claimed method novelty。

### 2.3 Method-design risk

- E70 是 scene-local composite，容易被质疑为 post-hoc tuning。
- 如果文中没有严格说明 diagnostics 使用 GT 只用于分析、不进入测试时方法，审稿人会质疑 leakage。
- 当前 bbox shape gate 漏掉 office2 关键 object，却误伤 office4，说明方法边界未完全理解。

## 3. 当前可支持的投稿级别

### Not supported: CCF-A / 顶会 / 顶刊

不建议投 CVPR/ICCV/NeurIPS/ICML/AAAI/TPAMI/IJCV 等。原因：

- 单数据集、单强 baseline；
- 统一方法未成立；
- 消融仍不完整；
- 创新点如果写成 graph memory，会与实验证据错位；
- 结果可能被看作 targeted heuristic repair。

### Weak / high-risk: CCF-B regular

例如 ICRA/ECCV 等级的 regular paper，目前很危险。若强行投，最可能被拒的理由是：

- contribution is incremental / heuristic;
- evaluation is incomplete;
- method is not robust without per-scene tuning;
- ablation does not isolate the proposed components.

只有在以下条件满足后，才建议冲 CCF-B 边缘：

1. 完成 E70 local leave-one-out；
2. 完成 A2 graph memory diagnostic；
3. 至少一个 scene-independent evidence-gated reliability row 显著接近 E70，或诚实把 E70 定位为 diagnostic composite；
4. 增加至少一个非 Replica / OOD / harder subset 的验证；
5. 补强 baselines 或给出公平 baseline audit。

### Realistic: CCF-C / 中等应用型期刊

当前最匹配的是 CCF-C 或接近 CCF-C 的会议/期刊，前提是论文叙事改成：

> object-level diagnostic framework + bounded geometry-carrier reliability analysis for online open-vocabulary 3D mapping.

此级别下，E70 超过 ConceptGraphs、object-level diagnostics、正负案例边界，已经可以形成一篇有价值的系统/分析型论文。但仍需补 clean ablation，否则 CCF-C regular 也有明显拒稿风险。

### Safe fallback: workshop / short paper / tech report

如果目标是尽快产出，而不补 A2 和 clean leave-one-out，则更安全的是 workshop、short paper、或实验诊断型技术报告。注意：按 CCF 目录口径，short/demo/workshop 通常不计入推荐目录 full/regular paper。

## 4. 推荐投稿策略

### 策略 A：最快可投

目标：CCF-C regular / 中等期刊。

必须完成：

- clean E70 leave-one-out；
- object-level diagnostic table；
- limitation 写清楚：当前 shared gate 未完全解决；
- 不把 two-layer graph 写成 mIoU 主因。

### 策略 B：冲 CCF-B

目标：ICRA/ECCV/B 类期刊边缘。

必须新增：

- A2 graph-memory diagnostic；
- shared evidence-gated reliability gate 或跨数据集验证；
- more baselines / stronger fairness audit；
- 更完整 qualitative cases。

### 策略 C：不建议

当前状态直接冲 A/B：高概率被认为是 heuristic tuning + incomplete evaluation。

## 5. Claim-evidence map

| Claim | Current evidence | Verdict |
| --- | --- | --- |
| DuoGraph3D can outperform ConceptGraphs on Replica official setting | E70 all `+3.041/+4.927/+8.460`, PASS | supported |
| Geometry-carrier failures are real and diagnosable | E65 office2 object-level bin/table diagnosis | supported |
| Tissue/cloth repair is transferable | A1 tissue-only vs no-large positive | partially supported |
| Table-sink repair is generally transferable | A3 naive/shape fail | not supported |
| Two-layer graph memory drives final mIoU gain | A2 missing | not yet supported |
| Method is robust and scene-independent | A3 fail | not supported |

## 6. Final verdict

当前最公平的级别判断：

- **直接投：CCF-C / 中等期刊，仍需补 clean ablation 才稳。**
- **补强后：有机会冲 CCF-B 边缘，但必须解决 scene-local / ablation / generalization 三个问题。**
- **当前不支持 CCF-A / 顶会 / 顶刊。**

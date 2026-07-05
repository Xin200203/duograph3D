# DuoGraph3D 后续测试与分层优化实验计划（CCF-B 目标，2026-06-27）

## 0. 当前判断

结合当前代码、实验结果和 zero-shot / open-vocabulary 3D 调研，后续优化不能继续做宽泛超参搜索。当前最需要解决的是三个 reviewer-facing 问题：

1. **E70 的收益是否能被干净归因？** 现在 E70 是 strong，但 scene-local composite 的贡献还需要 clean leave-one-out。
2. **carrier reliability 能否从 scene-local repair 变成 scene-independent method？** 当前 naive/global 和 bbox shape-gated table-sink 已失败，说明需要更强 evidence-gated gate。
3. **two-layer graph memory 是否有独立价值？** 当前代码有 candidate/memory/carrier diagnostics，但还没有形成 A2 级别的实验表。

CCF-B 目标下，横向 baseline 也必须补强：ConceptGraphs 之外至少需要 OnlineAnySeg、ESAM，以及一个 Open3DIS/OpenMask3D 级别的 offline upper-bound 或 related baseline。

## 1. 当前代码能支撑什么

### 1.1 已有可用 hooks

- `examples/run_conceptgraphs_engineered_parity.py`
  - official ConceptGraphs-format export/eval runner；
  - 支持 `--export-source {auto,geometry,memory,memory-dense}`；
  - 支持 `--clip-feature-mode {image,dominant-label-image,label-text,blend,adaptive}`；
  - 支持 `--geometry-repair-carve-rules`；
  - 支持 `--geometry-repair-large-label-rules source:target:min_extent[:max_z_extent]`；
  - 支持 `--phase {baseline,cand,l1,beta,gamma,delta,all}`。
- `src/duograph3d/export_policy.py`
  - 已有 memory/geometry/memory-dense source selection 和 carrier candidate scoring 的雏形。
- `src/duograph3d/candidate_metrics.py`
  - 可从 `association_candidate_diagnostic` / `association_birth_diagnostic` 中生成 candidate recall / birth failure decomposition。
- `src/duograph3d/memory_purity.py`
  - 可统计 births、associations、absorptions、merges、retired nodes。
- `src/duograph3d/carrier_metrics.py`
  - 可统计 export source selection / coverage gate。

### 1.2 当前代码暴露的问题

- `apply_geometry_repairs()` 当前 large-label rule 的触发条件主要是：object-level CLIP pred label + bbox extent / z thickness。它没有充分利用：
  - label buckets；
  - declared labels / class-name history；
  - per-frame prompt agreement；
  - surface normal / planarity；
  - support / neighbor relation；
  - relabel mass guard。
- 这解释了 A3 失败：bbox shape gate 没命中 office2 的关键 false-bin carrier，却在 office4 大量触发 `vent:table`。
- `selected_export_clip_feature()` 已有 adaptive 分支，但 E47/E48 证明 readout-only 不足以解决 carrier impurity；它应该作为 reliability evidence，而不是主修复。
- Graph memory diagnostics 已经存在，但还没组织成论文级实验：candidate recall、memory purity、fragmentation、export-source coverage 需要统一输出。

## 2. 先建立统一监控指标，不先改大方法

后续每个实验都必须输出三层指标。

### 2.1 Final metrics

- all / per-scene：mIoU、mF1、F-mIoU；
- per-class：IoU、precision、recall，重点类：`bin/table/vent/cloth/tissue-paper/pillow/sofa/cushion/sculpture`；
- 双差值：`Δ vs ConceptGraphs` 和 `drop vs E70`。

### 2.2 Carrier-level metrics

- object count / point count；
- export source：geometry / memory / memory-dense；
- predicted label、declared labels、label-bucket distribution；
- label entropy、top-share、CLIP margin/high-margin rate；
- bbox extents、PCA planarity、surface normal、horizontal support score；
- neighbor/support relation：附近是否存在 table/sofa/cloth anchors；
- relabel object count、relabel pcd points、relabel point mass rate；
- relabel examples：必须记录 object index、from/to、触发证据。

### 2.3 Memory / association metrics

- candidate count、candidate recall proxy、best/second score margin；
- birth reason：no_candidate / low_score / id_gate_fail / semantic_gate_low；
- duplicate birth / fragmentation；
- memory object purity、active/dormant/retired counts；
- export-source coverage：memory/key ratio、point ratio、fallback reason。

## 3. 三个分层优化实验包

## Ablation 1 — Clean E70 leave-one-out：先把强结果归因做干净

### Target hypothesis

E70 的主要收益来自少数 diagnosis-guided carrier repairs；去掉对应 repair 会造成目标场景/目标类别的局部退化，而不是随机影响全局。

### 实验设置

固定 E70 的 scene-local composite policy，只做单因子 removal：

| row | change | primary target |
| --- | --- | --- |
| Full E70 | no removal | anchor |
| w/o tissue repair | 去掉 office1 `tissue-paper:cloth` | office1 cloth/tissue |
| w/o office2 table-sink | 去掉 office2 `bin:table` + `vent:table` | office2 table/bin/vent |
| w/o bin-table only | 只去掉 office2 `bin:table` | office2 bin precision/table IoU |
| w/o vent-table only | 只去掉 office2 `vent:table` | office2 vent false positives |
| w/o all large-label repairs | 去掉 tissue + table-sink | carrier repair total contribution |

### Expected signal

确认假设：

- Full E70 仍最好；
- w/o tissue 主要损失 office1；
- w/o bin-table 主要损失 office2 bin/table；
- w/o vent-table 损失小于 bin-table；
- w/o all large-label 接近当前 `+0.142/+1.924` 级别。

削弱假设：

- 去掉某 repair 后目标类/目标场景不变；
- 退化主要发生在无关场景，说明 repair claim 不成立。

### Stop condition

完成 full + 至少 4 个 removal rows；每个 row 有 final metrics、per-class target metrics、relabel monitor、object-level examples。若 clean leave-one-out 不支持 E70 归因，暂停统一 gate 开发，回到 failure attribution。

---

## Ablation 2 — Evidence-gated shared carrier reliability：把局部 repair 推向统一方法

### Target hypothesis

简单 bbox gate 失败不是因为 carrier reliability 原理错误，而是因为当前 gate 只用了不足证据。一个 scene-independent evidence-gated gate 若同时利用几何、语义、多视角/可选 Grounded-SAM evidence、邻接关系和 mass guard，应能保留 E70 大部分收益并避免 office4 collapse。

### 实验设置

先 shadow、后 active，不能一上来全量改标签。

| stage | variant | purpose |
| --- | --- | --- |
| S0 | no large-label repair | lower-bound |
| S1 | current bbox shape gate | 已知 negative boundary |
| S2 | evidence-gate shadow mode | 只记录 would_relabel，不改输出 |
| S3 | evidence-gate active target scenes | 先跑 office1/office2/office3/office4 |
| S4 | evidence-gate active full Replica | 全场景验证 |

Evidence gate 不应只用 `min_extent/max_z_extent`，至少包含：

1. **Geometry evidence**：PCA planarity、horizontal support score、thickness、面积/高度 ratio；
2. **Semantic evidence**：label-bucket top-share / entropy、high-margin CLIP support、image/text agreement；
3. **Object evidence**：declared labels、历史 label distribution、是否出现 target label support；
4. **Relation evidence**：附近 support surface / anchor relation，例如 table-like plane、sofa/cushion proximity；
5. **Optional Grounded-SAM probe**：对疑似 failure carrier 的多视角 prompt agreement，仅作为 evidence，不作为 final authority；
6. **Guardrail**：单场景 relabel object count / point mass 上限，超过则 shadow-only。

### Expected signal

确认假设：

- shadow mode 能命中 E65 office2 false-bin/table carrier；
- active target scenes 中 office2 接近 E70，office4 不 collapse；
- full Replica all ΔmIoU 至少 > `+2.0`，最好 > `+2.5`；
- 无 scene 的 mIoU/mF1 为负；
- relabel mass 小且集中在诊断支持的 failure family。

削弱假设：

- gate 仍漏掉 office2 关键 object；
- office4/room2 继续出现大负迁移；
- 需要 scene name 才能工作；
- relabel mass 很大，看起来像 label rewriting。

### Stop condition

若 evidence-gated shared repair 低于 `+2.0 mIoU` 或仍出现明显场景负迁移，则论文不把 unified repair 当主方法；保留 E70 为 diagnostic composite，并把 CCF-B 目标降级或转向更强 baseline/diagnostic paper。

---

## Ablation 3 — A2 graph-memory diagnostics：证明 two-layer graph 的独立价值

### Target hypothesis

Two-layer graph memory 的贡献是在线 object state、association 可观测性和 export/source decision，而不是直接替代 geometry export。它应降低 duplicate birth / fragmentation，并提高 candidate quality / memory purity。

### 实验设置

先代表场景，再 full/supplement。

| row | phase/source | purpose |
| --- | --- | --- |
| baseline / no enhanced memory | `--phase baseline` | lower-bound |
| candidate retrieval only | `--phase cand` | 测 candidate recall / no-candidate birth |
| Layer1 only | `--phase l1` | 测 current evidence repair / mixed-label mass |
| beta/full memory | `--phase beta/all` | 测 combined state value |
| forced geometry export | `--export-source geometry` | memory 只做 state，不决定 dense source |
| forced memory-dense export | `--export-source memory-dense` | 测 dense memory source 风险 |

代表场景：`room0, office1, office2, office3, office4`。

### Expected signal

确认假设：

- cand 降低 no-candidate birth / 提高 candidate availability；
- l1 降低 mixed-label / over-merge 相关指标；
- beta/all 降低 fragmentation / duplicate birth，提高 memory purity；
- forced memory-dense 在部分场景不稳定，证明 export/source separation 必要；
- final mIoU 即使不是最大增益，diagnostic metrics 也能支撑 graph memory 的论文贡献。

削弱假设：

- phase rows 在 candidate/memory diagnostics 上几乎无差别；
- forced memory-dense 始终最好且无风险；
- graph memory 指标与最终 carrier repair 无任何关系。

### Stop condition

代表场景趋势清晰后停止，不做无意义全量 sweep。若 A2 不支持独立价值，论文中 two-layer graph 降级为 implementation detail / system support，不作为主创新。

## 4. 横向 baseline 轨道：与优化实验并行推进

这不是 ablation，但 CCF-B 必须做。

### P0 baselines

1. **ConceptGraphs**：保留当前 official Replica-format 主 baseline。
2. **OnlineAnySeg**：优先完成同协议 bridge，至少拿到 Replica/ScanNet 可解释指标。
3. **ESAM / EmbodiedSAM**：复核现有 ESAM 结果并建立 protocol bridge。
4. **Open3DIS 或 OpenMask3D**：作为 offline upper-bound；优先 Open3DIS，因为它支持 2D mask guidance / GroundingDINO / SAM 路线。

### Baseline table 写法

- Main online table：ConceptGraphs / OnlineAnySeg / ESAM / DuoGraph3D；
- Offline upper-bound table：Open3DIS 或 OpenMask3D；
- Diagnostic table：DuoGraph3D object-level carrier failure attribution，作为我们区别于 baseline 的核心。

## 5. Grounded-SAM 的使用边界

### 应该做

- 用作 targeted diagnostic probe：table/bin/vent/cloth/tissue/pillow/sofa/cushion prompt bank；
- 对失败 carrier 做多视角 prompt agreement；
- 把 prompt support 作为 evidence-gate 的一个输入；
- 可选地把 SAM2/Grounded-SAM2 tracking identity 作为 Layer2 candidate evidence。

### 不应该做

- 不要直接用 Grounded-SAM 单帧 label 覆盖 3D carrier；
- 不要把它变成新的黑盒语义权威；
- 不要在没有 multiview/geometry guard 的情况下替换现有 GSA detections。

## 6. 推荐执行顺序

1. **先跑 Ablation 1**：最快、最能修复当前论文证据链。
2. **同时整理 baseline bring-up**：OnlineAnySeg / ESAM / Open3DIS 选最先能跑通的一条。
3. **再做 Ablation 2 shadow mode**：先证明 gate 能命中目标 object，别先全量改输出。
4. **再做 Ablation 3 代表场景**：把 graph memory 从“代码结构”变成“可量化贡献”。
5. **最后才 full Replica / large-scale**：只有小实验通过 stop condition 后再扩全量。

## 7. CCF-B 级别的 go/no-go 条件

建议只有同时满足以下条件才继续按 CCF-B regular 冲：

- E70 clean leave-one-out 清楚支持 carrier repair 贡献；
- evidence-gated shared repair 至少 all ΔmIoU > `+2.0` 且无明显场景负迁移，或能诚实解释为何 scene-local diagnostic composite 是论文贡献；
- A2 graph memory 在 candidate/memory/carrier diagnostics 上有可展示正信号；
- 至少补齐 OnlineAnySeg + ESAM 中一个 direct online baseline，最好两个都补；
- Open3DIS/OpenMask3D 至少作为 offline upper-bound 或 related comparison 给出公平解释。

若不满足，建议不要强投 B，会被质疑 heuristic / incomplete evaluation。

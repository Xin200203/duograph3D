# DuoGraph3D 消融实验与创新点重构（2026-06-27）

## 0. 核心纠偏

上一轮“消融都是负面”的表达不准确。当前真实情况是：

1. **相对 ConceptGraphs，多数 variants 仍是正的**；
2. **相对 E70 full，所有去模块/替代模块都退化**，这反而说明 E70 组件有贡献；
3. 真正被否定的是：把 E70 的 scene-local diagnostic repairs 直接写成 **naive/global large-label relabel** 或 **bbox shape-gated global table-sink** 的统一方法。

因此，后续消融不能再把“与 ConceptGraphs 比是否仍为正”“与 E70 full 比是否退化”“是否支持某个论文创新点”混在同一结论里。

## 1. 之前消融设计的问题

### 1.1 把 ablation 和 method replacement 混在一起

严格的 ablation 应该是：在同一 full model / 同一 deployment policy 下，只移除一个组件。

但上一轮部分 row 同时改变了多个因素：

- `A1_no_tissue_shape` 不只是去掉 tissue；它还把 table-sink 从 E70 scene-local 版本换成了 shape-gated global 版本。
- `A1_bin_table_only_shape` 不只是 “bin-table only”；它测试的是 **shape-gated global bin-table**，不是 E70 中已证明有效的 office2 local bin-table。
- `A3_shape_gated_unified` 是一个新方法候选，不是 E70 的普通消融。

所以这些 row 适合回答“当前统一规则是否成立”，不适合直接回答“E70 的每个模块贡献多少”。

### 1.2 E70 是 scene-local composite，不能直接与 global variant 做单因子比较

E70 当前是 best composite：office1 使用 tissue repair，office2 使用 bin/table + vent/table local repair，其它场景沿用稳定源。

如果消融 row 改成全场景共享规则，它同时改变了：

1. 是否启用某个 repair；
2. repair 的作用域；
3. repair 的触发条件；
4. 部分场景的 export/relabel distribution。

这会导致无法归因。

### 1.3 创新点与消融 row 没有一一对应

旧创新点包括 two-layer graph memory，但上一轮 A1/A3 主要测的是 large-label repair / table-sink gate。这样会造成 reviewer 风险：论文 claim 是 graph memory，但实验支持的是 heuristic relabel。

## 2. 重构后的创新点思路

### Contribution 1：Geometry-carrier reliability, not label rewriting

建议主创新不要写成“我们提出若干 relabel rules”。更稳的表述是：

> DuoGraph3D treats 3D geometry carriers as stable objects and detects when semantic readout assigns unreliable sink labels to those carriers.

核心是 **carrier 与 semantic readout 分离**：几何 carrier 负责稳定对象/空间边界，语义 readout 只在可靠时成为最终标签。

支持证据：

- E65 证明 office2 bin 不是 missing-object，而是 large table carrier 被读成 bin；
- E66/E69/E70 证明小规模 carrier repair 可带来大指标增益；
- A3 naive/shape 负例证明不是任意 relabel 都有效，必须有 reliability boundary。

### Contribution 2：Auditable two-layer graph memory

two-layer graph 不要直接宣称是 E70 mIoU 主因。更合理的定位是：

> The graph memory makes object state auditable: current evidence, association candidates, label distributions, and export-source decisions can be inspected before committing to dense semantic output.

它的价值是状态维护、候选关联、diagnostic observability、source separation。是否直接提升 mIoU，要由 A2 单独证明。

### Contribution 3：Object-level failure attribution protocol

这应成为论文最稳的创新点之一：不仅报告最终 mIoU，而是定位到：

- 哪个 object carrier 出错；
- dominant GT 是什么；
- bbox/extent/points 是否支持 relabel；
- relabel 修改了多少对象和点；
- 修改是否只影响目标 failure family。

这解释了为什么 E70 正向，也解释了为什么 naive/shape global 失败。

## 3. 新消融设计原则

1. **每个 ablation 只回答一个问题**：组件贡献、统一性、或 graph memory 价值。
2. **每张表同时报告两个差值**：
   - `Δ vs ConceptGraphs`：方法是否仍优于 baseline；
   - `Δ vs Full E70`：移除/替代模块造成多少退化。
3. **局部 repair 与全局 shared gate 分开报告**：
   - local leave-one-out 是因果贡献；
   - shared gate 是泛化性/投稿风险。
4. **diagnostic metrics 必须进入 ablation 表**：不能只看 final all mIoU。

## 4. 最小三组消融

## Ablation 1 — E70 local leave-one-out: repair contribution under the same deployment policy

### Target hypothesis

E70 的全场景提升主要来自少数 diagnosis-guided carrier repairs；去掉对应 repair 会在目标场景/目标类别上局部退化，而不应大面积改变无关场景。

### 实验设置

固定 E70 的 scene-local composite policy，只做 leave-one-out：

| row | change | 目的 |
| --- | --- | --- |
| Full E70 | no removal | full anchor |
| w/o tissue repair | 去掉 office1 `tissue-paper:cloth` | 测 tissue/cloth 贡献 |
| w/o office2 table-sink | 去掉 office2 `bin:table` + `vent:table` | 测 office2 主修复贡献 |
| w/o bin-table only | 只去掉 office2 `bin:table` | 分离 bin/table 主因 |
| w/o vent-table only | 只去掉 office2 `vent:table` | 分离 vent/table 附加收益 |
| w/o all large-label repairs | 去掉 tissue + table-sink | 测 carrier repair 总贡献 |

### Expected signal

确认假设：

- Full E70 仍为最强；
- w/o tissue 主要损失 office1 cloth/tissue 相关指标；
- w/o bin-table 主要损失 office2 bin/table precision/IoU；
- w/o vent-table 损失小于 bin-table；
- w/o all large-label 接近 E39 / 当前 `+0.142/+1.924` 级别。

削弱假设：

- 去掉 repair 后指标几乎不变；
- 退化发生在大量无关场景/类别，说明 repair 与 claimed failure family 不匹配。

### Stop condition

拿到 full + 至少 4 个 leave-one-out row，每个 row 包含：all gap、per-scene gap、per-class target precision/recall、relabel object/point count。

---

## Ablation 2 — Shared carrier-reliability gate: generalization and boundary

### Target hypothesis

真正可发表的方法不应依赖 scene name；如果 geometry-carrier reliability 是有效原则，则一个 scene-independent gate 应该能保留 E70 的大部分收益，并避免 naive global relabel 的 office4 collapse。

### 实验设置

这不是普通 ablation，而是 **泛化性/边界实验**。建议比较：

| row | meaning |
| --- | --- |
| E70 scene-local | upper-bound / current best |
| no large-label | lower-bound / no carrier repair |
| naive global | negative boundary：无约束 relabel |
| bbox shape global | negative boundary：当前 insufficient gate |
| evidence-gated shared carrier repair | 新候选：不读 scene id，只用 object-level reliability evidence |

新的 evidence-gated shared repair 不能只用 bbox extent/thickness，至少应包含：

- source label 是否为 known sink label；
- target label 是否在 object/history/neighbor evidence 中有支持；
- object planarity / horizontal support-surface evidence；
- label entropy / top-share / CLIP margin；
- relabel object count 和 relabel point mass 的 guard。

### Expected signal

确认假设：

- evidence-gated shared row 明显高于 no large-label；
- 接近 E70，目标至少 all ΔmIoU > +2.0，最好 > +2.5；
- 不出现 office4 这类严重负迁移；
- relabel monitor 显示改动对象少且集中在诊断支持的 failure family。

削弱假设：

- evidence-gated shared row 仍只有 `+0.6` 左右；
- office4 / room2 仍 collapse；
- gate 漏掉 office2 关键 false-bin carrier。

### Stop condition

如果 evidence-gated shared gate 不能超过 `+2.0 mIoU` 或仍有场景 mIoU/mF1 为负，则论文不得把 unified carrier repair 当主方法；E70 只能作为 diagnostic composite / case-study result。

---

## Ablation 3 — Two-layer graph memory: state and diagnostic value

### Target hypothesis

two-layer graph memory 的贡献不是直接替代 dense geometry export，而是提升在线 object state 的可观测性与 association 稳定性，为 carrier/source decision 提供诊断依据。

### 实验设置

不要只看 mIoU。需要报告 official metrics + diagnostic metrics。

| row | meaning | primary diagnostics |
| --- | --- | --- |
| framewise / no memory | 无长期状态 | duplicate birth、fragmentation |
| Layer1 only | 当前 evidence repair | mixed-label mass、over/under-merge |
| Layer2 association only / cand | 当前到历史候选关联 | candidate recall@K、wrong-candidate rate |
| full two-layer memory | current + memory state | memory purity、export source coverage、object continuity |
| forced geometry export | memory 只做状态，不做 dense source | 检查 export/source separation |
| forced memory-dense export | memory 作为 dense source | 检查 memory dense 是否不稳定 |

### Expected signal

确认假设：

- full two-layer 在 duplicate birth、fragmentation、candidate recall、memory purity 上优于 no-memory / single-layer；
- forced memory-dense 在部分场景不稳定，说明需要 export/source separation；
- 即使 mIoU 提升不大，diagnostic metrics 显示它确实让后续 carrier repair 可定位、可解释。

削弱假设：

- graph rows 在 diagnostic metrics 上无明显差异；
- forced memory-dense 始终最好且无风险，则当前 source separation claim 变弱；
- graph memory 完全不能解释任何 repair decision。

### Stop condition

先在 `room0, office1, office2, office3, office4` 跑代表场景；如果趋势清晰，主文放 compact diagnostic table，full Replica 版本放 supplement。

## 5. 论文实验组织建议

### Main Table：Effectiveness

ConceptGraphs vs DuoGraph3D Full E70。主表只回答一个问题：是否超过强 baseline。

### Table 2：Causal repair ablation

放 Ablation 1。这里要用 `Δ vs CG` 和 `drop vs E70` 双口径。

### Table 3：Generalization and boundary

放 Ablation 2。这里明确展示：naive/shape global 失败，evidence-gated shared 是否能成立。若 shared gate 仍失败，这张表就是诚实 limitation，不要硬包装。

### Table 4 / Supplement：Graph memory diagnostics

放 Ablation 3。强调 graph memory 的 state/diagnostic value，而不是强行说它单独带来最大 mIoU。

### Diagnostic Case Table

不作为 ablation，而作为 claim-support table：

| case | failure before | object-level evidence | repair | outcome |
| --- | --- | --- | --- | --- |
| office2 bin/table | bin precision low | GT bin recall high; table carrier read as bin | bin→table | office2 jump |
| office2 vent/table | vent absorbs table/lamp/sofa | false vent objects dominated by non-vent GT | vent→table | small extra gain |
| office1 tissue/cloth | cloth lost to small-object label | large carrier read as tissue-paper | tissue→cloth | office1 gain |
| room0 cushion/sofa | broad relabel unsafe | large sofa/cushion mixed | broad relabel rejected | negative boundary |

## 6. 重新定义“正向/负面”口径

后续报告必须使用三列判断：

1. **Positive vs ConceptGraphs**：是否仍比 baseline 好；
2. **Causal contribution vs E70**：去掉后是否造成 targeted drop；
3. **Paper-claim support**：是否支持要写进论文的创新点。

例如：

- `A3_shape_gated_unified`：vs CG 是正；vs E70 是退化；对“当前 bbox shared gate 可作为主方法”是负。
- `w/o large-label`：vs CG 是弱正；vs E70 是大退化；对“carrier repair 有贡献”是正证据。
- `tissue-paper:cloth`：vs E70 局部贡献明确；对 transferable repair 是当前最强正证据。

## 7. 当前负责人判断

最应该避免的论文叙事是：

> 我们提出 two-layer graph，然后加若干 relabel 规则，结果超过 ConceptGraphs。

更稳的叙事是：

> DuoGraph3D exposes object-level carrier failures in online open-vocabulary 3D mapping. By separating geometry carriers from semantic readout, and by using a two-layer graph memory to make state and failure attribution auditable, the system can apply bounded carrier-reliability repairs that improve dense semantic evaluation over ConceptGraphs. The same diagnostics also reveal where simple global relabeling fails.

这个叙事能同时容纳 E70 正结果、A3 负结果和后续 A2 graph-memory 消融。
